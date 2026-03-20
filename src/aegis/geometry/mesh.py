"""Body mesh loading and triangle geometry."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def load_stl_binary(path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load a binary STL file.

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

        vertices = np.zeros((num_triangles, 3, 3), dtype=np.float64)
        normals = np.zeros((num_triangles, 3), dtype=np.float64)

        for i in range(num_triangles):
            normals[i] = struct.unpack("<3f", f.read(12))
            for j in range(3):
                vertices[i, j] = struct.unpack("<3f", f.read(12))
            f.read(2)  # attribute byte count

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
        """Write a binary STL (little-endian float32) for this mesh."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        n = self.n_triangles
        header = b"AEGIS BodyMesh" + b"\0" * (80 - 14)
        if len(header) != 80:
            raise ValueError("STL header must be 80 bytes")

        with path.open("wb") as f:
            f.write(header)
            f.write(struct.pack("<I", n))
            for i in range(n):
                ni = self.normals[i].astype(np.float32)
                f.write(struct.pack("<3f", float(ni[0]), float(ni[1]), float(ni[2])))
                for j in range(3):
                    v = self.vertices[i, j].astype(np.float32)
                    f.write(struct.pack("<3f", float(v[0]), float(v[1]), float(v[2])))
                f.write(struct.pack("<H", 0))

    def __repr__(self) -> str:
        return f"BodyMesh(name={self.name!r}, n_triangles={self.n_triangles}, total_area={self.total_area:.6g})"
