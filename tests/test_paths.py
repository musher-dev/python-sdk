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


class TestWindowsPaths:
    def test_windows_uses_localappdata(self):
        env_backup_home = os.environ.pop("MUSHER_HOME", None)
        env_backup_cache = os.environ.pop("MUSHER_CACHE_HOME", None)
        try:
            with (
                patch("musher._paths.sys") as mock_sys,
                patch.dict(
                    os.environ, {"LOCALAPPDATA": "C:\\Users\\test\\AppData\\Local"}, clear=False
                ),
            ):
                mock_sys.platform = "win32"
                result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
                assert result == Path("C:\\Users\\test\\AppData\\Local") / "musher" / "cache"
        finally:
            if env_backup_home is not None:
                os.environ["MUSHER_HOME"] = env_backup_home
            if env_backup_cache is not None:
                os.environ["MUSHER_CACHE_HOME"] = env_backup_cache

    def test_windows_flat_layout_all_categories(self):
        env_vars_to_clear = [
            "MUSHER_HOME",
            "MUSHER_CACHE_HOME",
            "MUSHER_CONFIG_HOME",
            "MUSHER_DATA_HOME",
            "MUSHER_STATE_HOME",
            "MUSHER_RUNTIME_DIR",
        ]
        backups = {k: os.environ.pop(k, None) for k in env_vars_to_clear}
        try:
            with (
                patch("musher._paths.sys") as mock_sys,
                patch.dict(
                    os.environ, {"LOCALAPPDATA": "C:\\Users\\test\\AppData\\Local"}, clear=False
                ),
            ):
                mock_sys.platform = "win32"
                for category, _fn in [
                    ("cache", cache_dir),
                    ("config", config_dir),
                    ("data", data_dir),
                    ("state", state_dir),
                    ("runtime", runtime_dir),
                ]:
                    branded_var = (
                        f"MUSHER_{category.upper()}_HOME"
                        if category != "runtime"
                        else "MUSHER_RUNTIME_DIR"
                    )
                    result = _resolve_root(branded_var, category, _dummy_platform_fn)
                    expected = Path("C:\\Users\\test\\AppData\\Local") / "musher" / category
                    assert result == expected, f"Failed for {category}"
        finally:
            for k, v in backups.items():
                if v is not None:
                    os.environ[k] = v

    def test_windows_fallback_without_localappdata(self):
        env_backup_home = os.environ.pop("MUSHER_HOME", None)
        env_backup_cache = os.environ.pop("MUSHER_CACHE_HOME", None)
        env_backup_lad = os.environ.pop("LOCALAPPDATA", None)
        try:
            with patch("musher._paths.sys") as mock_sys:
                mock_sys.platform = "win32"
                result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
                assert result.name == "cache"
                assert result.parent.name == "musher"
                assert "AppData" in str(result) or "Local" in str(result)
        finally:
            if env_backup_home is not None:
                os.environ["MUSHER_HOME"] = env_backup_home
            if env_backup_cache is not None:
                os.environ["MUSHER_CACHE_HOME"] = env_backup_cache
            if env_backup_lad is not None:
                os.environ["LOCALAPPDATA"] = env_backup_lad

    def test_windows_branded_var_still_wins(self, tmp_path: Path):
        with (
            patch("musher._paths.sys") as mock_sys,
            patch.dict(
                os.environ,
                {
                    "MUSHER_CACHE_HOME": str(tmp_path),
                    "LOCALAPPDATA": "C:\\Users\\test\\AppData\\Local",
                },
                clear=False,
            ),
        ):
            mock_sys.platform = "win32"
            result = _resolve_root("MUSHER_CACHE_HOME", "cache", _dummy_platform_fn)
            assert result == tmp_path


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
