"""
Visualization helper for Task 05 polarization response tables.

Loads a `.npz` produced by:
  `scripts/compute_polarization_response_tables.py`

Expected arrays in the .npz:
  - k_hat: (N,3)
  - A_tilde: (N,)
  - B_c: (N,)
  - B_s: (N,)

Produces:
  - Mollweide binned maps + histograms for A_tilde, B_c, B_s
  - Derived maps for |B| = sqrt(B_c^2 + B_s^2)
  - A simple "max fractional polarization effect" proxy:
        frac_max(k̂) = |B(k̂)| / (2*A_tilde(k̂))
    since max |ΔP_pol| = (cos(2χ)/2)|B| and baseline is ~A_tilde (S_inc=1).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import numpy as np


def _lon_lat_from_khat(k_hat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """lon in [-pi,pi], lat in [-pi/2, pi/2]."""
    k_hat = np.asarray(k_hat, dtype=float)
    if k_hat.ndim != 2 or k_hat.shape[1] != 3:
        raise ValueError(f"Expected k_hat shape (N,3); got {k_hat.shape}")
    norms = np.linalg.norm(k_hat, axis=1)
    if not np.all(norms > 0):
        raise ValueError("k_hat contains zero-length vectors")
    k = k_hat / norms[:, None]
    lon = np.arctan2(k[:, 1], k[:, 0])
    lat = np.arcsin(np.clip(k[:, 2], -1.0, 1.0))
    return lon, lat


def _binned_mean(lat: np.ndarray, lon: np.ndarray, values: np.ndarray, *, n_lat: int = 180, n_lon: int = 360) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (LonCentersGrid, LatCentersGrid, mean_values_grid) for pcolormesh on Mollweide."""
    lon_edges = np.linspace(-np.pi, np.pi, n_lon + 1)
    lat_edges = np.linspace(-np.pi / 2, np.pi / 2, n_lat + 1)

    sum_v, _, _ = np.histogram2d(lat, lon, bins=[lat_edges, lon_edges], weights=values)
    cnt, _, _ = np.histogram2d(lat, lon, bins=[lat_edges, lon_edges])
    mean_v = np.divide(sum_v, cnt, out=np.full_like(sum_v, np.nan), where=cnt > 0)

    lon_centers = 0.5 * (lon_edges[:-1] + lon_edges[1:])
    lat_centers = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    Lon, Lat = np.meshgrid(lon_centers, lat_centers)
    return Lon, Lat, mean_v


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot polarization response tables (Task 05).")
    p.add_argument("--tables", type=Path, required=True, help="Path to .npz from compute_polarization_response_tables.py")
    p.add_argument("--out", type=Path, default=None, help="Output directory for PNGs. Default: alongside the .npz")
    p.add_argument(
        "--mode",
        type=str,
        default="auto",
        choices=["auto", "binned", "scatter"],
        help="Plot mode for Mollweide maps. 'auto' uses scatter for small N and binned for large N.",
    )
    p.add_argument("--n_lon", type=int, default=360)
    p.add_argument("--n_lat", type=int, default=180)
    return p.parse_args()


def _plot_hist(values: np.ndarray, *, title: str, xlabel: str, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    v = np.asarray(values, dtype=float)
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 4.5))
    ax.hist(v[np.isfinite(v)], bins=70, color="#377eb8", alpha=0.8, edgecolor="black", linewidth=0.35)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("count")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _plot_mollweide_binned(k_hat: np.ndarray, values: np.ndarray, *, title: str, cbar_label: str, out_path: Path, n_lat: int, n_lon: int) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    lon, lat = _lon_lat_from_khat(k_hat)
    Lon, Lat, mean_v = _binned_mean(lat, lon, values, n_lat=n_lat, n_lon=n_lon)

    finite = np.isfinite(mean_v)
    if not np.any(finite):
        raise ValueError("No finite bins to plot (did you pass empty values?)")

    vmin = float(np.nanpercentile(mean_v, 1))
    vmax = float(np.nanpercentile(mean_v, 99))
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin = float(np.nanmin(mean_v))
        vmax = float(np.nanmax(mean_v))

    fig = plt.figure(figsize=(10.5, 5.5))
    ax = fig.add_subplot(111, projection="mollweide")
    norm = Normalize(vmin=vmin, vmax=vmax)
    im = ax.pcolormesh(Lon, Lat, mean_v, shading="nearest", cmap="viridis", norm=norm)
    ax.grid(True, alpha=0.25)
    ax.set_title(title)
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.08, fraction=0.06)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

