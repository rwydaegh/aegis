"""Property-based tests for dosimetry kernels using Hypothesis.

These tests verify physics invariants that must hold regardless of input:
- S_ab >= 0 (absorbed power is non-negative)
- Energy conservation: P_abs <= S_inc_total * T_0 * A_body
- Coherent single-element reduces to incoherent
- Level ordering consistency
- ECBF constraint satisfaction
"""

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from aegis.constants import Z_0
from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import NUMERICAL_FLOOR

# ---------------------------------------------------------------------------
# Strategies for random but valid inputs
# ---------------------------------------------------------------------------


def _unit_vector(rng, n):
    """Draw n random unit vectors."""
    v = rng.standard_normal((n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v


@st.composite
def random_mesh(draw, min_tri=3, max_tri=30):
    """Generate a random convex-ish mesh (icosahedron-like)."""
    seed = draw(st.integers(min_value=0, max_value=2**31))
    n_tri = draw(st.integers(min_value=min_tri, max_value=max_tri))
    rng = np.random.default_rng(seed)

    # Random triangles on a sphere (simplistic but valid for property tests)
    centroids = _unit_vector(rng, n_tri) * 0.1
    normals = centroids / np.linalg.norm(centroids, axis=1, keepdims=True)

    # Small random triangles around each centroid
    side = rng.uniform(0.005, 0.02, size=n_tri)
    vertices = np.zeros((n_tri, 3, 3))
    for i in range(n_tri):
        # Build perpendicular basis
        n = normals[i]
        u = np.cross(n, [1, 0, 0]) if abs(n[0]) < 0.9 else np.cross(n, [0, 1, 0])
        u /= np.linalg.norm(u)
        v = np.cross(n, u)
        s = side[i]
        vertices[i, 0] = centroids[i]
        vertices[i, 1] = centroids[i] + s * u
        vertices[i, 2] = centroids[i] + s * v

    areas = 0.5 * side**2  # approximate
    return BodyMesh(
        vertices=vertices,
        normals=normals,
        centroids=centroids,
        areas=areas,
        name="random",
    )


@st.composite
def random_paths(draw, min_paths=1, max_paths=20):
    """Generate random propagation paths."""
    seed = draw(st.integers(min_value=0, max_value=2**31))
    n = draw(st.integers(min_value=min_paths, max_value=max_paths))
    rng = np.random.default_rng(seed)

    k_hat = _unit_vector(rng, n)
    power = rng.uniform(0.01, 10.0, size=n)
    return PropagationPaths.from_powers(k_hat=k_hat, power=power)


# ---------------------------------------------------------------------------
# Physics invariants for incoherent kernels (levels 2-6)
# ---------------------------------------------------------------------------


class TestSabNonNegative:
    """S_ab must be non-negative for all incoherent levels."""

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=30, deadline=5000)
    def test_level2_sab_non_negative(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=2)
        assert np.all(result.sab >= NUMERICAL_FLOOR), f"min sab = {result.sab.min()}"

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=30, deadline=5000)
    def test_level3_sab_non_negative(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=3)
        assert np.all(result.sab >= NUMERICAL_FLOOR), f"min sab = {result.sab.min()}"

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=30, deadline=5000)
    def test_level4_sab_non_negative(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=4, q=0.0)
        assert np.all(result.sab >= NUMERICAL_FLOOR)

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=30, deadline=5000)
    def test_level5_sab_non_negative(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        H = np.full(mesh.n_triangles, 10.0)
        result = engine.compute(mesh, paths, level=5, curvature_H=H)
        assert np.all(result.sab >= NUMERICAL_FLOOR)

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=30, deadline=5000)
    def test_level6_sab_non_negative(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        H = np.full(mesh.n_triangles, 10.0)
        result = engine.compute(mesh, paths, level=6, curvature_H=H)
        assert np.all(result.sab >= NUMERICAL_FLOOR)


class TestEnergyConservation:
    """P_abs must not exceed the incident power times T0 times body area."""

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=30, deadline=5000)
    def test_level2_energy_bound(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=2)
        # Theoretical upper bound: each triangle absorbs at most T0 * power * 1 (cos=1)
        upper = SKIN_28GHZ.T0 * mesh.total_area * paths.total_power
        assert result.p_abs <= upper * 1.001, f"P_abs={result.p_abs:.6g} exceeds bound={upper:.6g}"

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=30, deadline=5000)
    def test_level3_energy_bound(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=3)
        # T_avg(mu) <= T0 at normal incidence, so same bound holds
        upper = SKIN_28GHZ.T0 * mesh.total_area * paths.total_power
        assert result.p_abs <= upper * 1.001


