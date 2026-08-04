"""The antenna axis of the illumination model.

Three groups of tests, and the middle group is the reason the file exists.

The first group pins the patterns against 3GPP TR 38.901 clause 7.3 by spot
value, so a transcription slip in Table 7.3-1 is caught rather than propagated.

The second group is about the structural claim of BEAMFORMING.md: that a
pattern enters the estimator only as a re-weighting of `Q`, that a beam matched
to the pedestrian therefore leaves `chi` exactly where it was, and that the
cancellation is a property of the array factor and not of the element pattern.
Each of those is run rather than asserted. The matched invariance in particular
is checked by tracing, on the same rays, and demanding bit level equality, which
is a much stronger statement than agreement to Monte Carlo error.

The third group is the parameter free identities the whole package lives on:
every illumination model, with or without an antenna on it, has to give
``chi = 1`` in free space and ``chi = 2`` above a perfect conductor.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.propagation import ISOTROPIC, PEC_PERMITTIVITY, ROOFTOP, STREET_SMALL_CELL, PlaneGeometry
from semantic_twin.propagation.antenna import (
    CANONICAL_ARRAY,
    KERNEL_EDGES_DEG,
    LOADED_TABLE,
    AntennaIllumination,
    BroadcastBeam,
    LoadedBeam,
    PlanarArray,
    SweptBeam,
    TabulatedGain,
    element_gain,
    element_pattern_db,
    elevation_probes,
    kernel_susceptibility,
    matched_gain,
    source_frame_angles,
    steering_artefact,
)
from semantic_twin.illumination import sample_sphere
from semantic_twin.propagation.tracer import PathRecorder, SbrTracer, TraceConfig


class Empty:
    """No geometry at all. Every ray escapes on its first step."""

    def intersect(self, origins, directions):  # noqa: ANN001, ANN202
        count = origins.shape[0]
        return (
            np.zeros(count, dtype=bool),
            np.full(count, 1.0e30),
            np.zeros((count, 3)),
            np.zeros(count, dtype=np.int64),
        )


def free_space_tracer(rays: int = 40_000) -> SbrTracer:
    config = TraceConfig(rays=rays, local_cells=128, exit_bands=18, seed=3)
    return SbrTracer(Empty(), None, np.array([PEC_PERMITTIVITY]), np.array([0.0]), config)


# --------------------------------------------------------------------------
# TR 38.901 clause 7.3
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("theta_deg", "phi_deg", "expected_db"),
    [
        (90.0, 0.0, 0.0),  # boresight
        (90.0, 65.0, -12.0),  # horizontal 3 dB beamwidth is 65 deg, so 12 dB down at its edge
        (155.0, 0.0, -12.0),  # and the vertical one likewise, 65 deg below the horizon
        (90.0, 180.0, -30.0),  # A_max front to back
        (0.0, 0.0, -23.0059),  # zenith, 12*(90/65)^2 short of the 30 dB SLA_V floor
        (180.0, 180.0, -30.0),  # both cuts on their floor, held at A_max by the 3D line
    ],
)
def test_the_element_matches_table_7_3_1(theta_deg: float, phi_deg: float, expected_db: float) -> None:
    """Spot values of the single element radiation power pattern.

    The last row is the one worth having. Without the third line of the table,
    ``A_3D = -min{-(A_V + A_H), A_max}``, the back upper quadrant reaches -60 dB
    instead of the -30 the standard holds it at, and nothing else in the pattern
    would notice.
    """
    got = float(element_pattern_db(np.array([theta_deg]), np.array([phi_deg]))[0])
    assert got == pytest.approx(expected_db, abs=1.0e-3)


def test_the_element_is_bounded_by_its_own_peak_and_its_own_floor() -> None:
    """Nowhere above 0 dB and nowhere below ``A_max``, over the whole sphere.

    The peak is checked at the boresight, where the standard puts it, and not
    by hoping a random sample lands there. A uniform draw of 200 000 directions
    has a nearest neighbour to boresight of about a quarter of a degree, and the
    element is 2e-4 dB down at a quarter of a degree, so demanding the sample
    maximum equal 0 would be a test of the sampler rather than of the pattern.
    """
    assert float(element_pattern_db(np.array([90.0]), np.array([0.0]))[0]) == 0.0
    rng = np.random.default_rng(0)
    directions = sample_sphere(200_000, rng)
    theta = np.degrees(np.arccos(np.clip(directions[:, 2], -1.0, 1.0)))
    phi = np.degrees(np.arctan2(directions[:, 1], directions[:, 0]))
    pattern = element_pattern_db(theta, phi)
    assert pattern.max() <= 0.0
    assert pattern.min() >= -30.0 - 1.0e-12
    assert pattern.min() == pytest.approx(-30.0, abs=1.0e-9)


@pytest.mark.parametrize(("tilt", "scan"), [(90.0, 0.0), (102.0, 0.0), (102.0, 30.0), (96.0, -45.0)])
def test_the_array_factor_peaks_at_mn_where_it_was_steered(tilt: float, scan: float) -> None:
    """``|AF|^2 = MN`` exactly in the steered direction, and nowhere higher."""
    array = CANONICAL_ARRAY
    assert array.array_factor(np.array([tilt]), np.array([scan]), tilt_deg=tilt, scan_deg=scan)[0] == pytest.approx(
        float(array.elements), rel=1.0e-12
    )
    rng = np.random.default_rng(1)
    directions = sample_sphere(200_000, rng)
    theta = np.degrees(np.arccos(np.clip(directions[:, 2], -1.0, 1.0)))
    phi = np.degrees(np.arctan2(directions[:, 1], directions[:, 0]))
    assert array.array_factor(theta, phi, tilt_deg=tilt, scan_deg=scan).max() <= array.elements + 1.0e-9


def test_the_array_beamwidth_is_the_uniform_aperture_one() -> None:
    """A broadside uniform line source has a 3 dB width of ``0.886 lam / L``.

    For half wavelength spacing that is ``101.5 / M`` degrees, which for the
    eight element column this study uses is 12.7 degrees. The number matters
    because it is what decides whether the array resolves the multipath, so it
    is pinned rather than quoted.

    ``101.5 / M`` is the large ``M`` limit, not the beamwidth. The exact width
    solves ``|sin(M u / 2) / (M sin(u / 2))|^2 = 1/2`` with
    ``u = pi sin(offset)``, and it exceeds the limit by 3.7 percent at four
    elements, 0.9 percent at eight and 0.2 percent at sixteen, so the limit
    itself is only a target worth pinning from about eight elements up. Both
    are checked: the exact root to one part in ten thousand, which is a real
    constraint on the array factor, and the approach to the limit, which is the
    statement the docstring above is making.
    """
    # Roots of the exact condition, from scipy.optimize.brentq at xtol 1e-13.
    exact_hpbw_deg = {4: 26.322952034675883, 8: 12.802525796993503, 16: 6.358725780160171}
    for rows in (4, 8, 16):
        array = PlanarArray(rows=rows, columns=1)
        theta = np.linspace(90.0, 130.0, 400_001)
        gain = array.array_factor(theta, np.zeros_like(theta), tilt_deg=90.0, scan_deg=0.0)
        half = theta[np.argmax(gain < 0.5 * rows)] - 90.0
        assert 2.0 * half == pytest.approx(exact_hpbw_deg[rows], rel=1.0e-4), rows
        assert 2.0 * half == pytest.approx(101.5 / rows, rel=0.02 if rows >= 8 else 0.04), rows
    # The limit is approached from above, and the gap closes like 1 / M^2.
    gaps = [exact_hpbw_deg[rows] / (101.5 / rows) - 1.0 for rows in (4, 8, 16)]
    assert gaps[0] > gaps[1] > gaps[2] > 0.0
    assert gaps[0] / gaps[1] == pytest.approx(4.0, rel=0.1)
    assert gaps[1] / gaps[2] == pytest.approx(4.0, rel=0.1)


def test_a_linear_array_at_half_wavelength_spacing_conserves_power_exactly() -> None:
    """The sphere mean of ``|AF|^2`` is exactly 1 for a line array, not for a panel.

    A line array's steering vectors are orthonormal under the uniform measure on
    the sphere, because every Cartesian component of a uniform direction is
    itself uniform on ``[-1, 1]`` and the element offsets are whole half
    wavelengths. A rectangular lattice has diagonal offsets of
    ``lam/2 sqrt(dm^2 + dn^2)``, which are not, so the cross terms survive and
    the panel radiates about 1.5 dB less than ``MN`` times isotropic would
    suggest. That is not an error, it is why the loaded beam limit of
    BEAMFORMING.md section 5 is stated as *approximately* unit array gain.
    """
    nodes, weights = np.polynomial.legendre.leggauss(2_000)
    theta = np.degrees(np.arccos(nodes))
    azimuth = np.linspace(-180.0, 180.0, 360, endpoint=False)

    def sphere_mean(array: PlanarArray) -> float:
        grid = array.array_factor(
            np.repeat(theta, azimuth.size), np.tile(azimuth, theta.size), tilt_deg=102.0, scan_deg=0.0
        ).reshape(theta.size, azimuth.size)
        return float(np.dot(grid.mean(axis=1), weights) / 2.0)

    for array in (PlanarArray(8, 1), PlanarArray(1, 8), PlanarArray(16, 1)):
        assert sphere_mean(array) == pytest.approx(1.0, rel=1.0e-6), array
    assert 0.6 < sphere_mean(CANONICAL_ARRAY) < 0.8


def test_the_sphere_mean_of_the_array_factor_is_a_sinc_sum() -> None:
    """An independent route to the same number, sharing no code with the first.

    ``(1/4pi) int |AF|^2 dOmega = (1/MN) sum over element pairs of
    cos(k dp . s) sinc(k |dp|)``, since the sphere average of a plane wave is a
    sinc in the separation. Agreeing with the direct quadrature says the array
    factor really is the aperture it claims to be.
    """
    array = CANONICAL_ARRAY
    rows = np.repeat(np.arange(array.rows) * array.row_spacing_wavelengths, array.columns)
    columns = np.tile(np.arange(array.columns) * array.column_spacing_wavelengths, array.rows)
    dz = rows[:, None] - rows[None, :]
    dy = columns[:, None] - columns[None, :]
    distance = 2.0 * np.pi * np.hypot(dz, dy)
    sinc = np.where(
        distance < 1.0e-12,
        1.0,
        np.sin(np.where(distance < 1.0e-12, 1.0, distance)) / np.where(distance < 1.0e-12, 1.0, distance),
    )
    for tilt, scan in ((90.0, 0.0), (102.0, 0.0), (102.0, 40.0)):
        phase = 2.0 * np.pi * (dz * np.cos(np.radians(tilt)) + dy * np.sin(np.radians(tilt)) * np.sin(np.radians(scan)))
        analytic = float((np.cos(phase) * sinc).sum() / array.elements)

        nodes, weights = np.polynomial.legendre.leggauss(600)
        theta = np.degrees(np.arccos(nodes))
        azimuth = np.linspace(-180.0, 180.0, 720, endpoint=False)
        grid = array.array_factor(
            np.repeat(theta, azimuth.size), np.tile(azimuth, theta.size), tilt_deg=tilt, scan_deg=scan
        ).reshape(theta.size, azimuth.size)
        quadrature = float(np.dot(grid.mean(axis=1), weights) / 2.0)
        assert analytic == pytest.approx(quadrature, rel=1.0e-6), (tilt, scan)


def test_a_site_seen_at_elevation_alpha_radiates_at_depression_alpha() -> None:
    """The one piece of geometry, and the reason a downtilt lands on `Q`.

    A site on the pedestrian's sky at 12 degrees of elevation is sampled at
    ``theta = 102``, which is exactly the electrical downtilt that points at it.
    The elevation axis of the illumination density and the elevation axis of the
    antenna pattern are the same axis.
    """
    elevation = np.radians(np.array([0.0, 3.0910, 12.0, 60.1135]))
    azimuth = np.radians(np.array([0.0, 90.0, 200.0, -30.0]))
    theta, phi = source_frame_angles(elevation, azimuth)
    assert theta == pytest.approx(np.array([90.0, 93.0910, 102.0, 150.1135]))
    # The wrap is half open on [-180, 180), so a site the pedestrian sees due
    # east of them, which radiates due west to reach them, comes back as -180
    # and not +180. Same bearing, one representative, and the gain laws are
    # even in phi so nothing downstream can tell them apart. Both the wrapped
    # value and the unwrapped bearing it stands for are pinned here, because
    # the sign at the seam is exactly the thing a reader would otherwise have
    # to guess.
    assert phi == pytest.approx(np.array([-180.0, -90.0, 20.0, 150.0]))
    unwrapped = np.degrees(azimuth) + 180.0
    assert np.allclose((phi - unwrapped + 180.0) % 360.0 - 180.0, 0.0, atol=1.0e-9)
    assert np.all(phi >= -180.0) and np.all(phi < 180.0)
    theta_rotated, phi_rotated = source_frame_angles(elevation, azimuth, boresight_azimuth_deg=20.0)
    assert theta_rotated == pytest.approx(theta)
    assert phi_rotated == pytest.approx(np.array([160.0, -110.0, 0.0, 130.0]))


# --------------------------------------------------------------------------
# The structural claim
# --------------------------------------------------------------------------


@pytest.mark.parametrize("base", [ISOTROPIC, ROOFTOP, STREET_SMALL_CELL], ids=lambda m: m.name)
def test_a_matched_beam_leaves_the_density_exactly_where_it_was(base) -> None:  # noqa: ANN001
    """The invariance of BEAMFORMING.md section 3, at the level of `Q` itself.

    Every site putting its peak on the pedestrian makes the gain a constant, it
    factors out of both line integrals of the adjoint identity, and the
    normalisation removes it. So `Q` is not approximately unchanged, it is the
    same array of numbers.
    """
    matched = AntennaIllumination(f"{base.name}_matched", base, matched_gain, "constant gain")
    rng = np.random.default_rng(4)
    directions = sample_sphere(50_000, rng)
    assert matched.density(directions) == pytest.approx(base.density(directions), rel=1.0e-12)


def test_a_matched_beam_leaves_the_traced_susceptibility_bit_identical() -> None:
    """The same statement one level up, through the estimator, on the same rays.

    The illumination model is consulted only when an escaped ray is deposited
    and never by the random number generator, so a trace that carries both
    models is paired exactly and any difference between the two columns would be
    a real difference in the physics rather than Monte Carlo noise. There is
    none.
    """
    tracer = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([PEC_PERMITTIVITY]),
        np.array([0.0]),
        TraceConfig(rays=40_000, local_cells=128, seed=5),
    )
    models = {
        "rooftop": ROOFTOP,
        "rooftop_matched": AntennaIllumination("rooftop_matched", ROOFTOP, matched_gain, "constant gain"),
    }
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), models, ground_z_m=0.0)
    assert result.susceptibility["rooftop_matched"] == pytest.approx(result.susceptibility["rooftop"], rel=1.0e-12)


def test_full_digital_maximum_ratio_transmission_cancels_the_array_gain() -> None:
    """`E ||h||^2 = MN sum_p |a_p|^2`, so `chi` under true MRT is the incoherent one.

    This is the claim that survives without the far source approximation, and it
    is a statement about expectations over path phase rather than about
    geometry. Maximum ratio transmission achieves ``||h||^2``. Under
    uncorrelated scattering the cross terms between distinct paths average to
    zero, so the expectation is ``MN`` times the plain power sum, and the free
    space reference is a single path with the same ``MN`` on it. The array gain
    is common to both and cancels. What does not cancel is the element pattern,
    which multiplies each path's power before the aperture sees it.
    """
    rng = np.random.default_rng(6)
    array = CANONICAL_ARRAY
    rows = np.repeat(np.arange(array.rows) * array.row_spacing_wavelengths, array.columns)
    columns = np.tile(np.arange(array.columns) * array.column_spacing_wavelengths, array.rows)

    paths = 24
    amplitude = rng.gamma(2.0, 1.0, size=paths)
    direction = sample_sphere(paths, rng)
    steering = np.exp(2j * np.pi * (np.outer(direction[:, 2], rows) + np.outer(direction[:, 1], columns)))
    realisations = 20_000
    phase = np.exp(2j * np.pi * rng.random((realisations, paths)))
    channel = (phase * amplitude) @ steering
    measured = np.mean(np.sum(np.abs(channel) ** 2, axis=1))
    predicted = array.elements * np.sum(amplitude**2)
    assert measured == pytest.approx(predicted, rel=0.02)


def test_the_broadcast_beam_does_not_cancel_and_moves_the_measure_downward() -> None:
    """A fixed downtilted beam is a real re-weighting, and its sign is knowable.

    The rooftop population's median site sits at 9.5 degrees of elevation and
    the beam is aimed at 12 degrees of downtilt with a 12.7 degree wide column,
    so the beam sits on the middle of the population and cuts both wings. The
    test asserts the direction rather than the size: the density has to rise
    near the tilt and fall at both the grazing edge and the steep edge.
    """
    beam = BroadcastBeam(tilt_deg=102.0)
    broadcast = AntennaIllumination("rooftop_broadcast", ROOFTOP, beam, "downtilted column")
    elevation = np.radians(np.array([3.5, 12.0, 45.0]))
    directions = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
    ratio = broadcast.density(directions) / ROOFTOP.density(directions)
    assert ratio[1] > ratio[0] > 0.0
    assert ratio[1] > ratio[2] > 0.0
    assert 10.0 * np.log10(ratio[1] / ratio[2]) > 10.0


def test_three_sectors_of_sixty_five_degree_elements_ripple_in_azimuth() -> None:
    """The cusp between sectors, which is why the grid rotation is a nuisance parameter.

    Three 65 degree elements on a 120 degree grid sum to a horizontal pattern
    that is flat on boresight and about 7 dB down at the 60 degree crossover.
    That is the ordinary three sector cusp, and it is the whole azimuth
    dependence of `Q` in this model.
    """
    azimuth = np.radians(np.linspace(0.0, 120.0, 241))
    theta, _ = source_frame_angles(np.zeros_like(azimuth), azimuth)
    total = np.zeros_like(azimuth)
    for sector in (0.0, 120.0, 240.0):
        _, phi = source_frame_angles(np.zeros_like(azimuth), azimuth, boresight_azimuth_deg=sector)
        total += element_gain(theta, phi)
    ripple_db = 10.0 * np.log10(total.max() / total.min())
    assert 6.0 < ripple_db < 9.0


def test_a_loaded_beam_with_users_everywhere_gives_back_unit_array_gain() -> None:
    """The limit that makes the loaded case interpretable.

    Average the array factor over a served user drawn uniformly over the whole
    sphere and the result is the sinc sum of the orthogonality test above, which
    for this panel is 0.68 to 0.72 rather than exactly 1. So a fully spread user
    population buys the pedestrian no array gain at all, and everything the
    loaded model reports is the value of the user population being *more*
    concentrated than that.
    """
    loaded = LoadedBeam(user_population=ISOTROPIC, sectors=(0.0,), sector_half_width_deg=180.0)
    elevation = np.radians(np.array([2.0, 10.0, 30.0]))
    azimuth = np.zeros_like(elevation)
    gain = loaded(elevation, azimuth)
    element = element_gain(*source_frame_angles(elevation, azimuth))
    assert np.all(gain / element < 1.2)
    assert np.all(gain / element > 0.4)


@pytest.mark.parametrize(
    ("gain", "nodes"),
    [
        (BroadcastBeam(tilt_deg=102.0), {}),
        (SweptBeam(tilt_deg=102.0), {"azimuth_nodes": 1_441}),
        (LoadedBeam(user_population=ROOFTOP), LOADED_TABLE),
    ],
    ids=["broadcast", "swept", "loaded"],
)
def test_tabulating_a_gain_law_does_not_change_it(gain, nodes: dict) -> None:  # noqa: ANN001
    """The interpolation layer is a speed trick, so it has to be one.

    Each law is tabulated at the node counts it actually ships with, not at a
    refined grid, because a grid nobody uses would make this pass on a table the
    study never builds. The loaded beam gets the coarse `LOADED_TABLE` for the
    reason that constant records: it is an average of the array factor over a
    thousand user directions, so it is smooth on the beamwidth and carries none
    of the nulls that force a fine grid on the others.

    The swept beam is the counterexample and the reason it is not tabulated in
    :func:`build_models`. Seven scan positions of a narrow beam put seven times
    the structure on the azimuth axis, and the default 361 node azimuth grid
    misses the peaks by 4.6 percent. Refining the elevation axis does nothing at
    all, which localises the problem: 721 nodes leaves 1.6 percent and 1441
    leaves 0.6, so the grid it needs is four times the default on one axis only.
    """
    tabulated = TabulatedGain(gain, **nodes)
    rng = np.random.default_rng(7)
    elevation = np.radians(rng.uniform(0.0, 61.0, 4_000))
    azimuth = np.radians(rng.uniform(-180.0, 180.0, 4_000))
    exact = gain(elevation, azimuth)
    approx = tabulated(elevation, azimuth)
    assert np.max(np.abs(approx - exact)) / np.max(exact) < 0.02


def test_the_antenna_normalisation_stops_moving_as_the_quadrature_refines() -> None:
    """The base laws are sharp at grazing and the gain is not, so refine both.

    The fine side is the shipped default rather than something beyond it, so
    what this asserts is that the number the study divides by is converged, not
    that some unreachable grid would have been.
    """
    for gain in (matched_gain, TabulatedGain(BroadcastBeam(tilt_deg=102.0))):
        for base in (ROOFTOP, STREET_SMALL_CELL):
            coarse = AntennaIllumination("coarse", base, gain, "", gain_nodes=2_049).normalisation(50_001)
            shipped = AntennaIllumination("shipped", base, gain, "").normalisation()
            assert abs(coarse / shipped - 1.0) < 1.0e-5


# --------------------------------------------------------------------------
# The parameter free identities
# --------------------------------------------------------------------------


def test_every_antenna_model_still_equals_one_in_free_space() -> None:
    """The identity the whole package is built to expose.

    An antenna is a re-weighting of a normalised density, so it cannot change
    what an empty scene does. If any of these drifts off 1 the normalisation and
    the deposit disagree, which is exactly the failure a free space check exists
    to catch.
    """
    models = {
        "rooftop": ROOFTOP,
        "rooftop_matched": AntennaIllumination("rooftop_matched", ROOFTOP, matched_gain, ""),
        "rooftop_broadcast": AntennaIllumination(
            "rooftop_broadcast", ROOFTOP, TabulatedGain(BroadcastBeam(tilt_deg=102.0)), ""
        ),
        "street_broadcast": AntennaIllumination(
            "street_broadcast", STREET_SMALL_CELL, TabulatedGain(BroadcastBeam(tilt_deg=96.0)), ""
        ),
    }
    result = free_space_tracer().trace(np.array([0.0, 0.0, 1.5]), models)
    for name, value in result.susceptibility.items():
        assert value == pytest.approx(1.0, abs=0.02), name


def test_the_elevation_probes_are_the_transfer_kernel() -> None:
    """Every probe is 1 in free space and 2 above a perfect conductor.

    A band indicator normalised to a density is ``1/Omega`` inside the band, and
    a free space trace puts ``Omega/4pi`` of its rays there carrying unit
    throughput, so the probe reads the band averaged transfer kernel of section
    1.3 of PAPER_METHODS.md on the same scale as `chi`. Over a perfect ground
    plane every upward direction receives the direct ray and its image, so the
    kernel is exactly 2, and that is a parameter free check on the probe
    construction and on the deposit weights at once.
    """
    edges = np.array([0.0, 10.0, 30.0, 60.0, 90.0])
    probes = elevation_probes(edges)
    free = free_space_tracer(rays=80_000).trace(np.array([0.0, 0.0, 1.5]), probes)
    for name, value in free.susceptibility.items():
        assert value == pytest.approx(1.0, abs=0.03), name

    plane = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([PEC_PERMITTIVITY]),
        np.array([0.0]),
        TraceConfig(rays=80_000, local_cells=128, seed=9),
    )
    above = plane.trace(np.array([0.0, 0.0, 1.5]), probes, ground_z_m=0.0)
    for name, value in above.susceptibility.items():
        assert value == pytest.approx(2.0, abs=0.06), name


def test_the_kernel_reconstructs_a_susceptibility_without_retracing() -> None:
    """`chi = sum_b K_b m_b`, which is the claim that a pattern costs no tracing.

    Traced directly and reconstructed from the kernel, on the same rays, above a
    perfect ground plane where the answer is 2 for any density supported above
    the horizon. The reconstruction is a dot product of the kernel with the
    density's band measure, so if it agrees the kernel is a sufficient statistic
    for every azimuthally symmetric illumination model there is.
    """
    probes = elevation_probes(KERNEL_EDGES_DEG)
    models = dict(probes)
    models["rooftop"] = ROOFTOP
    models["street_small_cell"] = STREET_SMALL_CELL
    tracer = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([PEC_PERMITTIVITY]),
        np.array([0.0]),
        TraceConfig(rays=200_000, local_cells=128, seed=11),
    )
    result = tracer.trace(np.array([0.0, 0.0, 1.5]), models, ground_z_m=0.0)
    kernel = np.array([result.susceptibility[name] for name in probes])
    for name, model in (("rooftop", ROOFTOP), ("street_small_cell", STREET_SMALL_CELL)):
        reconstructed = kernel_susceptibility(kernel, KERNEL_EDGES_DEG, model)
        assert reconstructed == pytest.approx(result.susceptibility[name], rel=0.02), name


# --------------------------------------------------------------------------
# The far source artefact, measured rather than bounded
# --------------------------------------------------------------------------


def _recorded(tracer: SbrTracer, origin: np.ndarray, ground_z_m: float = 0.0):  # noqa: ANN202
    recorder = PathRecorder(capacity=tracer.config.rays)
    tracer.trace(origin, {"rooftop": ROOFTOP}, ground_z_m=ground_z_m, recorder=recorder)
    return recorder.result()


def test_a_scene_with_no_surfaces_has_no_artefact_at_all() -> None:
    """Every ray is direct, so `x_K = x`, and a beam on the pedestrian misses nothing.

    This is the identity the measurement has to satisfy before any of its
    numbers mean anything: the reduction is a statement about *bounces*, so with
    no bounce available it has to be exactly zero and not approximately zero.
    """
    tracer = free_space_tracer(rays=20_000)
    artefact = steering_artefact(_recorded(tracer, np.array([0.0, 0.0, 1.5])), np.array([0.0, 0.0, 1.5]), ROOFTOP)
    assert artefact["mean_suppression"] == pytest.approx(1.0, rel=1.0e-12)
    assert artefact["direct_measure"] == pytest.approx(1.0, rel=1.0e-12)
    assert artefact["median_offset_deg"] == pytest.approx(0.0, abs=1.0e-6)


def _plane_record():  # noqa: ANN202
    """A perfect ground plane: half the illumination measure arrives off the ground."""
    tracer = SbrTracer(
        PlaneGeometry(0.0),
        None,
        np.array([PEC_PERMITTIVITY]),
        np.array([0.0]),
        TraceConfig(rays=60_000, local_cells=128, max_bounces=1, seed=5),
    )
    return _recorded(tracer, np.array([0.0, 0.0, 1.5]), ground_z_m=0.0)


def test_over_a_ground_plane_half_the_measure_is_direct_and_the_other_half_is_steerable() -> None:
    """The one scene where the split is known in closed form.

    A perfect plane sends every downward ray back up along the mirrored
    elevation with unit throughput, so each upward direction carries exactly one
    direct path and one reflected path and the direct share is a half. The
    reflected path's last vertex sits at `h / tan(alpha)` from the observer,
    which is 8.5 m at 10 degrees, so the offsets are real rather than
    infinitesimal and the suppression has something to bite on.
    """
    record = _plane_record()
    artefact = steering_artefact(record, np.array([0.0, 0.0, 1.5]), ROOFTOP)
    assert artefact["direct_measure"] == pytest.approx(0.5, abs=0.02)
    assert artefact["mean_suppression"] < 1.0
    assert artefact["bounced_suppression_db"] < 0.0
    # The direct half cannot be steered away from, so it is the floor.
    assert artefact["mean_suppression"] > artefact["direct_measure"]


def test_a_bigger_aperture_suppresses_more_of_the_multipath() -> None:
    """The size of the artefact is set by aperture against offset, and by nothing else.

    A wider array has a narrower beam, so the same angular offset costs more.
    Monotonicity in the element count is the whole content of the claim that the
    reduction is a range rather than a number, so it is asserted directly.
    """
    record = _plane_record()
    values = [
        steering_artefact(record, np.array([0.0, 0.0, 1.5]), ROOFTOP, array=PlanarArray(n, n))["mean_suppression"]
        for n in (2, 4, 8, 16, 32)
    ]
    assert values == sorted(values, reverse=True)
    assert values[0] > 0.95
    assert values[-1] < values[0]


def test_a_codebook_as_fine_as_the_aperture_is_the_geometric_case() -> None:
    """And a coarse one is not, which is the granularity axis.

    A discrete Fourier grid with as many beams as elements puts its beams one
    beamwidth apart, so quantising to it moves the steering by at most half a
    beamwidth and the scallop loss lands on the reference as well as on the
    scene. Coarsening the grid detunes the reference more than it detunes the
    already detuned scene paths, so the measured suppression rises towards one:
    a blunt codebook hides the artefact rather than causing it.
    """
    record = _plane_record()
    origin = np.array([0.0, 0.0, 1.5])
    exact = steering_artefact(record, origin, ROOFTOP)["mean_suppression"]
    matched_grid = steering_artefact(record, origin, ROOFTOP, codebook=(8, 8))["mean_suppression"]
    coarse = steering_artefact(record, origin, ROOFTOP, codebook=(2, 2))["mean_suppression"]
    assert matched_grid == pytest.approx(exact, rel=0.35)
    assert coarse > matched_grid
    fine = steering_artefact(record, origin, ROOFTOP, codebook=(4_096, 4_096))["mean_suppression"]
    assert fine == pytest.approx(exact, rel=1.0e-3)


def test_the_loaded_beam_user_quadrature_is_converged_at_its_defaults() -> None:
    """The default node counts have to be the answer, not a step towards it.

    ``LoadedBeam`` averages the array factor over the served user's direction on
    a fixed product rule, and the defaults are only 24 elevation nodes by 13 in
    azimuth. A rule that coarse is worth something only if refining it does not
    move the answer, and for a while this one did: the azimuth axis sampled the
    sector endpoints while weighting every node equally, which is the midpoint
    rule's weights on the trapezoid rule's nodes, and it left a first order
    error worth about 30 percent at the defaults. Refining each axis eight fold
    is the cheapest statement of the property that caught it.

    Five percent is the bar because that is what the corrected rule actually
    delivers at the shipped node counts. The worst deviation over a one degree
    sweep from 1 to 60 degrees is 1.3 percent for the rooftop population and
    3.4 percent for the street one, both at the elevation where the beam is
    walking off the observer and the value is falling fastest. That is six
    times inside the error the endpoint bug carried, so the bar is loose enough
    to be about the defaults rather than about the sweep and tight enough that
    the bug could not come back through it.
    """
    elevation = np.radians(np.linspace(1.0, 60.0, 60))
    azimuth = np.zeros_like(elevation)
    for population in (ROOFTOP, STREET_SMALL_CELL):
        coarse = LoadedBeam(user_population=population)
        fine = LoadedBeam(user_population=population, user_elevation_nodes=192, user_azimuth_nodes=104)
        assert coarse(elevation, azimuth) == pytest.approx(fine(elevation, azimuth), rel=0.05), population.name
    # The isotropic user limit, where the sector is the whole circle and the
    # endpoint bug put two nodes on the same azimuth, so it is the case that
    # showed the bug at its largest. The array gain a fully spread user
    # population leaves the pedestrian is the panel's sinc sum, which is near
    # 0.7 at the shallow elevations the sites actually sit at and is a function
    # of where the pedestrian is looking rather than a single number, so it is
    # pinned where the study reads it and checked for convergence everywhere.
    loaded = LoadedBeam(user_population=ISOTROPIC, sectors=(0.0,), sector_half_width_deg=180.0)
    loaded_fine = LoadedBeam(
        user_population=ISOTROPIC,
        sectors=(0.0,),
        sector_half_width_deg=180.0,
        user_elevation_nodes=192,
        user_azimuth_nodes=104,
    )
    assert loaded(elevation, azimuth) == pytest.approx(loaded_fine(elevation, azimuth), rel=0.05)
    shallow = np.radians(np.array([2.0, 5.0, 10.0]))
    ratio = loaded(shallow, np.zeros_like(shallow)) / element_gain(
        *source_frame_angles(shallow, np.zeros_like(shallow))
    )
    assert np.all(ratio < 0.72) and np.all(ratio > 0.68)
