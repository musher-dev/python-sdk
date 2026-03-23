"""Tests for _errors module — hierarchy checks, attribute storage."""

from musher import (
    APIError,
    AuthenticationError,
    BundleNotFoundError,
    CacheError,
    IntegrityError,
    MusherError,
    RateLimitError,
    RegistryError,
    VersionNotFoundError,
)


class TestHierarchy:
    def test_all_subclass_musher_error(self):
        errors = [
            AuthenticationError,
            BundleNotFoundError,
            VersionNotFoundError,
            IntegrityError,
            RegistryError,
            CacheError,
            RateLimitError,
            APIError,
        ]
        for error_cls in errors:
            assert issubclass(error_cls, MusherError)


class TestBundleNotFoundError:
    def test_stores_ref(self):
        err = BundleNotFoundError("myorg/bundle")
        assert err.ref == "myorg/bundle"
        assert "myorg/bundle" in str(err)


class TestVersionNotFoundError:
    def test_stores_ref_and_version(self):
        err = VersionNotFoundError("myorg/bundle", "1.0.0")
        assert err.ref == "myorg/bundle"
        assert err.version == "1.0.0"


class TestIntegrityError:
    def test_stores_expected_actual(self):
        err = IntegrityError("abc", "def")
        assert err.expected == "abc"
        assert err.actual == "def"


class TestRateLimitError:
    def test_stores_retry_after(self):
        err = RateLimitError(retry_after=30.0)
        assert err.retry_after == 30.0

    def test_none_retry_after(self):
        err = RateLimitError()
        assert err.retry_after is None


class TestAPIError:
    def test_stores_fields(self):
        err = APIError(
            status=404,
            title="Not Found",
            detail="Bundle not found",
            type_uri="https://api.musher.dev/errors/not-found",
        )
        assert err.status == 404
        assert err.title == "Not Found"
        assert err.detail == "Bundle not found"
        assert err.type_uri == "https://api.musher.dev/errors/not-found"
