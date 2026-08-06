import math

import numpy as np
import pytest

from semantic_twin.materials.masonry import BRICK_FORMATS, RECESSED_JOINT, STACK_BOND, JointGeometry, MasonryWall
from semantic_twin.materials.masonry import Layer, convolution_matrix, harmonic_indices, solve
from semantic_twin.materials.masonry.rcwa import (
    _normal_flux,
    _numerical_mode_branches,
    _pq_matrices,
)


def fresnel(permittivity: complex, theta_deg: float, polarisation: str) -> float:
    theta = math.radians(theta_deg)
    cos_i = math.cos(theta)
    root = np.sqrt(complex(permittivity) - math.sin(theta) ** 2)
    if root.real < 0.0:
        root = -root
    if polarisation == "te":
        reflection = (cos_i - root) / (cos_i + root)
    else:
        reflection = (permittivity * cos_i - root) / (permittivity * cos_i + root)
    return float(abs(reflection) ** 2)


@pytest.mark.parametrize("permittivity", [3.91, 5.24, complex(3.91, 0.24)])
@pytest.mark.parametrize("theta_deg", [0.0, 30.0, 60.0, 85.0])
@pytest.mark.parametrize("polarisation", ["te", "tm"])
def test_homogeneous_half_space_reproduces_fresnel(permittivity, theta_deg, polarisation) -> None:
    solution = solve(
        [Layer(permittivity=1.0), Layer(permittivity=permittivity)],
        period_x_m=0.225,
        period_y_m=0.075,
        frequency_hz=28e9,
        theta_deg=theta_deg,
        phi_deg=23.0,
        polarisation=polarisation,
        harmonics=(2, 2),
    )
    assert solution.specular_efficiency == pytest.approx(fresnel(permittivity, theta_deg, polarisation), abs=1e-10)
    assert solution.diffuse_efficiency == pytest.approx(0.0, abs=1e-14)


def test_flat_wall_gives_pure_specular_even_with_many_harmonics_retained() -> None:
    solution = solve(
        [Layer(permittivity=1.0), Layer(permittivity=np.full((64, 64), 3.91 + 0j))],
        period_x_m=0.225,
        period_y_m=0.075,
        frequency_hz=28e9,
        theta_deg=40.0,
        polarisation="tm",
        harmonics=(4, 3),
    )
    assert solution.specular_efficiency == pytest.approx(fresnel(3.91, 40.0, "tm"), abs=1e-9)
    assert solution.diffuse_efficiency == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("theta_deg", [0.0, 45.0, 70.0])
@pytest.mark.parametrize("polarisation", ["te", "tm"])
def test_dielectric_slab_matches_the_analytic_two_interface_result(theta_deg, polarisation) -> None:
    permittivity, thickness, frequency = 3.91, 0.012, 28e9
    k0 = 2.0 * math.pi * frequency / 299792458.0
    theta = math.radians(theta_deg)
    kz1 = k0 * math.cos(theta)
    kz2 = k0 * np.sqrt(complex(permittivity) - math.sin(theta) ** 2)
    if polarisation == "te":
        r12 = (kz1 - kz2) / (kz1 + kz2)
    else:
        r12 = (permittivity * kz1 - kz2) / (permittivity * kz1 + kz2)
    phase = np.exp(2j * kz2 * thickness)
    expected = abs((r12 - r12 * phase) / (1.0 - r12 * r12 * phase)) ** 2
    solution = solve(
        [Layer(1.0), Layer(permittivity, thickness_m=thickness), Layer(1.0)],
        period_x_m=0.225,
        period_y_m=0.075,
        frequency_hz=frequency,
        theta_deg=theta_deg,
        polarisation=polarisation,
        harmonics=(1, 1),
    )
    assert solution.specular_efficiency == pytest.approx(float(expected), abs=1e-9)
    assert solution.total_reflectance + solution.total_transmittance == pytest.approx(1.0, abs=1e-9)


def test_a_lossless_patterned_grating_conserves_energy() -> None:
    # A real relief pattern, a lossless dielectric, and a homogeneous substrate,
    # so every watt has to reappear as a reflected or transmitted order.
    period_x, period_y = 0.030, 0.030
    grid = np.ones((48, 48), dtype=complex)
    grid[:, :20] = 4.0
    solution = solve(
        [Layer(1.0), Layer(grid, thickness_m=0.004), Layer(2.0)],
        period_x_m=period_x,
        period_y_m=period_y,
        frequency_hz=28e9,
        theta_deg=25.0,
        phi_deg=15.0,
        polarisation="te",
        harmonics=(6, 6),
    )
    assert solution.diffuse_efficiency > 1e-4
    assert solution.total_reflectance + solution.total_transmittance == pytest.approx(1.0, abs=2e-3)


