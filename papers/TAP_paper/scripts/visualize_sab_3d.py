"""
3D visualization of absorbed power density S_ab on the Thelonious phantom.

Generates a multi-panel figure for the BioEM 2026 extended abstract:
  (a) Exposure fraction η(r)        — geometry only
  (b) S_ab from a specific direction — single plane wave
  (c) ⟨S_ab⟩_4cm² from that direction — spatially averaged

Reuses the software Z-buffer rasteriser from visualize_eta_3d.py (DRY).

Outputs
-------
  bioem2026/figures/sab_3d_panel.png   : multi-panel figure
  monograph/figures/sab_3d_front.png   : single-view S_ab (directional)
  monograph/figures/sab_3d_iso.png     : single-view S_ab (isotropic)

Usage
-----
    python scripts/visualize_sab_3d.py
    python scripts/visualize_sab_3d.py --results artifacts/sab_demo/results.npz
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

# Reuse rendering primitives from the η visualiser (DRY)
from visualize_eta_3d import (
    load_stl_binary,
    _build_view_matrix,
    render_zbuffer,
)


def infer_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Render a single scalar field on the phantom
# ---------------------------------------------------------------------------

def render_scalar_on_phantom(
    vertices: np.ndarray,
    normals: np.ndarray,
    scalar: np.ndarray,
    *,
    vmin: float = 0.0,
    vmax: float | None = None,
    cmap_name: str = "hot",
    azimuth: float = -30.0,
    elevation: float = 10.0,
    W: int = 480,
    H: int = 780,
) -> np.ndarray:
    """
    Render a per-face scalar field on the phantom mesh.

    Returns an (H, W, 3) float64 RGB image.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    if vmax is None:
        vmax = float(np.max(scalar))

    V = _build_view_matrix(azimuth, elevation)

    # Normalise scalar to [0, 1] for the colormap
    norm = Normalize(vmin=vmin, vmax=vmax)
    scalar_normed = np.clip(norm(scalar), 0, 1)

    # render_zbuffer expects eta in [0,1] and uses its own colormap.
    # We call it with our pre-normalised values and desired cmap.
    # To do this cleanly, we use render_zbuffer's cmap_name parameter.
    img = render_zbuffer(vertices, scalar_normed, normals, W, H, V,
                         pad_factor=1.08, cmap_name=cmap_name)
    return img


# ---------------------------------------------------------------------------
# Single-panel figure
# ---------------------------------------------------------------------------

