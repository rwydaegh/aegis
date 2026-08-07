"""Deterministic facade-tip curves and their one-dimensional source measure.

The production facade-tip law is a line measure, not a cloud of surface points.
This module keeps the geometric support and its quadrature weights explicit.  A
curve is built from ordered silhouette polylines from a fixed builder route,
then repeated observations are unioned by geometric intervals.  Consequently a
second view of the same edge does not create a second population, and splitting
one segment into finer pieces does not change its represented length.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np

from .roofline import ELEVATION_MAX_DEG, ELEVATION_MIN_DEG

CURVE_HASH_VERSION = "facade_tip_curve_canonical_ascii_v1"
MERGE_RULE = "union_collinear_intervals_orientation_invariant"
EDGE_MERGE_RULE = "undirected_mesh_vertex_edge_id_union"
MESH_NUMERICAL_FLOOR_M = 1.0e-6


def _canonical_digest(*arrays: np.ndarray) -> str:
    """Hash arrays through shape-aware, endian-independent decimal text."""
    chunks = [CURVE_HASH_VERSION]
    for array in arrays:
        values = np.asarray(array, dtype=np.float64)
        if values.ndim == 0:
            values = values.reshape(1)
        chunks.append(str(tuple(values.shape)))
        chunks.extend(format(float(value), ".15g") for value in values.reshape(-1))
    return hashlib.sha256("\n".join(chunks).encode("ascii")).hexdigest()


def _as_polyline(value: Any) -> np.ndarray:
    points = np.asarray(value, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"polyline must have shape (points, 3), got {points.shape}")
    if not np.all(np.isfinite(points)):
        raise ValueError("polyline points must be finite")
    return points


def polyline_segments(
    points: np.ndarray,
    *,
    closed: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(starts, ends, lengths)`` for a finite ordered polyline.

    Zero-length edges are discarded.  Silhouette rings are closed in azimuth,
    while an extracted line can be left open by passing ``closed=False``.
    """
    polyline = _as_polyline(points)
    if polyline.shape[0] < 2:
        empty = np.empty((0, 3), dtype=np.float64)
        return empty, empty.copy(), np.empty(0, dtype=np.float64)
    starts = polyline[:-1]
    ends = polyline[1:]
    if closed:
        starts = np.concatenate((starts, polyline[-1:]), axis=0)
        ends = np.concatenate((ends, polyline[:1]), axis=0)
    lengths = np.linalg.norm(ends - starts, axis=1)
    keep = lengths > 0.0
    return starts[keep], ends[keep], lengths[keep]


def _line_key(start: np.ndarray, end: np.ndarray, tolerance: float) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Canonical line direction and offset key for collinear interval union."""
    delta = end - start
    length = float(np.linalg.norm(delta))
    direction = delta / length
    # Direction sign does not identify a line orientation.  Force the largest
    # component positive, with deterministic lexicographic tie-breaking.
    pivot = int(np.argmax(np.abs(direction)))
    if direction[pivot] < 0.0:
        direction = -direction
    normal = start - float(np.dot(start, direction)) * direction
    scale = max(float(tolerance), 1.0e-9)
    return tuple(np.rint(direction / scale).astype(np.int64)), tuple(np.rint(normal / scale).astype(np.int64))


def _prepare_segments(
    starts: np.ndarray,
    ends: np.ndarray,
    lengths: np.ndarray | None,
    tolerance_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    start = np.asarray(starts, dtype=np.float64)
    end = np.asarray(ends, dtype=np.float64)
    if start.shape != end.shape or start.ndim != 2 or start.shape[1] != 3:
        raise ValueError("starts and ends must have matching shape (segments, 3)")
    if lengths is None:
        seg_length = np.linalg.norm(end - start, axis=1)
    else:
        seg_length = np.asarray(lengths, dtype=np.float64)
        if seg_length.shape != (start.shape[0],):
            raise ValueError("lengths must match starts")
    if not np.isfinite(tolerance_m) or tolerance_m <= 0.0:
        raise ValueError("tolerance_m must be positive and finite")
    keep = np.isfinite(seg_length) & (seg_length > tolerance_m * 1.0e-6)
    return start[keep], end[keep], seg_length[keep]


def _group_segments(
    start: np.ndarray,
    end: np.ndarray,
    seg_length: np.ndarray,
    tolerance_m: float,
) -> dict[tuple[tuple[int, ...], tuple[int, ...]], list[tuple[float, float, np.ndarray, np.ndarray]]]:
    groups: dict[tuple[tuple[int, ...], tuple[int, ...]], list[tuple[float, float, np.ndarray, np.ndarray]]] = {}
    for a, b, length in zip(start, end, seg_length, strict=True):
        actual = float(np.linalg.norm(b - a))
        if actual <= 0.0:
            continue
        direction = (b - a) / actual
        pivot = int(np.argmax(np.abs(direction)))
        if direction[pivot] < 0.0:
            direction = -direction
            a, b = b, a
        origin = a - float(np.dot(a, direction)) * direction
        key = _line_key(a, b, tolerance_m)
        groups.setdefault(key, []).append((float(np.dot(a, direction)), float(np.dot(b, direction)), origin, direction))
    return groups


def _merge_group(
    intervals: list[tuple[float, float, np.ndarray, np.ndarray]],
    tolerance_m: float,
) -> tuple[list[np.ndarray], list[float]]:
    intervals.sort(key=lambda item: item[0])
    a0, b0, origin, direction = intervals[0]
    low, high = min(a0, b0), max(a0, b0)
    points: list[np.ndarray] = []
    represented: list[float] = []
    for a, b, _, _ in intervals[1:]:
        a_low, b_high = min(a, b), max(a, b)
        if a_low <= high + tolerance_m:
            high = max(high, b_high)
            continue
        points.append(origin + 0.5 * (low + high) * direction)
        represented.append(high - low)
        low, high = a_low, b_high
    points.append(origin + 0.5 * (low + high) * direction)
    represented.append(high - low)
    return points, represented


def merge_segments(
    starts: np.ndarray,
    ends: np.ndarray,
    lengths: np.ndarray | None = None,
    *,
    tolerance_m: float = 1.0e-4,
) -> tuple[np.ndarray, np.ndarray]:
    """Union repeated collinear segments and return midpoint quadrature points.

    Segment intervals are grouped by a quantized unoriented supporting line and
    unioned in one-dimensional coordinates.  Overlap is counted once.  Small
    gaps no larger than ``tolerance_m`` are joined, which makes repeated views
    robust to ray-fan rounding while preserving disjoint facade edges.
    """
    start, end, seg_length = _prepare_segments(starts, ends, lengths, tolerance_m)
    if start.shape[0] == 0:
        return np.empty((0, 3)), np.empty(0, dtype=np.float64)
    groups = _group_segments(start, end, seg_length, tolerance_m)
    points: list[np.ndarray] = []
    represented: list[float] = []
    for key in sorted(groups):
        group_points, group_lengths = _merge_group(groups[key], tolerance_m)
        points.extend(group_points)
        represented.extend(group_lengths)
    if not points:
        return np.empty((0, 3)), np.empty(0, dtype=np.float64)
    return np.asarray(points, dtype=np.float64), np.asarray(represented, dtype=np.float64)


@dataclass(frozen=True)
class FacadeTipCurve:
    """A fixed route-observed facade-tip support and arc-length quadrature."""

    points: np.ndarray
    segment_lengths_m: np.ndarray
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        points = _as_polyline(self.points)
        lengths = np.asarray(self.segment_lengths_m, dtype=np.float64)
        if lengths.shape != (points.shape[0],):
            raise ValueError("segment_lengths_m must match points")
        if np.any(~np.isfinite(lengths)) or np.any(lengths <= 0.0):
            raise ValueError("segment_lengths_m must be finite and positive")
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "segment_lengths_m", lengths)
        object.__setattr__(self, "provenance", dict(self.provenance))

    @property
    def arc_lengths(self) -> np.ndarray:
        """Alias naming the represented arc length of each quadrature point."""
        return self.segment_lengths_m

    @property
    def support_length_m(self) -> float:
        return float(np.sum(self.segment_lengths_m, dtype=np.float64))

    def normalized_weights(self) -> np.ndarray:
        total = self.support_length_m
        if total <= 0.0:
            raise ValueError("facade-tip curve has no positive support length")
        return self.segment_lengths_m / total

    @property
    def hash_sha256(self) -> str:
        return _canonical_digest(self.points, self.segment_lengths_m)

    @property
    def source_hash(self) -> str:
        return self.hash_sha256

    def describe(self) -> dict[str, Any]:
        return {
            "support_length_m": self.support_length_m,
            "quadrature_points": int(self.points.shape[0]),
            "curve_hash_sha256": self.hash_sha256,
            "merge_rule": MERGE_RULE,
            **self.provenance,
        }


def curve_from_polylines(
    polylines: Iterable[np.ndarray],
    *,
    tolerance_m: float = 1.0e-4,
    provenance: dict[str, Any] | None = None,
) -> FacadeTipCurve:
    """Build a curve by unioning segment intervals from ordered polylines."""
    starts_list: list[np.ndarray] = []
    ends_list: list[np.ndarray] = []
    lengths_list: list[np.ndarray] = []
    observations = 0
    for polyline in polylines:
        observations += 1
        starts, ends, lengths = polyline_segments(polyline)
        starts_list.append(starts)
        ends_list.append(ends)
        lengths_list.append(lengths)
    if starts_list:
        starts = np.concatenate(starts_list, axis=0)
        ends = np.concatenate(ends_list, axis=0)
        lengths = np.concatenate(lengths_list, axis=0)
    else:
        starts = np.empty((0, 3))
        ends = np.empty((0, 3))
        lengths = np.empty(0)
    points, represented = merge_segments(starts, ends, lengths, tolerance_m=tolerance_m)
    if points.shape[0] == 0:
        raise ValueError("route observations contain no positive facade-tip support")
    details = {
        "observations": observations,
        "curve_resolution_m": float(tolerance_m),
        "merge_rule": MERGE_RULE,
        **(provenance or {}),
    }
    return FacadeTipCurve(points, represented, details)


def _mesh_edge_faces(faces: np.ndarray) -> dict[tuple[int, int], list[int]]:
    """Index each undirected mesh edge by its incident triangle IDs."""
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, face in enumerate(np.asarray(faces, dtype=np.int64)):
        a, b, c = (int(value) for value in face)
        for edge in ((a, b), (b, c), (c, a)):
            key = tuple(sorted(edge))
            edge_faces.setdefault(key, []).append(face_index)
    return edge_faces


def _mesh_edge_hash(edges: list[tuple[int, int]]) -> str:
    if not edges:
        return _canonical_digest(np.empty((0, 2), dtype=np.float64))
    return _canonical_digest(np.asarray(edges, dtype=np.float64))


def _mesh_face_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Return unit geometric normals, refusing degenerate triangles."""
    a = vertices[faces[:, 0]]
    raw = np.cross(vertices[faces[:, 1]] - a, vertices[faces[:, 2]] - a)
    norm = np.linalg.norm(raw, axis=1)
    if np.any(norm <= MESH_NUMERICAL_FLOOR_M):
        raise ValueError("mesh contains degenerate faces in facade-tip selector")
    return raw / norm[:, None]


