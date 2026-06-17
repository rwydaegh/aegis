"""Default scene and capability manifest for the Coherent Exposure Studio."""

from __future__ import annotations

from ._channel import DEFAULT_UE_IDX
from ._config import available_packs
from ._phantom import known_meshes

# Corridor UE standing positions 0..N_UE-1 (x = -7..+9 m at 2 m spacing in the
# e11 convention). Mirrors scripts/studio_precompute.N_UE; the body stands at
# DEFAULT_UE_IDX (mid-corridor, 14 m) unless the UE slider moves it.
_N_UE = 9

# Design-space axes for the studio. Ray packs ship for LOS only at present;
# NLOS is part of the design space but its packs are produced on demand.
_CONDITIONS = ("los", "nlos")
_FREQUENCIES = (8, 10, 12, 15, 20, 28)
_SEEDS = (0, 1, 2, 3, 4, 5)
_ARRAY_SIZES = (8, 16)
_BEAMS = ("mrt", "unfocused", "decohered", "decoy", "worstcase", "ecbf", "gep")
# UE receive antenna patterns C_R(k). The signal channel projects each path via
# C_R(k_n)^H psi_n (monograph signal branch), so the receive antenna shapes h,
# hence the MRT / ECBF precoder, hence (indirectly) the deposited map. The
# exposure channel G_tilde does NOT contain C_R, so only the live precoder-driven
# quantities respond to this; the static body-map packs are frozen at dipole.
_UE_ANTENNAS = ("isotropic", "vertical", "dipole", "patch")
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
        "beam": "ecbf",
        "focus_mode": "free-space",
        "focus_xyz": list(_FOCUS_CHEST),
        "frequency_ghz": 10,
        "plane": {
            "orientation": "transverse",
            "normal_xyz": None,
            "extent_m": 0.08,
            "res": 160,
        },
        "fieldQuantity": "S",
        # Open on the live, focus-tracking deposited map (applies the live
        # precoder to the field channel) so the body recolours as the beam
        # steers. Static packs are frozen at one focus; the frontend falls back
        # to 'mrt' when the default scene has no field-channel pack.
        "bodyMapQuantity": "deposited",
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
        "ue_antennas": list(_UE_ANTENNAS),
        "body_map_quantities": list(_BODY_MAP_QUANTITIES),
        "body_map_statistics": list(_BODY_MAP_STATISTICS),
        "ue_indices": list(range(_N_UE)),
        "default_ue_idx": DEFAULT_UE_IDX,
        "packs": available_packs(),
        "default_scene": default_scene(),
    }
