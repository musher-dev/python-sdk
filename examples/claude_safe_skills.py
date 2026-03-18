"""Example: Select a subset of skills and export as a Claude plugin.

Demonstrates per-session skill narrowing — only expose the skills your agent
actually needs, reducing the attack surface and avoiding tool overload.
"""

from pathlib import Path

import musher

musher.configure(token="your-token-here")

# Pull the full bundle (will raise NotImplementedError until pull is implemented)
bundle = musher.pull("acme/agent-toolkit:2.0.0")

# Select only the skills needed for this session
selection = bundle.select(skills=["web-search", "calculator"])

# Export the selection as a Claude plugin
plugin = selection.export_claude_plugin("safe-tools", dest=Path("./plugins"))
print(f"Plugin exported to: {plugin.path}")

# Verify only 2 skills are present
for skill in selection.skills():
    print(f"  Skill: {skill.name} — {skill.description}")
