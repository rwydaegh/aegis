"""Empirical rank of the coherent exposure operator Q on Thelonious.

Produces the spectrum of Q for 20 body positions in a Brussels-plaza-like
scenario at 26 GHz with an 8x8 base-station panel.

Two path models are run for each body, to separate the two questions that
hide inside the paper's "rank-few" claim:

    A) Plaza-specular (as specified in the agent prompt): LOS + ground bounce
       + 2 facade specular reflections. rank(Q) is bounded above by 4 here,
       so this confirms the lower end of "3-10" but cannot falsify the upper
       end -- the rank ceiling is geometric, not physical.

    B) 3GPP 38.901 UMa-LOS stochastic channel: 12 clusters * 20 subpaths =
       240 physical arrival directions per body, with angular spread drawn
       from the 3GPP preset. rank(Q) is bounded above by 64 = M_ant here,
       so the empirical dominant rank reflects what the 8x8 array can
       actually resolve -- the stronger test of "rank-few".

Outputs:
    rank_cdf.{pdf,png}  -- spectra for both models (two panels)
    rank_table.md       -- epsilon-effective rank at eps in {1e-1, 1e-2, 1e-3}
    spectra.npz         -- raw eigenvalue matrices for both models
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# Make the in-repo 'aegis' package importable regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import matplotlib.pyplot as plt
import numpy as np

from aegis.channel.generator import generate_channel
from aegis.channel.presets import load_preset
from aegis.coherent.body_channel import compute_body_channel, compute_body_channel_factored
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    eigendecompose_Q,
)
from aegis.constants import C_0, Z_0
from aegis.geometry.mesh import BodyMesh
from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel

# ---------------------------------------------------------------------------
# Scenario constants
# ---------------------------------------------------------------------------
FREQ_HZ = 26.0e9
FREQ_GHZ = FREQ_HZ / 1e9
LAMBDA = C_0 / FREQ_HZ
N_H = 8
N_V = 8
D = LAMBDA / 2.0
BS_CENTER = np.array([0.0, 0.0, 8.0])
TILT_DEG = 10.0
BROADSIDE = np.array(
    [np.cos(np.deg2rad(TILT_DEG)), 0.0, -np.sin(np.deg2rad(TILT_DEG))]
)

FACADE_Y = 20.0

N_BODIES = 20
RANGE_MIN, RANGE_MAX = 20.0, 80.0
AZ_HALF_DEG = 60.0
RNG_SEED = 42

REFL_GROUND = 0.55
REFL_FACADE = 0.35

TX_POWER_W = 10.0
TX_POWER_DBM = 10.0 * np.log10(TX_POWER_W * 1e3)

PRESET_NAME = "3GPP_38.901_UMa_LOS"
PRESET_DIR = Path("/home/user/aegis/data/channel_presets")

# Tissue at 26 GHz
try:
    TISSUE = TissueModel.from_database("Skin", FREQ_HZ)
except Exception:  # noqa: BLE001
    TISSUE = TissueModel("Skin 26 GHz", eps_r=17.4, sigma=23.5, freq_hz=FREQ_HZ)


# ---------------------------------------------------------------------------
# Path builders
# ---------------------------------------------------------------------------
def _reflect_point(p: np.ndarray, plane_point: np.ndarray, plane_normal: np.ndarray) -> np.ndarray:
    d = np.dot(p - plane_point, plane_normal)
    return p - 2.0 * d * plane_normal


def _perpendicular_pol(k_hat: np.ndarray) -> np.ndarray:
    """A unit vector perpendicular to k_hat; arbitrary but consistent.

    The exact polarisation only changes phase alignment, not the dominant
    subspace rank, so an arbitrary consistent choice is fine for this test.
    """
    z = np.array([0.0, 0.0, 1.0])
    ref = z if abs(k_hat[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
    e = np.cross(k_hat, ref)
    return e / np.linalg.norm(e)


def build_specular_paths(
    bs_center: np.ndarray,
    body_target: np.ndarray,
    tx_power_w: float = TX_POWER_W,
) -> PropagationPaths:
    """LOS + ground + 2 facade specular bounces, image-method.

    Each path is the k_hat from the virtual source to the body target.
    Field amplitude: free-space 1/r with a per-bounce reflection coefficient.
    """
    sources = [
        ("los", bs_center, 1.0),
        (
            "ground",
            _reflect_point(bs_center, np.zeros(3), np.array([0.0, 0.0, 1.0])),
            REFL_GROUND,
        ),
        (
            "facade_plus",
            _reflect_point(bs_center, np.array([0.0, +FACADE_Y, 0.0]), np.array([0.0, -1.0, 0.0])),
            REFL_FACADE,
        ),
        (
            "facade_minus",
            _reflect_point(bs_center, np.array([0.0, -FACADE_Y, 0.0]), np.array([0.0, +1.0, 0.0])),
            REFL_FACADE,
        ),
    ]

    k_hats, psis, delays, is_los = [], [], [], []
    psi_1m = np.sqrt(2.0 * Z_0 * tx_power_w / (4.0 * np.pi))  # |E| at r=1 m

    for name, source, refl in sources:
        direction = body_target - source
        dist = float(np.linalg.norm(direction))
        k_hat = direction / dist
        amp = psi_1m * refl / dist
        e_pol = _perpendicular_pol(k_hat)
        psi = (amp * e_pol).astype(complex)

        k_hats.append(k_hat)
        psis.append(psi)
        delays.append(dist / C_0)
        is_los.append(name == "los")

    return PropagationPaths(
        k_hat=np.stack(k_hats),
        psi=np.stack(psis),
        element_index=np.zeros(len(sources), dtype=np.intp),
        delay=np.array(delays),
        is_los=np.array(is_los, dtype=bool),
    )


_PRESET_CACHE: dict | None = None


def _get_preset() -> dict:
    global _PRESET_CACHE
    if _PRESET_CACHE is None:
        _PRESET_CACHE = load_preset(PRESET_NAME, PRESET_DIR)
    return _PRESET_CACHE


STOCHASTIC_SUBPATHS = 5  # override 3GPP default (20) for speed; 12*5=60 paths


def build_stochastic_paths(
    bs_center: np.ndarray,
    body_target: np.ndarray,
    seed: int,
) -> PropagationPaths:
    """3GPP 38.901 UMa LOS stochastic subpath channel.

    Uses aegis.channel.generator.generate_channel with NumSubPaths reduced
    to 5 (vs 3GPP default 20) for runtime. Rank is bounded above by
    n_clusters*n_subpaths and by M_ant, so 60 subpaths vs 240 is still
    well above the anticipated dominant rank of 3-10.

    The returned paths are treated as centre-of-array paths to be expanded
    across the UPA via expand_paths_to_array.
    """
    paths = generate_channel(
        params=_get_preset(),
        freq_ghz=FREQ_GHZ,
        antenna_pos=bs_center,
        body_center=body_target,
        power_dbm=TX_POWER_DBM,
        seed=seed,
        overrides={"NumSubPaths": STOCHASTIC_SUBPATHS},
    )
    return paths


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def place_body(base_body: BodyMesh, offset_xy: np.ndarray) -> BodyMesh:
    v = base_body.vertices.reshape(-1, 3)
    z_min = float(v[:, 2].min())
    shift = np.array([offset_xy[0], offset_xy[1], -z_min])
    vertices = base_body.vertices + shift[None, None, :]
    centroids = base_body.centroids + shift[None, :]
    return BodyMesh(
        vertices=vertices,
        normals=base_body.normals.copy(),
        centroids=centroids,
        areas=base_body.areas.copy(),
        name=base_body.name,
    )


def sample_body_positions(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    r = np.sqrt(rng.uniform(RANGE_MIN**2, RANGE_MAX**2, size=n))
    az = rng.uniform(-np.deg2rad(AZ_HALF_DEG), np.deg2rad(AZ_HALF_DEG), size=n)
    return np.stack([r * np.cos(az), r * np.sin(az)], axis=1)


# ---------------------------------------------------------------------------
# Spectrum
# ---------------------------------------------------------------------------
# Always use the factored body-channel builder. The non-factored variant
# materialises a (M_tri, N_total, 3) complex array for stochastic channels,
# which peaks at ~10-15 GB per worker for this scene and has crashed the
# host under 4-way parallelism. The factored builder loops over N_center
# centre paths and never holds more than (M_tri, M_elements, 3) at once
# (~35 MB), so per-worker memory stays under 1 GB.
def compute_Q_spectrum(body: BodyMesh, array: AntennaArray, center_paths: PropagationPaths) -> np.ndarray:
    array_paths = expand_paths_to_array(center_paths, array, FREQ_HZ)
    G_tilde = compute_body_channel_factored(
        normals=body.normals,
        centroids=body.centroids,
        center_k_hat=center_paths.k_hat,
        center_psi=center_paths.psi,
        element_psi=array_paths.psi,
        element_index=array_paths.element_index,
        n_tilde=TISSUE.n_complex,
        sigma=TISSUE.sigma,
        freq_hz=FREQ_HZ,
        n_elements=array.n_elements,
    )
    Q = compute_exposure_operator(G_tilde, body.areas)
    eigenvalues, _ = eigendecompose_Q(Q)
    return np.asarray(eigenvalues, dtype=np.float64)


def epsilon_rank(spectrum: np.ndarray, eps: float) -> int:
    norm = spectrum / spectrum[0]
    return int(np.sum(norm >= eps))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
_WORKER_STATE: dict = {}


def _worker_init(thelonious_stl_path: str):
    """Process-pool initialiser: load the phantom and build the BS array once.

    Threads for BLAS are capped to 1 per worker to avoid over-subscription on
    the 16-core host (16 workers x 16 threads would thrash).
    """
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    thelonious = BodyMesh.load(thelonious_stl_path)
    array = AntennaArray.upa(
        n_h=N_H,
        n_v=N_V,
        d_h=D,
        d_v=D,
        center=BS_CENTER,
        broadside=BROADSIDE,
        element_pattern="patch",
    )
    _WORKER_STATE["thelonious"] = thelonious
    _WORKER_STATE["array"] = array


def _worker_task(job: tuple[str, int, tuple[float, float]]) -> tuple[int, str, np.ndarray, int]:
    """Compute Q spectrum for a single (model, body_idx, xy) job.

    Returns (body_idx, model_name, eigenvalues, n_paths).
    """
    model_name, body_idx, xy = job
    thelonious = _WORKER_STATE["thelonious"]
    array = _WORKER_STATE["array"]

    body = place_body(thelonious, np.asarray(xy))
    body_target = body.centroids.mean(axis=0)

    if model_name == "specular":
        center_paths = build_specular_paths(BS_CENTER, body_target)
    elif model_name == "stochastic":
        center_paths = build_stochastic_paths(
            BS_CENTER, body_target, seed=RNG_SEED + 1000 + body_idx
        )
    else:
        raise ValueError(f"unknown model {model_name!r}")

    eigs = compute_Q_spectrum(body, array, center_paths)
    return body_idx, model_name, eigs, center_paths.n_paths


def run_model_parallel(
    model_name: str,
    positions: np.ndarray,
    n_workers: int,
    thelonious_stl_path: str,
    M_ant: int,
) -> np.ndarray:
    """Dispatch all body spectra for a model across a ProcessPoolExecutor."""
    spectra = np.zeros((len(positions), M_ant), dtype=np.float64)
    jobs = [(model_name, i, tuple(xy)) for i, xy in enumerate(positions)]
    print(f"\n== Model: {model_name} ({len(jobs)} bodies, {n_workers} workers) ==")
    with ProcessPoolExecutor(
        max_workers=n_workers,
        initializer=_worker_init,
        initargs=(thelonious_stl_path,),
    ) as pool:
        for i, mname, eigs, n_paths in pool.map(_worker_task, jobs):
            spectra[i] = eigs
            xy = positions[i]
            lam1 = float(eigs[0])
            rel = eigs / lam1
            print(
                f"  body {i:2d} r={np.linalg.norm(xy):5.1f} m  "
                f"N_paths={n_paths:4d}  "
                f"lam1={lam1:.3e}  "
                f"lam2/lam1={rel[1]:.2e} lam5/lam1={rel[4]:.2e} lam10/lam1={rel[9]:.2e}",
                flush=True,
            )
    return spectra


def plot_panel(ax, spectra, title, M_ant):
    normalised = spectra / spectra[:, :1]
    k_axis = np.arange(1, M_ant + 1)
    median = np.median(normalised, axis=0)
    p10 = np.percentile(normalised, 10, axis=0)
    p90 = np.percentile(normalised, 90, axis=0)
    for i in range(len(spectra)):
        ax.semilogy(k_axis, np.maximum(normalised[i], 1e-300), color="0.7", alpha=0.55, linewidth=0.9)
    ax.semilogy(k_axis, np.maximum(median, 1e-300), color="C0", linewidth=2.2, label="median")
    ax.fill_between(
        k_axis,
        np.maximum(p10, 1e-300),
        np.maximum(p90, 1e-300),
        color="C0",
        alpha=0.18,
        label="10-90%",
    )
    for eps, style in [(1e-1, ":"), (1e-2, "--"), (1e-3, "-.")]:
        ax.axhline(eps, color="k", linewidth=0.8, linestyle=style, alpha=0.6,
                   label=rf"$\varepsilon={eps:g}$")
    ax.set_xlabel(r"eigenvalue index $k$")
    ax.set_ylabel(r"$\lambda_k / \lambda_1$")
    ax.set_title(title)
    ax.set_xlim(1, M_ant)
    ax.set_ylim(1e-17, 2.0)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper right", ncol=2, fontsize=7.5)


def main() -> None:
    out_dir = Path(__file__).parent
    print(f"output dir: {out_dir}")
    print(f"freq: {FREQ_GHZ:.1f} GHz, lambda: {LAMBDA * 1e3:.2f} mm, d: {D * 1e3:.2f} mm")
    print(f"array: {N_H}x{N_V} UPA, {N_H * N_V} elements, 10 deg down-tilt")
    print(f"tissue: {TISSUE.name} (eps_r={TISSUE.eps_r:.2f}, sigma={TISSUE.sigma:.2f} S/m)")

    thelonious_path = "/home/user/aegis/data/thelonious.stl"
    thelonious = BodyMesh.load(thelonious_path)
    print(f"thelonious: {thelonious.n_triangles} triangles, area {thelonious.total_area:.3f} m^2")

    M_ant = N_H * N_V

    positions = sample_body_positions(N_BODIES, RNG_SEED)
    body_ranges = np.linalg.norm(positions, axis=1)
    print(f"body ranges: min {body_ranges.min():.1f} m, max {body_ranges.max():.1f} m")

    # Worker count: kept very conservative. Each stochastic worker holds a
    # ~1.5 GB phase matrix plus its own Python/numpy state. The host has been
    # freezing when we ran with 10 workers; 4 is safely under memory limits
    # while still giving roughly 2.5x speedup over serial.
    n_workers = int(os.environ.get("RANK_CHECK_WORKERS", "4"))
    n_workers = min(N_BODIES, max(1, n_workers))

    # Model A: specular plaza
    spectra_spec = run_model_parallel(
        "specular",
        positions,
        n_workers=n_workers,
        thelonious_stl_path=thelonious_path,
        M_ant=M_ant,
    )

    # Model B: 3GPP UMa LOS stochastic
    spectra_sto = run_model_parallel(
        "stochastic",
        positions,
        n_workers=n_workers,
        thelonious_stl_path=thelonious_path,
        M_ant=M_ant,
    )

    np.savez(
        out_dir / "spectra.npz",
        spectra_specular=spectra_spec,
        spectra_stochastic=spectra_sto,
        positions=positions,
        freq_hz=FREQ_HZ,
        n_h=N_H,
        n_v=N_V,
        d=D,
        bs_center=BS_CENTER,
        broadside=BROADSIDE,
        eps_r=TISSUE.eps_r,
        sigma=TISSUE.sigma,
    )

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    plot_panel(
        axes[0],
        spectra_spec,
        rf"(a) plaza specular (LOS + ground + 2 facades)",
        M_ant,
    )
    plot_panel(
        axes[1],
        spectra_sto,
        f"(b) 3GPP 38.901 UMa LOS (12 clusters x {STOCHASTIC_SUBPATHS} subpaths)",
        M_ant,
    )
    fig.suptitle(
        rf"Spectrum of $\mathbf{{Q}}^{{(u)}}$ on Thelonious, "
        rf"{N_BODIES} bodies, 20-80 m range, $\pm$60$^\circ$ azimuth"
    )
    fig.tight_layout()
    fig.savefig(out_dir / "rank_cdf.pdf")
    fig.savefig(out_dir / "rank_cdf.png", dpi=180)
    plt.close(fig)
    print(f"\nwrote {out_dir / 'rank_cdf.pdf'}")
    print(f"wrote {out_dir / 'rank_cdf.png'}")

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------
    eps_levels = [1e-1, 1e-2, 1e-3]

    def ranks_for(spectra):
        rows = []
        for eps in eps_levels:
            ranks = np.array([epsilon_rank(spectra[i], eps) for i in range(N_BODIES)])
            rows.append(
                {
                    "eps": eps,
                    "p10": int(np.percentile(ranks, 10)),
                    "p50": int(np.percentile(ranks, 50)),
                    "p90": int(np.percentile(ranks, 90)),
                    "min": int(ranks.min()),
                    "max": int(ranks.max()),
                }
            )
        return rows

    rows_spec = ranks_for(spectra_spec)
    rows_sto = ranks_for(spectra_sto)

    def rows_to_md(title, rows):
        lines = [
            f"### {title}",
            "",
            "| epsilon | p10 | median | p90 | min | max |",
            "|---|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['eps']:.0e} | {r['p10']} | {r['p50']} | "
                f"{r['p90']} | {r['min']} | {r['max']} |"
            )
        lines.append("")
        return lines

    lines = [
        "# epsilon-effective rank of Q on Thelonious, plaza scenario",
        "",
        f"- Bodies: {N_BODIES}, thelonious, 20-80 m range, azimuth +/- 60 deg",
        f"- Freq: {FREQ_GHZ:.0f} GHz, {N_H}x{N_V} UPA (half-wavelength), 10 deg down-tilt",
        f"- Tissue: {TISSUE.name} (eps_r={TISSUE.eps_r:.2f}, sigma={TISSUE.sigma:.2f} S/m)",
        "",
        "Definition: epsilon-effective rank = #{k : lambda_k / lambda_1 >= epsilon}.",
        "",
    ]
    lines.extend(rows_to_md("Model A: plaza specular (LOS + ground + 2 facades)", rows_spec))
    lines.extend(
        rows_to_md(
            f"Model B: {PRESET_NAME} stochastic "
            f"(12 clusters x {STOCHASTIC_SUBPATHS} subpaths = {12 * STOCHASTIC_SUBPATHS} paths)",
            rows_sto,
        )
    )

    (out_dir / "rank_table.md").write_text("\n".join(lines))
    print(f"wrote {out_dir / 'rank_table.md'}")

    print("\nsummary (model A - specular):")
    for r in rows_spec:
        print(f"  eps={r['eps']:.0e}: median={r['p50']}, [p10={r['p10']}, p90={r['p90']}], [{r['min']}, {r['max']}]")
    print("summary (model B - stochastic):")
    for r in rows_sto:
        print(f"  eps={r['eps']:.0e}: median={r['p50']}, [p10={r['p10']}, p90={r['p90']}], [{r['min']}, {r['max']}]")


if __name__ == "__main__":
    main()
