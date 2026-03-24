"""Musher Python SDK — programmatic access to the Musher bundle registry."""

from importlib.metadata import PackageNotFoundError, version as _metadata_version

from musher._auth import resolve_registry_url
from musher._bundle import Asset, Bundle, Manifest, ManifestAsset, ResolveResult
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
