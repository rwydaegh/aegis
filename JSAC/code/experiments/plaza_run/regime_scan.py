"""Quick scan to find a binding regime where Newton converges.

Iterates over (tx_power_dbm, reference_level_vpm) on a 5-slot smoke run
and reports:
    - precoder wall time (slot_loop p50)
    - fallback rate (% of slots where multibody_ecbf or oracle hit
      min-absorption)
    - average residual vs L_RL when method == multibody-ecbf

Only seeds=42, plaza_specular paths, 8x8.
"""

from __future__ import annotations

import contextlib
import io
import logging
import random
import sys
import time
import warnings

import numpy as np

from .budgets import per_body_budgets
from .paths import make_path_generator
from .scenario import (
    FREQ_HZ,
    TIER_COUNTS,
    assign_bodies,
    build_bs_panel,
    discover_walks,
    generate_walk_trajectory,
    load_pose_streams,
    smplx_body,
)
from .slot_loop import SlotLoopConfig, run_slots
from .tier_c import SensingConfig


def main():
    logging.basicConfig(level=logging.WARNING)

    seed = 42
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed + 7919)
    n_slots = 5
    n_bodies = sum(TIER_COUNTS.values())

    print(f"# Regime scan: seed={seed} n_slots={n_slots} 8x8 plaza_specular")
    print(f"# {'tx_dBm':>6} {'V/m':>6} {'wall_s':>7} {'p_p50_ms':>9} {'%fallback_p':>11} {'%fallback_o':>11}")

    walks = discover_walks()
    bodies = assign_bodies(n_bodies, rng, walks)
    pose_streams = load_pose_streams(bodies)
    parametric = smplx_body()

    body_positions = np.zeros((n_slots, n_bodies, 3), dtype=np.float64)
    for b in bodies:
        body_positions[:, b.index, :] = generate_walk_trajectory(b, n_slots, 1.0 / 30.0, np_rng)

    import os

    n_per_side = int(os.environ.get("AEGIS_NPS", "8"))
    print(f"# n_per_side={n_per_side}")
    sweep = [
        (30.0, 14.57),  # paper §VII.A nominal
        (35.0, 14.57),
        (43.0, 14.57),
        (43.0, 10.0),
        (43.0, 6.0),
        (43.0, 3.0),
        (50.0, 14.57),  # macro 100W
    ]

    for tx_dbm, vpm in sweep:
        bs_panel = build_bs_panel(freq_hz=FREQ_HZ, tx_power_dbm=tx_dbm, n_per_side=n_per_side)
        body_budgets = per_body_budgets(n_bodies, e_lim_vpm=vpm)
        path_gen = make_path_generator(
            "plaza_specular",
            bs_position=bs_panel.position,
            freq_hz=bs_panel.freq_hz,
            tx_power_w=bs_panel.tx_power_w,
            base_seed=seed,
        )
        config = SlotLoopConfig(sensing=SensingConfig())

        t0 = time.perf_counter()
        # Suppress per-call warnings and stdout from inside run_slots.
        with warnings.catch_warnings(), contextlib.redirect_stderr(io.StringIO()):
            warnings.simplefilter("ignore")
            buffers = run_slots(
                n_slots=n_slots,
                bs_panel=bs_panel,
                bodies=bodies,
                pose_streams=pose_streams,
                parametric=parametric,
                body_positions=body_positions,
                body_budgets=body_budgets,
                path_generator=path_gen,
                config=config,
                progress_every=0,
            )
        wall_s = time.perf_counter() - t0

        # Get precoder p50 from cadence_ms[:, 1].
        prec_p50 = float(np.percentile(buffers.cadence_ms[:, 1], 50))
        # Index 3 is multibody_ecbf, 4 is oracle.
        infeas_p_pct = 100.0 * float(buffers.infeasible[:, 3].mean())
        infeas_o_pct = 100.0 * float(buffers.infeasible[:, 4].mean())

        print(
            f"  {tx_dbm:>6.1f} {vpm:>6.2f} {wall_s:>7.2f} {prec_p50:>9.1f} {infeas_p_pct:>11.1f} {infeas_o_pct:>11.1f}"
        )
        sys.stdout.flush()


if __name__ == "__main__":
    main()