def test_lossless_propagating_modes_ignore_cross_dispatch_eigenvalue_residuals() -> None:
    """Tiny residuals on either side of the branch cut select the same modes.

    The two imaginary perturbations bracket those measured from Haswell and
    SkylakeX on the passive grating witness. Both transverse field modes must
    carry power towards ``+z`` after selection.
    """
    kx = np.array([0.2])
    ky = np.array([0.0])
    eps = 4.0 * np.eye(1)
    p_matrix, q_matrix = _pq_matrices(eps, np.eye(1) / 4.0, kx, ky)
    omega_squared = p_matrix @ q_matrix
    eigenvalues = np.array([-3.96 + 4.1e-12j, -3.96 - 3.8e-12j])

    v_matrix, roots = _numerical_mode_branches(
        omega_squared,
        eigenvalues,
        np.eye(2),
        q_matrix,
    )

    assert np.all(roots.real == 0.0)
    assert np.all(roots.imag < 0.0)
    assert np.all(_normal_flux(np.eye(2), v_matrix) > 0.0)


@pytest.mark.parametrize("kx_value", [0.2, 3.0])
@pytest.mark.parametrize("loss", [0.0, 0.2])
def test_numerical_modes_are_outgoing_or_decaying(kx_value: float, loss: float) -> None:
    """TE and TM modes use power flow when propagating and decay otherwise."""
    permittivity = complex(4.0, loss)
    kx = np.array([kx_value])
    ky = np.array([0.0])
    eps = permittivity * np.eye(1)
    p_matrix, q_matrix = _pq_matrices(eps, np.eye(1) / permittivity, kx, ky)
    omega_squared = p_matrix @ q_matrix
    eigenvalues, w_matrix = np.linalg.eig(omega_squared)

    v_matrix, roots = _numerical_mode_branches(
        omega_squared,
        eigenvalues,
        w_matrix,
        q_matrix,
    )
    flux = _normal_flux(w_matrix, v_matrix)

    if kx_value < permittivity.real**0.5:
        assert np.all(flux > 0.0)
        assert np.all(roots.imag < 0.0)
    else:
        assert np.all(roots.real > 0.0)
    if loss > 0.0:
        assert np.all(roots.real > 0.0)


@pytest.mark.parametrize("polarisation", ["te", "tm"])
@pytest.mark.parametrize("loss", [0.0, 0.2])
def test_a_subwavelength_patterned_slab_is_passive_and_reciprocal(polarisation: str, loss: float) -> None:
    frequency = 15.0e9
    wavelength = 299_792_458.0 / frequency
    x = (np.arange(1024) + 0.5) / 1024
    profile = np.where(np.abs(x - 0.5) < 0.25, 6.0 + 1j * loss, 1.5 + 1j * loss)[None, :]
    common = dict(
        layers=[Layer(1.0), Layer(profile, thickness_m=0.003), Layer(2.0)],
        period_x_m=wavelength / 20.0,
        period_y_m=wavelength / 20.0,
        frequency_hz=frequency,
        polarisation=polarisation,
        harmonics=(16, 0),
    )

    reverse = solve(theta_deg=-17.0, **common)
    forward = solve(theta_deg=17.0, **common)

    assert forward.total_reflectance == pytest.approx(reverse.total_reflectance, abs=1e-9)
    assert forward.total_transmittance == pytest.approx(reverse.total_transmittance, abs=1e-9)
    assert 0.0 <= forward.total_reflectance <= 1.0
    assert 0.0 <= forward.total_transmittance <= 1.0
    if loss == 0.0:
        assert forward.total_reflectance + forward.total_transmittance == pytest.approx(1.0, abs=1e-9)
    else:
        assert 0.0 < forward.absorbed < 1.0


def test_a_uniform_substrate_is_recognised_and_a_patterned_one_is_not() -> None:
    # With mortar and brick given the same permittivity the substrate is
    # uniform, so transmission orders are plane waves and the power budget
    # closes. Give the mortar its own permittivity and the substrate becomes a
    # laterally patterned half space whose modes are not plane waves, and the
    # transmitted efficiency is reported as undefined rather than guessed.
    common = dict(
        brick=BRICK_FORMATS["waalformaat"],
        joint=RECESSED_JOINT,
        bond=STACK_BOND,
        brick_permittivity=3.06 + 0j,
    )
    uniform = MasonryWall(**common, mortar_permittivity=3.06 + 0j)
    contrasted = MasonryWall(**common, mortar_permittivity=3.41 + 0j)
    solved = dict(
        period_x_m=uniform.cell_x_m,
        period_y_m=uniform.cell_y_m,
        frequency_hz=10e9,
        theta_deg=20.0,
        polarisation="te",
        harmonics=(6, 4),
    )
    plain = solve(uniform.rcwa_layers(96, 96), **solved)
    patterned = solve(contrasted.rcwa_layers(96, 96), **solved)
    assert plain.total_reflectance + plain.total_transmittance == pytest.approx(1.0, abs=5e-3)
    assert plain.absorbed == pytest.approx(0.0, abs=5e-3)
    assert np.all(np.isnan(patterned.transmission_efficiency))
    assert 0.0 < patterned.total_reflectance < 1.0


