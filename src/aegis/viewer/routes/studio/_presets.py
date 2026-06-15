"""Default scene and capability manifest for the Coherent Exposure Studio."""

from __future__ import annotations

from ._config import available_packs
from ._phantom import known_meshes

# Design-space axes for the studio. Ray packs ship for LOS only at present;
# NLOS is part of the design space but its packs are produced on demand.
_CONDITIONS = ("los", "nlos")
_FREQUENCIES = (8, 10, 12, 15, 20, 28)
_SEEDS = (0, 1, 2, 3, 4, 5)
_ARRAY_SIZES = (8, 16)
_BEAMS = ("mrt", "unfocused", "decohered", "decoy", "worstcase", "ecbf")
_BODY_MAP_QUANTITIES = ("floor", "mrt", "worstcase", "amp")
# Body-map realisation statistic: the single served realisation, or the mean /
# 95th percentile over the LOS seed ensemble (served from the ensemble packs).
_BODY_MAP_STATISTICS = ("single", "mean", "p95")

# At-skin chest focus and air focus in the e11 world frame (Z-up, metres).
_FOCUS_CHEST = (0.923, -0.005, 0.734)


def default_scene() -> dict:
    """The default studio scene the frontend opens with."""
    return {
        "mesh": "thelonious",
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "ue": "dipole",
        "beam": "mrt",
        "focus_mode": "at-skin",
        "focus_xyz": list(_FOCUS_CHEST),
        "frequency_ghz": 10,
        "plane": {
            "orientation": "transverse",
            "normal_xyz": None,
            "extent_m": 0.08,
            "res": 160,
        },
        "fieldQuantity": "S",
        "bodyMapQuantity": "mrt",
        "bodyMapStatistic": "single",
    }


def manifest() -> dict:
    """Capabilities: design-space axes, precomputed packs, and the default scene."""
    return {
        "phantoms": list(known_meshes()) or ["thelonious"],
        "conditions": list(_CONDITIONS),
        "frequencies": list(_FREQUENCIES),
        "seeds": list(_SEEDS),
        "array_sizes": list(_ARRAY_SIZES),
        "beams": list(_BEAMS),
        "body_map_quantities": list(_BODY_MAP_QUANTITIES),
        "body_map_statistics": list(_BODY_MAP_STATISTICS),
        "packs": available_packs(),
        "default_scene": default_scene(),
    }
