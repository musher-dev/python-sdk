"""Example: Select a subset of skills and export as a Claude plugin.

Demonstrates per-session skill narrowing — only expose the skills your agent
actually needs, reducing the skill surface area and avoiding tool overload.
"""

from pathlib import Path

import musher

# NOTE: Bundle references below (e.g. "acme/agent-toolkit:2.0.0") are
# placeholders. Replace with a real bundle ref from your Musher registry.

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/agent-toolkit:2.0.0")

# Select only the skills needed for this session
selection = bundle.select(skills=["csv-insights", "incident-summary"])

# PREVIEW: export_claude_plugin() is not yet implemented — will raise NotImplementedError.
plugin = selection.export_claude_plugin("safe-tools", dest=Path("./plugins"))
print(f"Plugin exported to: {plugin.path}")

# Verify only the selected skills are present
for skill in selection.skills():
    print(f"  Skill: {skill.name} — {skill.description}")
