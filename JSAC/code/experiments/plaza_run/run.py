"""Plaza run entrypoint.

Usage::

    python -m JSAC.code.experiments.plaza_run.run --seed 42

See ``--help`` for the full flag set. NPZ + run.json land under ``outputs/``.
"""

from __future__ import annotations

import argparse
import logging
import random
import time
from pathlib import Path

import numpy as np

from .budgets import per_body_budgets
from .outputs import RunMetadata, cadence_summary, write_run
from .paths import make_path_generator
from .scenario import (
    FREQ_HZ,
    TIER_COUNTS,
    assign_bodies,
    build_bs_panel,
    discover_walks,
    generate_flux_trajectory,
    generate_walk_trajectory,
    load_pose_streams,
    smplx_body,
)
from .slot_loop import PRECODER_NAMES, SlotLoopConfig, run_slots
from .tier_c import SensingConfig

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-bodies", type=int, default=sum(TIER_COUNTS.values()))
    p.add_argument(
        "--n-slots",
        type=int,
        default=9000,
        help="5 min × 30 fps. Use ~30 for smoke test.",
    )
    p.add_argument("--dt-s", type=float, default=1.0 / 30.0)
    p.add_argument(
        "--paths",
        choices=["plaza_specular", "uma_los", "sionna_dict", "both"],
        default="both",
    )
    p.add_argument(
        "--phy",
        choices=["shannon", "sionna", "both"],
        default="shannon",
    )
    p.add_argument("--ablate-pose-telemetry", action="store_true")
    p.add_argument("--decim", type=int, default=10, help="SMPL-X mesh stride.")
    p.add_argument("--pose-period", type=int, default=30)
    p.add_argument("--rt-period", type=int, default=30)
    p.add_argument("--noise-power", type=float, default=1e-2)
    p.add_argument("--oracle-noise-power", type=float, default=1e-3)
    p.add_argument(
        "--tx-power-dbm",
        type=float,
        default=30.0,
        help="BS total transmit power in dBm. 30 = 1W (paper §VII.A); 43 = 20W (macro); 46 = 40W.",
    )
    p.add_argument(
        "--budget-multiplier",
        type=float,
        default=1.0,
        help="Per-body L_RL multiplier. <1 tightens (e.g. 0.04 = 1980 3 V/m), >1 relaxes.",
    )
    p.add_argument(
        "--label-suffix",
        type=str,
        default="",
        help="Append to NPZ filename so multiple regimes don't overwrite each other.",
    )
    p.add_argument(
        "--realistic-walks",
        action="store_true",
        help="Use Brussels Grand Place entry/exit street nodes for flux trajectories instead of bounded random walk.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("JSAC/code/experiments/plaza_run/outputs"),
    )
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--progress-every", type=int, default=200)
    return p.parse_args()


def _run_once(args, paths_mode: str) -> Path:
    """Execute one path-mode pass and write its NPZ + run.json."""
    seed = args.seed
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed + 7919)

    bs_panel = build_bs_panel(freq_hz=FREQ_HZ, tx_power_dbm=args.tx_power_dbm)
    walks = discover_walks()
    bodies = assign_bodies(args.n_bodies, rng, walks)
    pose_streams = load_pose_streams(bodies)
    parametric = smplx_body()

    body_positions = np.zeros((args.n_slots, args.n_bodies, 3), dtype=np.float64)
    for b in bodies:
        if args.realistic_walks:
            body_positions[:, b.index, :] = generate_flux_trajectory(b, args.n_slots, args.dt_s, np_rng, rng)
        else:
            body_positions[:, b.index, :] = generate_walk_trajectory(b, args.n_slots, args.dt_s, np_rng)

    body_budgets = per_body_budgets(args.n_bodies) * args.budget_multiplier

    path_gen = make_path_generator(
        paths_mode,
        bs_position=bs_panel.position,
        freq_hz=bs_panel.freq_hz,
        tx_power_w=bs_panel.tx_power_w,
        base_seed=seed,
    )

    config = SlotLoopConfig(
        pose_period=args.pose_period,
        rt_period=args.rt_period,
        decim_stride=args.decim,
        noise_power=args.noise_power,
        oracle_noise_power=args.oracle_noise_power,
        paths_mode=paths_mode,
        ablate_pose_telemetry=args.ablate_pose_telemetry,
        sensing=SensingConfig(),
    )

    logger.info(
        "plaza_run start: seed=%d n_bodies=%d n_slots=%d paths=%s pose_ablate=%s",
        seed,
        args.n_bodies,
        args.n_slots,
        paths_mode,
        args.ablate_pose_telemetry,
    )
    t0 = time.perf_counter()
    buffers = run_slots(
        n_slots=args.n_slots,
        bs_panel=bs_panel,
        bodies=bodies,
        pose_streams=pose_streams,
        parametric=parametric,
        body_positions=body_positions,
        body_budgets=body_budgets,
        path_generator=path_gen,
        config=config,
        progress_every=args.progress_every,
    )
    wall_s = time.perf_counter() - t0

    cadence = cadence_summary(
        buffers.cadence_ms,
        ["q_refresh", "precoder", "rt", "phy"],
    )
    cadence["wall_clock_s"] = wall_s

    tier_arr = np.array([{"A": 0, "B": 1, "C": 2}.get(b.tier, 3) for b in bodies], dtype=np.uint8)

    # paths_mode -> short label for filename
    paths_label = {
        "plaza_specular": "dict",
        "sionna_dict": "dict",
        "uma_los": "uma",
    }.get(paths_mode, paths_mode)

    meta = RunMetadata(
        seed=seed,
        n_bodies=args.n_bodies,
        n_slots=args.n_slots,
        dt_s=args.dt_s,
        freq_hz=bs_panel.freq_hz,
        tx_power_dbm=args.tx_power_dbm,
        phy_mode="shannon",
        pose_mode="ablate" if args.ablate_pose_telemetry else "aware",
        paths_mode=paths_label,
        scene_hash="hand-placed-bs",
        decim=args.decim,
        bs_position=tuple(bs_panel.position.tolist()),
        bs_broadside=tuple(bs_panel.broadside.tolist()),
        n_users_max=int((tier_arr == 0).sum()),
        cadence_ms=cadence,
        notes=f"path_mode_label={paths_mode}",
        label_suffix=args.label_suffix,
        budget_multiplier=args.budget_multiplier,
    )

    npz = write_run(
        args.out_dir,
        meta,
        p_abs=buffers.p_abs,
        sumrate=buffers.sumrate,
        violation=buffers.violation,
        infeasible=buffers.infeasible,
        tier=tier_arr,
        body_positions=buffers.body_positions,
        cadence_ms=buffers.cadence_ms,
        precoder_names=PRECODER_NAMES,
        body_budgets_w=body_budgets,
    )
    logger.info("Wrote %s in %.1f s wall clock", npz, wall_s)
    return npz


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.paths == "both":
        for mode in ("plaza_specular", "uma_los"):
            args.paths = mode
            _run_once(args, mode)
    else:
        _run_once(args, args.paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
