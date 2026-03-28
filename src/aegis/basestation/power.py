"""EIRP to TX power conversions."""

from __future__ import annotations

import numpy as np


def eirp_to_tx_power_dbm(eirp_dbm: float, gain_dbi: float) -> float:
    """Convert EIRP to transmit power in dBm.

    EIRP = P_tx * G_linear, so P_tx_dBm = EIRP_dBm - Gain_dBi.
    """
    if np.isnan(gain_dbi) or gain_dbi == 0.0:
        return eirp_dbm  # treat as isotropic
    return eirp_dbm - gain_dbi


def eirp_to_tx_power_w(eirp_dbm: float, gain_dbi: float) -> float:
    """Convert EIRP to transmit power in watts."""
    tx_dbm = eirp_to_tx_power_dbm(eirp_dbm, gain_dbi)
    return 10.0 ** ((tx_dbm - 30.0) / 10.0)


def dbm_to_w(dbm: float) -> float:
    """Convert dBm to watts."""
    return 10.0 ** ((dbm - 30.0) / 10.0)


def w_to_dbm(w: float) -> float:
    """Convert watts to dBm."""
    return 10.0 * np.log10(w) + 30.0
