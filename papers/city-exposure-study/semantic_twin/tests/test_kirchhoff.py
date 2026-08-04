import math

import numpy as np
import pytest

from semantic_twin.materials.masonry import (
    DisorderModel,
    bistatic_map,
    fresnel_reflection,
    hemisphere_grid,
    equivalent_rms_height_m,
    gaussian_equivalence_limit_m,
    incoherent_power_fraction,
    kirchhoff_orders,
    order_angular_width_deg,
    phase_screen_incidence_limit_deg,
    phase_screen_recess_limit_m,
    specular_retention,
)
from semantic_twin.materials.masonry import (
    BRICK_FORMATS,
    JOINT_PROFILES,
    RECESSED_JOINT,
    RUNNING_BOND,
    STACK_BOND,
    STANDARD_JOINT,
    JointGeometry,
    MasonryWall,
)
from semantic_twin.materials.roughness import specular_power_fraction

BRICK = BRICK_FORMATS["standard_metric"]
HAIRLINE = JointGeometry(bed_m=2e-5, perp_m=2e-5, recess_m=0.0, profile="none")


def flat_wall() -> MasonryWall:
    return MasonryWall(BRICK, STANDARD_JOINT, RUNNING_BOND, brick_permittivity=3.91 + 0j, mortar_permittivity=3.91 + 0j)


@pytest.mark.parametrize("theta_deg", [0.0, 45.0, 75.0])
@pytest.mark.parametrize("polarisation", ["te", "tm"])
def test_a_wall_with_no_relief_and_no_contrast_is_purely_specular(theta_deg, polarisation) -> None:
    solution = kirchhoff_orders(
        flat_wall(), frequency_hz=28e9, theta_deg=theta_deg, polarisation=polarisation, harmonics=(6, 6)
    )
    expected = abs(fresnel_reflection(3.91 + 0j, theta_deg, polarisation)) ** 2
    assert solution.specular_efficiency == pytest.approx(expected, abs=1e-12)
    assert solution.coherent_diffuse == pytest.approx(0.0, abs=1e-20)
    assert solution.incoherent_fraction == 0.0


def test_fresnel_helper_matches_the_normal_incidence_closed_form() -> None:
    for permittivity in (3.91, 5.24, 7.07):
        expected = ((1.0 - math.sqrt(permittivity)) / (1.0 + math.sqrt(permittivity))) ** 2
        assert abs(fresnel_reflection(permittivity, 0.0, "te")) ** 2 == pytest.approx(expected)
        assert abs(fresnel_reflection(permittivity, 0.0, "tm")) ** 2 == pytest.approx(expected)


def test_a_lossy_wall_reflects_less_than_a_lossless_one_never_more() -> None:
    for theta in (0.0, 40.0, 80.0):
        lossless = abs(fresnel_reflection(3.91 + 0.0j, theta, "te")) ** 2
        lossy = abs(fresnel_reflection(3.91 + 0.6j, theta, "te")) ** 2
        assert lossy > lossless
        assert lossy < 1.0


@pytest.mark.parametrize("sigma_m", [0.0005, 0.001, 0.002])
@pytest.mark.parametrize("theta_deg", [0.0, 60.0])
def test_piston_disorder_reproduces_the_ament_factor_when_the_joints_vanish(sigma_m, theta_deg) -> None:
    # This is the load bearing analytic limit of the whole module. Shrink the
    # joint grid to nothing and the derived unit-to-unit result must collapse
    # onto the Gaussian rough-surface factor the literature fits.
    wall = MasonryWall(BRICK, HAIRLINE, RUNNING_BOND, brick_permittivity=3.91 + 0j, mortar_permittivity=3.91 + 0j)
    solution = kirchhoff_orders(
        wall,
        frequency_hz=28e9,
        theta_deg=theta_deg,
        polarisation="te",
        harmonics=(4, 4),
        disorder=DisorderModel(piston_sigma_m=sigma_m),
    )
    reference = abs(fresnel_reflection(3.91 + 0j, theta_deg, "te")) ** 2
    ament = float(specular_power_fraction(sigma_m, math.cos(math.radians(theta_deg)), 28e9))
    assert solution.specular_efficiency / reference == pytest.approx(ament, rel=0.02)


