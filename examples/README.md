# Musher SDK Examples

Examples for the Musher Python SDK, organized by use case.

## Prerequisites

Requires Python **>=3.13**.

```bash
pip install musher-sdk
```

Install example dependencies:

```bash
task setup:examples
```

## Environment Variables

| Variable | Required by | Description |
|----------|-------------|-------------|
| `MUSHER_API_KEY` | All examples | Musher registry API key |
| `OPENAI_API_KEY` | `openai/*`, `pydantic_ai/*` | OpenAI API key for agent execution |
| `ANTHROPIC_API_KEY` | `claude/*` | Anthropic API key for Claude agent SDK |

Set your Musher API key via environment variable (recommended):

```bash
export MUSHER_API_KEY="msk_..."
```

Credentials are auto-discovered in this order:

1. `MUSHER_API_KEY` environment variable
2. OS keyring (`musher/<host>`)
3. Credential file (`~/.local/share/musher/credentials/<host>/api-key`)

To override explicitly in code: `musher.configure(token="your-token")`.

## Running

Replace placeholder bundle references (e.g. `"acme/prompt-library:1.2.0"`) with
real ones from your Musher registry, then:

```bash
uv run python examples/openai/hosted_inline_skill.py
```

## Examples

| Example | Description | Extra deps | Status |
|---------|-------------|------------|--------|
| `basics/pull_bundle.py` | Pull a bundle and list its files | — | Working |
| `basics/inspect_manifest.py` | Resolve and inspect a manifest without pulling | — | Working |
| `basics/bundle_resources.py` | Access prompts, toolsets, and agent specs | — | Working |
| `claude/install_project_skills.py` | Install skills to a project `.claude/skills/` dir | `claude-agent-sdk` | Working |
| `claude/export_plugin.py` | Select skills and export as a Claude plugin | `claude-agent-sdk` | Working |
| `openai/local_shell_skill.py` | Export a skill as a local directory for OpenAI | `openai-agents` | Working |
| `openai/hosted_inline_skill.py` | Export a skill as an inline zip for OpenAI | `openai-agents` | Working |
| `pydantic_ai/instructions_from_bundle.py` | Use bundle prompts as PydanticAI agent instructions | `pydantic-ai` | Working |
| `pydantic_ai/structured_output.py` | Structured output with bundle-managed prompts | `pydantic-ai` | Working |
| `pydantic_ai/dynamic_instructions.py` | Dynamic instructions and tools from bundles | `pydantic-ai` | Working |

All examples use implemented SDK methods. Bundle references (e.g.
`"acme/prompt-library:1.2.0"`) are placeholders — replace them with a real
bundle ref from your Musher registry before running.
