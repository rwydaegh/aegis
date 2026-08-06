"""One broad pass over every numbered finding in ``docs/BUGS.md``.

This file and the six ``test_invariant_*.py`` files beside it were written in
parallel by two agents that did not know about each other, and the split they
landed on turned out to be a good one, so it was kept. The six take one physical
invariant each and go deep: interfaces, illumination measures, reciprocity
between the two estimators, the foliage slab, remeshing, the grating limit. This
file goes the other way. It walks the audit end to end, spends one or two tests
on each finding, and covers the three that no other file reaches: finding 2, the
roughness term that is never read, finding 6, the order width computed twice and
differently, and finding 7, the source shell centred on the world origin.

Read it as the audit's companion. If you want to know whether a finding is
pinned at all, look here. If you want to know what else breaks when it is wrong,
look in the file named after the invariant.

Where each finding is pinned, so that the coverage map lives next to the tests.

===== ======================================================================
1      here, and twice more in ``test_invariant_reciprocity.py``. The three
       pin different mechanisms: a value against a closed form here, and
       there the fact that the answer cannot depend on roughness at all.
2      here only.
3      here as the identity ``mean == p_abs / area``, and in
       ``test_invariant_remesh.py`` as invariance under subdivision.
4      ``test_invariant_foliage.py`` only.
5      here as the effective medium limit, and in
       ``test_invariant_rcwa_limit.py`` as a truncation convergence test that
       needs no reference value.
6      here only.
7      here only.
8      here only.
8b     not pinned, and not by oversight. It is a data defect rather than a
       physics one: Korenmarkt's fishnet was cut against one mesh and traced
       against another, so pinning it needs the site meshes rather than an
       invariant. A fixture that joins two triangle sets by centroid and
       asserts the match rate would belong in the golden tier, not here.
8c     not pinned because it is already fixed. The golden harness now clears
       its own rungs, so the case cannot silently re-read a run from disk.
9      here as the slab identity, and in ``test_invariant_foliage.py`` as the
       observer standing inside the canopy.
10     here only.
===== ======================================================================

The goldens in ``tests/golden/`` pin values. Both tiers pin physics. A golden
says "this number was 0.4471 yesterday". An invariant says "whatever this number
is, it cannot be negative, it cannot exceed the power that went in, and it
cannot depend on where the world origin happens to sit".

Every test here was chosen so that a plausible implementation error breaks it,
and every one of them was watched failing before it was kept. Three habits the
existing suite fell into are avoided on purpose.

- A test that only runs the symmetric case. ``tests/test_propagation.py:650``
  checks the absorbed density against isotropic illumination, which is exactly
  unbiased by symmetry, so an unweighted mean over triangles whose areas vary by
  four orders of magnitude sails through it.
- A test that only runs the degenerate case. Every test in
  ``tests/test_next_event.py`` sets ``rms_height_m = 1.0`` m, which forces the
  specular share to exactly zero. That is the one regime in which the next event
  estimator dropping the specular lobe cannot show up.
- A test that only checks a conserved quantity. ``tests/test_rcwa.py`` checks
  ``R + T``, which the wrong Fourier factorisation leaves at 1e-15 while it
  moves ``R`` by several percent.

So the cases here are lossy rather than lossless, uneven rather than half and
half, and off axis rather than normal, and where two routes to the same number
exist both are computed and compared.

Where an invariant fails today because of a defect in ``docs/BUGS.md``, the test
is marked ``xfail(strict=True)`` against the finding number rather than
weakened. Fixing the defect turns it into an unexpected pass, which is a
failure, which is what forces the marker to be removed and the test to become
the proof that the fix worked.
"""

from __future__ import annotations

import math
import pathlib

import numpy as np
import pytest

from semantic_twin.materials import (
    CLASS_NAMES,
    MaterialLibrary,
    SurfaceRoughnessLibrary,
    class_area_fractions,
    classify_faces,
)
from semantic_twin.illumination import catalogue as shipped_models
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY
from semantic_twin.illumination import (
    ISOTROPIC,
    VARIANTS,
    IlluminationModel,
    fibonacci_sphere,
)
from semantic_twin.propagation.geometry import PlaneGeometry
from semantic_twin.illumination.sources import SourceSet, direct_from_sites
from semantic_twin.transport.tracer import (
    SbrTracer,
    TraceConfig,
    fresnel_power_reflectance,
    specular_share,
)
from semantic_twin.transport.next_event import NextEventGather

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
FIFTEEN_GHZ = 15.0e9
INFINITY = 1.0e30


def finding(number: int, what: str) -> pytest.MarkDecorator:
    """Mark an invariant that a known defect breaks, naming the defect."""
    return pytest.mark.xfail(reason=f"docs/BUGS.md finding {number}: {what}", strict=True)


# ---------------------------------------------------------------------------
# Interfaces: reflectance and transmittance stay physical, and close.
# ---------------------------------------------------------------------------


def _amplitude_coefficients(cos_incidence: np.ndarray, permittivity: complex) -> tuple[np.ndarray, ...]:
    """Textbook Fresnel amplitudes in the refractive index form.

    Written out in ``n1``, ``n2``, ``cos(theta_i)`` and ``cos(theta_t)`` rather
    than in the ratio form the package uses, so that a mistake in one cannot be
    a mistake in both. ``root`` is ``n2 cos(theta_t)``.
    """
    cos_i = np.clip(cos_incidence, 0.0, 1.0).astype(np.complex128)
    index = np.sqrt(permittivity)
    cos_t = np.sqrt(1.0 - (1.0 - cos_i**2) / permittivity)
    root = index * cos_t
    reflect_te = (cos_i - root) / (cos_i + root)
    reflect_tm = (index * cos_i - cos_t) / (index * cos_i + cos_t)
    transmit_te = 2.0 * cos_i / (cos_i + root)
    transmit_tm = 2.0 * cos_i / (index * cos_i + cos_t)
    return cos_i, root, reflect_te, reflect_tm, transmit_te, transmit_tm


def reference_power_reflectance(cos_incidence: np.ndarray, permittivity: complex) -> np.ndarray:
    """Unpolarised power reflectance, second implementation.

    Exists so the whole trace energy budget below can be compared against a
    number the package did not compute. A reference that calls the function
    under test moves with it, and a budget that closes because both sides
    changed together is not a budget.
    """
    _, _, reflect_te, reflect_tm, _, _ = _amplitude_coefficients(cos_incidence, permittivity)
    return 0.5 * (np.abs(reflect_te) ** 2 + np.abs(reflect_tm) ** 2)