def test_the_mortar_grid_holds_specular_power_that_the_ament_factor_gives_away() -> None:
    # A real joint grid never moves, so a wall keeps more specular power than an
    # equally scattered homogeneous surface would. This is a prediction, not a
    # correction: the gap is the joint area fraction.
    wall = flat_wall()
    disorder = DisorderModel(piston_sigma_m=0.002)
    solution = kirchhoff_orders(
        wall, frequency_hz=28e9, theta_deg=0.0, polarisation="te", harmonics=(4, 4), disorder=disorder
    )
    reference = abs(fresnel_reflection(3.91 + 0j, 0.0, "te")) ** 2
    ament = float(specular_power_fraction(0.002, 1.0, 28e9))
    ratio = solution.specular_efficiency / reference
    assert ratio > ament
    mortar = wall.joint_area_fraction
    predicted = ((1.0 - mortar) * math.sqrt(ament) + mortar) ** 2
    assert ratio == pytest.approx(predicted, rel=0.02)


def test_lateral_disorder_leaves_the_specular_order_alone_and_kills_the_high_orders() -> None:
    wall = MasonryWall(BRICK, RECESSED_JOINT, RUNNING_BOND)
    ordered = kirchhoff_orders(wall, frequency_hz=28e9, theta_deg=20.0, harmonics=(20, 12))
    jittered = kirchhoff_orders(
        wall,
        frequency_hz=28e9,
        theta_deg=20.0,
        harmonics=(20, 12),
        disorder=DisorderModel(lateral_x_sigma_m=0.002, lateral_y_sigma_m=0.001),
    )
    assert jittered.specular_efficiency == pytest.approx(ordered.specular_efficiency, rel=1e-9)
    low = jittered.efficiency[jittered.order_index(2, 0)] / ordered.efficiency[ordered.order_index(2, 0)]
    high = jittered.efficiency[jittered.order_index(10, 0)] / ordered.efficiency[ordered.order_index(10, 0)]
    assert high < low < 1.0


def test_disorder_never_increases_the_coherent_comb() -> None:
    wall = MasonryWall(BRICK, RECESSED_JOINT, RUNNING_BOND)
    solution = kirchhoff_orders(
        wall,
        frequency_hz=28e9,
        theta_deg=35.0,
        harmonics=(16, 10),
        disorder=DisorderModel(piston_sigma_m=0.0015, lateral_x_sigma_m=0.002),
    )
    assert solution.total_coherent <= solution.ordered_efficiency.sum() + 1e-12
    assert solution.incoherent_fraction > 0.0


def test_the_power_budget_closes_against_the_flat_wall_reflectance() -> None:
    # Physical optics does not conserve energy, and the size of the deficit is a
    # reported quantity rather than a nuisance. It is worst where the round trip
    # through the joint recess is near half a wave, because that is where the
    # brick and mortar returns are in antiphase and the phase screen throws the
    # difference into directions beyond the horizon that it cannot represent.
    wall = MasonryWall(BRICK, RECESSED_JOINT, RUNNING_BOND)
    for theta in (0.0, 30.0, 60.0, 75.0):
        # The retained harmonics have to cover every propagating order, which at
        # grazing means the full (1 + sin theta) span on the long cell axis.
        solution = kirchhoff_orders(
            wall,
            frequency_hz=28e9,
            theta_deg=theta,
            harmonics=(44, 16),
            disorder=DisorderModel(piston_sigma_m=0.001),
        )
        budget = solution.total_coherent + solution.incoherent_fraction
        reference = abs(fresnel_reflection(3.91 + 0j, theta, "te")) ** 2
        assert 0.75 < budget / reference < 1.03


def test_the_physical_optics_deficit_peaks_at_the_antiphase_recess() -> None:
    lam = 299792458.0 / 28e9
    reference = abs(fresnel_reflection(3.91 + 0j, 0.0, "te")) ** 2
    deficits = {}
    for recess in (0.25 * lam, 0.5 * lam):
        wall = MasonryWall(BRICK, JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=recess), RUNNING_BOND)
        solution = kirchhoff_orders(wall, frequency_hz=28e9, theta_deg=0.0, harmonics=(44, 16))
        deficits[recess] = abs(1.0 - solution.total_coherent / reference)
    # A quarter wave recess is the round trip half wave, the antiphase case.
    assert deficits[0.25 * lam] > deficits[0.5 * lam]


