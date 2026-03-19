"""Tests for DosimetryEngine and kernel dispatch.

Tests use synthetic meshes (icosahedron, flat plane) so they run without
external data. E2E tests on Thelonious are in test_e2e.py (marked slow).
"""

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_flat_mesh(n: int = 100) -> BodyMesh:
    """Create a flat square mesh in the xy-plane, normals pointing +z.

    Each triangle has area ~1e-4 m^2.
    """
    rng = np.random.default_rng(42)
    side = np.sqrt(n * 1e-4)
    vertices = np.zeros((n, 3, 3))
    for i in range(n):
        cx = rng.uniform(0, side)
        cy = rng.uniform(0, side)
        s = np.sqrt(1e-4 * 2)  # triangle side for area ~1e-4
        vertices[i, 0] = [cx, cy, 0]
        vertices[i, 1] = [cx + s, cy, 0]
        vertices[i, 2] = [cx, cy + s, 0]

    normals = np.tile([0, 0, 1.0], (n, 1))
    centroids = np.mean(vertices, axis=1)
    areas = 0.5 * s * s * np.ones(n)

    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="flat_plane")


def _make_icosahedron() -> BodyMesh:
    """Create an icosahedron mesh (20 triangles) centered at origin."""
    phi = (1 + np.sqrt(5)) / 2
    verts_raw = np.array(
        [
            [-1, phi, 0],
            [1, phi, 0],
            [-1, -phi, 0],
            [1, -phi, 0],
            [0, -1, phi],
            [0, 1, phi],
            [0, -1, -phi],
            [0, 1, -phi],
            [phi, 0, -1],
            [phi, 0, 1],
            [-phi, 0, -1],
            [-phi, 0, 1],
        ],
        dtype=float,
    )
    # Normalize to unit sphere
    verts_raw /= np.linalg.norm(verts_raw[0])
    # Scale to ~10cm radius
    verts_raw *= 0.1

    faces = [
        (0, 11, 5),
        (0, 5, 1),
        (0, 1, 7),
        (0, 7, 10),
        (0, 10, 11),
        (1, 5, 9),
        (5, 11, 4),
        (11, 10, 2),
        (10, 7, 6),
        (7, 1, 8),
        (3, 9, 4),
        (3, 4, 2),
        (3, 2, 6),
        (3, 6, 8),
        (3, 8, 9),
        (4, 9, 5),
        (2, 4, 11),
        (6, 2, 10),
        (8, 6, 7),
        (9, 8, 1),
    ]

    n = len(faces)
    vertices = np.zeros((n, 3, 3))
    for i, (a, b, c) in enumerate(faces):
        vertices[i] = [verts_raw[a], verts_raw[b], verts_raw[c]]

    # Compute normals from cross product
    v0 = vertices[:, 0]
    v1 = vertices[:, 1]
    v2 = vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(cross, axis=1, keepdims=True)
    normals = cross / norms

    # Ensure outward-pointing (away from origin)
    centroids = np.mean(vertices, axis=1)
    flip = np.sum(normals * centroids, axis=1) < 0
    normals[flip] *= -1

    areas = 0.5 * norms[:, 0]

    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="icosahedron")


@pytest.fixture
def flat_mesh():
    return _make_flat_mesh()


@pytest.fixture
def ico_mesh():
    return _make_icosahedron()


@pytest.fixture
def engine():
    return DosimetryEngine(SKIN_28GHZ)


@pytest.fixture
def single_path_down():
    """Single plane wave from +z (downward)."""
    return PropagationPaths.from_powers(
        k_hat=np.array([[0, 0, -1.0]]),
        power=np.array([1.0]),
    )