def save_single_panel(
    img: np.ndarray,
    out_path: Path,
    *,
    label: str,
    vmin: float,
    vmax: float,
    cmap_name: str = "hot",
    units: str = "W/m²",
    dpi: int = 200,
) -> None:
    """Save a single 3D render with colorbar."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    fig = plt.figure(figsize=(5.8, 9.2), facecolor="white")

    ax_img = fig.add_axes([0.0, 0.0, 0.78, 1.0])
    ax_img.imshow(img, aspect="equal")
    ax_img.axis("off")

    ax_cb = fig.add_axes([0.82, 0.20, 0.038, 0.45])
    sm = ScalarMappable(cmap=plt.colormaps[cmap_name], norm=Normalize(vmin, vmax))
    sm.set_array([])
    cb = fig.colorbar(sm, cax=ax_cb)
    cb.ax.tick_params(labelsize=10)

    fig.text(0.84, 0.67, label, fontsize=14, ha="center", va="bottom",
             math_fontfamily="dejavuserif")
    if units:
        fig.text(0.84, 0.66, units, fontsize=9, ha="center", va="top",
                 color="#555")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight",
                facecolor="white", pad_inches=0.1)
    plt.close(fig)
    print(f"  Wrote: {out_path}")


# ---------------------------------------------------------------------------
# Multi-panel figure for the abstract
# ---------------------------------------------------------------------------

def create_abstract_figure(
    vertices: np.ndarray,
    normals: np.ndarray,
    eta: np.ndarray,
    sab_front: np.ndarray,
    sab_front_4cm2: np.ndarray | None,
    sab_iso: np.ndarray,
    *,
    S_inc: float,
    T_0: float,
    out_path: Path,
    azimuth: float = -30.0,
    elevation: float = 10.0,
    dpi: int = 250,
) -> None:
    """
    Create a multi-panel figure:
      (a) η(r)  — exposure fraction
      (b) S_ab directional (frontal)
      (c) S_ab isotropic
    Optionally (d) ⟨S_ab⟩_4cm² if provided.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    V = _build_view_matrix(azimuth, elevation)
    W_px, H_px = 400, 650

    print("  Rasterising panels...")
    t0 = time.time()

    # Panel (a): η
    img_eta = render_zbuffer(vertices, eta, normals, W_px, H_px, V,
                             pad_factor=1.08, cmap_name="RdYlBu_r")

    # Panel (b): S_ab frontal — normalise to [0, S_inc*T_0]
    sab_max = S_inc * T_0
    sab_front_norm = np.clip(sab_front / sab_max, 0, 1)
    img_front = render_zbuffer(vertices, sab_front_norm, normals, W_px, H_px, V,
                               pad_factor=1.08, cmap_name="inferno")

    # Panel (c): S_ab isotropic — normalise
    sab_iso_max = float(np.max(sab_iso))
    sab_iso_norm = np.clip(sab_iso / sab_iso_max, 0, 1) if sab_iso_max > 0 else sab_iso
    img_iso = render_zbuffer(vertices, sab_iso_norm, normals, W_px, H_px, V,
                             pad_factor=1.08, cmap_name="inferno")

    # Optional panel (d): 4cm² averaged
    img_4cm2 = None
    if sab_front_4cm2 is not None:
        sab_4cm2_max = float(np.max(sab_front_4cm2))
        sab_4cm2_norm = np.clip(sab_front_4cm2 / sab_max, 0, 1)
        img_4cm2 = render_zbuffer(vertices, sab_4cm2_norm, normals, W_px, H_px, V,
                                  pad_factor=1.08, cmap_name="inferno")

    print(f"  Rasterised in {time.time() - t0:.1f} s")

    # Build figure
    n_panels = 4 if img_4cm2 is not None else 3
    fig_w = 3.6 * n_panels + 1.0  # inches
    fig_h = 9.0

    fig, axes = plt.subplots(1, n_panels, figsize=(fig_w, fig_h), facecolor="white")
    if n_panels == 3:
        axes = list(axes)
    else:
        axes = list(axes)

    panels = []
    # (a) η
    panels.append(('(a)', img_eta, r"$\eta(\mathbf{r})$", 0, 1, "RdYlBu_r", ""))
    # (b) S_ab directional
    panels.append(('(b)', img_front, r"$S_{\mathrm{ab}}$  (frontal)",
                   0, sab_max, "inferno", "W/m²"))
    # (c) S_ab isotropic
    panels.append(('(c)', img_iso, r"$S_{\mathrm{ab}}$  (isotropic)",
                   0, sab_iso_max, "inferno", "W/m²"))
    if img_4cm2 is not None:
        panels.append(('(d)', img_4cm2,
                       r"$\langle S_{\mathrm{ab}}\rangle_{4\,\mathrm{cm}^2}$",
                       0, sab_max, "inferno", "W/m²"))

    for ax, (letter, img, title, vmin, vmax, cmap, units) in zip(axes, panels):
        ax.imshow(img, aspect="equal")
        ax.axis("off")
        ax.set_title(f"{letter}  {title}", fontsize=12, pad=8)

    # Colorbars — one for η, one shared for S_ab panels
    # η colorbar
    cax_eta = fig.add_axes([0.02 + 0.78 / n_panels, 0.08, 0.015, 0.25])
    sm_eta = ScalarMappable(cmap=plt.colormaps["RdYlBu_r"], norm=Normalize(0, 1))
    sm_eta.set_array([])
    cb_eta = fig.colorbar(sm_eta, cax=cax_eta)
    cb_eta.ax.tick_params(labelsize=8)

    # S_ab colorbar (rightmost)
    cax_sab = fig.add_axes([0.95, 0.08, 0.015, 0.25])
    sm_sab = ScalarMappable(cmap=plt.colormaps["inferno"], norm=Normalize(0, sab_max))
    sm_sab.set_array([])
    cb_sab = fig.colorbar(sm_sab, cax=cax_sab)
    cb_sab.set_label("W/m²", fontsize=9)
    cb_sab.ax.tick_params(labelsize=8)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight",
                facecolor="white", pad_inches=0.15)
    plt.close(fig)
    print(f"  Wrote: {out_path}")


# ---------------------------------------------------------------------------
# Two-panel figure: η + S_ab (compact, for the abstract)
# ---------------------------------------------------------------------------

