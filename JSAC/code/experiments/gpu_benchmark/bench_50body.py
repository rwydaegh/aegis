"""GPU benchmark: AEGIS 50-body coherent exposure operator Q refresh.

Question answered: on a GPU, how long does AEGIS take to recompute the per-body
coherent exposure operator Q^(u) for 50 bodies (~25 k triangles each) at one
pose, from ray-tracer path set through G_tilde to Q?

Scenario:
- Carrier: 26 GHz
- BS: 8x8 UPA, M = 64 elements
- 50 copies of Thelonious (~23.8 k triangles)
- Random positions in a 20-80 m ring in front of the BS
- 10 center multipath per body (LOS + ground + 8 facade/cluster), expanded to
  per-element paths (N_total = 10 * 64 = 640 per body)
- One fixed pose per body (default standing pose)

The ray tracer is stubbed with a synthetic multipath set. The prompt is about
AEGIS compute time, not end-to-end ray tracing.

Outputs:
- timings.json (raw timings, medians, percentiles, environment metadata)
- prints a summary to stdout
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

# Enable JAX backend BEFORE aegis import.
os.environ.setdefault("AEGIS_ARRAY_BACKEND", "jax")

import jax
import jax.numpy as jnp
import numpy as np

# JAX config: enable x64 to match AEGIS (see _array_backend.py)
jax.config.update("jax_enable_x64", True)

from aegis.coherent._accumulate import _accumulate_by_element_jax  # noqa: E402
from aegis.coherent.exposure_operator import compute_exposure_operator  # noqa: E402
from aegis.coherent.fresnel_operator import (  # noqa: E402
    apply_fresnel_operator,
    compute_fresnel_operator,
)
from aegis.constants import C_0  # noqa: E402
from aegis.defaults import NUMERICAL_FLOOR  # noqa: E402
from aegis.geometry.mesh import BodyMesh  # noqa: E402
from aegis.mimo.array import AntennaArray  # noqa: E402
from aegis.mimo.array_paths import expand_paths_to_array  # noqa: E402
from aegis.paths import PropagationPaths  # noqa: E402
from aegis.tissue.fresnel import n_complex, xi_from_mu  # noqa: E402


# Jit-friendly inlined version of compute_body_channel (skips host validation).
# Equivalent to the library function body; only the np.asarray validation is dropped.
def _compute_body_channel_jax(
    normals,
    centroids,
    k_hat,
    psi,
    element_index,
    n_tilde,
    sigma,
    freq_hz,
    n_elements,
):
    M = normals.shape[0]
    k0 = 2 * jnp.pi * freq_hz / C_0

    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n_tilde)
    F_psi = apply_fresnel_operator(psi, t_s, t_p, e_s, e_p)

    xi = xi_from_mu(mu, n_tilde)
    alpha = -jnp.imag(k0 * xi)
    alpha = jnp.maximum(alpha, NUMERICAL_FLOOR)
    depth_weight = jnp.sqrt(sigma / (4 * alpha))

    phase_arg = -k0 * (centroids @ k_hat.T)
    phase = jnp.exp(1j * phase_arg)

    weighted = depth_weight[:, :, None] * F_psi * phase[:, :, None]

    return _accumulate_by_element_jax(weighted, element_index, M, n_elements)


# -- scenario constants --------------------------------------------------------

FREQ_HZ = 26e9
N_H, N_V = 8, 8
D_H = D_V = 0.5 * (C_0 / FREQ_HZ)  # half-wavelength spacing
BS_CENTER = np.array([0.0, 0.0, 10.0])
BS_BROADSIDE = np.array([1.0, 0.0, 0.0])

N_BODIES = 50
N_CENTER_PATHS = 10  # LOS + ground + 8 facade/cluster
N_WARMUP = 3
N_STEADY = 30
RING_MIN_M = 20.0
RING_MAX_M = 80.0
RING_FWD_ANGLE_RAD = np.pi / 2  # +/- 90 deg front arc of BS broadside

# Tissue: skin at 26 GHz (matches monograph default).
EPS_R_SKIN = 16.5
SIGMA_SKIN = 25.8  # S/m
RNG_SEED = 20260424

# -- helpers -------------------------------------------------------------------


def _random_body_positions(rng: np.random.Generator, n: int) -> np.ndarray:
    """Random (x, y) positions in front of BS on a 20-80 m ring."""
    r = rng.uniform(RING_MIN_M, RING_MAX_M, size=n)
    theta = rng.uniform(-RING_FWD_ANGLE_RAD, RING_FWD_ANGLE_RAD, size=n)
    x = BS_CENTER[0] + r * np.cos(theta)
    y = BS_CENTER[1] + r * np.sin(theta)
    z = np.zeros_like(x)  # feet on ground
    return np.stack([x, y, z], axis=1)


def _translate_mesh(base: BodyMesh, offset: np.ndarray, yaw_rad: float) -> BodyMesh:
    """Translate and yaw a BodyMesh (z-axis rotation)."""
    c, s = np.cos(yaw_rad), np.sin(yaw_rad)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    vertices = (base.vertices.reshape(-1, 3) @ R.T).reshape(base.vertices.shape) + offset[None, None, :]
    normals = base.normals @ R.T
    centroids = (base.centroids @ R.T) + offset[None, :]
    return BodyMesh(
        vertices=vertices,
        normals=normals,
        centroids=centroids,
        areas=base.areas.copy(),
        name=base.name,
    )


def _synthetic_center_paths(
    rng: np.random.Generator,
    body_center: np.ndarray,
    array_center: np.ndarray,
    n_paths: int,
) -> PropagationPaths:
    """Stub ray-tracer output: LOS + ground bounce + facade clusters toward body.

    All psi are unit-amplitude complex-polarised orthogonal to k_hat. Power is
    spread with a LOS-dominant profile (LOS gets more amplitude than NLOS).
    """
    direction_los = body_center - array_center
    dist_los = float(np.linalg.norm(direction_los))
    k_los = direction_los / max(dist_los, 1e-9)

    # Ground bounce: reflect BS z through z=0, pointed at body
    image = array_center * np.array([1.0, 1.0, -1.0])
    direction_ground = body_center - image
    dist_ground = float(np.linalg.norm(direction_ground))
    k_ground = direction_ground / max(dist_ground, 1e-9)

    # Facade/cluster directions: randomly perturb the LOS direction by 5-30 deg
    n_nlos = n_paths - 2
    nlos_k = np.zeros((n_nlos, 3))
    nlos_delay = np.zeros(n_nlos)
    for i in range(n_nlos):
        perturb = rng.normal(scale=0.15, size=3)  # ~8.5 deg rms
        k = k_los + perturb
        k = k / np.linalg.norm(k)
        nlos_k[i] = k
        # longer NLOS delays
        nlos_delay[i] = dist_los / C_0 * rng.uniform(1.2, 2.5)

    k_hat = np.concatenate([k_los[None, :], k_ground[None, :], nlos_k], axis=0)

    # Build unit psi perpendicular to k_hat (x-ish polarisation)
    psi = np.zeros((n_paths, 3), dtype=complex)
    for i in range(n_paths):
        ref = np.array([0.0, 1.0, 0.0])
        if abs(k_hat[i] @ ref) > 0.95:
            ref = np.array([0.0, 0.0, 1.0])
        e_pol = np.cross(k_hat[i], ref)
        e_pol = e_pol / np.linalg.norm(e_pol)
        psi[i] = e_pol.astype(complex)

    # Amplitude profile: LOS = 1, ground = 0.4, NLOS ~ 0.2 each, random phase.
    amp = np.empty(n_paths)
    amp[0] = 1.0
    amp[1] = 0.4
    amp[2:] = 0.2
    phase = rng.uniform(0.0, 2 * np.pi, size=n_paths)
    psi = psi * (amp * np.exp(1j * phase))[:, None]

    delay = np.concatenate([[dist_los / C_0], [dist_ground / C_0], nlos_delay])
    is_los = np.zeros(n_paths, dtype=bool)
    is_los[0] = True

    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=np.zeros(n_paths, dtype=np.intp),
        delay=delay,
        is_los=is_los,
    )


# -- stage kernels (jit-compiled) ---------------------------------------------


def _fresnel_stage(normals, k_hat, n_tilde):
    # Fresnel-tensor construction only.
    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n_tilde)
    # Return a small scalar to force materialisation of all outputs.
    return jnp.sum(t_s.real) + jnp.sum(t_s.imag) + jnp.sum(t_p.real) + jnp.sum(e_s) + jnp.sum(e_p) + jnp.sum(mu)


def _body_channel_stage(normals, centroids, k_hat, psi, element_index, n_tilde, sigma, freq_hz, n_elements):
    # Full body-surface channel (includes Fresnel inside).
    return _compute_body_channel_jax(normals, centroids, k_hat, psi, element_index, n_tilde, sigma, freq_hz, n_elements)


def _gram_stage(G_tilde, areas):
    return compute_exposure_operator(G_tilde, areas)


def _full_stage(normals, centroids, areas, k_hat, psi, element_index, n_tilde, sigma, freq_hz, n_elements):
    G_tilde = _compute_body_channel_jax(
        normals, centroids, k_hat, psi, element_index, n_tilde, sigma, freq_hz, n_elements
    )
    return compute_exposure_operator(G_tilde, areas)


# -- benchmark driver ---------------------------------------------------------


def _wall_gpu(fn, *args):
    """Wall-clock that blocks until all device work completes."""
    t0 = time.perf_counter()
    out = fn(*args)
    jax.block_until_ready(out)
    return (time.perf_counter() - t0), out


def main():
    here = Path(__file__).resolve().parent
    out_json = here / "timings.json"

    # Environment metadata
    devices = jax.devices()
    if not any(d.platform == "gpu" for d in devices):
        print("FATAL: no GPU device visible to JAX. Aborting per prompt constraints.", file=sys.stderr)
        print(f"JAX devices: {devices}", file=sys.stderr)
        sys.exit(2)

    device = devices[0]
    gpu_info = {}
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,cuda_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            gpu_info["nvidia_smi"] = res.stdout.strip()
    except Exception:  # noqa: BLE001
        pass

    print(f"JAX devices: {devices}")
    print(f"JAX backend: {jax.default_backend()}")
    print(f"JAX version: {jax.__version__}")

    # Load canonical Thelonious mesh
    repo_root = here.parents[2]
    mesh_path = repo_root / "data" / "thelonious.stl"
    base = BodyMesh.load(str(mesh_path))
    print(f"Loaded {base.name}: {base.n_triangles} triangles, total area {base.total_area:.3f} m^2")

    # BS antenna array
    array = AntennaArray.upa(
        n_h=N_H,
        n_v=N_V,
        d_h=D_H,
        d_v=D_V,
        center=BS_CENTER,
        broadside=BS_BROADSIDE,
        element_pattern="patch",
    )
    print(f"Antenna: 8x8 UPA, M={array.n_elements}, spacing {D_H * 1e3:.2f} mm (lambda/2 @ 26 GHz)")

    # Tissue: complex index at 26 GHz
    n_tilde = n_complex(EPS_R_SKIN, SIGMA_SKIN, FREQ_HZ)
    print(f"Tissue: eps_r={EPS_R_SKIN}, sigma={SIGMA_SKIN} S/m, n_tilde={n_tilde:.3f}")

    # Build 50 body payloads (positioned mesh + expanded paths)
    rng = np.random.default_rng(RNG_SEED)
    positions = _random_body_positions(rng, N_BODIES)
    yaws = rng.uniform(-np.pi, np.pi, size=N_BODIES)

    bodies_data = []
    centers_data = []  # center-paths only, for factored-Fresnel reference
    for i in range(N_BODIES):
        body = _translate_mesh(base, positions[i], yaws[i])
        center_paths = _synthetic_center_paths(rng, body.centroids.mean(axis=0), BS_CENTER, N_CENTER_PATHS)
        paths = expand_paths_to_array(center_paths, array, FREQ_HZ)
        # Move arrays to device once.
        bodies_data.append(
            {
                "normals": jnp.asarray(body.normals),
                "centroids": jnp.asarray(body.centroids),
                "areas": jnp.asarray(body.areas),
                "k_hat": jnp.asarray(paths.k_hat),
                "psi": jnp.asarray(paths.psi),
                "element_index": jnp.asarray(paths.element_index),
                "n_tri": int(body.n_triangles),
                "n_paths": int(paths.k_hat.shape[0]),
            }
        )
        centers_data.append(
            {
                "normals": bodies_data[-1]["normals"],
                "k_hat": jnp.asarray(center_paths.k_hat),
            }
        )

    n_tri_per_body = bodies_data[0]["n_tri"]
    n_paths_per_body = bodies_data[0]["n_paths"]
    print(
        f"Per body: {n_tri_per_body} triangles, {N_CENTER_PATHS} center paths -> "
        f"{n_paths_per_body} per-element paths (N_center * M_ant = {N_CENTER_PATHS}*{array.n_elements})"
    )

    # JIT-compile stages.
    jit_fresnel = jax.jit(_fresnel_stage)
    jit_body_ch = jax.jit(_body_channel_stage, static_argnums=(8,))  # n_elements static
    jit_gram = jax.jit(_gram_stage)
    jit_full = jax.jit(_full_stage, static_argnums=(9,))

    # -- warm-up: compile once, then run a few warm iterations. --
    print("\nWarm-up (compilation + first-run)...")
    b0 = bodies_data[0]

    t0 = time.perf_counter()
    _, Q_warm = _wall_gpu(
        jit_full,
        b0["normals"],
        b0["centroids"],
        b0["areas"],
        b0["k_hat"],
        b0["psi"],
        b0["element_index"],
        n_tilde,
        SIGMA_SKIN,
        FREQ_HZ,
        int(array.n_elements),
    )
    t_compile_full = time.perf_counter() - t0
    print(f"  full   stage compile + 1 call: {t_compile_full * 1e3:.1f} ms  (Q shape: {Q_warm.shape})")

    t0 = time.perf_counter()
    _, _ = _wall_gpu(
        jit_fresnel,
        b0["normals"],
        b0["k_hat"],
        n_tilde,
    )
    t_compile_fresnel = time.perf_counter() - t0
    print(f"  fresnel stage compile + 1 call: {t_compile_fresnel * 1e3:.1f} ms")

    t0 = time.perf_counter()
    _, G_warm = _wall_gpu(
        jit_body_ch,
        b0["normals"],
        b0["centroids"],
        b0["k_hat"],
        b0["psi"],
        b0["element_index"],
        n_tilde,
        SIGMA_SKIN,
        FREQ_HZ,
        int(array.n_elements),
    )
    t_compile_body = time.perf_counter() - t0
    print(f"  body_ch stage compile + 1 call: {t_compile_body * 1e3:.1f} ms")

    t0 = time.perf_counter()
    _, _ = _wall_gpu(jit_gram, G_warm, b0["areas"])
    t_compile_gram = time.perf_counter() - t0
    print(f"  gram   stage compile + 1 call: {t_compile_gram * 1e3:.1f} ms")

    # Two more warm runs on b0 for the full pipeline.
    for _ in range(N_WARMUP - 1):
        _wall_gpu(
            jit_full,
            b0["normals"],
            b0["centroids"],
            b0["areas"],
            b0["k_hat"],
            b0["psi"],
            b0["element_index"],
            n_tilde,
            SIGMA_SKIN,
            FREQ_HZ,
            int(array.n_elements),
        )

    # -- steady-state: N_STEADY runs of the full 50-body refresh ----------------
    print(f"\nSteady-state: {N_STEADY} runs of full 50-body Q refresh...")
    per_refresh_total = []
    per_body_timings = []

    for run in range(N_STEADY):
        t_run = time.perf_counter()
        Q_results = []
        body_times = []
        for b in bodies_data:
            dt, Q = _wall_gpu(
                jit_full,
                b["normals"],
                b["centroids"],
                b["areas"],
                b["k_hat"],
                b["psi"],
                b["element_index"],
                n_tilde,
                SIGMA_SKIN,
                FREQ_HZ,
                int(array.n_elements),
            )
            body_times.append(dt)
            Q_results.append(Q)
        jax.block_until_ready(Q_results)
        t_total = time.perf_counter() - t_run
        per_refresh_total.append(t_total)
        per_body_timings.append(body_times)
        if run < 3 or run == N_STEADY - 1:
            med_body = statistics.median(body_times)
            print(f"  run {run + 1:2d}: total {t_total * 1e3:.2f} ms  (median per-body {med_body * 1e3:.3f} ms)")

    # -- per-stage breakdown on body 0 -----------------------------------------
    print("\nPer-stage breakdown (body 0, steady state, n=30 each)...")

    # Take body 0 and time each stage separately.
    n_stage = 30

    def _time_many(fn, args, n=n_stage):
        # drop one warm call per stage in case jit didn't survive
        out = fn(*args)
        jax.block_until_ready(out)
        ts = []
        for _ in range(n):
            t0 = time.perf_counter()
            out = fn(*args)
            jax.block_until_ready(out)
            ts.append(time.perf_counter() - t0)
        return ts

    fresnel_args = (b0["normals"], b0["k_hat"], n_tilde)
    body_ch_args = (
        b0["normals"],
        b0["centroids"],
        b0["k_hat"],
        b0["psi"],
        b0["element_index"],
        n_tilde,
        SIGMA_SKIN,
        FREQ_HZ,
        int(array.n_elements),
    )
    full_args = (
        b0["normals"],
        b0["centroids"],
        b0["areas"],
        b0["k_hat"],
        b0["psi"],
        b0["element_index"],
        n_tilde,
        SIGMA_SKIN,
        FREQ_HZ,
        int(array.n_elements),
    )

    t_fresnel_body = _time_many(jit_fresnel, fresnel_args)
    # For gram stage we need a fresh G_tilde.
    G0 = jit_body_ch(*body_ch_args)
    jax.block_until_ready(G0)
    gram_args = (G0, b0["areas"])
    t_body_ch = _time_many(jit_body_ch, body_ch_args)
    t_gram = _time_many(jit_gram, gram_args)
    t_full_one = _time_many(jit_full, full_args)

    def _stats(ts):
        arr = np.array(ts) * 1e3  # ms
        return {
            "median_ms": float(np.median(arr)),
            "p10_ms": float(np.percentile(arr, 10)),
            "p90_ms": float(np.percentile(arr, 90)),
            "mean_ms": float(np.mean(arr)),
            "min_ms": float(np.min(arr)),
            "max_ms": float(np.max(arr)),
            "n": int(arr.size),
        }

    # Factored-Fresnel reference: run Fresnel on N_center directions only.
    c0 = centers_data[0]
    fresnel_center_args = (c0["normals"], c0["k_hat"], n_tilde)
    # Warm
    _ = jit_fresnel(*fresnel_center_args)
    jax.block_until_ready(_)
    t_fresnel_center = _time_many(jit_fresnel, fresnel_center_args)

    stage_stats = {
        "fresnel_body0_N640_expanded": _stats(t_fresnel_body),
        "fresnel_body0_N10_center_only": _stats(t_fresnel_center),
        "body_channel_body0": _stats(t_body_ch),
        "gram_body0": _stats(t_gram),
        "full_body0": _stats(t_full_one),
    }
    # Derive surface-integration-only = body_channel - fresnel (median-based)
    stage_stats["surface_integration_body0_derived"] = {
        "median_ms": stage_stats["body_channel_body0"]["median_ms"]
        - stage_stats["fresnel_body0_N640_expanded"]["median_ms"],
        "note": "body_channel minus fresnel medians; a JIT-fused upper bound",
    }

    # Per-body loop overhead: 50 empty jit dispatches.
    @jax.jit
    def _noop(x):
        return x + 1.0

    zdev = jnp.float32(0.0)
    _noop(zdev).block_until_ready()
    t0 = time.perf_counter()
    for _ in range(N_BODIES):
        out = _noop(zdev)
    out.block_until_ready()
    loop_overhead_ms = (time.perf_counter() - t0) * 1e3
    stage_stats["python_loop_overhead_50_dispatches_ms"] = loop_overhead_ms

    # -- aggregate stats across the 50-body refresh runs -----------------------
    arr_totals = np.array(per_refresh_total) * 1e3  # ms
    arr_per_body = np.array(per_body_timings) * 1e3  # (N_STEADY, 50) ms

    refresh_stats = {
        "median_ms": float(np.median(arr_totals)),
        "p10_ms": float(np.percentile(arr_totals, 10)),
        "p90_ms": float(np.percentile(arr_totals, 90)),
        "mean_ms": float(np.mean(arr_totals)),
        "min_ms": float(np.min(arr_totals)),
        "max_ms": float(np.max(arr_totals)),
        "n_runs": int(arr_totals.size),
    }
    per_body_stats = {
        "median_ms": float(np.median(arr_per_body)),
        "p10_ms": float(np.percentile(arr_per_body, 10)),
        "p90_ms": float(np.percentile(arr_per_body, 90)),
        "mean_ms": float(np.mean(arr_per_body)),
    }

    warmup_stats = {
        "first_full_call_ms": t_compile_full * 1e3,
        "first_fresnel_call_ms": t_compile_fresnel * 1e3,
        "first_body_channel_call_ms": t_compile_body * 1e3,
        "first_gram_call_ms": t_compile_gram * 1e3,
        "comment": "Includes JAX tracing, XLA compilation, and first-time CUDA kernel launch.",
    }

    result = {
        "scenario": {
            "carrier_ghz": FREQ_HZ / 1e9,
            "bs_array": f"{N_H}x{N_V} UPA",
            "m_ant": int(array.n_elements),
            "n_bodies": N_BODIES,
            "n_triangles_per_body": n_tri_per_body,
            "n_center_paths_per_body": N_CENTER_PATHS,
            "n_expanded_paths_per_body": n_paths_per_body,
            "phantom": base.name,
            "ring_min_m": RING_MIN_M,
            "ring_max_m": RING_MAX_M,
            "tissue_eps_r": EPS_R_SKIN,
            "tissue_sigma": SIGMA_SKIN,
            "rng_seed": RNG_SEED,
        },
        "environment": {
            "jax_version": jax.__version__,
            "jax_backend": jax.default_backend(),
            "jax_devices": [str(d) for d in devices],
            "device_platform": device.platform,
            "device_kind": getattr(device, "device_kind", "gpu"),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "aegis_array_backend": os.environ.get("AEGIS_ARRAY_BACKEND"),
            "gpu_info": gpu_info,
        },
        "warmup": warmup_stats,
        "steady_state": {
            "fifty_body_refresh_ms": refresh_stats,
            "per_body_ms": per_body_stats,
            "per_stage_body0_ms": stage_stats,
            "raw_totals_ms": arr_totals.tolist(),
            "raw_per_body_ms": arr_per_body.tolist(),
        },
    }

    out_json.write_text(json.dumps(result, indent=2))
    print(f"\nWrote {out_json}")

    # -- summary --------------------------------------------------------------
    r = refresh_stats
    pb = per_body_stats
    st = stage_stats
    print("\n=== SUMMARY ===")
    print(
        f"50-body Q refresh: median {r['median_ms']:.2f} ms,  "
        f"p10 {r['p10_ms']:.2f},  p90 {r['p90_ms']:.2f}  (n={r['n_runs']})"
    )
    print(
        f"Per body (flattened across runs): median {pb['median_ms']:.3f} ms, "
        f"p10 {pb['p10_ms']:.3f}, p90 {pb['p90_ms']:.3f}"
    )
    print(f"Stages (body 0, ms median, n={st['fresnel_body0_N640_expanded']['n']}):")
    print(
        f"  Fresnel tensor (N=640):{st['fresnel_body0_N640_expanded']['median_ms']:.3f}"
        f"  (expanded paths, non-factored path)"
    )
    print(
        f"  Fresnel tensor (N= 10):{st['fresnel_body0_N10_center_only']['median_ms']:.3f}"
        f"  (center paths only; factored reference)"
    )
    print(f"  Body channel G_tilde:  {st['body_channel_body0']['median_ms']:.3f}  (includes Fresnel)")
    print(f"  Surface-int only:      {st['surface_integration_body0_derived']['median_ms']:.3f}  (derived)")
    print(f"  Gram accumulation Q:   {st['gram_body0']['median_ms']:.3f}")
    print(f"  Full per-body:         {st['full_body0']['median_ms']:.3f}")
    print(f"  Python loop overhead (50 noop jit dispatches): {st['python_loop_overhead_50_dispatches_ms']:.3f} ms")
    print(f"Warm-up cost (first jit'd call, full):  {warmup_stats['first_full_call_ms']:.1f} ms")

    hits_100 = r["p90_ms"] <= 100.0
    hits_10 = r["p90_ms"] <= 10.0
    print(f"Fits 100 ms pose cadence? {'YES' if hits_100 else 'NO'}")
    print(f"Fits  10 ms slot cadence? {'YES' if hits_10 else 'NO'}")

    return result


if __name__ == "__main__":
    main()
