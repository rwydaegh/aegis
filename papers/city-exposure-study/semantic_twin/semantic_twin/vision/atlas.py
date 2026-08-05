"""Triangle-local semantic atlases for non-destructive scene decals.

The atlas is an evidence layer, not replacement geometry.  Each support-mesh
triangle owns a small canonical right-triangle texture.  Image rays contribute
categorical weight to its texels, which keeps the original mesh topology intact
until a downstream renderer genuinely needs a material-boundary split.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TriangleSemanticAtlas:
    """Categorical evidence accumulated in canonical UV space per triangle.

    The atlas is sparse over the support mesh.  Only triangles that appear in
    the projected observations get a row, so a city mesh with millions of
    triangles costs nothing for the triangles no panorama has seen.  Row ``i``
    belongs to support-mesh triangle ``triangle_ids[i]``, and ``triangle_ids``
    is ascending.  Use :meth:`rows_for` to go from triangle identifiers to rows.

    ``weights`` has shape ``(observed_triangles, height, width, classes)``.
    ``labels`` is ``invalid_label`` where there is no observation or where a
    square texel falls outside the canonical triangle.  ``confidence`` is the
    winning class weight divided by total categorical weight at that texel.
    ``triangle_count`` is the size of the support mesh when the caller declared
    it, and ``None`` when it was inferred from the observations.
    """

    triangle_ids: np.ndarray
    weights: np.ndarray
    labels: np.ndarray
    confidence: np.ndarray
    support: np.ndarray
    valid_texels: np.ndarray
    invalid_label: int = -1
    triangle_count: int | None = None

    @property
    def observed_triangle_count(self) -> int:
        """Number of support-mesh triangles that own a row in this atlas."""
        return len(self.triangle_ids)

    def rows_for(self, triangle_ids: np.ndarray) -> np.ndarray:
        """Return the atlas row of each triangle, or ``-1`` when unobserved."""
        query = np.asarray(triangle_ids, dtype=np.int64)
        if not len(self.triangle_ids):
            return np.full(query.shape, -1, dtype=np.intp)
        position = np.clip(np.searchsorted(self.triangle_ids, query), 0, len(self.triangle_ids) - 1)
        return np.where(self.triangle_ids[position] == query, position, -1).astype(np.intp)


def barycentric_uv(vertices: np.ndarray) -> np.ndarray:
    """Return the canonical UV coordinates for a non-degenerate 3D triangle.

    A point with barycentric weights ``(w0, w1, w2)`` maps to ``(w1, w2)``.
    The returned coordinates therefore make each mesh triangle its own stable
    local atlas, independent of global mesh UVs.
    """
    vertices = np.asarray(vertices, dtype=np.float64)
    if vertices.shape != (3, 3) or not np.all(np.isfinite(vertices)):
        raise ValueError("vertices must be a finite array with shape (3, 3)")
    if np.linalg.norm(np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])) <= 1e-12:
        raise ValueError("vertices must form a non-degenerate triangle")
    return np.array(((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)), dtype=np.float64)


def rasterize_triangle_evidence(
    triangle_indices: np.ndarray,
    barycentric: np.ndarray,
    labels: np.ndarray,
    confidence: np.ndarray,
    *,
    resolution: int | tuple[int, int],
    triangle_count: int | None = None,
    class_count: int | None = None,
    invalid_label: int = -1,
) -> TriangleSemanticAtlas:
    """Accumulate labelled image evidence into a categorical triangle atlas.

    Inputs are one-dimensional observations, usually flattened valid image
    pixels after a camera ray has been associated with a support-mesh triangle.
    Repeated observations add their confidence rather than overwriting one
    another.  The winning class is returned along with its normalised support.
    Negative labels represent intentionally unlabelled observations and are
    ignored.  Invalid triangle indices, barycentrics, and confidences raise so
    that a bad projection cannot quietly corrupt a decal layer.

    The returned atlas allocates one row per *observed* triangle, not one row
    per support-mesh triangle.  ``triangle_count`` therefore only bounds the
    accepted identifiers, it never sizes the buffer.
    """
    height, width = _resolution(resolution)
    triangle_indices = np.asarray(triangle_indices, dtype=np.int64)
    barycentric = np.asarray(barycentric, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    confidence = np.asarray(confidence, dtype=np.float64)

    observations = triangle_indices.size
    if triangle_indices.ndim != 1 or labels.shape != (observations,) or confidence.shape != (observations,):
        raise ValueError("triangle_indices, labels, and confidence must be one-dimensional and equally sized")
    if barycentric.shape != (observations, 3):
        raise ValueError("barycentric must have shape (observations, 3)")
    if not np.all(np.isfinite(barycentric)) or not np.all(np.isfinite(confidence)):
        raise ValueError("barycentric coordinates and confidence must be finite")
    if np.any(confidence < 0.0):
        raise ValueError("confidence cannot be negative")
    if np.any(barycentric < -1e-6) or not np.allclose(barycentric.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("barycentric coordinates must be nonnegative and sum to one")

    labelled = labels >= 0
    if class_count is None:
        class_count = int(labels[labelled].max()) + 1 if np.any(labelled) else 0
    if class_count < 0 or np.any(labels[labelled] >= class_count):
        raise ValueError("class_count must include every nonnegative label")
    declared_triangle_count = triangle_count
    if triangle_count is None:
        triangle_count = int(triangle_indices.max()) + 1 if observations else 0
    if triangle_count < 0 or np.any((triangle_indices < 0) | (triangle_indices >= triangle_count)):
        raise ValueError("triangle indices must lie in [0, triangle_count)")

    valid_texels = _canonical_triangle_texels(height, width)
    observed, atlas_row = np.unique(triangle_indices, return_inverse=True)
    observed = observed.astype(np.int64, copy=False)
    atlas_row = np.reshape(atlas_row, (observations,)).astype(np.intp, copy=False)
    weights = np.zeros((len(observed), height, width, class_count), dtype=np.float32)
    if class_count:
        active = labelled & (confidence > 0.0)
        if np.any(active):
            rows, columns = triangle_texel_indices(barycentric[active], (height, width))
            np.add.at(
                weights,
                (atlas_row[active], rows, columns, labels[active]),
                confidence[active].astype(np.float32),
            )

    support = weights.sum(axis=-1)
    labels_out = np.full((len(observed), height, width), invalid_label, dtype=np.int64)
    confidence_out = np.zeros((len(observed), height, width), dtype=np.float32)
    if class_count:
        winner = weights.argmax(axis=-1)
        has_support = support > 0.0
        labels_out[has_support] = winner[has_support]
        confidence_out[has_support] = np.take_along_axis(weights, winner[..., None], axis=-1)[..., 0][has_support]
        confidence_out[has_support] /= support[has_support]

    outside = ~valid_texels
    weights[:, outside] = 0.0
    labels_out[:, outside] = invalid_label
    confidence_out[:, outside] = 0.0
    support[:, outside] = 0.0
    return TriangleSemanticAtlas(
        observed,
        weights,
        labels_out,
        confidence_out,
        support,
        valid_texels,
        invalid_label,
        declared_triangle_count,
    )


def triangle_texel_indices(
    barycentric: np.ndarray,
    resolution: int | tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Map full barycentric coordinates to canonical triangle texels.

    This is the common image-to-atlas discretisation used by both the small
    categorical rasteriser above and the all-camera joint material atlas.  A
    public helper keeps the two artifacts from acquiring slightly different
    seam coordinates.
    """
    height, width = _resolution(resolution)
    barycentric = np.asarray(barycentric, dtype=np.float64)
    if barycentric.ndim != 2 or barycentric.shape[1] != 3:
        raise ValueError("barycentric must have shape (observations, 3)")
    if not np.all(np.isfinite(barycentric)):
        raise ValueError("barycentric coordinates must be finite")
    if np.any(barycentric < -1e-6) or not np.allclose(barycentric.sum(axis=1), 1.0, atol=1e-6):
        raise ValueError("barycentric coordinates must be nonnegative and sum to one")
    return _texel_indices(barycentric[:, 2], barycentric[:, 1], height, width)