def test_diffraction_orders_leave_at_the_grating_equation_angles() -> None:
    wall = MasonryWall(BRICK_FORMATS["standard_metric"], RECESSED_JOINT, STACK_BOND)
    frequency, theta_deg = 15e9, 30.0
    solution = solve(
        wall.rcwa_layers(128, 96),
        period_x_m=wall.cell_x_m,
        period_y_m=wall.cell_y_m,
        frequency_hz=frequency,
        theta_deg=theta_deg,
        polarisation="te",
        harmonics=(6, 4),
    )
    lam = 299792458.0 / frequency
    in_plane = solution.propagating & (solution.n == 0)
    sines = np.sin(math.radians(theta_deg)) + solution.m[in_plane] * lam / wall.cell_x_m
    k0 = 2.0 * math.pi / lam
    assert np.allclose(solution.kx[in_plane] / k0, sines, atol=1e-12)


def test_a_recessed_joint_moves_power_out_of_the_specular_direction() -> None:
    wall = MasonryWall(BRICK_FORMATS["standard_metric"], RECESSED_JOINT, STACK_BOND)
    flush = MasonryWall(
        BRICK_FORMATS["standard_metric"],
        JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=0.0),
        STACK_BOND,
    )
    common = dict(
        period_x_m=wall.cell_x_m,
        period_y_m=wall.cell_y_m,
        frequency_hz=15e9,
        theta_deg=20.0,
        polarisation="te",
        harmonics=(6, 4),
    )
    recessed = solve(wall.rcwa_layers(128, 96), **common)
    plain = solve(flush.rcwa_layers(128, 96), **common)
    assert plain.diffuse_efficiency < 1e-12
    assert recessed.diffuse_efficiency > 0.05 * recessed.total_reflectance
    assert recessed.specular_efficiency < plain.specular_efficiency


def test_convolution_matrix_of_a_constant_map_is_the_scaled_identity() -> None:
    m_index = np.array([-1, 0, 1])
    n_index = np.array([0, 0, 0])
    matrix = convolution_matrix(np.full((16, 16), 2.5 + 0j), m_index, n_index)
    assert np.allclose(matrix, 2.5 * np.eye(3))


def test_convolution_matrix_refuses_an_undersampled_map() -> None:
    m_index = np.arange(-8, 9)
    n_index = np.zeros_like(m_index)
    with pytest.raises(ValueError):
        convolution_matrix(np.ones((8, 8), dtype=complex), m_index, n_index)


def test_malformed_layer_stacks_are_refused() -> None:
    common = dict(period_x_m=0.2, period_y_m=0.1, frequency_hz=28e9, theta_deg=0.0)
    with pytest.raises(ValueError):
        solve([Layer(1.0)], **common)
    with pytest.raises(ValueError):
        solve([Layer(1.0), Layer(3.91), Layer(2.0)], harmonics=(1, 1), **common)
    with pytest.raises(ValueError):
        solve([Layer(1.0, thickness_m=0.01), Layer(2.0)], harmonics=(1, 1), **common)
    with pytest.raises(ValueError):
        solve([Layer(np.ones((8, 8), dtype=complex)), Layer(2.0)], harmonics=(1, 1), **common)


def test_elliptic_truncation_agrees_with_rectangular_and_costs_less() -> None:
    # The box corners are the most deeply evanescent orders in the set. Dropping
    # them must not move the answer, and the agreement has to improve as the
    # truncation grows, which is what distinguishes a valid economy from a
    # coincidence at one size.
    wall = MasonryWall(BRICK_FORMATS["standard_metric"], RECESSED_JOINT, STACK_BOND)
    layers = wall.rcwa_layers(384, 256)
    common = dict(
        period_x_m=wall.cell_x_m,
        period_y_m=wall.cell_y_m,
        frequency_hz=15e9,
        theta_deg=45.0,
        polarisation="te",
    )
    errors = []
    for harmonics in ((8, 5), (12, 8)):
        box = solve(layers, harmonics=harmonics, truncation="rectangular", **common)
        ellipse = solve(layers, harmonics=harmonics, truncation="elliptic", **common)
        assert ellipse.m.size < 0.8 * box.m.size
        errors.append(abs(ellipse.specular_efficiency / box.specular_efficiency - 1.0))
    assert errors[0] < 0.02
    assert errors[1] < errors[0]


def test_harmonic_index_sets_are_well_formed() -> None:
    for truncation in ("elliptic", "rectangular"):
        m_index, n_index = harmonic_indices(6, 4, truncation=truncation)
        assert m_index.size == n_index.size
        assert np.count_nonzero((m_index == 0) & (n_index == 0)) == 1
        assert np.abs(m_index).max() == 6
        assert np.abs(n_index).max() == 4
        # The set is symmetric under inversion, which the Floquet expansion needs.
        pairs = {(int(m), int(n)) for m, n in zip(m_index, n_index, strict=True)}
        assert all((-m, -n) in pairs for m, n in pairs)
    with pytest.raises(ValueError):
        harmonic_indices(4, 4, truncation="hexagonal")
