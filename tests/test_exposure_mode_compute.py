"""Tests for exposure mode applied to user-placed antennas."""
import numpy as np
import pytest

from aegis.basestation.classify import _lookup_tdd
from aegis.viewer.compute import apply_exposure_reduction


def test_theoretical_mode_no_reduction():
    power_dbm = 60.0
    result = apply_exposure_reduction(power_dbm, 3.5e9, 16, "theoretical")
    assert result == power_dbm


def test_actual_max_tdd_reduction():
    power_dbm = 60.0
    result = apply_exposure_reduction(power_dbm, 3.5e9, 16, "actual_max")
    assert result < power_dbm
    is_tdd, dl_ratio = _lookup_tdd("5G", 3500.0)
    assert is_tdd
    assert result == pytest.approx(power_dbm + 10 * np.log10(dl_ratio * 0.32), rel=0.01)


def test_actual_max_fdd_no_tdd_reduction():
    power_dbm = 60.0
    result = apply_exposure_reduction(power_dbm, 2.1e9, 16, "actual_max")
    is_tdd, dl_ratio = _lookup_tdd("5G", 2100.0)
    assert not is_tdd
    assert result == pytest.approx(power_dbm + 10 * np.log10(0.32), rel=0.01)


def test_typical_adds_traffic_load():
    power_dbm = 60.0
    actual_max = apply_exposure_reduction(power_dbm, 3.5e9, 16, "actual_max")
    typical = apply_exposure_reduction(power_dbm, 3.5e9, 16, "typical")
    assert typical == pytest.approx(actual_max + 10 * np.log10(0.5), rel=0.01)


def test_single_element_no_prf():
    power_dbm = 60.0
    result = apply_exposure_reduction(power_dbm, 3.5e9, 1, "actual_max")
    is_tdd, dl_ratio = _lookup_tdd("5G", 3500.0)
    assert result == pytest.approx(power_dbm + 10 * np.log10(dl_ratio), rel=0.01)
