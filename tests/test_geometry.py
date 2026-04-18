"""Tests for aegis.geometry modules.

Unit tests use synthetic meshes. Slow tests need the Thelonious STL file.
"""

import numpy as np
import pytest
from conftest import make_cube_mesh, make_icosahedron, make_single_triangle
from scipy import stats

from aegis.geometry.cauchy import cauchy_projected_area, cauchy_relative_error, mean_projected_area
from aegis.geometry.directivity import (
    compute_directivity,
    sh_reconstruction_error,
    spherical_angles_from_k_hat,
)
from aegis.geometry.mesh import BodyMesh, triangle_areas
from aegis.geometry.occlusion import (
    build_bvh,
    cosine_weighted_hemisphere_samples,
    make_tangent_frame,
)
from aegis.geometry.projected_area import compute_projected_area, fibonacci_sphere

# ---------------------------------------------------------------------------
# BodyMesh
# ---------------------------------------------------------------------------


class TestBodyMesh:
    def test_cube_triangle_count(self):
        mesh = make_cube_mesh()
        assert mesh.n_triangles == 12

    def test_cube_total_area(self):
        mesh = make_cube_mesh()
        # Unit cube: 6 faces * 1 m^2 = 6 m^2
        assert mesh.total_area == pytest.approx(6.0, abs=1e-10)

    def test_cube_bounding_box(self):
        mesh = make_cube_mesh()
        bmin, bmax = mesh.bounding_box
        np.testing.assert_allclose(bmin, [-0.5, -0.5, -0.5])
        np.testing.assert_allclose(bmax, [0.5, 0.5, 0.5])

    def test_cube_scale(self):
        mesh = make_cube_mesh()
        # Diagonal of unit cube = sqrt(3)
        assert mesh.scale == pytest.approx(np.sqrt(3), abs=1e-10)

    def test_single_triangle_area(self):
        mesh = make_single_triangle()
        assert mesh.total_area == pytest.approx(0.5, abs=1e-10)


class TestTriangleAreas:
    def test_unit_square_triangle(self):
        verts = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        areas = triangle_areas(verts)
        assert areas[0] == pytest.approx(0.5, abs=1e-10)

    def test_degenerate_triangle(self):
        verts = np.array([[[0, 0, 0], [1, 0, 0], [2, 0, 0]]], dtype=np.float64)
        areas = triangle_areas(verts)
        assert areas[0] == pytest.approx(0.0, abs=1e-10)


# ---------------------------------------------------------------------------
# Fibonacci sphere
# ---------------------------------------------------------------------------


class TestFibonacciSphere:
    def test_unit_vectors(self):
        k = fibonacci_sphere(100)
        norms = np.linalg.norm(k, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-14)

    def test_shape(self):
        k = fibonacci_sphere(50)
        assert k.shape == (50, 3)

    def test_covers_hemisphere(self):
        """z values should span roughly [-1, 1]."""
        k = fibonacci_sphere(1000)
        assert k[:, 2].min() < -0.99
        assert k[:, 2].max() > 0.99

    def test_deterministic(self):
        k1 = fibonacci_sphere(100)
        k2 = fibonacci_sphere(100)
        np.testing.assert_array_equal(k1, k2)

    def test_invalid_n(self):
        with pytest.raises(ValueError, match="n must be positive"):
            fibonacci_sphere(0)

    def test_z_marginal_moments(self):
        """z-coordinate marginal is uniform on [-1, 1] for uniform sphere points."""
        k = fibonacci_sphere(6000)
        z = k[:, 2]
        assert abs(float(np.mean(z))) < 0.04
        expected_std = 1.0 / np.sqrt(3)
        assert abs(float(np.std(z)) - expected_std) < 0.03

    def test_z_marginal_kstest(self):
        k = fibonacci_sphere(8000)
        z = k[:, 2]
        _stat, p = stats.kstest(z, "uniform", args=(-1.0, 2.0))
        assert p > 1e-5


# ---------------------------------------------------------------------------
# Projected area
# ---------------------------------------------------------------------------


