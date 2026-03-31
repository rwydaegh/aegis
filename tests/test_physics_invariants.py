"""Deep physics invariant tests for AEGIS dosimetry kernels.

Tests fundamental physics properties that must hold regardless of input:
- Fresnel coefficient identities and bounds
- Level ordering (L2 >= L3 for lossy tissue)
- GELU convergence to ReLU
- Cole-Cole model stability
- Tissue dispersion monotonicity
- Coherent-incoherent equivalence for single element
- DosimetryResult.scale linearity
- Input validation (NaN, inf, negative freq)
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import NUMERICAL_FLOOR, make_flat_mesh, make_icosahedron, make_single_triangle

from aegis.engine import DosimetryEngine
from aegis.kernels._base import fresnel_weights, incidence_geometry, physical_gelu
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import FAT_28GHZ, MUSCLE_28GHZ, SKIN_28GHZ, SKIN_60GHZ, TissueModel
from aegis.tissue.fresnel import T0 as T0_func
from aegis.tissue.fresnel import _fresnel_core, fresnel_transmission

# ---------------------------------------------------------------------------
# Fresnel coefficient physics
# ---------------------------------------------------------------------------


class TestFresnelIdentities:
    """Fundamental Fresnel coefficient properties."""

    @pytest.mark.parametrize(
        "tissue",
        [SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ],
        ids=["skin28", "skin60", "muscle28", "fat28"],
    )
    def test_normal_incidence_ts_equals_tp(self, tissue):
        """At normal incidence (mu=1), T_s must equal T_p."""
        T_s, T_p = fresnel_transmission(1.0, tissue.n_complex)
        assert abs(T_s - T_p) < 1e-12, f"T_s={T_s}, T_p={T_p} differ at normal incidence"

    @pytest.mark.parametrize(
        "tissue",
        [SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ],
        ids=["skin28", "skin60", "muscle28", "fat28"],
    )
    def test_normal_incidence_matches_T0(self, tissue):
        """T_avg at normal incidence must match the T0 formula."""
        T_s, T_p = fresnel_transmission(1.0, tissue.n_complex)
        T_avg = 0.5 * (T_s + T_p)
        T0 = T0_func(tissue.n_complex)
        assert abs(T_avg - T0) < 1e-12, f"T_avg={T_avg}, T0={T0}"

    @pytest.mark.parametrize(
        "tissue",
        [SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ],
        ids=["skin28", "skin60", "muscle28", "fat28"],
    )
    def test_fresnel_bounded_0_1(self, tissue):
        """T_s and T_p must be in [0, 1] for all incidence angles."""
        mu = np.linspace(0.0, 1.0, 200)
        T_s, T_p = fresnel_transmission(mu, tissue.n_complex)
        assert np.all(T_s >= NUMERICAL_FLOOR), f"T_s min = {T_s.min()}"
        assert np.all(T_p >= NUMERICAL_FLOOR), f"T_p min = {T_p.min()}"
        assert np.all(T_s <= 1.0 + 1e-14), f"T_s max = {T_s.max()}"
        assert np.all(T_p <= 1.0 + 1e-14), f"T_p max = {T_p.max()}"

    def test_grazing_incidence_zero_transmission(self):
        """At grazing incidence (mu=0), transmission must be zero."""
        T_s, T_p = fresnel_transmission(0.0, SKIN_28GHZ.n_complex)
        assert abs(T_s) < 1e-10
        assert abs(T_p) < 1e-10

    def test_T0_positive_for_lossy_tissue(self):
        """T0 must be positive for any tissue with Re(n) > 0."""
        for tissue in [SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ]:
            T0 = T0_func(tissue.n_complex)
            assert T0 > 0, f"T0={T0} for {tissue.name}"
            assert T0 < 1, f"T0={T0} >= 1 for {tissue.name}"

    def test_fresnel_core_matches_convenience_wrapper(self):
        """_fresnel_core and fresnel_transmission must agree."""
        mu_vals = np.array([0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
        n_tilde = SKIN_28GHZ.n_complex
        T_s_wrap, T_p_wrap = fresnel_transmission(mu_vals, n_tilde)

        from aegis._array_backend import xp

        mu_c = xp.asarray(mu_vals, dtype=complex)
        _, _, T_s_core, T_p_core, _, _ = _fresnel_core(mu_c, n_tilde)
        np.testing.assert_allclose(np.asarray(T_s_core), T_s_wrap, atol=1e-12)
        np.testing.assert_allclose(np.asarray(T_p_core), T_p_wrap, atol=1e-12)

    @pytest.mark.parametrize(
        "n_real",
        [1.5, 2.0, 3.0, 5.0],
    )
    def test_brewster_angle_lossless(self, n_real):
        """For lossless dielectric, T_p reaches 1 at Brewster angle."""
        # Brewster angle: tan(theta_B) = n, so cos(theta_B) = 1/sqrt(1+n^2)
        mu_brewster = 1.0 / np.sqrt(1.0 + n_real**2)
        n_tilde = complex(n_real, 0)
        T_s, T_p = fresnel_transmission(mu_brewster, n_tilde)
        assert abs(T_p - 1.0) < 1e-10, f"T_p at Brewster = {T_p}, expected 1.0"


# ---------------------------------------------------------------------------
# Level ordering for lossy tissue
# ---------------------------------------------------------------------------


class TestLevelOrdering:
    """Level ordering and Fresnel T_avg behavior relative to T0."""

    def test_Tavg_exceeds_T0_near_pseudo_brewster(self):
        """For skin/muscle, T_avg(mu) can exceed T0 near the pseudo-Brewster angle.

        This is correct physics: TM transmission T_p is enhanced near Brewster
        angle. For moderately lossy tissue (kappa/n < ~0.5), this enhancement
        causes T_avg = (T_s + T_p)/2 to exceed T0 = T_avg(mu=1). The effect
        is ~3-6% for skin at 28 GHz and ~6-12% for muscle.

        Consequence: Level 3 (Fresnel) can give HIGHER sab than Level 2
        (geometric with constant T0) at oblique incidence angles.
        """
        mu = np.linspace(0.0, 1.0, 1000)
        for tissue in [SKIN_28GHZ, MUSCLE_28GHZ]:
            T_s, T_p = fresnel_transmission(mu, tissue.n_complex)
            T_avg = 0.5 * (T_s + T_p)
            T0 = tissue.T0
            max_excess = (T_avg - T0).max()
            # Verify the pseudo-Brewster enhancement exists and is bounded
            assert max_excess > 0.01, f"Expected Brewster enhancement for {tissue.name}"
            assert max_excess < 0.2, f"Implausibly large enhancement: {max_excess}"

    def test_Tavg_leq_T0_for_low_loss_tissue(self):
        """For low-loss tissue (fat), T_avg(mu) <= T0 for all mu."""
        mu = np.linspace(0.0, 1.0, 1000)
        T_s, T_p = fresnel_transmission(mu, FAT_28GHZ.n_complex)
        T_avg = 0.5 * (T_s + T_p)
        T0 = FAT_28GHZ.T0
        assert np.all(T_avg <= T0 + 1e-10)

    def test_L2_vs_L3_bounded_difference(self):
        """L2 and L3 must differ by less than 20% for skin at 28 GHz."""
        body = make_icosahedron()
        rng = np.random.default_rng(42)
        k_hat = rng.standard_normal((20, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 5.0, size=20)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

        engine = DosimetryEngine(SKIN_28GHZ)
        r2 = engine.compute(body, paths, level=2)
        r3 = engine.compute(body, paths, level=3)

        rel_diff = abs(r2.p_abs - r3.p_abs) / max(r2.p_abs, r3.p_abs)
        assert rel_diff < 0.2, f"L2 vs L3 differ by {rel_diff:.1%}"

    def test_normal_incidence_L2_equals_L3(self):
        """At normal incidence, L2 must equal L3 (T_avg(1) = T0)."""
        body = make_flat_mesh(50)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([5.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        r2 = engine.compute(body, paths, level=2)
        r3 = engine.compute(body, paths, level=3)

        np.testing.assert_allclose(r2.sab, r3.sab, rtol=1e-10)


# ---------------------------------------------------------------------------
# GELU convergence to ReLU
# ---------------------------------------------------------------------------


class TestGELUConvergence:
    """physical_gelu must converge to ReLU as sigma -> 0."""

    def test_gelu_converges_to_relu(self):
        """GELU with very small sigma should match ReLU."""
        mu_vals = np.array([-0.5, -0.1, -0.01, 0.0, 0.01, 0.1, 0.5, 1.0])
        mu = mu_vals.reshape(-1, 1)  # (M, 1) for (M, N) shape
        sigma = np.array([1e-10])  # tiny sigma

        gelu = np.asarray(physical_gelu(mu, sigma))
        relu = np.maximum(mu, 0.0)

        np.testing.assert_allclose(gelu, relu, atol=1e-8)

    def test_gelu_leq_relu_for_positive_mu(self):
        """For mu > 0, GELU(mu, sigma) <= mu (= ReLU) for any sigma > 0.

        This is because GELU = mu * 0.5 * (1 + erf(mu/sigma)) and erf < 1,
        so the factor 0.5*(1+erf) < 1.
        """
        mu = np.linspace(0.01, 1.0, 50).reshape(-1, 1)
        for sigma_val in [0.01, 0.1, 0.5, 1.0]:
            sigma = np.array([sigma_val])
            gelu = np.asarray(physical_gelu(mu, sigma))
            assert np.all(gelu <= mu + 1e-14), f"GELU > ReLU at sigma={sigma_val}"
            assert np.all(gelu >= 0), f"GELU < 0 for positive mu at sigma={sigma_val}"

    def test_gelu_smooth_at_zero(self):
        """GELU must be smooth (no discontinuity) at mu=0."""
        sigma = np.array([0.1])
        eps = 1e-6
        mu_minus = np.array([[-eps]])
        mu_zero = np.array([[0.0]])
        mu_plus = np.array([[eps]])

        g_minus = float(np.asarray(physical_gelu(mu_minus, sigma)).ravel()[0])
        g_zero = float(np.asarray(physical_gelu(mu_zero, sigma)).ravel()[0])
        g_plus = float(np.asarray(physical_gelu(mu_plus, sigma)).ravel()[0])

        # Continuity: values at mu=+-eps should be close to value at mu=0
        # GELU derivative at 0 is 0.5, so g(eps) - g(0) ~ 0.5*eps
        assert abs(g_plus - g_zero) < 2.0 * eps
        assert abs(g_zero - g_minus) < 2.0 * eps

    def test_gelu_at_zero_is_zero(self):
        """GELU(0, sigma) = 0 for any sigma."""
        for sigma_val in [0.001, 0.1, 1.0, 10.0]:
            sigma = np.array([sigma_val])
            mu = np.array([[0.0]])
            g = float(np.asarray(physical_gelu(mu, sigma)).ravel()[0])
            assert abs(g) < 1e-30, f"GELU(0, {sigma_val}) = {g}"


# ---------------------------------------------------------------------------
# Level 6 zero-curvature reduces to Level 3
# ---------------------------------------------------------------------------


class TestLevelReduction:
    """Levels must reduce to simpler levels under special conditions."""

    def test_level6_zero_curvature_matches_level3(self):
        """Level 6 with H=0 must match Level 3 (GELU->ReLU, no curvature term)."""
        body = make_icosahedron()
        rng = np.random.default_rng(77)
        k_hat = rng.standard_normal((10, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 3.0, size=10)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

        engine = DosimetryEngine(SKIN_28GHZ)
        r3 = engine.compute(body, paths, level=3)
        H = np.zeros(body.n_triangles)
        r6 = engine.compute(body, paths, level=6, curvature_H=H)

        np.testing.assert_allclose(r6.sab, r3.sab, rtol=1e-6, atol=1e-12)

    def test_spatial_no_corrections_matches_level2(self):
        """mode='spatial' with fresnel=False and no corrections matches L2."""
        body = make_icosahedron()
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0], [1.0, 0.0, 0.0]]),
            power=np.array([3.0, 1.5]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        r2 = engine.compute(body, paths, level=2)
        r_sp = engine.compute(body, paths, mode="spatial", fresnel=False)
        np.testing.assert_allclose(r_sp.sab, r2.sab, rtol=1e-12, atol=1e-15)


# ---------------------------------------------------------------------------
# Cole-Cole model stability
# ---------------------------------------------------------------------------


class TestColeColeStability:
    """Cole-Cole model must produce physically valid tissue properties."""

    def test_sigma_positive_across_frequency(self):
        """Effective conductivity must be positive at all mmWave frequencies."""

        for tissue in [SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ]:
            omega = 2 * np.pi * tissue.freq_hz
            from aegis.constants import EPS_0

            # sigma = -Im(eps_complex) * omega * eps_0
            # For any physical tissue, sigma > 0
            eps_complex = tissue.eps_r - 1j * tissue.sigma / (omega * EPS_0)
            sigma_eff = -np.imag(eps_complex) * omega * EPS_0
            assert sigma_eff > 0, f"Negative sigma for {tissue.name}: {sigma_eff}"

    def test_refractive_index_real_part_positive(self):
        """Re(n_tilde) must be positive for all tissues."""
        for tissue in [SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ]:
            n = tissue.n_complex
            assert np.real(n) > 0, f"Re(n) = {np.real(n)} for {tissue.name}"

    def test_T0_consistent_between_implementations(self):
        """T0 from fresnel.T0() must match database.get_tissue_properties() formula."""
        # T0 = 4*Re(n) / |1+n|^2
        for tissue in [SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ]:
            n = tissue.n_complex
            T0_fresnel = T0_func(n)
            T0_manual = float(4 * np.real(n) / abs(1 + n) ** 2)
            assert abs(T0_fresnel - T0_manual) < 1e-14, f"T0 mismatch for {tissue.name}"


# ---------------------------------------------------------------------------
# DosimetryResult.scale linearity
# ---------------------------------------------------------------------------


class TestResultScaling:
    """DosimetryResult.scale() must preserve physics."""

    def test_scale_linearity(self):
        """scale(a).scale(b) == scale(a*b) for the key fields."""
        body = make_icosahedron()
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([2.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        r = engine.compute(body, paths, level=3, freq_hz=28e9)

        r_2x = r.scale(2.0)
        r_6x = r.scale(6.0)

        # scale(2).scale(3) should give same as scale(6)
        r_2x_3x = r_2x.scale(3.0)
        np.testing.assert_allclose(r_2x_3x.sab, r_6x.sab, rtol=1e-14)
        assert abs(r_2x_3x.p_abs - r_6x.p_abs) < 1e-14 * r_6x.p_abs

    def test_scale_zero_gives_zero(self):
        """scale(0) must give all-zero sab."""
        body = make_icosahedron()
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        r = engine.compute(body, paths, level=2)

        r0 = r.scale(0.0)
        assert np.all(r0.sab == 0.0)
        assert r0.p_abs == 0.0

    def test_scale_negative_raises(self):
        """scale() with negative factor must raise."""
        body = make_single_triangle()
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        r = engine.compute(body, paths, level=2)

        with pytest.raises(ValueError, match="non-negative"):
            r.scale(-1.0)

    def test_scale_preserves_compliance(self):
        """Compliance status must be consistent after scaling."""
        body = make_flat_mesh(100)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([0.1]),  # low power, should be compliant
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        r = engine.compute(body, paths, level=3, freq_hz=28e9)

        # At low power, should be compliant
        assert r.peak_sab_averaged < 20.0  # ICNIRP limit

        # Scale up until non-compliant
        r_big = r.scale(1e6)
        assert r_big.peak_sab_averaged > 20.0


# ---------------------------------------------------------------------------
# Coherent single-element vs incoherent equivalence
# ---------------------------------------------------------------------------


class TestCoherentIncoherentEquivalence:
    """Single-element coherent (L7) must give consistent results with incoherent (L3)."""

    def test_single_element_Q_diagonal_is_sab_areas(self):
        """For single element with x=[1], x^H Q x = sum(sab * areas)."""
        from aegis.precoder import Precoder

        body = make_icosahedron()
        rng = np.random.default_rng(42)
        k_hat = rng.standard_normal((5, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        amp = rng.uniform(0.1, 1.0, size=5)

        # Single-element coherent paths
        psi = np.zeros((5, 3), dtype=complex)
        for i in range(5):
            ref = np.array([1, 0, 0]) if abs(k_hat[i, 0]) < 0.9 else np.array([0, 1, 0])
            e = np.cross(k_hat[i], ref)
            e /= np.linalg.norm(e)
            psi[i] = amp[i] * e

        paths = PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=np.zeros(5, dtype=np.intp),
            delay=np.zeros(5),
            is_los=np.ones(5, dtype=bool),
        )

        x = np.array([1.0 + 0j])
        precoder = Precoder(x=x)
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=7, precoder=precoder)

        # x^H Q x should equal sum(sab * areas)
        Q = result.Q
        xQx = float(np.real(x.conj() @ Q @ x))
        p_abs_from_sab = float(np.sum(result.sab * body.areas))

        np.testing.assert_allclose(xQx, p_abs_from_sab, rtol=1e-8)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """AEGIS must reject or handle invalid inputs gracefully."""

    def test_nan_power_in_from_powers(self):
        """NaN in power should raise ValueError."""
        with pytest.raises((ValueError, FloatingPointError)):
            PropagationPaths.from_powers(
                k_hat=np.array([[0.0, 0.0, -1.0]]),
                power=np.array([float("nan")]),
            )

    def test_inf_power_in_from_powers(self):
        """Inf in power should raise ValueError."""
        with pytest.raises((ValueError, FloatingPointError)):
            PropagationPaths.from_powers(
                k_hat=np.array([[0.0, 0.0, -1.0]]),
                power=np.array([float("inf")]),
            )

    def test_negative_power_accepted(self):
        """Negative power should work (clamped to 0 in amplitude)."""
        # from_powers uses np.maximum(power, 0.0) internally
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([-1.0]),
        )
        assert np.all(paths.power >= 0)

    def test_scale_nan_raises(self):
        """scale(nan) should raise ValueError."""
        body = make_single_triangle()
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        r = engine.compute(body, paths, level=2)

        with pytest.raises(ValueError):
            r.scale(float("nan"))

    def test_scale_inf_raises(self):
        """scale(inf) should raise ValueError."""
        body = make_single_triangle()
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        r = engine.compute(body, paths, level=2)

        with pytest.raises(ValueError):
            r.scale(float("inf"))

    def test_zero_frequency_raises(self):
        """Zero frequency must raise ValueError, not produce garbage."""
        with pytest.raises(ValueError, match="[Ff]req"):
            TissueModel("bad", eps_r=17.0, sigma=25.0, freq_hz=0.0)

    def test_negative_frequency_raises(self):
        """Negative frequency must raise ValueError."""
        with pytest.raises(ValueError, match="[Ff]req"):
            TissueModel("bad", eps_r=17.0, sigma=25.0, freq_hz=-1e9)


# ---------------------------------------------------------------------------
# Incidence geometry
# ---------------------------------------------------------------------------


class TestIncidenceGeometry:
    """Tests for the core incidence geometry computation."""

    def test_mu_range(self):
        """mu = n_hat . (-k_hat) must be in [-1, 1] for unit vectors."""
        rng = np.random.default_rng(42)
        normals = rng.standard_normal((50, 3))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        k_hat = rng.standard_normal((30, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)

        mu, mu_plus = incidence_geometry(normals, k_hat)
        assert np.all(mu >= -1.0 - 1e-10)
        assert np.all(mu <= 1.0 + 1e-10)
        assert np.all(mu_plus >= 0.0)
        assert np.all(mu_plus <= 1.0 + 1e-10)

    def test_back_facing_is_zero(self):
        """Back-facing triangles (mu < 0) must have mu_plus = 0."""
        normals = np.array([[0, 0, 1.0]])  # faces +z
        k_hat = np.array([[0, 0, 1.0]])  # propagates +z (hits back)

        mu, mu_plus = incidence_geometry(normals, k_hat)
        assert mu[0, 0] < 0  # back-facing
        assert mu_plus[0, 0] == 0.0  # ReLU zeros it

    def test_normal_incidence_gives_one(self):
        """Head-on incidence (normal // -k_hat) must give mu = 1."""
        normals = np.array([[0, 0, 1.0]])
        k_hat = np.array([[0, 0, -1.0]])  # propagates toward normal

        mu, mu_plus = incidence_geometry(normals, k_hat)
        assert abs(mu[0, 0] - 1.0) < 1e-14
        assert abs(mu_plus[0, 0] - 1.0) < 1e-14


# ---------------------------------------------------------------------------
# Fresnel weights in kernel base
# ---------------------------------------------------------------------------


class TestFresnelWeights:
    """Test fresnel_weights used inside kernels."""

    def test_fresnel_weights_shape(self):
        """fresnel_weights must return (M, N) arrays."""
        normals = np.array([[0, 0, 1.0], [1, 0, 0.0], [0, 1, 0.0]])
        k_hat = np.array([[0, 0, -1.0], [0, -1, 0.0]])
        mu, _ = incidence_geometry(normals, k_hat)

        T_s, T_p, T_avg = fresnel_weights(mu, SKIN_28GHZ.n_complex)
        assert T_s.shape == (3, 2)
        assert T_p.shape == (3, 2)
        assert T_avg.shape == (3, 2)

    def test_fresnel_weights_non_negative(self):
        """Fresnel weights must be non-negative."""
        body = make_icosahedron()
        rng = np.random.default_rng(42)
        k_hat = rng.standard_normal((20, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)

        mu, _ = incidence_geometry(body.normals, k_hat)
        T_s, T_p, T_avg = fresnel_weights(mu, SKIN_28GHZ.n_complex)

        assert np.all(np.asarray(T_s) >= NUMERICAL_FLOOR)
        assert np.all(np.asarray(T_p) >= NUMERICAL_FLOOR)
        assert np.all(np.asarray(T_avg) >= NUMERICAL_FLOOR)


# ---------------------------------------------------------------------------
# Energy conservation across all levels
# ---------------------------------------------------------------------------


class TestEnergyConservationAllLevels:
    """P_abs must not exceed the theoretical maximum for any level."""

    @pytest.mark.parametrize("level", [2, 3, 4, 5, 6])
    def test_p_abs_bounded(self, level):
        """P_abs <= T0 * total_area * total_power for all incoherent levels."""
        body = make_icosahedron()
        rng = np.random.default_rng(level * 42)
        n = 15
        k_hat = rng.standard_normal((n, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 5.0, size=n)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

        engine = DosimetryEngine(SKIN_28GHZ)
        kwargs = {}
        if level == 4:
            kwargs["q"] = 0.5
        if level in (5, 6):
            kwargs["curvature_H"] = np.full(body.n_triangles, 20.0)

        result = engine.compute(body, paths, level=level, **kwargs)

        upper_bound = SKIN_28GHZ.T0 * body.total_area * paths.total_power
        # Allow generous factor for curvature correction (can add power)
        safety = 2.0 if level in (5, 6) else 1.001
        assert result.p_abs <= upper_bound * safety, (
            f"Level {level}: P_abs={result.p_abs:.6g} exceeds {safety}x bound={upper_bound:.6g}"
        )
