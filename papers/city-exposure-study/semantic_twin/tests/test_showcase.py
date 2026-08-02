from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from semantic_twin.export import write_ply  # noqa: E402
from semantic_twin.showcase import (  # noqa: E402
    CROP_HALF_ELEVATION_DEG,
    MATERIAL_COLOURS,
    VISIBILITY_COLOURS,
    VISIBILITY_STATES,
    CropSpec,
    Layer,
    Pose,
    _crop_directions,
    _local_equirectangular,
    box,
    class_colour,
    classify_visibility,
    crop_specs,
    elevation_deg,
    ellipsoid,
    equirectangular_index,
    lift_towards,
    ramp,
    read_payload,
    read_ply,
    rejection_reason_names,
    triangle_area,
    unweld_duplicates,
    uniform,
    write_payload,
)


def unit_square() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    return vertices, faces


def test_ramp_is_monotone_and_opaque():
    values = np.linspace(0.0, 1.0, 32)
    colours = ramp(values, 0.0, 1.0)
    assert colours.shape == (32, 4)
    assert np.allclose(colours[:, 3], 1.0)
    assert colours.dtype == np.float32
    # Viridis rises monotonically in luminance from dark purple to yellow.
    luminance = colours[:, :3] @ np.array([0.2126, 0.7152, 0.0722])
    assert luminance[-1] > luminance[0]


def test_ramp_clips_outside_its_range():
    inside = ramp(np.array([0.0, 1.0]), 0.0, 1.0)
    outside = ramp(np.array([-5.0, 9.0]), 0.0, 1.0)
    assert np.allclose(inside, outside)


def test_ramp_rejects_an_empty_range():
    with pytest.raises(ValueError):
        ramp(np.array([0.0]), 1.0, 1.0)


def test_class_colour_prefers_the_shared_palette():
    assert class_colour(17, "Building") == class_colour(999, "building")
    assert class_colour(3, "Not A Known Class") != class_colour(4, "Not A Known Class")


def test_layer_rejects_a_mismatched_colour_channel():
    vertices, faces = unit_square()
    with pytest.raises(ValueError, match="colour channel"):
        Layer(name="bad", vertices=vertices, faces=faces, channels={"c": np.zeros((3, 4))})


def test_layer_rejects_an_out_of_range_face_index():
    vertices, faces = unit_square()
    with pytest.raises(ValueError, match="outside the vertex table"):
        Layer(name="bad", vertices=vertices, faces=faces + 10)


def test_read_ply_round_trips_the_project_writer(tmp_path):
    vertices = np.array([[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 5.0]])
    faces = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]])
    path = tmp_path / "mesh.ply"
    write_ply(path, vertices, faces)
    back_vertices, back_faces = read_ply(path)
    assert np.allclose(back_vertices, vertices)
    assert np.array_equal(back_faces, faces)


def test_read_ply_refuses_a_file_that_is_not_a_ply(tmp_path):
    path = tmp_path / "nope.ply"
    path.write_bytes(b"not a ply at all")
    with pytest.raises(ValueError, match="Not a binary PLY"):
        read_ply(path)


def test_triangle_area_matches_the_closed_form():
    vertices, faces = unit_square()
    assert np.allclose(triangle_area(vertices, faces), [0.5, 0.5])


def test_unweld_duplicates_separates_coincident_triangles():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    faces = np.array([[0, 1, 2], [2, 0, 1]])
    layer = Layer(name="pair", vertices=vertices, faces=faces)
    assert unweld_duplicates(layer) == 1
    assert len(layer.vertices) == 6
    key = np.sort(layer.faces, axis=1)
    assert len(np.unique(key, axis=0)) == 2
    assert np.allclose(triangle_area(layer.vertices, layer.faces), [0.5, 0.5])


def test_unweld_duplicates_leaves_a_clean_layer_alone():
    vertices, faces = unit_square()
    layer = Layer(name="clean", vertices=vertices, faces=faces)
    assert unweld_duplicates(layer) == 0
    assert len(layer.vertices) == 4


