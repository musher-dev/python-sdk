# Musher Python SDK

[![CI](https://github.com/musher-dev/python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/musher-dev/python-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/musher-sdk)](https://pypi.org/project/musher-sdk/)

Python SDK for the [Musher](https://musher.dev) bundle distribution platform. Pull versioned AI agent asset bundles (prompts, configs, tool definitions) into your Python applications.

## Installation

```bash
pip install musher-sdk
```

## Quick Start

```python
import musher

# Explicit token
musher.configure(api_key="your-token")

bundle = musher.pull("myorg/my-bundle:1.0.0")

for asset in bundle.files():
    print(f"{asset.logical_path}: {len(asset.text())} chars")
```

### Async

```python
async with musher.AsyncClient() as client:
    bundle = await client.pull("myorg/my-bundle:1.0.0")
```

### Sync

```python
with musher.Client() as client:
    result = client.resolve("myorg/my-bundle:1.0.0")
    asset = client.fetch_asset("asset-id", version="1.0.0")
```

## Configuration

### Credential Chain

The SDK resolves credentials automatically in this order:

1. **Environment variables** — `MUSHER_API_KEY`
2. **OS keyring** — host-scoped service `musher/{hostname}`
3. **File fallback** — `<data_dir>/credentials/<host_id>/api-key` (must be `0600` permissions)

### Registry URL

The registry URL is resolved from environment variables:

- `MUSHER_API_URL`
- Default: `https://api.musher.dev`

### Programmatic Configuration

```python
import musher

# All parameters are optional — omitted values auto-discover
musher.configure(
    api_key="your-token",  # or token="your-token"
    api_url="https://custom.dev",  # or registry_url="https://custom.dev"
    cache_dir=Path("/tmp/cache"),
)
```

### Cache Behavior

The SDK uses a content-addressable disk cache:

- Blobs are stored by SHA-256 hash (shared across registries)
- Manifests and refs are partitioned by registry hostname
- Manifests have a configurable TTL (default 24h); refs default to 5min
- `clean()` removes expired entries and garbage-collects unreferenced blobs

## What's Implemented

- `resolve()` — resolve bundle references to manifests
- `fetch_asset()` — fetch individual assets by ID
- `pull()` — resolve + fetch all assets + verify checksums
- Sync (`Client`) and async (`AsyncClient`) clients
- Content-addressable cache with TTL and garbage collection
- Typed handles: skills, prompts, toolsets, agent specs

## What's Stubbed

- `export_claude_plugin()`, `install_vscode_skills()`, `install_claude_skills()`
- `write_lockfile()`, `verify()`
- OCI direct pull (`OCIClient`)

## License

Apache-2.0
