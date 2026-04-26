"""Tier 0: AEGIS vs goliat FDTD on Thelonious, 450 MHz to 5.8 GHz.

Reads the goliat 2026 PMB campaign zip (extracted), runs every relevant AEGIS
kernel (L3, L4 with q(r), L6 with cotangent-Laplacian curvature) plus
per-direction occlusion, computes the Cauchy direction-averaged formula,
and writes a single Pandas DataFrame to disk for plotting.

No FDTD runs are launched. The expensive operation is the visibility
ray-tracing for 6 cardinal directions, ~1 s on Thelonious.

Usage:
    python run_tier0.py [--zip path/to/far_field.zip] [--phantom thelonious]
                        [--out path/to/tier0_records.parquet]
"""

from __future__ import annotations
import argparse
import json
import os
import zipfile
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from aegis import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel
from aegis.kernels._base import fresnel_weights
from aegis.geometry.occlusion import compute_ambient_occlusion

from geometry import GOLIAT_DIRS, goliat_basis, q_field, cache_geometry

# 1 / (2 * eta_0). Goliat excites with E = 1 V/m so its native S_inc = 1/754
# W/m^2; multiply outputs by 754 to renormalise to S_inc = 1 W/m^2.
NORM = 754.0


def Tbar(freq_hz: float, tissue_name: str = "Skin") -> float:
    """Flux-averaged Fresnel transmission Tbar(f) = 2 * int_0^1 T_avg(mu) mu dmu."""
    tis = TissueModel.from_database(tissue_name, freq_hz=freq_hz)
    eps_complex = complex(tis.eps_r, -tis.sigma / (2 * np.pi * freq_hz * 8.854e-12))
    n_tilde = complex(np.sqrt(eps_complex))
    mu = np.linspace(0.005, 0.995, 200)[:, None]
    _, _, T_avg = fresnel_weights(mu, n_tilde)
    return float(2.0 * np.trapezoid(T_avg.flatten() * mu.flatten(), mu.flatten()))


def parse_run_dir(name: str):
    """environmental_<dir>_<pol> -> (direction, polarisation) or None."""
    parts = name.split("_")
    if len(parts) != 4 or parts[0] != "environmental":
        return None
    direction = parts[1] + "_" + parts[2]
    pol = parts[3]
    if direction not in GOLIAT_DIRS or pol not in ("theta", "phi"):
        return None
    return direction, pol