def test_a_flush_joint_with_no_dielectric_contrast_scatters_nothing() -> None:
    wall = MasonryWall(BRICK, STANDARD_JOINT, RUNNING_BOND, brick_permittivity=3.91 + 0j, mortar_permittivity=3.91 + 0j)
    solution = kirchhoff_orders(wall, frequency_hz=28e9, theta_deg=30.0, harmonics=(10, 6))
    assert solution.coherent_diffuse < 1e-20


def test_dielectric_contrast_alone_scatters_even_with_a_flush_joint() -> None:
    wall = MasonryWall(BRICK, STANDARD_JOINT, RUNNING_BOND, brick_permittivity=3.91 + 0j, mortar_permittivity=6.0 + 0j)
    solution = kirchhoff_orders(wall, frequency_hz=28e9, theta_deg=30.0, harmonics=(10, 6))
    assert solution.coherent_diffuse > 1e-4 * solution.specular_efficiency


def test_order_directions_match_the_grating_equation() -> None:
    wall = MasonryWall(BRICK, RECESSED_JOINT, STACK_BOND)
    solution = kirchhoff_orders(wall, frequency_hz=28e9, theta_deg=40.0, harmonics=(8, 4))
    lam = 299792458.0 / 28e9
    k0 = 2.0 * math.pi / lam
    in_plane = solution.n == 0
    expected = math.sin(math.radians(40.0)) + solution.m[in_plane] * lam / wall.cell_x_m
    assert np.allclose(solution.kx[in_plane] / k0, expected)


def test_incoherent_pedestal_is_zero_without_disorder_and_grows_with_it() -> None:
    wall = MasonryWall(BRICK, RECESSED_JOINT, RUNNING_BOND)
    common = dict(frequency_hz=28e9, theta_deg=30.0, polarisation="te")
    assert incoherent_power_fraction(wall, disorder=DisorderModel(), **common) == 0.0
    small = incoherent_power_fraction(wall, disorder=DisorderModel(piston_sigma_m=0.0005), samples=201, **common)
    large = incoherent_power_fraction(wall, disorder=DisorderModel(piston_sigma_m=0.002), samples=201, **common)
    assert 0.0 < small < large


def test_hemisphere_grid_covers_the_unit_disc() -> None:
    u, v, inside = hemisphere_grid(101)
    assert u.shape == (101, 101)
    assert inside.mean() == pytest.approx(math.pi / 4.0, abs=0.02)


def test_order_width_shrinks_with_patch_size_and_grows_at_grazing() -> None:
    narrow = order_angular_width_deg(1.0, 28e9, 0.0)
    wide = order_angular_width_deg(0.25, 28e9, 0.0)
    grazing = order_angular_width_deg(1.0, 28e9, 80.0)
    assert wide == pytest.approx(4.0 * narrow)
    assert grazing > narrow
    assert narrow == pytest.approx(math.degrees(299792458.0 / 28e9), rel=1e-9)


def test_bistatic_map_resolves_a_comb_and_a_coarse_receiver_washes_it_out() -> None:
    wall = MasonryWall(BRICK, RECESSED_JOINT, RUNNING_BOND)
    sharp = bistatic_map(wall, frequency_hz=28e9, theta_deg=30.0, patch_size_m=2.0, samples=201, harmonics=(24, 14))
    blunt = bistatic_map(
        wall,
        frequency_hz=28e9,
        theta_deg=30.0,
        patch_size_m=2.0,
        receiver_resolution_deg=20.0,
        samples=201,
        harmonics=(24, 14),
    )
    assert sharp.modulation_depth() > blunt.modulation_depth()
    assert blunt.resolution_deg > sharp.resolution_deg


def test_unknown_polarisation_is_refused() -> None:
    with pytest.raises(ValueError):
        fresnel_reflection(3.91, 30.0, "circular")


