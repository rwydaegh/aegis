"""Intelligent hybrid pass: measure photogrammetry, audit OSM, build corrected scene.

Run inside Blender on the scene produced by build_scene.py:
  blender -b scene.blend -P analyze_hybridize.py -- --osm data/osm_buildings.json \
      --out data/decisions.json --blend scene_hybrid.blend --renders renders
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
GRID = 3.0
HALF = 210.0


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
    """All triangles of a collection's meshes in world space, as (V, F) numpy arrays."""
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
    V = np.vstack(verts_all)
    F = np.vstack(tris_all)
    return V, F


def point_in_poly(px, py, ring):
    """Vectorized ray-crossing. px,py arrays; ring list of (x,y)."""
    x = np.asarray([p[0] for p in ring])
    y = np.asarray([p[1] for p in ring])
    x2 = np.roll(x, -1)
    y2 = np.roll(y, -1)
    px = px[:, None]
    py = py[:, None]
    cond = (y[None] > py) != (y2[None] > py)
    with np.errstate(divide="ignore", invalid="ignore"):
        xin = (x2 - x)[None] * (py - y[None]) / (y2 - y)[None] + x[None]
    crossing = cond & (px < xin)
    return crossing.sum(axis=1) % 2 == 1


def dist_to_ring(px, py, ring):
    """Min distance from points to polygon edges (vectorized over edges)."""
    p = np.stack([px, py], axis=1)[:, None, :]
    a = np.array(ring)
    b = np.roll(a, -1, axis=0)
    ab = (b - a)[None]
    ap = p - a[None]
    t = np.clip((ap * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12), 0, 1)
    d = np.linalg.norm(ap - t[..., None] * ab, axis=-1)
    return d.min(axis=1)


