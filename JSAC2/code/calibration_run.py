"""Calibration recovery experiment (v4 §sec:closedloop).

Synthesizes a 'measured' cascaded channel from a perturbed body twin,
fits Tier C and Tier B against it, and measures recovery error vs SNR
and (for Tier B) vs K.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import Body, kirchhoff_h_body
from JSAC2.code.scene_nlos import BSArray, los_path_dict, los_h_at_phone
from JSAC2.code.pose_sweep import make_body
from JSAC2.code.calibration import (
    fit_tier_b,
    fit_tier_c,
    fit_tier_d,
    partition_thelonious_regions,
    per_region_h_body,
    synthesize_perturbed_truth,
)


def _gen_random_unit_perturbation(R: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    g = 1.0 + 0.20 * (rng.standard_normal(R) + 1j * rng.standard_normal(R))
    return g


def run_calibration(*, body_world_centroid, phone_offset_local,
                    scene_loss_db_los=35.0, yaw_deg=0.0, f_c=28e9,
                    bs_height=8.0, label="default"):
    """Run Tier C, Tier B, and Tier D calibration recovery in one geometry.

    The geometry is parametrised so we can run both far-BS (~30m) and
    close-BS (~5m) cases to expose the rank-1 vs rank-many regime."""
    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, bs_height]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=f_c)
    body = make_body(yaw_deg, body_world_centroid)
    r_phone = body_world_centroid + phone_offset_local
    paths = los_path_dict(bs, body.mesh.centroid)
    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=scene_loss_db_los)

    h_pred, extras = kirchhoff_h_body(body, paths, r_phone,
                                       f_c=f_c, M=bs.M, return_per_triangle=True)
    Lambda = extras["Lambda"]
    tri_idx = extras["tri_vis_idx"]

    region_labels = partition_thelonious_regions(
        body.centroids[tri_idx], body.normals[tri_idx]
    )
    R = 6
    h_per_region = per_region_h_body(Lambda, region_labels, R=R)

    h_pred_check = h_per_region.sum(axis=0)
    assert np.allclose(h_pred_check, h_pred, atol=1e-12)

    gamma_true = _gen_random_unit_perturbation(R, seed=0)
    print(f"  [{label}] gamma_true = {gamma_true}")

    # SVD info
    S = np.linalg.svd(Lambda, compute_uv=False)
    spec = (S ** 2)
    spec /= spec.sum()
    K99 = int(np.searchsorted(np.cumsum(spec), 0.99)) + 1
    print(f"  [{label}] Lambda rank cond={S[0]/max(S[-1],1e-30):.2e}, K_99={K99}")

    snr_grid_db = np.array([0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0])
    n_trials = 30

    h_body_perturbed_truth = (gamma_true[:, None] * h_per_region).sum(axis=0)

    err_c = np.zeros((len(snr_grid_db), n_trials))
    err_d = np.zeros((len(snr_grid_db), n_trials))
    K_grid = [1, 2, 4, 8, 16, 32]
    err_b = np.zeros((len(K_grid), len(snr_grid_db), n_trials))

    # Cache the SVD of Lambda once (independent of SNR / trial).
    U_full, S_full, _ = np.linalg.svd(Lambda, full_matrices=False)

    def _fit_tier_b_cached(h_meas, h_los, K):
        K_eff = min(K, len(S_full))
        A = U_full[:, :K_eff]
        y = h_meas - h_los
        Ahy = A.conj().T @ y
        # rho = 0 (overdetermined since K <= M)
        alpha_hat = Ahy
        return A @ alpha_hat

    for i, snr in enumerate(snr_grid_db):
        for t in range(n_trials):
            rng_t = np.random.default_rng(1000 + t * 7 + i)
            h_meas, _ = synthesize_perturbed_truth(
                h_los, h_per_region,
                region_perturbation=gamma_true,
                snr_db=snr, rng=rng_t,
            )
            # Tier D: single scalar
            gamma_d, _ = fit_tier_d(h_meas, h_los, h_pred, rho=1e-12)
            h_pred_d = gamma_d * h_pred
            err_d[i, t] = (np.linalg.norm(h_body_perturbed_truth - h_pred_d)
                           / max(np.linalg.norm(h_body_perturbed_truth), 1e-30))
            # Tier C: per-region (R=6)
            gamma_c, _ = fit_tier_c(h_meas, h_los, h_per_region, rho=1e-12)
            h_pred_c = (gamma_c[:, None] * h_per_region).sum(axis=0)
            err_c[i, t] = (np.linalg.norm(h_body_perturbed_truth - h_pred_c)
                           / max(np.linalg.norm(h_body_perturbed_truth), 1e-30))
            # Tier B: K-mode SVD (using cached SVD)
            for ki, K in enumerate(K_grid):
                h_body_pred = _fit_tier_b_cached(h_meas, h_los, K)
                err_b[ki, i, t] = (np.linalg.norm(h_body_perturbed_truth - h_body_pred)
                                    / max(np.linalg.norm(h_body_perturbed_truth), 1e-30))

    out_dir = Path("/home/user/aegis/JSAC2/code/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_dir / f"calibration_recovery_{label}.npz",
        snr_grid_db=snr_grid_db, K_grid=np.array(K_grid),
        gamma_true=gamma_true,
        err_c=err_c, err_d=err_d, err_b=err_b,
        S=S, K_99=K99,
        body_centroid=body_world_centroid, bs_height=bs_height,
    )
    print(f"  [{label}] Tier D (1 DOF) median err: "
          f"@5dB={np.median(err_d[1]):.3f}, @20dB={np.median(err_d[4]):.3f}, "
          f"@40dB={np.median(err_d[-1]):.3f}")
    print(f"  [{label}] Tier C (6 DOF) median err: "
          f"@5dB={np.median(err_c[1]):.3f}, @20dB={np.median(err_c[4]):.3f}, "
          f"@40dB={np.median(err_c[-1]):.3f}")
    for ki, K in enumerate(K_grid):
        med_low = np.median(err_b[ki][1])
        med_hi = np.median(err_b[ki][-1])
        print(f"  [{label}] Tier B (K={K:2d}) median err: @5dB={med_low:.3f}, @40dB={med_hi:.3f}")


def main():
    phone_offset = np.array([0.55, 0.0, 0.10])

    # Far-BS (30 m): body sub-beamwidth, Lambda is rank-1, only Tier D
    # is identifiable; Tier C is over-parametrised.
    print("=== Far-BS (30 m): rank-1 regime ===")
    run_calibration(
        body_world_centroid=np.array([30.0, 0.0, 1.2]),
        phone_offset_local=phone_offset,
        scene_loss_db_los=35.0, yaw_deg=0.0,
        bs_height=8.0, label="far30m",
    )

    # Close-BS (5 m): body resolved by the array, Tier C identifies.
    print("\n=== Close-BS (5 m): rank-many regime ===")
    run_calibration(
        body_world_centroid=np.array([5.0, 0.0, 1.2]),
        phone_offset_local=phone_offset,
        scene_loss_db_los=15.0, yaw_deg=0.0,
        bs_height=3.0, label="close5m",
    )


if __name__ == "__main__":
    main()