@pytest.mark.parametrize("frequency_hz", [7e9, 10e9, 15e9, 28e9, 40e9])
@pytest.mark.parametrize("theta_deg", [0.0, 30.0, 60.0, 75.0])
@pytest.mark.parametrize("recess_mm", [0.0, 2.0, 5.0, 10.0])
@pytest.mark.parametrize("piston_mm", [0.0, 1.97])
def test_closed_form_specular_retention_matches_the_full_solve(frequency_hz, theta_deg, recess_mm, piston_mm) -> None:
    # The two-level area average is not an approximation to the Kirchhoff solve,
    # it is the zero order of it, so the two must agree to machine precision.
    wall = MasonryWall(
        BRICK,
        JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=recess_mm / 1000.0),
        RUNNING_BOND,
        brick_permittivity=3.91 + 0j,
        mortar_permittivity=3.91 + 0j,
    )
    solution = kirchhoff_orders(
        wall,
        frequency_hz=frequency_hz,
        theta_deg=theta_deg,
        polarisation="te",
        harmonics=(4, 4),
        disorder=DisorderModel(piston_sigma_m=piston_mm / 1000.0),
    )
    reference = abs(fresnel_reflection(3.91 + 0j, theta_deg, "te")) ** 2
    closed_form = specular_retention(
        wall, frequency_hz=frequency_hz, theta_deg=theta_deg, piston_sigma_m=piston_mm / 1000.0
    )
    assert solution.specular_efficiency / reference == pytest.approx(closed_form, rel=1e-9)


def test_the_joint_recess_costs_nothing_at_a_whole_wave_round_trip() -> None:
    # The signature a Gaussian roughness model cannot produce. At a recess of
    # half a wavelength the round trip is a whole wave and the joint is
    # invisible in the specular direction, however deep it is.
    lam = 299792458.0 / 28e9
    invisible = MasonryWall(BRICK, JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=0.5 * lam), RUNNING_BOND)
    worst = MasonryWall(BRICK, JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=0.25 * lam), RUNNING_BOND)
    assert specular_retention(invisible, frequency_hz=28e9, theta_deg=0.0) == pytest.approx(1.0, abs=1e-9)
    mortar = worst.joint_area_fraction
    assert specular_retention(worst, frequency_hz=28e9, theta_deg=0.0) == pytest.approx((1.0 - 2.0 * mortar) ** 2)


def test_specular_retention_is_periodic_in_the_recess_not_monotone() -> None:
    lam = 299792458.0 / 28e9
    depths = np.linspace(0.0, lam, 41)
    retention = [
        specular_retention(
            MasonryWall(BRICK, JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=max(d, 1e-9)), RUNNING_BOND),
            frequency_hz=28e9,
            theta_deg=0.0,
        )
        for d in depths
    ]
    assert retention[-1] == pytest.approx(retention[0], abs=1e-9)
    assert min(retention) < 0.5 * max(retention)
    assert np.argmin(retention) not in (0, len(depths) - 1)


@pytest.mark.parametrize("recess_mm", [0.0, 1.0, 2.0])
@pytest.mark.parametrize("piston_mm", [0.0, 1.0, 1.97])
def test_equivalent_rms_height_reproduces_the_specular_loss_where_it_is_valid(recess_mm, piston_mm) -> None:
    if recess_mm == 0.0 and piston_mm == 0.0:
        pytest.skip("a wall with neither relief nor scatter has no equivalent height")
    frequency, theta = 10e9, 30.0
    wall = MasonryWall(
        BRICK,
        JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=max(recess_mm, 1e-6) / 1000.0),
        RUNNING_BOND,
    )
    assert recess_mm / 1000.0 <= gaussian_equivalence_limit_m(frequency, theta)
    sigma = equivalent_rms_height_m(wall, piston_sigma_m=piston_mm / 1000.0)
    exact = specular_retention(wall, frequency_hz=frequency, theta_deg=theta, piston_sigma_m=piston_mm / 1000.0)
    gaussian = float(specular_power_fraction(sigma, math.cos(math.radians(theta)), frequency))
    assert exact == pytest.approx(gaussian, rel=0.05)


