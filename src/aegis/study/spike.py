"""Cost-discovery spike (build-order step 1).

Measures wall-clock per slot for the cost centers on a real city mesh with one
static phantom: the deterministic ray trace, the static-gram build, the coherent
per-triangle Sab map, and the cheap Q phasor refresh. The measured timings set
the temporal cadences (dt, pose_period, recompute_period), TBD in the config
until this runs.

On a real mesh the coherent dosimetry dominates, not the ray trace. Measured on
the Ghent core (duke phantom, 56k triangles, 64-element panel) on CPU: ray trace
0.12 s, static gram 5.6 s, per-triangle Sab map 105 s, Q refresh 0.007 s. The
per-triangle Sab map is the sole bottleneck. The scalar-exposure path that runs
every slot (Q phasor refresh) and even the channel recompute (gram) are cheap, so
the framerate mechanism holds: only the headline 4 cm^2-peak map is expensive.
The GPU that matters is the one running the coherent kernel (the body channel
einsum over M_triangles x M_ant), not the tracer (Sionna RT is fine on CPU here).
Decoupling the map cadence from the channel cadence, decimating the phantom, or a
GPU are the three levers on that 105 s. Run on a GPU node to set the cadences:

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


def measure(trace_thunk, sab_thunk, qref_thunk, gram_thunk=None, n_reps: int = 3) -> dict:
    """Time the per-slot cost centers separately.

    On a real city mesh the coherent dosimetry (the per-triangle Sab map and the
    static-gram build, both O(M_triangles * M_ant * paths)) dwarfs the ray trace,
    so ``gram_thunk`` is timed when supplied: it, not the trace, gates how often a
    recompute can fire.
    """
    timings = {
        "raytrace_s": time_call(trace_thunk, n_reps),
        "dosimetry_s": time_call(sab_thunk, n_reps),
        "q_refresh_s": time_call(qref_thunk, n_reps),
    }
    if gram_thunk is not None:
        timings["gram_s"] = time_call(gram_thunk, n_reps)
    return timings


def recommend_cadences(timings: dict, budget_s_per_agent: float, n_slots: int = 60) -> dict:
    """Propose cadences so one agent's recompute cost fits the time budget.

    A recompute fires the ray trace, rebuilds the static gram, and materializes
    the per-triangle Sab map (all on the recompute cadence); between recomputes
    only the cheap Q phasor refresh runs every slot. The recompute count that
    fits the budget is the slot budget (net of the per-slot refresh floor)
    divided by the recompute cost, so the period is n_slots / that count. dt
    defaults to 1 s; poses refresh with the channel.
    """
    raytrace_s = max(timings.get("raytrace_s", 0.0), 0.0)
    gram_s = max(timings.get("gram_s", 0.0), 0.0)
    dosimetry_s = max(timings.get("dosimetry_s", 0.0), 0.0)
    qref_s = max(timings.get("q_refresh_s", 0.0), 0.0)

    recompute_cost = max(raytrace_s + gram_s + dosimetry_s, 1e-9)
    available_s = budget_s_per_agent - n_slots * qref_s
    affordable_recomputes = max(1, int(max(available_s, 0.0) / recompute_cost))
    recompute_period = max(1, math.ceil(n_slots / affordable_recomputes))
    return {
        "dt_s": 1.0,
        "pose_period": recompute_period,
        "recompute_period": recompute_period,
    }


def _run_real(config_path: str) -> int:  # pragma: no cover - needs mesh + Sionna RT + network
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

    # Build the city (Ghent core) and the sectors at a rooftop candidate.
    from pathlib import Path

    city = CityCache.build(51.0536, 3.7253, cfg.cities.radius_m, Path(".cache/spike_city"))
    site_xy = city.candidates[0] if len(city.candidates) else np.array([0.0, 0.0, 15.0])
    site = build_sites(
        site_xy[None, :],
        cfg.deployment.sectoring.sectors,
        cfg.deployment.sectoring.az_coverage_deg,
        cfg.deployment.sectoring.max_range_m,
        freq,
        eq.array,
        eq.tx_power_dbm,
    )[0]

    scene = city.sionna_scene

    # Find a receiver the deployment actually illuminates. A blind hardcoded
    # offset lands in a rooftop shadow in a dense core (Ghent: due-east at 50 m
    # traces zero paths), so scan each sector's wedge over a few ranges and
    # azimuth offsets and keep the ground-level point with the most center
    # paths. center_paths feeds the coherent Sab, which needs a non-empty set.
    best = None  # (n_paths, rx, sector, center)
    for sec in site.sectors:
        for rng in (15.0, 30.0, 60.0, 100.0):
            if rng > sec.max_range_m:
                continue
            for daz in (0.0, -30.0, 30.0):
                az = np.deg2rad(sec.boresight_az_deg + daz)
                rx = np.array([sec.position[0] + rng * np.cos(az), sec.position[1] + rng * np.sin(az), 1.1])
                cp = center_paths(scene, sec, rx, freq, engine="sionna")
                n = 0 if cp is None or cp.k_hat is None else int(cp.k_hat.shape[0])
                if best is None or n > best[0]:
                    best = (n, rx, sec, cp)
    if best is None or best[0] == 0:
        raise RuntimeError("no illuminated receiver found in any sector wedge")
    n_paths, rx, sector, center = best
    print(f"chosen rx {rx} via sector az={sector.boresight_az_deg:g} deg, {n_paths} center paths")

    # Static phantom standing at the illuminated receiver.
    stl = Path("data/duke.stl")
    poser = StaticPhantomPoser(BodyMesh.load(stl, name="duke"))
    pos = rx[:2]
    body = poser.pose(pos, heading_rad=0.0, z_ground=0.0)

    engine = DosimetryEngine(TissueModel.from_database("Skin", freq))

    def trace():
        return sector_paths(scene, sector, rx, freq, engine="sionna")

    per_elem = expand_paths_to_array(center, sector.array, freq)
    h = user_channel_vector(per_elem, sector.m_ant)
    precoder = mrt_for_user(h, sector.tx_power_w)
    m_static = build_static_gram(body, center, sector.array, freq)

    def sab():
        return per_triangle_sab(engine, body, per_elem, precoder)

    def gram():
        return build_static_gram(body, center, sector.array, freq)

    def qref():
        return refresh_Q(m_static, center.k_hat, np.array([0.1, 0.0, 0.0]), freq)

    timings = measure(trace, sab, qref, gram_thunk=gram, n_reps=3)
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
