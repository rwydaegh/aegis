"""Google Photorealistic 3D Tiles for one bounded region of interest.

Follows the external tilesets the Map Tiles API returns, prunes oriented
bounding boxes against the region, and writes leaf GLBs plus a ``manifest.json``
for the mesh builder. Authentication and session query values are used only for
requests and are never written to the manifest.

## The region is a cylinder, and that is not a detail

A ball centred on the ellipsoid is the obvious shape and it is wrong. Bounding
volumes are tested as a 3D distance from the centre, so at a site sitting ``h``
metres above the ellipsoid a ball of radius ``r`` reaches only
``sqrt(r^2 - h^2)`` horizontally at ground level, and nothing at all above
``z = r``.

At Ghent, with ``h`` near 50 m, a nominal 200 m ball still reaches 194 m
horizontally and the defect is invisible. Piazza del Duomo sits at ``h = 163 m``,
so the same request reached 116 m at street level, kept 233,997 triangles inside
a 200 m crop where a correct pull keeps 476,334, and truncated the cathedral at
226 m against its true 272 m. It cost a second pull of 691 requests to discover.

The cylinder reaches the full radius at every height in its band, so
``radius_m`` means what it says. :func:`ball_horizontal_reach_m` and
:func:`ball_ground_clearance_m` are kept because the defect is recorded against
the numbers they produce, and because a manifest written before the fix has to
be interpretable. :func:`check_reaches_terrain` is the guard: a site whose
terrain sits outside the cylinder's vertical band is refused with the height in
the message rather than silently returning no tiles.

Run from the ``semantic_twin`` directory::

    python download_inhouse_tiles.py \
      --lat 51.0550 --lon 3.7220 --radius-m 100 \
      --geometric-error-cutoff-m 0 --out /tmp/korenmarkt-tiles

Set ``GOOGLE_MAPS_API_KEY`` (preferred) or ``GOOGLE_API_KEY`` first. A zero
geometric-error cutoff means descend to the deepest available leaves. Positive
cutoffs stop at a tile whose geometric error is at or below the requested value.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..scene.enu import enu_rotation, llh_to_ecef
from .cache import ManifestCache, placement_key

API_ORIGIN = "https://tile.googleapis.com"
ROOT_TILESET_URL = f"{API_ORIGIN}/v1/3dtiles/root.json"

MAX_RADIUS_M = 2000.0

# Requests grow with the region's area, so the cap is what stops an oversized
# radius rather than a second guard. The r=200 m Korenmarkt traversal takes 351
# requests and the r=320 m Milan one 691, which a cap of 500 would have killed.
DEFAULT_MAX_REQUESTS = 2000
DEFAULT_MAX_BYTES = 1_000_000_000
READ_CHUNK_BYTES = 64 * 1024

# Half height of the cylinder about the ellipsoid, in metres. It only has to
# bracket the terrain, and no tile geometry exists off the terrain, so a
# generous band costs nothing. Sites above 3 km need this raised.
DEFAULT_VERTICAL_HALF_EXTENT_M = 3000.0

# How far above a site's pavement the band still has to reach. The tallest thing
# any site in this study puts in a crop is a Times Square tower at roughly 250 m,
# and Milan's spire is 109 m above its pavement.
BUILDING_HEADROOM_M = 300.0


@dataclass(frozen=True)
class TilesAcquireConfig:
    """Inputs for one bounded Google Photorealistic 3D Tiles acquisition."""

    lat: float
    lon: float
    radius_m: float
    geometric_error_cutoff_m: float
    out: pathlib.Path
    vertical_half_extent_m: float = DEFAULT_VERTICAL_HALF_EXTENT_M
    site_height_m: float | None = None
    max_requests: int = DEFAULT_MAX_REQUESTS
    max_bytes: int = DEFAULT_MAX_BYTES
    api_key: str | None = None


def google_api_key() -> str | None:
    """Return the preferred Google tile key, with the old fallback still supported."""
    return os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def api_key() -> str | None:
    """Compatibility alias for callers that used the old command helper."""
    return google_api_key()


class DownloadLimitExceeded(RuntimeError):
    """Raised before a configured request or byte limit can be exceeded."""


def ball_horizontal_reach_m(radius_m: float, ellipsoid_height_m: float) -> float:
    """How far a ball on the ellipsoid reaches sideways at a given height.

    ``sqrt(r^2 - h^2)``, and zero once the height passes the radius. This is the
    defect the cylinder replaced, kept because the Milan acquisition record is
    written in these numbers: at ``h = 162.94 m`` a 200 m ball reaches 116.0 m,
    a 258 m ball reaches 200.0 m, and 320 m was chosen to reach 275.4 m.
    """
    if radius_m <= abs(ellipsoid_height_m):
        return 0.0
    return math.sqrt(radius_m * radius_m - ellipsoid_height_m * ellipsoid_height_m)


def ball_ground_clearance_m(radius_m: float, ellipsoid_height_m: float, horizontal_m: float) -> float:
    """How far above the site's pavement a ball still reaches, at a given range.

    Negative when the ball does not reach the ground at that range at all, which
    is the case a table of horizontal reach alone hides. A 200 m ball at Milan
    clears 37.1 m at the centre and does not reach the ground by 130 m out.
    """
    if horizontal_m >= radius_m:
        return -math.inf
    return math.sqrt(radius_m * radius_m - horizontal_m * horizontal_m) - ellipsoid_height_m


def ball_radius_for_reach(horizontal_m: float, ellipsoid_height_m: float) -> float:
    """The smallest ball radius that reaches ``horizontal_m`` at a site's height.

    ``hypot(horizontal, h)``. At Milan that is 258 m for a 200 m reach, and the
    acquisition asked for 320 m so the band would still clear 114 m of air above
    the 160 m ring.
    """
    return math.hypot(horizontal_m, ellipsoid_height_m)


def check_reaches_terrain(
    half_height_m: float,
    site_ellipsoid_height_m: float,
    *,
    headroom_m: float = BUILDING_HEADROOM_M,
) -> None:
    """Refuse a region of interest that cannot hold the site's own ground.

    The cylinder is centred on the ellipsoid, not on the terrain, so its band
    has to be tall enough to bracket a site's ellipsoidal height plus whatever
    stands on it. Without this check a high site returns "no leaf tiles
    intersect", which reads as a bad radius and is nothing of the kind.

    The failure it guards against is real but not yet met here. Every site in
    this study sits under 250 m and the 3 km default clears them all. A site on
    an Andean or Tibetan plateau does not, and the message says so with the
    number rather than leaving it to be rediscovered the way Milan's was.
    """
    needed = abs(site_ellipsoid_height_m) + headroom_m
    if half_height_m < needed:
        raise ValueError(
            f"the region of interest spans {half_height_m:g} m either side of the ellipsoid, and this site sits at "
            f"{site_ellipsoid_height_m:g} m with {headroom_m:g} m of headroom above it, so its terrain is outside "
            f"the band. Raise the vertical half extent to at least {needed:g} m."
        )


class RegionOfInterest:
    """A vertical cylinder in ECEF: everything within ``radius_m`` of a site's up axis.

    Both predicates are conservative. They separate only when a supporting plane
    proves the volumes are apart, so a tile is never pruned when it might touch
    the region.
    """

    def __init__(
        self,
        lat_deg: float,
        lon_deg: float,
        radius_m: float,
        half_height_m: float,
        *,
        site_ellipsoid_height_m: float | None = None,
    ) -> None:
        if not math.isfinite(radius_m) or radius_m <= 0.0:
            raise ValueError("region radius must be finite and greater than zero")
        if not math.isfinite(half_height_m) or half_height_m <= 0.0:
            raise ValueError("region vertical half extent must be finite and greater than zero")
        if site_ellipsoid_height_m is not None:
            check_reaches_terrain(half_height_m, site_ellipsoid_height_m)
        self.radius_m = float(radius_m)
        self.half_height_m = float(half_height_m)
        self.center = llh_to_ecef(lat_deg, lon_deg, 0.0)
        self.up = enu_rotation(lat_deg, lon_deg)[2]

    def distance_to_point(self, point: np.ndarray) -> float:
        """Exact distance from an ECEF point to the cylinder, zero when inside."""
        delta = point - self.center
        vertical = float(np.dot(delta, self.up))
        horizontal = float(np.linalg.norm(delta - vertical * self.up))
        return math.hypot(max(0.0, horizontal - self.radius_m), max(0.0, abs(vertical) - self.half_height_m))

    def intersects_box(self, box: list[float], transform: np.ndarray | None = None) -> bool:
        """Return whether a 3D Tiles oriented box can touch the cylinder."""
        if len(box) != 12:
            raise ValueError("Tile boundingVolume.box must contain 12 numbers")
        values = np.asarray(box, dtype=np.float64)
        if not np.all(np.isfinite(values)):
            raise ValueError("Tile boundingVolume.box must contain finite numbers")

        world = np.eye(4, dtype=np.float64) if transform is None else transform
        box_center = (world @ np.append(values[:3], 1.0))[:3]
        linear = world[:3, :3]
        half_extents = [linear @ values[3:6], linear @ values[6:9], linear @ values[9:12]]
        delta = box_center - self.center

        vertical_reach = sum(abs(float(np.dot(self.up, axis))) for axis in half_extents)
        if abs(float(np.dot(self.up, delta))) > self.half_height_m + vertical_reach:
            return False

        # Horizontally the cylinder is a disc, so every direction perpendicular to
        # the up axis is a candidate separating normal. Testing the normals of the
        # box's own projected silhouette underestimates the true gap, which keeps
        # the test conservative: it can only fail to separate, never separate a box
        # that actually touches.
        for axis in half_extents:
            normal = np.cross(axis - float(np.dot(axis, self.up)) * self.up, self.up)
            length = float(np.linalg.norm(normal))
            if length <= 1e-9:
                continue
            normal = normal / length
            reach = sum(abs(float(np.dot(normal, other))) for other in half_extents)
            if abs(float(np.dot(normal, delta))) > self.radius_m + reach:
                return False
        return True

    def intersects_sphere(self, sphere: list[float], transform: np.ndarray) -> bool:
        """Return whether a 3D Tiles bounding sphere can touch the cylinder."""
        if len(sphere) != 4:
            raise ValueError("Tile boundingVolume.sphere must contain four numbers")
        values = np.asarray(sphere, dtype=np.float64)
        if not np.all(np.isfinite(values)) or values[3] < 0.0:
            raise ValueError("Tile boundingVolume.sphere must contain a non-negative finite radius")
        tile_center = (transform @ np.append(values[:3], 1.0))[:3]
        scale = max(float(np.linalg.norm(transform[:3, index])) for index in range(3))
        return bool(self.distance_to_point(tile_center) <= values[3] * scale)

    def intersects(self, bounding_volume: Any, transform: np.ndarray) -> bool:
        """Conservatively test a supported bounding volume against the region."""
        if not isinstance(bounding_volume, dict):
            return True
        if "box" in bounding_volume:
            return self.intersects_box(bounding_volume["box"], transform)
        if "sphere" in bounding_volume:
            return self.intersects_sphere(bounding_volume["sphere"], transform)
        # Region and extension bounding volumes are left unpruned to avoid false
        # negatives. Google's Photorealistic 3D Tiles hierarchy uses ECEF boxes.
        return True


def matrix_from_3d_tiles(values: Any) -> np.ndarray:
    """Decode a column-major 3D Tiles transform, or return identity."""
    if values is None:
        return np.eye(4, dtype=np.float64)
    transform = np.asarray(values, dtype=np.float64)
    if transform.shape != (16,) or not np.all(np.isfinite(transform)):
        raise ValueError("Tile transform must contain 16 finite numbers")
    return transform.reshape((4, 4), order="F")


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
            raise RuntimeError(f"Google tile request failed with HTTP {exc.code}") from exc
        except OSError as exc:
            raise RuntimeError("Google tile request failed") from exc

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


class GoogleTilesDownloader:
    """Traverse and download one bounded Photorealistic 3D Tiles region."""

    def __init__(
        self,
        api_key: str,
        *,
        lat: float,
        lon: float,
        radius_m: float,
        geometric_error_cutoff_m: float,
        out_dir: pathlib.Path,
        vertical_half_extent_m: float = DEFAULT_VERTICAL_HALF_EXTENT_M,
        site_ellipsoid_height_m: float | None = None,
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
        self.vertical_half_extent_m = vertical_half_extent_m
        self.site_ellipsoid_height_m = site_ellipsoid_height_m
        self.roi = RegionOfInterest(
            lat,
            lon,
            radius_m,
            vertical_half_extent_m,
            site_ellipsoid_height_m=site_ellipsoid_height_m,
        )
        self.center_ecef = self.roi.center
        self.http = http or BoundedHttpClient(max_requests, max_bytes)
        self.max_requests = self.http.max_requests
        self.max_bytes = self.http.max_bytes
        self.session_token: str | None = None
        self.tiles: list[dict[str, Any]] = []
        self._active_tilesets: set[str] = set()
        self._tileset_cache: dict[str, dict[str, Any]] = {}
        self._downloaded_keys: set[str] = set()
        self._asked_addresses: set[str] = set()
        self._attributions: set[str] = set()
        self._cache = ManifestCache(self.out_dir / "manifest.json")

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
        """One tileset JSON, remembered for the rest of this traversal.

        Keyed by address, and that is not a second cache rule. It never touches
        disk and never outlives the run: it is a memo saying "this traversal has
        already asked for this hierarchy node", which is a statement about the
        request and not about the content. Everything that is kept is keyed by
        placement.
        """
        request_url = self._request_url(uri, base_url)
        cache_key = sanitized_uri(request_url)
        if cache_key not in self._tileset_cache:
            self._tileset_cache[cache_key] = self.http.get_json(request_url)
        self._collect_attribution(self._tileset_cache[cache_key])
        return self._tileset_cache[cache_key], request_url

    def _collect_attribution(self, tileset: dict[str, Any]) -> None:
        """Remember who owns the imagery this tileset serves.

        Google publishes the data providers in ``asset.copyright`` of every
        tileset JSON, semicolon separated, and the terms of the 3D Tiles API
        require them to be shown wherever the imagery is. Which providers appear
        depends on where you looked, so this has to be harvested during the
        traversal rather than written down once. A site whose imagery came from
        Airbus and one whose imagery came from Maxar do not carry the same
        notice, and a paper that prints the wrong one is not complying.
        """
        asset = tileset.get("asset")
        if not isinstance(asset, dict):
            return
        for name in str(asset.get("copyright", "")).split(";"):
            if name.strip():
                self._attributions.add(name.strip())

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

    def _download_glb(self, uri: str, base_url: str, geometric_error_m: float, tile_key: str) -> None:
        """Fetch one leaf, or keep the one a previous run already paid for.

        Two guards, and only one of them is a cache. The placement key decides
        what is *kept*: it is written to the manifest, it is what a later run
        matches on, and it is the whole rule for anything on disk. The address
        set decides what is *asked for* inside this one traversal, the same memo
        the tileset loader keeps. It is never persisted, so a re-run cannot
        inherit it, and the address is worthless across runs anyway because
        Google serves these payloads at per session paths.
        """
        if tile_key in self._downloaded_keys:
            return
        request_url = self._request_url(uri, base_url)
        address = sanitized_uri(request_url)
        if address in self._asked_addresses:
            return
        self._asked_addresses.add(address)
        reused = self._cache.claim(tile_key)
        if reused is not None:
            filename, size = reused.file, reused.size
            print(f"[kept] {filename} ge={geometric_error_m:.3f} m, {size / 1e6:.2f} MB", flush=True)
        else:
            filename = self._cache.free_name(len(self.tiles))
            size = self.http.download(request_url, self.out_dir / filename)
            print(f"[tile] {filename} ge={geometric_error_m:.3f} m, {size / 1e6:.2f} MB", flush=True)
        self._downloaded_keys.add(tile_key)
        self.tiles.append(
            {
                "file": filename,
                "uri": sanitized_uri(uri),
                "tile_key": tile_key,
                "geometric_error": geometric_error_m,
                "size": size,
            }
        )

    def _walk_tile(self, tile: dict[str, Any], base_url: str, parent_transform: np.ndarray) -> None:
        transform = parent_transform @ matrix_from_3d_tiles(tile.get("transform"))
        if not self.roi.intersects(tile.get("boundingVolume"), transform):
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

        for order, uri in enumerate(glb_uris):
            self._download_glb(
                uri,
                base_url,
                geometric_error_m,
                placement_key(tile.get("boundingVolume"), transform, geometric_error_m, order),
            )

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
            raise RuntimeError(
                f"No GLB leaf tiles intersect the region: {self.radius_m:g} m horizontally about "
                f"{self.lat:g}, {self.lon:g}, within {self.vertical_half_extent_m:g} m of the ellipsoid. "
                "A high site whose terrain sits outside that band gives exactly this, so pass its "
                "ellipsoidal height and the region will say so instead."
            )

        manifest = {
            "format_version": 1,
            "generator": "semantic_twin/acquire/tiles.py",
            "lat": self.lat,
            "lon": self.lon,
            "radius": self.radius_m,
            "cutoff": self.cutoff_m,
            "roi_shape": "vertical cylinder about the site up axis, radius is horizontal",
            "roi_vertical_half_extent_m": self.vertical_half_extent_m,
            "site_ellipsoid_height_m": self.site_ellipsoid_height_m,
            "center_ecef": self.center_ecef.tolist(),
            "limits": {"max_requests": self.max_requests, "max_bytes": self.max_bytes},
            "tiles": self.tiles,
            "attributions": sorted(self._attributions),
            "reused_from_disk": self._cache.reused,
            "requests": self.http.request_count,
            "total_bytes": self.http.total_bytes,
        }
        manifest_path = self.out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._write_attribution_file()
        return manifest

    def _write_attribution_file(self) -> None:
        """The notice, beside the tiles, in the form a figure caption can copy."""
        names = sorted(self._attributions)
        if not names:
            return
        line = ", ".join(names)
        (self.out_dir / "ATTRIBUTION.txt").write_text(
            "The 3D imagery in this directory came from the Google Photorealistic 3D Tiles API.\n"
            "The API terms require these providers to be shown wherever the imagery is:\n\n"
            f"    {line}\n\n"
            "For a figure, the caption reads:\n\n"
            f"    Imagery: {line}\n",
            encoding="utf-8",
        )


def acquire_tiles(config: TilesAcquireConfig) -> dict[str, Any]:
    """Download one configured region and return its persisted manifest."""
    key = config.api_key or google_api_key()
    if not key:
        raise ValueError("An API key is required")
    downloader = GoogleTilesDownloader(
        key,
        lat=config.lat,
        lon=config.lon,
        radius_m=config.radius_m,
        geometric_error_cutoff_m=config.geometric_error_cutoff_m,
        out_dir=config.out,
        vertical_half_extent_m=config.vertical_half_extent_m,
        site_ellipsoid_height_m=config.site_height_m,
        max_requests=config.max_requests,
        max_bytes=config.max_bytes,
    )
    return downloader.run()
