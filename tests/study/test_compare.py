"""Det-vs-stoch comparison primitives: the P_LOS blend and the paired error."""

import numpy as np

from aegis.study.compare import blend_Q, paired_db_error


def test_blend_Q_is_convex_and_hermitian():
    rng = np.random.default_rng(0)
    a = rng.standard_normal((4, 4)) + 1j * rng.standard_normal((4, 4))
    q_los = a @ a.conj().T  # Hermitian PSD
    b = rng.standard_normal((4, 4)) + 1j * rng.standard_normal((4, 4))
    q_nlos = b @ b.conj().T
    # endpoints
    np.testing.assert_allclose(blend_Q(q_los, q_nlos, 1.0), q_los, atol=1e-12)
    np.testing.assert_allclose(blend_Q(q_los, q_nlos, 0.0), q_nlos, atol=1e-12)
    # midpoint is the average, and stays Hermitian
    mid = blend_Q(q_los, q_nlos, 0.5)
    np.testing.assert_allclose(mid, 0.5 * (q_los + q_nlos), atol=1e-12)
    np.testing.assert_allclose(mid, mid.conj().T, atol=1e-12)
    # out-of-range p is clamped
    np.testing.assert_allclose(blend_Q(q_los, q_nlos, 2.0), q_los, atol=1e-12)


def test_paired_db_error():
    det = np.array([1e-6, 1e-9, 1e-6])
    # equal -> 0 dB; 10x higher -> +10 dB; 10x lower -> -10 dB
    stoch = np.array([1e-6, 1e-8, 1e-7])
    err = paired_db_error(det, stoch)
    np.testing.assert_allclose(err, [0.0, 10.0, -10.0], atol=1e-9)
    # zero exposure is floored, not NaN/inf
    assert np.isfinite(paired_db_error([0.0], [0.0]))[0]
