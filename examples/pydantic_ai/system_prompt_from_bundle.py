"""Example: Use a Musher bundle prompt as a PydanticAI system prompt.

Pulls versioned prompts from a Musher bundle and wires them into a
PydanticAI Agent as the system prompt.

Requires: pip install pydantic-ai
"""

from pydantic_ai import Agent

import musher

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/prompt-library:1.2.0")

# Load a versioned system prompt from the bundle
system_prompt_text = bundle.prompt("system").text()

# Create a PydanticAI agent with the bundle-managed prompt
agent = Agent("openai:gpt-4o", system_prompt=system_prompt_text)

# To run the agent, set OPENAI_API_KEY and call:
#   agent.run_sync("Summarize the latest incident report.")
