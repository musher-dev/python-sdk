"""Example: Access versioned prompts, toolsets, and agent specs from a bundle."""

import musher

# Credentials auto-discovered from MUSHER_API_KEY env var, keyring,
# or credential file. To override: musher.configure(token="your-token")

bundle = musher.pull("musher-examples/prompt-library:1.2.0")

# Access versioned prompts by name
system_prompt = bundle.prompt("system")
print(f"System prompt: {system_prompt.text()[:80]}...")

# List all available prompts
print(f"\nAvailable prompts ({len(bundle.prompts())}):")
for p in bundle.prompts():
    print(f"  {p.name}: {p.text()[:60]}...")

# Access toolset configuration
print(f"\nAvailable toolsets ({len(bundle.toolsets())}):")
for t in bundle.toolsets():
    config = t.parse_json()
    print(f"  {t.name}: {config}")

# Access agent specs
print(f"\nAvailable agent specs ({len(bundle.agent_specs())}):")
for a in bundle.agent_specs():
    spec = a.parse_json()
    print(f"  {a.name}: {spec.get('name', 'unnamed')}")
