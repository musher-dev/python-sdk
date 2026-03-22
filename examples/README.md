# Musher SDK Examples

Examples for the Musher Python SDK, organized by use case.

## Prerequisites

Requires Python **>=3.13**.

```bash
pip install musher-sdk
```

Set your API key via environment variable (recommended):

```bash
export MUSHER_API_KEY="msk_..."
```

Credentials are auto-discovered in this order:

1. `MUSHER_API_KEY` environment variable
2. OS keyring (`musher/<host>`)
3. Credential file (`~/.local/share/musher/credentials/<host>/api-key`)

To override explicitly in code: `musher.configure(token="your-token")`.

## Examples

| Example | Description | Extra deps | Status |
|---------|-------------|------------|--------|
| `basics/pull_bundle.py` | Pull a bundle and list its files | — | Working |
| `basics/inspect_manifest.py` | Resolve and inspect a manifest without pulling | — | Working |
| `basics/bundle_resources.py` | Access prompts, toolsets, and agent specs | — | Working |
| `claude/install_project_skills.py` | Install skills to a project `.claude/skills/` dir | — | Working |
| `claude/export_plugin.py` | Select skills and export as a Claude plugin | — | Working |
| `openai/local_shell_skill.py` | Export a skill as a local directory for OpenAI | `openai-agents` | Working |
| `openai/hosted_inline_skill.py` | Export a skill as an inline zip for OpenAI | `openai-agents` | Working |
| `pydantic_ai/instructions_from_bundle.py` | Use bundle prompts as PydanticAI agent instructions | `pydantic-ai` | Working |

All examples use implemented SDK methods. Bundle references (e.g.
`"acme/prompt-library:1.2.0"`) are placeholders — replace them with a real
bundle ref from your Musher registry before running.