class TestLevelConsistency:
    """Levels that should agree under special conditions."""

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=20, deadline=5000)
    def test_level4_q0_equals_level3(self, mesh, paths):
        """Level 4 with q=0 must equal Level 3 (no polarisation effect)."""
        engine = DosimetryEngine(SKIN_28GHZ)
        r3 = engine.compute(mesh, paths, level=3)
        r4 = engine.compute(mesh, paths, level=4, q=0.0)
        np.testing.assert_allclose(r4.sab, r3.sab, rtol=1e-12, atol=1e-15)

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=20, deadline=5000)
    def test_level5_zero_curvature_equals_level3(self, mesh, paths):
        """Level 5 with H=0 must equal Level 3."""
        engine = DosimetryEngine(SKIN_28GHZ)
        r3 = engine.compute(mesh, paths, level=3)
        H = np.zeros(mesh.n_triangles)
        r5 = engine.compute(mesh, paths, level=5, curvature_H=H)
        np.testing.assert_allclose(r5.sab, r3.sab, rtol=1e-10, atol=1e-15)


class TestSpatialKernelComposability:
    """The mode='spatial' API must produce same results as legacy levels."""

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=20, deadline=5000)
    def test_spatial_fresnel_matches_level3(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        r3 = engine.compute(mesh, paths, level=3)
        r_sp = engine.compute(mesh, paths, mode="spatial", fresnel=True)
        np.testing.assert_allclose(r_sp.sab, r3.sab, rtol=1e-12, atol=1e-15)

    @given(mesh=random_mesh(), paths=random_paths())
    @settings(max_examples=20, deadline=5000)
    def test_spatial_no_fresnel_matches_level2(self, mesh, paths):
        engine = DosimetryEngine(SKIN_28GHZ)
        r2 = engine.compute(mesh, paths, level=2)
        r_sp = engine.compute(mesh, paths, mode="spatial", fresnel=False)
        np.testing.assert_allclose(r_sp.sab, r2.sab, rtol=1e-12, atol=1e-15)


# ---------------------------------------------------------------------------
# Coherent kernel properties
# ---------------------------------------------------------------------------


class TestCoherentProperties:
    """Physics invariants for coherent levels 7-8."""

    def _make_single_element_coherent(self, k_hat, power, n_elements=1):
        """Build coherent paths for a single antenna element."""
        k_hat = np.atleast_2d(k_hat).astype(np.float64)
        n = k_hat.shape[0]
        norms = np.linalg.norm(k_hat, axis=1, keepdims=True)
        k_hat = k_hat / norms

        # Build psi from power
        amplitude = np.sqrt(2 * Z_0 * np.maximum(power, 0.0))
        # Arbitrary polarisation perpendicular to k_hat
        ref = np.zeros_like(k_hat)
        abs_k = np.abs(k_hat)
        min_axis = np.argmin(abs_k, axis=1)
        ref[np.arange(n), min_axis] = 1.0
        e_perp = np.cross(k_hat, ref)
        e_perp /= np.linalg.norm(e_perp, axis=1, keepdims=True)
        psi = (amplitude[:, None] * e_perp).astype(complex)

        return PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=np.zeros(n, dtype=np.intp),
            delay=np.zeros(n),
            is_los=np.ones(n, dtype=bool),
        )

    def test_single_element_Q_is_hermitian_psd(self):
        """Exposure operator Q must be Hermitian PSD."""
        from aegis.precoder import Precoder

        rng = np.random.default_rng(42)
        from conftest import make_icosahedron

        body = make_icosahedron()
        k = rng.standard_normal((5, 3))
        k /= np.linalg.norm(k, axis=1, keepdims=True)
        power = rng.uniform(0.5, 2.0, size=5)
        paths = self._make_single_element_coherent(k, power)

        x = np.array([1.0 + 0j])
        precoder = Precoder(x=x)
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(body, paths, level=7, precoder=precoder)

        Q = result.Q
        assert Q is not None

        # Hermitian: Q == Q^H
        np.testing.assert_allclose(Q, Q.conj().T, atol=1e-12)

        # PSD: all eigenvalues >= 0
        eigvals = np.linalg.eigvalsh(Q)
        assert np.all(eigvals >= NUMERICAL_FLOOR), f"Negative eigenvalue: {eigvals.min()}"

    def test_ecbf_satisfies_constraint(self):
        """ECBF result must satisfy P_abs <= P_abs_max (within tolerance)."""
        from conftest import make_icosahedron

        body = make_icosahedron()
        rng = np.random.default_rng(99)

        n_elements = 4
        n_paths = 8
        k = rng.standard_normal((n_paths, 3))
        k /= np.linalg.norm(k, axis=1, keepdims=True)
        amplitude = rng.uniform(0.1, 1.0, size=n_paths)
        psi = np.zeros((n_paths, 3), dtype=complex)
        for i in range(n_paths):
            ref = np.array([1, 0, 0]) if abs(k[i, 0]) < 0.9 else np.array([0, 1, 0])
            e = np.cross(k[i], ref)
            e /= np.linalg.norm(e)
            psi[i] = amplitude[i] * e

        paths = PropagationPaths(
            k_hat=k,
            psi=psi,
            element_index=rng.integers(0, n_elements, size=n_paths),
            delay=np.zeros(n_paths),
            is_los=np.ones(n_paths, dtype=bool),
        )

        h = rng.standard_normal(n_elements) + 1j * rng.standard_normal(n_elements)
        P_abs_max = 0.01
        engine = DosimetryEngine(SKIN_28GHZ)

        result = engine.compute(body, paths, level=8, h=h, P_abs_max=P_abs_max, body_mass=70.0)

        # P_abs should respect the constraint (within solver tolerance)
        assert result.p_abs <= P_abs_max * 1.01 + 1e-10, f"P_abs={result.p_abs:.6g} exceeds P_abs_max={P_abs_max:.6g}"
        assert result.x_star is not None