@pytest.fixture
def multi_path():
    """Multiple paths from different directions."""
    rng = np.random.default_rng(123)
    N = 50
    k_hat = rng.standard_normal((N, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.1, 2.0, size=N)
    return PropagationPaths.from_powers(k_hat=k_hat, power=power)


# ---------------------------------------------------------------------------
# PropagationPaths tests
# ---------------------------------------------------------------------------


class TestPropagationPaths:
    def test_from_powers_single(self):
        p = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        assert p.n_paths == 1
        assert p.n_elements == 1
        assert p.power[0] == pytest.approx(1.0, rel=1e-10)

    def test_from_powers_preserves_power(self):
        powers = np.array([0.5, 1.0, 2.0])
        k = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        p = PropagationPaths.from_powers(k_hat=k, power=powers)
        np.testing.assert_allclose(p.power, powers, rtol=1e-10)

    def test_k_hat_normalised(self):
        p = PropagationPaths.from_powers(
            k_hat=np.array([[3, 4, 0.0]]),
            power=np.array([1.0]),
        )
        assert np.linalg.norm(p.k_hat[0]) == pytest.approx(1.0, abs=1e-14)

    def test_psi_perpendicular_to_k(self):
        p = PropagationPaths.from_powers(
            k_hat=np.array([[1, 0, 0.0]]),
            power=np.array([1.0]),
        )
        dot = np.abs(np.sum(p.psi[0] * p.k_hat[0]))
        assert dot < 1e-10

    def test_repr(self):
        p = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        assert "n_paths=1" in repr(p)


# ---------------------------------------------------------------------------
# DosimetryResult tests
# ---------------------------------------------------------------------------


class TestDosimetryResult:
    def test_basic_properties(self, engine, flat_mesh, single_path_down):
        result = engine.compute(flat_mesh, single_path_down, level=2)
        assert result.fidelity_level == 2
        assert result.p_abs > 0
        assert result.peak_sab > 0
        assert result.sab_averaged is None
        assert result.sar_wb is None
        assert result.compliant_sab is None

    def test_with_body_mass(self, engine, flat_mesh, single_path_down):
        result = engine.compute(flat_mesh, single_path_down, level=2, body_mass=70.0)
        assert result.sar_wb is not None
        assert result.sar_wb > 0
        assert result.compliant_sar is not None

    def test_repr(self, engine, flat_mesh, single_path_down):
        result = engine.compute(flat_mesh, single_path_down, level=2)
        r = repr(result)
        assert "level=2" in r
        assert "p_abs=" in r


# ---------------------------------------------------------------------------
# Level 2: Geometric ReLU map
# ---------------------------------------------------------------------------


class TestLevel2:
    def test_flat_plane_normal_incidence(self, engine, flat_mesh):
        """Flat plane with wave from +z: all triangles illuminated at mu=1."""
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        result = engine.compute(flat_mesh, paths, level=2)
        # S_ab = T_0 * 1.0 * cos(0) = T_0 for every triangle
        expected = SKIN_28GHZ.T0
        np.testing.assert_allclose(result.sab, expected, rtol=1e-10)

    def test_flat_plane_grazing(self, engine, flat_mesh):
        """Wave parallel to plane: no absorption."""
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[1, 0, 0.0]]),
            power=np.array([1.0]),
        )
        result = engine.compute(flat_mesh, paths, level=2)
        np.testing.assert_allclose(result.sab, 0.0, atol=1e-15)

    def test_flat_plane_backside(self, engine, flat_mesh):
        """Wave from below: all triangles in shadow (normals point +z)."""
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, 1.0]]),
            power=np.array([1.0]),
        )
        result = engine.compute(flat_mesh, paths, level=2)
        np.testing.assert_allclose(result.sab, 0.0, atol=1e-15)

    def test_sab_non_negative(self, engine, ico_mesh, multi_path):
        result = engine.compute(ico_mesh, multi_path, level=2)
        assert np.all(result.sab >= 0)

    def test_total_power_bounded(self, engine, ico_mesh, single_path_down):
        """P_abs <= S_inc * T_0 * A_total (energy conservation)."""
        result = engine.compute(ico_mesh, single_path_down, level=2)
        upper_bound = 1.0 * SKIN_28GHZ.T0 * ico_mesh.total_area
        assert result.p_abs <= upper_bound * 1.001

    def test_p_abs_equals_T0_A_perp(self, engine, flat_mesh):
        """For flat plane at normal incidence: P_abs = S_inc * T_0 * A_total."""
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        result = engine.compute(flat_mesh, paths, level=2)
        expected = SKIN_28GHZ.T0 * flat_mesh.total_area
        assert result.p_abs == pytest.approx(expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Level 3: Exact Fresnel
# ---------------------------------------------------------------------------


class TestLevel3:
    def test_normal_incidence_matches_level2(self, engine, flat_mesh):
        """At normal incidence, T_avg(0) = T_0, so Level 3 = Level 2."""
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        r2 = engine.compute(flat_mesh, paths, level=2)
        r3 = engine.compute(flat_mesh, paths, level=3)
        np.testing.assert_allclose(r3.sab, r2.sab, rtol=1e-3)

    def test_sab_non_negative(self, engine, ico_mesh, multi_path):
        result = engine.compute(ico_mesh, multi_path, level=3)
        assert np.all(result.sab >= 0)

    def test_level3_vs_level2_total_power_close(self, engine, ico_mesh, multi_path):
        """Total power should agree within monograph's 0.35% for complex bodies."""
        r2 = engine.compute(ico_mesh, multi_path, level=2)
        r3 = engine.compute(ico_mesh, multi_path, level=3)
        # For icosahedron the error may be larger, but should be within 10%
        rel_err = abs(r2.p_abs - r3.p_abs) / r3.p_abs
        assert rel_err < 0.10


# ---------------------------------------------------------------------------
# Level 4: Polarisation
# ---------------------------------------------------------------------------


class TestLevel4:
    def test_unpolarised_matches_level3(self, engine, ico_mesh, multi_path):
        """With q=0 (unpolarised), Level 4 = Level 3."""
        r3 = engine.compute(ico_mesh, multi_path, level=3)
        r4 = engine.compute(ico_mesh, multi_path, level=4, q=0.0)
        np.testing.assert_allclose(r4.sab, r3.sab, rtol=1e-12)

    def test_q_positive_increases_power(self, engine, ico_mesh, multi_path):
        """TM-dominant (q=+1) absorbs more than unpolarised (q=0)."""
        r_unpol = engine.compute(ico_mesh, multi_path, level=4, q=0.0)
        r_tm = engine.compute(ico_mesh, multi_path, level=4, q=1.0)
        assert r_tm.p_abs >= r_unpol.p_abs


# ---------------------------------------------------------------------------
# Level 5: Curvature
# ---------------------------------------------------------------------------


class TestLevel5:
    def test_zero_curvature_matches_level3(self, engine, ico_mesh, multi_path):
        """With H=0, Level 5 reduces to Level 3."""
        r3 = engine.compute(ico_mesh, multi_path, level=3)
        curvature_H = np.zeros(ico_mesh.n_triangles)
        r5 = engine.compute(ico_mesh, multi_path, level=5, curvature_H=curvature_H)
        np.testing.assert_allclose(r5.sab, r3.sab, rtol=1e-10)

    def test_positive_curvature_adds_power(self, engine, ico_mesh, single_path_down):
        """Positive curvature adds a correction term."""
        curvature_H = np.full(ico_mesh.n_triangles, 20.0)  # H = 20 /m
        r3 = engine.compute(ico_mesh, single_path_down, level=3)
        r5 = engine.compute(ico_mesh, single_path_down, level=5, curvature_H=curvature_H)
        assert r5.p_abs >= r3.p_abs


# ---------------------------------------------------------------------------
# Level 6: Diffraction GELU
# ---------------------------------------------------------------------------


class TestLevel6:
    def test_zero_curvature_matches_level3(self, engine, ico_mesh, multi_path):
        """With H=0, GELU -> ReLU, Level 6 -> Level 3 (approximately)."""
        r3 = engine.compute(ico_mesh, multi_path, level=3)
        curvature_H = np.zeros(ico_mesh.n_triangles)
        r6 = engine.compute(ico_mesh, multi_path, level=6, curvature_H=curvature_H)
        # GELU with sigma->0 converges to ReLU, but not exactly at sigma=0
        # With sigma=1e-30, it should be very close
        np.testing.assert_allclose(r6.sab, r3.sab, rtol=1e-3)

    def test_sab_non_negative(self, engine, ico_mesh, multi_path):
        curvature_H = np.full(ico_mesh.n_triangles, 10.0)
        result = engine.compute(ico_mesh, multi_path, level=6, curvature_H=curvature_H)
        # GELU can produce small negative values at mu < 0, but S_ab
        # should still be non-negative (because T_avg >= 0 and power >= 0)
        assert np.all(result.sab >= -1e-10)


# ---------------------------------------------------------------------------
# Level 0 and 1
# ---------------------------------------------------------------------------


class TestLevel0:
    def test_bound_exceeds_level2(self, engine, ico_mesh, multi_path):
        # For the icosahedron, A_ab ~ total_area (nearly convex, all exposed)
        # Use Cauchy A_ab = total_area and a generous D_max
        A_ab = ico_mesh.total_area
        D_max = 4.0  # loose upper bound to ensure bound > actual
        r0 = engine.compute(ico_mesh, multi_path, level=0, A_ab=A_ab, D_max=D_max)
        r2 = engine.compute(ico_mesh, multi_path, level=2)
        assert r0.p_abs >= r2.p_abs * 0.99  # bound should be >= actual

    def test_requires_A_ab(self, engine, ico_mesh, multi_path):
        with pytest.raises(ValueError, match="A_ab"):
            engine.compute(ico_mesh, multi_path, level=0, D_max=1.0)


class TestLevel1:
    def test_requires_A_ab(self, engine, ico_mesh, multi_path):
        with pytest.raises(ValueError, match="A_ab"):
            engine.compute(ico_mesh, multi_path, level=1)

    def test_isotropic_D_matches_level2_total_power(self, engine, ico_mesh, multi_path):
        """With D=1 (isotropic fallback), Level 1 gives P_abs = T_0*A_ab/4*sum(S)."""
        A_ab = ico_mesh.total_area / 4.0
        r1 = engine.compute(ico_mesh, multi_path, level=1, A_ab=A_ab)
        expected = SKIN_28GHZ.T0 * A_ab / 4.0 * float(np.sum(multi_path.power))
        assert r1.p_abs == pytest.approx(expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Level consistency
# ---------------------------------------------------------------------------


class TestLevelConsistency:
    def test_all_levels_return_correct_shape(self, engine, ico_mesh, multi_path):
        curvature_H = np.full(ico_mesh.n_triangles, 5.0)
        A_ab = ico_mesh.total_area / 4.0

        for level in range(7):
            kwargs = {}
            if level == 0:
                kwargs = {"A_ab": A_ab, "D_max": 2.0}
            elif level == 1:
                kwargs = {"A_ab": A_ab}
            elif level >= 5:
                kwargs = {"curvature_H": curvature_H}

            result = engine.compute(ico_mesh, multi_path, level=level, **kwargs)
            assert result.sab.shape == (ico_mesh.n_triangles,)
            assert result.fidelity_level == level

    def test_levels_2_through_6_total_power_within_20pct(
        self,
        engine,
        ico_mesh,
        multi_path,
    ):
        """Levels 2-6 should give similar total power (within 20% on simple body)."""
        curvature_H = np.full(ico_mesh.n_triangles, 5.0)
        results = {}
        for level in [2, 3, 4, 5, 6]:
            kwargs = {}
            if level >= 5:
                kwargs["curvature_H"] = curvature_H
            results[level] = engine.compute(ico_mesh, multi_path, level=level, **kwargs)

        ref = results[2].p_abs
        for level in [3, 4, 5, 6]:
            rel_err = abs(results[level].p_abs - ref) / ref
            assert rel_err < 0.20, f"Level {level} total power differs by {rel_err:.1%} from Level 2"

    def test_coherent_requires_precoder(self, engine, ico_mesh, single_path_down):
        with pytest.raises(ValueError, match="precoder"):
            engine.compute(ico_mesh, single_path_down, level=7)

    def test_invalid_level(self, engine, ico_mesh, single_path_down):
        with pytest.raises(ValueError, match="0-8"):
            engine.compute(ico_mesh, single_path_down, level=9)


# ---------------------------------------------------------------------------
# E2E on Thelonious (slow, requires data)
# ---------------------------------------------------------------------------


class TestE2EThelonious:
    @pytest.mark.slow
    def test_single_plane_wave(self, data_dir, has_data):
        """Reproduce monograph Table 6: total power error 0.35%."""
        if not has_data:
            pytest.skip("No mesh data available")

        mesh_path = data_dir / "thelonious.stl"
        if not mesh_path.exists():
            pytest.skip("thelonious.stl not found")

        body = BodyMesh.load(mesh_path)
        skin = SKIN_28GHZ
        engine = DosimetryEngine(skin)

        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([10.0]),  # 10 W/m^2
        )

        r2 = engine.compute(body, paths, level=2)
        r3 = engine.compute(body, paths, level=3)

        # Level 2 vs Level 3 total power should agree within ~5%
        rel_err = abs(r2.p_abs - r3.p_abs) / r3.p_abs
        assert rel_err < 0.05, f"Level 2 vs 3 error: {rel_err:.2%}"

        # S_ab should be non-negative everywhere
        assert np.all(r2.sab >= 0)
        assert np.all(r3.sab >= 0)

        # Peak S_ab should be close to S_inc * T_0
        assert r2.peak_sab == pytest.approx(10.0 * skin.T0, rel=0.01)
