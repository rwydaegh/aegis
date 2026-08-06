"""PoC: relevance-driven LOD. Importance of every surface w.r.t. a walk + real sites.

Run: blender -b scene_hybrid.blend -P poc_relevance.py -- \
    --osm data/osm_buildings.json --sites data/sites.json --gpx data/walk.gpx
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import xml.etree.ElementTree as ET

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3
RAYS_PER_SITE = 40000
NEAR_MISS = 2.5          # m, reflected ray counts if it passes this close to the walk
WALK_STEP = 1.0          # m
CONTEXT_RADIUS = 120.0   # m, keep prisms within this range of the walk even if cold


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


def point_in_poly(px, py, ring):
    x = np.asarray([p[0] for p in ring])
    y = np.asarray([p[1] for p in ring])
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    px, py = px[:, None], py[:, None]
    cond = (y[None] > py) != (y2[None] > py)
    with np.errstate(divide="ignore", invalid="ignore"):
        xin = (x2 - x)[None] * (py - y[None]) / (y2 - y)[None] + x[None]
    return (cond & (px < xin)).sum(axis=1) % 2 == 1


def load_walk(gpx_path, R, p0, bvh):
    pts = []
    root = ET.parse(gpx_path).getroot()
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    for tp in root.iter("{http://www.topografix.com/GPX/1/1}trkpt"):
        lat, lon = float(tp.get("lat")), float(tp.get("lon"))
        e = R @ (llh_to_ecef(lat, lon) - p0)
        pts.append(e[:2])
    pts = np.array(pts)
    # resample at WALK_STEP
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        seg = b - a
        n = max(int(np.linalg.norm(seg) / WALK_STEP), 1)
        for i in range(n):
            out.append(a + seg * (i / n))
    out.append(pts[-1])
    out = np.array(out)
    z = np.empty(len(out))
    down = Vector((0, 0, -1))
    # min over a small disk so points beside facades or under overhangs land on
    # the street, not on a roof edge the vertical ray happens to clip
    disk = ((0, 0), (2.5, 0), (-2.5, 0), (0, 2.5), (0, -2.5))
    for i, (x, y) in enumerate(out):
        zs = []
        for dx, dy in disk:
            h = bvh.ray_cast(Vector((x + dx, y + dy, 500.0)), down, 1000.0)
            if h[0] is not None:
                zs.append(h[0].z)
        z[i] = (min(zs) if zs else 50.0) + 1.5
    return np.column_stack([out, z])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", default="data/osm_buildings.json")
    ap.add_argument("--sites", default="data/sites.json")
    ap.add_argument("--gpx", default="data/walk.gpx")
    ap.add_argument("--out", default="data/relevance.json")
    ap.add_argument("--renders", default="renders")
    args = ap.parse_args(argv)

    osm = json.loads(pathlib.Path(args.osm).read_text())
    lat0, lon0 = osm["lat"], osm["lon"]
    p0 = llh_to_ecef(lat0, lon0, 0.0)
    R = enu_rotation(lat0, lon0)

    print("[bvh] building...", flush=True)
    V, F = collect_world_triangles(bpy.data.collections["google"])
    bvh = BVHTree.FromPolygons(V.tolist(), F.tolist(), all_triangles=True)
    tri_v = V[F]
    centroids = tri_v.mean(axis=1)
    walk = load_walk(args.gpx, R, p0, bvh)
    print(f"[walk] {len(walk)} samples", flush=True)

    sites = json.loads(pathlib.Path(args.sites).read_text())
    site_pos = []
    down = Vector((0, 0, -1))
    for s in sites:
        e = R @ (llh_to_ecef(s["lat"], s["lon"]) - p0)
        h = bvh.ray_cast(Vector((e[0], e[1], 500.0)), down, 1000.0)
        gz = h[0].z if h[0] is not None else 50.0
        site_pos.append((e[0], e[1], gz + s["height"]))
    site_pos = np.array(site_pos)

    importance = np.zeros(len(F))

    # ---- direct pass: blockers between site and walk get importance
    print("[direct] site-to-walk visibility...", flush=True)
    los_count = np.zeros(len(walk))
    for sp in site_pos:
        o = Vector(sp)
        for wi, w in enumerate(walk):
            d = Vector(w) - o
            dist = d.length
            hit = bvh.ray_cast(o, d.normalized(), dist - 0.5)
            if hit[0] is None:
                los_count[wi] += 1
            else:
                importance[hit[2]] += 0.5   # shadow-defining surface

    # ---- specular Monte Carlo: which surfaces bounce energy onto the walk
    print("[specular] monte carlo...", flush=True)
    rng = np.random.default_rng(7)
    walk_xyz = walk
    for si, sp in enumerate(site_pos):
        o = Vector(sp)
        phi = rng.uniform(0, 2 * np.pi, RAYS_PER_SITE)
        # bias downward: sample cos(theta) in [-1, 0.15]
        ct = rng.uniform(-1, 0.15, RAYS_PER_SITE)
        st = np.sqrt(1 - ct**2)
        dirs = np.column_stack([st * np.cos(phi), st * np.sin(phi), ct])
        hits_p, hits_r, hits_f = [], [], []
        for k in range(RAYS_PER_SITE):
            d = Vector(dirs[k])
            hit = bvh.ray_cast(o, d, 500.0)
            if hit[0] is None:
                continue
            n = hit[1]
            r = d - 2.0 * d.dot(n) * n
            hits_p.append([*hit[0]])
            hits_r.append([*r])
            hits_f.append(hit[2])
        P = np.array(hits_p)
        Rr = np.array(hits_r)
        fi = np.array(hits_f)
        # distance from reflected rays to walk samples, chunked
        for c0 in range(0, len(P), 20000):
            p = P[c0:c0 + 20000, None, :]
            r = Rr[c0:c0 + 20000, None, :]
            w = walk_xyz[None, :, :]
            t = ((w - p) * r).sum(-1)
            t = np.clip(t, 0.0, 300.0)
            closest = p + t[..., None] * r
            dmin = np.linalg.norm(w - closest, axis=-1).min(axis=1)
            sel = fi[c0:c0 + 20000][dmin < NEAR_MISS]
            np.add.at(importance, sel, 1.0)
        print(f"  site {si}: {len(P)} surface hits", flush=True)

    # ---- roll up to buildings
    print("[rollup] per building...", flush=True)
    walk_xy = walk[:, :2]
    tiers = {}
    rows = []
    for b in osm["buildings"]:
        ring = b["ring"][:-1]
        if len(ring) < 3:
            continue
        pts = [tuple((R @ (llh_to_ecef(la, lo) - p0))[:2]) for lo, la in ring]
        inside = point_in_poly(centroids[:, 0], centroids[:, 1], pts)
        imp = float(importance[inside].sum())
        n_tris = int(inside.sum())
        cx = np.mean([p[0] for p in pts])
        cy = np.mean([p[1] for p in pts])
        d_walk = float(np.linalg.norm(walk_xy - [cx, cy], axis=1).min())
        rows.append({"id": b["id"], "importance": round(imp, 1),
                     "tris_photo": n_tris, "d_walk": round(d_walk, 1),
                     "name": b.get("tags", {}).get("name")})

    nonzero = [r["importance"] for r in rows if r["importance"] > 0]
    thr = max(50.0, float(np.percentile(nonzero, 97))) if nonzero else 50.0
    print(f"[tiering] adaptive detailed threshold = {thr:.1f}")
    total_kept = 0
    for r in rows:
        if r["importance"] >= thr:
            r["tier"] = "detailed"
            total_kept += r["tris_photo"]
        elif r["importance"] > 0 or r["d_walk"] < CONTEXT_RADIUS:
            r["tier"] = "prism"
            total_kept += 12
        else:
            r["tier"] = "dropped"
        tiers[r["id"]] = r["tier"]

    rows.sort(key=lambda r: -r["importance"])
    counts = {}
    for r in rows:
        counts[r["tier"]] = counts.get(r["tier"], 0) + 1
    stats = {"faces_full_photo": len(F), "tri_budget_hybrid": total_kept,
             "tiers": counts, "los_fraction_walk": float((los_count > 0).mean())}
    json.dump({"stats": stats, "buildings": rows},
              open(args.out, "w"), indent=1)
    print("[stats]", json.dumps(stats))
    print("[top10]", json.dumps(rows[:10], indent=1))

    # ---- visuals
    print("[viz] building importance mesh...", flush=True)
    imp_mesh = bpy.data.meshes.new("importance")
    used = np.unique(F)
    remap = np.zeros(len(V), dtype=np.int64)
    remap[used] = np.arange(len(used))
    imp_mesh.from_pydata(V[used].tolist(), [], remap[F].tolist())
    imp_mesh.validate()
    att = imp_mesh.color_attributes.new(name="imp", type="FLOAT_COLOR",
                                        domain="POINT")
    # transfer face importance to vertices (max of adjacent faces), log scale
    vimp = np.zeros(len(used))
    logimp = np.log1p(importance)
    for k in range(3):
        np.maximum.at(vimp, remap[F[:, k]], logimp)
    vmax = max(vimp.max(), 1e-6)
    from matplotlib import cm
    cols = cm.inferno(vimp / vmax)
    flat = np.ascontiguousarray(cols, dtype=np.float32).ravel()
    att.data.foreach_set("color", flat)
    mat = bpy.data.materials.new("imp_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    attn = nt.nodes.new("ShaderNodeAttribute")
    attn.attribute_name = "imp"
    bsdf = nt.nodes["Principled BSDF"]
    nt.links.new(attn.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 1.0
    imp_mesh.materials.append(mat)
    imp_obj = bpy.data.objects.new("importance", imp_mesh)
    icoll = bpy.data.collections.new("relevance")
    bpy.context.scene.collection.children.link(icoll)
    icoll.objects.link(imp_obj)

    # walk tube
    curve = bpy.data.curves.new("walk", "CURVE")
    curve.dimensions = "3D"
    sp = curve.splines.new("POLY")
    sp.points.add(len(walk) - 1)
    for i, w in enumerate(walk):
        sp.points[i].co = (w[0], w[1], w[2], 1)
    curve.bevel_depth = 0.8
    wm = bpy.data.materials.new("walk_mat")
    wm.use_nodes = True
    wb = wm.node_tree.nodes["Principled BSDF"]
    wb.inputs["Base Color"].default_value = (0.0, 0.9, 1.0, 1)
    wb.inputs["Emission Color"].default_value = (0.0, 0.9, 1.0, 1)
    wb.inputs["Emission Strength"].default_value = 3.0
    curve.materials.append(wm)
    wobj = bpy.data.objects.new("walk", curve)
    icoll.objects.link(wobj)

    # site masts
    sm = bpy.data.materials.new("site_mat")
    sm.use_nodes = True
    sb = sm.node_tree.nodes["Principled BSDF"]
    sb.inputs["Base Color"].default_value = (1.0, 0.1, 0.9, 1)
    sb.inputs["Emission Color"].default_value = (1.0, 0.1, 0.9, 1)
    sb.inputs["Emission Strength"].default_value = 3.0
    for sp_ in site_pos:
        bpy.ops.mesh.primitive_cylinder_add(radius=1.2, depth=8,
                                            location=(sp_[0], sp_[1], sp_[2]))
        o = bpy.context.active_object
        o.data.materials.append(sm)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        icoll.objects.link(o)

    # retier the osm boxes
    tier_mats = {}
    for t, c in [("detailed", (1.0, 0.45, 0.05, 1)), ("prism", (0.55, 0.6, 0.65, 1)),
                 ("dropped", (0.2, 0.2, 0.22, 1))]:
        m = bpy.data.materials.new(f"tier_{t}")
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = c
        tier_mats[t] = m
    for obj in bpy.data.collections["osm"].objects:
        bid = int(obj.name.split("_")[1])
        t = tiers.get(bid)
        if t:
            obj.data.materials.clear()
            obj.data.materials.append(tier_mats[t])
            obj.hide_render = t == "dropped"

    # ---- renders
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1100
    sc.render.resolution_y = 850
    sc.cycles.device = "CPU"
    rd = pathlib.Path(args.renders)

    def show(names):
        for nm in ("google", "osm", "landmarks", "markers", "relevance"):
            vl = sc.view_layers[0].layer_collection.children.get(nm)
            if vl:
                vl.exclude = nm not in names

    cam = bpy.data.objects["cam_persp"]
    show({"relevance"})
    sc.camera = cam
    sc.render.filepath = str(rd / "relevance_heat.png")
    bpy.ops.render.render(write_still=True)

    top = bpy.data.objects["cam_top"]
    sc.camera = top
    sc.render.filepath = str(rd / "relevance_heat_top.png")
    bpy.ops.render.render(write_still=True)

    # budget view: keep walk+sites visible with tiered osm + landmarks
    for o in (imp_obj,):
        o.hide_render = True
    show({"relevance", "osm", "landmarks"})
    sc.camera = cam
    sc.render.filepath = str(rd / "budget_tiers.png")
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(pathlib.Path("scene_relevance.blend").resolve()))
    print("[done]")


main()