def conservative_simplify_contour(points: np.ndarray, tolerance: float) -> np.ndarray:
    """Simplify a closed contour without removing concave boundary vertices.

    Candidate vertices are removed only when their distance from the joining
    chord is at most ``tolerance`` and the local turn is convex or collinear.
    For a simple polygon, that chord stays on the contour's interior side, so
    simplification can only shrink the decal rather than spill a class into an
    adjacent one.  Concave corners are retained as conservative guards.
    """
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3 or not np.all(np.isfinite(points)):
        raise ValueError("points must be a finite array with shape (n, 2), n >= 3")
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and nonnegative")
    if np.allclose(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3:
        raise ValueError("a contour needs at least three distinct listed vertices")

    orientation = _signed_area(points)
    if abs(orientation) <= 1e-12:
        raise ValueError("contour must enclose nonzero signed area")
    kept = list(range(len(points)))
    changed = True
    while changed and len(kept) > 3:
        changed = False
        for position, index in enumerate(tuple(kept)):
            previous = kept[(position - 1) % len(kept)]
            following = kept[(position + 1) % len(kept)]
            before, current, after = points[previous], points[index], points[following]
            incoming = current - before
            outgoing = after - current
            turn = float(incoming[0] * outgoing[1] - incoming[1] * outgoing[0])
            convex_or_straight = turn * orientation >= -1e-12
            if convex_or_straight and _point_segment_distance(current, before, after) <= tolerance:
                kept.pop(position)
                changed = True
                break
    return points[np.asarray(kept, dtype=np.intp)]


def _resolution(resolution: int | tuple[int, int]) -> tuple[int, int]:
    if isinstance(resolution, int):
        height = width = resolution
    else:
        if len(resolution) != 2:
            raise ValueError("resolution must be an integer or (height, width)")
        height, width = resolution
    if not isinstance(height, (int, np.integer)) or not isinstance(width, (int, np.integer)) or height < 2 or width < 2:
        raise ValueError("atlas resolution must have integer height and width >= 2")
    return int(height), int(width)


def _texel_indices(v: np.ndarray, u: np.ndarray, height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    """Map barycentric ``(u, v)`` onto the nearest texel inside the triangle.

    Rounding each axis independently can push a point that genuinely lies in
    the triangle across the hypotenuse: at 8 x 8 the barycentric midpoint of
    the hypotenuse rounds to texel (4, 4), where ``u + v = 8/7``.  That texel
    is masked out of the canonical triangle, so the observation would be
    accumulated and then discarded.  Whenever the rounded texel lands outside,
    the axis that was rounded up hardest steps back to its neighbouring texel
    until the pair is inside again.  A texel outside the triangle always has
    both indices above zero, so the walk terminates at the origin at worst.
    """
    v = np.clip(v, 0.0, 1.0)
    u = np.clip(u, 0.0, 1.0)
    rows = np.floor(v * (height - 1) + 0.5)
    columns = np.floor(u * (width - 1) + 0.5)
    row_excess = rows - v * (height - 1)
    column_excess = columns - u * (width - 1)
    outside = rows / (height - 1) + columns / (width - 1) > 1.0 + 1e-12
    while np.any(outside):
        step_row = outside & (row_excess >= column_excess)
        step_column = outside & ~step_row
        rows[step_row] -= 1.0
        columns[step_column] -= 1.0
        row_excess[step_row] -= 1.0
        column_excess[step_column] -= 1.0
        outside = rows / (height - 1) + columns / (width - 1) > 1.0 + 1e-12
    return rows.astype(np.intp), columns.astype(np.intp)


def _canonical_triangle_texels(height: int, width: int) -> np.ndarray:
    u = np.linspace(0.0, 1.0, width, dtype=np.float64)
    v = np.linspace(0.0, 1.0, height, dtype=np.float64)
    return v[:, None] + u[None, :] <= 1.0 + 1e-12


def _signed_area(points: np.ndarray) -> float:
    return 0.5 * float(np.sum(points[:, 0] * np.roll(points[:, 1], -1) - points[:, 1] * np.roll(points[:, 0], -1)))


def _point_segment_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    direction = end - start
    squared_length = float(direction @ direction)
    if squared_length <= 1e-24:
        return float(np.linalg.norm(point - start))
    fraction = float(np.clip(((point - start) @ direction) / squared_length, 0.0, 1.0))
    return float(np.linalg.norm(point - (start + fraction * direction)))
