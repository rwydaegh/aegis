"""Build a local-ENU PLY from downloaded Inhouse Photorealistic 3D Tiles.

Run inside Blender from the repository's ``semantic_twin`` directory::

    blender --background --python build_inhouse_mesh.py -- \
      --tiles /tmp/korenmarkt-leaf-tiles-200m \
      --out data/geometry/korenmarkt/inhouse_leaf_130m.ply \
      --crop-radius-m 130

The optional blend keeps the imported, aligned source objects unchanged for
inspection. The PLY is assembled independently from their evaluated geometry.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from typing import Any

import bpy
import numpy as np
from mathutils import Matrix

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.export import compact, write_ply  # noqa: E402

WGS84_A = 6378137.0
WGS84_E2 = 6.69437999014e-3


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles", type=pathlib.Path, required=True, help="Directory containing manifest.json and GLBs")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="Output binary PLY")
    parser.add_argument("--crop-radius-m", type=positive_float, help="Keep faces wholly inside this horizontal radius")
    parser.add_argument("--blend", type=pathlib.Path, help="Optional Blender scene containing the aligned source tiles")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def positive_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return result


def llh_to_ecef(lat_deg: float, lon_deg: float, height_m: float = 0.0) -> np.ndarray:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    prime_vertical_radius = WGS84_A / math.sqrt(1.0 - WGS84_E2 * math.sin(lat) ** 2)
    return np.array(
        [
            (prime_vertical_radius + height_m) * math.cos(lat) * math.cos(lon),
            (prime_vertical_radius + height_m) * math.cos(lat) * math.sin(lon),
            (prime_vertical_radius * (1.0 - WGS84_E2) + height_m) * math.sin(lat),
        ],
        dtype=np.float64,
    )


def enu_rotation(lat_deg: float, lon_deg: float) -> np.ndarray:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    east = np.array([-math.sin(lon), math.cos(lon), 0.0])
    north = np.array([-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)])
    up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])
    return np.vstack([east, north, up])


def rotation_x(degrees: float) -> np.ndarray:
    angle = math.radians(degrees)
    return np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, math.cos(angle), -math.sin(angle)],
            [0.0, math.sin(angle), math.cos(angle)],
        ]
    )


def load_manifest(tiles_dir: pathlib.Path) -> tuple[dict[str, Any], list[tuple[dict[str, Any], pathlib.Path]]]:
    manifest_path = tiles_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Tile manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "lat" not in manifest or "lon" not in manifest:
        raise ValueError("Tile manifest must contain lat and lon")
    records = manifest.get("tiles")
    if not isinstance(records, list) or not records:
        raise ValueError("Tile manifest must contain a non-empty tiles list")

    resolved_dir = tiles_dir.resolve()
    payloads = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get("file"), str):
            raise ValueError(f"Tile record {index} must contain a string file field")
        payload = (tiles_dir / record["file"]).resolve()
        if not payload.is_relative_to(resolved_dir):
            raise ValueError(f"Tile record {index} escapes the tiles directory: {record['file']}")
        if not payload.is_file():
            raise FileNotFoundError(f"Tile payload does not exist: {payload}")
        payloads.append((record, payload))
    return manifest, payloads


def source_collection() -> bpy.types.Collection:
    collection = bpy.data.collections.new("Inhouse source tiles")
    bpy.context.scene.collection.children.link(collection)
    return collection


def import_tiles(
    payloads: list[tuple[dict[str, Any], pathlib.Path]], collection: bpy.types.Collection
) -> list[bpy.types.Object]:
    imported: list[bpy.types.Object] = []
    known = set(bpy.data.objects)
    for index, (record, payload) in enumerate(payloads):
        bpy.ops.import_scene.gltf(filepath=str(payload))
        tile_objects = sorted((obj for obj in bpy.data.objects if obj not in known), key=lambda obj: obj.name)
        if not tile_objects:
            raise RuntimeError(f"Blender imported no objects from {payload}")
        for obj in tile_objects:
            obj["source_tile_index"] = index
            obj["source_tile_file"] = record["file"]
            if record.get("geometric_error") is not None:
                obj["source_geometric_error_m"] = float(record["geometric_error"])
        imported.extend(tile_objects)
        known.update(tile_objects)
        print(f"[import] {index + 1}/{len(payloads)} {record['file']} ({len(tile_objects)} objects)", flush=True)

    for obj in imported:
        for current in list(obj.users_collection):
            current.objects.unlink(obj)
        collection.objects.link(obj)
    return imported


def align_to_local_enu(
    imported: list[bpy.types.Object], anchor_ecef: np.ndarray, rotation_enu: np.ndarray
) -> dict[str, Any]:
    imported_set = set(imported)
    roots = sorted(
        (obj for obj in imported if obj.parent is None or obj.parent not in imported_set),
        key=lambda obj: obj.name,
    )
    if not roots:
        raise RuntimeError("Imported tiles contain no root objects for ECEF calibration")

    root_centres = np.array([np.asarray(obj.matrix_world, dtype=np.float64)[:3, 3] for obj in roots])
    mean_centre = np.mean(root_centres, axis=0)
    candidates = {
        "identity": np.eye(3),
        "rx+90": rotation_x(90.0),
        "rx-90": rotation_x(-90.0),
    }
    best_name = ""
    best_error = math.inf
    best_inverse = np.eye(3)
    for name, conversion in candidates.items():
        inverse = conversion.T
        error = float(np.linalg.norm(inverse @ mean_centre - anchor_ecef))
        if error < best_error:
            best_name = name
            best_error = error
            best_inverse = inverse

    transform = np.eye(4)
    transform[:3, :3] = rotation_enu @ best_inverse
    transform[:3, 3] = -rotation_enu @ anchor_ecef
    blender_transform = Matrix(transform.tolist())
    for root in roots:
        root.matrix_world = blender_transform @ root.matrix_world
    bpy.context.view_layer.update()

    print(f"[calib] axis fix = {best_name}, residual to anchor = {best_error:.1f} m", flush=True)
    if best_error > 5000.0:
        print("[calib] WARNING: no candidate lands near anchor, alignment suspect", flush=True)
    return {
        "axis_fix": best_name,
        "residual_to_anchor_m": best_error,
        "root_object_count": len(roots),
        "ecef_to_local_enu_matrix": transform.tolist(),
    }


def collect_world_triangles(collection: bpy.types.Collection) -> tuple[np.ndarray, np.ndarray]:
    vertices_parts: list[np.ndarray] = []
    triangle_parts: list[np.ndarray] = []
    vertex_offset = 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_objects = sorted((obj for obj in collection.all_objects if obj.type == "MESH"), key=lambda obj: obj.name)

    for obj in mesh_objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            if not mesh.vertices or not mesh.loop_triangles:
                continue
            vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
            mesh.vertices.foreach_get("co", vertices)
            vertices = vertices.reshape(-1, 3)
            world = np.asarray(evaluated.matrix_world, dtype=np.float64)
            vertices = vertices @ world[:3, :3].T + world[:3, 3]

            triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
            mesh.loop_triangles.foreach_get("vertices", triangles)
            vertices_parts.append(vertices)
            triangle_parts.append(triangles.reshape(-1, 3) + vertex_offset)
            vertex_offset += len(vertices)
        finally:
            evaluated.to_mesh_clear()

    if not triangle_parts:
        raise RuntimeError("The imported tiles contain no evaluated mesh triangles")
    return np.vstack(vertices_parts), np.vstack(triangle_parts)


def crop_faces(vertices: np.ndarray, faces: np.ndarray, radius_m: float | None) -> np.ndarray:
    if radius_m is None:
        return faces
    horizontal_radius_squared = np.sum(vertices[:, :2] ** 2, axis=1)
    inside = horizontal_radius_squared <= radius_m**2
    return faces[np.all(inside[faces], axis=1)]


def bounding_box(vertices: np.ndarray) -> dict[str, list[float]]:
    return {
        "min_enu_m": vertices.min(axis=0).tolist(),
        "max_enu_m": vertices.max(axis=0).tolist(),
    }


def write_provenance(
    path: pathlib.Path,
    *,
    args: argparse.Namespace,
    manifest: dict[str, Any],
    payloads: list[tuple[dict[str, Any], pathlib.Path]],
    alignment: dict[str, Any],
    before_vertices: int,
    before_triangles: int,
    vertices: np.ndarray,
    faces: np.ndarray,
) -> None:
    geometric_errors = [
        float(record["geometric_error"]) if record.get("geometric_error") is not None else None
        for record, _ in payloads
    ]
    numeric_errors = [error for error in geometric_errors if error is not None]
    provenance = {
        "format_version": 2,
        "generator": "semantic_twin/build_inhouse_mesh.py",
        "coordinate_system": "local ENU metres, z up",
        "source_manifest": str((args.tiles / "manifest.json").resolve()),
        "source_acquisition": {
            "lat_deg": float(manifest["lat"]),
            "lon_deg": float(manifest["lon"]),
            "radius_m": manifest.get("radius"),
            "geometric_error_cutoff_m": manifest.get("cutoff"),
            "request_count": manifest.get("requests"),
            "request_bytes": manifest.get("total_bytes"),
        },
        "source_tile_count": len(payloads),
        "source_tiles": [
            {
                "file": record["file"],
                "geometric_error_m": record.get("geometric_error"),
                "payload_bytes": payload.stat().st_size,
            }
            for record, payload in payloads
        ],
        "source_geometric_errors_m": geometric_errors,
        "source_geometric_error_range_m": {
            "min": min(numeric_errors) if numeric_errors else None,
            "max": max(numeric_errors) if numeric_errors else None,
        },
        "source_payload_bytes": sum(payload.stat().st_size for _, payload in payloads),
        "anchor": {
            "lat_deg": float(manifest["lat"]),
            "lon_deg": float(manifest["lon"]),
            "height_m": 0.0,
        },
        "alignment": alignment,
        "crop_radius_m": args.crop_radius_m,
        "crop_policy": "keep triangles whose three vertices are inside the horizontal radius",
        "before_vertex_count": before_vertices,
        "before_triangle_count": before_triangles,
        "after_vertex_count": len(vertices),
        "after_triangle_count": len(faces),
        "bbox": bounding_box(vertices),
        "output_ply": str(args.out.resolve()),
        "output_bytes": args.out.stat().st_size,
        "blend": str(args.blend.resolve()) if args.blend is not None else None,
        "blender_version": bpy.app.version_string,
    }
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    args = arguments()
    args.tiles = args.tiles.resolve()
    args.out = args.out.resolve()
    if args.blend is not None:
        args.blend = args.blend.resolve()
    manifest, payloads = load_manifest(args.tiles)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.blend is not None:
        args.blend.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = source_collection()
    imported = import_tiles(payloads, collection)

    lat = float(manifest["lat"])
    lon = float(manifest["lon"])
    anchor_ecef = llh_to_ecef(lat, lon, 0.0)
    alignment = align_to_local_enu(imported, anchor_ecef, enu_rotation(lat, lon))

    vertices, faces = collect_world_triangles(collection)
    before_vertices = len(vertices)
    before_triangles = len(faces)
    faces = crop_faces(vertices, faces, args.crop_radius_m)
    if not len(faces):
        raise RuntimeError("The horizontal crop removed every triangle")
    vertices, faces = compact(vertices, faces)

    write_ply(args.out, vertices, faces)
    provenance_path = args.out.with_suffix(".json")
    if args.blend is not None:
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))
        print(f"[blend] {args.blend}", flush=True)
    write_provenance(
        provenance_path,
        args=args,
        manifest=manifest,
        payloads=payloads,
        alignment=alignment,
        before_vertices=before_vertices,
        before_triangles=before_triangles,
        vertices=vertices,
        faces=faces,
    )
    print(
        f"[done] {before_vertices:,} vertices/{before_triangles:,} triangles -> "
        f"{len(vertices):,} vertices/{len(faces):,} triangles",
        flush=True,
    )
    print(f"[ply] {args.out}", flush=True)
    print(f"[manifest] {provenance_path}", flush=True)


if __name__ == "__main__":
    main()
