"""EIRP to TX power conversions."""

from __future__ import annotations

import math
from enum import StrEnum

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


class ExposureMode(StrEnum):
    THEORETICAL = "theoretical"
    ACTUAL_MAX = "actual_max"
    TYPICAL = "typical"


def effective_eirp_dbm(bs, exposure, mode):
    """Compute effective EIRP accounting for exposure mode.

    bs: BaseStation (uses bs.eirp_dbm)
    exposure: ExposureConfig
    mode: ExposureMode
    """
    factor = 1.0
    if mode in (ExposureMode.ACTUAL_MAX, ExposureMode.TYPICAL):
        factor *= exposure.tdd_dl_ratio
        factor *= exposure.power_reduction_factor
    if mode == ExposureMode.TYPICAL:
        factor *= exposure.traffic_load_factor
    factor = max(factor, 1e-10)  # prevent log10(0)
    return bs.eirp_dbm + 10 * math.log10(factor)
