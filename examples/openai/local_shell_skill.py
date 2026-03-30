"""Load a Musher skill as a local OpenAI shell skill and use it on this repo.

Requires: pip install openai-agents
"""

import asyncio
from pathlib import Path

from agents import (
    Agent,
    Runner,
    ShellCallOutcome,
    ShellCommandOutput,
    ShellCommandRequest,
    ShellResult,
    ShellTool,
)

import musher

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

PROJECT_DIR = Path(__file__).resolve().parents[2]


# WARNING: This executor runs arbitrary shell commands on the local machine.
# It is intended for development and demonstration only. Do not use in
# production without sandboxing and command allowlisting.
class RepoShell:
    """Minimal local shell executor for the OpenAI Agents SDK."""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd

    async def __call__(self, request: ShellCommandRequest) -> ShellResult:
        outputs: list[ShellCommandOutput] = []

        for command in request.data.action.commands:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            outputs.append(
                ShellCommandOutput(
                    command=command,
                    stdout=stdout.decode("utf-8", errors="ignore"),
                    stderr=stderr.decode("utf-8", errors="ignore"),
                    outcome=ShellCallOutcome(type="exit", exit_code=proc.returncode),
                )
            )

        return ShellResult(
            output=outputs,
            max_output_length=request.data.action.max_output_length,
            provider_data={"working_directory": str(self.cwd)},
        )


async def main() -> None:
    bundle = musher.pull("musher-examples/code-review-kit:1.2.0")
    skill = bundle.skill("researching-repos")
    local = skill.export_openai_local_skill(dest=PROJECT_DIR / ".musher" / "openai" / "skills")

    agent = Agent(
        name="Repo Research Assistant",
        model="gpt-4.1",
        instructions="Use the local skill when it helps. Keep the answer concise and actionable.",
        tools=[
            ShellTool(
                executor=RepoShell(PROJECT_DIR),
                environment={"type": "local", "skills": [local.to_dict()]},
            )
        ],
    )

    result = await Runner.run(
        agent,
        "Use the researching-repos skill to explore this repository and summarize its tech stack, structure, and conventions.",
    )
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
