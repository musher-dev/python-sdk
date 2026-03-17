"""Tests for _types module — BundleRef parsing, enum values."""

import pytest

from musher import (
    AssetType,
    BundleRef,
    BundleSourceType,
    BundleVersionState,
    BundleVisibility,
)


class TestAssetType:
    def test_values_match_platform(self):
        assert set(AssetType) == {
            "agent_definition",
            "skill",
            "tool_config",
            "prompt",
            "config",
            "other",
        }


class TestBundleVisibility:
    def test_values(self):
        assert set(BundleVisibility) == {"private", "public"}


class TestBundleVersionState:
    def test_values(self):
        assert set(BundleVersionState) == {"published", "yanked"}


class TestBundleSourceType:
    def test_values(self):
        assert set(BundleSourceType) == {"console", "registry"}


class TestBundleRef:
    def test_parse_namespace_slug(self):
        ref = BundleRef.parse("myorg/my-bundle")
        assert ref.namespace == "myorg"
        assert ref.slug == "my-bundle"
        assert ref.version is None
        assert ref.digest is None

    def test_parse_with_version(self):
        ref = BundleRef.parse("myorg/my-bundle:1.0.0")
        assert ref.namespace == "myorg"
        assert ref.slug == "my-bundle"
        assert ref.version == "1.0.0"
        assert ref.digest is None

    def test_parse_with_digest(self):
        ref = BundleRef.parse("myorg/my-bundle@sha256:abc123")
        assert ref.namespace == "myorg"
        assert ref.slug == "my-bundle"
        assert ref.version is None
        assert ref.digest == "sha256:abc123"

    def test_parse_invalid_no_slash(self):
        with pytest.raises(ValueError, match="Invalid bundle reference"):
            BundleRef.parse("invalid")

    def test_parse_invalid_empty_namespace(self):
        with pytest.raises(ValueError, match="Invalid bundle reference"):
            BundleRef.parse("/slug")

    def test_parse_invalid_empty_slug(self):
        with pytest.raises(ValueError, match="Invalid bundle reference"):
            BundleRef.parse("namespace/")

    def test_str_namespace_slug(self):
        ref = BundleRef(namespace="myorg", slug="bundle")
        assert str(ref) == "myorg/bundle"

    def test_str_with_version(self):
        ref = BundleRef(namespace="myorg", slug="bundle", version="1.0.0")
        assert str(ref) == "myorg/bundle:1.0.0"

    def test_str_with_digest(self):
        ref = BundleRef(namespace="myorg", slug="bundle", digest="sha256:abc")
        assert str(ref) == "myorg/bundle@sha256:abc"

    def test_frozen(self):
        ref = BundleRef.parse("myorg/bundle")
        with pytest.raises(AttributeError):
            ref.namespace = "other"  # type: ignore[misc]
