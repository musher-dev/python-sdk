"""Sync and async clients for the Musher API."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from musher._config import MusherConfig, get_config

if TYPE_CHECKING:
    from types import TracebackType

    from musher._bundle import Asset, Bundle, ResolveResult


class AsyncClient:
    """Async client for pulling bundles from the Musher registry.

    Usage::

        async with musher.AsyncClient() as client:
            bundle = await client.pull("myorg/my-bundle:1.0.0")
    """

    def __init__(self, config: MusherConfig | None = None) -> None:
        self._config = config or get_config()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Release any held resources."""

    async def pull(self, ref: str) -> Bundle:
        """Resolve a bundle reference, fetch all assets, and verify checksums.

        Args:
            ref: Bundle reference (e.g. ``"myorg/my-bundle:1.0.0"``).

        Returns:
            A :class:`Bundle` with all assets loaded.
        """
        raise NotImplementedError

    async def resolve(self, ref: str) -> ResolveResult:
        """Resolve a bundle reference to its manifest without fetching assets.

        Hits ``POST /api/v1/bundles:resolve``.
        """
        raise NotImplementedError

    async def fetch_asset(self, asset_id: str) -> Asset:
        """Fetch a single asset by ID.

        Hits ``GET /api/v1/runner/assets/{id}``.
        """
        raise NotImplementedError


class Client:
    """Synchronous client wrapping :class:`AsyncClient`."""

    def __init__(self, config: MusherConfig | None = None) -> None:
        self._async_client = AsyncClient(config=config)

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release any held resources."""

    def pull(self, ref: str) -> Bundle:
        """Resolve, fetch, and verify a bundle (sync)."""
        return asyncio.run(self._async_client.pull(ref))

    def resolve(self, ref: str) -> ResolveResult:
        """Resolve a bundle reference (sync)."""
        return asyncio.run(self._async_client.resolve(ref))

    def fetch_asset(self, asset_id: str) -> Asset:
        """Fetch a single asset by ID (sync)."""
        return asyncio.run(self._async_client.fetch_asset(asset_id))
