"""Tests for _auth module — credential chain resolution."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from musher._auth import (
    _try_file,
    _try_keyring,
    _try_profile,
    resolve_registry_url,
    resolve_token,
)


class TestEnvVar:
    def test_env_var_takes_priority(self):
        with patch.dict(os.environ, {"MUSHER_API_KEY": "env-token"}):
            assert resolve_token() == "env-token"

    def test_mush_api_key_alias(self):
        env_backup = os.environ.pop("MUSHER_API_KEY", None)
        try:
            with patch.dict(os.environ, {"MUSH_API_KEY": "mush-token"}, clear=False):
                assert resolve_token() == "mush-token"
        finally:
            if env_backup is not None:
                os.environ["MUSHER_API_KEY"] = env_backup

    def test_musher_api_key_takes_precedence_over_mush(self):
        with patch.dict(
            os.environ,
            {"MUSHER_API_KEY": "musher-token", "MUSH_API_KEY": "mush-token"},
        ):
            assert resolve_token() == "musher-token"

    def test_empty_env_var_falls_through(self):
        with (
            patch.dict(os.environ, {"MUSHER_API_KEY": ""}, clear=False),
            patch("musher._auth._try_keyring", return_value=None),
            patch("musher._auth._try_profile", return_value=None),
            patch("musher._auth._try_file", return_value=None),
        ):
            # Empty string is falsy, should fall through to None
            assert resolve_token() is None


class TestKeyring:
    def test_keyring_used_when_no_env(self):
        env_backup = os.environ.pop("MUSHER_API_KEY", None)
        env_backup2 = os.environ.pop("MUSH_API_KEY", None)
        try:
            with patch("musher._auth._try_keyring", return_value="keyring-token"):
                assert resolve_token() == "keyring-token"
        finally:
            if env_backup is not None:
                os.environ["MUSHER_API_KEY"] = env_backup
            if env_backup2 is not None:
                os.environ["MUSH_API_KEY"] = env_backup2

    def test_keyring_import_failure_returns_none(self):
        # If keyring is not installed, should return None gracefully
        with patch.dict("sys.modules", {"keyring": None}):
            assert _try_keyring() is None

    def test_keyring_host_scoped_service_name(self):
        """Keyring service name is derived from registry URL hostname."""
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "kr-token"
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            result = _try_keyring(registry_url="https://custom.registry.dev")
            mock_keyring.get_password.assert_called_once_with(
                "musher/custom.registry.dev", "api-key"
            )
            assert result == "kr-token"

    def test_keyring_default_host(self):
        """Keyring uses default host when no registry URL given."""
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = None
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            _try_keyring()
            mock_keyring.get_password.assert_called_once_with("musher/api.musher.dev", "api-key")


class TestProfileConfig:
    def test_reads_api_key_from_profile(self, tmp_path: Path):
        config = tmp_path / "musher"
        config.mkdir()
        (config / "config.toml").write_text('[profile.default]\napi_key = "profile-token"\n')
        with patch("musher._auth.config_dir", return_value=config):
            assert _try_profile() == "profile-token"

    def test_reads_named_profile(self, tmp_path: Path):
        config = tmp_path / "musher"
        config.mkdir()
        (config / "config.toml").write_text('[profile.staging]\napi_key = "staging-token"\n')
        with patch("musher._auth.config_dir", return_value=config):
            assert _try_profile(profile="staging") == "staging-token"

    def test_missing_config_file_returns_none(self, tmp_path: Path):
        with patch("musher._auth.config_dir", return_value=tmp_path / "musher"):
            assert _try_profile() is None

    def test_missing_profile_returns_none(self, tmp_path: Path):
        config = tmp_path / "musher"
        config.mkdir()
        (config / "config.toml").write_text('[profile.other]\napi_key = "other-token"\n')
        with patch("musher._auth.config_dir", return_value=config):
            assert _try_profile() is None


class TestFileFallback:
    def test_reads_file_with_correct_permissions(self, tmp_path: Path):
        key_file = tmp_path / "musher" / "api-key"
        key_file.parent.mkdir(parents=True)
        key_file.write_text("file-token\n")
        key_file.chmod(0o600)

        env_backup = os.environ.pop("MUSHER_API_KEY", None)
        env_backup2 = os.environ.pop("MUSH_API_KEY", None)
        try:
            with (
                patch("musher._paths.config_dir", return_value=tmp_path / "musher"),
                patch("musher._auth.config_dir", return_value=tmp_path / "musher"),
                patch("musher._auth._try_keyring", return_value=None),
                patch("musher._auth._try_profile", return_value=None),
            ):
                assert resolve_token() == "file-token"
        finally:
            if env_backup is not None:
                os.environ["MUSHER_API_KEY"] = env_backup
            if env_backup2 is not None:
                os.environ["MUSH_API_KEY"] = env_backup2

    def test_rejects_file_with_group_permissions(self, tmp_path: Path):
        key_file = tmp_path / "musher" / "api-key"
        key_file.parent.mkdir(parents=True)
        key_file.write_text("file-token\n")
        key_file.chmod(0o640)

        with patch("musher._auth.config_dir", return_value=tmp_path / "musher"):
            assert _try_file() is None

    def test_missing_file_returns_none(self, tmp_path: Path):
        with patch("musher._auth.config_dir", return_value=tmp_path / "musher"):
            assert _try_file() is None


class TestResolveRegistryUrl:
    def test_musher_api_url(self):
        with patch.dict(os.environ, {"MUSHER_API_URL": "https://custom.dev/"}, clear=False):
            assert resolve_registry_url() == "https://custom.dev"

    def test_mush_api_url(self):
        env_backup = os.environ.pop("MUSHER_API_URL", None)
        try:
            with patch.dict(os.environ, {"MUSH_API_URL": "https://mush.dev"}, clear=False):
                assert resolve_registry_url() == "https://mush.dev"
        finally:
            if env_backup is not None:
                os.environ["MUSHER_API_URL"] = env_backup

    def test_musher_base_url(self):
        env_backup1 = os.environ.pop("MUSHER_API_URL", None)
        env_backup2 = os.environ.pop("MUSH_API_URL", None)
        try:
            with patch.dict(os.environ, {"MUSHER_BASE_URL": "https://base.dev/"}, clear=False):
                assert resolve_registry_url() == "https://base.dev"
        finally:
            if env_backup1 is not None:
                os.environ["MUSHER_API_URL"] = env_backup1
            if env_backup2 is not None:
                os.environ["MUSH_API_URL"] = env_backup2

    def test_mush_base_url(self):
        env_backup1 = os.environ.pop("MUSHER_API_URL", None)
        env_backup2 = os.environ.pop("MUSH_API_URL", None)
        env_backup3 = os.environ.pop("MUSHER_BASE_URL", None)
        try:
            with patch.dict(os.environ, {"MUSH_BASE_URL": "https://mushbase.dev"}, clear=False):
                assert resolve_registry_url() == "https://mushbase.dev"
        finally:
            if env_backup1 is not None:
                os.environ["MUSHER_API_URL"] = env_backup1
            if env_backup2 is not None:
                os.environ["MUSH_API_URL"] = env_backup2
            if env_backup3 is not None:
                os.environ["MUSHER_BASE_URL"] = env_backup3

    def test_default_url(self):
        env_vars = ["MUSHER_API_URL", "MUSH_API_URL", "MUSHER_BASE_URL", "MUSH_BASE_URL"]
        backups = {k: os.environ.pop(k, None) for k in env_vars}
        try:
            assert resolve_registry_url() == "https://api.musher.dev"
        finally:
            for k, v in backups.items():
                if v is not None:
                    os.environ[k] = v

    def test_precedence_musher_api_url_over_mush(self):
        with patch.dict(
            os.environ,
            {"MUSHER_API_URL": "https://first.dev", "MUSH_API_URL": "https://second.dev"},
        ):
            assert resolve_registry_url() == "https://first.dev"
