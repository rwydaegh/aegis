"""End-to-end smoke test: build a body, build BS, render h_body, print numbers.

Verifies that the Kirchhoff render produces sensible magnitudes and that
visibility culling is doing what it should.
"""

import sys
from pathlib import Path

import numpy as np

# Make repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import Body, kirchhoff_h_body, mrt_sinr_db, rate_bps_shannon
from JSAC2.code.scene_nlos import BSArray, los_path_dict, los_h_at_phone


def main():
    # Geometry: body at (30, 0, 1), phone at body+(0.55, 0, 0.10)
    body_world_centroid = np.array([30.0, 0.0, 1.0])
    phone_offset = np.array([0.55, 0.0, 0.10])
    r_phone = body_world_centroid + phone_offset

    # Load Thelonious mesh (upper torso + head)
    body = Body.from_stl(
        "/home/user/aegis/data/thelonious.stl",
        scale=1.0,  # check whether mesh is in m or mm; thelonious is in mm probably
        translate=body_world_centroid - np.array([0, 0, 0]),  # adjust below
    )
    # Inspect mesh extents to figure out scale
    print(f"Body mesh: {len(body.centroids)} triangles")
    print(f"Body bounds: {body.mesh.bounds}")
    print(f"Body centroid: {body.mesh.centroid}")

    # BS at (0, 0, 8), 8x8 URA at 28 GHz
    bs = BSArray(n_x=8, n_y=8, center=np.array([0.0, 0.0, 8.0]),
                 normal=np.array([1.0, 0.0, 0.0]), f_c=28e9)
    print(f"BS array: {bs.M} elements, spacing {bs.spacing*1000:.2f} mm")

    # LOS at body and at phone
    los_at_body = los_path_dict(bs, body.mesh.centroid)
    h_los = los_h_at_phone(bs, r_phone, scene_loss_db=35.0)
    print(f"||h_LOS|| (with 35 dB scene loss) = {np.linalg.norm(h_los):.3e}")

    # Visibility cull from phone
    vis_phone = body.visible_from(r_phone)
    print(f"Triangles visible from phone: {vis_phone.sum()} / {len(body.centroids)} "
          f"({100*vis_phone.mean():.1f} %)")

    # Kirchhoff render
    h_body, extras = kirchhoff_h_body(
        body, los_at_body, r_phone,
        f_c=bs.f_c, M=bs.M,
        return_per_triangle=True,
    )
    print(f"||h_body|| = {np.linalg.norm(h_body):.3e}")
    Lambda = extras["Lambda"]
    print(f"Lambda shape: {Lambda.shape}")
    print(f"Lambda spectral norm: {np.linalg.norm(Lambda, ord=2):.3e}")

    # Cascaded channel
    h_cas = h_los + h_body
    # Note: array gain is implicit in ||h||^2 (coherent combining over M elements)
    sinr_los_db = mrt_sinr_db(h_los, p_tx_dbm=43, noise_dbm=-94)
    sinr_cas_db = mrt_sinr_db(h_cas, p_tx_dbm=43, noise_dbm=-94)
    sinr_body_db = mrt_sinr_db(h_body, p_tx_dbm=43, noise_dbm=-94)
    print(f"SINR(h_LOS)        = {sinr_los_db:.2f} dB")
    print(f"SINR(h_body alone) = {sinr_body_db:.2f} dB")
    print(f"SINR(cascaded)     = {sinr_cas_db:.2f} dB")
    print(f"Rate(LOS only)     = {rate_bps_shannon(sinr_los_db)/1e6:.1f} Mbps")
    print(f"Rate(cascaded)     = {rate_bps_shannon(sinr_cas_db)/1e6:.1f} Mbps")


if __name__ == "__main__":
    main()
