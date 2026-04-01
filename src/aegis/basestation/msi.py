"""Parser for MSI (Mobile Systems International) antenna pattern files."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

import numpy as np

from aegis.basestation.antenna import AntennaPattern


@dataclass(frozen=True)
class MsiHeader:
    """Parsed header from an MSI antenna pattern file."""

    name: str
    frequency_mhz: float
    gain_dbi: float
    tilt_deg: float | None
    comment: str


def parse_msi(content: str | bytes) -> tuple[MsiHeader, AntennaPattern]:
    """Parse an MSI antenna pattern file.

    Parameters
    ----------
    content : str or bytes
        Raw file content. Bytes are decoded as latin-1.

    Returns
    -------
    header : MsiHeader
    pattern : AntennaPattern
        Shape (181, 360), AEGIS elevation/azimuth convention.
    """
    if isinstance(content, bytes):
        content = content.decode("latin-1")

    lines = content.splitlines()

    # Find keyword line positions
    h_idx = _find_keyword(lines, "HORIZONTAL")
    v_idx = _find_keyword(lines, "VERTICAL")

    header_lines = lines[:h_idx]
    header = _parse_header(header_lines)

    h_expected = int(lines[h_idx].split()[1])
    v_expected = int(lines[v_idx].split()[1])

    h_atten = _parse_section(lines, h_idx, h_expected)
    v_atten = _parse_section(lines, v_idx, v_expected)

    pattern = _build_pattern(h_atten, v_atten, header.gain_dbi)
    return header, pattern


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_keyword(lines: list[str], keyword: str) -> int:
    for i, line in enumerate(lines):
        if line.strip().upper().startswith(keyword):
            return i
    raise ValueError(f"Keyword {keyword!r} not found in MSI file")


def _parse_header(header_lines: list[str]) -> MsiHeader:
    name = header_lines[0].strip() if header_lines else ""
    frequency_mhz: float = float("nan")
    gain_dbi: float = float("nan")
    tilt_deg: float | None = None
    comment: str = ""

    for line in header_lines[1:]:
        upper = line.strip().upper()
        if upper.startswith("FREQUENCY"):
            parts = line.split(None, 1)
            if len(parts) > 1:
                frequency_mhz = float(parts[1])
        elif upper.startswith("GAIN"):
            # e.g. "GAIN (dBi) 8.15"
            tokens = line.split()
            # Last token is the numeric value
            with contextlib.suppress(ValueError, IndexError):
                gain_dbi = float(tokens[-1])
        elif upper.startswith("TILT"):
            parts = line.split(None, 1)
            if len(parts) > 1 and parts[1].strip():
                try:
                    tilt_deg = float(parts[1].strip())
                except ValueError:
                    tilt_deg = None
        elif upper.startswith("COMMENT"):
            parts = line.split(None, 1)
            comment = parts[1].strip() if len(parts) > 1 else ""

    return MsiHeader(
        name=name,
        frequency_mhz=frequency_mhz,
        gain_dbi=gain_dbi,
        tilt_deg=tilt_deg,
        comment=comment,
    )


def _parse_section(lines: list[str], keyword_line: int, expected: int) -> np.ndarray:
    """Parse angle/attenuation pairs after a keyword line.

    Parameters
    ----------
    lines : list of str
    keyword_line : int
        Index of the HORIZONTAL/VERTICAL keyword line.
    expected : int
        Number of pairs expected.

    Returns
    -------
    attenuation : (expected,) float array
        Indexed by MSI angle (0..expected-1 degrees).
    """
    atten = np.zeros(expected, dtype=np.float64)
    start = keyword_line + 1
    for i in range(expected):
        parts = lines[start + i].split()
        atten[i] = float(parts[1])
    return atten


def _build_pattern(
    h_atten_360: np.ndarray,
    v_atten_360: np.ndarray,
    max_gain_dbi: float,
) -> AntennaPattern:
    """Build an AntennaPattern from MSI attenuation vectors.

    MSI azimuth convention: 0 = boresight, increases clockwise.
    AEGIS azimuth: column c maps to azimuth (c - 180) degrees.
    Mapping: AEGIS column c -> MSI index (c + 180) % 360.

    MSI vertical convention: index 0 = horizon, 1..90 = above horizon,
    270..359 = below horizon (i.e. 360+elev for negative elevation).
    AEGIS elevation: row r maps to elevation (r - 90) degrees.
    Mapping: elev >= 0 -> MSI index = elev, elev < 0 -> MSI index = 360 + elev.
    """
    # Build (181,) vertical attenuation in AEGIS elevation order
    v_atten_aegis = np.empty(181, dtype=np.float64)
    for r in range(181):
        elev = r - 90  # -90..+90
        msi_v = elev if elev >= 0 else 360 + elev
        v_atten_aegis[r] = v_atten_360[msi_v]

    # Build (360,) horizontal attenuation in AEGIS azimuth order
    h_atten_aegis = np.empty(360, dtype=np.float64)
    for c in range(360):
        msi_h = (c + 180) % 360
        h_atten_aegis[c] = h_atten_360[msi_h]

    # Outer product reconstruction: gain = max_gain - v_atten - h_atten
    gain_2d = max_gain_dbi - v_atten_aegis[:, np.newaxis] - h_atten_aegis[np.newaxis, :]

    return AntennaPattern(gain_dbi=gain_2d.astype(np.float32), max_gain_dbi=max_gain_dbi)