def reference_power_transmittance(cos_incidence: np.ndarray, permittivity: complex) -> np.ndarray:
    """Unpolarised power transmittance into a half space, second implementation.

    The transmitted Poynting flux normal to the interface over the incident one,
    ``T = Re(n2 cos(theta_t)) / (n1 cos(theta_i)) |t|**2``. Two implementations
    that agree on ``R + T = 1`` at every angle is a far stronger statement than
    one implementation returning numbers between zero and one.
    """
    cos_i, root, _, _, transmit_te, transmit_tm = _amplitude_coefficients(cos_incidence, permittivity)
    flux = np.real(root) / np.real(cos_i)
    return 0.5 * flux * (np.abs(transmit_te) ** 2 + np.abs(transmit_tm) ** 2)


@pytest.fixture(scope="module")
def itu_rows() -> MaterialLibrary:
    return MaterialLibrary.load(CONFIG / "itu_p2040_4.json")


def test_reflectance_is_physical_on_every_shipped_material(itu_rows: MaterialLibrary) -> None:
    """`0 <= R <= 1` for all 15 rows, at both ends of every stated band.

    The existing Fresnel test looks at concrete, vacuum and a perfect conductor.
    This one sweeps the whole table, because the rows differ by a factor of 3e8
    in conductivity and a row is only ever wrong at its own extremes. Both ends
    of the validity band are evaluated rather than the middle, since the power
    law ``c * f**d`` puts the largest conductivity at whichever end ``d``
    points at.
    """
    # Exact grazing on a vacuum interface is 0/0, degenerate rather than wrong,
    # so it is stepped around rather than papered over.
    cosine = np.linspace(1.0e-9, 1.0, 61)
    assert len(itu_rows.materials) == 15
    for name, material in itu_rows.materials.items():
        for edge in (material.minimum_ghz, 0.5 * (material.minimum_ghz + material.maximum_ghz), material.maximum_ghz):
            evaluation = material.evaluate(edge * 1.0e9)
            assert evaluation.relative_permittivity_real >= 1.0, name
            assert evaluation.conductivity_s_per_m >= 0.0, name
            permittivity = complex(evaluation.relative_permittivity_real, -evaluation.relative_permittivity_imag)
            reflectance = fresnel_power_reflectance(cosine, np.asarray(permittivity))
            assert np.all(np.isfinite(reflectance)), (name, edge)
            assert np.all(reflectance >= 0.0), (name, edge, float(reflectance.min()))
            assert np.all(reflectance <= 1.0), (name, edge, float(reflectance.max()))
            if permittivity != complex(1.0, 0.0):
                # Grazing incidence on any interface with contrast reflects
                # everything, and normal incidence never does. The bound is
                # 0.999 rather than machine precision because metal's stand in
                # permittivity is large and finite.
                assert reflectance[0] > 0.999, (name, edge)
                assert reflectance[0] == reflectance.max(), (name, edge)
                assert reflectance[-1] < reflectance[0], (name, edge)


@pytest.mark.parametrize("relative_permittivity", [2.0, 4.0, 9.0, 25.0])
def test_a_lossless_interface_closes_its_power_budget(relative_permittivity: float) -> None:
    """`R + T = 1` at every incidence, against a second implementation.

    The split is uneven nearly everywhere on the sweep and that is the point. At
    ``eps = 4`` the reflectance runs from 0.111 at normal incidence to 1 at
    grazing, so a factor lost on either side moves the residual by far more than
    the tolerance. A test written at one angle where the split happened to be
    half and half could not say that.
    """
    permittivity = complex(relative_permittivity, 0.0)
    cosine = np.linspace(1.0e-6, 1.0, 501)
    reflected = fresnel_power_reflectance(cosine, np.asarray(permittivity))
    transmitted = reference_power_transmittance(cosine, permittivity)
    assert np.max(np.abs(reflected + transmitted - 1.0)) < 1.0e-12
    # The independent reflectance has to be the shipped one as well, or the
    # closure above could be met by two errors that cancel.
    assert np.allclose(reflected, reference_power_reflectance(cosine, permittivity), atol=1.0e-14)
    # The sweep really does span a wide split, so the closure above is not being
    # met by two numbers that sit near a half all the way along.
    assert reflected[0] > 0.99, "grazing has to be nearly all reflected"
    assert reflected[-1] < 0.5, "normal incidence has to be mostly transmitted"


@pytest.mark.parametrize("relative_permittivity", [2.0, 4.0, 9.0])
def test_the_brewster_null_sits_on_the_magnetic_branch(relative_permittivity: float) -> None:
    """At Brewster's angle the unpolarised reflectance is exactly half the electric one.

    A lossless half space reflects no transverse magnetic power at
    ``theta_B = atan(sqrt(eps))``, so the unpolarised average collapses to
    ``0.5 * |Gamma_TE|**2`` there and nowhere else. This is the one test in the
    file that can tell the two branches apart, and swapping them makes it fail
    by a factor of a few rather than by a rounding error.
    """
    permittivity = complex(relative_permittivity, 0.0)
    brewster = math.atan(math.sqrt(relative_permittivity))
    cos_i = math.cos(brewster)
    root = math.sqrt(relative_permittivity - math.sin(brewster) ** 2)
    te_only = abs((cos_i - root) / (cos_i + root)) ** 2
    unpolarised = float(fresnel_power_reflectance(np.array([cos_i]), np.asarray(permittivity))[0])
    assert unpolarised == pytest.approx(0.5 * te_only, rel=1.0e-9)
    # At normal incidence the two branches are the same wave, so the average is
    # the electric branch itself rather than half of it. Together the two lines
    # say the branches coincide at one angle and separate by exactly a factor of
    # two at another, which is a statement no swap of the two can satisfy.
    index = math.sqrt(relative_permittivity)
    at_normal = abs((1.0 - index) / (1.0 + index)) ** 2
    assert float(fresnel_power_reflectance(np.array([1.0]), np.asarray(permittivity))[0]) == pytest.approx(
        at_normal, rel=1.0e-12
    )


def test_the_p2040_imaginary_permittivity_constant_is_the_physical_one(itu_rows: MaterialLibrary) -> None:
    """`eps'' = 17.98 * sigma / f_GHz` has to be `sigma / (2 pi f eps0)`.

    The recommendation prints a rounded constant and the code carries the same
    digits. Checking it against the vacuum permittivity is what turns a copied
    literal into a derived one, and it is the only thing standing between a
    typed digit and every reflectance in the study.

    The constant is recovered from an evaluation rather than repeated here, so
    the test reads the shipped number instead of a copy of it.
    """
    exact = 1.0 / (2.0 * math.pi * 8.8541878128e-12 * 1.0e9)
    for name in ("concrete", "brick", "glass"):
        for frequency_ghz in (2.0, 15.0, 30.0):
            evaluation = itu_rows[name].evaluate(frequency_ghz * 1.0e9)
            shipped = evaluation.relative_permittivity_imag * frequency_ghz / evaluation.conductivity_s_per_m
            assert shipped == pytest.approx(exact, rel=1.0e-3), (name, frequency_ghz)


