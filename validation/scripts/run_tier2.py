"""Tier 2: surface-map comparison on a single Tier 1 scenario.

Picks one (frequency, direction, polarisation) from the Tier 1 sweep,
loads its `skin_apd.npz` per-vertex FDTD SAPD, runs AEGIS L_all on the
same mesh, and paints the absolute AEGIS Sab map, the FDTD SAPD map,
and the AEGIS / FDTD ratio map onto the phantom.

Outputs:
    validation/tier2_<f>MHz_<dir>_<pol>_aegis_sab.png
    validation/tier2_<f>MHz_<dir>_<pol>_fdtd_sapd.png
    validation/tier2_<f>MHz_<dir>_<pol>_ratio.png
    validation/tier2_<f>MHz_<dir>_<pol>_metrics.txt

Usage:
    python run_tier2.py --freq-mhz 11000 --direction x_pos --pol theta
"""

from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np

from aegis import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel

from geometry import goliat_basis, q_field, cache_geometry
from h5_surface_apd import load_skin_apd_npz
from surface_apd_compare import compare as surface_compare, paint_error


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", default="/home/user/goliat/results")
    ap.add_argument("--phantom", default="thelonious")
    ap.add_argument("--mass-kg", type=float, default=17.4)
    ap.add_argument("--freq-mhz", type=int, required=True)
    ap.add_argument("--direction", default="x_pos")
    ap.add_argument("--pol", default="theta")
    ap.add_argument("--stl", default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    val_dir = here.parent
    if args.stl is None:
        args.stl = str(val_dir.parent / "data" / f"{args.phantom}.stl")
    if args.out_dir is None:
        out_dir = val_dir
    else:
        out_dir = Path(args.out_dir)

    cache_dir = val_dir / "data" / "geometry_cache"
    geom = cache_geometry(args.stl, str(cache_dir))
    H_2x = geom["H_2x"]

    body = BodyMesh.load(args.stl)

    run_dir = (
        Path(args.results_root)
        / "far_field"
        / args.phantom
        / f"{args.freq_mhz}MHz"
        / f"environmental_{args.direction}_{args.pol}"
    )
    if not run_dir.exists():
        raise SystemExit(f"run dir not found: {run_dir}")
    npz = run_dir / "skin_apd.npz"
    if not npz.exists():
        raise SystemExit(f"skin_apd.npz not found in {run_dir}")
    print(f"[tier2] using {run_dir}")

    f_hz = args.freq_mhz * 1e6
    tissue = TissueModel.from_database("Skin", freq_hz=f_hz)
    eng = DosimetryEngine(tissue)

    khat, e_theta, e_phi = goliat_basis(args.direction)
    e_E = e_theta if args.pol == "theta" else e_phi
    q_arr = q_field(body.normals, khat, e_E)
    paths = PropagationPaths.from_powers(k_hat=khat[None, :], power=np.array([1.0]))
    vis = geom[f"vis_{args.direction}"]

    res = eng.compute(
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

    d = load_skin_apd_npz(str(npz), body, sinc_ref_w_m2=1.0)
    s_fdtd = d["sapd"]
    s_aegis = res.sab

    metrics = surface_compare(s_aegis, s_fdtd, body.areas, body=body)
    metrics_text = "\n".join(f"  {k}: {v:.6g}" if isinstance(v, float) else f"  {k}: {v}" for k, v in metrics.items())

    print()
    print(f"[tier2] {args.freq_mhz} MHz {args.direction} {args.pol}")
    print(metrics_text)

    metrics_path = out_dir / f"tier2_{args.freq_mhz}MHz_{args.direction}_{args.pol}_metrics.txt"
    metrics_path.write_text(
        f"Tier 2 surface-map comparison\n"
        f"  phantom={args.phantom}  freq={args.freq_mhz} MHz  dir={args.direction}  pol={args.pol}\n"
        f"  run_dir={run_dir}\n\n{metrics_text}\n"
    )
    print(f"\n[tier2] wrote {metrics_path}")

    # Paintings
    paint_error(
        body,
        s_aegis,
        str(out_dir / f"tier2_{args.freq_mhz}MHz_{args.direction}_{args.pol}_aegis_sab.png"),
        cmap="viridis",
        title=f"AEGIS Sab (W/m^2)  {args.freq_mhz} MHz  {args.direction}  {args.pol}",
    )
    paint_error(
        body,
        s_fdtd,
        str(out_dir / f"tier2_{args.freq_mhz}MHz_{args.direction}_{args.pol}_fdtd_sapd.png"),
        cmap="viridis",
        title=f"FDTD SAPD (W/m^2)  {args.freq_mhz} MHz  {args.direction}  {args.pol}",
    )
    eps = 1e-12
    ratio = s_aegis / np.maximum(s_fdtd, eps)
    paint_error(
        body,
        np.clip(ratio, 0, 3),
        str(out_dir / f"tier2_{args.freq_mhz}MHz_{args.direction}_{args.pol}_ratio.png"),
        vmin=0.0,
        vmax=2.0,
        cmap="RdBu_r",
        title=f"AEGIS / FDTD Sab ratio  {args.freq_mhz} MHz  {args.direction}  {args.pol}",
    )
    print(f"[tier2] painted 3 figures in {out_dir}/")


if __name__ == "__main__":
    main()
