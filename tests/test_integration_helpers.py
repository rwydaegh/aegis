"""Tests for DiffeRT and Sionna integration helper functions.

These test the pure-NumPy helper functions that convert ray tracer output
to AEGIS PropagationPaths. No DiffeRT or Sionna installation required.
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from aegis.constants import C_0
from aegis.integration.differt import (
    _arbitrary_perpendicular,
    _decompose_te_tm,
    _initial_polarisation_vector,
    _pad_and_concatenate,
    _reflect_at_surface,
    _track_polarisation,
    paths_from_differt,
)
from aegis.integration.sionna import (
    _convert_a_to_psi,
    _spherical_basis,
)
from aegis.paths import PropagationPaths
from aegis.result import DosimetryResult
from aegis.tissue.fresnel import n_complex


# ---------------------------------------------------------------------------
# _arbitrary_perpendicular
# ---------------------------------------------------------------------------
class TestArbitraryPerpendicular:
    def test_single_direction(self):
        k = np.array([[0.0, 0.0, 1.0]])
        e = _arbitrary_perpendicular(k)
        assert e.shape == (1, 3)
        assert abs(np.dot(e[0], k[0])) < 1e-12
        assert abs(np.linalg.norm(e[0]) - 1.0) < 1e-12

    def test_multiple_directions(self):
        k = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        e = _arbitrary_perpendicular(k)
        assert e.shape == (3, 3)
        for i in range(3):
            assert abs(np.dot(e[i], k[i])) < 1e-12, f"Not perpendicular for row {i}"
            assert abs(np.linalg.norm(e[i]) - 1.0) < 1e-12, f"Not unit for row {i}"

    def test_diagonal_direction(self):
        k = np.array([[1.0, 1.0, 1.0]]) / np.sqrt(3)
        e = _arbitrary_perpendicular(k)
        assert abs(np.dot(e[0], k[0])) < 1e-12
        assert abs(np.linalg.norm(e[0]) - 1.0) < 1e-12

    @given(arrays(np.float64, (10, 3), elements=st.floats(-1, 1, allow_nan=False, allow_infinity=False)))
    @settings(max_examples=20)
    def test_always_perpendicular(self, k_raw):
        norms = np.linalg.norm(k_raw, axis=1, keepdims=True)
        valid = norms[:, 0] > 1e-8
        if not np.any(valid):
            return
        k = k_raw[valid] / norms[valid]
        e = _arbitrary_perpendicular(k)
        dots = np.abs(np.sum(e * k, axis=1))
        np.testing.assert_allclose(dots, 0.0, atol=1e-10)
        np.testing.assert_allclose(np.linalg.norm(e, axis=1), 1.0, atol=1e-10)


# ---------------------------------------------------------------------------
# _initial_polarisation_vector
# ---------------------------------------------------------------------------
class TestInitialPolarisationVector:
    def test_vertical_z_propagation(self):
        """Vertical polarisation for z-directed propagation should be in xy plane."""
        k = np.array([0.0, 0.0, 1.0])
        e = _initial_polarisation_vector(k, "vertical")
        assert abs(np.linalg.norm(e) - 1.0) < 1e-12
        assert abs(np.dot(e, k)) < 1e-12
        # For pure z propagation, vertical projects z perp to k -> fallback
        # Just check it's perpendicular and unit

    def test_horizontal_z_propagation(self):
        k = np.array([0.0, 0.0, 1.0])
        e = _initial_polarisation_vector(k, "horizontal")
        assert abs(np.linalg.norm(e) - 1.0) < 1e-12
        # horizontal = cross(k, z_hat), but k IS z_hat, so fallback to [1,0,0]
        np.testing.assert_allclose(e, [1.0, 0.0, 0.0], atol=1e-12)

    def test_vertical_x_propagation(self):
        """Propagating along x: vertical pol should have z component."""
        k = np.array([1.0, 0.0, 0.0])
        e = _initial_polarisation_vector(k, "vertical")
        assert abs(np.linalg.norm(e) - 1.0) < 1e-12
        assert abs(np.dot(e, k)) < 1e-12
        # z projected perp to x -> should be [0, 0, 1]
        np.testing.assert_allclose(e, [0.0, 0.0, 1.0], atol=1e-12)

    def test_horizontal_x_propagation(self):
        """Propagating along x: horizontal pol = cross(x, z) = -y."""
        k = np.array([1.0, 0.0, 0.0])
        e = _initial_polarisation_vector(k, "horizontal")
        assert abs(np.linalg.norm(e) - 1.0) < 1e-12
        assert abs(np.dot(e, k)) < 1e-12
        # cross([1,0,0], [0,0,1]) = [0,-1,0], normalized -> [0,-1,0]
        np.testing.assert_allclose(np.abs(e), [0.0, 1.0, 0.0], atol=1e-12)

    def test_always_perpendicular_to_k(self):
        rng = np.random.default_rng(42)
        for _ in range(20):
            k = rng.standard_normal(3)
            k /= np.linalg.norm(k)
            for pol in ("vertical", "horizontal"):
                e = _initial_polarisation_vector(k, pol)
                assert abs(np.dot(e, k)) < 1e-10
                assert abs(np.linalg.norm(e) - 1.0) < 1e-10


# ---------------------------------------------------------------------------
# _decompose_te_tm
# ---------------------------------------------------------------------------
class TestDecomposeTE_TM:
    def test_normal_incidence(self):
        """At normal incidence, e_s and e_p should be perpendicular to k and each other."""
        k = np.array([0.0, 0.0, -1.0])
        normal = np.array([0.0, 0.0, 1.0])
        e_s, e_p = _decompose_te_tm(k, normal)
        assert abs(np.dot(e_s, k)) < 1e-10
        assert abs(np.dot(e_p, k)) < 1e-10
        assert abs(np.dot(e_s, e_p)) < 1e-10
        assert abs(np.linalg.norm(e_s) - 1.0) < 1e-10
        assert abs(np.linalg.norm(e_p) - 1.0) < 1e-10

    def test_oblique_incidence(self):
        k = np.array([1.0, 0.0, -1.0]) / np.sqrt(2)
        normal = np.array([0.0, 0.0, 1.0])
        e_s, e_p = _decompose_te_tm(k, normal)
        # e_s = cross(k, normal), should be along y
        assert abs(np.dot(e_s, k)) < 1e-10
        assert abs(np.linalg.norm(e_s) - 1.0) < 1e-10
        # e_p = cross(e_s, k)
        assert abs(np.dot(e_p, k)) < 1e-10
        assert abs(np.dot(e_s, e_p)) < 1e-10

    def test_forms_orthonormal_triad(self):
        rng = np.random.default_rng(123)
        for _ in range(20):
            k = rng.standard_normal(3)
            k /= np.linalg.norm(k)
            normal = rng.standard_normal(3)
            normal /= np.linalg.norm(normal)
            # Ensure normal faces the ray
            if np.dot(normal, -k) < 0:
                normal = -normal
            e_s, e_p = _decompose_te_tm(k, normal)
            assert abs(np.dot(e_s, k)) < 1e-9
            assert abs(np.dot(e_p, k)) < 1e-9


# ---------------------------------------------------------------------------
# _reflect_at_surface
# ---------------------------------------------------------------------------
class TestReflectAtSurface:
    def test_normal_incidence_reflection(self):
        """Normal incidence: reflected psi should be along same polarisation."""
        psi_in = np.array([1.0 + 0j, 0.0, 0.0])
        k_in = np.array([0.0, 0.0, -1.0])
        k_out = np.array([0.0, 0.0, 1.0])
        normal = np.array([0.0, 0.0, 1.0])
        n_t = 1.5 + 0j
        psi_out, k_ret = _reflect_at_surface(psi_in, k_in, k_out, normal, n_t)
        assert k_ret is k_out
        # At normal incidence r_s = r_p = (1 - n)/(1 + n)
        r_expected = (1 - n_t) / (1 + n_t)
        # psi should be scaled by r
        assert abs(np.linalg.norm(psi_out) - abs(r_expected)) < 1e-8

    def test_energy_bounded(self):
        """Reflected power should not exceed incident power (|r| <= 1)."""
        rng = np.random.default_rng(42)
        for _ in range(20):
            k_in = rng.standard_normal(3)
            k_in /= np.linalg.norm(k_in)
            normal = rng.standard_normal(3)
            normal /= np.linalg.norm(normal)
            if np.dot(normal, -k_in) < 0:
                normal = -normal
            k_out = k_in - 2 * np.dot(k_in, normal) * normal  # specular reflection
            psi_in = rng.standard_normal(3) + 1j * rng.standard_normal(3)
            n_t = complex(1 + rng.uniform(0, 5), rng.uniform(0, 2))
            psi_out, _ = _reflect_at_surface(psi_in, k_in, k_out, normal, n_t)
            assert np.linalg.norm(psi_out) <= np.linalg.norm(psi_in) + 1e-10

    def test_normal_flipping(self):
        """Should work regardless of normal orientation."""
        psi_in = np.array([1.0 + 0j, 0.0, 0.0])
        k_in = np.array([0.0, 0.0, -1.0])
        k_out = np.array([0.0, 0.0, 1.0])
        n_t = 1.5 + 0j

        psi_up, _ = _reflect_at_surface(psi_in, k_in, k_out, np.array([0, 0, 1.0]), n_t)
        psi_dn, _ = _reflect_at_surface(psi_in, k_in, k_out, np.array([0, 0, -1.0]), n_t)
        np.testing.assert_allclose(np.abs(psi_up), np.abs(psi_dn), atol=1e-10)


# ---------------------------------------------------------------------------
# _track_polarisation
# ---------------------------------------------------------------------------
class TestTrackPolarisation:
    def test_los_path(self):
        """LOS path (no reflections): psi = amplitude * e_pol."""
        # Path: TX at (0,0,0) -> RX at (10,0,0), no intermediate bounces
        path_verts = np.array([[[0, 0, 0], [10, 0, 0]]], dtype=np.float64)
        normals = np.zeros((1, 3))
        obj_indices = np.array([[-1, -1]], dtype=np.intp)
        amplitude = np.array([1.0])
        psi = _track_polarisation(path_verts, normals, obj_indices, None, [1.5 + 0j], amplitude, "vertical")
        assert psi.shape == (1, 3)
        assert abs(np.linalg.norm(psi[0]) - 1.0) < 1e-10
        # For x-propagation, vertical pol = z
        np.testing.assert_allclose(np.abs(psi[0]), [0, 0, 1], atol=1e-10)

    def test_single_reflection(self):
        """Single reflection: amplitude should decrease."""
        # TX(0,0,5) -> reflect at (5,0,0) on floor -> RX(10,0,5)
        path_verts = np.array([[[0, 0, 5], [5, 0, 0], [10, 0, 5]]], dtype=np.float64)
        normals = np.array([[0, 0, 1.0]])  # floor normal
        obj_indices = np.array([[-1, 0, -1]], dtype=np.intp)
        amplitude = np.array([1.0])
        psi = _track_polarisation(path_verts, normals, obj_indices, None, [1.5 + 0j], amplitude, "vertical")
        # After reflection, |psi| < 1 (Fresnel loss)
        assert np.linalg.norm(psi[0]) < 1.0
        assert np.linalg.norm(psi[0]) > 0.0

    def test_zero_amplitude(self):
        """Zero amplitude should give zero psi."""
        path_verts = np.array([[[0, 0, 0], [10, 0, 0]]], dtype=np.float64)
        normals = np.zeros((1, 3))
        obj_indices = np.array([[-1, -1]], dtype=np.intp)
        amplitude = np.array([0.0])
        psi = _track_polarisation(path_verts, normals, obj_indices, None, [1.5 + 0j], amplitude, "vertical")
        np.testing.assert_allclose(psi, 0.0, atol=1e-15)

    def test_degenerate_segment_skipped(self):
        """Zero-length first segment: path skipped, psi = 0."""
        path_verts = np.array([[[5, 0, 0], [5, 0, 0], [10, 0, 0]]], dtype=np.float64)
        normals = np.array([[0, 0, 1.0]])
        obj_indices = np.array([[-1, -1, -1]], dtype=np.intp)
        amplitude = np.array([1.0])
        psi = _track_polarisation(path_verts, normals, obj_indices, None, [1.5 + 0j], amplitude, "vertical")
        np.testing.assert_allclose(psi, 0.0, atol=1e-15)

    def test_multiple_materials(self):
        """Different materials at different reflections."""
        # TX -> reflect off material 0 -> reflect off material 1 -> RX
        path_verts = np.array([[[0, 0, 0], [5, 5, 0], [10, 0, 0], [15, 5, 0]]], dtype=np.float64)
        normals = np.array([[0, -1, 0], [0, 1, 0]], dtype=np.float64)
        obj_indices = np.array([[-1, 0, 1, -1]], dtype=np.intp)
        mat_indices = np.array([0, 1], dtype=np.intp)
        materials = [1.5 + 0.1j, 3.0 + 0.5j]
        amplitude = np.array([1.0])
        psi = _track_polarisation(path_verts, normals, obj_indices, mat_indices, materials, amplitude, "vertical")
        # Should produce nonzero but attenuated psi
        assert np.linalg.norm(psi[0]) > 0
        assert np.linalg.norm(psi[0]) < 1.0


# ---------------------------------------------------------------------------
# _pad_and_concatenate
# ---------------------------------------------------------------------------
class TestPadAndConcatenate:
    def test_same_length_paths(self):
        pv1 = np.random.randn(3, 4, 3)
        pv2 = np.random.randn(2, 4, 3)
        oi1 = np.random.randint(0, 10, (3, 4))
        oi2 = np.random.randint(0, 10, (2, 4))
        ei1 = np.array([0, 0, 1])
        ei2 = np.array([0, 1])

        pv, oi, ei = _pad_and_concatenate([pv1, pv2], [oi1, oi2], [ei1, ei2])
        assert pv.shape == (5, 4, 3)
        assert oi.shape == (5, 4)
        assert ei.shape == (5,)

    def test_different_length_paths(self):
        pv1 = np.random.randn(2, 3, 3)  # 3 vertices (1 bounce)
        pv2 = np.random.randn(2, 5, 3)  # 5 vertices (3 bounces)
        oi1 = np.zeros((2, 3), dtype=int)
        oi2 = np.zeros((2, 5), dtype=int)
        ei1 = np.array([0, 1])
        ei2 = np.array([0, 1])

        pv, oi, ei = _pad_and_concatenate([pv1, pv2], [oi1, oi2], [ei1, ei2])
        assert pv.shape == (4, 5, 3)  # padded to max length 5
        assert oi.shape == (4, 5)
        # Padded path vertices use edge padding (last vertex repeated)
        for row in range(3, 5):
            np.testing.assert_allclose(pv[0, row, :], pv[0, 2, :])
        # Padded object indices use -1
        assert np.all(oi[:2, 3:] == -1)


# ---------------------------------------------------------------------------
# paths_from_differt (end-to-end with synthetic data)
# ---------------------------------------------------------------------------
class TestPathsFromDiffert:
    def test_empty_paths(self):
        """Empty path array should return empty PropagationPaths."""
        verts = np.zeros((10, 3))
        normals = np.zeros((10, 3))
        path_verts = np.zeros((0, 3, 3))
        tx_pos = np.array([[0, 0, 10.0]])
        result = paths_from_differt(verts, normals, path_verts, tx_pos, freq_hz=28e9)
        assert result.n_paths == 0

    def test_single_los_path(self):
        """Single LOS path from TX at origin to body at (10, 0, 0)."""
        verts = np.zeros((1, 3))
        normals = np.array([[0, 0, 1.0]])
        # TX -> RX direct (2 vertices)
        path_verts = np.array([[[0, 0, 0], [10, 0, 0]]], dtype=np.float64)
        tx_pos = np.array([[0, 0, 0.0]])
        result = paths_from_differt(verts, normals, path_verts, tx_pos, freq_hz=28e9, tx_power_dbm=30.0)
        assert result.n_paths == 1
        # k_hat should point from TX to RX: [1, 0, 0]
        np.testing.assert_allclose(result.k_hat[0], [1, 0, 0], atol=1e-10)
        assert result.is_los[0]
        assert result.element_index[0] == 0
        # Power should be positive
        assert result.power[0] > 0

    def test_multiple_tx_elements(self):
        """Paths from 2 TX elements assigned by nearest position."""
        verts = np.zeros((1, 3))
        normals = np.array([[0, 0, 1.0]])
        path_verts = np.array(
            [
                [[0, 0, 0], [10, 0, 0]],
                [[0, 1, 0], [10, 0, 0]],
            ],
            dtype=np.float64,
        )
        tx_pos = np.array([[0, 0, 0], [0, 1, 0]], dtype=np.float64)
        result = paths_from_differt(verts, normals, path_verts, tx_pos, freq_hz=28e9)
        assert result.n_paths == 2
        assert result.element_index[0] == 0
        assert result.element_index[1] == 1

    def test_explicit_element_indices(self):
        """Explicit element_indices override nearest-TX assignment."""
        verts = np.zeros((1, 3))
        normals = np.array([[0, 0, 1.0]])
        path_verts = np.array([[[0, 0, 0], [10, 0, 0]]], dtype=np.float64)
        tx_pos = np.array([[0, 0, 0]], dtype=np.float64)
        elem_idx = np.array([5], dtype=np.intp)
        result = paths_from_differt(verts, normals, path_verts, tx_pos, freq_hz=28e9, element_indices=elem_idx)
        assert result.element_index[0] == 5

    def test_inverse_square_law(self):
        """Power should follow inverse square law with distance."""
        verts = np.zeros((1, 3))
        normals = np.array([[0, 0, 1.0]])
        # Path at distance 10
        path_10 = np.array([[[0, 0, 0], [10, 0, 0]]], dtype=np.float64)
        # Path at distance 20
        path_20 = np.array([[[0, 0, 0], [20, 0, 0]]], dtype=np.float64)
        tx_pos = np.array([[0, 0, 0.0]])

        r10 = paths_from_differt(verts, normals, path_10, tx_pos, freq_hz=28e9)
        r20 = paths_from_differt(verts, normals, path_20, tx_pos, freq_hz=28e9)

        # Power ~ 1/d^2, so ratio should be 4
        ratio = r10.power[0] / r20.power[0]
        np.testing.assert_allclose(ratio, 4.0, rtol=1e-10)

    def test_propagation_phase(self):
        """Coherent psi should include propagation phase exp(-j*k*d)."""
        verts = np.zeros((1, 3))
        normals = np.array([[0, 0, 1.0]])
        path_verts = np.array([[[0, 0, 0], [10, 0, 0]]], dtype=np.float64)
        tx_pos = np.array([[0, 0, 0.0]])
        freq = 28e9
        result = paths_from_differt(verts, normals, path_verts, tx_pos, freq_hz=freq)

        # Check that psi has the expected phase
        k0 = 2 * np.pi * freq / C_0
        d = 10.0
        expected_phase = -k0 * d
        actual_phase = np.angle(result.psi[0, 2])  # z-component (vertical pol for x-propagation)
        # Phase should match modulo 2*pi
        phase_diff = (actual_phase - expected_phase) % (2 * np.pi)
        assert phase_diff < 1e-6 or abs(phase_diff - 2 * np.pi) < 1e-6

    def test_with_polarisation_tracking(self):
        """Full polarisation tracking through reflections."""
        normals = np.array([[0, 0, 1.0]])  # floor
        verts = np.zeros((1, 3))
        # TX -> floor reflection -> RX
        path_verts = np.array([[[0, 0, 5], [5, 0, 0], [10, 0, 5]]], dtype=np.float64)
        tx_pos = np.array([[0, 0, 5.0]])
        obj_indices = np.array([[-1, 0, -1]], dtype=np.intp)
        mat_indices = None
        mat_n = [n_complex(5.31, 0.0326, 28e9)]

        result = paths_from_differt(
            verts,
            normals,
            path_verts,
            tx_pos,
            freq_hz=28e9,
            object_indices=obj_indices,
            material_indices=mat_indices,
            material_n_tilde=mat_n,
        )
        assert result.n_paths == 1
        assert result.power[0] > 0
        # With reflection, power should be less than LOS at same distance
        total_d = np.sqrt(50) + np.sqrt(50)
        los_path = np.array([[[0, 0, 5], [total_d, 0, 5]]], dtype=np.float64)
        los_result = paths_from_differt(verts, normals, los_path, tx_pos, freq_hz=28e9)
        assert result.power[0] < los_result.power[0]


# ---------------------------------------------------------------------------
# Sionna helpers: _spherical_basis
# ---------------------------------------------------------------------------
class TestSphericalBasis:
    def test_z_direction(self):
        """theta=0 (z-direction): e_theta should be in xy plane, e_phi should be in xy plane."""
        theta = np.array([0.0])
        phi = np.array([0.0])
        e_theta, e_phi = _spherical_basis(theta, phi)
        # At theta=0: e_theta = [cos(0)*cos(0), cos(0)*sin(0), -sin(0)] = [1, 0, 0]
        np.testing.assert_allclose(e_theta[0], [1, 0, 0], atol=1e-12)
        # e_phi = [-sin(0), cos(0), 0] = [0, 1, 0]
        np.testing.assert_allclose(e_phi[0], [0, 1, 0], atol=1e-12)

    def test_equator(self):
        """theta=pi/2, phi=0: e_theta should point downward (toward -z)."""
        theta = np.array([np.pi / 2])
        phi = np.array([0.0])
        e_theta, e_phi = _spherical_basis(theta, phi)
        # e_theta at equator, phi=0: [0, 0, -1]
        np.testing.assert_allclose(e_theta[0], [0, 0, -1], atol=1e-12)
        np.testing.assert_allclose(e_phi[0], [0, 1, 0], atol=1e-12)

    def test_orthogonality(self):
        """e_theta and e_phi should be orthogonal at all angles."""
        rng = np.random.default_rng(42)
        theta = rng.uniform(0.01, np.pi - 0.01, 50)
        phi = rng.uniform(0, 2 * np.pi, 50)
        e_theta, e_phi = _spherical_basis(theta, phi)
        dots = np.sum(e_theta * e_phi, axis=1)
        np.testing.assert_allclose(dots, 0.0, atol=1e-12)

    def test_unit_vectors(self):
        theta = np.linspace(0.1, np.pi - 0.1, 20)
        phi = np.linspace(0, 2 * np.pi, 20)
        e_theta, e_phi = _spherical_basis(theta, phi)
        np.testing.assert_allclose(np.linalg.norm(e_theta, axis=1), 1.0, atol=1e-12)
        np.testing.assert_allclose(np.linalg.norm(e_phi, axis=1), 1.0, atol=1e-12)

    def test_perpendicular_to_r_hat(self):
        """Both basis vectors should be perpendicular to the radial direction."""
        theta = np.array([np.pi / 4, np.pi / 3, np.pi / 2])
        phi = np.array([0.0, np.pi / 4, np.pi])
        e_theta, e_phi = _spherical_basis(theta, phi)
        # Radial unit vector
        r_hat = np.column_stack(
            [
                np.sin(theta) * np.cos(phi),
                np.sin(theta) * np.sin(phi),
                np.cos(theta),
            ]
        )
        dot_theta = np.sum(e_theta * r_hat, axis=1)
        dot_phi = np.sum(e_phi * r_hat, axis=1)
        np.testing.assert_allclose(dot_theta, 0.0, atol=1e-12)
        np.testing.assert_allclose(dot_phi, 0.0, atol=1e-12)


# ---------------------------------------------------------------------------
# Sionna helpers: _convert_a_to_psi
# ---------------------------------------------------------------------------
class TestConvertAToPsi:
    def test_zero_coefficients(self):
        """Zero channel coefficients -> zero psi."""
        psi = _convert_a_to_psi(
            np.zeros(3, dtype=complex),
            np.zeros(3, dtype=complex),
            np.array([0.1, 0.5, 1.0]),
            np.array([0.0, 1.0, 2.0]),
            28e9,
            1.0,
        )
        np.testing.assert_allclose(psi, 0.0, atol=1e-15)

    def test_scaling_with_power(self):
        """psi should scale as sqrt(P_tx)."""
        a_theta = np.array([1.0 + 0j])
        a_phi = np.array([0.0 + 0j])
        theta = np.array([np.pi / 2])
        phi = np.array([0.0])

        psi_1w = _convert_a_to_psi(a_theta, a_phi, theta, phi, 28e9, 1.0)
        psi_4w = _convert_a_to_psi(a_theta, a_phi, theta, phi, 28e9, 4.0)

        np.testing.assert_allclose(np.linalg.norm(psi_4w) / np.linalg.norm(psi_1w), 2.0, rtol=1e-10)

    def test_scaling_with_frequency(self):
        """psi should scale as freq (inversely with wavelength)."""
        a_theta = np.array([1.0 + 0j])
        a_phi = np.array([0.0 + 0j])
        theta = np.array([np.pi / 4])
        phi = np.array([0.0])

        psi_f1 = _convert_a_to_psi(a_theta, a_phi, theta, phi, 10e9, 1.0)
        psi_f2 = _convert_a_to_psi(a_theta, a_phi, theta, phi, 20e9, 1.0)

        np.testing.assert_allclose(np.linalg.norm(psi_f2) / np.linalg.norm(psi_f1), 2.0, rtol=1e-10)

    def test_theta_only(self):
        """Pure theta component: psi should be along e_theta."""
        a_theta = np.array([1.0 + 0j])
        a_phi = np.array([0.0 + 0j])
        theta = np.array([np.pi / 2])
        phi = np.array([0.0])
        psi = _convert_a_to_psi(a_theta, a_phi, theta, phi, 28e9, 1.0)
        # At theta=pi/2, phi=0: e_theta = [0, 0, -1]
        direction = psi[0] / np.linalg.norm(psi[0])
        np.testing.assert_allclose(np.abs(direction), [0, 0, 1], atol=1e-10)

    def test_phi_only(self):
        """Pure phi component: psi should be along e_phi."""
        a_theta = np.array([0.0 + 0j])
        a_phi = np.array([1.0 + 0j])
        theta = np.array([np.pi / 2])
        phi = np.array([0.0])
        psi = _convert_a_to_psi(a_theta, a_phi, theta, phi, 28e9, 1.0)
        # At theta=pi/2, phi=0: e_phi = [0, 1, 0]
        direction = psi[0] / np.linalg.norm(psi[0])
        np.testing.assert_allclose(np.abs(direction), [0, 1, 0], atol=1e-10)

    def test_output_is_complex(self):
        psi = _convert_a_to_psi(
            np.array([1.0 + 1j]),
            np.array([0.5 - 0.5j]),
            np.array([np.pi / 3]),
            np.array([np.pi / 4]),
            28e9,
            1.0,
        )
        assert psi.dtype == complex


# ---------------------------------------------------------------------------
# PropagationPaths.from_spherical
# ---------------------------------------------------------------------------
class TestFromSpherical:
    def test_single_path_along_z(self):
        """theta=0 means k_hat = [0, 0, 1] (downward from zenith)."""
        p = PropagationPaths.from_spherical(
            theta=np.array([0.0]),
            phi=np.array([0.0]),
            power=np.array([1.0]),
        )
        assert p.n_paths == 1
        np.testing.assert_allclose(p.k_hat[0], [0, 0, 1], atol=1e-12)

    def test_equatorial_paths(self):
        """theta=pi/2, phi=0 -> k_hat = [1, 0, 0]."""
        p = PropagationPaths.from_spherical(
            theta=np.array([np.pi / 2]),
            phi=np.array([0.0]),
            power=np.array([5.0]),
        )
        np.testing.assert_allclose(p.k_hat[0], [1, 0, 0], atol=1e-12)
        np.testing.assert_allclose(p.power[0], 5.0, rtol=1e-10)

    def test_multiple_paths(self):
        """Multiple paths from spherical coords."""
        theta = np.array([0, np.pi / 2, np.pi / 2, np.pi])
        phi = np.array([0, 0, np.pi / 2, 0])
        power = np.array([1.0, 2.0, 3.0, 4.0])
        p = PropagationPaths.from_spherical(theta, phi, power)
        assert p.n_paths == 4
        np.testing.assert_allclose(p.k_hat[0], [0, 0, 1], atol=1e-12)
        np.testing.assert_allclose(p.k_hat[1], [1, 0, 0], atol=1e-12)
        np.testing.assert_allclose(p.k_hat[2], [0, 1, 0], atol=1e-12)
        np.testing.assert_allclose(p.k_hat[3], [0, 0, -1], atol=1e-12)
        np.testing.assert_allclose(p.power, power, rtol=1e-10)

    def test_scalar_inputs(self):
        """Scalar theta/phi should work."""
        p = PropagationPaths.from_spherical(
            theta=np.float64(np.pi / 2),
            phi=np.float64(0.0),
            power=np.array([1.0]),
        )
        assert p.n_paths == 1

    def test_round_trip_power(self):
        """Power should be preserved through from_spherical."""
        rng = np.random.default_rng(42)
        n = 50
        theta = rng.uniform(0, np.pi, n)
        phi = rng.uniform(0, 2 * np.pi, n)
        power = rng.uniform(0.1, 10.0, n)
        p = PropagationPaths.from_spherical(theta, phi, power)
        np.testing.assert_allclose(p.power, power, rtol=1e-10)

    def test_k_hat_unit_vectors(self):
        """All k_hat should be unit vectors."""
        rng = np.random.default_rng(99)
        n = 100
        theta = rng.uniform(0.01, np.pi - 0.01, n)
        phi = rng.uniform(0, 2 * np.pi, n)
        power = np.ones(n)
        p = PropagationPaths.from_spherical(theta, phi, power)
        norms = np.linalg.norm(p.k_hat, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-12)

    def test_compatible_with_engine(self):
        """from_spherical paths should work with the dosimetry engine."""
        from aegis.engine import DosimetryEngine
        from aegis.geometry.mesh import BodyMesh
        from aegis.tissue.dielectric import TissueModel

        # Simple 2-triangle body (N, 3, 3) = 2 triangles, 3 vertices each, 3 coords
        body = BodyMesh.from_arrays(
            vertices=np.array(
                [
                    [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                    [[0, 0, 0], [0, 1, 0], [0, 0, 1]],
                ]
            ),
        )
        tissue = TissueModel(name="test", eps_r=10.0, sigma=1.0, freq_hz=28e9)
        paths = PropagationPaths.from_spherical(
            theta=np.array([np.pi / 2]),
            phi=np.array([0.0]),
            power=np.array([10.0]),
        )
        engine = DosimetryEngine(tissue)
        result = engine.compute(body, paths, level=3)
        assert result.p_abs >= 0
        assert result.sab.shape[0] == body.n_triangles


# ---------------------------------------------------------------------------
# Vectorized k_hat extraction in paths_from_differt
# ---------------------------------------------------------------------------
class TestVectorizedKhat:
    def test_padded_paths(self):
        """k_hat extraction with padded (zero-length) trailing segments."""
        verts = np.zeros((1, 3))
        normals = np.array([[0, 0, 1.0]])
        # Path: TX(0,0,0) -> body(10,0,0) -> padded(10,0,0)
        path_verts = np.array([[[0, 0, 0], [10, 0, 0], [10, 0, 0]]], dtype=np.float64)
        tx_pos = np.array([[0, 0, 0.0]])
        result = paths_from_differt(verts, normals, path_verts, tx_pos, freq_hz=28e9)
        # Should extract the last non-degenerate segment: [10,0,0] - [0,0,0] = [1,0,0]
        np.testing.assert_allclose(result.k_hat[0], [1, 0, 0], atol=1e-10)

    def test_multi_bounce_last_segment(self):
        """k_hat should be from the last real segment, not the first."""
        verts = np.zeros((1, 3))
        normals = np.array([[0, 0, 1.0]])
        # TX(0,0,0) -> wall(5,5,0) -> body(10,0,0)
        path_verts = np.array([[[0, 0, 0], [5, 5, 0], [10, 0, 0]]], dtype=np.float64)
        tx_pos = np.array([[0, 0, 0.0]])
        result = paths_from_differt(verts, normals, path_verts, tx_pos, freq_hz=28e9)
        # Last segment: (10,0,0) - (5,5,0) = (5,-5,0), normalized
        expected = np.array([5, -5, 0], dtype=float)
        expected /= np.linalg.norm(expected)
        np.testing.assert_allclose(result.k_hat[0], expected, atol=1e-10)

    def test_many_paths_vectorized(self):
        """Vectorized extraction should handle many paths efficiently."""
        rng = np.random.default_rng(42)
        n = 1000
        verts = np.zeros((1, 3))
        normals = np.array([[0, 0, 1.0]])
        # Random 2-vertex paths
        tx = rng.standard_normal((n, 1, 3))
        rx = rng.standard_normal((n, 1, 3))
        path_verts = np.concatenate([tx, rx], axis=1)
        tx_pos = np.array([[0, 0, 0.0]])

        result = paths_from_differt(verts, normals, path_verts, tx_pos, freq_hz=28e9)
        assert result.n_paths == n
        # All k_hat should be unit vectors
        norms = np.linalg.norm(result.k_hat, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-10)


# ---------------------------------------------------------------------------
# DosimetryResult serialization round-trip
# ---------------------------------------------------------------------------
class TestResultSerialization:
    def _make_incoherent_result(self):
        return DosimetryResult(
            sab=np.array([1.0, 2.0, 3.0]),
            p_abs=0.5,
            fidelity_level=3,
            sab_averaged=np.array([0.9, 1.8, 2.7]),
            sar_wb=0.01,
            mode="spatial",
            corrections=("fresnel",),
            sinc=np.array([10.0, 20.0, 30.0]),
            sinc_averaged=np.array([9.0, 18.0, 27.0]),
            sab_1cm2_averaged=np.array([1.1, 2.2, 3.3]),
            freq_hz=28e9,
        )

    def _make_coherent_result(self):
        return DosimetryResult(
            sab=np.array([1.0, 2.0]),
            p_abs=0.3,
            fidelity_level=7,
            Q=np.array([[1 + 2j, 3 + 4j], [3 - 4j, 5 + 0j]]),
            rho=0.42,
            eigenvalues=np.array([0.5 + 0.1j, 2.0 - 0.3j]),
            x_star=np.array([0.7 + 0.2j, 0.3 - 0.1j]),
            freq_hz=28e9,
        )

    def test_incoherent_round_trip(self):
        original = self._make_incoherent_result()
        d = original.to_dict()
        restored = DosimetryResult.from_dict(d)
        np.testing.assert_allclose(restored.sab, original.sab)
        np.testing.assert_allclose(restored.sab_averaged, original.sab_averaged)
        np.testing.assert_allclose(restored.sinc, original.sinc)
        np.testing.assert_allclose(restored.sab_1cm2_averaged, original.sab_1cm2_averaged)
        assert restored.p_abs == original.p_abs
        assert restored.sar_wb == original.sar_wb
        assert restored.fidelity_level == original.fidelity_level
        assert restored.mode == original.mode
        assert restored.corrections == original.corrections
        assert restored.freq_hz == original.freq_hz

    def test_coherent_round_trip(self):
        original = self._make_coherent_result()
        d = original.to_dict()
        restored = DosimetryResult.from_dict(d)
        np.testing.assert_allclose(restored.sab, original.sab)
        np.testing.assert_allclose(restored.Q, original.Q)
        np.testing.assert_allclose(restored.eigenvalues, original.eigenvalues)
        np.testing.assert_allclose(restored.x_star, original.x_star)
        assert restored.rho == original.rho
        assert restored.fidelity_level == 7

    def test_json_round_trip(self):
        original = self._make_incoherent_result()
        json_str = original.to_json()
        restored = DosimetryResult.from_json(json_str)
        np.testing.assert_allclose(restored.sab, original.sab)
        assert restored.mode == original.mode

    def test_minimal_result(self):
        """Minimal result with only required fields."""
        original = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.1,
            fidelity_level=2,
        )
        d = original.to_dict()
        restored = DosimetryResult.from_dict(d)
        np.testing.assert_allclose(restored.sab, original.sab)
        assert restored.p_abs == 0.1
        assert restored.sab_averaged is None
        assert restored.Q is None

    def test_extra_keys_ignored(self):
        """Extra keys in dict should be silently ignored."""
        d = {
            "sab": [1.0, 2.0],
            "p_abs": 0.5,
            "fidelity_level": 3,
            "extra_field": "should be ignored",
            "another_one": 42,
        }
        result = DosimetryResult.from_dict(d)
        assert result.p_abs == 0.5

    def test_corrections_tuple(self):
        """corrections should be a tuple after deserialization (not a list)."""
        d = {
            "sab": [1.0],
            "p_abs": 0.1,
            "fidelity_level": 3,
            "corrections": ["fresnel", "polarisation"],
        }
        result = DosimetryResult.from_dict(d)
        assert isinstance(result.corrections, tuple)
        assert result.corrections == ("fresnel", "polarisation")
