"""Read triangle geometry out of a Blender object into numpy world coordinates.

Imported only by the scripts that run inside Blender. ``bpy`` is never imported
here, so the module stays importable from an ordinary interpreter and the object
argument is duck-typed.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def mesh_arrays(obj: Any) -> tuple[np.ndarray, np.ndarray]:
    """World-space vertices and loop-triangle indices for one Blender object.

    ``matrix_world`` is single precision on the Blender side, so it is read into
    a float64 numpy array and applied here rather than left to ``mathutils``.
    """
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", vertices)
    vertices = vertices.reshape(-1, 3)
    matrix = np.array(obj.matrix_world, dtype=np.float64)
    vertices = vertices @ matrix[:3, :3].T + matrix[:3, 3]
    faces = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
    mesh.loop_triangles.foreach_get("vertices", faces)
    return vertices, faces.reshape(-1, 3)
