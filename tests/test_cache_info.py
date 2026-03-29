"""Tests for cache management API — scan, module-level functions, and Client methods."""

from pathlib import Path

import pytest

import musher
from musher._cache import BundleCache
from musher._cache_info import CachedBundle, CachedBundleVersion, CacheInfo
from musher._client import Client
from musher._config import MusherConfig

REGISTRY_URL = "https://api.musher.dev"


def _populate_cache(
    cache: BundleCache,
    namespace: str = "myorg",
    slug: str = "my-bundle",
    version: str = "1.0.0",
    blob_data: bytes = b"hello world",
    blob_sha: str = "abcdef1234567890" * 4,
) -> None:
    """Helper to populate a cache with a manifest referencing a blob."""
    manifest: dict[str, object] = {
        "manifest": {
            "layers": [
                {
                    "logicalPath": "prompt.txt",
                    "assetType": "prompt",
                    "contentSha256": blob_sha,
                    "sizeBytes": len(blob_data),
                }
            ]
        }
    }
    cache.put_manifest(namespace, slug, version, manifest)
    cache.put_blob(blob_sha, blob_data)


class TestCacheInfoTypes:
    def test_cached_bundle_version_frozen(self) -> None:
        v = CachedBundleVersion(version="1.0.0", size_bytes=100, fetched_at=None, is_fresh=False)
        with pytest.raises(AttributeError):
            v.version = "2.0.0"  # type: ignore[misc]

    def test_cached_bundle_frozen(self) -> None:
        b = CachedBundle(
            namespace="ns",
            slug="slug",
            host="localhost",
            versions=(),
            total_size_bytes=0,
        )
        with pytest.raises(AttributeError):
            b.namespace = "other"  # type: ignore[misc]

    def test_cache_info_frozen(self) -> None:
        info = CacheInfo(
            path=Path("/tmp"),
            total_size_bytes=0,
            bundle_count=0,
            version_count=0,
            blob_count=0,
            bundles=(),
        )
        with pytest.raises(AttributeError):
            info.bundle_count = 5  # type: ignore[misc]


