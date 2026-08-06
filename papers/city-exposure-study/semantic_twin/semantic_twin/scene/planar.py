"""Polygon arithmetic in the image plane, plus the one solid angle it needs.

Everything a projected triangle goes through between leaving the mesh and
becoming a cut piece happens here: clip against the near plane, clip to the
crop rectangle, rasterise, measure, fan into triangles. None of it knows about
semantics, cameras or meshes, which is why it is the layer the cutter and the
round-trip audit can both stand on.

Every body is carried over unchanged from ``fishnet.py``. The clipping is
Sutherland-Hodgman one half plane at a time, which is exact for the convex
inputs it gets and does not need a general polygon library.
"""

from __future__ import annotations

import math

import numpy as np


def signed_area(polygon: np.ndarray) -> float:
    """Shoelace area of a closed polygon, negative for clockwise winding.

    The sign is load bearing twice. :func:`rasterize_convex` uses it to decide
    which side of each edge is the inside, and the cutter uses the magnitude as
    a projected pixel area.
    """
    x = polygon[:, 0]
    y = polygon[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - y * np.roll(x, -1)))


def triangle_solid_angle(triangles: np.ndarray) -> np.ndarray:
    """Exact solid angle of camera-centred triangles, by Van Oosterom-Strackee."""
    triangles = np.asarray(triangles, dtype=np.float64)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3):
        raise ValueError("triangles must have shape (n, 3, 3)")
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    norm_a = np.linalg.norm(a, axis=1)
    norm_b = np.linalg.norm(b, axis=1)
    norm_c = np.linalg.norm(c, axis=1)
    numerator = np.abs(np.einsum("ij,ij->i", a, np.cross(b, c)))
    denominator = (
        norm_a * norm_b * norm_c
        + np.einsum("ij,ij->i", a, b) * norm_c
        + np.einsum("ij,ij->i", a, c) * norm_b
        + np.einsum("ij,ij->i", b, c) * norm_a
    )
    return 2.0 * np.arctan2(numerator, denominator)


def clip_near_plane(points: np.ndarray, near: float) -> np.ndarray:
    """Keep the part of a camera-space polygon at or beyond the near plane.

    Run before projection, never after. A vertex behind the camera projects to a
    finite pixel with the wrong sign, and the resulting outline looks ordinary,
    so the guard has to sit on the camera-space side of the divide.
    """
    inside = points[:, 2] >= near
    if inside.all():
        return points
    if not inside.any():
        return np.zeros((0, 3), dtype=np.float64)
    output = []
    count = len(points)
    for index in range(count):
        following = (index + 1) % count
        if inside[index]:
            output.append(points[index])
        if inside[index] != inside[following]:
            fraction = (near - points[index, 2]) / (points[following, 2] - points[index, 2])
            output.append(points[index] + fraction * (points[following] - points[index]))
    return np.asarray(output, dtype=np.float64)


def clip_to_rect(polygon: np.ndarray, width: int, height: int) -> np.ndarray:
    """Intersect an image-space polygon with the crop rectangle."""
    limits = ((0, 0.0, True), (0, float(width), False), (1, 0.0, True), (1, float(height), False))
    for axis, limit, keep_greater in limits:
        if len(polygon) < 3:
            return np.zeros((0, 2), dtype=np.float64)
        polygon = clip_half_plane(polygon, axis, limit, keep_greater)
    return polygon


def clip_half_plane(polygon: np.ndarray, axis: int, limit: float, keep_greater: bool) -> np.ndarray:
    """Keep the side of one axis-aligned line, inserting the crossing vertices."""
    values = polygon[:, axis]
    inside = values >= limit if keep_greater else values <= limit
    if inside.all():
        return polygon
    if not inside.any():
        return np.zeros((0, 2), dtype=np.float64)
    output = []
    count = len(polygon)
    for index in range(count):
        following = (index + 1) % count
        if inside[index]:
            output.append(polygon[index])
        if inside[index] != inside[following]:
            span = values[following] - values[index]
            fraction = 0.0 if abs(span) < 1e-15 else (limit - values[index]) / span
            output.append(polygon[index] + fraction * (polygon[following] - polygon[index]))
    return np.asarray(output, dtype=np.float64)


def rasterize_convex(polygon: np.ndarray, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """Rows and columns of the pixel centres inside a convex image polygon.

    A pixel belongs to the polygon when its centre is on the inner side of every
    edge, so neighbouring polygons of a partition never claim the same pixel and
    never leave one unclaimed.
    """
    x0 = max(int(math.floor(polygon[:, 0].min())), 0)
    x1 = min(int(math.ceil(polygon[:, 0].max())), width)
    y0 = max(int(math.floor(polygon[:, 1].min())), 0)
    y1 = min(int(math.ceil(polygon[:, 1].max())), height)
    if x1 <= x0 or y1 <= y0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    grid_x, grid_y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
    sign = 1.0 if signed_area(polygon) >= 0.0 else -1.0
    inside = np.ones(grid_x.shape, dtype=bool)
    count = len(polygon)
    for index in range(count):
        start = polygon[index]
        end = polygon[(index + 1) % count]
        cross = (end[0] - start[0]) * (grid_y - start[1]) - (end[1] - start[1]) * (grid_x - start[0])
        inside &= sign * cross >= 0.0
    rows, columns = np.nonzero(inside)
    return rows + y0, columns + x0


def fan_triangles(polygon: np.ndarray) -> np.ndarray:
    """Triangulate a convex polygon as a fan from its first vertex."""
    return np.stack([np.stack([polygon[0], polygon[i], polygon[i + 1]]) for i in range(1, len(polygon) - 1)])
