"""Multi-user MIMO extensions for AEGIS.

Phase 1 provides: antenna arrays, per-element path expansion,
communication channel computation, and the scene data model.
"""

from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.mimo.channel import compute_channel_vector, dipole_effective_length
from aegis.mimo.scene import MIMOScene
from aegis.mimo.user import UserConfig, UserState

__all__ = [
    "AntennaArray",
    "MIMOScene",
    "UserConfig",
    "UserState",
    "compute_channel_vector",
    "dipole_effective_length",
    "expand_paths_to_array",
]
