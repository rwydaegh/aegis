"""Per-user data model for multi-user MIMO.

UserConfig is the frozen input (position, phantom, device). UserState
holds the mutable computation cache (body mesh, paths, channel, Q, result).

Design doc: section A2.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.result import DosimetryResult


@dataclass(frozen=True)
class UserConfig:
    """Static per-user setup, sent from the frontend.

    Attributes
    ----------
    user_id : unique identifier (UUID string).
    phantom_name : body phantom ("thelonious", "duke", "eartha", "ella").
    position : (3,) world position of body origin [m].
    orientation : rotation about z-axis [rad].
    device_position : (3,) smartphone position in world coordinates [m].
    device_orientation : (3,) unit vector along UE dipole axis.
    """

    user_id: str
    phantom_name: str
    position: np.ndarray = field(repr=False)
    device_position: np.ndarray = field(repr=False)
    device_orientation: np.ndarray = field(repr=False)
    orientation: float = 0.0

    def __post_init__(self) -> None:
        pos = np.asarray(self.position, dtype=np.float64)
        if pos.shape != (3,):
            raise ValueError(f"position must be (3,), got {pos.shape}")
        object.__setattr__(self, "position", pos)

        dev_pos = np.asarray(self.device_position, dtype=np.float64)
        if dev_pos.shape != (3,):
            raise ValueError(f"device_position must be (3,), got {dev_pos.shape}")
        object.__setattr__(self, "device_position", dev_pos)

        dev_ori = np.asarray(self.device_orientation, dtype=np.float64)
        if dev_ori.shape != (3,):
            raise ValueError(f"device_orientation must be (3,), got {dev_ori.shape}")
        norm = np.linalg.norm(dev_ori)
        if norm < 1e-15:
            raise ValueError("device_orientation must be nonzero")
        object.__setattr__(self, "device_orientation", dev_ori / norm)


@dataclass
class UserState:
    """Mutable per-user computation results.

    Attributes
    ----------
    config : the frozen user configuration.
    body : loaded and positioned BodyMesh, or None.
    paths : per-element PropagationPaths (expanded), or None.
    center_paths : center-of-array paths (before expansion), or None.
    h : (M_ant,) communication channel vector, or None.
    G_tilde : (M_tri, 3, M_ant) body-surface channel, or None.
    Q : (M_ant, M_ant) exposure operator, or None.
    result : DosimetryResult from the engine, or None.
    """

    config: UserConfig
    body: BodyMesh | None = None
    paths: PropagationPaths | None = None
    center_paths: PropagationPaths | None = None
    h: np.ndarray | None = None
    G_tilde: np.ndarray | None = None
    Q: np.ndarray | None = None
    result: DosimetryResult | None = None
