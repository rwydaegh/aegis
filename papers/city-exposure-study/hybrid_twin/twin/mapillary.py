"""Street-level photographs as director evidence, matched to buildings by geometry.

    .venv/bin/python -m twin.mapillary --area graslei

The Google tiles answer a different question from the one the facade grammar asks.
An aerial pass at roughly 25 cm/texel resolves roof form and massing, which nothing
at street level can see, and dissolves everything below about a metre, which is
where the grammar lives. Reading a facade from tiles alone leaves most of the schema
marked `inferred`, and it shows: mullions, sills, shopfronts and brick bond are all
guesses from a regional prior wearing the costume of an observation.

Mapillary is a real photograph from the pavement, so the same fields become `seen`.
It is worse at exactly what the tiles are good at, so this does not replace the
plate, it joins it. The director gets both and is told which is which.

Matching is geometric, never by search. For each building we already know the
street-facing edge, its midpoint and its outward normal from the anchor layer, and
Mapillary publishes each image's computed position and compass bearing. A photograph
qualifies when the camera stands outside that edge, within a sensible range, and is
actually pointing at it. No model is asked "which building is this".

Panoramas are accepted only when nothing else exists. An equirectangular frame shown
to a vision model is a warped strip in which a facade spans a fraction of the width,
and reading storey rhythm off it is worse than reading it off the aerial.
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
from .facade import street_facing_edges

ROOT = pathlib.Path(__file__).resolve().parent.parent
GRAPH = "https://graph.mapillary.com/images"

FIELDS = ("id,computed_geometry,computed_compass_angle,captured_at,is_pano,"
          "thumb_2048_url,camera_type,quality_score,width,height,"
          "camera_parameters,computed_rotation")

MIN_RANGE, MAX_RANGE = 4.0, 55.0
MAX_OFF_AXIS_DEG = 55.0     # how far the camera may be pointed off the facade
MIN_FRONTALITY = 0.15       # how square-on the camera must stand to the wall


def token() -> str:
    """The Mapillary client token, from the environment or the repo `.env`."""
    import os

    tok = os.environ.get("MAPILLARY_TOKEN")
    if tok:
        return tok
    env = pathlib.Path("/home/user/aegis/.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("MAPILLARY_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("no MAPILLARY_TOKEN in env or /home/user/aegis/.env")


def fetch_bbox(tok: str, bbox, limit: int = 2000) -> list[dict]:
    """Every image Mapillary has in the box. One call, then all matching is local."""
    q = urllib.parse.urlencode({
        "access_token": tok, "fields": FIELDS,
        "bbox": ",".join(f"{v:.6f}" for v in bbox), "limit": str(limit),
    })
    with urllib.request.urlopen(f"{GRAPH}?{q}", timeout=60) as r:
        return json.loads(r.read())["data"]


def to_local(frame, images: list[dict]) -> list[dict]:
    """Attach ENU position and a unit view direction to each image."""
    out = []
    for im in images:
        geom = im.get("computed_geometry")
        ang = im.get("computed_compass_angle")
        if not geom or ang is None:
            continue
        lon, lat = geom["coordinates"]
        xy = frame.to_enu(lon, lat)[:2]
        # Compass is degrees clockwise from north, so it maps to ENU as
        # (sin, cos), not the usual (cos, sin).
        th = math.radians(float(ang))
        out.append({**im, "xy": xy,
                    "dir": np.array([math.sin(th), math.cos(th)])})
    return out


def front_of(b: Building, anchor: Anchor):
    """Street-facing edge midpoint, outward normal and width. Same edge the plate
    camera used, so the two images agree on what the subject is."""
    ring = b.ring
    idx = street_facing_edges(b, anchor)
    best = max(idx, key=lambda i: np.linalg.norm(
        ring[(i + 1) % len(ring)] - ring[i]))
    a, c = ring[best], ring[(best + 1) % len(ring)]
    e = c - a
    w = float(np.linalg.norm(e))
    mid = (a + c) / 2.0
    nrm = np.array([e[1], -e[0]]) / max(w, 1e-9)
    if np.dot(nrm, mid - b.centroid) < 0:
        nrm = -nrm
    return mid, nrm, w


def score(im: dict, mid, nrm, width: float) -> float | None:
    """How good a photograph of this facade is, or None if it is not one."""
    v = mid - im["xy"]
    dist = float(np.linalg.norm(v))
    if not (MIN_RANGE <= dist <= MAX_RANGE):
        return None
    v = v / dist
    # Standing on the right side of the wall, and looking at it.
    frontality = float(np.dot(-v, nrm))
    if frontality < MIN_FRONTALITY:
        return None
    off_axis = math.degrees(math.acos(max(-1.0, min(1.0,
                                                    float(np.dot(im["dir"], v))))))
    if off_axis > MAX_OFF_AXIS_DEG:
        return None
    # Range that frames a facade of this width on a phone lens, roughly 65 deg.
    want = max(8.0, 0.85 * width)
    s = (frontality
         * math.exp(-0.5 * (off_axis / 30.0) ** 2)
         * math.exp(-0.5 * ((dist - want) / (0.7 * want)) ** 2))
    if im.get("is_pano"):
        s *= 0.25          # a warped strip, only if nothing else exists
    if im.get("quality_score") is not None:
        s *= 0.5 + 0.5 * float(im["quality_score"])
    return s


def pick(b: Building, anchor: Anchor, images: list[dict], n: int = 2) -> list[dict]:
    """Best few photographs of this building, spread apart rather than duplicated.

    Consecutive frames from one drive are near-identical, so taking the top two by
    score usually buys nothing. Candidates within 6 m of an already chosen camera
    are skipped, which turns the second image into a genuinely different angle.
    """
    mid, nrm, width = front_of(b, anchor)
    ranked = []
    for im in images:
        s = score(im, mid, nrm, width)
        if s is not None:
            ranked.append((s, im))
    ranked.sort(key=lambda t: -t[0])
    out: list[dict] = []
    for s, im in ranked:
        if any(np.linalg.norm(im["xy"] - o["xy"]) < 6.0 for o in out):
            continue
        d = float(np.linalg.norm(mid - im["xy"]))
        out.append({**im, "score": round(s, 3), "range_m": round(d, 1)})
        if len(out) >= n:
            break
    return out


def _rodrigues(v) -> np.ndarray:
    """Angle-axis to rotation matrix."""
    v = np.asarray(v, dtype=float)
    th = float(np.linalg.norm(v))
    if th < 1e-12:
        return np.eye(3)
    k = v / th
    kx = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(th) * kx + (1.0 - math.cos(th)) * (kx @ kx)


def project(im: dict, cam_xyz: np.ndarray, p: np.ndarray) -> tuple | None:
    """World ENU point to normalised image coordinates, origin top left.

    `computed_rotation` is angle-axis for world to camera, with world being a local
    ENU frame and camera being x right, y down, z forward. Checked rather than
    assumed: the forward axis recovered from it reproduces `computed_compass_angle`
    to 0.01 degrees on a sample image, which pins the convention down completely.

    `camera_parameters` is OpenSfM's `[focal, k1, k2]`, focal normalised by the
    longer image side, so the Brown distortion has to be applied before scaling to
    pixels or the projection drifts by tens of degrees at the frame edge, which is
    exactly where a facade in a 113 degree phone frame tends to sit.
    """
    rot, cp = im.get("computed_rotation"), im.get("camera_parameters")
    w, h = im.get("width"), im.get("height")
    if not rot or not cp or not w or not h:
        return None
    focal = float(cp[0])
    k1 = float(cp[1]) if len(cp) > 1 else 0.0
    k2 = float(cp[2]) if len(cp) > 2 else 0.0
    v = _rodrigues(rot) @ (np.asarray(p, dtype=float) - cam_xyz)
    if v[2] <= 0.05:
        return None                       # behind the camera
    xn, yn = v[0] / v[2], v[1] / v[2]
    r2 = xn * xn + yn * yn
    if r2 > R_MAX * R_MAX:
        return None
    d = 1.0 + k1 * r2 + k2 * r2 * r2
    scale = float(max(w, h))
    return (0.5 + focal * d * xn * scale / w,
            0.5 + focal * d * yn * scale / h)


# Beyond this off-axis tangent the Brown polynomial is being evaluated outside the
# data it was fitted to, and it folds: the roof line of a 14 m building seen from
# 6 m projects *below* its own doorway. Corners past it are refused rather than
# trusted, which also does the useful work of rejecting frames standing too close
# to hold the facade at all.
R_MAX = 1.15        # tan(49 deg)


def target_box(im: dict, b: Building, mid, nrm, width: float,
               cam_z: float) -> dict | None:
    """Where the target facade lands in the photograph, normalised.

    Returns the ground line always and the eaves only when they are inside the
    lens's honest field. A box that says "this building, from here up out of frame"
    is true; one that says "this building, ending at mid-frame" is a lie the
    director will faithfully act on.
    """
    cam = np.array([im["xy"][0], im["xy"][1], cam_z])
    u = np.array([-nrm[1], nrm[0]])
    ground, tops = [], []
    for s in (-0.42, 0.0, 0.42):
        q = mid + u * (s * width)
        g = project(im, cam, np.array([q[0], q[1], b.ground_z]))
        if g is None:
            continue
        ground.append(g)
        t = project(im, cam, np.array([q[0], q[1], b.ground_z + b.height]))
        if t is not None:
            tops.append(t)
    if len(ground) < 2:
        return None
    xs = [p[0] for p in ground] + [p[0] for p in tops]
    y_bottom = max(p[1] for p in ground)
    clipped = len(tops) < len(ground)
    y_top = 0.0 if clipped else min(p[1] for p in tops)
    box = {"x0": min(xs), "x1": max(xs), "y0": y_top, "y1": y_bottom}
    if box["x1"] < 0.05 or box["x0"] > 0.95 or box["x1"] - box["x0"] < 0.04:
        return None
    out = {k: round(float(np.clip(v, 0.0, 1.0)), 3) for k, v in box.items()}
    out["top_clipped"] = clipped
    return out


def draw_box(src: pathlib.Path, dst: pathlib.Path, box: dict) -> bool:
    """Outline the target on a copy, leaving the original clean."""
    from PIL import Image, ImageDraw

    try:
        img = Image.open(src).convert("RGB")
    except Exception:                             # noqa: BLE001
        return False
    w, h = img.size
    d = ImageDraw.Draw(img)
    xy = [box["x0"] * w, box["y0"] * h, box["x1"] * w, box["y1"] * h]
    xy = [xy[0], xy[1], max(xy[2], xy[0] + 4), max(xy[3], xy[1] + 4)]
    wd = max(3, w // 340)
    d.rectangle(xy, outline=(255, 0, 190), width=wd)
    if box.get("top_clipped"):
        # Dashed lid, so an outline that stops at the frame edge does not read as
        # the roof line of a building that is actually taller than the photograph.
        step = max(18, w // 60)
        for x in range(int(xy[0]), int(xy[2]), 2 * step):
            d.line([x, xy[1] + wd, min(x + step, xy[2]), xy[1] + wd],
                   fill=(255, 0, 190), width=wd)
    img.save(dst, quality=92)
    return True


def download(im: dict, path: pathlib.Path) -> bool:
    if path.exists():
        return True
    url = im.get("thumb_2048_url")
    if not url:
        return False
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            path.write_bytes(r.read())
        return True
    except Exception as exc:                      # noqa: BLE001
        print(f"    download failed {im['id']}: {exc}")
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="graslei")
    ap.add_argument("--per-building", type=int, default=2)
    ap.add_argument("--min-score", type=float, default=0.02,
                    help="below this the geometric match is too weak to be "
                         "evidence, and a photograph of the wrong street is "
                         "worse than no photograph")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    anchor = load()
    cx, cy, radius = AREAS[args.area]
    centre = np.array([cx, cy])
    bbox = anchor.frame.bbox(radius + 70.0, (cx, cy))
    print(f"[mly] bbox {tuple(round(v, 5) for v in bbox)}")

    raw = fetch_bbox(token(), bbox)
    images = to_local(anchor.frame, raw)
    n_pano = sum(1 for i in images if i.get("is_pano"))
    print(f"[mly] {len(raw)} images in box, {len(images)} georeferenced, "
          f"{n_pano} panoramic")

    targets = [b for b in anchor.buildings
               if np.linalg.norm(b.centroid - centre) <= radius]
    targets.sort(key=lambda b: float(np.linalg.norm(b.centroid - centre)))

    out_dir = ROOT / "renders" / "streetview" / args.area
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs, records = [], {}
    for b in targets:
        mid, nrm, width = front_of(b, anchor)
        # The building's own datum, not the filtered terrain grid: the two differ
        # by 1.7 m at this facade, which is a whole storey of vertical error.
        cam_z = b.ground_z + 1.6
        recs = []
        for k, im in enumerate(pick(b, anchor, images, n=args.per_building)):
            if im["score"] < args.min_score:
                continue
            box = target_box(im, b, mid, nrm, width, cam_z)
            if box is None:
                continue        # target not actually in frame: not evidence
            path = out_dir / f"{b.osm_id}_{k}.jpg"
            jobs.append((im, path, box))
            recs.append({"id": im["id"], "file": str(path),
                         "keyed_file": str(path.with_name(path.stem + "_key.jpg")),
                         "target_box": box,
                         "range_m": im["range_m"], "score": im["score"],
                         "is_pano": bool(im.get("is_pano")),
                         "captured_at": im.get("captured_at")})
        records[b.osm_id] = recs
        detail = ", ".join(f"{r['range_m']}m s={r['score']}" for r in recs)
        print(f"  {b.osm_id}  {len(recs)} photo(s)  {detail or 'none'}")

    def fetch(job) -> bool:
        im, path, box = job
        return download(im, path) and draw_box(
            path, pathlib.Path(path.with_name(path.stem + "_key.jpg")), box)

    with ThreadPoolExecutor(max_workers=8) as ex:
        got = list(ex.map(fetch, jobs))
    print(f"[mly] downloaded {sum(got)}/{len(jobs)}")

    # Drop anything that failed, so the manifest never points at a file the
    # director will be told to read and cannot.
    for osm_id, recs in records.items():
        records[osm_id] = [r for r in recs
                           if pathlib.Path(r["file"]).exists()
                           and pathlib.Path(r["keyed_file"]).exists()]

    out = pathlib.Path(args.out) if args.out else \
        ROOT / "data" / "twin" / f"streetview_{args.area}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"area": args.area, "photos": records}, indent=1))
    covered = sum(1 for v in records.values() if v)
    print(f"[mly] {covered}/{len(targets)} buildings have a street photo -> {out}")


if __name__ == "__main__":
    main()
