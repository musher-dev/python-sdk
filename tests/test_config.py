"""Tests for _config module — XDG paths, env vars, defaults."""

import os
from pathlib import Path
from unittest.mock import patch

import musher._config as config_mod
from musher._config import MusherConfig, _xdg_cache_home, get_config


class TestXDGPaths:
    def test_xdg_cache_home_default(self):
        with patch.dict(os.environ, {}, clear=False):
            env_backup = os.environ.pop("XDG_CACHE_HOME", None)
            try:
                assert _xdg_cache_home() == Path.home() / ".cache"
            finally:
                if env_backup is not None:
                    os.environ["XDG_CACHE_HOME"] = env_backup

    def test_xdg_cache_home_from_env(self, tmp_path: Path):
        with patch.dict(os.environ, {"XDG_CACHE_HOME": str(tmp_path)}):
            assert _xdg_cache_home() == tmp_path


class TestDefaults:
    def test_default_timeout_is_60(self):
        cfg = MusherConfig()
        assert cfg.timeout == 60.0

    def test_default_cache_dir_uses_xdg(self):
        cfg = MusherConfig()
        assert cfg.cache_dir.name == "musher"
        assert ".cache" in str(cfg.cache_dir)


class TestGetConfig:
    def test_auto_discovers_env_vars(self):
        # Reset global config
        config_mod._global_config = None
        try:
            with (
                patch.dict(
                    os.environ,
                    {"MUSHER_API_KEY": "env-key", "MUSHER_API_URL": "https://custom.api.dev"},
                ),
                patch("musher._auth.resolve_token", return_value="env-key"),
            ):
                cfg = get_config()
                assert cfg.token == "env-key"
                assert cfg.registry_url == "https://custom.api.dev"
        finally:
            config_mod._global_config = None

    def test_returns_cached_config(self):
        config_mod._global_config = None
        try:
            with patch("musher._auth.resolve_token", return_value=None):
                cfg1 = get_config()
                cfg2 = get_config()
                assert cfg1 is cfg2
        finally:
            config_mod._global_config = None
