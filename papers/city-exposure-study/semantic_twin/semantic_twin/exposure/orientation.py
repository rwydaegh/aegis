"""Exact body-orientation averages for the level-2 incidence law."""

from __future__ import annotations

import operator

import numpy as np


_HORIZONTAL_TOL = 1.0e-15


def _unit_vectors(value: np.ndarray, name: str) -> np.ndarray:
    vectors = np.asarray(value, dtype=np.float64)
    if vectors.ndim != 2 or vectors.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3), got {vectors.shape}")
    if not np.all(np.isfinite(vectors)):
        raise ValueError(f"{name} must be finite")
    norms = np.linalg.norm(vectors, axis=1)
    if np.any(norms <= 0.0):
        raise ValueError(f"{name} rows must have positive norms")
    if not np.allclose(norms, 1.0, rtol=1.0e-7, atol=1.0e-7):
        raise ValueError(f"{name} rows must be unit directions")
    return vectors


def _positive_chunk_size(value: int, name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a positive integer")
    try:
        chunk = operator.index(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if chunk <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return chunk


def _uniform_z_yaw_mean_chunk(normals: np.ndarray, arrival_k_hat: np.ndarray) -> np.ndarray:
    """Evaluate the closed form for one direction chunk.

    The returned array has shape ``(normals, directions)``. ``arrival_k_hat``
    is the physical direction of arrival, so the propagation direction in the
    AEGIS incidence law is ``q = -arrival_k_hat``.
    """
    q = -arrival_k_hat
    vertical = normals[:, 2, None] * q[None, :, 2]
    horizontal = np.hypot(normals[:, 0], normals[:, 1])[:, None] * np.hypot(q[:, 0], q[:, 1])[None, :]

    result = np.empty_like(vertical)
    horizontal_zero = horizontal <= _HORIZONTAL_TOL
    np.maximum(vertical, 0.0, out=result, where=horizontal_zero)

    active = ~horizontal_zero
    all_positive = active & (vertical >= horizontal)
    all_negative = active & (vertical <= -horizontal)
    interior = active & ~all_positive & ~all_negative
    result[all_positive] = vertical[all_positive]
    result[all_negative] = 0.0
    if np.any(interior):
        ratio = np.clip(-vertical[interior] / horizontal[interior], -1.0, 1.0)
        radicand = np.maximum(horizontal[interior] ** 2 - vertical[interior] ** 2, 0.0)
        result[interior] = (vertical[interior] * np.arccos(ratio) + np.sqrt(radicand)) / np.pi
    np.clip(result, 0.0, 1.0, out=result)
    return result


def uniform_z_yaw_mean_incidence(
    normals: np.ndarray,
    arrival_k_hat: np.ndarray,
    *,
    chunk_directions: int = 512,
    chunk_normals: int = 4096,
) -> np.ndarray:
    """Return exact uniform-Z-yaw mean incidence for each triangle/direction.

    For unit body normal ``n`` and physical arrival direction ``k``, this is
    the exact mean over ``theta`` in ``[0, 2*pi)`` of
    ``ReLU[(Rz(theta) n) dot (-k)]``. The formula has no angular quadrature.
    The result has shape ``(len(normals), len(arrival_k_hat))`` and is filled in
    two-axis blocks to bound temporary memory. The returned matrix itself is
    unavoidable because this helper exposes the per-triangle/direction field.
    """
    normals = _unit_vectors(normals, "normals")
    arrival_k_hat = _unit_vectors(arrival_k_hat, "arrival_k_hat")
    direction_chunk = _positive_chunk_size(chunk_directions, "chunk_directions")
    normal_chunk = _positive_chunk_size(chunk_normals, "chunk_normals")
    result = np.empty((normals.shape[0], arrival_k_hat.shape[0]), dtype=np.float64)
    for normal_start in range(0, normals.shape[0], normal_chunk):
        normal_stop = min(normal_start + normal_chunk, normals.shape[0])
        normal_view = normals[normal_start:normal_stop]
        for direction_start in range(0, arrival_k_hat.shape[0], direction_chunk):
            direction_stop = min(direction_start + direction_chunk, arrival_k_hat.shape[0])
            result[normal_start:normal_stop, direction_start:direction_stop] = _uniform_z_yaw_mean_chunk(
                normal_view,
                arrival_k_hat[direction_start:direction_stop],
            )
    return result


__all__ = ["uniform_z_yaw_mean_incidence"]
