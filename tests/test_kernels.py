"""Direct tests for incoherent kernels (levels 0-6)."""

import numpy as np

from aegis.kernels.level0_bound import level0_bound
from aegis.kernels.level1_aggregate import level1_aggregate
from aegis.kernels.level2_geometric import level2_geometric
from aegis.kernels.level3_fresnel import level3_fresnel
from aegis.kernels.level4_polarisation import level4_polarisation
from aegis.kernels.level5_curvature import level5_curvature
from aegis.kernels.level6_diffraction import level6_diffraction
from aegis.tissue.dielectric import SKIN_28GHZ


def _synthetic_incidence(rng: np.random.Generator, m: int, n: int):
    normals = rng.standard_normal((m, 3))
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    k_hat = rng.standard_normal((n, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.05, 1.0, size=n)
    return normals, k_hat, power


def test_level0_bound():
    rng = np.random.default_rng(0)
    n_triangles = 7
    total_area = 1.25
    A_ab = 0.4
    D_max = 1.8
    power = rng.uniform(0.1, 0.5, size=4)
    T0 = 0.55
    sab, p_abs = level0_bound(total_area, A_ab, D_max, power, T0, n_triangles)
    assert sab.shape == (n_triangles,)
    assert np.all(sab >= 0.0)
    assert p_abs > 0.0


def test_level1_aggregate():
    rng = np.random.default_rng(1)
    n_triangles = 6
    total_area = 2.0
    A_ab = 0.3
    _, k_hat, power = _synthetic_incidence(rng, m=5, n=4)
    T0 = 0.5
    sab, p_abs = level1_aggregate(total_area, A_ab, k_hat, power, T0, n_triangles)
    assert sab.shape == (n_triangles,)
    assert np.all(sab >= 0.0)
    assert p_abs >= 0.0


def test_level2_geometric():
    rng = np.random.default_rng(2)
    m, n = 9, 5
    normals, k_hat, power = _synthetic_incidence(rng, m, n)
    T0 = SKIN_28GHZ.T0
    sab = level2_geometric(normals, k_hat, power, T0)
    assert sab.shape == (m,)
    assert np.all(sab >= 0.0)


def test_level3_fresnel():
    rng = np.random.default_rng(3)
    m, n = 8, 4
    normals, k_hat, power = _synthetic_incidence(rng, m, n)
    sab = level3_fresnel(normals, k_hat, power, SKIN_28GHZ.n_complex)
    assert sab.shape == (m,)
    assert np.all(sab >= 0.0)


def test_level4_polarisation():
    rng = np.random.default_rng(4)
    m, n = 8, 4
    normals, k_hat, power = _synthetic_incidence(rng, m, n)
    sab = level4_polarisation(normals, k_hat, power, SKIN_28GHZ.n_complex, q=0.0)
    assert sab.shape == (m,)
    assert np.all(sab >= 0.0)


def test_level5_curvature():
    rng = np.random.default_rng(5)
    m, n = 7, 5
    normals, k_hat, power = _synthetic_incidence(rng, m, n)
    curvature_H = np.abs(rng.standard_normal(m)) * 2.0
    freq_hz = 28e9
    sab = level5_curvature(normals, k_hat, power, SKIN_28GHZ.n_complex, SKIN_28GHZ.T0, curvature_H, freq_hz)
    assert sab.shape == (m,)
    assert np.all(sab >= 0.0)


def test_level6_diffraction():
    rng = np.random.default_rng(6)
    m, n = 6, 4
    normals, k_hat, power = _synthetic_incidence(rng, m, n)
    curvature_H = np.abs(rng.standard_normal(m)) * 1.5 + 0.1
    freq_hz = 28e9
    sab = level6_diffraction(normals, k_hat, power, SKIN_28GHZ.n_complex, SKIN_28GHZ.T0, curvature_H, freq_hz)
    assert sab.shape == (m,)
    assert np.all(sab >= 0.0)
