"""Download Google Photorealistic 3D Tiles (GLB) intersecting a small bbox.

Traverses the 3D Tiles tree at tile.googleapis.com, keeps tiles whose oriented
bounding box intersects a target sphere, recurses until geometric error drops
below a cutoff, and saves the leaf GLBs plus a manifest.

Usage: python download_google_tiles.py --lat 51.0550 --lon 3.7220 --radius 200 \
        --cutoff 4 --out data/tiles
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
from urllib.parse import parse_qs, urlparse

import numpy as np
import requests

API = "https://tile.googleapis.com"

WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3


def llh_to_ecef(lat_deg: float, lon_deg: float, h: float = 0.0) -> np.ndarray:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    x = (n + h) * math.cos(lat) * math.cos(lon)
    y = (n + h) * math.cos(lat) * math.sin(lon)
    z = (n * (1 - WGS84_E2) + h) * math.sin(lat)
    return np.array([x, y, z])


def obb_intersects_sphere(box: list[float], center: np.ndarray, radius: float) -> bool:
    c = np.array(box[0:3])
    axes = [np.array(box[3:6]), np.array(box[6:9]), np.array(box[9:12])]
    delta = center - c
    closest = c.copy()
    for a in axes:
        length = np.linalg.norm(a)
        if length < 1e-9:
            continue
        u = a / length
        d = np.clip(np.dot(delta, u), -length, length)
        closest = closest + d * u
    return np.linalg.norm(center - closest) <= radius


class Traverser:
    def __init__(self, key: str, center: np.ndarray, radius: float, cutoff: float,
                 out_dir: pathlib.Path, max_tiles: int):
        self.key = key
        self.center = center
        self.radius = radius
        self.cutoff = cutoff
        self.out = out_dir
        self.max_tiles = max_tiles
        self.session = None
        self.glbs: list[dict] = []
        self.n_requests = 0
        self.bytes = 0
        self.http = requests.Session()

    def url(self, uri: str) -> str:
        sep = "&" if "?" in uri else "?"
        u = f"{API}{uri}{sep}key={self.key}"
        if self.session and "session=" not in u:
            u += f"&session={self.session}"
        return u

    def fetch_json(self, uri: str) -> dict:
        r = self.http.get(self.url(uri), timeout=30)
        r.raise_for_status()
        self.n_requests += 1
        self.bytes += len(r.content)
        return r.json()

    def maybe_grab_session(self, uri: str) -> None:
        if self.session is None and "session=" in uri:
            self.session = parse_qs(urlparse(uri).query)["session"][0]

    def walk(self, tile: dict) -> None:
        if len(self.glbs) >= self.max_tiles:
            return
        bv = tile.get("boundingVolume", {})
        if "box" in bv and not obb_intersects_sphere(bv["box"], self.center, self.radius):
            return
        ge = tile.get("geometricError", 0.0)
        content = tile.get("content", {})
        uri = content.get("uri", "")
        if uri:
            self.maybe_grab_session(uri)
        children = tile.get("children", [])

        if uri.split("?")[0].endswith(".json"):
            sub = self.fetch_json(uri)
            self.walk(sub["root"])
            return

        is_glb = uri.split("?")[0].endswith(".glb")
        if children and ge > self.cutoff:
            for ch in children:
                self.walk(ch)
            return
        if is_glb:
            self.download_glb(uri, ge)
        else:
            for ch in children:
                self.walk(ch)

    def download_glb(self, uri: str, ge: float) -> None:
        name = f"tile_{len(self.glbs):04d}.glb"
        r = self.http.get(self.url(uri), timeout=60)
        r.raise_for_status()
        self.n_requests += 1
        self.bytes += len(r.content)
        (self.out / name).write_bytes(r.content)
        self.glbs.append({"file": name, "uri": uri.split("?")[0], "geometric_error": ge,
                          "size": len(r.content)})
        print(f"  {name}  ge={ge:7.2f}  {len(r.content)/1e6:5.2f} MB", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--radius", type=float, default=200.0)
    ap.add_argument("--cutoff", type=float, default=4.0)
    ap.add_argument("--max-tiles", type=int, default=150)
    ap.add_argument("--out", default="data/tiles")
    args = ap.parse_args()

    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("GOOGLE_API_KEY not set", file=sys.stderr)
        return 1

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    center = llh_to_ecef(args.lat, args.lon, 20.0)

    t = Traverser(key, center, args.radius, args.cutoff, out, args.max_tiles)
    root = t.fetch_json("/v1/3dtiles/root.json")
    t.walk(root["root"])

    manifest = {
        "lat": args.lat, "lon": args.lon, "radius": args.radius,
        "cutoff": args.cutoff, "center_ecef": center.tolist(),
        "tiles": t.glbs, "requests": t.n_requests, "total_bytes": t.bytes,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(t.glbs)} tiles, {t.bytes/1e6:.1f} MB total, {t.n_requests} requests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
