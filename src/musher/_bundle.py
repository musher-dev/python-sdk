"""Bundle, manifest, and asset models."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from musher._types import AssetType, BundleSourceType, BundleVersionState


class _SDKSchema(BaseModel):
    """Base schema with camelCase aliasing, matching the platform API wire format."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
    )


class ManifestAsset(_SDKSchema):
    """A single layer entry in a bundle manifest (maps to BundleLayerOutput)."""

    asset_id: str
    logical_path: str
    asset_type: str
    content_sha256: str
    size_bytes: int
    media_type: str | None = None


class Manifest(_SDKSchema):
    """Bundle manifest listing all layers (maps to BundleManifestOutput)."""

    layers: list[ManifestAsset]


class ResolveResult(_SDKSchema):
    """Result of resolving a bundle reference (maps to BundleResolveOutput)."""

    bundle_id: str
    version_id: str
    namespace: str
    slug: str
    ref: str
    version: str
    source_type: BundleSourceType = BundleSourceType.CONSOLE
    oci_ref: str | None = None
    oci_digest: str | None = None
    state: BundleVersionState
    manifest: Manifest | None = None


@dataclass
class Asset:
    """A fetched asset with content bytes and metadata."""

    asset_id: str
    logical_path: str
    asset_type: AssetType
    content: bytes
    content_sha256: str
    size_bytes: int
    media_type: str | None = None


@dataclass
class Bundle:
    """A resolved bundle with its assets."""

    ref: str
    version: str
    resolve_result: ResolveResult
    _assets: dict[str, Asset] = field(default_factory=dict, repr=False)

    def asset(self, logical_path: str) -> Asset | None:
        """Get a single asset by logical path."""
        return self._assets.get(logical_path)

    def assets(self) -> list[Asset]:
        """Return all assets in this bundle."""
        return list(self._assets.values())

    def assets_by_type(self, asset_type: AssetType) -> list[Asset]:
        """Return assets filtered by type."""
        return [a for a in self._assets.values() if a.asset_type == asset_type]

    def verify(self) -> bool:
        """Verify all asset checksums. Raises NotImplementedError (stub)."""
        raise NotImplementedError
