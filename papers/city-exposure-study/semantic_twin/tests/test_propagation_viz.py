"""The payload stage of the propagation walkthrough blend.

Only the parts that turn a physical model into something drawable are tested
here. The tracing itself is covered by ``tests/test_propagation.py`` and the
recorder is asserted there to leave every traced number bit identical.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap

import numpy as np
import pytest

from semantic_twin.viz.blender.exporter import (
    HEIGHT_BAND_M,
    RANGE_BAND_M,
    crop_for_drawing,
    facade_tip_rim,
    network_markers,
    next_event_connections,
    sphere_triangulation,
)
from semantic_twin.illumination import MODELS, elevation_band_measure, fibonacci_sphere
from semantic_twin.propagation.geometry import INFINITY
from semantic_twin.viz.blender.payload import (
    camera_rotation,
    drawable_ray_legs,
    octahedra,
    ray_bundles,
    shorten_sky_legs,
    supported_live_scattering_vertices,
)
from semantic_twin.viz.blender.style import (
    RAY_STYLE,
    angular_law_sample_metadata,
    angular_law_sample_object_name,
    colour_ramp,
)

#: Integrated per band, never sampled at the midpoint. The reason lives in the
#: docstring of the library function, which this file used to carry its own copy
#: of and now shares with the tests of the law itself.
band_measure = elevation_band_measure


def test_hidden_angular_law_samples_cannot_read_as_counted_source_sites() -> None:
    name = angular_law_sample_object_name("rooftop")
    record = angular_law_sample_metadata("rooftop")

    assert name == "angular_law_samples_rooftop_not_counted_sites"
    assert record["marker_points_used_in_exposure"] is False
    assert record["analytic_population_defines_scored_angular_law"] is True
    assert "Monte Carlo" in record["role"]
    assert "superseded" not in " ".join(str(value) for value in record.values())


def marker_elevation(name: str, count: int, seed: int) -> np.ndarray:
    markers = network_markers(name, count, np.random.default_rng(seed))["positions"]
    return np.degrees(np.arctan2(markers[:, 2], np.linalg.norm(markers[:, :2], axis=1)))


@pytest.mark.parametrize("name", sorted(HEIGHT_BAND_M))
def test_the_drawn_sources_span_exactly_the_model_support(name: str) -> None:
    """The markers must cover the model's elevation support and nothing outside it.

    A marker outside the support would be a source contributing zero power, and
    a support the markers fail to reach would be power arriving from nowhere.

    Containment is exact and asserted as such. Reach is asserted as a rate
    rather than as one tolerance at one sample count, because under the
    corrected law both support edges are *corners* of the height by range
    rectangle rather than whole edges of it: the top edge needs the tallest site
    at the shortest range at once. The measure within `delta` of either edge
    therefore falls as `delta^2`, so the empirical extreme approaches the edge
    only as the inverse square root of the sample count. Sixteen times the
    markers should buy about four times the reach, and 2.5 is asserted. The
    statistic is the median gap over independent draws rather than one draw's
    gap, because a single sample maximum is an extreme value and its scatter
    would swamp the rate being measured.
    """
    model = MODELS[name]
    gaps = []
    for count in (100_000, 1_600_000):
        low, high = [], []
        for seed in range(6):
            elevation = marker_elevation(name, count, seed)
            assert elevation.min() >= model.elevation_min_deg - 1.0e-9
            assert elevation.max() <= model.elevation_max_deg + 1.0e-9
            low.append(elevation.min() - model.elevation_min_deg)
            high.append(model.elevation_max_deg - elevation.max())
        gaps.append((float(np.median(low)), float(np.median(high))))
    coarse, fine = gaps
    assert fine[0] < coarse[0] / 2.5
    assert fine[1] < coarse[1] / 2.5
    assert fine[0] < 0.01
    assert fine[1] < 0.35


@pytest.mark.parametrize("name", sorted(HEIGHT_BAND_M))
def test_the_drawn_sources_reproduce_the_model_elevation_law(name: str) -> None:
    """Binning the markers by elevation must recover ``Q_S`` up to a constant.

    This is the check that makes the source markers evidence rather than
    decoration, and it is the one that first showed the height band and the
    elevation law of section 2.7 to be different models. Read
    ``network_markers`` for which of the two survived.
    """
    model = MODELS[name]
    markers = network_markers(name, 400_000, np.random.default_rng(4))["positions"]
    elevation = np.degrees(np.arctan2(markers[:, 2], np.linalg.norm(markers[:, :2], axis=1)))
    # Equal count bins, so every bin carries the same Poisson error. Equal width
    # bins on a `1/sin^3` law put almost nothing in the top half of the support.
    edges = np.quantile(elevation, np.linspace(0.0, 1.0, 21))
    drawn, _ = np.histogram(elevation, bins=edges)

    expected = band_measure(model, edges)
    expected = expected / expected.sum() * drawn.sum()

    assert np.all(drawn > 0)
    ratio = drawn / expected
    assert ratio.max() / ratio.min() < 1.10


def test_giving_each_height_its_own_annulus_would_not_reproduce_the_law() -> None:
    """The rejected sampler of section 2.7, kept so the correction cannot regress.

    Drawing the height with density proportional to `h^2` and then the range
    uniformly by area inside `h*cot(el_max)` to `h*cot(el_min)` reproduces the
    uncorrected `1/sin^3` law exactly. It was in ``network_markers`` until
    2026-08-02. Against the corrected law it is off by more than an order of
    magnitude, and it needs ranges out to 803 m to do it.
    """
    model = MODELS["rooftop"]
    low_h, high_h = HEIGHT_BAND_M["rooftop"]
    rng = np.random.default_rng(5)
    count = 400_000
    inner = 1.0 / np.tan(np.radians(model.elevation_max_deg))
    outer = 1.0 / np.tan(np.radians(model.elevation_min_deg))
    height = np.cbrt(low_h**3 + rng.random(count) * (high_h**3 - low_h**3))
    radius = np.sqrt((inner * height) ** 2 + rng.random(count) * ((outer * height) ** 2 - (inner * height) ** 2))
    elevation = np.degrees(np.arctan2(height, radius))

    edges = np.linspace(model.elevation_min_deg, model.elevation_max_deg, 25)
    drawn, _ = np.histogram(elevation, bins=edges)
    expected = band_measure(model, edges)
    expected = expected / expected.sum() * drawn.sum()

    ratio = drawn / np.maximum(expected, 1.0e-12)
    assert ratio.max() / ratio.min() > 10.0
    # And the reason it is rejected rather than merely different: the sources it
    # asks for are nowhere near the range band the model names.
    assert radius.max() > 3.0 * RANGE_BAND_M["rooftop"][1]


def test_source_markers_sit_inside_the_stated_height_and_range_bands() -> None:
    for name, (low_h, high_h) in HEIGHT_BAND_M.items():
        drawn = network_markers(name, 5_000, np.random.default_rng(0))
        markers = drawn["positions"]
        assert markers[:, 2].min() >= low_h - 1.0e-9
        assert markers[:, 2].max() <= high_h + 1.0e-9
        horizontal = np.linalg.norm(markers[:, :2], axis=1)
        near, far = drawn["range_m"]
        assert (near, far) == RANGE_BAND_M[name]
        assert horizontal.min() >= near - 1.0e-6
        assert horizontal.max() <= far + 1.0e-6


def test_an_isotropic_model_has_no_source_geometry_to_draw() -> None:
    """Isotropic illumination is not a network, so it gets no markers.

    Drawing sources for it would invent a range and a height the model never
    had, which is the one thing this whole module is trying not to do.
    """
    assert network_markers("isotropic", 100, np.random.default_rng(0))["positions"].shape == (0, 3)


class WallGeometry:
    """A wall of azimuth dependent radius and one height, seen from its own axis.

    A ray leaving the axis along azimuth ``phi`` and elevation ``el`` meets the
    wall at horizontal range ``radius(phi)`` and rises ``radius(phi) tan(el)``
    doing it, so the silhouette is at ``arctan(height / radius(phi))`` and at
    horizontal distance ``radius(phi)``, both known in closed form. That is what
    makes it a test of the extraction rather than a second copy of it.

    Only valid for rays that start on the axis, which is every ray
    ``measure_skyline.skyline`` casts.
    """

    def __init__(self, base_m: float = 30.0, swing_m: float = 10.0, height_m: float = 20.0) -> None:
        self.base = base_m
        self.swing = swing_m
        self.height = height_m

    def radius(self, azimuth: np.ndarray) -> np.ndarray:
        return self.base + self.swing * np.cos(azimuth)

    def intersect(self, origins, directions):
        origins = np.asarray(origins, dtype=np.float64)
        directions = np.asarray(directions, dtype=np.float64)
        azimuth = np.arctan2(directions[:, 1], directions[:, 0])
        horizontal = np.linalg.norm(directions[:, :2], axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            slant = self.radius(azimuth) / horizontal
        rise = slant * directions[:, 2]
        hit = np.isfinite(slant) & (slant > 0.0) & (rise <= self.height)
        distance = np.where(hit, slant, INFINITY)
        normal = np.zeros_like(directions)
        return hit, distance, normal, np.zeros(origins.shape[0], dtype=np.int64)


class NothingGeometry:
    """Empty space. Every ray misses."""

    def intersect(self, origins, directions):
        count = np.asarray(origins).shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, INFINITY),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


class NearWallGeometry:
    """A wall a metre off every ray's shoulder, so every connection is blocked."""

    def intersect(self, origins, directions):
        count = np.asarray(origins).shape[0]
        return (
            np.ones(count, dtype=bool),
            np.ones(count),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


def test_the_rim_sits_on_the_silhouette_at_the_azimuth_it_claims() -> None:
    """The extracted tip must land on the wall, at the azimuth it is indexed by.

    Horizontal distance is the sharp half of this. The elevation the fan finds
    is one of its grid values and is therefore short of the true silhouette by
    up to a grid step, but the horizontal distance is the slant range times the
    cosine of that same elevation, and on this wall the two errors cancel
    exactly. So the distance is a closed form answer and is asserted as one.

    A convention drift of half a cell in azimuth would rotate the whole rim off
    the rooflines, and nothing else in the pipeline would say so. Here it moves
    the distance off ``radius(phi)`` and this fails.
    """
    wall = WallGeometry()
    rim = facade_tip_rim(NothingGeometry(), np.zeros(3), azimuths=90, elevations=200)
    assert not rim["found"].any(), "empty space has no skyline and must not invent one"

    rim = facade_tip_rim(wall, np.zeros(3), azimuths=90, elevations=200)
    assert rim["found"].all()
    expected = wall.radius(rim["azimuth_rad"])
    assert np.allclose(rim["distance_m"], expected, rtol=1.0e-9)

    # The elevation is the largest grid value that still hits, so it sits under
    # the true silhouette by less than one step of a 200 point logarithmic grid.
    truth = np.arctan2(wall.height, expected)
    step = (np.log(85.0) - np.log(0.05)) / 199.0
    assert np.all(rim["alpha_rad"] <= truth + 1.0e-12)
    assert np.all(rim["alpha_rad"] > truth * np.exp(-step))

    # The drawn offset must be the same point again, in Cartesian.
    offset = rim["offset"]
    assert np.allclose(np.linalg.norm(offset[:, :2], axis=1), expected)
    assert np.allclose(offset[:, 2], expected * np.tan(rim["alpha_rad"]))
    assert np.allclose(np.arctan2(offset[:, 1], offset[:, 0]) % (2.0 * np.pi), rim["azimuth_rad"])

    weight = np.cos(rim["alpha_rad"]) ** 2 / expected
    assert rim["summary"]["direct_term"] == pytest.approx(float(weight.mean()))
    assert rim["summary"]["open_azimuth_fraction"] == 0.0


def straight_paths(count: int, reach_m: float = 400.0) -> tuple[np.ndarray, np.ndarray]:
    """``count`` recorded paths that left the head and never bounced.

    Two vertices each, the head and where it left the scene, which is the layout
    ``PathRecorder`` writes. Only the first of the two is a scattering vertex,
    so each of these paths owes exactly one connection.
    """
    direction = fibonacci_sphere(count)
    vertices = np.zeros((2 * count, 3))
    vertices[1::2] = reach_m * direction
    return vertices, np.arange(count + 1) * 2


def test_a_connection_leaves_every_vertex_except_the_one_that_left_the_scene() -> None:
    wall = WallGeometry()
    rim = facade_tip_rim(wall, np.zeros(3), azimuths=90, elevations=200)
    vertices, offsets = straight_paths(12)
    drawn = next_event_connections(wall, vertices, offsets, rim, np.zeros(3), paths=12, seed=0)

    assert drawn["summary"]["paths_drawn"] == 12
    assert drawn["summary"]["connections"] == 12
    assert np.array_equal(drawn["vertex_index"], np.zeros(12, dtype=np.int32))
    assert np.allclose(drawn["origin"], 0.0), "the connection starts at the vertex, not near it"
    # Every site is one of the tips, and the weight travels with it.
    assert np.allclose(drawn["site"], rim["offset"][drawn["azimuth_index"]])
    assert np.allclose(drawn["weight"], rim["weight"][drawn["azimuth_index"]])


def test_nothing_blocks_a_connection_from_the_standpoint_the_rim_was_measured_at() -> None:
    """The tip is the silhouette from the head, so the head can always see it.

    This is a check on the geometry rather than a result. If it ever fails, the
    rim and the shadow rays are not being cast against the same surface.
    """
    wall = WallGeometry()
    rim = facade_tip_rim(wall, np.zeros(3), azimuths=180, elevations=300)
    vertices, offsets = straight_paths(40)
    drawn = next_event_connections(wall, vertices, offsets, rim, np.zeros(3), paths=40, seed=3)
    assert not drawn["blocked"].any()
    assert drawn["summary"]["blocked_fraction_from_the_head"] == 0.0


def test_a_surface_across_the_connection_blocks_it_and_empty_space_does_not() -> None:
    wall = WallGeometry()
    rim = facade_tip_rim(wall, np.zeros(3), azimuths=90, elevations=200)
    vertices, offsets = straight_paths(8)
    for geometry, expected in ((NearWallGeometry(), True), (NothingGeometry(), False)):
        drawn = next_event_connections(geometry, vertices, offsets, rim, np.zeros(3), paths=8, seed=1)
        assert bool(drawn["blocked"].all()) is expected
        assert drawn["summary"]["blocked_fraction"] == float(expected)


def test_sphere_triangulation_closes_the_grid_and_faces_outward() -> None:
    grid = fibonacci_sphere(256)
    faces = sphere_triangulation(grid)
    # A closed triangulated sphere has 2n - 4 facets by Euler's formula.
    assert faces.shape[0] == 2 * grid.shape[0] - 4
    assert set(np.unique(faces)) == set(range(grid.shape[0]))
    a, b, c = grid[faces[:, 0]], grid[faces[:, 1]], grid[faces[:, 2]]
    centroid = grid[faces].mean(axis=1)
    assert np.all(np.einsum("ij,ij->i", np.cross(b - a, c - a), centroid) > 0.0)
    # Every edge is shared by exactly two facets, which is what "closed" means.
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.all(counts == 2)


def test_crop_for_drawing_keeps_only_what_is_inside_and_reindexes_cleanly() -> None:
    rng = np.random.default_rng(1)
    vertices = rng.uniform(-50.0, 50.0, size=(400, 3))
    faces = rng.integers(0, 400, size=(300, 3))
    kept_vertices, kept_faces, kept_index = crop_for_drawing(vertices, faces, 20.0)

    centroid = vertices[faces].mean(axis=1)
    expected = np.flatnonzero(np.linalg.norm(centroid[:, :2], axis=1) <= 20.0)
    assert np.array_equal(kept_index, expected)
    assert kept_faces.shape[0] == expected.size
    assert kept_faces.max() < kept_vertices.shape[0]
    # The reindexed geometry must be the same triangles, not merely the same count.
    assert np.allclose(kept_vertices[kept_faces], vertices[faces[expected]])


def scene_module():
    """Import the Blender vocabulary with ``bpy`` stubbed out.

    Everything in ``semantic_twin.viz.blender.scene`` calls Blender, so this is
    the one module here that cannot be imported plainly. Its module level is
    still free of ``bpy`` calls, so a stub is enough to reach the camera search,
    which decides where to stand by casting rays at an object it is handed and
    never touches the scene. Shelling out to a headless Blender to check that
    would take a hundred times longer and prove less.

    The three pure helpers this file also covers live in
    :mod:`~semantic_twin.viz.blender.payload` and
    :mod:`~semantic_twin.viz.blender.style` and are imported at the top like any
    other library. That is the whole point of the split.
    """
    import importlib
    import sys
    import types

    if "bpy" not in sys.modules:
        stub = types.ModuleType("bpy")
        stub.types = types.SimpleNamespace(Object=object, Collection=object, Material=object)
        sys.modules["bpy"] = stub
    return importlib.import_module("semantic_twin.viz.blender.scene")


def test_camera_rotation_actually_points_at_the_target() -> None:
    """Rebuild the rotation and check it maps the camera axis onto the sight line."""
    rng = np.random.default_rng(7)
    for _ in range(64):
        location = rng.uniform(-200.0, 200.0, size=3)
        target = rng.uniform(-200.0, 200.0, size=3)
        if np.linalg.norm(target - location) < 1.0:
            continue
        rx, ry, rz = camera_rotation(location, target)
        assert ry == 0.0
        cx, sx = np.cos(rx), np.sin(rx)
        cz, sz = np.cos(rz), np.sin(rz)
        rotation = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]]) @ np.array(
            [[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]]
        )
        aim = rotation @ np.array([0.0, 0.0, -1.0])
        wanted = (target - location) / np.linalg.norm(target - location)
        assert np.allclose(aim, wanted, atol=1.0e-9)
        # The camera must also stay upright, meaning its own up axis has no
        # roll about the sight line.
        up = rotation @ np.array([0.0, 1.0, 0.0])
        assert up[2] >= -1.0e-9 or abs(wanted[2]) > 0.999


