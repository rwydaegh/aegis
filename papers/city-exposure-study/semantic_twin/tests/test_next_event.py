"""What the next event estimator has to survive.

The connection is the whole physics of `semantic_twin.illumination.sources`, so it
is checked against a case with an answer known in closed form, and against the
two numerical traps that were found the expensive way while building it.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.illumination import ISOTROPIC
from semantic_twin.propagation.geometry import PlaneGeometry
from semantic_twin.illumination.sources import SourceSet
from semantic_twin.transport.tracer import SbrTracer, TraceConfig
from semantic_twin.transport.next_event import NextEventEstimator, NextEventField, NextEventGather, _direct_field_masses
from semantic_twin.transport.directional import DirectionalMeasure
from semantic_twin.transport.observers import MultiGather


def one_site(height_m: float) -> SourceSet:
    return SourceSet(
        positions=np.array([[0.0, 0.0, height_m]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )


class OpenSky:
    """Controlled geometry with exact visibility and no tracer intersections."""

    def intersect(self, origins: np.ndarray, directions: np.ndarray) -> tuple[np.ndarray, ...]:
        count = np.asarray(origins).shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, 1.0e30),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


class CountingSky(OpenSky):
    def __init__(self) -> None:
        self.counts: list[int] = []

    def intersect(self, origins: np.ndarray, directions: np.ndarray) -> tuple[np.ndarray, ...]:
        self.counts.append(int(np.asarray(origins).shape[0]))
        return super().intersect(origins, directions)


def bounce_over_plane(
    source_height_m: float,
    head_height_m: float,
    *,
    rays: int = 200_000,
    seed: int = 3,
    lift_m: float = 1.0e-2,
) -> float:
    """One bounce off an infinite Lambertian plane, by the estimator."""
    plane = PlaneGeometry(0.0)
    config = TraceConfig(rays=rays, max_bounces=2, seed=seed, local_cells=256)
    # A perfect conductor reflects everything, and a metre of roughness against a
    # two centimetre wavelength leaves no coherent share at all, so the surface
    # is a pure Lambertian of reflectance 1 and the closed form has no material
    # constants left in it.
    tracer = SbrTracer(plane, None, np.array([PEC_PERMITTIVITY]), np.array([1.0]), config)
    gather = NextEventGather(
        geometry=plane,
        sources=one_site(source_height_m),
        rng=np.random.default_rng(seed),
        samples=1,
        max_order=2,
        lift_m=lift_m,
    )
    tracer.trace(
        np.array([0.0, 0.0, head_height_m]),
        {"isotropic": ISOTROPIC},
        ground_z_m=0.0,
        seed=seed,
        gather=gather,
    )
    return gather.chi_bounce()


@pytest.mark.parametrize(
    ("source_height_m", "head_height_m"),
    [(20.0, 10.0), (10.0, 10.0), (30.0, 1.5), (12.0, 6.0)],
)
def test_one_bounce_off_a_plane_matches_the_closed_form(source_height_m, head_height_m):
    """A point source and a head over an infinite Lambertian plane.

    Put the source at height ``a`` and the head at height ``b`` on the same
    vertical. The once bounced radiance arriving at the head integrates over the
    sphere to ``2 R / (a + b)**2`` exactly, for reflectance ``R``.

    The derivation is short enough to keep here. Irradiance on the plane at
    radius ``p`` from the foot is ``a / (p**2 + a**2)**1.5``, the Lambertian lobe
    turns it into radiance ``R / pi`` times that, and the head subtends
    ``b / (p**2 + b**2)**1.5`` per unit area. Integrating over the plane in
    ``u = p**2`` gives ``R a b`` times ``2 / (a b (a + b)**2)``.

    This is the test that would catch a missing cosine, a missing ``1/pi``, or the
    ``4 pi`` of the solid angle measure being dropped or doubled, none of which
    any amount of staring at a city mesh would reveal.
    """
    target = 2.0 / (source_height_m + head_height_m) ** 2
    measured = bounce_over_plane(source_height_m, head_height_m)
    assert measured == pytest.approx(target, rel=0.03)


def test_the_estimator_lands_on_the_closed_form_from_several_seeds():
    """Within its own noise, not just once by luck."""
    target = 2.0 / (20.0 + 10.0) ** 2
    values = np.array([bounce_over_plane(20.0, 10.0, rays=100_000, seed=s) for s in range(5)])
    assert values.std() / values.mean() < 0.05
    assert values.mean() == pytest.approx(target, rel=0.02)


def test_nothing_arrives_when_the_source_is_under_the_plane():
    """A site below an opaque plane is not reachable from above it."""
    assert bounce_over_plane(-20.0, 10.0) == 0.0


def test_an_empty_source_set_contributes_nothing():
    plane = PlaneGeometry(0.0)
    config = TraceConfig(rays=2_000, max_bounces=2, seed=1, local_cells=64)
    tracer = SbrTracer(plane, None, np.array([PEC_PERMITTIVITY]), np.array([1.0]), config)
    empty = SourceSet(positions=np.empty((0, 3)), cell_m=1.0, dims=3, azimuths=0, builders=0)
    gather = NextEventGather(geometry=plane, sources=empty, rng=np.random.default_rng(1), max_order=2)
    tracer.trace(np.array([0.0, 0.0, 5.0]), {"isotropic": ISOTROPIC}, ground_z_m=0.0, seed=1, gather=gather)
    assert gather.chi_bounce() == 0.0
    assert gather.connections == 0


def test_attaching_the_gather_does_not_move_the_traced_result():
    """The invariant the tracer's own docstring promises.

    The connection draws from its own generator and touches no accumulator, so a
    trace has to come out bit identical with it attached and without it. If this
    ever fails, every number in the study computed alongside a connection is a
    different number from the one computed without.
    """
    plane = PlaneGeometry(0.0)
    config = TraceConfig(rays=20_000, max_bounces=3, seed=9, local_cells=128)
    models = {"isotropic": ISOTROPIC}

    tracer = SbrTracer(plane, None, np.array([PEC_PERMITTIVITY]), np.array([1.0]), config)
    plain = tracer.trace(np.array([0.0, 0.0, 5.0]), models, ground_z_m=0.0, seed=9)

    tracer = SbrTracer(plane, None, np.array([PEC_PERMITTIVITY]), np.array([1.0]), config)
    gather = NextEventGather(geometry=plane, sources=one_site(30.0), rng=np.random.default_rng(4), max_order=3)
    watched = tracer.trace(np.array([0.0, 0.0, 5.0]), models, ground_z_m=0.0, seed=9, gather=gather)

    assert gather.chi_bounce() > 0.0
    assert watched.susceptibility["isotropic"] == plain.susceptibility["isotropic"]
    assert np.array_equal(watched.rho["isotropic"], plain.rho["isotropic"])
    assert watched.sky_fraction == plain.sky_fraction


def test_more_connections_per_vertex_lower_the_noise_and_not_the_answer():
    """Connecting k times per vertex is an average, not a k fold contribution."""
    one = np.array([bounce_over_plane(20.0, 10.0, rays=40_000, seed=s) for s in range(6)])

    plane = PlaneGeometry(0.0)
    many = []
    for seed in range(6):
        config = TraceConfig(rays=40_000, max_bounces=2, seed=seed, local_cells=256)
        tracer = SbrTracer(plane, None, np.array([PEC_PERMITTIVITY]), np.array([1.0]), config)
        gather = NextEventGather(
            geometry=plane,
            sources=one_site(20.0),
            rng=np.random.default_rng(seed),
            samples=8,
            max_order=2,
        )
        tracer.trace(
            np.array([0.0, 0.0, 10.0]),
            {"isotropic": ISOTROPIC},
            ground_z_m=0.0,
            seed=seed,
            gather=gather,
        )
        many.append(gather.chi_bounce())
    many = np.array(many)

    assert many.mean() == pytest.approx(one.mean(), rel=0.03)
    assert many.std() < one.std()


def test_the_bounced_term_lands_in_the_order_it_was_scattered():
    """A flat plane can only be hit once, so everything is first order.

    A cosine lobe leaving a flat plane goes up and never comes back, so any
    weight appearing at second order would mean the order bookkeeping is off by
    one, which is the kind of error that hides perfectly inside a total.
    """
    plane = PlaneGeometry(0.0)
    config = TraceConfig(rays=50_000, max_bounces=3, seed=2, local_cells=128)
    tracer = SbrTracer(plane, None, np.array([PEC_PERMITTIVITY]), np.array([1.0]), config)
    gather = NextEventGather(geometry=plane, sources=one_site(20.0), rng=np.random.default_rng(2), max_order=3)
    tracer.trace(np.array([0.0, 0.0, 10.0]), {"isotropic": ISOTROPIC}, ground_z_m=0.0, seed=2, gather=gather)
    by_order = gather.chi_by_order()
    assert by_order[0] == 0.0
    assert by_order[1] > 0.0
    assert np.all(by_order[2:] == 0.0)


def test_the_plane_answer_does_not_care_where_the_connection_starts():
    """The counterpart of the city measurement, on geometry that cannot lie.

    On a real mesh the connection start has to be lifted off the surface, and
    that lift was worth 1.8 dB until the sites themselves were lifted clear. A
    flat plane has no lumps and no tangency, so here the lift has to be worth
    nothing at all. That is what separates a numerical artefact from physics.
    """
    values = np.array([bounce_over_plane(20.0, 10.0, rays=100_000, lift_m=lift) for lift in (0.0, 1e-3, 1e-2, 1e-1)])
    assert values.max() / values.min() < 1.01


def test_direct_field_uses_receiver_directions_and_explicit_source_weights():
    geometry = OpenSky()
    sources = SourceSet(
        positions=np.array([[3.0, 0.0, 0.0], [0.0, 0.0, 8.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
        source_weights=np.array([1.0, 3.0]),
    )
    grid = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    masses, seen = _direct_field_masses(geometry, np.zeros(3), sources, grid)
    assert masses == pytest.approx([0.25 / 9.0, 0.75 / 64.0])
    assert seen == pytest.approx(1.0)


def test_field_bounced_deposits_follow_original_launch_cells():
    geometry = OpenSky()
    sources = one_site(10.0)
    grid = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
    gather = NextEventGather(
        geometry=geometry,
        sources=sources,
        rng=np.random.default_rng(1),
        max_order=2,
        field_grid=grid,
    )
    gather.begin(np.zeros(3), 2)
    gather.set_launch_cells(np.array([0, 1]))
    gather.vertex(
        index=np.array([0, 1]),
        position=np.zeros((2, 3)),
        incoming=np.tile([0.0, 0.0, -1.0], (2, 1)),
        normal=np.tile([0.0, 0.0, 1.0], (2, 1)),
        throughput=np.array([1.0, 2.0]),
        share=np.zeros(2),
        order=np.ones(2, dtype=np.int64),
        path_length=np.ones(2),
    )
    field = gather.field()
    expected = np.array([0.02, 0.04])
    assert field.bounced_mass == pytest.approx(expected)
    assert field.bounced == pytest.approx(gather.chi_bounce(), rel=1.0e-14)
    assert field.arrival_directions == pytest.approx(-grid)


def test_field_direction_sign_matches_body_coupler_reciprocity():
    grid = np.array([[1.0, 0.0, 0.0]])
    field = NextEventGather(
        geometry=OpenSky(),
        sources=one_site(10.0),
        rng=np.random.default_rng(0),
        field_grid=grid,
    ).field(np.array([1.0]))
    body_normal = np.array([1.0, 0.0, 0.0])
    # BodyCoupler constructs k_hat=-local_grid and evaluates n dot (-k_hat).
    assert np.dot(body_normal, -field.arrival_directions[0]) == pytest.approx(1.0)
    assert field.normalized_density("direct", field.direct)[0] == pytest.approx(1.0 / field.solid_angle)


@pytest.mark.parametrize(
    "grid",
    [np.array([[0.0, 0.0, 0.0]]), np.array([[2.0, 0.0, 0.0]])],
)
def test_next_event_field_rejects_zero_or_nonunit_grid_directions(grid: np.ndarray) -> None:
    with pytest.raises(ValueError, match="(positive|unit)"):
        NextEventField(grid, 4.0 * np.pi, np.zeros(1), np.zeros(1))
    with pytest.raises(ValueError, match="(positive|unit)"):
        NextEventGather(
            geometry=OpenSky(),
            sources=one_site(10.0),
            rng=np.random.default_rng(0),
            field_grid=grid,
        )


def test_multi_gather_forwards_launch_cells_only_to_field_observers():
    field_gather = NextEventGather(
        geometry=OpenSky(),
        sources=one_site(10.0),
        rng=np.random.default_rng(0),
        field_grid=np.array([[0.0, 0.0, 1.0]]),
    )

    class ScalarObserver:
        def begin(self, origin: np.ndarray, count: int) -> None:
            del origin, count

        def vertex(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

    combined = MultiGather((ScalarObserver(), field_gather))
    cells = np.array([3, 7], dtype=np.int64)
    combined.begin(np.zeros(3), cells.size)
    combined.set_launch_cells(cells)
    assert field_gather._launch_cells is not None
    assert np.array_equal(field_gather._launch_cells, cells)


def test_estimate_field_conserves_direct_and_bounced_scalars_across_batches():
    geometry = PlaneGeometry(0.0)
    config = TraceConfig(rays=2_000, batch=137, max_bounces=2, seed=5, local_cells=32)
    tracer = SbrTracer(geometry, None, np.array([PEC_PERMITTIVITY]), np.array([1.0]), config)
    sources = SourceSet(
        positions=np.array([[0.0, 0.0, 20.0], [8.0, 0.0, 18.0]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
        source_weights=np.array([1.0, 2.0]),
    )
    estimator = NextEventEstimator(tracer, geometry, sources, samples=2)
    scalar = estimator.estimate(np.array([0.0, 0.0, 10.0]), seed=11)
    with_field, field = estimator.estimate_field(np.array([0.0, 0.0, 10.0]), seed=11)
    assert with_field == scalar
    assert field.direct == pytest.approx(scalar.direct, rel=1.0e-14, abs=1.0e-15)
    expected_atoms = np.array([1.0 / (3.0 * 10.0**2), (2.0 / 3.0) / (8.0**2 + 8.0**2)])
    expected_directions = np.array([[0.0, 0.0, -1.0], [-8.0, 0.0, -8.0]])
    expected_directions[1] /= np.linalg.norm(expected_directions[1])
    np.testing.assert_allclose(field.direct_atom_mass, expected_atoms, rtol=1.0e-14, atol=1.0e-15)
    np.testing.assert_allclose(field.direct_k_hat, expected_directions, rtol=1.0e-14, atol=1.0e-15)
    assert field.direct_atoms == pytest.approx(scalar.direct, rel=1.0e-14, abs=1.0e-15)
    assert field.direct_mass.sum() == pytest.approx(scalar.direct, rel=1.0e-14, abs=1.0e-15)
    assert field.bounced == pytest.approx(scalar.bounced, rel=1.0e-14, abs=1.0e-15)
    assert field.total == pytest.approx(scalar.total, rel=1.0e-14, abs=1.0e-15)
    assert np.sum(field.direct_density) * field.solid_angle == pytest.approx(scalar.direct)
    assert np.sum(field.bounced_density) * field.solid_angle == pytest.approx(scalar.bounced)
    assert field.diagnostic and field.missing_specular and not field.includes_specular
    measure = field.directional_measure(1.0)
    assert measure.atomic_total == pytest.approx(scalar.direct, rel=1.0e-14, abs=1.0e-15)
    assert measure.diffuse_total == pytest.approx(scalar.bounced, rel=1.0e-14, abs=1.0e-15)
    assert measure.diffuse_k_hat == pytest.approx(-field.local_grid)


def test_directional_measure_keeps_direct_atoms_out_of_diffuse_grid():
    field = NextEventGather(
        geometry=OpenSky(),
        sources=one_site(10.0),
        rng=np.random.default_rng(0),
        field_grid=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
    ).field(
        np.array([0.25, 0.0]),
        direct_k_hat=np.array([[0.0, 0.0, -1.0]]),
        direct_atom_mass=np.array([0.25]),
    )
    measure = field.directional_measure(0.5, reference_id="fixture")
    assert isinstance(measure, DirectionalMeasure)
    assert measure.reference_id == "fixture"
    np.testing.assert_allclose(measure.atom_k_hat, [[0.0, 0.0, -1.0]])
    assert measure.atom_mass == pytest.approx([0.5])
    assert measure.diffuse_mass == pytest.approx([0.0, 0.0])
    assert measure.total_transfer == pytest.approx(field.total / 0.5)
    with pytest.raises(ValueError, match="reference_transfer"):
        field.directional_measure(0.0)


def test_directional_measure_validates_components():
    valid = dict(
        atom_k_hat=np.empty((0, 3)),
        atom_mass=np.empty(0),
        diffuse_k_hat=np.empty((0, 3)),
        diffuse_mass=np.empty(0),
    )
    DirectionalMeasure(**valid)
    with pytest.raises(ValueError, match="unit"):
        DirectionalMeasure(
            atom_k_hat=np.array([[2.0, 0.0, 0.0]]),
            atom_mass=np.array([1.0]),
            diffuse_k_hat=np.empty((0, 3)),
            diffuse_mass=np.empty(0),
        )
    with pytest.raises(ValueError, match="nonnegative"):
        DirectionalMeasure(
            atom_k_hat=np.array([[1.0, 0.0, 0.0]]),
            atom_mass=np.array([-1.0]),
            diffuse_k_hat=np.empty((0, 3)),
            diffuse_mass=np.empty(0),
        )
    with pytest.raises(ValueError, match="shape"):
        DirectionalMeasure(
            atom_k_hat=np.array([1.0, 0.0, 0.0]),
            atom_mass=np.array([1.0]),
            diffuse_k_hat=np.empty((0, 3)),
            diffuse_mass=np.empty(0),
        )
    with pytest.raises(ValueError, match="finite"):
        DirectionalMeasure(
            atom_k_hat=np.array([[np.nan, 0.0, 0.0]]),
            atom_mass=np.array([1.0]),
            diffuse_k_hat=np.empty((0, 3)),
            diffuse_mass=np.empty(0),
        )
    with pytest.raises(ValueError, match="positive"):
        DirectionalMeasure(
            atom_k_hat=np.array([[0.0, 0.0, 0.0]]),
            atom_mass=np.array([1.0]),
            diffuse_k_hat=np.empty((0, 3)),
            diffuse_mass=np.empty(0),
        )
    with pytest.raises(ValueError, match="finite"):
        DirectionalMeasure(
            atom_k_hat=np.array([[1.0, 0.0, 0.0]]),
            atom_mass=np.array([np.nan]),
            diffuse_k_hat=np.empty((0, 3)),
            diffuse_mass=np.empty(0),
        )


def test_field_direct_atoms_use_one_source_visibility_pass():
    geometry = CountingSky()
    sources = SourceSet(
        positions=np.column_stack((np.arange(5, dtype=np.float64), np.zeros(5), np.full(5, 10.0))),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )
    config = TraceConfig(rays=32, batch=32, max_bounces=1, seed=2, local_cells=16)
    tracer = SbrTracer(geometry, None, np.array([PEC_PERMITTIVITY]), np.array([1.0]), config)
    estimator = NextEventEstimator(tracer, geometry, sources)
    estimator.estimate_field(np.array([0.0, 0.0, 5.0]), seed=3)
    assert geometry.counts.count(len(sources)) == 1


def test_source_weights_are_validated_and_equal_defaults_remain_legacy():
    with pytest.raises(ValueError, match="source_weights"):
        SourceSet(np.zeros((2, 3)), 1.0, 3, 0, 0, source_weights=np.ones(1))
    with pytest.raises(ValueError, match="nonnegative"):
        SourceSet(np.zeros((2, 3)), 1.0, 3, 0, 0, source_weights=np.array([1.0, -1.0]))
    equal = SourceSet(np.zeros((2, 3)), 1.0, 3, 0, 0)
    explicit = SourceSet(np.zeros((2, 3)), 1.0, 3, 0, 0, source_weights=np.ones(2))
    assert equal.normalized_source_weights() == pytest.approx(explicit.normalized_source_weights())


def test_sources_preserve_existing_position_dtype_and_weight_provenance():
    positions = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
    unweighted = SourceSet(positions, 1.0, 3, 0, 0)
    assert unweighted.positions.dtype == np.float32
    assert "weight_provenance" not in unweighted.describe()
    assert unweighted.weight_provenance()["mode"] == "equal"

    first = SourceSet(positions, 1.0, 3, 0, 0, source_weights=np.array([1.0, 2.0]))
    second = SourceSet(positions, 1.0, 3, 0, 0, source_weights=np.array([10.0, 20.0]))
    first_provenance = first.weight_provenance()
    second_provenance = second.weight_provenance()
    assert first_provenance["mode"] == "explicit"
    assert first_provenance["count"] == 2
    assert first_provenance["nonzero"] == 2
    assert first_provenance["normalized_weights_sha256"] == second_provenance["normalized_weights_sha256"]
    assert first_provenance["canonicalization"].endswith("ascii_v1")
    assert first.describe()["weight_provenance"] == first_provenance

    triple_positions = np.vstack([positions, [[7.0, 8.0, 9.0]]]).astype(np.float32)
    decimal = SourceSet(triple_positions, 1.0, 3, 0, 0, source_weights=np.array([0.1, 0.2, 0.3]))
    integer = SourceSet(triple_positions, 1.0, 3, 0, 0, source_weights=np.array([1.0, 2.0, 3.0]))
    different = SourceSet(triple_positions, 1.0, 3, 0, 0, source_weights=np.array([1.0, 2.0, 4.0]))
    assert (
        decimal.weight_provenance()["normalized_weights_sha256"]
        == integer.weight_provenance()["normalized_weights_sha256"]
    )
    assert (
        decimal.weight_provenance()["normalized_weights_sha256"]
        != different.weight_provenance()["normalized_weights_sha256"]
    )

    zero = SourceSet(triple_positions, 1.0, 3, 0, 0, source_weights=np.array([0.0, 1.0, 3.0]))
    assert zero.weight_provenance()["nonzero"] == 2
    little = SourceSet(triple_positions, 1.0, 3, 0, 0, source_weights=np.array([1.0, 2.0, 3.0], dtype="<f8"))
    big = SourceSet(triple_positions, 1.0, 3, 0, 0, source_weights=np.array([1.0, 2.0, 3.0], dtype=">f8"))
    assert (
        little.weight_provenance()["normalized_weights_sha256"] == big.weight_provenance()["normalized_weights_sha256"]
    )


def test_trace_config_rejects_zero_rays_early():
    with pytest.raises(ValueError, match="rays must be positive"):
        TraceConfig(rays=0)