class TestProjectedArea:
    def test_cube_along_axis(self):
        """Cube illuminated from +Z: A_perp = 1 m^2 (top face)."""
        mesh = make_cube_mesh()
        k_hat = np.array([[0.0, 0.0, -1.0]])  # wave from +z
        A = compute_projected_area(mesh.normals, mesh.areas, k_hat)
        assert A[0] == pytest.approx(1.0, abs=0.01)

    def test_cube_all_axes(self):
        """Cube projected area is 1.0 along any axis."""
        mesh = make_cube_mesh()
        axes = np.array(
            [
                [1, 0, 0],
                [-1, 0, 0],
                [0, 1, 0],
                [0, -1, 0],
                [0, 0, 1],
                [0, 0, -1],
            ],
            dtype=np.float64,
        )
        # k_hat points *into* the body, so negate the illumination direction
        k_hat = -axes  # wave coming from +axis direction
        A = compute_projected_area(mesh.normals, mesh.areas, k_hat)
        np.testing.assert_allclose(A, 1.0, atol=0.01)

    def test_single_triangle_normal_incidence(self):
        """Triangle illuminated head-on: A_perp = triangle area."""
        mesh = make_single_triangle()
        k_hat = np.array([[0.0, 0.0, -1.0]])
        A = compute_projected_area(mesh.normals, mesh.areas, k_hat)
        assert A[0] == pytest.approx(0.5, abs=1e-10)

    def test_single_triangle_backface(self):
        """Triangle illuminated from behind: A_perp = 0."""
        mesh = make_single_triangle()
        k_hat = np.array([[0.0, 0.0, 1.0]])
        A = compute_projected_area(mesh.normals, mesh.areas, k_hat)
        assert A[0] == pytest.approx(0.0, abs=1e-10)

    def test_nonnegative(self):
        mesh = make_cube_mesh()
        k_hat = fibonacci_sphere(100)
        A = compute_projected_area(mesh.normals, mesh.areas, k_hat)
        assert np.all(A >= 0)


# ---------------------------------------------------------------------------
# Cauchy formula
# ---------------------------------------------------------------------------


class TestCauchy:
    def test_convex_cube(self):
        """For a convex cube, mean(A_perp) should be close to A_total/4."""
        mesh = make_cube_mesh()
        k_hat = fibonacci_sphere(2048)
        A = compute_projected_area(mesh.normals, mesh.areas, k_hat)
        cauchy_val = cauchy_projected_area(mesh.total_area)
        assert cauchy_val == pytest.approx(6.0 / 4.0, abs=1e-10)
        # Mean A_perp for a cube should match Cauchy
        assert mean_projected_area(A) == pytest.approx(cauchy_val, rel=0.02)

    def test_relative_error_small_for_cube(self):
        mesh = make_cube_mesh()
        k_hat = fibonacci_sphere(2048)
        A = compute_projected_area(mesh.normals, mesh.areas, k_hat)
        err = cauchy_relative_error(A, mesh.total_area)
        assert abs(err) < 0.02


# ---------------------------------------------------------------------------
# Directivity
# ---------------------------------------------------------------------------


class TestDirectivity:
    def test_mean_is_one(self):
        A_perp = np.array([1.0, 2.0, 3.0, 4.0])
        D = compute_directivity(A_perp)
        assert np.mean(D) == pytest.approx(1.0, abs=1e-12)

    def test_proportional(self):
        A_perp = np.array([2.0, 4.0])
        D = compute_directivity(A_perp)
        assert D[1] / D[0] == pytest.approx(2.0, abs=1e-12)

    def test_zero_mean_raises(self):
        with pytest.raises(ValueError, match=r"mean\(A_perp\) must be > 0"):
            compute_directivity(np.array([0.0, 0.0]))


class TestSphericalAngles:
    def test_z_axis(self):
        k = np.array([[0, 0, 1]])
        theta, phi = spherical_angles_from_k_hat(k)
        assert theta[0] == pytest.approx(0.0, abs=1e-10)

    def test_neg_z_axis(self):
        k = np.array([[0, 0, -1]])
        theta, phi = spherical_angles_from_k_hat(k)
        assert theta[0] == pytest.approx(np.pi, abs=1e-10)

    def test_x_axis(self):
        k = np.array([[1, 0, 0]])
        theta, phi = spherical_angles_from_k_hat(k)
        assert theta[0] == pytest.approx(np.pi / 2, abs=1e-10)
        assert phi[0] == pytest.approx(0.0, abs=1e-10)


class TestSHFit:
    def test_constant_function(self):
        """A constant function is perfectly captured by L=0."""
        k_hat = fibonacci_sphere(200)
        theta, phi = spherical_angles_from_k_hat(k_hat)
        D = np.ones(len(k_hat))
        result = sh_reconstruction_error(D, theta, phi, L=0)
        assert result["rms"] < 1e-10

    def test_higher_L_reduces_error(self):
        """Higher SH degree should reduce or maintain error."""
        k_hat = fibonacci_sphere(500)
        theta, phi = spherical_angles_from_k_hat(k_hat)
        # Non-trivial function: 1 + 0.3*cos(theta)
        D = 1.0 + 0.3 * np.cos(theta)
        err_0 = sh_reconstruction_error(D, theta, phi, L=0)["rms"]
        err_1 = sh_reconstruction_error(D, theta, phi, L=1)["rms"]
        assert err_1 <= err_0 + 1e-10