def _edge_parameter(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> tuple[float, float, np.ndarray]:
    delta = end - start
    length_sq = float(np.dot(delta, delta))
    if length_sq <= MESH_NUMERICAL_FLOOR_M**2:
        return 0.0, float("inf"), start.copy()
    parameter = float(np.clip(np.dot(point - start, delta) / length_sq, 0.0, 1.0))
    projected = start + parameter * delta
    return parameter, float(np.linalg.norm(projected - point)), projected


def _edge_silhouette_kind(
    edge: tuple[int, int],
    *,
    origin: np.ndarray,
    point: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
) -> str | None:
    """Classify a geometric edge as a front-facing boundary or a crease.

    Coplanar shared edges are always seams, even when inconsistent triangle
    winding would make their signed facing tests disagree.  A non-manifold edge
    is refused rather than guessed.  This keeps the contour support tied to a
    real mesh silhouette instead of an arbitrary triangle edge.
    """
    incident = edge_faces[edge]
    if len(incident) == 1:
        face_index = incident[0]
        facing = float(np.dot(normals[face_index], origin - point))
        # Boundary winding is not guaranteed by imported/tiled city meshes.  A
        # boundary is silhouette-visible from either oriented side, provided it
        # is not tangent to the viewpoint.  Interior edges still require a true
        # opposite-facing crease below.
        if abs(facing) > MESH_NUMERICAL_FLOOR_M:
            return "boundary"
        return None
    if len(incident) != 2:
        return None
    first, second = incident
    if abs(float(np.dot(normals[first], normals[second]))) >= 1.0 - 1.0e-8:
        return None
    first_facing = float(np.dot(normals[first], origin - point))
    second_facing = float(np.dot(normals[second], origin - point))
    if first_facing * second_facing < -(MESH_NUMERICAL_FLOOR_M**2):
        return "crease"
    return None


def _coplanar_component(
    start_face: int,
    *,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
) -> set[int]:
    """Collect the coplanar triangle component around a tessellation seam."""
    component = {int(start_face)}
    pending = [int(start_face)]
    while pending:
        face_index = pending.pop()
        face = faces[face_index]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((int(face[i]), int(face[j]))))
            incident = edge_faces[edge]
            if len(incident) != 2:
                continue
            other = incident[0] if incident[1] == face_index else incident[1]
            if abs(float(np.dot(normals[face_index], normals[other]))) < 1.0 - 1.0e-8:
                continue
            if other not in component:
                component.add(other)
                pending.append(other)
    return component


def _ray_edge_contact(
    origin: np.ndarray,
    azimuth: float,
    start: np.ndarray,
    end: np.ndarray,
) -> tuple[float, np.ndarray] | None:
    """Intersect an edge with the horizontal ray's azimuth, if it crosses it."""
    ray_horizontal = np.array([np.cos(azimuth), np.sin(azimuth)], dtype=np.float64)
    lateral = np.array([-ray_horizontal[1], ray_horizontal[0]], dtype=np.float64)
    signed_start = float(np.dot(start[:2] - origin[:2], lateral))
    signed_end = float(np.dot(end[:2] - origin[:2], lateral))
    tolerance = MESH_NUMERICAL_FLOOR_M
    if abs(signed_start) <= tolerance and abs(signed_end) <= tolerance:
        return None
    if signed_start * signed_end > tolerance**2:
        return None
    denominator = signed_start - signed_end
    parameter = 0.5 if abs(denominator) <= tolerance else float(np.clip(signed_start / denominator, 0.0, 1.0))
    point = start + parameter * (end - start)
    if float(np.dot(point[:2] - origin[:2], ray_horizontal)) <= 0.0:
        return None
    return parameter, point


