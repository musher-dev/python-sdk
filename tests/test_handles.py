"""Tests for _handles module — typed resource handles."""

import base64
import io
import json
import zipfile

import pytest

from musher._handles import (
    AgentSpecHandle,
    BundleSelection,
    FileHandle,
    PromptHandle,
    SkillHandle,
    ToolsetHandle,
)


class TestFileHandle:
    def test_text_decodes_utf8(self):
        fh = FileHandle(logical_path="hello.txt", _content=b"Hello world")
        assert fh.text() == "Hello world"

    def test_bytes_returns_raw(self):
        fh = FileHandle(logical_path="data.bin", _content=b"\x00\x01\x02")
        assert fh.bytes() == b"\x00\x01\x02"

    def test_custom_encoding(self):
        content = "Héllo".encode("latin-1")
        fh = FileHandle(logical_path="latin.txt", _content=content)
        assert fh.text(encoding="latin-1") == "Héllo"

    def test_media_type(self):
        fh = FileHandle(logical_path="img.png", _content=b"PNG", media_type="image/png")
        assert fh.media_type == "image/png"

    def test_media_type_none_by_default(self):
        fh = FileHandle(logical_path="f.txt", _content=b"x")
        assert fh.media_type is None


class TestSkillHandle:
    def _make_skill(self) -> SkillHandle:
        files = {
            "SKILL.md": FileHandle(logical_path="skills/search/SKILL.md", _content=b"# Search"),
            "handler.py": FileHandle(
                logical_path="skills/search/handler.py", _content=b"def run(): ..."
            ),
        }
        return SkillHandle(
            name="search",
            description="Search skill",
            root_path="skills/search",
            _files=files,
        )

    def test_file_lookup(self):
        skill = self._make_skill()
        fh = skill.file("handler.py")
        assert fh is not None
        assert fh.text() == "def run(): ..."

    def test_file_not_found(self):
        skill = self._make_skill()
        assert skill.file("nonexistent.py") is None

    def test_files_returns_all(self):
        skill = self._make_skill()
        assert len(skill.files()) == 2

    def test_skill_md(self):
        skill = self._make_skill()
        assert skill.skill_md().text() == "# Search"

    def test_export_openai_local_skill(self, tmp_path):
        skill = self._make_skill()
        result = skill.export_openai_local_skill(dest=tmp_path)
        assert result.name == "search"
        assert result.description == "Search skill"
        assert result.path == tmp_path / "search"
        assert (result.path / "SKILL.md").read_text() == "# Search"
        assert (result.path / "handler.py").read_text() == "def run(): ..."
        assert result.to_dict() == {
            "name": "search",
            "description": "Search skill",
            "path": str(tmp_path / "search"),
        }

    def test_export_openai_local_skill_default_dest(self):
        skill = self._make_skill()
        result = skill.export_openai_local_skill()
        assert result.path.name == "search"
        assert (result.path / "SKILL.md").read_text() == "# Search"

    def test_export_openai_inline_skill(self):
        skill = self._make_skill()
        result = skill.export_openai_inline_skill()
        assert result.name == "search"
        assert result.description == "Search skill"
        # Verify the base64 content is a valid zip with expected entries
        zip_bytes = base64.b64decode(result.content_base64)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = set(zf.namelist())
            assert "search/SKILL.md" in names
            assert "search/handler.py" in names
            assert zf.read("search/SKILL.md") == b"# Search"
        # Verify to_dict structure
        d = result.to_dict()
        assert d["type"] == "inline"
        assert d["name"] == "search"
        assert d["source"]["type"] == "base64"
        assert d["source"]["media_type"] == "application/zip"
        assert d["source"]["data"] == result.content_base64

    def test_export_path(self, tmp_path):
        skill = self._make_skill()
        result = skill.export_path(dest=tmp_path)
        assert result == tmp_path / "search"
        assert (tmp_path / "search" / "SKILL.md").read_text() == "# Search"
        assert (tmp_path / "search" / "handler.py").read_text() == "def run(): ..."

    def test_export_path_default_dest(self):
        skill = self._make_skill()
        result = skill.export_path()
        assert result.name == "search"
        assert (result / "SKILL.md").read_text() == "# Search"
        assert (result / "handler.py").read_text() == "def run(): ..."

    def test_export_zip(self, tmp_path):
        skill = self._make_skill()
        result = skill.export_zip(dest=tmp_path)
        assert result == tmp_path / "search.zip"
        assert result.is_file()
        with zipfile.ZipFile(result) as zf:
            names = set(zf.namelist())
            assert "search/SKILL.md" in names
            assert "search/handler.py" in names
            assert zf.read("search/SKILL.md") == b"# Search"

    def test_export_zip_default_dest(self):
        skill = self._make_skill()
        result = skill.export_zip()
        assert result.name == "search.zip"
        assert result.is_file()


