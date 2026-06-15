"""Offline precompute for the Coherent Exposure Studio data layer.

Regenerates the studio's data packs (ray packs, phantom pack, per-triangle
body-map packs, ensemble packs) from the coherent-exposure-operator paper's
e11 pipeline, so the runtime viewer can render them without ever touching the
ray tracer or the paper fork.

OFFLINE-ONLY FORK COUPLING
--------------------------
This is the single place in the AEGIS tree that imports the paper fork
(``papers/coherent-exposure-operator``). It does so to reproduce the EXACT e11
world geometry (scene, BS array, placed/decimated phantom) and, when a ray pack
is missing, to retrace it with Sionna RT. The runtime viewer
(``src/aegis/viewer/routes/studio``) must NEVER import the fork; it reads only
the packs this script writes. Physics (body channel, exposure operator, ECBF,
worst-case map, field synthesis) comes from the live ``aegis.*`` packages, not
the fork's vendored snapshot.

Coordinate frame: the e11 world frame, Z-up, metres. BS at (-13, 0, 3), 16x16
URA at 28 GHz; body feet at z=0, faces -x toward the BS; UE index 4 (14 m).

Usage
-----
    python scripts/studio_precompute.py --sync-rays --phantom --bodymaps \\
        --conditions los --arrays 16 --freqs 10 28 --beams floor mrt worstcase amp

Subcommands (combine freely):
    --sync-rays   copy/trace BS->UE ray packs into <studio>/rays/
    --phantom     export the placed, decimated thelonious mesh
    --bodymaps    compute per-triangle body maps for each (condition, array,
                  freq, beam)
    --ensemble    mean and p95 of each body-map quantity over LOS seeds
    --qoperator   precompute the exposure operator Q (M_ant x M_ant) for each
                  (condition, array, freq) so the runtime can do a fast ECBF
                  solve without rebuilding the full-body tissue channel
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
FORK_ROOT = REPO_ROOT / "papers" / "coherent-exposure-operator" / "code"

UE_IDX = 4  # the 14 m UE, mid-corridor (e11 convention)
BEAMS = ("floor", "mrt", "worstcase", "amp", "ecbf")
ENSEMBLE_SEEDS = (0, 1, 2, 3, 4, 5)
ECBF_BUDGET_FRAC = 0.5  # P_abs_max as a fraction of the MRT absorbed power

# IT'IS v5.0 Gabriel 4-pole Cole-Cole skin (eps_r, sigma [S/m]) per dosimetry
# frequency, copied verbatim from SKIN_BY_GHZ in the paper fork's
# code/scripts/e11b_freq_sweep.py (same source/convention as SKIN_28GHZ). The
# ray geometry stays fixed at 28 GHz; only the tissue response moves with freq.
SKIN_BY_GHZ = {
    8.0: (33.18, 5.82),
    10.0: (31.29, 8.01),
    12.0: (29.33, 10.34),
    15.0: (26.40, 13.85),
    20.0: (21.96, 19.22),
    28.0: (16.55, 25.82),
}


# --------------------------------------------------------------------------
# Offline-only fork bootstrap
# --------------------------------------------------------------------------
def _bootstrap_fork() -> None:
    """Prepend the paper fork's scripts + lib to sys.path (offline only).

    Raises a clear error if the fork is absent, since this is the
    regenerate-from-source path and there is no runtime fallback.
    """
    scripts = FORK_ROOT / "scripts"
    lib = FORK_ROOT / "lib"
    if not scripts.is_dir() or not lib.is_dir():
        raise SystemExit(
            "error: paper fork not found at "
            f"{FORK_ROOT}. studio_precompute regenerates studio packs from the "
            "coherent-exposure-operator paper source and cannot run without it. "
            "This fork coupling is OFFLINE-ONLY; the runtime viewer never needs it."
        )
    for p in (str(lib), str(scripts)):
        if p not in sys.path:
            sys.path.insert(0, p)


# --------------------------------------------------------------------------
# Geometry helpers (the e11 recipe, reproduced for the studio frame)
# --------------------------------------------------------------------------
def _skin_focus_point(spec, body, height_frac: float = 0.62) -> np.ndarray:
    """BS-facing body-surface point at ~62% of body height (upper torso).

    Reproduces ``skin_focus_point`` from the fork's e11_hotspot_tomography.py:
    the front-facing triangle whose centroid is nearest the upper-chest height
    and the body midline. Geometry only, deterministic.
    """
    bs = np.asarray(spec.bs_position, float)
    ue = np.asarray(spec.ue_positions[UE_IDX], float)
    cen = body.centroids
    nrm = body.normals
    bmin, bmax = body.bounding_box
    chest_z = bmin[2] + height_frac * (bmax[2] - bmin[2])
    to_bs = bs[None, :] - cen
    to_bs /= np.linalg.norm(to_bs, axis=1, keepdims=True)
    facing = np.einsum("ij,ij->i", nrm, to_bs) > 0.3
    score = np.where(facing, np.abs(cen[:, 2] - chest_z) + np.abs(cen[:, 1] - ue[1]), 1e9)
    return cen[int(np.argmin(score))]


def _skin_props(freq_ghz: float) -> tuple[complex, float]:
    """Complex refractive index and conductivity of skin at a frequency."""
    from aegis.tissue.dielectric import SKIN_28GHZ
    from aegis.tissue.fresnel import n_complex

    if abs(freq_ghz - 28.0) < 1e-9:
        return complex(SKIN_28GHZ.n_complex), float(SKIN_28GHZ.sigma)
    if freq_ghz not in SKIN_BY_GHZ:
        raise SystemExit(
            f"error: no skin dielectric for {freq_ghz} GHz. Known: "
            f"{sorted(SKIN_BY_GHZ)} (or 28). Add it to SKIN_BY_GHZ."
        )
    eps_r, sigma = SKIN_BY_GHZ[freq_ghz]
    return complex(n_complex(eps_r, sigma, freq_ghz * 1e9)), float(sigma)


# --------------------------------------------------------------------------
# Ray packs
# --------------------------------------------------------------------------
def _rays_path(studio_dir: Path, bs_n: int, condition: str, seed: int) -> Path:
    return studio_dir / "rays" / f"bs{bs_n}_{condition}_seed{seed}.npz"


def _trace_pack(out: Path, bs_n: int, condition: str, seed: int) -> None:
    """Trace one BS->UE ray pack with Sionna RT into the studio dir.

    Mirrors the fork's e11.trace_paths but writes to the studio data dir (the
    fork tree stays read-only). Only invoked when a requested pack is absent
    from the fork's cache.
    """
    _bootstrap_fork()
    # sionna.rt first so it selects the right Mitsuba variant before mitsuba is
    # imported anywhere downstream; keep this order (do not let isort reflow it).
    import sionna.rt  # noqa: F401, I001
    import e8_scene_setup as scene_lib  # noqa: I001
    from e8_rt_runner import bs_element_positions, scene_spec_to_sionna_scene  # noqa: I001
    from paper_aegis.integration.sionna import paths_from_sionna_scene  # noqa: I001

    with_blocker = condition == "nlos"
    spec = scene_lib.build_scene(with_blocker=with_blocker, seed=seed, bs_n=bs_n)
    rx = np.asarray(spec.ue_positions[UE_IDX], float)
    scene = scene_spec_to_sionna_scene(spec, with_blocker=with_blocker)
    tx = bs_element_positions(spec)
    paths = paths_from_sionna_scene(
        scene=scene,
        tx_positions=tx,
        rx_position=rx,
        freq_hz=float(scene_lib.BS_FREQ_HZ),
        max_bounces=5,
        tx_power_dbm=25.0,
        tx_pattern="isotropic",
        return_viz=False,
        los=True,
        specular_reflection=True,
        diffuse_reflection=False,
        refraction=True,
        diffraction=True,
        synthetic_array=True,
        seed=42,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out,
        k_hat=np.asarray(paths.k_hat),
        psi=np.asarray(paths.psi),
        element_index=np.asarray(paths.element_index).astype(int),
        n_elements=bs_n * bs_n,
    )
    print(f"  traced  {out.name}")


def sync_rays(studio_dir: Path, arrays: list[int], conditions: list[str], seeds: list[int]) -> None:
    """Copy ray packs from the fork's cache, tracing any that are missing.

    NLOS has a single realisation in the fork (``bs{N}_nlos_seed0.npz``); the
    multi-seed ensemble is LOS-only. So for NLOS we sync only seed 0 and never
    attempt to trace the other seeds (a stray NLOS trace would also exhaust the
    box). LOS keeps the full requested seed list.
    """
    from aegis.viewer.routes.studio._config import paper_fork_paths_dir

    fork_dir = paper_fork_paths_dir()
    (studio_dir / "rays").mkdir(parents=True, exist_ok=True)
    for bs_n in arrays:
        for cond in conditions:
            cond_seeds = [0] if cond == "nlos" else seeds
            for seed in cond_seeds:
                dst = _rays_path(studio_dir, bs_n, cond, seed)
                src = fork_dir / f"bs{bs_n}_{cond}_seed{seed}.npz" if fork_dir else None
                if src is not None and src.exists():
                    shutil.copy2(src, dst)
                    print(f"  copied  {dst.name}")
                elif dst.exists():
                    print(f"  present {dst.name}")
                else:
                    print(f"  missing in fork, tracing {dst.name}")
                    _trace_pack(dst, bs_n, cond, seed)


def _load_rays(studio_dir: Path, bs_n: int, condition: str, seed: int):
    path = _rays_path(studio_dir, bs_n, condition, seed)
    if not path.exists():
        raise SystemExit(f"error: ray pack {path} not found. Run --sync-rays first.")
    d = np.load(path)
    return (
        np.asarray(d["k_hat"]),
        np.asarray(d["psi"]),
        np.asarray(d["element_index"]).astype(int),
        int(d["n_elements"]),
    )


# --------------------------------------------------------------------------
# Phantom
# --------------------------------------------------------------------------
def _load_body(bs_n: int):
    """Load the placed, full-resolution thelonious phantom in the e11 world frame.

    Replicates the fork's ``load_phantom_at_ue`` placement (translate so feet
    are at z=0 and centre at the UE xy). The full mesh (~23.8k triangles) is
    kept: the previous ``np.linspace`` index-decimation to 8000 faces
    threw away two thirds of the faces at scattered indices, leaving a
    non-manifold scatter (~15% shared edges) that rendered as a holey body.
    Every downstream build (``_compute_g_tilde``, ``_compute_q_chunked``) is
    already triangle-chunked, so the working set is capped by ``chunk`` and is
    independent of the triangle count; full resolution only costs wall-clock,
    not memory, and the served mesh is now a coherent closed surface.

    Deliberately avoids importing the fork's e8_rt_runner module, whose
    top-level ``import sionna.rt`` pulls in TensorFlow and exhausts memory; only
    ``build_scene`` (pure numpy) and the vendored ``BodyMesh`` are needed here.
    Placement depends only on the deterministic UE xy, so geometry is identical
    across conditions and seeds.
    """
    _bootstrap_fork()
    import e8_scene_setup as scene_lib
    from paper_aegis.geometry.mesh import BodyMesh

    spec = scene_lib.build_scene(with_blocker=False, seed=0, bs_n=bs_n)
    stl = str(FORK_ROOT.parent / "data" / "thelonious.stl")
    mesh = BodyMesh.load(stl, name="thelonious")
    bb_min, bb_max = mesh.bounding_box
    ue_x, ue_y, _ = spec.ue_positions[UE_IDX]
    new_v = mesh.vertices.copy()
    new_v[:, :, 0] -= (bb_min[0] + bb_max[0]) / 2
    new_v[:, :, 1] -= (bb_min[1] + bb_max[1]) / 2
    new_v[:, :, 2] -= bb_min[2]
    new_v[:, :, 0] += ue_x
    new_v[:, :, 1] += ue_y
    body = BodyMesh.from_arrays(new_v, normals=mesh.normals, name=f"thelonious_at_UE{UE_IDX}")
    return spec, body


def export_phantom(studio_dir: Path, bs_n: int) -> None:
    """Export the placed phantom mesh to <studio>/phantom/thelonious.npz."""
    _, body = _load_body(bs_n)
    tri = np.asarray(body.vertices, float)  # (M, 3, 3) per-triangle vertices
    m = tri.shape[0]
    vertices = tri.reshape(-1, 3).astype(np.float32)  # (3M, 3)
    faces = np.arange(3 * m, dtype=np.int32).reshape(m, 3)  # face order == body order
    out = studio_dir / "phantom" / "thelonious.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out,
        vertices=vertices,
        faces=faces,
        centroids=np.asarray(body.centroids, np.float32),
        normals=np.asarray(body.normals, np.float32),
        areas=np.asarray(body.areas, np.float32),
    )
    print(f"  wrote {out} (V={vertices.shape[0]}, M={m})")


# --------------------------------------------------------------------------
# Body maps
# --------------------------------------------------------------------------
def _mrt_precoder(focus, k, psi, elem, freq_hz, m, ue_rx, power: float = 1.0):
    from aegis.hotspot import channel_at

    h = channel_at(focus, k, psi, elem, freq_hz, m, rx_response=ue_rx)
    return np.sqrt(power) * np.conj(h) / np.linalg.norm(h)


def _deposited_sab(g_tilde: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Per-triangle deposited S_ab = sum_axis |G_tilde @ x|^2."""
    return (np.abs(np.einsum("tim,m->ti", g_tilde, x)) ** 2).sum(axis=1)


