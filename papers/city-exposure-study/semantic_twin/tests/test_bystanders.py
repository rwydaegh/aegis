"""Tests for the bystander layer.

Two things need testing and they are different in kind. The Beer-Lambert law is
arithmetic with a closed form, so it is checked against exact targets. The
composite geometry is plumbing, and the failure mode of plumbing is silence, so
it is checked against a case where the answer is known by construction: a wall
placed across the sky must remove exactly the solid angle it covers, and the
face class of a hit must come back as the body class and not as a wall.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from semantic_twin.propagation import PlaneGeometry, SphereGeometry, fibonacci_sphere
from semantic_twin.propagation.bystanders import (
    ARMS,
    DENSITY_LADDER,
    EXCLUSION_RADIUS_M,
    FRUIN_WALKWAY_LOS,
    SQFT_M2,
    BodyLibrary,
    CompositeGeometry,
    Crowd,
    CrowdConfig,
    blocked_susceptibility,
    crowd_transmittance,
    extinction_length_m,
    load_body_library,
    mean_silhouette_width_m,
    near_horizon_share,
    projected_area_m2,
    sample_crowd,
    simplify,
    skin_permittivity,
    stature_library,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
BODIES = ROOT / "outputs" / "korenmarkt_dynamic_bodies"


# ---------------------------------------------------------------------------
# The extinction geometry, against hand computed targets
# ---------------------------------------------------------------------------


def test_a_body_shorter_than_the_observation_point_blocks_nothing_upward():
    """The whole result of this module turns on this one inequality."""
    length = extinction_length_m(
        np.radians([1.0, 5.0, 30.0]),
        observer_height_m=1.5,
        body_height_m=1.4,
        radius_m=30.0,
    )
    assert np.all(length == 0.0)


def test_upward_extinction_length_is_the_height_gap_over_the_tangent():
    elevation = np.radians([1.0, 2.0, 5.0, 20.0])
    length = extinction_length_m(
        elevation,
        observer_height_m=1.5,
        body_height_m=1.75,
        radius_m=1000.0,
    )
    expected = 0.25 / np.tan(elevation)
    assert np.allclose(length[:, 0], expected, rtol=1e-12)


def test_downward_extinction_stops_at_the_ground():
    """A falling ray is blockable until it reaches z = 0 and no further."""
    elevation = np.radians([-5.0, -20.0])
    length = extinction_length_m(
        elevation,
        observer_height_m=1.5,
        body_height_m=1.75,
        radius_m=1000.0,
    )
    assert np.allclose(length[:, 0], 1.5 / np.tan(-elevation), rtol=1e-12)


def test_downward_extinction_starts_where_the_ray_drops_below_the_body():
    """An observation point above the crowd is clear until the ray comes down."""
    elevation = np.radians([-10.0])
    length = extinction_length_m(
        elevation,
        observer_height_m=2.5,
        body_height_m=1.5,
        radius_m=1000.0,
    )
    near = 1.0 / np.tan(np.radians(10.0))
    far = 2.5 / np.tan(np.radians(10.0))
    assert length[0, 0] == pytest.approx(far - near, rel=1e-12)


def test_a_level_ray_is_blocked_over_the_whole_crowd_or_none_of_it():
    tall = extinction_length_m(np.array([0.0]), observer_height_m=1.5, body_height_m=1.75, radius_m=12.0)
    short = extinction_length_m(np.array([0.0]), observer_height_m=1.5, body_height_m=1.4, radius_m=12.0)
    assert tall[0, 0] == pytest.approx(12.0)
    assert short[0, 0] == 0.0


def test_the_exclusion_radius_and_the_crowd_radius_both_clip():
    elevation = np.radians([1.0])
    unclipped = extinction_length_m(
        elevation, observer_height_m=1.5, body_height_m=1.75, radius_m=1000.0, exclusion_radius_m=0.0
    )
    clipped = extinction_length_m(
        elevation, observer_height_m=1.5, body_height_m=1.75, radius_m=5.0, exclusion_radius_m=1.0
    )
    assert unclipped[0, 0] > 10.0
    assert clipped[0, 0] == pytest.approx(4.0)


def test_extinction_length_is_monotone_in_elevation_above_the_horizon():
    elevation = np.radians(np.linspace(0.2, 45.0, 200))
    length = extinction_length_m(
        elevation, observer_height_m=1.5, body_height_m=1.75, radius_m=30.0, exclusion_radius_m=0.0
    )[:, 0]
    assert np.all(np.diff(length) <= 1e-12)


# ---------------------------------------------------------------------------
# The Beer-Lambert law itself
# ---------------------------------------------------------------------------


def test_zero_density_transmits_everything():
    grid = fibonacci_sphere(256)
    transmittance = crowd_transmittance(
        grid, density_per_m2=0.0, width_m=[0.5], body_height_m=[1.75], observer_height_m=1.5
    )
    assert np.allclose(transmittance, 1.0)


def test_transmittance_matches_the_closed_form_at_one_elevation():
    elevation = np.radians(2.0)
    direction = np.array([[np.cos(elevation), 0.0, np.sin(elevation)]])
    density, width, height = 0.4, 0.55, 1.8
    transmittance = crowd_transmittance(
        direction,
        density_per_m2=density,
        width_m=[width],
        body_height_m=[height],
        observer_height_m=1.5,
        radius_m=100.0,
        exclusion_radius_m=0.0,
    )
    expected = np.exp(-density * width * (height - 1.5) / np.tan(elevation))
    assert transmittance[0] == pytest.approx(expected, rel=1e-12)


def test_transmittance_decreases_with_density():
    grid = fibonacci_sphere(512)
    previous = np.inf
    for density in DENSITY_LADDER:
        total = crowd_transmittance(
            grid, density_per_m2=density, width_m=[0.6], body_height_m=[1.75], observer_height_m=1.5
        ).sum()
        assert total < previous
        previous = total


def test_a_mixed_population_thins_the_field_rather_than_averaging_the_survival():
    """Two body types must enter the exponent, not the exponential."""
    elevation = np.radians(1.5)
    direction = np.array([[np.cos(elevation), 0.0, np.sin(elevation)]])
    widths = np.array([0.5, 0.7])
    heights = np.array([1.6, 1.9])
    mixed = crowd_transmittance(
        direction,
        density_per_m2=0.5,
        width_m=widths,
        body_height_m=heights,
        observer_height_m=1.5,
        radius_m=100.0,
        exclusion_radius_m=0.0,
    )[0]
    singles = [
        crowd_transmittance(
            direction,
            density_per_m2=0.5,
            width_m=[w],
            body_height_m=[h],
            observer_height_m=1.5,
            radius_m=100.0,
            exclusion_radius_m=0.0,
        )[0]
        for w, h in zip(widths, heights, strict=True)
    ]
    assert mixed == pytest.approx(np.sqrt(singles[0] * singles[1]), rel=1e-12)
    # The geometric mean, not the arithmetic one, and they are not close.
    assert mixed < np.mean(singles)


def test_the_cell_average_only_moves_the_band_where_transmittance_is_collapsing():
    """Sampling a convex, collapsing factor at the cell centre is not neutral."""
    grid = fibonacci_sphere(512)
    centre = crowd_transmittance(grid, density_per_m2=1.0, width_m=[0.6], body_height_m=[1.75], observer_height_m=1.5)
    averaged = crowd_transmittance(
        grid, density_per_m2=1.0, width_m=[0.6], body_height_m=[1.75], observer_height_m=1.5, cells=512
    )
    assert np.any(np.abs(averaged - centre) > 1e-4)
    assert np.all(averaged >= -1e-12) and np.all(averaged <= 1.0 + 1e-12)
    # Above 30 degrees a 1.75 m bystander would have to stand inside the
    # exclusion zone to be in the way, so nothing is blocked and the cell
    # average has nothing to correct.
    high = np.arcsin(grid[:, 2]) > np.radians(30.0)
    assert np.all(centre[high] == 1.0)
    assert np.all(averaged[high] == 1.0)


def test_mismatched_body_population_is_rejected():
    with pytest.raises(ValueError, match="paired per body"):
        crowd_transmittance(fibonacci_sphere(32), density_per_m2=1.0, width_m=[0.5, 0.6], body_height_m=[1.75])


def test_blocked_susceptibility_is_the_weighted_sum():
    rho = np.array([1.0, 2.0, 3.0])
    transmittance = np.array([1.0, 0.5, 0.0])
    assert blocked_susceptibility(rho, transmittance, 0.25) == pytest.approx(0.5)


def test_near_horizon_share_reads_off_the_grid():
    grid = fibonacci_sphere(1024)
    below = np.arcsin(grid[:, 2]) <= np.radians(5.0)
    rho = np.where(below, 2.0, 1.0)
    share = near_horizon_share(grid, rho, 4.0 * np.pi / 1024, 5.0)
    expected = 2.0 * below.sum() / (2.0 * below.sum() + (~below).sum())
    assert share == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# Materials and the literature constants
# ---------------------------------------------------------------------------


def test_skin_is_lossy_and_opaque_at_15_ghz():
    eps = skin_permittivity(15.0e9)
    assert eps.real > 20.0
    assert eps.imag < -10.0
    # One skin depth at 15 GHz is under a millimetre, so a body is opaque and
    # the tracer's treatment of it as a half space is the right one.
    from semantic_twin.propagation.tracer import fresnel_power_reflectance

    reflectance = fresnel_power_reflectance(np.array([1.0]), np.array([eps]))
    assert 0.3 < reflectance[0] < 0.7


def test_the_absorber_control_reflects_essentially_nothing():
    """The control material has to actually be the Beer-Lambert assumption.

    Beer-Lambert treats a bystander as a perfect absorber. The traced control
    only tests that assumption if the body class returns a ray with negligible
    throughput at the incidence angles a crowd is hit at, which for an observer
    at head height means everything from face on down to a few degrees off
    grazing.
    """
    from semantic_twin.propagation.bystanders import ABSORBER_PERMITTIVITY
    from semantic_twin.propagation.tracer import fresnel_power_reflectance

    cos_i = np.cos(np.radians(np.array([0.0, 30.0, 60.0, 80.0, 85.0])))
    reflectance = fresnel_power_reflectance(cos_i, np.full(cos_i.shape, ABSORBER_PERMITTIVITY))
    assert np.max(reflectance) < 1.0e-6
    skin = fresnel_power_reflectance(cos_i, np.full(cos_i.shape, skin_permittivity(15.0e9)))
    assert np.min(skin) > 0.4


def test_the_fruin_ladder_is_the_ladder_that_is_swept():
    """The density ladder must stay pinned to the level of service boundaries."""
    # Fruin's own numbers, in square feet per pedestrian at the crowded edge.
    assert FRUIN_WALKWAY_LOS["A"][0] / SQFT_M2 == pytest.approx(35.0)
    assert FRUIN_WALKWAY_LOS["E"][0] / SQFT_M2 == pytest.approx(5.0)
    assert FRUIN_WALKWAY_LOS["A"][1] == pytest.approx(0.3074, rel=1e-3)
    assert FRUIN_WALKWAY_LOS["E"][1] == pytest.approx(2.1528, rel=1e-3)
    for edge in (density for _, density in FRUIN_WALKWAY_LOS.values()):
        if edge != FRUIN_WALKWAY_LOS["B"][1]:
            assert edge in DENSITY_LADDER
    assert list(DENSITY_LADDER) == sorted(DENSITY_LADDER)


# ---------------------------------------------------------------------------
# Mesh handling
# ---------------------------------------------------------------------------


def _box(width: float = 0.5, depth: float = 0.3, height: float = 1.75) -> tuple[np.ndarray, np.ndarray]:
    """An axis aligned box standing on z = 0, as a stand in for a body."""
    x, y = width / 2.0, depth / 2.0
    vertices = np.array(
        [
            [-x, -y, 0.0],
            [x, -y, 0.0],
            [x, y, 0.0],
            [-x, y, 0.0],
            [-x, -y, height],
            [x, -y, height],
            [x, y, height],
            [-x, y, height],
        ]
    )
    faces = np.array(
        [
            [0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
        ]
    )  # fmt: skip
    return vertices, faces


def test_projected_area_of_a_box_is_the_azimuth_mean_of_its_two_faces():
    vertices, faces = _box(0.5, 0.3, 1.75)
    # For a convex prism of cross section perimeter P and height h the azimuth
    # averaged silhouette area is h*P/pi by Cauchy's formula.
    expected = 1.75 * (2.0 * (0.5 + 0.3)) / np.pi
    assert projected_area_m2(vertices, faces, samples=720) == pytest.approx(expected, rel=1e-3)


def test_mean_silhouette_width_of_a_box_is_its_perimeter_over_pi():
    vertices, _ = _box(0.5, 0.3, 1.75)
    assert mean_silhouette_width_m(vertices) == pytest.approx(2.0 * (0.5 + 0.3) / np.pi, rel=1e-12)


def test_simplify_leaves_a_mesh_already_under_target_alone():
    vertices, faces = _box()
    out_v, out_f = simplify(vertices, faces, 100)
    assert out_f.shape == faces.shape
    assert np.array_equal(out_v, vertices)


# ---------------------------------------------------------------------------
# Composite geometry
# ---------------------------------------------------------------------------


class _NoGeometry:
    """Nothing anywhere, so every ray escapes."""

    def intersect(self, origins, directions):  # noqa: ANN001, ANN202
        count = origins.shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, 1.0e30),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


def test_composite_takes_the_nearer_hit_and_offsets_the_face_index():
    inner = SphereGeometry(2.0)
    outer = SphereGeometry(5.0)
    composite = CompositeGeometry(outer, inner, base_face_count=7)
    origins = np.zeros((4, 3))
    directions = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])
    hit, distance, _, face = composite.intersect(origins, directions)
    assert np.all(hit)
    assert np.allclose(distance, 2.0)
    assert np.all(face == 7)


def test_composite_falls_back_to_the_base_where_the_overlay_misses():
    composite = CompositeGeometry(PlaneGeometry(0.0), _NoGeometry(), base_face_count=3)
    origins = np.array([[0.0, 0.0, 1.5]])
    directions = np.array([[0.0, 0.0, -1.0]])
    hit, distance, normal, face = composite.intersect(origins, directions)
    assert hit[0] and distance[0] == pytest.approx(1.5)
    assert face[0] == 0
    assert normal[0, 2] == pytest.approx(1.0)


def test_composite_reports_a_miss_when_neither_backend_hits():
    composite = CompositeGeometry(_NoGeometry(), _NoGeometry(), base_face_count=3)
    hit, distance, _, _ = composite.intersect(np.zeros((5, 3)), np.tile([0.0, 0.0, 1.0], (5, 1)))
    assert not np.any(hit)
    assert np.all(distance >= 1.0e30)


# ---------------------------------------------------------------------------
# Crowd placement
# ---------------------------------------------------------------------------


def _library(count: int = 3) -> BodyLibrary:
    vertices, faces = _box()
    heights = np.linspace(1.6, 1.9, count)
    return BodyLibrary(
        body_ids=tuple(f"box{i}" for i in range(count)),
        vertices=tuple(vertices * (h / 1.75) for h in heights),
        faces=tuple(faces for _ in range(count)),
        stature_m=heights,
        width_m=np.full(count, 2.0 * (0.5 + 0.3) / np.pi) * heights / 1.75,
        provenance={"synthetic": True},
    )


def test_a_crowd_on_flat_ground_hits_the_requested_density():
    library = _library()
    config = CrowdConfig(density_per_m2=0.3, max_radius_m=20.0, seed=3)
    crowd = sample_crowd(PlaneGeometry(0.0), np.zeros(2), 0.0, library, config)
    assert crowd.provenance["walkable_fraction"] == pytest.approx(1.0)
    assert crowd.achieved_density_per_m2 == pytest.approx(0.3, rel=0.02)


def test_the_hard_core_and_the_exclusion_zone_are_both_respected():
    library = _library()
    config = CrowdConfig(density_per_m2=1.5, max_radius_m=12.0, seed=5)
    crowd = sample_crowd(PlaneGeometry(0.0), np.zeros(2), 0.0, library, config)
    assert len(crowd) > 100
    separation = (
        np.linalg.norm(crowd.positions_xy[:, None, :] - crowd.positions_xy[None, :, :], axis=2)
        + np.eye(len(crowd)) * 1e6
    )
    assert separation.min() >= config.min_separation_m - 1e-9
    assert np.linalg.norm(crowd.positions_xy, axis=1).min() >= EXCLUSION_RADIUS_M - 1e-9


def test_an_empty_crowd_leaves_the_scene_untouched():
    from semantic_twin.propagation.bystanders import crowd_geometry

    library = _library()
    config = CrowdConfig(density_per_m2=0.0, max_radius_m=10.0, seed=1)
    crowd = sample_crowd(PlaneGeometry(0.0), np.zeros(2), 0.0, library, config)
    assert len(crowd) == 0
    site = PlaneGeometry(0.0)
    face_class = np.zeros(4, dtype=np.int64)
    geometry, classes = crowd_geometry(site, crowd, library, face_class, 9)
    assert geometry is site
    assert np.array_equal(classes, face_class)


def test_bodies_stand_on_the_ground_at_their_own_yaw():
    library = _library()
    config = CrowdConfig(density_per_m2=0.05, max_radius_m=10.0, seed=11)
    crowd = sample_crowd(PlaneGeometry(3.25), np.zeros(2), 3.25, library, config)
    vertices, faces = crowd.to_mesh(library)
    assert faces.max() == vertices.shape[0] - 1
    assert vertices[:, 2].min() == pytest.approx(3.25)
    per_body = vertices.shape[0] // len(crowd)
    for i in range(len(crowd)):
        block = vertices[i * per_body : (i + 1) * per_body]
        assert block[:, 2].min() == pytest.approx(3.25)
        assert np.allclose(block[:, :2].mean(axis=0), crowd.positions_xy[i], atol=1e-9)


def test_yaw_is_a_rigid_rotation():
    library = _library(1)
    crowd = Crowd(
        positions_xy=np.array([[0.0, 0.0]]),
        ground_z_m=np.zeros(1),
        yaw_rad=np.array([0.7]),
        shape_index=np.zeros(1, dtype=np.int64),
        radius_m=10.0,
        config=CrowdConfig(density_per_m2=0.1),
    )
    vertices, _ = crowd.to_mesh(library)
    source = library.vertices[0]
    assert np.allclose(np.sort(np.linalg.norm(vertices, axis=1)), np.sort(np.linalg.norm(source, axis=1)))
    assert mean_silhouette_width_m(vertices) == pytest.approx(mean_silhouette_width_m(source), rel=1e-9)


# ---------------------------------------------------------------------------
# The reconstructions on disk
# ---------------------------------------------------------------------------

pytestmark_bodies = pytest.mark.skipif(not BODIES.exists(), reason="no reconstructed bodies on disk")


@pytest.mark.skipif(not BODIES.exists(), reason="no reconstructed bodies on disk")
def test_the_reconstructed_library_loads_and_keeps_its_silhouette():
    library = load_body_library(BODIES, target_faces=600)
    assert len(library) >= 10
    assert library.provenance["silhouette_area_change_max_abs_fraction"] < 0.03
    assert np.all(library.stature_m > 1.2)
    assert 0.4 < float(np.mean(library.width_m)) < 0.8
    for vertices in library.vertices:
        assert vertices[:, 2].min() == pytest.approx(0.0, abs=1e-9)
        assert np.allclose(vertices[:, :2].mean(axis=0), 0.0, atol=1e-9)


@pytest.mark.skipif(not BODIES.exists(), reason="no reconstructed bodies on disk")
def test_the_reconstructions_are_shorter_than_the_adults_they_stand_in_for():
    """The caveat the study reports, asserted rather than remembered."""
    library = load_body_library(BODIES, target_faces=600)
    assert float(np.median(library.stature_m)) < 1.65
    adult = stature_library(library, "adult", seed=0)
    assert float(np.median(adult.stature_m)) > 1.68
    # Uniform scaling, so the width tracks the height and the two stay paired.
    assert np.allclose(adult.width_m / adult.stature_m, library.width_m / library.stature_m)


@pytest.mark.skipif(not BODIES.exists(), reason="no reconstructed bodies on disk")
def test_a_taller_crowd_blocks_strictly_more():
    library = load_body_library(BODIES, target_faces=300)
    adult = stature_library(library, "adult", seed=0)
    grid = fibonacci_sphere(512)
    short = crowd_transmittance(
        grid,
        density_per_m2=0.72,
        width_m=library.width_m,
        body_height_m=library.stature_m,
        observer_height_m=1.5,
        cells=512,
    )
    tall = crowd_transmittance(
        grid,
        density_per_m2=0.72,
        width_m=adult.width_m,
        body_height_m=adult.stature_m,
        observer_height_m=1.5,
        cells=512,
    )
    assert np.all(tall <= short + 1e-12)
    assert tall.sum() < short.sum()


def test_the_arm_names_are_the_ones_the_rows_carry():
    assert ARMS == ("full", "walkable", "nominal")