class TestPromptHandle:
    def test_text_delegates(self):
        fh = FileHandle(logical_path="prompts/main.txt", _content=b"Be helpful.")
        ph = PromptHandle(name="main", file=fh)
        assert ph.text() == "Be helpful."


class TestToolsetHandle:
    def test_text(self):
        fh = FileHandle(logical_path="tools.json", _content=b'{"tools": []}')
        th = ToolsetHandle(name="tools", file=fh)
        assert th.text() == '{"tools": []}'

    def test_parse_json(self):
        fh = FileHandle(logical_path="tools.json", _content=b'{"tools": ["a", "b"]}')
        th = ToolsetHandle(name="tools", file=fh)
        parsed = th.parse_json()
        assert parsed == {"tools": ["a", "b"]}


class TestAgentSpecHandle:
    def test_text(self):
        fh = FileHandle(logical_path="spec.json", _content=b'{"name": "agent"}')
        ah = AgentSpecHandle(name="spec", file=fh)
        assert ah.text() == '{"name": "agent"}'

    def test_parse_json(self):
        fh = FileHandle(logical_path="spec.json", _content=b'{"name": "agent", "v": 1}')
        ah = AgentSpecHandle(name="spec", file=fh)
        parsed = ah.parse_json()
        assert parsed == {"name": "agent", "v": 1}


class TestBundleSelection:
    def _make_selection(self) -> BundleSelection:
        fh1 = FileHandle(logical_path="skills/search/SKILL.md", _content=b"# Search")
        fh2 = FileHandle(logical_path="prompts/main.txt", _content=b"Hello")
        skill = SkillHandle(
            name="search", description="Search", root_path="skills/search", _files={"SKILL.md": fh1}
        )
        prompt = PromptHandle(name="main", file=fh2)
        return BundleSelection(
            _skills={"search": skill},
            _prompts={"main": prompt},
            _files={fh1.logical_path: fh1, fh2.logical_path: fh2},
        )

    def test_skill_accessor(self):
        sel = self._make_selection()
        assert sel.skill("search").name == "search"
        assert len(sel.skills()) == 1

    def test_skill_not_found(self):
        sel = self._make_selection()
        with pytest.raises(KeyError):
            sel.skill("nonexistent")

    def test_prompt_accessor(self):
        sel = self._make_selection()
        assert sel.prompt("main").name == "main"
        assert len(sel.prompts()) == 1

    def test_file_accessor(self):
        sel = self._make_selection()
        assert sel.file("prompts/main.txt") is not None
        assert sel.file("nonexistent") is None
        assert len(sel.files()) == 2

    def test_empty_toolsets_and_agent_specs(self):
        sel = self._make_selection()
        assert sel.toolsets() == []
        assert sel.agent_specs() == []

    def test_export_claude_plugin(self, tmp_path):
        sel = self._make_selection()
        result = sel.export_claude_plugin("my-plugin", dest=tmp_path)
        assert result.plugin_name == "my-plugin"
        assert result.path == tmp_path / "my-plugin"

        # Verify directory layout
        assert (tmp_path / "my-plugin" / ".claude-plugin" / "plugin.json").is_file()
        assert (tmp_path / "my-plugin" / "skills" / "search" / "SKILL.md").is_file()

        # Verify plugin manifest
        manifest = json.loads(
            (tmp_path / "my-plugin" / ".claude-plugin" / "plugin.json").read_text()
        )
        assert manifest["name"] == "my-plugin"
        assert manifest["version"] == "1.0.0"
        assert len(manifest["skills"]) == 1
        assert manifest["skills"][0]["name"] == "search"
        assert manifest["skills"][0]["path"] == "skills/search"

    def test_export_claude_plugin_empty_name_raises(self):
        sel = self._make_selection()
        with pytest.raises(ValueError, match="plugin_name must be a non-empty string"):
            sel.export_claude_plugin("")
