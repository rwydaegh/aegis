"""The studio channel pack reads transparently in both storage formats."""

import numpy as np

from aegis.viewer.routes.studio._channel import read_g_tilde


class _Npz:
    """Minimal stand-in for an ``np.load`` mapping (has ``.files`` + ``__getitem__``)."""

    def __init__(self, **arrays):
        self._a = arrays

    @property
    def files(self):
        return list(self._a)

    def __getitem__(self, k):
        return self._a[k]


def _sample(seed=0, t=64, m=16):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal((t, 3, m)) + 1j * rng.standard_normal((t, 3, m))).astype(np.complex64)


def test_reads_legacy_complex64_pack():
    g = _sample()
    out = read_g_tilde(_Npz(g_tilde=g, areas=np.ones(g.shape[0], np.float32)))
    assert out.dtype == np.complex64
    np.testing.assert_array_equal(out, g)


def test_reads_float16_pack_and_matches_rounding():
    g = _sample(seed=1)
    re16, im16 = g.real.astype(np.float16), g.imag.astype(np.float16)
    out = read_g_tilde(_Npz(g_tilde_re=re16, g_tilde_im=im16, areas=np.ones(g.shape[0], np.float32)))
    assert out.dtype == np.complex64
    expect = (re16.astype(np.float32) + 1j * im16.astype(np.float32)).astype(np.complex64)
    np.testing.assert_array_equal(out, expect)


def test_float16_pack_preserves_deposited_map_to_1e_4():
    # The served quantity is sum_axis |G x|^2; float16 storage must not move its
    # peak by more than ~1e-4 relative (the headline guarantee of the format).
    g = _sample(seed=2, t=256, m=64)
    fp16 = read_g_tilde(_Npz(g_tilde_re=g.real.astype(np.float16), g_tilde_im=g.imag.astype(np.float16)))
    rng = np.random.default_rng(3)
    x = (rng.standard_normal(64) + 1j * rng.standard_normal(64)).astype(np.complex64)
    x /= np.linalg.norm(x)

    def dep(gg):
        return (np.abs(np.einsum("tim,m->ti", gg, x)) ** 2).sum(axis=1)

    d0, d1 = dep(g), dep(fp16)
    assert abs(d1.max() - d0.max()) / d0.max() < 1e-4
