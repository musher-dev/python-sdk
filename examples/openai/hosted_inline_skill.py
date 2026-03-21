"""Example: Export a skill as an inline zip for OpenAI Agents.

Exports a single skill as a base64-encoded zip suitable for hosted inline
consumption by the OpenAI Agents SDK.
"""

import musher

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/agent-toolkit:2.0.0")

# Get a single skill
skill = bundle.skill("csv-insights")

# PREVIEW: export_openai_inline_skill() is not yet implemented — will raise NotImplementedError.
# NOTE: The to_dict() shape may change to match OpenAI's current inline format
# (type: "inline" with a nested source block) before this method is finalized.
inline = skill.export_openai_inline_skill()
print(f"Inline skill: {inline.name}")
print(f"  Base64 size: {len(inline.content_base64)} chars")
print(f"  Registration dict: {inline.to_dict()}")
