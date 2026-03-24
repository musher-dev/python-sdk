"""Bundle, manifest, and asset models."""

from __future__ import annotations

import json as _json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, ClassVar, cast

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from musher._export import ClaudePluginExport

from musher._handles import (
    AgentSpecHandle,
    BundleSelection,
    FileHandle,
    PromptHandle,
    SkillHandle,
    ToolsetHandle,
)
from musher._types import AssetType, BundleSourceType, BundleVersionState


class _SDKSchema(BaseModel):
    """Base schema with camelCase aliasing, matching the platform API wire format."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
    )


class ManifestAsset(_SDKSchema):
    """A single layer entry in a bundle manifest (maps to BundleLayerOutput)."""

    asset_id: str
    logical_path: str
    asset_type: str
    content_sha256: str
    size_bytes: int
    media_type: str | None = None


class Manifest(_SDKSchema):
    """Bundle manifest listing all layers (maps to BundleManifestOutput)."""

    layers: list[ManifestAsset]


class ResolveResult(_SDKSchema):
    """Result of resolving a bundle reference (maps to BundleResolveOutput)."""

    bundle_id: str
    version_id: str
    namespace: str
    slug: str
    ref: str
    version: str
    source_type: BundleSourceType = BundleSourceType.CONSOLE
    oci_ref: str | None = None
    oci_digest: str | None = None
    state: BundleVersionState
    manifest: Manifest | None = None


@dataclass
class Asset:
    """A fetched asset with content bytes and metadata."""

    asset_id: str
    logical_path: str
    asset_type: AssetType
    content: bytes
    content_sha256: str
    size_bytes: int
    media_type: str | None = None


def _build_file_handles(assets: dict[str, Asset]) -> dict[str, FileHandle]:
    """Build FileHandle instances for every asset."""
    return {
        a.logical_path: FileHandle(
            logical_path=a.logical_path,
            _content=a.content,
            media_type=a.media_type,
        )
        for a in assets.values()
    }


def _build_skill_handles(
    assets: dict[str, Asset],
    file_handles: dict[str, FileHandle],
) -> dict[str, SkillHandle]:
    """Group SKILL assets by directory containing SKILL.md into SkillHandles."""
    skill_roots: dict[str, dict[str, FileHandle]] = {}

    for asset in assets.values():
        if asset.asset_type != AssetType.SKILL:
            continue
        path = PurePosixPath(asset.logical_path)
        if path.name == "SKILL.md":
            root = str(path.parent) if path.parent != PurePosixPath() else ""
            skill_roots.setdefault(root, {})[path.name] = file_handles[asset.logical_path]
        else:
            _place_skill_file(asset, path, assets, file_handles, skill_roots)

    result: dict[str, SkillHandle] = {}
    for root, root_files in skill_roots.items():
        skill_md = root_files.get("SKILL.md")
        name = PurePosixPath(root).name if root else "root"
        description = _extract_skill_description(skill_md) if skill_md else ""
        result[name] = SkillHandle(
            name=name,
            description=description,
            root_path=root,
            _files=root_files,
        )
    return result


def _place_skill_file(
    asset: Asset,
    path: PurePosixPath,
    assets: dict[str, Asset],
    file_handles: dict[str, FileHandle],
    skill_roots: dict[str, dict[str, FileHandle]],
) -> None:
    """Place a non-SKILL.md skill file into the correct skill root."""
    parts = list(path.parts)
    for i in range(len(parts) - 1, 0, -1):
        candidate_root = str(PurePosixPath(*parts[:i]))
        if f"{candidate_root}/SKILL.md" in assets:
            rel = str(PurePosixPath(*parts[i:]))
            skill_roots.setdefault(candidate_root, {})[rel] = file_handles[asset.logical_path]
            return
    # Top-level skill file without nested directory
    skill_roots.setdefault("", {})[asset.logical_path] = file_handles[asset.logical_path]


def _extract_skill_description(skill_md: FileHandle) -> str:
    """Extract description from the first non-empty line of SKILL.md."""
    for line in skill_md.text().splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped
    return ""


def _build_typed_handles(
    assets: dict[str, Asset],
    file_handles: dict[str, FileHandle],
    asset_type: AssetType,
) -> dict[str, FileHandle]:
    """Return a name→FileHandle mapping for assets of a given type."""
    return {
        PurePosixPath(a.logical_path).stem: file_handles[a.logical_path]
        for a in assets.values()
        if a.asset_type == asset_type
    }


@dataclass
class Bundle:
    """A resolved bundle with its assets."""

    ref: str
    version: str
    resolve_result: ResolveResult
    _assets: dict[str, Asset] = field(default_factory=dict, repr=False)

    # Lazily-built handle caches
    _file_handles: dict[str, FileHandle] | None = field(default=None, repr=False)
    _skill_handles: dict[str, SkillHandle] | None = field(default=None, repr=False)
    _prompt_handles: dict[str, PromptHandle] | None = field(default=None, repr=False)
    _toolset_handles: dict[str, ToolsetHandle] | None = field(default=None, repr=False)
    _agent_spec_handles: dict[str, AgentSpecHandle] | None = field(default=None, repr=False)

    # ── File access ──────────────────────────────────────────────

    def file(self, logical_path: str) -> FileHandle | None:
        """Get a single file by logical path."""
        self._build_handles()
        assert self._file_handles is not None  # noqa: S101
        return self._file_handles.get(logical_path)

    def files(self) -> list[FileHandle]:
        """Return all files in this bundle."""
        self._build_handles()
        assert self._file_handles is not None  # noqa: S101
        return list(self._file_handles.values())

    # ── Typed accessors ─────────────────────────────────────────────

    def skill(self, name: str) -> SkillHandle:
        """Get a skill by name. Raises KeyError if not found."""
        self._build_handles()
        assert self._skill_handles is not None  # noqa: S101
        return self._skill_handles[name]

    def skills(self) -> list[SkillHandle]:
        """Return all skills in this bundle."""
        self._build_handles()
        assert self._skill_handles is not None  # noqa: S101
        return list(self._skill_handles.values())

    def prompt(self, name: str) -> PromptHandle:
        """Get a prompt by name. Raises KeyError if not found."""
        self._build_handles()
        assert self._prompt_handles is not None  # noqa: S101
        return self._prompt_handles[name]

    def prompts(self) -> list[PromptHandle]:
        """Return all prompts in this bundle."""
        self._build_handles()
        assert self._prompt_handles is not None  # noqa: S101
        return list(self._prompt_handles.values())

    def toolset(self, name: str) -> ToolsetHandle:
        """Get a toolset by name. Raises KeyError if not found."""
        self._build_handles()
        assert self._toolset_handles is not None  # noqa: S101
        return self._toolset_handles[name]

    def toolsets(self) -> list[ToolsetHandle]:
        """Return all toolsets in this bundle."""
        self._build_handles()
        assert self._toolset_handles is not None  # noqa: S101
        return list(self._toolset_handles.values())

    def agent_spec(self, name: str) -> AgentSpecHandle:
        """Get an agent spec by name. Raises KeyError if not found."""
        self._build_handles()
        assert self._agent_spec_handles is not None  # noqa: S101
        return self._agent_spec_handles[name]

    def agent_specs(self) -> list[AgentSpecHandle]:
        """Return all agent specs in this bundle."""
        self._build_handles()
        assert self._agent_spec_handles is not None  # noqa: S101
        return list(self._agent_spec_handles.values())

    # ── Selection ───────────────────────────────────────────────────

    def select(
        self,
        *,
        skills: list[str] | None = None,
        prompts: list[str] | None = None,
        toolsets: list[str] | None = None,
        agent_specs: list[str] | None = None,
    ) -> BundleSelection:
        """Return a filtered subset of this bundle's resources."""
        self._build_handles()
        assert self._skill_handles is not None  # noqa: S101
        assert self._prompt_handles is not None  # noqa: S101
        assert self._toolset_handles is not None  # noqa: S101
        assert self._agent_spec_handles is not None  # noqa: S101

        sel_skills = _filter_map(self._skill_handles, skills)
        sel_prompts = _filter_map(self._prompt_handles, prompts)
        sel_toolsets = _filter_map(self._toolset_handles, toolsets)
        sel_agent_specs = _filter_map(self._agent_spec_handles, agent_specs)

        # Collect files belonging to selected resources
        sel_files: dict[str, FileHandle] = {}
        for sh in sel_skills.values():
            for fh in sh.files():
                sel_files[fh.logical_path] = fh
        for ph in sel_prompts.values():
            sel_files[ph.file.logical_path] = ph.file
        for th in sel_toolsets.values():
            sel_files[th.file.logical_path] = th.file
        for ah in sel_agent_specs.values():
            sel_files[ah.file.logical_path] = ah.file

        return BundleSelection(
            _skills=sel_skills,
            _prompts=sel_prompts,
            _toolsets=sel_toolsets,
            _agent_specs=sel_agent_specs,
            _files=sel_files,
        )

    # ── Export / install ───────────────────────────────────────────

    def export_claude_plugin(
        self,
        plugin_name: str,
        skills: list[str] | None = None,
        dest: Path | None = None,
    ) -> ClaudePluginExport:
        """Export bundle as a Claude plugin."""
        return self.select(skills=skills).export_claude_plugin(plugin_name, dest=dest)

    def install_claude_skills(
        self,
        dest: Path,
        skills: list[str] | None = None,
        *,
        clean: bool = False,
    ) -> None:
        """Install skills to a Claude skills directory."""
        selection = self.select(skills=skills)

        if clean and dest.is_dir():
            for child in dest.iterdir():
                marker = child / ".musher-managed"
                if child.is_dir() and marker.is_file():
                    try:
                        info = cast(
                            "dict[str, object]", _json.loads(marker.read_text(encoding="utf-8"))
                        )
                    except (OSError, _json.JSONDecodeError):
                        continue
                    if info.get("bundle_ref") == self.ref:
                        shutil.rmtree(child)

        dest.mkdir(parents=True, exist_ok=True)

        for skill in selection.skills():
            _ = skill.export_path(dest=dest)
            marker_data = {
                "bundle_ref": self.ref,
                "bundle_version": self.version,
                "installed_at": datetime.now(UTC).isoformat(),
            }
            _ = (dest / skill.name / ".musher-managed").write_text(
                _json.dumps(marker_data, indent=2) + "\n", encoding="utf-8"
            )

    # ── Internal ────────────────────────────────────────────────────

    def _build_handles(self) -> None:
        """Lazily build typed handle caches from raw assets."""
        if self._file_handles is not None:
            return

        file_handles = _build_file_handles(self._assets)
        skill_handles = _build_skill_handles(self._assets, file_handles)

        prompt_fhs = _build_typed_handles(self._assets, file_handles, AssetType.PROMPT)
        prompt_handles = {n: PromptHandle(name=n, file=fh) for n, fh in prompt_fhs.items()}

        toolset_fhs = _build_typed_handles(self._assets, file_handles, AssetType.TOOLSET)
        toolset_handles = {n: ToolsetHandle(name=n, file=fh) for n, fh in toolset_fhs.items()}

        agent_spec_fhs = _build_typed_handles(self._assets, file_handles, AssetType.AGENT_SPEC)
        agent_spec_handles = {
            n: AgentSpecHandle(name=n, file=fh) for n, fh in agent_spec_fhs.items()
        }

        self._file_handles = file_handles
        self._skill_handles = skill_handles
        self._prompt_handles = prompt_handles
        self._toolset_handles = toolset_handles
        self._agent_spec_handles = agent_spec_handles


def _filter_map[T](source: dict[str, T], names: list[str] | None) -> dict[str, T]:
    """Filter a dict by a list of names, or return a copy if names is None."""
    if names is None:
        return dict(source)
    return {n: source[n] for n in names if n in source}