def test_lift_towards_moves_only_the_used_vertices():
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [50.0, 50.0, 50.0]])
    faces = np.array([[0, 1, 2]])
    moved = lift_towards(vertices, faces, np.array([0.0, 0.0, 10.0]), 1.0)
    assert np.allclose(moved[3], vertices[3])
    assert moved[0][2] == pytest.approx(1.0)
    assert np.linalg.norm(moved[1] - vertices[1]) == pytest.approx(1.0)


def test_lift_towards_with_zero_distance_is_the_identity():
    vertices, faces = unit_square()
    assert np.allclose(lift_towards(vertices, faces, np.array([0.0, 0.0, 5.0]), 0.0), vertices)


def test_elevation_deg_reads_the_horizon_and_the_poles():
    directions = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 4.0], [0.0, 0.0, -2.0]])
    assert np.allclose(elevation_deg(directions), [0.0, 90.0, -90.0])


def test_equirectangular_index_puts_the_heading_at_the_centre_column():
    pose = Pose(
        position=np.zeros(3),
        rotation=np.eye(3),
        heading_deg=0.0,
        residual_deg=0.0,
        height_above_ground_m=2.0,
        covariance_xyz=np.eye(3) * 1e-4,
    )
    rows, columns = equirectangular_index(np.array([[0.0, 1.0, 0.0]]), pose.rotation, (100, 200))
    assert columns[0] == 100
    assert rows[0] == 50


def test_crop_directions_reproduce_the_shared_projection():
    from semantic_twin.pano_geometry import perspective_direction_at, PerspectiveView

    spec = CropSpec(name="h+00_090", yaw_deg=90.0, pitch_deg=0.0, fov_deg=90.0, size=64)
    view = PerspectiveView(name=spec.name, yaw_deg=spec.yaw_deg, pitch_deg=spec.pitch_deg, fov_deg=spec.fov_deg)
    rows = np.array([0, 17, 63])
    columns = np.array([5, 40, 63])
    mine = _crop_directions(spec, rows, columns, spec.size)
    theirs = np.stack(
        [
            perspective_direction_at(view, float(column) + 0.5, float(row) + 0.5, spec.size, spec.size)
            for row, column in zip(rows, columns, strict=True)
        ]
    )
    assert np.allclose(mine, theirs)


def test_local_equirectangular_is_the_inverse_of_the_shared_grid():
    from semantic_twin.pano_geometry import equirectangular_directions

    grid = equirectangular_directions(64, 32)
    flat = grid.reshape(-1, 3)
    rows, columns = _local_equirectangular(flat, (32, 64))
    expected_rows = np.repeat(np.arange(32), 64)
    expected_columns = np.tile(np.arange(64), 32)
    assert np.array_equal(rows, expected_rows)
    assert np.array_equal(columns, expected_columns)


def test_ellipsoid_axes_follow_the_covariance():
    covariance = np.diag([4.0, 1.0, 0.25])
    shell = ellipsoid(np.zeros(3), covariance, sigma=1.0, subdivisions=1)
    extent = shell.vertices.max(axis=0)
    assert extent[0] == pytest.approx(2.0, rel=1e-6)
    assert extent[1] == pytest.approx(1.0, rel=1e-6)
    assert extent[2] == pytest.approx(0.5, rel=1e-6)
    assert len(shell.faces) == 80


def test_ellipsoid_is_deterministic():
    covariance = np.diag([1.0, 2.0, 3.0])
    first = ellipsoid(np.ones(3), covariance, sigma=3.0)
    second = ellipsoid(np.ones(3), covariance, sigma=3.0)
    assert np.array_equal(first.vertices, second.vertices)
    assert np.array_equal(first.faces, second.faces)


def test_ellipsoid_survives_a_singular_covariance():
    shell = ellipsoid(np.zeros(3), np.zeros((3, 3)), sigma=3.0, subdivisions=1)
    assert np.allclose(shell.vertices, 0.0)


def test_box_is_closed_and_centred():
    vertices, faces = box(np.array([1.0, 2.0, 3.0]), np.array([2.0, 2.0, 2.0]))
    assert len(faces) == 12
    assert np.allclose(vertices.mean(axis=0), [1.0, 2.0, 3.0])
    assert np.allclose(vertices.max(axis=0) - vertices.min(axis=0), [2.0, 2.0, 2.0])


