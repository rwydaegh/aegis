"""Closed form targets for the susceptibility itself, not only the exit profile.

Why this file exists, stated plainly, because it is the whole point of it.

``tests/test_propagation.py`` already checks the estimator hard, but almost
everything it checks is ``exit_profile``, a diagnostic nothing downstream
consumes. The published quantity is ``susceptibility``, and every closed form
the suite had for it was *independent of the illumination law*: free space gives
1 because ``Q`` integrates to 1, and a perfect conductor under any illumination
confined above the horizon gives 2 for the same reason. Replace the elevation
law with a completely different function of elevation, keep it normalised and
above the horizon, and both targets are still met exactly. That is the shape of
the defect MONOSTATIC_SBR.md section 2.7 records: a law that was wrong for years
and was caught by rederiving an integral, not by a test failing.

So the targets here are law dependent by construction. A half space under the
observation point admits a closed form for `chi` that carries the elevation law
inside the integrand:

    chi = int_up Q(u) dOmega
        + int_up R(u_z) kappa(u_z) Q(u) dOmega
        + I_cos * 2 pi int_0^1 R(s) (1 - kappa(s)) ds,      I_cos = (1/pi) int_up Q(v) v_z dOmega

The three terms are the ray that escapes without touching anything, the ray that
reflects specularly off the plane, and the ray the Rayleigh split sends into the
Lambertian lobe instead. Derivation in the docstring of :func:`chi_over_half_space`.

The oracle below shares no line of code with the package. Fresnel and the
Rayleigh factor are reimplemented rather than imported, so a sign error inside
``tracer.py`` cannot cancel itself.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.propagation import (
    ISOTROPIC,
    PEC_PERMITTIVITY,
    ROOFTOP,
    STREET_SMALL_CELL,
    IlluminationModel,
    PlaneGeometry,
    SbrTracer,
    TraceConfig,
)

#: ITU-R P.2040-4 concrete at 15 GHz, the row the ground class actually binds to.
CONCRETE = complex(5.24, -0.46055233310470917)
WAVELENGTH_M = 299_792_458.0 / 15.0e9
MODELS = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}

#: Coarse enough that the Rayleigh split is genuinely mixed across the band the
#: illumination laws occupy, which is what gives the two branch closed form its
#: discriminating power. At 15 GHz, ``g = 4 pi s cos(th) / lam`` is 0.63 at ten
#: degrees elevation and 3.4 at sixty, so kappa runs from 0.67 down to 1e-5.
ROUGH_M = 0.010


def fresnel_unpolarised(cos_incidence: np.ndarray, permittivity: complex) -> np.ndarray:
    """Mean of the TE and TM power reflectances of a half space.

    Reimplemented here on purpose. ``closed_form.ground_plane_susceptibility``
    calls ``tracer.fresnel_power_reflectance``, so it is not an independent
    oracle for the surface model, only for the ``1 +`` structure around it.
    """
    cos_i = np.clip(np.asarray(cos_incidence, dtype=np.float64), 0.0, 1.0).astype(np.complex128)
    sin_sq = 1.0 - cos_i**2
    root = np.sqrt(permittivity - sin_sq)
    te = (cos_i - root) / (cos_i + root)
    tm = (permittivity * cos_i - root) / (permittivity * cos_i + root)
    return np.real(0.5 * (np.abs(te) ** 2 + np.abs(tm) ** 2))


def coherent_power_fraction(cos_incidence: np.ndarray, rms_height_m: float) -> np.ndarray:
    """Rayleigh coherent *power* fraction, ``exp(-g**2)``, ``g = 4 pi s cos(th) / lam``.

    The power of two matters and is the thing most easily got wrong. The
    coherent reflection coefficient is reduced in *amplitude* by ``exp(-g**2/2)``,
    so the coherent share of the *power* is its square, ``exp(-g**2)``. An
    estimator that uses the amplitude factor as a power fraction sends too little
    into the diffuse lobe, and
    :func:`test_the_two_branch_target_rejects_four_specific_implementation_errors`
    pins how far wrong that is.
    """
    g = 4.0 * np.pi * rms_height_m * np.clip(np.asarray(cos_incidence, dtype=np.float64), 0.0, 1.0) / WAVELENGTH_M
    return np.exp(-np.minimum(g * g, 60.0))


def chi_over_half_space(
    model: IlluminationModel,
    permittivity: complex,
    rms_height_m: float,
    *,
    samples: int = 200_001,
    fresnel: str = "unpolarised",
    coherent: str = "power",
    diffuse: str = "cosine",
) -> float:
    """`chi` for one illumination law over an infinite half space, in closed form.

    The observation point sits above an infinite plane, so the geometry is
    exactly solvable and every departure direction has a known fate.

    A ray leaving upward escapes at once and deposits ``Q(u)``. A ray leaving
    downward with ``u_z = -s`` meets the plane at incidence cosine ``s``, is
    multiplied by ``R(s)``, and then leaves specularly with probability
    ``kappa(s)`` or into a cosine lobe with probability ``1 - kappa(s)``. The
    specular exit direction is the mirror image of the departure direction, and
    mirroring is measure preserving, so that branch can be rewritten as an
    integral over the *upper* hemisphere. The cosine lobe forgets the incoming
    direction entirely, which is what lets it factor:

        chi = 4 pi E_u[w(u) Q(u_exit)]
            = int_up Q dOmega                                    escaped, no contact
            + int_up R(v_z) kappa(v_z) Q(v) dOmega                specular branch
            + I_cos * int_down R(s) (1 - kappa(s)) dOmega         diffuse branch

    with ``I_cos = (1/pi) int_up Q(v) v_z dOmega`` the mean of ``Q`` under the
    cosine lobe and ``int_down R (1-kappa) dOmega = 2 pi int_0^1 R (1-kappa) ds``.

    Only one bounce is ever possible: from an upward facing plane both the
    mirror direction and every cosine lobe sample point upward. So the target is
    exact rather than truncated, and it holds at ``max_bounces = 1``.

    The keyword arguments select deliberately wrong variants, used only to show
    the assertions have teeth.
    """
    elevation = np.linspace(1.0e-12, 0.5 * np.pi - 1.0e-12, samples)
    upward = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
    density = model.density(upward)
    sine = np.sin(elevation)
    jacobian = 2.0 * np.pi * np.cos(elevation)

    def reflectance(cos_i: np.ndarray) -> np.ndarray:
        if fresnel == "te_only":
            cos_c = np.clip(cos_i, 0.0, 1.0).astype(np.complex128)
            root = np.sqrt(permittivity - (1.0 - cos_c**2))
            return np.real(np.abs((cos_c - root) / (cos_c + root)) ** 2)
        return fresnel_unpolarised(cos_i, permittivity)

    def share(cos_i: np.ndarray) -> np.ndarray:
        if coherent == "amplitude":
            return np.sqrt(coherent_power_fraction(cos_i, rms_height_m))
        return coherent_power_fraction(cos_i, rms_height_m)

    direct = float(np.trapezoid(density * jacobian, elevation))
    specular = float(np.trapezoid(density * reflectance(sine) * share(sine) * jacobian, elevation))
    if diffuse == "dropped":
        return direct + specular
    if diffuse == "uniform":
        lobe = float(np.trapezoid(density * jacobian, elevation)) / (2.0 * np.pi)
    else:
        lobe = float(np.trapezoid(density * sine * jacobian, elevation)) / np.pi
    grid = np.linspace(0.0, 1.0, samples)
    pool = 2.0 * np.pi * float(np.trapezoid(reflectance(grid) * (1.0 - share(grid)), grid))
    return direct + specular + lobe * pool


def trace_plane(
    permittivity: complex,
    rms_height_m: float,
    *,
    rays: int = 800_000,
    seed: int = 21,
    local_cells: int = 512,
    roulette_start: int = 3,
    max_bounces: int = 1,
):  # noqa: ANN201
    config = TraceConfig(
        frequency_hz=15.0e9,
        rays=rays,
        local_cells=local_cells,
        exit_bands=18,
        max_bounces=max_bounces,
        roulette_start=roulette_start,
        seed=seed,
    )
    tracer = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([permittivity]),
        np.array([rms_height_m]),
        config,
    )
    return tracer.trace(np.array([0.0, 0.0, 1.5]), MODELS, ground_z_m=0.0)


# Per model tolerance on the traced susceptibility. These are not round numbers
# picked for comfort: the residual against the closed form was measured over
# twenty four independent seeds at this ray count, and the worst draw was 0.0002
# isotropic, 0.0048 rooftop and 0.0086 street small cell. Each tolerance is a
# little over twice its measured worst case. The three differ by more than an
# order of magnitude because the variance is set by how peaked ``Q`` is, and the
# street small cell law crowds its whole mass into the first thirty degrees.
CHI_TOLERANCE = {"isotropic": 0.002, "rooftop": 0.012, "street_small_cell": 0.020}


def test_the_oracle_reproduces_the_two_targets_the_suite_already_trusts() -> None:
    """Before the oracle is used to judge the tracer, it has to pass what is known.

    Two independently derived special cases exist in the suite already. A
    perfect conductor under illumination confined above the horizon gives
    ``chi = 2``, because the direct and the specular branch each carry the whole
    measure. A perfect conductor rough enough to kill the coherent branch turns
    the second branch into the Lambertian one behind
    ``test_lambertian_ground_plane_matches_one_plus_two_sine``, leaving
    ``chi = M + 2 <sin el>_Q`` with ``M`` the measure above the horizon. The
    general formula has to collapse onto both.

    Writing ``1`` for ``M`` is the easy slip and is wrong for isotropic
    illumination, which puts half its mass below the horizon where an infinite
    plane means no ray ever escapes to sample it.
    """
    for name in ("rooftop", "street_small_cell"):
        assert chi_over_half_space(MODELS[name], PEC_PERMITTIVITY, 0.0) == pytest.approx(2.0, abs=1.0e-4)

    for name, model in MODELS.items():
        elevation = np.linspace(1.0e-12, 0.5 * np.pi - 1.0e-12, 200_001)
        directions = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
        jacobian = 2.0 * np.pi * np.cos(elevation)
        above_horizon = np.trapezoid(model.density(directions) * jacobian, elevation)
        mean_sine = np.trapezoid(model.density(directions) * np.sin(elevation) * jacobian, elevation)
        assert above_horizon == pytest.approx(0.5 if name == "isotropic" else 1.0, abs=1.0e-6), name
        # A limit rather than an idealisation, because "rough enough that the
        # coherent branch vanishes" is never exactly true. Two floors sit under
        # this identity and conflating them would hide either one.
        #
        # The first is ``PEC_PERMITTIVITY`` being large but finite, so the
        # reflectance falls short of 1 by about 1.8e-5 averaged over incidence.
        # Every law inherits half of that, and isotropic illumination inherits
        # nothing else, which is why its residual does not move with roughness
        # at all.
        #
        # The second belongs to the laws whose support stops above the horizon.
        # At RMS height s the coherent fraction survives inside roughly
        # ``lam/(4 pi s)`` of grazing, and it reflects into grazing directions
        # those laws do not illuminate, so that power is lost rather than
        # rescattered. It falls like 1/s, and asserting that it does is what
        # says the general formula tends to the Lambertian one rather than
        # merely sitting near it.
        target = above_horizon + 2.0 * mean_sine
        residual = [abs(chi_over_half_space(model, PEC_PERMITTIVITY, s) / target - 1.0) for s in (0.5, 5.0, 50.0)]
        assert residual[-1] < 3.0e-5, (name, residual)
        if name == "isotropic":
            assert max(residual) - min(residual) < 1.0e-8, residual
            assert residual[0] == pytest.approx(
                0.5 * (1.0 - np.mean(fresnel_unpolarised(np.linspace(0.0, 1.0, 200_001), PEC_PERMITTIVITY))),
                rel=0.05,
            )
        else:
            assert residual[1] < residual[0] / 5.0, (name, residual)
            assert residual[2] < residual[1] / 5.0, (name, residual)

    # Isotropic illumination over a lossless plane can only give back what it put
    # in, whatever the roughness, because nothing absorbs and nothing escapes
    # downward. That is a conservation statement, not a quadrature one.
    for rough in (0.0, 0.002, 0.5):
        assert chi_over_half_space(ISOTROPIC, PEC_PERMITTIVITY, rough) == pytest.approx(1.0, abs=1.0e-4)


def test_chi_over_a_smooth_dielectric_plane_matches_the_closed_form() -> None:
    """`chi = int_up Q(u) [1 + R(u_z)] dOmega`, one number per illumination law.

    This is the first target in the suite for the published quantity that
    depends on the *shape* of the elevation law and not merely on its
    normalisation. The three laws land on 0.644, 1.446 and 1.751 over the same
    plane, so swapping one law for another moves the target by up to 4.3 dB and
    the test notices.
    """
    result = trace_plane(CONCRETE, 0.0)
    for name, model in MODELS.items():
        target = chi_over_half_space(model, CONCRETE, 0.0)
        assert result.susceptibility[name] == pytest.approx(target, rel=CHI_TOLERANCE[name]), name

    # And the three targets really are far apart, so the agreement above is a
    # constraint on the law and not a coincidence any normalised law would meet.
    targets = np.array([chi_over_half_space(model, CONCRETE, 0.0) for model in MODELS.values()])
    assert targets.max() / targets.min() > 2.5


def test_chi_over_a_rough_dielectric_plane_matches_the_two_branch_closed_form() -> None:
    """The Rayleigh split, the diffuse lobe and the illumination law, all at once.

    At ten millimetre RMS the coherent share runs from 0.67 near the horizon to
    a part in a hundred thousand at sixty degrees, so both branches carry real
    weight over the support of every law here. Meeting this target requires the
    Fresnel average, the coherent fraction, the survival of the incoherent
    remainder into the Lambertian lobe, the cosine lobe normalisation, the
    ``4 pi / N`` quadrature constant and the illumination density to be
    simultaneously right.
    """
    result = trace_plane(CONCRETE, ROUGH_M)
    for name, model in MODELS.items():
        target = chi_over_half_space(model, CONCRETE, ROUGH_M)
        assert result.susceptibility[name] == pytest.approx(target, rel=CHI_TOLERANCE[name]), name


def test_the_two_branch_target_rejects_four_specific_implementation_errors() -> None:
    """A target that cannot fail is not a target. These are the ways it fails.

    Four mistakes, each one a plausible thing to write, each one invisible to
    every closed form the suite had before this file:

    * reading the Rayleigh factor as an amplitude and using it as a power share,
      which under-fills the diffuse lobe,
    * multiplying the throughput by the coherent share and dropping the
      incoherent remainder instead of scattering it, which loses power,
    * taking TE alone instead of the unpolarised average, the mistake the
      dielectric exit profile test already rejects, checked here on ``chi`` too,
    * sampling the diffuse lobe uniformly over the hemisphere rather than by
      cosine.

    Each is asserted to be separated from the truth by more than the tolerance,
    and then the trace is asserted to be inconsistent with it. The perfect
    conductor cases cannot do any of this, and neither can free space.
    """
    rough = trace_plane(CONCRETE, ROUGH_M)
    wrong = {
        "coherent fraction read as an amplitude": {"coherent": "amplitude"},
        "incoherent remainder dropped": {"diffuse": "dropped"},
        "TE only instead of the unpolarised average": {"fresnel": "te_only"},
        "diffuse lobe uniform instead of cosine": {"diffuse": "uniform"},
    }
    for label, variant in wrong.items():
        rejected = 0
        for name, model in MODELS.items():
            truth = chi_over_half_space(model, CONCRETE, ROUGH_M)
            mistake = chi_over_half_space(model, CONCRETE, ROUGH_M, **variant)
            if abs(mistake / truth - 1.0) < 3.0 * CHI_TOLERANCE[name]:
                # Some laws are blind to some mistakes. Isotropic illumination
                # cannot see the lobe shape at all, because the cosine mean and
                # the uniform mean of a constant are the same number. That is a
                # fact about the law, so it is skipped rather than asserted away.
                continue
            assert abs(rough.susceptibility[name] / mistake - 1.0) > 2.0 * CHI_TOLERANCE[name], f"{label}, {name}"
            rejected += 1
        assert rejected >= 1, f"no illumination law can see {label}"

    # The rooftop law sees all four, which is why it is the one to reach for.
    truth = chi_over_half_space(ROOFTOP, CONCRETE, ROUGH_M)
    for variant in wrong.values():
        mistake = chi_over_half_space(ROOFTOP, CONCRETE, ROUGH_M, **variant)
        assert abs(mistake / truth - 1.0) > 0.05


def test_russian_roulette_from_the_first_bounce_does_not_move_the_closed_form() -> None:
    """Roulette has to be unbiased, and the only honest check is an exact target.

    In production the roulette is off, pinned by
    ``roulette_start = DEFAULT_MAX_BOUNCES + 1``, so it can never fire at the
    shipped budget and no production run exercises it. Here it is moved to
    bounce 1, where it kills between a third and a half of the
    rays before they can deposit and inflates the survivors by up to twenty
    times. The estimator has one job under that treatment: return the same
    number. If the division by the survival probability were dropped, or applied
    before the survival draw rather than to the survivors, or clipped
    differently on the two sides, ``chi`` would move by tens of percent.
    """
    target = {name: chi_over_half_space(model, CONCRETE, ROUGH_M) for name, model in MODELS.items()}
    plain = trace_plane(CONCRETE, ROUGH_M, roulette_start=99)
    rouletted = trace_plane(CONCRETE, ROUGH_M, roulette_start=1)

    # It really did fire, otherwise the test asserts nothing.
    assert rouletted.escaped_fraction < 0.75 * plain.escaped_fraction
    assert plain.escaped_fraction == pytest.approx(1.0, abs=1.0e-9)

    for name in MODELS:
        assert rouletted.susceptibility[name] == pytest.approx(target[name], rel=2.0 * CHI_TOLERANCE[name]), name
        assert plain.susceptibility[name] == pytest.approx(target[name], rel=CHI_TOLERANCE[name]), name


def test_the_specular_and_diffuse_branch_probabilities_carry_no_weight() -> None:
    """One lobe is sampled per bounce, with no compensating throughput factor.

    That is correct only because the branch is chosen with probability equal to
    its own energy share, so the ``1/p`` of the estimator and the ``p`` of the
    split cancel exactly. The consequence is testable without any reference to
    the closed form: over a lossless plane the total escaping power cannot
    depend on the roughness, at any roughness, because a perfect reflector
    conserves power whichever lobe it chooses. If the branch probability and the
    branch weight failed to cancel, this would drift monotonically with the
    roughness.
    """
    totals = []
    for rough in (0.0, 0.001, 0.004, 0.010, 0.100, 1.0):
        result = trace_plane(PEC_PERMITTIVITY, rough, rays=200_000)
        totals.append(result.susceptibility["isotropic"])
    totals = np.array(totals)
    assert np.all(np.abs(totals - 1.0) < 2.0e-3), totals
    # Not merely bounded but flat: the spread across a factor of a thousand in
    # roughness is smaller than the Monte Carlo error of any single entry.
    assert totals.max() - totals.min() < 1.0e-3


def test_the_quadrature_constant_does_not_depend_on_the_cell_count() -> None:
    """`4 pi / N` is used as every Voronoi cell's area. It is not exactly that.

    A Fibonacci sphere is equal area in the ``z`` marginal but its Voronoi cells
    differ from the nominal ``4 pi / N`` by a few percent, and ``chi`` sums per
    cell means against the nominal area. The resulting bias is real. What this
    test asserts is its size: sweeping the cell count over a factor of sixty
    four moves ``chi`` by less than the tolerance, so the binning is not what
    sets the accuracy of a published number. A per cell weight that was wrong by
    a constant factor, or an ``N``, would fail this immediately.
    """
    target = {name: chi_over_half_space(model, CONCRETE, ROUGH_M) for name, model in MODELS.items()}
    measured = {name: [] for name in MODELS}
    for cells in (64, 256, 1024, 2048):
        result = trace_plane(CONCRETE, ROUGH_M, rays=400_000, local_cells=cells, seed=31)
        for name in MODELS:
            measured[name].append(result.susceptibility[name] / target[name] - 1.0)
    for name in MODELS:
        residual = np.array(measured[name])
        assert np.all(np.abs(residual) < 2.0 * CHI_TOLERANCE[name]), (name, residual)
        assert np.ptp(residual) < 2.0 * CHI_TOLERANCE[name], (name, residual)


def test_the_truncated_throughput_share_is_a_ratio_to_the_escaped_power() -> None:
    """Pin what the convergence diagnostic actually divides by, because it matters.

    ``truncated_throughput_share`` is quoted in the bounce convergence table as
    a share, which reads as a fraction of the power budget. It is not. The
    denominator is the throughput that escaped, so the quantity is truncated
    over escaped and it is unbounded above.

    Truncating a plane at zero bounces makes the two readings differ by exactly
    a factor of two and pins which one the code computes: half the rays escape
    upward untouched and half are still travelling when the loop ends, so
    truncated over escaped is 1 while truncated over the whole budget is 1/2.

    The published figure of 0.567 at one bounce therefore means the discarded
    power was 57 percent of the retained power, that is 36 percent of the
    budget, not 57 percent of it. At the four bounce operating point the two
    readings differ in the fifth decimal and nothing turns on it, but the
    definition should be stated rather than inferred.
    """
    config = TraceConfig(rays=200_000, local_cells=128, max_bounces=0, seed=3)
    tracer = SbrTracer(PlaneGeometry(0.0), None, np.array([PEC_PERMITTIVITY]), np.array([0.0]), config)
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), {"isotropic": ISOTROPIC})

    share = result.diagnostics["truncated_throughput_share"]
    truncated = result.diagnostics["truncated_rays"]
    escaped = result.escaped_fraction * config.rays
    assert share == pytest.approx(truncated / escaped, rel=1.0e-12)
    assert share == pytest.approx(1.0, abs=0.02)
    assert truncated / config.rays == pytest.approx(0.5, abs=0.01)


def voronoi_cell_means(grid: np.ndarray, values, samples: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Mean of a direction function over each Voronoi cell of ``grid``.

    The nearest cell search is written out here rather than imported, so this
    stays an oracle for the tracer's binning instead of a restatement of it.
    """
    rng = np.random.default_rng(seed)
    total = np.zeros(grid.shape[0])
    count = np.zeros(grid.shape[0])
    for _ in range(samples // 250_000):
        z = rng.uniform(-1.0, 1.0, 250_000)
        phi = rng.uniform(0.0, 2.0 * np.pi, 250_000)
        radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
        block = np.stack([radius * np.cos(phi), radius * np.sin(phi), z], axis=1)
        cell = np.argmax(block @ grid.T, axis=1)
        np.add.at(total, cell, values(block))
        np.add.at(count, cell, 1.0)
    return total / np.maximum(count, 1.0), count


def test_the_local_spectrum_matches_the_closed_form_cell_by_cell() -> None:
    """`rho` is what AEGIS consumes, and nothing has ever checked it per cell.

    Over a smooth plane under isotropic illumination every departure direction
    has an analytic fate. A ray leaving upward escapes untouched, so it deposits
    ``1/4pi``. A ray leaving downward reflects once and deposits
    ``R(|u_z|)/4pi``. So the exact per cell target is the mean of

        f(u) = 1 if u_z > 0 else R(|u_z|)

    over that cell's Voronoi region, divided by ``4 pi``.

    Comparing against ``f`` at the cell centre instead would be wrong by up to
    seven percent near grazing, and in one direction: ``R`` is convex there, so
    a cell mean sits above its centre value. That is Jensen's inequality, not a
    defect, and integrating over the cell removes it. Doing so also lets the
    cells that straddle the horizon be tested rather than excluded, which are
    exactly the cells a binning offset would corrupt first.
    """
    result = trace_plane(CONCRETE, 0.0, rays=2_000_000, local_cells=256, seed=41)
    grid = result.local_grid
    rho = result.rho["isotropic"]

    def fate(directions: np.ndarray) -> np.ndarray:
        return np.where(directions[:, 2] > 0.0, 1.0, fresnel_unpolarised(-directions[:, 2], CONCRETE))

    target, count = voronoi_cell_means(grid, fate, 4_000_000, seed=5)
    assert count.min() > 8_000
    ratio = rho * 4.0 * np.pi / target
    assert np.max(np.abs(ratio - 1.0)) < 0.02, float(np.max(np.abs(ratio - 1.0)))
    assert abs(np.mean(ratio) - 1.0) < 0.002

    # Cells whose Voronoi region lies wholly above the horizon carry no variance
    # at all: every ray in them escapes untouched, so the cell mean is 1/4pi with
    # nothing to average. Any scatter there is binning, not Monte Carlo, so it is
    # held to roundoff. This is the assertion a horizon leak would break, and it
    # is not weakened by the Monte Carlo tolerance above.
    wholly_above = target == 1.0
    assert wholly_above.sum() > 80, int(wholly_above.sum())
    scaled = rho[wholly_above] * 4.0 * np.pi
    # Floating point accumulation over the few thousand rays per cell, and
    # nothing else. Eight orders below the Monte Carlo tolerance above, so this
    # is a statement about the binning rather than a restatement of it.
    assert np.ptp(scaled) < 1.0e-12, float(np.ptp(scaled))

    # They agree with each other exactly and with 1 only to 2e-11, and the
    # residual is not roundoff. It is the trapezoid error of the isotropic
    # model's own normalisation, whose exact value is 4 pi: two hundred thousand
    # abscissae over a half turn leave ``h**2/6`` behind. Naming it rather than
    # absorbing it into a tolerance is the point, since an unexplained constant
    # offset in rho is exactly what a lost quadrature factor would look like.
    offset = float(np.mean(scaled)) - 1.0
    assert offset == pytest.approx(4.0 * np.pi / ISOTROPIC.normalisation() - 1.0, rel=1.0e-6)
    assert 0.0 < offset < 1.0e-9

    # The integral of the spectrum reproduces the scalar the run publishes, which
    # is the link between what the body side is handed and the susceptibility
    # quoted beside it.
    assert float(np.sum(rho) * result.local_solid_angle) == pytest.approx(
        result.susceptibility["isotropic"], rel=1.0e-12
    )
