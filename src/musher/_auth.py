"""Credential resolution chain (CLI-compatible)."""

from __future__ import annotations

import logging
import os
import stat
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from pathlib import Path

_log = logging.getLogger(__name__)

_DEFAULT_REGISTRY_URL = "https://api.musher.dev"

_TOKEN_ENV_VARS = ("MUSHER_API_KEY",)
_URL_ENV_VARS = ("MUSHER_API_URL", "MUSHER_BASE_URL")


def resolve_registry_url() -> str:
    """Resolve the registry URL from environment variables or return the default.

    Checks ``MUSHER_API_URL``, ``MUSHER_BASE_URL`` in order.
    Returns the first match (stripped of trailing ``/``) or the default.
    """
    for var in _URL_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value.rstrip("/")
    return _DEFAULT_REGISTRY_URL


def resolve_token(
    *,
    registry_url: str | None = None,
    config_dir: Path | None = None,
) -> str | None:
    """Resolve an API token using the credential chain.

    1. Environment variables (``MUSHER_API_KEY``)
    2. OS keyring — host-scoped service ``musher/{host}``
    3. File fallback — ``<config_dir>/credentials/<host_id>/api-key`` (must be 0600)
    """
    # 1. Environment variables
    for var in _TOKEN_ENV_VARS:
        env_token = os.environ.get(var)
        if env_token:
            return env_token

    # 2. OS keyring (host-scoped)
    keyring_token = _try_keyring(registry_url=registry_url)
    if keyring_token:
        return keyring_token

    # 3. File fallback (host-scoped)
    return _try_file(registry_url=registry_url, config_dir=config_dir)


def _try_keyring(*, registry_url: str | None = None) -> str | None:
    """Attempt to read token from OS keyring. Returns None if unavailable."""
    try:
        import keyring  # type: ignore[import-untyped]  # noqa: PLC0415

        url = registry_url or resolve_registry_url()
        parsed = urlparse(url)
        hostname = parsed.hostname or "api.musher.dev"
        port = parsed.port
        host = f"{hostname}:{port}" if port else hostname
        service = f"musher/{host}"
        token = keyring.get_password(service, "api-key")
        if token:
            return token
    except Exception:  # noqa: BLE001
        _log.debug("keyring lookup failed", exc_info=True)
    return None


def _host_id(url: str) -> str:
    """Return a filesystem-safe host identifier from a URL."""
    parsed = urlparse(url)
    hostname = parsed.hostname or "api.musher.dev"
    port = parsed.port
    return f"{hostname}_{port}" if port else hostname


def _read_key_file(path: Path) -> str | None:
    """Read a key file if it exists and has safe permissions (0600)."""
    if not path.is_file():
        return None

    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        return None

    return path.read_text().strip() or None


def _try_file(
    *,
    registry_url: str | None = None,
    config_dir: Path | None = None,
) -> str | None:
    """Read token from host-scoped credential file."""
    if config_dir is None:
        from musher._paths import config_dir as _default_config_dir  # noqa: PLC0415

        config_dir = _default_config_dir()

    url = registry_url or resolve_registry_url()
    host = _host_id(url)

    # Host-scoped: <config_dir>/credentials/<host_id>/api-key
    host_scoped = config_dir / "credentials" / host / "api-key"
    return _read_key_file(host_scoped)
