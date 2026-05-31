import numpy as np

from aegis.paths import PropagationPaths
from aegis.study.precoding import mrt_for_user, user_channel_vector


def _paths(m_ant, per_elem=3, seed=0):
    rng = np.random.default_rng(seed)
    n = m_ant * per_elem
    k_hat = rng.standard_normal((n, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    psi = rng.standard_normal((n, 3)) + 1j * rng.standard_normal((n, 3))
    elem = np.repeat(np.arange(m_ant), per_elem)
    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=elem,
        delay=np.zeros(n),
        is_los=np.ones(n, bool),
    )


def test_channel_vector_length_is_m_ant():
    h = user_channel_vector(_paths(4), m_ant=4)
    assert h.shape == (4,)
    assert np.iscomplexobj(h)


def test_empty_element_gets_zero():
    # only elements 0 and 2 have paths; 1 and 3 must be zero
    n = 2
    psi = np.ones((n, 3), dtype=complex)
    paths = PropagationPaths(
        k_hat=np.tile([1.0, 0, 0], (n, 1)),
        psi=psi,
        element_index=np.array([0, 2]),
        delay=np.zeros(n),
        is_los=np.ones(n, bool),
    )
    h = user_channel_vector(paths, m_ant=4, copol_axis=[1.0, 0.0, 0.0])
    assert h[1] == 0
    assert h[3] == 0
    assert h[0] != 0
    assert h[2] != 0


def test_mrt_points_at_user():
    h = np.array([1 + 0j, 0 + 1j, -1 + 0j, 0 - 1j])
    pre = mrt_for_user(h, power_w=1.0)
    align = np.abs(np.vdot(pre.x, np.conj(h))) / (np.linalg.norm(pre.x) * np.linalg.norm(h))
    assert align > 0.999


def test_mrt_respects_power():
    h = np.array([1 + 0j, 2 - 1j, 0.5 + 0.5j])
    pre = mrt_for_user(h, power_w=4.0)
    assert abs(float(np.vdot(pre.x, pre.x).real) - 4.0) < 1e-9
