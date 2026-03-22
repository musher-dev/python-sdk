"""Example: Install skills to a project-level Claude skills directory.

Replaces fragile symlink-based workflows with a real directory install.
Handles file copying, cleanup of stale skills, and directory structure.
"""

from pathlib import Path

import musher

# NOTE: Bundle references below (e.g. "acme/engineering-workflows:2.0.0") are
# placeholders. Replace with a real bundle ref from your Musher registry.

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/engineering-workflows:2.0.0")

# Install specific skills to the project-level Claude skills directory.
# clean=True removes stale Musher-managed skill installs for this bundle
# from the target directory. It does NOT affect unrelated user-managed skills.
skills_dir = Path(".claude/skills")
bundle.install_claude_skills(
    skills_dir,
    skills=["researching-repos", "drafting-release-notes"],
    clean=True,
)

print(f"Installed skills to {skills_dir}")
for skill in bundle.skills():
    print(f"  {skill.name}: {skill.description}")
    print(f"    Files: {len(skill.files())}")

# To use these skills with the Claude Agent SDK:
#
#   from claude_agent_sdk import ClaudeAgentOptions, query
#
#   options = ClaudeAgentOptions(
#       cwd=str(Path(__file__).resolve().parents[1]),
#       setting_sources=["project"],
#       allowed_tools=["Skill", "Read", "Grep", "Glob", "Bash"],
#       max_turns=4,
#   )
#
#   async for message in query(prompt="What skills are available?", options=options):
#       ...
