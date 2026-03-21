"""Credential resolution chain (CLI-compatible)."""

from __future__ import annotations

import logging
import os
import stat
from urllib.parse import urlparse

from musher._paths import config_dir

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


def resolve_token(*, registry_url: str | None = None, profile: str = "default") -> str | None:
    """Resolve an API token using the credential chain.

    1. Environment variables (``MUSHER_API_KEY``)
    2. OS keyring — host-scoped service ``musher/{hostname}``
    3. Profile config file — ``<config_dir>/config.toml``
    4. File fallback — ``$config_dir/api-key`` (must be 0600)
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

    # 3. Profile config file
    profile_token = _try_profile(profile=profile)
    if profile_token:
        return profile_token

    # 4. File fallback
    return _try_file()


def _try_keyring(*, registry_url: str | None = None) -> str | None:
    """Attempt to read token from OS keyring. Returns None if unavailable."""
    try:
        import keyring  # type: ignore[import-untyped]  # noqa: PLC0415

        url = registry_url or resolve_registry_url()
        hostname = urlparse(url).hostname or "api.musher.dev"
        service = f"musher/{hostname}"
        token = keyring.get_password(service, "api-key")
        if token:
            return token
    except Exception:  # noqa: BLE001
        _log.debug("keyring lookup failed", exc_info=True)
    return None


def _try_profile(profile: str = "default") -> str | None:
    """Read token from config_dir/config.toml profile section."""
    config_file = config_dir() / "config.toml"
    if not config_file.is_file():
        return None

    try:
        import tomllib  # noqa: PLC0415

        data = tomllib.loads(config_file.read_text())
        profile_data = data.get("profile", {}).get(profile, {})
        token = profile_data.get("api_key")
        if token:
            return token
    except Exception:  # noqa: BLE001
        _log.debug("profile config read failed", exc_info=True)
    return None


def _try_file() -> str | None:
    """Read token from config_dir/api-key if permissions are safe."""
    key_file = config_dir() / "api-key"
    if not key_file.is_file():
        return None

    # Check permissions — must be owner-only (0600)
    mode = key_file.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        return None

    return key_file.read_text().strip() or None
