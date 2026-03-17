"""Global SDK configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_REGISTRY_URL = "https://api.musher.dev"
_DEFAULT_CACHE_DIR = Path.home() / ".cache" / "musher" / "bundles"


@dataclass
class MusherConfig:
    """Configuration for the Musher SDK."""

    token: str | None = None
    registry_url: str = _DEFAULT_REGISTRY_URL
    cache_dir: Path = field(default_factory=lambda: _DEFAULT_CACHE_DIR)
    verify_checksums: bool = True
    timeout: float = 30.0
    max_retries: int = 3


_global_config: MusherConfig | None = None


def configure(
    *,
    token: str | None = None,
    registry_url: str = _DEFAULT_REGISTRY_URL,
    cache_dir: Path | None = None,
    verify_checksums: bool = True,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> None:
    """Set global SDK configuration."""
    global _global_config  # noqa: PLW0603
    _global_config = MusherConfig(
        token=token,
        registry_url=registry_url,
        cache_dir=cache_dir or _DEFAULT_CACHE_DIR,
        verify_checksums=verify_checksums,
        timeout=timeout,
        max_retries=max_retries,
    )


def get_config() -> MusherConfig:
    """Return the current global configuration, creating a default if needed."""
    global _global_config  # noqa: PLW0603
    if _global_config is None:
        _global_config = MusherConfig()
    return _global_config
