"""Example: Pull a bundle and list its files."""

import musher

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("acme/agent-toolkit:2.0.0")

# List all files
for fh in bundle.files():
    print(f"{fh.logical_path} ({fh.media_type or 'unknown'})")

# Get a specific file
prompt = bundle.file("prompts/main.txt")
if prompt:
    print(f"Prompt content: {prompt.text()}")

# For reproducible deployments, pass a digest ref instead of a version tag:
#   "acme/agent-toolkit@sha256:abc123def456"