def ensure_extracted(zip_path: Path, extract_dir: Path):
    """Extract goliat far_field.zip into extract_dir if not already there."""
    if (extract_dir / "far_field").exists():
        return extract_dir / "far_field"
    print(f"[tier0] extracting {zip_path} -> {extract_dir}")
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    return extract_dir / "far_field"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default="/home/user/goliat/results/far_field.zip")
    ap.add_argument("--phantom", default="thelonious")
    ap.add_argument("--stl", default=None, help="phantom STL path; default ../../data/<phantom>.stl")
    ap.add_argument("--mass-kg", type=float, default=17.4)
    ap.add_argument("--max-freq-mhz", type=int, default=5800)
    ap.add_argument("--out", default=None, help="output parquet path; default ../data/tier0_<phantom>.parquet")
    ap.add_argument("--extract-dir", default="/tmp/goliat_far_field")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    val_dir = here.parent
    if args.stl is None:
        args.stl = str(val_dir.parent / "data" / f"{args.phantom}.stl")
    if args.out is None:
        args.out = str(val_dir / "data" / f"tier0_{args.phantom}.parquet")

    # Extract goliat data if needed
    far_field_dir = ensure_extracted(Path(args.zip), Path(args.extract_dir))
    phantom_dir = far_field_dir / args.phantom
    if not phantom_dir.exists():
        raise SystemExit(f"phantom {args.phantom} not found in zip")

    # Geometry cache
    cache_dir = val_dir / "data" / "geometry_cache"
    geom = cache_geometry(args.stl, str(cache_dir))
    H_2x = geom["H_2x"]
    eta = geom["eta"]

    body = BodyMesh.load(args.stl)
    A_tri = body.areas
    A_ab = float((eta * A_tri).sum())
    print(
        f"[tier0] phantom: {body.n_triangles} tri, A_total={body.total_area:.3f} m^2, "
        f"A_ab={A_ab:.3f} m^2 (eta_avg={A_ab / body.total_area:.3f})"
    )

    rows = []
    freq_dirs = sorted([p for p in phantom_dir.iterdir() if p.is_dir() and p.name.endswith("MHz")])
    for freq_dir in freq_dirs:
        f_mhz = int(freq_dir.name.replace("MHz", ""))
        if f_mhz > args.max_freq_mhz:
            continue
        f_hz = f_mhz * 1e6
        try:
            tissue = TissueModel.from_database("Skin", freq_hz=f_hz)
        except Exception as e:
            print(f"  skip {f_mhz}: {e}")
            continue
        eng = DosimetryEngine(tissue)
        Tb = Tbar(f_hz)
        Pabs_cauchy = 1.0 * Tb * A_ab / 4.0
        for run_dir in sorted(freq_dir.iterdir()):
            parsed = parse_run_dir(run_dir.name)
            if parsed is None:
                continue
            direction, pol = parsed
            sar_json = run_dir / "sar_results.json"
            if not sar_json.exists():
                continue
            r = json.loads(sar_json.read_text())
            pb = r["power_balance"]
            diel_W = pb["DielLoss"]
            fdtd_pabs = diel_W * NORM

            khat, e_theta, e_phi = goliat_basis(direction)
            e_E = e_theta if pol == "theta" else e_phi
            q_arr = q_field(body.normals, khat, e_E)
            paths = PropagationPaths.from_powers(k_hat=khat[None, :], power=np.array([1.0]))

            res3 = eng.compute(body, paths, level=3, body_mass=args.mass_kg, freq_hz=f_hz)
            res4 = eng.compute(body, paths, level=4, body_mass=args.mass_kg, freq_hz=f_hz, q=q_arr)
            res6 = eng.compute(body, paths, level=6, body_mass=args.mass_kg, freq_hz=f_hz, curvature_H=H_2x)
            vis = geom[f"vis_{direction}"]
            res3o = eng.compute(body, paths, level=3, body_mass=args.mass_kg, freq_hz=f_hz, occlusion=vis)
            res4o = eng.compute(body, paths, level=4, body_mass=args.mass_kg, freq_hz=f_hz, q=q_arr, occlusion=vis)
            res6o = eng.compute(
                body, paths, level=6, body_mass=args.mass_kg, freq_hz=f_hz, curvature_H=H_2x, occlusion=vis
            )
            # "Ultimate" — every spatial-mode correction simultaneously
            res_all = eng.compute(
                body,
                paths,
                mode="spatial",
                body_mass=args.mass_kg,
                freq_hz=f_hz,
                fresnel=True,
                polarisation=True,
                curvature=True,
                diffraction=True,
                q=q_arr,
                curvature_H=H_2x,
            )
            res_all_o = eng.compute(
                body,
                paths,
                mode="spatial",
                body_mass=args.mass_kg,
                freq_hz=f_hz,
                fresnel=True,
                polarisation=True,
                curvature=True,
                diffraction=True,
                q=q_arr,
                curvature_H=H_2x,
                occlusion=vis,
            )
            rows.append(
                {
                    "freq_mhz": f_mhz,
                    "direction": direction,
                    "pol": pol,
                    "fdtd_Pin": pb["Pin"],
                    "fdtd_DielLoss": pb["DielLoss"],
                    "fdtd_RadPower": pb["RadPower"],
                    "fdtd_Pabs_W_m2": fdtd_pabs,
                    "fdtd_wbsar": r["whole_body_sar"] * NORM,
                    "L3_Pabs": res3.p_abs,
                    "L3o_Pabs": res3o.p_abs,
                    "L4_Pabs": res4.p_abs,
                    "L4o_Pabs": res4o.p_abs,
                    "L6_Pabs": res6.p_abs,
                    "L6o_Pabs": res6o.p_abs,
                    "Lall_Pabs": res_all.p_abs,
                    "Lallo_Pabs": res_all_o.p_abs,
                    "Cauchy_Pabs": Pabs_cauchy,
                    "Tbar": Tb,
                    "A_ab_m2": A_ab,
                    "qmean": float(np.mean(q_arr)),
                }
            )
        print(f"  done {f_mhz} MHz ({len(rows)} rows total)")

    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out)
    print(f"[tier0] wrote {len(df)} rows -> {args.out}")
    print()
    print("Direction-averaged ratios per frequency:")
    summary = df.groupby("freq_mhz").agg(
        {
            "L3_Pabs": "mean",
            "L4_Pabs": "mean",
            "L6_Pabs": "mean",
            "L6o_Pabs": "mean",
            "Lall_Pabs": "mean",
            "Lallo_Pabs": "mean",
            "Cauchy_Pabs": "mean",
            "fdtd_Pabs_W_m2": "mean",
        }
    )
    for col in ["L3_Pabs", "L4_Pabs", "L6_Pabs", "L6o_Pabs", "Lall_Pabs", "Lallo_Pabs", "Cauchy_Pabs"]:
        summary[col + "_ratio"] = summary[col] / summary["fdtd_Pabs_W_m2"]
    print(summary[[c for c in summary.columns if c.endswith("_ratio")]].round(3))


if __name__ == "__main__":
    main()
