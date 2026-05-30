"""S2/S3 PoC: rotate the body's torso, watch the cascaded channel respond.

This is the v4 spine demonstration: the body-mediated channel h_body is
computed via the per-triangle Kirchhoff render (UE-anchored), and we sweep
torso yaw to show that pose-tuning the body re-shapes the cascaded channel.

Two regimes are run:
  - S2: body-shadowed LOS, scene_loss=35 dB on LOS path. Body-mediated
        contribution is comparable to attenuated LOS, gives Pareto-style
        rate gain via pose.
  - S3: extinguished LOS (wall fully blocks). Body-mediated path is the
        only path. Pose moves directly determine whether the link works.

Outputs: NPZ + PNG/PDF figures.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import (
    Body,
    kirchhoff_h_body,
    mrt_sinr_db,
    rate_bps_shannon,
)
from JSAC2.code.scene_nlos import BSArray, los_path_dict, los_h_at_phone
from JSAC2.code.scene_smplx import make_body_yaw_smplx


def make_body(yaw_deg: float, world_centroid: np.ndarray) -> Body:
    """Load Thelonious mesh and rotate by yaw about its vertical axis through
    its centroid, then translate to `world_centroid`.

    Kept for SI traceability: the original v4 PoC used Thelonious. The
    JSAC2 sweep now drives SMPL-X via `make_body_yaw_smplx` so the
    `theta -> mesh -> channel` pipeline is differentiable in pose.
    """
    mesh = trimesh.load("/home/user/aegis/data/thelonious.stl", force="mesh")
    if yaw_deg != 0.0:
        R = trimesh.transformations.rotation_matrix(
            np.deg2rad(yaw_deg), [0, 0, 1], point=mesh.centroid
        )
        mesh.apply_transform(R)
    delta = world_centroid - mesh.centroid
    mesh.apply_translation(delta)
    return Body(mesh)


def run_sweep(
    *,
    scene_loss_db_los: float,
    yaws_deg: np.ndarray,
    body_world_centroid: np.ndarray,
    phone_offset_local: np.ndarray,
    p_tx_dbm: float = 43.0,
    noise_dbm: float = -94.0,
    f_c: float = 28e9,
    label: str = "S2",
    body_factory=make_body_yaw_smplx,
):
    """Returns dict of arrays indexed by yaw."""
    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, 8.0]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=f_c)
    r_phone = body_world_centroid + phone_offset_local

    n_y = len(yaws_deg)
    h_los_norm = np.zeros(n_y)
    h_body_norm = np.zeros(n_y)
    h_cas_norm = np.zeros(n_y)
    sinr_los_db = np.zeros(n_y)
    sinr_body_db = np.zeros(n_y)
    sinr_cas_db = np.zeros(n_y)
    rate_los_mbps = np.zeros(n_y)
    rate_body_mbps = np.zeros(n_y)
    rate_cas_mbps = np.zeros(n_y)
    n_vis = np.zeros(n_y, dtype=int)
    cosine_cas_to_los = np.zeros(n_y)  # |<h_cas, h_LOS>| / (|h_cas| |h_LOS|)
    cosine_cas_to_body = np.zeros(n_y)
    coherent_gain_db = np.zeros(n_y)  # |h_LOS+h_body|^2 / (|h_LOS|^2 + |h_body|^2)
    cas_to_los_db = np.zeros(n_y)  # |h_cas|^2 / |h_LOS|^2

    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=scene_loss_db_los)

    t0 = time.time()
    for i, yaw in enumerate(yaws_deg):
        body = body_factory(yaw, body_world_centroid)
        path_dict = los_path_dict(bs, body.mesh.centroid)

        h_body, extras = kirchhoff_h_body(
            body, path_dict, r_phone, f_c=f_c, M=bs.M
        )
        h_cas = h_los + h_body

        h_los_norm[i] = np.linalg.norm(h_los)
        h_body_norm[i] = np.linalg.norm(h_body)
        h_cas_norm[i] = np.linalg.norm(h_cas)
        sinr_los_db[i] = mrt_sinr_db(h_los, p_tx_dbm=p_tx_dbm, noise_dbm=noise_dbm)
        sinr_body_db[i] = mrt_sinr_db(h_body, p_tx_dbm=p_tx_dbm, noise_dbm=noise_dbm)
        sinr_cas_db[i] = mrt_sinr_db(h_cas, p_tx_dbm=p_tx_dbm, noise_dbm=noise_dbm)
        rate_los_mbps[i] = rate_bps_shannon(sinr_los_db[i]) / 1e6
        rate_body_mbps[i] = rate_bps_shannon(sinr_body_db[i]) / 1e6
        rate_cas_mbps[i] = rate_bps_shannon(sinr_cas_db[i]) / 1e6
        n_vis[i] = extras["vis"].sum()

        denom = max(np.linalg.norm(h_los) * np.linalg.norm(h_cas), 1e-30)
        cosine_cas_to_los[i] = abs(np.vdot(h_los, h_cas)) / denom
        denom2 = max(np.linalg.norm(h_body) * np.linalg.norm(h_cas), 1e-30)
        cosine_cas_to_body[i] = abs(np.vdot(h_body, h_cas)) / denom2
        # Coherent gain: positive if cascaded sums constructively
        h_los_pow = float(np.sum(np.abs(h_los) ** 2))
        h_body_pow = float(np.sum(np.abs(h_body) ** 2))
        h_cas_pow = float(np.sum(np.abs(h_cas) ** 2))
        coherent_gain_db[i] = 10 * np.log10(
            h_cas_pow / max(h_los_pow + h_body_pow, 1e-30)
        )
        cas_to_los_db[i] = 10 * np.log10(h_cas_pow / max(h_los_pow, 1e-30))

    elapsed = time.time() - t0
    print(f"[{label}] swept {n_y} poses in {elapsed:.1f} s "
          f"({elapsed/n_y*1000:.0f} ms / pose)")

    return dict(
        label=label,
        yaws_deg=yaws_deg,
        h_los_norm=h_los_norm,
        h_body_norm=h_body_norm,
        h_cas_norm=h_cas_norm,
        sinr_los_db=sinr_los_db,
        sinr_body_db=sinr_body_db,
        sinr_cas_db=sinr_cas_db,
        rate_los_mbps=rate_los_mbps,
        rate_body_mbps=rate_body_mbps,
        rate_cas_mbps=rate_cas_mbps,
        n_vis=n_vis,
        cosine_cas_to_los=cosine_cas_to_los,
        cosine_cas_to_body=cosine_cas_to_body,
        coherent_gain_db=coherent_gain_db,
        cas_to_los_db=cas_to_los_db,
        scene_loss_db_los=scene_loss_db_los,
        body_centroid=body_world_centroid,
        phone_offset=phone_offset_local,
    )


def main(use_smplx: bool = True):
    out_dir = Path("/home/user/aegis/JSAC2/code/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    yaws = np.linspace(-45, 45, 19)
    body_centroid = np.array([30.0, 0.0, 1.2])
    phone_offset = np.array([0.55, 0.0, 0.10])

    body_factory = make_body_yaw_smplx if use_smplx else make_body
    suffix = "_smplx" if use_smplx else ""

    # Regime A: body-shadowed LOS (S2-like) - moderate scene loss
    res_s2 = run_sweep(
        scene_loss_db_los=35.0,
        yaws_deg=yaws,
        body_world_centroid=body_centroid,
        phone_offset_local=phone_offset,
        label="S2_los35dB",
        body_factory=body_factory,
    )
    np.savez(out_dir / f"pose_sweep{suffix}_S2.npz", **res_s2)

    # Regime B: extinguished LOS (S3-like). 80 dB additional loss kills LOS.
    res_s3 = run_sweep(
        scene_loss_db_los=80.0,
        yaws_deg=yaws,
        body_world_centroid=body_centroid,
        phone_offset_local=phone_offset,
        label="S3_los80dB",
        body_factory=body_factory,
    )
    np.savez(out_dir / f"pose_sweep{suffix}_S3.npz", **res_s3)

    # Regime C: binding regime (55 dB scene loss puts SINR around the Shannon)
    res_s2b = run_sweep(
        scene_loss_db_los=55.0,
        yaws_deg=yaws,
        body_world_centroid=body_centroid,
        phone_offset_local=phone_offset,
        label="S2bind_los55dB",
        body_factory=body_factory,
    )
    np.savez(out_dir / f"pose_sweep{suffix}_S2bind.npz", **res_s2b)

    # Print summary tables
    for res in (res_s2, res_s3):
        print()
        print(f"=== {res['label']}: scene_loss={res['scene_loss_db_los']:.0f} dB ===")
        print(f"{'yaw [°]':>8s} {'|h_los|':>10s} {'|h_body|':>10s} {'|h_cas|':>10s} "
              f"{'sinr_los':>9s} {'sinr_body':>10s} {'sinr_cas':>9s} {'R_cas [Mbps]':>13s}")
        for i in range(0, len(res['yaws_deg']), 2):
            y = res['yaws_deg'][i]
            print(f"{y:8.1f} {res['h_los_norm'][i]:10.3e} "
                  f"{res['h_body_norm'][i]:10.3e} "
                  f"{res['h_cas_norm'][i]:10.3e} "
                  f"{res['sinr_los_db'][i]:9.2f} "
                  f"{res['sinr_body_db'][i]:10.2f} "
                  f"{res['sinr_cas_db'][i]:9.2f} "
                  f"{res['rate_cas_mbps'][i]:13.1f}")

    print()
    print("Key claim checks:")
    for res in (res_s2, res_s3):
        sinr_var_db = res['sinr_cas_db'].max() - res['sinr_cas_db'].min()
        rate_var_pct = (res['rate_cas_mbps'].max() / res['rate_cas_mbps'].min() - 1) * 100
        print(f"  [{res['label']}] cascaded SINR varies {sinr_var_db:.2f} dB across pose; "
              f"rate varies {rate_var_pct:.1f}%")


if __name__ == "__main__":
    main()
