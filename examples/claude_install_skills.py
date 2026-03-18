"""Example: Install skills to a Claude skills directory.

Replaces fragile symlink-based workflows with a real directory install.
Handles file copying, cleanup of stale skills, and directory structure.
"""

from pathlib import Path

import musher

musher.configure(token="your-token-here")

# Pull the bundle (will raise NotImplementedError until pull is implemented)
bundle = musher.pull("acme/agent-toolkit:2.0.0")

# Install all skills to the Claude skills directory, cleaning up old versions
skills_dir = Path.home() / ".claude" / "skills"
bundle.install_claude_skills(skills_dir, clean=True)

print(f"Installed {len(bundle.skills())} skills to {skills_dir}")
for skill in bundle.skills():
    print(f"  {skill.name}: {skill.description}")
    print(f"    Files: {len(skill.files())}")
