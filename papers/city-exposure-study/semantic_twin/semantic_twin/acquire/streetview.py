"""Google Street View panoramas, one camera at a time.

Acquires one full resolution equirectangular panorama and its camera pose
through the official Map Tiles API, stitching the tile grid the API serves.
This is the provider behind every single camera site in the study and behind
the nine sites whose stations were fetched in a cohort. Korenmarkt's walk comes
from Mapillary instead. :mod:`semantic_twin.acquire.source` says which site uses
which and why the two are not interchangeable.

Run from ``semantic_twin`` with the AEGIS virtual environment::

    ../../../.venv/bin/python -m semantic_twin.cli.streetview \
      --scene config/korenmarkt.json --zoom 5

Zoom 5 is the native panorama resolution for a car capture, usually 13k or 16k
pixels wide. Zoom 4 is useful for fast iteration and is the top of the pyramid
for a user contributed photosphere. Tile downloads are resumable and the output
folder records the complete metadata and ENU pose the projection pipeline reads.
"""

from __future__ import annotations

import json
import math
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image

from .. import paths, sites
from ..scene.camera_ground import camera_altitude
from ..scene.enu import EnuFrame
from ..scene.site_config import google_api_key
from .source import PanoramaPose, load_support_mesh

CREATE_SESSION = "https://tile.googleapis.com/v1/createSession"
METADATA = "https://tile.googleapis.com/v1/streetview/metadata"
TILE = "https://tile.googleapis.com/v1/streetview/tiles"


def streetview_orientation_source(metadata: dict[str, Any]) -> str:
    """Say whether a Street View panorama has measured orientation or a default.

    ``tilt = 90`` with ``roll = 0`` exactly is the tell for a capture with no
    orientation metadata at all, which is a different claim from a levelled
    camera. Three of the five sites screened for this study reported exactly
    those values and are user photospheres with no pose solution behind them.
    """
    if "tilt" not in metadata and "roll" not in metadata:
        return "absent: metadata carries neither tilt nor roll, camera assumed level"
    tilt = float(metadata.get("tilt", 90.0))
    roll = float(metadata.get("roll", 0.0))
    if tilt == 90.0 and roll == 0.0:
        return "degenerate: tilt is exactly 90 and roll exactly 0, which marks a capture with no orientation solution"
    return "map tiles streetview metadata tilt and roll"


class StreetViewTiles:
    """Small, retrying client for one Map Tiles Street View session."""

    def __init__(
        self,
        api_key: str,
        *,
        tries: int = 4,
        throttle_backoff_s: float = 20.0,
        server_backoff_s: float = 1.5,
        timeout_s: float = 60.0,
        region: str | None = "BE",
        opener: Any | None = None,
    ) -> None:
        self.api_key = api_key
        self.tries = tries
        self.throttle_backoff_s = throttle_backoff_s
        self.server_backoff_s = server_backoff_s
        self.timeout_s = timeout_s
        self.region = region
        self.opener = opener
        self.requests = 0
        self.session: dict[str, Any] | None = None

    def _read(
        self,
        request: str | urllib.request.Request,
        *,
        missing_ok: bool = False,
        retry: bool = True,
    ) -> bytes:
        """Fetch one resource, retrying on server errors and on throttling.

        A 4xx is a statement that the request itself is wrong and retrying it
        will not help, so those raise immediately. **429 is the exception**: it
        says the request was fine and arrived too soon. One zoom-5 panorama is
        338 tiles, so a multi site acquisition will meet a rate limit at some
        point, and raising on the first one loses the whole run rather than
        pausing through it. Back off longer than for a 5xx, since a throttle
        window is seconds to minutes rather than milliseconds.
        """
        last: Exception | None = None
        attempts = self.tries if retry else 1
        for attempt in range(attempts):
            self.requests += 1
            try:
                if self.opener is None:
                    response = urllib.request.urlopen(request, timeout=self.timeout_s)
                else:
                    response = self.opener.open(request, timeout=self.timeout_s)
                with response:
                    return response.read()
            except (OSError, urllib.error.HTTPError) as exc:
                last = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code == 404 and missing_ok:
                    return b"{}"
                if not retry:
                    raise
                throttled = isinstance(exc, urllib.error.HTTPError) and exc.code == 429
                if isinstance(exc, urllib.error.HTTPError) and exc.code < 500 and not throttled:
                    detail = exc.read().decode("utf-8", errors="replace")[:1000]
                    raise RuntimeError(f"Street View HTTP {exc.code}: {detail}") from exc
                if throttled:
                    time.sleep(self.throttle_backoff_s * (attempt + 1))
                else:
                    time.sleep(self.server_backoff_s * (attempt + 1))
        if isinstance(last, urllib.error.HTTPError) and last.code == 429:
            raise RuntimeError(
                f"Street View still throttled after {attempts} attempts. A daily quota, as opposed to a "
                "burst limit, does not clear by waiting and has to be raised in the console."
            ) from last
        raise RuntimeError(f"Street View request failed after {attempts} attempts") from last

    def create_session(self, *, retry: bool = True) -> dict[str, Any]:
        payload = {"mapType": "streetview", "language": "en-US"}
        if self.region is not None:
            payload["region"] = self.region
        body = json.dumps(payload).encode()
        url = f"{CREATE_SESSION}?{urllib.parse.urlencode({'key': self.api_key})}"
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        self.session = json.loads(self._read(request, retry=retry))
        return self.session

    @property
    def token(self) -> str:
        if self.session is None:
            self.create_session()
        assert self.session is not None
        return str(self.session["session"])

    def metadata(
        self,
        *,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float = 50.0,
        pano_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str | float] = {"session": self.token, "key": self.api_key}
        if pano_id:
            params["panoId"] = pano_id
        elif lat is not None and lon is not None:
            params.update({"lat": lat, "lng": lon, "radius": int(round(radius_m))})
        else:
            raise ValueError("metadata needs pano_id or both lat and lon")
        return json.loads(self._read(f"{METADATA}?{urllib.parse.urlencode(params)}", missing_ok=True))

    def by_pano_id(self, pano_id: str) -> dict[str, Any]:
        """Return metadata for one panorama, as required by screening."""
        return self.metadata(pano_id=pano_id)

    def by_location(self, lat: float, lon: float, radius_m: float) -> dict[str, Any]:
        """Return metadata near one point, as required by screening."""
        return self.metadata(lat=lat, lon=lon, radius_m=radius_m)

    def tile_bytes(self, pano_id: str, zoom: int, x: int, y: int) -> bytes:
        params = urllib.parse.urlencode({"session": self.token, "key": self.api_key, "panoId": pano_id})
        return self._read(f"{TILE}/{zoom}/{x}/{y}?{params}")