def _compute_g_tilde(body, k, psi, elem, m, n_tilde, sigma, freq_hz, chunk: int = 128) -> np.ndarray:
    """Build the tissue channel G_tilde (T, 3, M_ant) in triangle chunks.

    Chunking is essential: ``compute_body_channel`` forms a per-path
    (T, N, 3) intermediate, and with N ~ 67k paths an unchunked 8000-triangle
    build needs ~26 GB. Chunking caps the working set and the result is
    bit-identical to a single call.
    """
    from aegis.coherent.body_channel import compute_body_channel

    t = body.normals.shape[0]
    g = np.empty((t, 3, m), dtype=complex)
    for a in range(0, t, chunk):
        b = min(a + chunk, t)
        g[a:b] = np.asarray(
            compute_body_channel(body.normals[a:b], body.centroids[a:b], k, psi, elem, n_tilde, sigma, freq_hz, m)
        )
    return g


def _maps_from_g(g_tilde: np.ndarray, body, beams, focus, k, psi, elem, m, freq_hz, ue_rx) -> dict[str, np.ndarray]:
    """Derive every requested per-triangle body map from one G_tilde build.

    ``floor`` is the phase-blind expected deposition under an equal-amplitude,
    random-phase unit-power precoder (E[|G x|^2] = ||G||_F^2 / M_ant per
    triangle). ``worstcase`` is lambda_max(G_tilde^H G_tilde) per triangle (the
    top singular value squared, precoder-independent, identical to
    ``worst_case_body``). ``mrt`` and ``ecbf`` are the deposited S_ab under the
    MRT and ECBF precoders to the chest focus at matched power. ``amp`` is
    worstcase / floor.
    """
    from aegis.coherent import compute_exposure_operator, solve_ecbf
    from aegis.hotspot import channel_at

    beams = set(beams)
    out: dict[str, np.ndarray] = {}

    floor = None
    if {"floor", "amp"} & beams:
        floor = (np.abs(g_tilde) ** 2).sum(axis=(1, 2)) / m
        if "floor" in beams:
            out["floor"] = floor
    if {"worstcase", "amp"} & beams:
        s = np.linalg.svd(g_tilde, compute_uv=False)  # (T, 3)
        worstcase = s[:, 0] ** 2
        if "worstcase" in beams:
            out["worstcase"] = worstcase
        if "amp" in beams:
            out["amp"] = worstcase / np.maximum(floor, 1e-30)
    if "mrt" in beams:
        x = _mrt_precoder(focus, k, psi, elem, freq_hz, m, ue_rx)
        out["mrt"] = _deposited_sab(g_tilde, x)
    if "ecbf" in beams:
        q = np.asarray(compute_exposure_operator(g_tilde, body.areas))
        h = channel_at(focus, k, psi, elem, freq_hz, m, rx_response=ue_rx)
        x_mrt = _mrt_precoder(focus, k, psi, elem, freq_hz, m, ue_rx)
        p_abs_mrt = float(np.real(x_mrt.conj() @ q @ x_mrt))
        x = np.asarray(solve_ecbf(h, q, ECBF_BUDGET_FRAC * p_abs_mrt, 1.0))
        out["ecbf"] = _deposited_sab(g_tilde, x)
    return out


