"""Tests for _handles module — typed resource handles."""

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

    def test_export_stubs_raise(self):
        skill = self._make_skill()
        with pytest.raises(NotImplementedError):
            skill.export_openai_local_skill()
        with pytest.raises(NotImplementedError):
            skill.export_openai_inline_skill()
        with pytest.raises(NotImplementedError):
            skill.export_path()
        with pytest.raises(NotImplementedError):
            skill.export_zip()


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

    def test_export_stubs_raise(self):
        sel = self._make_selection()
        with pytest.raises(NotImplementedError):
            sel.export_claude_plugin("test")
