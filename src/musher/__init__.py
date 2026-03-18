"""Musher Python SDK — programmatic access to the Musher bundle registry."""

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
    OCI_MEDIA_TYPE_ASSET,
    OCI_MEDIA_TYPE_CONFIG,
    AssetType,
    BundleRef,
    BundleSourceType,
    BundleVersionState,
    BundleVisibility,
)

__all__ = [
    "OCI_MEDIA_TYPE_ASSET",
    "OCI_MEDIA_TYPE_CONFIG",
    # Errors
    "APIError",
    "AgentSpecHandle",
    # Models
    "Asset",
    # Types
    "AssetType",
    # Client
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
    # Config
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
    "configure",
    "get_config",
    # Convenience
    "pull",
    "pull_async",
]


def pull(ref: str) -> Bundle:
    """Pull a bundle using the global configuration (sync convenience)."""
    with Client() as client:
        return client.pull(ref)


async def pull_async(ref: str) -> Bundle:
    """Pull a bundle using the global configuration (async convenience)."""
    async with AsyncClient() as client:
        return await client.pull(ref)
