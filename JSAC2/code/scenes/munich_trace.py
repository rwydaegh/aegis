"""Trace Munich paths for each Rx, save per-scene NPZ for the latent sweep.

For each (BS, phone, body_centroid) triple, Sionna RT produces all paths
up to max_depth interactions. We package them into AEGIS-compatible
per-element representations:

  body_paths.npz fields (one per scene):
    j_idx          (P,) int     -- BS element index (0..M-1)
    k_hat          (P, 3) float -- direction at body in world frame
    psi            (P, 3) cplx  -- polarization vector at body (V/m)
    amp            (P,)  cplx   -- per-(element, path) scalar amplitude
                                    encodes spreading + carrier phase +
                                    array steering
  phone_h.npz fields:
    h_scene        (M,)  cplx   -- per-element scene channel at phone
                                    (multipath sum)

Convention: Sionna runs with a single-element point Tx and a single
Rx; we recover per-Sionna-path (k_hat_dod, k_hat_doa, amp_scalar) and
fan it across the M=64 BS elements via planewave phase ramp
exp(-j k0 (bs_pos[m] - bs_center) . k_hat_dod). Per-element delay
variation across the panel is sub-mm and ignored.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import contextlib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from sionna.rt import (load_scene, scene as sc, PlanarArray,
                        Transmitter, Receiver, PathSolver)

from JSAC2.code.scene_nlos import BSArray
from JSAC2.code.kirchhoff import C0

OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs/munich")
TRACE_DIR = OUT_DIR / "traces"
RX_JSON = Path(__file__).with_name("munich_rx.json")

F_C = 28e9                     # carrier
LAMBDA = C0 / F_C
PHONE_Z = 1.5
BODY_Z = 1.20                  # SMPL-X centroid for upright adult
PHONE_OFFSET_BS_DIR = 0.40     # phone in front of body, toward BS
MAX_DEPTH = 5                  # up to 5 interactions (refl + diffraction)
SOLVER = PathSolver()


def make_bs_array(bs_pos, normal=None):
    """8x8 URA. Default boresight points at the centroid of the
    operator-selected LOS plaza (~(16, 68, 1.5)) -- a typical
    street-cell mast mounted on a building edge, downtilted and
    yawed to face the served zone."""
    if normal is None:
        bs = np.asarray(bs_pos, dtype=float)
        target = np.array([33.0, 91.0, 1.5])
        v = target - bs
        normal = v / np.linalg.norm(v)
    return BSArray(n_x=8, n_y=8, center=np.asarray(bs_pos),
                    normal=np.asarray(normal), f_c=F_C)


def trace_one(scene, bs_center, target_xyz, max_depth=MAX_DEPTH):
    """Run a single Sionna trace with a point Tx and point Rx.

    Returns a dict with per-Sionna-path arrays:
      a       (P,) complex                    -- per-path amplitude (sum of theta + phi)
      tau     (P,)                            -- per-path delay [s]
      k_dod   (P, 3) world-frame from BS      -- direction of departure
      k_doa   (P, 3) world-frame at target    -- direction signal travels INTO target
      psi     (P, 3) complex                  -- polarization at target (V/m at unit P_tx)
      n_valid                                  -- number of valid paths
    """
    for n in list(scene.transmitters.keys()) + list(scene.receivers.keys()):
        with contextlib.suppress(Exception):
            scene.remove(n)
    scene.tx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                  polarization="V")
    scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                  polarization="V")
    scene.add(Transmitter("tx", position=[float(bs_center[0]),
                                          float(bs_center[1]),
                                          float(bs_center[2])]))
    scene.add(Receiver("rx", position=[float(target_xyz[0]),
                                       float(target_xyz[1]),
                                       float(target_xyz[2])]))
    paths = SOLVER(scene=scene, los=True, specular_reflection=True,
                   diffuse_reflection=False, refraction=True,
                   diffraction=True, edge_diffraction=True,
                   max_depth=max_depth, samples_per_src=10_000_000,
                   max_num_paths_per_src=200_000)

    # paths.cir() returns (a, tau).
    # a shape (Sionna v2): (num_rx_field_comp=2, num_rx_ant, num_tx_field_comp,
    #                       num_tx_ant, num_rx_devs, num_paths, num_time_steps)
    # For point Tx (V) and point Rx (V): a[0, ...] = E_theta, a[1, ...] = E_phi.
    a_raw, tau_raw = paths.cir()
    a_np = np.asarray(a_raw)  # (2, 1, 1, 1, 1, P, 1)
    tau_np = np.asarray(tau_raw)  # (1, 1, P)
    a_theta_all = a_np[0, 0, 0, 0, 0, :, 0]  # (P,) complex
    a_phi_all = a_np[1, 0, 0, 0, 0, :, 0]    # (P,) complex
    # Combined scalar amplitude (norm) for validity testing
    a_mag = np.sqrt(np.abs(a_theta_all) ** 2 + np.abs(a_phi_all) ** 2)
    tau = tau_np[0, 0, :]  # (P,)

    # Departure / arrival angles
    theta_t = np.asarray(paths.theta_t)[0, 0, :]  # (P,)
    phi_t = np.asarray(paths.phi_t)[0, 0, :]
    theta_r = np.asarray(paths.theta_r)[0, 0, :]
    phi_r = np.asarray(paths.phi_r)[0, 0, :]

    # Validity mask: use non-zero combined amp + finite delay
    valid = (a_mag > 1e-30) & np.isfinite(tau)
    a_theta = a_theta_all[valid]
    a_phi = a_phi_all[valid]
    tau = tau[valid]
    theta_t, phi_t = theta_t[valid], phi_t[valid]
    theta_r, phi_r = theta_r[valid], phi_r[valid]

    # Convert spherical -> Cartesian unit vectors (in world frame; default
    # device orientation is identity)
    def sph_to_cart(th, ph):
        st, ct = np.sin(th), np.cos(th)
        sp, cp = np.sin(ph), np.cos(ph)
        return np.column_stack([st * cp, st * sp, ct])  # (P, 3)

    # k_dod = direction signal LEAVES Tx = +(sin theta cos phi, ...) when
    # theta_t/phi_t are measured from the Tx outward.
    k_dod = sph_to_cart(theta_t, phi_t)
    # k_doa = direction signal travels INTO target. Sionna gives angles
    # in Rx local frame describing where the signal CAME FROM. The direction
    # "into target" is the negative of that.
    k_doa = -sph_to_cart(theta_r, phi_r)

    # Polarization basis at Rx for spherical (theta_r, phi_r); recover the
    # full 3-D complex E-field psi = a_theta * e_theta + a_phi * e_phi.
    e_theta = np.column_stack([
        np.cos(theta_r) * np.cos(phi_r),
        np.cos(theta_r) * np.sin(phi_r),
        -np.sin(theta_r),
    ])
    e_phi = np.column_stack([-np.sin(phi_r), np.cos(phi_r),
                              np.zeros_like(phi_r)])
    psi = a_theta[:, None] * e_theta + a_phi[:, None] * e_phi  # (P, 3)
    # Scalar amplitude (used for per-element steering ramp): the complex
    # carrier-phase factor exp(j 2pi f tau) extracted from the path delay
    # so that the per-path amp can be applied as a scalar then steered.
    # Sionna's psi already includes this phase, so we set scalar a = 1
    # and let psi carry the magnitude.
    a_scalar = np.ones_like(tau, dtype=np.complex128)

    return {
        "a": a_scalar, "tau": tau, "k_dod": k_dod, "k_doa": k_doa,
        "psi": psi, "n_valid": int(valid.sum()),
    }


def fanout_to_elements(trace_dict, bs_array, lambda_):
    """Expand per-Sionna-path data to per-(element, path) AEGIS format.

    Returns (j_idx, k_hat, psi, amp) suitable for BSPathDict.
    """
    P = trace_dict["n_valid"]
    if P == 0:
        return (np.zeros(0, dtype=np.int32),
                np.zeros((0, 3), dtype=np.float64),
                np.zeros((0, 3), dtype=np.complex128),
                np.zeros(0, dtype=np.complex128))
    M = bs_array.M
    bs_pos = bs_array.positions  # (M, 3)
    bs_center = bs_array.center  # (3,)
    k_dod = trace_dict["k_dod"]  # (P, 3)
    k_doa = trace_dict["k_doa"]  # (P, 3)
    psi = trace_dict["psi"]      # (P, 3) complex
    a = trace_dict["a"]          # (P,) complex (carries 1/r spreading + carrier phase)

    # Per-element steering phase: planewave phase ramp around bs_center
    # in the direction of departure k_dod.
    k0 = 2.0 * np.pi / lambda_
    rel = bs_pos - bs_center[None, :]  # (M, 3)
    # element_phase[m, p] = exp(-j k0 (bs_pos[m] - center) . k_dod[p])
    element_phase = np.exp(-1j * k0 * (rel @ k_dod.T))  # (M, P)

    # Build flat (M*P,) arrays
    # psi: same direction for each element on a given path
    psi_flat = np.tile(psi, (M, 1))  # (M*P, 3)
    k_hat_flat = np.tile(k_doa, (M, 1))  # (M*P, 3)
    j_idx_flat = np.repeat(np.arange(M, dtype=np.int32), P)
    a_flat = (a[None, :] * element_phase).reshape(-1)  # (M*P,)
    return j_idx_flat, k_hat_flat, psi_flat, a_flat


def per_element_h_at_phone(trace_dict, bs_array, lambda_):
    """h_scene[m] for a phone Rx: sum over paths of (a_p * element_phase[m, p]).

    The scalar polarization contribution is the V (z) component of psi
    projected on a vertical-pol UE antenna; we keep it complex.
    """
    P = trace_dict["n_valid"]
    if P == 0:
        return np.zeros(bs_array.M, dtype=np.complex128)
    bs_pos = bs_array.positions
    bs_center = bs_array.center
    k_dod = trace_dict["k_dod"]
    psi = trace_dict["psi"]
    a = trace_dict["a"]
    k0 = 2.0 * np.pi / lambda_
    rel = bs_pos - bs_center[None, :]
    element_phase = np.exp(-1j * k0 * (rel @ k_dod.T))  # (M, P)
    # Vertical-pol UE pickup: take the world-z component of polarization
    psi_z = psi[:, 2]  # (P,) complex
    h_scene = (element_phase * (a * psi_z)[None, :]).sum(axis=1)  # (M,)
    return h_scene


def trace_all_scenes():
    rx_data = json.loads(RX_JSON.read_text())
    bs_xyz = np.array(rx_data["bs_pos_xyz_m"])
    rxs = rx_data["rx"]

    print(f"Loading Munich scene ...")
    s = load_scene(sc.munich)
    s.frequency = F_C

    bs_array = make_bs_array(bs_xyz)
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    summary = []
    for i, rx in enumerate(rxs):
        phone_xyz = np.array([rx["x"], rx["y"], PHONE_Z])
        # Body faces BS in xy. Phone is 0.40 m IN FRONT of body (toward BS).
        bs_dir_xy = np.array([bs_xyz[0] - phone_xyz[0],
                              bs_xyz[1] - phone_xyz[1]])
        bs_dir_xy /= max(np.linalg.norm(bs_dir_xy), 1e-9)
        body_centroid = np.array([
            phone_xyz[0] - PHONE_OFFSET_BS_DIR * bs_dir_xy[0],
            phone_xyz[1] - PHONE_OFFSET_BS_DIR * bs_dir_xy[1],
            BODY_Z,
        ])
        face_azimuth_rad = float(np.arctan2(bs_dir_xy[1], bs_dir_xy[0]))

        print(f"  scene {i:2d}: rx=({rx['x']:+5.0f}, {rx['y']:+5.0f}) "
              f"[{rx['los_flag']}, {rx['label']}]")

        body_trace = trace_one(s, bs_xyz, body_centroid)
        phone_trace = trace_one(s, bs_xyz, phone_xyz)
        body_j, body_k, body_psi, body_amp = fanout_to_elements(
            body_trace, bs_array, LAMBDA)
        h_scene = per_element_h_at_phone(phone_trace, bs_array, LAMBDA)

        out_path = TRACE_DIR / f"scene_{i:02d}.npz"
        # Save BOTH the fanout (NumPy/legacy) and the Sionna-native per-path
        # arrays (compact for JAX autodiff: (P,) instead of (M*P,)).
        np.savez(out_path,
                 bs_pos=bs_xyz, bs_positions=bs_array.positions,
                 phone_xyz=phone_xyz, body_centroid=body_centroid,
                 face_azimuth_rad=face_azimuth_rad,
                 body_j_idx=body_j, body_k_hat=body_k,
                 body_psi=body_psi, body_amp=body_amp,
                 # native (per-Sionna-path) arrays for JAX autodiff:
                 body_k_dod=body_trace["k_dod"],
                 body_k_doa=body_trace["k_doa"],
                 body_psi_path=body_trace["psi"],
                 body_amp_path=body_trace["a"],
                 h_scene=h_scene,
                 los_flag=rx["los_flag"], label=rx["label"],
                 n_body_paths=body_trace["n_valid"],
                 n_phone_paths=phone_trace["n_valid"])
        summary.append({
            "scene": i,
            "los_flag": rx["los_flag"],
            "label": rx["label"],
            "n_body_paths": body_trace["n_valid"],
            "n_phone_paths": phone_trace["n_valid"],
            "h_scene_db": float(20 * np.log10(np.abs(h_scene).sum() + 1e-30)),
        })
        print(f"     body paths={body_trace['n_valid']}, "
              f"phone paths={phone_trace['n_valid']}, "
              f"|h_scene| sum={20*np.log10(np.abs(h_scene).sum() + 1e-30):.1f} dB")

    (TRACE_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n  wrote {len(rxs)} scene NPZs to {TRACE_DIR}")


if __name__ == "__main__":
    trace_all_scenes()
