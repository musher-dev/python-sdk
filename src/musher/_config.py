"""Global SDK configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _xdg_cache_home() -> Path:
    """Return XDG_CACHE_HOME, defaulting to ~/.cache."""
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


_DEFAULT_REGISTRY_URL = "https://api.musher.dev"


def _default_cache_dir() -> Path:
    return _xdg_cache_home() / "musher"


@dataclass
class MusherConfig:
    """Configuration for the Musher SDK."""

    token: str | None = None
    registry_url: str = _DEFAULT_REGISTRY_URL
    cache_dir: Path = field(default_factory=_default_cache_dir)
    verify_checksums: bool = True
    timeout: float = 60.0
    max_retries: int = 3


_global_config: MusherConfig | None = None


def configure(
    *,
    token: str | None = None,
    registry_url: str | None = None,
    cache_dir: Path | None = None,
    verify_checksums: bool = True,
    timeout: float = 60.0,
    max_retries: int = 3,
) -> None:
    """Set global SDK configuration."""
    global _global_config  # noqa: PLW0603
    _global_config = MusherConfig(
        token=token,
        registry_url=registry_url or os.environ.get("MUSHER_API_URL", _DEFAULT_REGISTRY_URL),
        cache_dir=cache_dir or _default_cache_dir(),
        verify_checksums=verify_checksums,
        timeout=timeout,
        max_retries=max_retries,
    )


def get_config() -> MusherConfig:
    """Return the current global configuration, creating a default if needed.

    Auto-discovers ``MUSHER_API_KEY`` and ``MUSHER_API_URL`` env vars,
    then falls back to the credential chain in :mod:`musher._auth`.
    """
    global _global_config  # noqa: PLW0603
    if _global_config is None:
        from musher._auth import resolve_token  # noqa: PLC0415

        _global_config = MusherConfig(
            token=resolve_token(),
            registry_url=os.environ.get("MUSHER_API_URL", _DEFAULT_REGISTRY_URL),
        )
    return _global_config
