"""Tests for ICNIRP compliance helpers."""

import math

import pytest

from aegis.compliance import ICNIRP_2020, is_compliant_sab, is_compliant_sar, margin_db, summary_text


def test_is_compliant_sab_threshold() -> None:
    assert is_compliant_sab(9.0) is True
    assert is_compliant_sab(11.0) is False


def test_is_compliant_sar_threshold() -> None:
    assert is_compliant_sar(0.07) is True
    assert is_compliant_sar(0.09) is False


def test_icnirp_2020_constants() -> None:
    assert ICNIRP_2020.sab_peak == 10.0
    assert ICNIRP_2020.sar_wb == 0.08
    assert ICNIRP_2020.averaging_area_cm2 == 4.0


def test_margin_db() -> None:
    assert margin_db(1.0) == pytest.approx(10.0 * math.log10(10.0))
    assert margin_db(10.0) == pytest.approx(0.0)
    assert margin_db(100.0) == pytest.approx(-10.0)
    with pytest.raises(ValueError):
        margin_db(0.0)
    with pytest.raises(ValueError):
        margin_db(-1.0)


def test_summary_text_includes_pass_and_margin() -> None:
    s = summary_text(5.0)
    assert "PASS" in s
    assert "5" in s
    assert "dB" in s

    s_fail = summary_text(15.0)
    assert "FAIL" in s_fail

    s_sar = summary_text(5.0, sar_wb=0.01)
    assert "SAR" in s_sar
    assert "PASS" in s_sar
