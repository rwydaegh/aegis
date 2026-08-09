"""Street-level facade photos of the walk-corridor buildings ("AI eyes" input).

One frontal shot per building, rendered from the TEXTURED Inhouse photogrammetry
so a downstream vision pass can guess ITU-R P.2040 material classes.

Run: ~/blender-4.5/blender -b scene.blend -P render_facades.py
Optional args after `--`: --limit N --only ID,ID --skip-render

Writes renders/facades/<osm_id>.png and data/facade_manifest.json.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3

WALK_STEP = 1.0          # m, walk resampling
EYE_HEIGHT = 1.7         # m above local ground
PRISM_MAX_DWALK = 30.0   # m, prism-tier buildings this close to the walk qualify
MAX_BUILDINGS = 36
MIN_CAM_DIST = 8.0       # m, camera to footprint centroid
MIN_FACADE_DIST = 5.0    # m, camera to the facade it is shooting. Low, because
#                          Ghent alleys leave no choice; the standoff preference
#                          below pulls the camera back whenever it can.
MAX_CAM_DIST = 150.0     # m, do not shoot a building from across the district
OCCLUSION_SLACK = 2.0    # m, hit this much before the facade means blocked
CLEAR_FRACTION = 0.5     # fraction of probe rays that must reach the facade
CLUTTER_MAX = 0.15       # fraction of the frame allowed to be near-field junk
CLUTTER_NEAR = 0.45      # a hit inside this fraction of the facade range is junk
STANDOFF_BEST = 25.0     # m, facade standoff the tile texel budget likes
STANDOFF_WIDTH = 20.0    # m, tolerance of the standoff preference
AIM_HEIGHT_CAP = 8.0     # m, target height cap above ground
FRAME_MARGIN = 1.45      # >1 keeps sky above the roof and street below the door
RES_X, RES_Y = 640, 480
SAMPLES = 20
SENSOR_W = 36.0          # mm, Blender default; sensor_fit AUTO -> fits the long axis
LENS_MIN, LENS_MAX, LENS_DEFAULT = 11.0, 32.0, 24.0
FAN_U = (-0.45, -0.22, 0.0, 0.22, 0.45)   # frame fractions for the clutter fan
FAN_V = (-0.2, 0.05, 0.28, 0.5)


def llh_to_ecef(lat_deg, lon_deg, h=0.0):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    return np.array([
        (n + h) * math.cos(lat) * math.cos(lon),
        (n + h) * math.cos(lat) * math.sin(lon),
        (n * (1 - WGS84_E2) + h) * math.sin(lat)])


def enu_rotation(lat_deg, lon_deg):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    east = np.array([-math.sin(lon), math.cos(lon), 0.0])
    north = np.array([-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon),
                      math.cos(lat)])
    up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon),
                   math.sin(lat)])
    return np.vstack([east, north, up])


def collect_world_triangles(coll):
    verts_all, tris_all, offset = [], [], 0
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in coll.all_objects:
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(deps)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        n = len(me.vertices)
        if n == 0:
            continue
        v = np.empty(n * 3)
        me.vertices.foreach_get("co", v)
        v = v.reshape(-1, 3)
        m = np.array(obj.matrix_world)
        v = v @ m[:3, :3].T + m[:3, 3]
        t = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
        me.loop_triangles.foreach_get("vertices", t)
        verts_all.append(v)
        tris_all.append(t.reshape(-1, 3) + offset)
        offset += n
        ev.to_mesh_clear()
    return np.vstack(verts_all), np.vstack(tris_all)


def ground_at(bvh, x, y, radius=2.5):
    """Lowest hit over a small disk: keeps the sample on the street, not on a
    roof edge or an overhang the single vertical ray happens to clip."""
    down = Vector((0, 0, -1))
    zs = []
    for dx, dy in ((0, 0), (radius, 0), (-radius, 0), (0, radius), (0, -radius)):
        h = bvh.ray_cast(Vector((x + dx, y + dy, 500.0)), down, 1000.0)
        if h[0] is not None:
            zs.append(h[0].z)
    return min(zs) if zs else None


def load_walk(gpx_path, R, p0, bvh):
    import xml.etree.ElementTree as ET
    pts = []
    root = ET.parse(gpx_path).getroot()
    for tp in root.iter("{http://www.topografix.com/GPX/1/1}trkpt"):
        e = R @ (llh_to_ecef(float(tp.get("lat")), float(tp.get("lon"))) - p0)
        pts.append(e[:2])
    pts = np.array(pts)
    out = []
    for a, b in zip(pts[:-1], pts[1:], strict=True):
        seg = b - a
        n = max(int(np.linalg.norm(seg) / WALK_STEP), 1)
        for i in range(n):
            out.append(a + seg * (i / n))
    out.append(pts[-1])
    out = np.array(out)
    z = np.array([ground_at(bvh, x, y) or 50.0 for x, y in out])
    return np.column_stack([out, z])


def ring_enu(ring, R, p0):
    pts = [tuple((R @ (llh_to_ecef(la, lo) - p0))[:2]) for lo, la in ring]
    if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    return pts


def poly_centroid(pts):
    """Area-weighted centroid, falling back to the vertex mean for degenerates."""
    x = np.array([p[0] for p in pts])
    y = np.array([p[1] for p in pts])
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    cross = x * y2 - x2 * y
    a = cross.sum() / 2.0
    if abs(a) < 1e-6:
        return float(x.mean()), float(y.mean()), 0.0
    cx = ((x + x2) * cross).sum() / (6.0 * a)
    cy = ((y + y2) * cross).sum() / (6.0 * a)
    return float(cx), float(cy), abs(float(a))


def point_in_poly(px, py, pts):
    x = np.array([p[0] for p in pts])
    y = np.array([p[1] for p in pts])
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    cond = (y > py) != (y2 > py)
    with np.errstate(divide="ignore", invalid="ignore"):
        xin = (x2 - x) * (py - y) / (y2 - y) + x
    return bool((cond & (px < xin)).sum() % 2 == 1)


def ray_poly_t(ox, oy, dx, dy, pts):
    """Horizontal distance from (ox,oy) along (dx,dy) to the first footprint edge,
    plus that edge's outward-ish unit normal (the facade being photographed)."""
    best, normal = None, None
    for i in range(len(pts)):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % len(pts)]
        ex, ey = bx - ax, by - ay
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((ax - ox) * ey - (ay - oy) * ex) / den
        u = ((ax - ox) * dy - (ay - oy) * dx) / den
        if t > 1e-6 and -1e-9 <= u <= 1.0 + 1e-9 and (best is None or t < best):
            best = t
            L = math.hypot(ex, ey)
            normal = (ey / L, -ex / L) if L > 1e-9 else None
    return best, normal


