"""Multi-user MIMO extensions for AEGIS.

Phase 1: antenna arrays, per-element path expansion,
communication channel computation, and the scene data model.

Phase 2a: multi-user precoders (MRT, ZF, MMSE, ZF+exposure-scaling)
and scene orchestration (compute_mimo_scene).

Phase 2b: viewer-facing compute helpers (compute_mrt_precoder,
compute_user_sab, compute_total_exposure).
"""

from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.mimo.channel import compute_channel_vector, dipole_effective_length
from aegis.mimo.compute import (
    build_user_channels,
    compute_mimo_scene,
    compute_mimo_scene_with_bodies,
    compute_mrt_precoder,
    compute_multistream_sab,
    compute_total_exposure,
    compute_user_sab,
)
from aegis.mimo.precoders import compute_precoder, mmse, mrt, zf, zf_exposure
from aegis.mimo.scene import MIMOScene
from aegis.mimo.user import UserConfig, UserState

__all__ = [
    "AntennaArray",
    "MIMOScene",
    "UserConfig",
    "UserState",
    "build_user_channels",
    "compute_channel_vector",
    "compute_mimo_scene",
    "compute_mimo_scene_with_bodies",
    "compute_mrt_precoder",
    "compute_multistream_sab",
    "compute_precoder",
    "compute_total_exposure",
    "compute_user_sab",
    "dipole_effective_length",
    "expand_paths_to_array",
    "mmse",
    "mrt",
    "zf",
    "zf_exposure",
]
