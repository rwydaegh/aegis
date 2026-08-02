"""The payload stage of the propagation walkthrough blend.

Only the parts that turn a physical model into something drawable are tested
here. The tracing itself is covered by ``tests/test_propagation.py`` and the
recorder is asserted there to leave every traced number bit identical.
"""

from __future__ import annotations

import numpy as np
import pytest

from export_propagation_payload import (
    HEIGHT_BAND_M,
    RANGE_BAND_M,
    crop_for_drawing,
    network_markers,
    sphere_triangulation,
)
from semantic_twin.propagation.directions import MODELS, elevation_band_measure, fibonacci_sphere

#: Integrated per band, never sampled at the midpoint. The reason lives in the
#: docstring of the library function, which this file used to carry its own copy
#: of and now shares with the tests of the law itself.
band_measure = elevation_band_measure


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


def blender_module():
    """Import the Blender stage with ``bpy`` stubbed out.

    Its module level is deliberately free of ``bpy`` calls so the pure geometry
    in it stays testable outside Blender. Shelling out to a headless Blender to
    check a rotation matrix would take a hundred times longer and prove less.
    """
    import importlib.util
    import pathlib
    import sys
    import types

    if "bpy" not in sys.modules:
        stub = types.ModuleType("bpy")
        stub.types = types.SimpleNamespace(Object=object, Collection=object, Material=object)
        sys.modules["bpy"] = stub
    path = pathlib.Path(__file__).resolve().parent.parent / "propagation_blender.py"
    spec = importlib.util.spec_from_file_location("propagation_blender", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_camera_rotation_actually_points_at_the_target() -> None:
    """Rebuild the rotation and check it maps the camera axis onto the sight line."""
    module = blender_module()
    rng = np.random.default_rng(7)
    for _ in range(64):
        location = rng.uniform(-200.0, 200.0, size=3)
        target = rng.uniform(-200.0, 200.0, size=3)
        if np.linalg.norm(target - location) < 1.0:
            continue
        rx, ry, rz = module.camera_rotation(location, target)
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
    module = blender_module()
    values = np.array([-5.0, 0.0, 0.25, 0.5, 0.75, 1.0, 5.0])
    rgba = module.colour_ramp(values, 0.0, 1.0)
    assert rgba.shape == (values.size, 4)
    assert np.allclose(rgba[:, 3], 1.0)
    assert np.allclose(rgba[0], rgba[1])
    assert np.allclose(rgba[-1], rgba[-2])
    # Inferno rises monotonically in luminance across its whole range.
    luminance = rgba[1:-1] @ np.array([0.2126, 0.7152, 0.0722, 0.0])
    assert np.all(np.diff(luminance) > 0.0)


def test_ray_bundles_are_exclusive_and_exhaustive() -> None:
    module = blender_module()
    rng = np.random.default_rng(3)
    count = 500
    directions = rng.normal(size=(count, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    payload = {
        "path_termination": rng.integers(0, 3, size=count),
        "path_bounces": rng.integers(0, 5, size=count),
        "path_exit_direction": directions,
    }
    bundles = module.ray_bundles(payload, ["sky", "roulette", "truncated"])
    stacked = np.stack(list(bundles.values()))
    assert np.array_equal(stacked.sum(axis=0), np.ones(count, dtype=int))
    assert set(bundles) == set(module.RAY_STYLE)


def test_octahedra_build_one_closed_marker_per_centre() -> None:
    module = blender_module()
    centres = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, -4.0, 3.0]])
    vertices, faces = module.octahedra(centres, 2.0)
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
    module = blender_module()
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
    module = blender_module()

    class OpenTwin:
        data = None

        def ray_cast(self, origin, direction, distance=None):
            return False, None, None, -1

    location = module.clear_view(OpenTwin(), np.zeros(3), 85.0, (28.0, 40.0, 55.0, 72.0))
    elevation = np.degrees(np.arcsin(location[2] / np.linalg.norm(location)))
    assert elevation == pytest.approx(28.0, abs=0.5)


def test_clear_view_climbs_when_every_bearing_at_low_elevation_is_shut() -> None:
    """A canyon has one open direction and it is up. The search has to find it."""
    module = blender_module()

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
