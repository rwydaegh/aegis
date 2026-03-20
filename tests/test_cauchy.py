"""Cauchy projected-area consistency tests (convex body sampling)."""

import pytest
from conftest import make_icosahedron

from aegis.geometry.cauchy import cauchy_projected_area, mean_projected_area
from aegis.geometry.projected_area import compute_projected_area, fibonacci_sphere


def test_icosahedron_mean_projected_area_near_cauchy():
    """Spherical icosahedron: mean A_perp over directions ~ A_total / 4."""
    mesh = make_icosahedron()
    k_hat = fibonacci_sphere(4096)
    A_perp = compute_projected_area(mesh.normals, mesh.areas, k_hat)
    cauchy = cauchy_projected_area(mesh.total_area)
    mean_A = mean_projected_area(A_perp)
    assert mean_A == pytest.approx(cauchy, rel=0.03)
