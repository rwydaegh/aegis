"""Building geometry: wall extrusion and roof algorithms.

All functions output numpy arrays. No Blender/bmesh dependency.
Reference: blosm/building/roof/, blosm/action/volume/
"""

from __future__ import annotations

import numpy as np


def triangulate_polygon(polygon: np.ndarray) -> np.ndarray:
    """Triangulate a 2D polygon using ear clipping.

    Args:
        polygon: (N, 2) array of 2D vertices in CCW order.

    Returns:
        (N-2, 3) uint32 array of triangle indices.
    """
    n = len(polygon)
    if n < 3:
        return np.empty((0, 3), dtype=np.uint32)
    if n == 3:
        return np.array([[0, 1, 2]], dtype=np.uint32)

    # ensure CCW winding
    signed_area = _signed_area_2d(polygon)
    indices = list(range(n))
    if signed_area < 0:
        indices = indices[::-1]

    triangles = []
    remaining = list(indices)

    max_iter = n * n
    iteration = 0
    while len(remaining) > 3 and iteration < max_iter:
        iteration += 1
        ear_found = False
        for i in range(len(remaining)):
            prev_i = (i - 1) % len(remaining)
            next_i = (i + 1) % len(remaining)
            a = polygon[remaining[prev_i]]
            b = polygon[remaining[i]]
            c = polygon[remaining[next_i]]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 0:
                continue
            is_ear = True
            for j in range(len(remaining)):
                if j in (prev_i, i, next_i):
                    continue
                if _point_in_triangle(polygon[remaining[j]], a, b, c):
                    is_ear = False
                    break
            if is_ear:
                triangles.append([remaining[prev_i], remaining[i], remaining[next_i]])
                remaining.pop(i)
                ear_found = True
                break
        if not ear_found:
            break

    if len(remaining) == 3:
        triangles.append(remaining)

    return np.array(triangles, dtype=np.uint32) if triangles else np.empty((0, 3), dtype=np.uint32)


def extrude_walls(
    footprint: np.ndarray,
    base_height: float,
    top_height: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Extrude vertical walls from a 2D footprint polygon.

    Args:
        footprint: (N, 2) array of 2D footprint vertices.
        base_height: Z coordinate of the bottom edge.
        top_height: Z coordinate of the top edge.

    Returns:
        (vertices, triangles) where vertices is (N*4, 3) float64
        and triangles is (N*2, 3) uint32.
    """
    n = len(footprint)
    vertices = []
    triangles = []
    for i in range(n):
        j = (i + 1) % n
        p0 = footprint[i]
        p1 = footprint[j]
        base_idx = len(vertices)
        vertices.append([p0[0], p0[1], base_height])
        vertices.append([p1[0], p1[1], base_height])
        vertices.append([p1[0], p1[1], top_height])
        vertices.append([p0[0], p0[1], top_height])
        triangles.append([base_idx, base_idx + 1, base_idx + 2])
        triangles.append([base_idx, base_idx + 2, base_idx + 3])

    return (
        np.array(vertices, dtype=np.float64),
        np.array(triangles, dtype=np.uint32),
    )


def _signed_area_2d(polygon: np.ndarray) -> float:
    """Signed area of a 2D polygon (positive = CCW)."""
    x = polygon[:, 0]
    y = polygon[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _point_in_triangle(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
    """Test if 2D point p is inside triangle abc."""
    d1 = (p[0] - c[0]) * (a[1] - c[1]) - (a[0] - c[0]) * (p[1] - c[1])
    d2 = (p[0] - a[0]) * (b[1] - a[1]) - (b[0] - a[0]) * (p[1] - a[1])
    d3 = (p[0] - b[0]) * (c[1] - b[1]) - (c[0] - b[0]) * (p[1] - b[1])
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)