def _plot_mollweide_scatter(k_hat: np.ndarray, values: np.ndarray, *, title: str, cbar_label: str, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    lon, lat = _lon_lat_from_khat(k_hat)
    v = np.asarray(values, dtype=float)

    fig = plt.figure(figsize=(10.5, 5.5))
    ax = fig.add_subplot(111, projection="mollweide")
    sc = ax.scatter(lon, lat, c=v, s=10, cmap="viridis", linewidths=0, alpha=0.95)
    ax.grid(True, alpha=0.35)
    ax.set_title(title)
    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", pad=0.08, fraction=0.06)
    cb.set_label(cbar_label)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = _parse_args()
    tables_path = args.tables
    if not tables_path.exists():
        raise FileNotFoundError(tables_path)

    out_dir = args.out if args.out is not None else tables_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(tables_path)
    for k in ("k_hat", "A_tilde", "B_c", "B_s"):
        if k not in data:
            raise KeyError(f"{tables_path} missing required array '{k}'")

    k_hat = np.asarray(data["k_hat"], dtype=float)
    A = np.asarray(data["A_tilde"], dtype=float).reshape(-1)
    Bc = np.asarray(data["B_c"], dtype=float).reshape(-1)
    Bs = np.asarray(data["B_s"], dtype=float).reshape(-1)

    if k_hat.shape[0] != A.shape[0] or A.shape != Bc.shape or A.shape != Bs.shape:
        raise ValueError("Array shapes must match: k_hat (N,3), A_tilde (N,), B_c (N,), B_s (N,)")

    Bmag = np.sqrt(Bc * Bc + Bs * Bs)
    frac_max = np.divide(Bmag, 2.0 * A, out=np.full_like(Bmag, np.nan), where=(A > 0) & np.isfinite(A))

    stem = tables_path.stem
    N = int(k_hat.shape[0])
    mode = args.mode
    if mode == "auto":
        # Heuristic: below this, binning onto a 180x360 grid looks like a few isolated pixels.
        mode = "scatter" if N < 2000 else "binned"

    try:
        _plot_hist(A, title=f"{stem}: A_tilde histogram", xlabel="A_tilde", out_path=out_dir / f"{stem}_A_tilde_hist.png")
        _plot_hist(Bc, title=f"{stem}: B_c histogram", xlabel="B_c", out_path=out_dir / f"{stem}_B_c_hist.png")
        _plot_hist(Bs, title=f"{stem}: B_s histogram", xlabel="B_s", out_path=out_dir / f"{stem}_B_s_hist.png")
        _plot_hist(Bmag, title=f"{stem}: |B| histogram", xlabel="|B|", out_path=out_dir / f"{stem}_B_mag_hist.png")
        _plot_hist(frac_max, title=f"{stem}: |B|/(2 A_tilde) histogram", xlabel="|B|/(2 A_tilde)", out_path=out_dir / f"{stem}_frac_max_hist.png")

        if mode == "scatter":
            _plot_mollweide_scatter(
                k_hat, A,
                title=f"A_tilde(k_hat) directional map (scatter): {stem}",
                cbar_label="A_tilde",
                out_path=out_dir / f"{stem}_A_tilde_mollweide_scatter.png",
            )
            _plot_mollweide_scatter(
                k_hat, Bc,
                title=f"B_c(k_hat) directional map (scatter): {stem}",
                cbar_label="B_c",
                out_path=out_dir / f"{stem}_B_c_mollweide_scatter.png",
            )
            _plot_mollweide_scatter(
                k_hat, Bs,
                title=f"B_s(k_hat) directional map (scatter): {stem}",
                cbar_label="B_s",
                out_path=out_dir / f"{stem}_B_s_mollweide_scatter.png",
            )
            _plot_mollweide_scatter(
                k_hat, Bmag,
                title=f"|B|(k_hat) directional map (scatter): {stem}",
                cbar_label="|B|",
                out_path=out_dir / f"{stem}_B_mag_mollweide_scatter.png",
            )
            _plot_mollweide_scatter(
                k_hat, frac_max,
                title=f"|B|/(2 A_tilde) directional map (scatter): {stem}",
                cbar_label="|B|/(2 A_tilde)",
                out_path=out_dir / f"{stem}_frac_max_mollweide_scatter.png",
            )
        else:
            _plot_mollweide_binned(
                k_hat, A,
                title=f"A_tilde(k_hat) directional map (binned): {stem}",
                cbar_label="mean A_tilde in bin",
                out_path=out_dir / f"{stem}_A_tilde_mollweide.png",
                n_lat=args.n_lat, n_lon=args.n_lon,
            )
            _plot_mollweide_binned(
                k_hat, Bc,
                title=f"B_c(k_hat) directional map (binned): {stem}",
                cbar_label="mean B_c in bin",
                out_path=out_dir / f"{stem}_B_c_mollweide.png",
                n_lat=args.n_lat, n_lon=args.n_lon,
            )
            _plot_mollweide_binned(
                k_hat, Bs,
                title=f"B_s(k_hat) directional map (binned): {stem}",
                cbar_label="mean B_s in bin",
                out_path=out_dir / f"{stem}_B_s_mollweide.png",
                n_lat=args.n_lat, n_lon=args.n_lon,
            )
            _plot_mollweide_binned(
                k_hat, Bmag,
                title=f"|B|(k_hat) directional map (binned): {stem}",
                cbar_label="mean |B| in bin",
                out_path=out_dir / f"{stem}_B_mag_mollweide.png",
                n_lat=args.n_lat, n_lon=args.n_lon,
            )
            _plot_mollweide_binned(
                k_hat, frac_max,
                title=f"|B|/(2 A_tilde) directional map (binned): {stem}",
                cbar_label="mean |B|/(2 A_tilde) in bin",
                out_path=out_dir / f"{stem}_frac_max_mollweide.png",
                n_lat=args.n_lat, n_lon=args.n_lon,
            )
    except ModuleNotFoundError as e:
        raise SystemExit(f"Matplotlib required for plotting but not installed: {e}")

    print(f"Wrote plots to: {out_dir}")


if __name__ == "__main__":
    main()