# ---------------------------------------------------------------------------
# Illumination: every density is a probability density on the sphere.
# ---------------------------------------------------------------------------


def discovered_models() -> dict[str, IlluminationModel]:
    """Every illumination model the catalogue defines, found rather than listed.

    Scanning the module namespace is the point. A test that lists the seven
    models by name checks the seven that existed when it was written, and a new
    law added next month inherits nothing. This inherits the whole file.
    """
    found: dict[str, IlluminationModel] = {}
    for value in vars(shipped_models).values():
        if isinstance(value, IlluminationModel):
            found[value.name] = value
    for registry in (shipped_models.MODELS, shipped_models.VARIANTS):
        for model in registry.values():
            found[model.name] = model
    return found


MODEL_NAMES = sorted(discovered_models())


def test_the_module_registers_every_illumination_model_it_defines() -> None:
    """A law that exists but is not in ``VARIANTS`` is invisible to every sweep."""
    found = discovered_models()
    assert len(found) >= 7
    assert set(found) == set(VARIANTS)


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_every_illumination_density_integrates_to_one_over_the_sphere(name: str) -> None:
    """`integral Q dOmega = 1`, by a quadrature that shares nothing with the module's.

    The module normalises with a 200001 point trapezoid in elevation carrying a
    ``cos(el)`` Jacobian. Re-integrating in elevation would re-use that Jacobian
    and could not see it go missing. This integrates in ``z = sin(el)``, where
    the sphere measure is a flat ``2 pi dz`` and there is no Jacobian to get
    wrong, using adaptive Gauss-Kronrod with the band law knots handed in as
    break points.

    The residual comes out at 2e-9, four orders tighter than the 2 percent the
    existing Monte Carlo check can reach, so this is also the sharpest statement
    in the file about the constant every susceptibility is divided by.
    """
    from scipy.integrate import quad

    model = discovered_models()[name]

    def density_at_height(z: float) -> float:
        horizontal = math.sqrt(max(0.0, 1.0 - z * z))
        return float(model.density(np.array([[horizontal, 0.0, z]]))[0])

    low = math.sin(math.radians(model.elevation_min_deg))
    high = math.sin(math.radians(model.elevation_max_deg))
    knots = sorted(math.sin(k) for k in model.knots() if low < math.sin(k) < high)
    value, error = quad(density_at_height, low, high, points=knots or None, limit=400, epsabs=1e-13, epsrel=1e-13)
    assert error < 1.0e-9, name
    assert 2.0 * math.pi * value == pytest.approx(1.0, abs=1.0e-6), name


@pytest.mark.parametrize("name", MODEL_NAMES)
def test_every_illumination_density_is_non_negative_and_stops_at_its_support(name: str) -> None:
    """A density cannot go negative, and a law with a support has to respect it.

    The band laws are differences of slant range caps, so an ordering slip in
    ``max(far - near, 0)`` shows up here as negative measure and nowhere else in
    the suite.
    """
    model = discovered_models()[name]
    rng = np.random.default_rng(4)
    z = rng.uniform(-1.0, 1.0, 20_000)
    phi = rng.uniform(0.0, 2.0 * math.pi, 20_000)
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    sphere = np.stack([radius * np.cos(phi), radius * np.sin(phi), z], axis=1)
    density = model.density(sphere)
    assert np.all(np.isfinite(density)), name
    assert np.all(density >= 0.0), name
    outside = []
    if model.elevation_min_deg > -90.0:
        outside.append(math.radians(model.elevation_min_deg) - 1.0e-4)
    if model.elevation_max_deg < 90.0:
        outside.append(math.radians(model.elevation_max_deg) + 1.0e-4)
    for elevation in outside:
        direction = np.array([[math.cos(elevation), 0.0, math.sin(elevation)]])
        assert float(model.density(direction)[0]) == 0.0, (name, elevation)


# ---------------------------------------------------------------------------
# The trace as a whole: what leaves the head comes back as escape plus loss.
# ---------------------------------------------------------------------------

CONCRETE_15_GHZ = complex(5.24, -0.4605523331047092)


def mean_reflectance_over_the_lower_hemisphere(permittivity: complex) -> float:
    """`integral_0^1 R(mu) dmu`, which is what a plane under a point absorbs from.

    Rays drawn uniformly on the sphere have ``|mu|`` uniform on ``(0, 1]``, so
    the mean reflectance a ground plane hands back is a plain integral in
    ``mu`` with no weight. 200001 abscissae puts the quadrature error four
    orders below the Monte Carlo error of the trace it is compared against.

    The integrand is the independent reflectance, never the shipped one, so the
    budget below cannot close by both sides moving together.
    """
    mu = np.linspace(1.0e-9, 1.0, 200_001)
    return float(np.trapezoid(reference_power_reflectance(mu, permittivity), mu))


@pytest.mark.parametrize(
    ("regime", "rms_height_m"),
    [("specular", 0.0), ("lambertian", 1.0), ("partly rough", 3.18e-3)],
)
def test_the_trace_closes_its_energy_budget_over_a_lossy_ground(regime: str, rms_height_m: float) -> None:
    """Escaped power plus absorbed power is the power that left, on a 64/36 split.

    Concrete at 15 GHz hands back 64.4 percent of what a point above it radiates
    and keeps 35.6 percent, so neither side of the budget is near a half and a
    lost factor cannot cancel. The existing white furnace test is the opposite
    case: a closed perfect reflector where nothing escapes at all, which any
    estimator that returns zero passes.

    Three roughness regimes are run because the reflected lobe is chosen by a
    coin flip on the Rayleigh share, and the budget must not care which way it
    lands. A perfect mirror, a Lambertian and a surface that is half of each all
    have to give the same escaped fraction, since the throughput that survives
    the interface is the same and only its direction differs.
    """
    escaping = 0.5 * (1.0 + mean_reflectance_over_the_lower_hemisphere(CONCRETE_15_GHZ))
    config = TraceConfig(rays=400_000, max_bounces=3, seed=4, local_cells=256, exit_bands=18)
    tracer = SbrTracer(PlaneGeometry(0.0), None, np.array([CONCRETE_15_GHZ]), np.array([rms_height_m]), config)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), {"isotropic": ISOTROPIC}, ground_z_m=0.0)

    # Every ray over an infinite plane leaves after at most one interaction, so
    # nothing is left travelling and the budget has only two terms.
    assert result.escaped_fraction == 1.0
    assert result.diagnostics["truncated_rays"] == 0

    escaped = float(result.exit_profile.sum()) / config.exit_bands
    assert escaped == pytest.approx(escaping, rel=2.0e-3), regime
    absorbed = 1.0 - escaped
    assert absorbed == pytest.approx(1.0 - escaping, rel=4.0e-3), regime
    assert 0.3 < absorbed < 0.4, "the split has to stay uneven or this test proves nothing"


