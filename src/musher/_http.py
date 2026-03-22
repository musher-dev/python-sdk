"""HTTP transport layer with error mapping."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from musher._errors import (
    APIError,
    AuthenticationError,
    BundleNotFoundError,
    RateLimitError,
)

if TYPE_CHECKING:
    from musher._config import MusherConfig


class HTTPTransport:
    """Thin wrapper around ``httpx.AsyncClient`` with auth and error mapping."""

    def __init__(self, config: MusherConfig) -> None:
        self._config: MusherConfig = config
        self._client: httpx.AsyncClient | None = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {"User-Agent": "musher-python/0.1.0"}
            if self._config.token:
                headers["Authorization"] = f"Bearer {self._config.token}"

            transport = httpx.AsyncHTTPTransport(retries=self._config.max_retries)
            self._client = httpx.AsyncClient(
                base_url=self._config.registry_url,
                headers=headers,
                timeout=self._config.timeout,
                transport=transport,
            )
        return self._client

    async def get(self, path: str, *, params: dict[str, str] | None = None) -> httpx.Response:
        """Send a GET request and map errors."""
        client = self._ensure_client()
        response = await client.get(path, params=params)
        _raise_for_status(response)
        return response

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def _raise_for_status(response: httpx.Response) -> None:
    """Map HTTP error responses to SDK exceptions."""
    if response.is_success:
        return

    status = response.status_code

    if status == 401:  # noqa: PLR2004
        raise AuthenticationError("Invalid or missing API token")

    if status == 404:  # noqa: PLR2004
        raise BundleNotFoundError(str(response.url))

    if status == 429:  # noqa: PLR2004
        retry_after_header: str | None = response.headers.get("Retry-After")  # pyright: ignore[reportAny]
        raise RateLimitError(retry_after=float(retry_after_header) if retry_after_header else None)

    # Try RFC 9457 Problem Details
    try:
        body: dict[str, object] = response.json()  # pyright: ignore[reportAny]
        title = body.get("title", response.reason_phrase)
        detail = body.get("detail", "")
        type_uri = body.get("type", "")
        raise APIError(
            status=status,
            title=str(title),
            detail=str(detail),
            type_uri=str(type_uri),
        )
    except (ValueError, KeyError):
        raise APIError(
            status=status,
            title=response.reason_phrase,
            detail=response.text,
        ) from None
