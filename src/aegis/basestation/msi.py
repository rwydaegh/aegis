"""MSI antenna pattern file parser.

MSI is a simple text format used by antenna manufacturers (Kathrein,
Commscope, Huawei, etc.) to distribute radiation pattern data.

Format overview
---------------
- Line 1: antenna name
- Header lines: FREQUENCY (MHz), GAIN (dBi), TILT (degrees), COMMENT ...
- HORIZONTAL 360: followed by 360 rows of ``angle attenuation_dB``
- VERTICAL 360: same format, 360 rows

Vertical-plane convention
-------------------------
The V-plane uses the *boresight* convention by default:

- MSI index 0  = boresight forward (elevation 0)
- MSI index 90 = zenith (elevation +90)
- MSI index 180 = back (elevation 180, below boresight continues)
- MSI index 270 = nadir (elevation -90)

This is detected by checking whether ``v_atten[0] == 0``.  If not, the
convention is reported as ``"zenith"`` (index 0 = zenith).

Elevation remapping (boresight convention)
------------------------------------------
AntennaPattern rows: index 0 = elev -90 (nadir), index 90 = elev 0, index 180 = elev +90 (zenith).

Mapping ``elev_deg`` in -90..+90 to MSI index::

    msi_idx = elev_deg % 360  (integer arithmetic on integer degree grid)

So:
- elev   0 -> MSI   0  (boresight forward)
- elev +90 -> MSI  90  (zenith)
- elev -90 -> MSI 270  (nadir, since -90 % 360 == 270)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.basestation.antenna import AntennaPattern


@dataclass(frozen=True)
class MSIMetadata:
    """Metadata extracted from an MSI file header."""

    name: str
    manufacturer: str
    frequency_mhz: float
    gain_dbi: float
    tilt_deg: float
    source_zip: str
    source_path: str
    vertical_convention: str  # "boresight" or "zenith"


def _parse_frequency(line: str, upper: str) -> float:
    """Parse a ``FREQUENCY`` directive. Returns MHz (nan if malformed)."""
    parts = line.split()
    if len(parts) < 2:
        return float("nan")
    freq_str = parts[1]
    # Handle ranges like "1.88-1.93" by taking the midpoint
    if "-" in freq_str and not freq_str.startswith("-"):
        lo, hi = freq_str.split("-", 1)
        freq_mhz = (float(lo) + float(hi)) / 2
    else:
        freq_mhz = float(freq_str)
    if "GHZ" in upper:
        freq_mhz *= 1000
    return freq_mhz


def _parse_gain(line: str, upper: str) -> float:
    """Parse a ``GAIN`` directive. Handles dBi and dBd (adds 2.15)."""
    parts = line.split()
    is_dbd = "DBD" in upper
    gain_dbi = float("nan")
    for token in reversed(parts[1:]):
        try:
            gain_dbi = float(token)
            break
        except ValueError:
            continue
    if is_dbd and not np.isnan(gain_dbi):
        gain_dbi += 2.15
    return gain_dbi


def _parse_tilt(line: str) -> float:
    parts = line.split()
    if len(parts) < 2:
        return 0.0
    try:
        return float(parts[1])
    except ValueError:
        return 0.0


def _read_pattern_rows(lines: list[str], start: int, count: int, out: np.ndarray) -> int:
    """Read ``count`` angle-attenuation rows into out[0..count]. Returns new line index."""
    i = start
    n = len(lines)
    for j in range(min(count, 360)):
        i += 1
        if i >= n:
            break
        row = lines[i].strip().split()
        if len(row) >= 2:
            out[j] = float(row[1])
    return i


def parse_msi(
    text: str,
    manufacturer: str = "",
    source_zip: str = "",
    source_path: str = "",
) -> tuple[MSIMetadata, np.ndarray, np.ndarray]:
    """Parse MSI text into metadata and H/V attenuation arrays.

    Parameters
    ----------
    text:
        Full MSI file content as a string.
    manufacturer:
        Manufacturer name (not stored in MSI file itself).
    source_zip:
        Name of the zip archive this file came from.
    source_path:
        Path within the zip archive.

    Returns
    -------
    metadata : MSIMetadata
    h_atten : (360,) float array - H-plane attenuation in dB (0 = peak)
    v_atten : (360,) float array - V-plane attenuation in dB (0 = peak)
    """
    lines = text.splitlines()
    if not lines:
        raise ValueError("Empty MSI file")

    name = lines[0].strip()
    frequency_mhz = float("nan")
    gain_dbi = float("nan")
    tilt_deg = 0.0
    h_atten = np.zeros(360, dtype=np.float64)
    v_atten = np.zeros(360, dtype=np.float64)

    i = 1
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        upper = line.upper()

        if upper.startswith("FREQUENCY"):
            frequency_mhz = _parse_frequency(line, upper)
        elif upper.startswith("GAIN"):
            gain_dbi = _parse_gain(line, upper)
        elif upper.startswith("TILT"):
            tilt_deg = _parse_tilt(line)
        elif upper.startswith("HORIZONTAL"):
            parts = line.split()
            count = int(parts[1]) if len(parts) >= 2 else 360
            i = _read_pattern_rows(lines, i, count, h_atten)
        elif upper.startswith("VERTICAL"):
            parts = line.split()
            count = int(parts[1]) if len(parts) >= 2 else 360
            i = _read_pattern_rows(lines, i, count, v_atten)

        i += 1

    vertical_convention = "boresight" if np.isclose(v_atten[0], 0.0, atol=1e-6) else "zenith"

    meta = MSIMetadata(
        name=name,
        manufacturer=manufacturer,
        frequency_mhz=frequency_mhz,
        gain_dbi=gain_dbi,
        tilt_deg=tilt_deg,
        source_zip=source_zip,
        source_path=source_path,
        vertical_convention=vertical_convention,
    )
    return meta, h_atten, v_atten


def msi_to_antenna_pattern(
    h_atten: np.ndarray,
    v_atten: np.ndarray,
    gain_dbi: float,
    vertical_convention: str = "boresight",
) -> AntennaPattern:
    """Reconstruct a 2D AntennaPattern from H/V cuts.

    Uses the separable approximation from 3GPP TR 38.901 Sec 7.3:

    .. code-block:: text

        gain_2d[elev_i, azim_j] = gain_dbi - v_atten_remapped[elev_i] - h_atten[azim_j]

    Parameters
    ----------
    h_atten:
        (360,) H-plane attenuation array from MSI (index 0 = azimuth 0 = forward).
    v_atten:
        (360,) V-plane attenuation array from MSI.
    gain_dbi:
        Peak antenna gain in dBi.
    vertical_convention:
        ``"boresight"`` (MSI index 0 = elevation 0) or ``"zenith"``
        (MSI index 0 = elevation +90).

    Returns
    -------
    AntennaPattern
        Frozen dataclass with ``gain_dbi`` shape (181, 360).
    """
    # ------------------------------------------------------------------
    # Remap V-plane attenuation to AntennaPattern elevation rows
    # ------------------------------------------------------------------
    # AntennaPattern row i corresponds to elevation = -90 + i degrees.
    # For the "boresight" convention:
    #   MSI index = elevation_deg % 360
    #   elev =   0 -> MSI   0  (boresight)
    #   elev = +90 -> MSI  90  (zenith)
    #   elev = -90 -> MSI 270  (nadir, -90 % 360 = 270 in Python)
    #
    # For the "zenith" convention:
    #   MSI index 0 = elevation +90, index 90 = elevation 0, etc.
    #   MSI index = (90 - elevation_deg) % 360

    elev_deg = np.arange(-90, 91, dtype=int)  # -90 .. +90, length 181

    v_msi_idx = elev_deg % 360 if vertical_convention == "boresight" else (90 - elev_deg) % 360

    # v_atten_rows[i] = attenuation at elevation (-90+i)
    v_atten_rows = v_atten[v_msi_idx]  # shape (181,)

    # ------------------------------------------------------------------
    # Build 2D gain matrix via outer sum
    # ------------------------------------------------------------------
    # h_atten is indexed 0..359 where index 0 = azimuth 0 (boresight).
    # AntennaPattern column j = azimuth (-180 + j) degrees.
    # MSI azimuth index = (-180 + j) % 360 = (j + 180) % 360.
    #   col   0 = azim -180 -> MSI 180
    #   col 180 = azim   0  -> MSI   0
    #   col 359 = azim +179 -> MSI 179
    azim_col = np.arange(360, dtype=int)
    h_msi_idx = (azim_col + 180) % 360  # shape (360,)
    h_atten_cols = h_atten[h_msi_idx]  # shape (360,)

    # gain_2d[i, j] = gain_dbi - v_atten_rows[i] - h_atten_cols[j]
    gain_2d = gain_dbi - v_atten_rows[:, np.newaxis] - h_atten_cols[np.newaxis, :]

    return AntennaPattern(gain_dbi=gain_2d, max_gain_dbi=gain_dbi)
