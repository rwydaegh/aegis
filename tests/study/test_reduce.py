import numpy as np
import pytest

from aegis.study.reduce import as_icnirp_fraction, population_cdf, time_average


def test_time_average_is_mean_power():
    series = np.array([1.0, 3.0, 2.0, 2.0])
    assert time_average(series) == 2.0


def test_time_average_empty():
    assert time_average([]) == 0.0


def test_cdf_is_monotone_in_zero_one():
    samples = np.array([0.1, 0.2, 0.05, 0.4])
    x, f = population_cdf(samples)
    assert np.all(np.diff(f) >= 0)
    assert f[0] >= 0
    assert f[-1] <= 1.0 + 1e-9
    assert x[0] <= x[-1]


def test_icnirp_fraction_28ghz_general_public():
    # general public sab_4cm2 = 20 W/m^2 at 28 GHz
    assert abs(as_icnirp_fraction(10.0, freq_hz=28e9) - 0.5) < 1e-12
    assert abs(as_icnirp_fraction(20.0, freq_hz=28e9) - 1.0) < 1e-12


def test_icnirp_fraction_below_6ghz_raises():
    with pytest.raises(ValueError, match="below 6 GHz"):
        as_icnirp_fraction(1.0, freq_hz=3.5e9)
