"""Tier-C bystander treatment — wraps ``aegis.sensing`` for plaza_run.

Brief 07 picked option (a): the BS runs monostatic ISAC RCS detection, and
detected tier-C bodies are treated as cooperating-with-position-only
(known position, Cauchy worst case on pose). Undetected tier-C bodies fall
through to the occupancy-envelope (regulator-defined) bound.

Operating point and resolution numbers come from
``JSAC/planning/experiments/tier_c_decision/decision.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from aegis.sensing.rcs import detection

# Paper / brief 07 default operating point.
DEFAULT_NF_DB = 6.0
DEFAULT_PFA = 1e-6
DEFAULT_BANDWIDTH_HZ = 400e6
DEFAULT_BODY_RCS_DBSM = 0.0
DEFAULT_CPI_S = 0.010
DEFAULT_OFDM_SYM_RATE_HZ = 60_000.0  # mu=2 NR FR2, ~60 k symbols/s


@dataclass(frozen=True)
class TierCDecision:
    """Per-body verdict at one slot."""

    detected: bool
    snr_db: float
    pd: float
    range_m: float


@dataclass(frozen=True)
class SensingConfig:
    n_per_side: int = 8
    freq_hz: float = 26e9
    bandwidth_hz: float = DEFAULT_BANDWIDTH_HZ
    tx_power_dbm: float = 30.0
    array_gain_db: float = 21.0
    body_rcs_dbsm: float = DEFAULT_BODY_RCS_DBSM
    nf_db: float = DEFAULT_NF_DB
    pfa: float = DEFAULT_PFA
    cpi_s: float = DEFAULT_CPI_S
    ofdm_sym_rate_hz: float = DEFAULT_OFDM_SYM_RATE_HZ
    pd_threshold: float = 0.9


def integration_gain_db(cfg: SensingConfig) -> float:
    n_int = max(1.0, cfg.cpi_s * cfg.ofdm_sym_rate_hz)
    return 10.0 * math.log10(n_int)


def detect_bodies(
    bs_position: np.ndarray,
    body_positions: np.ndarray,
    cfg: SensingConfig,
) -> list[TierCDecision]:
    """Per-body detection verdicts at one slot.

    Parameters
    ----------
    bs_position : (3,) BS phase center [m].
    body_positions : (N, 3) tier-C body positions [m].
    """
    eirp_dbm = cfg.tx_power_dbm + cfg.array_gain_db
    int_gain = integration_gain_db(cfg)
    out: list[TierCDecision] = []
    for r_world in body_positions:
        rng = float(np.linalg.norm(r_world - bs_position))
        rng = max(rng, 1.0)  # avoid R=0 singularity
        res = detection(
            range_m=rng,
            eirp_dbm=eirp_dbm,
            rx_gain_dbi=cfg.array_gain_db,
            freq_hz=cfg.freq_hz,
            bandwidth_hz=cfg.bandwidth_hz,
            rcs_dbsm=cfg.body_rcs_dbsm,
            noise_figure_db=cfg.nf_db,
            integration_gain_db=int_gain,
            pfa=cfg.pfa,
            num_elements_per_side=cfg.n_per_side,
        )
        out.append(
            TierCDecision(
                detected=res.pd >= cfg.pd_threshold,
                snr_db=float(res.snr_integrated_db),
                pd=float(res.pd),
                range_m=float(rng),
            )
        )
    return out
