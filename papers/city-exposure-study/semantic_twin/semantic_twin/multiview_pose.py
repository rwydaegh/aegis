"""Dependency-light calibrated two-view relative pose primitives.

This module intentionally stops at a calibrated *relative* pose.  It can recover
rotation and a translation direction from static, geometrically valid feature
matches, but neither an essential matrix nor two-view triangulation determines
metric scale or an absolute world pose.  A caller must supply those from a
camera-position prior, mesh registration, GNSS, or another external constraint.

All cameras are conventional rectilinear pinhole cameras.  Equirectangular
panoramas must first be sampled into perspective views with their known
intrinsics; raw equirectangular pixel coordinates are not valid input here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class PinholeIntrinsics:
    """Pinhole intrinsics in pixel units."""

    fx: float
    fy: float
    cx: float
    cy: float

    def __post_init__(self) -> None:
        if self.fx <= 0.0 or self.fy <= 0.0:
            raise ValueError("fx and fy must be positive")


@dataclass(frozen=True)
class PixelCorrespondences:
    """Matched pixel centres ordered as camera A then camera B."""

    points_a: np.ndarray
    points_b: np.ndarray
    scores: np.ndarray | None = None

    def __post_init__(self) -> None:
        a = np.asarray(self.points_a, dtype=float)
        b = np.asarray(self.points_b, dtype=float)
        if a.ndim != 2 or a.shape[1] != 2 or b.shape != a.shape:
            raise ValueError("points_a and points_b must have matching shape (N, 2)")
        if not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError("pixel correspondences must be finite")
        if self.scores is not None:
            scores = np.asarray(self.scores, dtype=float)
            if scores.shape != (len(a),) or not np.isfinite(scores).all():
                raise ValueError("scores must be a finite array of shape (N,)")

    def subset(self, mask: np.ndarray) -> "PixelCorrespondences":
        """Return a checked subset, preserving score alignment."""
        keep = np.asarray(mask, dtype=bool)
        if keep.shape != (len(self.points_a),):
            raise ValueError("match mask must have shape (N,)")
        scores = None if self.scores is None else np.asarray(self.scores)[keep]
        return PixelCorrespondences(np.asarray(self.points_a)[keep], np.asarray(self.points_b)[keep], scores)


@dataclass(frozen=True)
class FilteredCorrespondences:
    """Result of match filtering with indices into the original match array."""

    correspondences: PixelCorrespondences
    source_indices: np.ndarray


MatchFilter = Callable[[PixelCorrespondences], np.ndarray]


def filter_correspondences(
    correspondences: PixelCorrespondences,
    *,
    valid_mask: np.ndarray | None = None,
    minimum_score: float | None = None,
    robust_filter: MatchFilter | None = None,
) -> FilteredCorrespondences:
    """Apply static/projection masks and an optional external robust filter.

    ``valid_mask`` is the integration point for SAM dynamic masks, depth
    blockers, and panorama seam/pole rules.  ``robust_filter`` may be a RANSAC
    adapter from OpenCV, Kornia, or a project-specific matcher.  It must return
    one boolean decision per input correspondence.  Keeping it external avoids
    an OpenCV dependency and lets callers record their exact robust estimator.
    """
    count = len(correspondences.points_a)
    keep = np.ones(count, dtype=bool)
    if valid_mask is not None:
        mask = np.asarray(valid_mask, dtype=bool)
        if mask.shape != (count,):
            raise ValueError("valid_mask must have shape (N,)")
        keep &= mask
    if minimum_score is not None:
        if correspondences.scores is None:
            raise ValueError("minimum_score requires correspondence scores")
        keep &= np.asarray(correspondences.scores) >= minimum_score
    if robust_filter is not None:
        robust = np.asarray(robust_filter(correspondences), dtype=bool)
        if robust.shape != (count,):
            raise ValueError("robust_filter must return a boolean array of shape (N,)")
        keep &= robust
    return FilteredCorrespondences(correspondences.subset(keep), np.flatnonzero(keep))


def pixels_to_unit_bearings(points: np.ndarray, intrinsics: PinholeIntrinsics) -> np.ndarray:
    """Convert pinhole pixel centres to unit camera-frame rays."""
    pixels = np.asarray(points, dtype=float)
    if pixels.ndim != 2 or pixels.shape[1] != 2 or not np.isfinite(pixels).all():
        raise ValueError("points must be a finite array of shape (N, 2)")
    rays = np.column_stack(
        (
            (pixels[:, 0] - intrinsics.cx) / intrinsics.fx,
            (pixels[:, 1] - intrinsics.cy) / intrinsics.fy,
            np.ones(len(pixels)),
        )
    )
    return rays / np.linalg.norm(rays, axis=1, keepdims=True)


def essential_matrix_eight_point(bearings_a: np.ndarray, bearings_b: np.ndarray) -> np.ndarray:
    """Estimate a rank-two essential matrix from at least eight calibrated rays."""
    a = _checked_bearings(bearings_a)
    b = _checked_bearings(bearings_b)
    if a.shape != b.shape or len(a) < 8:
        raise ValueError("eight-point estimation requires matching bearing arrays with N >= 8")
    ax, ay = a[:, 0] / a[:, 2], a[:, 1] / a[:, 2]
    bx, by = b[:, 0] / b[:, 2], b[:, 1] / b[:, 2]
    design = np.column_stack((bx * ax, bx * ay, bx, by * ax, by * ay, by, ax, ay, np.ones(len(a))))
    _, _, vh = np.linalg.svd(design)
    essential = vh[-1].reshape(3, 3)
    u, singular_values, vh = np.linalg.svd(essential)
    # Essential matrices have two equal non-zero singular values.  This is the
    # closest essential matrix in Frobenius norm after linear estimation.
    mean = (singular_values[0] + singular_values[1]) / 2.0
    return u @ np.diag([mean, mean, 0.0]) @ vh


@dataclass(frozen=True)
class RelativePose:
    """Pose of camera B relative to camera A, with an explicit metric scale."""

    rotation_b_from_a: np.ndarray
    translation_direction_b: np.ndarray
    cheirality_inliers: int
    source_indices: np.ndarray
    scale_from_prior: float | None = None

    def __post_init__(self) -> None:
        rotation = np.asarray(self.rotation_b_from_a, dtype=float)
        direction = np.asarray(self.translation_direction_b, dtype=float)
        if rotation.shape != (3, 3) or direction.shape != (3,):
            raise ValueError("rotation must be (3, 3) and translation direction must be (3,)")
        if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6) or np.linalg.det(rotation) < 0.0:
            raise ValueError("rotation_b_from_a must be a proper rotation")
        if not np.isclose(np.linalg.norm(direction), 1.0, atol=1e-6):
            raise ValueError("translation_direction_b must be unit length")
        if self.scale_from_prior is not None and self.scale_from_prior <= 0.0:
            raise ValueError("scale_from_prior must be positive")

    @property
    def translation_b_from_a(self) -> np.ndarray | None:
        """Metric translation only when an external scale prior was supplied."""
        if self.scale_from_prior is None:
            return None
        return self.translation_direction_b * self.scale_from_prior


def decompose_essential_matrix(essential: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return the four calibrated pose candidates ``(R_b_from_a, t_b)``."""
    matrix = np.asarray(essential, dtype=float)
    if matrix.shape != (3, 3) or not np.isfinite(matrix).all():
        raise ValueError("essential must be a finite (3, 3) matrix")
    u, _, vh = np.linalg.svd(matrix)
    if np.linalg.det(u) < 0.0:
        u[:, -1] *= -1.0
    if np.linalg.det(vh) < 0.0:
        vh[-1, :] *= -1.0
    w = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    rotations = (u @ w @ vh, u @ w.T @ vh)
    translation = u[:, 2] / np.linalg.norm(u[:, 2])
    candidates: list[tuple[np.ndarray, np.ndarray]] = []
    for rotation in rotations:
        if np.linalg.det(rotation) < 0.0:
            rotation = -rotation
        candidates.extend(((rotation, translation), (rotation, -translation)))
    return candidates


