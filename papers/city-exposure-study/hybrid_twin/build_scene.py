"""Build an aligned Blender scene: Google 3D tiles + OSM extrusions in a local ENU frame.

Run inside Blender:
  blender -b -P build_scene.py -- --tiles data/tiles --osm data/osm_buildings.json \
      --blend scene.blend --renders renders
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bpy
import numpy as np

WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3


def llh_to_ecef(lat_deg, lon_deg, h=0.0):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * math.sin(lat) ** 2)
    return np.array([
        (n + h) * math.cos(lat) * math.cos(lon),
        (n + h) * math.cos(lat) * math.sin(lon),
        (n * (1 - WGS84_E2) + h) * math.sin(lat),
    ])


def enu_rotation(lat_deg, lon_deg):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    east = np.array([-math.sin(lon), math.cos(lon), 0.0])
    north = np.array([-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon),
                      math.cos(lat)])
    up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon),
                   math.sin(lat)])
    return np.vstack([east, north, up])


def rot_x(deg):
    r = math.radians(deg)
    return np.array([[1, 0, 0], [0, math.cos(r), -math.sin(r)],
                     [0, math.sin(r), math.cos(r)]])


def get_collection(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def import_google_tiles(tiles_dir, p0, R, coll):
    manifest = json.loads((tiles_dir / "manifest.json").read_text())
    before = set(bpy.data.objects)
    for t in manifest["tiles"]:
        bpy.ops.import_scene.gltf(filepath=str(tiles_dir / t["file"]))
    imported = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in imported if o.parent is None or o.parent not in imported]

    # Self-calibrate the fixed axis conversion the importer applied to ECEF data:
    # candidates map blender-world back to ECEF; pick the one landing nearest anchor.
    centers = []
    for o in roots:
        m = np.array(o.matrix_world, dtype=np.float64)
        centers.append(m[:3, 3])
    mean_c = np.mean(centers, axis=0)
    candidates = {"identity": np.eye(3), "rx+90": rot_x(90), "rx-90": rot_x(-90)}
    best_name, best_err, best_Cinv = None, np.inf, None
    for name, C in candidates.items():
        err = np.linalg.norm(C.T @ mean_c - p0)
        if err < best_err:
            best_name, best_err, best_Cinv = name, err, C.T
    print(f"[calib] axis fix = {best_name}, residual to anchor = {best_err:.1f} m")
    if best_err > 5000:
        print("[calib] WARNING: no candidate lands near anchor, alignment suspect")

    # world_enu = R @ (Cinv @ world_blender - p0)
    M = np.eye(4)
    M[:3, :3] = R @ best_Cinv
    M[:3, 3] = -R @ p0
    from mathutils import Matrix
    Mb = Matrix(M.tolist())
    for o in roots:
        o.matrix_world = Mb @ o.matrix_world
    for o in imported:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    return imported


def osm_height(tags):
    if "height" in tags:
        try:
            return float(str(tags["height"]).replace("m", "").strip()), "tag:height"
        except ValueError:
            pass
    if "building:levels" in tags:
        try:
            return float(tags["building:levels"]) * 3.2 + 4.0, "tag:levels"
        except ValueError:
            pass
    return 9.0, "default"


def build_osm(osm_path, p0, R, coll):
    data = json.loads(pathlib.Path(osm_path).read_text())
    mat_tag = bpy.data.materials.new("osm_tagged")
    mat_tag.diffuse_color = (0.1, 0.6, 0.15, 1.0)
    mat_def = bpy.data.materials.new("osm_default")
    mat_def.diffuse_color = (0.85, 0.45, 0.05, 1.0)
    for m in (mat_tag, mat_def):
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = \
            m.diffuse_color

    records = []
    for b in data["buildings"]:
        ring = b["ring"]
        if len(ring) < 4:
            continue
        pts = []
        for lon, lat in ring[:-1]:
            e = R @ (llh_to_ecef(lat, lon, 0.0) - p0)
            pts.append((e[0], e[1]))
        h, src = osm_height(b.get("tags", {}))
        name = f"osm_{b['id']}"
        mesh = bpy.data.meshes.new(name)
        nv = len(pts)
        verts = [(x, y, 0.0) for x, y in pts] + [(x, y, h) for x, y in pts]
        faces = [[i, (i + 1) % nv, nv + (i + 1) % nv, nv + i] for i in range(nv)]
        faces.append(list(range(nv)))                      # floor
        faces.append([nv + i for i in range(nv - 1, -1, -1)])  # roof
        mesh.from_pydata(verts, [], faces)
        mesh.validate()
        obj = bpy.data.objects.new(name, mesh)
        obj.data.materials.append(mat_tag if src.startswith("tag") else mat_def)
        obj["osm_id"] = b["id"]
        obj["height_source"] = src
        obj["height"] = h
        coll.objects.link(obj)
        records.append({"id": b["id"], "height": h, "source": src,
                        "tags": b.get("tags", {})})
    return records


def setup_world_and_lights():
    w = bpy.data.worlds["World"]
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.75, 0.82, 0.95, 1.0)
    bg.inputs[1].default_value = 0.7
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(120))
    bpy.context.scene.collection.objects.link(sun)


def make_cameras():
    cams = {}
    top = bpy.data.cameras.new("cam_top")
    top.type = "ORTHO"
    top.ortho_scale = 430
    top.clip_end = 2000
    o = bpy.data.objects.new("cam_top", top)
    o.location = (0, 0, 400)
    bpy.context.scene.collection.objects.link(o)
    cams["top"] = o

    persp = bpy.data.cameras.new("cam_persp")
    persp.lens = 35
    persp.clip_end = 3000
    o2 = bpy.data.objects.new("cam_persp", persp)
    from mathutils import Vector
    o2.location = (260, -260, 200)
    d = Vector((0, 0, 30)) - Vector(o2.location)
    o2.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(o2)
    cams["persp"] = o2
    return cams


def render(path, cam, show):
    sc = bpy.context.scene
    sc.camera = cam
    for name in ("google", "osm"):
        vl = sc.view_layers[0].layer_collection.children.get(name)
        if vl:
            vl.exclude = name not in show
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print(f"[render] {path}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiles", default="data/tiles")
    ap.add_argument("--osm", default="data/osm_buildings.json")
    ap.add_argument("--blend", default="scene.blend")
    ap.add_argument("--renders", default="renders")
    args = ap.parse_args(argv)

    tiles_dir = pathlib.Path(args.tiles)
    manifest = json.loads((tiles_dir / "manifest.json").read_text())
    lat0, lon0 = manifest["lat"], manifest["lon"]
    p0 = llh_to_ecef(lat0, lon0, 0.0)
    R = enu_rotation(lat0, lon0)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    g_coll = get_collection("google")
    o_coll = get_collection("osm")
    import_google_tiles(tiles_dir, p0, R, g_coll)
    records = build_osm(args.osm, p0, R, o_coll)
    pathlib.Path("data/osm_heights_phase1.json").write_text(json.dumps(records, indent=1))

    setup_world_and_lights()
    cams = make_cameras()

    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1100
    sc.render.resolution_y = 850
    sc.cycles.device = "CPU"

    rd = pathlib.Path(args.renders)
    rd.mkdir(exist_ok=True)
    render(rd / "google_top.png", cams["top"], {"google"})
    render(rd / "osm_top.png", cams["top"], {"osm"})
    render(rd / "google_persp.png", cams["persp"], {"google"})
    render(rd / "both_persp.png", cams["persp"], {"google", "osm"})

    bpy.ops.wm.save_as_mainfile(filepath=str(pathlib.Path(args.blend).resolve()))
    print("[done] scene saved")


main()