def test_the_susceptibility_and_the_exit_profile_are_the_same_energy() -> None:
    """Two accumulators, one number, and they are written in different places.

    ``rho`` is binned on the departure direction and divided by a per cell
    count. ``exit_power`` is binned on the exit direction and divided by a flat
    ray count. Under isotropic illumination both reduce to the mean surviving
    throughput, so they have to agree, and they only agree if the solid angle
    weight, the cell counting and the band edges are all right at once.
    """
    config = TraceConfig(rays=400_000, max_bounces=3, seed=4, local_cells=256, exit_bands=18)
    tracer = SbrTracer(PlaneGeometry(0.0), None, np.array([CONCRETE_15_GHZ]), np.array([0.0]), config)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), {"isotropic": ISOTROPIC}, ground_z_m=0.0)
    by_band = float(result.exit_profile.sum()) / config.exit_bands
    assert result.susceptibility["isotropic"] == pytest.approx(by_band, rel=1.0e-3)


# ---------------------------------------------------------------------------
# Reciprocity: the escape estimator and the next event estimator are one integral.
# ---------------------------------------------------------------------------

SOURCE_SHELL_M = 4.0e3
HEAD = np.array([0.0, 0.0, 1.5])


@pytest.fixture(scope="module")
def far_isotropic_sources() -> tuple[SourceSet, float]:
    """Sites spread evenly over a shell far outside the scene, and the direct term.

    A Fibonacci shell rather than a random draw, because the comparison is
    between two estimators and not between two samples. With the set fixed to
    equal solid angle the only Monte Carlo error left is the ray count, which
    both estimators pay, and the residual falls to a few parts in a thousand.

    Sites at 4 km against a head at 1.5 m puts the population in the far field
    the escape estimator assumes, so the two are answering the same question.
    Repeating this at 40 km and 400 km moves nothing, which is what says the
    limit has been reached rather than approached.
    """
    positions = SOURCE_SHELL_M * fibonacci_sphere(2048)
    sources = SourceSet(positions=positions, cell_m=1.0, dims=3, azimuths=0, builders=0)
    direct, _ = direct_from_sites(PlaneGeometry(0.0), np.atleast_2d(HEAD), positions)
    return sources, float(direct[0])


def two_estimators_on_a_ground_plane(sources: SourceSet, rms_height_m: float, seed: int) -> tuple[float, float]:
    """Bounced over direct, computed twice, on an infinite perfectly reflecting plane."""
    plane = PlaneGeometry(0.0)
    config = TraceConfig(rays=400_000, max_bounces=2, seed=seed, local_cells=256)
    tracer = SbrTracer(plane, None, np.array([PEC_PERMITTIVITY]), np.array([rms_height_m]), config)
    gather = NextEventGather(
        geometry=plane,
        sources=sources,
        rng=np.random.default_rng(seed),
        samples=4,
        max_order=2,
    )
    result = tracer.trace(HEAD, {"isotropic": ISOTROPIC}, ground_z_m=0.0, seed=seed, gather=gather)
    total = result.susceptibility["isotropic"]
    direct = result.susceptibility_direct["isotropic"]
    return (total - direct) / direct, gather.chi_bounce()


@pytest.mark.parametrize(
    ("regime", "rms_height_m"),
    [
        ("fully rough", 1.0),
        pytest.param(
            "half rough",
            3.18e-3,
            marks=finding(1, "next event credits only (1 - share), and nothing carries the rest"),
        ),
        pytest.param(
            "perfectly smooth",
            0.0,
            marks=finding(1, "next event credits only (1 - share), and nothing carries the rest"),
        ),
    ],
)
def test_the_two_estimators_agree_where_the_answer_is_known(
    far_isotropic_sources: tuple[SourceSet, float], regime: str, rms_height_m: float
) -> None:
    """Escape and next event have to return the same ratio, and the ratio is 1.

    This is the single most valuable test in the file, because the two
    estimators disagree by a factor of three to five on real cities and nobody
    could say how much of that was geometry. Here the geometry is an infinite
    perfectly reflecting plane under a head at 1.5 m with the sources isotropic
    and at infinity, and both the answer and the two routes to it are exact.

    Half the rays leave upward and reach the sky. The other half reflect once
    with unit throughput and reach it too. So the bounced term equals the direct
    term and the ratio is 1, whatever the surface does with the direction. The
    escape estimator gets 1.0008 at 400k rays. Next event gets 0.998 when the
    surface is fully rough.

    The roughness is the parameter that matters and it is why this test is
    parametrised on it. ``tests/test_next_event.py`` fixes ``rms_height_m`` at
    1.0 m throughout, which drives the Rayleigh coherent share to exactly zero,
    and that is precisely the regime in which the missing specular term cannot
    appear. Turn the roughness down and next event returns 0.56 of the right
    answer at half rough and exactly 0 at perfectly smooth, because the coherent
    share is deferred to image sources that no code path builds.
    """
    sources, direct = far_isotropic_sources
    by_escape, by_next_event = two_estimators_on_a_ground_plane(sources, rms_height_m, seed=5)
    assert by_escape == pytest.approx(1.0, rel=0.01), "the escape side is the reference and must hold"
    assert by_next_event / direct == pytest.approx(by_escape, rel=0.01), regime


# ---------------------------------------------------------------------------
# Invariance: the answer cannot depend on the coordinate system.
# ---------------------------------------------------------------------------


class GroundDisc:
    """A finite ground disc with a bounding radius, placed anywhere.

    ``PlaneGeometry`` is infinite and carries no vertices, so it can say nothing
    about a scene bounding radius. This one does, which is what lets the same
    scene be handed to the tracer twice in two coordinate systems.
    """

    def __init__(self, radius_m: float, centre: np.ndarray) -> None:
        self.radius_m = float(radius_m)
        self.centre = np.asarray(centre, dtype=np.float64)
        angle = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
        rim = np.stack([self.radius_m * np.cos(angle), self.radius_m * np.sin(angle), np.zeros_like(angle)], axis=1)
        self.vertices = rim + self.centre

    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        with np.errstate(divide="ignore", invalid="ignore"):
            travel = (self.centre[2] - origins[:, 2]) / directions[:, 2]
        point = origins + np.where(np.isfinite(travel), travel, 0.0)[:, None] * directions
        offset = np.linalg.norm(point[:, :2] - self.centre[None, :2], axis=1)
        hit = np.isfinite(travel) & (travel > 0.0) & (offset <= self.radius_m)
        normal = np.tile(np.array([0.0, 0.0, 1.0]), (origins.shape[0], 1))
        return hit, np.where(hit, travel, INFINITY), normal, np.zeros(origins.shape[0], dtype=np.int64)