def probe_points(cx, cy, target_z, ground_z, height, view_dir, half_w):
    """Aim point plus four spread probes across the facade."""
    lat = np.array([-view_dir[1], view_dir[0]])
    lat /= max(np.linalg.norm(lat), 1e-9)
    off = min(half_w * 0.5, 6.0)
    zs_hi = min(ground_z + height * 0.85, target_z + 6.0)
    zs_lo = ground_z + max(1.0, min(2.0, height * 0.2))
    return [
        (cx, cy, target_z),
        (cx + lat[0] * off, cy + lat[1] * off, target_z),
        (cx - lat[0] * off, cy - lat[1] * off, target_z),
        (cx, cy, zs_hi),
        (cx, cy, zs_lo),
    ]


def visibility(bvh, cam, pts, cx, cy, target_z, ground_z, height, half_w):
    """Fraction of probe rays from cam that reach the footprint without being
    stopped short. A ray is blocked when the first mesh hit is well in front of
    where the ray crosses the building's own footprint boundary."""
    d0 = np.array([cx - cam[0], cy - cam[1]])
    n0 = np.linalg.norm(d0)
    if n0 < 1e-6:
        return 0.0, None
    view = d0 / n0
    clear, t_face_center, frontality = 0, None, 0.0
    probes = probe_points(cx, cy, target_z, ground_z, height, view, half_w)
    for k, p in enumerate(probes):
        d = Vector((p[0] - cam[0], p[1] - cam[1], p[2] - cam[2]))
        dist = d.length
        if dist < 1e-6:
            continue
        d = d / dist
        hor = math.hypot(d.x, d.y)
        if hor < 1e-6:
            continue
        t2, nrm = ray_poly_t(cam[0], cam[1], d.x / hor, d.y / hor, pts)
        if t2 is None:
            t2 = math.hypot(p[0] - cam[0], p[1] - cam[1])
        t_face = t2 / hor
        if k == 0:
            t_face_center = t_face
            if nrm is not None:
                frontality = abs(view[0] * nrm[0] + view[1] * nrm[1])
        hit = bvh.ray_cast(Vector(cam), d, t_face + 40.0)
        if hit[0] is None:
            continue                      # nothing there at all: not a facade
        t_hit = (hit[0] - Vector(cam)).length
        if t_hit >= t_face - OCCLUSION_SLACK:
            clear += 1
    return clear / len(probes), t_face_center, frontality