_QUANTITY = {
    "floor": ("Sab_floor", "W/m^2 per W"),
    "mrt": ("Sab_mrt", "W/m^2 per W"),
    "worstcase": ("Sab_worstcase", "W/m^2 per W"),
    "ecbf": ("Sab_ecbf", "W/m^2 per W"),
    "amp": ("amplification", "ratio"),
}


def _ghz_tag(freq_ghz: float) -> str:
    return f"{freq_ghz:g}"


def _atomic_savez(out: Path, **arrays) -> None:
    """Write an .npz atomically: savez to a tmp file, then os.replace.

    A crash or interrupt mid-write leaves the tmp file, never a truncated or
    half-written pack at ``out``. ``os.replace`` is atomic on the same
    filesystem, and the tmp file is created in the destination dir so the
    rename never crosses devices. The tmp name ends in ``.npz`` so numpy does
    not append a second extension.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=out.stem + ".", suffix=".npz")
    os.close(fd)
    try:
        np.savez(tmp, **arrays)
        os.replace(tmp, out)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _write_map(out: Path, values: np.ndarray, beam: str, provenance: str) -> None:
    quantity, units = _QUANTITY[beam]
    values = np.asarray(values, np.float32)
    _atomic_savez(
        out,
        values=values,
        vmin=np.float32(values.min()),
        vmax=np.float32(values.max()),
        units=units,
        quantity=quantity,
        mesh="thelonious",
        provenance=provenance,
    )


def compute_bodymaps(
    studio_dir: Path,
    arrays: list[int],
    conditions: list[str],
    freqs: list[float],
    beams: list[str],
    seed: int = 0,
) -> None:
    """Compute and write per-triangle body maps for each combination."""
    from aegis.hotspot import make_rx_response

    for bs_n in arrays:
        spec, body = _load_body(bs_n)
        focus = _skin_focus_point(spec, body)
        for cond in conditions:
            k, psi, elem, m = _load_rays(studio_dir, bs_n, cond, seed)
            for freq_ghz in freqs:
                n_tilde, sigma = _skin_props(freq_ghz)
                freq_hz = freq_ghz * 1e9
                ue_rx = make_rx_response("dipole", freq_hz)
                g_tilde = _compute_g_tilde(body, k, psi, elem, m, n_tilde, sigma, freq_hz)
                maps = _maps_from_g(g_tilde, body, beams, focus, k, psi, elem, m, freq_hz, ue_rx)
                tag = _ghz_tag(freq_ghz)
                for beam in beams:
                    values = maps[beam]
                    out = studio_dir / "bodymaps" / f"{cond}_bs{bs_n}_{beam}_{tag}.npz"
                    prov = (
                        f"studio_precompute {beam} cond={cond} bs{bs_n} {tag}GHz seed={seed} "
                        f"| e11 recipe | focus={np.round(focus, 4).tolist()}"
                    )
                    _write_map(out, values, beam, prov)
                    print(f"  wrote {out.name}: shape={values.shape} vmin={values.min():.4e} vmax={values.max():.4e}")


# --------------------------------------------------------------------------
# Ensemble (over LOS seeds)
# --------------------------------------------------------------------------
def compute_ensemble(
    studio_dir: Path,
    arrays: list[int],
    freqs: list[float],
    beams: list[str],
) -> None:
    """Mean and p95 of each body-map quantity over the available LOS seeds."""
    from aegis.hotspot import make_rx_response

    cond = "los"
    for bs_n in arrays:
        spec, body = _load_body(bs_n)
        focus = _skin_focus_point(spec, body)
        present = [s for s in ENSEMBLE_SEEDS if _rays_path(studio_dir, bs_n, cond, s).exists()]
        if not present:
            print(f"  no LOS ray packs for bs{bs_n}, skipping ensemble")
            continue
        k_count = len(present)
        for freq_ghz in freqs:
            n_tilde, sigma = _skin_props(freq_ghz)
            freq_hz = freq_ghz * 1e9
            ue_rx = make_rx_response("dipole", freq_hz)
            tag = _ghz_tag(freq_ghz)
            per_seed: dict[str, list[np.ndarray]] = {beam: [] for beam in beams}
            for s in present:
                k, psi, elem, m = _load_rays(studio_dir, bs_n, cond, s)
                g_tilde = _compute_g_tilde(body, k, psi, elem, m, n_tilde, sigma, freq_hz)
                maps = _maps_from_g(g_tilde, body, beams, focus, k, psi, elem, m, freq_hz, ue_rx)
                for beam in beams:
                    per_seed[beam].append(maps[beam])
            for beam in beams:
                stack = np.asarray(per_seed[beam])  # (K, M)
                mean_v = stack.mean(axis=0)
                p95_v = np.percentile(stack, 95, axis=0)
                base = f"{cond}_bs{bs_n}_{beam}_{tag}"
                prov = (
                    f"studio_precompute ensemble {beam} cond={cond} bs{bs_n} {tag}GHz "
                    f"| LOS seeds {present} (K={k_count})"
                )
                _write_map(studio_dir / "ensemble" / f"{base}_mean{k_count}.npz", mean_v, beam, prov + " | mean")
                _write_map(studio_dir / "ensemble" / f"{base}_p95.npz", p95_v, beam, prov + " | p95")
                print(f"  wrote {base}_mean{k_count}.npz and {base}_p95.npz (K={k_count})")


# --------------------------------------------------------------------------
# Exposure operator Q
# --------------------------------------------------------------------------
def _compute_q_chunked(body, k, psi, elem, m, n_tilde, sigma, freq_hz, chunk: int = 128) -> np.ndarray:
    """Accumulate the exposure operator Q (M_ant x M_ant) in triangle chunks.

    Q = sum_t area_t * G_tilde_t^H @ G_tilde_t is linear in the per-triangle
    contributions (see ``compute_exposure_operator``), so summing the operators
    of disjoint triangle chunks is exact and equals the full-body Q. Building
    G_tilde one 128-triangle chunk at a time keeps the working set tiny: the
    full (T, N, 3) channel for ~8000 triangles and ~67k paths would be ~26 GB,
    which swap-kills the box, but a single chunk's contribution to the running
    256x256 accumulator is negligible.
    """
    from aegis.coherent import compute_exposure_operator
    from aegis.coherent.body_channel import compute_body_channel

    t = body.normals.shape[0]
    q = np.zeros((m, m), dtype=np.complex128)
    for a in range(0, t, chunk):
        b = min(a + chunk, t)
        g = np.asarray(
            compute_body_channel(body.normals[a:b], body.centroids[a:b], k, psi, elem, n_tilde, sigma, freq_hz, m)
        )
        q += np.asarray(compute_exposure_operator(g, body.areas[a:b]))
    # Each chunk operator is already Hermitian; the sum is too. Re-symmetrise to
    # scrub the last bit of floating-point asymmetry before serialising.
    return (q + np.conj(q).T) / 2


def compute_qoperators(
    studio_dir: Path,
    arrays: list[int],
    conditions: list[str],
    freqs: list[float],
    seed: int = 0,
) -> None:
    """Precompute and serialise the exposure operator Q for each scenario.

    Writes ``<studio>/qop/{condition}_bs{N}_{ghz}.npz`` with the Hermitian PSD
    operator so the runtime can run a fast small ECBF solve (x^H Q x) instead of
    rebuilding the full-body tissue channel (~8 min). Verifies Hermitian
    symmetry and positive-semidefiniteness before writing.
    """
    for bs_n in arrays:
        _, body = _load_body(bs_n)
        for cond in conditions:
            k, psi, elem, m = _load_rays(studio_dir, bs_n, cond, seed)
            for freq_ghz in freqs:
                n_tilde, sigma = _skin_props(freq_ghz)
                freq_hz = freq_ghz * 1e9
                q = _compute_q_chunked(body, k, psi, elem, m, n_tilde, sigma, freq_hz)
                herm_err = float(np.linalg.norm(q - np.conj(q).T))
                eigs = np.linalg.eigvalsh(q)
                min_eig = float(eigs.min())
                tag = _ghz_tag(freq_ghz)
                out = studio_dir / "qop" / f"{cond}_bs{bs_n}_{tag}.npz"
                prov = (
                    f"studio_precompute qoperator cond={cond} bs{bs_n} {tag}GHz seed={seed} "
                    f"| e11 recipe | Q=sum_t area_t G_t^H G_t (128-tri chunked)"
                )
                _atomic_savez(
                    out,
                    Q=np.asarray(q, np.complex128),
                    condition=cond,
                    array_n=np.int64(bs_n),
                    frequency_ghz=np.float64(freq_ghz),
                    provenance=prov,
                )
                print(
                    f"  wrote {out.name}: shape={q.shape} "
                    f"||Q-Q^H||={herm_err:.3e} min_eig={min_eig:.3e} "
                    f"lambda_max={float(eigs.max()):.3e}"
                )


# --------------------------------------------------------------------------
# Field channel G_tilde (for the live, focus-tracking body map)
# --------------------------------------------------------------------------
def _channel_path(studio_dir: Path, bs_n: int, condition: str, freq_ghz: float, seed: int) -> Path:
    return studio_dir / "channel" / f"{condition}_bs{bs_n}_{_ghz_tag(freq_ghz)}_seed{seed}.npz"


def compute_channels(
    studio_dir: Path,
    arrays: list[int],
    conditions: list[str],
    freqs: list[float],
    seeds: list[int],
) -> None:
    """Persist the per-triangle field channel G_tilde (T, 3, M) per scenario.

    Unlike the finished body-map packs (frozen at one focus), the channel is
    precoder-free: the runtime live-body-map endpoint loads it and applies the
    current precoder x to get deposited S_ab = sum|G_tilde @ x|^2 on the fly, so
    the served map tracks focus / beam / ECBF budget exactly the way the slice
    does. Stored as complex64: the build is complex128 but half precision is
    ample for a visualised map and halves the pack to ~150 MB. The build is
    triangle-chunked, so peak memory is independent of triangle count.
    """
    for bs_n in arrays:
        _, body = _load_body(bs_n)
        areas = np.asarray(body.areas, np.float32)
        for cond in conditions:
            for seed in seeds:
                if not _rays_path(studio_dir, bs_n, cond, seed).exists():
                    print(f"  no ray pack for bs{bs_n} {cond} seed{seed}, skipping")
                    continue
                k, psi, elem, m = _load_rays(studio_dir, bs_n, cond, seed)
                for freq_ghz in freqs:
                    n_tilde, sigma = _skin_props(freq_ghz)
                    freq_hz = freq_ghz * 1e9
                    g_tilde = _compute_g_tilde(body, k, psi, elem, m, n_tilde, sigma, freq_hz)
                    out = _channel_path(studio_dir, bs_n, cond, freq_ghz, seed)
                    prov = (
                        f"studio_precompute channel cond={cond} bs{bs_n} {_ghz_tag(freq_ghz)}GHz "
                        f"seed={seed} | G_tilde (T,3,M)={tuple(g_tilde.shape)} | e11 recipe"
                    )
                    _atomic_savez(
                        out,
                        g_tilde=np.asarray(g_tilde, np.complex64),
                        areas=areas,
                        n_elements=np.int32(m),
                        mesh="thelonious",
                        provenance=prov,
                    )
                    print(f"  wrote {out.name}: G_tilde={tuple(g_tilde.shape)} ({out.stat().st_size / 1e6:.0f} MB)")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sync-rays", action="store_true", help="copy/trace ray packs into <studio>/rays/")
    ap.add_argument("--phantom", action="store_true", help="export the placed thelonious mesh")
    ap.add_argument("--bodymaps", action="store_true", help="compute per-triangle body maps")
    ap.add_argument("--ensemble", action="store_true", help="mean/p95 over LOS seeds")
    ap.add_argument("--qoperator", action="store_true", help="precompute exposure operator Q packs")
    ap.add_argument("--channel", action="store_true", help="persist G_tilde field-channel packs (live body map)")
    ap.add_argument("--conditions", nargs="+", default=["los"], choices=["los", "nlos"])
    ap.add_argument("--arrays", nargs="+", type=int, default=[16])
    ap.add_argument("--freqs", nargs="+", type=float, default=[28.0], help="dosimetry frequencies [GHz]")
    ap.add_argument("--beams", nargs="+", default=["floor", "mrt", "worstcase", "amp"], choices=list(BEAMS))
    ap.add_argument("--seed", type=int, default=0, help="ray seed for the single-realisation body maps")
    ap.add_argument(
        "--sync-seeds",
        nargs="+",
        type=int,
        default=list(ENSEMBLE_SEEDS),
        help="seeds to sync/trace for --sync-rays",
    )
    args = ap.parse_args()

    from aegis.viewer.routes.studio._config import studio_data_dir

    studio_dir = studio_data_dir()
    print(f"studio data dir: {studio_dir}")

    if not any((args.sync_rays, args.phantom, args.bodymaps, args.ensemble, args.qoperator, args.channel)):
        ap.error("choose at least one of --sync-rays --phantom --bodymaps --ensemble --qoperator --channel")

    if args.sync_rays:
        print("[sync-rays]")
        sync_rays(studio_dir, args.arrays, args.conditions, args.sync_seeds)
    if args.phantom:
        print("[phantom]")
        for bs_n in args.arrays:
            export_phantom(studio_dir, bs_n)
    if args.bodymaps:
        print("[bodymaps]")
        compute_bodymaps(studio_dir, args.arrays, args.conditions, args.freqs, args.beams, seed=args.seed)
    if args.ensemble:
        print("[ensemble]")
        compute_ensemble(studio_dir, args.arrays, args.freqs, args.beams)
    if args.qoperator:
        print("[qoperator]")
        compute_qoperators(studio_dir, args.arrays, args.conditions, args.freqs, seed=args.seed)
    if args.channel:
        print("[channel]")
        compute_channels(studio_dir, args.arrays, args.conditions, args.freqs, args.sync_seeds)

    print("done")


if __name__ == "__main__":
    main()
