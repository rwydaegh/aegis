"""Per-body absorbed-power budgets — paper §IV.D.

Active per-body cap is ``min(L_RL, L_BR)``:

    L_RL = T0 · S_lim · A_ab · eta_bar           reference-level (Brussels)
    L_BR = w_BR · m_body                          basic-restriction (ICNIRP WB-SAR)

Constants (paper §IV.D, line 660-668):
    Z0      = 377 Ω                              free-space impedance
    S_lim   = 14.57 V/m field -> 0.56 W/m²       Brussels arrêté cumulative
    T0      = 0.4                                mean Fresnel transmissivity
    eta_bar = 0.5                                mean illumination view-factor
    A_ab    = 1.45 m²                            ICRP 89 reference-adult surface
    w_BR    = 0.08 W/kg                          ICNIRP 2020 GP whole-body SAR
    m_body  = 70 kg                              reference adult mass

For these defaults: L_RL ≈ 0.42 W, L_BR = 5.6 W. RL binds first by ≈ 13×.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Z0_OHM = 376.73
T0_MEAN = 0.4
ETA_BAR_MEAN = 0.5
A_AB_M2 = 1.45
W_BR_GP_WPK = 0.08
M_BODY_KG = 70.0
BRUSSELS_E_LIM_VPM = 14.57


@dataclass(frozen=True)
class BodyBudget:
    """Per-body active budget plus its components."""

    l_rl_w: float
    l_br_w: float
    l_active_w: float
    binds_on: str  # "RL" or "BR"


def s_lim_from_e_field(e_lim_vpm: float) -> float:
    """RMS reference-level field [V/m] -> incident power density [W/m²]."""
    return float(e_lim_vpm * e_lim_vpm / Z0_OHM)


def l_rl_w(
    s_lim_wpm2: float = s_lim_from_e_field(BRUSSELS_E_LIM_VPM),
    t0: float = T0_MEAN,
    a_ab_m2: float = A_AB_M2,
    eta_bar: float = ETA_BAR_MEAN,
) -> float:
    """Reference-level absorbed-power budget per paper §IV.D, eq. L_RL."""
    return float(t0 * s_lim_wpm2 * a_ab_m2 * eta_bar)


def l_br_w(
    m_body_kg: float = M_BODY_KG,
    w_br: float = W_BR_GP_WPK,
) -> float:
    """Basic-restriction absorbed-power budget = ICNIRP WB-SAR × body mass."""
    return float(w_br * m_body_kg)


def body_budget(
    *,
    e_lim_vpm: float = BRUSSELS_E_LIM_VPM,
    a_ab_m2: float = A_AB_M2,
    eta_bar: float = ETA_BAR_MEAN,
    m_body_kg: float = M_BODY_KG,
    w_br: float = W_BR_GP_WPK,
    t0: float = T0_MEAN,
) -> BodyBudget:
    """Compute a single body's RL, BR, and active budget."""
    s_lim = s_lim_from_e_field(e_lim_vpm)
    rl = l_rl_w(s_lim, t0=t0, a_ab_m2=a_ab_m2, eta_bar=eta_bar)
    br = l_br_w(m_body_kg=m_body_kg, w_br=w_br)
    if rl < br:
        return BodyBudget(l_rl_w=rl, l_br_w=br, l_active_w=rl, binds_on="RL")
    return BodyBudget(l_rl_w=rl, l_br_w=br, l_active_w=br, binds_on="BR")


def per_body_budgets(
    n_bodies: int,
    *,
    e_lim_vpm: float = BRUSSELS_E_LIM_VPM,
    a_ab_m2: float = A_AB_M2,
    eta_bar: float = ETA_BAR_MEAN,
    m_body_kg: float = M_BODY_KG,
    w_br: float = W_BR_GP_WPK,
    t0: float = T0_MEAN,
) -> np.ndarray:
    """Return ``(n_bodies,)`` active budgets in W. Static across the run."""
    b = body_budget(
        e_lim_vpm=e_lim_vpm,
        a_ab_m2=a_ab_m2,
        eta_bar=eta_bar,
        m_body_kg=m_body_kg,
        w_br=w_br,
        t0=t0,
    )
    return np.full(n_bodies, b.l_active_w, dtype=np.float64)
