from __future__ import annotations

import numpy as np
from PIL import Image
from semantic_twin.pano_geometry import (
    PerspectiveView,
    ProjectionValidity,
    decoded_panorama,
    directions_to_equirectangular,
    extract_perspective,
    panorama_to_world_matrix,
    perspective_direction_at,
    perspective_directions,
    perspective_projection_validity_mask,
    streetview_orientation_prior,
    view_basis,
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


def test_pixel_centre_direction_matches_the_grid_it_is_derived_from() -> None:
    # raycast_mesh_depth.py and project_pixel_semantics.py sample rays at
    # arbitrary sub-pixel coordinates, while the segmentation crops come from
    # perspective_directions. If the two ever disagree the depth maps and the
    # imagery desynchronise silently, so bind them here.
    view = PerspectiveView("h+45_037", 37.0, 45.0, 90.0)
    grid = perspective_directions(view, 16, 12)
    for row in range(12):
        for column in range(16):
            at = perspective_direction_at(view, column + 0.5, row + 0.5, 16, 12)
            assert np.allclose(grid[row, column], at, atol=1e-12)


def test_pixel_corner_directions_span_the_requested_field_of_view() -> None:
    view = PerspectiveView("front", 0.0, 0.0, 90.0)
    left = perspective_direction_at(view, 0.0, 512.0, 1024, 1024)
    right = perspective_direction_at(view, 1024.0, 512.0, 1024, 1024)
    assert np.isclose(np.degrees(np.arccos(np.clip(left @ right, -1.0, 1.0))), 90.0)


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


def test_perspective_directions_match_the_dense_grid_construction_exactly() -> None:
    # The grid is built from two separable broadcasts instead of a meshgrid and
    # two full (height, width, 3) products, which is only worth doing if it
    # cannot move a ray. Bind it to the dense form, bit for bit.
    for view in (PerspectiveView("h-45_135", 135.0, -45.0, 90.0), PerspectiveView("nadir", 0.0, -90.0, 100.0)):
        width, height = 37, 21
        right, forward, up = view_basis(view.yaw_deg, view.pitch_deg)
        tangent_x = np.tan(np.radians(view.fov_deg) / 2.0)
        tangent_y = tangent_x / (width / height)
        x = ((np.arange(width) + 0.5) / width * 2.0 - 1.0) * tangent_x
        y = (1.0 - (np.arange(height) + 0.5) / height * 2.0) * tangent_y
        xx, yy = np.meshgrid(x, y)
        dense = forward[None, None, :] + xx[:, :, None] * right[None, None, :] + yy[:, :, None] * up[None, None, :]
        dense = dense / np.linalg.norm(dense, axis=2, keepdims=True)

        np.testing.assert_array_equal(perspective_directions(view, width, height), dense)


def test_decoded_panorama_reuses_one_decode_and_notices_a_different_image() -> None:
    first = Image.fromarray(np.random.default_rng(0).integers(0, 256, (8, 16, 3), dtype=np.uint8), "RGB")
    second = Image.fromarray(np.random.default_rng(1).integers(0, 256, (8, 16, 3), dtype=np.uint8), "RGB")

    decoded = decoded_panorama(first)
    np.testing.assert_array_equal(decoded, np.asarray(first.convert("RGB")))
    assert decoded_panorama(first) is decoded
    np.testing.assert_array_equal(decoded_panorama(second), np.asarray(second.convert("RGB")))
    assert decoded_panorama(first) is not decoded


def test_decoded_panorama_converts_an_image_that_is_not_already_rgb() -> None:
    grey = Image.fromarray(np.arange(64, dtype=np.uint8).reshape(8, 8), "L")
    np.testing.assert_array_equal(decoded_panorama(grey), np.asarray(grey.convert("RGB")))


def test_extract_perspective_does_not_depend_on_a_previous_call() -> None:
    rng = np.random.default_rng(4)
    first = Image.fromarray(rng.integers(0, 256, (32, 64, 3), dtype=np.uint8), "RGB")
    second = Image.fromarray(rng.integers(0, 256, (32, 64, 3), dtype=np.uint8), "RGB")
    view = PerspectiveView("front", 20.0, 10.0, 90.0)

    alone = np.asarray(extract_perspective(second, view, width=16, height=16))
    extract_perspective(first, view, width=16, height=16)
    after = np.asarray(extract_perspective(second, view, width=16, height=16))

    np.testing.assert_array_equal(alone, after)
