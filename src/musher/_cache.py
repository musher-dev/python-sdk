"""XDG-compliant disk cache for downloaded bundles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from musher._config import get_config

if TYPE_CHECKING:
    from pathlib import Path


class BundleCache:
    """Local disk cache for bundle assets.

    Defaults to ``~/.cache/musher/bundles/`` (XDG_CACHE_HOME compliant).
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or get_config().cache_dir

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def get(self, ref: str, version: str) -> bytes | None:
        """Retrieve a cached bundle. Returns None on cache miss."""
        raise NotImplementedError

    def put(self, ref: str, version: str, data: bytes) -> None:
        """Store a bundle in the cache."""
        raise NotImplementedError

    def evict(self, ref: str, version: str) -> None:
        """Remove a specific bundle from the cache."""
        raise NotImplementedError

    def clear(self) -> None:
        """Remove all cached bundles."""
        raise NotImplementedError
