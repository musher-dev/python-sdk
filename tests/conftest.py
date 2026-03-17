"""Shared test fixtures."""

import pytest

from musher._config import MusherConfig


@pytest.fixture
def config() -> MusherConfig:
    return MusherConfig(token="test-token")
