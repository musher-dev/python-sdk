"""Example: Select a subset of skills and export as a Claude plugin.

Demonstrates per-session skill narrowing — only expose the skills your agent
actually needs, reducing the skill surface area and avoiding tool overload.

Requires: pip install claude-agent-sdk
"""

import asyncio
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

import musher

# NOTE: Bundle references below (e.g. "acme/engineering-workflows:2.0.0") are
# placeholders. Replace with a real bundle ref from your Musher registry.

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/engineering-workflows:2.0.0")

# Select only the skills needed for this session
selection = bundle.select(skills=["researching-repos", "drafting-release-notes"])

# Export as a local Claude plugin with a namespaced plugin name.
# Skills will be accessible as "team-workflows:researching-repos", etc.
plugin = selection.export_claude_plugin("team-workflows", dest=Path("./plugins"))
print(f"Plugin exported to: {plugin.path}")

# Verify only the selected skills are present
for skill in selection.skills():
    print(f"  Skill: {skill.name} — {skill.description}")

PROJECT_DIR = str(Path(__file__).resolve().parents[1])


async def main() -> None:
    """Query Claude with the exported plugin loaded."""
    options = ClaudeAgentOptions(
        cwd=PROJECT_DIR,
        plugins=[{"type": "local", "path": str(plugin.path)}],
        allowed_tools=["Skill", "Read", "Grep", "Glob", "Bash"],
        max_turns=3,
    )

    async for message in query(
        prompt="What custom commands do you have available?",
        options=options,
    ):
        print(message)


if __name__ == "__main__":
    asyncio.run(main())
