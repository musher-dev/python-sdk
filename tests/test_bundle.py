"""Tests for _bundle module — Pydantic model deserialization, Asset/Bundle construction."""

from pathlib import Path

import pytest

from musher import Asset, Bundle, Manifest, ManifestAsset, ResolveResult
from musher._types import AssetType, BundleVersionState


def _make_resolve() -> ResolveResult:
    return ResolveResult.model_validate(
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


def _make_bundle_with_typed_assets() -> Bundle:
    """Create a bundle with assets of various types for handle testing."""
    assets: dict[str, Asset] = {}

    # Skill assets (a skill folder with SKILL.md)
    assets["skills/search/SKILL.md"] = Asset(
        asset_id="s1",
        logical_path="skills/search/SKILL.md",
        asset_type=AssetType.SKILL,
        content=b"# Search\nA web search skill.",
        content_sha256="aaa",
        size_bytes=27,
        media_type="text/markdown",
    )
    assets["skills/search/handler.py"] = Asset(
        asset_id="s2",
        logical_path="skills/search/handler.py",
        asset_type=AssetType.SKILL,
        content=b"def search(): ...",
        content_sha256="bbb",
        size_bytes=17,
    )

    # Another skill
    assets["skills/calc/SKILL.md"] = Asset(
        asset_id="s3",
        logical_path="skills/calc/SKILL.md",
        asset_type=AssetType.SKILL,
        content=b"# Calculator\nA math skill.",
        content_sha256="ccc",
        size_bytes=25,
        media_type="text/markdown",
    )

    # Prompt asset
    assets["prompts/main.txt"] = Asset(
        asset_id="p1",
        logical_path="prompts/main.txt",
        asset_type=AssetType.PROMPT,
        content=b"You are a helpful assistant.",
        content_sha256="ddd",
        size_bytes=28,
        media_type="text/plain",
    )

    # Toolset asset
    assets["toolsets/web.json"] = Asset(
        asset_id="t1",
        logical_path="toolsets/web.json",
        asset_type=AssetType.TOOLSET,
        content=b'{"tools": ["fetch", "scrape"]}',
        content_sha256="eee",
        size_bytes=29,
        media_type="application/json",
    )

    # Agent spec asset
    assets["specs/agent.json"] = Asset(
        asset_id="as1",
        logical_path="specs/agent.json",
        asset_type=AssetType.AGENT_SPEC,
        content=b'{"name": "my-agent", "version": "1.0"}',
        content_sha256="fff",
        size_bytes=37,
        media_type="application/json",
    )

    return Bundle(
        ref="org/bundle",
        version="1.0.0",
        resolve_result=_make_resolve(),
        _assets=assets,
    )


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
    def test_file_lookup(self):
        asset = Asset(
            asset_id="a1",
            logical_path="prompts/main.txt",
            asset_type=AssetType.PROMPT,
            content=b"Hello",
            content_sha256="abc",
            size_bytes=5,
        )
        bundle = Bundle(
            ref="org/bundle",
            version="1.0.0",
            resolve_result=_make_resolve(),
            _assets={"prompts/main.txt": asset},
        )
        fh = bundle.file("prompts/main.txt")
        assert fh is not None
        assert fh.text() == "Hello"
        assert bundle.file("nonexistent") is None
        assert len(bundle.files()) == 1

    def test_verify_raises_not_implemented(self):
        bundle = Bundle(ref="org/bundle", version="1.0.0", resolve_result=_make_resolve())
        with pytest.raises(NotImplementedError):
            bundle.verify()

    def test_skills(self):
        bundle = _make_bundle_with_typed_assets()
        skills = bundle.skills()
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert names == {"search", "calc"}

    def test_skill_lookup(self):
        bundle = _make_bundle_with_typed_assets()
        search = bundle.skill("search")
        assert search.name == "search"
        assert search.description == "Search"
        assert len(search.files()) == 2
        assert search.skill_md().text().startswith("# Search")

    def test_skill_not_found(self):
        bundle = _make_bundle_with_typed_assets()
        with pytest.raises(KeyError):
            bundle.skill("nonexistent")

    def test_prompts(self):
        bundle = _make_bundle_with_typed_assets()
        prompts = bundle.prompts()
        assert len(prompts) == 1
        assert prompts[0].name == "main"
        assert prompts[0].text() == "You are a helpful assistant."

    def test_prompt_lookup(self):
        bundle = _make_bundle_with_typed_assets()
        p = bundle.prompt("main")
        assert p.name == "main"

    def test_prompt_not_found(self):
        bundle = _make_bundle_with_typed_assets()
        with pytest.raises(KeyError):
            bundle.prompt("nonexistent")

    def test_toolsets(self):
        bundle = _make_bundle_with_typed_assets()
        toolsets = bundle.toolsets()
        assert len(toolsets) == 1
        assert toolsets[0].name == "web"
        parsed = toolsets[0].parse_json()
        assert parsed["tools"] == ["fetch", "scrape"]

    def test_toolset_lookup(self):
        bundle = _make_bundle_with_typed_assets()
        t = bundle.toolset("web")
        assert t.name == "web"

    def test_toolset_not_found(self):
        bundle = _make_bundle_with_typed_assets()
        with pytest.raises(KeyError):
            bundle.toolset("nonexistent")

    def test_agent_specs(self):
        bundle = _make_bundle_with_typed_assets()
        specs = bundle.agent_specs()
        assert len(specs) == 1
        assert specs[0].name == "agent"
        parsed = specs[0].parse_json()
        assert parsed["name"] == "my-agent"

    def test_agent_spec_lookup(self):
        bundle = _make_bundle_with_typed_assets()
        a = bundle.agent_spec("agent")
        assert a.name == "agent"

    def test_agent_spec_not_found(self):
        bundle = _make_bundle_with_typed_assets()
        with pytest.raises(KeyError):
            bundle.agent_spec("nonexistent")

    def test_select_skills_subset(self):
        bundle = _make_bundle_with_typed_assets()
        sel = bundle.select(skills=["search"])
        assert len(sel.skills()) == 1
        assert sel.skills()[0].name == "search"
        # Prompts/toolsets/agent_specs included by default when not filtered
        assert len(sel.prompts()) == 1
        assert len(sel.toolsets()) == 1
        assert len(sel.agent_specs()) == 1

    def test_select_prompts_subset(self):
        bundle = _make_bundle_with_typed_assets()
        sel = bundle.select(prompts=["main"], skills=[])
        assert len(sel.prompts()) == 1
        assert len(sel.skills()) == 0

    def test_select_empty(self):
        bundle = _make_bundle_with_typed_assets()
        sel = bundle.select(skills=[], prompts=[], toolsets=[], agent_specs=[])
        assert len(sel.skills()) == 0
        assert len(sel.prompts()) == 0
        assert len(sel.toolsets()) == 0
        assert len(sel.agent_specs()) == 0
        assert len(sel.files()) == 0

    def test_export_claude_plugin_raises_not_implemented(self):
        bundle = _make_bundle_with_typed_assets()
        with pytest.raises(NotImplementedError):
            bundle.export_claude_plugin("test-plugin")

    def test_install_vscode_skills_raises_not_implemented(self):
        bundle = _make_bundle_with_typed_assets()
        with pytest.raises(NotImplementedError):
            bundle.install_vscode_skills(Path("/tmp/skills"))

    def test_install_claude_skills_raises_not_implemented(self):
        bundle = _make_bundle_with_typed_assets()
        with pytest.raises(NotImplementedError):
            bundle.install_claude_skills(Path("/tmp/skills"))

    def test_write_lockfile_raises_not_implemented(self):
        bundle = _make_bundle_with_typed_assets()
        with pytest.raises(NotImplementedError):
            bundle.write_lockfile()
