"""Content-addressable disk cache for bundle blobs and manifests."""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from musher._config import get_config

_CACHEDIR_TAG_HEADER = (
    "Signature: 8a477f597d28d172789f06886806bc55\n"
    "# This file is a cache directory tag created by musher.\n"
    "# For information about cache directory tags, see:\n"
    "#   https://bford.info/cachedir/spec.html\n"
)

_DEFAULT_MANIFEST_TTL = 86400
_DEFAULT_REF_TTL = 300


def _host_id_from_url(url: str) -> str:
    """Extract and sanitize a hostname identifier from a registry URL.

    Replaces ``:``, ``/``, and other path-unsafe characters with ``_``.
    """
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port
    if port:
        return f"{host}_{port}"
    return host


class BundleCache:
    """Local disk cache with content-addressable blob storage.

    Layout::

        $cache_root/
          CACHEDIR.TAG
          blobs/sha256/<prefix>/<digest>
          manifests/<host-id>/<ns>/<slug>/<version>.json
          manifests/<host-id>/<ns>/<slug>/<version>.meta.json
          refs/<host-id>/<ns>/<slug>/<ref>.json
    """

    _cache_dir: Path
    _host_id: str
    _tag_written: bool

    def __init__(self, cache_dir: Path | None = None, *, registry_url: str | None = None) -> None:
        self._cache_dir = cache_dir or get_config().cache_dir
        registry_url = registry_url or get_config().registry_url
        self._host_id = _host_id_from_url(registry_url)
        self._tag_written = False

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    @property
    def host_id(self) -> str:
        return self._host_id

    # ── CACHEDIR.TAG ────────────────────────────────────────────────

    def _ensure_cachedir_tag(self) -> None:
        """Write CACHEDIR.TAG at cache root on first write operation."""
        if self._tag_written:
            return
        tag_path = self._cache_dir / "CACHEDIR.TAG"
        if not tag_path.is_file():
            tag_path.parent.mkdir(parents=True, exist_ok=True)
            _ = tag_path.write_text(_CACHEDIR_TAG_HEADER)
        self._tag_written = True

    # ── Blob operations ────────────────────────────────────────────

    def get_blob(self, content_sha256: str) -> bytes | None:
        """Retrieve a cached blob by SHA-256 hash. Returns ``None`` on miss."""
        path = self._blob_path(content_sha256)
        if path.is_file():
            return path.read_bytes()
        return None

    def put_blob(self, content_sha256: str, data: bytes) -> None:
        """Store a blob using atomic write (tmp + rename)."""
        self._ensure_cachedir_tag()
        path = self._blob_path(content_sha256)
        self._atomic_write_bytes(path, data)

    # ── Manifest operations ────────────────────────────────────────

    def get_manifest(self, namespace: str, slug: str, version: str) -> dict[str, object] | None:
        """Retrieve a cached manifest. Returns ``None`` on miss."""
        path = self._manifest_path(namespace, slug, version)
        if path.is_file():
            return cast("dict[str, object]", json.loads(path.read_text()))
        return None

    def put_manifest(
        self,
        namespace: str,
        slug: str,
        version: str,
        data: dict[str, object],
        *,
        oci_digest: str | None = None,
        ttl: int = _DEFAULT_MANIFEST_TTL,
    ) -> None:
        """Store a manifest as JSON with a freshness sidecar."""
        self._ensure_cachedir_tag()
        path = self._manifest_path(namespace, slug, version)
        self._atomic_write_json(path, data)

        # Write .meta.json sidecar
        meta_path = self._meta_path(namespace, slug, version)
        meta: dict[str, object] = {
            "fetchedAt": datetime.now(UTC).isoformat(),
            "ttlSeconds": ttl,
            "ociDigest": oci_digest,
        }
        self._atomic_write_json(meta_path, meta)

    def is_manifest_fresh(self, namespace: str, slug: str, version: str) -> bool:
        """Check whether a cached manifest is still within its TTL."""
        meta_path = self._meta_path(namespace, slug, version)
        if not meta_path.is_file():
            return False
        try:
            raw = cast("dict[str, object]", json.loads(meta_path.read_text()))
            fetched_at = datetime.fromisoformat(cast("str", raw["fetchedAt"]))
            ttl = cast("int", raw.get("ttlSeconds", _DEFAULT_MANIFEST_TTL))
            age = (datetime.now(UTC) - fetched_at).total_seconds()
            return bool(age < ttl)
        except (KeyError, ValueError, json.JSONDecodeError):
            return False

    # ── Ref operations ─────────────────────────────────────────────

    def get_ref(self, namespace: str, slug: str, ref: str) -> str | None:
        """Retrieve a cached ref → version mapping. Returns ``None`` on miss or expiry."""
        path = self._ref_path(namespace, slug, ref)
        if not path.is_file():
            return None
        try:
            data = cast("dict[str, object]", json.loads(path.read_text()))
            expires_at = cast("float", data.get("expiresAt", 0))
            if time.time() > expires_at:
                path.unlink(missing_ok=True)
                return None
            return cast("str | None", data.get("version"))
        except (json.JSONDecodeError, KeyError):
            return None

    def put_ref(
        self,
        namespace: str,
        slug: str,
        ref: str,
        version: str,
        *,
        ttl: int = _DEFAULT_REF_TTL,
    ) -> None:
        """Cache a ref → version alias mapping with TTL."""
        self._ensure_cachedir_tag()
        path = self._ref_path(namespace, slug, ref)
        data: dict[str, object] = {
            "version": version,
            "cachedAt": datetime.now(UTC).isoformat(),
            "expiresAt": time.time() + ttl,
        }
        self._atomic_write_json(path, data)

    # ── Maintenance ────────────────────────────────────────────────

    def clean(self) -> int:
        """Remove expired manifests (stale meta) and refs, then GC unreferenced blobs.

        Returns count of removed entries (manifests + refs + blobs).
        """
        removed = 0

        # Clean expired manifests
        manifests_dir = self._cache_dir / "manifests" / self._host_id
        if manifests_dir.is_dir():
            for meta_file in manifests_dir.rglob("*.meta.json"):
                try:
                    raw = cast("dict[str, object]", json.loads(meta_file.read_text()))
                    fetched_at = datetime.fromisoformat(cast("str", raw["fetchedAt"]))
                    ttl = cast("int", raw.get("ttlSeconds", _DEFAULT_MANIFEST_TTL))
                    age = (datetime.now(UTC) - fetched_at).total_seconds()
                    if age >= ttl:
                        # Remove both manifest and meta
                        manifest_file = meta_file.with_name(
                            meta_file.name.replace(".meta.json", ".json")
                        )
                        manifest_file.unlink(missing_ok=True)
                        meta_file.unlink(missing_ok=True)
                        removed += 1
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        # Clean expired refs
        refs_dir = self._cache_dir / "refs" / self._host_id
        if refs_dir.is_dir():
            for ref_file in refs_dir.rglob("*.json"):
                try:
                    ref_data = cast("dict[str, object]", json.loads(ref_file.read_text()))
                    if time.time() > cast("float", ref_data.get("expiresAt", 0)):
                        ref_file.unlink(missing_ok=True)
                        removed += 1
                except (json.JSONDecodeError, KeyError):
                    continue

        # GC unreferenced blobs
        removed += self.gc()

        return removed

    def gc(self) -> int:
        """Remove blobs not referenced by any cached manifest. Returns count of removed blobs."""
        referenced = self._collect_referenced_blobs()

        blobs_dir = self._cache_dir / "blobs" / "sha256"
        if not blobs_dir.is_dir():
            return 0

        removed = 0
        for prefix_dir in blobs_dir.iterdir():
            if not prefix_dir.is_dir():
                continue
            for blob_file in prefix_dir.iterdir():
                if blob_file.is_file() and blob_file.name not in referenced:
                    blob_file.unlink()
                    removed += 1
            # Clean up empty prefix directory
            if prefix_dir.is_dir() and not any(prefix_dir.iterdir()):
                prefix_dir.rmdir()

        return removed

    def _collect_referenced_blobs(self) -> set[str]:
        """Walk all cached manifests and collect referenced contentSha256 values."""
        referenced: set[str] = set()
        manifests_root = self._cache_dir / "manifests"
        if not manifests_root.is_dir():
            return referenced

        for manifest_file in manifests_root.rglob("*.json"):
            if manifest_file.name.endswith(".meta.json"):
                continue
            try:
                manifest = cast("dict[str, object]", json.loads(manifest_file.read_text()))
                manifest_obj = cast("dict[str, object]", manifest.get("manifest", manifest))
                layers = cast("list[dict[str, object]]", manifest_obj.get("layers", []))
                for layer in layers:
                    sha = cast("str | None", layer.get("contentSha256"))
                    if sha:
                        referenced.add(sha)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        return referenced

    def purge(self, namespace: str, slug: str, version: str | None = None) -> None:
        """Remove specific cached entries for a bundle.

        If *version* is given, removes only that version's manifest and meta.
        Otherwise removes all manifests, refs, and meta for the namespace/slug.
        """
        if version:
            self._manifest_path(namespace, slug, version).unlink(missing_ok=True)
            self._meta_path(namespace, slug, version).unlink(missing_ok=True)
        else:
            # Remove all manifests for this ns/slug
            manifest_dir = self._cache_dir / "manifests" / self._host_id / namespace / slug
            if manifest_dir.is_dir():
                shutil.rmtree(manifest_dir)
            # Remove all refs for this ns/slug
            ref_dir = self._cache_dir / "refs" / self._host_id / namespace / slug
            if ref_dir.is_dir():
                shutil.rmtree(ref_dir)

    def clear(self) -> None:
        """Remove all cached data."""
        if self._cache_dir.is_dir():
            shutil.rmtree(self._cache_dir)

    # ── Internal ───────────────────────────────────────────────────

    def _blob_path(self, content_sha256: str) -> Path:
        return self._cache_dir / "blobs" / "sha256" / content_sha256[:2] / content_sha256

    def _manifest_path(self, namespace: str, slug: str, version: str) -> Path:
        return self._cache_dir / "manifests" / self._host_id / namespace / slug / f"{version}.json"

    def _meta_path(self, namespace: str, slug: str, version: str) -> Path:
        return (
            self._cache_dir
            / "manifests"
            / self._host_id
            / namespace
            / slug
            / f"{version}.meta.json"
        )

    def _ref_path(self, namespace: str, slug: str, ref: str) -> Path:
        return self._cache_dir / "refs" / self._host_id / namespace / slug / f"{ref}.json"

    @staticmethod
    def _atomic_write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent)
        tmp = Path(tmp_name)
        try:
            with open(fd, "wb") as f:  # noqa: PTH123, FURB103
                _ = f.write(data)
            _ = tmp.replace(path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    @staticmethod
    def _atomic_write_json(path: Path, data: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".json")
        tmp = Path(tmp_name)
        try:
            with open(fd, "w", encoding="utf-8") as f:  # noqa: PTH123
                json.dump(data, f)
            _ = tmp.replace(path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
