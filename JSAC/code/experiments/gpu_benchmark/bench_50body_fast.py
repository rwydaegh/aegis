"""GPU benchmark: factored-Fresnel + vmap and translation-phasor refresh.

Companion to ``bench_50body.py``. The reference benchmark times the per-body
loop with element-expanded paths through ``compute_body_channel`` and
``compute_exposure_operator``. This script exercises the two levers from
prompt 04:

1. Factored Fresnel + ``jax.vmap`` over a leading body axis
   (`compute_q_batch_vmap` from `aegis.coherent._fast`). One device dispatch
   per refresh, Fresnel evaluated at the ``N_center`` directions only.

2. Translation phasor identity (`coherent.translation`) for cheap warm
   refreshes. ``M_static`` is built once per (body, pose) and reused for an
   arbitrary translation Δt at each slot.

The script writes `timings_after_speedup.json` next to the existing
`timings.json` / `timings_decim10.json` so the before/after delta is on
disk for the paper.

Run:
    AEGIS_ARRAY_BACKEND=jax XLA_PYTHON_CLIENT_PREALLOCATE=false \\
      python JSAC/code/experiments/gpu_benchmark/bench_50body_fast.py
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("AEGIS_ARRAY_BACKEND", "jax")

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402
import numpy as np  # noqa: E402

jax.config.update("jax_enable_x64", True)

from aegis.coherent._fast import compute_q_batch_vmap  # noqa: E402
from aegis.coherent.translation import (  # noqa: E402
    compute_static_path_gram,
    q_translate_batch,
    translation_phasor,
)
from aegis.constants import C_0  # noqa: E402
from aegis.geometry.mesh import BodyMesh  # noqa: E402
from aegis.mimo.array import AntennaArray  # noqa: E402
from aegis.paths import PropagationPaths  # noqa: E402
from aegis.tissue.fresnel import n_complex  # noqa: E402

FREQ_HZ = 26e9
N_H, N_V = 8, 8
D_H = D_V = 0.5 * (C_0 / FREQ_HZ)
BS_CENTER = np.array([0.0, 0.0, 10.0])
BS_BROADSIDE = np.array([1.0, 0.0, 0.0])

N_BODIES = 50
N_CENTER_PATHS = 10
N_WARMUP = 3
N_STEADY = 30
RING_MIN_M = 20.0
RING_MAX_M = 80.0
RING_FWD_ANGLE_RAD = np.pi / 2

EPS_R_SKIN = 16.5
SIGMA_SKIN = 25.8
RNG_SEED = 20260424

DECIM_STRIDE = int(os.environ.get("AEGIS_BENCH_DECIM", "10"))


def _random_body_positions(rng, n):
    r = rng.uniform(RING_MIN_M, RING_MAX_M, size=n)
    theta = rng.uniform(-RING_FWD_ANGLE_RAD, RING_FWD_ANGLE_RAD, size=n)
    x = BS_CENTER[0] + r * np.cos(theta)
    y = BS_CENTER[1] + r * np.sin(theta)
    z = np.zeros_like(x)
    return np.stack([x, y, z], axis=1)


def _translate_mesh(base, offset, yaw_rad):
    c, s = np.cos(yaw_rad), np.sin(yaw_rad)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    normals = base.normals @ R.T
    centroids = (base.centroids @ R.T) + offset[None, :]
    return normals, centroids, base.areas.copy()


def _decimate(normals, centroids, areas, stride):
    if stride <= 1:
        return normals, centroids, areas
    return normals[::stride].copy(), centroids[::stride].copy(), (areas[::stride] * stride).copy()


def _synthetic_center_paths(rng, body_center, array_center, array, freq_hz, n_paths):
    direction_los = body_center - array_center
    dist_los = float(np.linalg.norm(direction_los))
    k_los = direction_los / max(dist_los, 1e-9)
    image = array_center * np.array([1.0, 1.0, -1.0])
    k_ground = (body_center - image) / max(np.linalg.norm(body_center - image), 1e-9)

    n_nlos = n_paths - 2
    nlos_k = np.zeros((n_nlos, 3))
    for i in range(n_nlos):
        perturb = rng.normal(scale=0.15, size=3)
        k = k_los + perturb
        nlos_k[i] = k / np.linalg.norm(k)
    k_hat = np.concatenate([k_los[None, :], k_ground[None, :], nlos_k], axis=0)

    psi = np.zeros((n_paths, 3), dtype=complex)
    for i in range(n_paths):
        ref = np.array([0.0, 1.0, 0.0])
        if abs(k_hat[i] @ ref) > 0.95:
            ref = np.array([0.0, 0.0, 1.0])
        e = np.cross(k_hat[i], ref)
        psi[i] = (e / np.linalg.norm(e)).astype(complex)

    amp = np.empty(n_paths)
    amp[0], amp[1] = 1.0, 0.4
    amp[2:] = 0.2
    phase = rng.uniform(0.0, 2 * np.pi, size=n_paths)
    psi = psi * (amp * np.exp(1j * phase))[:, None]

    # Fold the array element-pattern gain so factored == expanded.
    gain = array.element_gain(k_hat)
    psi_gained = psi * gain[:, None]
    return PropagationPaths(
        k_hat=k_hat,
        psi=psi_gained,
        element_index=np.zeros(n_paths, dtype=np.intp),
        delay=np.zeros(n_paths),
        is_los=np.array([True] + [False] * (n_paths - 1)),
    )


def _wall(fn, *args):
    t0 = time.perf_counter()
    out = fn(*args)
    jax.block_until_ready(out)
    return time.perf_counter() - t0, out


def _stats(ts):
    arr = np.asarray(ts) * 1e3
    return {
        "median_ms": float(np.median(arr)),
        "p10_ms": float(np.percentile(arr, 10)),
        "p90_ms": float(np.percentile(arr, 90)),
        "mean_ms": float(np.mean(arr)),
        "min_ms": float(np.min(arr)),
        "max_ms": float(np.max(arr)),
        "n": int(arr.size),
    }


def main():
    here = Path(__file__).resolve().parent
    out_json = here / "timings_after_speedup.json"

    devices = jax.devices()
    print(f"JAX devices: {devices}, backend: {jax.default_backend()}, version: {jax.__version__}")
    gpu_info = {}
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            gpu_info["nvidia_smi"] = res.stdout.strip()
    except Exception:  # noqa: BLE001
        pass

    repo_root = here.parents[3]
    mesh_path = repo_root / "data" / "thelonious.stl"
    base = BodyMesh.load(str(mesh_path))
    print(f"Loaded {base.name}: {base.n_triangles} tri, decim_stride={DECIM_STRIDE}")

    array = AntennaArray.upa(
        n_h=N_H,
        n_v=N_V,
        d_h=D_H,
        d_v=D_V,
        center=BS_CENTER,
        broadside=BS_BROADSIDE,
        element_pattern="patch",
    )
    n_tilde = n_complex(EPS_R_SKIN, SIGMA_SKIN, FREQ_HZ)

    rng = np.random.default_rng(RNG_SEED)
    positions = _random_body_positions(rng, N_BODIES)
    yaws = rng.uniform(-np.pi, np.pi, size=N_BODIES)

    normals_list, centroids_list, areas_list = [], [], []
    k_list, psi_list = [], []
    for i in range(N_BODIES):
        n, c, a = _translate_mesh(base, positions[i], yaws[i])
        n, c, a = _decimate(n, c, a, DECIM_STRIDE)
        normals_list.append(n)
        centroids_list.append(c)
        areas_list.append(a)
        body_center = c.mean(axis=0)
        center_paths = _synthetic_center_paths(rng, body_center, BS_CENTER, array, FREQ_HZ, N_CENTER_PATHS)
        k_list.append(np.asarray(center_paths.k_hat))
        psi_list.append(np.asarray(center_paths.psi))

    normals_b = jnp.asarray(np.stack(normals_list))
    centroids_b = jnp.asarray(np.stack(centroids_list))
    areas_b = jnp.asarray(np.stack(areas_list))
    k_b = jnp.asarray(np.stack(k_list))
    psi_b = jnp.asarray(np.stack(psi_list))
    offsets = jnp.asarray(array.element_positions - array.reference_position)

    n_tri = int(normals_b.shape[1])
    n_paths = int(k_b.shape[1])
    print(f"Per body: {n_tri} tri, {n_paths} center paths, M_ant={array.n_elements}")

    jit_q_batch = jax.jit(compute_q_batch_vmap, static_argnames=("freq_hz",))
    jit_translate = jax.jit(q_translate_batch)

    print("\nWarm-up factored+vmap cold construction...")
    t_compile, Q_warm = _wall(
        jit_q_batch,
        normals_b,
        centroids_b,
        areas_b,
        k_b,
        psi_b,
        offsets,
        n_tilde,
        SIGMA_SKIN,
        FREQ_HZ,
    )
    print(f"  first call (compile): {t_compile * 1e3:.1f} ms; Q_b shape: {Q_warm.shape}")
    for _ in range(N_WARMUP - 1):
        _wall(jit_q_batch, normals_b, centroids_b, areas_b, k_b, psi_b, offsets, n_tilde, SIGMA_SKIN, FREQ_HZ)

    print(f"\nSteady state ({N_STEADY} runs): full 50-body Q via factored+vmap...")
    cold_times = []
    for run in range(N_STEADY):
        dt, _ = _wall(
            jit_q_batch,
            normals_b,
            centroids_b,
            areas_b,
            k_b,
            psi_b,
            offsets,
            n_tilde,
            SIGMA_SKIN,
            FREQ_HZ,
        )
        cold_times.append(dt)
        if run < 3 or run == N_STEADY - 1:
            print(f"  run {run + 1:2d}: {dt * 1e3:.2f} ms")
    cold_stats = _stats(cold_times)

    print("\nBuilding M_static cache (vmap over bodies)...")
    static_vmap = jax.jit(
        jax.vmap(compute_static_path_gram, in_axes=(0, 0, 0, 0, 0, None, None, None, None)),
        static_argnames=("freq_hz",),
    )
    t_build, M_static_b = _wall(
        static_vmap,
        normals_b,
        centroids_b,
        areas_b,
        k_b,
        psi_b,
        offsets,
        n_tilde,
        SIGMA_SKIN,
        FREQ_HZ,
    )
    print(f"  M_static build (one-time per pose): {t_build * 1e3:.1f} ms; shape: {M_static_b.shape}")
    static_bytes = int(M_static_b.size * (M_static_b.dtype.itemsize))
    print(f"  M_static memory: {static_bytes / 1e6:.1f} MB")

    deltas_b = jnp.asarray(np.random.default_rng(0).normal(scale=0.005, size=(N_BODIES, 3)))

    def _phi_for_all(deltas_b):
        return jax.vmap(translation_phasor, in_axes=(0, 0, None))(k_b, deltas_b, FREQ_HZ)

    jit_phi_all = jax.jit(_phi_for_all)

    # Warm
    _wall(jit_phi_all, deltas_b)
    _wall(jit_translate, M_static_b, jit_phi_all(deltas_b))

    print(f"\nSteady state ({N_STEADY} runs): warm refresh via translation phasor...")
    warm_times = []
    for run in range(N_STEADY):
        t0 = time.perf_counter()
        phi_b = jit_phi_all(deltas_b)
        Qw = jit_translate(M_static_b, phi_b)
        jax.block_until_ready(Qw)
        warm_times.append(time.perf_counter() - t0)
        if run < 3 or run == N_STEADY - 1:
            print(f"  run {run + 1:2d}: {warm_times[-1] * 1e3:.3f} ms")
    warm_stats = _stats(warm_times)

    cold_med = cold_stats["median_ms"]
    warm_med = warm_stats["median_ms"]
    cold_p10, cold_p90 = cold_stats["p10_ms"], cold_stats["p90_ms"]
    warm_p10, warm_p90 = warm_stats["p10_ms"], warm_stats["p90_ms"]
    print("\n=== SUMMARY ===")
    print(f"50-body cold Q (factored + vmap): median {cold_med:.2f} ms (p10 {cold_p10:.2f}, p90 {cold_p90:.2f})")
    print(f"50-body warm Q (translation phasor): median {warm_med:.3f} ms (p10 {warm_p10:.3f}, p90 {warm_p90:.3f})")
    print(f"M_static one-time build: {t_build * 1e3:.1f} ms")
    print(f"Fits 100 ms pose cadence (cold)? {'YES' if cold_stats['p90_ms'] <= 100.0 else 'NO'}")
    print(f"Fits  10 ms slot cadence (warm)? {'YES' if warm_stats['p90_ms'] <= 10.0 else 'NO'}")

    result = {
        "scenario": {
            "carrier_ghz": FREQ_HZ / 1e9,
            "bs_array": f"{N_H}x{N_V} UPA",
            "m_ant": int(array.n_elements),
            "n_bodies": N_BODIES,
            "n_triangles_per_body": n_tri,
            "n_center_paths_per_body": n_paths,
            "phantom": base.name,
            "decim_stride": DECIM_STRIDE,
            "rng_seed": RNG_SEED,
        },
        "environment": {
            "jax_version": jax.__version__,
            "jax_backend": jax.default_backend(),
            "jax_devices": [str(d) for d in devices],
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "gpu_info": gpu_info,
        },
        "factored_vmap_cold_ms": cold_stats,
        "translation_phasor_warm_ms": warm_stats,
        "m_static_one_time_build_ms": t_build * 1e3,
        "m_static_size_bytes": static_bytes,
        "first_call_compile_ms": t_compile * 1e3,
    }
    out_json.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {out_json}")
    return result


if __name__ == "__main__":
    main()
