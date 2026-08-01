"""Read the support mesh and answer the two geometric questions registration needs.

The first is the ground elevation under a camera, which replaces the scene-wide
``camera_ground_z_m`` constant with a measurement at the camera's own easting and
northing. The second is first-hit range along arbitrary rays, which is what turns
"segmentation says sky here" into a testable claim about the geometry.

Both consume the same binary PLY the acquisition writes, so nothing has to be
rebuilt to use them.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np


def read_binary_ply(path: pathlib.Path) -> tuple[np.ndarray, np.ndarray]:
    """Read vertices and triangle indices from the compact binary PLY.

    The acquisition writes ``float`` vertices and a ``uchar int`` face list with
    exactly three indices per face, which is the only layout accepted here. A
    silently different layout would produce plausible but wrong geometry, so it
    raises instead.
    """
    with path.open("rb") as stream:
        if stream.readline().decode().strip() != "ply":
            raise ValueError(f"not a PLY file: {path}")
        vertex_count: int | None = None
        face_count: int | None = None
        binary_little = False
        element: str | None = None
        properties: list[str] = []
        while True:
            line = stream.readline().decode().strip()
            if line == "format binary_little_endian 1.0":
                binary_little = True
            elif line.startswith("element vertex "):
                element = "vertex"
                vertex_count = int(line.rsplit(" ", 1)[1])
            elif line.startswith("element face "):
                element = "face"
                face_count = int(line.rsplit(" ", 1)[1])
            elif line.startswith("property ") and element == "vertex":
                properties.append(line.split(" ", 1)[1])
            elif line.startswith("property ") and element == "face":
                if line != "property list uchar int vertex_indices":
                    raise ValueError(f"unsupported face property in {path}: {line}")
            elif line == "end_header":
                break
            elif not line:
                raise ValueError(f"truncated PLY header in {path}")
        if not binary_little or vertex_count is None or face_count is None:
            raise ValueError("expected a binary_little_endian PLY with vertex and face elements")
        if properties != ["float x", "float y", "float z"]:
            raise ValueError(f"expected exactly float x, y, z vertices in {path}, found {properties}")
        vertices = np.fromfile(stream, dtype="<f4", count=vertex_count * 3).reshape(vertex_count, 3)
        record = np.dtype([("count", "u1"), ("indices", "<i4", 3)])
        faces = np.fromfile(stream, dtype=record, count=face_count)
    if len(faces) != face_count or np.any(faces["count"] != 3):
        raise ValueError(f"expected {face_count} triangular faces in {path}")
    return vertices.astype(np.float64), faces["indices"].astype(np.int64)


def read_binary_ply_vertices(path: pathlib.Path) -> np.ndarray:
    """Read only the vertices, skipping the face list."""
    with path.open("rb") as stream:
        if stream.readline().decode().strip() != "ply":
            raise ValueError(f"not a PLY file: {path}")
        count = None
        binary_little = False
        while True:
            line = stream.readline().decode().strip()
            if line == "format binary_little_endian 1.0":
                binary_little = True
            if line.startswith("element vertex "):
                count = int(line.rsplit(" ", 1)[1])
            if line == "end_header":
                break
            if not line:
                raise ValueError(f"truncated PLY header in {path}")
        if not binary_little or count is None:
            raise ValueError("expected binary_little_endian PLY with vertices")
        return np.fromfile(stream, dtype="<f4", count=count * 3).reshape(count, 3)


@dataclass(frozen=True)
class GroundSample:
    """Support-mesh ground elevation under one camera.

    ``spread_m`` and ``peak_to_peak_m`` describe the patch the value was taken
    over, so a camera standing on a step or over a hole in the photogrammetry is
    visible as a wide spread rather than as a confidently wrong number.
    """

    elevation_m: float
    spread_m: float
    peak_to_peak_m: float
    n_hits: int
    n_samples: int
    patch_m: float
    source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "ground_elevation_m": self.elevation_m,
            "ground_spread_m": self.spread_m,
            "ground_peak_to_peak_m": self.peak_to_peak_m,
            "ground_n_hits": self.n_hits,
            "ground_n_samples": self.n_samples,
            "ground_patch_m": self.patch_m,
            "ground_source": self.source,
        }


def _downward_hits(vertices: np.ndarray, faces: np.ndarray, points: np.ndarray, ceiling_z: float) -> list[float]:
    """Topmost surface at or below ``ceiling_z`` under each xy point."""
    triangles = vertices[faces]
    ax, ay = triangles[:, 0, 0], triangles[:, 0, 1]
    bx, by = triangles[:, 1, 0], triangles[:, 1, 1]
    cx, cy = triangles[:, 2, 0], triangles[:, 2, 1]
    lo_x = np.minimum(np.minimum(ax, bx), cx)
    hi_x = np.maximum(np.maximum(ax, bx), cx)
    lo_y = np.minimum(np.minimum(ay, by), cy)
    hi_y = np.maximum(np.maximum(ay, by), cy)
    area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
    elevations: list[float] = []
    for x, y in points:
        near = (lo_x <= x) & (hi_x >= x) & (lo_y <= y) & (hi_y >= y) & (np.abs(area) > 1e-12)
        if not np.any(near):
            continue
        index = np.flatnonzero(near)
        w0 = ((bx[index] - x) * (cy[index] - y) - (cx[index] - x) * (by[index] - y)) / area[index]
        w1 = ((cx[index] - x) * (ay[index] - y) - (ax[index] - x) * (cy[index] - y)) / area[index]
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not np.any(inside):
            continue
        z = w0[inside] * triangles[index[inside], 0, 2]
        z += w1[inside] * triangles[index[inside], 1, 2]
        z += w2[inside] * triangles[index[inside], 2, 2]
        below = z[z <= ceiling_z]
        if below.size:
            elevations.append(float(below.max()))
    return elevations


def ground_elevation(
    vertices: np.ndarray,
    faces: np.ndarray,
    easting_m: float,
    northing_m: float,
    *,
    ceiling_z_m: float,
    patch_m: float = 3.0,
    samples_per_axis: int = 5,
) -> GroundSample:
    """Cast down onto the support mesh under one camera and report the spread.

    ``ceiling_z_m`` is where the downward ray starts, so an arcade roof or a
    balcony above the camera is not mistaken for the pavement. The patch median
    is used rather than the single central hit because the photogrammetry has
    occasional holes and single-triangle spikes at street level.
    """
    if samples_per_axis < 1:
        raise ValueError("samples_per_axis must be at least one")
    if patch_m < 0.0:
        raise ValueError("patch_m must be non-negative")
    offsets = (
        np.zeros(1)
        if samples_per_axis == 1 or patch_m == 0.0
        else np.linspace(-patch_m / 2.0, patch_m / 2.0, samples_per_axis)
    )
    grid = np.stack(np.meshgrid(offsets + easting_m, offsets + northing_m), axis=-1).reshape(-1, 2)
    elevations = _downward_hits(vertices, faces, grid, ceiling_z_m)
    if not elevations:
        raise ValueError(f"support mesh has no surface under ({easting_m:.3f}, {northing_m:.3f}) below {ceiling_z_m}")
    values = np.asarray(elevations, dtype=float)
    return GroundSample(
        elevation_m=float(np.median(values)),
        spread_m=float(values.std(ddof=1)) if values.size > 1 else 0.0,
        peak_to_peak_m=float(values.max() - values.min()),
        n_hits=int(values.size),
        n_samples=int(len(grid)),
        patch_m=float(patch_m),
        source="support mesh downward ray cast, patch median",
    )


def camera_altitude(
    scene: dict[str, Any],
    easting_m: float,
    northing_m: float,
    *,
    support_mesh: tuple[np.ndarray, np.ndarray] | None = None,
    search_up_m: float = 5.0,
    patch_m: float = 3.0,
) -> tuple[float, dict[str, Any]]:
    """Camera altitude for one panorama, measured where possible.

    ``camera_ground_z_m`` in the scene config is a single constant for the whole
    site, so a camera on a flight of steps or a ramp inherits the pavement height
    under a different camera. When the support mesh is available the ground is
    instead cast for under this camera's own easting and northing, and the scene
    constant survives only as the datum for the search ceiling and as the
    fallback. ``search_up_m`` is how far above that datum a surface may be and
    still count as ground, which keeps an arcade roof out of the answer.
    """
    ground_z = float(scene["camera_ground_z_m"])
    camera_height = float(scene.get("camera_height_m", 2.5))
    if support_mesh is None:
        return ground_z + camera_height, {
            "altitude_source": "scene camera_ground_z_m plus configured camera height",
            "scene_camera_ground_z_m": ground_z,
        }
    vertices, faces = support_mesh
    sample = ground_elevation(
        vertices,
        faces,
        easting_m,
        northing_m,
        ceiling_z_m=ground_z + search_up_m,
        patch_m=patch_m,
    )
    provenance: dict[str, Any] = {
        "altitude_source": "support mesh downward ray cast under this camera plus configured camera height",
        "scene_camera_ground_z_m": ground_z,
        "ground_minus_scene_constant_m": sample.elevation_m - ground_z,
    }
    provenance.update(sample.as_dict())
    return sample.elevation_m + camera_height, provenance


def first_hit_range(
    vertices: np.ndarray,
    faces: np.ndarray,
    origin: np.ndarray,
    directions: np.ndarray,
) -> np.ndarray:
    """First-hit range in metres along each unit direction, NaN where nothing is hit.

    Backed by Embree through trimesh. It is an optional dependency because only
    the registration diagnostics need it, so the import failure names the extra.
    """
    try:
        import trimesh
        from trimesh.ray.ray_pyembree import RayMeshIntersector
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError("first_hit_range needs the raycast extra: pip install trimesh embreex") from exc
    directions = np.asarray(directions, dtype=np.float64).reshape(-1, 3)
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices, dtype=np.float64), faces=np.asarray(faces), process=False)
    intersector = RayMeshIntersector(mesh)
    origins = np.repeat(np.asarray(origin, dtype=np.float64).reshape(1, 3), len(directions), axis=0)
    locations, index_ray, _ = intersector.intersects_location(origins, directions, multiple_hits=False)
    ranges = np.full(len(directions), np.nan)
    if len(index_ray):
        ranges[index_ray] = np.linalg.norm(locations - origins[index_ray], axis=1)
    return ranges
