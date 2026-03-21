"""Tests for _auth module — credential chain resolution."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from musher._auth import (
    _try_file,
    _try_keyring,
    resolve_registry_url,
    resolve_token,
)


class TestEnvVar:
    def test_env_var_takes_priority(self):
        with patch.dict(os.environ, {"MUSHER_API_KEY": "env-token"}):
            assert resolve_token() == "env-token"

    def test_empty_env_var_falls_through(self):
        with (
            patch.dict(os.environ, {"MUSHER_API_KEY": ""}, clear=False),
            patch("musher._auth._try_keyring", return_value=None),
            patch("musher._auth._try_file", return_value=None),
        ):
            # Empty string is falsy, should fall through to None
            assert resolve_token() is None


class TestKeyring:
    def test_keyring_used_when_no_env(self):
        env_backup = os.environ.pop("MUSHER_API_KEY", None)
        try:
            with patch("musher._auth._try_keyring", return_value="keyring-token"):
                assert resolve_token() == "keyring-token"
        finally:
            if env_backup is not None:
                os.environ["MUSHER_API_KEY"] = env_backup

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

    def test_keyring_includes_port(self):
        """Keyring service name includes port when present in URL."""
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "kr-token"
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            result = _try_keyring(registry_url="https://localhost:8080")
            mock_keyring.get_password.assert_called_once_with("musher/localhost:8080", "api-key")
            assert result == "kr-token"


def _write_host_scoped_key(
    data_dir: Path,
    token: str,
    host: str = "api.musher.dev",
    mode: int = 0o600,
) -> Path:
    """Helper to create a host-scoped credential file."""
    key_file = data_dir / "credentials" / host / "api-key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(f"{token}\n")
    key_file.chmod(mode)
    return key_file


class TestFileFallback:
    def test_reads_file_with_correct_permissions(self, tmp_path: Path):
        config = tmp_path / "musher"
        _write_host_scoped_key(config, "file-token")

        env_backup = os.environ.pop("MUSHER_API_KEY", None)
        try:
            with patch("musher._auth._try_keyring", return_value=None):
                assert resolve_token(data_dir=config) == "file-token"
        finally:
            if env_backup is not None:
                os.environ["MUSHER_API_KEY"] = env_backup

    def test_rejects_file_with_group_permissions(self, tmp_path: Path):
        config = tmp_path / "musher"
        _write_host_scoped_key(config, "file-token", mode=0o640)

        assert _try_file(data_dir=config) is None

    def test_missing_file_returns_none(self, tmp_path: Path):
        assert _try_file(data_dir=tmp_path / "musher") is None

    def test_try_file_with_custom_data_dir(self, tmp_path: Path):
        """_try_file uses data_dir param instead of default."""
        config = tmp_path / "custom-config"
        _write_host_scoped_key(config, "custom-token")

        assert _try_file(data_dir=config) == "custom-token"

    def test_reads_host_scoped_credential_file(self, tmp_path: Path):
        """Host-scoped credential file is found."""
        config = tmp_path / "musher"
        _write_host_scoped_key(config, "host-token", host="custom.registry.dev")

        assert (
            _try_file(registry_url="https://custom.registry.dev", data_dir=config) == "host-token"
        )

    def test_host_scoped_with_port(self, tmp_path: Path):
        """Host-scoped file uses underscore-separated port."""
        config = tmp_path / "musher"
        _write_host_scoped_key(config, "port-token", host="localhost_8080")

        assert _try_file(registry_url="https://localhost:8080", data_dir=config) == "port-token"


class TestResolveRegistryUrl:
    def test_musher_api_url(self):
        with patch.dict(os.environ, {"MUSHER_API_URL": "https://custom.dev/"}, clear=False):
            assert resolve_registry_url() == "https://custom.dev"

    def test_default_url(self):
        env_vars = ["MUSHER_API_URL"]
        backups = {k: os.environ.pop(k, None) for k in env_vars}
        try:
            assert resolve_registry_url() == "https://api.musher.dev"
        finally:
            for k, v in backups.items():
                if v is not None:
                    os.environ[k] = v
