"""Tests for _client module — resolve, fetch_asset, pull, context managers."""

import hashlib
import json
from pathlib import Path

import httpx
import pytest
import respx

from musher import AsyncClient, Client
from musher._bundle import Asset, Bundle, ResolveResult
from musher._config import MusherConfig
from musher._errors import IntegrityError

_BASE = "https://api.test.dev"

_RESOLVE_RESPONSE = {
    "bundleId": "bundle-123",
    "versionId": "version-456",
    "namespace": "myorg",
    "slug": "my-bundle",
    "ref": "myorg/my-bundle",
    "version": "1.0.0",
    "state": "published",
    "manifest": {
        "layers": [
            {
                "assetId": "asset-1",
                "logicalPath": "skills/greet/SKILL.md",
                "assetType": "skill",
                "contentSha256": hashlib.sha256(b"Hello skill").hexdigest(),
                "sizeBytes": 11,
                "mediaType": "text/markdown",
            }
        ]
    },
}

_ASSET_RESPONSE = {
    "id": "asset-1",
    "logicalPath": "skills/greet/SKILL.md",
    "assetType": "skill",
    "contentText": "Hello skill",
    "contentSha256": hashlib.sha256(b"Hello skill").hexdigest(),
    "contentSizeBytes": 11,
    "mediaType": "text/markdown",
}

_PULL_RESPONSE = {
    "namespace": "myorg",
    "slug": "my-bundle",
    "version": "1.0.0",
    "name": "My Bundle",
    "manifest": [
        {
            "logicalPath": "skills/greet/SKILL.md",
            "assetType": "skill",
            "contentText": "Hello skill",
            "mediaType": "text/markdown",
        }
    ],
}


@pytest.fixture
def config(tmp_path: Path) -> MusherConfig:
    return MusherConfig(token="test-token", registry_url=_BASE, cache_dir=tmp_path / "cache")