def _fan_residual_bound_m(alpha: float, slant_range: float, *, azimuths: int, elevations: int) -> float:
    """Conservative hit-to-edge bound implied by the silhouette fan cell."""
    if not np.isfinite(slant_range) or slant_range < 0.0:
        return MESH_NUMERICAL_FLOOR_M
    if elevations > 1:
        log_step = np.log(ELEVATION_MAX_DEG / ELEVATION_MIN_DEG) / float(elevations - 1)
        minimum = np.radians(ELEVATION_MIN_DEG)
        local = max(abs(float(alpha)), minimum) * np.expm1(log_step)
    else:
        local = np.pi / 2.0
    azimuth_step = 2.0 * np.pi / max(int(azimuths), 1)
    half_cell = 0.5 * float(np.hypot(local, azimuth_step))
    angular = min(0.5 * np.pi, half_cell)
    return max(MESH_NUMERICAL_FLOOR_M, float(slant_range) * np.sin(angular))


def _face_edges(face: np.ndarray) -> list[tuple[int, int]]:
    return [
        tuple(sorted((int(face[0]), int(face[1])))),
        tuple(sorted((int(face[1]), int(face[2])))),
        tuple(sorted((int(face[2]), int(face[0])))),
    ]


def _contact_edge_data(
    edge: tuple[int, int],
    *,
    point: np.ndarray,
    origin: np.ndarray,
    vertices: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
) -> tuple[float, float, np.ndarray, str] | None:
    kind = _edge_silhouette_kind(
        edge,
        origin=origin,
        point=point,
        edge_faces=edge_faces,
        normals=normals,
    )
    if kind is None:
        return None
    parameter, residual, projected = _edge_parameter(point, vertices[edge[0]], vertices[edge[1]])
    return parameter, residual, projected, kind


def _contact_candidate_edges(
    face_index: int,
    point: np.ndarray,
    *,
    vertices: np.ndarray,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
) -> tuple[set[tuple[int, int]], str]:
    local_edges = _face_edges(faces[face_index])
    edge_residuals = {edge: _edge_parameter(point, vertices[edge[0]], vertices[edge[1]])[1] for edge in local_edges}
    nearest_residual = min(edge_residuals.values(), default=np.inf)
    seam = any(
        len(edge_faces[edge]) == 2
        and abs(float(np.dot(normals[edge_faces[edge][0]], normals[edge_faces[edge][1]]))) >= 1.0 - 1.0e-8
        and edge_residuals[edge] <= nearest_residual + 10.0 * MESH_NUMERICAL_FLOOR_M
        for edge in local_edges
    )
    if not seam:
        return set(local_edges), "direct"
    component = _coplanar_component(face_index, faces=faces, edge_faces=edge_faces, normals=normals)
    candidate_edges = {edge for component_face in sorted(component) for edge in _face_edges(faces[component_face])}
    return candidate_edges, "coplanar_component_contour"


def _contact_candidates(
    candidate_edges: set[tuple[int, int]],
    mode: str,
    *,
    point: np.ndarray,
    origin: np.ndarray,
    azimuth: float,
    vertices: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
) -> list[tuple[float, float, tuple[int, int], float, str]]:
    candidates: list[tuple[float, float, tuple[int, int], float, str]] = []
    for edge in sorted(candidate_edges):
        data = _contact_edge_data(
            edge,
            point=point,
            origin=origin,
            vertices=vertices,
            edge_faces=edge_faces,
            normals=normals,
        )
        if data is None:
            continue
        parameter, residual, projected, kind = data
        ray_contact = _ray_edge_contact(origin, azimuth, vertices[edge[0]], vertices[edge[1]])
        if ray_contact is not None:
            parameter, projected = ray_contact
            residual = float(np.linalg.norm(projected - point))
            horizontal = float(np.linalg.norm(projected[:2] - origin[:2]))
            elevation = float(np.arctan2(projected[2] - origin[2], max(horizontal, MESH_NUMERICAL_FLOOR_M)))
            candidates.append((elevation, -residual, edge, parameter, kind))
        elif mode == "direct":
            candidates.append((-residual, -residual, edge, parameter, kind))
    return candidates


def _select_mesh_contact(
    face_index: int,
    point: np.ndarray,
    origin: np.ndarray,
    azimuth: float,
    *,
    vertices: np.ndarray,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
) -> tuple[tuple[int, int], float, float, str] | None:
    """Select one silhouette edge/contact, walking across coplanar seams."""
    candidate_edges, mode = _contact_candidate_edges(
        face_index,
        point,
        vertices=vertices,
        faces=faces,
        edge_faces=edge_faces,
        normals=normals,
    )
    candidates = _contact_candidates(
        candidate_edges,
        mode,
        point=point,
        origin=origin,
        azimuth=azimuth,
        vertices=vertices,
        edge_faces=edge_faces,
        normals=normals,
    )
    if not candidates:
        return None
    # Component candidates are ordered by their projected elevation (the
    # actual upper contour), with residual and vertex IDs as deterministic ties.
    if mode == "coplanar_component_contour":
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    else:
        candidates.sort(key=lambda item: (-item[0], item[2]))
    _, negative_residual, edge, parameter, kind = candidates[0]
    residual = -negative_residual
    return edge, parameter, residual, mode if mode != "direct" else kind


