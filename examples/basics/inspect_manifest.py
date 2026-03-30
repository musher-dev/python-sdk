"""Example: Resolve a bundle reference and inspect its manifest without pulling."""

import musher

result = musher.resolve("musher-examples/agent-toolkit:2.0.0")

print(f"Bundle: {result.ref} v{result.version}")
print(f"State: {result.state}")

if result.manifest:
    print(f"Files ({len(result.manifest.layers)}):")
    for layer in result.manifest.layers:
        print(f"  {layer.logical_path} ({layer.asset_type}): {layer.size_bytes} bytes")