def test_colour_ramp_is_monotone_and_clamps() -> None:
    values = np.array([-5.0, 0.0, 0.25, 0.5, 0.75, 1.0, 5.0])
    rgba = colour_ramp(values, 0.0, 1.0)
    assert rgba.shape == (values.size, 4)
    assert np.allclose(rgba[:, 3], 1.0)
    assert np.allclose(rgba[0], rgba[1])
    assert np.allclose(rgba[-1], rgba[-2])
    # Inferno rises monotonically in luminance across its whole range.
    luminance = rgba[1:-1] @ np.array([0.2126, 0.7152, 0.0722, 0.0])
    assert np.all(np.diff(luminance) > 0.0)


def test_ray_bundles_are_exclusive_and_exhaustive() -> None:
    rng = np.random.default_rng(3)
    count = 500
    directions = rng.normal(size=(count, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    payload = {
        "path_termination": rng.integers(0, 3, size=count),
        "path_bounces": rng.integers(0, 5, size=count),
        "path_exit_direction": directions,
    }
    bundles = ray_bundles(payload, ["sky", "roulette", "truncated"])
    stacked = np.stack(list(bundles.values()))
    assert np.array_equal(stacked.sum(axis=0), np.ones(count, dtype=int))
    assert set(bundles) == set(RAY_STYLE)


def ray_leg_payload() -> dict[str, np.ndarray]:
    """Five paths covering sky, bounce, absorption, crop and duplicate endpoints."""
    paths = [
        [[0.0, 0.0, 1.0], [200.0, 0.0, 1.0]],
        [[0.0, 0.0, 1.0], [10.0, 0.0, 1.0], [200.0, 20.0, 50.0]],
        [[0.0, 0.0, 1.0], [5.0, 0.0, 0.0], [10.0, 0.0, 10.0]],
        [[0.0, 0.0, 1.0], [111.0, 0.0, 1.0], [200.0, 0.0, 20.0]],
        [[0.0, 0.0, 1.0], [4.0, 0.0, 1.0], [4.0, 0.0, 1.0]],
    ]
    power = [[1.0, 1.0], [1.0, 0.25, 0.25], [1.0, 0.0, 0.0], [1.0, 0.5, 0.5], [1.0, 0.5, 0.5]]
    return {
        "path_vertices": np.concatenate(paths),
        "path_offsets": np.concatenate([[0], np.cumsum([len(path) for path in paths])]),
        "path_throughput": np.concatenate(power),
        "path_bounces": np.array([0, 1, 1, 1, 1]),
        "path_termination": np.array([0, 0, 0, 0, 1]),
        "path_exit_direction": np.array(
            [[1.0, 0.0, 0.0], [0.9, 0.1, 0.3], [0.7, 0.0, 0.7], [1.0, 0.0, 0.1], [1.0, 0.0, 0.0]]
        ),
    }


def test_recorded_paths_become_constant_physical_legs_with_honest_endpoints() -> None:
    payload = ray_leg_payload()
    legs = drawable_ray_legs(payload, np.arange(5), ["sky", "roulette", "truncated"], drawn_radius_m=110.0)

    assert legs.lengths.tolist() == [2, 2, 2, 2, 2]
    assert legs.leg_throughput.tolist() == [1.0, 1.0, 0.25, 1.0, 1.0]
    assert legs.path_index.tolist() == [0, 1, 1, 2, 4]
    assert legs.leg_index.tolist() == [0, 0, 1, 0, 0]
    assert legs.escaped_final.tolist() == [True, False, True, False, False]
    assert legs.paths_left_out_beyond_drawn_support.tolist() == [3]
    assert legs.paths_trimmed_at_zero_throughput.tolist() == [2]
    assert legs.outgoing_legs_after_zero_left_out == 1
    assert legs.degenerate_legs_left_out == 1

    pairs = legs.points.reshape(-1, 2, 3)
    assert np.array_equal(pairs[1, 1], pairs[2, 0]), "a bounce is duplicated rather than smoothed through"
    point_power = np.repeat(legs.leg_throughput, 2).reshape(-1, 2)
    assert np.array_equal(point_power[:, 0], point_power[:, 1]), "each physical leg has one constant throughput"
    assert np.linalg.norm(pairs[0, 1, :2]) > 110.0, "a direct sky proxy may extend beyond the support"
    assert not np.any(legs.path_index == 3), "a path may not turn beyond the displayed support"
    assert not np.any((legs.path_index == 2) & (legs.leg_index > 0)), "no leg leaves a zero-throughput vertex"


def test_zero_throughput_escape_is_sorted_as_stopped_in_the_scene() -> None:
    payload = ray_leg_payload()
    bundles = ray_bundles(payload, ["sky", "roulette", "truncated"])
    assert bundles["stopped_in_the_scene"][2]
    assert not any(bundle[2] for name, bundle in bundles.items() if name != "stopped_in_the_scene")


def test_only_the_escaped_display_proxy_is_shortened() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [5.0, 0.0, 0.0],
            [5.0, 0.0, 0.0],
            [105.0, 0.0, 0.0],
        ]
    )
    moved = shorten_sky_legs(points, np.array([2, 2]), reach=30.0, escaped_final=np.array([False, True]))
    assert np.array_equal(moved[:2], points[:2])
    assert np.array_equal(moved[2], points[2])
    assert np.linalg.norm(moved[3] - moved[2]) == pytest.approx(30.0)