def _refine_silhouette_hits(
    geometry: Any,
    origin: np.ndarray,
    azimuths: np.ndarray,
    alphas: np.ndarray,
    *,
    elevations: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Batch last-hit/first-miss refinement for one viewpoint."""
    minimum = np.radians(ELEVATION_MIN_DEG)
    maximum = np.radians(ELEVATION_MAX_DEG)
    azimuth = np.asarray(azimuths, dtype=np.float64)
    alpha = np.asarray(alphas, dtype=np.float64)
    if azimuth.shape != alpha.shape or azimuth.ndim != 1:
        raise ValueError("azimuths and alphas must be matching one-dimensional arrays")
    count = int(alpha.size)
    low = np.clip(alpha, minimum, maximum)
    low_distance = np.full(count, np.inf, dtype=np.float64)
    low_face = np.full(count, -1, dtype=np.int64)
    low_point = np.full((count, 3), np.nan, dtype=np.float64)
    low_hit = np.zeros(count, dtype=bool)
    high = np.full(count, maximum, dtype=np.float64)
    high_distance = np.full(count, np.inf, dtype=np.float64)
    high_face = np.full(count, -1, dtype=np.int64)
    high_hit = np.zeros(count, dtype=bool)
    high_point = np.full((count, 3), np.nan, dtype=np.float64)

    def query(elevation: np.ndarray, active: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        indices = np.flatnonzero(active)
        if indices.size == 0:
            return np.empty(0, bool), np.empty(0), np.empty(0, np.int64), np.empty((0, 3))
        elev = np.asarray(elevation, dtype=np.float64)[indices]
        directions = np.stack(
            [np.cos(elev) * np.cos(azimuth[indices]), np.cos(elev) * np.sin(azimuth[indices]), np.sin(elev)],
            axis=-1,
        )
        origins = np.broadcast_to(np.asarray(origin, dtype=np.float64), directions.shape)
        hit, distance, _, face = geometry.intersect(origins, directions)
        hit_value = np.asarray(hit, dtype=bool)
        distance_value = np.asarray(distance, dtype=np.float64)
        face_value = np.asarray(face, dtype=np.int64)
        finite_hit = hit_value & np.isfinite(distance_value)
        points = np.asarray(origin, dtype=np.float64)[None, :] + distance_value[:, None] * directions
        return finite_hit, distance_value, face_value, points

    active_all = np.ones(count, dtype=bool)
    queried_hit, queried_distance, queried_face, queried_point = query(low, active_all)
    low_indices = np.flatnonzero(active_all)
    low_hit[low_indices] = queried_hit
    low_distance[low_indices] = queried_distance
    low_face[low_indices] = queried_face
    low_point[low_indices] = queried_point
    if elevations <= 1 or not np.any(low_hit):
        return low, low_distance, low_face, low_point, low_hit

    grid = np.radians(np.logspace(np.log10(ELEVATION_MIN_DEG), np.log10(ELEVATION_MAX_DEG), elevations))
    high_indices = np.searchsorted(grid, low + MESH_NUMERICAL_FLOOR_M, side="right")
    has_grid_high = high_indices < grid.size
    high[has_grid_high] = grid[high_indices[has_grid_high]]
    active_high = low_hit.copy()
    queried_hit, queried_distance, queried_face, queried_point = query(high, active_high)
    high_indices_active = np.flatnonzero(active_high)
    high_hit[high_indices_active] = queried_hit
    high_distance[high_indices_active] = queried_distance
    high_face[high_indices_active] = queried_face
    high_point[high_indices_active] = queried_point

    while True:
        advance = low_hit & high_hit & (high < maximum - MESH_NUMERICAL_FLOOR_M)
        if not np.any(advance):
            break
        next_indices = np.searchsorted(grid, high + MESH_NUMERICAL_FLOOR_M, side="right")
        next_high = np.full(count, maximum, dtype=np.float64)
        has_next = next_indices < grid.size
        next_high[has_next] = grid[next_indices[has_next]]
        high[advance] = next_high[advance]
        queried_hit, queried_distance, queried_face, queried_point = query(high, advance)
        advance_indices = np.flatnonzero(advance)
        high_hit[advance_indices] = queried_hit
        high_distance[advance_indices] = queried_distance
        high_face[advance_indices] = queried_face
        high_point[advance_indices] = queried_point

    refine = low_hit & ~high_hit
    if np.any(refine):
        safe_distance = np.where(np.isfinite(low_distance), np.maximum(low_distance, 1.0), 1.0)
        angular_floor = MESH_NUMERICAL_FLOOR_M / safe_distance
        bracket = np.maximum((high - low) / angular_floor, 1.0)
        iterations = np.maximum(
            1,
            np.ceil(np.log2(bracket)).astype(np.int64),
        )
        iterations = np.minimum(iterations, 24)
        max_iterations = int(np.max(iterations[refine]))
        for iteration in range(max_iterations):
            active = refine & (iterations > iteration)
            if not np.any(active):
                break
            midpoint = 0.5 * (low + high)
            queried_hit, queried_distance, queried_face, queried_point = query(midpoint, active)
            active_indices = np.flatnonzero(active)
            hit_indices = active_indices[queried_hit]
            miss_indices = active_indices[~queried_hit]
            low[hit_indices] = midpoint[hit_indices]
            low_distance[hit_indices] = queried_distance[queried_hit]
            low_face[hit_indices] = queried_face[queried_hit]
            low_point[hit_indices] = queried_point[queried_hit]
            high[miss_indices] = midpoint[miss_indices]
    return low, low_distance, low_face, low_point, low_hit


def _refine_silhouette_hit(
    geometry: Any,
    origin: np.ndarray,
    azimuth: float,
    alpha: float,
    *,
    elevations: int,
) -> tuple[float, float, int, np.ndarray] | None:
    """Scalar compatibility wrapper around the batched refinement."""
    refined_alpha, distance, face, point, valid = _refine_silhouette_hits(
        geometry,
        np.asarray(origin, dtype=np.float64),
        np.asarray([azimuth], dtype=np.float64),
        np.asarray([alpha], dtype=np.float64),
        elevations=elevations,
    )
    if not valid[0]:
        return None
    return float(refined_alpha[0]), float(distance[0]), int(face[0]), point[0]


def _midpoint_face_gate(
    valid_indices: np.ndarray,
    first_valid: np.ndarray,
    face_values: np.ndarray,
    candidates: list[tuple[np.ndarray, np.ndarray, tuple[int, int]]],
    *,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
) -> np.ndarray:
    sky_ready = first_valid.copy()
    for local_index, candidate_index in enumerate(valid_indices):
        if not first_valid[local_index]:
            continue
        face_index = int(face_values[local_index])
        edge = candidates[candidate_index][2]
        incident = edge_faces.get(edge, [])
        if not (0 <= face_index < faces.shape[0]) or not incident:
            sky_ready[local_index] = False
            continue
        if edge in _face_edges(faces[face_index]):
            continue
        in_coplanar_component = any(
            face_index
            in _coplanar_component(
                incident_face,
                faces=faces,
                edge_faces=edge_faces,
                normals=normals,
            )
            for incident_face in incident
        )
        if not in_coplanar_component:
            sky_ready[local_index] = False
    return sky_ready


def _midpoint_sky_probes(
    valid_indices: np.ndarray,
    sky_ready: np.ndarray,
    origins: np.ndarray,
    delta: np.ndarray,
    slant: np.ndarray,
    *,
    elevations: int,
) -> tuple[list[int], list[np.ndarray], list[list[float]]]:
    minimum = np.radians(ELEVATION_MIN_DEG)
    maximum = np.radians(ELEVATION_MAX_DEG)
    log_step = np.log(maximum / minimum) / float(max(elevations - 1, 1))
    sky_indices: list[int] = []
    sky_origins: list[np.ndarray] = []
    sky_directions: list[list[float]] = []
    for local_index, candidate_index in enumerate(valid_indices):
        if not sky_ready[local_index]:
            continue
        delta_candidate = delta[candidate_index]
        horizontal = float(np.linalg.norm(delta_candidate[:2]))
        elevation = float(np.arctan2(delta_candidate[2], horizontal))
        if elevation < minimum - MESH_NUMERICAL_FLOOR_M or elevation >= maximum - MESH_NUMERICAL_FLOOR_M:
            continue
        local_step = max(abs(elevation), minimum) * np.expm1(log_step) if elevations > 1 else maximum - minimum
        above_elevation = min(
            elevation + max(local_step * 0.5, MESH_NUMERICAL_FLOOR_M / max(slant[candidate_index], 1.0)),
            maximum - MESH_NUMERICAL_FLOOR_M,
        )
        if above_elevation <= elevation:
            continue
        azimuth = float(np.arctan2(delta_candidate[1], delta_candidate[0]))
        sky_indices.append(local_index)
        sky_origins.append(origins[candidate_index])
        sky_directions.append(
            [
                np.cos(above_elevation) * np.cos(azimuth),
                np.cos(above_elevation) * np.sin(azimuth),
                np.sin(above_elevation),
            ]
        )
    return sky_indices, sky_origins, sky_directions


def _midpoint_shadow_valid_batch(
    geometry: Any,
    candidates: list[tuple[np.ndarray, np.ndarray, tuple[int, int]]],
    *,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
    elevations: int,
) -> np.ndarray:
    """Batch first-hit and sky-above checks for candidate interval midpoints."""
    count = len(candidates)
    result = np.zeros(count, dtype=bool)
    if count == 0:
        return result
    origins = np.asarray([candidate[0] for candidate in candidates], dtype=np.float64)
    midpoints = np.asarray([candidate[1] for candidate in candidates], dtype=np.float64)
    delta = midpoints - origins
    slant = np.linalg.norm(delta, axis=1)
    valid_indices = np.flatnonzero(np.isfinite(slant) & (slant > MESH_NUMERICAL_FLOOR_M))
    if valid_indices.size == 0:
        return result
    direction = delta[valid_indices] / slant[valid_indices, None]
    hit, distance, _, hit_face = geometry.intersect(origins[valid_indices], direction)
    hit_value = np.asarray(hit, dtype=bool)
    distance_value = np.asarray(distance, dtype=np.float64)
    face_value = np.asarray(hit_face, dtype=np.int64)
    tolerance = np.maximum(
        MESH_NUMERICAL_FLOOR_M,
        np.finfo(np.float64).eps * 64.0 * np.maximum(slant[valid_indices], 1.0),
    )
    first_valid = (
        hit_value
        & np.isfinite(distance_value)
        & (distance_value > 0.0)
        & (np.abs(distance_value - slant[valid_indices]) <= tolerance)
    )
    sky_ready = _midpoint_face_gate(
        valid_indices,
        first_valid,
        face_value,
        candidates,
        faces=faces,
        edge_faces=edge_faces,
        normals=normals,
    )
    sky_indices, sky_origins, sky_directions = _midpoint_sky_probes(
        valid_indices,
        sky_ready,
        origins,
        delta,
        slant,
        elevations=elevations,
    )
    if not sky_indices:
        return result
    above_hit, above_distance, _, _ = geometry.intersect(
        np.asarray(sky_origins, dtype=np.float64), np.asarray(sky_directions, dtype=np.float64)
    )
    for sky_index, blocked, sky_distance in zip(
        sky_indices,
        np.asarray(above_hit, dtype=bool),
        np.asarray(above_distance, dtype=np.float64),
        strict=True,
    ):
        if not (blocked and np.isfinite(sky_distance) and sky_distance > 0.0):
            result[valid_indices[sky_index]] = True
    return result


def _midpoint_shadow_valid(
    geometry: Any,
    origin: np.ndarray,
    midpoint: np.ndarray,
    edge: tuple[int, int],
    *,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
    elevations: int,
) -> bool:
    """Require one interval midpoint to pass the batched visibility gate."""
    result = _midpoint_shadow_valid_batch(
        geometry,
        [(np.asarray(origin, dtype=np.float64), np.asarray(midpoint, dtype=np.float64), edge)],
        faces=faces,
        edge_faces=edge_faces,
        normals=normals,
        elevations=elevations,
    )
    return bool(result[0])


_MeshEdgeKey = tuple[tuple[int, ...], tuple[int, ...]]
_MeshContact = tuple[int, int, float, float, tuple[int, int], np.ndarray]
_MeshInterval = tuple[tuple[int, ...], tuple[int, ...], float, float, set[tuple[int, int]]]
_ShadowCandidate = tuple[
    tuple[int, ...],
    tuple[int, ...],
    float,
    float,
    set[tuple[int, int]],
    np.ndarray,
    np.ndarray,
    tuple[int, int],
]


@dataclass
class _MeshViewResult:
    contacts_by_edge: dict[_MeshEdgeKey, list[_MeshContact]] = field(default_factory=dict)
    original_edges_by_geometry: dict[_MeshEdgeKey, set[tuple[int, int]]] = field(default_factory=dict)
    selected: set[tuple[int, int]] = field(default_factory=set)
    visible_face_ids: set[int] = field(default_factory=set)
    residuals: list[float] = field(default_factory=list)
    residual_bounds: list[float] = field(default_factory=list)
    refused_residuals: list[float] = field(default_factory=list)
    accepted_contacts: int = 0
    refused_contacts: int = 0


@dataclass
class _IntervalBuildResult:
    interval_records: list[_MeshInterval] = field(default_factory=list)
    candidate_interval_count: int = 0
    refused_shadow_intervals: int = 0
    singleton_contacts: int = 0
    zero_intervals: int = 0


def _geometric_edge_key(
    vertices: np.ndarray,
    coordinate_tolerance: float,
    edge: tuple[int, int],
) -> _MeshEdgeKey:
    endpoints = vertices[np.asarray(edge, dtype=np.int64)]
    quantized = np.rint(endpoints / coordinate_tolerance).astype(np.int64)
    ordered = sorted(tuple(int(value) for value in endpoint) for endpoint in quantized)
    return ordered[0], ordered[1]


def _evaluate_mesh_hit(
    face_index: int,
    point: np.ndarray,
    origin: np.ndarray,
    azimuth: float,
    alpha: float,
    slant_range: float,
    *,
    vertices: np.ndarray,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
    azimuths: int,
    elevations: int,
    clutter_triangles: np.ndarray | None,
) -> tuple[tuple[tuple[int, int], float, float, str] | None, float | None]:
    residual_bound = _fan_residual_bound_m(alpha, slant_range, azimuths=azimuths, elevations=elevations)
    candidate = _select_mesh_contact(
        face_index,
        point,
        origin,
        azimuth,
        vertices=vertices,
        faces=faces,
        edge_faces=edge_faces,
        normals=normals,
    )
    if candidate is None:
        return None, None
    edge, _, residual, _ = candidate
    if clutter_triangles is not None and any(
        0 <= index < clutter_triangles.size and bool(clutter_triangles[index]) for index in edge_faces[edge]
    ):
        return None, None
    if residual > residual_bound:
        return None, residual
    return candidate, residual_bound


def _collect_mesh_view(
    geometry: Any,
    origin: np.ndarray,
    view_index: int,
    silhouette: Any,
    *,
    vertices: np.ndarray,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
    coordinate_tolerance: float,
    azimuths: int,
    elevations: int,
    floor_m: float,
    clutter_triangles: np.ndarray | None,
) -> _MeshViewResult:
    result = _MeshViewResult()
    alpha, horizontal, found = silhouette(geometry, origin, azimuths=azimuths, elevations=elevations)
    azimuth = (np.arange(azimuths, dtype=np.float64) + 0.5) * (2.0 * np.pi / azimuths)
    good = found & np.isfinite(horizontal) & (horizontal > floor_m) & np.isfinite(alpha)
    if not np.any(good):
        return result
    directions = np.stack(
        [np.cos(alpha) * np.cos(azimuth), np.cos(alpha) * np.sin(azimuth), np.sin(alpha)],
        axis=-1,
    )
    hit, distance, _, hit_face = geometry.intersect(np.broadcast_to(origin, directions[good].shape), directions[good])
    hit_face = np.asarray(hit_face, dtype=np.int64)
    hit = np.asarray(hit, dtype=bool)
    distance = np.asarray(distance, dtype=np.float64)
    valid = hit & (hit_face >= 0) & (hit_face < faces.shape[0]) & np.isfinite(distance)
    if not np.any(valid):
        return result
    hit_face = hit_face[valid]
    good_indices = np.flatnonzero(good)[valid]
    hit_points = np.asarray(origin)[None, :] + distance[valid, None] * directions[good][valid]
    hit_distances = distance[valid]
    result.visible_face_ids.update(int(face_index) for face_index in np.unique(hit_face))
    _, refined_distance, refined_face, refined_point, refined_valid = _refine_silhouette_hits(
        geometry,
        origin,
        azimuth[good_indices],
        alpha[good_indices],
        elevations=elevations,
    )
    for local_index, (ray_index, face_index, point, slant_range) in enumerate(
        zip(good_indices, hit_face, hit_points, hit_distances, strict=True)
    ):
        if refined_valid[local_index] and 0 <= refined_face[local_index] < faces.shape[0]:
            slant_range = refined_distance[local_index]
            face_index = int(refined_face[local_index])
            point = refined_point[local_index]
        candidate, bound_or_rejected_residual = _evaluate_mesh_hit(
            int(face_index),
            point,
            origin,
            float(azimuth[ray_index]),
            float(alpha[ray_index]),
            float(slant_range),
            vertices=vertices,
            faces=faces,
            edge_faces=edge_faces,
            normals=normals,
            azimuths=azimuths,
            elevations=elevations,
            clutter_triangles=clutter_triangles,
        )
        if candidate is None:
            result.refused_contacts += 1
            if bound_or_rejected_residual is not None:
                result.refused_residuals.append(bound_or_rejected_residual)
            continue
        edge, parameter, residual, _ = candidate
        result.accepted_contacts += 1
        result.residuals.append(residual)
        result.residual_bounds.append(float(bound_or_rejected_residual))
        result.selected.add(edge)
        key = _geometric_edge_key(vertices, coordinate_tolerance, edge)
        result.original_edges_by_geometry.setdefault(key, set()).add(edge)
        result.contacts_by_edge.setdefault(key, []).append(
            (int(view_index), int(ray_index), parameter, residual, edge, np.asarray(origin, dtype=np.float64).copy())
        )
    return result


def _adjacent_shadow_candidates(
    key: _MeshEdgeKey,
    contacts: list[_MeshContact],
    original_edges: set[tuple[int, int]],
    *,
    coordinate_tolerance: float,
    azimuths: int,
) -> tuple[list[_ShadowCandidate], int, int, int]:
    endpoint_coordinates = np.asarray(key, dtype=np.float64) * coordinate_tolerance
    edge_length = float(np.linalg.norm(endpoint_coordinates[1] - endpoint_coordinates[0]))
    if edge_length <= MESH_NUMERICAL_FLOOR_M:
        return [], 0, 0, 0
    by_view: dict[int, dict[int, list[tuple[float, float, tuple[int, int], np.ndarray]]]] = {}
    for view_index, ray_index, parameter, residual, edge, origin in contacts:
        by_view.setdefault(view_index, {}).setdefault(ray_index, []).append((parameter, residual, edge, origin))
    candidates: list[_ShadowCandidate] = []
    candidate_count = 0
    singleton_count = 0
    zero_count = 0
    for view_index in sorted(by_view):
        by_ray = by_view[view_index]
        if len(by_ray) < 2:
            singleton_count += len(by_ray)
            continue
        pair_result = _shadow_pair_candidates(
            key,
            by_ray,
            original_edges,
            endpoint_coordinates,
            azimuths,
        )
        pair_candidates, pair_count, pair_zero_count = pair_result
        candidates.extend(pair_candidates)
        candidate_count += pair_count
        zero_count += pair_zero_count
    return candidates, candidate_count, singleton_count, zero_count


def _shadow_pair_candidates(
    key: _MeshEdgeKey,
    by_ray: dict[int, list[tuple[float, float, tuple[int, int], np.ndarray]]],
    original_edges: set[tuple[int, int]],
    endpoint_coordinates: np.ndarray,
    azimuths: int,
) -> tuple[list[_ShadowCandidate], int, int]:
    candidates: list[_ShadowCandidate] = []
    candidate_count = 0
    zero_count = 0
    paired_cells: set[tuple[int, int]] = set()
    for ray_index in sorted(by_ray):
        next_ray = (ray_index + 1) % max(int(azimuths), 1)
        if next_ray == ray_index or next_ray not in by_ray:
            continue
        pair_key = (min(ray_index, next_ray), max(ray_index, next_ray))
        if pair_key in paired_cells:
            continue
        paired_cells.add(pair_key)
        for first in by_ray[ray_index]:
            for second in by_ray[next_ray]:
                start_parameter, end_parameter = float(first[0]), float(second[0])
                low, high = sorted((start_parameter, end_parameter))
                candidate_count += 1
                if high - low <= MESH_NUMERICAL_FLOOR_M:
                    zero_count += 1
                    continue
                midpoint = endpoint_coordinates[0] + 0.5 * (low + high) * (
                    endpoint_coordinates[1] - endpoint_coordinates[0]
                )
                candidates.append(
                    (
                        key[0],
                        key[1],
                        low,
                        high,
                        original_edges,
                        first[3],
                        midpoint,
                        first[2],
                    )
                )
    return candidates, candidate_count, zero_count


def _build_interval_records(
    geometry: Any,
    contacts_by_edge: dict[_MeshEdgeKey, list[_MeshContact]],
    original_edges_by_geometry: dict[_MeshEdgeKey, set[tuple[int, int]]],
    *,
    coordinate_tolerance: float,
    azimuths: int,
    faces: np.ndarray,
    edge_faces: dict[tuple[int, int], list[int]],
    normals: np.ndarray,
    elevations: int,
) -> _IntervalBuildResult:
    result = _IntervalBuildResult()
    shadow_candidates: list[_ShadowCandidate] = []
    for key in sorted(contacts_by_edge):
        contacts = sorted(contacts_by_edge[key], key=lambda item: (item[0], item[1], item[2], item[4]))
        candidates, candidate_count, singleton_count, zero_count = _adjacent_shadow_candidates(
            key,
            contacts,
            original_edges_by_geometry[key],
            coordinate_tolerance=coordinate_tolerance,
            azimuths=azimuths,
        )
        shadow_candidates.extend(candidates)
        result.candidate_interval_count += candidate_count
        result.singleton_contacts += singleton_count
        result.zero_intervals += zero_count
    shadow_results = _midpoint_shadow_valid_batch(
        geometry,
        [(candidate[5], candidate[6], candidate[7]) for candidate in shadow_candidates],
        faces=faces,
        edge_faces=edge_faces,
        normals=normals,
        elevations=elevations,
    )
    for candidate, accepted in zip(shadow_candidates, shadow_results, strict=True):
        if not accepted:
            result.refused_shadow_intervals += 1
            continue
        result.interval_records.append((candidate[0], candidate[1], candidate[2], candidate[3], candidate[4]))
    return result


def _union_interval_records(
    interval_records: list[_MeshInterval],
    coordinate_tolerance: float,
) -> list[_MeshInterval]:
    validated_by_key: dict[_MeshEdgeKey, list[tuple[float, float]]] = {}
    contributing_by_key: dict[_MeshEdgeKey, set[tuple[int, int]]] = {}
    for start_coordinates, end_coordinates, low, high, original_edges in interval_records:
        key = (start_coordinates, end_coordinates)
        validated_by_key.setdefault(key, []).append((low, high))
        contributing_by_key.setdefault(key, set()).update(original_edges)
    unioned: list[_MeshInterval] = []
    for key in sorted(validated_by_key):
        endpoint_coordinates = np.asarray(key, dtype=np.float64) * coordinate_tolerance
        edge_length = float(np.linalg.norm(endpoint_coordinates[1] - endpoint_coordinates[0]))
        parameter_tolerance = max(MESH_NUMERICAL_FLOOR_M / max(edge_length, MESH_NUMERICAL_FLOOR_M), 1.0e-12)
        spans = sorted(validated_by_key[key])
        low, high = spans[0]
        for start_parameter, end_parameter in spans[1:]:
            if start_parameter <= high + parameter_tolerance:
                high = max(high, end_parameter)
                continue
            unioned.append((key[0], key[1], low, high, contributing_by_key[key]))
            low, high = start_parameter, end_parameter
        unioned.append((key[0], key[1], low, high, contributing_by_key[key]))
    return unioned


def _materialize_interval_records(
    interval_records: list[_MeshInterval],
    coordinate_tolerance: float,
) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int]]]:
    points_list: list[np.ndarray] = []
    lengths_list: list[float] = []
    contributing_edges: set[tuple[int, int]] = set()
    for start_coordinates, end_coordinates, low, high, original_edges in interval_records:
        start = np.asarray(start_coordinates, dtype=np.float64) * coordinate_tolerance
        end = np.asarray(end_coordinates, dtype=np.float64) * coordinate_tolerance
        midpoint = start + 0.5 * (low + high) * (end - start)
        length = float(high - low) * float(np.linalg.norm(end - start))
        points_list.append(midpoint)
        lengths_list.append(length)
        contributing_edges.update(original_edges)
    return (
        np.asarray(points_list, dtype=np.float64),
        np.asarray(lengths_list, dtype=np.float64),
        sorted(contributing_edges),
    )


@dataclass
class _MeshCurveAccumulation:
    selected: set[tuple[int, int]] = field(default_factory=set)
    visible_face_ids: set[int] = field(default_factory=set)
    residuals: list[float] = field(default_factory=list)
    residual_bounds: list[float] = field(default_factory=list)
    refused_residuals: list[float] = field(default_factory=list)
    accepted_contacts: int = 0
    refused_contacts: int = 0
    contacts_by_edge: dict[_MeshEdgeKey, list[_MeshContact]] = field(default_factory=dict)
    original_edges_by_geometry: dict[_MeshEdgeKey, set[tuple[int, int]]] = field(default_factory=dict)


def _prepare_mesh_curve_inputs(
    geometry: Any,
    standpoints: np.ndarray,
    top_edge_tolerance_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[tuple[int, int], list[int]], np.ndarray, float]:
    vertices = np.asarray(geometry.vertices, dtype=np.float64)
    faces = np.asarray(geometry.faces, dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError("mesh geometry must expose vertices (V, 3) and faces (F, 3)")
    origins = np.asarray(standpoints, dtype=np.float64)
    edge_faces = _mesh_edge_faces(faces)
    if not np.isfinite(top_edge_tolerance_m) or top_edge_tolerance_m < 0.0:
        raise ValueError("top_edge_tolerance_m must be finite and nonnegative")
    normals = _mesh_face_normals(vertices, faces)
    coordinate_span = max(float(np.ptp(vertices, axis=0).max()), 1.0)
    coordinate_tolerance = max(MESH_NUMERICAL_FLOOR_M, 1.0e-8 * coordinate_span)
    return vertices, faces, origins, edge_faces, normals, coordinate_tolerance


def _merge_mesh_view_result(state: _MeshCurveAccumulation, view: _MeshViewResult) -> None:
    state.selected.update(view.selected)
    state.visible_face_ids.update(view.visible_face_ids)
    state.residuals.extend(view.residuals)
    state.residual_bounds.extend(view.residual_bounds)
    state.refused_residuals.extend(view.refused_residuals)
    state.accepted_contacts += view.accepted_contacts
    state.refused_contacts += view.refused_contacts
    for key, edges in view.original_edges_by_geometry.items():
        state.original_edges_by_geometry.setdefault(key, set()).update(edges)
    for key, contacts in view.contacts_by_edge.items():
        state.contacts_by_edge.setdefault(key, []).extend(contacts)


def build_mesh_edge_curve(
    geometry: Any,
    standpoints: np.ndarray,
    silhouette: Any,
    *,
    azimuths: int = 1440,
    elevations: int = 600,
    floor_m: float = 0.0,
    clutter_triangles: np.ndarray | None = None,
    top_edge_tolerance_m: float = 0.25,
) -> FacadeTipCurve:
    """Build a route skyline support from exact undirected mesh edges.

    A face is route-visible when it is the first hit of a topmost silhouette ray.
    Each hit is bracketed against the next elevation miss, then chooses an exact
    oriented boundary/crease contact. Coplanar shared edges are traversed as one
    tessellation component. Contacts form intervals only between adjacent fan
    cells within one view, and each interval midpoint must be first-visible with
    clear sky above. The geometric endpoint key prevents tiled duplicate IDs from
    double counting across views.
    """
    vertices, faces, origins, edge_faces, normals, coordinate_tolerance = _prepare_mesh_curve_inputs(
        geometry,
        standpoints,
        top_edge_tolerance_m,
    )
    state = _MeshCurveAccumulation()

    for view_index, origin in enumerate(origins):
        view = _collect_mesh_view(
            geometry,
            origin,
            view_index,
            silhouette,
            vertices=vertices,
            faces=faces,
            edge_faces=edge_faces,
            normals=normals,
            coordinate_tolerance=coordinate_tolerance,
            azimuths=azimuths,
            elevations=elevations,
            floor_m=floor_m,
            clutter_triangles=clutter_triangles,
        )
        _merge_mesh_view_result(state, view)
    if not state.selected:
        raise ValueError(
            "route silhouette selected no mesh facade-tip edges: "
            f"accepted_contacts={state.accepted_contacts}, refused_contacts={state.refused_contacts}"
        )

    interval_result = _build_interval_records(
        geometry,
        state.contacts_by_edge,
        state.original_edges_by_geometry,
        coordinate_tolerance=coordinate_tolerance,
        azimuths=azimuths,
        faces=faces,
        edge_faces=edge_faces,
        normals=normals,
        elevations=elevations,
    )
    if not interval_result.interval_records:
        raise ValueError("route silhouette selected only zero-length or unmatched mesh-edge intervals")
    interval_records = _union_interval_records(interval_result.interval_records, coordinate_tolerance)
    if not interval_records:
        raise ValueError("route silhouette selected only zero-length or unmatched mesh-edge intervals")
    points, lengths, contributing_edges = _materialize_interval_records(
        interval_records,
        coordinate_tolerance,
    )
    edges = sorted(contributing_edges or state.selected)
    if points.shape[0] == 0:
        raise ValueError("route silhouette selected only zero-length mesh edges")
    return FacadeTipCurve(
        points,
        lengths,
        {
            "construction": "route-visible skyline mesh-edge contour contacts",
            "selection_gate": (
                "oriented boundary/crease contour, coplanar-component traversal, "
                "adjacent-cell interval, midpoint first-visibility and sky gate, fan residual gate"
            ),
            "builders": int(origins.shape[0]),
            "builder_standpoints_sha256": _canonical_digest(origins),
            "builder_visible_faces": int(len(state.visible_face_ids)),
            "edge_selection_residual_m_max": float(max(state.residuals, default=0.0)),
            "edge_selection_residual_m_mean": float(np.mean(state.residuals)) if state.residuals else 0.0,
            "selection_residual_m_max": float(max(state.residuals, default=0.0)),
            "selection_residual_m_mean": float(np.mean(state.residuals)) if state.residuals else 0.0,
            "resolution_bound_m_max": float(max(state.residual_bounds, default=0.0)),
            "resolution_bound_m_mean": float(np.mean(state.residual_bounds)) if state.residual_bounds else 0.0,
            "accepted_contact_count": int(state.accepted_contacts),
            "refused_contact_count": int(state.refused_contacts),
            "refused_residual_m_max": float(max(state.refused_residuals, default=0.0)),
            "singleton_contact_count": int(interval_result.singleton_contacts),
            "zero_interval_count": int(interval_result.zero_intervals),
            "candidate_interval_count": int(interval_result.candidate_interval_count),
            "refused_shadow_interval_count": int(interval_result.refused_shadow_intervals),
            "interval_count": int(len(interval_records)),
            "interval_total_length_m": float(np.sum(lengths, dtype=np.float64)),
            "edge_coordinate_tolerance_m": float(coordinate_tolerance),
            "fan_boundary_recovery": "log-spaced elevation bracket with last-hit/first-miss bisection",
            "interval_pair_rule": "same_view_adjacent_azimuth_cells_with_wraparound",
            "midpoint_visibility_rule": "first_hit_on_selected_edge_and_resolution_derived_sky_miss",
            "contributing_edge_ids_sha256": _mesh_edge_hash(sorted(contributing_edges or state.selected)),
            "deprecated_top_edge_tolerance_m": float(top_edge_tolerance_m),
            "azimuths": int(azimuths),
            "elevations": int(elevations),
            "floor_m": float(floor_m),
            "edge_count": int(points.shape[0]),
            "resolution_metrics": {
                "azimuths": int(azimuths),
                "elevations": int(elevations),
                "edge_count": int(points.shape[0]),
                "support_length_m": float(np.sum(lengths, dtype=np.float64)),
            },
            "edge_ids_sha256": _mesh_edge_hash(edges),
            "merge_rule": EDGE_MERGE_RULE,
            "curve_resolution_m": 0.0,
        },
    )


def silhouette_polyline(
    geometry: Any,
    origin: np.ndarray,
    silhouette: Any,
    *,
    azimuths: int,
    elevations: int,
    floor_m: float = 0.0,
    clutter_triangles: np.ndarray | None = None,
) -> np.ndarray:
    """Evaluate one deterministic azimuth fan and return its ordered points."""
    point = np.asarray(origin, dtype=np.float64)
    alpha, horizontal, found = silhouette(geometry, point, azimuths=azimuths, elevations=elevations)
    azimuth = (np.arange(azimuths, dtype=np.float64) + 0.5) * (2.0 * np.pi / azimuths)
    good = found & np.isfinite(horizontal) & (horizontal > floor_m) & np.isfinite(alpha)
    slant = horizontal / np.maximum(np.cos(alpha), 1.0e-12)
    directions = np.stack(
        [np.cos(alpha) * np.cos(azimuth), np.cos(alpha) * np.sin(azimuth), np.sin(alpha)],
        axis=-1,
    )
    points = point + slant[:, None] * directions
    if clutter_triangles is not None and np.any(good):
        _, _, _, faces = geometry.intersect(
            np.broadcast_to(point, points[good].shape),
            directions[good],
        )
        faces = np.asarray(faces, dtype=np.int64)
        mask = np.ones(faces.shape, dtype=bool)
        valid = (faces >= 0) & (faces < clutter_triangles.size)
        mask[valid] = ~np.asarray(clutter_triangles, dtype=bool)[faces[valid]]
        good_indices = np.flatnonzero(good)
        good[good_indices[~mask]] = False
    return points[good]


def silhouette_polylines(
    geometry: Any,
    origin: np.ndarray,
    silhouette: Any,
    *,
    azimuths: int,
    elevations: int,
    floor_m: float = 0.0,
    clutter_triangles: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Return contiguous ordered silhouette runs, preserving no-hit gaps."""
    point = np.asarray(origin, dtype=np.float64)
    alpha, horizontal, found = silhouette(geometry, point, azimuths=azimuths, elevations=elevations)
    azimuth = (np.arange(azimuths, dtype=np.float64) + 0.5) * (2.0 * np.pi / azimuths)
    good = found & np.isfinite(horizontal) & (horizontal > floor_m) & np.isfinite(alpha)
    slant = horizontal / np.maximum(np.cos(alpha), 1.0e-12)
    directions = np.stack(
        [np.cos(alpha) * np.cos(azimuth), np.cos(alpha) * np.sin(azimuth), np.sin(alpha)],
        axis=-1,
    )
    points = point + slant[:, None] * directions
    if clutter_triangles is not None and np.any(good):
        _, _, _, faces = geometry.intersect(np.broadcast_to(point, points[good].shape), directions[good])
        faces = np.asarray(faces, dtype=np.int64)
        keep = np.ones(faces.shape, dtype=bool)
        valid = (faces >= 0) & (faces < clutter_triangles.size)
        keep[valid] = ~np.asarray(clutter_triangles, dtype=bool)[faces[valid]]
        indices = np.flatnonzero(good)
        good[indices[~keep]] = False
    if not np.any(good):
        return []
    if np.all(good):
        return [points]
    # Break at every missing azimuth, then join the wrap-around runs so that a
    # skyline crossing north is still one observed curve rather than two.
    starts = np.flatnonzero(good & ~np.roll(good, 1))
    runs: list[np.ndarray] = []
    for start in starts:
        indices = [int(start)]
        current = (int(start) + 1) % azimuths
        while current != start and good[current]:
            indices.append(current)
            current = (current + 1) % azimuths
        runs.append(points[np.asarray(indices, dtype=np.int64)])
    return runs


def build_facade_tip_curve(
    geometry: Any,
    standpoints: np.ndarray,
    silhouette: Any,
    *,
    azimuths: int = 1440,
    elevations: int = 600,
    floor_m: float = 0.0,
    clutter_triangles: np.ndarray | None = None,
    curve_resolution_m: float = 1.0e-4,
    top_edge_tolerance_m: float = 0.25,
) -> FacadeTipCurve:
    """Build one deterministic curve from the fixed builder standpoint set."""
    origins = np.asarray(standpoints, dtype=np.float64)
    if origins.ndim != 2 or origins.shape[1] != 3:
        raise ValueError("standpoints must have shape (builders, 3)")
    if hasattr(geometry, "vertices") and hasattr(geometry, "faces") and hasattr(geometry, "intersect"):
        return build_mesh_edge_curve(
            geometry,
            origins,
            silhouette,
            azimuths=azimuths,
            elevations=elevations,
            floor_m=floor_m,
            clutter_triangles=clutter_triangles,
            top_edge_tolerance_m=top_edge_tolerance_m,
        )
    polylines: list[np.ndarray] = []
    for origin in origins:
        polylines.extend(
            silhouette_polylines(
                geometry,
                origin,
                silhouette,
                azimuths=azimuths,
                elevations=elevations,
                floor_m=floor_m,
                clutter_triangles=clutter_triangles,
            )
        )
    return curve_from_polylines(
        polylines,
        tolerance_m=curve_resolution_m,
        provenance={
            "construction": "deterministic silhouette polylines from fixed builder standpoints",
            "builders": int(origins.shape[0]),
            "builder_standpoints_sha256": _canonical_digest(origins),
            "azimuths": int(azimuths),
            "elevations": int(elevations),
            "floor_m": float(floor_m),
            "resolution_metrics": {
                "azimuths": int(azimuths),
                "elevations": int(elevations),
            },
        },
    )
