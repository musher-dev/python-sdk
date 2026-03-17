"""Tests for _cache module — default cache dir resolution."""

from pathlib import Path

import pytest

from musher._cache import BundleCache


class TestBundleCache:
    def test_default_cache_dir(self):
        cache = BundleCache()
        assert cache.cache_dir == Path.home() / ".cache" / "musher" / "bundles"

    def test_custom_cache_dir(self, tmp_path: Path):
        cache = BundleCache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path

    def test_get_raises_not_implemented(self):
        cache = BundleCache()
        with pytest.raises(NotImplementedError):
            cache.get("org/bundle", "1.0.0")

    def test_put_raises_not_implemented(self):
        cache = BundleCache()
        with pytest.raises(NotImplementedError):
            cache.put("org/bundle", "1.0.0", b"data")

    def test_evict_raises_not_implemented(self):
        cache = BundleCache()
        with pytest.raises(NotImplementedError):
            cache.evict("org/bundle", "1.0.0")

    def test_clear_raises_not_implemented(self):
        cache = BundleCache()
        with pytest.raises(NotImplementedError):
            cache.clear()
