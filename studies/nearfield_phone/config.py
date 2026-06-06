"""Shared configuration for the near-field hand-held exposure study.

Collects the phantom masses, tissue density, frequency bands, antenna patterns,
and output paths so the sweep / PoC / reporting scripts agree on everything.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from aegis.geometry.mesh import BodyMesh
from aegis.nearfield.patterns import AntennaPattern3D, load_band_patterns
from aegis.tissue.dielectric import TissueModel

# -- paths ------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[2]  # /home/user/aegis
HOME = REPO.parent  # /home/user
PATTERN_DIR = HOME / "goliat_farfield_results"
DATA_DIR = REPO / "data"

STUDY_DIR = Path(__file__).resolve().parent
OUT_DIR = STUDY_DIR / "out"
FIG_DIR = STUDY_DIR / "report" / "figures"
for _d in (OUT_DIR, FIG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# -- physical constants -----------------------------------------------------

# IT'IS v5 mass density of dry skin (the outermost tissue that sets psSAR10g).
RHO_SKIN = 1109.0  # kg/m^3

# The 8 free-space antenna bands available as measured patterns.
BANDS_MHZ = [700, 835, 1450, 2140, 2450, 3500, 5200, 5800]

# Bands flagged under-converged in the pattern README (off-resonance, <2% eff):
# their pattern SHAPE is usable but absolute efficiency is not. Kept in the sweep
# but flagged so the report can caveat them.
UNRELIABLE_EFFICIENCY_MHZ = {700, 835}

PLACEMENTS = ["front_of_eyes", "by_cheek", "by_belly"]


# -- loaders ----------------------------------------------------------------


def phantom_masses() -> dict[str, float]:
    """Whole-body masses [kg] from data/phantoms.yaml."""
    doc = yaml.safe_load((DATA_DIR / "phantoms.yaml").read_text())
    return {k: float(v["mass_kg"]) for k, v in doc.items() if "mass_kg" in v}


def load_mesh(name: str) -> BodyMesh:
    return BodyMesh.load(DATA_DIR / f"{name}.stl")


def load_patterns() -> dict[int, AntennaPattern3D]:
    return load_band_patterns(PATTERN_DIR)


@dataclass(frozen=True)
class BandTissue:
    freq_mhz: int
    freq_hz: float
    n_tilde: complex
    t0: float
    pattern: AntennaPattern3D


def band_tissues(patterns: dict[int, AntennaPattern3D]) -> dict[int, BandTissue]:
    """Skin tissue model + pattern for every available band."""
    out: dict[int, BandTissue] = {}
    for mhz in BANDS_MHZ:
        if mhz not in patterns:
            continue
        f = mhz * 1e6
        tis = TissueModel.from_database("Skin", f)
        out[mhz] = BandTissue(mhz, f, tis.n_complex, tis.T0, patterns[mhz])
    return out


def random_rotations(n: int, seed: int = 0) -> np.ndarray:
    """``n`` uniformly random 3x3 rotation matrices (Shoemake's method)."""
    rng = np.random.default_rng(seed)
    u1, u2, u3 = rng.random((3, n))
    q = np.stack(
        [
            np.sqrt(1 - u1) * np.sin(2 * np.pi * u2),
            np.sqrt(1 - u1) * np.cos(2 * np.pi * u2),
            np.sqrt(u1) * np.sin(2 * np.pi * u3),
            np.sqrt(u1) * np.cos(2 * np.pi * u3),
        ],
        axis=1,
    )  # (n, 4) quaternions (x, y, z, w)
    x, y, z, w = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    rot = np.empty((n, 3, 3))
    rot[:, 0, 0] = 1 - 2 * (y * y + z * z)
    rot[:, 0, 1] = 2 * (x * y - z * w)
    rot[:, 0, 2] = 2 * (x * z + y * w)
    rot[:, 1, 0] = 2 * (x * y + z * w)
    rot[:, 1, 1] = 1 - 2 * (x * x + z * z)
    rot[:, 1, 2] = 2 * (y * z - x * w)
    rot[:, 2, 0] = 2 * (x * z - y * w)
    rot[:, 2, 1] = 2 * (y * z + x * w)
    rot[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return rot