def test_uniform_repeats_one_colour():
    colours = uniform((0.1, 0.2, 0.3, 1.0), 5)
    assert colours.shape == (5, 4)
    assert np.allclose(colours[0], colours[4])


def test_rejection_reason_names_cover_the_cutter_table():
    names = rejection_reason_names()
    assert names[7] == "transient_object"
    assert names[5] == "occluded_by_support_mesh"
    assert len(set(names.values())) == len(names)


def test_visibility_colours_cover_every_state():
    assert set(VISIBILITY_COLOURS) == set(VISIBILITY_STATES)


def test_material_colours_are_distinct():
    assert len(set(MATERIAL_COLOURS.values())) == len(MATERIAL_COLOURS)


class _StubIntersector:
    """A ray query over an explicit hit table, standing in for Embree."""

    def __init__(self, triangles: np.ndarray, points: np.ndarray) -> None:
        self.triangles = triangles
        self.points = points

    def intersects_id(self, origins, directions, return_locations=False, multiple_hits=False):
        rays = np.arange(len(directions))
        return self.triangles, rays, self.points


def test_classify_visibility_splits_the_three_states():
    # Two triangles in front of the camera and one behind a wall. The stub
    # reports the near triangle as the first hit for both of the coplanar pair.
    vertices = np.array(
        [
            [5.0, -1.0, 0.0],
            [5.0, 1.0, 0.0],
            [5.0, 0.0, 2.0],
            [9.0, -1.0, 0.0],
            [9.0, 1.0, 0.0],
            [9.0, 0.0, 2.0],
            [0.0, 20.0, 0.0],
            [1.0, 20.0, 0.0],
            [0.0, 20.0, 1.0],
        ]
    )
    faces = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8]])
    pose = Pose(
        position=np.zeros(3),
        rotation=np.eye(3),
        heading_deg=0.0,
        residual_deg=0.0,
        height_above_ground_m=0.0,
        covariance_xyz=np.eye(3) * 1e-4,
    )
    centroids = vertices[faces].mean(axis=1)
    # The near triangle owns its own ray, the far one is occluded by the near
    # one, and the third is left to the texture layer.
    stub = _StubIntersector(
        triangles=np.array([0, 0, 2]),
        points=np.array([centroids[0], centroids[0], centroids[2]]),
    )
    state, report = classify_visibility(vertices, faces, pose, np.array([1]), stub)
    assert VISIBILITY_STATES[state[0]] == "panorama"
    assert VISIBILITY_STATES[state[1]] == "texture"
    assert VISIBILITY_STATES[state[2]] == "panorama"
    assert report["faces"] == 3
    assert report["crop_half_elevation_deg"] == CROP_HALF_ELEVATION_DEG
    assert report["panorama_faces"] + report["texture_faces"] + report["unseen_faces"] == 3
    total = report["panorama_area_fraction"] + report["texture_area_fraction"] + report["unseen_area_fraction"]
    assert total == pytest.approx(1.0)


def test_classify_visibility_leaves_faces_outside_the_crop_band_unseen():
    vertices = np.array([[0.1, 0.0, 30.0], [0.2, 0.0, 30.0], [0.1, 0.1, 30.0]])
    faces = np.array([[0, 1, 2]])
    pose = Pose(
        position=np.zeros(3),
        rotation=np.eye(3),
        heading_deg=0.0,
        residual_deg=0.0,
        height_above_ground_m=0.0,
        covariance_xyz=np.eye(3) * 1e-4,
    )
    stub = _StubIntersector(triangles=np.zeros(0, dtype=np.int64), points=np.zeros((0, 3)))
    state, report = classify_visibility(vertices, faces, pose, None, stub)
    assert VISIBILITY_STATES[state[0]] == "unseen"
    assert report["in_crop_band_faces"] == 0


