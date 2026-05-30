"""Parity + speed test: JAX kirchhoff vs NumPy reference, on a Munich scene."""
import sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from JSAC2.code.kirchhoff import kirchhoff_h_body, BSPathDict
from JSAC2.code.kirchhoff_jax import kirchhoff_h_body_jax
from JSAC2.code.scene_smplx import make_body_smplx
from JSAC2.code.latent_sweep_munich import load_munich_scene, decode_z, LATENT_D

import jax
print("JAX backend:", jax.default_backend(), "devices:", jax.devices())

# Load 1 LOS + 1 NLOS scene
def run_one(scene_idx, label):
    print(f"\n=== Scene {scene_idx} ({label}) ===")
    (bs, h_scene, r_phone, body_paths, body_centroid, face_az,
     flag, name, _) = load_munich_scene(scene_idx)
    print(f"  {flag} {name}, BS paths P={body_paths.N}, M={bs.M}")

    # Build a body at baseline (z = 0 -> mean pose)
    z = np.zeros(LATENT_D)
    pose22 = decode_z(z)
    body = make_body_smplx(pose22, body_centroid, face_azimuth_rad=face_az)
    print(f"  body: T={len(body.normals)} triangles")

    # Reference NumPy
    t0 = time.perf_counter()
    h_ref, _ = kirchhoff_h_body(body, body_paths, r_phone, M=bs.M)
    t_ref = time.perf_counter() - t0
    print(f"  NumPy: {t_ref*1000:.1f} ms")

    # JAX (warm-up: first call compiles the kernel)
    t0 = time.perf_counter()
    h_jax = kirchhoff_h_body_jax(body, body_paths, r_phone, M=bs.M)
    h_jax.block_until_ready() if hasattr(h_jax, "block_until_ready") else None
    t_jax_warm = time.perf_counter() - t0
    print(f"  JAX warm:  {t_jax_warm*1000:.1f} ms (incl. JIT compile)")

    # Hot calls (3 iterations)
    for i in range(3):
        t0 = time.perf_counter()
        h_jax = kirchhoff_h_body_jax(body, body_paths, r_phone, M=bs.M)
        t_jax_hot = time.perf_counter() - t0
        print(f"  JAX hot {i}: {t_jax_hot*1000:.1f} ms")

    # Parity check
    ref_norm = np.abs(h_ref).max()
    err = np.abs(h_jax - h_ref).max() / max(ref_norm, 1e-30)
    print(f"  max(|h_ref|) = {ref_norm:.3e}, "
          f"max(|h_jax - h_ref|)/ref = {err:.3e}")
    print(f"  speedup vs NumPy (hot): {t_ref / t_jax_hot:.1f}x")
    return err


if __name__ == "__main__":
    err0 = run_one(0,  "LOS_close")
    err15 = run_one(15, "NLOS_far")
    print()
    if max(err0, err15) < 1e-4:
        print("PASS: JAX parity within 1e-4 of NumPy on both scenes.")
    else:
        print(f"FAIL: parity error too large (max {max(err0, err15):.3e})")
