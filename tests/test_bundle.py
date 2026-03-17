"""Tests for _bundle module — Pydantic model deserialization, Asset/Bundle construction."""

import pytest

from musher import Asset, Bundle, Manifest, ManifestAsset, ResolveResult
from musher._types import AssetType, BundleVersionState


class TestManifestAsset:
    def test_from_camel_case(self):
        asset = ManifestAsset.model_validate(
            {
                "assetId": "abc-123",
                "logicalPath": "prompts/main.txt",
                "assetType": "prompt",
                "contentSha256": "deadbeef",
                "sizeBytes": 1024,
                "mediaType": "text/plain",
            }
        )
        assert asset.asset_id == "abc-123"
        assert asset.logical_path == "prompts/main.txt"
        assert asset.asset_type == "prompt"
        assert asset.content_sha256 == "deadbeef"
        assert asset.size_bytes == 1024
        assert asset.media_type == "text/plain"

    def test_from_snake_case(self):
        asset = ManifestAsset.model_validate(
            {
                "asset_id": "abc",
                "logical_path": "config.yaml",
                "asset_type": "config",
                "content_sha256": "aabb",
                "size_bytes": 100,
            }
        )
        assert asset.asset_id == "abc"
        assert asset.media_type is None


class TestManifest:
    def test_layers(self):
        manifest = Manifest.model_validate(
            {
                "layers": [
                    {
                        "assetId": "a1",
                        "logicalPath": "p.txt",
                        "assetType": "prompt",
                        "contentSha256": "xx",
                        "sizeBytes": 10,
                    }
                ]
            }
        )
        assert len(manifest.layers) == 1
        assert manifest.layers[0].asset_id == "a1"


class TestResolveResult:
    def test_from_api_response(self):
        result = ResolveResult.model_validate(
            {
                "bundleId": "uuid-1",
                "versionId": "uuid-2",
                "namespace": "myorg",
                "slug": "my-bundle",
                "ref": "myorg/my-bundle",
                "version": "1.0.0",
                "state": "published",
                "manifest": {
                    "layers": [
                        {
                            "assetId": "a1",
                            "logicalPath": "main.txt",
                            "assetType": "prompt",
                            "contentSha256": "abc",
                            "sizeBytes": 100,
                        }
                    ]
                },
            }
        )
        assert result.bundle_id == "uuid-1"
        assert result.version == "1.0.0"
        assert result.state == BundleVersionState.PUBLISHED
        assert result.manifest is not None
        assert len(result.manifest.layers) == 1


class TestAsset:
    def test_construction(self):
        asset = Asset(
            asset_id="a1",
            logical_path="prompts/main.txt",
            asset_type=AssetType.PROMPT,
            content=b"Hello world",
            content_sha256="abc123",
            size_bytes=11,
        )
        assert asset.asset_id == "a1"
        assert asset.content == b"Hello world"


class TestBundle:
    def test_asset_lookup(self):
        asset = Asset(
            asset_id="a1",
            logical_path="prompts/main.txt",
            asset_type=AssetType.PROMPT,
            content=b"Hello",
            content_sha256="abc",
            size_bytes=5,
        )
        resolve = ResolveResult.model_validate(
            {
                "bundleId": "b1",
                "versionId": "v1",
                "namespace": "org",
                "slug": "bundle",
                "ref": "org/bundle",
                "version": "1.0.0",
                "state": "published",
            }
        )
        bundle = Bundle(
            ref="org/bundle",
            version="1.0.0",
            resolve_result=resolve,
            _assets={"prompts/main.txt": asset},
        )
        assert bundle.asset("prompts/main.txt") is asset
        assert bundle.asset("nonexistent") is None
        assert len(bundle.assets()) == 1
        assert bundle.assets_by_type(AssetType.PROMPT) == [asset]
        assert bundle.assets_by_type(AssetType.CONFIG) == []

    def test_verify_raises_not_implemented(self):
        resolve = ResolveResult.model_validate(
            {
                "bundleId": "b1",
                "versionId": "v1",
                "namespace": "org",
                "slug": "bundle",
                "ref": "org/bundle",
                "version": "1.0.0",
                "state": "published",
            }
        )
        bundle = Bundle(ref="org/bundle", version="1.0.0", resolve_result=resolve)
        with pytest.raises(NotImplementedError):
            bundle.verify()
