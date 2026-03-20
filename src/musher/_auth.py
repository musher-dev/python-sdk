"""Credential resolution chain (CLI-compatible)."""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

_log = logging.getLogger(__name__)


def _xdg_config_home() -> Path:
    """Return XDG_CONFIG_HOME, defaulting to ~/.config."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def resolve_token() -> str | None:
    """Resolve an API token using the same 3-tier priority as the CLI.

    1. ``MUSHER_API_KEY`` environment variable
    2. OS keyring — service ``dev.musher.musher``, username ``api-key``
    3. File fallback — ``$XDG_CONFIG_HOME/musher/api-key`` (must be 0600)
    """
    # 1. Environment variable
    env_token = os.environ.get("MUSHER_API_KEY")
    if env_token:
        return env_token

    # 2. OS keyring (optional dependency)
    keyring_token = _try_keyring()
    if keyring_token:
        return keyring_token

    # 3. File fallback
    return _try_file()


def _try_keyring() -> str | None:
    """Attempt to read token from OS keyring. Returns None if unavailable."""
    try:
        import keyring  # type: ignore[import-untyped]  # noqa: PLC0415

        token = keyring.get_password("dev.musher.musher", "api-key")
        if token:
            return token
    except Exception:  # noqa: BLE001
        _log.debug("keyring lookup failed", exc_info=True)
    return None


def _try_file() -> str | None:
    """Read token from $XDG_CONFIG_HOME/musher/api-key if permissions are safe."""
    key_file = _xdg_config_home() / "musher" / "api-key"
    if not key_file.is_file():
        return None

    # Check permissions — must be owner-only (0600)
    mode = key_file.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        return None

    return key_file.read_text().strip() or None
