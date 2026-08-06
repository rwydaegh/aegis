from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.vision.bodies import (
    BodyUncertainty,
    CameraBasisENU,
    build_dynamic_body_artifact,
    camera_basis_from_pose,
    enu_to_camera,
    person_instances,
    pinhole_intrinsics,
    project_camera_points,
    range_corrected_translation,
)
from semantic_twin.pano_geometry import PerspectiveView, panorama_to_world_matrix, perspective_direction_at


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


def test_person_instances_split_by_connectivity_and_drop_what_cannot_be_reconstructed() -> None:
    labels = np.zeros((120, 120), dtype=np.int64)
    labels[10:90, 10:40] = 3  # a large person
    labels[10:70, 60:80] = 4  # a smaller one, a different person class
    labels[100:104, 100:104] = 3  # too few pixels
    labels[5:9, 100:118] = 3  # enough pixels but far too short to pose
    confidence = np.full((120, 120), 0.4)
    confidence[10:90, 10:40] = 0.9

    instances = person_instances(labels, {3, 4}, view_id="h+00_000", confidence=confidence, min_pixels=600)

    assert [instance.instance_id for instance in instances] == ["h+00_000_person_000", "h+00_000_person_001"]
    assert [instance.pixel_count for instance in instances] == [80 * 30, 60 * 20]
    assert instances[0].bbox_xyxy == (10, 10, 40, 90)
    assert instances[0].mean_confidence == pytest.approx(0.9)
    assert not np.any(instances[0].mask & instances[1].mask)


def test_two_people_in_one_class_stay_two_instances_when_they_do_not_touch() -> None:
    labels = np.zeros((120, 120), dtype=np.int64)
    labels[10:90, 10:40] = 3
    labels[10:90, 45:75] = 3

    assert len(person_instances(labels, {3}, view_id="v")) == 2

    labels[10:90, 40:45] = 3
    assert len(person_instances(labels, {3}, view_id="v")) == 1


def test_the_crop_basis_matches_the_ray_the_segmenter_and_the_depth_buffer_use() -> None:
    rotation = panorama_to_world_matrix(37.0, pitch_deg=4.0, roll_deg=-2.0)
    basis = camera_basis_from_pose(rotation, yaw_deg=90.0, pitch_deg=0.0)

    assert np.allclose(basis.matrix.T @ basis.matrix, np.eye(3), atol=1e-12)
    assert np.linalg.det(basis.matrix) > 0.0
    centre = perspective_direction_at(PerspectiveView("t", 90.0, 0.0, 90.0), 512.0, 512.0, 1024, 1024)
    assert np.allclose(basis.forward_enu, rotation @ centre, atol=1e-12)


def test_range_correction_moves_a_body_along_its_bearing_and_nowhere_else() -> None:
    translation = np.array((0.6, 1.2, 4.0))
    model_range = float(np.linalg.norm(translation))

    corrected, provenance, disagreement = range_corrected_translation(translation, 6.0)

    assert provenance == "range_corrected_along_bearing"
    assert np.linalg.norm(corrected) == pytest.approx(6.0)
    assert disagreement == pytest.approx(abs(6.0 - model_range))
    # Same ray, different distance along it.
    assert np.allclose(corrected / np.linalg.norm(corrected), translation / model_range, atol=1e-12)


def test_an_implausible_range_keeps_the_model_number_and_records_the_conflict() -> None:
    translation = np.array((0.0, 0.0, 4.0))

    far, provenance, disagreement = range_corrected_translation(translation, 40.0)
    absent, no_evidence, nothing = range_corrected_translation(translation, None)

    assert provenance == "sam_metric_translation_evidence_implausible"
    assert np.allclose(far, translation)
    assert disagreement == pytest.approx(36.0)
    assert no_evidence == "sam_metric_translation"
    assert np.allclose(absent, translation)
    assert nothing is None


def test_a_placed_body_reprojects_onto_the_pixels_it_was_reconstructed_from() -> None:
    rotation = panorama_to_world_matrix(211.0, pitch_deg=3.0, roll_deg=1.0)
    basis = camera_basis_from_pose(rotation, yaw_deg=180.0)
    origin = np.array((12.0, -5.0, 51.0))
    keypoints = np.array([(0.0, 0.0, 0.0), (0.2, -0.7, 0.05), (-0.3, 0.6, -0.1)])
    translation = np.array((0.4, 0.9, 5.0))
    intrinsics = pinhole_intrinsics(1024, 1024)
    expected = project_camera_points(keypoints + translation, intrinsics)

    artifact = build_dynamic_body_artifact(
        body_id="p",
        source_view_id="v",
        vertices_camera_raw_m=keypoints,
        faces=np.array(((0, 1, 2),)),
        keypoints_camera_raw_m=keypoints,
        pred_cam_t_m=translation,
        camera_origin_enu_m=origin,
        camera_basis_enu=basis,
    )
    recovered = project_camera_points(enu_to_camera(artifact.keypoints_enu_m, origin, basis), intrinsics)

    assert np.allclose(recovered, expected, atol=1e-9)


def test_the_floor_shift_is_carried_as_uncertainty_rather_than_silently_absorbed() -> None:
    artifact = _artifact(floor=np.array((100.0, -300.0, 1.5)))

    assert artifact.floor_shift_enu_m[2] == pytest.approx(-1.25)
    # The unfloored placement is kept beside the floored one, so how far the
    # camera ray and the support mesh disagreed stays readable after the fact.
    assert np.min(artifact.vertices_enu_unfloored_m[:, 2]) == pytest.approx(2.75)
    assert np.min(artifact.vertices_enu_m[:, 2]) == pytest.approx(1.5)