def clutter(bvh, cam, target, t_face):
    """Fraction of the frame filled by geometry sitting right in front of the
    lens. Only counts hits at or above eye level, so the street surface running
    away under the camera does not read as an obstruction."""
    if t_face is None or t_face < 1.0:
        return 1.0
    quat = (Vector(target) - Vector(cam)).to_track_quat("-Z", "Y")
    sw = (SENSOR_W / 2.0) / LENS_DEFAULT
    sh = (SENSOR_W * RES_Y / RES_X / 2.0) / LENS_DEFAULT
    near, n = 0, 0
    for u in FAN_U:
        for v in FAN_V:
            d = quat @ Vector((u * 2 * sw, v * 2 * sh, -1.0))
            d.normalize()
            n += 1
            hit = bvh.ray_cast(Vector(cam), d, t_face * CLUTTER_NEAR)
            if hit[0] is not None and hit[0].z > cam[2] - 0.5:
                near += 1
    return near / max(n, 1)


def standoff_pref(d):
    return math.exp(-0.5 * ((d - STANDOFF_BEST) / STANDOFF_WIDTH) ** 2)


def facade_point(cam, cx, cy, pts, aim_z):
    """Where the sight line to the centroid crosses the footprint: the piece of
    wall actually being photographed. Framing must key off this, not off the
    centroid, or a deep building puts the wall in your face at full zoom."""
    dx, dy = cx - cam[0], cy - cam[1]
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return (cx, cy, aim_z), 0.0
    dx, dy = dx / L, dy / L
    t, _ = ray_poly_t(cam[0], cam[1], dx, dy, pts)
    if t is None or t > L:
        t = L
    return (cam[0] + dx * t, cam[1] + dy * t, aim_z), t


def open_sky(bvh, cam):
    """Nothing overhead: rejects spots inside a building or under an overhang."""
    return bvh.ray_cast(Vector(cam), Vector((0, 0, 1)), 60.0)[0] is None


def score_camera(bvh, cam, pts, cx, cy, target_z, ground_z, height, half_w):
    """(score, clear fraction, clutter, facade distance, passes clutter cap)."""
    _, t_hor = facade_point(cam, cx, cy, pts, target_z)
    if t_hor < MIN_FACADE_DIST:
        return None
    frac, t_face, front = visibility(bvh, cam, pts, cx, cy, target_z, ground_z,
                                     height, half_w)
    if t_face is None or frac < CLEAR_FRACTION:
        return None
    cl = clutter(bvh, cam, (cx, cy, target_z), t_face)
    s = frac * (1.0 - cl) ** 2 * standoff_pref(t_hor) * (0.3 + 0.7 * front)
    return s, frac, cl, t_hor, cl <= CLUTTER_MAX


