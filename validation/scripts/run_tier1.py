"""Tier 1: AEGIS vs goliat FDTD on full thelonious at 7/9/11 GHz.

Path A of the campaign: 6 directions × 2 polarisations × 3 frequencies
= 36 sims, no scaled-phantom shortcut (Phase 1 closed Path B by
showing that scale invariance is broken by dispersion across the
operating-frequency range).

Reads goliat results under
`/home/user/goliat/results/far_field/thelonious/<freq>MHz/environmental_<dir>_<pol>/`
and runs AEGIS in every relevant kernel mode plus the per-direction
Cauchy formula, on the full-thelonious mesh at the same frequency.

Outputs:
    validation/data/tier1_thelonious.parquet — 36-row table
    validation/data/tier1_summary.csv — per-frequency direction-averaged
                                        ratios and headline metrics

Usage:
    python run_tier1.py
    python run_tier1.py --max-freq-mhz 9000   # subset
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from aegis import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel
from aegis.kernels._base import fresnel_weights

from geometry import GOLIAT_DIRS, goliat_basis, q_field, cache_geometry
from h5_surface_apd import load_skin_apd_npz
from surface_apd_compare import compare as surface_compare


NORM = 754.0


def Tbar(freq_hz: float, tissue_name: str = "Skin") -> float:
    tis = TissueModel.from_database(tissue_name, freq_hz=freq_hz)
    eps_complex = complex(tis.eps_r, -tis.sigma / (2 * np.pi * freq_hz * 8.854e-12))
    n_tilde = complex(np.sqrt(eps_complex))
    mu = np.linspace(0.005, 0.995, 200)[:, None]
    _, _, T_avg = fresnel_weights(mu, n_tilde)
    return float(2.0 * np.trapezoid(T_avg.flatten() * mu.flatten(), mu.flatten()))


def parse_run_dir(name: str):
    """environmental_<dir>_<pol> for either 'x_pos'-style (no underscore in dir)
    or 'theta_phi' tessellation format (underscore in dir).  Returns None on
    bad name."""
    if not name.startswith("environmental_"):
        return None
    parts = name.split("_")
    # Expected formats:  environmental_x_pos_theta  →  4 parts after split
    # or                  environmental_90_0_theta   →  4 parts (theta_phi)
    if len(parts) == 4:
        # environmental_<axis>_<pos|neg>_<pol>  (orthogonal alias)
        axis_pos = f"{parts[1]}_{parts[2]}"
        pol = parts[3]
        if axis_pos in GOLIAT_DIRS and pol in ("theta", "phi"):
            return axis_pos, pol
    return None


def load_goliat_record(run_dir: Path) -> dict:
    out: dict = {}
    sar_json = run_dir / "sar_results.json"
    if sar_json.exists():
        out.update(json.loads(sar_json.read_text()))
    sapd_json = run_dir / "sapd_results.json"
    if sapd_json.exists():
        out.update(json.loads(sapd_json.read_text()))
    skin_apd = run_dir / "skin_apd.npz"
    if skin_apd.exists():
        out["__skin_apd_path__"] = str(skin_apd)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", default="/home/user/goliat/results")
    ap.add_argument("--phantom", default="thelonious")
    ap.add_argument("--mass-kg", type=float, default=17.4)
    ap.add_argument("--stl", default=None, help="default <repo>/data/<phantom>.stl")
    ap.add_argument("--max-freq-mhz", type=int, default=15000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    val_dir = here.parent
    if args.stl is None:
        args.stl = str(val_dir.parent / "data" / f"{args.phantom}.stl")
    if args.out is None:
        args.out = str(val_dir / "data" / f"tier1_{args.phantom}.parquet")

    cache_dir = val_dir / "data" / "geometry_cache"
    geom = cache_geometry(args.stl, str(cache_dir))
    H_2x = geom["H_2x"]
    eta = geom["eta"]

    body = BodyMesh.load(args.stl)
    A_tri = body.areas
    A_ab = float((eta * A_tri).sum())
    bbox = body.vertices.max(axis=0) - body.vertices.min(axis=0)
    h_body = float(bbox.max())
    print(
        f"[tier1] phantom={args.phantom}  n_tri={body.n_triangles}  "
        f"A_total={body.total_area:.4f} m²  A_ab={A_ab:.4f} m²  h={h_body:.4f} m"
    )

    phantom_dir = Path(args.results_root) / "far_field" / args.phantom
    if not phantom_dir.exists():
        raise SystemExit(f"phantom dir not found: {phantom_dir}")

    rows = []
    freq_dirs = sorted(
        [p for p in phantom_dir.iterdir() if p.is_dir() and p.name.endswith("MHz")],
        key=lambda p: int(p.name.replace("MHz", "")),
    )
    for freq_dir in freq_dirs:
        f_mhz = int(freq_dir.name.replace("MHz", ""))
        if f_mhz > args.max_freq_mhz:
            continue
        f_hz = f_mhz * 1e6
        try:
            tissue = TissueModel.from_database("Skin", freq_hz=f_hz)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {f_mhz} MHz: tissue lookup failed ({exc})")
            continue
        eng = DosimetryEngine(tissue)
        Tb = Tbar(f_hz)
        Pabs_cauchy = 1.0 * Tb * A_ab / 4.0
        c0 = 299792458.0
        x_param = float(np.pi * h_body / (c0 / f_hz))

        for run_dir in sorted(freq_dir.iterdir()):
            parsed = parse_run_dir(run_dir.name)
            if parsed is None:
                continue
            direction, pol = parsed
            rec = load_goliat_record(run_dir)
            if "power_balance" not in rec:
                continue
            diel_W = float(rec["power_balance"]["DielLoss"])
            fdtd_pabs = diel_W * NORM
            fdtd_peak_sapd = float(rec.get("peak_sapd_W_m2", float("nan"))) * NORM

            khat, e_theta, e_phi = goliat_basis(direction)
            e_E = e_theta if pol == "theta" else e_phi
            q_arr = q_field(body.normals, khat, e_E)
            paths = PropagationPaths.from_powers(k_hat=khat[None, :], power=np.array([1.0]))
            vis = geom[f"vis_{direction}"]

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

            # Surface comparison if dual-evaluator dump is present
            nrmse = pearson_r2 = peak_4cm2_ratio = peak_raw_ratio = float("nan")
            integ_aegis = integ_fdtd = float("nan")
            if "__skin_apd_path__" in rec:
                try:
                    d = load_skin_apd_npz(rec["__skin_apd_path__"], body, sinc_ref_w_m2=1.0)
                    fdtd_sapd = d["sapd"]
                    cmp_metrics = surface_compare(res_all_o.sab, fdtd_sapd, body.areas, body=body)
                    nrmse = float(cmp_metrics.get("nrmse", float("nan")))
                    pearson_r2 = float(cmp_metrics.get("r2", float("nan")))
                    peak_raw_ratio = float(cmp_metrics.get("peak_ratio_raw", float("nan")))
                    peak_4cm2_ratio = float(cmp_metrics.get("peak_ratio_4cm2", float("nan")))
                    integ_aegis = float(np.sum(res_all_o.sab * body.areas))
                    integ_fdtd = float(d.get("integrated_W", float("nan")))
                except Exception as exc:  # noqa: BLE001
                    print(f"    surface compare failed at {f_mhz} {direction} {pol}: {exc}")

            rows.append(
                {
                    "freq_mhz": f_mhz,
                    "direction": direction,
                    "pol": pol,
                    "phantom": args.phantom,
                    "h_body_m": h_body,
                    "A_tot_m2": body.total_area,
                    "A_ab_m2": A_ab,
                    "size_x": x_param,
                    "fdtd_DielLoss_W": diel_W,
                    "fdtd_Pabs_W_m2": fdtd_pabs,
                    "fdtd_Pin_W": float(rec["power_balance"]["Pin"]),
                    "fdtd_RadPower_W": float(rec["power_balance"]["RadPower"]),
                    "fdtd_wbsar": float(rec.get("whole_body_sar", float("nan"))) * NORM,
                    "fdtd_peak_sapd_W_m2": fdtd_peak_sapd,
                    "Lall_Pabs": float(res_all.p_abs),
                    "Lallo_Pabs": float(res_all_o.p_abs),
                    "Lallo_peak_sab_4cm2": float(getattr(res_all_o, "peak_sab_averaged", float("nan"))),
                    "Cauchy_Pabs": Pabs_cauchy,
                    "Tbar": Tb,
                    "qmean": float(np.mean(q_arr)),
                    "surface_nrmse": nrmse,
                    "surface_r2": pearson_r2,
                    "surface_peak_ratio_raw": peak_raw_ratio,
                    "surface_peak_ratio_4cm2": peak_4cm2_ratio,
                    "surface_integrated_W_aegis": integ_aegis,
                    "surface_integrated_W_fdtd": integ_fdtd,
                }
            )
        print(f"  done {f_mhz} MHz ({len([r for r in rows if r['freq_mhz']==f_mhz])} runs)")

    if not rows:
        raise SystemExit("[tier1] no results found")

    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out)
    print()
    print(f"[tier1] wrote {len(df)} rows -> {args.out}")
    print()
    summary = df.groupby("freq_mhz").agg(
        size_x=("size_x", "first"),
        fdtd_Pabs=("fdtd_Pabs_W_m2", "mean"),
        Lall_Pabs=("Lall_Pabs", "mean"),
        Lallo_Pabs=("Lallo_Pabs", "mean"),
        Cauchy_Pabs=("Cauchy_Pabs", "mean"),
    )
    summary["Lall_ratio"] = summary["Lall_Pabs"] / summary["fdtd_Pabs"]
    summary["Lallo_ratio"] = summary["Lallo_Pabs"] / summary["fdtd_Pabs"]
    summary["Cauchy_ratio"] = summary["Cauchy_Pabs"] / summary["fdtd_Pabs"]
    print("Direction-averaged ratios:")
    print(summary.round(3).to_string())

    # Polarisation residual D_B per (freq, dir-pair)
    print()
    print("Polarisation residual D_B = (P_theta - P_phi) / P_avg:")
    for f_mhz in sorted(df["freq_mhz"].unique()):
        sub = df[df["freq_mhz"] == f_mhz]
        for direction in sorted(sub["direction"].unique()):
            theta_row = sub[(sub["direction"] == direction) & (sub["pol"] == "theta")]
            phi_row = sub[(sub["direction"] == direction) & (sub["pol"] == "phi")]
            if len(theta_row) and len(phi_row):
                pt = theta_row["fdtd_Pabs_W_m2"].iloc[0]
                pp = phi_row["fdtd_Pabs_W_m2"].iloc[0]
                D_B = abs(pt - pp) / max((pt + pp) / 2, 1e-30)
                print(f"  {f_mhz:5d} MHz  {direction:>5}  theta={pt:.4f}  phi={pp:.4f}  |D_B|={D_B:.3f}")

    csv_out = str(Path(args.out).with_suffix(".summary.csv"))
    summary.reset_index().to_csv(csv_out, index=False)
    print(f"\n[tier1] summary CSV -> {csv_out}")


if __name__ == "__main__":
    main()
