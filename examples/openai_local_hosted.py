"""Example: Export a skill for both OpenAI local-path and inline-zip formats.

Demonstrates dual-format export from a single skill — useful when you need
the same skill available as a local directory (for development) and as an
inline zip (for deployment/sharing).
"""

import musher

musher.configure(token="your-token-here")

# Pull the bundle (will raise NotImplementedError until pull is implemented)
bundle = musher.pull("acme/agent-toolkit:2.0.0")

# Get a single skill
search = bundle.skill("web-search")

# Export as local directory for development
local = search.export_openai_local_skill()
print(f"Local skill: {local.name} at {local.path}")
print(f"  Registration dict: {local.to_dict()}")

# Export as inline zip for deployment
inline = search.export_openai_inline_skill()
print(f"Inline skill: {inline.name}")
print(f"  Base64 size: {len(inline.content_base64)} chars")
print(f"  Registration dict: {inline.to_dict()}")
