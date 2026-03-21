"""Example: Export a skill as a local directory for OpenAI Agents.

Exports a single skill to disk so it can be loaded as a local shell skill
by the OpenAI Agents SDK.
"""

import musher

# NOTE: Bundle references below (e.g. "acme/agent-toolkit:2.0.0") are
# placeholders. Replace with a real bundle ref from your Musher registry.

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/agent-toolkit:2.0.0")

# Get a single skill
skill = bundle.skill("csv-insights")

# PREVIEW: export_openai_local_skill() is not yet implemented — will raise NotImplementedError.
local = skill.export_openai_local_skill()
print(f"Local skill: {local.name} at {local.path}")
print(f"  Registration dict: {local.to_dict()}")
