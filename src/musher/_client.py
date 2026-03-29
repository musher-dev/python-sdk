"""Sync and async clients for the Musher API."""

from __future__ import annotations

import asyncio
import hashlib
import threading
from typing import TYPE_CHECKING, cast

from musher._bundle import (
    Asset,
    Bundle,
    ManifestAsset,
    ResolveResult,
    _SDKSchema,  # pyright: ignore[reportPrivateUsage]
)
from musher._cache import BundleCache
from musher._config import MusherConfig, get_config
from musher._errors import APIError, IntegrityError
from musher._http import HTTPTransport
from musher._types import AssetType, BundleRef

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from pathlib import Path
    from types import TracebackType

    from musher._cache_info import CacheInfo


class _AssetResponse(_SDKSchema):
    """API response model for a single asset (camelCase wire format)."""

    id: str
    logical_path: str
    asset_type: str
    content_text: str
    content_sha256: str
    content_size_bytes: int | None = None
    media_type: str | None = None


class AsyncClient:
    """Async client for pulling bundles from the Musher registry.

    Usage::

        async with musher.AsyncClient() as client:
            bundle = await client.pull("myorg/my-bundle:1.0.0")
    """

    def __init__(self, config: MusherConfig | None = None) -> None:
        self._config: MusherConfig = config or get_config()
        self._http: HTTPTransport = HTTPTransport(self._config)
        self._cache: BundleCache = BundleCache(
            self._config.cache_dir, registry_url=self._config.registry_url
        )

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
        response_data: dict[str, object] = response.json()  # pyright: ignore[reportAny]
        result = ResolveResult.model_validate(response_data)

        # Cache the manifest with metadata
        if result.version:
            self._cache.put_manifest(
                parsed.namespace,
                parsed.slug,
                result.version,
                response_data,
                oci_digest=result.oci_digest,
            )
            # Cache ref mapping for unversioned refs (but not digest lookups)
            if not parsed.version and not parsed.digest:
                self._cache.put_ref(parsed.namespace, parsed.slug, "latest", result.version)

        return result

    async def fetch_asset(
        self,
        logical_path: str,
        *,
        namespace: str,
        slug: str,
        version: str | None = None,
    ) -> Asset:
        """Fetch a single asset by logical path.

        Hits ``GET /v1/namespaces/{ns}/bundles/{slug}/assets/{path}``.
        """
        import urllib.parse  # noqa: PLC0415

        encoded_path = urllib.parse.quote(logical_path, safe="")
        params: dict[str, str] = {}
        if version:
            params["version"] = version

        response = await self._http.get(
            f"/v1/namespaces/{namespace}/bundles/{slug}/assets/{encoded_path}",
            params=params or None,
        )
        data = _AssetResponse.model_validate(response.json())
        content = data.content_text.encode()

        return Asset(
            asset_id=data.id,
            logical_path=data.logical_path,
            asset_type=AssetType(data.asset_type),
            content=content,
            content_sha256=data.content_sha256,
            size_bytes=data.content_size_bytes or len(content),
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

        # Build a lookup of manifest layers by logical_path for checksum verification
        layer_map: dict[str, ManifestAsset] = {
            layer.logical_path: layer for layer in result.manifest.layers
        }

        # Check if all blobs are cached
        all_cached = True
        assets: dict[str, Asset] = {}
        for layer in result.manifest.layers:
            cached_blob = self._cache.get_blob(layer.content_sha256)
            if cached_blob is not None:
                assets[layer.logical_path] = Asset(
                    asset_id=layer.asset_id,
                    logical_path=layer.logical_path,
                    asset_type=AssetType(layer.asset_type),
                    content=cached_blob,
                    content_sha256=layer.content_sha256,
                    size_bytes=layer.size_bytes,
                    media_type=layer.media_type,
                )
            else:
                all_cached = False

        if all_cached:
            return Bundle(
                ref=result.ref,
                version=result.version,
                resolve_result=result,
                _assets=assets,
            )

        # Fetch all assets via the :pull endpoint
        pull_data = await self._pull_version(result.namespace, result.slug, result.version)
        pull_manifest = cast("list[dict[str, object]]", pull_data.get("manifest", []))
        assets = self._build_assets_from_pull(pull_manifest, layer_map)

        return Bundle(
            ref=result.ref,
            version=result.version,
            resolve_result=result,
            _assets=assets,
        )

    def _build_assets_from_pull(
        self,
        pull_manifest: list[dict[str, object]],
        layer_map: dict[str, ManifestAsset],
    ) -> dict[str, Asset]:
        """Build Asset dict from a :pull response, verifying checksums against resolve manifest."""
        assets: dict[str, Asset] = {}
        for item in pull_manifest:
            logical_path = str(item["logicalPath"])
            content = str(item.get("contentText", "")).encode()
            layer = layer_map.get(logical_path)

            # Verify checksum against the resolve manifest
            if layer and self._config.verify_checksums:
                actual_sha = hashlib.sha256(content).hexdigest()
                if actual_sha != layer.content_sha256:
                    raise IntegrityError(expected=layer.content_sha256, actual=actual_sha)

            content_sha256 = layer.content_sha256 if layer else hashlib.sha256(content).hexdigest()
            self._cache.put_blob(content_sha256, content)

            media_type = str(item.get("mediaType") or "") or (layer.media_type if layer else None)
            assets[logical_path] = Asset(
                asset_id=layer.asset_id if layer else logical_path,
                logical_path=logical_path,
                asset_type=AssetType(str(item["assetType"])),
                content=content,
                content_sha256=content_sha256,
                size_bytes=layer.size_bytes if layer else len(content),
                media_type=media_type or None,
            )
        return assets

    async def _pull_version(self, namespace: str, slug: str, version: str) -> dict[str, object]:
        """Fetch all assets for a version via the :pull endpoint.

        Tries the namespaced endpoint first, falls back to the hub endpoint
        for public bundles in other namespaces.
        """
        try:
            response = await self._http.get(
                f"/v1/namespaces/{namespace}/bundles/{slug}/versions/{version}:pull",
            )
            return response.json()  # pyright: ignore[reportAny]
        except APIError as exc:
            if exc.status != 403:  # noqa: PLR2004
                raise
        # Fall back to the hub endpoint for public bundles
        response = await self._http.get(
            f"/v1/hub/bundles/{namespace}/{slug}/versions/{version}:pull",
        )
        return response.json()  # pyright: ignore[reportAny]


class Client:
    """Synchronous client wrapping :class:`AsyncClient`.

    Uses a dedicated background thread with its own event loop so it works
    in Jupyter notebooks and other contexts where an event loop is already running.
    """

    def __init__(self, config: MusherConfig | None = None) -> None:
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._thread: threading.Thread = threading.Thread(
            target=self._loop.run_forever, daemon=True
        )
        self._thread.start()
        self._async_client: AsyncClient = AsyncClient(config=config)

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def _run[T](self, coro: Coroutine[object, object, T]) -> T:
        """Submit a coroutine to the background loop and block for the result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def close(self) -> None:
        """Release any held resources."""
        self._run(self._async_client.close())
        _ = self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)

    def pull(self, ref: str) -> Bundle:
        """Resolve, fetch, and verify a bundle (sync)."""
        return self._run(self._async_client.pull(ref))

    def resolve(self, ref: str) -> ResolveResult:
        """Resolve a bundle reference (sync)."""
        return self._run(self._async_client.resolve(ref))

    def fetch_asset(
        self,
        logical_path: str,
        *,
        namespace: str,
        slug: str,
        version: str | None = None,
    ) -> Asset:
        """Fetch a single asset by logical path (sync)."""
        return self._run(
            self._async_client.fetch_asset(
                logical_path, namespace=namespace, slug=slug, version=version
            )
        )

    # ── Cache management ──────────────────────────────────────────

    @property
    def _cache(self) -> BundleCache:
        return self._async_client._cache  # pyright: ignore[reportPrivateUsage]

    def cache_info(self) -> CacheInfo:
        """Return information about the local bundle cache."""
        return self._cache.scan()

    def cache_remove(self, ref: str) -> None:
        """Remove a specific bundle from the cache.

        Args:
            ref: Bundle reference (e.g. ``"myorg/my-bundle:1.0.0"`` or ``"myorg/my-bundle"``).
        """
        parsed = BundleRef.parse(ref)
        self._cache.purge(parsed.namespace, parsed.slug, parsed.version)

    def cache_clear(self) -> None:
        """Remove all cached data."""
        self._cache.clear()

    def cache_clean(self) -> int:
        """Remove expired entries and garbage-collect orphaned blobs.

        Returns the number of entries removed.
        """
        return self._cache.clean()

    def cache_path(self) -> Path:
        """Return the cache directory path."""
        return self._cache.cache_dir
