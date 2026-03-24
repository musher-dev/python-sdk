"""Example: Structured output with bundle-managed prompts.

Combines Musher versioned prompts with PydanticAI structured output so
the agent returns a typed Pydantic model instead of plain text.

Requires: pip install pydantic-ai
"""

from pydantic import BaseModel
from pydantic_ai import Agent

import musher

# NOTE: Bundle references below (e.g. "acme/prompt-library:1.2.0") are
# placeholders. Replace with a real bundle ref from your Musher registry.

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")


class IncidentSummary(BaseModel):
    """Structured incident report summary."""

    title: str
    severity: str
    root_cause: str
    action_items: list[str]


bundle = musher.pull("acme/prompt-library:1.2.0")
instructions_text = bundle.prompt("system").text()

# The agent returns an IncidentSummary instead of free-form text
agent = Agent("openai:gpt-4o", instructions=instructions_text, output_type=IncidentSummary)

if __name__ == "__main__":
    result = agent.run_sync(
        "The payments API returned 503 errors for 12 minutes on 2025-03-20 "
        "due to a misconfigured connection pool after a config rollout."
    )
    summary = result.output
    print(f"Title:       {summary.title}")
    print(f"Severity:    {summary.severity}")
    print(f"Root cause:  {summary.root_cause}")
    print(f"Actions:     {', '.join(summary.action_items)}")
