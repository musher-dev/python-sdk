"""Sync and async clients for the Musher API."""

from __future__ import annotations

import asyncio
import hashlib
import threading
from typing import TYPE_CHECKING

from musher._bundle import Asset, Bundle, ManifestAsset, ResolveResult, _SDKSchema
from musher._cache import BundleCache
from musher._config import MusherConfig, get_config
from musher._errors import IntegrityError
from musher._http import HTTPTransport
from musher._types import AssetType, BundleRef

if TYPE_CHECKING:
    from types import TracebackType


class _AssetResponse(_SDKSchema):
    """API response model for a single asset (camelCase wire format)."""

    asset_id: str
    logical_path: str
    asset_type: str
    content: str
    content_sha256: str
    size_bytes: int
    media_type: str | None = None


class AsyncClient:
    """Async client for pulling bundles from the Musher registry.

    Usage::

        async with musher.AsyncClient() as client:
            bundle = await client.pull("myorg/my-bundle:1.0.0")
    """

    def __init__(self, config: MusherConfig | None = None) -> None:
        self._config = config or get_config()
        self._http = HTTPTransport(self._config)
        self._cache = BundleCache(self._config.cache_dir, registry_url=self._config.registry_url)

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
        await self._http.close()

    async def resolve(self, ref: str) -> ResolveResult:
        """Resolve a bundle reference to its manifest without fetching assets.

        Hits ``GET /v1/namespaces/{ns}/bundles/{slug}:resolve``.
        """
        parsed = BundleRef.parse(ref)

        # For unversioned refs, check ref cache first
        if not parsed.version and not parsed.digest:
            cached_version = self._cache.get_ref(parsed.namespace, parsed.slug, "latest")
            if cached_version:
                cached = self._cache.get_manifest(parsed.namespace, parsed.slug, cached_version)
                if cached is not None and self._cache.is_manifest_fresh(
                    parsed.namespace, parsed.slug, cached_version
                ):
                    return ResolveResult.model_validate(cached)

        # Check manifest cache for versioned refs
        if parsed.version:
            cached = self._cache.get_manifest(parsed.namespace, parsed.slug, parsed.version)
            if cached is not None and self._cache.is_manifest_fresh(
                parsed.namespace, parsed.slug, parsed.version
            ):
                return ResolveResult.model_validate(cached)

        params: dict[str, str] = {}
        if parsed.version:
            params["version"] = parsed.version
        if parsed.digest:
            params["digest"] = parsed.digest

        response = await self._http.get(
            f"/v1/namespaces/{parsed.namespace}/bundles/{parsed.slug}:resolve",
            params=params or None,
        )
        result = ResolveResult.model_validate(response.json())

        # Cache the manifest with metadata
        if result.version:
            self._cache.put_manifest(
                parsed.namespace,
                parsed.slug,
                result.version,
                response.json(),
                oci_digest=result.oci_digest,
            )
            # Cache ref mapping for unversioned refs (but not digest lookups)
            if not parsed.version and not parsed.digest:
                self._cache.put_ref(parsed.namespace, parsed.slug, "latest", result.version)

        return result

    async def fetch_asset(self, asset_id: str, *, version: str | None = None) -> Asset:
        """Fetch a single asset by ID.

        Hits ``GET /v1/runner/assets/{id}``.
        """
        params: dict[str, str] = {}
        if version:
            params["version"] = version

        response = await self._http.get(
            f"/v1/runner/assets/{asset_id}",
            params=params or None,
        )
        data = _AssetResponse.model_validate(response.json())
        content = data.content.encode()

        return Asset(
            asset_id=data.asset_id,
            logical_path=data.logical_path,
            asset_type=AssetType(data.asset_type),
            content=content,
            content_sha256=data.content_sha256,
            size_bytes=data.size_bytes,
            media_type=data.media_type,
        )

    async def pull(self, ref: str) -> Bundle:
        """Resolve a bundle reference, fetch all assets, and verify checksums.

        Args:
            ref: Bundle reference (e.g. ``"myorg/my-bundle:1.0.0"``).

        Returns:
            A :class:`Bundle` with all assets loaded.
        """
        result = await self.resolve(ref)

        if not result.manifest or not result.manifest.layers:
            return Bundle(
                ref=result.ref,
                version=result.version,
                resolve_result=result,
            )

        # Determine which assets need fetching vs cache hits
        semaphore = asyncio.Semaphore(10)
        assets: dict[str, Asset] = {}

        async def _fetch_layer(layer: ManifestAsset) -> None:
            # Check blob cache first
            cached_blob = self._cache.get_blob(layer.content_sha256)
            if cached_blob is not None:
                assets[layer.asset_id] = Asset(
                    asset_id=layer.asset_id,
                    logical_path=layer.logical_path,
                    asset_type=AssetType(layer.asset_type),
                    content=cached_blob,
                    content_sha256=layer.content_sha256,
                    size_bytes=layer.size_bytes,
                    media_type=layer.media_type,
                )
                return

            async with semaphore:
                asset = await self.fetch_asset(layer.asset_id, version=result.version)

            # Verify checksum
            if self._config.verify_checksums:
                actual_sha = hashlib.sha256(asset.content).hexdigest()
                if actual_sha != layer.content_sha256:
                    raise IntegrityError(expected=layer.content_sha256, actual=actual_sha)

            # Cache the blob
            self._cache.put_blob(layer.content_sha256, asset.content)

            assets[layer.asset_id] = asset

        await asyncio.gather(*[_fetch_layer(layer) for layer in result.manifest.layers])

        return Bundle(
            ref=result.ref,
            version=result.version,
            resolve_result=result,
            _assets=assets,
        )


class Client:
    """Synchronous client wrapping :class:`AsyncClient`.

    Uses a dedicated background thread with its own event loop so it works
    in Jupyter notebooks and other contexts where an event loop is already running.
    """

    def __init__(self, config: MusherConfig | None = None) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
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

    def _run(self, coro: object) -> object:
        """Submit a coroutine to the background loop and block for the result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)  # type: ignore[arg-type]
        return future.result()

    def close(self) -> None:
        """Release any held resources."""
        self._run(self._async_client.close())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    def pull(self, ref: str) -> Bundle:
        """Resolve, fetch, and verify a bundle (sync)."""
        return self._run(self._async_client.pull(ref))  # type: ignore[return-value]

    def resolve(self, ref: str) -> ResolveResult:
        """Resolve a bundle reference (sync)."""
        return self._run(self._async_client.resolve(ref))  # type: ignore[return-value]

    def fetch_asset(self, asset_id: str, *, version: str | None = None) -> Asset:
        """Fetch a single asset by ID (sync)."""
        return self._run(self._async_client.fetch_asset(asset_id, version=version))  # type: ignore[return-value]
