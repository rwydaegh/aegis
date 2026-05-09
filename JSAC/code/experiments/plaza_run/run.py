"""Plaza run entrypoint.

Usage::

    python -m JSAC.code.experiments.plaza_run.run --seed 42
    python -m JSAC.code.experiments.plaza_run.run --config configs/mmwave_aggressive_2007.json

See ``--help`` for the full flag set. NPZ + run.json land under ``outputs/``.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from pathlib import Path

import numpy as np

from .budgets import BRUSSELS_E_LIM_VPM, per_body_budgets
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
        "--reference-level-vpm",
        type=float,
        default=BRUSSELS_E_LIM_VPM,
        help="ICNIRP-style reference level in V/m used to derive L_RL via paper §IV.D. "
        "14.57 = current Brussels (2024 arrete); 6 = post-2014 / Italy attention (large urban); "
        "3 = pre-2014 Brussels / Italy attention (small urban).",
    )
    p.add_argument(
        "--n-array-per-side",
        type=int,
        default=8,
        help="UPA elements per side (square panel). 8 = paper default 8x8 = 64 elements; 16 = 16x16 = 256.",
    )
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a JSON config that overrides flag defaults. CLI flags take precedence.",
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
    p.add_argument(
        "--solver-backend",
        choices=["numpy", "jax"],
        default="numpy",
        help="ECBF inner solver kernel backend. 'jax' offloads the Newton "
        "step + FD Jacobian to GPU (~14x at M=64, ~14x at M=256).",
    )
    p.add_argument(
        "--use-wmmse",
        action="store_true",
        help="Replace the unweighted MMSE-with-exposure inner solve with the "
        "WMMSE outer + dual-Newton inner. The proposed and oracle precoders "
        "both pick this up; baselines (MRT, ZF, WC back-off) are unchanged.",
    )
    p.add_argument(
        "--pose-source",
        choices=["oracle", "tpose", "imu"],
        default="oracle",
        help="Pose telemetry source for the proposed precoder's per-body Q. "
        "'oracle' = ground truth from the AMASS stream; 'tpose' = T-pose "
        "Cauchy envelope (same effect as --ablate-pose-telemetry); 'imu' = "
        "virtual-IMU-estimated pose with calibrated bias-drift + white "
        "noise (aegis.geometry.virtual_imu).",
    )
    p.add_argument(
        "--imu-rms-deg",
        type=float,
        default=4.0,
        help="Steady-state per-joint attitude RMS error in degrees for the "
        "virtual-IMU pose model. 4° = consumer smartphone AHRS; 1.5° = "
        "deep-learning-augmented inertial-mocap.",
    )
    args = p.parse_args()
    if args.config is not None:
        with open(args.config) as f:
            cfg = json.load(f)
        # CLI flag overrides config; only fill in fields the user did not pass.
        cfg_to_dest = {
            "tx_power_dbm": "tx_power_dbm",
            "reference_level_vpm": "reference_level_vpm",
            "n_array_per_side": "n_array_per_side",
            "label_suffix": "label_suffix",
        }
        provided = {a.lstrip("-").replace("-", "_") for a in __import__("sys").argv[1:] if a.startswith("--")}
        for cfg_key, dest in cfg_to_dest.items():
            if cfg_key in cfg and dest not in provided:
                setattr(args, dest, cfg[cfg_key])
        args.config_name = cfg.get("name", args.config.stem)
    else:
        args.config_name = ""
    return args


def _run_once(args, paths_mode: str) -> Path:
    """Execute one path-mode pass and write its NPZ + run.json."""
    seed = args.seed
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed + 7919)

    bs_panel = build_bs_panel(
        freq_hz=FREQ_HZ,
        tx_power_dbm=args.tx_power_dbm,
        n_per_side=args.n_array_per_side,
    )
    walks = discover_walks()
    bodies = assign_bodies(args.n_bodies, rng, walks)
    pose_streams = load_pose_streams(bodies)
    parametric = smplx_body()

    pose_streams_imu = None
    if args.pose_source == "imu":
        from dataclasses import replace as _replace

        from aegis.geometry.virtual_imu import IMUNoiseModel, simulate_imu_pose_trajectory

        imu_model = IMUNoiseModel(rms_per_joint_deg=args.imu_rms_deg)
        pose_streams_imu = []
        for b_idx, ps in enumerate(pose_streams):
            est = simulate_imu_pose_trajectory(
                ps.poses, fps=float(ps.fps), noise=imu_model, rng_seed=seed + b_idx + 1
            )
            pose_streams_imu.append(_replace(ps, poses=est))

    body_positions = np.zeros((args.n_slots, args.n_bodies, 3), dtype=np.float64)
    for b in bodies:
        if args.realistic_walks:
            body_positions[:, b.index, :] = generate_flux_trajectory(b, args.n_slots, args.dt_s, np_rng, rng)
        else:
            body_positions[:, b.index, :] = generate_walk_trajectory(b, args.n_slots, args.dt_s, np_rng)

    body_budgets = per_body_budgets(args.n_bodies, e_lim_vpm=args.reference_level_vpm)

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
        solver_backend=args.solver_backend,
        use_wmmse=args.use_wmmse,
        pose_source=args.pose_source,
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
        pose_streams_imu=pose_streams_imu,
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
        reference_level_vpm=args.reference_level_vpm,
        n_per_side=args.n_array_per_side,
        config_name=getattr(args, "config_name", ""),
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
