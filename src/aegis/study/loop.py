"""Per-agent serial time loop.

Ties the three cadences together for one walking agent:

- ``pose_period`` slots between full body re-poses (articulation frozen between).
- ``recompute_period`` slots between full body-channel recomputes (the ray-trace
  cadence). Between recomputes, the body's bulk translation is applied by the Q
  translation phasor (cheap per-slot refresh).
- every slot: refresh Q, evaluate this agent's absorbed power under the beams the
  crowd's served users induce that slot, summed over illuminating sectors.

All physics is injected as callables, so the cadence logic and sector summation
are tested without the ray tracer or the dosimetry kernel. The beam a bystander
sees comes from the synchronized crowd (served-user precoders), so it is supplied
per (sector, slot) by the orchestrator rather than computed here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.study.deployment import sectors_illuminating
from aegis.study.exposure import scalar_exposure_w


@dataclass
class Agent:
    trajectory: object  # study.walk.Trajectory
    is_user: bool = False
    z_ground: float = 0.0
    agent_id: int = 0


@dataclass
class AgentResult:
    exposure_w: np.ndarray  # (T,) per-slot absorbed power [W]
    is_user: bool
    agent_id: int
    peak_sab_w_m2: np.ndarray | None = None  # (T,) 4 cm^2-averaged peak S_ab [W/m^2]


@dataclass
class _SectorState:
    m_static: object
    center_k_hat: np.ndarray
    ref_xy: np.ndarray
    center_paths: object = None


def run_agent(
    agent,
    sites,
    pose_period,
    recompute_period,
    *,
    pose_fn,
    channel_fn,
    gram_fn,
    refresh_fn,
    beam_fn,
    sab_fn=None,
) -> AgentResult:
    """Walk one agent and return its per-slot absorbed-power series.

    Parameters
    ----------
    agent : Agent with a trajectory (positions (T,2), headings_rad (T,)).
    sites : list of deployment Site.
    pose_period, recompute_period : cadences in slots (>= 1).
    pose_fn(position_xy, heading_rad, frame_idx, z_ground) -> body
    channel_fn(sector, body, position_xy) -> center_paths for this body
    gram_fn(body, center_paths, sector) -> M_static
    refresh_fn(m_static, center_k_hat, delta_xy) -> Q  (delta_xy is 3-vector)
    beam_fn(sector, t) -> precoder x (M_ant,) for the served-user beam at slot t
    sab_fn(body, sector, x, center_paths) -> peak 4 cm^2-averaged S_ab [W/m^2].
        Optional; evaluated only at recompute frames (the per-triangle map is
        the expensive path). The peak over lit sectors is carried forward
        between recomputes. When None, the density series is left as None.
    """
    positions = np.asarray(agent.trajectory.positions, dtype=float)
    headings = np.asarray(agent.trajectory.headings_rad, dtype=float)
    n_slots = positions.shape[0]
    exposure = np.zeros(n_slots)
    peak_sab = np.zeros(n_slots) if sab_fn is not None else None

    body = None
    states: dict[int, _SectorState] = {}
    last_peak = 0.0

    for t in range(n_slots):
        pos_xy = positions[t]
        pos3 = np.array([pos_xy[0], pos_xy[1], agent.z_ground])

        if body is None or t % pose_period == 0:
            body = pose_fn(pos_xy, headings[t], t, agent.z_ground)
            states.clear()  # geometry changed; stale grams must be rebuilt

        lit = sectors_illuminating(pos3, sites)
        total = 0.0
        recompute_frame = t % recompute_period == 0
        slot_peak = 0.0
        for sector in lit:
            sid = id(sector)
            need = sid not in states or recompute_frame
            if need:
                center_paths = channel_fn(sector, body, pos_xy)
                states[sid] = _SectorState(
                    m_static=gram_fn(body, center_paths, sector),
                    center_k_hat=np.asarray(center_paths.k_hat),
                    ref_xy=pos_xy.copy(),
                    center_paths=center_paths,
                )
            st = states[sid]
            delta = pos_xy - st.ref_xy
            delta3 = np.array([delta[0], delta[1], 0.0])
            Q = refresh_fn(st.m_static, st.center_k_hat, delta3)
            x = beam_fn(sector, t)
            total += scalar_exposure_w(Q, x)
            if sab_fn is not None and need:
                slot_peak = max(slot_peak, float(sab_fn(body, sector, x, st.center_paths)))
        exposure[t] = total
        if peak_sab is not None:
            if recompute_frame and lit:
                last_peak = slot_peak
            peak_sab[t] = last_peak

    return AgentResult(
        exposure_w=exposure,
        is_user=agent.is_user,
        agent_id=agent.agent_id,
        peak_sab_w_m2=peak_sab,
    )