def native_zoom(metadata: dict[str, Any]) -> int:
    """Return the zoom index at which this panorama is served at native size.

    Five is right for a Street View car capture, which is 13k or 16k pixels wide
    and therefore 26 or 32 tiles across, but it is not a property of the API. A
    user contributed photosphere is 8192 wide, 16 tiles across, and its pyramid
    stops one level earlier: every ``/5/x/y`` request against one returns 404
    while ``/4/x/y`` returns the full 16 by 8 grid. Times Square has no car
    coverage at all, so every panorama there is such a photosphere and a
    constant alone loses the site.

    The pyramid halves each level and the top level is whatever holds the native
    image, so the index is the number of halvings from one tile to the tile grid
    the metadata implies.
    """
    tile_width = int(metadata.get("tileWidth") or 512)
    tiles_across = max(1, math.ceil(int(metadata["imageWidth"]) / tile_width))
    return max(0, math.ceil(math.log2(tiles_across)))


def zoom_dimensions(metadata: dict[str, Any], zoom: int) -> tuple[int, int]:
    """Return the useful equirectangular dimensions at a Street View zoom level."""
    top = native_zoom(metadata)
    if not 0 <= zoom <= top:
        raise ValueError(f"zoom must be in [0, {top}] for this panorama")
    divisor = 2 ** (top - zoom)
    return (
        math.ceil(int(metadata["imageWidth"]) / divisor),
        math.ceil(int(metadata["imageHeight"]) / divisor),
    )


def stitch_tiles(
    tile_paths: dict[tuple[int, int], pathlib.Path],
    *,
    width: int,
    height: int,
    tile_width: int,
    tile_height: int,
) -> Image.Image:
    """Stitch a complete tile grid and crop the provider's padded edge tiles."""
    canvas = Image.new(
        "RGB", (math.ceil(width / tile_width) * tile_width, math.ceil(height / tile_height) * tile_height)
    )
    for (x, y), path in tile_paths.items():
        with Image.open(path) as tile:
            canvas.paste(tile.convert("RGB"), (x * tile_width, y * tile_height))
    return canvas.crop((0, 0, width, height))


def pose_from_metadata(
    metadata: dict[str, Any],
    scene: dict[str, Any],
    *,
    support_mesh: tuple[np.ndarray, np.ndarray] | None = None,
) -> PanoramaPose:
    """Initial pose for one Street View panorama.

    When ``support_mesh`` is supplied the altitude is cast for this camera's own
    easting and northing instead of inheriting the scene wide
    ``camera_ground_z_m``, which is only correct for the one camera it was
    measured under.
    """
    origin = scene["enu_origin"]
    frame = EnuFrame(
        float(origin["lat"]),
        float(origin["lon"]),
        float(origin.get("ellipsoid_height_m", 0.0)),
    )
    xy = frame.to_enu(float(metadata["lat"]), float(metadata["lng"]))[:2]
    camera_height_m = float(scene.get("camera_height_m", 2.5))
    z, provenance = camera_altitude(scene, float(xy[0]), float(xy[1]), support_mesh=support_mesh)
    return PanoramaPose(
        position_enu_m=(float(xy[0]), float(xy[1]), float(z)),
        position_wgs84=(float(metadata["lat"]), float(metadata["lng"])),
        heading_deg=float(metadata.get("heading", 0.0)),
        tilt_deg=float(metadata.get("tilt", 90.0)),
        roll_deg=float(metadata.get("roll", 0.0)),
        camera_height_m=camera_height_m,
        altitude_source=str(provenance["altitude_source"]),
        orientation_source=streetview_orientation_source(metadata),
        provenance=provenance,
    )