def select_pose_by_cheirality(
    candidates: list[tuple[np.ndarray, np.ndarray]], bearings_a: np.ndarray, bearings_b: np.ndarray
) -> tuple[np.ndarray, np.ndarray, int]:
    """Choose the candidate placing the most triangulated points before both cameras."""
    a = _checked_bearings(bearings_a)
    b = _checked_bearings(bearings_b)
    if a.shape != b.shape or not candidates:
        raise ValueError("matching bearings and at least one candidate are required")
    best: tuple[np.ndarray, np.ndarray, int] | None = None
    for rotation, translation in candidates:
        depths = _triangulated_depths(rotation, translation, a, b)
        count = int(np.count_nonzero((depths[:, 0] > 0.0) & (depths[:, 1] > 0.0)))
        if best is None or count > best[2]:
            best = (rotation, translation, count)
    assert best is not None
    return best


def estimate_relative_pose(
    correspondences: PixelCorrespondences,
    intrinsics_a: PinholeIntrinsics,
    intrinsics_b: PinholeIntrinsics,
    *,
    valid_mask: np.ndarray | None = None,
    minimum_score: float | None = None,
    robust_filter: MatchFilter | None = None,
    scale_from_prior: float | None = None,
) -> RelativePose:
    """Estimate/refine a pose from caller-filtered static calibrated matches.

    This re-estimates the essential matrix from all retained correspondences.
    In a production pipeline, provide a robust RANSAC inlier mask through
    ``robust_filter`` and call this again after mesh/depth consistency filtering
    to obtain the final inlier refinement.  It does not solve absolute pose.
    """
    filtered = filter_correspondences(
        correspondences, valid_mask=valid_mask, minimum_score=minimum_score, robust_filter=robust_filter
    )
    a = pixels_to_unit_bearings(filtered.correspondences.points_a, intrinsics_a)
    b = pixels_to_unit_bearings(filtered.correspondences.points_b, intrinsics_b)
    essential = essential_matrix_eight_point(a, b)
    rotation, direction, count = select_pose_by_cheirality(decompose_essential_matrix(essential), a, b)
    return RelativePose(rotation, direction, count, filtered.source_indices, scale_from_prior)


def _checked_bearings(bearings: np.ndarray) -> np.ndarray:
    rays = np.asarray(bearings, dtype=float)
    if rays.ndim != 2 or rays.shape[1] != 3 or not np.isfinite(rays).all() or np.any(rays[:, 2] <= 0.0):
        raise ValueError("bearings must be finite front-facing arrays of shape (N, 3)")
    return rays / np.linalg.norm(rays, axis=1, keepdims=True)


def _triangulated_depths(rotation: np.ndarray, translation: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Least-squares depths for ``lambda_b b = R lambda_a a + t``."""
    depths = np.empty((len(a), 2), dtype=float)
    for index, (ray_a, ray_b) in enumerate(zip(a, b, strict=True)):
        system = np.column_stack((rotation @ ray_a, -ray_b))
        depths[index] = np.linalg.lstsq(system, -translation, rcond=None)[0]
    return depths