def multipath_gain_of_a_translated_disc(shift: np.ndarray, *, range_weighted: bool) -> float:
    geometry = GroundDisc(60.0, shift)
    config = TraceConfig(rays=200_000, max_bounces=3, seed=7, local_cells=256, range_weighted_escape=range_weighted)
    tracer = SbrTracer(geometry, None, np.array([PEC_PERMITTIVITY]), np.array([0.0]), config)
    result = tracer.trace(shift + HEAD, {"isotropic": ISOTROPIC}, ground_z_m=float(shift[2]))
    return result.susceptibility["isotropic"] / result.susceptibility_direct["isotropic"]


@pytest.mark.parametrize(
    ("mode", "range_weighted"),
    [
        ("plain escape", False),
        pytest.param(
            "range charged escape",
            True,
            marks=finding(7, "the source shell is centred on the world origin, not on the scene"),
        ),
    ],
)
def test_the_multipath_gain_does_not_move_when_the_scene_does(mode: str, range_weighted: bool) -> None:
    """Translate the whole scene and the physics cannot notice.

    The same disc, the same head above it, the same rays and the same seed, in
    three coordinate systems. Nothing physical distinguishes them, so the
    multipath gain has to be the same number three times.

    The plain escape estimator returns it bit for bit, which is the control that
    says the harness is measuring the coordinate system and not the noise. The
    range charged diagnostic does not: 120 m of lift moves the gain from 1.90 to
    1.67, which is 0.57 dB of pure artefact, because the shell it charges
    against is a sphere about the world origin rather than about the scene. At
    Korenmarkt the world origin sits 35 to 45 m below the lowest mesh point, so
    this is the situation the study is actually in.
    """
    origin = multipath_gain_of_a_translated_disc(np.zeros(3), range_weighted=range_weighted)
    sideways = multipath_gain_of_a_translated_disc(np.array([300.0, 0.0, 0.0]), range_weighted=range_weighted)
    upward = multipath_gain_of_a_translated_disc(np.array([0.0, 0.0, 120.0]), range_weighted=range_weighted)
    assert sideways == pytest.approx(origin, rel=1.0e-6), mode
    assert upward == pytest.approx(origin, rel=1.0e-6), mode


# ---------------------------------------------------------------------------
# The validation gate: it has to compare like with like.
# ---------------------------------------------------------------------------

#: What ``run_exposure.validate`` reports as its worst disagreement between the
#: tracer and the closed form, at the published 400,000 rays.
PUBLISHED_MAX_ABS_ERROR = 0.0122


@pytest.fixture(scope="module")
def validation_report() -> dict:
    """``validate`` at a low ray count, because the assertions do not read rays.

    Both tests below look only at the ``closed_form`` array, which is built from
    ``exit_sin_edges`` and the permittivity and does not depend on how many rays
    were cast. 2000 rays give the identical array in a third of a second, where
    the published 400,000 take minutes. The ``measured`` side is noise at this
    count and is deliberately not asserted on.
    """
    import run_exposure

    return run_exposure.validate(rays=2000)["dielectric_ground_plane"]


def closed_forms_above_horizon(permittivity: complex, bands: int = 18) -> tuple[np.ndarray, np.ndarray]:
    """``(at the band centre, averaged over the band)``, over the gate's bands.

    Both are computed here rather than read back from the report, so that the
    comparison between them stays meaningful whichever one ``validate`` decides
    to use.
    """
    from semantic_twin.propagation.closed_form import ground_plane_band_average, ground_plane_susceptibility

    edges = np.linspace(-1.0, 1.0, bands + 1)
    elevation = np.degrees(np.arcsin(0.5 * (edges[:-1] + edges[1:])))
    above = elevation > 0.0
    at_centre = ground_plane_susceptibility(elevation, permittivity)[above]
    over_band = ground_plane_band_average(edges, permittivity)[above]
    return at_centre, over_band


@finding(8, "validate compares a band average against the closed form at the band centre")
def test_the_gate_compares_the_band_average_and_not_the_band_centre(validation_report) -> None:
    """The tracer reports a band average, so the target has to be one too.

    ``exit_profile`` is the mean over an equal solid angle band, not a value at
    a point. ``closed_form.ground_plane_band_average`` exists to integrate the
    analytic answer over those same bands and its own docstring says why:
    comparing against the band centre builds the band width into the residual.
    ``run_exposure.validate`` never calls it and evaluates
    ``ground_plane_susceptibility`` at the centres instead.

    So this is a like for like test and nothing else. It recomputes the band
    average over the bands the gate actually used and asserts the gate's own
    published target equals it. Today the lowest band above the horizon is
    1.73203 where the average is 1.74782, and the fix is to call the function
    that is already there.
    """
    permittivity = complex(*validation_report["permittivity"])
    _, over_band = closed_forms_above_horizon(permittivity)
    assert np.asarray(validation_report["closed_form"]) == pytest.approx(over_band, rel=1.0e-9)


def test_the_band_width_correction_is_larger_than_the_agreement_it_is_quoted_with(
    validation_report,
) -> None:
    """Why the test above is worth having rather than a rounding quibble.

    The gate's headline is one percent agreement, a ``max_abs_error`` of 0.0122
    at 400,000 rays. The band centre against band average mismatch is 0.0158,
    which is larger. So the quoted agreement is mostly quadrature and the gate
    cannot resolve an estimator error below about one percent, which is the part
    of finding 8 that matters for reading the study.

    This one stays green after the fix, since it is a statement about the band
    width rather than about which function is called. It goes red if the band
    count changes enough to make the correction small, and that is the intended
    behaviour: at that point finding 8 stops mattering and somebody should read
    it again rather than carry it forward.
    """
    at_centre, over_band = closed_forms_above_horizon(complex(*validation_report["permittivity"]))
    assert float(np.max(np.abs(at_centre - over_band))) > PUBLISHED_MAX_ABS_ERROR


# ---------------------------------------------------------------------------
# Remeshing: an area weighted quantity cannot depend on the triangulation.
# ---------------------------------------------------------------------------


def unequal_box() -> np.ndarray:
    """A closed box as twelve triangles, six distinct normals."""
    corner = np.array(
        [[0, 0, 0], [4, 0, 0], [4, 3, 0], [0, 3, 0], [0, 0, 2], [4, 0, 2], [4, 3, 2], [0, 3, 2]], dtype=np.float64
    )
    quads = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    triangles = []
    for a, b, c, d in quads:
        triangles.append([corner[a], corner[b], corner[c]])
        triangles.append([corner[a], corner[c], corner[d]])
    return np.asarray(triangles)


