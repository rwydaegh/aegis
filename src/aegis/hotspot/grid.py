"""Sampling grids for free-space field reconstruction around a focus point.

Two primitives:

``FieldVolume``
    A 3D axis-aligned box of sample points centred on a focus, used for the
    full Maxwell reconstruction and for extracting arbitrarily oriented
    cut planes after the fact.

``SlicePlane``
    A 2D rectangular lattice embedded in 3D, defined by a centre and two
    orthonormal in-plane axes. This generalises the axis-aligned slices in
    the original hybridizer code to any orientation, so a cut can follow the
    beam axis, lie tangent to the skin, or sit transverse to the propagation
    direction.

Both store world-frame sample coordinates as an ``(..., 3)`` array and expose
``points`` as a flat ``(P, 3)`` view, which is all the synthesis layer needs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n < 1e-15:
        raise ValueError("cannot normalise a near-zero vector")
    return v / n


def orthonormal_frame(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return an orthonormal (e1, e2, n) frame with n along ``normal``.

    e1 is chosen to be as horizontal as possible (perpendicular to world z)
    so transverse slices read naturally; e2 completes the right-handed set.
    """
    n = _unit(normal)
    z = np.array([0.0, 0.0, 1.0])
    e1 = np.cross(z, n)
    if np.linalg.norm(e1) < 1e-8:
        # normal is (anti)parallel to z; fall back to world x
        e1 = np.cross(np.array([1.0, 0.0, 0.0]), n)
    e1 = _unit(e1)
    e2 = _unit(np.cross(n, e1))
    return e1, e2, n


@dataclass
class SlicePlane:
    """A 2D lattice of sample points embedded in 3D world space.

    Parameters
    ----------
    center : (3,)
        World-frame centre of the plane.
    e1, e2 : (3,)
        Orthonormal in-plane axes (horizontal, vertical on the rendered slice).
    extent1, extent2 : float
        Full side lengths along e1 and e2 [m].
    n1, n2 : int
        Number of sample points along e1 and e2.
    label : str
        Human-readable tag (e.g. "axial", "tangent").
    """

    center: np.ndarray
    e1: np.ndarray
    e2: np.ndarray
    extent1: float
    extent2: float
    n1: int
    n2: int
    label: str = ""

    def __post_init__(self) -> None:
        self.center = np.asarray(self.center, dtype=float)
        self.e1 = _unit(self.e1)
        self.e2 = _unit(self.e2)
        # local coordinates along each axis, centred on zero
        self.u = np.linspace(-self.extent1 / 2, self.extent1 / 2, self.n1)
        self.v = np.linspace(-self.extent2 / 2, self.extent2 / 2, self.n2)
        uu, vv = np.meshgrid(self.u, self.v, indexing="ij")
        # world coordinates: center + u*e1 + v*e2, shape (n1, n2, 3)
        self.coords = (
            self.center[None, None, :] + uu[..., None] * self.e1[None, None, :] + vv[..., None] * self.e2[None, None, :]
        )

    @classmethod
    def oriented(
        cls,
        center,
        normal,
        extent,
        resolution,
        *,
        in_plane_axis=None,
        label: str = "",
    ) -> SlicePlane:
        """Build a square-ish slice perpendicular to ``normal``.

        ``in_plane_axis`` optionally pins the first in-plane axis (e.g. the
        beam direction) so the slice orientation is meaningful; it is
        projected into the plane and normalised.
        """
        e1_h, e2_h, n = orthonormal_frame(normal)
        if in_plane_axis is not None:
            a = np.asarray(in_plane_axis, dtype=float)
            a = a - np.dot(a, n) * n
            if np.linalg.norm(a) > 1e-8:
                e1_h = _unit(a)
                e2_h = _unit(np.cross(n, e1_h))
        ext = np.atleast_1d(np.asarray(extent, dtype=float))
        ext1, ext2 = (ext[0], ext[0]) if ext.size == 1 else (ext[0], ext[1])
        res = np.atleast_1d(np.asarray(resolution))
        r1, r2 = (int(res[0]), int(res[0])) if res.size == 1 else (int(res[0]), int(res[1]))
        return cls(center, e1_h, e2_h, ext1, ext2, r1, r2, label=label)

    @property
    def points(self) -> np.ndarray:
        """Flat (P, 3) view of the sample coordinates."""
        return self.coords.reshape(-1, 3)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.n1, self.n2)

    def reshape(self, flat: np.ndarray) -> np.ndarray:
        """Reshape a per-point (P, ...) array back to (n1, n2, ...)."""
        flat = np.asarray(flat)
        return flat.reshape(self.n1, self.n2, *flat.shape[1:])

    @property
    def extent_cm(self) -> tuple[float, float, float, float]:
        """imshow/pcolormesh extent in cm: (umin, umax, vmin, vmax)."""
        return (
            100 * self.u[0],
            100 * self.u[-1],
            100 * self.v[0],
            100 * self.v[-1],
        )


@dataclass
class FieldVolume:
    """A 3D axis-aligned box of sample points centred on a focus point."""

    center: np.ndarray
    size: np.ndarray  # (3,) full side lengths [m]
    resolution: np.ndarray  # (3,) point counts

    def __post_init__(self) -> None:
        self.center = np.asarray(self.center, dtype=float)
        size = np.atleast_1d(np.asarray(self.size, dtype=float))
        if size.size == 1:
            size = np.repeat(size, 3)
        self.size = size
        res = np.atleast_1d(np.asarray(self.resolution))
        if res.size == 1:
            res = np.repeat(res, 3)
        self.resolution = res.astype(int)
        self.x = np.linspace(self.center[0] - size[0] / 2, self.center[0] + size[0] / 2, self.resolution[0])
        self.y = np.linspace(self.center[1] - size[1] / 2, self.center[1] + size[1] / 2, self.resolution[1])
        self.z = np.linspace(self.center[2] - size[2] / 2, self.center[2] + size[2] / 2, self.resolution[2])

    @classmethod
    def centered(cls, center, size, resolution) -> FieldVolume:
        return cls(center, size, resolution)

    @property
    def points(self) -> np.ndarray:
        xx, yy, zz = np.meshgrid(self.x, self.y, self.z, indexing="ij")
        return np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(int(n) for n in self.resolution)

    def reshape(self, flat: np.ndarray) -> np.ndarray:
        flat = np.asarray(flat)
        return flat.reshape(*self.shape, *flat.shape[1:])

    def axis_plane(self, axis: str, resolution=None, label: str = "") -> SlicePlane:
        """Extract an axis-normal slice plane through the volume centre."""
        normals = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
        idx = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
        ext = (self.size[idx[0]], self.size[idx[1]])
        if resolution is None:
            resolution = (self.resolution[idx[0]], self.resolution[idx[1]])
        return SlicePlane.oriented(self.center, normals[axis], ext, resolution, label=label or axis)