def choose_camera(bvh, walk, pts, cx, cy, target_z, ground_z, height, half_w):
    """Walk sample with the best view of the facade: clear line, no near-field
    junk filling the lens, and a standoff the tile texel budget can support.
    Falls back to backing off along the target->walk direction."""
    d = np.linalg.norm(walk[:, :2] - [cx, cy], axis=1)
    order = [i for i in np.argsort(d) if MIN_CAM_DIST <= d[i] <= MAX_CAM_DIST]
    best, soft = None, None
    for i in order[:160:2]:
        cam = (float(walk[i, 0]), float(walk[i, 1]), float(walk[i, 2]) + EYE_HEIGHT)
        if point_in_poly(cam[0], cam[1], pts):
            continue
        s = score_camera(bvh, cam, pts, cx, cy, target_z, ground_z, height, half_w)
        if s is None:
            continue
        cand = (s[0], cam, s[1], s[2], float(d[i]), "walk", s[3])
        if s[4]:
            best = cand if best is None or cand[0] > best[0] else best
        else:
            soft = cand if soft is None or cand[0] > soft[0] else soft
    if best:
        return best[1], best[2], best[4], best[5], best[3], best[6]

    # nothing clean on the walk: back off along the target->walk direction.
    # These spots are invented rather than walked, so they have to prove they
    # are outdoors before they are allowed to beat an obstructed walk view.
    i0 = int(np.argmin(d))
    v = walk[i0, :2] - np.array([cx, cy])
    nv = np.linalg.norm(v)
    if nv > 1e-6:
        v = v / nv
        for dist in (MIN_CAM_DIST, 10.0, 14.0, 18.0, 24.0, 30.0, 40.0):
            x, y = cx + v[0] * dist, cy + v[1] * dist
            gz = ground_at(bvh, x, y)
            if gz is None or abs(gz - walk[i0, 2]) > 4.0:
                continue
            if point_in_poly(x, y, pts):
                continue
            cam = (float(x), float(y), float(gz) + EYE_HEIGHT)
            if not open_sky(bvh, cam):
                continue
            s = score_camera(bvh, cam, pts, cx, cy, target_z, ground_z, height,
                             half_w)
            if s and s[4] and (best is None or s[0] > best[0]):
                best = (s[0], cam, s[1], s[2], dist, "backoff", s[3])
    best = best or soft
    if best:
        return best[1], best[2], best[4], best[5], best[3], best[6]
    return None, 0.0, None, "none", 1.0, None


