"""Aimed Street View shots of each facade.

    .venv/bin/python -m twin.streetview --area graslei

Needs the Street View Static API enabled on the GCP project behind `GOOGLE_API_KEY`
(`street-view-image-backend.googleapis.com`). Metadata calls are free; images are
about $7 per thousand, so a 32 building area costs well under a euro.

This supersedes `twin.mapillary` where Google has coverage, for one reason that
matters more than image quality: **the camera is a parameter**. Mapillary hands you
whatever a passing cyclist happened to be pointing at, and matching is then a search
over drive-by frames that leaves a third of the block with nothing usable. Here the
heading, pitch and field of view are requested, so every building gets a shot framed
on its own facade, and the projection of the target into that frame is analytic
rather than a distortion model evaluated outside its calibrated range.

Coverage still is not guaranteed. Where Google has no pano within reach the building
falls back to Mapillary and then to the tile plate, and the manifest records which,
because a reading is only worth what its evidence was.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from .anchor import Anchor, Building, load
from .areas import AREAS
from .mapillary import front_of

ROOT = pathlib.Path(__file__).resolve().parent.parent
META = "https://maps.googleapis.com/maps/api/streetview/metadata"
IMAGE = "https://maps.googleapis.com/maps/api/streetview"

TILE = 640                 # the Static API's maximum without a premium plan
CAM_HEIGHT = 2.5           # m, Google's mast, close enough for the pitch solve
FILL = 0.80                # fraction of the frame the facade should occupy
FOV_MIN, FOV_MAX = 25.0, 100.0
PROBE_RADIUS = 26.0        # m, how far Google may wander from the asked-for spot


def key() -> str:
    import os

    k = os.environ.get("GOOGLE_API_KEY")
    if k:
        return k
    env = pathlib.Path("/home/user/aegis/.env")
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith("GOOGLE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no GOOGLE_API_KEY in env or /home/user/aegis/.env")


def enu_to_llh(frame, xy) -> tuple[float, float]:
    """Local flat-earth inverse of `Frame.to_enu`, good to centimetres here."""
    deg_lat = 111_320.0
    deg_lon = deg_lat * math.cos(math.radians(frame.lat0))
    return (frame.lat0 + xy[1] / deg_lat, frame.lon0 + xy[0] / deg_lon)


def metadata(k: str, lat: float, lon: float, radius: float = PROBE_RADIUS,
             tries: int = 4) -> dict:
    """Free lookup of the nearest pano, retried through transient denials.

    Google's API-enable propagates unevenly across edges: immediately after
    switching the Static API on, the same request alternated between a valid answer
    and `REQUEST_DENIED` within seconds. Treating the denial as fatal would have
    silently written off a third of the block as having no coverage.
    """
    import time

    q = urllib.parse.urlencode({"location": f"{lat:.7f},{lon:.7f}",
                                "radius": f"{radius:.0f}", "source": "outdoor",
                                "key": k})
    last: dict = {}
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(f"{META}?{q}", timeout=30) as r:
                last = json.loads(r.read())
        except Exception as exc:                   # noqa: BLE001
            last = {"status": "EXCEPTION", "error_message": str(exc)}
        if last.get("status") in {"OK", "ZERO_RESULTS", "NOT_FOUND"}:
            return last
        time.sleep(1.5 * (attempt + 1))
    return last


def is_official(meta: dict) -> bool:
    """Google's own car or trekker, rather than a contributed photosphere.

    Worth separating: the first probe on the Graslei returned a tour-boat sphere
    with the photographer's hand across a third of the frame. Contributed spheres
    are still used where nothing else exists, but they lose the tie.
    """
    return (meta.get("copyright") or "").strip() in {"© Google", "©  Google"}


def solve_shot(b: Building, mid, nrm, width: float, cam_xy) -> dict | None:
    """Heading, pitch and field of view that put this facade in the frame.

    Solved rather than preferred. The whole reason to pay for Street View over a
    free drive-by archive is that this is a request, not a hope.
    """
    v = mid - cam_xy
    dist = float(np.linalg.norm(v))
    if dist < 3.0:
        return None
    heading = math.degrees(math.atan2(v[0], v[1])) % 360.0
    cam_z = b.ground_z + CAM_HEIGHT
    target_z = b.ground_z + 0.55 * b.height
    pitch = math.degrees(math.atan2(target_z - cam_z, dist))
    # Frame whichever of width and height needs the wider angle.
    half = max(width / 2.0, 0.5 * b.height * 1.05)
    fov = 2.0 * math.degrees(math.atan(half / dist)) / FILL
    return {"heading": round(heading, 2), "pitch": round(pitch, 2),
            "fov": round(min(FOV_MAX, max(FOV_MIN, fov)), 2),
            "dist_m": round(dist, 1), "cam_z": cam_z,
            "frontality": round(float(np.dot(-v / dist, nrm)), 3)}


def project(shot: dict, cam_xy, p) -> tuple[float, float] | None:
    """World ENU point to normalised image coordinates, origin top left.

    A rectilinear Street View request is a pinhole camera whose parameters we chose,
    so this is exact. No lens model, no calibrated range to fall outside of.
    """
    head = math.radians(shot["heading"])
    pit = math.radians(shot["pitch"])
    fwd = np.array([math.sin(head) * math.cos(pit),
                    math.cos(head) * math.cos(pit), math.sin(pit)])
    right = np.array([math.cos(head), -math.sin(head), 0.0])
    up = np.cross(right, fwd)
    v = np.asarray(p, dtype=float) - np.array([cam_xy[0], cam_xy[1], shot["cam_z"]])
    z = float(v @ fwd)
    if z <= 0.2:
        return None
    f = 0.5 / math.tan(math.radians(shot["fov"]) / 2.0)   # in frame widths
    return (0.5 + f * float(v @ right) / z, 0.5 - f * float(v @ up) / z)


def target_box(shot: dict, cam_xy, b: Building, mid, nrm, width: float):
    u = np.array([-nrm[1], nrm[0]])
    pts = []
    for s in (-0.5, 0.5):
        q = mid + u * (s * width)
        for z in (b.ground_z, b.ground_z + b.height):
            uv = project(shot, cam_xy, np.array([q[0], q[1], z]))
            if uv is None:
                return None
            pts.append(uv)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    box = {"x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys)}
    if box["x1"] < 0.02 or box["x0"] > 0.98:
        return None
    return {k: round(float(np.clip(v, 0.0, 1.0)), 3) for k, v in box.items()}


def grab(k: str, lat: float, lon: float, shot: dict, path: pathlib.Path) -> bool:
    if path.exists() and path.stat().st_size > 4000:
        return True
    q = urllib.parse.urlencode({
        "size": f"{TILE}x{TILE}", "location": f"{lat:.7f},{lon:.7f}",
        "heading": shot["heading"], "pitch": shot["pitch"], "fov": shot["fov"],
        "source": "outdoor", "return_error_code": "true", "key": k,
    })
    try:
        with urllib.request.urlopen(f"{IMAGE}?{q}", timeout=60) as r:
            data = r.read()
    except Exception as exc:                       # noqa: BLE001
        print(f"    image failed: {exc}")
        return False
    if len(data) < 4000:
        return False                               # the grey "no imagery" tile
    path.write_bytes(data)
    return True


def draw_box(src: pathlib.Path, dst: pathlib.Path, box: dict) -> bool:
    from PIL import Image, ImageDraw

    try:
        img = Image.open(src).convert("RGB")
    except Exception:                              # noqa: BLE001
        return False
    w, h = img.size
    d = ImageDraw.Draw(img)
    d.rectangle([box["x0"] * w, box["y0"] * h, box["x1"] * w, box["y1"] * h],
                outline=(255, 0, 190), width=max(2, w // 320))
    img.save(dst, quality=94)
    return True


def shoot_building(k: str, b: Building, anchor: Anchor, out_dir: pathlib.Path,
                   n_views: int = 2) -> list[dict]:
    """Up to `n_views` aimed shots, from standoffs Google actually has a pano near.

    Two views rather than one because a single frontal shot of a terraced house
    tells you nothing about depth, and the oblique catches the reveal shadows that
    make a reveal class readable at all.
    """
    mid, nrm, width = front_of(b, anchor)
    recs: list[dict] = []
    want = max(9.0, min(0.95 * max(width, b.height), 26.0))
    # Straight out from the wall first, then swung along the street, which is
    # usually where the pavement actually is in a medieval block.
    u = np.array([-nrm[1], nrm[0]])
    offers = [nrm * want,
              nrm * want * 0.92 + u * want * 0.5,
              nrm * want * 0.92 - u * want * 0.5,
              nrm * want * 1.5]
    # Look everything up first, rank, then spend money on images. Metadata is free
    # and the ranking wants to see all the options before choosing.
    found: list[tuple] = []
    seen: list[np.ndarray] = []
    for off in offers:
        probe = mid + off
        lat, lon = enu_to_llh(anchor.frame, probe)
        meta = metadata(k, lat, lon)
        if meta.get("status") != "OK":
            continue
        loc = meta["location"]
        cam_xy = anchor.frame.to_enu(loc["lng"], loc["lat"])[:2]
        if any(float(np.linalg.norm(cam_xy - s)) < 7.0 for s in seen):
            continue                       # Google returned the same pano again
        seen.append(cam_xy)
        shot = solve_shot(b, mid, nrm, width, cam_xy)
        if shot is None or shot["frontality"] < 0.12:
            continue
        box = target_box(shot, cam_xy, b, mid, nrm, width)
        if box is None:
            continue
        rank = shot["frontality"] * (1.0 if is_official(meta) else 0.55) \
            * math.exp(-0.5 * ((shot["dist_m"] - want) / max(0.8 * want, 6.0)) ** 2)
        found.append((rank, meta, loc, cam_xy, shot, box))

    found.sort(key=lambda t: -t[0])
    for rank, meta, loc, _cam_xy, shot, box in found[:n_views]:
        path = out_dir / f"{b.osm_id}_{len(recs)}.jpg"
        if not grab(k, loc["lat"], loc["lng"], shot, path):
            continue
        keyed = path.with_name(path.stem + "_key.jpg")
        if not draw_box(path, keyed, box):
            continue
        recs.append({"pano_id": meta.get("pano_id"), "date": meta.get("date"),
                     "official": is_official(meta),
                     "copyright": meta.get("copyright"),
                     "file": str(path), "keyed_file": str(keyed),
                     "target_box": box, "range_m": shot["dist_m"],
                     "frontality": shot["frontality"], "fov": shot["fov"],
                     "heading": shot["heading"], "pitch": shot["pitch"],
                     "rank": round(rank, 3), "source": "google_streetview"})
    return recs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="graslei")
    ap.add_argument("--views", type=int, default=2)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--merge-mapillary", action="store_true", default=True,
                    help="keep Mapillary photos for buildings Google cannot see")
    args = ap.parse_args()

    k = key()
    anchor = load()
    cx, cy, radius = AREAS[args.area]
    centre = np.array([cx, cy])
    targets = [b for b in anchor.buildings
               if np.linalg.norm(b.centroid - centre) <= radius]
    targets.sort(key=lambda b: float(np.linalg.norm(b.centroid - centre)))
    out_dir = ROOT / "renders" / "streetview_g" / args.area
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[gsv] {len(targets)} buildings in {args.area}")

    def one(b: Building):
        recs = shoot_building(k, b, anchor, out_dir, n_views=args.views)
        detail = ", ".join(f"{r['range_m']}m fov{r['fov']:.0f} {r['date']}"
                           for r in recs)
        print(f"  {b.osm_id}  {len(recs)} view(s)  {detail or 'no coverage'}")
        return b.osm_id, recs

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        got = dict(ex.map(one, targets))

    photos = {int(i): r for i, r in got.items()}
    n_google = sum(1 for v in photos.values() if v)

    mly_path = ROOT / "data" / "twin" / f"streetview_{args.area}.json"
    filled = 0
    if args.merge_mapillary and mly_path.exists():
        mly = json.loads(mly_path.read_text())["photos"]
        for osm_id, recs in mly.items():
            if not photos.get(int(osm_id)) and recs:
                for r in recs:
                    r["source"] = "mapillary"
                photos[int(osm_id)] = recs
                filled += 1

    out = ROOT / "data" / "twin" / f"photos_{args.area}.json"
    out.write_text(json.dumps({"area": args.area,
                               "photos": {str(i): v for i, v in photos.items()}},
                              indent=1))
    covered = sum(1 for v in photos.values() if v)
    print(f"\n[gsv] Google covers {n_google}/{len(targets)}, "
          f"Mapillary fills {filled} more, {covered}/{len(targets)} total")
    print(f"[gsv] -> {out}")


if __name__ == "__main__":
    main()
