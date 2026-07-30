"""Render one scene from many viewpoints in a single Blender run.

    ~/blender-4.5/blender -b -P twin/contact.py -- --area graslei

Guessing a camera, rendering, looking, and guessing again costs a minute per guess
and converges slowly. Building the scene once and shooting eight candidates at low
sample count costs about the same as two guesses and settles the question. This is
the same argument as the six-view QA sheet: one view hides whole classes of error,
and the cheapest fix is more views.

Also renders a top-down orthographic plate, which is the fastest way to see whether
the geometry itself is right, independent of any composition.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import sys

import bpy  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from twin import realise  # noqa: E402


def ortho_camera(centre, half: float, z: float):
    cam = bpy.data.cameras.new("ortho")
    cam.type = "ORTHO"
    cam.ortho_scale = 2.2 * half
    ob = bpy.data.objects.new("ortho", cam)
    ob.location = (centre[0], centre[1], z + 260.0)
    ob.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="graslei")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="renders/twin/contact")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--ring", type=float, default=70.0)
    args = ap.parse_args(argv)

    sys.argv = ["blender", "--", "--area", args.area, "--seed", str(args.seed)]
    realise.main()

    a = realise.anchor_mod.load()
    cx, cy, radius = realise.AREAS[args.area]
    sel = [b for b in a.buildings
           if np.linalg.norm(b.centroid - np.array([cx, cy])) < radius]
    focus = np.array([cx, cy])
    top = float(np.percentile([b.top_z for b in sel], 75))
    aim = np.array([cx, cy, a.ground_global + 0.5 * (top - a.ground_global)])

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = args.samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 640, 400
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.5

    # Top-down plate first: is the geometry right at all.
    sc.camera = ortho_camera((cx, cy), radius, a.ground_global)
    sc.render.resolution_x, sc.render.resolution_y = 700, 700
    sc.render.filepath = str(out / "v00_top.png")
    bpy.ops.render.render(write_still=True)
    print(f"[contact] v00_top  ortho half={radius:.0f} m")

    # Then a ring of eye-level candidates.
    sc.render.resolution_x, sc.render.resolution_y = 640, 400
    for k in range(8):
        th = 2 * math.pi * k / 8
        eye_xy = focus + np.array([math.cos(th), math.sin(th)]) * args.ring
        z = max(a.terrain.at(*eye_xy), a.ground_global) + 1.7
        cam = realise.place_camera(np.array([eye_xy[0], eye_xy[1], z]), aim,
                                   lens=32.0)
        sc.render.filepath = str(out / f"v{k + 1:02d}_az{int(math.degrees(th))}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[contact] v{k + 1:02d} az={math.degrees(th):5.0f} "
              f"eye={np.round(eye_xy, 1)}")
        bpy.data.objects.remove(cam, do_unlink=True)

    print(f"[contact] wrote 9 plates to {out}")


if __name__ == "__main__":
    main()