class TestAsyncClient:
    async def test_instantiation_default_config(self):
        client = AsyncClient()
        assert client._config is not None
        await client.close()

    async def test_instantiation_custom_config(self, config: MusherConfig):
        client = AsyncClient(config=config)
        assert client._config.token == "test-token"
        await client.close()

    async def test_context_manager(self, config: MusherConfig):
        async with AsyncClient(config=config) as client:
            assert isinstance(client, AsyncClient)

    @respx.mock
    async def test_resolve(self, config: MusherConfig):
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        async with AsyncClient(config=config) as client:
            result = await client.resolve("myorg/my-bundle:1.0.0")
        assert isinstance(result, ResolveResult)
        assert result.bundle_id == "bundle-123"
        assert result.version == "1.0.0"
        assert result.manifest is not None
        assert len(result.manifest.layers) == 1

    @respx.mock
    async def test_resolve_passes_version_param(self, config: MusherConfig):
        route = respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        async with AsyncClient(config=config) as client:
            await client.resolve("myorg/my-bundle:1.0.0")
        assert route.calls[0].request.url.params["version"] == "1.0.0"

    @respx.mock
    async def test_fetch_asset(self, config: MusherConfig):
        respx.get(
            f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle/assets/skills%2Fgreet%2FSKILL.md"
        ).mock(return_value=httpx.Response(200, json=_ASSET_RESPONSE))
        async with AsyncClient(config=config) as client:
            asset = await client.fetch_asset(
                "skills/greet/SKILL.md", namespace="myorg", slug="my-bundle"
            )
        assert isinstance(asset, Asset)
        assert asset.asset_id == "asset-1"
        assert asset.content == b"Hello skill"

    @respx.mock
    async def test_pull(self, config: MusherConfig):
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle/versions/1.0.0:pull").mock(
            return_value=httpx.Response(200, json=_PULL_RESPONSE)
        )
        async with AsyncClient(config=config) as client:
            bundle = await client.pull("myorg/my-bundle:1.0.0")
        assert isinstance(bundle, Bundle)
        assert bundle.version == "1.0.0"
        files = bundle.files()
        assert len(files) == 1
        assert files[0].text() == "Hello skill"

    @respx.mock
    async def test_pull_empty_manifest(self, config: MusherConfig):
        empty_resolve = {**_RESOLVE_RESPONSE, "manifest": {"layers": []}}
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=empty_resolve)
        )
        async with AsyncClient(config=config) as client:
            bundle = await client.pull("myorg/my-bundle:1.0.0")
        assert bundle.files() == []

    @respx.mock
    async def test_pull_checksum_mismatch(self, config: MusherConfig):
        bad_pull = {
            **_PULL_RESPONSE,
            "manifest": [{**_PULL_RESPONSE["manifest"][0], "contentText": "WRONG CONTENT"}],
        }
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle/versions/1.0.0:pull").mock(
            return_value=httpx.Response(200, json=bad_pull)
        )
        async with AsyncClient(config=config) as client:
            with pytest.raises(IntegrityError):
                await client.pull("myorg/my-bundle:1.0.0")

    @respx.mock
    async def test_ref_caching_round_trip(self, config: MusherConfig):
        """Unversioned resolve caches the ref, second call uses cache."""
        route = respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        async with AsyncClient(config=config) as client:
            result1 = await client.resolve("myorg/my-bundle")
            assert result1.version == "1.0.0"
            # Second resolve should hit cache
            result2 = await client.resolve("myorg/my-bundle")
            assert result2.version == "1.0.0"
        # Only one HTTP call should have been made
        assert len(route.calls) == 1

    @respx.mock
    async def test_manifest_freshness_check(self, config: MusherConfig):
        """Versioned resolve caches manifest with freshness metadata."""
        route = respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        async with AsyncClient(config=config) as client:
            result1 = await client.resolve("myorg/my-bundle:1.0.0")
            assert result1.version == "1.0.0"
            # Second resolve should hit cache (manifest is fresh)
            result2 = await client.resolve("myorg/my-bundle:1.0.0")
            assert result2.version == "1.0.0"
        assert len(route.calls) == 1

    @respx.mock
    async def test_digest_ref_does_not_write_latest_alias(self, config: MusherConfig):
        """Resolving by digest should NOT create a 'latest' ref cache entry."""
        digest_response = {**_RESOLVE_RESPONSE, "ociDigest": "sha256:abc123"}
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=digest_response)
        )
        async with AsyncClient(config=config) as client:
            result = await client.resolve("myorg/my-bundle@sha256:abc123")
            assert result.version == "1.0.0"
            # Verify no "latest" ref was cached
            ref = client._cache.get_ref("myorg", "my-bundle", "latest")
            assert ref is None

    @respx.mock
    async def test_oci_digest_flows_to_meta(self, config: MusherConfig):
        """oci_digest from resolve result should be stored in .meta.json."""
        digest_response = {**_RESOLVE_RESPONSE, "ociDigest": "sha256:abc123"}
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=digest_response)
        )
        async with AsyncClient(config=config) as client:
            await client.resolve("myorg/my-bundle:1.0.0")
            # Check the meta sidecar has the oci digest
            meta_path = (
                config.cache_dir
                / "manifests"
                / client._cache.host_id
                / "myorg"
                / "my-bundle"
                / "1.0.0.meta.json"
            )
            assert meta_path.is_file()
            meta = json.loads(meta_path.read_text())
            assert meta["ociDigest"] == "sha256:abc123"

    @respx.mock
    async def test_pull_hub_fallback(self, config: MusherConfig):
        """When namespaced :pull returns 403, falls back to hub :pull."""
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        # Namespaced :pull returns 403 (not authorized for this namespace)
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle/versions/1.0.0:pull").mock(
            return_value=httpx.Response(
                403,
                json={
                    "type": "https://api.platform.musher.dev/errors/forbidden",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": "Not authorized",
                },
            )
        )
        # Hub :pull succeeds
        respx.get(f"{_BASE}/v1/hub/bundles/myorg/my-bundle/versions/1.0.0:pull").mock(
            return_value=httpx.Response(200, json=_PULL_RESPONSE)
        )
        async with AsyncClient(config=config) as client:
            bundle = await client.pull("myorg/my-bundle:1.0.0")
        assert isinstance(bundle, Bundle)
        assert bundle.version == "1.0.0"
        assert len(bundle.files()) == 1


class TestClient:
    def test_instantiation(self, config: MusherConfig):
        client = Client(config=config)
        assert client._async_client is not None
        client.close()

    def test_context_manager(self, config: MusherConfig):
        with Client(config=config) as client:
            assert isinstance(client, Client)

    @respx.mock
    def test_sync_pull(self, config: MusherConfig):
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle/versions/1.0.0:pull").mock(
            return_value=httpx.Response(200, json=_PULL_RESPONSE)
        )
        with Client(config=config) as client:
            bundle = client.pull("myorg/my-bundle:1.0.0")
        assert isinstance(bundle, Bundle)
        assert bundle.version == "1.0.0"

    @respx.mock
    def test_sync_resolve(self, config: MusherConfig):
        respx.get(f"{_BASE}/v1/namespaces/myorg/bundles/my-bundle:resolve").mock(
            return_value=httpx.Response(200, json=_RESOLVE_RESPONSE)
        )
        with Client(config=config) as client:
            result = client.resolve("myorg/my-bundle:1.0.0")
        assert result.bundle_id == "bundle-123"
