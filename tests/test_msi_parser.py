"""Tests for MSI antenna pattern parser."""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from aegis.basestation.antenna import AntennaPattern

# ---------------------------------------------------------------------------
# Fixture: synthetic MSI file text
# ---------------------------------------------------------------------------


def _gaussian_atten(angles_deg: np.ndarray, beamwidth_deg: float) -> np.ndarray:
    """Gaussian attenuation (dB) relative to peak, given half-power beamwidth."""
    # At ±beamwidth/2, attenuation = 3 dB  =>  sigma^2 = (bw/2)^2 / (2*ln2)
    sigma2 = (beamwidth_deg / 2.0) ** 2 / (2.0 * np.log(2.0))
    atten = angles_deg**2 / (2.0 * sigma2) * (10.0 / np.log(10.0))  # dB
    return np.clip(atten, 0.0, 40.0)


def _make_msi_text(
    name: str = "TestAntenna Model1",
    frequency_mhz: float = 900.0,
    gain_dbi: float = 12.0,
    h_beamwidth: float = 65.0,
    v_beamwidth: float = 10.0,
) -> str:
    """Generate a synthetic MSI text with Gaussian H and V patterns."""
    h_angles = np.arange(360, dtype=float)
    # Wrap: angles > 180 map to negative angles for Gaussian
    h_wrapped = np.where(h_angles <= 180, h_angles, h_angles - 360)
    h_atten = _gaussian_atten(h_wrapped, h_beamwidth)

    # V-plane: MSI convention index 0 = boresight (elev 0), 90 = zenith, 270 = nadir
    v_angles = np.arange(360, dtype=float)
    v_wrapped = np.where(v_angles <= 180, v_angles, v_angles - 360)
    v_atten = _gaussian_atten(v_wrapped, v_beamwidth)

    lines = [
        name,
        f"FREQUENCY {frequency_mhz}",
        f"GAIN (dBi) {gain_dbi}",
        "TILT ",
        "COMMENT synthetic test pattern",
        "HORIZONTAL 360",
    ]
    for i in range(360):
        lines.append(f"{i}.0 {h_atten[i]:.6f}")
    lines.append("VERTICAL 360")
    for i in range(360):
        lines.append(f"{i}.0 {v_atten[i]:.6f}")
    return "\n".join(lines) + "\n"


MSI_TEXT = _make_msi_text()

# Write the fixture file (used by test_parse_msi_header indirectly)
_FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "test_antenna.msi"
if not _FIXTURE_PATH.exists():
    _FIXTURE_PATH.write_text(MSI_TEXT)


# ---------------------------------------------------------------------------
# Tests: parse_msi
# ---------------------------------------------------------------------------


def test_parse_msi_header():
    """Name, frequency, gain are parsed from header."""
    from aegis.basestation.msi import parse_msi

    meta, h_atten, v_atten = parse_msi(
        MSI_TEXT,
        manufacturer="TestCorp",
        source_zip="test.zip",
        source_path="test_antenna.msi",
    )
    assert meta.name == "TestAntenna Model1"
    assert meta.frequency_mhz == pytest.approx(900.0)
    assert meta.gain_dbi == pytest.approx(12.0)
    assert meta.manufacturer == "TestCorp"
    assert meta.source_zip == "test.zip"
    assert meta.source_path == "test_antenna.msi"


def test_parse_msi_shapes():
    """H and V attenuation arrays are (360,) with expected peak/back values."""
    from aegis.basestation.msi import parse_msi

    _, h_atten, v_atten = parse_msi(MSI_TEXT)
    assert h_atten.shape == (360,)
    assert v_atten.shape == (360,)
    # Index 0 = boresight (peak), attenuation = 0
    assert h_atten[0] == pytest.approx(0.0, abs=1e-6)
    # Index 180 = back lobe, attenuation > 0
    assert h_atten[180] > 0.0


def test_parse_msi_boresight_convention():
    """Vertical convention is detected as 'boresight' when v_atten[0] == 0."""
    from aegis.basestation.msi import parse_msi

    meta, _, v_atten = parse_msi(MSI_TEXT)
    assert meta.vertical_convention == "boresight"
    assert v_atten[0] == pytest.approx(0.0, abs=1e-6)


def test_parse_msi_from_fixture_file():
    """Parse the fixture file on disk and verify it matches in-memory result."""
    from aegis.basestation.msi import parse_msi

    text = _FIXTURE_PATH.read_text()
    meta, h_atten, v_atten = parse_msi(text, manufacturer="FixtureCorp")
    assert meta.name == "TestAntenna Model1"
    assert h_atten.shape == (360,)
    assert v_atten.shape == (360,)


# ---------------------------------------------------------------------------
# Tests: msi_to_antenna_pattern
# ---------------------------------------------------------------------------


