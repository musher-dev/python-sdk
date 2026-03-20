"""Tests for _http module — auth headers, error mapping."""

import httpx
import pytest
import respx

from musher._config import MusherConfig
from musher._errors import APIError, AuthenticationError, BundleNotFoundError, RateLimitError
from musher._http import HTTPTransport


@pytest.fixture
def transport() -> HTTPTransport:
    return HTTPTransport(MusherConfig(token="test-token", registry_url="https://api.test.dev"))


@pytest.fixture
def anon_transport() -> HTTPTransport:
    return HTTPTransport(MusherConfig(registry_url="https://api.test.dev"))


class TestAuthHeaders:
    @respx.mock
    async def test_bearer_token_sent(self, transport: HTTPTransport):
        route = respx.get("https://api.test.dev/v1/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        await transport.get("/v1/test")
        assert route.called
        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer test-token"

    @respx.mock
    async def test_no_auth_header_when_no_token(self, anon_transport: HTTPTransport):
        route = respx.get("https://api.test.dev/v1/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        await anon_transport.get("/v1/test")
        assert "Authorization" not in route.calls[0].request.headers

    @respx.mock
    async def test_user_agent_set(self, transport: HTTPTransport):
        route = respx.get("https://api.test.dev/v1/test").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        await transport.get("/v1/test")
        assert "musher-python/0.1.0" in route.calls[0].request.headers["User-Agent"]


class TestErrorMapping:
    @respx.mock
    async def test_401_raises_authentication_error(self, transport: HTTPTransport):
        respx.get("https://api.test.dev/v1/test").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )
        with pytest.raises(AuthenticationError):
            await transport.get("/v1/test")

    @respx.mock
    async def test_404_raises_bundle_not_found(self, transport: HTTPTransport):
        respx.get("https://api.test.dev/v1/test").mock(
            return_value=httpx.Response(404, text="Not Found")
        )
        with pytest.raises(BundleNotFoundError):
            await transport.get("/v1/test")

    @respx.mock
    async def test_429_raises_rate_limit_with_retry_after(self, transport: HTTPTransport):
        respx.get("https://api.test.dev/v1/test").mock(
            return_value=httpx.Response(
                429, headers={"Retry-After": "30"}, text="Too Many Requests"
            )
        )
        with pytest.raises(RateLimitError) as exc_info:
            await transport.get("/v1/test")
        assert exc_info.value.retry_after == 30.0

    @respx.mock
    async def test_500_raises_api_error(self, transport: HTTPTransport):
        respx.get("https://api.test.dev/v1/test").mock(
            return_value=httpx.Response(
                500,
                json={
                    "title": "Internal Server Error",
                    "detail": "Something broke",
                    "type": "about:blank",
                },
            )
        )
        with pytest.raises(APIError) as exc_info:
            await transport.get("/v1/test")
        assert exc_info.value.status == 500
        assert exc_info.value.title == "Internal Server Error"
        assert exc_info.value.detail == "Something broke"

    @respx.mock
    async def test_500_plain_text_fallback(self, transport: HTTPTransport):
        respx.get("https://api.test.dev/v1/test").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(APIError) as exc_info:
            await transport.get("/v1/test")
        assert exc_info.value.status == 500


class TestClose:
    @respx.mock
    async def test_close_releases_client(self, transport: HTTPTransport):
        respx.get("https://api.test.dev/v1/test").mock(return_value=httpx.Response(200, json={}))
        await transport.get("/v1/test")
        await transport.close()
        assert transport._client is None
