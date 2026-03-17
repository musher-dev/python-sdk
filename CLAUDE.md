# Musher Python SDK

Python SDK for programmatically pulling and using Musher bundle assets.

## Architecture

```
src/musher/
├── _types.py      # Enums, BundleRef, OCI constants (no deps)
├── _errors.py     # Exception hierarchy (no deps)
├── _config.py     # Global configuration (deps: _errors)
├── _bundle.py     # Pydantic models for bundles/manifests (deps: _types)
├── _cache.py      # XDG-compliant disk cache (deps: _types, _errors)
├── _oci.py        # Low-level OCI interaction (deps: _types, _errors)
├── _client.py     # Client + AsyncClient (deps: all above)
├── adapters/      # Future framework adapters (LangChain, LlamaIndex)
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
```

## Code Standards

- Enums and types must mirror the platform API domain model
- Pydantic models use `alias_generator=to_camel` for camelCase wire format
- All public API is re-exported from `__init__.py`
- Internal modules are prefixed with `_` (private)
- Stub methods raise `NotImplementedError` until implemented
