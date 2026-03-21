"""Tests for _cache module — blob, manifest, ref, and maintenance operations."""

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from musher._cache import BundleCache, _host_id_from_url


class TestHostIdFromUrl:
    def test_simple_host(self):
        assert _host_id_from_url("https://api.musher.dev") == "api.musher.dev"

    def test_host_with_port(self):
        assert _host_id_from_url("http://localhost:8080") == "localhost_8080"

    def test_host_with_path(self):
        assert _host_id_from_url("https://api.musher.dev/v1") == "api.musher.dev"

    def test_no_scheme(self):
        # urlparse puts everything in path when no scheme
        assert _host_id_from_url("localhost:8080") == "localhost"


class TestBlobOperations:
    def test_get_blob_miss(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        assert cache.get_blob("deadbeef" * 8) is None

    def test_put_and_get_blob(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        sha = "abcdef1234567890" * 4
        data = b"hello world"
        cache.put_blob(sha, data)
        assert cache.get_blob(sha) == data

    def test_blob_path_structure(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        sha = "abcdef1234567890" * 4
        cache.put_blob(sha, b"data")
        expected = tmp_path / "blobs" / "sha256" / sha[:2] / sha
        assert expected.is_file()


class TestHostPartitioning:
    def test_manifests_partitioned_by_host(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True})
        expected = tmp_path / "manifests" / "api.musher.dev" / "ns" / "slug" / "1.0.0.json"
        assert expected.is_file()

    def test_blobs_not_partitioned_by_host(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        sha = "ab" * 32
        cache.put_blob(sha, b"data")
        expected = tmp_path / "blobs" / "sha256" / sha[:2] / sha
        assert expected.is_file()

    def test_different_hosts_different_manifest_paths(self, tmp_path: Path):
        cache1 = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        cache2 = BundleCache(cache_dir=tmp_path, registry_url="http://localhost:8080")
        cache1.put_manifest("ns", "slug", "1.0.0", {"host": "prod"})
        cache2.put_manifest("ns", "slug", "1.0.0", {"host": "local"})
        assert cache1.get_manifest("ns", "slug", "1.0.0") == {"host": "prod"}
        assert cache2.get_manifest("ns", "slug", "1.0.0") == {"host": "local"}


class TestManifestOperations:
    def test_get_manifest_miss(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        assert cache.get_manifest("ns", "slug", "1.0.0") is None

    def test_put_and_get_manifest(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        data = {"bundleId": "123", "version": "1.0.0"}
        cache.put_manifest("ns", "slug", "1.0.0", data)
        result = cache.get_manifest("ns", "slug", "1.0.0")
        assert result == data

    def test_put_manifest_writes_meta_sidecar(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True}, oci_digest="sha256:abc123")
        meta_path = tmp_path / "manifests" / "api.musher.dev" / "ns" / "slug" / "1.0.0.meta.json"
        assert meta_path.is_file()
        meta = json.loads(meta_path.read_text())
        assert "fetchedAt" in meta
        assert meta["ttlSeconds"] == 86400
        assert meta["ociDigest"] == "sha256:abc123"


class TestManifestFreshness:
    def test_fresh_manifest(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True})
        assert cache.is_manifest_fresh("ns", "slug", "1.0.0")

    def test_stale_manifest(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True}, ttl=1)
        # Manually backdate the meta
        meta_path = tmp_path / "manifests" / "api.musher.dev" / "ns" / "slug" / "1.0.0.meta.json"
        meta = json.loads(meta_path.read_text())
        meta["fetchedAt"] = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
        meta_path.write_text(json.dumps(meta))
        assert not cache.is_manifest_fresh("ns", "slug", "1.0.0")

    def test_missing_meta_is_not_fresh(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        assert not cache.is_manifest_fresh("ns", "slug", "1.0.0")


class TestRefCache:
    def test_put_and_get_ref(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_ref("ns", "slug", "latest", "1.0.0")
        assert cache.get_ref("ns", "slug", "latest") == "1.0.0"

    def test_ref_miss(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        assert cache.get_ref("ns", "slug", "latest") is None

    def test_expired_ref_returns_none(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        cache.put_ref("ns", "slug", "latest", "1.0.0", ttl=1)
        # Manually expire the ref
        ref_path = tmp_path / "refs" / "api.musher.dev" / "ns" / "slug" / "latest.json"
        data = json.loads(ref_path.read_text())
        data["expiresAt"] = time.time() - 10
        ref_path.write_text(json.dumps(data))
        assert cache.get_ref("ns", "slug", "latest") is None

    def test_ref_path_structure(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        cache.put_ref("ns", "slug", "latest", "1.0.0")
        expected = tmp_path / "refs" / "api.musher.dev" / "ns" / "slug" / "latest.json"
        assert expected.is_file()


class TestCachedirTag:
    def test_tag_created_on_blob_write(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_blob("ab" * 32, b"data")
        tag = tmp_path / "CACHEDIR.TAG"
        assert tag.is_file()
        assert "8a477f597d28d172789f06886806bc55" in tag.read_text()

    def test_tag_created_on_manifest_write(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True})
        tag = tmp_path / "CACHEDIR.TAG"
        assert tag.is_file()

    def test_tag_created_on_ref_write(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_ref("ns", "slug", "latest", "1.0.0")
        tag = tmp_path / "CACHEDIR.TAG"
        assert tag.is_file()

    def test_tag_not_created_on_reads(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.get_blob("ab" * 32)
        cache.get_manifest("ns", "slug", "1.0.0")
        cache.get_ref("ns", "slug", "latest")
        tag = tmp_path / "CACHEDIR.TAG"
        assert not tag.is_file()


class TestClean:
    def test_clean_removes_expired_manifests(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True}, ttl=1)
        # Backdate the meta
        meta_path = tmp_path / "manifests" / "api.musher.dev" / "ns" / "slug" / "1.0.0.meta.json"
        meta = json.loads(meta_path.read_text())
        meta["fetchedAt"] = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
        meta_path.write_text(json.dumps(meta))
        removed = cache.clean()
        assert removed == 1
        assert cache.get_manifest("ns", "slug", "1.0.0") is None

    def test_clean_keeps_fresh_manifests(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True}, ttl=86400)
        removed = cache.clean()
        assert removed == 0
        assert cache.get_manifest("ns", "slug", "1.0.0") is not None

    def test_clean_removes_expired_refs(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path, registry_url="https://api.musher.dev")
        cache.put_ref("ns", "slug", "latest", "1.0.0", ttl=1)
        # Manually expire
        ref_path = tmp_path / "refs" / "api.musher.dev" / "ns" / "slug" / "latest.json"
        data = json.loads(ref_path.read_text())
        data["expiresAt"] = time.time() - 10
        ref_path.write_text(json.dumps(data))
        removed = cache.clean()
        assert removed == 1

    def test_clean_noop_on_empty_cache(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        assert cache.clean() == 0


class TestPurge:
    def test_purge_specific_version(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_manifest("ns", "slug", "1.0.0", {"v": "1.0.0"})
        cache.put_manifest("ns", "slug", "2.0.0", {"v": "2.0.0"})
        cache.purge("ns", "slug", "1.0.0")
        assert cache.get_manifest("ns", "slug", "1.0.0") is None
        assert cache.get_manifest("ns", "slug", "2.0.0") is not None

    def test_purge_all_versions(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_manifest("ns", "slug", "1.0.0", {"v": "1.0.0"})
        cache.put_manifest("ns", "slug", "2.0.0", {"v": "2.0.0"})
        cache.put_ref("ns", "slug", "latest", "2.0.0")
        cache.purge("ns", "slug")
        assert cache.get_manifest("ns", "slug", "1.0.0") is None
        assert cache.get_manifest("ns", "slug", "2.0.0") is None
        assert cache.get_ref("ns", "slug", "latest") is None

    def test_purge_noop_if_missing(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.purge("ns", "slug", "1.0.0")  # should not raise


class TestClear:
    def test_clear_removes_all(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_blob("ab" * 32, b"data")
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True})
        cache.clear()
        assert not tmp_path.exists()

    def test_clear_noop_if_missing(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path / "nonexistent")
        cache.clear()  # should not raise


class TestCacheDir:
    def test_custom_cache_dir(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path
