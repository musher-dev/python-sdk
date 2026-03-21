"""Example: Install skills to a project-level Claude skills directory.

Replaces fragile symlink-based workflows with a real directory install.
Handles file copying, cleanup of stale skills, and directory structure.
"""

from pathlib import Path

import musher

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/agent-toolkit:2.0.0")

# Install all skills to the project-level Claude skills directory
skills_dir = Path(".claude/skills")

# PREVIEW: install_claude_skills() is not yet implemented — will raise NotImplementedError.
bundle.install_claude_skills(skills_dir, clean=True)

print(f"Installed {len(bundle.skills())} skills to {skills_dir}")
for skill in bundle.skills():
    print(f"  {skill.name}: {skill.description}")
    print(f"    Files: {len(skill.files())}")
