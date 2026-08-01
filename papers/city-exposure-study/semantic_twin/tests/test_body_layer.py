from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.body_layer import BodyUncertainty, CameraBasisENU, build_dynamic_body_artifact


def _basis() -> CameraBasisENU:
    return CameraBasisENU(
        right_enu=np.array((1.0, 0.0, 0.0)),
        forward_enu=np.array((0.0, 1.0, 0.0)),
        up_enu=np.array((0.0, 0.0, 1.0)),
    )


def _artifact(*, floor: np.ndarray | None = None):
    return build_dynamic_body_artifact(
        body_id="person-004",
        source_view_id="mapillary-00/h+00_000",
        vertices_camera_raw_m=np.array(((0.0, 0.0, 2.0), (1.0, 2.0, 3.0), (-1.0, 1.0, 4.0))),
        faces=np.array(((0, 1, 2),)),
        keypoints_camera_raw_m=np.array(((0.0, 1.0, 3.0),)),
        pred_cam_t_m=np.array((0.5, 0.25, 1.0)),
        camera_origin_enu_m=np.array((10.0, 20.0, 5.0)),
        camera_basis_enu=_basis(),
        support_floor_point_enu_m=floor,
        uncertainty=BodyUncertainty(reconstruction_std_m=0.08, reprojection_rmse_px=1.2),
    )


def test_camera_down_axis_and_pred_cam_translation_map_to_enu() -> None:
    artifact = _artifact()

    np.testing.assert_allclose(artifact.vertices_camera_raw_m[1], (1.0, 2.0, 3.0))
    np.testing.assert_allclose(artifact.vertices_enu_unfloored_m[1], (11.5, 24.0, 2.75))
    np.testing.assert_allclose(artifact.keypoints_enu_unfloored_m[0], (10.5, 24.0, 3.75))
    np.testing.assert_allclose(artifact.vertices_enu_m, artifact.vertices_enu_unfloored_m)
    assert artifact.placement_provenance == "camera_transform_only"


def test_optional_support_floor_uses_vertical_only_shift_and_preserves_raw_mesh() -> None:
    artifact = _artifact(floor=np.array((100.0, -300.0, 1.5)))

    np.testing.assert_allclose(artifact.vertices_camera_raw_m[0], (0.0, 0.0, 2.0))
    np.testing.assert_allclose(artifact.floor_shift_enu_m, (0.0, 0.0, -1.25))
    assert np.min(artifact.vertices_enu_m[:, 2]) == pytest.approx(1.5)
    np.testing.assert_allclose(artifact.vertices_enu_m[:, :2], artifact.vertices_enu_unfloored_m[:, :2])
    assert artifact.placement_provenance == "support_floor_vertical_alignment"


def test_npz_round_trip_preserves_separate_raw_placed_and_uncertainty(tmp_path) -> None:
    artifact = _artifact(floor=np.array((0.0, 0.0, 1.5)))
    path = tmp_path / "person-004.npz"
    artifact.save(path)

    restored = type(artifact).load(path)

    for name in (
        "vertices_camera_raw_m",
        "faces",
        "keypoints_camera_raw_m",
        "vertices_enu_unfloored_m",
        "vertices_enu_m",
        "floor_shift_enu_m",
    ):
        np.testing.assert_array_equal(getattr(restored, name), getattr(artifact, name))
    assert restored.uncertainty == artifact.uncertainty
    assert restored.placement_provenance == artifact.placement_provenance


def test_body_artifact_rejects_non_orthonormal_basis_and_invalid_faces() -> None:
    with pytest.raises(ValueError, match="orthonormal"):
        CameraBasisENU(np.array((1.0, 0.0, 0.0)), np.array((1.0, 0.0, 0.0)), np.array((0.0, 0.0, 1.0)))
    with pytest.raises(ValueError, match="index vertices"):
        build_dynamic_body_artifact(
            body_id="bad",
            source_view_id="view",
            vertices_camera_raw_m=np.array(((0.0, 0.0, 1.0),)),
            faces=np.array(((0, 1, 2),)),
            keypoints_camera_raw_m=np.array(((0.0, 0.0, 1.0),)),
            pred_cam_t_m=np.zeros(3),
            camera_origin_enu_m=np.zeros(3),
            camera_basis_enu=_basis(),
        )
