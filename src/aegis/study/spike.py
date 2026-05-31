"""Cost-discovery spike (build-order step 1).

Measures wall-clock per slot for the three cost centers on a real city mesh with
one static phantom: the deterministic ray trace, the coherent per-triangle Sab,
and the cheap Q phasor refresh. The measured timings set the temporal cadences
(dt, pose_period, recompute_period), which are TBD in the config until this runs.

The ray trace dominates, so recompute_period (its cadence) is the lever. Run on
real hardware (a GPU node if available):

    python -m aegis.study.spike --config configs/study/ghent_core_v1.yaml
"""

from __future__ import annotations

import argparse
import math
import time


def time_call(fn, n_reps: int = 3) -> float:
    """Mean wall-clock seconds over n_reps calls of a zero-arg thunk."""
    n_reps = max(1, int(n_reps))
    # one warm-up to exclude JIT/compile from the measured mean
    fn()
    t0 = time.perf_counter()
    for _ in range(n_reps):
        fn()
    return (time.perf_counter() - t0) / n_reps


def measure(trace_thunk, sab_thunk, qref_thunk, n_reps: int = 3) -> dict:
    """Time the three per-slot cost centers separately."""
    return {
        "raytrace_s": time_call(trace_thunk, n_reps),
        "dosimetry_s": time_call(sab_thunk, n_reps),
        "q_refresh_s": time_call(qref_thunk, n_reps),
    }


def recommend_cadences(timings: dict, budget_s_per_agent: float, n_slots: int = 60) -> dict:
    """Propose cadences so one agent's ray-trace cost fits the time budget.

    The ray trace fires once per recompute_period; everything else is cheap. The
    recompute count that fits the budget is budget / raytrace_s, so the period is
    n_slots / that count. dt defaults to 1 s; poses refresh with the channel.
    """
    raytrace_s = max(timings["raytrace_s"], 1e-9)
    affordable_recomputes = max(1, int(budget_s_per_agent / raytrace_s))
    recompute_period = max(1, math.ceil(n_slots / affordable_recomputes))
    return {
        "dt_s": 1.0,
        "pose_period": recompute_period,
        "recompute_period": recompute_period,
    }


def _run_real(config_path: str) -> int:  # pragma: no cover - needs mesh + DiffeRT + GPU
    import numpy as np

    from aegis.engine import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.mimo.array_paths import expand_paths_to_array
    from aegis.study.bodies import StaticPhantomPoser
    from aegis.study.channel_det import center_paths, sector_paths
    from aegis.study.city import CityCache
    from aegis.study.config import StudyConfig
    from aegis.study.deployment import build_sites
    from aegis.study.exposure import build_static_gram, per_triangle_sab, refresh_Q
    from aegis.study.precoding import mrt_for_user, user_channel_vector
    from aegis.tissue.dielectric import TissueModel

    cfg = StudyConfig.from_yaml(config_path)
    eq = cfg.deployment.equipment
    freq = eq.freq_hz

    # Build the city (Ghent core) and one sector at a rooftop candidate.
    from pathlib import Path

    city = CityCache.build(51.0536, 3.7253, cfg.cities.radius_m, Path(".cache/spike_city"))
    site_xy = city.candidates[0] if len(city.candidates) else np.array([0.0, 0.0, 15.0])
    sector = build_sites(
        site_xy[None, :],
        cfg.deployment.sectoring.sectors,
        cfg.deployment.sectoring.az_coverage_deg,
        cfg.deployment.sectoring.max_range_m,
        freq,
        eq.array,
        eq.tx_power_dbm,
    )[0].sectors[0]

    # Static phantom standing 50 m from the site.
    stl = Path("data/duke.stl")
    poser = StaticPhantomPoser(BodyMesh.load(stl, name="duke"))
    pos = site_xy[:2] + np.array([50.0, 0.0])
    body = poser.pose(pos, heading_rad=0.0, z_ground=0.0)
    rx = np.array([pos[0], pos[1], 1.1])

    engine = DosimetryEngine(TissueModel.from_database("Skin", freq))
    scene = city.sionna_scene

    def trace():
        return sector_paths(scene, sector, rx, freq, engine="sionna")

    center = center_paths(scene, sector, rx, freq, engine="sionna")
    per_elem = expand_paths_to_array(center, sector.array, freq)
    h = user_channel_vector(per_elem, sector.m_ant)
    precoder = mrt_for_user(h, sector.tx_power_w)
    m_static = build_static_gram(body, center, sector.array, freq)

    def sab():
        return per_triangle_sab(engine, body, per_elem, precoder)

    def qref():
        return refresh_Q(m_static, center.k_hat, np.array([0.1, 0.0, 0.0]), freq)

    timings = measure(trace, sab, qref, n_reps=3)
    cadences = recommend_cadences(timings, budget_s_per_agent=30.0, n_slots=int(cfg.mobility.window_s))
    print("Timings (s/call):", timings)
    print("Recommended cadences:", cadences)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="HPC study cost-discovery spike")
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    return _run_real(args.config)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
