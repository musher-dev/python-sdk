"""Exception hierarchy for the Musher SDK."""

from __future__ import annotations


class MusherError(Exception):
    """Base exception for all Musher SDK errors."""


class AuthenticationError(MusherError):
    """Authentication failed or token is invalid."""


class BundleNotFoundError(MusherError):
    """The requested bundle does not exist."""

    def __init__(self, ref: str) -> None:
        self.ref: str = ref
        super().__init__(f"Bundle not found: {ref}")


class VersionNotFoundError(MusherError):
    """The requested version of a bundle does not exist."""

    def __init__(self, ref: str, version: str) -> None:
        self.ref: str = ref
        self.version: str = version
        super().__init__(f"Version '{version}' not found for bundle: {ref}")


class IntegrityError(MusherError):
    """Content checksum verification failed."""

    def __init__(self, expected: str, actual: str) -> None:
        self.expected: str = expected
        self.actual: str = actual
        super().__init__(f"Integrity check failed: expected {expected}, got {actual}")


class RegistryError(MusherError):
    """An error occurred communicating with the OCI registry."""


class CacheError(MusherError):
    """An error occurred accessing the local bundle cache."""


class RateLimitError(MusherError):
    """API rate limit exceeded."""

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after: float | None = retry_after
        msg = "Rate limit exceeded"
        if retry_after is not None:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)


class APIError(MusherError):
    """API returned an error response (maps to RFC 9457 Problem Details)."""

    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        type_uri: str = "",
    ) -> None:
        self.status: int = status
        self.title: str = title
        self.detail: str = detail
        self.type_uri: str = type_uri
        super().__init__(f"{status} {title}: {detail}")
