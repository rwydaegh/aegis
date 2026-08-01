"""Project adaptive, pixel-faithful semantic tiles onto a coarse Blender mesh.

Unlike ``project_semantics.py``, this script never assigns one label to an
existing photogrammetry triangle. It starts from the dense perspective label
maps. Uniform image regions may merge, but semantic boundaries split down to
the original source pixels. Every accepted tile is then ray-projected from the
recovered Street View camera onto the first Inhouse-mesh surface.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from collections import Counter

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from project_semantics import is_object, mesh_arrays  # noqa: E402
from render_blender_alignment import (  # noqa: E402
    camera_matrix,
    cylinder_between,
    local_view_basis,
    look_at,
    material,
    panorama_rotation,
    setup_scene,
)
from render_projected_semantics import PREFERRED_COLOURS, fallback_colour  # noqa: E402
from semantic_twin.pixel_projection import (  # noqa: E402
    SemanticTile,
    adaptive_semantic_tiles,
    edge_aware_smooth_depth,
    plane_fit_error,
)


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--yaws", type=int, nargs="+", default=[0, 90, 180, 270])
    parser.add_argument("--min-confidence", type=float, default=0.35)
    parser.add_argument("--max-tile-pixels", type=int, default=16)
    parser.add_argument("--max-surface-error", type=float, default=0.08)
    parser.add_argument("--surface-offset", type=float, default=0.015)
    parser.add_argument("--smooth-surface", action="store_true")
    parser.add_argument("--depth-grid-size", type=int, default=257)
    parser.add_argument("--smooth-iterations", type=int, default=4)
    parser.add_argument("--edge-sigma-m", type=float, default=0.75)
    parser.add_argument("--max-smooth-deviation-m", type=float, default=1.5)
    parser.add_argument("--size", type=int, default=1024)
    return parser.parse_args(argv)


def pixel_boundary_direction(x: float, y: float, width: int, height: int, yaw_deg: float) -> Vector:
    """Panorama-local ray through a perspective-view pixel boundary."""
    yaw = math.radians(yaw_deg)
    forward = Vector((math.sin(yaw), math.cos(yaw), 0.0))
    right = Vector((math.cos(yaw), -math.sin(yaw), 0.0))
    up = right.cross(forward)
    tangent_x = math.tan(math.radians(45.0))
    tangent_y = tangent_x / (width / height)
    image_x = (x / width * 2.0 - 1.0) * tangent_x
    image_y = (1.0 - y / height * 2.0) * tangent_y
    return (forward + image_x * right + image_y * up).normalized()


class SurfaceProjector:
    def __init__(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        camera: Vector,
        rotation,
        width: int,
        height: int,
        yaw: int,
        *,
        max_tile_pixels: int,
        max_surface_error: float,
        surface_offset: float,
        smooth_surface: bool,
        depth_grid_size: int,
        smooth_iterations: int,
        edge_sigma_m: float,
        max_smooth_deviation_m: float,
    ) -> None:
        self.bvh = BVHTree.FromPolygons([Vector(vertex) for vertex in vertices], faces.tolist(), all_triangles=True)
        self.camera = camera
        self.rotation = rotation
        self.width = width
        self.height = height
        self.yaw = yaw
        self.max_tile_pixels = max_tile_pixels
        self.max_surface_error = max_surface_error
        self.surface_offset = surface_offset
        self.max_smooth_deviation_m = max_smooth_deviation_m
        self.hits: dict[tuple[float, float], tuple[Vector, Vector, int, float] | None] = {}
        self.ray_count = 0
        self._smooth_depth: np.ndarray | None = None
        self._smooth_valid: np.ndarray | None = None
        if smooth_surface:
            if depth_grid_size < 17:
                raise ValueError("depth_grid_size must be at least 17")
            self._build_smooth_depth(depth_grid_size, smooth_iterations, edge_sigma_m)

    def _build_smooth_depth(self, size: int, iterations: int, edge_sigma_m: float) -> None:
        depth = np.full((size, size), np.nan, dtype=float)
        for row in range(size):
            y = row * self.height / (size - 1)
            for column in range(size):
                x = column * self.width / (size - 1)
                hit = self.hit(x, y)
                if hit is not None:
                    depth[row, column] = hit[3]
        valid = np.isfinite(depth)
        self._smooth_valid = valid
        self._smooth_depth = edge_aware_smooth_depth(depth, valid, iterations=iterations, edge_sigma_m=edge_sigma_m)

    def _smooth_distance(self, x: float, y: float) -> float | None:
        if self._smooth_depth is None or self._smooth_valid is None:
            return None
        height, width = self._smooth_depth.shape
        fx = np.clip(x / self.width * (width - 1), 0.0, width - 1.0)
        fy = np.clip(y / self.height * (height - 1), 0.0, height - 1.0)
        x0, y0 = int(np.floor(fx)), int(np.floor(fy))
        x1, y1 = min(x0 + 1, width - 1), min(y0 + 1, height - 1)
        samples = ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
        if not all(self._smooth_valid[row, column] for column, row in samples):
            return None
        dx, dy = fx - x0, fy - y0
        return float(
            (1.0 - dx) * (1.0 - dy) * self._smooth_depth[y0, x0]
            + dx * (1.0 - dy) * self._smooth_depth[y0, x1]
            + (1.0 - dx) * dy * self._smooth_depth[y1, x0]
            + dx * dy * self._smooth_depth[y1, x1]
        )

    def _point(self, x: float, y: float, raw: tuple[Vector, Vector, int, float]) -> Vector:
        distance = self._smooth_distance(x, y)
        if distance is None or abs(distance - raw[3]) > self.max_smooth_deviation_m:
            return raw[0]
        return self.camera + self.direction(x, y) * distance

    def hit(self, x: float, y: float) -> tuple[Vector, Vector, int, float] | None:
        key = (x, y)
        if key in self.hits:
            return self.hits[key]
        direction = self.direction(x, y)
        location, normal, face_id, distance = self.bvh.ray_cast(self.camera, direction, 2000.0)
        self.ray_count += 1
        if location is None or normal is None or face_id is None or distance is None:
            result = None
        else:
            result = (location, normal.normalized(), int(face_id), float(distance))
        self.hits[key] = result
        return result

    def direction(self, x: float, y: float) -> Vector:
        local = pixel_boundary_direction(x, y, self.width, self.height, self.yaw)
        return (self.rotation @ local).normalized()

    def _samples(self, tile: SemanticTile) -> dict[str, tuple[Vector, Vector, int, float] | None]:
        xm = (tile.x0 + tile.x1) * 0.5
        ym = (tile.y0 + tile.y1) * 0.5
        return {
            "tl": self.hit(tile.x0, tile.y0),
            "tr": self.hit(tile.x1, tile.y0),
            "br": self.hit(tile.x1, tile.y1),
            "bl": self.hit(tile.x0, tile.y1),
            "tm": self.hit(xm, tile.y0),
            "rm": self.hit(tile.x1, ym),
            "bm": self.hit(xm, tile.y1),
            "lm": self.hit(tile.x0, ym),
            "c": self.hit(xm, ym),
        }

    def _continuous(self, samples: dict[str, tuple[Vector, Vector, int, float] | None]) -> bool:
        if any(hit is None for hit in samples.values()):
            return False
        coordinates = np.asarray([tuple(hit[0]) for hit in samples.values() if hit is not None])
        error, plane_normal_array = plane_fit_error(coordinates)
        if error > self.max_surface_error:
            return False
        plane_normal = Vector(plane_normal_array)
        normals = [hit[1] for hit in samples.values() if hit is not None]
        return min(abs(normal.dot(plane_normal)) for normal in normals) >= math.cos(math.radians(50.0))

    def _leaf_fallback(self, tile: SemanticTile, samples) -> dict[str, Vector] | None:
        """Project a one-pixel surfel from its reliable centre hit.

        Photogrammetry cracks often make a corner ray miss even when the pixel
        centre has a sound first hit. Intersecting the four boundary rays with
        the centre hit's tangent plane preserves that source pixel instead of
        silently dropping it.
        """
        centre = samples["c"]
        if centre is None:
            return None
        centre_point, centre_normal, _face_id, _distance = centre
        numerator = centre_normal.dot(centre_point - self.camera)
        corners = {
            "tl": (tile.x0, tile.y0),
            "tr": (tile.x1, tile.y0),
            "br": (tile.x1, tile.y1),
            "bl": (tile.x0, tile.y1),
        }
        projected = {}
        for name, (x, y) in corners.items():
            direction = self.direction(x, y)
            denominator = centre_normal.dot(direction)
            if abs(denominator) < 1e-7:
                return None
            distance = numerator / denominator
            if distance <= 0.0:
                return None
            projected[name] = self.camera + direction * distance
        return projected

    @staticmethod
    def split(tile: SemanticTile) -> list[SemanticTile]:
        xm = (tile.x0 + tile.x1) // 2
        ym = (tile.y0 + tile.y1) // 2
        children = (
            SemanticTile(tile.x0, tile.y0, xm, ym, tile.class_id),
            SemanticTile(xm, tile.y0, tile.x1, ym, tile.class_id),
            SemanticTile(tile.x0, ym, xm, tile.y1, tile.class_id),
            SemanticTile(xm, ym, tile.x1, tile.y1, tile.class_id),
        )
        return [child for child in children if child.width > 0 and child.height > 0]

    def project(self, semantic_tiles: list[SemanticTile]) -> tuple[list[Vector], list[tuple[int, int, int]], list[int]]:
        vertices: list[Vector] = []
        faces: list[tuple[int, int, int]] = []
        classes: list[int] = []
        vertex_ids: dict[tuple[float, ...], int] = {}
        pending = list(semantic_tiles)
        while pending:
            tile = pending.pop()
            samples = self._samples(tile)
            oversized = tile.width > self.max_tile_pixels or tile.height > self.max_tile_pixels
            continuous = self._continuous(samples)
            if (oversized or not continuous) and (tile.width > 1 or tile.height > 1):
                pending.extend(self.split(tile))
                continue
            fallback = None if continuous else self._leaf_fallback(tile, samples)
            if not continuous and fallback is None:
                continue

            corners = (
                (tile.x0, tile.y0, "tl"),
                (tile.x1, tile.y0, "tr"),
                (tile.x1, tile.y1, "br"),
                (tile.x0, tile.y1, "bl"),
            )
            indices = []
            for x, y, name in corners:
                key = (float(x), float(y)) if continuous else (float(x), float(y), tile.x0, tile.y0)
                if key not in vertex_ids:
                    point = self._point(x, y, samples[name]) if continuous else fallback[name]
                    toward_camera = (self.camera - point).normalized()
                    vertex_ids[key] = len(vertices)
                    vertices.append(point + toward_camera * self.surface_offset)
                indices.append(vertex_ids[key])
            diagonal_a = (vertices[indices[0]] - vertices[indices[2]]).length
            diagonal_b = (vertices[indices[1]] - vertices[indices[3]]).length
            if diagonal_a <= diagonal_b:
                faces.extend(((indices[0], indices[1], indices[2]), (indices[0], indices[2], indices[3])))
            else:
                faces.extend(((indices[0], indices[1], indices[3]), (indices[1], indices[2], indices[3])))
            classes.extend((tile.class_id, tile.class_id))
        return vertices, faces, classes


def main() -> None:
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    pose = json.loads(args.pose.read_text())
    document = json.loads(args.semantics_json.read_text())
    labels_by_id = {int(class_id): name for class_id, name in document["entity_id2label"].items()}
    object_ids = {class_id for class_id, name in labels_by_id.items() if is_object(name)}
    sky_ids = {class_id for class_id, name in labels_by_id.items() if name.casefold() == "sky"}

    scene = setup_scene(args.size)
    bpy.ops.wm.ply_import(filepath=str(args.mesh.resolve()))
    source = bpy.context.object
    source.name = "Inhouse photogrammetry reference"
    vertices, faces = mesh_arrays(source)
    source.hide_render = True

    camera_location = Vector(pose["position_enu_m"])
    rotation = panorama_rotation(
        float(pose["heading_deg"]),
        float(pose["pitch_correction_deg"]),
        float(pose["roll_correction_deg"]),
    )
    camera_data = bpy.data.cameras.new("Recovered Street View camera")
    camera_data.angle = math.radians(90.0)
    camera_data.clip_start = 0.03
    camera_data.clip_end = 2000.0
    camera = bpy.data.objects.new("Recovered Street View camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera

    manifests = []
    all_legend: dict[int, dict] = {}
    projected_objects = []
    for yaw in args.yaws:
        labels = np.load(args.views / f"h+00_{yaw:03d}_labels.npy")
        confidence = np.load(args.views / f"h+00_{yaw:03d}_confidence.npy")
        valid = (confidence >= args.min_confidence) & ~np.isin(labels, list(object_ids | sky_ids))
        semantic_tiles = adaptive_semantic_tiles(labels, valid)
        projector = SurfaceProjector(
            vertices,
            faces,
            camera_location,
            rotation,
            labels.shape[1],
            labels.shape[0],
            yaw,
            max_tile_pixels=args.max_tile_pixels,
            max_surface_error=args.max_surface_error,
            surface_offset=args.surface_offset,
            smooth_surface=args.smooth_surface,
            depth_grid_size=args.depth_grid_size,
            smooth_iterations=args.smooth_iterations,
            edge_sigma_m=args.edge_sigma_m,
            max_smooth_deviation_m=args.max_smooth_deviation_m,
        )
        projected_vertices, projected_faces, face_classes = projector.project(semantic_tiles)
        mesh_data = bpy.data.meshes.new(f"Pixel semantic mesh yaw {yaw}")
        mesh_data.from_pydata([tuple(vertex) for vertex in projected_vertices], [], projected_faces)
        mesh_data.update()
        projected = bpy.data.objects.new(f"Pixel semantic projection yaw {yaw}", mesh_data)
        bpy.context.collection.objects.link(projected)
        projected_objects.append(projected)

        class_to_slot = {}
        for class_id in sorted(set(face_classes)):
            name = labels_by_id.get(class_id, f"class {class_id}")
            colour = PREFERRED_COLOURS.get(name.casefold(), fallback_colour(class_id))
            class_to_slot[class_id] = len(mesh_data.materials)
            mesh_data.materials.append(material(f"{name} yaw {yaw}", colour, emission=1.0))
            all_legend[class_id] = {
                "id": class_id,
                "name": name,
                "rgb": [round(255 * value) for value in colour[:3]],
            }
        for polygon, class_id in zip(mesh_data.polygons, face_classes, strict=True):
            polygon.material_index = class_to_slot[class_id]

        camera.matrix_world = camera_matrix(camera_location, rotation, yaw)
        scene.render.filepath = str(args.out / f"pixel_projected_yaw_{yaw:03d}.png")
        bpy.ops.render.render(write_still=True)
        projected.hide_render = True
        counts = Counter(face_classes)
        manifests.append(
            {
                "yaw": yaw,
                "source_shape": list(labels.shape),
                "valid_source_pixels": int(valid.sum()),
                "semantic_tiles_before_geometry": len(semantic_tiles),
                "projected_vertices": len(projected_vertices),
                "projected_triangles": len(projected_faces),
                "ray_queries": projector.ray_count,
                "triangle_classes": {labels_by_id.get(key, str(key)): value for key, value in sorted(counts.items())},
            }
        )

    for projected in projected_objects:
        projected.hide_render = False
    source.hide_render = False
    source.data.materials.clear()
    source.data.materials.append(material("Photogrammetry reference", (0.07, 0.09, 0.14, 1.0), emission=0.22))

    bpy.ops.object.light_add(type="SUN", location=camera_location + Vector((0.0, 0.0, 80.0)))
    sun = bpy.context.object
    sun.data.energy = 2.5
    sun.data.angle = math.radians(18.0)
    sun.rotation_euler = (math.radians(32.0), math.radians(-24.0), math.radians(28.0))

    camera_marker = material("Recovered camera marker", (1.0, 0.04, 0.015, 1.0), emission=0.8)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.65, location=camera_location)
    bpy.context.object.data.materials.append(camera_marker)
    for yaw in args.yaws:
        _, local_forward, _ = local_view_basis(yaw)
        direction = rotation @ local_forward
        cylinder_between(camera_location, camera_location + direction * 8.0, 0.08, camera_marker)

    overview_data = bpy.data.cameras.new("Pixel projection overview camera")
    overview = bpy.data.objects.new("Pixel projection overview camera", overview_data)
    bpy.context.collection.objects.link(overview)
    overview.location = camera_location + Vector((62.0, -62.0, 42.0))
    overview_data.lens = 48.0
    overview_data.clip_end = 2000.0
    look_at(overview, camera_location + Vector((0.0, 0.0, 2.0)))
    scene.camera = overview
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.012, 0.024)
    scene.render.filepath = str(args.out / "pixel_projection_overview.png")
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=str((args.out / "pixel_semantic_projection.blend").resolve()))
    manifest = {
        "method": "adaptive source-pixel tiles ray-projected onto first-hit photogrammetry surface",
        "source_mesh": str(args.mesh),
        "pose": str(args.pose),
        "min_confidence": args.min_confidence,
        "max_tile_pixels": args.max_tile_pixels,
        "max_surface_error_m": args.max_surface_error,
        "surface_offset_m": args.surface_offset,
        "excluded_object_classes": sorted(labels_by_id[class_id] for class_id in object_ids),
        "views": manifests,
        "legend": [all_legend[class_id] for class_id in sorted(all_legend)],
    }
    (args.out / "pixel_projection_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
