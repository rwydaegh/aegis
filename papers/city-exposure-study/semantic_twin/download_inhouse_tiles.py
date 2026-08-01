"""Download official Inhouse Photorealistic 3D Tiles for a small circular ROI.

The downloader follows the external tilesets returned by the Map Tiles API,
prunes oriented bounding boxes against an ECEF sphere, and writes leaf GLBs and
``manifest.json`` for ``build_inhouse_mesh.py``. Authentication and session query
values are used only for requests and are never written to the manifest.

Run from the ``semantic_twin`` directory::

    python download_inhouse_tiles.py \
      --lat 51.0550 --lon 3.7220 --radius-m 100 \
      --geometric-error-cutoff-m 0 --out /tmp/korenmarkt-inhouse-tiles

Set ``GOOGLE_MAPS_API_KEY`` (preferred) or ``GOOGLE_API_KEY`` first. A zero
geometric-error cutoff means descend to the deepest available leaves. Positive
cutoffs stop at a tile whose geometric error is at or below the requested value.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any

import numpy as np

API_ORIGIN = "https://tile.googleapis.com"
ROOT_TILESET_URL = f"{API_ORIGIN}/v1/3dtiles/root.json"
WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3

MAX_RADIUS_M = 2000.0
DEFAULT_MAX_REQUESTS = 500
DEFAULT_MAX_BYTES = 1_000_000_000
READ_CHUNK_BYTES = 64 * 1024


class DownloadLimitExceeded(RuntimeError):
    """Raised before a configured request or byte limit can be exceeded."""


def llh_to_ecef(lat_deg: float, lon_deg: float, height_m: float = 0.0) -> np.ndarray:
    """Convert WGS84 latitude, longitude and ellipsoid height to ECEF metres."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    prime_vertical_radius = WGS84_A / math.sqrt(1.0 - WGS84_E2 * math.sin(lat) ** 2)
    return np.array(
        [
            (prime_vertical_radius + height_m) * math.cos(lat) * math.cos(lon),
            (prime_vertical_radius + height_m) * math.cos(lat) * math.sin(lon),
            (prime_vertical_radius * (1.0 - WGS84_E2) + height_m) * math.sin(lat),
        ],
        dtype=np.float64,
    )


def matrix_from_3d_tiles(values: Any) -> np.ndarray:
    """Decode a column-major 3D Tiles transform, or return identity."""
    if values is None:
        return np.eye(4, dtype=np.float64)
    transform = np.asarray(values, dtype=np.float64)
    if transform.shape != (16,) or not np.all(np.isfinite(transform)):
        raise ValueError("Tile transform must contain 16 finite numbers")
    return transform.reshape((4, 4), order="F")