class TestBundleCacheScan:
    def test_empty_cache(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        info = cache.scan()

        assert info.path == tmp_path
        assert info.total_size_bytes == 0
        assert info.bundle_count == 0
        assert info.version_count == 0
        assert info.blob_count == 0
        assert info.bundles == ()

    def test_single_bundle_single_version(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        blob_data = b"hello world"
        blob_sha = "abcdef1234567890" * 4
        _populate_cache(cache, blob_data=blob_data, blob_sha=blob_sha)

        info = cache.scan()

        assert info.bundle_count == 1
        assert info.version_count == 1
        assert info.blob_count == 1
        assert info.total_size_bytes > 0

        bundle = info.bundles[0]
        assert bundle.namespace == "myorg"
        assert bundle.slug == "my-bundle"
        assert bundle.host == "api.musher.dev"
        assert len(bundle.versions) == 1

        ver = bundle.versions[0]
        assert ver.version == "1.0.0"
        assert ver.size_bytes == len(blob_data)
        assert ver.fetched_at is not None
        assert ver.is_fresh is True

    def test_single_bundle_multiple_versions(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        sha1 = "aa" * 32
        sha2 = "bb" * 32
        _populate_cache(cache, version="1.0.0", blob_sha=sha1, blob_data=b"v1")
        _populate_cache(cache, version="2.0.0", blob_sha=sha2, blob_data=b"v2data")

        info = cache.scan()

        assert info.bundle_count == 1
        assert info.version_count == 2
        assert info.blob_count == 2

        bundle = info.bundles[0]
        versions_by_name = {v.version: v for v in bundle.versions}
        assert "1.0.0" in versions_by_name
        assert "2.0.0" in versions_by_name
        assert versions_by_name["1.0.0"].size_bytes == 2
        assert versions_by_name["2.0.0"].size_bytes == 6

    def test_multiple_bundles(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        sha1 = "aa" * 32
        sha2 = "bb" * 32
        _populate_cache(cache, namespace="org1", slug="bundle-a", blob_sha=sha1, blob_data=b"a")
        _populate_cache(cache, namespace="org2", slug="bundle-b", blob_sha=sha2, blob_data=b"b")

        info = cache.scan()

        assert info.bundle_count == 2
        assert info.version_count == 2
        slugs = {b.slug for b in info.bundles}
        assert slugs == {"bundle-a", "bundle-b"}

    def test_multi_host_partitions(self, tmp_path: Path) -> None:
        cache1 = BundleCache(cache_dir=tmp_path, registry_url="https://host1.dev")
        cache2 = BundleCache(cache_dir=tmp_path, registry_url="https://host2.dev")
        sha1 = "aa" * 32
        sha2 = "bb" * 32
        _populate_cache(cache1, slug="a", blob_sha=sha1, blob_data=b"a")
        _populate_cache(cache2, slug="b", blob_sha=sha2, blob_data=b"b")

        # scan() discovers all hosts
        info = cache1.scan()

        assert info.bundle_count == 2
        hosts = {b.host for b in info.bundles}
        assert hosts == {"host1.dev", "host2.dev"}

    def test_missing_meta_sidecar(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        _populate_cache(cache)

        # Remove the meta sidecar
        meta_files = list((tmp_path / "manifests").rglob("*.meta.json"))
        assert len(meta_files) == 1
        meta_files[0].unlink()

        info = cache.scan()

        assert info.bundle_count == 1
        ver = info.bundles[0].versions[0]
        assert ver.fetched_at is None
        assert ver.is_fresh is False

    def test_expired_manifest_not_fresh(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        # Put manifest with a very short TTL
        manifest: dict[str, object] = {"manifest": {"layers": []}}
        cache.put_manifest("ns", "slug", "1.0.0", manifest, ttl=0)

        # Give it a moment to expire
        info = cache.scan()
        ver = info.bundles[0].versions[0]
        assert ver.is_fresh is False

    def test_blob_without_manifest_counted(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        sha = "cc" * 32
        cache.put_blob(sha, b"orphan blob")

        info = cache.scan()

        assert info.blob_count == 1
        assert info.bundle_count == 0
        assert info.total_size_bytes == len(b"orphan blob")


class TestModuleLevelCacheFunctions:
    def test_cache_info_on_empty(self, tmp_path: Path) -> None:
        info = musher.cache_info(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        assert info.bundle_count == 0
        assert info.path == tmp_path

    def test_cache_info_with_data(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        _populate_cache(cache)

        info = musher.cache_info(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        assert info.bundle_count == 1
        assert info.blob_count == 1

    def test_cache_path(self, tmp_path: Path) -> None:
        assert musher.cache_path(cache_dir=tmp_path) == tmp_path

    def test_cache_remove_by_version(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        sha1 = "aa" * 32
        sha2 = "bb" * 32
        _populate_cache(cache, version="1.0.0", blob_sha=sha1, blob_data=b"v1")
        _populate_cache(cache, version="2.0.0", blob_sha=sha2, blob_data=b"v2")

        musher.cache_remove(
            "myorg/my-bundle:1.0.0",
            cache_dir=tmp_path,
            registry_url=REGISTRY_URL,
        )

        info = musher.cache_info(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        assert info.version_count == 1
        assert info.bundles[0].versions[0].version == "2.0.0"

    def test_cache_remove_all_versions(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        sha1 = "aa" * 32
        sha2 = "bb" * 32
        _populate_cache(cache, version="1.0.0", blob_sha=sha1, blob_data=b"v1")
        _populate_cache(cache, version="2.0.0", blob_sha=sha2, blob_data=b"v2")

        musher.cache_remove(
            "myorg/my-bundle",
            cache_dir=tmp_path,
            registry_url=REGISTRY_URL,
        )

        info = musher.cache_info(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        assert info.bundle_count == 0

    def test_cache_clear(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        _populate_cache(cache)

        musher.cache_clear(cache_dir=tmp_path)
        assert not tmp_path.exists()

    def test_cache_clean_removes_expired(self, tmp_path: Path) -> None:
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        # Create manifest with TTL=0 so it's immediately expired
        manifest: dict[str, object] = {"manifest": {"layers": []}}
        cache.put_manifest("ns", "slug", "1.0.0", manifest, ttl=0)

        removed = musher.cache_clean(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        assert removed >= 1


class TestClientCacheMethods:
    def test_client_cache_info(self, tmp_path: Path) -> None:
        config = MusherConfig(
            token="test-key",
            cache_dir=tmp_path,
            registry_url=REGISTRY_URL,
        )
        with Client(config=config) as client:
            info = client.cache_info()
            assert info.path == tmp_path
            assert info.bundle_count == 0

    def test_client_cache_path(self, tmp_path: Path) -> None:
        config = MusherConfig(
            token="test-key",
            cache_dir=tmp_path,
            registry_url=REGISTRY_URL,
        )
        with Client(config=config) as client:
            assert client.cache_path() == tmp_path

    def test_client_cache_clear(self, tmp_path: Path) -> None:
        config = MusherConfig(
            token="test-key",
            cache_dir=tmp_path,
            registry_url=REGISTRY_URL,
        )
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        _populate_cache(cache)

        with Client(config=config) as client:
            client.cache_clear()
            assert not tmp_path.exists()

    def test_client_cache_remove(self, tmp_path: Path) -> None:
        config = MusherConfig(
            token="test-key",
            cache_dir=tmp_path,
            registry_url=REGISTRY_URL,
        )
        cache = BundleCache(cache_dir=tmp_path, registry_url=REGISTRY_URL)
        _populate_cache(cache)

        with Client(config=config) as client:
            client.cache_remove("myorg/my-bundle:1.0.0")
            info = client.cache_info()
            assert info.bundle_count == 0
