"""Render first-hit metric range from the recovered panorama camera into a mesh.

This is deliberately a depth *hypothesis*, not ground truth.  Comparing it to
the independent UniDepth estimate exposes foreground blockers, broken tile
surfaces, and camera-pose errors before semantic evidence is painted onto a
surface.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from project_pixel_semantics import pixel_boundary_direction  # noqa: E402
from project_semantics import mesh_arrays  # noqa: E402
from render_blender_alignment import panorama_rotation  # noqa: E402


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--yaws", type=int, nargs="+", default=[0, 90, 180, 270])
    return parser.parse_args(argv)


def main() -> None:
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.ply_import(filepath=str(args.mesh.resolve()))
    source = bpy.context.object
    vertices, faces = mesh_arrays(source)
    bvh = BVHTree.FromPolygons([Vector(vertex) for vertex in vertices], faces.tolist(), all_triangles=True)
    pose = json.loads(args.pose.read_text())
    camera = Vector(pose["position_enu_m"])
    rotation = panorama_rotation(
        float(pose["heading_deg"]),
        float(pose["pitch_correction_deg"]),
        float(pose["roll_correction_deg"]),
    )

    manifest = []
    for yaw in args.yaws:
        # The image is only used for the dimensions. UniDepth and SAM consume
        # exactly this crop, so its pixels correspond one-to-one with this map.
        import PIL.Image

        image = PIL.Image.open(args.views / f"h+00_{yaw:03d}.jpg")
        width, height = image.size
        range_m = np.full((height, width), np.nan, dtype=np.float32)
        face_ids = np.full((height, width), -1, dtype=np.int32)
        for y in range(height):
            for x in range(width):
                local = pixel_boundary_direction(x + 0.5, y + 0.5, width, height, yaw)
                location, _normal, face_id, distance = bvh.ray_cast(camera, rotation @ local, 2000.0)
                if location is not None and face_id is not None and distance is not None:
                    range_m[y, x] = distance
                    face_ids[y, x] = int(face_id)
        np.savez_compressed(args.out / f"h+00_{yaw:03d}.npz", range_m=range_m, face_ids=face_ids)
        manifest.append(
            {
                "view": f"h+00_{yaw:03d}",
                "shape": [height, width],
                "hit_fraction": float(np.isfinite(range_m).mean()),
                "median_range_m": float(np.nanmedian(range_m)),
            }
        )
        print(f"[mesh-depth] yaw {yaw:03d}: {manifest[-1]['hit_fraction']:.1%} rays hit")
    (args.out / "manifest.json").write_text(
        json.dumps({"mesh": str(args.mesh), "pose": str(args.pose), "views": manifest}, indent=2)
    )


if __name__ == "__main__":
    main()
