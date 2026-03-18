"""Example: Pull a bundle and list its files."""

import musher

# Configure with your API token
musher.configure(token="your-token-here")

# Pull a bundle (will raise NotImplementedError until implemented)
bundle = musher.pull("myorg/my-bundle:1.0.0")

# List all files
for fh in bundle.files():
    print(f"{fh.logical_path} ({fh.media_type or 'unknown'})")

# Get a specific file
prompt = bundle.file("prompts/main.txt")
if prompt:
    print(f"Prompt content: {prompt.text()}")
