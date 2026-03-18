"""Example: Digest-pinned pull with verification and lockfile.

Demonstrates pulling a specific bundle version by digest, verifying integrity,
and writing a lockfile for reproducible deployments.
"""

import musher

musher.configure(token="your-token-here")

# Pull by digest for reproducibility (will raise NotImplementedError until pull is implemented)
bundle = musher.pull("acme/agent-toolkit@sha256:abc123def456")

# Verify all asset checksums match the manifest
bundle.verify()
print(f"Bundle verified: {bundle.ref} v{bundle.version}")

# Write a lockfile for CI/CD reproducibility
lockfile_path = bundle.write_lockfile()
print(f"Lockfile written to: {lockfile_path}")

# Inspect contents
for fh in bundle.files():
    print(f"  {fh.logical_path} ({fh.media_type or 'unknown'})")
