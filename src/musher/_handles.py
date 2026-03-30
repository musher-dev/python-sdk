"""Typed resource handles for bundle assets."""

from __future__ import annotations

import base64
import io
import json
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import cast

from musher._export import ClaudePluginExport, OpenAIInlineSkill, OpenAILocalSkill


def _validate_relative_path(relative_path: str) -> None:
    """Reject paths that could escape the target directory."""
    p = PurePosixPath(relative_path)
    if p.is_absolute() or ".." in p.parts:
        msg = f"Unsafe relative path in skill: {relative_path}"
        raise ValueError(msg)


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
        exported_path = self.export_path(dest)
        return OpenAILocalSkill(
            name=self.name,
            description=self.description,
            path=exported_path,
        )

    def export_openai_inline_skill(self) -> OpenAIInlineSkill:
        """Export this skill as an inline base64 zip for OpenAI."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for relative_path, fh in self._files.items():
                _validate_relative_path(relative_path)
                zf.writestr(f"{self.name}/{relative_path}", fh.bytes())
        content_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return OpenAIInlineSkill(
            name=self.name,
            description=self.description,
            content_base64=content_b64,
        )

    def export_path(self, dest: Path | None = None) -> Path:
        """Write skill files to a directory and return the path."""
        if dest is None:
            dest = Path(tempfile.mkdtemp(prefix="musher-"))

        skill_dir = dest / self.name
        for relative_path, fh in self._files.items():
            _validate_relative_path(relative_path)
            out = skill_dir / relative_path
            out.parent.mkdir(parents=True, exist_ok=True)
            _ = out.write_bytes(fh.bytes())
        return skill_dir

    def export_zip(self, dest: Path | None = None) -> Path:
        """Write skill files to a zip archive and return the path."""
        if dest is None:
            dest = Path(tempfile.mkdtemp(prefix="musher-"))

        dest.mkdir(parents=True, exist_ok=True)
        zip_path = dest / f"{self.name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for relative_path, fh in self._files.items():
                _validate_relative_path(relative_path)
                zf.writestr(f"{self.name}/{relative_path}", fh.bytes())
        return zip_path


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

    def parse_json(self) -> dict[str, object]:
        """Parse toolset content as JSON."""
        return cast("dict[str, object]", json.loads(self.file.bytes()))


@dataclass(frozen=True, slots=True)
class AgentSpecHandle:
    """Typed handle to an agent spec asset."""

    name: str
    file: FileHandle

    def text(self) -> str:
        """Return agent spec text content."""
        return self.file.text()

    def parse_json(self) -> dict[str, object]:
        """Parse agent spec content as JSON."""
        return cast("dict[str, object]", json.loads(self.file.bytes()))


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
        plugin_name: str,
        dest: Path | None = None,
    ) -> ClaudePluginExport:
        """Export selected resources as a Claude plugin."""
        if not plugin_name:
            msg = "plugin_name must be a non-empty string"
            raise ValueError(msg)

        if dest is None:
            dest = Path(tempfile.mkdtemp(prefix="musher-plugin-"))

        plugin_root = dest / plugin_name
        plugin_meta_dir = plugin_root / ".claude-plugin"
        plugin_meta_dir.mkdir(parents=True, exist_ok=True)

        skills_manifest: list[dict[str, str]] = []
        for skill in self._skills.values():
            _ = skill.export_path(dest=plugin_root / "skills")
            skills_manifest.append({
                "name": skill.name,
                "description": skill.description,
                "path": f"skills/{skill.name}",
            })

        manifest = {
            "name": plugin_name,
            "version": "1.0.0",
            "skills": skills_manifest,
        }
        _ = (plugin_meta_dir / "plugin.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        return ClaudePluginExport(plugin_name=plugin_name, path=plugin_root)
