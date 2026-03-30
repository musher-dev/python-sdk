# Musher Python SDK

Python SDK for programmatically pulling and using Musher bundle assets.

## Architecture

```
src/musher/
├── _types.py      # Enums, BundleRef (no deps)
├── _errors.py     # Exception hierarchy (no deps)
├── _paths.py      # Platform-aware directory resolution (deps: platformdirs)
├── _config.py     # Global configuration (deps: _paths)
├── _auth.py       # Credential resolution chain (deps: _paths)
├── _bundle.py     # Pydantic models for bundles/manifests (deps: _types)
├── _cache.py      # Content-addressable disk cache (deps: _types, _errors)
├── _cache_info.py # Cache inspection types (no deps)
├── _http.py       # HTTP transport with error mapping (deps: _types, _errors)
├── _handles.py    # Typed resource handles (deps: _types, _export)
├── _export.py     # Framework export dataclasses (no deps)
├── _client.py     # Client + AsyncClient (deps: all above)
└── __init__.py    # Public API re-exports
```

## Essential Commands

```bash
task setup          # Install dependencies (uv sync --dev)
task check          # Run all checks (format + lint + types + test)
task check:lint     # Ruff linter
task check:types    # basedpyright type checker
task check:test     # pytest
task check:format   # Format with ruff
task check:fix      # Auto-fix lint issues and format
```

## Code Standards

- Enums and types must mirror the platform API domain model
- Pydantic models use `alias_generator=to_camel` for camelCase wire format
- All public API is re-exported from `__init__.py`
- Internal modules are prefixed with `_` (private)
- `BundleCache` is internal — not exported in `__all__`