# ---------------------------------------------------------------------------
# BVH and tangent frame
# ---------------------------------------------------------------------------


class TestBVH:
    def test_build_bvh_cube(self):
        mesh = make_cube_mesh()
        v0 = mesh.vertices[:, 0]
        v1 = mesh.vertices[:, 1]
        v2 = mesh.vertices[:, 2]
        tri_bmin = np.minimum(np.minimum(v0, v1), v2)
        tri_bmax = np.maximum(np.maximum(v0, v1), v2)
        bvh, tri_order = build_bvh(tri_bmin, tri_bmax, mesh.centroids, max_leaf=4)
        assert bvh["bmin"].shape[0] > 0
        assert len(tri_order) == 12


class TestTangentFrame:
    def test_orthonormal(self):
        n = np.array([0.0, 0.0, 1.0])
        t, b = make_tangent_frame(n)
        assert np.dot(t, b) == pytest.approx(0.0, abs=1e-10)
        assert np.dot(t, n) == pytest.approx(0.0, abs=1e-10)
        assert np.dot(b, n) == pytest.approx(0.0, abs=1e-10)
        assert np.linalg.norm(t) == pytest.approx(1.0, abs=1e-10)
        assert np.linalg.norm(b) == pytest.approx(1.0, abs=1e-10)

    def test_right_handed(self):
        n = np.array([0.0, 1.0, 0.0])
        t, b = make_tangent_frame(n)
        # t x b should equal n
        cross = np.cross(t, b)
        np.testing.assert_allclose(cross, n, atol=1e-10)


class TestCosineHemisphere:
    def test_shape(self):
        rng = np.random.default_rng(42)
        samples = cosine_weighted_hemisphere_samples(100, rng)
        assert samples.shape == (100, 3)

    def test_z_nonnegative(self):
        rng = np.random.default_rng(42)
        samples = cosine_weighted_hemisphere_samples(1000, rng)
        assert np.all(samples[:, 2] >= 0)

    def test_unit_vectors(self):
        rng = np.random.default_rng(42)
        samples = cosine_weighted_hemisphere_samples(1000, rng)
        norms = np.linalg.norm(samples, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-10)


def test_icosahedron_mean_projected_area_near_cauchy():
    """Spherical icosahedron: mean A_perp over directions ~ A_total / 4."""
    mesh = make_icosahedron()
    k_hat = fibonacci_sphere(4096)
    A_perp = compute_projected_area(mesh.normals, mesh.areas, k_hat)
    cauchy = cauchy_projected_area(mesh.total_area)
    mean_A = mean_projected_area(A_perp)
    assert mean_A == pytest.approx(cauchy, rel=0.03)


# ---------------------------------------------------------------------------
# Thelonious STL tests (slow, need mesh data)
# ---------------------------------------------------------------------------


class TestTheloniousMesh:
    @pytest.fixture(autouse=True)
    def _setup(self, data_dir, has_data):
        if not has_data:
            pytest.skip("Mesh data not available")
        self.mesh = BodyMesh.load(data_dir / "thelonious.stl")

    @pytest.mark.slow
    def test_triangle_count(self):
        assert self.mesh.n_triangles == 23826

    @pytest.mark.slow
    def test_normals_unit(self):
        norms = np.linalg.norm(self.mesh.normals, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-6)

    @pytest.mark.slow
    def test_areas_positive(self):
        assert np.all(self.mesh.areas > 0)

    @pytest.mark.slow
    def test_total_area_positive(self):
        assert self.mesh.total_area > 0

    @pytest.mark.slow
    def test_cauchy_identity(self):
        """mean(A_perp) = A_total/4 (Cauchy formula for any closed surface).

        Without ray-traced self-occlusion, this holds exactly.
        The no-occlusion projected area uses sum(a_j * [n_j.(-k)]_+)
        which equals A_total/4 when averaged over all directions.
        """
        k_hat = fibonacci_sphere(2048)
        A = compute_projected_area(self.mesh.normals, self.mesh.areas, k_hat)
        err = cauchy_relative_error(A, self.mesh.total_area)
        assert abs(err) < 0.01

    @pytest.mark.slow
    def test_projected_area_nonnegative(self):
        k_hat = fibonacci_sphere(512)
        A = compute_projected_area(self.mesh.normals, self.mesh.areas, k_hat)
        assert np.all(A >= 0)

    @pytest.mark.slow
    def test_directivity_mean_one(self):
        k_hat = fibonacci_sphere(512)
        A = compute_projected_area(self.mesh.normals, self.mesh.areas, k_hat)
        D = compute_directivity(A)
        assert np.mean(D) == pytest.approx(1.0, abs=1e-12)
