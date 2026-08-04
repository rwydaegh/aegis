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
from semantic_twin.illumination.sources import NextEventGather, SourceSet
from semantic_twin.propagation.tracer import SbrTracer, TraceConfig


def one_site(height_m: float) -> SourceSet:
    return SourceSet(
        positions=np.array([[0.0, 0.0, height_m]]),
        cell_m=1.0,
        dims=3,
        azimuths=0,
        builders=0,
    )


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