def pick_lens(cam, target, ground_z, height):
    """Widen until the ground line and the roof line both fit, within reason."""
    d = math.dist(cam, target)
    top = ground_z + height + 2.0
    half_span = max(target[2] - ground_z + 1.0, top - target[2]) * FRAME_MARGIN
    if d < 1e-6 or half_span < 1e-6:
        return LENS_DEFAULT
    sensor_h = SENSOR_W * RES_Y / RES_X
    lens = (sensor_h / 2.0) * d / half_span
    return float(min(LENS_MAX, max(LENS_MIN, lens)))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", default="data/osm_buildings.json")
    ap.add_argument("--relevance", default="data/relevance.json")
    ap.add_argument("--decisions", default="data/decisions.json")
    ap.add_argument("--gpx", default="data/walk.gpx")
    ap.add_argument("--out", default="renders/facades")
    ap.add_argument("--manifest", default="data/facade_manifest.json")
    ap.add_argument("--limit", type=int, default=MAX_BUILDINGS)
    ap.add_argument("--only", default=None)
    ap.add_argument("--skip-render", action="store_true")
    args = ap.parse_args(argv)

    osm = json.loads(pathlib.Path(args.osm).read_text())
    p0 = llh_to_ecef(osm["lat"], osm["lon"], 0.0)
    R = enu_rotation(osm["lat"], osm["lon"])
    rings = {b["id"]: b for b in osm["buildings"]}
    dec = {d["id"]: d for d in json.loads(
        pathlib.Path(args.decisions).read_text())["decisions"]}
    rel = json.loads(pathlib.Path(args.relevance).read_text())["buildings"]

    print("[bvh] building from photogrammetry...", flush=True)
    V, F = collect_world_triangles(bpy.data.collections["inhouse"])
    bvh = BVHTree.FromPolygons(V.tolist(), F.tolist(), all_triangles=True)
    print(f"[bvh] {len(F)} triangles", flush=True)
    walk = load_walk(args.gpx, R, p0, bvh)
    print(f"[walk] {len(walk)} samples, z {walk[:, 2].min():.1f}..{walk[:, 2].max():.1f}",
          flush=True)

    sel = [r for r in rel if r["tier"] == "detailed"
           or (r["tier"] == "prism" and r["d_walk"] <= PRISM_MAX_DWALK)]
    sel.sort(key=lambda r: -r["importance"])
    if args.only:
        keep = {int(s) for s in args.only.split(",")}
        sel = [r for r in sel if r["id"] in keep]
    sel = sel[:args.limit]
    print(f"[select] {len(sel)} buildings "
          f"({sum(1 for r in sel if r['tier'] == 'detailed')} detailed)", flush=True)

    # ---- scene setup: photogrammetry only, no OSM boxes in frame
    sc = bpy.context.scene
    for name in ("inhouse", "osm"):
        vl = sc.view_layers[0].layer_collection.children.get(name)
        if vl:
            vl.exclude = name != "inhouse"
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.device = "CPU"
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = "PNG"

    cam_data = bpy.data.cameras.new("cam_facade")
    cam_data.lens = LENS_DEFAULT
    cam_data.clip_start = 0.05
    cam_data.clip_end = 2000.0
    cam_obj = bpy.data.objects.new("cam_facade", cam_data)
    sc.collection.objects.link(cam_obj)
    sc.camera = cam_obj

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    manifest, n_ok, n_occ = [], 0, 0
    for n, r in enumerate(sel):
        bid = r["id"]
        b = rings.get(bid)
        d = dec.get(bid, {})
        row = {"id": bid,
               "name": (b or {}).get("tags", {}).get("name") or r.get("name"),
               "tier": r["tier"], "importance": r["importance"],
               "d_walk": r["d_walk"], "height_m": None,
               "camera_xyz": None, "target_xyz": None, "status": "occluded"}
        if b is None or len(b["ring"]) < 4:
            row["reason"] = "no footprint"
            manifest.append(row)
            n_occ += 1
            continue

        pts = ring_enu(b["ring"], R, p0)
        cx, cy, area = poly_centroid(pts)
        half_w = math.sqrt(max(area, 4.0)) * 0.5
        gz = d.get("ground_z")
        if gz is None:
            gz = ground_at(bvh, cx, cy) or 50.0
        height = d.get("h_final") or d.get("h_photo_p75") or 9.0
        target_z = gz + min(height * 0.5, AIM_HEIGHT_CAP)
        row["height_m"] = round(float(height), 1)

        cam, frac, dist, how, cl, t_face = choose_camera(
            bvh, walk, pts, cx, cy, target_z, gz, height, half_w)
        target = (cx, cy, target_z)
        if cam is not None:
            # from a few metres away, aiming at half the building height points
            # the lens at the sky; hold the elevation under about 30 degrees
            aim_z = gz + min(height * 0.5, AIM_HEIGHT_CAP,
                             max(2.0, EYE_HEIGHT + 0.6 * t_face))
            target, t_face = facade_point(cam, cx, cy, pts, aim_z)
        row["target_xyz"] = [round(v, 2) for v in target]
        if cam is None or frac < CLEAR_FRACTION:
            row["reason"] = f"no clear line (best {frac:.1f})"
            if cam is not None:
                row["camera_xyz"] = [round(v, 2) for v in cam]
            manifest.append(row)
            n_occ += 1
            stale = outdir / f"{bid}.png"      # do not leave a previous run's
            if stale.exists() and not args.skip_render:   # shot behind
                stale.unlink()
            print(f"[{n + 1}/{len(sel)}] {bid} OCCLUDED ({row['reason']})", flush=True)
            continue

        row["camera_xyz"] = [round(v, 2) for v in cam]
        row["status"] = "rendered"
        row["clear_fraction"] = round(frac, 2)
        row["frame_clutter"] = round(cl, 2)
        row["cam_dist_m"] = round(dist, 1)
        row["facade_dist_m"] = round(t_face, 1)
        row["cam_source"] = how
        cam_obj.location = cam
        cam_data.lens = pick_lens(cam, target, gz, height)
        cam_obj.rotation_euler = (Vector(target) - Vector(cam)) \
            .to_track_quat("-Z", "Y").to_euler()
        row["lens_mm"] = round(cam_data.lens, 1)
        path = outdir / f"{bid}.png"
        if not args.skip_render:
            sc.render.filepath = str(path.resolve())
            bpy.ops.render.render(write_still=True)
        manifest.append(row)
        n_ok += 1
        print(f"[{n + 1}/{len(sel)}] {bid} {row['name'] or ''} d={dist:.1f}m "
              f"face={t_face:.1f}m lens={cam_data.lens:.0f}mm clear={frac:.1f} "
              f"clutter={cl:.2f} -> {path}", flush=True)

    pathlib.Path(args.manifest).write_text(json.dumps(manifest, indent=1))
    print(f"[done] rendered {n_ok}, occluded {n_occ} -> {args.manifest}")


main()
