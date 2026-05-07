"""
Task 09: Posture sensitivity study
---------------------------------

Reads a Blender export manifest (artifacts/postures/<model>/manifest.json) and:

Per pose STL:
  1) compute A_perp LUT (Task 01 logic)
  2) compute D(k_hat) and SH fit errors (Task 02 logic)
  3) compute a couple angular-spectrum scalars F (Task 03 logic)
  4) optionally compute eta(r) with a small ray budget (Task 04 script via subprocess)

Writes:
  - artifacts/postures/<model>/posture_summary.csv
  - figures/posture_sensitivity_summary.png
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import matplotlib.pyplot as plt

# Import existing task code as modules. This works because the script is executed from scripts/.
import compute_projected_area_table as cap
import compute_body_directivity as cbd
import angular_spectrum_examples as ase


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run posture sensitivity study from a Blender export manifest.")
    p.add_argument("--manifest", type=Path, required=True, help="Path to manifest.json produced by blender/posture_export.py")
    p.add_argument("--n_dirs", type=int, default=2048, help="Number of sphere directions (default: 2048)")
    p.add_argument("--chunk", type=int, default=128, help="Direction chunk size for A_perp computation (default: 128)")
    p.add_argument("--maxL", type=int, default=6, help="Max SH degree for fit sweep (default: 6)")

    p.add_argument("--elev0-deg", dest="elev0_deg", type=float, default=15.0)
    p.add_argument("--elev-sigma-deg", dest="elev_sigma_deg", type=float, default=7.5)
    p.add_argument("--elev-upper-only", action="store_true")

    p.add_argument("--eta_rays", type=int, default=0, help="If >0, compute eta with this many rays per triangle (slow).")
    p.add_argument("--eta_max_leaf", type=int, default=8, help="BVH leaf size for eta script (default: 8)")
    p.add_argument("--eta_seed", type=int, default=0)
    return p.parse_args()


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if "poses" not in data or not isinstance(data["poses"], list):
        raise ValueError("manifest.json missing required list: poses")
    return data


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_existing_path(p: Path, *, manifest_path: Path) -> Path:
    """
    Resolve a path from the manifest robustly.

    We accept:
    - absolute paths
    - paths relative to repo root
    - paths relative to the manifest directory
    """
    if p.is_absolute():
        return p
    candidates = [
        p,
        (manifest_path.parent / p),
        (_repo_root() / p),
    ]
    for c in candidates:
        c2 = c.resolve()
        if c2.exists():
            return c2
    # If nothing exists, return the "most likely" one for error message
    return (manifest_path.parent / p).resolve()


def _weighted_mean(x: np.ndarray, w: Optional[np.ndarray]) -> float:
    return float(ase._weighted_mean(x, w))  # reuse well-tested helper


def _normalize_rho(rho_raw: np.ndarray, w: Optional[np.ndarray]) -> np.ndarray:
    return ase._normalize_rho(rho_raw, w)


def _compute_F_metrics(k_hat: np.ndarray, D: np.ndarray, w: Optional[np.ndarray], *,
                       elev0_deg: float, elev_sigma_deg: float, elev_upper_only: bool) -> dict[str, float]:
    kz = np.asarray(k_hat[:, 2], dtype=float)
    el = np.arcsin(np.clip(kz, -1.0, 1.0))  # [-pi/2, pi/2]

    # Isotropic (rho=1 normalized)
    rho_iso = np.ones_like(kz)
    rho_iso = _normalize_rho(rho_iso, w)
    F_iso = _weighted_mean(rho_iso * D, w)

    # Elevation Gaussian
    el0 = np.deg2rad(float(elev0_deg))
    sigma = np.deg2rad(max(float(elev_sigma_deg), 1e-6))
    rho_elev = np.exp(-0.5 * ((el - el0) / sigma) ** 2)
    if elev_upper_only:
        rho_elev = rho_elev * (kz > 0).astype(float)
    rho_elev = _normalize_rho(rho_elev, w)
    F_elev = _weighted_mean(rho_elev * D, w)

    return {
        "F_isotropic": float(F_iso),
        f"F_elev_gaussian_{float(elev0_deg):g}deg_sigma{float(elev_sigma_deg):g}deg": float(F_elev),
    }


def _eta_subprocess(*, stl_path: Path, out_dir: Path, n_rays: int, seed: int, max_leaf: int) -> dict[str, float]:
    """
    Run scripts/compute_exposure_fraction_eta.py as a subprocess and return summary stats.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "compute_exposure_fraction_eta.py"),
        "--stl", str(stl_path),
        "--n_rays", str(int(n_rays)),
        "--out", str(out_dir),
        "--seed", str(int(seed)),
        "--max_leaf", str(int(max_leaf)),
        "--progress_every", "0",
    ]
    subprocess.run(cmd, check=True)
    eta_npz = out_dir / "eta.npz"
    data = np.load(eta_npz)
    eta = np.asarray(data["eta"], dtype=float)
    return {
        "eta_mean": float(np.mean(eta)),
        "eta_p10": float(np.percentile(eta, 10)),
        "eta_p1": float(np.percentile(eta, 1)),
    }


