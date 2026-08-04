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
from dataclasses import dataclass
from typing import Any

import numpy as np

INFINITY = 1.0e30


@dataclass(frozen=True)
class DeviceIntersection:
    """A Mitsuba intersection whose fields remain on the active Dr.Jit backend."""

    hit: Any
    distance: Any
    normal: Any
    face: Any


class MitsubaGeometry:
    """Support mesh loaded into Mitsuba 3, queried with ``ray_intersect``.

    Pickles as its own recipe. The Mitsuba scene and its acceleration structure
    are native objects with no serialisation, so what crosses a process boundary
    is the mesh path and the variant, and the receiving process loads the mesh
    itself. That is what lets a sweep hand a tracer to a pool of workers, and it
    costs one mesh load per worker rather than one per observation point.
    """

    def __init__(self, ply_path: str | pathlib.Path, *, variant: str = "llvm_ad_rgb") -> None:
        import mitsuba as mi

        if mi.variant() != variant:
            mi.set_variant(variant)
        self._mi = mi
        self.variant = variant
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
        self._face_normals: np.ndarray | None = None
        self._device_normals: Any = None

    def __reduce__(self) -> tuple[Any, tuple[Any, ...]]:
        return (_load_mitsuba_geometry, (str(self.path), self.variant))

    @property
    def face_count(self) -> int:
        return int(self.faces.shape[0])

    def face_areas(self) -> np.ndarray:
        a = self.vertices[self.faces[:, 0]]
        b = self.vertices[self.faces[:, 1]]
        c = self.vertices[self.faces[:, 2]]
        return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)

    def face_normals(self) -> np.ndarray:
        """Unit geometric normal per face, in the winding order of the mesh.

        Built once and kept. The scene loads with ``face_normals=True``, so this
        is the same quantity ``si.n`` reports, computed in float64 rather than
        the float32 Mitsuba returns.
        """
        if self._face_normals is None:
            a = self.vertices[self.faces[:, 0]]
            normal = np.cross(self.vertices[self.faces[:, 1]] - a, self.vertices[self.faces[:, 2]] - a)
            length = np.linalg.norm(normal, axis=1, keepdims=True)
            self._face_normals = normal / np.maximum(length, 1.0e-300)
        return self._face_normals

    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        # ``ray_intersect`` builds a full SurfaceInteraction3f, with UVs, shading
        # frames and position partials that nothing here reads, and then each
        # field is moved to numpy separately. The preliminary query returns the
        # distance and the face and stops, and the normal comes from indexing a
        # precomputed table. Measured at 1.76 times the full query on the CPU
        # path and bit identical on hit, face, distance and normal. It is slower
        # under CUDA, where the table lookup lands on the host.
        mi = self._mi
        ray = mi.Ray3f(
            mi.Point3f(np.ascontiguousarray(origins.T)),
            mi.Vector3f(np.ascontiguousarray(directions.T)),
        )
        pi = self.scene.ray_intersect_preliminary(ray)
        distance = np.array(pi.t, dtype=np.float64)
        hit = np.isfinite(distance) & (distance < INFINITY)
        # A miss leaves prim_index undefined, and it comes back well past the
        # face count. ``ray_intersect`` reported 0 there, so keep that, or a
        # caller that reads the face without masking on the hit flag indexes out
        # of range.
        face = np.where(hit, np.array(pi.prim_index, dtype=np.int64), 0)
        normal = np.where(hit[:, None], self.face_normals()[face], 0.0)
        distance = np.where(hit, distance, INFINITY)
        return hit, distance, normal, face

    def intersect_device(self, origins: Any, directions: Any, active: Any) -> DeviceIntersection:
        """Intersect without moving rays, hits, or normals through NumPy.

        The mesh acceleration structure, preliminary hit query, and face-normal
        lookup all run on the backend selected by ``variant``. The ordinary
        :meth:`intersect` method stays as the NumPy reference path.
        """
        import drjit as dr

        mi = self._mi
        self.prepare_device()
        ray = mi.Ray3f(origins, directions)
        preliminary = self.scene.ray_intersect_preliminary(ray, False, active)
        hit = active & preliminary.is_valid() & (preliminary.t < INFINITY)
        face = dr.select(hit, preliminary.prim_index, 0)
        normal = dr.gather(mi.Vector3f, self._device_normals, face, hit)
        distance = dr.select(hit, preliminary.t, INFINITY)
        return DeviceIntersection(hit, distance, normal, face)

    def prepare_device(self) -> None:
        """Upload the face-normal lookup before a timed device trace."""
        import drjit as dr

        mi = self._mi
        if mi.variant() != self.variant:
            raise RuntimeError(
                f"MitsubaGeometry was built for {self.variant!r}, but the active variant is {mi.variant()!r}"
            )
        if self._device_normals is None:
            normals = self.face_normals()
            self._device_normals = mi.Vector3f(
                mi.Float(np.ascontiguousarray(normals[:, 0])),
                mi.Float(np.ascontiguousarray(normals[:, 1])),
                mi.Float(np.ascontiguousarray(normals[:, 2])),
            )
            dr.eval(self._device_normals)


def _load_mitsuba_geometry(ply_path: str, variant: str) -> MitsubaGeometry:
    """Module level so :meth:`MitsubaGeometry.__reduce__` has something to name."""
    return MitsubaGeometry(ply_path, variant=variant)


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
