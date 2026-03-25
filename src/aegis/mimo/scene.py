"""MIMOScene: data container for multi-user MIMO scenarios.

Holds the antenna array, user list, and shared configuration.
No compute logic. The orchestrator (Phase 2a, compute.py) operates
on this container. Invalidation tracking deferred to Phase 2b.

Design doc: section A3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.mimo.array import AntennaArray
from aegis.mimo.user import UserState
from aegis.tissue.dielectric import TissueModel


@dataclass
class MIMOScene:
    """Multi-user MIMO scenario.

    Attributes
    ----------
    array : antenna array geometry.
    users : list of per-user state containers.
    freq_hz : carrier frequency [Hz].
    total_power : total transmit power budget P [W].
    tissue : tissue EM model (shared across users for v1), or None.
    """

    array: AntennaArray
    users: list[UserState] = field(default_factory=list)
    freq_hz: float = 28e9
    total_power: float = 1.0
    tissue: TissueModel | None = None

    @property
    def n_users(self) -> int:
        return len(self.users)

    @property
    def user_ids(self) -> list[str]:
        return [u.config.user_id for u in self.users]

    def get_user(self, user_id: str) -> UserState:
        """Retrieve a user by ID. Raises KeyError if not found."""
        for u in self.users:
            if u.config.user_id == user_id:
                return u
        raise KeyError(f"No user with id {user_id!r}")

    def all_Q(self) -> list[np.ndarray]:
        """Return Q matrices for all users.

        Raises ValueError if any user lacks an exposure operator.
        """
        qs = []
        for u in self.users:
            if u.Q is None:
                raise ValueError(f"User {u.config.user_id} has no exposure operator Q")
            qs.append(u.Q)
        return qs

    def all_h(self) -> np.ndarray:
        """Return (K, M_ant) stacked channel matrix H.

        Raises ValueError if any user lacks a channel vector.
        """
        channels = []
        for u in self.users:
            if u.h is None:
                raise ValueError(f"User {u.config.user_id} has no channel vector")
            channels.append(u.h)
        return np.stack(channels, axis=0)
