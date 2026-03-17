"""Example: Resolve a bundle reference and inspect its manifest without pulling."""

import asyncio

import musher


async def main():
    musher.configure(token="your-token-here")

    # Resolve without pulling asset content (will raise NotImplementedError until implemented)
    async with musher.AsyncClient() as client:
        result = await client.resolve("myorg/my-bundle:1.0.0")

    print(f"Bundle: {result.ref} v{result.version}")
    print(f"State: {result.state}")

    if result.manifest:
        print(f"Assets ({len(result.manifest.layers)}):")
        for layer in result.manifest.layers:
            print(f"  {layer.logical_path} ({layer.asset_type}): {layer.size_bytes} bytes")


asyncio.run(main())
