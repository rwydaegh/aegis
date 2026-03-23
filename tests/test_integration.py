"""Tests for ray tracer integration (DiffeRT path loader)."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.constants import C_0
from aegis.integration.differt import paths_from_differt
from aegis.tissue.fresnel import fresnel_reflection, n_complex
from aegis.viewer.raytracer import isotropic_incident_power_density


class TestPathsFromDiffert:
    """Test the low-level path conversion (does not require DiffeRT installed)."""

    def test_single_los_path(self):
        """A single LOS path: TX at (5,0,3) -> body at (0,0,1)."""
        tx_pos = np.array([[5.0, 0.0, 3.0]])
        body_pos = np.array([0.0, 0.0, 1.0])

        # Path vertices: just TX and RX (LOS)
        path_vertices = np.array([[[5.0, 0.0, 3.0], [0.0, 0.0, 1.0]]])

        paths = paths_from_differt(
            vertices=np.zeros((1, 3)),  # dummy scene geometry
            normals=np.zeros((1, 3)),
            path_vertices=path_vertices,
            tx_positions=tx_pos,
            freq_hz=28e9,
        )

        assert paths.n_paths == 1
        assert paths.n_elements == 1

        # k_hat should point from TX to body (normalised)
        expected_dir = body_pos - tx_pos[0]
        expected_dir /= np.linalg.norm(expected_dir)
        np.testing.assert_allclose(paths.k_hat[0], expected_dir, atol=1e-10)

        # Power should be positive
        assert paths.power[0] > 0

        # Delay should be distance / c
        dist = np.linalg.norm(body_pos - tx_pos[0])
        np.testing.assert_allclose(paths.delay[0], dist / C_0, rtol=1e-10)

        assert bool(paths.is_los[0])
        tx_power_w = 10 ** ((60.0 - 30) / 10)
        expected_S = tx_power_w / (4.0 * np.pi * dist**2)
        np.testing.assert_allclose(paths.power[0], expected_S, rtol=1e-10)

    def test_multiple_paths_multi_element(self):
        """Multiple paths from 2 TX elements."""
        tx_positions = np.array([[5.0, 0.0, 3.0], [5.0, 0.05, 3.0]])

        # 3 paths, all padded to 3 vertices (max bounces + 2)
        # LOS paths have the last vertex repeated for padding
        padded = np.array(
            [
                [[5.0, 0.0, 3.0], [0.0, 0.0, 1.0], [0.0, 0.0, 1.0]],  # LOS from elem 0
                [[5.0, 0.0, 3.0], [2.0, 3.0, 2.0], [0.0, 0.0, 1.0]],  # reflected from elem 0
                [[5.05, 0.05, 3.0], [0.0, 0.0, 1.0], [0.0, 0.0, 1.0]],  # LOS from elem 1
            ]
        )

        paths = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=np.zeros((1, 3)),
            path_vertices=padded,
            tx_positions=tx_positions,
            freq_hz=28e9,
            element_indices=np.array([0, 0, 1]),
        )

        assert paths.n_paths == 3
        assert paths.n_elements == 2
        np.testing.assert_array_equal(paths.element_index, [0, 0, 1])

        # All k_hat should be unit vectors
        norms = np.linalg.norm(paths.k_hat, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-10)

        # All powers positive
        assert np.all(paths.power > 0)

        np.testing.assert_array_equal(paths.is_los, [True, False, True])

    def test_isotropic_incident_power_matches_friis_relation(self):
        """S = P_rx / A_e with isotropic RX is equivalent to P_tx / (4 pi d^2)."""
        d = 10.0
        freq_hz = 28e9
        wavelength = C_0 / freq_hz
        tx_power_w = 1.0
        # Friis received power (isotropic Gt=Gr=1)
        p_rx = tx_power_w * (wavelength / (4 * np.pi * d)) ** 2
        ae = wavelength**2 / (4 * np.pi)
        s_from_friis = p_rx / ae
        s_direct = isotropic_incident_power_density(tx_power_w, d)
        np.testing.assert_allclose(s_from_friis, s_direct, rtol=1e-12)
        np.testing.assert_allclose(s_direct, tx_power_w / (4 * np.pi * d**2), rtol=1e-12)

    def test_empty_paths(self):
        """No paths should return empty PropagationPaths."""
        paths = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=np.zeros((1, 3)),
            path_vertices=np.zeros((0, 2, 3)),
            tx_positions=np.array([[0.0, 0.0, 0.0]]),
            freq_hz=28e9,
        )
        assert paths.n_paths == 0

    def test_power_decreases_with_distance(self):
        """Paths from farther TX should have less power (FSPL)."""
        tx_near = np.array([[2.0, 0.0, 1.0]])
        tx_far = np.array([[20.0, 0.0, 1.0]])

        pv_near = np.array([[[2.0, 0.0, 1.0], [0.0, 0.0, 1.0]]])
        pv_far = np.array([[[20.0, 0.0, 1.0], [0.0, 0.0, 1.0]]])

        paths_near = paths_from_differt(
            np.zeros((1, 3)),
            np.zeros((1, 3)),
            pv_near,
            tx_near,
            28e9,
        )
        paths_far = paths_from_differt(
            np.zeros((1, 3)),
            np.zeros((1, 3)),
            pv_far,
            tx_far,
            28e9,
        )

        assert paths_near.power[0] > paths_far.power[0]

    def test_element_auto_assignment(self):
        """Element indices auto-assigned from nearest TX position."""
        tx_positions = np.array(
            [
                [5.0, 0.0, 3.0],
                [10.0, 0.0, 3.0],
            ]
        )

        path_vertices = np.array(
            [
                [[5.1, 0.0, 3.0], [0.0, 0.0, 1.0]],  # closer to elem 0
                [[9.9, 0.0, 3.0], [0.0, 0.0, 1.0]],  # closer to elem 1
            ]
        )

        paths = paths_from_differt(
            np.zeros((1, 3)),
            np.zeros((1, 3)),
            path_vertices,
            tx_positions,
            28e9,
        )

        assert paths.element_index[0] == 0
        assert paths.element_index[1] == 1

    def test_paths_usable_in_engine(self):
        """Paths from differt loader should work with DosimetryEngine."""
        from aegis.engine import DosimetryEngine
        from aegis.geometry.mesh import BodyMesh
        from aegis.tissue.dielectric import SKIN_28GHZ

        # Simple 2-triangle body
        vertices = np.array(
            [
                [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                [[0, 0, 0], [0, 1, 0], [0, 0, 1]],
            ],
            dtype=np.float64,
        )
        normals = np.array([[0, 0, 1], [1, 0, 0]], dtype=np.float64)
        areas = np.array([0.5, 0.5])
        centroids = np.mean(vertices, axis=1)

        body = BodyMesh(
            vertices=vertices,
            normals=normals,
            centroids=centroids,
            areas=areas,
            name="test",
        )

        path_vertices = np.array([[[5.0, 0.0, 3.0], [0.5, 0.5, 0.5]]])
        tx_positions = np.array([[5.0, 0.0, 3.0]])

        paths = paths_from_differt(
            np.zeros((1, 3)),
            np.zeros((1, 3)),
            path_vertices,
            tx_positions,
            28e9,
        )

        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=2)

        assert result.p_abs >= 0
        assert result.sab.shape == (2,)
        assert np.all(result.sab >= 0)


# Concrete at 28 GHz: eps_r=5.31, sigma=0.0326
N_CONCRETE = n_complex(5.31, 0.0326, 28e9)

# High-conductivity metal approximation
N_METAL = n_complex(1.0, 1e7, 28e9)


class TestPolarisationTracking:
    """Tests for TE/TM polarisation tracking through reflections."""

    def test_los_polarisation_preserved(self):
        """LOS path (no reflections) preserves initial vertical polarisation."""
        tx_pos = np.array([[5.0, 0.0, 3.0]])
        path_vertices = np.array([[[5.0, 0.0, 3.0], [0.0, 0.0, 1.0]]])
        # object_indices: -1 for TX and RX
        obj_idx = np.array([[-1, -1]])

        paths = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=np.array([[0.0, 0.0, 1.0]]),
            path_vertices=path_vertices,
            tx_positions=tx_pos,
            freq_hz=28e9,
            object_indices=obj_idx,
            material_indices=np.array([0]),
            material_n_tilde=[N_CONCRETE],
        )

        psi = paths.psi[0]
        # psi should be perpendicular to k_hat
        k = paths.k_hat[0]
        assert abs(np.dot(psi, k)) == pytest.approx(0.0, abs=1e-10)

        # psi should have a z component (vertical polarisation projected perp to k)
        # k points roughly from (5,0,3) to (0,0,1) = (-5,0,-2)/sqrt(29)
        # Vertical pol (z) projected perp to k should retain some z
        psi_real = np.real(psi)
        psi_norm = psi_real / np.linalg.norm(psi_real)
        # The z component of psi should be nonzero
        assert abs(psi_norm[2]) > 0.1

    def test_single_reflection_power_reduction(self):
        """One reflection off concrete reduces power by |r|^2."""
        # Path: TX(5,0,3) -> wall(2.5,0,0) -> body(0,0,3)
        # Wall at y=0 with normal (0,0,1) pointing up
        # This is a specular reflection off the ground
        tx = np.array([5.0, 0.0, 3.0])
        wall = np.array([2.5, 0.0, 0.0])
        body = np.array([0.0, 0.0, 3.0])

        path_vertices = np.array([[tx, wall, body]])
        obj_idx = np.array([[-1, 0, -1]])  # triangle 0 at bounce
        wall_normal = np.array([[0.0, 0.0, 1.0]])

        # With polarisation tracking
        paths_pol = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=wall_normal,
            path_vertices=path_vertices,
            tx_positions=tx[np.newaxis],
            freq_hz=28e9,
            object_indices=obj_idx,
            material_indices=np.array([0]),
            material_n_tilde=[N_CONCRETE],
        )

        # Without polarisation tracking (arbitrary perp)
        paths_arb = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=wall_normal,
            path_vertices=path_vertices,
            tx_positions=tx[np.newaxis],
            freq_hz=28e9,
        )

        # Polarisation-tracked power should be less than arbitrary
        # (arbitrary doesn't apply reflection loss)
        power_pol = paths_pol.power[0]
        power_arb = paths_arb.power[0]
        assert power_pol < power_arb

        # Compute expected reflection loss
        k_i = (wall - tx) / np.linalg.norm(wall - tx)
        cos_theta = abs(np.dot(wall_normal[0], -k_i))
        r_s, r_p = fresnel_reflection(cos_theta, N_CONCRETE)
        # Average power reflection (unpolarised bound)
        max_r2 = max(abs(r_s) ** 2, abs(r_p) ** 2)
        # Power should be reduced by at most |r|^2
        assert power_pol / power_arb <= max_r2 + 0.01

    def test_metal_reflection_near_unity(self):
        """Reflection off metal preserves nearly all power."""
        tx = np.array([5.0, 0.0, 3.0])
        wall = np.array([2.5, 0.0, 0.0])
        body = np.array([0.0, 0.0, 3.0])

        path_vertices = np.array([[tx, wall, body]])
        obj_idx = np.array([[-1, 0, -1]])
        wall_normal = np.array([[0.0, 0.0, 1.0]])

        paths_pol = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=wall_normal,
            path_vertices=path_vertices,
            tx_positions=tx[np.newaxis],
            freq_hz=28e9,
            object_indices=obj_idx,
            material_indices=np.array([0]),
            material_n_tilde=[N_METAL],
        )

        paths_arb = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=wall_normal,
            path_vertices=path_vertices,
            tx_positions=tx[np.newaxis],
            freq_hz=28e9,
        )

        # Metal reflection should preserve >99% of power
        ratio = paths_pol.power[0] / paths_arb.power[0]
        assert ratio > 0.99

    def test_power_never_increases(self):
        """After reflections, |psi|^2 should not exceed the FSPL-only value."""
        # Two-bounce path
        tx = np.array([10.0, 0.0, 3.0])
        w1 = np.array([7.0, 3.0, 0.0])
        w2 = np.array([3.0, 3.0, 0.0])
        body = np.array([0.0, 0.0, 1.0])

        path_vertices = np.array([[tx, w1, w2, body]])
        obj_idx = np.array([[-1, 0, 1, -1]])
        normals = np.array(
            [
                [0.0, 0.0, 1.0],
                [0.0, 0.0, 1.0],
            ]
        )

        paths_pol = paths_from_differt(
            vertices=np.zeros((2, 3)),
            normals=normals,
            path_vertices=path_vertices,
            tx_positions=tx[np.newaxis],
            freq_hz=28e9,
            object_indices=obj_idx,
            material_indices=np.array([0, 0]),
            material_n_tilde=[N_CONCRETE],
        )

        paths_arb = paths_from_differt(
            vertices=np.zeros((2, 3)),
            normals=normals,
            path_vertices=path_vertices,
            tx_positions=tx[np.newaxis],
            freq_hz=28e9,
        )

        # Tracked power <= FSPL-only power
        assert paths_pol.power[0] <= paths_arb.power[0] * (1 + 1e-10)

    def test_backward_compatible(self):
        """Without object_indices, behavior matches old arbitrary perpendicular."""
        tx_pos = np.array([[5.0, 0.0, 3.0]])
        path_vertices = np.array([[[5.0, 0.0, 3.0], [2.5, 0.0, 0.0], [0.0, 0.0, 1.0]]])

        paths = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=np.zeros((1, 3)),
            path_vertices=path_vertices,
            tx_positions=tx_pos,
            freq_hz=28e9,
        )

        # psi should be perpendicular to k_hat
        k = paths.k_hat[0]
        psi = paths.psi[0]
        assert abs(np.dot(psi, k)) == pytest.approx(0.0, abs=1e-10)

        # Power should match FSPL (no reflection loss applied)
        assert paths.power[0] > 0

    def test_horizontal_polarisation(self):
        """Horizontal initial polarisation should be perpendicular to z and k."""
        tx_pos = np.array([[5.0, 0.0, 3.0]])
        path_vertices = np.array([[[5.0, 0.0, 3.0], [0.0, 0.0, 1.0]]])
        obj_idx = np.array([[-1, -1]])

        paths = paths_from_differt(
            vertices=np.zeros((1, 3)),
            normals=np.array([[0.0, 0.0, 1.0]]),
            path_vertices=path_vertices,
            tx_positions=tx_pos,
            freq_hz=28e9,
            object_indices=obj_idx,
            material_indices=np.array([0]),
            material_n_tilde=[N_CONCRETE],
            initial_polarisation="horizontal",
        )

        psi = paths.psi[0]
        k = paths.k_hat[0]
        # psi perpendicular to k
        assert abs(np.dot(psi, k)) == pytest.approx(0.0, abs=1e-10)
        # Horizontal pol should be in the x-y plane (z component ~ 0)
        psi_real = np.real(psi)
        psi_norm = psi_real / np.linalg.norm(psi_real)
        assert abs(psi_norm[2]) < 0.1
