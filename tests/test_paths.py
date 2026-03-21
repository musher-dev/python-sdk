"""Tests for _paths module — platform-aware directory resolution."""

import os
from pathlib import Path
from unittest.mock import patch

from musher._paths import (
    _resolve_root,
    cache_dir,
    config_dir,
    data_dir,
    runtime_dir,
    state_dir,
)


def _dummy_platform_fn(appname: str) -> Path:
    return Path(f"/platform-default/{appname}")


class TestResolveRoot:
    def test_branded_var_wins(self, tmp_path: Path):
        with patch.dict(os.environ, {"MUSHER_CACHE_HOME": str(tmp_path)}, clear=False):
            result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
            assert result == tmp_path

    def test_musher_home_umbrella(self, tmp_path: Path):
        with patch.dict(
            os.environ,
            {"MUSHER_HOME": str(tmp_path)},
            clear=False,
        ):
            env_backup = os.environ.pop("MUSHER_CACHE_HOME", None)
            try:
                result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
                assert result == tmp_path / "cache"
            finally:
                if env_backup is not None:
                    os.environ["MUSHER_CACHE_HOME"] = env_backup

    def test_platformdirs_fallback(self):
        env_backup_home = os.environ.pop("MUSHER_HOME", None)
        env_backup_cache = os.environ.pop("MUSHER_CACHE_HOME", None)
        try:
            result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
            assert result == Path("/platform-default/musher")
        finally:
            if env_backup_home is not None:
                os.environ["MUSHER_HOME"] = env_backup_home
            if env_backup_cache is not None:
                os.environ["MUSHER_CACHE_HOME"] = env_backup_cache

    def test_branded_var_takes_precedence_over_musher_home(self, tmp_path: Path):
        branded = tmp_path / "branded"
        home = tmp_path / "home"
        with patch.dict(
            os.environ,
            {"MUSHER_CACHE_HOME": str(branded), "MUSHER_HOME": str(home)},
            clear=False,
        ):
            result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
            assert result == branded

    def test_relative_branded_var_ignored(self):
        env_backup_home = os.environ.pop("MUSHER_HOME", None)
        try:
            with patch.dict(os.environ, {"MUSHER_CACHE_HOME": "relative/path"}, clear=False):
                result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
                # Should fall through to platformdirs since relative path is ignored
                assert result == Path("/platform-default/musher")
        finally:
            if env_backup_home is not None:
                os.environ["MUSHER_HOME"] = env_backup_home

    def test_relative_musher_home_ignored(self):
        env_backup_cache = os.environ.pop("MUSHER_CACHE_HOME", None)
        try:
            with patch.dict(os.environ, {"MUSHER_HOME": "relative/home"}, clear=False):
                result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
                assert result == Path("/platform-default/musher")
        finally:
            if env_backup_cache is not None:
                os.environ["MUSHER_CACHE_HOME"] = env_backup_cache


class TestDirectoryFunctions:
    def test_cache_dir_returns_path(self):
        result = cache_dir()
        assert isinstance(result, Path)

    def test_config_dir_returns_path(self):
        result = config_dir()
        assert isinstance(result, Path)

    def test_data_dir_returns_path(self):
        result = data_dir()
        assert isinstance(result, Path)

    def test_state_dir_returns_path(self):
        result = state_dir()
        assert isinstance(result, Path)

    def test_runtime_dir_returns_path(self):
        result = runtime_dir()
        assert isinstance(result, Path)

    def test_musher_home_derives_all_categories(self, tmp_path: Path):
        env_overrides = {
            "MUSHER_HOME": str(tmp_path),
        }
        # Clear individual overrides
        keys_to_clear = [
            "MUSHER_CACHE_HOME",
            "MUSHER_CONFIG_HOME",
            "MUSHER_DATA_HOME",
            "MUSHER_STATE_HOME",
            "MUSHER_RUNTIME_DIR",
        ]
        clean_env = {k: v for k, v in os.environ.items() if k not in keys_to_clear}
        clean_env.update(env_overrides)
        with patch.dict(os.environ, clean_env, clear=True):
            assert cache_dir() == tmp_path / "cache"
            assert config_dir() == tmp_path / "config"
            assert data_dir() == tmp_path / "data"
            assert state_dir() == tmp_path / "state"
            assert runtime_dir() == tmp_path / "runtime"
