"""Tests for _client module — instantiation, context manager protocol."""

import pytest

from musher import AsyncClient, Client
from musher._config import MusherConfig


class TestAsyncClient:
    async def test_instantiation_default_config(self):
        client = AsyncClient()
        assert client._config is not None

    async def test_instantiation_custom_config(self):
        config = MusherConfig(token="test")
        client = AsyncClient(config=config)
        assert client._config.token == "test"

    async def test_context_manager(self):
        async with AsyncClient() as client:
            assert isinstance(client, AsyncClient)

    async def test_pull_raises_not_implemented(self):
        async with AsyncClient() as client:
            with pytest.raises(NotImplementedError):
                await client.pull("myorg/bundle:1.0.0")

    async def test_resolve_raises_not_implemented(self):
        async with AsyncClient() as client:
            with pytest.raises(NotImplementedError):
                await client.resolve("myorg/bundle:1.0.0")

    async def test_fetch_asset_raises_not_implemented(self):
        async with AsyncClient() as client:
            with pytest.raises(NotImplementedError):
                await client.fetch_asset("asset-id")


class TestClient:
    def test_instantiation(self):
        client = Client()
        assert client._async_client is not None

    def test_context_manager(self):
        with Client() as client:
            assert isinstance(client, Client)

    def test_pull_raises_not_implemented(self):
        with Client() as client, pytest.raises(NotImplementedError):
            client.pull("myorg/bundle:1.0.0")
