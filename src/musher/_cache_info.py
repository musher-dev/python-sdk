"""Data types for cache inspection results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


@dataclass(frozen=True)
class CachedBundleVersion:
    """Information about a single cached bundle version."""

    version: str
    size_bytes: int
    fetched_at: datetime | None
    is_fresh: bool


@dataclass(frozen=True)
class CachedBundle:
    """Information about a cached bundle across all its versions."""

    namespace: str
    slug: str
    host: str
    versions: tuple[CachedBundleVersion, ...]
    total_size_bytes: int


@dataclass(frozen=True)
class CacheInfo:
    """Summary of the local bundle cache contents."""

    path: Path
    total_size_bytes: int
    bundle_count: int
    version_count: int
    blob_count: int
    bundles: tuple[CachedBundle, ...]
