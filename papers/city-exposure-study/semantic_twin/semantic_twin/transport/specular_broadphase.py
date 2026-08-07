"""Conservative geometric broad phase for finite order-one reflections."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

_DEFAULT_INSIDE_TOLERANCE = 2.0e-8
_ROUND_OFF_MULTIPLIER = 128.0


@dataclass(frozen=True)
class OrderOneBroadPhase:
    """Logical Cartesian indices surviving a conservative reflection-cone test."""

    flat_index: np.ndarray
    logical_candidates: int
    survivors: int
    source_chunks: int
    seconds: float

    def __post_init__(self) -> None:
        flat = np.asarray(self.flat_index, dtype=np.int64)
        if flat.ndim != 1:
            raise ValueError("broad-phase candidate indices must be one-dimensional")
        if np.any(flat < 0) or np.any(flat >= self.logical_candidates):
            raise ValueError("broad-phase candidate index lies outside the Cartesian product")
        if flat.size > 1 and np.any(flat[1:] <= flat[:-1]):
            raise ValueError("broad-phase candidate indices must be strictly increasing")
        if self.survivors != flat.size or not (0 <= self.survivors <= self.logical_candidates):
            raise ValueError("broad-phase survivor count must match candidate indices")
        if self.source_chunks < 0 or not np.isfinite(self.seconds) or self.seconds < 0.0:
            raise ValueError("broad-phase work diagnostics must be nonnegative")
        object.__setattr__(self, "flat_index", flat)

    def as_dict(self) -> dict[str, int | float | str]:
        fraction = self.survivors / self.logical_candidates if self.logical_candidates else 0.0
        return {
            "method": "conservative_mirrored_receiver_triangle_cones",
            "logical_candidates": self.logical_candidates,
            "survivors": self.survivors,
            "survivor_fraction": fraction,
            "source_chunks": self.source_chunks,
            "seconds": self.seconds,
        }


def conservative_order_one_candidates(
    sources: np.ndarray,
    receiver: np.ndarray,
    triangles: np.ndarray,
    normals: np.ndarray,
    *,
    epsilon_m: float,
    source_chunk: int = 16,
    inside_tolerance: float = _DEFAULT_INSIDE_TOLERANCE,
) -> OrderOneBroadPhase:
    """Return pairs whose image ray may meet its finite triangle.

    Reflecting the receiver in a face turns a valid reflection into a straight
    segment from the source through that triangle. The triangle and mirrored
    receiver define three oriented cone half-spaces. Together with the existing
    same-side condition, these are necessary conditions for the exact image
    solve. The barycentric tolerance is expanded projectively, and floating
    point padding only enlarges the cones.
    """
    started = time.perf_counter()
    source = np.asarray(sources, dtype=np.float64)
    receiver = np.asarray(receiver, dtype=np.float64)
    triangle = np.asarray(triangles, dtype=np.float64)
    normal = np.asarray(normals, dtype=np.float64)
    if source.ndim != 2 or source.shape[1] != 3:
        raise ValueError("sources must have shape (sources, 3)")
    if receiver.shape != (3,):
        raise ValueError("receiver must be one three-vector")
    if triangle.ndim != 3 or triangle.shape[1:] != (3, 3):
        raise ValueError("triangles must have shape (faces, 3, 3)")
    if normal.shape != (triangle.shape[0], 3):
        raise ValueError("normals must match triangles")
    if np.any(~np.isfinite(source)) or np.any(~np.isfinite(receiver)):
        raise ValueError("broad-phase endpoints must be finite")
    if np.any(~np.isfinite(triangle)) or np.any(~np.isfinite(normal)):
        raise ValueError("broad-phase surfaces must be finite")
    if epsilon_m < 0.0:
        raise ValueError("epsilon_m must be nonnegative")
    if inside_tolerance < 0.0 or not np.isfinite(inside_tolerance):
        raise ValueError("inside_tolerance must be finite and nonnegative")
    if source_chunk < 1:
        raise ValueError("source_chunk must be positive")

    source_count = source.shape[0]
    face_count = triangle.shape[0]
    logical = source_count * face_count
    if logical == 0:
        return OrderOneBroadPhase(np.empty(0, dtype=np.int64), logical, 0, 0, time.perf_counter() - started)

    plane_point = triangle[:, 0]
    receiver_side = np.einsum("ij,ij->i", receiver - plane_point, normal)
    normal_norm_bound = float(np.max(np.linalg.norm(normal, axis=1), initial=0.0))
    plane_point_norm_bound = float(np.max(np.linalg.norm(plane_point, axis=1), initial=0.0))
    receiver_side_error_bound = (
        np.finfo(np.float64).eps
        * _ROUND_OFF_MULTIPLIER
        * (np.linalg.norm(receiver) + plane_point_norm_bound)
        * normal_norm_bound
    )
    apex = receiver - 2.0 * receiver_side[:, None] * normal
    plane_offset = np.einsum("ij,ij->i", plane_point, normal)

    cone_normal = np.empty((3, face_count, 3), dtype=np.float64)
    cone_reference = np.empty((3, face_count), dtype=np.float64)
    cone_offset = np.empty((3, face_count), dtype=np.float64)
    cone_valid = np.empty((3, face_count), dtype=bool)
    for edge_index in range(3):
        first = triangle[:, edge_index]
        second = triangle[:, (edge_index + 1) % 3]
        opposite = triangle[:, (edge_index + 2) % 3]
        raw = np.cross(first - apex, second - apex)
        reference = np.einsum("ij,ij->i", opposite - apex, raw)
        orientation = np.where(reference < 0.0, -1.0, 1.0)
        oriented = raw * orientation[:, None]
        cone_normal[edge_index] = oriented
        cone_reference[edge_index] = np.abs(reference)
        cone_offset[edge_index] = np.einsum("ij,ij->i", apex, oriented)
        scale = np.linalg.norm(raw, axis=1) * np.maximum(np.linalg.norm(opposite - apex, axis=1), 1.0)
        cone_valid[edge_index] = np.abs(reference) > np.finfo(np.float64).eps * _ROUND_OFF_MULTIPLIER * scale

    flat_parts: list[np.ndarray] = []
    chunks = 0
    receiver_safe = np.maximum(np.abs(receiver_side), np.finfo(np.float64).tiny)
    cone_norm = np.linalg.norm(cone_normal, axis=2)
    for first_source in range(0, source_count, source_chunk):
        chunks += 1
        last_source = min(first_source + source_chunk, source_count)
        source_block = source[first_source:last_source]
        source_norm = np.linalg.norm(source_block, axis=1)[:, None]
        source_side = source_block @ normal.T - plane_offset
        source_side_error_bound = (
            np.finfo(np.float64).eps
            * _ROUND_OFF_MULTIPLIER
            * (float(np.max(source_norm, initial=0.0)) + plane_point_norm_bound)
            * normal_norm_bound
        )
        product_padding_bound = (
            float(np.max(np.abs(receiver_side), initial=0.0)) * source_side_error_bound
            + float(np.max(np.abs(source_side), initial=0.0)) * receiver_side_error_bound
            + source_side_error_bound * receiver_side_error_bound
        )
        keep = source_side * receiver_side > epsilon_m * epsilon_m - product_padding_bound
        with np.errstate(over="ignore", invalid="ignore"):
            projective_scale = 1.0 + np.abs(source_side) / receiver_safe
        projective_scale = np.where(np.isfinite(projective_scale), projective_scale, np.inf)

        for edge_index in range(3):
            value = source_block @ cone_normal[edge_index].T - cone_offset[edge_index]
            with np.errstate(over="ignore", invalid="ignore"):
                tolerance = inside_tolerance * cone_reference[edge_index] * projective_scale
                magnitude = (
                    source_norm * cone_norm[edge_index][None, :]
                    + np.abs(cone_offset[edge_index])[None, :]
                    + cone_reference[edge_index][None, :] * projective_scale
                )
                padding = np.finfo(np.float64).eps * _ROUND_OFF_MULTIPLIER * magnitude
            inside = value >= -(tolerance + padding)
            inside[:, ~cone_valid[edge_index]] = True
            keep &= inside

        local_source, local_face = np.nonzero(keep)
        flat_parts.append((local_source + first_source) * face_count + local_face)

    flat = np.concatenate(flat_parts) if flat_parts else np.empty(0, dtype=np.int64)
    return OrderOneBroadPhase(flat, logical, flat.size, chunks, time.perf_counter() - started)
