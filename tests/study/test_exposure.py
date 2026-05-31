import numpy as np

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.study.exposure import (
    build_static_gram,
    combine_sites_power,
    per_triangle_sab,
    refresh_Q,
    scalar_exposure_w,
)
from aegis.tissue.dielectric import TissueModel


def test_scalar_exposure_nonneg_and_real():
    m = 4
    rng = np.random.default_rng(0)
    a = rng.standard_normal((m, m)) + 1j * rng.standard_normal((m, m))
    Q = a.conj().T @ a  # Hermitian PSD
    x = rng.standard_normal(m) + 1j * rng.standard_normal(m)
    p = scalar_exposure_w(Q, x)
    assert isinstance(p, float)
    assert p >= 0


def test_combine_sites_power_sums():
    assert combine_sites_power([1.0, 2.5, 0.5]) == 4.0
    assert combine_sites_power([]) == 0.0


def _tiny_body():
    # two triangles in the z=0 plane facing +z
    v = np.array(
        [
            [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            [[1, 0, 0], [1, 1, 0], [0, 1, 0]],
        ],
        dtype=float,
    )
    return BodyMesh.from_arrays(v, name="tiny")


def _center_paths(n=5, seed=1):
    rng = np.random.default_rng(seed)
    k = rng.standard_normal((n, 3))
    # Force arrival from above so all directions couple to the +z body
    # (n_hat . -k_hat = -k_z > 0). Otherwise only back-facing directions, which
    # the ReLU zeroes, leaving no off-diagonal cross terms to test translation.
    k[:, 2] = -np.abs(k[:, 2]) - 0.3
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    psi = rng.standard_normal((n, 3)) + 1j * rng.standard_normal((n, 3))
    return PropagationPaths(
        k_hat=k,
        psi=psi,
        element_index=np.zeros(n, dtype=int),
        delay=np.zeros(n),
        is_los=np.ones(n, bool),
    )


def test_static_gram_and_refresh_Q_hermitian_psd():
    body = _tiny_body()
    paths = _center_paths()
    array = AntennaArray.upa(
        n_h=2,
        n_v=2,
        d_h=0.005,
        d_v=0.005,
        center=np.array([0.0, -3.0, 2.0]),
        broadside=np.array([0.0, 1.0, 0.0]),
    )
    m_static = build_static_gram(body, paths, array, freq_hz=28e9, n_tilde=2.0 - 1j, sigma=1.0)
    assert m_static.shape == (5, 5, 4, 4)

    Q = refresh_Q(m_static, paths.k_hat, delta_t=np.zeros(3), freq_hz=28e9)
    assert Q.shape == (4, 4)
    # Hermitian
    np.testing.assert_allclose(Q, Q.conj().T, atol=1e-9)
    # PSD: x^H Q x >= 0 for random x
    rng = np.random.default_rng(3)
    for _ in range(5):
        x = rng.standard_normal(4) + 1j * rng.standard_normal(4)
        assert scalar_exposure_w(Q, x) >= -1e-9


def test_translation_changes_Q():
    body = _tiny_body()
    paths = _center_paths()
    array = AntennaArray.upa(
        n_h=2,
        n_v=2,
        d_h=0.005,
        d_v=0.005,
        center=np.array([0.0, -3.0, 2.0]),
        broadside=np.array([0.0, 1.0, 0.0]),
    )
    m_static = build_static_gram(body, paths, array, freq_hz=28e9, n_tilde=2.0 - 1j, sigma=1.0)
    Q0 = refresh_Q(m_static, paths.k_hat, delta_t=np.zeros(3), freq_hz=28e9)
    Q1 = refresh_Q(m_static, paths.k_hat, delta_t=np.array([0.5, 0.0, 0.0]), freq_hz=28e9)
    assert not np.allclose(Q0, Q1)


def test_scalar_Q_matches_per_triangle_map():
    """x^H Q x (scalar route) equals the integrated per-triangle Sab map and the
    engine's own p_abs: two routes to the same absorbed power."""
    body = _tiny_body()
    paths = _center_paths(n=6)
    array = AntennaArray.upa(
        n_h=2,
        n_v=2,
        d_h=0.005,
        d_v=0.005,
        center=np.array([0.0, -3.0, 2.0]),
        broadside=np.array([0.0, 1.0, 0.0]),
    )
    per_elem = expand_paths_to_array(paths, array, 28e9)
    engine = DosimetryEngine(TissueModel.from_database("Skin", 28e9))
    rng = np.random.default_rng(7)
    x = rng.standard_normal(4) + 1j * rng.standard_normal(4)
    precoder = Precoder(x=x)

    result = engine.compute(body, per_elem, level=7, precoder=precoder)
    scalar = scalar_exposure_w(result.Q, x)
    sab = per_triangle_sab(engine, body, per_elem, precoder)
    integrated = float(np.sum(sab * body.areas))

    assert abs(scalar - result.p_abs) < 1e-9
    assert abs(integrated - result.p_abs) < 1e-9