def test_msi_to_pattern_shape():
    """Result AntennaPattern has shape (181, 360)."""
    from aegis.basestation.msi import msi_to_antenna_pattern, parse_msi

    _, h_atten, v_atten = parse_msi(MSI_TEXT)
    pattern = msi_to_antenna_pattern(h_atten, v_atten, gain_dbi=12.0)
    assert isinstance(pattern, AntennaPattern)
    assert pattern.gain_dbi.shape == (181, 360)
    assert pattern.max_gain_dbi == pytest.approx(12.0)


def test_msi_to_pattern_boresight():
    """Peak gain appears at elevation=0 (row 90), azimuth=0 (col 180)."""
    from aegis.basestation.msi import msi_to_antenna_pattern, parse_msi

    _, h_atten, v_atten = parse_msi(MSI_TEXT)
    pattern = msi_to_antenna_pattern(h_atten, v_atten, gain_dbi=12.0)

    # Row 90 = elevation 0 (horizontal), col 180 = azimuth 0 (boresight)
    peak_val = pattern.gain_dbi[90, 180]
    assert peak_val == pytest.approx(12.0, abs=0.01)


def test_msi_to_pattern_elevation_mapping():
    """Zenith (row 180) and nadir (row 0) are attenuated vs boresight (row 90)."""
    from aegis.basestation.msi import msi_to_antenna_pattern, parse_msi

    _, h_atten, v_atten = parse_msi(MSI_TEXT)
    pattern = msi_to_antenna_pattern(h_atten, v_atten, gain_dbi=12.0)

    boresight_gain = pattern.gain_dbi[90, 180]  # elev=0, azim=0
    zenith_gain = pattern.gain_dbi[180, 180]  # elev=+90, azim=0
    nadir_gain = pattern.gain_dbi[0, 180]  # elev=-90, azim=0

    assert boresight_gain > zenith_gain, "Boresight should exceed zenith gain"
    assert boresight_gain > nadir_gain, "Boresight should exceed nadir gain"


def test_msi_to_pattern_azimuth_symmetry():
    """Gaussian H-plane pattern is symmetric around boresight azimuth."""
    from aegis.basestation.msi import msi_to_antenna_pattern, parse_msi

    _, h_atten, v_atten = parse_msi(MSI_TEXT)
    pattern = msi_to_antenna_pattern(h_atten, v_atten, gain_dbi=12.0)

    # At elevation 0 (row 90), gain at +10 deg (col 190) == gain at -10 deg (col 170)
    left = pattern.gain_dbi[90, 170]  # azimuth = -10 deg
    right = pattern.gain_dbi[90, 190]  # azimuth = +10 deg
    assert left == pytest.approx(right, abs=0.01)


def test_msi_to_pattern_hpbw():
    """Horizontal 3dB beamwidth is close to the specified 65 degrees."""
    from aegis.basestation.msi import msi_to_antenna_pattern, parse_msi

    _, h_atten, v_atten = parse_msi(MSI_TEXT)
    pattern = msi_to_antenna_pattern(h_atten, v_atten, gain_dbi=12.0)

    # At elevation=0 (row 90), find angles where gain drops by 3 dB
    row = pattern.gain_dbi[90, :]  # shape (360,)
    peak = row[180]  # col 180 = azimuth 0
    half_power = peak - 3.0

    # Search from col 180 rightward for the 3dB point
    found = False
    for offset in range(1, 90):
        if row[180 + offset] <= half_power:
            # Beamwidth ~ 2 * offset degrees (rough)
            assert 55 <= 2 * offset <= 75, f"HPBW = {2 * offset} deg, expected ~65"
            found = True
            break
    assert found, "3dB point not found within 90 degrees"


# ---------------------------------------------------------------------------
# Regression: truncated MSI files and oversized counts
# ---------------------------------------------------------------------------


def test_parse_msi_truncated_file_no_crash():
    """Truncated MSI file (file ends mid-section) must not crash with IndexError."""
    from aegis.basestation.msi import parse_msi

    text = "TruncatedAntenna\nFREQUENCY 900\nGAIN 10.0\nHORIZONTAL 360\n"
    # Only 5 data rows then file ends (no VERTICAL section at all)
    for deg in range(5):
        text += f"{deg} 1.5\n"

    meta, h_atten, v_atten = parse_msi(text)
    assert meta.name == "TruncatedAntenna"
    assert h_atten[0] == pytest.approx(1.5)
    assert h_atten[4] == pytest.approx(1.5)


def test_parse_msi_count_exceeds_360():
    """MSI file declaring >360 rows must not overflow the pre-allocated array."""
    from aegis.basestation.msi import parse_msi

    text = "BigAntenna\nFREQUENCY 2100\nGAIN 15.0\nHORIZONTAL 720\n"
    for deg in range(720):
        text += f"{deg % 360} 3.0\n"
    text += "VERTICAL 360\n"
    for deg in range(360):
        text += f"{deg} 2.0\n"

    meta, h_atten, v_atten = parse_msi(text)
    assert h_atten.shape == (360,)
    assert h_atten[0] == pytest.approx(3.0)
