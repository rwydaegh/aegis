"""Acquire one full-resolution Inhouse Street View panorama and its camera pose.

This module uses the official Map Tiles API and stitches the tiled
equirectangular panorama. It is deliberately bounded to one panorama per command.

Run from ``semantic_twin`` with the AEGIS virtual environment::

    ../../../.venv/bin/python -m semantic_twin.panorama \
      --scene config/korenmarkt.json --zoom 5

Zoom 5 is the native panorama resolution, usually 13k or 16k pixels wide. Zoom 4
is useful for fast iteration. Tile downloads are resumable and the output folder
records the complete metadata and ENU pose used by the projection pipeline.
"""

from __future__ import annotations

import argparse
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

from PIL import Image

from .geo import EnuFrame
from .scene import inhouse_api_key, load_scene

ROOT = pathlib.Path(__file__).resolve().parent.parent
CREATE_SESSION = "https://tile.googleapis.com/v1/createSession"
METADATA = "https://tile.googleapis.com/v1/streetview/metadata"
TILE = "https://tile.googleapis.com/v1/streetview/tiles"
MAX_ZOOM = 5


@dataclass(frozen=True)
class PanoramaPose:
    """Street View camera in the configured geometry's local ENU frame.

    Inhouse supplies latitude, longitude and orientation but no camera altitude.
    The initial z therefore comes from the measured terrain plus ``camera_height``.
    Skyline registration is expected to refine it before semantic projection.
    """

    position_enu_m: tuple[float, float, float]
    position_wgs84: tuple[float, float]
    heading_deg: float
    tilt_deg: float
    roll_deg: float
    camera_height_m: float
    altitude_source: str = "terrain_plus_camera_height"
    coordinate_frame: str = "ENU: x east, y north, z up"


class StreetViewTiles:
    """Small, retrying client for one Map Tiles Street View session."""

    def __init__(self, api_key: str, *, tries: int = 4) -> None:
        self.api_key = api_key
        self.tries = tries
        self.session: dict[str, Any] | None = None

    def _read(self, request: str | urllib.request.Request) -> bytes:
        last: Exception | None = None
        for attempt in range(self.tries):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    return response.read()
            except (OSError, urllib.error.HTTPError) as exc:
                last = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code < 500:
                    detail = exc.read().decode("utf-8", errors="replace")[:1000]
                    raise RuntimeError(f"Street View HTTP {exc.code}: {detail}") from exc
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Street View request failed after {self.tries} attempts") from last

    def create_session(self) -> dict[str, Any]:
        body = json.dumps({"mapType": "streetview", "language": "en-US", "region": "BE"}).encode()
        url = f"{CREATE_SESSION}?{urllib.parse.urlencode({'key': self.api_key})}"
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        self.session = json.loads(self._read(request))
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
        return json.loads(self._read(f"{METADATA}?{urllib.parse.urlencode(params)}"))

    def tile_bytes(self, pano_id: str, zoom: int, x: int, y: int) -> bytes:
        params = urllib.parse.urlencode({"session": self.token, "key": self.api_key, "panoId": pano_id})
        return self._read(f"{TILE}/{zoom}/{x}/{y}?{params}")


def zoom_dimensions(metadata: dict[str, Any], zoom: int) -> tuple[int, int]:
    """Return the useful equirectangular dimensions at a Street View zoom level."""
    if not 0 <= zoom <= MAX_ZOOM:
        raise ValueError(f"zoom must be in [0, {MAX_ZOOM}]")
    divisor = 2 ** (MAX_ZOOM - zoom)
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
    """Stitch a complete tile grid and crop Inhouse's padded edge tiles."""
    canvas = Image.new(
        "RGB", (math.ceil(width / tile_width) * tile_width, math.ceil(height / tile_height) * tile_height)
    )
    for (x, y), path in tile_paths.items():
        with Image.open(path) as tile:
            canvas.paste(tile.convert("RGB"), (x * tile_width, y * tile_height))
    return canvas.crop((0, 0, width, height))


def pose_from_metadata(metadata: dict[str, Any], scene: dict[str, Any]) -> PanoramaPose:
    origin = scene["enu_origin"]
    frame = EnuFrame(
        float(origin["lat"]),
        float(origin["lon"]),
        float(origin.get("ellipsoid_height_m", 0.0)),
    )
    xy = frame.to_enu(float(metadata["lat"]), float(metadata["lng"]))[:2]
    camera_height_m = float(scene.get("camera_height_m", 2.5))
    ground_z = float(scene["camera_ground_z_m"])
    z = ground_z + camera_height_m
    return PanoramaPose(
        position_enu_m=(float(xy[0]), float(xy[1]), float(z)),
        position_wgs84=(float(metadata["lat"]), float(metadata["lng"])),
        heading_deg=float(metadata.get("heading", 0.0)),
        tilt_deg=float(metadata.get("tilt", 90.0)),
        roll_deg=float(metadata.get("roll", 0.0)),
        camera_height_m=camera_height_m,
    )


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
    paths = {(x, y): tile_dir / f"{x:02d}_{y:02d}.jpg" for y in range(ny) for x in range(nx)}

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
        list(pool.map(fetch, paths.items()))

    panorama = stitch_tiles(
        paths,
        width=width,
        height=height,
        tile_width=tile_width,
        tile_height=tile_height,
    )
    destination = out_dir / f"panorama_z{zoom}.jpg"
    panorama.save(destination, quality=96, subsampling=0)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=pathlib.Path, required=True)
    parser.add_argument("--zoom", type=int, choices=range(0, 6), default=5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-tiles", type=int, default=600)
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()

    scene = load_scene(args.scene)
    location = scene["location"]
    out_dir = args.out or ROOT / "data" / "panoramas" / str(scene["name"])
    client = StreetViewTiles(inhouse_api_key())
    session = client.create_session()
    metadata = client.metadata(
        lat=float(location["lat"]),
        lon=float(location["lon"]),
        radius_m=float(location.get("radius_m", 50.0)),
    )
    if "panoId" not in metadata:
        raise SystemExit(f"no Street View panorama found: {metadata}")

    pose = pose_from_metadata(metadata, scene)
    safe_session = {k: session[k] for k in ("expiry", "tileWidth", "tileHeight", "imageFormat")}
    (out_dir / "metadata.json").parent.mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    (out_dir / "pose_initial.json").write_text(json.dumps(asdict(pose), indent=2))
    (out_dir / "session.json").write_text(json.dumps(safe_session, indent=2))

    destination = download_panorama(
        client,
        metadata,
        out_dir,
        zoom=args.zoom,
        workers=args.workers,
        max_tiles=args.max_tiles,
    )
    width, height = zoom_dimensions(metadata, args.zoom)
    print(f"[panorama] {metadata.get('date', 'undated')} {width}x{height}")
    print(f"[panorama] ENU camera {pose.position_enu_m}")
    print(f"[panorama] {metadata.get('copyright', '')}")
    print(f"[panorama] -> {destination}")


if __name__ == "__main__":
    main()
