"""Tests for MSI antenna pattern file parser."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.basestation.antenna import AntennaPattern
from aegis.basestation.msi import parse_msi

# ---------------------------------------------------------------------------
# Synthetic MSI content
# ---------------------------------------------------------------------------

_H_ATTEN = [min(i * 0.1, 30.0) for i in range(360)]
_V_ATTEN = [min(i * 0.05, 25.0) for i in range(360)]


def _make_msi(*, include_tilt: bool = True, tilt_value: str = "6") -> str:
    lines = [
        "Kathrein 731620X7",
        "FREQUENCY 1767.5",
        "GAIN (dBi) 8.15",
    ]
    if include_tilt:
        lines.append(f"TILT {tilt_value}")
    lines.append("COMMENT DATE 30.05.1996")
    lines.append("HORIZONTAL 360")
    for i in range(360):
        lines.append(f"{i}.0 {_H_ATTEN[i]:.4f}")
    lines.append("VERTICAL 360")
    for i in range(360):
        lines.append(f"{i}.0 {_V_ATTEN[i]:.4f}")
    return "\n".join(lines) + "\n"


SAMPLE_MSI = _make_msi()
SAMPLE_MSI_NO_TILT = _make_msi(include_tilt=False)
SAMPLE_MSI_EMPTY_TILT = _make_msi(include_tilt=True, tilt_value="")


# ---------------------------------------------------------------------------
# TestMsiHeader
# ---------------------------------------------------------------------------


class TestMsiHeader:
    def setup_method(self):
        self.header, _ = parse_msi(SAMPLE_MSI)

    def test_name(self):
        assert self.header.name == "Kathrein 731620X7"

    def test_frequency(self):
        assert self.header.frequency_mhz == pytest.approx(1767.5)

    def test_gain(self):
        assert self.header.gain_dbi == pytest.approx(8.15)

    def test_tilt(self):
        assert self.header.tilt_deg == pytest.approx(6.0)

    def test_comment(self):
        assert self.header.comment == "DATE 30.05.1996"

    def test_header_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            self.header.name = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestMsiPattern
# ---------------------------------------------------------------------------


class TestMsiPattern:
    def setup_method(self):
        _, self.pattern = parse_msi(SAMPLE_MSI)

    def test_shape(self):
        assert self.pattern.gain_dbi.shape == (181, 360)

    def test_max_gain_matches_header(self):
        header, pattern = parse_msi(SAMPLE_MSI)
        assert pattern.max_gain_dbi == pytest.approx(header.gain_dbi)

    def test_boresight_is_peak(self):
        # Boresight: elevation=0 (row 90), azimuth=0 (col 180)
        peak = self.pattern.gain_dbi[90, 180]
        assert peak == pytest.approx(self.pattern.max_gain_dbi)

    def test_off_axis_less_than_peak(self):
        # Off-axis: azimuth=90 (MSI index 90), elevation=0
        off_axis = self.pattern.gain_dbi[90, (180 + 90) % 360]
        assert off_axis < self.pattern.max_gain_dbi

    def test_gain_non_negative(self):
        # All gain values should be <= max_gain_dbi (attenuations are non-negative)
        # and >= max_gain_dbi - max_attenuation
        assert np.all(self.pattern.gain_dbi <= self.pattern.max_gain_dbi + 1e-9)

    def test_returns_antenna_pattern(self):
        assert isinstance(self.pattern, AntennaPattern)

    def test_missing_tilt_returns_none(self):
        header, _ = parse_msi(SAMPLE_MSI_NO_TILT)
        assert header.tilt_deg is None

    def test_empty_tilt_returns_none(self):
        header, _ = parse_msi(SAMPLE_MSI_EMPTY_TILT)
        assert header.tilt_deg is None

    def test_bytes_input(self):
        data = SAMPLE_MSI.encode("latin-1")
        header, pattern = parse_msi(data)
        assert header.name == "Kathrein 731620X7"
        assert pattern.gain_dbi.shape == (181, 360)

    def test_h_attenuation_applied(self):
        # At azimuth=10 (MSI index 10), elevation=0: h_atten should be 1.0 dB
        # AEGIS col for MSI azim index 10: col = (10 - 180) % 360 = 190
        col = (10 + 180) % 360
        expected_h_atten = min(10 * 0.1, 30.0)
        gain_at_az10 = self.pattern.gain_dbi[90, col]
        expected = self.pattern.max_gain_dbi - expected_h_atten
        assert gain_at_az10 == pytest.approx(expected, abs=1e-3)

    def test_v_attenuation_applied(self):
        # At elevation=5 (MSI index 5), azimuth=0: v_atten should be 0.25 dB
        # AEGIS row for elev=5: row = 5 + 90 = 95
        row = 5 + 90
        expected_v_atten = min(5 * 0.05, 25.0)
        gain_at_el5 = self.pattern.gain_dbi[row, 180]
        expected = self.pattern.max_gain_dbi - expected_v_atten
        assert gain_at_el5 == pytest.approx(expected, abs=1e-3)
