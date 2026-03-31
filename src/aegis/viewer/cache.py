"""File-based cache for environment data (OSM, 3D Tiles)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


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
        self._dir.mkdir(parents=True, exist_ok=True)

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
        path = self._dir / f"{self._key(source, lat, lon, radius, options)}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

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
        path = self._dir / f"{self._key(source, lat, lon, radius, options)}.json"
        with open(path, "w") as f:
            json.dump({"data": data, "meta": meta}, f)

    def get_binary(
        self,
        source: str,
        lat: float,
        lon: float,
        radius: float,
        options: dict,
    ) -> tuple[bytes, dict] | None:
        """Return cached (binary_blob, meta) or None if not cached."""
        key = self._key(source, lat, lon, radius, options)
        bin_path = self._dir / f"{key}.bin"
        meta_path = self._dir / f"{key}.meta.json"
        if not bin_path.exists() or not meta_path.exists():
            return None
        with open(meta_path) as f:
            meta = json.load(f)
        with open(bin_path, "rb") as f:
            blob = f.read()
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
        """Cache a binary blob with its metadata."""
        key = self._key(source, lat, lon, radius, options)
        bin_path = self._dir / f"{key}.bin"
        meta_path = self._dir / f"{key}.meta.json"
        with open(bin_path, "wb") as f:
            f.write(blob)
        with open(meta_path, "w") as f:
            json.dump(meta, f)

    def clear(self) -> None:
        if self._dir.exists():
            shutil.rmtree(self._dir)
            self._dir.mkdir(parents=True, exist_ok=True)