def subdivide(triangles: np.ndarray, which: set[int]) -> np.ndarray:
    """Split the named triangles four ways at their edge midpoints.

    Midpoint subdivision changes nothing about the surface: same geometry, same
    normals, same total area. Only the triangulation moves. Subdividing a
    *subset* is what matters, because splitting every triangle by the same
    factor leaves even an unweighted mean where it was, and a test that did that
    would pass against the defect it is looking for.
    """
    out = []
    for index, triangle in enumerate(triangles):
        if index not in which:
            out.append(triangle)
            continue
        a, b, c = triangle
        ab, bc, ca = 0.5 * (a + b), 0.5 * (b + c), 0.5 * (c + a)
        out += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]
    return np.asarray(out)


def couple_a_synthetic_body(triangles: np.ndarray) -> tuple[object, float]:
    """Run the real ``BodyCoupler.couple`` over a mesh built from arrays.

    Only the constructor is bypassed, because it insists on loading a phantom
    from disk. Everything the invariant is about, the composition of the angular
    spectrum with the body and the reduction to scalars, is the shipped code.
    """
    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.tissue import TissueModel

    from semantic_twin.exposure import BodyCoupler

    mesh = BodyMesh.from_arrays(triangles, name="box")
    coupler = BodyCoupler.__new__(BodyCoupler)
    coupler.body = mesh
    coupler.tissue = TissueModel.from_database("Skin", FIFTEEN_GHZ)
    coupler.engine = DosimetryEngine(coupler.tissue)
    coupler.level = 2
    coupler.body_mass_kg = 70.0
    coupler.frequency_hz = FIFTEEN_GHZ

    grid = fibonacci_sphere(256)
    solid_angle = 4.0 * np.pi / 256
    rho = np.abs(np.random.default_rng(0).normal(size=256))
    return coupler.couple(grid, rho, solid_angle, 1.0), float(mesh.areas.sum())


@pytest.fixture(scope="module")
def remeshed_exposures() -> list[tuple[object, float]]:
    pytest.importorskip("aegis")
    coarse = unequal_box()
    once = subdivide(coarse, {0, 1})
    twice = subdivide(once, set(range(8)))
    return [couple_a_synthetic_body(mesh) for mesh in (coarse, once, twice)]


def test_the_absorbed_power_and_the_peak_survive_remeshing(remeshed_exposures) -> None:
    """The control. Same surface, three triangulations, same total area.

    ``p_abs`` is a sum over triangles weighted by area and ``peak_sab`` is a
    maximum, so both are properties of the surface rather than of how it was cut
    up. They come back bit identical, which is what says the next test is
    reading a real dependence and not a numerical wobble.
    """
    first, area = remeshed_exposures[0]
    for exposure, other_area in remeshed_exposures[1:]:
        assert other_area == pytest.approx(area, rel=1.0e-12)
        assert exposure.absorbed_power_w == pytest.approx(first.absorbed_power_w, rel=1.0e-12)
        assert exposure.peak_sab_w_m2 == pytest.approx(first.peak_sab_w_m2, rel=1.0e-12)


# The remesh invariance itself is pinned in
# ``test_invariant_remesh.py::test_the_mean_absorbed_density_survives_the_remesh``,
# which runs the real ``BodyCoupler`` constructor over a mesh on disk rather than
# hand building the object, and moves the mean 28 percent rather than 6.7. What
# is kept here is the identity below, which the invariance test does not state.


@finding(3, "mean_sab_w_m2 is a plain mean over triangles of unequal area")
def test_the_mean_absorbed_density_is_the_area_weighted_mean(remeshed_exposures) -> None:
    """`mean = p_abs / total_area`, which is the identity the fix establishes.

    ``p_abs`` is exactly ``sum(sab * area)``, so the area weighted mean density
    is already computed and only has to be divided. Stating it as an identity
    rather than as a tolerance is what makes this test the proof that the one
    line fix landed.
    """
    for exposure, area in remeshed_exposures:
        assert exposure.mean_sab_w_m2 == pytest.approx(exposure.absorbed_power_w / area, rel=1.0e-12)


def test_class_area_fractions_survive_remeshing() -> None:
    """The same invariant on the environment side, where it already holds.

    ``class_area_fractions`` weights by area and so is blind to the
    triangulation. Kept as the paired positive case: the surface side of the
    study does this correctly and the body side does not.
    """
    vertices = np.array(
        [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 12.0], [10.0, 0.0, 12.0]]
    )
    faces = np.array([[0, 1, 2], [0, 2, 3], [0, 1, 5], [0, 5, 4]])
    coarse_class = classify_faces(vertices, faces, 0.0)
    a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    coarse_area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    coarse = class_area_fractions(coarse_class, coarse_area)

    # Split the first triangle in two by pushing a new vertex onto one edge,
    # which changes the count without changing the surface.
    midpoint = 0.5 * (vertices[1] + vertices[2])
    fine_vertices = np.vstack([vertices, midpoint])
    fine_faces = np.array([[0, 1, 6], [0, 6, 2], [0, 2, 3], [0, 1, 5], [0, 5, 4]])
    fine_class = classify_faces(fine_vertices, fine_faces, 0.0)
    a, b, c = fine_vertices[fine_faces[:, 0]], fine_vertices[fine_faces[:, 1]], fine_vertices[fine_faces[:, 2]]
    fine_area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    fine = class_area_fractions(fine_class, fine_area)

    for name in CLASS_NAMES:
        assert fine[name] == pytest.approx(coarse[name], abs=1.0e-12), name
    assert sum(coarse.values()) == pytest.approx(1.0, abs=1.0e-12)


# ---------------------------------------------------------------------------
# Foliage: the slab has a closed form, and the module has to agree with itself.
# ---------------------------------------------------------------------------


def slab_susceptibility(observer_z_m: float, sigma_per_m: float, base_m: float, depth_m: float) -> float:
    from semantic_twin.materials.foliage import CanopyCanyonGeometry, FoliageMedium, FoliageTracer

    scene = CanopyCanyonGeometry(
        street_width_m=1.0e-6,
        street_length_m=1.0e4,
        facade_height_m=0.0,
        canopy_half_width_m=1.0e5,
        canopy_base_m=base_m,
        canopy_depth_m=depth_m,
    )
    medium = FoliageMedium(extinction_per_m=sigma_per_m, albedo=0.0, forward_fraction=0.0, phase_beamwidth_deg=180.0)
    tracer = FoliageTracer(
        scene,
        permittivity=np.array([PEC_PERMITTIVITY] * 4),
        rms_height_m=np.zeros(4),
        frequency_hz=FIFTEEN_GHZ,
        medium=medium,
        rays=200_000,
        seed=3,
    )
    return tracer.trace(np.array([0.0, 0.0, observer_z_m]), {"isotropic": ISOTROPIC}).susceptibility["isotropic"]


