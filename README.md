<div align="center">

# Musher Python SDK

[![CI](https://github.com/musher-dev/python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/musher-dev/python-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/musher-sdk)](https://pypi.org/project/musher-sdk/)

Python SDK for the [Musher](https://musher.dev) bundle distribution platform. Pull versioned AI agent asset bundles — prompts, tool definitions, agent specs, and skills — into your Python applications.

</div>

## Installation

Requires **Python 3.13+**.

```bash
pip install musher-sdk
```

## Authentication

Set your API key as an environment variable:

```bash
export MUSHER_API_KEY="msk_..."
```

The SDK resolves credentials automatically in this order:

1. `MUSHER_API_KEY` environment variable
2. OS keyring (`musher/{hostname}`)
3. Credential file (`<data_dir>/credentials/<host_id>/api-key`, must be `0600`)

You can also pass a token directly:

```python
musher.configure(token="msk_...")
```

## Quick Start

```python
import musher

bundle = musher.pull("myorg/my-bundle:1.0.0")

for f in bundle.files():
    print(f"{f.logical_path}: {len(f.text())} chars")
```

### Async

```python
import musher

async with musher.AsyncClient() as client:
    bundle = await client.pull("myorg/my-bundle:1.0.0")
```

### Sync Client

```python
import musher

with musher.Client() as client:
    bundle = client.pull("myorg/my-bundle:1.0.0")

    result = client.resolve("myorg/my-bundle:1.0.0")

    asset = client.fetch_asset(
        "prompts/system.md",
        namespace="myorg",
        slug="my-bundle",
        version="1.0.0",
    )
```

## Working with Bundles

Bundles provide typed accessors for each resource type:

```python
bundle = musher.pull("myorg/my-bundle:1.0.0")

# Prompts
prompt = bundle.prompt("system")
print(prompt.text())

# Skills
for skill in bundle.skills():
    print(skill.name, skill.description)

# Toolsets and agent specs
toolset = bundle.toolset("search-tools")
data = toolset.parse_json()

spec = bundle.agent_spec("reviewer")
config = spec.parse_json()
```

Filter to a subset of resources with `select()`:

```python
selection = bundle.select(skills=["code-review"], prompts=["system"])
```

## Framework Integrations

The SDK integrates with popular AI agent frameworks:

- **Claude** — export bundles as Claude plugins or install skills to `.claude/skills/` ([examples](examples/claude/))
- **OpenAI Agents** — export skills as local directories or inline zips for the OpenAI shell tool ([examples](examples/openai/))
- **PydanticAI** — use bundle prompts as agent instructions with structured output ([examples](examples/pydantic_ai/))

## Configuration

### Registry URL

```bash
export MUSHER_API_URL="https://custom-registry.example.com"
```

Default: `https://api.musher.dev`

### Programmatic Configuration

```python
from pathlib import Path
import musher

musher.configure(
    token="msk_...",
    registry_url="https://custom-registry.example.com",
    cache_dir=Path("/tmp/musher-cache"),
    verify_checksums=True,
    timeout=30.0,
    max_retries=2,
)
```

All parameters are optional — omitted values are auto-discovered.

See [Configuration](docs/configuration.md) for the full reference (directory layout, credential chain, cache structure, TTL defaults).

### Cache

The SDK uses a content-addressable disk cache:

- Blobs stored by SHA-256 hash, shared across registries
- Manifests and refs partitioned by registry hostname
- Manifests TTL: 24h; refs TTL: 5min
- `cache_clean()` removes expired entries and garbage-collects unreferenced blobs

Cache management functions are available at the module level and on the `Client`:

```python
import musher

info = musher.cache_info()  # cache statistics
musher.cache_remove("myorg/my-bundle:1.0.0")  # remove a specific bundle
musher.cache_clean()  # remove expired entries
musher.cache_clear()  # remove all cached data
path = musher.cache_path()  # cache directory path
```

## Features

- `pull()` / `pull_async()` — resolve + fetch all assets + verify checksums
- `resolve()` / `resolve_async()` — resolve bundle references to manifests
- `fetch_asset()` — fetch individual assets by logical path
- Sync (`Client`) and async (`AsyncClient`) clients
- Typed handles: `SkillHandle`, `PromptHandle`, `ToolsetHandle`, `AgentSpecHandle`
- `bundle.select()` — filter resources by type
- Content-addressable cache with TTL and garbage collection
- Cache management: `cache_info()`, `cache_remove()`, `cache_clear()`, `cache_clean()`, `cache_path()`
- `export_claude_plugin()` / `install_claude_skills()` — Claude integration
- `export_openai_local_skill()` / `export_openai_inline_skill()` — OpenAI Agents integration

## Examples

See the [examples/](examples/) directory for runnable code samples covering basic usage, Claude, OpenAI Agents, and PydanticAI integrations.

## License

Apache-2.0
