"""Closed form and invariant tests for the adjoint SBR estimator.

MONOSTATIC_SBR.md section 11 orders these from "cannot be argued with" to
"agrees with another tool". Everything here is in the first category: an exact
analytic target, run against the same estimator that produces the published
numbers.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from semantic_twin.propagation import (
    ISOTROPIC,
    PEC_PERMITTIVITY,
    ROOFTOP,
    STREET_SMALL_CELL,
    TERMINATIONS,
    PathRecorder,
    PlaneGeometry,
    SbrTracer,
    SphereGeometry,
    TraceConfig,
    fibonacci_sphere,
    ground_plane_susceptibility,
)
from semantic_twin.propagation.closed_form import (
    ground_plane_band_average,
    ground_plane_susceptibility_te_only,
)
from semantic_twin.propagation.directions import (
    ROOFTOP_FIXED_HEIGHT,
    ROOFTOP_PATHLOSS,
    STREET_SMALL_CELL_FIXED_HEIGHT,
    STREET_SMALL_CELL_PATHLOSS,
    VARIANTS,
    IlluminationModel,
    elevation_band_measure,
    measure_below,
    sample_sphere,
)
from semantic_twin.propagation.scene import CLASS_NAMES, classify_faces
from semantic_twin.propagation.tracer import fresnel_power_reflectance, specular_share

MODELS = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
BAND_MODELS = {
    "rooftop": ROOFTOP,
    "street_small_cell": STREET_SMALL_CELL,
    "rooftop_pathloss": ROOFTOP_PATHLOSS,
    "street_small_cell_pathloss": STREET_SMALL_CELL_PATHLOSS,
}
CONCRETE = complex(5.24, -0.46055233310470917)


class EmptyGeometry:
    """No geometry at all. Every ray escapes on the zero bounce."""

    def intersect(self, origins, directions):  # noqa: ANN001, ANN201
        count = origins.shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, 1.0e30),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


def make_tracer(geometry, permittivity, rms, **kwargs):  # noqa: ANN001, ANN201
    config = TraceConfig(local_cells=256, exit_bands=18, **kwargs)
    return SbrTracer(geometry, None, np.array([permittivity]), np.array([rms]), config)


def test_fibonacci_sphere_is_near_equal_solid_angle() -> None:
    grid = fibonacci_sphere(4096)
    assert np.allclose(np.linalg.norm(grid, axis=1), 1.0)
    # The z marginal of an equal area sphere grid is uniform on [-1, 1].
    counts, _ = np.histogram(grid[:, 2], bins=16, range=(-1.0, 1.0))
    assert counts.max() / counts.min() < 1.02


def test_illumination_models_integrate_to_one() -> None:
    rng = np.random.default_rng(0)
    directions = sample_sphere(2_000_000, rng)
    for model in VARIANTS.values():
        total = 4.0 * np.pi * model.density(directions).mean()
        assert total == pytest.approx(1.0, abs=0.02), model.name


def test_the_elevation_quadrature_and_the_sphere_integral_are_the_same_number() -> None:
    """`Q_S` integrates to 1 over 4 pi by the route the tracer normalises on.

    The Monte Carlo check above says the two routes agree to sampling error.
    This one says they agree to quadrature error, which is the tolerance the
    free space identity actually inherits, since the tracer divides by
    ``normalisation()`` and nothing else.

    The residual is asserted to *shrink* as well as to be small. A constant
    offset would be a wrong Jacobian or a lost factor of 2 pi and would survive
    any number of abscissae. Trapezoid error falls as the square of the spacing,
    so quadrupling the samples must buy about sixteen times the agreement.
    """
    for model in VARIANTS.values():
        edges = np.array([model.elevation_min_deg, model.elevation_max_deg])
        coarse = abs(elevation_band_measure(model, edges)[0] - 1.0)
        fine = abs(elevation_band_measure(model, edges, samples=65_536)[0] - 1.0)
        assert coarse < 3.0e-6, model.name
        assert fine < coarse / 8.0, model.name


def draw_sites(model: IlluminationModel, count: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """The site population section 2.7 names, sampled directly.

    Uniform areal density on the annulus `[d_min, d_max]`, which is uniform in
    the squared radius, and a height drawn from the band independently of
    position. Returns the elevation of each site above the head and its slant
    range. Nothing here uses the illumination law, which is the point: it is the
    population the law has to be derived from, so it is the oracle.
    """
    rng = np.random.default_rng(seed)
    low_h, high_h = model.height_band_m
    near, far = model.range_band_m
    height = rng.uniform(low_h, high_h, size=count)
    radius = np.sqrt(rng.uniform(near**2, far**2, size=count))
    return np.arctan2(height, radius), np.hypot(height, radius)


def analytic_normalisation(model: IlluminationModel) -> float:
    """The band law's normalisation integrated by hand, as an independent oracle.

    Both band laws are piecewise elementary in elevation, because the two slant
    range bounds each switch once between a height cap and a range cap. On a
    height branch the integrand is `(h/sin)^p * cos`, on a range branch it is
    `(d/cos)^p * cos`, and both have closed antiderivatives for `p` of 1 and 3.
    This shares no code with ``normalisation``, which does the same integral by
    trapezoid.
    """
    low_h, high_h = model.height_band_m
    low_d, high_d = model.range_band_m
    low = np.radians(model.elevation_min_deg)
    high = np.radians(model.elevation_max_deg)
    far_knot, near_knot = model.knots()
    power = model.law == "uniform_sites_band_pathloss"

    def height_branch(h: float, a: float, b: float) -> float:
        if power:
            return h * (np.log(np.sin(b)) - np.log(np.sin(a)))
        return -0.5 * h**3 * (1.0 / np.sin(b) ** 2 - 1.0 / np.sin(a) ** 2)

    def range_branch(d: float, a: float, b: float) -> float:
        if power:
            return d * (b - a)
        return d**3 * (np.tan(b) - np.tan(a))

    edges = np.unique(np.clip([low, far_knot, near_knot, high], low, high))
    total = 0.0
    for a, b in zip(edges[:-1], edges[1:], strict=False):
        middle = 0.5 * (a + b)
        total += range_branch(high_d, a, b) if middle < far_knot else height_branch(high_h, a, b)
        total -= height_branch(low_h, a, b) if middle < near_knot else range_branch(low_d, a, b)
    return float(2.0 * np.pi * total) if power else float(2.0 * np.pi * total / 3.0)


def population_z_scores(
    population: IlluminationModel,
    law: IlluminationModel,
    count: int,
    seed: int,
    bins: int = 20,
) -> np.ndarray:
    """How many standard errors each elevation bin of ``law`` is from ``population``.

    The bins are equal measure under ``law``, so every bin carries about the
    same sampling error and the comparison is not dominated by whichever bin
    happens to be nearly empty. Sites are weighted by whatever ``law`` says a
    site contributes, one for a count law and `1/r^2` for a path loss law, and
    the expected weight in a bin is integrated across the bin rather than
    sampled at its midpoint.
    """
    elevation, slant = draw_sites(population, count, seed)
    weight = 1.0 / slant**2 if law.law.endswith("pathloss") else np.ones_like(slant)

    grid = np.linspace(law.elevation_min_deg, law.elevation_max_deg, 2001)
    cumulative = np.concatenate([[0.0], np.cumsum(elevation_band_measure(law, grid, samples=64))])
    edges = np.interp(np.linspace(0.0, 1.0, bins + 1), cumulative / cumulative[-1], grid)

    drawn, _ = np.histogram(np.degrees(elevation), bins=edges, weights=weight)
    variance, _ = np.histogram(np.degrees(elevation), bins=edges, weights=weight**2)
    expected = elevation_band_measure(law, edges)
    expected = expected / expected.sum() * drawn.sum()
    # A weighted bin sum has standard error sqrt(sum of squared weights), which
    # for a count law is the usual sqrt(n).
    return (drawn - expected) / np.sqrt(variance)


@pytest.mark.parametrize("name", sorted(BAND_MODELS))
def test_the_band_law_matches_the_population_it_claims_to_describe(name: str) -> None:
    """Section 2.7, corrected. The law is derived, so it has to be derivable.

    Draw the site population itself and bin its elevations. For the count
    weighted law each site counts once, for the path loss weighted law each site
    counts as its own free space spreading `1/r^2` with `r` the slant range. In
    both cases the histogram must reproduce `Q_S` with nothing left over, and at
    four million sites a bin holds enough that a one percent error in the law
    would show as twenty standard errors.
    """
    model = BAND_MODELS[name]
    z = population_z_scores(model, model, 4_000_000, seed=17)
    assert np.abs(z).max() < 4.0, f"{name}: worst bin is {np.abs(z).max():.1f} sigma from the law"


@pytest.mark.parametrize("name", sorted(BAND_MODELS))
def test_the_band_law_normalisation_agrees_with_the_hand_integral(name: str) -> None:
    """The shipped trapezoid against a closed form that shares no code with it.

    The residual has to shrink like trapezoid error, sixteen times per four
    times the abscissae. That is what says the two routes are the same integral
    rather than two integrals that happen to be close.
    """
    model = BAND_MODELS[name]
    target = analytic_normalisation(model)
    coarse = abs(model.normalisation() / target - 1.0)
    fine = abs(model.normalisation(3_200_001) / target - 1.0)
    assert coarse < 3.0e-9, name
    assert fine < coarse / 100.0, name


@pytest.mark.parametrize("name", sorted(BAND_MODELS))
def test_the_band_law_support_is_where_the_two_bands_still_intersect(name: str) -> None:
    """`el` in `[atan(h_min/d_max), atan(h_max/d_min)]`, and zero at both ends.

    The support is the one thing the uncorrected model already had right. What
    it did not have is that the density *vanishes* at both edges rather than
    peaking at the lower one: each edge is the single direction in which only
    one corner of the height by range rectangle is still visible, so the depth
    of population along it is zero.
    """
    model = BAND_MODELS[name]
    low_h, high_h = model.height_band_m
    low_d, high_d = model.range_band_m
    assert model.elevation_min_deg == pytest.approx(np.degrees(np.arctan2(low_h, high_d)), abs=1.0e-12)
    assert model.elevation_max_deg == pytest.approx(np.degrees(np.arctan2(high_h, low_d)), abs=1.0e-12)

    interior = np.radians(np.linspace(model.elevation_min_deg, model.elevation_max_deg, 501)[1:-1])
    inside = model.weight(np.column_stack([np.cos(interior), np.zeros_like(interior), np.sin(interior)]))
    assert np.all(inside > 0.0)

    elevation = np.radians(np.array([model.elevation_min_deg, model.elevation_max_deg]))
    edges = model.weight(np.column_stack([np.cos(elevation), np.zeros(2), np.sin(elevation)]))
    # Vanishing rather than bitwise zero. The edge is where two slant range
    # bounds meet, and subtracting two numbers the round trip through arcsin has
    # separated by an ulp leaves roundoff, twelve orders below the interior.
    assert np.all(edges < 1.0e-12 * inside.max())

    outside = np.radians(np.array([model.elevation_min_deg - 0.01, model.elevation_max_deg + 0.01, -45.0]))
    beyond = model.weight(np.column_stack([np.cos(outside), np.zeros(3), np.sin(outside)]))
    assert np.all(beyond == 0.0)


@pytest.mark.parametrize(
    ("band", "fixed"),
    [(ROOFTOP, ROOFTOP_FIXED_HEIGHT), (STREET_SMALL_CELL, STREET_SMALL_CELL_FIXED_HEIGHT)],
)
def test_the_fixed_height_law_survives_only_between_the_two_knots(
    band: IlluminationModel, fixed: IlluminationModel
) -> None:
    """Where neither range cap binds, the band law is the old `1/sin^3` law.

    This is what makes the correction a correction rather than a replacement.
    Between the two knots every height in the band is admissible at every
    elevation, so the mixture over heights contributes only a constant second
    moment and the shape is the single height law exactly. Outside them a range
    cap truncates the height band and the two part company.
    """
    far_knot, near_knot = band.knots()
    middle = np.linspace(far_knot, near_knot, 400)[1:-1]
    directions = np.column_stack([np.cos(middle), np.zeros_like(middle), np.sin(middle)])
    ratio = band.weight(directions) / fixed.weight(directions)
    assert np.max(ratio) / np.min(ratio) == pytest.approx(1.0, abs=1.0e-9)

    # And outside them the two laws are not each other, by a lot.
    wings = np.radians(np.array([band.elevation_min_deg + 0.05, band.elevation_max_deg - 0.05]))
    flanks = np.column_stack([np.cos(wings), np.zeros(2), np.sin(wings)])
    edge_ratio = band.density(flanks) / fixed.density(flanks)
    assert np.max(edge_ratio) < 0.05


def test_the_uncorrected_fixed_height_law_is_rejected_by_the_population() -> None:
    """The reading that shipped until 2026-08-02, pinned so it cannot come back.

    `1/sin^3(el)` is derived for sites at a single fixed height above the head.
    Read over the support of a height band it is not the law of that band's
    population, and the same Monte Carlo that confirms the corrected law refutes
    it. The failure is concentrated at the horizon, which is where the crop
    radius argument of section 9.4 lives, so it is not a cosmetic difference.
    """
    z = population_z_scores(ROOFTOP, ROOFTOP_FIXED_HEIGHT, 2_000_000, seed=19)
    # The same statistic that accepts the corrected law at under 4 sigma rejects
    # this one at hundreds. There is no sample size at which it would pass.
    assert np.abs(z).max() > 200.0
    assert np.count_nonzero(np.abs(z) > 20.0) >= 15
    # The specific way it fails: it puts most of the measure in the first few
    # degrees, where the population puts almost none.
    assert measure_below(ROOFTOP_FIXED_HEIGHT, 5.0) > 0.6
    assert measure_below(ROOFTOP, 5.0) < 0.1


def test_the_low_elevation_measure_is_what_section_2_7_now_reports() -> None:
    """The published fractions, pinned. These are the numbers the crop argument uses.

    Integrated per band rather than sampled at a midpoint, which for a convex
    `1/sin^3` law is the difference between a right answer and one that is
    wrong in a single direction and worst in the widest bin.
    """
    # The superseded pair keeps the rounded support the shipped code carried, not
    # the exact edges, because that is what reproduces the published numbers. The
    # difference is not decorative: the same law puts 61.7 percent below 5 degrees
    # on [3.1, 60.1], 62.0 percent on the exact [3.0910, 60.1135] and 64.2 percent
    # on a 3.0 degree edge, and section 2.7 quoted the last of those.
    assert (ROOFTOP_FIXED_HEIGHT.elevation_min_deg, ROOFTOP_FIXED_HEIGHT.elevation_max_deg) == (3.1, 60.1)
    assert measure_below(ROOFTOP_FIXED_HEIGHT, 5.0) == pytest.approx(0.617, abs=0.002)
    assert measure_below(ROOFTOP_FIXED_HEIGHT, 9.0) == pytest.approx(0.884, abs=0.002)
    assert measure_below(STREET_SMALL_CELL_FIXED_HEIGHT, 5.0) == pytest.approx(0.965, abs=0.002)

    exact = IlluminationModel(
        name="rooftop_fixed_height_exact_edges",
        law="uniform_sites",
        description="the same superseded law on the edges the bands imply",
        elevation_min_deg=ROOFTOP.elevation_min_deg,
        elevation_max_deg=ROOFTOP.elevation_max_deg,
    )
    assert measure_below(exact, 5.0) == pytest.approx(0.620, abs=0.002)

    assert measure_below(ROOFTOP, 5.0) == pytest.approx(0.094, abs=0.002)
    assert measure_below(ROOFTOP, 9.0) == pytest.approx(0.452, abs=0.002)
    assert measure_below(STREET_SMALL_CELL, 5.0) == pytest.approx(0.879, abs=0.002)

    assert measure_below(ROOFTOP_PATHLOSS, 5.0) == pytest.approx(0.032, abs=0.002)
    assert measure_below(STREET_SMALL_CELL_PATHLOSS, 5.0) == pytest.approx(0.422, abs=0.002)


def test_path_loss_on_horizontal_range_is_not_path_loss_on_slant_range() -> None:
    """Section 2.7's `1/(sin*cos^2)` reading, and what it costs.

    Free space spreading is `1/r^2` in the separation `r`, which is the slant
    range. Weighting by the horizontal range instead gives `1/(sin*cos^2)`
    against the correct `1/sin`, so the two differ by `1/cos^2`. That is 4 at
    60 degrees, at the top of the rooftop support, and it over-weights exactly
    the elevations the path loss term is there to suppress.
    """
    elevation = np.radians(np.array([5.0, 30.0, 45.0, 60.0]))
    horizontal = 1.0 / (np.sin(elevation) * np.cos(elevation) ** 2)
    slant = 1.0 / np.sin(elevation)
    assert np.allclose(horizontal / slant, 1.0 / np.cos(elevation) ** 2)
    assert (horizontal / slant)[-1] == pytest.approx(4.0, abs=1.0e-12)
    # The two agree at grazing, which is why the error is easy to miss: the
    # horizontal range is the separation only when the site is on the horizon.
    assert (horizontal / slant)[0] == pytest.approx(1.0, abs=0.01)


def test_free_space_identity() -> None:
    """Section 11.3. With no geometry T_S is the transverse projector and K_S is 1."""
    tracer = make_tracer(EmptyGeometry(), PEC_PERMITTIVITY, 0.0, rays=200_000, seed=1)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), VARIANTS)
    assert result.sky_fraction == 1.0
    assert result.susceptibility["isotropic"] == pytest.approx(1.0, abs=1.0e-6)
    assert np.max(np.abs(result.exit_profile - 1.0)) < 0.03
    # The uncorrected pair is the loose one, because a `1/sin^3` law concentrates
    # its mass in a solid angle a uniform ray set barely samples. The corrected
    # laws are bounded, so they converge three times faster on the same rays and
    # are held to a tolerance the old ones could not meet.
    for name, model in VARIANTS.items():
        tolerance = 0.05 if model.law in ("uniform_sites", "uniform_sites_pathloss") else 0.02
        assert result.susceptibility[name] == pytest.approx(1.0, abs=tolerance), name


def test_pec_ground_plane_gives_exactly_two() -> None:
    """Section 11.1. The angle independent closed form target is 2, not 1.

    A naive amplitude accumulating estimator returns 1.0 here with no visible
    noise, which is how section 2.8 of the design document was found. What this
    case cannot do is discriminate polarisation handling, since both Fresnel
    coefficients have unit magnitude at every angle. That job belongs to the
    dielectric test below. The target is 2 to about 1e-5 rather than to machine
    precision, because ``PEC_PERMITTIVITY`` is a large finite stand in for
    infinite conductivity.
    """
    tracer = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.0, rays=400_000, seed=2)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    half = result.exit_profile.size // 2
    upper = result.exit_profile[half:]
    lower = result.exit_profile[:half]
    assert np.max(np.abs(upper - 2.0)) < 0.03
    assert np.max(lower) == 0.0
    # Illumination confined above the horizon sees the same factor of two.
    assert result.susceptibility["rooftop"] == pytest.approx(2.0, rel=0.03)


def test_dielectric_ground_plane_matches_closed_form() -> None:
    """Section 11.1, dielectric case. This is the test with teeth.

    The perfect conductor case cannot discriminate anything about polarisation
    or material handling: both Fresnel coefficients have unit magnitude at
    every angle, so K is 2 whether the estimator averages TE and TM, uses one
    of them, or takes the larger. Concrete near its pseudo Brewster angle
    separates them by nearly three orders of magnitude, so the correct answer
    and the TE only answer differ by about 0.9 dB.
    """
    tracer = make_tracer(PlaneGeometry(0.0), CONCRETE, 0.0, rays=800_000, seed=3)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    target = ground_plane_band_average(result.exit_sin_edges, CONCRETE)
    centres = 0.5 * (result.exit_sin_edges[:-1] + result.exit_sin_edges[1:])
    above = centres > 0.0
    measured = result.exit_profile[above]
    assert np.max(np.abs(measured / target[above] - 1.0)) < 0.02

    # And the wrong answer has to be rejected, at every band where the two
    # differ by more than the Monte Carlo error.
    elevation = np.degrees(np.arcsin(centres[above]))
    wrong = ground_plane_susceptibility_te_only(elevation, CONCRETE)
    right = ground_plane_susceptibility(elevation, CONCRETE)
    separated = np.abs(wrong / right - 1.0) > 0.05
    assert separated.sum() >= 5
    assert np.all(np.abs(measured[separated] / wrong[separated] - 1.0) > 0.04)

    # The band nearest the pseudo Brewster angle. TM has all but vanished there,
    # so the two candidate answers sit about 0.9 dB apart and the trace has to
    # land on the lower one.
    sharpest = int(np.argmin(np.abs(elevation - 24.4)))
    assert elevation[sharpest] == pytest.approx(22.9, abs=1.0)
    assert right[sharpest] == pytest.approx(1.23, abs=0.02)
    separation_db = 10.0 * np.log10(wrong[sharpest] / right[sharpest])
    assert separation_db == pytest.approx(0.78, abs=0.05)
    assert measured[sharpest] == pytest.approx(right[sharpest], rel=0.02)


def test_fresnel_limits() -> None:
    cosine = np.linspace(0.0, 1.0, 21)
    perfect = fresnel_power_reflectance(cosine, np.asarray(PEC_PERMITTIVITY))
    # PEC_PERMITTIVITY is a large finite stand in for infinite conductivity, so
    # the reflectance falls short of 1 by order 1/sqrt(|eps|).
    assert np.allclose(perfect, 1.0, atol=1.0e-4)
    # Exact grazing on a vacuum interface is 0/0, which is degenerate rather
    # than wrong, so it is excluded rather than papered over.
    vacuum = fresnel_power_reflectance(cosine[1:], np.asarray(complex(1.0, 0.0)))
    assert np.allclose(vacuum, 0.0, atol=1.0e-12)
    concrete = fresnel_power_reflectance(cosine, np.asarray(CONCRETE))
    assert np.all((concrete >= 0.0) & (concrete <= 1.0))
    # Grazing incidence reflects everything, normal incidence does not.
    assert concrete[0] == pytest.approx(1.0, abs=1.0e-6)
    assert concrete[-1] < 0.2


def test_specular_share_is_a_fraction() -> None:
    cosine = np.linspace(0.0, 1.0, 11)
    share = specular_share(np.full_like(cosine, 0.004), cosine, 0.02)
    assert np.all((share >= 0.0) & (share <= 1.0))
    assert share[0] == pytest.approx(1.0)
    assert share[-1] < share[0]
    smooth = specular_share(np.zeros_like(cosine), cosine, 0.02)
    assert np.allclose(smooth, 1.0)


def test_closed_lossless_cavity_conserves_energy() -> None:
    """Section 11.3 white furnace. Nothing escapes a closed perfect reflector."""
    tracer = make_tracer(SphereGeometry(10.0), PEC_PERMITTIVITY, 0.0, rays=20_000, seed=4, max_bounces=8)
    result = tracer.trace(np.array([0.0, 0.0, 0.0]), {"isotropic": ISOTROPIC})
    assert result.escaped_fraction == 0.0
    assert result.susceptibility["isotropic"] == 0.0
    assert result.diagnostics["truncated_rays"] == 20_000


def test_susceptibility_is_non_negative_and_bounded_by_the_reflector() -> None:
    """A lossy ground can only remove power relative to the perfect one."""
    lossy = make_tracer(PlaneGeometry(0.0), CONCRETE, 0.0, rays=200_000, seed=5)
    perfect = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.0, rays=200_000, seed=5)
    a = lossy.trace(np.array([0.0, 0.0, 1.5]), MODELS).susceptibility["rooftop"]
    b = perfect.trace(np.array([0.0, 0.0, 1.5]), MODELS).susceptibility["rooftop"]
    assert 1.0 <= a <= b


def test_zero_bounce_susceptibility_equals_the_sky_fraction() -> None:
    """Section 2.7. `K_iso^(0)` is the sky fraction, exactly and by definition.

    This is the strongest cheap check in the suite and it costs nothing. The
    zero bounce transfer tensor is the identity in sky visible directions and
    zero in blocked ones, so its isotropic average is the sky solid angle
    fraction. Getting it right requires the direction binning, the per cell
    solid angle weight, the occlusion test and the illumination normalisation
    to all be correct at once, and unlike the ground plane cases it holds for
    any geometry whatever, so it is asserted here on a plane, on a sphere and
    on nothing at all.

    It is an identity of the estimator rather than an independent measurement,
    so it cannot detect a systematically wrong ray distribution. What it does
    detect is any inconsistency between the two ways this code counts the same
    directions.

    It holds to Monte Carlo precision and not exactly, and the reason is worth
    recording because the near miss looks like a bug and is not one. The sky
    fraction is a ratio of sums over all rays, while ``chi_iso_direct`` sums a
    per cell mean, so the two differ by the covariance between a cell's escape
    rate and its ray count. Both are unbiased for the same limit and they
    converge to each other, which is what the scaling test below asserts.
    """
    for geometry, expected in ((EmptyGeometry(), 1.0), (PlaneGeometry(0.0), 0.5)):
        tracer = make_tracer(geometry, CONCRETE, 0.0, rays=200_000, seed=6)
        result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
        assert result.sky_fraction == pytest.approx(expected, abs=0.01)
        assert result.susceptibility_direct["isotropic"] == pytest.approx(result.sky_fraction, rel=0.01)


def test_sky_fraction_identity_converges_as_the_ray_count_grows() -> None:
    """The residual in the identity is Monte Carlo noise, so it must shrink.

    A constant offset would mean a genuine normalisation error. A residual that
    falls roughly as one over the square root of the ray count is the ratio
    estimator behaving as it should.
    """
    geometry = SphereGeometry(20.0, (0.0, 0.0, -19.0))
    residuals = []
    for rays in (25_000, 400_000):
        tracer = make_tracer(geometry, CONCRETE, 0.0, rays=rays, seed=9)
        result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS)
        assert 0.0 < result.sky_fraction < 1.0
        residuals.append(abs(result.susceptibility_direct["isotropic"] / result.sky_fraction - 1.0))
    # Sixteen times the rays should buy about four times the agreement. Allow a
    # wide margin, since a single realisation of a noise level is itself noisy.
    assert residuals[1] < residuals[0] / 2.0
    assert residuals[1] < 3.0e-3


def test_lambertian_ground_plane_matches_one_plus_two_sine() -> None:
    """Closed form for the diffuse branch, which the specular tests never touch.

    Make the plane a perfect reflector and rough enough that the Rayleigh
    coherent fraction vanishes, so every bounce is cosine scattered. Half the
    rays leave upward and escape, contributing 1. The other half hit the plane
    and re-emit with density ``cos(theta)/pi = sin(el)/pi``, so their
    contribution to ``K_tot`` is ``4*pi*(1/2)*sin(el)/pi = 2*sin(el)``. Hence

        K_tot(el) = 1 + 2*sin(el)

    exactly, running from 1 at the horizon to 3 at the zenith. This tests the
    cosine hemisphere sampler and the diffuse throughput weight together, and a
    wrong power of the cosine in either shows up immediately as a slope error.
    """
    tracer = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.5, rays=800_000, seed=7, max_bounces=1)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    edges = result.exit_sin_edges
    above = 0.5 * (edges[:-1] + edges[1:]) > 0.0
    # Band average of 1 + 2*sin(el) over equal solid angle bands in sin(el).
    target = 1.0 + 2.0 * 0.5 * (edges[:-1] + edges[1:])
    measured = result.exit_profile
    assert np.max(np.abs(measured[above] - target[above])) < 0.06
    assert np.max(measured[~above]) == 0.0
    assert measured[above].mean() == pytest.approx(2.0, rel=0.01)


def test_rayleigh_criterion_is_angle_dependent_at_grazing() -> None:
    """The same plane is rough at the zenith and smooth at the horizon.

    ``g = 4*pi*s*cos(theta)/lam`` uses the incidence cosine, which for a ground
    plane is ``sin(el)``, so a surface that fully diffuses a steep ray still
    reflects a grazing one specularly. Against the pure Lambertian closed form
    of the previous test, that shows up as an excess in the lowest elevation
    band and nowhere else.
    """
    tracer = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.05, rays=800_000, seed=7, max_bounces=1)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)
    edges = result.exit_sin_edges
    lambertian = 1.0 + 2.0 * 0.5 * (edges[:-1] + edges[1:])
    excess = result.exit_profile - lambertian
    half = excess.size // 2
    assert excess[half] > 0.15
    assert np.max(np.abs(excess[half + 1 :])) < 0.08


def test_roughness_conserves_power_and_flattens_the_specular_lobe() -> None:
    smooth = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.0, rays=200_000, seed=7)
    rough = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.05, rays=200_000, seed=7)
    fine = smooth.trace(np.array([0.0, 0.0, 1.5]), MODELS).exit_profile
    coarse = rough.trace(np.array([0.0, 0.0, 1.5]), MODELS).exit_profile
    # A perfect reflector conserves power whatever the roughness, so the total
    # over the exit bands is unchanged, only its distribution moves.
    assert coarse.sum() == pytest.approx(fine.sum(), rel=0.02)
    half = fine.size // 2
    # Specular reflection off a plane maps elevation to elevation, so the smooth
    # profile is flat. Diffuse scattering is not, and tilts toward the zenith.
    assert np.max(np.abs(fine[half:] - 2.0)) < 0.05
    assert np.max(np.abs(coarse[half:] - 2.0)) > 0.5
    assert coarse[-1] > coarse[half]


def test_absorbed_power_density_obeys_the_relu_bound() -> None:
    """`Sab = Sinc*T0*ReLU[n.(-k)]` can never exceed `Sinc*T0`, for any spectrum.

    This is the monograph's own bound applied to whatever the tracer produces,
    and it is the check that catches a solid angle weight or a sign error in the
    handover from the environment side to the body side. It is run against real
    traced spectra in the study, and here against three extreme ones.
    """
    pytest.importorskip("aegis")
    from semantic_twin.propagation.exposure import BodyCoupler

    phantom = pathlib.Path("/home/user/aegis/data/duke.stl")
    if not phantom.exists():
        pytest.skip("phantom mesh not available")
    coupler = BodyCoupler(str(phantom), 15.0e9, body_mass_kg=72.4)
    grid = fibonacci_sphere(256)
    solid_angle = 4.0 * np.pi / 256
    rng = np.random.default_rng(0)
    spectra = {
        "isotropic": np.full(256, 1.0 / (4.0 * np.pi)),
        "single direction": np.eye(256)[0] / solid_angle,
        "random": np.abs(rng.normal(size=256)),
    }
    for name, rho in spectra.items():
        exposure = coupler.couple(grid, rho, solid_angle, 1.0)
        bound = exposure.arriving_power_density_w_m2 * coupler.engine.T0
        assert exposure.peak_sab_w_m2 <= bound * (1.0 + 1.0e-9), name
        assert exposure.mean_sab_w_m2 <= exposure.peak_sab_w_m2 + 1.0e-12
        assert exposure.absorbed_power_w >= 0.0
    # A single plane wave all but saturates the bound. It falls short by the
    # angle between the arrival direction and the best aligned facet normal,
    # which on a 56k triangle phantom is small but not zero, so the bound is
    # approached from below rather than met exactly.
    single = coupler.couple(grid, spectra["single direction"], solid_angle, 1.0)
    assert single.peak_sab_w_m2 <= coupler.engine.T0
    assert single.peak_sab_w_m2 > 0.999 * coupler.engine.T0
    # Isotropic illumination puts the mean at exactly a quarter of it, because
    # the average of ReLU(cos) over the sphere is 1/4.
    isotropic = coupler.couple(grid, spectra["isotropic"], solid_angle, 1.0)
    assert isotropic.mean_sab_w_m2 == pytest.approx(coupler.engine.T0 / 4.0, rel=0.02)


def test_classify_faces_separates_ground_facade_and_roof() -> None:
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 20.0],
            [1.0, 0.0, 20.0],
            [0.0, 1.0, 20.0],
            [0.0, 0.0, 10.0],
            [0.0, 1.0, 10.0],
        ]
    )
    faces = np.array([[0, 1, 2], [3, 4, 5], [0, 2, 6], [3, 5, 4]])
    index = classify_faces(vertices, faces, 0.0)
    assert CLASS_NAMES[index[0]] == "ground"
    assert CLASS_NAMES[index[1]] == "roof"
    assert CLASS_NAMES[index[2]] == "facade"
    assert vertices[7][2] == 10.0


def test_excess_delay_matches_image_theory_on_a_ground_plane() -> None:
    """Section 2.4. `Delta = l_K - u_e.(x_K - S)` must equal `2*h*sin(el)`."""
    height = 1.5
    tracer = make_tracer(PlaneGeometry(0.0), PEC_PERMITTIVITY, 0.0, rays=400_000, seed=8)
    result = tracer.trace(np.array([0.0, 0.0, height]), MODELS, ground_z_m=0.0)
    # Half the rays go straight up with zero excess path, half reflect. The
    # throughput weighted mean excess path is therefore half the mean of
    # 2*h*sin(el) over the downward hemisphere, which is 2*h*(1/2)/2 = h/2.
    expected_ns = 0.5 * height / 299_792_458.0 * 1e9
    assert result.mean_excess_delay_ns == pytest.approx(expected_ns, rel=0.02)


def test_recording_paths_does_not_change_a_single_number() -> None:
    """The recorder must be a passive observer, not a second consumer of the rng.

    This is the only thing that makes a visualisation trustworthy as a picture
    of the estimator: the rays drawn are the rays integrated, because attaching
    the recorder returns a bit identical result.
    """
    origin = np.array([0.0, 0.0, 1.5])
    plain = make_tracer(PlaneGeometry(0.0), CONCRETE, 0.0, rays=20_000, seed=11)
    watched = make_tracer(PlaneGeometry(0.0), CONCRETE, 0.0, rays=20_000, seed=11)
    recorder = PathRecorder(capacity=64)

    reference = plain.trace(origin, MODELS, ground_z_m=0.0)
    observed = watched.trace(origin, MODELS, ground_z_m=0.0, recorder=recorder)

    for name in MODELS:
        assert observed.susceptibility[name] == reference.susceptibility[name]
        assert np.array_equal(observed.rho[name], reference.rho[name])
    assert observed.sky_fraction == reference.sky_fraction
    assert observed.mean_bounces == reference.mean_bounces
    assert observed.escaped_fraction == reference.escaped_fraction


def test_recorded_paths_start_at_the_observer_and_every_ray_terminates() -> None:
    origin = np.array([0.0, 0.0, 1.5])
    tracer = make_tracer(PlaneGeometry(0.0), CONCRETE, 0.0, rays=5_000, seed=12)
    recorder = PathRecorder(capacity=200, sky_distance_m=250.0)
    tracer.trace(origin, MODELS, ground_z_m=0.0, recorder=recorder)
    record = recorder.result()

    assert len(record) == 200
    assert record.offsets[0] == 0
    assert record.offsets[-1] == record.vertices.shape[0]
    # A path is at least an origin and a termination, and a ray with b bounces
    # has exactly b + 2 vertices.
    counts = np.diff(record.offsets)
    assert np.all(counts >= 2)
    assert np.array_equal(counts, record.bounces + 2)
    for start in record.offsets[:-1]:
        assert np.array_equal(record.vertices[start], origin)
    # Throughput never grows along a path except where Russian roulette
    # divides by the survival probability, which only fires from bounce three.
    for i in range(len(record)):
        segment = record.throughput[record.offsets[i] : record.offsets[i + 1]]
        if record.bounces[i] < 3:
            assert np.all(np.diff(segment) <= 1.0e-12)


def test_recorded_terminations_agree_with_the_traced_totals() -> None:
    """Sky terminations among the recorded rays must track the escape fraction."""
    origin = np.array([0.0, 0.0, 1.5])
    tracer = make_tracer(PlaneGeometry(0.0), CONCRETE, 0.0, rays=4_000, seed=13, max_bounces=4)
    recorder = PathRecorder(capacity=4_000)
    result = tracer.trace(origin, MODELS, ground_z_m=0.0, recorder=recorder)
    record = recorder.result()

    sky = TERMINATIONS.index("sky")
    assert np.count_nonzero(record.termination == sky) / len(record) == pytest.approx(
        result.escaped_fraction, abs=1.0e-12
    )
    # Zero bounce rays are exactly the ones that saw sky without touching
    # anything, which is the sky fraction.
    straight = np.count_nonzero((record.termination == sky) & (record.bounces == 0))
    assert straight / len(record) == pytest.approx(result.sky_fraction, abs=1.0e-12)
    assert np.allclose(np.linalg.norm(record.exit_direction, axis=1), 1.0)