@pytest.mark.parametrize(
    ("where", "observer_z_m"),
    [
        ("below the canopy", 1.5),
        pytest.param(
            "inside the canopy",
            7.0,
            marks=finding(9, "the inside-canopy parity flag starts False wherever the observer is"),
        ),
    ],
)
def test_the_absorbing_slab_reproduces_the_exponential_integral(where: str, observer_z_m: float) -> None:
    """`chi = 1/2 E_2(tau_up) + 1/2 E_2(tau_down)`, from either side of the boundary.

    A ray leaving at ``mu = cos(theta)`` crosses a horizontal slab along a chord
    of ``depth / mu``, and ``mu`` is uniform on ``(0, 1]`` for directions drawn
    uniformly on the sphere, so the surviving fraction integrates to the second
    exponential integral. It is a sharp angle dependent target: Beer-Lambert
    along a single normal ray passes nothing here.

    ``tests/test_foliage.py`` already runs the observer below the canopy. The
    case that is not run is the observer standing in it, and it is the one that
    fails. The parity flag that says whether a ray is inside the medium is
    initialised to ``False`` for every ray whatever the observer's height, so a
    ray that starts inside has its parity inverted for the whole trace, then
    collides in vacuum. ``chi`` comes back as exactly 0.000000 against 0.21711,
    and ``absorbed_in_medium_fraction`` reads 1.0000, which cannot happen. It
    fails silently: nothing raises.
    """
    from scipy.special import expn

    sigma, base, depth = 0.25, 4.0, 6.0
    if observer_z_m < base:
        expected = 0.5 + 0.5 * float(expn(2, sigma * depth))
    else:
        upward = sigma * (base + depth - observer_z_m)
        downward = sigma * (observer_z_m - base)
        expected = 0.5 * float(expn(2, upward)) + 0.5 * float(expn(2, downward))
    assert slab_susceptibility(observer_z_m, sigma, base, depth) == pytest.approx(expected, rel=0.01), where


# The neper to decibel identity is pinned in
# ``test_invariant_foliage.py::test_the_two_routes_from_extinction_to_decibels_agree``,
# which runs the same comparison over four frequencies and two slab depths
# instead of three frequencies at one depth. The depth axis is what shows the
# disagreement is a constant factor of two rather than something that grows with
# optical depth, so that version is the one kept.


# ---------------------------------------------------------------------------
# Masonry: the rigorous solver against an analytic referee it cannot argue with.
# ---------------------------------------------------------------------------

LAMELLAR_FILL = 0.5
LAMELLAR_HIGH = 6.0 + 0.0j
LAMELLAR_LOW = 1.0 + 0.0j


def lamellar_profile(samples: int = 4096) -> np.ndarray:
    across = (np.arange(samples) + 0.5) / samples
    return np.where(across < LAMELLAR_FILL, LAMELLAR_HIGH, LAMELLAR_LOW)[None, :]


def grating_reflectance(period_m: float, polarisation: str, harmonics: int, profile: np.ndarray | None) -> float:
    from semantic_twin.materials.masonry.rcwa import Layer, solve

    substrate = Layer(profile if profile is not None else 0.0)
    solution = solve(
        [Layer(1.0 + 0.0j), substrate],
        period_x_m=period_m,
        period_y_m=period_m,
        frequency_hz=FIFTEEN_GHZ,
        theta_deg=0.0,
        polarisation=polarisation,
        harmonics=(harmonics, 0),
    )
    return solution.total_reflectance


@pytest.mark.parametrize(
    ("polarisation", "effective_permittivity"),
    [
        ("te", LAMELLAR_FILL * LAMELLAR_HIGH + (1.0 - LAMELLAR_FILL) * LAMELLAR_LOW),
        pytest.param(
            "tm",
            1.0 / (LAMELLAR_FILL / LAMELLAR_HIGH + (1.0 - LAMELLAR_FILL) / LAMELLAR_LOW),
            marks=finding(5, "Laurent's rule where Li's inverse rule is required for the TM case"),
        ),
    ],
)
def test_a_deeply_subwavelength_grating_is_its_own_effective_medium(
    polarisation: str, effective_permittivity: complex
) -> None:
    """A lamellar grating at one fortieth of a wavelength is a homogeneous slab.

    This is the classic referee for a Fourier modal solver and the reason is
    that the answer is known without solving anything. A binary grating whose
    period is far below the wavelength cannot resolve its own structure, so it
    reflects as a uniform medium: the arithmetic mean of the two permittivities
    for the field along the grooves, the harmonic mean for the field across
    them. The two differ by a factor of two here, so nothing about this test
    turns on the tolerance.

    The transverse electric case matches to 0.14 percent at four retained
    harmonics and does not improve past that, since the residual is the genuine
    second order effective medium correction rather than truncation. The
    transverse magnetic case is 22 percent high at four harmonics, 11 percent at
    eight, 5.8 percent at sixteen and 3.9 percent at twenty four. That is
    convergence as one over the harmonic count, which is the signature of
    Laurent's rule standing in for Li's inverse rule, and it converges to the
    right answer slowly rather than failing loudly.

    ``tests/test_rcwa.py`` checks ``R + T``, and cannot see this at all: the
    reflectance moves 2.4 percent while the sum stays at 1e-15.
    """
    from semantic_twin.materials.mmwave import wavelength_m

    period = float(wavelength_m(FIFTEEN_GHZ)) / 40.0
    homogeneous = grating_reflectance(period, polarisation, 0, np.full((1, 1), effective_permittivity))
    patterned = grating_reflectance(period, polarisation, 8, lamellar_profile())
    assert patterned == pytest.approx(homogeneous, rel=5.0e-3), polarisation