def test_crop_specs_read_the_shipped_manifest_shape(tmp_path):
    manifest = tmp_path / "fishnet_manifest.json"
    manifest.write_text(json.dumps({"views": [{"view": "h+00_000", "shape": [1024, 1024]}]}))
    specs = crop_specs(manifest, ["h+00_000"], [0])
    assert specs[0].size == 1024
    assert specs[0].fov_deg == 90.0


def test_crop_specs_refuse_a_missing_crop(tmp_path):
    manifest = tmp_path / "fishnet_manifest.json"
    manifest.write_text(json.dumps({"views": [{"view": "h+00_000", "shape": [1024, 1024]}]}))
    with pytest.raises(KeyError):
        crop_specs(manifest, ["h+00_090"], [90])


def test_crop_specs_refuse_a_non_square_crop(tmp_path):
    manifest = tmp_path / "fishnet_manifest.json"
    manifest.write_text(json.dumps({"views": [{"view": "h+00_000", "shape": [512, 1024]}]}))
    with pytest.raises(ValueError, match="not square"):
        crop_specs(manifest, ["h+00_000"], [0])


def test_crop_basis_reproduces_the_crop_projection():
    """The camera basis must map crop image coordinates onto the same world rays.

    ``perspective_direction_at`` gives the ray of a crop pixel in the panorama
    frame, and the pose rotation carries it to ENU. A Blender camera with this
    basis and a 90 degree lens has to produce that same ray, otherwise the
    render and the photograph beside it are not the same projection.
    """
    from semantic_twin.pano_geometry import PerspectiveView, panorama_to_world_matrix, perspective_direction_at
    from render_showcase import crop_basis

    pose = {"heading_deg": 217.0, "pitch_correction_deg": 3.5, "roll_correction_deg": -1.25}
    basis = crop_basis(pose, 90.0)
    assert np.allclose(basis.T @ basis, np.eye(3), atol=1e-12)
    assert np.linalg.det(basis) == pytest.approx(1.0)

    rotation = panorama_to_world_matrix(217.0, pitch_deg=3.5, roll_deg=-1.25)
    view = PerspectiveView(name="h+00_090", yaw_deg=90.0, pitch_deg=0.0, fov_deg=90.0)
    size = 256
    for row, column in ((0, 0), (128, 200), (255, 255)):
        expected = rotation @ perspective_direction_at(view, column + 0.5, row + 0.5, size, size)
        # The same pixel expressed in the camera basis, with plus X right, plus
        # Y up and minus Z forward, and a 90 degree square field of view.
        x = (column + 0.5) / size * 2.0 - 1.0
        y = 1.0 - (row + 0.5) / size * 2.0
        local = np.array([x, y, -1.0])
        rendered = basis @ (local / np.linalg.norm(local))
        assert np.allclose(rendered, expected, atol=1e-12)


def _write_fishnet_crop(path, vertices, faces, image, camera):
    np.savez(
        path,
        vertices=vertices,
        faces=faces,
        face_image=image,
        camera_position=camera,
    )


def test_reprojection_residual_is_zero_for_a_self_consistent_crop(tmp_path):
    from semantic_twin.showcase import _view_components, reprojection_residual_px

    spec = CropSpec(name="h+00_000", yaw_deg=0.0, pitch_deg=0.0, fov_deg=90.0, size=256)
    pose = Pose(
        position=np.array([1.0, -2.0, 3.0]),
        rotation=np.eye(3),
        heading_deg=0.0,
        residual_deg=0.0,
        height_above_ground_m=2.0,
        covariance_xyz=np.eye(3) * 1e-4,
    )
    rng = np.random.default_rng(7)
    vertices = pose.position + np.array([0.0, 20.0, 0.0]) + rng.uniform(-4.0, 4.0, size=(9, 3))
    faces = np.arange(9).reshape(3, 3)
    local = _view_components(vertices[faces].reshape(-1, 3) - pose.position, pose.rotation, spec)
    tangent = 1.0
    image = np.stack(
        [
            (local[:, 0] / (local[:, 2] * tangent) + 1.0) * 0.5 * spec.size,
            (1.0 - local[:, 1] / (local[:, 2] * tangent)) * 0.5 * spec.size,
        ],
        axis=1,
    ).reshape(3, 3, 2)
    _write_fishnet_crop(tmp_path / "h+00_000_fishnet.npz", vertices, faces, image, pose.position)
    report = reprojection_residual_px(tmp_path, ["h+00_000"], [spec], pose)
    assert report["median_px"] < 1e-9
    assert report["samples"] == 9


