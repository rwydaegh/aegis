"""Export three Sionna RT scene variants (Mitsuba XML + binary PLY) for an ablation.

Two modes, selected by whether ``bpy`` is importable:

  export    ~/blender-4.5/blender -b scene_hybrid.blend -P export_scenes.py
  validate  /home/user/aegis/.venv/bin/python export_scenes.py --validate

The three variants, all in the same local ENU frame (metres, z up, origin at the
osm_buildings.json anchor):

  scenes/hybrid/scene.xml  relevance-tiered hybrid. Detailed-tier buildings are
                           carved out of the photogrammetry, prism-tier buildings
                           are clean extrusions on their own audited ground level,
                           dropped-tier buildings are gone. Plus a raycast terrain
                           and canopy proxy volumes for the vegetation blobs.
  scenes/osm/scene.xml     naive OSM: every footprint extruded, one flat ground
                           level for all of them, same terrain mesh.
  scenes/photo/scene.xml   naive photogrammetry: the raw Google mesh, one material.

Material ids follow the convention Sionna's ``process_xml`` recognises: a BSDF
whose id is ``mat-itu_<name>`` (or ``itu_<name>``) is rewritten into the
``itu-radio-material`` plugin with ``type=<name>``. Verified against
sionna/rt/scene_utils.py:75-121 in sionna-rt 2.0.1.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np

try:
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import tessellate_polygon

    IN_BLENDER = True
except ImportError:  # running under the venv python for validation
    IN_BLENDER = False

WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3

HALF = 210.0            # half-extent of the exported terrain [m]
SAMPLE_GRID = 4.0       # raycast spacing used to sample the photogrammetry [m]
TERRAIN_GRID = 10.0     # spacing of the exported terrain triangulation [m]
GROUND_PCTL = 25.0      # percentile of local ground hits (rejects cars/awnings)
GROUND_RADII = (25.0, 50.0, 100.0)
SEED_PCTL = 5.0         # low percentile over a wide window: seeds the ground level
SEED_RADII = (60.0, 120.0, 400.0)
SEED_TOL = 3.0          # a sample this far above the seed is a roof, not ground
BASE_TOL = 3.0          # audited ground this far above terrain is a roof, clamp it
CARVE_RING_PAD = 2.0    # keep photogrammetry this far outside a carved footprint
CARVE_Z_CLEAR = 1.0     # drop carved triangles below ground + this (that is terrain)
CANOPY_BASE_FRAC = 0.35  # trunk gap: canopy proxy spans [0.35 h, h]
DEFAULT_THICKNESS = 0.1

# sionna.rt.radio_materials.itu.ITU_MATERIALS_PROPERTIES keys (sionna-rt 2.0.1).
# Duplicated here because Blender's python has no sionna; validated in --validate.
ITU_MATERIALS = (
    "concrete", "brick", "plasterboard", "wood", "glass", "ceiling_board",
    "chipboard", "plywood", "marble", "floorboard", "metal", "very_dry_ground",
    "medium_dry_ground", "wet_ground",
)

MAT_PRISM = "brick"
MAT_CARVED = "marble"
MAT_GROUND = "medium_dry_ground"
MAT_VEG = "wood"
MAT_PHOTO = "concrete"


# --------------------------------------------------------------------------- geo
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


def point_in_poly(px, py, ring):
    """Vectorised ray crossing. px, py arrays; ring list of (x, y)."""
    x = np.asarray([p[0] for p in ring])
    y = np.asarray([p[1] for p in ring])
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    px, py = px[:, None], py[:, None]
    cond = (y[None] > py) != (y2[None] > py)
    with np.errstate(divide="ignore", invalid="ignore"):
        xin = (x2 - x)[None] * (py - y[None]) / (y2 - y)[None] + x[None]
    return (cond & (px < xin)).sum(axis=1) % 2 == 1


def dist_to_ring(px, py, ring):
    p = np.stack([px, py], axis=1)[:, None, :]
    a = np.array(ring)
    b = np.roll(a, -1, axis=0)
    ab = (b - a)[None]
    ap = p - a[None]
    t = np.clip((ap * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12), 0, 1)
    return np.linalg.norm(ap - t[..., None] * ab, axis=-1).min(axis=1)


def signed_area(pts):
    x = np.asarray([p[0] for p in pts])
    y = np.asarray([p[1] for p in pts])
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def load_footprints(osm):
    """OSM rings -> CCW ENU xy polygons, keyed by osm id."""
    lat0, lon0 = osm["lat"], osm["lon"]
    p0 = llh_to_ecef(lat0, lon0, 0.0)
    rot = enu_rotation(lat0, lon0)
    out = {}
    for b in osm["buildings"]:
        ring = b["ring"][:-1]
        if len(ring) < 3:
            continue
        pts = []
        for lo, la in ring:
            e = rot @ (llh_to_ecef(la, lo, 0.0) - p0)
            pts.append((float(e[0]), float(e[1])))
        # drop consecutive duplicates
        clean = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - clean[-1][0]) > 1e-6 or abs(p[1] - clean[-1][1]) > 1e-6:
                clean.append(p)
        if len(clean) < 3:
            continue
        if signed_area(clean) < 0:
            clean.reverse()
        out[b["id"]] = clean
    return out, p0, rot


# --------------------------------------------------------------------------- ply
def write_ply(path, verts, faces):
    """Binary little-endian PLY, float32 positions, uchar/int32 triangle list."""
    v = np.ascontiguousarray(verts, dtype=np.float32).reshape(-1, 3)
    f = np.ascontiguousarray(faces, dtype=np.int32).reshape(-1, 3)
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "comment hybrid_twin export_scenes.py, local ENU metres, z up\n"
        f"element vertex {len(v)}\n"
        "property float x\nproperty float y\nproperty float z\n"
        f"element face {len(f)}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n")
    rec = np.empty(len(f), dtype=[("n", "u1"), ("i", "<i4", (3,))])
    rec["n"] = 3
    rec["i"] = f
    with open(path, "wb") as fh:
        fh.write(header.encode("ascii"))
        fh.write(v.astype("<f4").tobytes())
        fh.write(rec.tobytes())
    return len(v), len(f)


def drop_degenerate(V, F, eps=1e-9):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    area2 = np.linalg.norm(np.cross(b - a, c - a), axis=1)
    return F[area2 > eps]


def compact(V, F):
    used = np.unique(F)
    remap = np.zeros(len(V), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[F]


# ----------------------------------------------------------------- mesh builders
def prism(pts, z0, z1):
    """Closed extrusion of a CCW footprint. Outward normals, ear-clipped caps."""
    nv = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = []
    for i in range(nv):
        j = (i + 1) % nv
        # (bottom_i, bottom_j, top_j, top_i) -> normal points out of a CCW ring
        faces.append((i, j, nv + j))
        faces.append((i, nv + j, nv + i))
    cap = tessellate_polygon([[Vector((x, y, 0.0)) for x, y in pts]])
    for t in cap:
        faces.append((nv + t[0], nv + t[1], nv + t[2]))      # roof, +z
        faces.append((t[2], t[1], t[0]))                      # floor, -z
    return np.array(verts, dtype=np.float64), np.array(faces, dtype=np.int64)


def ellipsoid(cx, cy, cz, rx, ry, rz, n_phi=16, n_theta=8):
    verts = [(cx, cy, cz + rz)]
    for i in range(1, n_theta):
        th = math.pi * i / n_theta
        st, ct = math.sin(th), math.cos(th)
        for j in range(n_phi):
            ph = 2 * math.pi * j / n_phi
            verts.append((cx + rx * st * math.cos(ph),
                          cy + ry * st * math.sin(ph),
                          cz + rz * ct))
    verts.append((cx, cy, cz - rz))
    bot = len(verts) - 1
    faces = []

    def idx(ring, j):
        return 1 + ring * n_phi + (j % n_phi)

    for j in range(n_phi):
        faces.append((0, idx(0, j), idx(0, j + 1)))
    for r in range(n_theta - 2):
        for j in range(n_phi):
            faces.append((idx(r, j), idx(r + 1, j), idx(r + 1, j + 1)))
            faces.append((idx(r, j), idx(r + 1, j + 1), idx(r, j + 1)))
    for j in range(n_phi):
        faces.append((bot, idx(n_theta - 2, j + 1), idx(n_theta - 2, j)))
    return np.array(verts, dtype=np.float64), np.array(faces, dtype=np.int64)


# ------------------------------------------------------------------------- blend
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


def local_percentile(pts, vals, node_xy, radii, pct, fallback, block=256):
    """Percentile of vals within the first radius holding >= 5 samples, per node."""
    out = np.full(len(node_xy), fallback, dtype=np.float64)
    for c0 in range(0, len(node_xy), block):
        blk = node_xy[c0:c0 + block]
        d2 = ((blk[:, None, 0] - pts[None, :, 0]) ** 2
              + (blk[:, None, 1] - pts[None, :, 1]) ** 2)
        for k in range(len(blk)):
            row = d2[k]
            for rad in radii:
                sel = vals[row < rad * rad]
                if len(sel) >= 5:
                    out[c0 + k] = float(np.percentile(sel, pct))
                    break
    return out


def smooth3(z):
    p = np.pad(z, 1, mode="edge")
    return sum(p[i:i + z.shape[0], j:j + z.shape[1]]
               for i in range(3) for j in range(3)) / 9.0


def sample_ground(bvh, footprints, cache_path, force=False):
    """Raycast the photogrammetry, keep off-footprint hits, fit a terrain grid.

    Two passes, because "off any OSM footprint" is not the same as "on the
    ground": unmapped buildings put whole neighbourhoods of samples on roofs.
    Pass 1 seeds a smooth low-percentile surface over a wide window, pass 2
    rejects every sample more than SEED_TOL above that seed and refits locally.

    Returns (terrain_dict, ground_pts Nx2, ground_z N). The terrain dict is the
    JSON-serialisable cache: origin, step, n and the node heights.
    """
    key = {"half": HALF, "sample": SAMPLE_GRID, "terrain": TERRAIN_GRID,
           "pctl": GROUND_PCTL, "radii": list(GROUND_RADII),
           "seed": [SEED_PCTL, SEED_TOL, list(SEED_RADII)]}
    cache = pathlib.Path(cache_path)
    if cache.exists() and not force:
        blob = json.loads(cache.read_text())
        if blob.get("key") == key:
            print("[terrain] using cache", cache)
            return (blob["terrain"], np.array(blob["ground_xy"]),
                    np.array(blob["ground_z"]))

    ax = np.arange(-HALF, HALF + SAMPLE_GRID, SAMPLE_GRID)
    gx, gy = np.meshgrid(ax, ax)
    gx, gy = gx.ravel(), gy.ravel()
    print(f"[terrain] raycasting {len(gx)} sample points...", flush=True)
    gz = np.full(len(gx), np.nan)
    down = Vector((0, 0, -1))
    for i in range(len(gx)):
        h = bvh.ray_cast(Vector((float(gx[i]), float(gy[i]), 500.0)), down, 1000.0)
        if h[0] is not None:
            gz[i] = h[0].z
    valid = ~np.isnan(gz)
    inside_any = np.zeros(len(gx), dtype=bool)
    for pts in footprints.values():
        inside_any |= point_in_poly(gx, gy, pts)
    mask = valid & ~inside_any
    gpts = np.stack([gx[mask], gy[mask]], axis=1)
    gzs = gz[mask]
    z_global = float(np.percentile(gzs, GROUND_PCTL))
    print(f"[terrain] {mask.sum()} street-level samples, global {z_global:.2f} m",
          flush=True)

    nodes = np.arange(-HALF, HALF + TERRAIN_GRID, TERRAIN_GRID)
    n = len(nodes)
    nx, ny = np.meshgrid(nodes, nodes)
    node_xy = np.stack([nx.ravel(), ny.ravel()], axis=1)   # index iy * n + ix

    seed = local_percentile(gpts, gzs, node_xy, SEED_RADII, SEED_PCTL, z_global)
    seed = smooth3(seed.reshape(n, n))
    seed_grid = {"x0": float(-HALF), "step": float(TERRAIN_GRID), "n": int(n),
                 "z": seed}
    at_sample = np.array([terrain_z(seed_grid, x, y) for x, y in gpts])
    keep = gzs < at_sample + SEED_TOL
    print(f"[terrain] seed rejects {int((~keep).sum())} of {len(gzs)} samples as"
          " roofs of unmapped structures", flush=True)

    zt = local_percentile(gpts[keep], gzs[keep], node_xy, GROUND_RADII,
                          GROUND_PCTL, z_global).reshape(n, n)
    zt = smooth3(zt)
    terrain = {"x0": float(-HALF), "step": float(TERRAIN_GRID), "n": int(n),
               "z_global": z_global, "z_flat": float(np.median(zt)),
               "z": zt.tolist()}
    cache.write_text(json.dumps(
        {"key": key, "terrain": terrain, "ground_xy": gpts.round(2).tolist(),
         "ground_z": gzs.round(3).tolist()}))
    print(f"[terrain] {n}x{n} nodes, z in "
          f"[{zt.min():.2f}, {zt.max():.2f}] m -> {cache}", flush=True)
    return terrain, gpts, gzs


def terrain_z(terrain, x, y):
    """Bilinear lookup on the terrain grid, clamped at the border."""
    z = np.asarray(terrain["z"])
    n, x0, st = terrain["n"], terrain["x0"], terrain["step"]
    fx = min(max((x - x0) / st, 0.0), n - 1.001)
    fy = min(max((y - x0) / st, 0.0), n - 1.001)
    ix, iy = int(fx), int(fy)
    tx, ty = fx - ix, fy - iy
    return float((1 - ty) * ((1 - tx) * z[iy, ix] + tx * z[iy, ix + 1])
                 + ty * ((1 - tx) * z[iy + 1, ix] + tx * z[iy + 1, ix + 1]))


def terrain_mesh(terrain):
    n, x0, st = terrain["n"], terrain["x0"], terrain["step"]
    z = np.asarray(terrain["z"])
    xs = x0 + st * np.arange(n)
    gx, gy = np.meshgrid(xs, xs)
    V = np.stack([gx.ravel(), gy.ravel(), z.ravel()], axis=1)
    faces = []
    for iy in range(n - 1):
        for ix in range(n - 1):
            a = iy * n + ix
            b = a + 1
            c = a + n
            d = c + 1
            faces.append((a, b, d))   # CCW seen from +z
            faces.append((a, d, c))
    return V, np.array(faces, dtype=np.int64)


# --------------------------------------------------------------------------- xml
def scene_xml(shapes, comments=()):
    """shapes: list of (mesh_id, ply_relpath, itu_material_name)."""
    mats = sorted({m for _, _, m in shapes})
    out = ['<scene version="2.1.0">', ""]
    for c in comments:
        out.append(f"<!-- {c} -->")
    out += ["", "<!-- Materials -->", ""]
    for m in mats:
        out += [f'\t<bsdf type="itu-radio-material" id="mat-itu_{m}">',
                f'\t\t<string name="type" value="{m}"/>',
                f'\t\t<float name="thickness" value="{DEFAULT_THICKNESS}"/>',
                "\t</bsdf>"]
    out += ["", "<!-- Shapes -->", ""]
    for mid, ply, mat in shapes:
        out += [f'\t<shape type="ply" id="mesh-{mid}" name="mesh-{mid}">',
                f'\t\t<string name="filename" value="{ply}"/>',
                '\t\t<boolean name="face_normals" value="true"/>',
                f'\t\t<ref id="mat-itu_{mat}" name="bsdf"/>',
                "\t</shape>"]
    out += ["", "</scene>", ""]
    return "\n".join(out)


# ------------------------------------------------------------------------ export
def run_export(args):
    root = pathlib.Path(args.root).resolve()
    data = root / "data"
    osm = json.loads((data / args.osm).read_text())
    decisions = json.loads((data / "decisions.json").read_text())
    relevance = json.loads((data / "relevance.json").read_text())
    dec = {r["id"]: r for r in decisions["decisions"]}
    tier = {b["id"]: b["tier"] for b in relevance["buildings"]}
    blobs = decisions["unmapped_blobs"]

    mats_path = pathlib.Path(args.materials) if args.materials \
        else data / "materials.json"
    per_building = {}
    if mats_path.exists():
        raw = json.loads(mats_path.read_text())
        raw = raw.get("materials", raw) if isinstance(raw, dict) else raw
        bad = []
        for k, v in raw.items():
            name = str(v).strip().lower()
            if name.startswith("mat-"):
                name = name[4:]
            if name.startswith("itu_") or name.startswith("itu-"):
                name = name[4:]
            if name in ITU_MATERIALS:
                per_building[int(k)] = name
            else:
                bad.append((k, v))
        print(f"[materials] {mats_path} -> {len(per_building)} assignments"
              + (f", {len(bad)} unknown names ignored (e.g. {bad[:3]})" if bad else ""))
    else:
        print(f"[materials] {mats_path} absent, using defaults "
              f"(prism={MAT_PRISM}, carved={MAT_CARVED}, ground={MAT_GROUND}, "
              f"veg={MAT_VEG})")

    footprints, _p0, _rot = load_footprints(osm)
    print(f"[osm] {len(footprints)} usable footprints")

    print("[bvh] collecting google triangles...", flush=True)
    V, F = collect_world_triangles(bpy.data.collections["google"])
    F = drop_degenerate(V, F)
    print(f"[bvh] {len(V)} verts, {len(F)} tris", flush=True)
    bvh = BVHTree.FromPolygons(V.tolist(), F.tolist(), all_triangles=True)

    terrain, _gxy, _gz = sample_ground(bvh, footprints,
                                       data / "terrain_grid.json", args.refresh_terrain)
    z_flat = terrain["z_flat"]

    n_clamped = [0]

    def base_of(bid):
        """Ground level a building sits on, sanity-checked against the terrain.

        decisions.json measured each building's ground from off-footprint cells
        near it, which lands on a roof where a neighbour is missing from OSM.
        Those bases float; clamp them back onto the terrain.
        """
        pts = footprints[bid]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        gt = terrain_z(terrain, cx, cy)
        g = dec.get(bid, {}).get("ground_z", gt)
        if g > gt + BASE_TOL or g < gt - BASE_TOL:
            n_clamped[0] += 1
            g = gt
        return g

    # ---- carve set: relevance "detailed" plus the audit's landmark-keep-photo.
    # A landmark that the height audit flagged as "a box would lie" stays
    # photogrammetric even if the relevance pass only ranked it prism.
    detailed = {b for b, t in tier.items() if t == "detailed"}
    landmarks = {r["id"] for r in decisions["decisions"]
                 if r["decision"] == "landmark-keep-photo"}
    carve_ids = sorted((detailed | landmarks) & set(footprints))
    prism_ids = sorted(b for b, t in tier.items()
                       if t == "prism" and b not in carve_ids and b in footprints)
    dropped_ids = sorted(b for b, t in tier.items() if t == "dropped")
    print(f"[tiers] carve {len(carve_ids)} (detailed {len(detailed)} + landmarks "
          f"{len(landmarks)}), prism {len(prism_ids)}, dropped {len(dropped_ids)}")

    cent = V[F].mean(axis=1)
    claimed = np.zeros(len(F), dtype=bool)
    carve_masks = {}
    for bid in carve_ids:                      # interiors first, then the pad ring
        m = point_in_poly(cent[:, 0], cent[:, 1], footprints[bid]) & ~claimed
        carve_masks[bid] = m
        claimed |= m
    for bid in carve_ids:
        m = (dist_to_ring(cent[:, 0], cent[:, 1], footprints[bid])
             < CARVE_RING_PAD) & ~claimed
        carve_masks[bid] |= m
        claimed |= m

    # ---------------------------------------------------------------- hybrid
    hyb = root / "scenes" / "hybrid"
    (hyb / "meshes").mkdir(parents=True, exist_ok=True)
    shapes, stats = [], {"tris": 0, "verts": 0}

    def emit(scene_dir, shape_list, mid, Vm, Fm, mat):
        Fm = drop_degenerate(np.asarray(Vm, dtype=np.float64), np.asarray(Fm))
        if len(Fm) == 0:
            return 0
        Vc, Fc = compact(np.asarray(Vm, dtype=np.float64), Fm)
        rel = f"meshes/{mid}.ply"
        nv, nf = write_ply(scene_dir / rel, Vc, Fc)
        shape_list.append((mid, rel, mat))
        stats["verts"] += nv
        stats["tris"] += nf
        return nf

    for bid in carve_ids:
        m = carve_masks[bid]
        gzb = base_of(bid)
        if m.sum() == 0:
            print(f"  [warn] carve {bid} has no photogrammetry, falling back to prism")
            Vm, Fm = prism(footprints[bid], gzb - 0.5, gzb + dec[bid]["h_final"])
            emit(hyb, shapes, f"bldg_{bid}", Vm, Fm,
                 per_building.get(bid, MAT_PRISM))
            continue
        keep = m & (cent[:, 2] > gzb + CARVE_Z_CLEAR)   # shed the street underneath
        if keep.sum() < 20:
            keep = m
        emit(hyb, shapes, f"detail_{bid}", V, F[keep],
             per_building.get(bid, MAT_CARVED))

    for bid in prism_ids:
        g = base_of(bid)
        Vm, Fm = prism(footprints[bid], g - 0.5, g + dec[bid]["h_final"])
        emit(hyb, shapes, f"bldg_{bid}", Vm, Fm, per_building.get(bid, MAT_PRISM))
    print(f"[hybrid] {n_clamped[0]} building bases clamped onto the terrain")

    Vt, Ft = terrain_mesh(terrain)
    emit(hyb, shapes, "terrain", Vt, Ft, MAT_GROUND)

    n_veg = 0
    for i, bl in enumerate(b for b in blobs if b["guess"] == "vegetation"):
        r = max(math.sqrt(bl["area_m2"] / math.pi), 2.0)
        h = max(bl["h_mean"], 3.0)
        gz = terrain_z(terrain, bl["x"], bl["y"])
        z0 = gz + CANOPY_BASE_FRAC * h
        rz = 0.5 * (h - CANOPY_BASE_FRAC * h)
        Vm, Fm = ellipsoid(bl["x"], bl["y"], z0 + rz, r, r, rz)
        if emit(hyb, shapes, f"veg_{i}", Vm, Fm, MAT_VEG):
            n_veg += 1

    (hyb / "scene.xml").write_text(scene_xml(shapes, comments=[
        "Hybrid twin, Korenmarkt Ghent. Local ENU frame, metres, z up.",
        f"detail_* = photogrammetry carved per footprint ({len(carve_ids)} buildings:"
        " relevance tier 'detailed' + the height audit's 'landmark-keep-photo').",
        f"bldg_* = OSM extrusion at the audited height on its own measured ground"
        f" level ({len(prism_ids)} buildings).",
        f"{len(dropped_ids)} relevance tier 'dropped' buildings are omitted.",
        "terrain = 10 m triangulation of the photogrammetry street level.",
        f"veg_* = {n_veg} canopy proxy volumes for the blobs decisions.json"
        " classified as vegetation. They carry itu_wood only as a placeholder:"
        " a canopy is a lossy VOLUME, not a slab. The runner is expected to"
        " replace this BSDF with a specific-attenuation material derived from"
        " ITU-R P.833 rather than to trust itu_wood.",
    ]))
    print(f"[hybrid] {len(shapes)} shapes, {stats['tris']} tris -> {hyb/'scene.xml'}")
    hybrid_stats = dict(stats, shapes=len(shapes))

    # ------------------------------------------------------------------- osm
    osm_dir = root / "scenes" / "osm"
    (osm_dir / "meshes").mkdir(parents=True, exist_ok=True)
    shapes, stats = [], {"tris": 0, "verts": 0}
    base = z_flat - 10.0    # bury bases so nothing floats over the shared terrain
    n_tag = n_meas = n_def = 0
    for bid, pts in footprints.items():
        rec = dec.get(bid, {})
        h = rec.get("h_tag")
        if h:
            n_tag += 1
        elif rec.get("h_photo_p75"):
            h = rec["h_photo_p75"]
            n_meas += 1
        else:
            h = 12.0
            n_def += 1
        Vm, Fm = prism(pts, base, z_flat + float(h))
        emit(osm_dir, shapes, f"bldg_{bid}", Vm, Fm, per_building.get(bid, MAT_PRISM))
    emit(osm_dir, shapes, "terrain", Vt, Ft, MAT_GROUND)
    (osm_dir / "scene.xml").write_text(scene_xml(shapes, comments=[
        "Naive OSM baseline, Korenmarkt Ghent. Local ENU frame, metres, z up.",
        f"Every footprint extruded ({len(footprints)}): {n_tag} from an OSM height or"
        f" levels tag, {n_meas} from the photogrammetry measurement, {n_def} at the"
        " 12 m default.",
        f"All bases sit on one flat level ({z_flat:.2f} m), which is the point:"
        " OSM alone has no terrain. The terrain mesh is shared with the hybrid"
        " scene so the ablation isolates the building representation; prism bases"
        " are sunk 10 m so no building floats above the real ground.",
    ]))
    print(f"[osm] {len(shapes)} shapes, {stats['tris']} tris -> {osm_dir/'scene.xml'}")
    osm_stats = dict(stats, shapes=len(shapes))

    # ----------------------------------------------------------------- photo
    ph = root / "scenes" / "photo"
    (ph / "meshes").mkdir(parents=True, exist_ok=True)
    shapes, stats = [], {"tris": 0, "verts": 0}
    emit(ph, shapes, "photogrammetry", V, F, MAT_PHOTO)
    (ph / "scene.xml").write_text(scene_xml(shapes, comments=[
        "Naive photogrammetry baseline, Korenmarkt Ghent. Local ENU frame, metres.",
        "The raw Google Photorealistic 3D Tiles mesh, unsegmented, one material."
        " Terrain, buildings, trees and street furniture are one object because"
        " the source has no semantics to split them by.",
    ]))
    print(f"[photo] {len(shapes)} shapes, {stats['tris']} tris -> {ph/'scene.xml'}")
    photo_stats = dict(stats, shapes=len(shapes))

    summary = {"hybrid": hybrid_stats, "osm": osm_stats, "photo": photo_stats,
               "carve_ids": carve_ids, "n_prism": len(prism_ids),
               "n_dropped": len(dropped_ids), "n_vegetation": n_veg,
               "n_bases_clamped": n_clamped[0],
               "z_flat": z_flat, "z_global": terrain["z_global"],
               "terrain_z_range": [float(np.min(Vt[:, 2])), float(np.max(Vt[:, 2]))],
               "materials_json": bool(per_building)}
    (root / "scenes" / "export_summary.json").write_text(json.dumps(summary, indent=1))
    print("[summary]", json.dumps({k: summary[k] for k in
                                   ("hybrid", "osm", "photo", "n_vegetation")}))
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=str((root / args.blend).resolve()))
    print("[done]")


# ---------------------------------------------------------------------- validate
def probe_surface(scene, x, y, z_from=400.0):
    """Height of the topmost surface of a loaded Mitsuba scene at (x, y)."""
    import mitsuba as mi

    r = mi.Ray3f(o=mi.Point3f(x, y, z_from), d=mi.Vector3f(0.0, 0.0, -1.0))
    si = scene.mi_scene.ray_intersect(r)
    if not bool(np.asarray(si.is_valid())[0]):
        return None
    return float(np.asarray(si.p).ravel()[2])


def run_validate(args):
    import xml.etree.ElementTree as ET

    from sionna.rt import PathSolver, PlanarArray, Receiver, Transmitter, load_scene
    from sionna.rt.radio_materials.itu import ITU_MATERIALS_PROPERTIES

    unknown = [m for m in ITU_MATERIALS if m not in ITU_MATERIALS_PROPERTIES]
    assert not unknown, f"stale ITU material list in this file: {unknown}"

    root = pathlib.Path(args.root).resolve()
    data = root / "data"
    osm = json.loads((data / args.osm).read_text())
    p0 = llh_to_ecef(osm["lat"], osm["lon"], 0.0)
    rot = enu_rotation(osm["lat"], osm["lon"])
    terrain = json.loads((data / "terrain_grid.json").read_text())["terrain"]

    sites = json.loads((data / "sites.json").read_text())
    s = sites[0]
    e = rot @ (llh_to_ecef(s["lat"], s["lon"]) - p0)
    tx_xy = (float(e[0]), float(e[1]))

    pts = []
    for tp in ET.parse(data / "walk.gpx").getroot().iter(
            "{http://www.topografix.com/GPX/1/1}trkpt"):
        w = rot @ (llh_to_ecef(float(tp.get("lat")), float(tp.get("lon"))) - p0)
        pts.append((float(w[0]), float(w[1])))
    # the walk point closest to the site, so the trace has something to find
    rx_xy = min(pts, key=lambda p: (p[0] - tx_xy[0]) ** 2 + (p[1] - tx_xy[1]) ** 2)

    names = ("hybrid", "osm", "photo")
    scenes, failed = {}, []
    for name in names:
        xml = root / "scenes" / name / "scene.xml"
        try:
            scenes[name] = load_scene(str(xml), merge_shapes=True)
        except Exception as exc:  # noqa: BLE001 - report and keep going
            failed.append(name)
            print(f"[{name:6s}] LOAD FAILED: {type(exc).__name__}: {exc}")

    # The three scenes disagree about where the ground is (that is the experiment),
    # so put the terminals above the highest of the three surfaces. Otherwise the
    # receiver ends up buried in the photogrammetry and no scene is comparable.
    surf = {n: probe_surface(sc, *rx_xy) for n, sc in scenes.items()}
    surf_tx = {n: probe_surface(sc, *tx_xy) for n, sc in scenes.items()}
    rx_g = max([v for v in surf.values() if v is not None]
               + [terrain_z(terrain, *rx_xy)])
    tx_g = terrain_z(terrain, *tx_xy)
    tx_z = max([tx_g + s["height"]]
               + [v + 2.0 for v in surf_tx.values() if v is not None])
    tx_pos = [tx_xy[0], tx_xy[1], tx_z]
    rx_pos = [rx_xy[0], rx_xy[1], rx_g + 1.5]
    print(f"tx (site {s['site']}, h={s['height']} m) = "
          f"{[round(v, 2) for v in tx_pos]}")
    print(f"rx (nearest walk point, 1.5 m agl) = {[round(v, 2) for v in rx_pos]}")
    print(f"tx-rx distance = {math.dist(tx_pos, rx_pos):.1f} m")
    print("surface under rx per scene: "
          + ", ".join(f"{n}={surf[n]:.2f}" for n in scenes if surf[n] is not None))
    print("surface under tx per scene: "
          + ", ".join(f"{n}={surf_tx[n]:.2f}" for n in scenes
                      if surf_tx[n] is not None) + "\n")

    for name in names:
        xml = root / "scenes" / name / "scene.xml"
        n_shapes = len(ET.parse(xml).getroot().findall("shape"))
        if name not in scenes:
            continue
        try:
            scene = scenes[name]
            scene.frequency = args.frequency
            scene.tx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                         polarization="V")
            scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                         polarization="V")
            scene.add(Transmitter("tx", position=tx_pos))
            scene.add(Receiver("rx", position=rx_pos))
            tris = sum(int(o.mi_mesh.face_count()) for o in scene.objects.values())
            solver = PathSolver()
            paths = solver(scene, max_depth=args.max_depth,
                           samples_per_src=args.samples, los=True,
                           specular_reflection=True, diffraction=False)
            tau = np.asarray(paths.tau).ravel()
            n_paths = int((tau >= 0).sum())
            a_r, a_i = paths.a
            g = (np.asarray(a_r) ** 2 + np.asarray(a_i) ** 2).ravel()
            g = g[g > 0]
            best = 10 * math.log10(g.max()) if len(g) else float("nan")
            tot = 10 * math.log10(g.sum()) if len(g) else float("nan")
            print(f"[{name:6s}] load ok  xml_shapes={n_shapes:4d}  "
                  f"sionna_objects={len(scene.objects):4d}  "
                  f"materials={len(scene.radio_materials):2d}  "
                  f"triangles={tris:7d}  paths={n_paths:3d}  "
                  f"best={best:7.1f} dB  sum={tot:7.1f} dB")
        except Exception as exc:  # noqa: BLE001 - report and keep going
            failed.append(name)
            print(f"[{name:6s}] TRACE FAILED: {type(exc).__name__}: {exc}")
    if failed:
        sys.exit(1)


# --------------------------------------------------------------------------- cli
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else (
        [] if IN_BLENDER else sys.argv[1:])
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parent))
    ap.add_argument("--osm", default="osm_buildings.json")
    ap.add_argument("--blend", default="", help="optional debug .blend to save")
    ap.add_argument("--materials", default="",
                    help="per-building material map, default data/materials.json")
    ap.add_argument("--refresh-terrain", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--frequency", type=float, default=3.5e9)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--samples", type=int, default=1000000)
    args = ap.parse_args(argv)
    if IN_BLENDER and not args.validate:
        run_export(args)
    else:
        run_validate(args)


main()
