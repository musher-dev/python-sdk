"""Typed resource handles for bundle assets."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from musher._export import ClaudePluginExport, OpenAIInlineSkill, OpenAILocalSkill


@dataclass(frozen=True, slots=True)
class FileHandle:
    """Typed handle to a single file within a bundle."""

    logical_path: str
    _content: bytes
    media_type: str | None = None

    def text(self, encoding: str = "utf-8") -> str:
        """Decode file content as text."""
        return self._content.decode(encoding)

    def bytes(self) -> bytes:
        """Return raw file content."""
        return self._content


@dataclass(frozen=True, slots=True)
class SkillHandle:
    """Typed handle to a skill (folder rooted by SKILL.md) within a bundle."""

    name: str
    description: str
    root_path: str
    _files: dict[str, FileHandle] = field(repr=False)

    def file(self, relative_path: str) -> FileHandle | None:
        """Look up a file within this skill by relative path."""
        return self._files.get(relative_path)

    def files(self) -> list[FileHandle]:
        """Return all files belonging to this skill."""
        return list(self._files.values())

    def skill_md(self) -> FileHandle:
        """Return the SKILL.md file for this skill."""
        return self._files["SKILL.md"]

    def export_openai_local_skill(self, dest: Path | None = None) -> OpenAILocalSkill:
        """Export this skill for OpenAI local-path consumption."""
        raise NotImplementedError

    def export_openai_inline_skill(self) -> OpenAIInlineSkill:
        """Export this skill as an inline base64 zip for OpenAI."""
        raise NotImplementedError

    def export_path(self, dest: Path | None = None) -> Path:
        """Write skill files to a directory and return the path."""
        raise NotImplementedError

    def export_zip(self, dest: Path | None = None) -> Path:
        """Write skill files to a zip archive and return the path."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class PromptHandle:
    """Typed handle to a prompt asset."""

    name: str
    file: FileHandle

    def text(self) -> str:
        """Return prompt text content."""
        return self.file.text()


@dataclass(frozen=True, slots=True)
class ToolsetHandle:
    """Typed handle to a toolset asset."""

    name: str
    file: FileHandle

    def text(self) -> str:
        """Return toolset text content."""
        return self.file.text()

    def parse_json(self) -> dict:  # type: ignore[type-arg]
        """Parse toolset content as JSON."""
        return json.loads(self.file.bytes())


@dataclass(frozen=True, slots=True)
class AgentSpecHandle:
    """Typed handle to an agent spec asset."""

    name: str
    file: FileHandle

    def text(self) -> str:
        """Return agent spec text content."""
        return self.file.text()

    def parse_json(self) -> dict:  # type: ignore[type-arg]
        """Parse agent spec content as JSON."""
        return json.loads(self.file.bytes())


@dataclass
class BundleSelection:
    """A filtered subset of bundle resources returned by Bundle.select()."""

    _skills: dict[str, SkillHandle] = field(default_factory=dict, repr=False)
    _prompts: dict[str, PromptHandle] = field(default_factory=dict, repr=False)
    _toolsets: dict[str, ToolsetHandle] = field(default_factory=dict, repr=False)
    _agent_specs: dict[str, AgentSpecHandle] = field(default_factory=dict, repr=False)
    _files: dict[str, FileHandle] = field(default_factory=dict, repr=False)

    def skill(self, name: str) -> SkillHandle:
        """Get a skill by name. Raises KeyError if not found."""
        return self._skills[name]

    def skills(self) -> list[SkillHandle]:
        """Return all skills in the selection."""
        return list(self._skills.values())

    def prompt(self, name: str) -> PromptHandle:
        """Get a prompt by name. Raises KeyError if not found."""
        return self._prompts[name]

    def prompts(self) -> list[PromptHandle]:
        """Return all prompts in the selection."""
        return list(self._prompts.values())

    def toolset(self, name: str) -> ToolsetHandle:
        """Get a toolset by name. Raises KeyError if not found."""
        return self._toolsets[name]

    def toolsets(self) -> list[ToolsetHandle]:
        """Return all toolsets in the selection."""
        return list(self._toolsets.values())

    def agent_spec(self, name: str) -> AgentSpecHandle:
        """Get an agent spec by name. Raises KeyError if not found."""
        return self._agent_specs[name]

    def agent_specs(self) -> list[AgentSpecHandle]:
        """Return all agent specs in the selection."""
        return list(self._agent_specs.values())

    def file(self, logical_path: str) -> FileHandle | None:
        """Get a file by logical path."""
        return self._files.get(logical_path)

    def files(self) -> list[FileHandle]:
        """Return all files in the selection."""
        return list(self._files.values())

    def export_claude_plugin(
        self,
        plugin_name: str = "",
        dest: Path | None = None,
    ) -> ClaudePluginExport:
        """Export selected resources as a Claude plugin."""
        raise NotImplementedError