# ---------------------------------------------------------------------------
# Power scaling invariants
# ---------------------------------------------------------------------------


class TestPowerScaling:
    """S_ab must scale linearly with incident power density."""

    @given(
        mesh=random_mesh(min_tri=5, max_tri=15),
        seed=st.integers(min_value=0, max_value=2**31),
        scale=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=20, deadline=5000)
    def test_linear_scaling_level2(self, mesh, seed, scale):
        rng = np.random.default_rng(seed)
        n = rng.integers(1, 10)
        k = _unit_vector(rng, n)
        pwr = rng.uniform(0.1, 5.0, size=n)

        p1 = PropagationPaths.from_powers(k_hat=k, power=pwr)
        p2 = PropagationPaths.from_powers(k_hat=k, power=pwr * scale)

        engine = DosimetryEngine(SKIN_28GHZ)
        r1 = engine.compute(mesh, p1, level=2)
        r2 = engine.compute(mesh, p2, level=2)

        np.testing.assert_allclose(r2.sab, r1.sab * scale, rtol=1e-10)

    @given(
        mesh=random_mesh(min_tri=5, max_tri=15),
        seed=st.integers(min_value=0, max_value=2**31),
        scale=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=20, deadline=5000)
    def test_linear_scaling_level3(self, mesh, seed, scale):
        rng = np.random.default_rng(seed)
        n = rng.integers(1, 10)
        k = _unit_vector(rng, n)
        pwr = rng.uniform(0.1, 5.0, size=n)

        p1 = PropagationPaths.from_powers(k_hat=k, power=pwr)
        p2 = PropagationPaths.from_powers(k_hat=k, power=pwr * scale)

        engine = DosimetryEngine(SKIN_28GHZ)
        r1 = engine.compute(mesh, p1, level=3)
        r2 = engine.compute(mesh, p2, level=3)

        np.testing.assert_allclose(r2.sab, r1.sab * scale, rtol=1e-10)


# ---------------------------------------------------------------------------
# Averaging matrix properties
# ---------------------------------------------------------------------------


class TestAveragingProperties:
    """Properties of the spatial averaging matrix."""

    def test_averaging_reduces_peak(self):
        """Spatial averaging must not increase the maximum value (smoothing)."""
        from conftest import make_flat_mesh

        mesh = make_flat_mesh(200)
        engine = DosimetryEngine(SKIN_28GHZ)

        # Create a single path that illuminates one side more
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.5, 0.0, -np.sqrt(0.75)]]),
            power=np.array([10.0]),
        )
        result = engine.compute(mesh, paths, level=2)
        # peak_sab_averaged <= peak_sab (averaging smooths the peak)
        assert result.peak_sab_averaged <= result.peak_sab + 1e-10

    def test_averaging_preserves_total_power(self):
        """Area-weighted sum of averaged S_ab equals P_abs."""
        from conftest import make_flat_mesh

        mesh = make_flat_mesh(100)
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([5.0]),
        )
        result = engine.compute(mesh, paths, level=2)

        # P_abs from sab
        p_from_raw = float(np.sum(result.sab * mesh.areas))
        # P_abs from averaged sab (row-stochastic G preserves area-weighted sum)
        p_from_avg = float(np.sum(result.sab_averaged * mesh.areas))
        np.testing.assert_allclose(p_from_avg, p_from_raw, rtol=1e-6)
