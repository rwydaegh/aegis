"""Dump Q matrices and rank profile from a tiny plaza_run smoke.

Used to validate the empirical low-rank claim before plumbing the
Woodbury solver.

Run:
    /home/user/aegis/.venv/bin/python -m JSAC.code.experiments.plaza_run.profile_q
"""

from __future__ import annotations

import logging
import time

import numpy as np

from aegis.tissue.dielectric import TissueModel

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
from .slot_loop import (
    _BodyState,
    _build_M_static,
    _decimate_arrays,
    _q_translate_np,
    _translate_to_world,
    _translation_phasor_np,
)


def main(n_per_side: int = 8, n_bodies: int | None = None, seed: int = 42, n_slot_demo: int = 1) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if n_bodies is None:
        n_bodies = sum(TIER_COUNTS.values())
    print(f"# Profile: M={n_per_side**2} (n_per_side={n_per_side}), B={n_bodies}")

    np_rng = np.random.default_rng(seed + 7919)
    import random as _random

    rng = _random.Random(seed)

    bs_panel = build_bs_panel(freq_hz=FREQ_HZ, tx_power_dbm=30.0, n_per_side=n_per_side)
    walks = discover_walks()
    bodies = assign_bodies(n_bodies, rng, walks)
    pose_streams = load_pose_streams(bodies)
    parametric = smplx_body()

    body_positions = np.zeros((n_slot_demo + 1, n_bodies, 3), dtype=np.float64)
    for b in bodies:
        body_positions[:, b.index, :] = generate_walk_trajectory(b, n_slot_demo + 1, 1.0 / 30.0, np_rng)

    path_gen = make_path_generator(
        "plaza_specular",
        bs_position=bs_panel.position,
        freq_hz=bs_panel.freq_hz,
        tx_power_w=bs_panel.tx_power_w,
        base_seed=seed,
    )

    tissue = TissueModel.from_database("Skin", bs_panel.freq_hz)
    n_tilde = tissue.n_complex
    sigma = float(tissue.sigma)
    array = bs_panel.array
    array_offsets = array.element_positions - array.reference_position

    # Build state for one frame.
    state = [_BodyState() for _ in range(n_bodies)]
    bs_pos = bs_panel.position

    print(f"# Building M_static for {n_bodies} bodies...")
    t0 = time.perf_counter()
    for b in bodies:
        from .paths import PathSpec

        spec = PathSpec(
            bs_position=bs_pos,
            body_target=body_positions[0, b.index].astype(np.float64),
            freq_hz=bs_panel.freq_hz,
            tx_power_w=bs_panel.tx_power_w,
            body_index=b.index,
            slot_index=0,
        )
        state[b.index].last_path_set = path_gen(spec)

        pose_axang, _trans = pose_streams[b.index].frame(0, loop=True)
        betas = pose_streams[b.index].betas
        world_pos = body_positions[0, b.index].astype(np.float64)
        paths_b = state[b.index].last_path_set

        posed_local = parametric.generate(betas=betas[:10], pose=pose_axang[:66], name=f"body{b.index}")
        posed_cents = _translate_to_world(posed_local.centroids, posed_local.vertices, world_pos)
        n_p, c_p, a_p = _decimate_arrays(posed_local.normals, posed_cents, posed_local.areas, 10)
        state[b.index].posed_M_static = _build_M_static(
            n_p, c_p, a_p, paths_b, array, array_offsets, n_tilde, sigma, bs_panel.freq_hz
        )
        state[b.index].posed_centroids_ref = world_pos.copy()
    print(f"# M_static build wall: {time.perf_counter() - t0:.2f} s")

    # Translate to Q at slot 0.
    Q_list: list[np.ndarray] = []
    for b in bodies:
        paths = state[b.index].last_path_set
        world = body_positions[0, b.index].astype(np.float64)
        delta = world - state[b.index].posed_centroids_ref
        phi = _translation_phasor_np(paths.k_hat, delta, bs_panel.freq_hz)
        Q = _q_translate_np(state[b.index].posed_M_static, phi)
        Q_list.append(Q)

    Q_arr = np.stack(Q_list, axis=0)
    print(f"# Q stack shape: {Q_arr.shape}, dtype: {Q_arr.dtype}")

    # Eigenvalue / rank profile.
    M = Q_arr.shape[1]
    print("\n# Per-body singular value decay (Q is Hermitian PSD; eigenvalues = singular values).")
    print("# rank-r relative Frobenius reconstruction error: r=1, 2, 3, 4, 5, 6, 8, 10, 12, M")
    rs = [1, 2, 3, 4, 5, 6, 8, 10, 12, M]
    err_table = np.zeros((n_bodies, len(rs)))
    for u in range(n_bodies):
        Q = 0.5 * (Q_arr[u] + Q_arr[u].conj().T)  # Hermitianize
        evals = np.linalg.eigvalsh(Q)
        evals_sorted = np.sort(np.abs(evals))[::-1]
        total_e2 = float(np.sum(evals_sorted**2))
        for j, r in enumerate(rs):
            r_eff = min(r, M)
            err_table[u, j] = float(np.sum(evals_sorted[r_eff:] ** 2) / max(total_e2, 1e-300))

    print("# rank | median | p90 | p99 | max")
    for j, r in enumerate(rs):
        col = err_table[:, j]
        print(
            f"  r={r:3d}  med={np.median(col):.2e}  p90={np.percentile(col, 90):.2e}  "
            f"p99={np.percentile(col, 99):.2e}  max={np.max(col):.2e}"
        )

    # Save Q for later use.
    out = "JSAC/code/experiments/plaza_run/outputs/profile_q.npz"
    np.savez_compressed(out, Q=Q_arr.astype(np.complex64))
    print(f"# Saved Q stack to {out}")


if __name__ == "__main__":
    import sys

    n_per_side = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    main(n_per_side=n_per_side)
