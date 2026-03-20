"""Tests for Precoder."""

import numpy as np
import pytest

from aegis.precoder import Precoder


def test_mrt_power_matches_p():
    rng = np.random.default_rng(42)
    h = rng.standard_normal(4) + 1j * rng.standard_normal(4)
    P = 2.5
    precoder = Precoder.mrt(h, P)
    assert precoder.power == pytest.approx(P, rel=1e-10, abs=1e-10)
    assert precoder.x.shape == h.shape


def test_mrt_zero_channel_does_not_crash():
    h = np.zeros(3, dtype=complex)
    P = 1.0
    precoder = Precoder.mrt(h, P)
    assert precoder.power == pytest.approx(P, rel=1e-10, abs=1e-10)
    assert precoder.x.shape == (3,)
    assert precoder.x[0] == pytest.approx(np.sqrt(P), abs=1e-10)
    assert np.all(precoder.x[1:] == 0)


def test_post_init_rejects_2d():
    with pytest.raises(ValueError, match="1D"):
        Precoder(x=np.zeros((2, 2), dtype=complex))
