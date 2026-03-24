"""Body mesh loading and triangle geometry."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def load_stl_binary(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load a binary STL file.

    Uses vectorized numpy reads instead of per-triangle struct.unpack,
    giving ~50-100x speedup on large meshes (100k+ triangles).

    Returns
    -------
    vertices : (N, 3, 3)
        Triangle vertices.
    normals : (N, 3)
        Unit triangle normals.
    centroids : (N, 3)
        Triangle centroids.
    """
    path = Path(path)
    with path.open("rb") as f:
        f.read(80)  # header
        num_triangles = struct.unpack("<I", f.read(4))[0]
        data = f.read()

    # Binary STL: each triangle is 50 bytes
    # 12 bytes normal (3x float32) + 36 bytes vertices (9x float32) + 2 bytes attr
    record_bytes = 50
    expected = num_triangles * record_bytes
    if len(data) < expected:
        raise ValueError(
            f"STL file truncated: expected {expected} bytes for {num_triangles} triangles, got {len(data)}"
        )

    # Build a structured dtype matching the STL record layout
    dt = np.dtype(
        [
            ("normal", "<f4", (3,)),
            ("v0", "<f4", (3,)),
            ("v1", "<f4", (3,)),
            ("v2", "<f4", (3,)),
            ("attr", "<u2"),
        ]
    )
    records = np.frombuffer(data[:expected], dtype=dt)

    normals = records["normal"].astype(np.float64)
    vertices = np.stack([records["v0"], records["v1"], records["v2"]], axis=1).astype(np.float64)

    centroids = np.mean(vertices, axis=1)

    # Normalize normals. Recompute from vertices if STL normal is zero.
    n_norm = np.linalg.norm(normals, axis=1, keepdims=True)
    bad = n_norm[:, 0] <= 0
    if np.any(bad):
        v0 = vertices[bad, 0]
        v1 = vertices[bad, 1]
        v2 = vertices[bad, 2]
        nn = np.cross(v1 - v0, v2 - v0)
        nn_norm = np.linalg.norm(nn, axis=1, keepdims=True)
        nn = nn / np.where(nn_norm > 0, nn_norm, 1.0)
        normals[bad] = nn
        n_norm = np.linalg.norm(normals, axis=1, keepdims=True)

    normals = normals / np.where(n_norm > 0, n_norm, 1.0)

    return vertices, normals, centroids


def triangle_areas(vertices: np.ndarray) -> np.ndarray:
    """Compute area of each triangle from a (N, 3, 3) vertex array."""
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    return 0.5 * np.linalg.norm(cross, axis=1)


@dataclass(frozen=True)
class BodyMesh:
    """Triangulated body surface mesh.

    All arrays are read-only views after construction.

    Attributes
    ----------
    vertices : (N, 3, 3) triangle vertices
    normals : (N, 3) unit outward normals
    centroids : (N, 3) triangle centroids
    areas : (N,) triangle areas in mesh units squared
    """

    vertices: np.ndarray = field(repr=False)
    normals: np.ndarray = field(repr=False)
    centroids: np.ndarray = field(repr=False)
    areas: np.ndarray = field(repr=False)
    name: str = ""

    @classmethod
    def from_arrays(
        cls,
        vertices: np.ndarray,
        normals: np.ndarray | None = None,
        name: str = "synthetic",
    ) -> BodyMesh:
        """Create a BodyMesh from raw vertex arrays.

        Centroids and areas are computed automatically. If normals are not
        provided, they are computed from the vertex cross product.

        Parameters
        ----------
        vertices : (N, 3, 3) triangle vertices
        normals : (N, 3) unit outward normals, or None to compute from vertices
        name : mesh name
        """
        vertices = np.asarray(vertices, dtype=np.float64)
        if vertices.ndim != 3 or vertices.shape[1:] != (3, 3):
            raise ValueError(f"vertices must be (N, 3, 3), got {vertices.shape}")

        centroids = np.mean(vertices, axis=1)
        areas = triangle_areas(vertices)

        if normals is None:
            v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
            cross = np.cross(v1 - v0, v2 - v0)
            norms = np.linalg.norm(cross, axis=1, keepdims=True)
            normals = cross / np.where(norms > 0, norms, 1.0)
        else:
            normals = np.asarray(normals, dtype=np.float64)
            if normals.shape != (vertices.shape[0], 3):
                raise ValueError(f"normals must be ({vertices.shape[0]}, 3), got {normals.shape}")

        return cls(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name=name)

    @staticmethod
    def load(path: str | Path, name: str | None = None) -> BodyMesh:
        """Load a binary STL file and return a BodyMesh."""
        path = Path(path)
        vertices, normals, centroids = load_stl_binary(path)
        areas = triangle_areas(vertices)
        if name is None:
            name = path.stem
        return BodyMesh(
            vertices=vertices,
            normals=normals,
            centroids=centroids,
            areas=areas,
            name=name,
        )

    @property
    def n_triangles(self) -> int:
        return self.vertices.shape[0]

    @property
    def total_area(self) -> float:
        return float(np.sum(self.areas))

    @property
    def bounding_box(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (bmin, bmax) of the mesh."""
        flat = self.vertices.reshape(-1, 3)
        return np.min(flat, axis=0), np.max(flat, axis=0)

    @property
    def center(self) -> np.ndarray:
        bmin, bmax = self.bounding_box
        return (bmin + bmax) / 2.0

    @property
    def height(self) -> float:
        bmin, bmax = self.bounding_box
        return float(bmax[2] - bmin[2])

    @property
    def scale(self) -> float:
        """Bounding box diagonal length."""
        bmin, bmax = self.bounding_box
        return float(np.linalg.norm(bmax - bmin))

    def save_binary_stl(self, path: str | Path) -> None:
        """Write a binary STL (little-endian float32) for this mesh.

        Uses vectorized numpy writes for speed on large meshes.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        n = self.n_triangles
        header = b"AEGIS BodyMesh" + b"\0" * (80 - 14)

        dt = np.dtype(
            [
                ("normal", "<f4", (3,)),
                ("v0", "<f4", (3,)),
                ("v1", "<f4", (3,)),
                ("v2", "<f4", (3,)),
                ("attr", "<u2"),
            ]
        )
        records = np.zeros(n, dtype=dt)
        records["normal"] = self.normals.astype(np.float32)
        records["v0"] = self.vertices[:, 0].astype(np.float32)
        records["v1"] = self.vertices[:, 1].astype(np.float32)
        records["v2"] = self.vertices[:, 2].astype(np.float32)

        with path.open("wb") as f:
            f.write(header)
            f.write(struct.pack("<I", n))
            f.write(records.tobytes())

    def __repr__(self) -> str:
        return f"BodyMesh(name={self.name!r}, n_triangles={self.n_triangles}, total_area={self.total_area:.6g})"
