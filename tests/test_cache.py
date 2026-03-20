"""Tests for _cache module — blob and manifest operations."""

from pathlib import Path

from musher._cache import BundleCache


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

    def test_manifest_path_structure(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        cache.put_manifest("ns", "slug", "1.0.0", {"ok": True})
        expected = tmp_path / "manifests" / "ns" / "slug" / "1.0.0.json"
        assert expected.is_file()


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
