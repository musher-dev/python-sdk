"""Load a Musher skill as an inline hosted OpenAI shell skill.

Requires: pip install openai-agents
"""

import asyncio

from agents import Agent, Runner, ShellTool

import musher

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")


async def main() -> None:
    bundle = musher.pull("musher-examples/data-workflows:1.0.0")
    skill = bundle.skill("csv-insights")
    inline = skill.export_openai_inline_skill()

    agent = Agent(
        name="Hosted CSV Analyst",
        model="gpt-4.1",
        instructions="Use the inline skill when it helps.",
        tools=[
            ShellTool(
                environment={
                    "type": "container_auto",
                    "network_policy": {"type": "disabled"},
                    "skills": [inline.to_dict()],
                }
            )
        ],
    )

    result = await Runner.run(
        agent,
        (
            "Use the csv-insights skill. Create /mnt/data/orders.csv with columns "
            "id,region,amount,status and at least 8 rows. Then report total amount "
            "by region and count failed orders."
        ),
    )
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