def test_reprojection_residual_catches_a_pose_that_has_moved(tmp_path):
    from semantic_twin.showcase import _view_components, reprojection_residual_px

    spec = CropSpec(name="h+00_000", yaw_deg=0.0, pitch_deg=0.0, fov_deg=90.0, size=256)
    truth = Pose(
        position=np.zeros(3),
        rotation=np.eye(3),
        heading_deg=0.0,
        residual_deg=0.0,
        height_above_ground_m=2.0,
        covariance_xyz=np.eye(3) * 1e-4,
    )
    rng = np.random.default_rng(11)
    vertices = np.array([0.0, 25.0, 0.0]) + rng.uniform(-3.0, 3.0, size=(9, 3))
    faces = np.arange(9).reshape(3, 3)
    local = _view_components(vertices[faces].reshape(-1, 3) - truth.position, truth.rotation, spec)
    image = np.stack(
        [
            (local[:, 0] / local[:, 2] + 1.0) * 0.5 * spec.size,
            (1.0 - local[:, 1] / local[:, 2]) * 0.5 * spec.size,
        ],
        axis=1,
    ).reshape(3, 3, 2)
    _write_fishnet_crop(tmp_path / "h+00_000_fishnet.npz", vertices, faces, image, truth.position)
    moved = Pose(
        position=np.array([1.5, 0.0, 0.0]),
        rotation=truth.rotation,
        heading_deg=0.0,
        residual_deg=0.0,
        height_above_ground_m=2.0,
        covariance_xyz=np.eye(3) * 1e-4,
    )
    report = reprojection_residual_px(tmp_path, ["h+00_000"], [spec], moved)
    # A 1.5 m sideways shift at 25 m is 3.4 degrees, which is about 8 px in a
    # 256 pixel 90 degree crop. The check has to see that, not average it away.
    assert report["median_px"] > 5.0


def test_payload_round_trips(tmp_path):
    vertices, faces = unit_square()
    layer = Layer(
        name="patch",
        vertices=vertices,
        faces=faces,
        channels={"flat": uniform((0.2, 0.4, 0.6, 1.0), 2)},
        legends={"flat": [{"label": "patch", "colour": [0.2, 0.4, 0.6, 1.0], "value": "2 faces"}]},
        scalars={"area": triangle_area(vertices, faces)},
    )
    path = tmp_path / "payload.npz"
    write_payload(path, [layer], {"site": "test", "views": [], "render": {"seed": 0}})
    layers, sidecar = read_payload(path)
    assert set(layers) == {"patch"}
    assert np.allclose(layers["patch"]["vertices"], vertices)
    assert np.array_equal(layers["patch"]["faces"], faces)
    from semantic_twin.showcase import srgb_to_linear

    assert np.allclose(layers["patch"]["channels"]["flat"], srgb_to_linear(layer.channels["flat"]), atol=1e-6)
    assert np.allclose(layers["patch"]["scalars"]["area"], [0.5, 0.5])
    assert sidecar["site"] == "test"
    assert layers["patch"]["legends"]["flat"][0]["value"] == "2 faces"


def test_payload_is_byte_identical_across_two_writes(tmp_path):
    vertices, faces = unit_square()
    layer = Layer(name="patch", vertices=vertices, faces=faces, channels={"flat": uniform((0.5, 0.5, 0.5, 1.0), 2)})
    metadata = {"site": "test", "views": [], "render": {"seed": 0}}
    first = tmp_path / "a.npz"
    second = tmp_path / "b.npz"
    write_payload(first, [layer], metadata)
    write_payload(second, [layer], metadata)
    assert first.with_suffix(".json").read_bytes() == second.with_suffix(".json").read_bytes()
    a_layers, _ = read_payload(first)
    b_layers, _ = read_payload(second)
    assert np.array_equal(a_layers["patch"]["channels"]["flat"], b_layers["patch"]["channels"]["flat"])


