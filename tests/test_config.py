"""Tests for _config module — paths, env vars, defaults."""

import os
from pathlib import Path
from unittest.mock import patch

import musher._config as config_mod
from musher._config import MusherConfig, configure, get_config


class TestDefaults:
    def test_default_timeout_is_60(self):
        cfg = MusherConfig()
        assert cfg.timeout == 60.0

    def test_default_cache_dir_ends_with_musher(self):
        cfg = MusherConfig()
        assert cfg.cache_dir.name == "musher"

    def test_default_config_dir_ends_with_musher(self):
        cfg = MusherConfig()
        assert cfg.config_dir.name == "musher"

    def test_default_data_dir_ends_with_musher(self):
        cfg = MusherConfig()
        assert cfg.data_dir.name == "musher"

    def test_default_state_dir_ends_with_musher(self):
        cfg = MusherConfig()
        assert cfg.state_dir.name == "musher"


class TestConfigure:
    def test_configure_with_custom_dirs(self, tmp_path: Path):
        configure(
            cache_dir=tmp_path / "cache",
            config_dir=tmp_path / "config",
            data_dir=tmp_path / "data",
            state_dir=tmp_path / "state",
        )
        cfg = get_config()
        assert cfg.cache_dir == tmp_path / "cache"
        assert cfg.config_dir == tmp_path / "config"
        assert cfg.data_dir == tmp_path / "data"
        assert cfg.state_dir == tmp_path / "state"

    def test_configure_preserves_existing_fields(self):
        configure(token="my-token", registry_url="https://custom.dev")
        cfg = get_config()
        assert cfg.token == "my-token"
        assert cfg.registry_url == "https://custom.dev"


class TestGetConfig:
    def test_auto_discovers_env_vars(self):
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