def create_two_panel_figure(
    vertices: np.ndarray,
    normals: np.ndarray,
    eta: np.ndarray,
    sab: np.ndarray,
    *,
    sab_label: str = r"$S_{\mathrm{ab}}$",
    sab_vmax: float,
    out_path: Path,
    azimuth: float = -30.0,
    elevation: float = 10.0,
    dpi: int = 250,
) -> None:
    """
    Compact 2-panel: (a) η(r), (b) S_ab from one direction.
    Designed for a half-page figure in the extended abstract.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    V = _build_view_matrix(azimuth, elevation)
    W_px, H_px = 420, 680

    print("  Rasterising 2-panel figure...")
    t0 = time.time()

    img_eta = render_zbuffer(vertices, eta, normals, W_px, H_px, V,
                             pad_factor=1.08, cmap_name="RdYlBu_r")

    sab_norm = np.clip(sab / sab_vmax, 0, 1)
    img_sab = render_zbuffer(vertices, sab_norm, normals, W_px, H_px, V,
                             pad_factor=1.08, cmap_name="inferno")
    print(f"  Rasterised in {time.time() - t0:.1f} s")

    fig = plt.figure(figsize=(10.5, 9.2), facecolor="white")

    # Left: η
    ax_a = fig.add_axes([0.00, 0.0, 0.40, 1.0])
    ax_a.imshow(img_eta, aspect="equal")
    ax_a.axis("off")
    ax_a.set_title(r"(a)  $\eta(\mathbf{r})$", fontsize=13, pad=10)

    # η colorbar
    ax_cb_eta = fig.add_axes([0.405, 0.22, 0.018, 0.38])
    sm_eta = ScalarMappable(cmap=plt.colormaps["RdYlBu_r"], norm=Normalize(0, 1))
    sm_eta.set_array([])
    cb_eta = fig.colorbar(sm_eta, cax=ax_cb_eta)
    cb_eta.set_ticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    cb_eta.ax.tick_params(labelsize=9)

    # Right: S_ab
    ax_b = fig.add_axes([0.50, 0.0, 0.40, 1.0])
    ax_b.imshow(img_sab, aspect="equal")
    ax_b.axis("off")
    ax_b.set_title(f"(b)  {sab_label}", fontsize=13, pad=10)

    # S_ab colorbar
    ax_cb_sab = fig.add_axes([0.905, 0.22, 0.018, 0.38])
    sm_sab = ScalarMappable(cmap=plt.colormaps["inferno"], norm=Normalize(0, sab_vmax))
    sm_sab.set_array([])
    cb_sab = fig.colorbar(sm_sab, cax=ax_cb_sab)
    cb_sab.ax.tick_params(labelsize=9)
    fig.text(0.914, 0.62, "W/m²", fontsize=9, ha="center", va="bottom", color="#444")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight",
                facecolor="white", pad_inches=0.12)
    plt.close(fig)
    print(f"  Wrote: {out_path}")


# ---------------------------------------------------------------------------
# Combined 2+1 figure: (a) η, (b) S_ab on top; (c) D(k) Mollweide below
# ---------------------------------------------------------------------------

def create_combined_figure(
    vertices: np.ndarray,
    normals: np.ndarray,
    eta: np.ndarray,
    sab: np.ndarray,
    D: np.ndarray,
    k_hat_dirs: np.ndarray,
    *,
    sab_label: str = r"$S_{\mathrm{ab}}$  (frontal, 10 W/m$^2$)",
    sab_vmax: float,
    D_max: float,
    D_min: float,
    out_path: Path,
    azimuth: float = -30.0,
    elevation: float = 10.0,
    dpi: int = 250,
) -> None:
    """
    Combined figure with layout:
        | (a) η(r) | (b) S_ab |
        |      (c) D(k̂)       |

    Top row: two 3D body renders with colorbars.
    Bottom row: directivity Mollweide projection spanning full width.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    V = _build_view_matrix(azimuth, elevation)
    W_px, H_px = 420, 680

    print("  Rasterising top panels...")
    t0 = time.time()

    # Panel (a): η
    img_eta = render_zbuffer(vertices, eta, normals, W_px, H_px, V,
                             pad_factor=1.08, cmap_name="RdYlBu_r")

    # Panel (b): S_ab
    sab_norm = np.clip(sab / sab_vmax, 0, 1)
    img_sab = render_zbuffer(vertices, sab_norm, normals, W_px, H_px, V,
                             pad_factor=1.08, cmap_name="inferno")
    print(f"  Rasterised in {time.time() - t0:.1f} s")

    # Compute lon/lat for directivity Mollweide
    k = k_hat_dirs / np.linalg.norm(k_hat_dirs, axis=1, keepdims=True)
    lon = np.arctan2(k[:, 1], k[:, 0])        # [-pi, pi]
    lat = np.pi / 2 - np.arccos(np.clip(k[:, 2], -1, 1))  # [-pi/2, pi/2]

    # Build figure with gridspec: 2 rows, 2 cols
    # Top row: (a) and (b) each take one column
    # Bottom row: (c) spans both columns
    fig = plt.figure(figsize=(11.0, 12.5), facecolor="white")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.55, 1.0],
                          hspace=0.08, wspace=0.05)

    # --- Top left: (a) η ---
    ax_a = fig.add_subplot(gs[0, 0])
    ax_a.imshow(img_eta, aspect="equal")
    ax_a.axis("off")
    ax_a.set_title(r"(a)  $\eta(\mathbf{r})$", fontsize=13, pad=8)

    # --- Top right: (b) S_ab ---
    ax_b = fig.add_subplot(gs[0, 1])
    ax_b.imshow(img_sab, aspect="equal")
    ax_b.axis("off")
    ax_b.set_title(f"(b)  {sab_label}", fontsize=13, pad=8)

    # --- Bottom: (c) D(k̂) Mollweide ---
    ax_c = fig.add_subplot(gs[1, :], projection="mollweide")
    sc = ax_c.scatter(lon, lat, c=D, s=5, cmap="viridis", linewidths=0,
                      alpha=0.92, vmin=D_min * 0.95, vmax=D_max * 1.02)
    ax_c.grid(True, alpha=0.3)
    ax_c.set_title(r"(c)  Absorption directivity $D(\hat{\mathbf{k}})$",
                    fontsize=13, pad=10)

    # Colorbars
    # η colorbar (left of top row)
    bbox_a = ax_a.get_position()
    cax_eta = fig.add_axes([bbox_a.x1 + 0.005, bbox_a.y0 + 0.12,
                            0.012, bbox_a.height * 0.5])
    sm_eta = ScalarMappable(cmap=plt.colormaps["RdYlBu_r"], norm=Normalize(0, 1))
    sm_eta.set_array([])
    cb_eta = fig.colorbar(sm_eta, cax=cax_eta)
    cb_eta.set_ticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    cb_eta.ax.tick_params(labelsize=8)

    # S_ab colorbar (right of top row)
    bbox_b = ax_b.get_position()
    cax_sab = fig.add_axes([bbox_b.x1 + 0.005, bbox_b.y0 + 0.12,
                            0.012, bbox_b.height * 0.5])
    sm_sab = ScalarMappable(cmap=plt.colormaps["inferno"],
                            norm=Normalize(0, sab_vmax))
    sm_sab.set_array([])
    cb_sab = fig.colorbar(sm_sab, cax=cax_sab)
    cb_sab.ax.tick_params(labelsize=8)
    fig.text(cax_sab.get_position().x1 + 0.008,
             cax_sab.get_position().y1, "W/m$^2$",
             fontsize=8, ha="left", va="top", color="#444")

    # D colorbar (below Mollweide)
    cb_D = fig.colorbar(sc, ax=ax_c, orientation="horizontal",
                        pad=0.08, fraction=0.06, aspect=35)
    cb_D.set_label(r"$D(\hat{\mathbf{k}})$", fontsize=11)
    cb_D.ax.tick_params(labelsize=9)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight",
                facecolor="white", pad_inches=0.12)
    plt.close(fig)
    print(f"  Wrote: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    root = infer_repo_root()
    p = argparse.ArgumentParser(
        description="3D S_ab visualisation on Thelonious phantom.")
    p.add_argument("--stl", default=str(root / "data" / "thelonious.stl"))
    p.add_argument("--eta_npz", default=str(root / "artifacts" / "eta" / "thelonious" / "eta.npz"))
    p.add_argument("--results", default=str(root / "artifacts" / "sab_demo" / "results.npz"),
                   help="Path to sab_demo results.npz")
    p.add_argument("--lut", default=str(root / "artifacts" / "body" / "thelonious" / "A_perp_lut.npz"),
                   help="Path to A_perp LUT for directivity")
    p.add_argument("--dpi", type=int, default=250)
    p.add_argument("--azimuth", type=float, default=-30.0)
    p.add_argument("--elevation", type=float, default=10.0)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = infer_repo_root()

    # Load mesh
    print(f"Loading mesh: {args.stl}")
    vertices, normals, centroids = load_stl_binary(args.stl)
    n_tri = vertices.shape[0]
    print(f"  {n_tri:,} triangles")

    # Load η
    print(f"Loading η: {args.eta_npz}")
    eta = np.load(args.eta_npz)["eta"]
    assert eta.shape[0] == n_tri

    # Load sab_demo results
    print(f"Loading results: {args.results}")
    res = np.load(args.results, allow_pickle=True)

    S_inc = float(res['S_inc'])
    T_0 = float(res['T_0'])
    sab_front = res['sab_front']
    sab_iso = res['sab_iso']
    sab_front_4cm2 = res.get('sab_front_4cm2', None)
    sab_worst = res.get('sab_worst', None)

    sab_max = S_inc * T_0

    # --- Load directivity data ---
    print(f"Loading A_perp LUT: {args.lut}")
    lut = np.load(args.lut)
    A_perp_lut = lut['A_perp']
    k_hat_dirs = lut['k_hat']
    A_perp_mean = float(np.mean(A_perp_lut))
    D = A_perp_lut / A_perp_mean  # D = A_perp / <A_perp>, gives <D> = 1
    D_max = float(np.max(D))
    D_min = float(np.min(D))
    print(f"  D_max = {D_max:.4f}, D_min = {D_min:.4f}")

    # --- 1. Combined 2+1 figure for the abstract ---
    combined_path = root / "bioem2026" / "figures" / "eta_sab_D_panel.png"
    print(f"\nCreating combined 2+1 figure: {combined_path}")
    create_combined_figure(
        vertices, normals, eta, sab_front,
        D, k_hat_dirs,
        sab_label=r"$S_{\mathrm{ab}}$  (frontal, 10 W/m$^2$)",
        sab_vmax=sab_max,
        D_max=D_max, D_min=D_min,
        out_path=combined_path,
        azimuth=args.azimuth,
        elevation=args.elevation,
        dpi=args.dpi,
    )

    # --- 2. Also keep the 2-panel version ---
    two_panel_path = root / "bioem2026" / "figures" / "eta_sab_panel.png"
    print(f"\nCreating 2-panel figure: {two_panel_path}")
    create_two_panel_figure(
        vertices, normals, eta, sab_front,
        sab_label=r"$S_{\mathrm{ab}}$  (frontal, 10 W/m$^2$)",
        sab_vmax=sab_max,
        out_path=two_panel_path,
        azimuth=args.azimuth,
        elevation=args.elevation,
        dpi=args.dpi,
    )

    # --- 3. Single-panel S_ab renders for the monograph ---
    print(f"\nCreating single-panel renders for monograph...")

    img_front = render_scalar_on_phantom(
        vertices, normals, sab_front,
        vmin=0, vmax=sab_max, cmap_name="inferno",
        azimuth=args.azimuth, elevation=args.elevation,
    )
    save_single_panel(
        img_front, root / "monograph" / "figures" / "sab_3d_front.png",
        label=r"$S_{\mathrm{ab}}$", vmin=0, vmax=sab_max,
        cmap_name="inferno", units="W/m²", dpi=args.dpi,
    )

    img_iso = render_scalar_on_phantom(
        vertices, normals, sab_iso,
        vmin=0, vmax=float(np.max(sab_iso)), cmap_name="inferno",
        azimuth=args.azimuth, elevation=args.elevation,
    )
    save_single_panel(
        img_iso, root / "monograph" / "figures" / "sab_3d_iso.png",
        label=r"$S_{\mathrm{ab}}^{\,\mathrm{iso}}$",
        vmin=0, vmax=float(np.max(sab_iso)),
        cmap_name="inferno", units="W/m²", dpi=args.dpi,
    )

    if sab_front_4cm2 is not None:
        img_4cm2 = render_scalar_on_phantom(
            vertices, normals, sab_front_4cm2,
            vmin=0, vmax=sab_max, cmap_name="inferno",
            azimuth=args.azimuth, elevation=args.elevation,
        )
        save_single_panel(
            img_4cm2, root / "monograph" / "figures" / "sab_3d_4cm2.png",
            label=r"$\langle S_{\mathrm{ab}}\rangle_{4\,\mathrm{cm}^2}$",
            vmin=0, vmax=sab_max,
            cmap_name="inferno", units="W/m²", dpi=args.dpi,
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
