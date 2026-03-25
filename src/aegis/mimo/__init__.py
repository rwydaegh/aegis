"""Multi-user MIMO extensions for AEGIS.

Phase 1: antenna arrays, per-element path expansion, communication channels,
and the scene data model. Phase 2a: precoders and orchestration.
"""

from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.mimo.channel import compute_channel_vector, dipole_effective_length
from aegis.mimo.compute import MIMOResult, compute_mimo_scene, compute_per_user_channels
from aegis.mimo.precoders import PrecoderMatrix, mmse, mrt, zf, zf_exposure_scaled
from aegis.mimo.scene import MIMOScene
from aegis.mimo.user import UserConfig, UserState

__all__ = [
    "AntennaArray",
    "MIMOResult",
    "MIMOScene",
    "PrecoderMatrix",
    "UserConfig",
    "UserState",
    "compute_channel_vector",
    "compute_mimo_scene",
    "compute_per_user_channels",
    "dipole_effective_length",
    "expand_paths_to_array",
    "mmse",
    "mrt",
    "zf",
    "zf_exposure_scaled",
]