@pytest.mark.parametrize(
    ("regime", "period_over_wavelength", "harmonics"),
    [
        ("masonry pitch", 3.75, (4, 8, 16, 24, 32)),
        ("subwavelength", 20.0, (4, 8, 16, 24, 32)),
        ("deeply subwavelength", 100.0, (4, 8, 16, 24, 32)),
        ("effective-medium limit", 400.0, (4, 8, 16, 24, 32)),
    ],
)
def test_a_passive_grating_never_reflects_more_than_it_receives(
    regime: str, period_over_wavelength: float, harmonics: tuple[int, ...]
) -> None:
    """`R <= 1` at every truncation, for a lossless dielectric grating in vacuum.

    The module's own docstring says its only error is the Fourier truncation and
    that ``convergence_sweep`` reports it. That claim needs the solve to stay
    physical along the whole ladder, and at the masonry pitch it does.

    The ladder reaches one four hundredth of a wavelength. The retained orders
    then carry transverse wavenumbers in the thousands and the gap medium
    permittivity grows as their square. This is the regime where a numerical
    mode-direction error used to return reflectances of 12.8, 54, 56.7 or 58.

    The reason no existing test catches it is not the energy identity, and this
    is worth stating because the obvious guess is wrong. On a patterned half
    space the transmitted efficiency is ``nan`` by design, since the substrate
    modes are not plane waves and ``rcwa.py`` reports the budget as undefined
    rather than guessing it. So ``R + T`` is ``nan`` here on every run, the
    sound ones included, and no energy test is applied to this geometry at all.

    The old blind spot was narrow. ``tests/test_rcwa.py`` asserted
    ``0 < total_reflectance < 1`` on this patterned half space at one masonry
    point. The failure was not monotone in period, polarisation or truncation.
    This ladder keeps every one of those axes in the invariant.

    Finding 5 lives in the same solver and is a separate defect. That one is a
    steady bias from Laurent's rule; this one is a broken solve.

    The former strict xfail was removed only after this full ladder passed with
    Haswell, SkylakeX, Prescott and Zen OpenBLAS dispatch.
    """
    from semantic_twin.materials.mmwave import wavelength_m

    period = float(wavelength_m(FIFTEEN_GHZ)) / period_over_wavelength
    profile = lamellar_profile()
    for polarisation in ("te", "tm"):
        for count in harmonics:
            reflectance = grating_reflectance(period, polarisation, count, profile)
            assert 0.0 <= reflectance <= 1.0, (regime, polarisation, count, reflectance)


@pytest.mark.parametrize(
    "theta_deg",
    [
        0.0,
        pytest.param(45.0, marks=finding(6, "an angle is compared against a direction cosine width")),
        pytest.param(60.0, marks=finding(6, "an angle is compared against a direction cosine width")),
        pytest.param(85.0, marks=finding(6, "an angle is compared against a direction cosine width")),
    ],
)
def test_the_rendered_order_width_is_the_width_the_module_computes(theta_deg: float) -> None:
    """One angular width, two functions in one module, and they must agree.

    ``order_angular_width_deg`` converts the finite patch lobe width to an angle
    correctly: a width of ``lambda / W`` in direction cosine subtends
    ``lambda / (W cos(theta))`` in angle, because ``u = sin(theta)`` and so
    ``du = cos(theta) d(theta)``. ``bistatic_map`` lays the same lobe onto its
    direction cosine grid at width ``lambda / W`` and then reports it back as an
    angle without dividing, so its ``resolution_deg`` is short by exactly one
    over the cosine.

    At normal incidence the two agree and there is nothing to see, which is why
    that row is the control. At 45 degrees they differ by a factor of 1.41, at
    60 by 2 and at 85 by 11.5. The same missing cosine is applied to the
    receiver beam, and ``MASONRY.md``'s comb above trend numbers move 1.3 to 4.6
    dB at 60 degrees because of it.
    """
    from semantic_twin.materials.masonry import BRICK_FORMATS, RECESSED_JOINT, RUNNING_BOND, MasonryWall
    from semantic_twin.materials.masonry.kirchhoff import bistatic_map, order_angular_width_deg

    wall = MasonryWall(BRICK_FORMATS["standard_metric"], RECESSED_JOINT, RUNNING_BOND)
    patch_m = 1.0
    rendered = bistatic_map(
        wall,
        frequency_hz=FIFTEEN_GHZ,
        theta_deg=theta_deg,
        patch_size_m=patch_m,
        receiver_resolution_deg=0.0,
        samples=121,
        harmonics=(10, 6),
    )
    expected = order_angular_width_deg(patch_m, FIFTEEN_GHZ, theta_deg)
    assert rendered.resolution_deg == pytest.approx(expected, rel=1.0e-6)


# ---------------------------------------------------------------------------
# Roughness: the closure has to read every random term the class declares.
# ---------------------------------------------------------------------------


def test_the_two_rayleigh_closures_are_the_same_closure() -> None:
    """``tracer.specular_share`` and ``mmwave.specular_power_fraction`` are one formula.

    Written twice, in two modules, and the tracer's copy carries a clamp at
    ``g**2 = 60`` that the other does not. Below the clamp they have to be
    identical to the last bit, and where the clamp bites the tracer's must be
    the smaller of the two rather than the larger.
    """
    from semantic_twin.materials.mmwave import specular_power_fraction

    cosine = np.linspace(0.0, 1.0, 101)
    for rms in (0.0, 1.0e-4, 1.0e-3, 4.0e-3):
        wavelength = 299_792_458.0 / FIFTEEN_GHZ
        mine = specular_share(np.full_like(cosine, rms), cosine, wavelength)
        theirs = specular_power_fraction(np.full_like(cosine, rms), cosine, FIFTEEN_GHZ)
        assert np.all((mine >= 0.0) & (mine <= 1.0))
        assert np.allclose(mine, theirs, atol=1.0e-15), rms
    # Where the clamp bites, the shipped value is a ceiling and never a floor:
    # a metre of roughness against a two centimetre wavelength leaves nothing
    # coherent, and the clamp must not invent any.
    clamped = float(specular_share(np.array([1.0]), np.array([1.0]), 0.02)[0])
    unclamped = float(specular_power_fraction(np.array([1.0]), np.array([1.0]), FIFTEEN_GHZ)[0])
    assert 0.0 <= clamped < 1.0e-20
    assert clamped >= unclamped


@finding(2, "the wall scale random term unit_scatter_mm is never read")
def test_the_effective_roughness_reads_every_random_height_the_class_declares() -> None:
    """Change a declared random height and the roughness the tracer uses has to move.

    This one deliberately takes no side on the open question of whether
    ``unit_scatter_mm`` is an RMS or a full width, because that is not settled
    and the test does not need it settled. It asserts only that the number is
    read at all. ``_effective_rms_height`` folds the monolithic finish together
    with the deterministic mortar joint relief and never touches
    ``unit_scatter_mm``, so setting it to zero and to the top of its own stated
    range gives the same answer, and a brick wall's specular share does not
    depend on the one term the config calls "the random part of a brick wall
    that actually matters".
    """
    import dataclasses

    from semantic_twin.materials.roughness import effective_rms_height as _effective_rms_height

    library = SurfaceRoughnessLibrary.load(CONFIG / "surface_roughness.json")
    brick = library["brick_wall_with_mortar_joints"]
    assert brick.periodic_component is not None
    assert "unit_scatter_mm" in brick.periodic_component

    quiet = dataclasses.replace(brick, periodic_component={**brick.periodic_component, "unit_scatter_mm": 0.0})
    loud = dataclasses.replace(brick, periodic_component={**brick.periodic_component, "unit_scatter_mm": 9.0})
    assert _effective_rms_height(loud) > 1.5 * _effective_rms_height(quiet)
