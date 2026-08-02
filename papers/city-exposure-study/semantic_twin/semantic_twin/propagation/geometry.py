"""Ray casting backends.

``MitsubaGeometry`` wraps a Mitsuba 3 scene over the support mesh. The Dr.Jit
gotcha recorded in MONOSTATIC_SBR.md is that ``si.n`` comes back as ``(3, N)``
and not ``(N, 3)``, which transposes silently for a square batch, so the
transpose is asserted here rather than assumed.

``PlaneGeometry`` and ``SphereGeometry`` have no mesh at all. They exist so the
closed form validation of section 11.1 and 11.2 runs against the same estimator
that produces the published numbers, not against a copy of it.
"""

from __future__ import annotations

import pathlib
from typing import Any

import numpy as np

INFINITY = 1.0e30


class MitsubaGeometry:
    """Support mesh loaded into Mitsuba 3, queried with ``ray_intersect``."""

    def __init__(self, ply_path: str | pathlib.Path, *, variant: str = "llvm_ad_rgb") -> None:
        import mitsuba as mi

        if mi.variant() != variant:
            mi.set_variant(variant)
        self._mi = mi
        self.path = pathlib.Path(ply_path)
        self.scene = mi.load_dict(
            {
                "type": "scene",
                "mesh": {"type": "ply", "filename": str(self.path), "face_normals": True},
            }
        )
        shape = self.scene.shapes()[0]
        self.vertices = np.array(shape.vertex_positions_buffer()).reshape(-1, 3).astype(np.float64)
        self.faces = np.array(shape.faces_buffer()).reshape(-1, 3).astype(np.int64)

    @property
    def face_count(self) -> int:
        return int(self.faces.shape[0])

    def face_areas(self) -> np.ndarray:
        a = self.vertices[self.faces[:, 0]]
        b = self.vertices[self.faces[:, 1]]
        c = self.vertices[self.faces[:, 2]]
        return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)

    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        mi = self._mi
        ray = mi.Ray3f(
            mi.Point3f(np.ascontiguousarray(origins.T)),
            mi.Vector3f(np.ascontiguousarray(directions.T)),
        )
        si = self.scene.ray_intersect(ray)
        distance = np.array(si.t, dtype=np.float64)
        hit = np.isfinite(distance) & (distance < INFINITY)
        raw_normal = np.array(si.n, dtype=np.float64)
        if raw_normal.shape[0] != 3:
            raise RuntimeError(f"expected si.n as (3, N), got {raw_normal.shape}")
        normal = raw_normal.T
        face = np.array(si.prim_index, dtype=np.int64)
        distance = np.where(hit, distance, INFINITY)
        return hit, distance, normal, face


class PlaneGeometry:
    """An infinite plane ``z = plane_z`` with a single material class."""

    def __init__(self, plane_z: float = 0.0) -> None:
        self.plane_z = float(plane_z)

    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        dz = directions[:, 2]
        height = origins[:, 2] - self.plane_z
        with np.errstate(divide="ignore", invalid="ignore"):
            distance = -height / dz
        hit = np.isfinite(distance) & (distance > 0.0)
        distance = np.where(hit, distance, INFINITY)
        normal = np.tile(np.array([0.0, 0.0, 1.0]), (origins.shape[0], 1))
        face = np.zeros(origins.shape[0], dtype=np.int64)
        return hit, distance, normal, face


class SphereGeometry:
    """The inside of a sphere of radius ``radius`` centred on ``centre``."""

    def __init__(self, radius: float, centre: Any = (0.0, 0.0, 0.0)) -> None:
        self.radius = float(radius)
        self.centre = np.asarray(centre, dtype=np.float64)

    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        offset = origins - self.centre
        b = np.einsum("ij,ij->i", offset, directions)
        c = np.einsum("ij,ij->i", offset, offset) - self.radius**2
        discriminant = b * b - c
        root = np.sqrt(np.maximum(discriminant, 0.0))
        distance = -b + root
        hit = (discriminant > 0.0) & (distance > 0.0)
        distance = np.where(hit, distance, INFINITY)
        point = origins + np.where(hit, distance, 0.0)[:, None] * directions
        normal = self.centre - point
        norms = np.linalg.norm(normal, axis=1, keepdims=True)
        normal = np.divide(normal, np.where(norms > 0.0, norms, 1.0))
        face = np.zeros(origins.shape[0], dtype=np.int64)
        return hit, distance, normal, face
