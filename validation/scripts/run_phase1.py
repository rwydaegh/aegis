"""Phase 1 of the validation campaign: scaled-(1/3) thelonious sanity check.

Reads goliat FDTD results for the scaled phantom (a single direction
`x_pos` and a single polarisation `theta` per frequency, 5 frequencies
spanning 700 MHz to 28 GHz) and compares them against AEGIS at the same
geometry / frequency.

Outputs `phase1_<phantom>.parquet` with one row per frequency.  Metrics
captured:

  * Total absorbed power: AEGIS L_all and Cauchy direction-average vs FDTD
    `DielLoss × NORM`.
  * 4-cm² peak SAPD: AEGIS `result.peak_sab_averaged` vs goliat
    `peak_sapd_W_m2`.
  * Per-vertex surface APD comparison (NRMSE, peak ratio, integrated
    ratio) when the goliat-side `skin_apd.npz` dump is present.
  * Size parameter `x = π h / λ` using body height `h` (the dominant
    dimension for diffraction).  Tier 0 used full thelonious, so its
    `x` at the same frequency is 3× that of the scaled body, matching
    Tier 0 at `f/3`.

Designed to run after `goliat study scaled_thelonious_one_third` and
the result-tar pull from the VM.  See the campaign handoff for the
exact pull command.

Usage:
    python run_phase1.py
    python run_phase1.py --results-root /home/user/goliat/results \\
                         --phantom thelonious_one_third \\
                         --stl ../data/scaled_phantoms/thelonious_one_third.stl
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
from aegis.geometry.occlusion import compute_ambient_occlusion

from geometry import goliat_basis, q_field, cache_geometry
from h5_surface_apd import load_skin_apd_npz
from surface_apd_compare import compare as surface_compare

# Goliat E=1 V/m → S_inc=1 W/m² renorm.  Same constant as run_tier0.py.
NORM = 754.0


def Tbar(freq_hz: float, tissue_name: str = "Skin") -> float:
    tis = TissueModel.from_database(tissue_name, freq_hz=freq_hz)
    eps_complex = complex(tis.eps_r, -tis.sigma / (2 * np.pi * freq_hz * 8.854e-12))
    n_tilde = complex(np.sqrt(eps_complex))
    mu = np.linspace(0.005, 0.995, 200)[:, None]
    _, _, T_avg = fresnel_weights(mu, n_tilde)
    return float(2.0 * np.trapezoid(T_avg.flatten() * mu.flatten(), mu.flatten()))


def find_run_dir(freq_dir: Path, direction: str = "90_0", pol: str = "theta") -> Path | None:
    """Return the goliat run directory for a given (direction, pol).

    Goliat names them `environmental_<dir_str>_<pol>` where dir_str is
    `<theta>_<phi>` or one of the orthogonal aliases (we only use
    spherical_tessellation, so it's `90_0` for x_pos).
    """
    candidate = freq_dir / f"environmental_{direction}_{pol}"
    if candidate.exists() and candidate.is_dir():
        return candidate
    # Fall back to anything matching environmental_*_<pol>
    for d in freq_dir.iterdir():
        if d.is_dir() and d.name.startswith("environmental_") and d.name.endswith(f"_{pol}"):
            return d
    return None


def load_goliat_record(run_dir: Path) -> dict:
    """Load sar_results.json + sapd_results.json + (optional) skin_apd.npz
    from a goliat run dir.  Returns a dict keyed by goliat field names.
    """
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
    ap.add_argument(
        "--results-root",
        default="/home/user/goliat/results",
        help="goliat results root (looks for far_field/<phantom>/<freq>MHz/...)",
    )
    ap.add_argument("--phantom", default="thelonious_one_third")
    ap.add_argument("--mass-kg", type=float, default=17.4 / 27.0, help="mass for whole-body SAR (default scales 17.4 by 1/27)")
    ap.add_argument("--scale-factor", type=float, default=1.0 / 3.0, help="STL scale factor used for the phantom (informational)")
    ap.add_argument(
        "--stl",
        default=None,
        help="STL of the scaled mesh; default: validation/data/scaled_phantoms/<phantom>.stl",
    )
    ap.add_argument("--direction", default="x_pos")
    ap.add_argument("--polarization", default="theta")
    ap.add_argument("--out", default=None, help="output parquet path")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    val_dir = here.parent
    if args.stl is None:
        args.stl = str(val_dir / "data" / "scaled_phantoms" / f"{args.phantom}.stl")
    if args.out is None:
        args.out = str(val_dir / "data" / f"phase1_{args.phantom}.parquet")

    # Geometry cache (curvature + visibility) on the scaled mesh.  The cache
    # is keyed by the STL hash so it isolates from the full-size cache.
    cache_dir = val_dir / "data" / "geometry_cache"
    geom = cache_geometry(args.stl, str(cache_dir))
    H_2x = geom["H_2x"]
    eta = geom["eta"]

    body = BodyMesh.load(args.stl)
    A_tri = body.areas
    A_ab = float((eta * A_tri).sum())
    bbox = body.vertices.max(axis=0) - body.vertices.min(axis=0)
    h_body = float(bbox.max())  # body height (dominant dimension)
    print(
        f"[phase1] phantom={args.phantom}  factor={args.scale_factor:.4f}  "
        f"n_tri={body.n_triangles}  A_total={body.total_area:.4f} m²  "
        f"A_ab={A_ab:.4f} m²  h={h_body:.4f} m"
    )

    # Goliat results dir
    phantom_dir = Path(args.results_root) / "far_field" / args.phantom
    if not phantom_dir.exists():
        raise SystemExit(f"phantom dir not found: {phantom_dir}")

    khat, e_theta, e_phi = goliat_basis(args.direction)
    e_E = e_theta if args.polarization == "theta" else e_phi
    q_arr = q_field(body.normals, khat, e_E)
    paths = PropagationPaths.from_powers(k_hat=khat[None, :], power=np.array([1.0]))
    vis = geom[f"vis_{args.direction}"]

    rows = []
    freq_dirs = sorted(
        [p for p in phantom_dir.iterdir() if p.is_dir() and p.name.endswith("MHz")],
        key=lambda p: int(p.name.replace("MHz", "")),
    )
    for freq_dir in freq_dirs:
        f_mhz = int(freq_dir.name.replace("MHz", ""))
        f_hz = f_mhz * 1e6
        run_dir = find_run_dir(freq_dir, direction="90_0", pol=args.polarization)
        if run_dir is None:
            print(f"  skip {f_mhz} MHz: no run dir under {freq_dir}")
            continue
        rec = load_goliat_record(run_dir)
        if "power_balance" not in rec:
            print(f"  skip {f_mhz} MHz: no sar_results.json under {run_dir}")
            continue

        try:
            tissue = TissueModel.from_database("Skin", freq_hz=f_hz)
        except Exception as e:
            print(f"  skip {f_mhz} MHz: tissue lookup failed ({e})")
            continue
        eng = DosimetryEngine(tissue)
        Tb = Tbar(f_hz)
        Pabs_cauchy = 1.0 * Tb * A_ab / 4.0

        # FDTD-side absorbed power and peak SAPD
        diel_W = float(rec["power_balance"]["DielLoss"])
        fdtd_pabs = diel_W * NORM
        fdtd_peak_sapd = float(rec.get("peak_sapd_W_m2", float("nan")))
        if "peak_sapd_W_m2" in rec:
            # Goliat reports peak in V/m^2 native units; the renormalisation
            # factor is already applied in the goliat post-process (verified
            # against tier0 and the campaign README).  Keep as-is.
            pass

        # AEGIS L_all (every spatial-mode kernel on, with real H, real q,
        # binary occlusion).  This is the "best-AEGIS" estimate.
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
            occlusion=vis,
        )

        # Surface-APD comparison (if the goliat-side dump exists)
        nrmse = pearson_r2 = peak_4cm2_ratio = peak_raw_ratio = float("nan")
        integrated_aegis_W = integrated_fdtd_W = float("nan")
        if "__skin_apd_path__" in rec:
            try:
                d = load_skin_apd_npz(rec["__skin_apd_path__"], body, sinc_ref_w_m2=1.0)
                fdtd_sapd = d["sapd"]
                cmp_metrics = surface_compare(res_all.sab, fdtd_sapd, body.areas, body=body)
                nrmse = float(cmp_metrics.get("nrmse", float("nan")))
                pearson_r2 = float(cmp_metrics.get("r2", float("nan")))
                peak_raw_ratio = float(cmp_metrics.get("peak_ratio_raw", float("nan")))
                peak_4cm2_ratio = float(cmp_metrics.get("peak_ratio_4cm2", float("nan")))
                integrated_aegis_W = float(np.sum(res_all.sab * body.areas))
                integrated_fdtd_W = float(d.get("integrated_W", float("nan")))
            except Exception as exc:  # noqa: BLE001
                print(f"    surface-APD compare failed at {f_mhz} MHz: {exc}")

        # x = π h / λ
        c0 = 299792458.0
        lam = c0 / f_hz
        x_param = np.pi * h_body / lam

        rows.append(
            {
                "freq_mhz": f_mhz,
                "phantom": args.phantom,
                "scale_factor": args.scale_factor,
                "h_body_m": h_body,
                "A_tot_m2": body.total_area,
                "A_ab_m2": A_ab,
                "size_x": x_param,
                "direction": args.direction,
                "pol": args.polarization,
                # FDTD totals
                "fdtd_DielLoss_W": diel_W,
                "fdtd_Pabs_W_m2": fdtd_pabs,
                "fdtd_Pin_W": float(rec["power_balance"]["Pin"]),
                "fdtd_RadPower_W": float(rec["power_balance"]["RadPower"]),
                "fdtd_wbsar": float(rec.get("whole_body_sar", float("nan"))) * NORM,
                "fdtd_peak_sapd_W_m2": fdtd_peak_sapd,
                # AEGIS L_all kernel
                "Lall_Pabs_W_m2": float(res_all.p_abs),
                "Lall_peak_sab": float(getattr(res_all, "peak_sab", float("nan"))),
                "Lall_peak_sab_4cm2": float(getattr(res_all, "peak_sab_averaged", float("nan"))),
                # Cauchy
                "Cauchy_Pabs_W_m2": Pabs_cauchy,
                "Tbar": Tb,
                # Surface map metrics
                "surface_nrmse": nrmse,
                "surface_r2": pearson_r2,
                "surface_peak_ratio_raw": peak_raw_ratio,
                "surface_peak_ratio_4cm2": peak_4cm2_ratio,
                "surface_integrated_W_aegis": integrated_aegis_W,
                "surface_integrated_W_fdtd": integrated_fdtd_W,
            }
        )
        print(
            f"  done {f_mhz} MHz  x={x_param:6.2f}  "
            f"Pabs aegis/fdtd = {res_all.p_abs/fdtd_pabs:.3f}  "
            f"peak4cm² aegis/fdtd = {peak_4cm2_ratio if not np.isnan(peak_4cm2_ratio) else float('nan')}"
        )

    if not rows:
        raise SystemExit("[phase1] no results found")

    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out)
    print()
    print(f"[phase1] wrote {len(df)} rows -> {args.out}")
    print()
    summary_cols = [
        "freq_mhz",
        "size_x",
        "fdtd_Pabs_W_m2",
        "Lall_Pabs_W_m2",
        "Cauchy_Pabs_W_m2",
        "fdtd_peak_sapd_W_m2",
        "Lall_peak_sab_4cm2",
        "surface_nrmse",
        "surface_peak_ratio_4cm2",
    ]
    s = df[summary_cols].copy()
    s["Lall/FDTD_Pabs"] = s["Lall_Pabs_W_m2"] / s["fdtd_Pabs_W_m2"]
    s["Cauchy/FDTD_Pabs"] = s["Cauchy_Pabs_W_m2"] / s["fdtd_Pabs_W_m2"]
    s["AEGIS/FDTD_peak4cm²"] = s["Lall_peak_sab_4cm2"] / s["fdtd_peak_sapd_W_m2"]
    print(
        s[
            [
                "freq_mhz",
                "size_x",
                "Lall/FDTD_Pabs",
                "Cauchy/FDTD_Pabs",
                "AEGIS/FDTD_peak4cm²",
                "surface_peak_ratio_4cm2",
                "surface_nrmse",
            ]
        ].round(4).to_string(index=False)
    )


if __name__ == "__main__":
    main()
