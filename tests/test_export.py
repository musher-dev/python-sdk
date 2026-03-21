"""Tests for _export module — export result types."""

from pathlib import Path

from musher._export import ClaudePluginExport, OpenAIInlineSkill, OpenAILocalSkill


class TestClaudePluginExport:
    def test_construction(self):
        export = ClaudePluginExport(path=Path("/tmp/my-plugin"))
        assert export.path == Path("/tmp/my-plugin")


class TestOpenAILocalSkill:
    def test_construction(self):
        skill = OpenAILocalSkill(
            name="search",
            description="Web search",
            path=Path("/tmp/skills/search"),
        )
        assert skill.name == "search"
        assert skill.description == "Web search"
        assert skill.path == Path("/tmp/skills/search")

    def test_to_dict(self):
        skill = OpenAILocalSkill(
            name="search",
            description="Web search",
            path=Path("/tmp/skills/search"),
        )
        d = skill.to_dict()
        assert d == {
            "name": "search",
            "description": "Web search",
            "path": "/tmp/skills/search",
        }


class TestOpenAIInlineSkill:
    def test_construction(self):
        skill = OpenAIInlineSkill(
            name="calc",
            description="Calculator",
            content_base64="dGVzdA==",
        )
        assert skill.name == "calc"
        assert skill.description == "Calculator"
        assert skill.content_base64 == "dGVzdA=="

    def test_to_dict(self):
        skill = OpenAIInlineSkill(
            name="calc",
            description="Calculator",
            content_base64="dGVzdA==",
        )
        d = skill.to_dict()
        assert d == {
            "type": "inline",
            "name": "calc",
            "description": "Calculator",
            "source": {
                "type": "base64",
                "media_type": "application/zip",
                "data": "dGVzdA==",
            },
        }
