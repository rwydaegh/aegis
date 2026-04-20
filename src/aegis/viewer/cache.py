"""File-based cache for environment data (OSM, 3D Tiles)."""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class EnvironmentCache:
    """Simple file-based cache keyed by source, location, radius, and options."""

    def __init__(self, cache_dir: str | None = None):
        if cache_dir is None:
            base = os.environ.get(
                "AEGIS_CACHE_DIR",
                os.path.expanduser("~/.cache/aegis"),
            )
            cache_dir = base
        self._dir = Path(cache_dir) / "environments"
        self._enabled = True
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Cannot create environment cache at %s: %s. Caching disabled.", self._dir, e)
            self._enabled = False

    def _key(
        self,
        source: str,
        lat: float,
        lon: float,
        radius: float,
        options: dict,
    ) -> str:
        opts_str = json.dumps(options, sort_keys=True)
        opts_hash = hashlib.md5(opts_str.encode()).hexdigest()[:8]
        return f"{source}_{lat:.3f}_{lon:.3f}_{int(radius)}_{opts_hash}"

    def get(
        self,
        source: str,
        lat: float,
        lon: float,
        radius: float,
        options: dict,
    ) -> dict | None:
        if not self._enabled:
            return None
        path = self._dir / f"{self._key(source, lat, lon, radius, options)}.json"
        if not path.exists():
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Discarding corrupt cache entry %s: %s", path, e)
            self._remove_quiet(path)
            return None

    def put(
        self,
        source: str,
        lat: float,
        lon: float,
        radius: float,
        options: dict,
        data: dict,
        meta: dict,
    ) -> None:
        if not self._enabled:
            return
        path = self._dir / f"{self._key(source, lat, lon, radius, options)}.json"
        try:
            self._atomic_write_text(path, json.dumps({"data": data, "meta": meta}))
        except OSError as e:
            logger.warning("Failed to write cache entry %s: %s", path, e)

    def get_binary(
        self,
        source: str,
        lat: float,
        lon: float,
        radius: float,
        options: dict,
    ) -> tuple[bytes, dict] | None:
        """Return cached (binary_blob, meta) or None if not cached.

        Treats unreadable or partially written cache files as a miss so that
        a corrupted on-disk entry never surfaces as a 500 to the caller. The
        offending files are removed so the next request can refresh cleanly.
        """
        if not self._enabled:
            return None
        key = self._key(source, lat, lon, radius, options)
        bin_path = self._dir / f"{key}.bin"
        meta_path = self._dir / f"{key}.meta.json"
        if not bin_path.exists() or not meta_path.exists():
            return None
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            with open(bin_path, "rb") as f:
                blob = f.read()
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Discarding corrupt cache entry %s/%s: %s", bin_path, meta_path, e)
            self._remove_quiet(bin_path)
            self._remove_quiet(meta_path)
            return None
        return blob, meta

    def put_binary(
        self,
        source: str,
        lat: float,
        lon: float,
        radius: float,
        options: dict,
        blob: bytes,
        meta: dict,
    ) -> None:
        """Cache a binary blob with its metadata.

        Writes are atomic (temp file + rename) so an interrupted write does
        not leave a partial file that would later read as corrupt.
        """
        if not self._enabled:
            return
        key = self._key(source, lat, lon, radius, options)
        bin_path = self._dir / f"{key}.bin"
        meta_path = self._dir / f"{key}.meta.json"
        try:
            self._atomic_write_bytes(bin_path, blob)
            self._atomic_write_text(meta_path, json.dumps(meta))
        except OSError as e:
            logger.warning("Failed to write cache entry %s: %s", bin_path, e)
            self._remove_quiet(bin_path)
            self._remove_quiet(meta_path)

    @staticmethod
    def _atomic_write_bytes(path: Path, data: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)

    @staticmethod
    def _atomic_write_text(path: Path, data: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w") as f:
            f.write(data)
        os.replace(tmp, path)

    @staticmethod
    def _remove_quiet(path: Path) -> None:
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)

    def clear(self) -> None:
        if not self._enabled:
            return
        if self._dir.exists():
            shutil.rmtree(self._dir)
            self._dir.mkdir(parents=True, exist_ok=True)