class GoogleStreetView:
    """The Street View arm of :class:`~semantic_twin.acquire.source.PanoramaSource`."""

    provider = sites.GOOGLE_STREETVIEW

    def image_id(self, metadata: dict[str, Any]) -> str:
        return str(metadata["panoId"])

    def orientation_source(self, metadata: dict[str, Any]) -> str:
        return streetview_orientation_source(metadata)

    def pose(
        self,
        metadata: dict[str, Any],
        scene: dict[str, Any],
        *,
        support_mesh: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> PanoramaPose:
        return pose_from_metadata(metadata, scene, support_mesh=support_mesh)


def download_panorama(
    client: StreetViewTiles,
    metadata: dict[str, Any],
    out_dir: pathlib.Path,
    *,
    zoom: int,
    workers: int = 8,
    max_tiles: int = 600,
) -> pathlib.Path:
    """Download, cache and stitch one panorama. Existing valid tiles are reused."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tile_dir = out_dir / "tiles" / f"z{zoom}"
    tile_dir.mkdir(parents=True, exist_ok=True)

    width, height = zoom_dimensions(metadata, zoom)
    tile_width = int(metadata.get("tileWidth") or client.session["tileWidth"])
    tile_height = int(metadata.get("tileHeight") or client.session["tileHeight"])
    nx, ny = math.ceil(width / tile_width), math.ceil(height / tile_height)
    if nx * ny > max_tiles:
        raise RuntimeError(f"refusing {nx * ny} tiles, above --max-tiles={max_tiles}")

    pano_id = str(metadata["panoId"])
    tile_paths = {(x, y): tile_dir / f"{x:02d}_{y:02d}.jpg" for y in range(ny) for x in range(nx)}

    def fetch(item: tuple[tuple[int, int], pathlib.Path]) -> None:
        (x, y), path = item
        if path.exists() and path.stat().st_size > 1000:
            return
        data = client.tile_bytes(pano_id, zoom, x, y)
        with Image.open(BytesIO(data)) as image:
            image.verify()
        part = path.with_suffix(".part")
        part.write_bytes(data)
        part.replace(path)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(fetch, tile_paths.items()))

    panorama = stitch_tiles(
        tile_paths,
        width=width,
        height=height,
        tile_width=tile_width,
        tile_height=tile_height,
    )
    destination = out_dir / f"panorama_z{zoom}.jpg"
    panorama.save(destination, quality=96, subsampling=0)
    return destination


@dataclass(frozen=True)
class StreetViewAcquireConfig:
    """Inputs for acquiring one Street View panorama."""

    scene: pathlib.Path
    zoom: int
    workers: int
    max_tiles: int
    out: pathlib.Path | None


def acquire_panorama(config: StreetViewAcquireConfig) -> None:
    from ..scene.site_config import load_scene

    scene = load_scene(config.scene)
    location = scene["location"]
    out_dir = config.out or paths.panorama_set(str(scene["name"]))
    client = StreetViewTiles(google_api_key())
    session = client.create_session()
    metadata = client.metadata(
        lat=float(location["lat"]),
        lon=float(location["lon"]),
        radius_m=float(location.get("radius_m", 50.0)),
    )
    if "panoId" not in metadata:
        raise SystemExit(f"no Street View panorama found: {metadata}")

    zoom = min(config.zoom, native_zoom(metadata))
    pose = pose_from_metadata(metadata, scene, support_mesh=load_support_mesh(scene))
    safe_session = {k: session[k] for k in ("expiry", "tileWidth", "tileHeight", "imageFormat")}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (out_dir / "pose_initial.json").write_text(json.dumps(asdict(pose), indent=2))
    (out_dir / "session.json").write_text(json.dumps(safe_session, indent=2))

    destination = download_panorama(
        client,
        metadata,
        out_dir,
        zoom=zoom,
        workers=config.workers,
        max_tiles=config.max_tiles,
    )
    width, height = zoom_dimensions(metadata, zoom)
    print(f"[panorama] {metadata.get('date', 'undated')} {width}x{height}")
    print(f"[panorama] ENU camera {pose.position_enu_m}")
    print(f"[panorama] {metadata.get('copyright', '')}")
    print(f"[panorama] -> {destination}")
