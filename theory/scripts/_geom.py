"""
Shared geometry helpers used across scripts.

Right now this is focused on:
  - binary STL loading (no external deps)
  - triangle area computation

Kept as a standalone module so scripts can run via:
    python scripts/<script>.py
"""

from __future__ import annotations

import struct
from typing import Tuple

import numpy as np


def load_stl_binary(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load a binary STL file.

    Parameters
    ----------
    path
        Path to STL file.

    Returns
    -------
    vertices : (N, 3, 3)
        Triangle vertices.
    normals : (N, 3)
        Triangle normals (unit-length; STL normals are sometimes unnormalized).
    centroids : (N, 3)
        Triangle centroids.
    """
    with open(path, "rb") as f:
        f.read(80)  # header
        num_triangles = struct.unpack("<I", f.read(4))[0]

        vertices = np.zeros((num_triangles, 3, 3), dtype=float)
        normals = np.zeros((num_triangles, 3), dtype=float)

        for i in range(num_triangles):
            normals[i] = struct.unpack("<3f", f.read(12))
            for j in range(3):
                vertices[i, j] = struct.unpack("<3f", f.read(12))
            f.read(2)  # attribute byte count

    centroids = np.mean(vertices, axis=1)

    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms > 0, norms, 1)

    return vertices, normals, centroids


def triangle_areas(vertices: np.ndarray) -> np.ndarray:
    """Compute area of each triangle for a (N, 3, 3) vertex array."""
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    return 0.5 * np.linalg.norm(cross, axis=1)

