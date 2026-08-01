from __future__ import annotations

import numpy as np
from PIL import Image
from semantic_twin.pano_geometry import (
    PerspectiveView,
    ProjectionValidity,
    directions_to_equirectangular,
    extract_perspective,
    panorama_to_world_matrix,
    perspective_directions,
    perspective_projection_validity_mask,
    streetview_orientation_prior,
    world_directions_to_equirectangular,
)
from semantic_twin.semantics import material_hints


def test_streetview_orientation_prior_uses_tilt_departure_from_horizon() -> None:
    pitch, roll = streetview_orientation_prior(102.32776, 4.2383833)
    assert np.isclose(pitch, 12.32776)
    assert np.isclose(roll, 4.2383833)


def test_perspective_centre_faces_requested_yaw() -> None:
    view = PerspectiveView("east", 90.0, 0.0, 90.0)
    direction = perspective_directions(view, 1, 1)[0, 0]
    assert np.allclose(direction, [1.0, 0.0, 0.0])
    u, v = directions_to_equirectangular(direction)
    assert np.isclose(u, 0.75)
    assert np.isclose(v, 0.5)


def test_world_panorama_rotation_round_trip() -> None:
    local = np.array([[0.2, 0.9, 0.3], [-0.8, 0.1, -0.2]])
    local /= np.linalg.norm(local, axis=1, keepdims=True)
    rotation = panorama_to_world_matrix(271.0, pitch_deg=3.0, roll_deg=-2.0)
    world = local @ rotation.T
    expected = directions_to_equirectangular(local)
    actual = world_directions_to_equirectangular(world, heading_deg=271.0, pitch_deg=3.0, roll_deg=-2.0)
    assert np.allclose(actual[0], expected[0])
    assert np.allclose(actual[1], expected[1])


def test_extract_perspective_preserves_centre_pixel() -> None:
    panorama = np.zeros((32, 64, 3), dtype=np.uint8)
    panorama[:, :, 0] = np.arange(64, dtype=np.uint8)
    image = extract_perspective(Image.fromarray(panorama), PerspectiveView("front", 0.0, 0.0), width=1, height=1)
    assert abs(int(np.asarray(image)[0, 0, 0]) - 31) <= 1


def test_projection_validity_masks_poles_but_not_horizon() -> None:
    rules = ProjectionValidity(min_elevation_deg=-70.0, max_elevation_deg=70.0)
    horizon = perspective_projection_validity_mask(PerspectiveView("horizon", 0.0, 0.0), 9, 9, validity=rules)
    zenith = perspective_projection_validity_mask(PerspectiveView("zenith", 0.0, 90.0), 9, 9, validity=rules)
    nadir = perspective_projection_validity_mask(PerspectiveView("nadir", 0.0, -90.0), 9, 9, validity=rules)

    assert horizon[4, 4]
    assert not zenith[4, 4]
    assert not nadir[4, 4]


def test_projection_validity_can_exclude_equirectangular_seam() -> None:
    rules = ProjectionValidity(seam_margin_deg=3.0)
    seam = perspective_projection_validity_mask(PerspectiveView("seam", 180.0, 0.0), 5, 5, validity=rules)
    opposite = perspective_projection_validity_mask(PerspectiveView("opposite", 0.0, 0.0), 5, 5, validity=rules)

    assert not seam[2, 2]
    assert opposite[2, 2]


def test_projection_validity_crop_margin_preserves_centre() -> None:
    mask = perspective_projection_validity_mask(
        PerspectiveView("front", 0.0, 0.0),
        10,
        10,
        validity=ProjectionValidity(crop_margin_px=1.0),
    )

    assert not mask[0, 0]
    assert not mask[-1, -1]
    assert mask[5, 5]


def test_projection_validity_rejects_impossible_rules() -> None:
    with np.testing.assert_raises(ValueError):
        ProjectionValidity(min_elevation_deg=80.0, max_elevation_deg=70.0)
    with np.testing.assert_raises(ValueError):
        perspective_projection_validity_mask(
            PerspectiveView("front", 0.0, 0.0),
            4,
            4,
            validity=ProjectionValidity(crop_margin_px=2.0),
        )


def test_entity_and_material_vocabularies_stay_separate() -> None:
    mapping, names = material_hints({0: "Building", 1: "Person", 2: "Sky"})
    assert names[mapping[0]] == "unknown_building"
    assert names[mapping[1]] == "human_tissue"
    assert names[mapping[2]] == "none"
