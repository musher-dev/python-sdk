# Musher SDK Configuration

Storage, authentication, and cache specification for the Musher Python SDK.

## Directory Layout

The SDK uses platform-aware directory resolution with the following precedence:

1. **Branded env var** (e.g. `MUSHER_CACHE_HOME=/path`)
2. **Umbrella env var** (`MUSHER_HOME=/path` derives `$MUSHER_HOME/<category>`)
3. **Platform default**

| Category | Env Var | Linux (XDG) | macOS | Windows |
|---|---|---|---|---|
| cache | `MUSHER_CACHE_HOME` | `~/.cache/musher` | `~/Library/Caches/musher` | `%LOCALAPPDATA%\musher\cache` |
| config | `MUSHER_CONFIG_HOME` | `~/.config/musher` | `~/Library/Application Support/musher` | `%LOCALAPPDATA%\musher\config` |
| data | `MUSHER_DATA_HOME` | `~/.local/share/musher` | `~/Library/Application Support/musher` | `%LOCALAPPDATA%\musher\data` |
| state | `MUSHER_STATE_HOME` | `~/.local/state/musher` | `~/Library/Application Support/musher` | `%LOCALAPPDATA%\musher\state` |
| runtime | `MUSHER_RUNTIME_DIR` | `$XDG_RUNTIME_DIR/musher` | `<tempdir>/musher/run`* | `<tempdir>\musher\run`* |

\* `<tempdir>` is the system temporary directory (e.g. `/tmp` on macOS, `C:\Users\<user>\AppData\Local\Temp` on Windows).

On Windows, the SDK uses a flat layout under `%LOCALAPPDATA%\musher\` with category subdirectories rather than relying on `platformdirs`, which maps some categories to the same physical path.

## Environment Variables

### Token / API Key

| Variable | Purpose |
|---|---|
| `MUSHER_API_KEY` | API token |

### Registry URL

| Variable | Purpose |
|---|---|
| `MUSHER_API_URL` | Registry URL |

Default: `https://api.musher.dev`

All URL values are stripped of trailing `/` before use.

## Credential Resolution Chain

The SDK resolves credentials in this order, stopping at the first match:

1. **Environment variables** — `MUSHER_API_KEY`
2. **OS keyring** — service `musher/{hostname}`, username `api-key`
   - Hostname is derived from the registry URL (e.g. `musher/api.musher.dev`)
3. **File fallback** — `<data_dir>/credentials/<host_id>/api-key`
   - Must have `0600` permissions (owner-only); rejected otherwise

## Cache Structure

```
$cache_root/
  CACHEDIR.TAG
  blobs/sha256/<prefix>/<digest>
  manifests/<host-id>/<ns>/<slug>/<version>.json
  manifests/<host-id>/<ns>/<slug>/<version>.meta.json
  refs/<host-id>/<ns>/<slug>/<ref>.json
```

- **Blobs** are content-addressable by SHA-256, shared across all registries
- **Manifests** and **refs** are partitioned by registry hostname (`<host-id>`)
- **Meta sidecars** (`.meta.json`) track fetch time, TTL, and OCI digest
- **CACHEDIR.TAG** marks the root as a cache directory per the [spec](https://bford.info/cachedir/spec.html)

### TTL Defaults

| Entry Type | Default TTL |
|---|---|
| Manifest | 86400s (24h) |
| Ref | 300s (5min) |

### Garbage Collection

`BundleCache.gc()` removes blobs not referenced by any cached manifest. It is called automatically at the end of `clean()`. Empty blob prefix directories are removed.

## Programmatic Configuration

```python
import musher
from pathlib import Path

musher.configure(
    token="...",  # explicit token
    registry_url="https://...",  # explicit registry URL
    cache_dir=Path("..."),  # override cache directory
)
```

When `token` is not provided, the credential chain is used automatically. When `registry_url` is not provided, the URL env var chain is checked.
