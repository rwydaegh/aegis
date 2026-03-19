"""Tests for ray tracer integration (DiffeRT path loader)."""

from __future__ import annotations

import numpy as np

from aegis.constants import C_0
from aegis.integration.differt import paths_from_differt


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
