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


def clearance(a, p) -> float:
    """Distance from a point to the nearest building footprint."""
    from twin.facade import _seg_dist
    return min(_seg_dist(p, np.vstack([b.ring, b.ring[:1]])) for b in a.buildings)


def water_in_shot(a, eye, aim) -> float:
    """Fraction of the sight line that runs over water.

    Foreground water is not decoration on a canal quay, it is the reason the view
    exists: it separates the camera from the row, fills the bottom of the frame, and
    doubles the facade through its reflection. The first hero preset had none,
    which is most of why it read as a car park with houses at the far end.
    """
    from twin.facade import _seg_dist
    lines = [(w.line, 14.0 if "leie" in (w.tags.get("name") or "").lower() else 7.0)
             for w in a.ways_of("waterline")]
    if not lines:
        return 0.0
    eye, aim = np.asarray(eye)[:2], np.asarray(aim)[:2]
    hits = 0
    n = 24
    for i in range(n):
        p = eye + (aim - eye) * ((i + 0.5) / n)
        if any(_seg_dist(p, ln) < half for ln, half in lines):
            hits += 1
    return hits / n


def candidate_eyes(a, sel, focus, aim, *, ring: float, n: int = 8) -> list:
    """Viewpoints that are outdoors, clear of walls, and looking at something.

    A bare ring of azimuths puts a third of its cameras inside the block. Scoring
    first is cheap, and the number that matters is clearance: the previous authored
    preset stood 1.0 m from a facade, which no amount of lens choice recovers.
    """
    out = []
    for k in range(n * 6):
        th = 2 * math.pi * k / (n * 6)
        best = None
        for rad in (ring, ring * 0.75, ring * 1.25, ring * 0.55):
            eye = focus + np.array([math.cos(th), math.sin(th)]) * rad
            clear = clearance(a, eye)
            if clear < 5.0:
                continue
            water = water_in_shot(a, eye, aim)
            # How much of the row is actually in front of this camera.
            view = (aim[:2] - eye) / (np.linalg.norm(aim[:2] - eye) + 1e-9)
            infront = sum(1 for b in sel
                          if np.dot(b.centroid - eye, view) > 0.3 * rad)
            s = (min(clear, 25.0) / 25.0) * (0.35 + 1.4 * water) \
                * (infront / max(len(sel), 1))
            if best is None or s > best[0]:
                best = (s, eye, clear, water, infront, rad)
        if best:
            out.append((th, *best))
    # Keep the best in each of `n` azimuth buckets, so the sheet stays a sheet.
    buckets: dict[int, tuple] = {}
    for th, s, eye, clear, water, infront, rad in out:
        b = int(n * th / (2 * math.pi)) % n
        if b not in buckets or s > buckets[b][0]:
            buckets[b] = (s, eye, clear, water, infront, rad, th)
    return [buckets[k] for k in sorted(buckets)]


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--area", default="graslei")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="renders/twin/contact")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--ring", type=float, default=70.0)
    ap.add_argument("--lens", type=float, default=32.0)
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

    # Then eye-level candidates, scored rather than swept.
    sc.render.resolution_x, sc.render.resolution_y = 640, 400
    cands = candidate_eyes(a, sel, focus, aim, ring=args.ring)
    for k, (s, eye_xy, clear, water, infront, rad, th) in enumerate(cands):
        z = max(a.terrain.at(*eye_xy), a.ground_global) + 1.7
        cam = realise.place_camera(np.array([eye_xy[0], eye_xy[1], z]), aim,
                                   lens=args.lens)
        sc.render.filepath = str(out / f"v{k + 1:02d}_az{int(math.degrees(th))}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[contact] v{k + 1:02d} az={math.degrees(th):5.0f} "
              f"eye={np.round(eye_xy, 1)} d={rad:.0f} clear={clear:.1f} "
              f"water={water:.2f} rowfrac={infront / max(len(sel), 1):.2f} "
              f"score={s:.3f}")
        bpy.data.objects.remove(cam, do_unlink=True)

    print(f"[contact] wrote {len(cands) + 1} plates to {out}")


if __name__ == "__main__":
    main()