def test_the_gaussian_equivalence_fails_for_a_deep_recess_at_fr2() -> None:
    frequency, theta = 28e9, 0.0
    recess = 0.005
    assert recess > gaussian_equivalence_limit_m(frequency, theta)
    wall = MasonryWall(BRICK, JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=recess), RUNNING_BOND)
    sigma = equivalent_rms_height_m(wall)
    exact = specular_retention(wall, frequency_hz=frequency, theta_deg=theta)
    gaussian = float(specular_power_fraction(sigma, 1.0, frequency))
    assert exact > 5.0 * gaussian


def test_disorder_coherence_factors_are_the_characteristic_functions_they_claim() -> None:
    lam = 299792458.0 / 28e9
    k0 = 2.0 * math.pi / lam
    disorder = DisorderModel(piston_sigma_m=0.002, lateral_x_sigma_m=0.003, lateral_y_sigma_m=0.001)
    psi = 2.0 * k0
    assert disorder.piston_coherence(np.array([0.0]))[0] == pytest.approx(1.0)
    assert disorder.piston_coherence(np.array([psi]))[0] == pytest.approx(math.exp(-((psi * 0.002) ** 2)))
    # At the specular direction the piston factor is exactly the Ament factor.
    assert disorder.piston_coherence(np.array([psi]))[0] == pytest.approx(
        float(specular_power_fraction(0.002, 1.0, 28e9))
    )
    assert disorder.lateral_coherence(np.array([0.0]), np.array([0.0]))[0] == pytest.approx(1.0)
    assert disorder.lateral_coherence(np.array([100.0]), np.array([50.0]))[0] == pytest.approx(
        math.exp(-((100.0 * 0.003) ** 2) - ((50.0 * 0.001) ** 2))
    )


def test_the_phase_screen_recess_limit_is_an_aspect_ratio_not_a_wavelength() -> None:
    # The rigorous ladder found the error tracking depth over width rather than
    # depth over wavelength, so the limit must not depend on frequency at all.
    assert phase_screen_recess_limit_m(0.010) == pytest.approx(0.005)
    assert phase_screen_recess_limit_m(0.012) == pytest.approx(0.006)
    with pytest.raises(ValueError):
        phase_screen_recess_limit_m(0.0)


def test_the_standard_joint_profiles_sit_inside_and_outside_the_checked_envelope() -> None:
    limit = phase_screen_recess_limit_m(0.010)
    assert JOINT_PROFILES["recessed"].recess_m <= limit
    assert JOINT_PROFILES["bucket_handle"].recess_m <= limit
    # The square-cut rake KNB infoblad 28 describes has depth equal to width, so
    # it is exactly the case the phase screen gets wrong.
    assert JOINT_PROFILES["recessed_deep"].recess_m > limit


def test_the_two_validity_limits_answer_different_questions() -> None:
    # One is set by the joint width and bounds the solver, the other is set by
    # the wavelength and bounds whether the answer can be summarised as an RMS
    # height. A wall can pass one and fail the other, and at 28 GHz it does.
    solver = phase_screen_recess_limit_m(0.010)
    summary = gaussian_equivalence_limit_m(28e9, 0.0)
    assert 0.005 <= solver
    assert 0.005 > summary


def test_the_incidence_limit_tightens_once_the_joint_is_resolvable() -> None:
    # At 10 GHz a 10 mm joint is a third of a wavelength and the wave does not
    # resolve the groove shadow, so the checked envelope runs to 60 degrees. At
    # 28 GHz the same joint is nearly a wavelength and the one grazing case
    # tested fails, so the envelope stops at 45.
    assert phase_screen_incidence_limit_deg(0.010, 10e9) == 60.0
    assert phase_screen_incidence_limit_deg(0.010, 28e9) == 45.0
    # Only those two grazing cases were run, so everything between them takes
    # the conservative branch rather than an invented threshold.
    assert phase_screen_incidence_limit_deg(0.010, 15e9) == 45.0
    assert phase_screen_incidence_limit_deg(0.006, 15e9) == 60.0
    with pytest.raises(ValueError):
        phase_screen_incidence_limit_deg(0.0, 28e9)
