"""Export result types for framework-specific materialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ClaudePluginExport:
    """Result of exporting a bundle selection as a Claude plugin."""

    path: Path


@dataclass(frozen=True, slots=True)
class OpenAILocalSkill:
    """Result of exporting a skill for OpenAI local-path consumption."""

    name: str
    description: str
    path: Path

    def to_dict(self) -> dict[str, str]:
        """Serialize to a dict suitable for OpenAI tool registration."""
        return {
            "name": self.name,
            "description": self.description,
            "path": str(self.path),
        }


@dataclass(frozen=True, slots=True)
class OpenAIInlineSkill:
    """Result of exporting a skill as an inline base64 zip for OpenAI."""

    name: str
    description: str
    content_base64: str

    def to_dict(self) -> dict[str, object]:
        """Serialize to a dict matching OpenAI's inline skill format."""
        return {
            "type": "inline",
            "name": self.name,
            "description": self.description,
            "source": {
                "type": "base64",
                "media_type": "application/zip",
                "data": self.content_base64,
            },
        }
