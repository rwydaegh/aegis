"""Tests for analysis.py: path_contributions, exposure_heatmap, path_importance.

These functions analyze which propagation paths contribute most to absorbed
power density. Tests verify physics invariants: non-negativity, correct
summation, ordering, and consistency across the three functions.
"""

from __future__ import annotations

import numpy as np
from conftest import make_flat_mesh, make_icosahedron, make_single_triangle

from aegis.analysis import exposure_heatmap, path_contributions, path_importance
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_paths(n: int = 8, seed: int = 0) -> PropagationPaths:
    rng = np.random.default_rng(seed)
    k_hat = rng.standard_normal((n, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.1, 2.0, size=n)
    return PropagationPaths.from_powers(k_hat=k_hat, power=power)


def _make_single_path_down() -> PropagationPaths:
    return PropagationPaths.from_powers(
        k_hat=np.array([[0.0, 0.0, -1.0]]),
        power=np.array([1.0]),
    )


# ---------------------------------------------------------------------------
# path_contributions
# ---------------------------------------------------------------------------


class TestPathContributions:
    def test_returns_expected_keys(self):
        body = make_flat_mesh(50)
        paths = _make_paths()
        result = path_contributions(body, paths, SKIN_28GHZ)
        required = {
            "triangle_index",
            "sab_total",
            "path_indices",
            "contributions",
            "fractions",
            "cumulative",
            "k_hat",
            "power",
        }
        assert required <= result.keys()

    def test_sab_total_positive(self):
        body = make_icosahedron()
        paths = _make_paths()
        result = path_contributions(body, paths, SKIN_28GHZ)
        assert result["sab_total"] >= 0.0

    def test_contributions_non_negative(self):
        body = make_icosahedron()
        paths = _make_paths()
        result = path_contributions(body, paths, SKIN_28GHZ)
        assert np.all(result["contributions"] >= 0.0)

    def test_fractions_sum_to_one(self):
        body = make_flat_mesh(50)
        paths = _make_paths()
        result = path_contributions(body, paths, SKIN_28GHZ)
        if result["sab_total"] > 0:
            assert abs(np.sum(result["fractions"]) - 1.0) < 1e-10

    def test_fractions_sum_to_one_single_path(self):
        body = make_single_triangle()
        paths = _make_single_path_down()
        result = path_contributions(body, paths, SKIN_28GHZ)
        if result["sab_total"] > 0:
            assert abs(np.sum(result["fractions"]) - 1.0) < 1e-10

    def test_cumulative_last_is_one(self):
        body = make_flat_mesh(50)
        paths = _make_paths()
        result = path_contributions(body, paths, SKIN_28GHZ)
        if result["sab_total"] > 0:
            assert abs(result["cumulative"][-1] - 1.0) < 1e-10

    def test_cumulative_monotone(self):
        body = make_flat_mesh(50)
        paths = _make_paths()
        result = path_contributions(body, paths, SKIN_28GHZ)
        assert np.all(np.diff(result["cumulative"]) >= -1e-12)

    def test_contributions_sorted_descending(self):
        body = make_flat_mesh(50)
        paths = _make_paths()
        result = path_contributions(body, paths, SKIN_28GHZ)
        c = result["contributions"]
        assert np.all(np.diff(c) <= 1e-12), "contributions must be sorted descending"

    def test_top_k_limits_output(self):
        body = make_flat_mesh(50)
        n_paths = 8
        paths = _make_paths(n=n_paths)
        result = path_contributions(body, paths, SKIN_28GHZ, top_k=3)
        assert len(result["contributions"]) == 3
        assert len(result["path_indices"]) == 3
        assert len(result["k_hat"]) == 3
        assert len(result["power"]) == 3

    def test_top_k_equals_n_same_as_no_top_k(self):
        body = make_icosahedron()
        n_paths = 8
        paths = _make_paths(n=n_paths)
        full = path_contributions(body, paths, SKIN_28GHZ)
        topk = path_contributions(body, paths, SKIN_28GHZ, top_k=n_paths)
        np.testing.assert_array_equal(full["path_indices"], topk["path_indices"])

    def test_explicit_triangle_index(self):
        body = make_flat_mesh(50)
        paths = _make_paths()
        target = 5
        result = path_contributions(body, paths, SKIN_28GHZ, triangle_index=target)
        assert result["triangle_index"] == target

    def test_default_triangle_is_peak(self):
        body = make_flat_mesh(50)
        paths = _make_paths()
        result = path_contributions(body, paths, SKIN_28GHZ)
        # Compute sab manually and check peak
        from aegis.kernels._base import fresnel_weights, incidence_geometry

        mu, mu_plus = incidence_geometry(body.normals, paths.k_hat)
        _, _, T_avg = fresnel_weights(mu, SKIN_28GHZ.n_complex)
        C = np.asarray(T_avg * mu_plus)
        sab = C @ np.asarray(paths.power)
        expected_peak = int(np.argmax(sab))
        assert result["triangle_index"] == expected_peak

    def test_k_hat_shape(self):
        body = make_flat_mesh(50)
        n_paths = 8
        paths = _make_paths(n=n_paths)
        result = path_contributions(body, paths, SKIN_28GHZ)
        assert result["k_hat"].shape == (n_paths, 3)

    def test_path_indices_in_range(self):
        body = make_flat_mesh(50)
        n_paths = 8
        paths = _make_paths(n=n_paths)
        result = path_contributions(body, paths, SKIN_28GHZ)
        assert np.all(result["path_indices"] >= 0)
        assert np.all(result["path_indices"] < n_paths)

    def test_zero_power_gives_zero_sab(self):
        body = make_single_triangle()
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([0.0]),
        )
        result = path_contributions(body, paths, SKIN_28GHZ)
        assert result["sab_total"] == 0.0


