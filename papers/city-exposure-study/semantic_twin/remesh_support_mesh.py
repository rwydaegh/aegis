"""Solidify, voxel-remesh and planar-decimate a photogrammetry support mesh.

Run inside Blender from the repository's ``semantic_twin`` directory::

    blender --background --python remesh_support_mesh.py -- \
      --mesh data/geometry/korenmarkt/inhouse_leaf_130m_f64.ply \
      --out outputs/remesh/korenmarkt_v0.50.ply \
      --solidify-m 0.50 --voxel-size-m 0.50 --adaptivity 0.5 --planar-angle-deg 1.0

The tile mesh arrives as an open, doubly-sided, vertex-split shell with slivers
and inconsistent winding. Solidify turns it into a closed volume, the Remesh
modifier in voxel mode rebuilds that volume as an OpenVDB level set and contours
it, and the decimation stages try to give the flat parts back.

Two settings decide whether this works at all, and the first run of this script
got both wrong. The shell has to be at least as thick as the voxel it is about to
be sampled onto, or the level set cannot resolve it and the wall erodes into lace,
so ``--solidify-m`` should track ``--voxel-size-m`` rather than sit below it.
And contouring at ``--adaptivity 0`` emits one quad per voxel face everywhere,
including across a flat wall where a single large triangle would do.

The middle step is still the one to watch. A level set resamples every surface
onto a uniform grid, so a facade comes back quantised to the voxel and the
contouring is not guaranteed to leave it planar. A wavy wall scatters worse than
a coarse flat one, so the planarity of the result is reported next to the triangle
count rather than assumed. Nothing here is wired into the production path.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import time

import bpy
import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.export import compact, write_ply  # noqa: E402


def positive_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return result


def non_negative_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise argparse.ArgumentTypeError("must be a finite non-negative number")
    return result


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=pathlib.Path, required=True, help="Input support mesh PLY")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="Output binary PLY")
    parser.add_argument(
        "--solidify-m",
        type=non_negative_float,
        default=0.3,
        help="Shell thickness in metres before remeshing, zero to skip (default: 0.3)",
    )
    parser.add_argument(
        "--solidify-offset",
        type=float,
        default=0.0,
        help="Solidify offset: 0 straddles the surface, -1 grows the shell inward (default: 0)",
    )
    parser.add_argument(
        "--collapse-ratio",
        type=non_negative_float,
        default=0.0,
        help="Quadric collapse decimate ratio, zero to skip (default: 0)",
    )
    parser.add_argument(
        "--collapse-stage",
        choices=("before", "after"),
        default="after",
        help="Run the collapse decimate before the solidify or after the remesh (default: after)",
    )
    parser.add_argument("--voxel-size-m", type=positive_float, required=True, help="OpenVDB voxel size in metres")
    parser.add_argument(
        "--adaptivity",
        type=non_negative_float,
        default=0.0,
        help="Remesh modifier adaptivity, which coarsens flat regions during contouring (default: 0)",
    )
    parser.add_argument(
        "--planar-angle-deg",
        type=non_negative_float,
        default=1.0,
        help="Planar decimate angle limit in degrees, zero to skip (default: 1.0)",
    )
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def import_mesh(path: pathlib.Path) -> bpy.types.Object:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.ply_import(filepath=str(path.resolve()))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected exactly one imported mesh, got {len(meshes)}")
    return meshes[0]


def evaluated_triangles(obj: bpy.types.Object) -> tuple[np.ndarray, np.ndarray]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", vertices)
        triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
        mesh.loop_triangles.foreach_get("vertices", triangles)
        world = np.asarray(evaluated.matrix_world, dtype=np.float64)
        vertices = vertices.reshape(-1, 3) @ world[:3, :3].T + world[:3, 3]
        return vertices, triangles.reshape(-1, 3)
    finally:
        evaluated.to_mesh_clear()


def apply_modifier(obj: bpy.types.Object, modifier: bpy.types.Modifier) -> int:
    """Bake one modifier into the mesh and return the resulting triangle count.

    Applying each stage keeps the stack one deep, so a voxel remesh that costs
    minutes is evaluated once rather than again for every later stage.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return triangle_count(obj)


def triangle_count(obj: bpy.types.Object) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def main() -> None:
    args = arguments()
    args.out = args.out.resolve()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    obj = import_mesh(args.mesh)
    stages: list[dict[str, object]] = []
    started = time.perf_counter()
    stages.append({"stage": "import", "triangles": triangle_count(obj), "seconds": time.perf_counter() - started})

    def collapse() -> None:
        started = time.perf_counter()
        modifier = obj.modifiers.new(name="collapse", type="DECIMATE")
        modifier.decimate_type = "COLLAPSE"
        modifier.ratio = args.collapse_ratio
        stages.append(
            {
                "stage": f"collapse_{args.collapse_stage}",
                "triangles": apply_modifier(obj, modifier),
                "seconds": time.perf_counter() - started,
            }
        )

    if args.collapse_ratio > 0.0 and args.collapse_stage == "before":
        collapse()

    if args.solidify_m > 0.0:
        started = time.perf_counter()
        modifier = obj.modifiers.new(name="solidify", type="SOLIDIFY")
        modifier.thickness = args.solidify_m
        modifier.offset = args.solidify_offset
        modifier.use_even_offset = False
        modifier.nonmanifold_thickness_mode = "CONSTRAINTS"
        stages.append(
            {"stage": "solidify", "triangles": apply_modifier(obj, modifier), "seconds": time.perf_counter() - started}
        )

    started = time.perf_counter()
    remesh = obj.modifiers.new(name="remesh", type="REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = args.voxel_size_m
    remesh.adaptivity = args.adaptivity
    stages.append(
        {"stage": "remesh", "triangles": apply_modifier(obj, remesh), "seconds": time.perf_counter() - started}
    )

    if args.collapse_ratio > 0.0 and args.collapse_stage == "after":
        collapse()

    if args.planar_angle_deg > 0.0:
        started = time.perf_counter()
        decimate = obj.modifiers.new(name="planar", type="DECIMATE")
        decimate.decimate_type = "DISSOLVE"
        decimate.angle_limit = math.radians(args.planar_angle_deg)
        decimate.delimit = set()
        stages.append(
            {
                "stage": "planar_decimate",
                "triangles": apply_modifier(obj, decimate),
                "seconds": time.perf_counter() - started,
            }
        )

    started = time.perf_counter()
    obj.modifiers.new(name="triangulate", type="TRIANGULATE")
    vertices, faces = evaluated_triangles(obj)
    vertices, faces = compact(vertices, faces)
    stages.append({"stage": "triangulate", "triangles": len(faces), "seconds": time.perf_counter() - started})

    write_ply(args.out, vertices, faces)
    provenance = {
        "generator": "semantic_twin/remesh_support_mesh.py",
        "source_mesh": str(args.mesh.resolve()),
        "solidify_m": args.solidify_m,
        "solidify_offset": args.solidify_offset,
        "collapse_ratio": args.collapse_ratio,
        "collapse_stage": args.collapse_stage,
        "voxel_size_m": args.voxel_size_m,
        "adaptivity": args.adaptivity,
        "planar_angle_deg": args.planar_angle_deg,
        "stages": stages,
        "vertex_count": len(vertices),
        "triangle_count": len(faces),
        "blender_version": bpy.app.version_string,
    }
    args.out.with_suffix(".json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for stage in stages:
        print(f"[stage] {stage['stage']:<16} {stage['triangles']:>12,} tri  {stage['seconds']:.1f} s", flush=True)
    print(f"[ply] {args.out}", flush=True)


if __name__ == "__main__":
    main()
