"""Content-addressable disk cache for bundle blobs and manifests."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from musher._config import get_config


class BundleCache:
    """Local disk cache with content-addressable blob storage.

    Layout::

        $XDG_CACHE_HOME/musher/
          blobs/sha256/<first-2-chars>/<full-hash>
          manifests/<namespace>/<slug>/<version>.json
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or get_config().cache_dir

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    # ── Blob operations ────────────────────────────────────────────

    def get_blob(self, content_sha256: str) -> bytes | None:
        """Retrieve a cached blob by SHA-256 hash. Returns ``None`` on miss."""
        path = self._blob_path(content_sha256)
        if path.is_file():
            return path.read_bytes()
        return None

    def put_blob(self, content_sha256: str, data: bytes) -> None:
        """Store a blob using atomic write (tmp + rename)."""
        path = self._blob_path(content_sha256)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent)
        tmp = Path(tmp_name)
        try:
            with open(fd, "wb") as f:  # noqa: PTH123
                f.write(data)
            tmp.rename(path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    # ── Manifest operations ────────────────────────────────────────

    def get_manifest(self, namespace: str, slug: str, version: str) -> dict[str, Any] | None:
        """Retrieve a cached manifest. Returns ``None`` on miss."""
        path = self._manifest_path(namespace, slug, version)
        if path.is_file():
            return json.loads(path.read_text())
        return None

    def put_manifest(self, namespace: str, slug: str, version: str, data: dict[str, Any]) -> None:
        """Store a manifest as JSON using atomic write."""
        path = self._manifest_path(namespace, slug, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".json")
        tmp = Path(tmp_name)
        try:
            with open(fd, "w") as f:  # noqa: PTH123
                json.dump(data, f)
            tmp.rename(path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    # ── Maintenance ────────────────────────────────────────────────

    def clear(self) -> None:
        """Remove all cached data."""
        if self._cache_dir.is_dir():
            shutil.rmtree(self._cache_dir)

    # ── Internal ───────────────────────────────────────────────────

    def _blob_path(self, content_sha256: str) -> Path:
        return self._cache_dir / "blobs" / "sha256" / content_sha256[:2] / content_sha256

    def _manifest_path(self, namespace: str, slug: str, version: str) -> Path:
        return self._cache_dir / "manifests" / namespace / slug / f"{version}.json"
