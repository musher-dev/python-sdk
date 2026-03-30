"""Musher Python SDK — programmatic access to the Musher bundle registry."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _metadata_version
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from musher._auth import resolve_registry_url
from musher._bundle import Asset, Bundle, Manifest, ManifestAsset, ResolveResult
from musher._cache import BundleCache  # internal; not re-exported in __all__
from musher._cache_info import CachedBundle, CachedBundleVersion, CacheInfo
from musher._client import AsyncClient, Client
from musher._config import MusherConfig, configure, get_config
from musher._errors import (
    APIError,
    AuthenticationError,
    BundleNotFoundError,
    CacheError,
    IntegrityError,
    MusherError,
    RateLimitError,
    RegistryError,
    VersionNotFoundError,
)
from musher._export import ClaudePluginExport, OpenAIInlineSkill, OpenAILocalSkill
from musher._handles import (
    AgentSpecHandle,
    BundleSelection,
    FileHandle,
    PromptHandle,
    SkillHandle,
    ToolsetHandle,
)
from musher._types import (
    AssetType,
    BundleRef,
    BundleSourceType,
    BundleVersionState,
    BundleVisibility,
)

try:
    __version__ = _metadata_version("musher-sdk")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "APIError",
    "AgentSpecHandle",
    "Asset",
    "AssetType",
    "AsyncClient",
    "AuthenticationError",
    "Bundle",
    "BundleNotFoundError",
    "BundleRef",
    "BundleSelection",
    "BundleSourceType",
    "BundleVersionState",
    "BundleVisibility",
    "CacheError",
    "CacheInfo",
    "CachedBundle",
    "CachedBundleVersion",
    "ClaudePluginExport",
    "Client",
    "FileHandle",
    "IntegrityError",
    "Manifest",
    "ManifestAsset",
    "MusherConfig",
    "MusherError",
    "OpenAIInlineSkill",
    "OpenAILocalSkill",
    "PromptHandle",
    "RateLimitError",
    "RegistryError",
    "ResolveResult",
    "SkillHandle",
    "ToolsetHandle",
    "VersionNotFoundError",
    "__version__",
    "cache_clean",
    "cache_clear",
    "cache_info",
    "cache_path",
    "cache_remove",
    "configure",
    "get_config",
    "pull",
    "pull_async",
    "resolve",
    "resolve_async",
    "resolve_registry_url",
]


def pull(ref: str) -> Bundle:
    """Pull a bundle using the global configuration (sync convenience)."""
    with Client() as client:
        return client.pull(ref)


async def pull_async(ref: str) -> Bundle:
    """Pull a bundle using the global configuration (async convenience)."""
    async with AsyncClient() as client:
        return await client.pull(ref)


def resolve(ref: str) -> ResolveResult:
    """Resolve a bundle reference without pulling (sync convenience)."""
    with Client() as client:
        return client.resolve(ref)


async def resolve_async(ref: str) -> ResolveResult:
    """Resolve a bundle reference without pulling (async convenience)."""
    async with AsyncClient() as client:
        return await client.resolve(ref)


# ── Cache management ──────────────────────────────────────────────


def _make_cache(
    cache_dir: Path | None = None,
    registry_url: str | None = None,
) -> BundleCache:
    from musher._paths import cache_dir as _default_cache_dir  # noqa: PLC0415

    return BundleCache(
        cache_dir=cache_dir or _default_cache_dir(),
        registry_url=registry_url or resolve_registry_url(),
    )


def cache_info(
    *,
    cache_dir: Path | None = None,
    registry_url: str | None = None,
) -> CacheInfo:
    """Scan the local bundle cache and return statistics."""
    return _make_cache(cache_dir, registry_url).scan()


def cache_remove(
    ref: str,
    *,
    cache_dir: Path | None = None,
    registry_url: str | None = None,
) -> None:
    """Remove a specific bundle from the cache."""
    parsed = BundleRef.parse(ref)
    _make_cache(cache_dir, registry_url).purge(parsed.namespace, parsed.slug, parsed.version)


def cache_clear(*, cache_dir: Path | None = None) -> None:
    """Remove all cached data."""
    from musher._paths import cache_dir as _default_cache_dir  # noqa: PLC0415

    cache = BundleCache(cache_dir=cache_dir or _default_cache_dir())
    cache.clear()


def cache_clean(
    *,
    cache_dir: Path | None = None,
    registry_url: str | None = None,
) -> int:
    """Remove expired entries and garbage-collect orphaned blobs.

    Returns the number of entries removed.
    """
    return _make_cache(cache_dir, registry_url).clean()


def cache_path(*, cache_dir: Path | None = None) -> Path:
    """Return the cache directory path."""
    if cache_dir:
        return cache_dir
    from musher._paths import cache_dir as _default_cache_dir  # noqa: PLC0415

    return _default_cache_dir()
