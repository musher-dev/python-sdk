"""Example: Dynamic instructions and tools powered by a Musher bundle.

Uses PydanticAI's @system_prompt decorator to load instructions at
runtime and exposes bundle toolset metadata as agent tools.

Requires: pip install pydantic-ai
"""

from pydantic_ai import Agent

import musher

# NOTE: Bundle references below (e.g. "acme/prompt-library:1.2.0") are
# placeholders. Replace with a real bundle ref from your Musher registry.

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/prompt-library:1.2.0")

agent = Agent("openai:gpt-4o")


@agent.system_prompt
def load_instructions() -> str:
    """Load instructions from the bundle at runtime."""
    return bundle.prompt("system").text()


@agent.tool_plain
def list_toolsets() -> str:
    """List available toolset names from the bundle."""
    names = [t.name for t in bundle.toolsets()]
    return f"Available toolsets: {', '.join(names)}" if names else "No toolsets available."


@agent.tool_plain
def get_toolset_config(name: str) -> str:
    """Get the JSON configuration for a named toolset."""
    ts = bundle.toolset(name)
    return str(ts.parse_json())


if __name__ == "__main__":
    result = agent.run_sync("What toolsets are available and what do they configure?")
    print(result.output)