@dataclass(frozen=True)
class PoseRow:
    pose_name: str
    stl_path: Path
    triangles: int
    surface_area: float
    D_max: float
    D_min: float
    D_p50: float
    D_p95: float
    sh_rms_L2: float
    sh_rms_L6: float
    F_isotropic: float
    F_elev: float
    eta_mean: Optional[float]
    eta_p10: Optional[float]
    eta_p1: Optional[float]


def main() -> int:
    args = _parse_args()
    manifest = _load_manifest(args.manifest)
    t0 = time.perf_counter()

    export_dir = Path(manifest.get("export_dir") or args.manifest.parent)
    model_name = str(manifest.get("model_name") or export_dir.name)

    # Output locations (all under artifacts/, which repo ignores)
    out_root = export_dir
    derived_dir = out_root / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)

    figures_dir = Path("figures")
    figures_dir.mkdir(parents=True, exist_ok=True)

    rows: list[PoseRow] = []

    # Common direction sampler
    k_hat = cap.fibonacci_sphere(int(args.n_dirs))

    for pose in manifest["poses"]:
        t_pose0 = time.perf_counter()
        pose_name = str(pose["pose_name"])
        stl_path = _resolve_existing_path(Path(pose["stl_path"]), manifest_path=args.manifest)
        if not stl_path.exists():
            raise FileNotFoundError(f"Missing STL for pose {pose_name}: {stl_path}")

        # Load mesh + basic stats
        vertices, normals, _centroids = cap.load_stl_binary(stl_path)
        areas = cap.triangle_areas(vertices)
        triangles = int(vertices.shape[0])
        surface_area = float(np.sum(areas))

        # A_perp LUT (stored per-pose for reuse)
        A_perp = cap.compute_A_perp_lut(normals, areas, k_hat, chunk_dirs=int(args.chunk))
        A_mean = float(np.mean(A_perp))
        if not np.isfinite(A_mean) or A_mean <= 0:
            raise ValueError(f"Bad mean(A_perp) for {pose_name}: {A_mean}")
        D = A_perp / A_mean

        pose_out = derived_dir / pose_name
        pose_out.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            pose_out / "A_perp_lut.npz",
            k_hat=k_hat.astype(np.float64),
            A_perp=A_perp.astype(np.float64),
            n_triangles=triangles,
            surface_area=surface_area,
            stl_path=str(stl_path),
            sampler="fibonacci_sphere",
            mu_definition="mu = n_hat · (-k_hat)",
            note_no_occlusion=True,
        )

        # Directivity stats
        D_max = float(np.max(D))
        D_min = float(np.min(D))
        D_p50 = float(np.percentile(D, 50))
        D_p95 = float(np.percentile(D, 95))

        # SH fit errors (RMS at L=2 and L=6 by default)
        theta, phi = cbd._spherical_angles_from_k_hat(k_hat)
        summaries = cbd._sh_error_sweep(D, theta, phi, maxL=int(args.maxL))
        rms_by_L = {s.L: float(s.rms) for s in summaries}
        sh_rms_L2 = float(rms_by_L.get(2, np.nan))
        sh_rms_L6 = float(rms_by_L.get(6, np.nan))

        # Angular spectrum scalars F
        F_metrics = _compute_F_metrics(
            k_hat, D, None,
            elev0_deg=float(args.elev0_deg),
            elev_sigma_deg=float(args.elev_sigma_deg),
            elev_upper_only=bool(args.elev_upper_only),
        )
        # Pull out canonical keys
        F_isotropic = float(F_metrics["F_isotropic"])
        # second key is deterministic but formatted; extract by excluding isotropic
        F_elev_key = [k for k in F_metrics.keys() if k != "F_isotropic"][0]
        F_elev = float(F_metrics[F_elev_key])

        # Optional eta
        eta_mean = eta_p10 = eta_p1 = None
        if int(args.eta_rays) > 0:
            eta_dir = pose_out / "eta"
            eta_stats = _eta_subprocess(
                stl_path=stl_path,
                out_dir=eta_dir,
                n_rays=int(args.eta_rays),
                seed=int(args.eta_seed),
                max_leaf=int(args.eta_max_leaf),
            )
            eta_mean = float(eta_stats["eta_mean"])
            eta_p10 = float(eta_stats["eta_p10"])
            eta_p1 = float(eta_stats["eta_p1"])

        rows.append(
            PoseRow(
                pose_name=pose_name,
                stl_path=stl_path,
                triangles=triangles,
                surface_area=surface_area,
                D_max=D_max,
                D_min=D_min,
                D_p50=D_p50,
                D_p95=D_p95,
                sh_rms_L2=sh_rms_L2,
                sh_rms_L6=sh_rms_L6,
                F_isotropic=F_isotropic,
                F_elev=F_elev,
                eta_mean=eta_mean,
                eta_p10=eta_p10,
                eta_p1=eta_p1,
            )
        )

        dt_pose = time.perf_counter() - t_pose0
        print(
            f"[posture_study] {pose_name}: D_max={D_max:.3f}  SH(L6) RMS={sh_rms_L6:.4f}  "
            f"F_elev={F_elev:.3f}  ({dt_pose:.2f}s)"
        )

    # Write CSV summary
    csv_path = out_root / "posture_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "pose_name",
                "stl_path",
                "triangles",
                "surface_area",
                "D_max",
                "D_min",
                "D_p50",
                "D_p95",
                "sh_rms_L2",
                "sh_rms_L6",
                "F_isotropic",
                "F_elev_gaussian",
                "eta_mean",
                "eta_p10",
                "eta_p1",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.pose_name,
                    str(r.stl_path),
                    r.triangles,
                    f"{r.surface_area:.10g}",
                    f"{r.D_max:.10g}",
                    f"{r.D_min:.10g}",
                    f"{r.D_p50:.10g}",
                    f"{r.D_p95:.10g}",
                    f"{r.sh_rms_L2:.10g}",
                    f"{r.sh_rms_L6:.10g}",
                    f"{r.F_isotropic:.10g}",
                    f"{r.F_elev:.10g}",
                    "" if r.eta_mean is None else f"{r.eta_mean:.10g}",
                    "" if r.eta_p10 is None else f"{r.eta_p10:.10g}",
                    "" if r.eta_p1 is None else f"{r.eta_p1:.10g}",
                ]
            )

    # Summary figure
    pose_names = [r.pose_name for r in rows]
    x = np.arange(len(rows))

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 7.5))
    ax = axes[0, 0]
    ax.bar(x, [r.D_max for r in rows], color="#377eb8", edgecolor="black", linewidth=0.6)
    ax.set_title("D_max by posture")
    ax.set_xticks(x)
    ax.set_xticklabels(pose_names, rotation=25, ha="right")
    ax.grid(True, axis="y", alpha=0.25)

    ax = axes[0, 1]
    ax.plot(x, [r.sh_rms_L2 for r in rows], "o-", label="L=2 RMS", color="#4daf4a")
    ax.plot(x, [r.sh_rms_L6 for r in rows], "o-", label="L=6 RMS", color="#e41a1c")
    ax.set_title("SH reconstruction RMS error")
    ax.set_xticks(x)
    ax.set_xticklabels(pose_names, rotation=25, ha="right")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend()

    ax = axes[1, 0]
    ax.bar(x, [r.F_elev for r in rows], color="#984ea3", edgecolor="black", linewidth=0.6)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1.2)
    ax.set_title("F (elevation Gaussian) by posture")
    ax.set_xticks(x)
    ax.set_xticklabels(pose_names, rotation=25, ha="right")
    ax.grid(True, axis="y", alpha=0.25)

    ax = axes[1, 1]
    if any(r.eta_mean is not None for r in rows):
        eta_vals = [np.nan if r.eta_mean is None else r.eta_mean for r in rows]
        ax.bar(x, eta_vals, color="#ff7f00", edgecolor="black", linewidth=0.6)
        ax.set_title("eta_mean by posture")
        ax.set_xticks(x)
        ax.set_xticklabels(pose_names, rotation=25, ha="right")
        ax.set_ylim(0, 1)
        ax.grid(True, axis="y", alpha=0.25)
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "eta not computed (--eta_rays 0)", ha="center", va="center")

    fig.suptitle(f"Posture sensitivity summary — {model_name} (n_dirs={int(args.n_dirs)})")
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig_path = figures_dir / "posture_sensitivity_summary.png"
    fig.savefig(fig_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    print(f"[posture_study] Wrote: {csv_path}")
    print(f"[posture_study] Wrote: {fig_path}")
    dt = time.perf_counter() - t0
    n_pose = len(rows)
    per = (dt / n_pose) if n_pose > 0 else float("nan")
    print(f"[posture_study] Total time: {dt:.2f}s  ({per:.2f}s / pose)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

