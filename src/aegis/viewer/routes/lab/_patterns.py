"""Antenna-pattern catalog for the Exposure Lab near-field source.

Synthetic patterns (isotropic, dipole, patch) are always available and public.
GOLIAT measured bands are appended only when AEGIS_NEARFIELD_PATTERNS points at a
populated results directory. GOLIAT data is never committed.
"""

import os
from pathlib import Path

_SYNTHETIC = [
    {"id": "isotropic", "label": "Isotropic", "freqs_mhz": [], "synthetic": True},
    {"id": "dipole", "label": "Half-wave dipole", "freqs_mhz": [], "synthetic": True},
    {"id": "patch", "label": "Patch (broadside)", "freqs_mhz": [], "synthetic": True},
]

_SYNTHETIC_FREQ_HZ = 3.5e9  # default frequency for the synthetic factories


def _goliat_patterns() -> list[dict]:
    root = os.environ.get("AEGIS_NEARFIELD_PATTERNS")
    if not root or not Path(root).is_dir():
        return []
    from aegis.nearfield.patterns import load_band_patterns

    try:
        bands = load_band_patterns(root)
    except Exception:
        return []
    if not bands:
        return []
    return [
        {
            "id": "goliat",
            "label": "GOLIAT (measured)",
            "freqs_mhz": sorted(bands.keys()),
            "synthetic": False,
        }
    ]


def list_patterns() -> list[dict]:
    """All available pattern descriptors (synthetic always, GOLIAT if env data)."""
    return list(_SYNTHETIC) + _goliat_patterns()


def get_pattern(pattern_id: str, freq_mhz: float | None):
    """Resolve an id (+ optional MHz) to an AntennaPattern3D."""
    from aegis.nearfield.patterns import AntennaPattern3D, load_band_patterns

    f_hz = (freq_mhz * 1e6) if freq_mhz else _SYNTHETIC_FREQ_HZ
    if pattern_id == "isotropic":
        return AntennaPattern3D.isotropic(f_hz)
    if pattern_id == "dipole":
        return AntennaPattern3D.dipole(f_hz)
    if pattern_id == "patch":
        return AntennaPattern3D.patch(f_hz)
    if pattern_id == "goliat":
        root = os.environ.get("AEGIS_NEARFIELD_PATTERNS")
        if not root:
            raise ValueError("GOLIAT patterns not configured")
        bands = load_band_patterns(root)
        if not bands:
            raise ValueError("no GOLIAT bands found")
        key = min(bands, key=lambda k: abs(k - (freq_mhz or 0)))
        return bands[key]
    raise ValueError(f"unknown pattern id {pattern_id!r}")
