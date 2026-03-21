"""Global SDK configuration."""

from __future__ import annotations

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

_UNSET = object()


@dataclass
class MusherConfig:
    """Configuration for the Musher SDK."""

    token: str | None = None
    registry_url: str = "https://api.musher.dev"
    cache_dir: Path = field(default_factory=_default_cache_dir)
    config_dir: Path = field(default_factory=_default_config_dir)
    data_dir: Path = field(default_factory=_default_data_dir)
    state_dir: Path = field(default_factory=_default_state_dir)
    verify_checksums: bool = True
    timeout: float = 30.0
    max_retries: int = 2


_global_config: MusherConfig | None = None


def configure(  # noqa: PLR0913
    *,
    token: object = _UNSET,
    api_key: object = _UNSET,
    registry_url: str | None = None,
    api_url: str | None = None,
    cache_dir: Path | None = None,
    config_dir: Path | None = None,
    data_dir: Path | None = None,
    state_dir: Path | None = None,
    verify_checksums: bool = True,
    timeout: float = 30.0,
    max_retries: int = 2,
) -> None:
    """Set global SDK configuration.

    ``api_key`` is an alias for ``token``; ``api_url`` is an alias for
    ``registry_url``.  When neither ``token`` nor ``api_key`` is provided,
    the credential chain is used to auto-discover a token.
    """
    from musher._auth import resolve_registry_url, resolve_token  # noqa: PLC0415

    global _global_config  # noqa: PLW0603

    # Resolve URL and data_dir first so token resolution can use them
    resolved_url = registry_url or api_url or resolve_registry_url()
    resolved_data_dir = data_dir or _default_data_dir()

    # Resolve token: explicit token > explicit api_key > credential chain
    if token is not _UNSET:
        resolved_token: str | None = token  # type: ignore[assignment]
    elif api_key is not _UNSET:
        resolved_token = api_key  # type: ignore[assignment]
    else:
        resolved_token = resolve_token(registry_url=resolved_url, data_dir=resolved_data_dir)

    _global_config = MusherConfig(
        token=resolved_token,
        registry_url=resolved_url,
        cache_dir=cache_dir or _default_cache_dir(),
        config_dir=config_dir or _default_config_dir(),
        data_dir=resolved_data_dir,
        state_dir=state_dir or _default_state_dir(),
        verify_checksums=verify_checksums,
        timeout=timeout,
        max_retries=max_retries,
    )


def get_config() -> MusherConfig:
    """Return the current global configuration, creating a default if needed.

    Auto-discovers credentials via the credential chain in :mod:`musher._auth`
    and registry URL from environment variables.
    """
    global _global_config  # noqa: PLW0603
    if _global_config is None:
        from musher._auth import resolve_registry_url, resolve_token  # noqa: PLC0415

        url = resolve_registry_url()
        _global_config = MusherConfig(
            token=resolve_token(registry_url=url),
            registry_url=url,
        )
    return _global_config
