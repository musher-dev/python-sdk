"""Global SDK configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from musher._paths import (
    cache_dir as _default_cache_dir,
    config_dir as _default_config_dir,
    data_dir as _default_data_dir,
    state_dir as _default_state_dir,
)

if TYPE_CHECKING:
    from pathlib import Path

_DEFAULT_REGISTRY_URL = "https://api.musher.dev"


@dataclass
class MusherConfig:
    """Configuration for the Musher SDK."""

    token: str | None = None
    registry_url: str = _DEFAULT_REGISTRY_URL
    cache_dir: Path = field(default_factory=_default_cache_dir)
    config_dir: Path = field(default_factory=_default_config_dir)
    data_dir: Path = field(default_factory=_default_data_dir)
    state_dir: Path = field(default_factory=_default_state_dir)
    verify_checksums: bool = True
    timeout: float = 60.0
    max_retries: int = 3


_global_config: MusherConfig | None = None


def configure(  # noqa: PLR0913
    *,
    token: str | None = None,
    registry_url: str | None = None,
    cache_dir: Path | None = None,
    config_dir: Path | None = None,
    data_dir: Path | None = None,
    state_dir: Path | None = None,
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
        config_dir=config_dir or _default_config_dir(),
        data_dir=data_dir or _default_data_dir(),
        state_dir=state_dir or _default_state_dir(),
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
