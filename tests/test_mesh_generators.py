"""Tests for synthetic mesh generators (sphere, cylinder)."""

import numpy as np
import pytest

from aegis.geometry.mesh import BodyMesh


class TestSphere:
    """BodyMesh.sphere() produces a valid closed sphere mesh."""

    def test_returns_body_mesh(self):
        body = BodyMesh.sphere(radius=0.1, n_subdivisions=2)
        assert isinstance(body, BodyMesh)

    def test_name(self):
        body = BodyMesh.sphere(radius=0.1, n_subdivisions=2)
        assert body.name == "sphere"

    def test_triangle_count_grows_with_subdivision(self):
        """Icosphere: 20 * 4^n triangles."""
        b1 = BodyMesh.sphere(radius=0.1, n_subdivisions=1)
        b2 = BodyMesh.sphere(radius=0.1, n_subdivisions=2)
        assert b1.n_triangles == 20 * 4**1
        assert b2.n_triangles == 20 * 4**2

    def test_surface_area_converges_to_4pi_r2(self):
        """At subdivision 3, surface area should be within 1% of 4*pi*r^2."""
        r = 0.15
        body = BodyMesh.sphere(radius=r, n_subdivisions=3)
        expected = 4.0 * np.pi * r**2
        assert body.total_area == pytest.approx(expected, rel=0.01)

    def test_normals_point_outward(self):
        """All normals should point away from the origin (dot with centroid > 0)."""
        body = BodyMesh.sphere(radius=0.1, n_subdivisions=2)
        dots = np.sum(body.normals * body.centroids, axis=1)
        assert np.all(dots > 0)

    def test_vertices_on_sphere(self):
        """All vertices should be at distance r from origin."""
        r = 0.2
        body = BodyMesh.sphere(radius=r, n_subdivisions=2)
        flat_verts = body.vertices.reshape(-1, 3)
        dists = np.linalg.norm(flat_verts, axis=1)
        np.testing.assert_allclose(dists, r, atol=1e-12)

    def test_zero_subdivision_is_icosahedron(self):
        body = BodyMesh.sphere(radius=0.1, n_subdivisions=0)
        assert body.n_triangles == 20

    def test_radius_must_be_positive(self):
        with pytest.raises(ValueError, match="positive"):
            BodyMesh.sphere(radius=0.0)

    def test_subdivision_must_be_nonnegative(self):
        with pytest.raises(ValueError, match="non-negative"):
            BodyMesh.sphere(radius=0.1, n_subdivisions=-1)


class TestCylinder:
    """BodyMesh.cylinder() produces a valid capped cylinder mesh."""

    def test_returns_body_mesh(self):
        body = BodyMesh.cylinder(radius=0.1, height=0.5, n_segments=16)
        assert isinstance(body, BodyMesh)

    def test_name(self):
        body = BodyMesh.cylinder(radius=0.1, height=0.5, n_segments=16)
        assert body.name == "cylinder"

    def test_triangle_count(self):
        """Side: 2*n_segments triangles. Top cap: n_segments. Bottom cap: n_segments.
        Total: 4 * n_segments."""
        n = 16
        body = BodyMesh.cylinder(radius=0.1, height=0.5, n_segments=n)
        assert body.n_triangles == 4 * n

    def test_surface_area_converges(self):
        """With many segments, area should approach 2*pi*r*h + 2*pi*r^2."""
        r, h, n = 0.1, 0.5, 64
        body = BodyMesh.cylinder(radius=r, height=h, n_segments=n)
        expected = 2 * np.pi * r * h + 2 * np.pi * r**2
        assert body.total_area == pytest.approx(expected, rel=0.01)

    def test_normals_point_outward(self):
        """All normals should be unit vectors."""
        body = BodyMesh.cylinder(radius=0.1, height=0.5, n_segments=16)
        norms = np.linalg.norm(body.normals, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-12)

    def test_height_extent(self):
        """Mesh spans from z = -h/2 to z = +h/2."""
        h = 0.4
        body = BodyMesh.cylinder(radius=0.1, height=h, n_segments=16)
        bmin, bmax = body.bounding_box
        assert bmax[2] == pytest.approx(h / 2, abs=1e-10)
        assert bmin[2] == pytest.approx(-h / 2, abs=1e-10)

    def test_radius_must_be_positive(self):
        with pytest.raises(ValueError, match="positive"):
            BodyMesh.cylinder(radius=0.0, height=0.5)

    def test_height_must_be_positive(self):
        with pytest.raises(ValueError, match="positive"):
            BodyMesh.cylinder(radius=0.1, height=0.0)

    def test_cap_normals_point_outward(self):
        """Top cap normals must point +Z, bottom cap normals must point -Z."""
        n = 16
        body = BodyMesh.cylinder(radius=0.1, height=0.5, n_segments=n)
        top_start = 2 * n
        bot_start = 3 * n
        top_normals = body.normals[top_start:bot_start]
        bot_normals = body.normals[bot_start:]
        assert np.all(top_normals[:, 2] > 0.99), "Top cap normals should point +Z"
        assert np.all(bot_normals[:, 2] < -0.99), "Bottom cap normals should point -Z"

    def test_segments_minimum(self):
        with pytest.raises(ValueError, match="at least 3"):
            BodyMesh.cylinder(radius=0.1, height=0.5, n_segments=2)


class TestFromArraysDegenerateTriangles:
    """BodyMesh.from_arrays handles degenerate (zero-area) triangles.

    GLB skinned meshes can produce degenerate triangles when bone transforms
    collapse vertices. The resulting zero normals must not crash the backend.
    """

    def test_zero_normal_does_not_raise(self):
        """A triangle with zero normals should be accepted, not rejected."""
        good_tri = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
        zero_normal = np.array([[0.0, 0.0, 0.0]])
        body = BodyMesh.from_arrays(good_tri, normals=zero_normal)
        # Fallback normal should be a unit vector
        np.testing.assert_allclose(np.linalg.norm(body.normals, axis=1), 1.0)

    def test_degenerate_triangle_computed_normals(self):
        """Degenerate triangle (collinear vertices) with computed normals."""
        degen = np.array([[[0, 0, 0], [1, 0, 0], [2, 0, 0]]], dtype=np.float64)
        body = BodyMesh.from_arrays(degen)
        np.testing.assert_allclose(np.linalg.norm(body.normals, axis=1), 1.0)

    def test_mixed_good_and_degenerate(self):
        """Mix of valid and degenerate triangles preserves valid normals."""
        verts = np.array(
            [
                [[0, 0, 0], [1, 0, 0], [0, 1, 0]],  # valid, normal ~ +Z
                [[0, 0, 0], [1, 0, 0], [2, 0, 0]],  # degenerate
            ],
            dtype=np.float64,
        )
        body = BodyMesh.from_arrays(verts)
        assert body.n_triangles == 2
        # First triangle normal should point +Z
        assert body.normals[0, 2] > 0.99
        # Both must be unit vectors
        np.testing.assert_allclose(np.linalg.norm(body.normals, axis=1), 1.0)
