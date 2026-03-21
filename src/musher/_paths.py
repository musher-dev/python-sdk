"""Platform-aware directory resolution for the musher ecosystem."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from platformdirs import (
    user_cache_path,
    user_config_path,
    user_data_path,
    user_runtime_path,
    user_state_path,
)

if TYPE_CHECKING:
    from collections.abc import Callable

APP_NAME = "musher"


def _resolve_root(branded_var: str, category: str, platform_fn: Callable[..., Path]) -> Path:
    """Resolve a directory root using the standard precedence chain.

    1. Branded env var (e.g. ``MUSHER_CACHE_HOME``)
    2. ``MUSHER_HOME/<category>`` umbrella
    3. Windows flat layout: ``%LOCALAPPDATA%\\musher\\<category>``
    4. ``platformdirs`` (XDG on Linux, Library on macOS)
    """
    # 1. Branded env var
    branded = os.environ.get(branded_var)
    if branded:
        p = Path(branded)
        if p.is_absolute():
            return p

    # 2. MUSHER_HOME umbrella
    home = os.environ.get("MUSHER_HOME")
    if home:
        p = Path(home)
        if p.is_absolute():
            return p / category

    # 3. Windows flat layout
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_NAME / category
        return Path.home() / "AppData" / "Local" / APP_NAME / category

    # 4. platformdirs
    return platform_fn(APP_NAME)


def cache_dir() -> Path:
    """Return the cache root directory."""
    return _resolve_root("MUSHER_CACHE_HOME", "cache", user_cache_path)


def config_dir() -> Path:
    """Return the config root directory."""
    return _resolve_root("MUSHER_CONFIG_HOME", "config", user_config_path)


def data_dir() -> Path:
    """Return the data root directory."""
    return _resolve_root("MUSHER_DATA_HOME", "data", user_data_path)


def state_dir() -> Path:
    """Return the state root directory."""
    return _resolve_root("MUSHER_STATE_HOME", "state", user_state_path)


def runtime_dir() -> Path:
    """Return the runtime root directory."""
    return _resolve_root("MUSHER_RUNTIME_DIR", "runtime", user_runtime_path)
