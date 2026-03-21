"""Example: Resolve a bundle reference and inspect its manifest without pulling."""

import musher

# NOTE: Bundle references below (e.g. "acme/agent-toolkit:2.0.0") are
# placeholders. Replace with a real bundle ref from your Musher registry.

result = musher.resolve("acme/agent-toolkit:2.0.0")

print(f"Bundle: {result.ref} v{result.version}")
print(f"State: {result.state}")

if result.manifest:
    print(f"Files ({len(result.manifest.layers)}):")
    for layer in result.manifest.layers:
        print(f"  {layer.logical_path} ({layer.asset_type}): {layer.size_bytes} bytes")