def test_next_event_keeps_a_live_terminal_scattering_vertex_without_an_outgoing_leg() -> None:
    payload = ray_leg_payload()
    keep = supported_live_scattering_vertices(
        payload,
        np.array([4, 2, 3]),
        np.array([1, 1, 1]),
        np.array([3]),
    )
    assert keep.tolist() == [True, False, False]

    with pytest.raises(ValueError, match="terminal marker"):
        supported_live_scattering_vertices(payload, np.array([0]), np.array([1]), np.zeros(0, dtype=int))


BLENDER = pathlib.Path.home() / "blender-4.5" / "blender"


@pytest.mark.skipif(not BLENDER.is_file(), reason="Blender is not installed at the default location")
def test_hair_curves_are_poly_and_evaluated_bounds_do_not_overshoot(tmp_path: pathlib.Path) -> None:
    """Exercise Blender's evaluated geometry, where the old Catmull curve failed."""
    study = pathlib.Path(__file__).resolve().parents[1]
    report = tmp_path / "curves.json"
    script = tmp_path / "curve_probe.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import json
            import pathlib
            import sys

            import bpy
            import numpy as np

            sys.path.insert(0, {str(study)!r})
            from semantic_twin.viz.blender.scene import build_curves

            bpy.ops.wm.read_factory_settings(use_empty=True)
            collection = bpy.data.collections.new("probe")
            bpy.context.scene.collection.children.link(collection)
            points = np.array([[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 0.0, 4.0], [8.0, 0.0, 4.0]])
            obj = build_curves("probe", points, np.array([4]), np.full(4, 0.1), collection)
            empty = build_curves("empty", np.zeros((0, 3)), np.zeros(0, dtype=int), np.zeros(0), collection)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            depsgraph.update()
            evaluated = obj.evaluated_get(depsgraph)
            bounds = np.asarray(evaluated.bound_box)
            curve_type = obj.data.attributes["curve_type"]
            pathlib.Path({str(report)!r}).write_text(json.dumps({{
                "curve_type": [item.value for item in curve_type.data],
                "minimum": bounds.min(axis=0).tolist(),
                "maximum": bounds.max(axis=0).tolist(),
                "empty_type": empty.type,
                "empty_placeholder": bool(empty.get("empty_curve_placeholder")),
            }}))
            """
        )
    )
    result = subprocess.run(
        [str(BLENDER), "--background", "--factory-startup", "--python", str(script)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    measured = json.loads(report.read_text())
    assert measured["curve_type"] == [1]
    assert measured["empty_type"] == "MESH"
    assert measured["empty_placeholder"]
    assert np.all(np.asarray(measured["minimum"]) >= np.array([-0.11, -0.11, -0.11]))
    assert np.all(np.asarray(measured["maximum"]) <= np.array([8.11, 0.11, 4.11]))


def test_octahedra_build_one_closed_marker_per_centre() -> None:
    centres = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, -4.0, 3.0]])
    vertices, faces = octahedra(centres, 2.0)
    assert vertices.shape == (18, 3)
    assert faces.shape == (24, 3)
    for i, centre in enumerate(centres):
        block = vertices[6 * i : 6 * (i + 1)]
        assert np.allclose(block.mean(axis=0), centre)
        assert np.allclose(np.linalg.norm(block - centre, axis=1), 2.0)
        # No facet may reach across to a neighbouring marker.
        assert faces[8 * i : 8 * (i + 1)].min() >= 6 * i
        assert faces[8 * i : 8 * (i + 1)].max() < 6 * (i + 1)


class FakeTwin:
    """A Blender object stand in with one blocking wall, for the camera search.

    ``ray_cast`` is the only thing ``clear_view`` uses, and a real Blender scene
    would take a hundred times longer to build than the thing being tested.
    """

    def __init__(self, blocked_azimuth_deg: float, half_width_deg: float, wall_distance_m: float) -> None:
        self.blocked = blocked_azimuth_deg
        self.half_width = half_width_deg
        self.distance = wall_distance_m
        self.data = None

    def ray_cast(self, origin, direction, distance=None):
        direction = np.asarray(direction, dtype=np.float64)
        azimuth = np.degrees(np.arctan2(direction[1], direction[0])) % 360.0
        delta = abs((azimuth - self.blocked + 180.0) % 360.0 - 180.0)
        if delta > self.half_width or self.distance > (distance or np.inf):
            return False, None, None, -1
        return True, np.asarray(origin, dtype=np.float64) + direction * self.distance, None, 0


def test_clear_view_avoids_a_blocked_bearing_rather_than_shortening_it() -> None:
    """The repair that does not work, pinned so it cannot come back.

    Casting along the wanted bearing and stopping short of the wall parks the
    camera inside its own subject. The search has to leave the blocked sector.
    """
    module = scene_module()
    twin = FakeTwin(blocked_azimuth_deg=225.0, half_width_deg=40.0, wall_distance_m=8.0)
    subject = np.zeros(3)
    location = module.clear_view(twin, subject, 85.0, (28.0, 40.0, 55.0))

    reach = float(np.linalg.norm(location - subject))
    assert reach == pytest.approx(85.0, abs=0.5), "the camera settled inside the wall's sector"
    azimuth = np.degrees(np.arctan2(location[1], location[0])) % 360.0
    assert abs((azimuth - 225.0 + 180.0) % 360.0 - 180.0) > 40.0


def test_clear_view_prefers_the_lowest_open_elevation() -> None:
    """With everything open, the search must not climb for no reason.

    A three quarter view is the readable one and overhead is the fallback, so
    ties have to break downwards or every site gets a plan view.
    """
    module = scene_module()

    class OpenTwin:
        data = None

        def ray_cast(self, origin, direction, distance=None):
            return False, None, None, -1

    location = module.clear_view(OpenTwin(), np.zeros(3), 85.0, (28.0, 40.0, 55.0, 72.0))
    elevation = np.degrees(np.arcsin(location[2] / np.linalg.norm(location)))
    assert elevation == pytest.approx(28.0, abs=0.5)


def test_clear_view_climbs_when_every_bearing_at_low_elevation_is_shut() -> None:
    """A canyon has one open direction and it is up. The search has to find it."""
    module = scene_module()

    class CanyonTwin:
        data = None

        def ray_cast(self, origin, direction, distance=None):
            direction = np.asarray(direction, dtype=np.float64)
            elevation = np.degrees(np.arcsin(direction[2]))
            if elevation >= 70.0:
                return False, None, None, -1
            return True, np.asarray(origin, dtype=np.float64) + direction * 6.0, None, 0

    location = module.clear_view(CanyonTwin(), np.zeros(3), 85.0, (28.0, 40.0, 55.0, 72.0))
    elevation = np.degrees(np.arcsin(location[2] / np.linalg.norm(location)))
    assert elevation == pytest.approx(72.0, abs=0.5)
    assert np.linalg.norm(location) == pytest.approx(85.0, abs=0.5)
