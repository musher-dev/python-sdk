"""Enums, reference types, and OCI constants matching the platform domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import override


class AssetType(StrEnum):
    """Type of asset within a bundle."""

    AGENT_SPEC = "agent_spec"
    SKILL = "skill"
    TOOLSET = "toolset"
    PROMPT = "prompt"
    CONFIG = "config"
    OTHER = "other"


class BundleVisibility(StrEnum):
    """Visibility level of a bundle."""

    PRIVATE = "private"
    PUBLIC = "public"


class BundleVersionState(StrEnum):
    """State of a published bundle version."""

    PUBLISHED = "published"
    YANKED = "yanked"


class BundleSourceType(StrEnum):
    """How the bundle was created."""

    CONSOLE = "console"
    REGISTRY = "registry"


@dataclass(frozen=True, slots=True)
class BundleRef:
    """Parsed bundle reference.

    Formats:
        - ``namespace/slug``
        - ``namespace/slug:version``
        - ``namespace/slug@sha256:digest``
    """

    namespace: str
    slug: str
    version: str | None = None
    digest: str | None = None

    @classmethod
    def parse(cls, ref: str) -> BundleRef:
        """Parse a bundle reference string."""
        if "@" in ref:
            base, digest = ref.split("@", 1)
            namespace, slug = _split_base(base)
            return cls(namespace=namespace, slug=slug, digest=digest)

        if ":" in ref:
            base, version = ref.rsplit(":", 1)
            namespace, slug = _split_base(base)
            return cls(namespace=namespace, slug=slug, version=version)

        namespace, slug = _split_base(ref)
        return cls(namespace=namespace, slug=slug)

    @override
    def __str__(self) -> str:
        base = f"{self.namespace}/{self.slug}"
        if self.digest:
            return f"{base}@{self.digest}"
        if self.version:
            return f"{base}:{self.version}"
        return base


def _split_base(base: str) -> tuple[str, str]:
    parts = base.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:  # noqa: PLR2004
        msg = f"Invalid bundle reference: expected 'namespace/slug', got '{base}'"
        raise ValueError(msg)
    return parts[0], parts[1]


# OCI media types for Musher bundle artifacts
OCI_MEDIA_TYPE_ASSET = "application/vnd.musher.bundle.v1.asset"
OCI_MEDIA_TYPE_CONFIG = "application/vnd.musher.bundle.v1.config"