def obb_intersects_sphere(
    box: list[float],
    center: np.ndarray,
    radius_m: float,
    transform: np.ndarray | None = None,
) -> bool:
    """Return whether a 3D Tiles oriented box intersects an ECEF sphere."""
    if len(box) != 12:
        raise ValueError("Tile boundingVolume.box must contain 12 numbers")
    values = np.asarray(box, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("Tile boundingVolume.box must contain finite numbers")

    world = np.eye(4, dtype=np.float64) if transform is None else transform
    local_center = np.append(values[:3], 1.0)
    box_center = (world @ local_center)[:3]
    linear = world[:3, :3]
    axes = [linear @ values[3:6], linear @ values[6:9], linear @ values[9:12]]

    delta = center - box_center
    closest = box_center.copy()
    for axis in axes:
        half_length = float(np.linalg.norm(axis))
        if half_length <= 1e-12:
            continue
        direction = axis / half_length
        distance = float(np.clip(np.dot(delta, direction), -half_length, half_length))
        closest += distance * direction
    return bool(np.linalg.norm(center - closest) <= radius_m)


def sphere_intersects_sphere(sphere: list[float], center: np.ndarray, radius_m: float, transform: np.ndarray) -> bool:
    """Return whether a transformed 3D Tiles bounding sphere intersects the ROI."""
    if len(sphere) != 4:
        raise ValueError("Tile boundingVolume.sphere must contain four numbers")
    values = np.asarray(sphere, dtype=np.float64)
    if not np.all(np.isfinite(values)) or values[3] < 0.0:
        raise ValueError("Tile boundingVolume.sphere must contain a non-negative finite radius")
    tile_center = (transform @ np.append(values[:3], 1.0))[:3]
    scale = max(float(np.linalg.norm(transform[:3, index])) for index in range(3))
    return bool(np.linalg.norm(center - tile_center) <= radius_m + values[3] * scale)


def bounding_volume_intersects_roi(
    bounding_volume: Any, center: np.ndarray, radius_m: float, transform: np.ndarray
) -> bool:
    """Conservatively test a supported bounding volume against the ROI."""
    if not isinstance(bounding_volume, dict):
        return True
    if "box" in bounding_volume:
        return obb_intersects_sphere(bounding_volume["box"], center, radius_m, transform)
    if "sphere" in bounding_volume:
        return sphere_intersects_sphere(bounding_volume["sphere"], center, radius_m, transform)
    # Region and extension bounding volumes are left unpruned to avoid false
    # negatives. Inhouse's Photorealistic 3D Tiles hierarchy uses ECEF boxes.
    return True


def sanitized_uri(uri: str) -> str:
    """Remove every query value and fragment before persisting a tile URI."""
    parsed = urllib.parse.urlsplit(uri)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _content_uris(tile: dict[str, Any]) -> list[str]:
    contents: list[Any] = []
    if "content" in tile:
        contents.append(tile["content"])
    if isinstance(tile.get("contents"), list):
        contents.extend(tile["contents"])
    uris: list[str] = []
    for content in contents:
        if not isinstance(content, dict):
            continue
        uri = content.get("uri", content.get("url"))
        if isinstance(uri, str) and uri:
            uris.append(uri)
    return uris


def _uri_kind(uri: str) -> str:
    path = urllib.parse.urlsplit(uri).path.lower()
    if path.endswith(".json"):
        return "tileset"
    if path.endswith(".glb"):
        return "glb"
    return "other"


class BoundedHttpClient:
    """Minimal HTTP reader that enforces request and response-byte limits."""

    def __init__(
        self,
        max_requests: int,
        max_bytes: int,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        timeout_s: float = 60.0,
    ) -> None:
        if max_requests <= 0 or max_bytes <= 0:
            raise ValueError("Request and byte caps must be greater than zero")
        self.max_requests = max_requests
        self.max_bytes = max_bytes
        self.opener = opener
        self.timeout_s = timeout_s
        self.request_count = 0
        self.total_bytes = 0

    def _chunks(self, url: str) -> Iterator[bytes]:
        if self.request_count >= self.max_requests:
            raise DownloadLimitExceeded(f"request cap reached ({self.max_requests})")
        if self.total_bytes >= self.max_bytes:
            raise DownloadLimitExceeded(f"byte cap reached ({self.max_bytes} bytes)")

        request = urllib.request.Request(url, headers={"User-Agent": "AEGIS-semantic-twin/1"})
        self.request_count += 1
        try:
            response = self.opener(request, timeout=self.timeout_s)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Inhouse tile request failed with HTTP {exc.code}") from exc
        except OSError as exc:
            raise RuntimeError("Inhouse tile request failed") from exc

        with response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    announced_bytes = int(content_length)
                except ValueError:
                    announced_bytes = -1
                if announced_bytes > self.max_bytes - self.total_bytes:
                    raise DownloadLimitExceeded(f"response would exceed byte cap ({self.max_bytes} bytes)")

            while True:
                remaining = self.max_bytes - self.total_bytes
                chunk = response.read(min(READ_CHUNK_BYTES, remaining + 1))
                if not chunk:
                    return
                if len(chunk) > remaining:
                    raise DownloadLimitExceeded(f"byte cap reached ({self.max_bytes} bytes)")
                self.total_bytes += len(chunk)
                yield chunk

    def get_json(self, url: str) -> dict[str, Any]:
        body = b"".join(self._chunks(url))
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError("Tileset response must be a JSON object")
        return value

    def download(self, url: str, destination: pathlib.Path) -> int:
        partial = destination.with_suffix(destination.suffix + ".part")
        size = 0
        try:
            with partial.open("wb") as output:
                for chunk in self._chunks(url):
                    output.write(chunk)
                    size += len(chunk)
            partial.replace(destination)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        return size


class InhouseTilesDownloader:
    """Traverse and download one bounded Photorealistic 3D Tiles ROI."""

    def __init__(
        self,
        api_key: str,
        *,
        lat: float,
        lon: float,
        radius_m: float,
        geometric_error_cutoff_m: float,
        out_dir: pathlib.Path,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        max_bytes: int = DEFAULT_MAX_BYTES,
        http: BoundedHttpClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("An API key is required")
        if not math.isfinite(lat) or not -90.0 <= lat <= 90.0:
            raise ValueError("Latitude must be finite and in [-90, 90]")
        if not math.isfinite(lon) or not -180.0 <= lon <= 180.0:
            raise ValueError("Longitude must be finite and in [-180, 180]")
        if not math.isfinite(radius_m) or not 0.0 < radius_m <= MAX_RADIUS_M:
            raise ValueError(f"Radius must be finite and in (0, {MAX_RADIUS_M:g}] metres")
        if not math.isfinite(geometric_error_cutoff_m) or geometric_error_cutoff_m < 0.0:
            raise ValueError("Geometric-error cutoff must be finite and non-negative")

        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.radius_m = radius_m
        self.cutoff_m = geometric_error_cutoff_m
        self.out_dir = out_dir
        self.center_ecef = llh_to_ecef(lat, lon)
        self.http = http or BoundedHttpClient(max_requests, max_bytes)
        self.max_requests = self.http.max_requests
        self.max_bytes = self.http.max_bytes
        self.session_token: str | None = None
        self.tiles: list[dict[str, Any]] = []
        self._active_tilesets: set[str] = set()
        self._tileset_cache: dict[str, dict[str, Any]] = {}
        self._downloaded_payloads: set[str] = set()

    def _remember_session(self, uri: str) -> None:
        for name, value in urllib.parse.parse_qsl(urllib.parse.urlsplit(uri).query, keep_blank_values=True):
            if name.lower() == "session" and value:
                self.session_token = value

    def _request_url(self, uri: str, base_url: str) -> str:
        self._remember_session(uri)
        resolved = urllib.parse.urljoin(base_url, uri)
        parsed = urllib.parse.urlsplit(resolved)
        if parsed.scheme != "https" or parsed.netloc != urllib.parse.urlsplit(API_ORIGIN).netloc:
            raise ValueError("Refusing to send the API key outside tile.googleapis.com")

        query = [
            (name, value)
            for name, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            if name.lower() not in {"key", "session"}
        ]
        if self.session_token is not None:
            query.append(("session", self.session_token))
        query.append(("key", self.api_key))
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), ""))

    def _load_tileset(self, uri: str, base_url: str) -> tuple[dict[str, Any], str]:
        request_url = self._request_url(uri, base_url)
        cache_key = sanitized_uri(request_url)
        if cache_key not in self._tileset_cache:
            self._tileset_cache[cache_key] = self.http.get_json(request_url)
        return self._tileset_cache[cache_key], request_url

    def _walk_external_tileset(self, uri: str, base_url: str, parent_transform: np.ndarray) -> None:
        tileset, request_url = self._load_tileset(uri, base_url)
        identity = sanitized_uri(request_url)
        if identity in self._active_tilesets:
            raise ValueError(f"External tileset cycle detected at {identity}")
        root = tileset.get("root")
        if not isinstance(root, dict):
            raise ValueError(f"Tileset has no object root: {identity}")
        self._active_tilesets.add(identity)
        try:
            self._walk_tile(root, request_url, parent_transform)
        finally:
            self._active_tilesets.remove(identity)

    def _download_glb(self, uri: str, base_url: str, geometric_error_m: float) -> None:
        request_url = self._request_url(uri, base_url)
        identity = sanitized_uri(request_url)
        if identity in self._downloaded_payloads:
            return
        filename = f"tile_{len(self.tiles):04d}.glb"
        size = self.http.download(request_url, self.out_dir / filename)
        self._downloaded_payloads.add(identity)
        self.tiles.append(
            {
                "file": filename,
                "uri": sanitized_uri(uri),
                "geometric_error": geometric_error_m,
                "size": size,
            }
        )
        print(f"[tile] {filename} ge={geometric_error_m:.3f} m, {size / 1e6:.2f} MB", flush=True)

    def _walk_tile(self, tile: dict[str, Any], base_url: str, parent_transform: np.ndarray) -> None:
        transform = parent_transform @ matrix_from_3d_tiles(tile.get("transform"))
        if not bounding_volume_intersects_roi(tile.get("boundingVolume"), self.center_ecef, self.radius_m, transform):
            return

        try:
            geometric_error_m = float(tile.get("geometricError", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError("Tile geometricError must be numeric") from exc
        if not math.isfinite(geometric_error_m) or geometric_error_m < 0.0:
            raise ValueError("Tile geometricError must be finite and non-negative")

        uris = _content_uris(tile)
        for uri in uris:
            self._remember_session(uri)
        external_uris = [uri for uri in uris if _uri_kind(uri) == "tileset"]
        glb_uris = [uri for uri in uris if _uri_kind(uri) == "glb"]
        children = [child for child in tile.get("children", []) if isinstance(child, dict)]
        has_descendants = bool(external_uris or children)

        # Cutoff zero explicitly means leaves, even when a parent reports zero
        # geometric error. External tilesets are hierarchy, not payloads.
        refine = has_descendants and (self.cutoff_m == 0.0 or geometric_error_m > self.cutoff_m or not glb_uris)
        if refine:
            for uri in external_uris:
                self._walk_external_tileset(uri, base_url, transform)
            for child in children:
                self._walk_tile(child, base_url, transform)
            return

        for uri in glb_uris:
            self._download_glb(uri, base_url, geometric_error_m)

        # Unknown or absent payload formats should not prevent reaching known
        # GLBs lower in the hierarchy.
        if not glb_uris:
            for uri in external_uris:
                self._walk_external_tileset(uri, base_url, transform)
            for child in children:
                self._walk_tile(child, base_url, transform)

    def run(self) -> dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        root_tileset, root_url = self._load_tileset(ROOT_TILESET_URL, API_ORIGIN)
        root = root_tileset.get("root")
        if not isinstance(root, dict):
            raise ValueError("Root tileset has no object root")
        self._walk_tile(root, root_url, np.eye(4, dtype=np.float64))
        if not self.tiles:
            raise RuntimeError("No GLB leaf tiles intersect the requested ROI")

        manifest = {
            "format_version": 1,
            "generator": "semantic_twin/download_inhouse_tiles.py",
            "lat": self.lat,
            "lon": self.lon,
            "radius": self.radius_m,
            "cutoff": self.cutoff_m,
            "center_ecef": self.center_ecef.tolist(),
            "limits": {"max_requests": self.max_requests, "max_bytes": self.max_bytes},
            "tiles": self.tiles,
            "requests": self.http.request_count,
            "total_bytes": self.http.total_bytes,
        }
        manifest_path = self.out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest


def positive_int(value: str) -> int:
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise argparse.ArgumentTypeError("must be finite")
    return result


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", type=finite_float, required=True, help="ROI centre latitude in WGS84 degrees")
    parser.add_argument("--lon", type=finite_float, required=True, help="ROI centre longitude in WGS84 degrees")
    parser.add_argument(
        "--radius-m",
        "--radius",
        dest="radius_m",
        type=finite_float,
        required=True,
        help=f"Circular ROI radius in metres, at most {MAX_RADIUS_M:g}",
    )
    parser.add_argument(
        "--geometric-error-cutoff-m",
        "--cutoff",
        dest="geometric_error_cutoff_m",
        type=finite_float,
        default=0.0,
        help="Stop at this geometric error in metres. Zero downloads deepest leaves (default: 0)",
    )
    parser.add_argument(
        "--max-requests",
        type=positive_int,
        default=DEFAULT_MAX_REQUESTS,
        help=f"Hard HTTP request cap (default: {DEFAULT_MAX_REQUESTS})",
    )
    parser.add_argument(
        "--max-bytes",
        type=positive_int,
        default=DEFAULT_MAX_BYTES,
        help=f"Hard aggregate response-byte cap (default: {DEFAULT_MAX_BYTES})",
    )
    parser.add_argument("--out", type=pathlib.Path, required=True, help="Output directory for GLBs and manifest.json")
    return parser.parse_args(argv)


def _api_key() -> str | None:
    return os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    api_key = _api_key()
    if not api_key:
        print("Set GOOGLE_MAPS_API_KEY or GOOGLE_API_KEY", file=sys.stderr)
        return 2
    try:
        downloader = InhouseTilesDownloader(
            api_key,
            lat=args.lat,
            lon=args.lon,
            radius_m=args.radius_m,
            geometric_error_cutoff_m=args.geometric_error_cutoff_m,
            out_dir=args.out,
            max_requests=args.max_requests,
            max_bytes=args.max_bytes,
        )
        manifest = downloader.run()
    except (DownloadLimitExceeded, RuntimeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"[done] {len(manifest['tiles'])} tiles, {manifest['requests']} requests, "
        f"{manifest['total_bytes'] / 1e6:.1f} MB -> {args.out / 'manifest.json'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
