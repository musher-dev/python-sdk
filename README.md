# Musher Python SDK

[![CI](https://github.com/musher-dev/python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/musher-dev/python-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/musher)](https://pypi.org/project/musher/)

Python SDK for the [Musher](https://musher.dev) bundle distribution platform. Pull versioned AI agent asset bundles (prompts, configs, tool definitions) into your Python applications.

## Installation

```bash
pip install musher
```

## Quick Start

```python
import musher

musher.configure(token="your-token")

bundle = musher.pull("myorg/my-bundle:1.0.0")

for asset in bundle.assets():
    print(f"{asset.logical_path}: {asset.size_bytes} bytes")
```

### Async

```python
async with musher.AsyncClient() as client:
    bundle = await client.pull("myorg/my-bundle:1.0.0")
```

## Status

This package is in early development. Core SDK methods are stubbed with `NotImplementedError` and will be implemented in upcoming releases.

## License

Apache-2.0
