"""Tests for _auth module — credential chain resolution."""

import os
from pathlib import Path
from unittest.mock import patch

from musher._auth import _try_file, _try_keyring, resolve_token


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


class TestFileFallback:
    def test_reads_file_with_correct_permissions(self, tmp_path: Path):
        key_file = tmp_path / "musher" / "api-key"
        key_file.parent.mkdir(parents=True)
        key_file.write_text("file-token\n")
        key_file.chmod(0o600)

        env_backup = os.environ.pop("MUSHER_API_KEY", None)
        try:
            with (
                patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}, clear=False),
                patch("musher._auth._try_keyring", return_value=None),
            ):
                assert resolve_token() == "file-token"
        finally:
            if env_backup is not None:
                os.environ["MUSHER_API_KEY"] = env_backup

    def test_rejects_file_with_group_permissions(self, tmp_path: Path):
        key_file = tmp_path / "musher" / "api-key"
        key_file.parent.mkdir(parents=True)
        key_file.write_text("file-token\n")
        key_file.chmod(0o640)

        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            assert _try_file() is None

    def test_missing_file_returns_none(self, tmp_path: Path):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(tmp_path)}):
            assert _try_file() is None
