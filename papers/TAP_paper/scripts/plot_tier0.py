"""Regenerate the four Tier 0 figures from the parquet produced by run_tier0.py.

Usage:
    python plot_tier0.py [--records data/tier0_thelonious.parquet]
                         [--phantom thelonious]
                         [--outdir figures]
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

try:
    from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402
    _HAVE_STYLE = True
except Exception:
    _HAVE_STYLE = False


def fig_kernels_vs_fdtd(df: pd.DataFrame, out_path: Path, *, ieee: bool = False):
    """Single-panel: kernel curves with errorbars + Cauchy stars."""
    freqs = np.sort(df["freq_mhz"].unique())
    if ieee:
        # Leave room inside the figure for the legend so the saved PDF is
        # exactly column-width and LaTeX includegraphics does not rescale.
        fig, ax = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.95))
    else:
        fig, ax = plt.subplots(1, 1, figsize=(7, 5.0))

    # (col, color, marker, linestyle, label)
    kernels = [
        ("L3_Pabs",   "#0072B2", "o", (0, (1, 1)),       "Fresnel"),
        ("L4_Pabs",   "#009E73", "s", (0, (3, 1, 1, 1)), "+ polar."),
        ("L6_Pabs",   "#E69F00", "^", (0, (5, 2)),       r"+ curv./diffr."),
        ("Lall_Pabs", "#CC79A7", "D", "-",               "Full"),
        ("Lallo_Pabs","#56B4E9", "P", (0, (2, 1)),       "Full + occl."),
    ]

    for col, color, marker, ls, label in kernels:
        means, stds = [], []
        for f in freqs:
            sub = df[df["freq_mhz"] == f]
            ratios = sub[col] / sub["fdtd_Pabs_W_m2"]
            means.append(ratios.mean())
            stds.append(ratios.std())
        ax.errorbar(
            freqs / 1000, means, yerr=stds,
            marker=marker, color=color, linestyle=ls,
            label=label, capsize=1.8, lw=1.0, ms=4.0,
            markerfacecolor="none", markeredgewidth=0.9,
            elinewidth=0.6,
        )

    # Cauchy stars: closed form vs FDTD direction-averaged
    grouped = df.groupby("freq_mhz").mean(numeric_only=True)
    fdtd_avg = grouped["fdtd_Pabs_W_m2"]
    cauchy_ratio = grouped["Cauchy_Pabs"] / fdtd_avg
    ax.plot(
        grouped.index / 1000, cauchy_ratio,
        marker="*", color="black", linestyle="-",
        markersize=8.0, lw=1.2, markerfacecolor="none", markeredgewidth=0.9,
        label=r"Cauchy formula",
        zorder=10,
    )
    ax.axhline(1.0, color="k", ls=(0, (4, 2)), lw=0.7, alpha=0.6, zorder=0)

    # Annotate Cauchy at 5.8 GHz (closed form, no fit)
    f58 = 5.8
    y58 = float(cauchy_ratio.iloc[-1])
    ax.annotate(
        f"Cauchy: {y58:.3f}\nat 5.8\\,GHz (no fit)",
        xy=(f58, y58), xytext=(2.0, 0.30),
        fontsize=7.0, ha="left", va="center",
        arrowprops=dict(arrowstyle="-", lw=0.6, color="black",
                        shrinkA=0.5, shrinkB=2.0,
                        connectionstyle="arc3,rad=-0.15"),
    )

    ax.set_xscale("linear")
    ax.set_xticks([0, 1, 2, 3, 4, 5, 6])
    ax.set_xlabel(r"Frequency $f$ [GHz]")
    ax.set_ylabel(
        r"$P_{\mathrm{abs}}^{\mathrm{law}} / P_{\mathrm{abs}}^{\mathrm{FDTD}}$"
    )
    ax.set_xlim(0.0, 6.0)
    ax.set_ylim(0.15, 1.45)
    ax.grid(alpha=0.25)

    # Legend on the axes (axes-relative coords) so the saved bbox tracks
    # axes width, not figure width. fig.legend would span the full figure
    # width and force bbox_inches="tight" to keep that width, leaving the
    # plot panel narrower than the column once LaTeX scales to columnwidth.
    leg = ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.18),
        ncol=3, fontsize=7.0,
        handlelength=1.4, handletextpad=0.3,
        columnspacing=0.6, borderpad=0.3,
        frameon=True, fancybox=False,
    )
    leg.get_frame().set_edgecolor("black")
    leg.get_frame().set_linewidth(1.0)

    suf = Path(out_path).suffix.lower()
    # bbox_inches="tight" then crops to axes + y-label + legend, giving a
    # PDF that LaTeX displays with the plot panel filling the column width
    # (minus the y-label).
    if suf == ".png":
        plt.savefig(Path(out_path).with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.02)
        print(f"[plot] {Path(out_path).with_suffix('.pdf')}")
    plt.savefig(out_path, dpi=300, bbox_inches="tight", pad_inches=0.02)
    print(f"[plot] {out_path}")
    plt.close(fig)


def fig_polarisation(df: pd.DataFrame, out_path: Path, goliat_dirs: dict):
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
        for d in goliat_dirs:
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
    """3D phantom maps: 2H, eta, O(r,+x), APD at 5.8 GHz."""
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
        "APD(r), 5.8 GHz, x_neg incidence\nL6, IPD=1 W/m^2",
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
        "--records", default=None, help="parquet from run_tier0.py; default data/tier0_<phantom>.parquet"
    )
    ap.add_argument("--phantom", default="thelonious")
    ap.add_argument("--stl", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument(
        "--mode",
        choices=["png", "pdf"],
        default="pdf",
        help="Style mode: 'pdf' uses SciencePlots+LaTeX; 'png' falls back to no-LaTeX.",
    )
    ap.add_argument(
        "--ieee",
        action="store_true",
        default=True,
        help="Use IEEE column sizing for figures suitable for publication.",
    )
    ap.add_argument(
        "--diagnostics",
        action="store_true",
        help=(
            "Also regenerate diagnostic geometry/bookkeeping figures. This path "
            "requires the broader AEGIS package and validation geometry helpers "
            "and is not needed for the TAP publication figure."
        ),
    )
    args = ap.parse_args()

    if _HAVE_STYLE:
        try:
            apply_monograph_style(mode=args.mode)
        except Exception as exc:
            print(f"[plot] WARNING: could not apply SciencePlots style ({exc}); using defaults.")

    here = Path(__file__).resolve().parent
    paper_root = here.parent
    if args.records is None:
        args.records = str(paper_root / "data" / f"tier0_{args.phantom}.parquet")
    if args.stl is None:
        args.stl = str(paper_root / "data" / f"{args.phantom}.stl")
    if args.outdir is None:
        args.outdir = str(paper_root / "figures")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(args.records)
    print(f"[plot] loaded {len(df)} records from {args.records}")

    fig_kernels_vs_fdtd(df, outdir / "fig_kernels_vs_fdtd.png", ieee=bool(args.ieee))

    if args.diagnostics:
        try:
            from geometry import GOLIAT_DIRS, cache_geometry  # type: ignore
            from aegis.geometry.mesh import BodyMesh
        except Exception as exc:
            raise RuntimeError(
                "Tier-0 diagnostics require the broader AEGIS package and "
                "validation/scripts/geometry.py. The publication figure path "
                "is self-contained and does not use these imports."
            ) from exc

        fig_polarisation(df, outdir / "fig_polarisation.png", GOLIAT_DIRS)
        cache_dir = paper_root / "data" / "geometry_cache"
        geom = cache_geometry(args.stl, str(cache_dir))
        fig_geometry_maps(Path(args.stl), geom, outdir / "fig_geometry_maps.png")

        body = BodyMesh.load(args.stl)
        bbox = tuple(body.bounding_box[1] - body.bounding_box[0])
        fig_fdtd_bookkeeping(df, bbox, outdir / "fig_fdtd_bookkeeping.png")


if __name__ == "__main__":
    main()
