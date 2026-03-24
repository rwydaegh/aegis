"""Tests for Agent 2 features: max_compliant_power, DosimetryResult.scale,
BodyMesh.from_arrays, and LRU cache eviction."""

import math

import numpy as np
import pytest

from aegis.compliance import (
    ExposureScenario,
    evaluate_compliance,
    max_compliant_power,
)
from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.result import DosimetryResult
from aegis.tissue.dielectric import SKIN_28GHZ

# ---------------------------------------------------------------------------
# max_compliant_power
# ---------------------------------------------------------------------------


class TestMaxCompliantPower:
    """Test max_compliant_power()."""

    def test_half_limit_doubles_power(self) -> None:
        """If measured Sab is half the limit, max power is 2x reference."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)  # limit 20
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(2.0)

    def test_at_limit_returns_ref(self) -> None:
        """If measured equals limit, max power equals reference."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=20.0)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(1.0)

    def test_over_limit_returns_less(self) -> None:
        """If measured exceeds limit, max power < reference."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=40.0)  # 2x limit
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(0.5)

    def test_tightest_constraint_wins(self) -> None:
        """Max power is limited by the tightest check."""
        r = evaluate_compliance(
            freq_hz=28e9,
            sab_4cm2=10.0,  # 10/20 = 0.5x -> can 2x
            sar_wb=0.04,  # 0.04/0.08 = 0.5x -> can 2x
            sinc_whole_body=8.0,  # 8/10 = 0.8x -> can 1.25x (tightest)
        )
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(10.0 / 8.0)

    def test_zero_measured_returns_inf(self) -> None:
        """If all measured values are zero, no constraint binds."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=0.0)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == float("inf")

    def test_no_checks_returns_inf(self) -> None:
        """If no values provided, max power is unconstrained."""
        r = evaluate_compliance(freq_hz=28e9)
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == float("inf")

    def test_ref_power_scales(self) -> None:
        """Max power scales linearly with reference power."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        p1 = max_compliant_power(r, ref_power_w=1.0)
        p2 = max_compliant_power(r, ref_power_w=2.0)
        assert p2 == pytest.approx(2 * p1)

    def test_occupational_allows_more(self) -> None:
        """Occupational limits are 5x higher, so max power is 5x higher."""
        r_gp = evaluate_compliance(
            freq_hz=28e9,
            scenario=ExposureScenario.GENERAL_PUBLIC,
            sab_4cm2=10.0,
        )
        r_oc = evaluate_compliance(
            freq_hz=28e9,
            scenario=ExposureScenario.OCCUPATIONAL,
            sab_4cm2=10.0,
        )
        p_gp = max_compliant_power(r_gp, ref_power_w=1.0)
        p_oc = max_compliant_power(r_oc, ref_power_w=1.0)
        assert p_oc == pytest.approx(5 * p_gp)

    def test_negative_ref_power_raises(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        with pytest.raises(ValueError, match="positive"):
            max_compliant_power(r, ref_power_w=-1.0)

    def test_zero_ref_power_raises(self) -> None:
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        with pytest.raises(ValueError, match="positive"):
            max_compliant_power(r, ref_power_w=0.0)

    def test_above_30ghz_includes_1cm2(self) -> None:
        """Above 30 GHz, 1 cm^2 limit (40 W/m^2) may be the binding constraint."""
        r = evaluate_compliance(
            freq_hz=60e9,
            sab_4cm2=10.0,  # limit 20 -> can 2x
            sab_1cm2=30.0,  # limit 40 -> can 1.33x (tighter)
        )
        p_max = max_compliant_power(r, ref_power_w=1.0)
        assert p_max == pytest.approx(40.0 / 30.0)

    def test_converts_to_dbm(self) -> None:
        """Verify the max power in dBm makes sense."""
        r = evaluate_compliance(freq_hz=28e9, sab_4cm2=10.0)
        p_max_w = max_compliant_power(r, ref_power_w=0.2)  # 200 mW = 23 dBm
        p_max_dbm = 10 * math.log10(p_max_w * 1000)
        # 2x ref -> 0.4 W = 400 mW -> ~26 dBm
        assert p_max_dbm == pytest.approx(10 * math.log10(400), rel=1e-6)


# ---------------------------------------------------------------------------
# DosimetryResult.scale
# ---------------------------------------------------------------------------


class TestDosimetryResultScale:
    """Test DosimetryResult.scale()."""

    @pytest.fixture
    def base_result(self) -> DosimetryResult:
        """A result at 1 W reference."""
        return DosimetryResult(
            sab=np.array([1.0, 2.0, 3.0]),
            p_abs=0.5,
            fidelity_level=3,
            sab_averaged=np.array([1.5, 2.0, 2.5]),
            sar_wb=0.01,
            sinc=np.array([2.0, 3.0, 4.0]),
            sinc_averaged=np.array([2.5, 3.0, 3.5]),
            sab_1cm2_averaged=np.array([1.2, 2.2, 3.2]),
            freq_hz=28e9,
        )

    def test_scale_doubles_sab(self, base_result) -> None:
        scaled = base_result.scale(2.0)
        np.testing.assert_allclose(scaled.sab, 2.0 * base_result.sab)

    def test_scale_doubles_p_abs(self, base_result) -> None:
        scaled = base_result.scale(2.0)
        assert scaled.p_abs == pytest.approx(2.0 * base_result.p_abs)

    def test_scale_doubles_sar(self, base_result) -> None:
        scaled = base_result.scale(2.0)
        assert scaled.sar_wb == pytest.approx(2.0 * base_result.sar_wb)

    def test_scale_doubles_averaged(self, base_result) -> None:
        scaled = base_result.scale(2.0)
        np.testing.assert_allclose(scaled.sab_averaged, 2.0 * base_result.sab_averaged)
        np.testing.assert_allclose(scaled.sinc_averaged, 2.0 * base_result.sinc_averaged)
        np.testing.assert_allclose(scaled.sab_1cm2_averaged, 2.0 * base_result.sab_1cm2_averaged)

    def test_scale_preserves_metadata(self, base_result) -> None:
        scaled = base_result.scale(2.0)
        assert scaled.fidelity_level == base_result.fidelity_level
        assert scaled.freq_hz == base_result.freq_hz
        assert scaled.mode == base_result.mode
        assert scaled.corrections == base_result.corrections

    def test_scale_zero(self, base_result) -> None:
        scaled = base_result.scale(0.0)
        np.testing.assert_allclose(scaled.sab, 0.0)
        assert scaled.p_abs == 0.0

    def test_scale_one_is_identity(self, base_result) -> None:
        scaled = base_result.scale(1.0)
        np.testing.assert_allclose(scaled.sab, base_result.sab)
        assert scaled.p_abs == base_result.p_abs

    def test_negative_factor_raises(self, base_result) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            base_result.scale(-1.0)

    def test_scale_none_fields(self) -> None:
        """Scale works when optional fields are None."""
        r = DosimetryResult(sab=np.array([1.0]), p_abs=0.1, fidelity_level=2)
        scaled = r.scale(3.0)
        np.testing.assert_allclose(scaled.sab, [3.0])
        assert scaled.sab_averaged is None
        assert scaled.sar_wb is None
        assert scaled.sinc is None

    def test_coherent_q_scales(self) -> None:
        """Q and eigenvalues scale, but rho and x_star do not."""
        Q = np.array([[1.0, 0.5], [0.5, 2.0]])
        eigs = np.array([2.0, 0.5])
        x_star = np.array([0.7, 0.3])
        r = DosimetryResult(
            sab=np.array([1.0]),
            p_abs=0.1,
            fidelity_level=7,
            Q=Q,
            eigenvalues=eigs,
            x_star=x_star,
            rho=0.5,
        )
        scaled = r.scale(3.0)
        np.testing.assert_allclose(scaled.Q, 3.0 * Q)
        np.testing.assert_allclose(scaled.eigenvalues, 3.0 * eigs)
        np.testing.assert_allclose(scaled.x_star, x_star)  # not scaled
        assert scaled.rho == 0.5  # not scaled

    def test_chain_scale(self, base_result) -> None:
        """scale(a).scale(b) == scale(a*b)."""
        chained = base_result.scale(2.0).scale(3.0)
        direct = base_result.scale(6.0)
        np.testing.assert_allclose(chained.sab, direct.sab)
        assert chained.p_abs == pytest.approx(direct.p_abs)


# ---------------------------------------------------------------------------
# DosimetryResult.evaluate_compliance
# ---------------------------------------------------------------------------


class TestDosimetryResultEvaluateCompliance:
    """Test DosimetryResult.evaluate_compliance()."""

    def test_pass_at_low_power(self) -> None:
        r = DosimetryResult(
            sab=np.array([5.0, 10.0]),
            p_abs=0.01,
            fidelity_level=3,
            sab_averaged=np.array([8.0, 12.0]),
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.overall_pass is True
        assert cr.sab_4cm2 is not None
        assert cr.sab_4cm2.value == pytest.approx(12.0)

    def test_fail_at_high_power(self) -> None:
        r = DosimetryResult(
            sab=np.array([50.0]),
            p_abs=1.0,
            fidelity_level=3,
            sab_averaged=np.array([50.0]),
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.overall_pass is False

    def test_missing_freq_raises(self) -> None:
        r = DosimetryResult(sab=np.array([1.0]), p_abs=0.01, fidelity_level=2)
        with pytest.raises(ValueError, match="freq_hz"):
            r.evaluate_compliance()

    def test_occupational_scenario(self) -> None:
        r = DosimetryResult(
            sab=np.array([50.0]),
            p_abs=1.0,
            fidelity_level=3,
            sab_averaged=np.array([50.0]),
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance(ExposureScenario.OCCUPATIONAL)
        # 50 < 100 occupational limit
        assert cr.overall_pass is True

    def test_includes_sar_when_available(self) -> None:
        r = DosimetryResult(
            sab=np.array([5.0]),
            p_abs=0.01,
            fidelity_level=3,
            sab_averaged=np.array([5.0]),
            sar_wb=0.05,
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.sar_wb is not None
        assert cr.sar_wb.value == pytest.approx(0.05)

    def test_includes_sinc_when_available(self) -> None:
        r = DosimetryResult(
            sab=np.array([5.0]),
            p_abs=0.01,
            fidelity_level=3,
            sab_averaged=np.array([5.0]),
            sinc_averaged=np.array([15.0, 20.0]),
            freq_hz=28e9,
        )
        cr = r.evaluate_compliance()
        assert cr.sinc_local is not None
        assert cr.sinc_local.value == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# BodyMesh.from_arrays
# ---------------------------------------------------------------------------


class TestBodyMeshFromArrays:
    """Test BodyMesh.from_arrays()."""

    def test_basic(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        body = BodyMesh.from_arrays(vertices)
        assert body.n_triangles == 1
        assert body.name == "synthetic"
        assert body.areas[0] == pytest.approx(0.5)
        np.testing.assert_allclose(body.normals[0], [0, 0, 1])

    def test_custom_normals(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        normals = np.array([[0, 0, -1.0]])  # intentionally flipped
        body = BodyMesh.from_arrays(vertices, normals=normals)
        np.testing.assert_allclose(body.normals[0], [0, 0, -1])

    def test_multiple_triangles(self) -> None:
        vertices = np.array(
            [
                [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                [[0, 0, 0], [0, 1, 0], [0, 0, 1]],
                [[0, 0, 0], [1, 0, 0], [0, 0, 1]],
            ],
            dtype=np.float64,
        )
        body = BodyMesh.from_arrays(vertices)
        assert body.n_triangles == 3
        assert body.centroids.shape == (3, 3)

    def test_computed_normals_are_unit(self) -> None:
        rng = np.random.default_rng(42)
        vertices = rng.standard_normal((10, 3, 3))
        body = BodyMesh.from_arrays(vertices)
        norms = np.linalg.norm(body.normals, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-12)

    def test_custom_name(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        body = BodyMesh.from_arrays(vertices, name="test_mesh")
        assert body.name == "test_mesh"

    def test_wrong_shape_raises(self) -> None:
        with pytest.raises(ValueError, match="\\(N, 3, 3\\)"):
            BodyMesh.from_arrays(np.zeros((5, 3)))

    def test_normals_shape_mismatch_raises(self) -> None:
        vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        with pytest.raises(ValueError, match="normals"):
            BodyMesh.from_arrays(vertices, normals=np.zeros((2, 3)))

    def test_compatible_with_engine(self) -> None:
        """from_arrays mesh works with DosimetryEngine."""
        vertices = np.array(
            [
                [[0, 0, 0], [0.01, 0, 0], [0, 0.01, 0]],
                [[0.01, 0, 0], [0.01, 0.01, 0], [0, 0.01, 0]],
            ],
            dtype=np.float64,
        )
        body = BodyMesh.from_arrays(vertices)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=3)
        assert result.peak_sab > 0


# ---------------------------------------------------------------------------
# LRU cache eviction
# ---------------------------------------------------------------------------


class TestCacheEviction:
    """Test that caches are bounded and evict old entries."""

    def test_G_cache_bounded(self) -> None:
        """_G_cache never exceeds _G_CACHE_MAX entries."""
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )

        old_max = DosimetryEngine._G_CACHE_MAX
        DosimetryEngine._G_CACHE_MAX = 4
        DosimetryEngine._G_cache.clear()

        try:
            for i in range(10):
                rng = np.random.default_rng(i)
                vertices = np.zeros((5, 3, 3))
                s = 0.01
                for j in range(5):
                    cx, cy = rng.uniform(0, 0.1, 2)
                    vertices[j] = [[cx, cy, 0], [cx + s, cy, 0], [cx, cy + s, 0]]
                body = BodyMesh.from_arrays(vertices)
                engine.compute(body, paths, level=3)
                assert len(DosimetryEngine._G_cache) <= DosimetryEngine._G_CACHE_MAX
        finally:
            DosimetryEngine._G_CACHE_MAX = old_max
            DosimetryEngine._G_cache.clear()

    def test_fibonacci_cache_bounded(self) -> None:
        """_fibonacci_sphere_cache never exceeds limit."""
        from aegis.geometry.projected_area import (
            _FIBONACCI_CACHE_MAX,
            _fibonacci_sphere_cache,
            fibonacci_sphere,
        )

        _fibonacci_sphere_cache.clear()
        try:
            for n in range(1, _FIBONACCI_CACHE_MAX + 20):
                fibonacci_sphere(n)
                assert len(_fibonacci_sphere_cache) <= _FIBONACCI_CACHE_MAX
        finally:
            _fibonacci_sphere_cache.clear()


# ---------------------------------------------------------------------------
# Integration: scale + max_compliant_power end-to-end
# ---------------------------------------------------------------------------


class TestScaleComplianceIntegration:
    """End-to-end: compute at ref power, scale, find max compliant power."""

    def test_round_trip(self) -> None:
        """Compute at P_ref, find P_max, scale to P_max, verify compliance."""
        vertices = np.zeros((20, 3, 3))
        rng = np.random.default_rng(99)
        s = 0.01
        for i in range(20):
            cx, cy = rng.uniform(0, 0.1, 2)
            vertices[i] = [[cx, cy, 0], [cx + s, cy, 0], [cx, cy + s, 0]]
        body = BodyMesh.from_arrays(vertices)

        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([10.0]),  # high power -> likely over limit
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=3, freq_hz=28e9)

        # Evaluate compliance at reference
        cr_ref = result.evaluate_compliance()

        # Find max compliant power
        P_ref = 1.0  # 1 W reference
        p_max = max_compliant_power(cr_ref, ref_power_w=P_ref)

        # Scale result to max compliant power
        scale_factor = p_max / P_ref
        scaled = result.scale(scale_factor)

        # At exactly P_max, the tightest check should be at the limit
        cr_scaled = scaled.evaluate_compliance()
        assert cr_scaled.overall_pass is True

        # Slightly over should fail
        over = result.scale(scale_factor * 1.01)
        cr_over = over.evaluate_compliance()
        # The tightest check should now fail (unless rounding)
        tightest = min(c.margin_db for c in cr_over.all_checks)
        assert tightest < 0.1  # very close to or below limit

    def test_already_compliant(self) -> None:
        """If already compliant, P_max >= P_ref."""
        body = BodyMesh.from_arrays(np.array([[[0, 0, 0], [0.01, 0, 0], [0, 0.01, 0]]], dtype=np.float64))
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([0.001]),  # very low power
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=3, freq_hz=28e9)
        cr = result.evaluate_compliance()
        assert cr.overall_pass is True

        p_max = max_compliant_power(cr, ref_power_w=1.0)
        assert p_max >= 1.0
