"""Example: Pull a bundle and list its files."""

import musher

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("musher-examples/agent-toolkit:2.0.0")

# List all files
for fh in bundle.files():
    print(f"{fh.logical_path} ({fh.media_type or 'unknown'})")

# Get a specific file
prompt = bundle.file("prompts/system.md")
if prompt:
    print(f"System prompt: {prompt.text()[:120]}...")

# For reproducible deployments, pass a digest ref instead of a version tag:
#   "musher-examples/agent-toolkit@sha256:abc123def456"
