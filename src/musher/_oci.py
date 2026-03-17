"""Low-level OCI registry interaction (internal)."""

from __future__ import annotations


class OCIClient:
    """Internal client for direct OCI registry blob/manifest operations.

    This is a low-level building block used by the higher-level Client.
    Not part of the public API.
    """

    def __init__(self, registry_url: str, token: str | None = None) -> None:
        self._registry_url = registry_url
        self._token = token

    async def pull_manifest(self, repository: str, reference: str) -> dict:
        """Pull an OCI manifest for the given repository and reference."""
        raise NotImplementedError

    async def pull_blob(self, repository: str, digest: str) -> bytes:
        """Pull a blob by digest from the given repository."""
        raise NotImplementedError
