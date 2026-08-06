"""Reference plates: one clean frontal shot per building, from the Google tiles.

    ~/blender-4.5/blender -b scene.blend -P twin/shoot.py -- --area graslei

This is the director's eyes. Everything downstream in `twin/read.py` is only as good
as these frames, so the camera is derived from the building's own street-facing edge
rather than from a walk track. The older `render_facades.py` picked the nearest
usable GPX sample, which is the right idea for a corridor study and the wrong one
here: on the Graslei the classic view is from the opposite quay, where nobody walked,
and half the resulting plates were 11 mm shots angled into a wall.

Three things this fixes, all of which showed up in the earlier plates:

- The frame is solved, not preferred. Standoff comes from the facade's own width and
  height at a fixed 35 mm, so the target fills the frame and the director is never
  guessing which of five houses it was asked about.
- Photogrammetry is lit flat. Google tiles carry baked sun in the albedo; adding a
  second sun renders a dark street with double shadows, which is what the old plates
  look like. Standard view transform, uniform white world, no sun.
- Occlusion is escaped sideways, not backwards. Backing off in a medieval street
  puts another building in the lens. The candidate fan swings around the facade
  midpoint at constant range instead.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from twin.anchor import load  # noqa: E402
from twin.areas import AREAS  # noqa: E402
from twin.facade import street_facing_edges  # noqa: E402

RES_X, RES_Y = 1024, 768
LENS = 35.0
SENSOR_W = 36.0
FILL = 0.78            # fraction of the frame the target facade should occupy
D_MIN, D_MAX = 7.0, 90.0
SAMPLES = 24
EXPOSURE = 1.35        # stops; the Ghent tile capture is overcast and dim
CLEAR_MIN = 0.55       # fraction of probes that must reach the facade


def scene_bvh(collection: str = "google") -> BVHTree:
    """One BVH over the photogrammetry, for occlusion and ground height."""
    coll = bpy.data.collections[collection]
    deps = bpy.context.evaluated_depsgraph_get()
    verts, tris, off = [], [], 0
    for obj in coll.all_objects:
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(deps)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        n = len(me.vertices)
        if n:
            v = np.empty(n * 3)
            me.vertices.foreach_get("co", v)
            m = np.array(obj.matrix_world)
            verts.append(v.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3])
            t = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
            me.loop_triangles.foreach_get("vertices", t)
            tris.append(t.reshape(-1, 3) + off)
            off += n
        ev.to_mesh_clear()
    return BVHTree.FromPolygons([tuple(p) for p in np.vstack(verts)],
                                [tuple(t) for t in np.vstack(tris)])


def ground_at(bvh: BVHTree, x: float, y: float) -> float | None:
    hit = bvh.ray_cast(Vector((x, y, 400.0)), Vector((0, 0, -1)), 900.0)
    return hit[0].z if hit[0] is not None else None


def front_edge(b, anchor):
    """The widest street-facing edge, with its midpoint and outward normal.

    Widest rather than closest: on a corner plot both edges front a street, and the
    long one is the one a photograph of "that building" would show.
    """
    ring = b.ring
    idx = street_facing_edges(b, anchor)
    best = max(idx, key=lambda i: np.linalg.norm(
        ring[(i + 1) % len(ring)] - ring[i]))
    a, c = ring[best], ring[(best + 1) % len(ring)]
    e = c - a
    width = float(np.linalg.norm(e))
    mid = (a + c) / 2.0
    nrm = np.array([e[1], -e[0]]) / max(width, 1e-9)
    if np.dot(nrm, mid - b.centroid) < 0:
        nrm = -nrm
    return mid, nrm, width


def solve_standoff(width: float, height: float) -> float:
    """Range at which the facade fills `FILL` of the frame at a fixed 35 mm.

    Solving for distance rather than for focal length keeps perspective constant
    across the set, so the director sees 32 comparable photographs instead of 32
    different lenses.
    """
    sensor_h = SENSOR_W * RES_Y / RES_X
    d_w = (width / FILL) * LENS / SENSOR_W
    d_h = (height * 1.15 / FILL) * LENS / sensor_h
    return float(np.clip(max(d_w, d_h), D_MIN, D_MAX))


def probes(mid, nrm, width, z0, height):
    """Five points spread over the facade: centre, both quarters, sill and eaves."""
    u = np.array([-nrm[1], nrm[0]])
    q = width * 0.30
    zc = z0 + height * 0.5
    return [
        (mid[0], mid[1], zc),
        (mid[0] + u[0] * q, mid[1] + u[1] * q, zc),
        (mid[0] - u[0] * q, mid[1] - u[1] * q, zc),
        (mid[0], mid[1], z0 + min(2.0, height * 0.25)),
        (mid[0], mid[1], z0 + height * 0.92),
    ]


def clear_fraction(bvh, cam, targets) -> float:
    """How much of the facade the lens actually reaches.

    A ray that stops short of the target by more than a metre hit something else.
    Slack of 1.0 m absorbs the offset between the OSM footprint plane and where the
    photogrammetry actually puts the wall, which is routinely half a metre out.
    """
    ok = 0
    for t in targets:
        d = Vector(t) - Vector(cam)
        dist = d.length
        if dist < 1e-6:
            continue
        hit = bvh.ray_cast(Vector(cam), d / dist, dist + 5.0)
        if hit[0] is None or (hit[0] - Vector(cam)).length >= dist - 1.0:
            ok += 1
    return ok / len(targets)


def choose_camera(bvh, b, anchor):
    """Best of a fan swung around the facade midpoint at near-constant range."""
    mid, nrm, width = front_edge(b, anchor)
    z0, h = b.ground_z, b.height
    d0 = solve_standoff(width, h)
    tgt = probes(mid, nrm, width, z0, h)
    aim = (float(mid[0]), float(mid[1]), z0 + h * 0.45)

    best = None
    for scale in (1.0, 0.78, 1.3, 0.6, 1.7):
        for yaw_deg in (0, -18, 18, -34, 34, -50, 50):
            th = math.radians(yaw_deg)
            rot = np.array([[math.cos(th), -math.sin(th)],
                            [math.sin(th), math.cos(th)]])
            v = rot @ nrm
            d = float(np.clip(d0 * scale, D_MIN, D_MAX))
            x, y = mid[0] + v[0] * d, mid[1] + v[1] * d
            gz = ground_at(bvh, x, y)
            if gz is None or gz > z0 + 6.0:
                continue                       # on a roof, or nothing under us
            # Eye level unless the facade is tall, then lift to halve the tilt.
            cz = gz + 1.7 + max(0.0, min(h * 0.22, 9.0)) * (0.0 if h < 12 else 1.0)
            cam = (float(x), float(y), float(cz))
            frac = clear_fraction(bvh, cam, tgt)
            if frac < CLEAR_MIN:
                continue
            # Prefer square-on, prefer the solved range, prefer an unblocked view.
            front = abs(float(np.dot(v, nrm)))
            score = frac * (0.35 + 0.65 * front) * math.exp(
                -0.5 * ((d - d0) / (0.5 * d0)) ** 2)
            if best is None or score > best[0]:
                best = (score, cam, frac, d, front)
    if best is None:
        return None
    _, cam, frac, d, front = best
    return {"cam": cam, "aim": aim, "clear": frac, "dist_m": d,
            "frontality": front, "facade_w": width, "solved_d": d0,
            "mid": mid, "nrm": nrm}


def project(cam, aim, p) -> tuple[float, float]:
    """World point to normalised image coordinates, origin top left.

    Needed because a 35 mm frame in a terraced street always contains the
    neighbours. Telling the director *which* facade is the subject is not optional:
    ask "read this building" over a picture of five and you get an average of five.
    """
    quat = (Vector(aim) - Vector(cam)).to_track_quat("-Z", "Y")
    v = quat.inverted() @ (Vector(p) - Vector(cam))
    if v.z > -1e-6:
        return (float("nan"), float("nan"))
    sensor_h = SENSOR_W * RES_Y / RES_X
    u = (v.x / -v.z) * LENS / (SENSOR_W / 2.0)
    w = (v.y / -v.z) * LENS / (sensor_h / 2.0)
    return (0.5 * (u + 1.0), 0.5 * (1.0 - w))


def facade_box(b, cam, aim, mid, nrm, width) -> dict | None:
    """Where the target facade lands in the frame, as a normalised box."""
    u = np.array([-nrm[1], nrm[0]])
    corners = []
    for s in (-0.5, 0.5):
        for z in (b.ground_z, b.ground_z + b.height):
            q = mid + u * (s * width)
            corners.append(project(cam, aim, (float(q[0]), float(q[1]), z)))
    xs = [c[0] for c in corners if c[0] == c[0]]
    ys = [c[1] for c in corners if c[1] == c[1]]
    if len(xs) < 4:
        return None
    return {"x0": round(max(0.0, min(xs)), 3), "x1": round(min(1.0, max(xs)), 3),
            "y0": round(max(0.0, min(ys)), 3), "y1": round(min(1.0, max(ys)), 3)}


def write_keyed(src: pathlib.Path, dst: pathlib.Path, box: dict) -> None:
    """Copy the plate with the target facade outlined, as a second reference image.

    Drawn on a copy rather than on the plate itself so the clean frame stays clean:
    a director that can see the annotation should still be able to see the wall it
    covers.
    """
    img = bpy.data.images.load(str(src))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    x0, x1 = int(box["x0"] * (w - 1)), int(box["x1"] * (w - 1))
    # Image rows run bottom-up in Blender, so the normalised y flips here.
    y0, y1 = int((1.0 - box["y1"]) * (h - 1)), int((1.0 - box["y0"]) * (h - 1))
    t = 3
    px[y0:y0 + t, x0:x1, :3] = (1.0, 0.0, 0.75)
    px[max(y1 - t, 0):y1, x0:x1, :3] = (1.0, 0.0, 0.75)
    px[y0:y1, x0:x0 + t, :3] = (1.0, 0.0, 0.75)
    px[y0:y1, max(x1 - t, 0):x1, :3] = (1.0, 0.0, 0.75)
    img.pixels = px.reshape(-1).tolist()
    img.filepath_raw = str(dst)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def oblique_camera(b, anchor):
    """Elevated three-quarter view, for buildings with no street a lens can stand in.

    Eleven of the 32 here are interior-of-block, which is not a bug to be tuned away:
    a courtyard building genuinely cannot be photographed from the street. Rather
    than drop them to the regional prior, look down at them. Roof form and massing
    survive an aerial, which are the two fields that matter most for a building the
    beam will only ever see over a ridge line.
    """
    mid, nrm, width = front_edge(b, anchor)
    h = max(b.height, 6.0)
    d = max(1.9 * h, 1.3 * width, 22.0)
    el = math.radians(38.0)
    cam = (float(mid[0] + nrm[0] * d * math.cos(el)),
           float(mid[1] + nrm[1] * d * math.cos(el)),
           float(b.ground_z + h + d * math.sin(el)))
    aim = (float(b.centroid[0]), float(b.centroid[1]), b.ground_z + h * 0.75)
    return {"cam": cam, "aim": aim, "clear": 0.0, "dist_m": d, "frontality": 1.0,
            "facade_w": width, "solved_d": d, "mid": mid, "nrm": nrm,
            "view": "oblique"}


def setup_render(out_dir: pathlib.Path) -> None:
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_Y
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    # Photogrammetry albedo already contains the sun that lit the flyover. Relight it
    # and you get the double-shadowed murk the first plate set had.
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    # The tiles are Emission shaders, so the beauty pass already *is* flat albedo and
    # the sun in the scene never touched them. The old plates were not dark because
    # they were badly lit, they were dark because Google's Ghent capture is overcast
    # and the texture itself is dim. Exposure is therefore the whole fix, and the
    # diffuse-colour pass, which would be the usual move for photogrammetry, renders
    # solid black here for the same reason.
    sc.view_settings.exposure = EXPOSURE
    world = sc.world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs[1].default_value = 1.0
    # `bpy.data.objects` yields a None slot in this blend, so guard rather than
    # iterate it blind.
    for o in list(bpy.context.scene.objects):
        if o is not None and o.type == "LIGHT":
            o.hide_render = True
    if "osm" in bpy.data.collections:
        for o in bpy.data.collections["osm"].all_objects:
            if o is not None:
                o.hide_render = True
    out_dir.mkdir(parents=True, exist_ok=True)


def render_one(cam_obj, shot: dict, path: pathlib.Path) -> None:
    cam_obj.location = Vector(shot["cam"])
    direction = Vector(shot["aim"]) - Vector(shot["cam"])
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam_obj.data.lens = LENS
    cam_obj.data.sensor_width = SENSOR_W
    bpy.context.scene.camera = cam_obj
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="graslei")
    ap.add_argument("--out", default="renders/plates")
    ap.add_argument("--manifest", default="data/twin/plates.json")
    ap.add_argument("--only", default=None, help="comma-separated osm ids")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)

    anchor = load()
    cx, cy, radius = AREAS[args.area]
    centre = np.array([cx, cy])
    targets = [b for b in anchor.buildings
               if np.linalg.norm(b.centroid - centre) <= radius]
    if args.only:
        keep = {int(s) for s in args.only.split(",")}
        targets = [b for b in targets if b.osm_id in keep]
    targets.sort(key=lambda b: float(np.linalg.norm(b.centroid - centre)))
    print(f"[shoot] {len(targets)} buildings in {args.area}")

    bvh = scene_bvh()
    out_dir = pathlib.Path(args.out) / args.area
    if not args.dry:
        setup_render(out_dir)
        cam_obj = bpy.data.objects.get("cam_facade")
        if cam_obj is None:
            cam_obj = bpy.data.objects.new("cam_facade",
                                           bpy.data.cameras.new("cam_facade"))
            bpy.context.scene.collection.objects.link(cam_obj)

    records = []
    for i, b in enumerate(targets):
        shot = choose_camera(bvh, b, anchor)
        if shot is None:
            shot = oblique_camera(b, anchor)
        view = shot.get("view", "street")
        path = out_dir / f"{b.osm_id}.png"
        print(f"  [{i:2d}] {b.osm_id}  {view:7s} d={shot['dist_m']:.1f} m  "
              f"clear={shot['clear']:.2f}  front={shot['frontality']:.2f}  "
              f"w={shot['facade_w']:.1f} m  h={b.height:.1f} m")
        box = facade_box(b, shot["cam"], shot["aim"], shot["mid"], shot["nrm"],
                         shot["facade_w"])
        keyed = out_dir / f"{b.osm_id}_key.png"
        if not args.dry:
            render_one(cam_obj, shot, path)
            if box:
                write_keyed(path, keyed, box)
        records.append({
            "id": b.osm_id, "status": "rendered", "view": view,
            "image": str(path),
            "keyed_image": str(keyed) if box else None,
            "target_box": box,
            "camera_xyz": [round(v, 2) for v in shot["cam"]],
            "aim_xyz": [round(v, 2) for v in shot["aim"]],
            "dist_m": round(shot["dist_m"], 1),
            "clear_fraction": round(shot["clear"], 2),
            "frontality": round(shot["frontality"], 2),
            "facade_width_m": round(shot["facade_w"], 1),
            "height_m": round(b.height, 1),
            "lens_mm": LENS,
        })

    man = pathlib.Path(args.manifest)
    man.parent.mkdir(parents=True, exist_ok=True)
    man.write_text(json.dumps({"area": args.area, "plates": records}, indent=1))
    n_ok = sum(1 for r in records if r["status"] == "rendered")
    print(f"[shoot] {n_ok}/{len(records)} plates -> {out_dir}")


if __name__ == "__main__":
    main()
