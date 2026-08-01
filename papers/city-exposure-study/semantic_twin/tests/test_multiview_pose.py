from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.multiview_pose import (
    PinholeIntrinsics,
    PixelCorrespondences,
    estimate_relative_pose,
    filter_correspondences,
    pixels_to_unit_bearings,
)


def _rotation_y(angle_deg: float) -> np.ndarray:
    angle = np.deg2rad(angle_deg)
    return np.array(
        [[np.cos(angle), 0.0, np.sin(angle)], [0.0, 1.0, 0.0], [-np.sin(angle), 0.0, np.cos(angle)]], dtype=float
    )


def _synthetic_matches() -> tuple[PixelCorrespondences, PinholeIntrinsics, np.ndarray, np.ndarray]:
    intrinsics = PinholeIntrinsics(900.0, 880.0, 640.0, 360.0)
    rng = np.random.default_rng(5)
    points_a_3d = np.column_stack((rng.uniform(-2.0, 2.0, 40), rng.uniform(-1.4, 1.4, 40), rng.uniform(5.0, 11.0, 40)))
    rotation = _rotation_y(7.0)
    translation = np.array([0.8, -0.05, 0.2])
    points_b_3d = (rotation @ points_a_3d.T).T + translation

    def project(point: np.ndarray) -> np.ndarray:
        return np.column_stack(
            (
                intrinsics.fx * point[:, 0] / point[:, 2] + intrinsics.cx,
                intrinsics.fy * point[:, 1] / point[:, 2] + intrinsics.cy,
            )
        )

    return PixelCorrespondences(project(points_a_3d), project(points_b_3d)), intrinsics, rotation, translation


def test_pixel_bearings_respect_principal_point_and_focal_lengths() -> None:
    intrinsics = PinholeIntrinsics(400.0, 200.0, 10.0, 20.0)
    bearings = pixels_to_unit_bearings(np.array([[10.0, 20.0], [410.0, 20.0], [10.0, 220.0]]), intrinsics)
    assert np.allclose(bearings[0], [0.0, 0.0, 1.0])
    assert np.allclose(bearings[1], np.array([1.0, 0.0, 1.0]) / np.sqrt(2.0))
    assert np.allclose(bearings[2], np.array([0.0, 1.0, 1.0]) / np.sqrt(2.0))


def test_filter_interface_combines_static_score_and_external_robust_masks() -> None:
    matches = PixelCorrespondences(
        np.arange(10, dtype=float).reshape(5, 2),
        np.arange(10, 20, dtype=float).reshape(5, 2),
        np.array([0.2, 0.9, 0.8, 0.1, 0.7]),
    )
    result = filter_correspondences(
        matches,
        valid_mask=np.array([True, True, False, True, True]),
        minimum_score=0.5,
        robust_filter=lambda _: np.array([True, True, True, True, False]),
    )
    assert result.source_indices.tolist() == [1]
    assert len(result.correspondences.points_a) == 1


def test_relative_pose_uses_cheirality_and_keeps_scale_explicit() -> None:
    matches, intrinsics, rotation_truth, translation_truth = _synthetic_matches()
    estimate = estimate_relative_pose(
        matches, intrinsics, intrinsics, scale_from_prior=np.linalg.norm(translation_truth)
    )
    assert estimate.cheirality_inliers == len(matches.points_a)
    assert np.allclose(estimate.rotation_b_from_a, rotation_truth, atol=1e-6)
    assert np.dot(estimate.translation_direction_b, translation_truth / np.linalg.norm(translation_truth)) > 0.999999
    assert np.allclose(estimate.translation_b_from_a, translation_truth, atol=1e-6)


def test_relative_pose_requires_external_metric_scale() -> None:
    matches, intrinsics, _, _ = _synthetic_matches()
    estimate = estimate_relative_pose(matches, intrinsics, intrinsics)
    assert estimate.scale_from_prior is None
    assert estimate.translation_b_from_a is None
    with pytest.raises(ValueError, match="positive"):
        estimate_relative_pose(matches, intrinsics, intrinsics, scale_from_prior=0.0)
