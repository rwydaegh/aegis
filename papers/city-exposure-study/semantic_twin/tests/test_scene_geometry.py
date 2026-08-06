"""The geometry floor: frames, planar arithmetic, the ground and the cut's inverse.

These pin the seams that the ``semantic_twin.scene`` split created or exposed.
Nothing here needs a mesh on disk, so all of it runs in CI.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin import pano_geometry
from semantic_twin.scene import camera_ground, enu, planar
from semantic_twin.scene.fishnet import build_fishnet, build_region_map, paintability
from semantic_twin.scene.pinhole import CameraPose, PinholeView, view_to_world, world_to_view


# ---------------------------------------------------------------- the frames


@pytest.mark.parametrize("pitch", [0.0, 45.0, -45.0, 89.5, -89.5, 13.7])
def test_the_cutter_and_the_panorama_sampler_build_one_set_of_crop_axes(pitch: float) -> None:
    # The mesh cutter and the panorama sampler each used to carry their own
    # copy of this. They were bit identical, so one was deleted. If a future
    # edit reintroduces a second convention the cut pieces and the pixels they
    # were cut from desynchronise silently, which is what this refuses.
    for yaw in np.linspace(-540.0, 540.0, 97):
        crop = PinholeView(yaw_deg=float(yaw), pitch_deg=pitch)
        camera = world_to_view(np.eye(3), CameraPose(np.zeros(3), np.eye(3)), crop)
        right, forward, up = pano_geometry.view_basis(float(yaw), pitch)
        np.testing.assert_array_equal(camera, np.stack([right, up, forward]).T)


def test_crop_axes_are_right_handed_and_never_rolled() -> None:
    for yaw in (0.0, 90.0, 217.4, -33.0):
        for pitch in (0.0, 60.0, -60.0):
            right, forward, up = pano_geometry.view_basis(yaw, pitch)
            assert np.allclose([right @ right, forward @ forward, up @ up], 1.0)
            assert np.allclose([right @ forward, right @ up, forward @ up], 0.0, atol=1e-15)
            assert np.allclose(np.cross(forward, up), right, atol=1e-15)
            # A crop is never rolled about its own axis, which is what lets an
            # image column stand for one azimuth at any pitch.
            assert right[2] == 0.0


def test_an_enu_frame_round_trips_a_point_to_the_millimetre() -> None:
    rng = np.random.default_rng(11)
    for lat, lon, height in zip(
        rng.uniform(-84.0, 84.0, 40), rng.uniform(-180.0, 180.0, 40), rng.uniform(-400.0, 4000.0, 40), strict=True
    ):
        frame = enu.EnuFrame(float(lat), float(lon), float(height))
        np.testing.assert_allclose(frame.to_enu(float(lat), float(lon), float(height)), np.zeros(3), atol=1e-6)
        for offset in ([300.0, -120.0, 25.0], [-4000.0, 4000.0, -90.0], [0.0, 0.0, 0.0]):
            back = frame.to_llh(np.asarray(offset))
            np.testing.assert_allclose(frame.to_enu(*back), offset, atol=1e-3)


def test_the_enu_axes_point_east_north_and_up() -> None:
    frame = enu.EnuFrame(51.0543, 3.7174)  # Korenmarkt
    east = frame.to_enu(51.0543, 3.7174 + 1e-4)
    north = frame.to_enu(51.0543 + 1e-4, 3.7174)
    up = frame.to_enu(51.0543, 3.7174, 25.0)
    assert east[0] > 0.0 and abs(east[1]) < 1e-3 and abs(east[2]) < 1e-3
    assert north[1] > 0.0 and abs(north[0]) < 1e-3 and abs(north[2]) < 1e-3
    np.testing.assert_allclose(up, [0.0, 0.0, 25.0], atol=1e-6)


# ------------------------------------------------------- the image plane


def test_signed_area_flips_with_the_winding_and_matches_the_shoelace() -> None:
    square = np.array([[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]])
    assert planar.signed_area(square) == pytest.approx(12.0)
    assert planar.signed_area(square[::-1]) == pytest.approx(-12.0)
    # Winding is not a formality here: rasterize_convex reads the sign to decide
    # which side of each edge is inside, so a reversed polygon must still
    # rasterise to the same pixels.
    forward = planar.rasterize_convex(square * 4.0, 32, 32)
    reversed_ = planar.rasterize_convex(square[::-1] * 4.0, 32, 32)
    np.testing.assert_array_equal(np.sort(forward[0]), np.sort(reversed_[0]))


def test_clipping_to_the_crop_keeps_the_part_inside_and_nothing_else() -> None:
    inside = np.array([[2.0, 2.0], [30.0, 2.0], [30.0, 20.0], [2.0, 20.0]])
    np.testing.assert_array_equal(planar.clip_to_rect(inside, 64, 48), inside)

    straddling = np.array([[-10.0, -10.0], [30.0, -10.0], [30.0, 20.0], [-10.0, 20.0]])
    clipped = planar.clip_to_rect(straddling, 64, 48)
    assert abs(planar.signed_area(clipped)) == pytest.approx(30.0 * 20.0)
    assert clipped[:, 0].min() >= 0.0 and clipped[:, 1].min() >= 0.0

    outside = np.array([[100.0, 100.0], [120.0, 100.0], [120.0, 120.0]])
    assert len(planar.clip_to_rect(outside, 64, 48)) == 0


def test_two_halves_of_a_square_claim_every_pixel_once() -> None:
    # The fishnet is only a partition if neighbouring pieces neither overlap nor
    # leave a gap. That property lives in the pixel-centre rule, so pin it here
    # rather than through a whole cut.
    square = np.array([[1.0, 1.0], [25.0, 1.0], [25.0, 19.0], [1.0, 19.0]])
    left = np.array([[1.0, 1.0], [13.0, 1.0], [13.0, 19.0], [1.0, 19.0]])
    right = np.array([[13.0, 1.0], [25.0, 1.0], [25.0, 19.0], [13.0, 19.0]])

    def flat(polygon: np.ndarray) -> set[int]:
        rows, columns = planar.rasterize_convex(polygon, 32, 32)
        return {int(r) * 32 + int(c) for r, c in zip(rows, columns, strict=True)}

    whole, a, b = flat(square), flat(left), flat(right)
    assert a & b == set()
    assert a | b == whole
    assert len(whole) == pytest.approx(abs(planar.signed_area(square)), rel=0.1)


def test_the_near_plane_clip_leaves_the_crossing_vertex_on_the_plane() -> None:
    triangle = np.array([[0.0, 0.0, -3.0], [1.0, 0.0, 5.0], [0.0, 1.0, 5.0]])
    kept = planar.clip_near_plane(triangle, 0.05)
    assert len(kept) == 4
    assert kept[:, 2].min() == pytest.approx(0.05, abs=1e-15)
    assert np.all(kept[:, 2] >= 0.05 - 1e-15)
    assert len(planar.clip_near_plane(triangle - np.array([0.0, 0.0, 20.0]), 0.05)) == 0


def test_the_solid_angle_of_eight_octants_is_the_whole_sphere() -> None:
    corners = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    octants = np.array([corners * (2.0 * np.array(sign) - 1.0) for sign in np.ndindex(2, 2, 2)])
    total = planar.triangle_solid_angle(octants)
    assert np.allclose(total, np.pi / 2.0)
    assert total.sum() == pytest.approx(4.0 * np.pi)


# ----------------------------------------------------------------- the ground


def _ramp(gradient: float, half: float = 6.0) -> tuple[np.ndarray, np.ndarray]:
    """A pavement sloping in +x, so the patch median has something to be wrong about."""
    vertices = np.array(
        [
            [-half, -half, 10.0 - gradient * half],
            [half, -half, 10.0 + gradient * half],
            [half, half, 10.0 + gradient * half],
            [-half, half, 10.0 - gradient * half],
        ]
    )
    return vertices, np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)


def test_the_ground_under_a_camera_lies_on_the_surface_it_claims_to_measure() -> None:
    vertices, faces = _ramp(0.2)
    sample = camera_ground.ground_elevation(vertices, faces, 1.0, -0.5, ceiling_z_m=30.0, patch_m=3.0)
    lowest = 10.0 + 0.2 * (1.0 - 1.5)
    highest = 10.0 + 0.2 * (1.0 + 1.5)
    assert lowest <= sample.elevation_m <= highest
    assert sample.elevation_m == pytest.approx(10.0 + 0.2 * 1.0)
    assert sample.peak_to_peak_m == pytest.approx(highest - lowest)
    assert sample.n_hits == sample.n_samples == 25


def test_a_flat_pavement_reports_no_spread_and_a_ramp_reports_its_own() -> None:
    flat_sample = camera_ground.ground_elevation(*_ramp(0.0), 0.0, 0.0, ceiling_z_m=30.0, patch_m=4.0)
    assert flat_sample.spread_m < 1e-12
    assert flat_sample.peak_to_peak_m < 1e-12
    steep = camera_ground.ground_elevation(*_ramp(0.5), 0.0, 0.0, ceiling_z_m=30.0, patch_m=4.0)
    assert steep.peak_to_peak_m == pytest.approx(2.0)
    assert steep.spread_m > 0.5


# -------------------------------------------------------------------- the cut


def _tilted_wall(pose: CameraPose, tilt_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """A wall leaning back by ``tilt_deg``, so its plane is not axis aligned."""
    tilt = np.radians(tilt_deg)
    lean = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(tilt), -np.sin(tilt)], [0.0, np.sin(tilt), np.cos(tilt)]])
    corners = np.array([[-9.0, 7.0, -9.0], [9.0, 7.0, -9.0], [9.0, 7.0, 9.0], [-9.0, 7.0, 9.0]]) @ lean.T
    return pose.position + corners @ pose.rotation.T, np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)


def _cut_a_striped_wall(size: int = 48, tilt_deg: float = 20.0):
    pose = CameraPose(np.array([1.0, -2.0, 1.5]), np.eye(3))
    view = PinholeView(yaw_deg=0.0, width=size, height=size)
    vertices, faces = _tilted_wall(pose, tilt_deg)

    directions = pano_geometry.perspective_directions(
        pano_geometry.PerspectiveView("t", view.yaw_deg, view.pitch_deg, view.fov_deg), size, size
    ).reshape(-1, 3)
    plane_normal = np.cross(vertices[1] - vertices[0], vertices[2] - vertices[0])
    plane_normal /= np.linalg.norm(plane_normal)
    denominator = directions @ plane_normal
    distance = ((vertices[0] - pose.position) @ plane_normal) / denominator
    range_m = np.where(distance > 0.0, distance, np.nan).reshape(size, size)
    face_ids = np.where(np.isfinite(range_m), 0, -1).astype(np.int64)

    labels = np.zeros((size, size), dtype=np.int64)
    labels[:, size // 2 :] = 1
    labels[: size // 4, :] = 2
    confidence = np.full((size, size), 0.9)
    reason = paintability(labels, confidence, range_m)
    regions = build_region_map(labels, reason, range_m, min_region_pixels=4)
    surface = build_fishnet(
        vertices, faces, face_ids, regions, pose, view, confidence=confidence, min_piece_area_px=0.0
    )
    return surface, vertices, faces, pose, view


def test_every_cut_piece_lands_back_on_its_source_triangle_plane() -> None:
    # The cut is legitimate only because the map from a triangle to its image is
    # projective and exactly invertible inside one crop. If a piece came back
    # off the plane, the surface would sit at the wrong range and the whole
    # approach would be a resampling rather than a partition.
    surface, vertices, faces, _pose, _view = _cut_a_striped_wall()
    assert surface.triangle_count > 3

    corners = vertices[faces[0]]
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    normal /= np.linalg.norm(normal)
    offset = (surface.vertices - corners[0]) @ normal
    assert np.abs(offset).max() < 1e-9


def test_a_cut_wall_keeps_its_metric_area_and_its_classes() -> None:
    surface, _vertices, _faces, pose, view = _cut_a_striped_wall()
    report = surface.report
    assert report["cut_source_triangles"] >= 1.0
    assert report["emitted_area_px"] + report["rejected_area_px"] == pytest.approx(report["clipped_source_area_px"])
    assert set(np.unique(surface.face_class)) == {0, 1, 2}

    # Every face points back at the camera it was seen from, by construction.
    toward = pose.position - surface.face_centroid
    toward /= np.linalg.norm(toward, axis=1, keepdims=True)
    assert np.einsum("ij,ij->i", surface.face_normal, toward).min() > 0.0

    # And every face is inside the crop it was cut in.
    assert surface.face_image[:, :, 0].min() >= -1e-9
    assert surface.face_image[:, :, 0].max() <= view.width + 1e-9
    assert surface.face_image[:, :, 1].min() >= -1e-9
    assert surface.face_image[:, :, 1].max() <= view.height + 1e-9


def test_a_world_point_survives_the_camera_and_comes_back() -> None:
    rng = np.random.default_rng(5)
    angle = np.radians(41.0)
    rotation = np.array([[np.cos(angle), np.sin(angle), 0.0], [-np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    pose = CameraPose(np.array([12.0, -4.0, 1.6]), rotation)
    for yaw, pitch in ((0.0, 0.0), (215.0, 30.0), (-88.0, -60.0)):
        view = PinholeView(yaw_deg=yaw, pitch_deg=pitch, width=800, height=600)
        world = rng.normal(size=(200, 3)) * 40.0
        np.testing.assert_allclose(view_to_world(world_to_view(world, pose, view), pose, view), world, atol=1e-11)
