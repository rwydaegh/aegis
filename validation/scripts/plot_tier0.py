"""Regenerate the four Tier 0 figures from the parquet produced by run_tier0.py.

Usage:
    python plot_tier0.py [--records ../data/tier0_thelonious.parquet]
                         [--phantom thelonious]
                         [--outdir ..]
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from geometry import GOLIAT_DIRS, goliat_basis, cache_geometry


def fig_kernels_vs_fdtd(df: pd.DataFrame, out_path: Path):
    """Per-direction ratios + direction-averaged ratios + Cauchy line."""
    freqs = np.sort(df["freq_mhz"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    ax = axes[0]
    kernels = [
        ("L3_Pabs", "C0", "o", "L3 (Fresnel only)"),
        ("L4_Pabs", "C1", "s", "L4 (+ polarisation)"),
        ("L6_Pabs", "C2", "^", "L6 (+ curvature/diffraction, real H)"),
        ("Lall_Pabs", "C5", "*", "L_all (Fresnel+pol+curv+diff)"),
        ("L3o_Pabs", "C3", "v", r"L3 $\times O$"),
        ("Lallo_Pabs", "C6", "P", r"L_all $\times O$"),
    ]
    for col, color, marker, label in kernels:
        means, stds = [], []
        for f in freqs:
            sub = df[df["freq_mhz"] == f]
            ratios = sub[col] / sub["fdtd_Pabs_W_m2"]
            means.append(ratios.mean())
            stds.append(ratios.std())
        ax.errorbar(freqs / 1000, means, yerr=stds, marker=marker, color=color, label=label, capsize=2, alpha=0.85)
    ax.axhline(1.0, color="k", ls="--", alpha=0.4, label="AEGIS = FDTD")
    ax.set_xscale("log")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel(
        r"$P_{\rm abs}^{\rm AEGIS} / P_{\rm abs}^{\rm FDTD}$"
        " (mean ± std over 12 dirs × 2 pols)"
    )
    ax.set_title("Per-direction comparison: AEGIS kernels vs FDTD")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[1]
    grouped = df.groupby("freq_mhz").mean(numeric_only=True)
    fdtd_avg = grouped["fdtd_Pabs_W_m2"]
    for col, color, marker, label in [
        ("L3_Pabs", "C0", "o", "L3"),
        ("L4_Pabs", "C1", "s", "L4"),
        ("L6_Pabs", "C2", "^", "L6 (real H)"),
        ("Lall_Pabs", "C5", "*", "L_all (Fresnel+pol+curv+diff)"),
        ("Lallo_Pabs", "C6", "P", r"L_all $\times O$"),
    ]:
        ax.plot(grouped.index / 1000, grouped[col] / fdtd_avg, marker=marker, color=color, label=label)
    ax.plot(
        grouped.index / 1000,
        grouped["Cauchy_Pabs"] / fdtd_avg,
        "*-",
        color="k",
        markersize=14,
        lw=2,
        label=r"Cauchy $S_{\rm inc}\bar T A_{ab}/4$ / FDTD",
    )
    ax.axhline(1.0, color="k", ls="--", alpha=0.4)
    ax.set_xscale("log")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel(
        r"$\langle P_{\rm abs}^{\rm AEGIS}\rangle / "
        r"\langle P_{\rm abs}^{\rm FDTD}\rangle$"
    )
    ax.set_title("Direction-averaged comparison: kernels & Cauchy-T̄ vs FDTD")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    print(f"[plot] {out_path}")


def fig_polarisation(df: pd.DataFrame, out_path: Path):
    freqs = np.sort(df["freq_mhz"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    classes = {
        "lateral (x)": ["x_pos", "x_neg"],
        "frontal (y)": ["y_pos", "y_neg"],
        "vertical (z)": ["z_pos", "z_neg"],
    }
    ax = axes[0]
    for cls_name, dirs in classes.items():
        db_vals = []
        for f in freqs:
            ds = []
            for d in dirs:
                t_p = df[(df.freq_mhz == f) & (df.direction == d) & (df.pol == "theta")]["fdtd_Pabs_W_m2"]
                p_p = df[(df.freq_mhz == f) & (df.direction == d) & (df.pol == "phi")]["fdtd_Pabs_W_m2"]
                if len(t_p) and len(p_p):
                    tt, pp = float(t_p.iloc[0]), float(p_p.iloc[0])
                    ds.append(abs(tt - pp) / (tt + pp))
            db_vals.append(np.mean(ds) if ds else np.nan)
        ax.plot(freqs / 1000, db_vals, "o-", label=cls_name)
    ax.axhline(0.16, color="r", ls="--", alpha=0.6, label=r"paper Thel max $D_B = 16\%$")
    ax.axhline(0.279, color="r", ls=":", alpha=0.6, label=r"cylinder bound $27.9\%$")
    ax.set_xscale("log")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel(r"$D_B = |P_\theta - P_\phi|/(P_\theta + P_\phi)$ (FDTD)")
    ax.set_title("Polarisation residual vs frequency by direction class")
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes[1]
    for f, color in [(3500, "C0"), (5800, "C1")]:
        obs, pred = [], []
        for d in GOLIAT_DIRS:
            tF = df[(df.freq_mhz == f) & (df.direction == d) & (df.pol == "theta")]["fdtd_Pabs_W_m2"]
            pF = df[(df.freq_mhz == f) & (df.direction == d) & (df.pol == "phi")]["fdtd_Pabs_W_m2"]
            tA = df[(df.freq_mhz == f) & (df.direction == d) & (df.pol == "theta")]["L4_Pabs"]
            pA = df[(df.freq_mhz == f) & (df.direction == d) & (df.pol == "phi")]["L4_Pabs"]
            if all(len(x) for x in [tF, pF, tA, pA]):
                tF, pF = float(tF.iloc[0]), float(pF.iloc[0])
                tA, pA = float(tA.iloc[0]), float(pA.iloc[0])
                obs.append((tF - pF) / (tF + pF))
                pred.append((tA - pA) / (tA + pA))
        ax.scatter(obs, pred, color=color, label=f"{f / 1000:.1f} GHz", s=80)
    ax.plot([-0.3, 0.3], [-0.3, 0.3], "k--", alpha=0.4, label="1:1")
    ax.set_xlabel(r"FDTD $D_B^{\rm signed} = (P_\theta - P_\phi)/(P_\theta+P_\phi)$")
    ax.set_ylabel("AEGIS L4 predicted")
    ax.set_title("Polarisation split: AEGIS L4 vs FDTD per direction")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.axhline(0, color="k", alpha=0.2)
    ax.axvline(0, color="k", alpha=0.2)

    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    print(f"[plot] {out_path}")


def fig_geometry_maps(stl_path: Path, geom: dict, out_path: Path):
    """3D phantom maps: 2H, eta, O(r,+x), Sab at 5.8 GHz."""
    import trimesh
    from aegis import DosimetryEngine
    from aegis.geometry.mesh import BodyMesh
    from aegis.paths import PropagationPaths
    from aegis.tissue.dielectric import TissueModel

    body = BodyMesh.load(str(stl_path))
    tm = trimesh.load(str(stl_path))
    V, F = tm.vertices, tm.faces

    def plot_face_field(ax, field, title, cmap, vmin=None, vmax=None, azim=-60, elev=15):
        norm = Normalize(vmin=vmin if vmin is not None else field.min(), vmax=vmax if vmax is not None else field.max())
        colors = plt.get_cmap(cmap)(norm(field))
        pc = Poly3DCollection(V[F], facecolors=colors, edgecolors="none")
        ax.add_collection3d(pc)
        ax.set_xlim(V[:, 0].min(), V[:, 0].max())
        ax.set_ylim(V[:, 1].min(), V[:, 1].max())
        ax.set_zlim(V[:, 2].min(), V[:, 2].max())
        ax.set_box_aspect(
            [
                1,
                (V[:, 1].max() - V[:, 1].min()) / (V[:, 0].max() - V[:, 0].min()),
                (V[:, 2].max() - V[:, 2].min()) / (V[:, 0].max() - V[:, 0].min()),
            ]
        )
        ax.view_init(elev=elev, azim=azim)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.set_title(title, fontsize=10)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        return sm

    fig = plt.figure(figsize=(16, 8))
    sm = plot_face_field(
        fig.add_subplot(141, projection="3d"),
        np.clip(geom["H_2x"], 0, 100),
        "2H (1/m, positive part)\nL5/L6 input",
        cmap="viridis",
        vmin=0,
        vmax=100,
    )
    plt.colorbar(sm, ax=fig.axes[-1], shrink=0.6)
    sm = plot_face_field(
        fig.add_subplot(142, projection="3d"),
        geom["eta"],
        "eta(r), direction-averaged\nexposure fraction",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
    )
    plt.colorbar(sm, ax=fig.axes[-1], shrink=0.6)
    sm = plot_face_field(
        fig.add_subplot(143, projection="3d"),
        geom["vis_x_neg"],
        "O(r, k=-x)\nbinary visibility from source",
        cmap="Blues",
        vmin=0,
        vmax=1,
    )
    plt.colorbar(sm, ax=fig.axes[-1], shrink=0.6)

    f_hz = 5.8e9
    tissue = TissueModel.from_database("Skin", freq_hz=f_hz)
    eng = DosimetryEngine(tissue)
    khat, _, _ = goliat_basis("x_neg")
    paths = PropagationPaths.from_powers(k_hat=khat[None, :], power=np.array([1.0]))
    res = eng.compute(body, paths, level=6, body_mass=17.4, freq_hz=f_hz, curvature_H=geom["H_2x"])
    sm = plot_face_field(
        fig.add_subplot(144, projection="3d"),
        res.sab,
        "S_ab(r), 5.8 GHz, x_neg incidence\nL6, S_inc=1 W/m^2",
        cmap="hot",
        vmin=0,
        vmax=float(res.sab.max()),
    )
    plt.colorbar(sm, ax=fig.axes[-1], shrink=0.6)

    plt.tight_layout()
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"[plot] {out_path}")


def fig_fdtd_bookkeeping(df: pd.DataFrame, body_bbox: tuple, out_path: Path):
    """Power balance ratio and Pin reconciliation."""
    df = df.copy()
    df["ratio"] = (df["fdtd_DielLoss"] + df["fdtd_RadPower"]) / df["fdtd_Pin"]
    df["cls"] = df["direction"].apply(
        lambda d: "lateral (x)" if d.startswith("x") else "frontal (y)" if d.startswith("y") else "vertical (z)"
    )

    dx, dy, dz = body_bbox
    A_perp = {
        "x_pos": dy * dz,
        "x_neg": dy * dz,
        "y_pos": dx * dz,
        "y_neg": dx * dz,
        "z_pos": dx * dy,
        "z_neg": dx * dy,
    }
    df["Pin_theory"] = df["direction"].map(lambda d: 1 / (2 * 376.73) * A_perp[d])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    ax = axes[0]
    for cls in ["lateral (x)", "frontal (y)", "vertical (z)"]:
        sub = df[df["cls"] == cls].groupby("freq_mhz")["ratio"].agg(["mean", "std"])
        ax.errorbar(sub.index / 1000, sub["mean"], yerr=sub["std"], marker="o", label=cls, capsize=2)
    ax.axhline(1.0, color="k", ls="--", alpha=0.4, label="energy conservation")
    ax.set_xscale("log")
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("(DielLoss + RadPower) / Pin")
    ax.set_title("Goliat-reported power balance ratio by direction class")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 4)

    ax = axes[1]
    sc = ax.scatter(
        df["Pin_theory"] * 1e6, df["fdtd_Pin"] * 1e6, c=df["freq_mhz"] / 1000, cmap="viridis", alpha=0.6, s=30
    )
    lim = max(df["fdtd_Pin"].max(), df["Pin_theory"].max()) * 1e6 * 1.1
    ax.plot([0, lim], [0, lim], "k--", alpha=0.5, label="1:1")
    ax.set_xlabel(r"$S_{\rm inc} \cdot A_{\perp}^{\rm phantom\,bbox}$ (uW)")
    ax.set_ylabel("goliat-reported Pin (uW)")
    ax.set_title("Pin: reported vs phantom-bbox theoretical")
    plt.colorbar(sc, ax=ax, label="Frequency (GHz)")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    print(f"[plot] {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--records", default=None, help="parquet from run_tier0.py; default ../data/tier0_<phantom>.parquet"
    )
    ap.add_argument("--phantom", default="thelonious")
    ap.add_argument("--stl", default=None)
    ap.add_argument("--outdir", default=None)
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    val_dir = here.parent
    if args.records is None:
        args.records = str(val_dir / "data" / f"tier0_{args.phantom}.parquet")
    if args.stl is None:
        args.stl = str(val_dir.parent / "data" / f"{args.phantom}.stl")
    if args.outdir is None:
        args.outdir = str(val_dir)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(args.records)
    print(f"[plot] loaded {len(df)} records from {args.records}")

    fig_kernels_vs_fdtd(df, outdir / "fig_kernels_vs_fdtd.png")
    fig_polarisation(df, outdir / "fig_polarisation.png")

    cache_dir = val_dir / "data" / "geometry_cache"
    geom = cache_geometry(args.stl, str(cache_dir))
    fig_geometry_maps(Path(args.stl), geom, outdir / "fig_geometry_maps.png")

    from aegis.geometry.mesh import BodyMesh

    body = BodyMesh.load(args.stl)
    bbox = tuple(body.bounding_box[1] - body.bounding_box[0])
    fig_fdtd_bookkeeping(df, bbox, outdir / "fig_fdtd_bookkeeping.png")


if __name__ == "__main__":
    main()
