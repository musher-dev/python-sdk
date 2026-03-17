"""Example: Pull a bundle and list its assets."""

import musher

# Configure with your API token
musher.configure(token="your-token-here")

# Pull a bundle (will raise NotImplementedError until implemented)
bundle = musher.pull("myorg/my-bundle:1.0.0")

# List all assets
for asset in bundle.assets():
    print(f"{asset.logical_path} ({asset.asset_type}): {asset.size_bytes} bytes")

# Get a specific asset
prompt = bundle.asset("prompts/main.txt")
if prompt:
    print(f"Prompt content: {prompt.content.decode()}")
