"""Shared test fixtures."""

import pytest

import musher._config as config_mod


@pytest.fixture(autouse=True)
def _reset_global_config():
    """Reset global config between tests to avoid leaking state."""
    config_mod._global_config = None
    yield
    config_mod._global_config = None