def raycast_grid(bvh, pts_xy, z0=500.0):
    hits = np.full(len(pts_xy), np.nan)
    down = Vector((0, 0, -1))
    for i, (x, y) in enumerate(pts_xy):
        h = bvh.ray_cast(Vector((x, y, z0)), down, 1000.0)
        if h[0] is not None:
            hits[i] = h[0].z
    return hits


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", default="data/osm_buildings.json")
    ap.add_argument("--out", default="data/decisions.json")
    ap.add_argument("--blend", default="scene_hybrid.blend")
    ap.add_argument("--renders", default="renders")
    args = ap.parse_args(argv)

    osm = json.loads(pathlib.Path(args.osm).read_text())
    lat0, lon0 = osm["lat"], osm["lon"]
    p0 = llh_to_ecef(lat0, lon0, 0.0)
    R = enu_rotation(lat0, lon0)

    print("[bvh] collecting google triangles...", flush=True)
    V, F = collect_world_triangles(bpy.data.collections["google"])
    print(f"[bvh] {len(V)} verts, {len(F)} tris", flush=True)
    bvh = BVHTree.FromPolygons(V.tolist(), F.tolist(), all_triangles=True)

    # ---- footprints in ENU
    polys = []
    for b in osm["buildings"]:
        ring = b["ring"][:-1]
        if len(ring) < 3:
            continue
        pts = [(float((R @ (llh_to_ecef(la, lo, 0.0) - p0))[0]),
                float((R @ (llh_to_ecef(la, lo, 0.0) - p0))[1]))
               for lo, la in ring]
        polys.append({"id": b["id"], "tags": b.get("tags", {}), "pts": pts})

    # ---- global grid + terrain
    ax = np.arange(-HALF, HALF + GRID, GRID)
    gx, gy = np.meshgrid(ax, ax)
    gx, gy = gx.ravel(), gy.ravel()
    print(f"[grid] raycasting {len(gx)} points...", flush=True)
    gz = raycast_grid(bvh, np.stack([gx, gy], axis=1))
    valid = ~np.isnan(gz)

    inside_any = np.zeros(len(gx), dtype=bool)
    inside_of = {}
    near_of = {}
    for pl in polys:
        inside = point_in_poly(gx, gy, pl["pts"])
        inside_of[pl["id"]] = inside
        inside_any |= inside
        d = dist_to_ring(gx, gy, pl["pts"])
        near_of[pl["id"]] = (~inside) & (d < 10.0)

    ground_mask = valid & ~inside_any
    # local ground: for each grid point take 25m-neighborhood median of street-level pts
    print("[terrain] building local ground model...", flush=True)
    gpts = np.stack([gx[ground_mask], gy[ground_mask]], axis=1)
    gzs = gz[ground_mask]
    # streets contain cars/trees: use 25th percentile locally
    ground_global = float(np.percentile(gzs, 25))

    def local_ground(x, y, rad=25.0):
        d2 = (gpts[:, 0] - x) ** 2 + (gpts[:, 1] - y) ** 2
        sel = gzs[d2 < rad * rad]
        if len(sel) < 5:
            return ground_global
        return float(np.percentile(sel, 25))

    # ---- per-building audit
    decisions = []
    for pl in polys:
        pid = pl["id"]
        tags = pl["tags"]
        cx = np.mean([p[0] for p in pl["pts"]])
        cy = np.mean([p[1] for p in pl["pts"]])
        area = 0.5 * abs(sum(
            pl["pts"][i][0] * pl["pts"][(i + 1) % len(pl["pts"])][1]
            - pl["pts"][(i + 1) % len(pl["pts"])][0] * pl["pts"][i][1]
            for i in range(len(pl["pts"]))))
        gnd = local_ground(cx, cy)
        roof_z = gz[inside_of[pid] & valid]
        n_hits = len(roof_z)
        h_tag, tag_src = None, None
        if "height" in tags:
            try:
                h_tag = float(str(tags["height"]).replace("m", "").strip())
                tag_src = "height"
            except ValueError:
                pass
        if h_tag is None and "building:levels" in tags:
            try:
                h_tag = float(tags["building:levels"]) * 3.2 + 4.0
                tag_src = "levels"
            except ValueError:
                pass

        rec = {"id": pid, "area_m2": round(area, 1), "ground_z": round(gnd, 2),
               "n_samples": n_hits, "h_tag": h_tag, "tag_src": tag_src,
               "name": tags.get("name")}
        if n_hits < 4:
            h = h_tag if h_tag else 9.0
            rec.update(decision="no-data", h_final=h,
                       note="photogrammetry hole or tiny footprint")
        else:
            rel = roof_z - gnd
            h75 = float(np.percentile(rel, 75))
            hmax = float(rel.max())
            hstd = float(rel.std())
            rec.update(h_photo_p75=round(h75, 1), h_photo_max=round(hmax, 1),
                       h_photo_std=round(hstd, 1))
            if area > 600 and (hstd > 8 or hmax > 40):
                rec.update(decision="landmark-keep-photo", h_final=round(h75, 1),
                           note="large + strongly non-prismatic: box would lie")
            elif h_tag is None:
                rec.update(decision="adopted-photo", h_final=round(max(h75, 3.0), 1))
            elif abs(h75 - h_tag) <= 3.0:
                rec.update(decision="confirmed", h_final=h_tag)
            else:
                trust_photo = hstd < 6.0 and n_hits >= 8
                rec.update(
                    decision="conflict-photo" if trust_photo else "conflict-tag",
                    h_final=round(h75, 1) if trust_photo else h_tag,
                    note=f"tag {h_tag:.1f} vs photo {h75:.1f} (std {hstd:.1f})")
        decisions.append(rec)

    # ---- unmapped structures (photogrammetry has mass, OSM has nothing)
    print("[unmapped] clustering off-footprint elevated cells...", flush=True)
    n = len(ax)
    rel_h = np.full(len(gx), 0.0)
    for i in np.nonzero(valid & ~inside_any)[0]:
        rel_h[i] = gz[i] - local_ground(gx[i], gy[i])
    elevated = (valid & ~inside_any & (rel_h > 4.0)).reshape(n, n)
    lab = np.zeros((n, n), dtype=np.int32)
    nlab = 0
    blobs = []
    for i in range(n):
        for j in range(n):
            if elevated[i, j] and lab[i, j] == 0:
                nlab += 1
                stack = [(i, j)]
                cells = []
                lab[i, j] = nlab
                while stack:
                    a, b = stack.pop()
                    cells.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        na, nb = a + da, b + db
                        if 0 <= na < n and 0 <= nb < n and elevated[na, nb] \
                                and lab[na, nb] == 0:
                            lab[na, nb] = nlab
                            stack.append((na, nb))
                if len(cells) * GRID * GRID >= 30:
                    idxs = [a * n + b for a, b in cells]
                    hs = rel_h[idxs]
                    blobs.append({
                        "x": round(float(np.mean(gx[idxs])), 1),
                        "y": round(float(np.mean(gy[idxs])), 1),
                        "area_m2": len(cells) * GRID * GRID,
                        "h_mean": round(float(hs.mean()), 1),
                        "h_std": round(float(hs.std()), 1),
                        "guess": "vegetation" if hs.std() / max(hs.mean(), 1) > 0.35
                                 else "unmapped structure"})
    blobs.sort(key=lambda b: -b["area_m2"])

    # ---- rebuild OSM extrusions with corrected base + height
    palette = {
        "confirmed": (0.10, 0.65, 0.20, 1),
        "adopted-photo": (0.25, 0.45, 0.85, 1),
        "conflict-photo": (0.60, 0.20, 0.80, 1),
        "conflict-tag": (0.90, 0.15, 0.15, 1),
        "no-data": (0.95, 0.60, 0.10, 1),
        "landmark-keep-photo": (0.9, 0.9, 0.2, 1),
    }
    mats = {}
    for k, c in palette.items():
        m = bpy.data.materials.new(f"dec_{k}")
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = c
        mats[k] = m

    old = bpy.data.collections.get("osm")
    if old:
        for o in list(old.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    coll = old or bpy.data.collections.new("osm")
    if not old:
        bpy.context.scene.collection.children.link(coll)

    by_id = {p["id"]: p for p in polys}
    for rec in decisions:
        pl = by_id[rec["id"]]
        pts = pl["pts"]
        nv = len(pts)
        z0 = rec["ground_z"] - 0.5
        z1 = rec["ground_z"] + rec["h_final"]
        verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
        faces = [[i, (i + 1) % nv, nv + (i + 1) % nv, nv + i] for i in range(nv)]
        faces.append(list(range(nv)))
        faces.append([nv + i for i in range(nv - 1, -1, -1)])
        mesh = bpy.data.meshes.new(f"osm_{rec['id']}")
        mesh.from_pydata(verts, [], faces)
        mesh.validate()
        obj = bpy.data.objects.new(f"osm_{rec['id']}", mesh)
        obj.data.materials.append(mats[rec["decision"]])
        coll.objects.link(obj)
        if rec["decision"] == "landmark-keep-photo":
            obj.hide_render = True

    # ---- carve photogrammetry islands for landmark buildings
    print("[landmark] carving photogrammetry islands...", flush=True)
    land_coll = bpy.data.collections.new("landmarks")
    bpy.context.scene.collection.children.link(land_coll)
    landmarks = [r for r in decisions if r["decision"] == "landmark-keep-photo"]
    if landmarks:
        cent = V[F].mean(axis=1)
        keep = np.zeros(len(F), dtype=bool)
        for rec in landmarks:
            pts = by_id[rec["id"]]["pts"]
            inside = point_in_poly(cent[:, 0], cent[:, 1], pts)
            near = dist_to_ring(cent[:, 0], cent[:, 1], pts) < 4.0
            keep |= inside | near
        Fk = F[keep]
        used = np.unique(Fk)
        remap = np.zeros(len(V), dtype=np.int64)
        remap[used] = np.arange(len(used))
        mesh = bpy.data.meshes.new("landmark_photo")
        mesh.from_pydata(V[used].tolist(), [], remap[Fk].tolist())
        mesh.validate()
        m = bpy.data.materials.new("landmark_gray")
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = \
            (0.55, 0.52, 0.48, 1)
        mesh.materials.append(m)
        obj = bpy.data.objects.new("landmark_photo", mesh)
        land_coll.objects.link(obj)

    # ---- unmapped-structure markers
    mark_coll = bpy.data.collections.new("markers")
    bpy.context.scene.collection.children.link(mark_coll)
    mmat = bpy.data.materials.new("marker_red")
    mmat.use_nodes = True
    mmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = \
        (1.0, 0.05, 0.05, 1)
    mmat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.0
    mmat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = \
        (1.0, 0.05, 0.05, 1)
    for i, bl in enumerate(blobs[:40]):
        r = max(math.sqrt(bl["area_m2"] / math.pi), 2.0)
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=r, location=(bl["x"], bl["y"],
                                local_ground(bl["x"], bl["y"]) + bl["h_mean"] + r + 2))
        o = bpy.context.active_object
        o.name = f"blob_{i}"
        o.data.materials.append(mmat)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        mark_coll.objects.link(o)

    # ---- ground plane
    bpy.ops.mesh.primitive_plane_add(size=2 * HALF,
                                     location=(0, 0, ground_global - 0.6))
    gp = bpy.context.active_object
    gp.name = "ground_plane"
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = \
        (0.35, 0.37, 0.33, 1)
    gp.data.materials.append(gm)

    # ---- outputs
    out = {"ground_global": ground_global,
           "counts": {}, "decisions": decisions, "unmapped_blobs": blobs}
    for r in decisions:
        out["counts"][r["decision"]] = out["counts"].get(r["decision"], 0) + 1
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1))
    print("[counts]", json.dumps(out["counts"]))
    print(f"[unmapped] {len(blobs)} blobs, largest: {blobs[:5]}")

    # ---- renders
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1100
    sc.render.resolution_y = 850
    sc.cycles.device = "CPU"
    rd = pathlib.Path(args.renders)
    rd.mkdir(exist_ok=True)

    def show(names):
        for nm in ("google", "osm", "landmarks", "markers"):
            vl = sc.view_layers[0].layer_collection.children.get(nm)
            if vl:
                vl.exclude = nm not in names
    cam_top = bpy.data.objects["cam_top"]
    cam_top.location.z = ground_global + 400
    cam_persp = bpy.data.objects["cam_persp"]
    cam_persp.location = (260, -260, ground_global + 180)
    d = Vector((0, 0, ground_global + 15)) - Vector(cam_persp.location)
    cam_persp.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    sc.camera = cam_persp
    show({"osm", "landmarks", "markers"})
    sc.render.filepath = str(rd / "hybrid_persp.png")
    bpy.ops.render.render(write_still=True)
    show({"osm", "landmarks", "markers"})
    sc.camera = cam_top
    sc.render.filepath = str(rd / "hybrid_top.png")
    bpy.ops.render.render(write_still=True)
    show({"google", "osm"})
    sc.camera = cam_persp
    sc.render.filepath = str(rd / "overlay_check.png")
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(pathlib.Path(args.blend).resolve()))
    print("[done]")


main()
