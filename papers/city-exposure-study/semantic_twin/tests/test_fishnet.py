from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from semantic_twin.pano_geometry import PerspectiveView, perspective_directions
from semantic_twin.scene.fishnet import (
    PAINT_REASONS,
    REJECTION_REASONS,
    aggregate_occlusion_budget,
    angular_tolerance_deg,
    boundary_chains,
    build_fishnet,
    build_region_map,
    class_fidelity,
    load_fishnet,
    occlusion_budget,
    occlusion_fidelity,
    paintability,
    rasterize_fishnet,
    save_fishnet,
)
from semantic_twin.scene.pinhole import (
    CameraPose,
    PinholeView,
    image_to_view_directions,
    view_to_image,
    view_to_world,
    world_to_view,
)
from semantic_twin.scene.planar import triangle_solid_angle

WALL_DISTANCE_M = 6.0
WALL_HALF_M = 12.0


def _view(size: int = 64, yaw: float = 0.0) -> PinholeView:
    return PinholeView(yaw_deg=yaw, width=size, height=size)


def _pose(yaw_offset_deg: float = 0.0) -> CameraPose:
    angle = np.radians(yaw_offset_deg)
    rotation = np.array(
        [
            [np.cos(angle), np.sin(angle), 0.0],
            [-np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    return CameraPose(np.array([1.0, -2.0, 1.5]), rotation)


def _quad(distance: float, half: float, pose: CameraPose) -> np.ndarray:
    """A wall square facing the camera along its forward axis, in world metres."""
    corners = np.array(
        [
            [-half, distance, -half],
            [half, distance, -half],
            [half, distance, half],
            [-half, distance, half],
        ]
    )
    return pose.position + corners @ pose.rotation.T


def _first_hit(vertices: np.ndarray, faces: np.ndarray, pose: CameraPose, view: PinholeView):
    """Reference ray cast built on the pipeline's own direction model.

    Using ``pano_geometry.perspective_directions`` rather than the fishnet
    projection keeps the visibility inputs independent of the code under test,
    and cross-checks that the two share one camera convention.
    """
    local = perspective_directions(PerspectiveView("t", view.yaw_deg, view.pitch_deg, view.fov_deg), *view.shape[::-1])
    directions = local.reshape(-1, 3) @ pose.rotation.T
    best = np.full(len(directions), np.inf)
    hit = np.full(len(directions), -1, dtype=np.int64)
    for index, face in enumerate(faces):
        a, b, c = vertices[face]
        edge_1, edge_2 = b - a, c - a
        pvec = np.cross(directions, edge_2)
        determinant = pvec @ edge_1
        usable = np.abs(determinant) > 1e-12
        tvec = pose.position - a
        u = np.where(usable, (pvec @ tvec) / np.where(usable, determinant, 1.0), -1.0)
        qvec = np.cross(tvec, edge_1)
        v = np.where(usable, directions @ qvec / np.where(usable, determinant, 1.0), -1.0)
        t = np.where(usable, (qvec @ edge_2) / np.where(usable, determinant, 1.0), -1.0)
        inside = usable & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1.0 + 1e-9) & (t > 1e-9) & (t < best)
        best = np.where(inside, t, best)
        hit = np.where(inside, index, hit)
    range_m = np.where(np.isfinite(best), best, np.nan).reshape(view.shape)
    return range_m, hit.reshape(view.shape)


def _scene(labels: np.ndarray, *, view: PinholeView, pose: CameraPose, extra: tuple | None = None):
    """Wall split into two triangles, optionally with a nearer occluder."""
    wall = _quad(WALL_DISTANCE_M, WALL_HALF_M, pose)
    vertices = list(wall)
    faces = [[0, 1, 2], [0, 2, 3]]
    if extra is not None:
        offset = len(vertices)
        vertices.extend(extra[0])
        faces.extend((np.asarray(extra[1]) + offset).tolist())
    vertices = np.asarray(vertices)
    faces = np.asarray(faces, dtype=np.int64)
    range_m, face_ids = _first_hit(vertices, faces, pose, view)
    confidence = np.full(view.shape, 0.8)
    return vertices, faces, range_m, face_ids, confidence, labels


def _build(labels, *, view=None, pose=None, extra=None, decision=None, transient=None, **kwargs):
    view = view or _view()
    pose = pose or _pose()
    vertices, faces, range_m, face_ids, confidence, labels = _scene(labels, view=view, pose=pose, extra=extra)
    reason = paintability(labels, confidence, range_m, transient_class_ids=transient, decision=decision)
    regions = build_region_map(labels, reason, range_m, min_region_pixels=kwargs.pop("min_region_pixels", 4))
    surface = build_fishnet(
        vertices, faces, face_ids, regions, pose, view, confidence=confidence, min_piece_area_px=0.0, **kwargs
    )
    return surface, regions, face_ids, view, pose


def test_projection_and_its_inverse_agree_with_the_shared_camera_model() -> None:
    view = _view(size=32, yaw=125.0)
    pose = _pose(37.0)
    camera_space = np.array([[-2.0, 1.0, 9.0], [3.0, -1.5, 4.0], [0.5, 2.5, 12.0], [0.0, 0.0, 1.0]])
    world = view_to_world(camera_space, pose, view)
    assert np.allclose(world_to_view(world, pose, view), camera_space, atol=1e-12)

    pixels = view_to_image(camera_space, view)
    directions = image_to_view_directions(pixels, view)
    recovered = view_to_world(directions * (camera_space[:, 2] / directions[:, 2])[:, None], pose, view)
    assert np.allclose(recovered, world, atol=1e-9)

    reference = perspective_directions(PerspectiveView("t", view.yaw_deg, view.pitch_deg, view.fov_deg), 32, 32)
    corner = view_to_world(image_to_view_directions(np.array([[7.5, 21.5]]), view), pose, view) - pose.position
    corner /= np.linalg.norm(corner)
    assert np.allclose(corner[0], reference[21, 7] @ pose.rotation.T, atol=1e-12)


def test_uniform_wall_conserves_image_area_and_metric_area() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    surface, _regions, _face_ids, _view, _camera = _build(labels)

    report = surface.report
    assert report["emitted_area_px"] + report["rejected_area_px"] == pytest.approx(report["clipped_source_area_px"])
    assert report["rejected_area_px"] == pytest.approx(0.0)
    expected_area = (2.0 * WALL_DISTANCE_M) ** 2
    assert surface.face_area_m2.sum() == pytest.approx(expected_area, rel=1e-9)
    assert surface.face_solid_angle_sr.sum() == pytest.approx(4.0 * np.arcsin(0.5), rel=1e-9)


def test_every_emitted_triangle_is_non_degenerate_and_faces_the_camera() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[10:30, 8:52] = 1
    labels[40:60, 20:44] = 2
    surface, _regions, _face_ids, _view, camera = _build(labels)

    assert surface.triangle_count > 0
    assert np.all(surface.face_area_m2 > 1e-12)
    assert np.all(np.isfinite(surface.vertices))
    corners = surface.vertices[surface.faces]
    image = surface.face_image
    signed = 0.5 * (
        (image[:, 1, 0] - image[:, 0, 0]) * (image[:, 2, 1] - image[:, 0, 1])
        - (image[:, 2, 0] - image[:, 0, 0]) * (image[:, 1, 1] - image[:, 0, 1])
    )
    assert np.all(np.abs(signed) > 1e-9)
    assert np.all(np.abs(np.sign(signed) - np.sign(signed[0])) < 1e-12)
    toward_camera = camera.position - corners.mean(axis=1)
    assert np.all(np.einsum("ij,ij->i", surface.face_normal, toward_camera) > 0.0)
    assert np.allclose(np.linalg.norm(surface.face_normal, axis=1), 1.0)


def test_class_boundaries_survive_the_round_trip_without_leaking() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[16:48, 16:48] = 1
    surface, regions, face_ids, view, _camera = _build(labels)

    fidelity = class_fidelity(rasterize_fishnet(surface, view.shape), regions)
    assert fidelity["coverage"] == pytest.approx(1.0)
    assert fidelity["changed_pixels"] == 0
    assert fidelity["leaked_pixels"] == 0
    occlusion = occlusion_fidelity(rasterize_fishnet(surface, view.shape), face_ids, regions)
    assert occlusion["deleted_pixels"] == 0


def test_an_island_with_a_hole_keeps_both_classes_and_no_triangle_spans_them() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[12:52, 12:52] = 1
    labels[24:40, 24:40] = 2
    surface, regions, _face_ids, view, _camera = _build(labels)

    assert set(np.unique(surface.face_class)) == {0, 1, 2}
    raster = rasterize_fishnet(surface, view.shape)
    assert class_fidelity(raster, regions)["changed_pixels"] == 0
    # The ring class must not be triangulated across its hole.
    ring = surface.face_image[surface.face_class == 1]
    centres = ring.mean(axis=1)
    assert not np.any((centres > 25.0).all(axis=1) & (centres < 39.0).all(axis=1))


def test_two_disjoint_islands_of_one_class_stay_separate_pieces() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[8:24, 8:24] = 1
    labels[40:56, 40:56] = 1
    surface, regions, _face_ids, view, _camera = _build(labels)

    assert regions.region_count == 3
    assert class_fidelity(rasterize_fishnet(surface, view.shape), regions)["changed_pixels"] == 0
    marked = surface.face_image[surface.face_class == 1].mean(axis=1)
    assert marked[:, 0].min() < 24.0 and marked[:, 0].max() > 40.0
    assert not np.any((marked[:, 0] > 25.0) & (marked[:, 0] < 39.0))


def test_geometry_hidden_behind_a_nearer_support_triangle_is_rejected_not_painted() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    view, camera = _view(), _pose()
    blocker = _quad(2.5, 0.8, camera)
    surface, regions, face_ids, view, _camera = _build(
        labels, view=view, pose=camera, extra=(blocker, [[0, 1, 2], [0, 2, 3]])
    )

    hidden = np.count_nonzero(surface.rejected_reason == REJECTION_REASONS["occluded_by_support_mesh"])
    assert hidden > 0
    raster = rasterize_fishnet(surface, view.shape)
    occlusion = occlusion_fidelity(raster, face_ids, regions)
    assert occlusion["phantom_pixels"] == 0
    # The wall behind must not be painted over the blocker's footprint.
    wall_faces = np.isin(surface.face_source_triangle, (0, 1))
    assert np.all(surface.face_visible_fraction[wall_faces] > 0.0)
    blocked = face_ids == 2
    assert np.all(raster.source_triangle[blocked] >= 2)


def test_a_person_is_never_painted_onto_the_wall_behind_them() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[20:44, 20:44] = 7
    surface, regions, _face_ids, view, _camera = _build(labels, transient={7})

    assert np.all(regions.paint_reason[20:44, 20:44] == PAINT_REASONS["transient_object"])
    raster = rasterize_fishnet(surface, view.shape)
    assert np.all(raster.class_map[24:40, 24:40] == -1)
    assert 7 not in set(np.unique(surface.face_class))
    assert np.count_nonzero(surface.rejected_reason == REJECTION_REASONS["transient_object"]) > 0
    assert np.count_nonzero(surface.rejected_reason == REJECTION_REASONS["clutter_in_front"]) == 0


def test_rejected_cells_keep_their_own_geometry_instead_of_the_whole_source_face() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[20:44, 20:44] = 7
    surface, _regions, _face_ids, _view, _camera = _build(labels, transient={7})

    records = np.flatnonzero(surface.rejected_reason == REJECTION_REASONS["transient_object"])
    face_mask = np.isin(surface.rejected_face_record, records)
    assert records.size > 0
    assert face_mask.any()
    assert np.all(surface.rejected_geometry_kind[records] == 1)

    image = surface.rejected_face_image[face_mask]
    twice_area = np.abs(
        (image[:, 1, 0] - image[:, 0, 0]) * (image[:, 2, 1] - image[:, 0, 1])
        - (image[:, 2, 0] - image[:, 0, 0]) * (image[:, 1, 1] - image[:, 0, 1])
    )
    assert 0.5 * twice_area.sum() == pytest.approx(surface.rejected_image_area_px[records].sum())

    rejected_world = surface.rejected_vertices[surface.rejected_faces[face_mask]]
    rejected_area = 0.5 * np.linalg.norm(
        np.cross(rejected_world[:, 1] - rejected_world[:, 0], rejected_world[:, 2] - rejected_world[:, 0]),
        axis=1,
    )
    source_world = _quad(WALL_DISTANCE_M, WALL_HALF_M, _pose())[[0, 1, 2]]
    source_area = 0.5 * np.linalg.norm(np.cross(source_world[1] - source_world[0], source_world[2] - source_world[0]))
    assert rejected_area.max() < 0.25 * source_area

    projected = view_to_image(world_to_view(rejected_world.reshape(-1, 3), _camera, _view), _view).reshape(-1, 3, 2)
    assert np.allclose(projected, image, atol=1e-9)


def test_a_whole_refused_footprint_is_stored_as_its_clipped_geometry() -> None:
    labels = np.full((64, 64), 7, dtype=np.int64)
    surface, _regions, _face_ids, _view, _camera = _build(labels, transient={7})

    records = np.flatnonzero(surface.rejected_reason == REJECTION_REASONS["transient_object"])
    assert records.size == 2
    assert 2 in surface.rejected_geometry_kind[records]
    assert surface.rejected_face_offsets[-1] == surface.rejected_faces.shape[0]
    assert surface.rejected_face_offsets.shape == (surface.rejected_reason.size + 1,)

    clipped = records[surface.rejected_geometry_kind[records] == 2]
    faces = np.isin(surface.rejected_face_record, clipped)
    image = surface.rejected_face_image[faces]
    assert image.min() >= 0.0
    assert image.max() <= 64.0
    area = 0.5 * np.abs(
        (image[:, 1, 0] - image[:, 0, 0]) * (image[:, 2, 1] - image[:, 0, 1])
        - (image[:, 2, 0] - image[:, 0, 0]) * (image[:, 1, 1] - image[:, 0, 1])
    )
    assert area.sum() == pytest.approx(surface.rejected_image_area_px[clipped].sum())


@pytest.mark.parametrize(
    "face_record",
    (
        np.array([0, 1, 0, 1], dtype=np.int64),
        np.array([1, 1, 0, 0], dtype=np.int64),
    ),
    ids=("interleaved", "misordered"),
)
def test_rejected_geometry_csr_requires_faces_in_record_order(face_record: np.ndarray) -> None:
    labels = np.full((64, 64), 7, dtype=np.int64)
    surface = _build(labels, transient={7})[0]
    expanded = replace(
        surface,
        rejected_faces=np.repeat(surface.rejected_faces, 2, axis=0),
        rejected_face_image=np.repeat(surface.rejected_face_image, 2, axis=0),
        rejected_face_record=np.repeat(surface.rejected_face_record, 2),
        rejected_face_offsets=np.array([0, 2, 4], dtype=np.int64),
    )
    assert np.array_equal(expanded.rejected_face_record, np.array([0, 0, 1, 1]))

    with pytest.raises(ValueError, match="must follow rejected_face_offsets record order"):
        replace(expanded, rejected_face_record=face_record)


def test_rejected_geometry_csr_rejects_inconsistent_offsets_and_geometry() -> None:
    labels = np.full((64, 64), 7, dtype=np.int64)
    surface = _build(labels, transient={7})[0]

    with pytest.raises(ValueError, match="must start at zero"):
        replace(surface, rejected_face_offsets=np.array([1, 1, 2], dtype=np.int64))
    with pytest.raises(ValueError, match="must be nondecreasing"):
        replace(surface, rejected_face_offsets=np.array([0, 2, 1], dtype=np.int64))
    with pytest.raises(ValueError, match="must end at the rejected face count"):
        replace(surface, rejected_face_offsets=np.array([0, 0, 1], dtype=np.int64))
    with pytest.raises(ValueError, match="unavailable rejected geometry records must not own faces"):
        replace(surface, rejected_geometry_kind=np.zeros(2, dtype=np.uint8))
    with pytest.raises(ValueError, match="exact rejected geometry records must own at least one face"):
        replace(
            surface,
            rejected_face_record=np.ones(2, dtype=np.int64),
            rejected_face_offsets=np.array([0, 0, 2], dtype=np.int64),
        )
    with pytest.raises(ValueError, match=r"rejected_face_image must have shape \(n_faces, 3, 2\)"):
        replace(surface, rejected_face_image=surface.rejected_face_image[:1])
    invalid_image = surface.rejected_face_image.copy()
    invalid_image[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="rejected_face_image must contain finite numbers"):
        replace(surface, rejected_face_image=invalid_image)


def test_distance_evidence_rejects_clutter_and_stays_distinct_from_a_transient() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    decision = np.ones((64, 64), dtype=np.uint8)
    decision[20:44, 20:44] = 3
    surface, regions, _face_ids, view, _camera = _build(labels, decision=decision)

    assert np.all(regions.paint_reason[20:44, 20:44] == PAINT_REASONS["clutter_in_front"])
    assert np.all(rasterize_fishnet(surface, view.shape).class_map[24:40, 24:40] == -1)
    assert np.count_nonzero(surface.rejected_reason == REJECTION_REASONS["clutter_in_front"]) > 0
    assert np.count_nonzero(surface.rejected_reason == REJECTION_REASONS["transient_object"]) == 0


def test_a_registration_conflict_is_not_reported_as_clutter_in_front() -> None:
    # Decision 4 is the depth fusion saying the tile first hit is implausibly
    # near, which is a conflict about where the surface is rather than evidence
    # of an object standing in front of it. Both withhold the pixel, but only
    # one of them means a scatterer was observed.
    labels = np.zeros((64, 64), dtype=np.int64)
    decision = np.ones((64, 64), dtype=np.uint8)
    decision[20:44, 20:44] = 4
    surface, regions, _face_ids, view, _camera = _build(labels, decision=decision)

    assert np.all(regions.paint_reason[20:44, 20:44] == PAINT_REASONS["mesh_or_pose_conflict"])
    assert np.all(rasterize_fishnet(surface, view.shape).class_map[24:40, 24:40] == -1)
    assert np.count_nonzero(surface.rejected_reason == REJECTION_REASONS["mesh_or_pose_conflict"]) > 0
    assert np.count_nonzero(surface.rejected_reason == REJECTION_REASONS["clutter_in_front"]) == 0


def test_a_withheld_distance_test_leaves_the_pixel_to_the_mesh_and_the_class() -> None:
    # no_depth_evidence is what the fusion emits when the range fit is not
    # plausible. It must withhold nothing on its own, while the class test that
    # never depended on a fitted scale keeps working.
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[20:44, 20:44] = 7
    decision = np.full((64, 64), 6, dtype=np.uint8)
    surface, regions, _face_ids, _view, _camera = _build(labels, decision=decision, transient={7})

    assert np.all(regions.paint_reason[:20] == PAINT_REASONS["paintable"])
    assert np.all(regions.paint_reason[20:44, 20:44] == PAINT_REASONS["transient_object"])
    assert not np.any(regions.paint_reason == PAINT_REASONS["clutter_in_front"])
    assert surface.triangle_count > 0


def test_the_occlusion_budget_adds_the_rejected_cells_to_the_within_cell_shortfall() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    view, camera = _view(), _pose()
    blocker = _quad(2.5, 0.8, camera)
    surface = _build(labels, view=view, pose=camera, extra=(blocker, [[0, 1, 2], [0, 2, 3]]))[0]

    budget = occlusion_budget(surface)

    assert budget["within_cell_fraction"] > 0.0
    assert budget["absent_surface_fraction"] > 0.0
    assert budget["occlusion_budget_fraction"] == pytest.approx(
        budget["within_cell_fraction"] + budget["absent_surface_fraction"] + budget["deferred_surface_fraction"]
    )
    # Reading the within-cell term alone would understate what occlusion
    # removed, because a piece owning less than the threshold never reaches the
    # accepted table at all.
    assert budget["occlusion_budget_fraction"] > budget["within_cell_fraction"]
    assert budget["piece_visibility_fraction"] == 0.5
    assert budget["by_reason_fraction"]["occluded_by_support_mesh"] > 0.0
    assert budget["solid_angle_weighted_visible_fraction"] < 1.0


def test_a_site_budget_weighs_crops_by_projected_area_not_by_crop_count() -> None:
    small = {
        "projected_source_area_px": 100.0,
        "within_cell_px": 1.0,
        "absent_surface_px": 0.0,
        "deferred_surface_px": 0.0,
        "by_reason_fraction": {"transient_object": 0.0},
        "piece_visibility_fraction": 0.5,
    }
    large = {
        "projected_source_area_px": 9900.0,
        "within_cell_px": 0.0,
        "absent_surface_px": 99.0,
        "deferred_surface_px": 0.0,
        "by_reason_fraction": {"transient_object": 0.01},
        "piece_visibility_fraction": 0.5,
    }

    site = aggregate_occlusion_budget([small, large])

    assert site["views"] == 2
    assert site["projected_source_area_px"] == 10000.0
    assert site["occlusion_budget_fraction"] == pytest.approx(0.01)
    # Averaging the two crop fractions would give 0.5 percent from the small
    # crop plus 0.5 percent from the large one, which is not what the site is.
    assert site["within_cell_fraction"] == pytest.approx(0.0001)
    assert site["by_reason_fraction"]["transient_object"] == pytest.approx(0.0099)


def test_broken_support_geometry_is_reported_rather_than_crashing() -> None:
    view, pose = _view(), _pose()
    wall = _quad(WALL_DISTANCE_M, WALL_HALF_M, pose)
    behind = pose.position + np.array([[-1.0, -3.0, 0.0], [1.0, -3.0, 0.0], [0.0, -3.0, 1.0]]) @ pose.rotation.T
    vertices = np.vstack([wall, behind, wall[:1], wall[:1], wall[:1]])
    faces = np.array([[0, 1, 2], [0, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.int64)
    labels = np.zeros(view.shape, dtype=np.int64)
    range_m, face_ids = _first_hit(vertices, faces, pose, view)
    face_ids[0, 0] = 2
    face_ids[0, 1] = 3
    range_m[0, 0] = 3.0
    range_m[0, 1] = 3.0
    confidence = np.full(view.shape, 0.9)
    reason = paintability(labels, confidence, range_m)
    regions = build_region_map(labels, reason, range_m, min_region_pixels=4)
    surface = build_fishnet(vertices, faces, face_ids, regions, pose, view, confidence=confidence)

    assert surface.triangle_count > 0
    assert surface.report["rejected_degenerate_triangle"] == 1.0
    assert surface.report["rejected_behind_near_plane"] == 1.0
    with pytest.raises(ValueError, match="outside the support mesh"):
        build_fishnet(vertices, faces, np.full(view.shape, 99), regions, pose, view)


def test_boundary_chains_cover_every_crack_exactly_once_and_respect_the_tolerance() -> None:
    region = np.zeros((40, 40), dtype=np.int64)
    region[5:20, 5:20] = 1
    region[24:36, 24:36] = 2
    region[30:33, 30:33] = -1

    exact = boundary_chains(region, tolerance_px=0.0)
    cracks = int((region[:, :-1] != region[:, 1:]).sum() + (region[:-1, :] != region[1:, :]).sum())
    assert sum(len(chain) - 1 for chain in exact) == cracks
    segments = {tuple(sorted((tuple(chain[i]), tuple(chain[i + 1])))) for chain in exact for i in range(len(chain) - 1)}
    assert len(segments) == cracks

    simplified = boundary_chains(region, tolerance_px=1.5)
    assert sum(len(chain) for chain in simplified) < sum(len(chain) for chain in exact)
    for chain in exact:
        assert any(np.allclose(chain[0], other[0]) or np.allclose(chain[0], other[-1]) for other in simplified)


def test_regions_split_at_a_depth_step_and_absorb_speckle() -> None:
    labels = np.zeros((32, 32), dtype=np.int64)
    range_m = np.full((32, 32), 10.0)
    range_m[:, 16:] = 30.0
    labels[4, 4] = 5
    reason = paintability(labels, np.ones((32, 32)), range_m)
    regions = build_region_map(labels, reason, range_m, depth_break_ratio=0.15, min_region_pixels=8)

    assert regions.region_count == 2
    assert regions.region[0, 15] != regions.region[0, 16]
    assert regions.region[4, 4] == regions.region[4, 5]
    assert regions.report["merged_small_regions"] == 1
    assert np.all(regions.region_class == 0)


def test_solid_angle_matches_the_analytic_square_pyramid() -> None:
    triangles = np.array(
        [
            [[-1.0, -1.0, 1.0], [1.0, -1.0, 1.0], [1.0, 1.0, 1.0]],
            [[-1.0, -1.0, 1.0], [1.0, 1.0, 1.0], [-1.0, 1.0, 1.0]],
        ]
    )
    assert triangle_solid_angle(triangles).sum() == pytest.approx(4.0 * np.arcsin(0.5))
    with pytest.raises(ValueError, match="shape"):
        triangle_solid_angle(np.zeros((2, 3)))


def test_provenance_points_back_at_pixels_carrying_the_face_class() -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[16:48, 16:48] = 1
    surface, regions, face_ids, view, _camera = _build(labels)

    assert surface.pixel_offsets[-1] == len(surface.pixel_indices)
    for face in range(0, surface.triangle_count, 7):
        pixels = surface.source_pixels(face)
        assert pixels.size >= surface.face_pixel_support[face] > 0
        rows, columns = np.divmod(pixels, view.width)
        assert np.all(face_ids[rows, columns] == surface.face_source_triangle[face])
        winning = regions.region_class[regions.region[rows, columns]] == surface.face_class[face]
        assert winning.mean() >= 0.5


def test_confidence_and_material_posteriors_reach_the_output(tmp_path) -> None:
    labels = np.zeros((64, 64), dtype=np.int64)
    labels[16:48, 16:48] = 1
    view, pose = _view(), _pose()
    vertices, faces, range_m, face_ids, confidence, labels = _scene(labels, view=view, pose=pose)
    confidence[16:48, 16:48] = 0.4
    material = np.zeros((64, 64, 3))
    material[..., 0] = 1.0
    material[16:48, 16:48] = (0.0, 0.25, 0.75)
    reason = paintability(labels, confidence, range_m)
    regions = build_region_map(labels, reason, range_m, min_region_pixels=4)
    surface = build_fishnet(
        vertices,
        faces,
        face_ids,
        regions,
        pose,
        view,
        confidence=confidence,
        material_probability=material,
        min_piece_area_px=0.0,
    )

    window = surface.face_class == 1
    assert surface.face_confidence[window].max() == pytest.approx(0.4, abs=1e-6)
    assert surface.face_confidence[~window].max() == pytest.approx(0.8, abs=1e-6)
    assert np.allclose(surface.face_material[window], (0.0, 0.25, 0.75))
    assert np.allclose(surface.face_material[~window], (1.0, 0.0, 0.0))
    assert np.allclose(surface.face_class_probability.sum(axis=1), 1.0)

    path = tmp_path / "surface.npz"
    save_fishnet(surface, path)
    restored = load_fishnet(path)
    assert restored.triangle_count == surface.triangle_count
    assert np.array_equal(restored.faces, surface.faces)
    assert np.allclose(restored.face_material, surface.face_material)
    assert restored.format_version == 2
    assert np.array_equal(restored.rejected_faces, surface.rejected_faces)
    assert np.array_equal(restored.rejected_face_record, surface.rejected_face_record)
    assert np.array_equal(restored.rejected_geometry_kind, surface.rejected_geometry_kind)
    assert restored.report["emitted_area_px"] == pytest.approx(surface.report["emitted_area_px"])

    with np.load(path) as archive:
        legacy = {name: archive[name] for name in archive.files}
    for name in (
        "fishnet_format_version",
        "rejected_vertices",
        "rejected_faces",
        "rejected_face_image",
        "rejected_face_record",
        "rejected_face_offsets",
        "rejected_geometry_kind",
    ):
        legacy.pop(name)
    legacy_path = tmp_path / "legacy_surface.npz"
    np.savez_compressed(legacy_path, **legacy)
    restored_legacy = load_fishnet(legacy_path)
    assert restored_legacy.format_version == 1
    assert restored_legacy.rejected_faces.shape == (0, 3)
    assert restored_legacy.rejected_face_offsets.shape == (restored_legacy.rejected_reason.size + 1,)


def test_angular_tolerance_tracks_the_pixel_pitch() -> None:
    view = PinholeView(0.0, fov_deg=90.0, width=1024, height=1024)
    assert angular_tolerance_deg(0.0, view) == 0.0
    assert angular_tolerance_deg(1.0, view) == pytest.approx(np.degrees(np.arctan(2.0 / 1024.0)))
    assert angular_tolerance_deg(2.0, view) < 2.0 * angular_tolerance_deg(1.0, view)
    with pytest.raises(ValueError, match="non-negative"):
        angular_tolerance_deg(-1.0, view)


def test_malformed_inputs_are_refused() -> None:
    view = _view()
    pose = _pose()
    labels = np.zeros(view.shape, dtype=np.int64)
    range_m = np.full(view.shape, 5.0)
    reason = paintability(labels, np.ones(view.shape), range_m)
    regions = build_region_map(labels, reason, range_m)
    vertices = _quad(WALL_DISTANCE_M, WALL_HALF_M, pose)
    faces = np.array([[0, 1, 2], [0, 2, 3]])

    with pytest.raises(ValueError, match="orthonormal"):
        CameraPose(np.zeros(3), np.full((3, 3), 2.0))
    with pytest.raises(ValueError, match="fov_deg"):
        PinholeView(0.0, fov_deg=200.0)
    with pytest.raises(ValueError, match="equally shaped"):
        build_region_map(labels, reason, np.zeros((8, 8)))
    with pytest.raises(ValueError, match="positive"):
        build_region_map(labels, reason, range_m, depth_break_ratio=0.0)
    with pytest.raises(ValueError, match="match the view resolution"):
        build_fishnet(vertices, faces, np.zeros((8, 8), dtype=np.int64), regions, pose, view)
    with pytest.raises(ValueError, match="in front of the camera"):
        view_to_image(np.array([[0.0, 0.0, -1.0]]), view)
