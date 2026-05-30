"""SVD spectrum of the body-to-UE Kirchhoff operator (v4 §sec:eval-modes).

The operator is Lambda(theta, r_p) of shape (M, T_vis), each entry the
per-element-per-triangle Kirchhoff coefficient. Its singular spectrum
tells us how many modes capture the body's response — the K parameter
in the Tier B calibration ladder.

We sweep a few representative phone-on-body geometries and report
- the spectral mass concentrated in the top K modes
- the K_99% threshold (smallest K such that >=99% of spectral mass)
- per-mode SVs for plotting
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import Body, kirchhoff_h_body
from JSAC2.code.scene_nlos import BSArray, los_path_dict
from JSAC2.code.pose_sweep import make_body


def measure_svd(*, body_world_centroid, phone_offset_local, yaw_deg=0.0,
                f_c=28e9, bs_height=8.0):
    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, bs_height]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=f_c)
    body = make_body(yaw_deg, body_world_centroid)
    r_phone = body_world_centroid + phone_offset_local
    paths = los_path_dict(bs, body.mesh.centroid)
    _, extras = kirchhoff_h_body(body, paths, r_phone, f_c=f_c, M=bs.M,
                                  return_per_triangle=True)
    Lambda = extras["Lambda"]  # (M, T_vis)
    M, T_vis = Lambda.shape

    # SVD
    U, S, Vh = np.linalg.svd(Lambda, full_matrices=False)
    # Cumulative mass (squared SVs since the energy-conserving inner product
    # is the operator's induced norm; spectral mass = sum_k s_k^2).
    s2 = S ** 2
    cum = np.cumsum(s2) / np.sum(s2)
    K_90 = int(np.searchsorted(cum, 0.90)) + 1
    K_99 = int(np.searchsorted(cum, 0.99)) + 1
    K_999 = int(np.searchsorted(cum, 0.999)) + 1
    return dict(
        S=S, cum_mass=cum, M=M, T_vis=T_vis,
        K_90=K_90, K_99=K_99, K_999=K_999,
        Lambda_norm=float(np.linalg.norm(Lambda, ord="fro")),
        Lambda_op_norm=float(np.linalg.norm(Lambda, ord=2)),
        cond=float(S[0] / max(S[-1], 1e-30)),
    )


def main():
    out_dir = Path("/home/user/aegis/JSAC2/code/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Sweep over BS distance to expose the rank-1 → rank-many transition.
    # The BS aperture is 14 cm; at 28 GHz angular resolution at distance d
    # is ~lambda/D ~ 4°. Body subtends atan(D_body/d) deg from BS:
    #   30 m: ~2.5° (sub-beamwidth), expect K_99 ~ 1
    #   10 m: ~7°   (~ beamwidth), expect K_99 ~ 2-3
    #   3 m:  ~22°  (super-resolved), expect K_99 ~ 5-10
    bs_distances = [(30.0, 8.0), (10.0, 5.0), (5.0, 3.0), (3.0, 2.5)]
    phone_offset = np.array([0.40, 0.0, 0.10])

    results = {}
    for d, bs_h in bs_distances:
        body_centroid = np.array([d, 0.0, 1.2])
        for yaw in [0.0]:
            key = f"d{int(d)}m_yaw{int(yaw)}"
            print(f"Measuring SVD for BS distance={d}m (BS height={bs_h}m), yaw={yaw:.0f}deg ...")
            r = measure_svd(body_world_centroid=body_centroid,
                            phone_offset_local=phone_offset, yaw_deg=yaw,
                            bs_height=bs_h)
            r["bs_distance_m"] = d
            r["bs_height_m"] = bs_h
            print(f"  T_vis={r['T_vis']}, K_90={r['K_90']}, K_99={r['K_99']}, "
                  f"K_999={r['K_999']}, cond={r['cond']:.2e}")
            results[key] = r

    # Save in a single NPZ with name prefix per key
    flat = {}
    for key, r in results.items():
        for k, v in r.items():
            flat[f"{key}__{k}"] = v
    flat["geom_keys"] = np.array(list(results.keys()))
    np.savez(out_dir / "svd_spectrum.npz", **flat)
    print(f"Saved to {out_dir / 'svd_spectrum.npz'}")


if __name__ == "__main__":
    main()