def test_colour_round_trips_through_linear_light():
    from semantic_twin.showcase import linear_to_srgb, srgb_to_linear

    display = np.array([[0.0, 0.04, 0.5, 1.0], [1.0, 0.36, 0.06, 1.0], [0.2, 0.21, 0.24, 1.0]])
    assert np.allclose(linear_to_srgb(srgb_to_linear(display)), display, atol=1e-6)
    # Alpha is not a light quantity and must be left alone.
    assert np.allclose(srgb_to_linear(display)[:, 3], display[:, 3])
    # The conversion has to actually darken, otherwise it is a no-op that hides
    # the bug it exists to prevent.
    assert srgb_to_linear(display)[1, 1] < display[1, 1] - 0.2


def test_write_payload_stores_linear_light(tmp_path):
    from semantic_twin.showcase import srgb_to_linear

    vertices, faces = unit_square()
    display = uniform((1.0, 0.36, 0.06, 1.0), 2)
    layer = Layer(name="patch", vertices=vertices, faces=faces, channels={"flat": display})
    path = tmp_path / "payload.npz"
    write_payload(path, [layer], {"site": "test", "views": [], "render": {"seed": 0}})
    layers, _ = read_payload(path)
    assert np.allclose(layers["patch"]["channels"]["flat"], srgb_to_linear(display), atol=1e-6)


BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_rendered_pixel_equals_the_legend_swatch(tmp_path):
    """The regression guard: a categorical layer must render as its own colour.

    A quad is placed square to a camera and rendered through the real pipeline.
    If the payload ever goes back to carrying display values, or the flat layers
    are lit again, the centre pixel stops being the swatch and this fails.
    """
    import subprocess

    from semantic_twin.showcase import write_payload

    swatch = (1.0, 0.36, 0.06, 1.0)
    vertices = np.array([[-8.0, 20.0, -8.0], [8.0, 20.0, -8.0], [8.0, 20.0, 8.0], [-8.0, 20.0, 8.0]])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    layer = Layer(
        name="patch",
        vertices=vertices,
        faces=faces,
        channels={"swatch": uniform(swatch, 2)},
        legends={"swatch": [{"label": "patch", "colour": list(swatch), "value": ""}]},
    )
    payload = tmp_path / "payload.npz"
    write_payload(
        payload,
        [layer],
        {
            "site": "unit test",
            "generator": "test",
            "legend_index": {"patch:swatch": layer.legends["swatch"]},
            "render": {
                "seed": 0,
                "sky_zenith": [0.1, 0.1, 0.1, 1.0],
                "sky_horizon": [0.1, 0.1, 0.1, 1.0],
                "flat_world_colour": [0.0, 0.0, 0.0, 1.0],
                "flat_world_strength": 1.0,
                "suns": [],
            },
            "views": [
                {
                    "name": "swatch",
                    "title": "swatch",
                    "subtitle": "",
                    "camera": {"position": [0.0, 0.0, 0.0], "target": [0.0, 20.0, 0.0], "lens_mm": 36.0},
                    "resolution": [64, 64],
                    "samples": 4,
                    "layers": [{"layer": "patch", "channel": "swatch"}],
                    "legend": [["patch", "swatch"]],
                }
            ],
        },
    )
    result = subprocess.run(
        [
            str(BLENDER),
            "--background",
            "--python",
            str(ROOT / "showcase_blender.py"),
            "--",
            "--payload",
            str(payload),
            "--out",
            str(tmp_path / "raw"),
            "--device",
            "CPU",
            "--skip-tiles",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    rendered = tmp_path / "raw" / "swatch.png"
    assert rendered.is_file(), result.stdout[-3000:] + result.stderr[-3000:]

    from PIL import Image

    pixels = np.asarray(Image.open(rendered).convert("RGB"), dtype=np.float64) / 255.0
    centre = pixels[32, 32]
    assert np.allclose(centre, swatch[:3], atol=2.0 / 255.0), f"centre pixel {centre} is not the swatch {swatch[:3]}"