# ---------------------------------------------------------------------------
# exposure_heatmap
# ---------------------------------------------------------------------------


class TestExposureHeatmap:
    def test_shape(self):
        n_tri = 20
        n_paths = 6
        body = make_icosahedron()  # 20 triangles
        paths = _make_paths(n=n_paths)
        C = exposure_heatmap(body, paths, SKIN_28GHZ)
        assert C.shape == (n_tri, n_paths)

    def test_non_negative(self):
        body = make_icosahedron()
        paths = _make_paths()
        C = exposure_heatmap(body, paths, SKIN_28GHZ)
        assert np.all(C >= -1e-15), "heatmap entries must be non-negative"

    def test_row_sum_matches_sab(self):
        """C.sum(axis=1) should equal the level-3 S_ab per triangle."""
        from aegis.kernels._base import fresnel_weights, incidence_geometry

        body = make_icosahedron()
        paths = _make_paths()
        C = exposure_heatmap(body, paths, SKIN_28GHZ)
        sab_from_heatmap = C.sum(axis=1)

        # Recompute directly
        mu, mu_plus = incidence_geometry(body.normals, paths.k_hat)
        _, _, T_avg = fresnel_weights(mu, SKIN_28GHZ.n_complex)
        sab_direct = np.asarray(T_avg * mu_plus) @ np.asarray(paths.power)

        np.testing.assert_allclose(sab_from_heatmap, sab_direct, rtol=1e-10)

    def test_columns_scale_with_power(self):
        """Doubling power for path j should double column j of heatmap."""
        body = make_icosahedron()
        n_paths = 4
        rng = np.random.default_rng(7)
        k_hat = rng.standard_normal((n_paths, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = np.ones(n_paths)
        paths1 = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        power2 = power.copy()
        power2[0] *= 2.0
        paths2 = PropagationPaths.from_powers(k_hat=k_hat, power=power2)

        C1 = exposure_heatmap(body, paths1, SKIN_28GHZ)
        C2 = exposure_heatmap(body, paths2, SKIN_28GHZ)
        np.testing.assert_allclose(C2[:, 0], 2 * C1[:, 0], rtol=1e-10)
        np.testing.assert_allclose(C2[:, 1:], C1[:, 1:], rtol=1e-10)


# ---------------------------------------------------------------------------
# path_importance
# ---------------------------------------------------------------------------


class TestPathImportance:
    def test_shape(self):
        n_paths = 8
        body = make_icosahedron()
        paths = _make_paths(n=n_paths)
        imp = path_importance(body, paths, SKIN_28GHZ)
        assert imp.shape == (n_paths,)

    def test_non_negative(self):
        body = make_icosahedron()
        paths = _make_paths()
        imp = path_importance(body, paths, SKIN_28GHZ)
        assert np.all(imp >= -1e-15)

    def test_sums_to_p_abs(self):
        """Sum of path importances should equal total absorbed power P_abs.

        P_abs = sum_m area_m * S_ab(m) = area @ C @ power = importance.sum()
        """
        from aegis.engine import DosimetryEngine

        body = make_icosahedron()
        paths = _make_paths()
        imp = path_importance(body, paths, SKIN_28GHZ)
        p_abs_from_importance = float(np.sum(imp))

        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=3)
        p_abs_direct = float(result.p_abs)

        assert abs(p_abs_from_importance - p_abs_direct) / (p_abs_direct + 1e-30) < 1e-8

    def test_scales_linearly_with_power(self):
        """Scaling all powers by k should scale all importances by k."""
        body = make_icosahedron()
        n_paths = 6
        rng = np.random.default_rng(11)
        k_hat = rng.standard_normal((n_paths, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 1.0, n_paths)
        paths1 = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        paths2 = PropagationPaths.from_powers(k_hat=k_hat, power=power * 3.0)

        imp1 = path_importance(body, paths1, SKIN_28GHZ)
        imp2 = path_importance(body, paths2, SKIN_28GHZ)
        np.testing.assert_allclose(imp2, 3.0 * imp1, rtol=1e-10)

    def test_consistency_with_exposure_heatmap(self):
        """path_importance must equal area @ exposure_heatmap."""
        body = make_icosahedron()
        paths = _make_paths()
        imp = path_importance(body, paths, SKIN_28GHZ)
        C = exposure_heatmap(body, paths, SKIN_28GHZ)
        imp_from_heatmap = np.asarray(body.areas) @ C
        np.testing.assert_allclose(imp, imp_from_heatmap, rtol=1e-10)

    def test_zero_power_gives_zero_importance(self):
        body = make_icosahedron()
        n_paths = 4
        rng = np.random.default_rng(99)
        k_hat = rng.standard_normal((n_paths, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=np.zeros(n_paths))
        imp = path_importance(body, paths, SKIN_28GHZ)
        assert np.all(imp == 0.0)

    def test_single_path_down_flat_mesh(self):
        """Single downward path on flat +z mesh: all triangles contribute equally."""
        body = make_flat_mesh(100)
        paths = _make_single_path_down()
        imp = path_importance(body, paths, SKIN_28GHZ)
        assert imp.shape == (1,)
        assert float(imp[0]) > 0.0
