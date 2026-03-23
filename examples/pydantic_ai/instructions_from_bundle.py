"""Example: Use a Musher bundle prompt as PydanticAI agent instructions.

Pulls versioned prompts from a Musher bundle and wires them into a
PydanticAI Agent as the system instructions.

Requires: pip install pydantic-ai
"""

from pydantic_ai import Agent

import musher

# NOTE: Bundle references below (e.g. "acme/prompt-library:1.2.0") are
# placeholders. Replace with a real bundle ref from your Musher registry.

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/prompt-library:1.2.0")

# Load versioned instructions from the bundle
instructions_text = bundle.prompt("system").text()
print(f"Loaded instructions ({len(instructions_text)} chars): {instructions_text[:80]}...")

# Create a PydanticAI agent with bundle-managed instructions
agent = Agent("openai:gpt-4o", instructions=instructions_text)

if __name__ == "__main__":
    result = agent.run_sync("Summarize the latest incident report.")
    print(result.output)
