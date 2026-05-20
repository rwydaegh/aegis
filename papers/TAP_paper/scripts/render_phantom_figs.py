"""
Render phantom-with-colour figures for Papers A and B.

Outputs (in ./figures/):
  - eta_phantom_paperB.pdf, .png : single-panel eta(r) on Thelonious for Paper B
  - sab_phantom_pair.pdf, .png   : two-panel S_ab(r) on Thelonious for Paper A
                                    (a) convex limit V=1, (b) V(r,k_hat)

Uses local BVH and rasteriser helpers in this PaperMaker instance.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent

# Reuse the existing primitives
from compute_exposure_fraction_eta import (
    load_stl_binary,
    cosine_weighted_hemisphere_samples,
    make_tangent_frame,
    build_bvh,
    ray_mesh_any_hit_bvh,
)
from visualize_eta_3d import (
    _build_view_matrix,
    render_zbuffer,
)
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402


FIGURE_DIR = REPO_ROOT / "figures"
CACHE_DIR = REPO_ROOT / "data"
STL = REPO_ROOT / "data" / "thelonious.stl"


def compute_eta(
    centroids, normals, vertices, n_samples=64, seed=12345
):
    """Compute exposure fraction eta(r) at each triangle centroid."""
    import time
    n_tris = centroids.shape[0]

    # Triangle vertex/edge data flat
    v0 = vertices[:, 0, :]
    e1 = vertices[:, 1, :] - v0
    e2 = vertices[:, 2, :] - v0
    bmin = np.minimum(np.minimum(vertices[:, 0], vertices[:, 1]), vertices[:, 2])
    bmax = np.maximum(np.maximum(vertices[:, 0], vertices[:, 1]), vertices[:, 2])

    print(f"  Building BVH over {n_tris:,} triangles...")
    bvh, tri_indices = build_bvh(bmin, bmax, centroids)
    v0x, v0y, v0z = v0[:, 0].copy(), v0[:, 1].copy(), v0[:, 2].copy()
    e1x, e1y, e1z = e1[:, 0].copy(), e1[:, 1].copy(), e1[:, 2].copy()
    e2x, e2y, e2z = e2[:, 0].copy(), e2[:, 1].copy(), e2[:, 2].copy()

    rng = np.random.default_rng(seed)
    samples = cosine_weighted_hemisphere_samples(n_samples, rng)

    eta = np.zeros(n_tris, dtype=np.float64)
    bbox_size = float(np.linalg.norm(bmax.max(0) - bmin.min(0)))
    eps = 1e-4 * bbox_size

    print(f"  Tracing {n_samples} rays per triangle...")
    t0 = time.time()
    for i in range(n_tris):
        if i % 2000 == 0:
            elapsed = time.time() - t0
            rate = i / max(elapsed, 1e-3)
            eta_remaining = (n_tris - i) / max(rate, 1e-3) if i > 0 else 0
            print(f"    {i}/{n_tris}  ({elapsed:.0f}s elapsed, "
                  f"~{eta_remaining:.0f}s remaining)", flush=True)
        n = normals[i]
        t, b = make_tangent_frame(n)
        # World-space directions
        dirs = samples[:, 0:1] * t + samples[:, 1:2] * b + samples[:, 2:3] * n
        origin = centroids[i] + eps * n
        n_hit = 0
        for s in range(n_samples):
            d = dirs[s]
            hit = ray_mesh_any_hit_bvh(
                float(origin[0]), float(origin[1]), float(origin[2]),
                float(d[0]), float(d[1]), float(d[2]),
                bvh, tri_indices,
                v0x, v0y, v0z, e1x, e1y, e1z, e2x, e2y, e2z,
                ignore_tri=int(i), t_min=0.0,
            )
            if hit:
                n_hit += 1
        eta[i] = 1.0 - n_hit / n_samples
    return eta


def compute_visibility(
    centroids, normals, vertices, k_hat, eps_factor=1e-4
):
    """
    Compute binary visibility V(r, k_hat) for each triangle:
        V = 1 if a ray from centroid in direction (-k_hat) does not hit
            another triangle of the body, 0 otherwise.

    Front-facing test (n . -k_hat > 0) is enforced separately when used.
    """
    n_tris = centroids.shape[0]
    v0 = vertices[:, 0, :]
    e1 = vertices[:, 1, :] - v0
    e2 = vertices[:, 2, :] - v0
    bmin = np.minimum(np.minimum(vertices[:, 0], vertices[:, 1]), vertices[:, 2])
    bmax = np.maximum(np.maximum(vertices[:, 0], vertices[:, 1]), vertices[:, 2])

    print(f"  Building BVH over {n_tris:,} triangles...")
    bvh, tri_indices = build_bvh(bmin, bmax, centroids)
    v0x, v0y, v0z = v0[:, 0].copy(), v0[:, 1].copy(), v0[:, 2].copy()
    e1x, e1y, e1z = e1[:, 0].copy(), e1[:, 1].copy(), e1[:, 2].copy()
    e2x, e2y, e2z = e2[:, 0].copy(), e2[:, 1].copy(), e2[:, 2].copy()

    bbox_size = float(np.linalg.norm(bmax.max(0) - bmin.min(0)))
    eps = eps_factor * bbox_size

    # Direction TO the source: -k_hat
    d = -np.asarray(k_hat, dtype=np.float64)
    d /= np.linalg.norm(d)

    V = np.zeros(n_tris, dtype=np.uint8)
    print(f"  Casting visibility rays for direction k_hat={k_hat}...")
    for i in range(n_tris):
        if i % 5000 == 0:
            print(f"    {i}/{n_tris}")
        # Origin slightly above the surface to avoid self-intersection
        origin = centroids[i] + eps * normals[i]
        # If front-facing AND no hit, V=1
        # Note: the (n . -k_hat)_+ gate is applied separately at render time;
        # V here is purely the geometric self-shadow factor.
        hit = ray_mesh_any_hit_bvh(
            float(origin[0]), float(origin[1]), float(origin[2]),
            float(d[0]), float(d[1]), float(d[2]),
            bvh, tri_indices,
            v0x, v0y, v0z, e1x, e1y, e1z, e2x, e2y, e2z,
            ignore_tri=int(i), t_min=0.0,
        )
        V[i] = 0 if hit else 1
    return V


def render_eta_paperB(vertices, normals, eta, eta_mean_area, out_path_base):
    """
    Single-column eta phantom figure for Paper B.
    Two views (front + side) at single-column width.
    """
    apply_monograph_style(mode="pdf")

    # In this view-matrix convention, the camera sits at the origin
    # looking in +fwd, so vertices visible to the camera have view-z
    # in the +fwd half-space. Body face is at -y. To see the face,
    # set fwd in -y direction: az=180, el=0. Side view: fwd in +x
    # (camera looks at body's left side): az=-90.
    V_front = _build_view_matrix(180.0, 5.0)
    V_side = _build_view_matrix(90.0, 5.0)

    # Higher pixel resolution for crisp PDF rendering of triangle edges.
    W_px, H_px = 560, 1080
    cmap_name = "viridis"
    print("  Rasterising eta panels...")
    img_front = render_zbuffer(vertices, eta, normals, W_px, H_px, V_front,
                               pad_factor=1.06, cmap_name=cmap_name)
    img_side = render_zbuffer(vertices, eta, normals, W_px, H_px, V_side,
                              pad_factor=1.06, cmap_name=cmap_name)

    # Phantom is roughly 2x taller than wide. With two panels side by side
    # at single-column width, an aspect close to 1 fits well without
    # leaving a large blank top strip.
    fig_w, fig_h = fig_size_ieee(columns=1, aspect=1.05)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    # Two image panels side by side, plus a slim colorbar on the right.
    left_pad = 0.005
    cbar_w = 0.028
    cbar_gap = 0.020
    right_pad = 0.085  # space for colorbar tick labels and label
    panels_w = 1.0 - left_pad - cbar_gap - cbar_w - right_pad
    pw = panels_w / 2

    # Vertical extent: leave room for the bottom annotation and (a)/(b).
    bottom = 0.075
    height = 0.91

    ax_a = fig.add_axes([left_pad, bottom, pw, height])
    ax_a.imshow(img_front, aspect="equal", interpolation="none")
    ax_a.axis("off")
    ax_a.text(0.5, -0.005, "(a)", transform=ax_a.transAxes,
              ha="center", va="top", fontsize=8)

    ax_b = fig.add_axes([left_pad + pw, bottom, pw, height])
    ax_b.imshow(img_side, aspect="equal", interpolation="none")
    ax_b.axis("off")
    ax_b.text(0.5, -0.005, "(b)", transform=ax_b.transAxes,
              ha="center", va="top", fontsize=8)

    # Colorbar: span most of the panel height for visual balance.
    cax = fig.add_axes([left_pad + 2 * pw + cbar_gap,
                        bottom + 0.10, cbar_w, height - 0.20])
    sm = ScalarMappable(cmap=plt.colormaps[cmap_name], norm=Normalize(0, 1))
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_ticks([0.0, 0.25, 0.5, 0.75, 1.0])
    cb.ax.tick_params(labelsize=7, length=2.5, width=0.5)
    cb.outline.set_linewidth(0.5)
    # Dimensionless quantity: render unit slot as (\,\,) per house style.
    cb.set_label(r"$\eta\,(\,\,)$", fontsize=9, rotation=90, labelpad=3)

    # Annotate area-weighted mean (passed in). Dimensionless tag.
    fig.text(0.5, 0.013,
             rf"area-weighted mean $\bar{{\eta}} = {eta_mean_area:.3f}\,(\,\,)$",
             ha="center", va="bottom", fontsize=8)

    pdf_path = out_path_base.with_suffix(".pdf")
    png_path = out_path_base.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"  Wrote: {pdf_path} and .png")


def render_sab_pair_paperA(
    vertices, normals, sab_convex, sab_visible, sab_max,
    out_path_base
):
    """
    Two-panel S_ab figure for Paper A:
      (a) S_ab with V=1 (convex limit prediction)
      (b) S_ab with V(r,k_hat) (real Thelonious)
    Two-column wide.
    """
    apply_monograph_style(mode="pdf")

    # k_hat = (0, 1, 0): wave from -y, lighting up the front of the body.
    # In this view-matrix convention fwd is the look direction with the
    # camera at the origin, so the visible half is the +fwd half. Body
    # face is at -y, so to see the face fwd should have a -y component.
    # az=210 gives fwd = (sin(30)*cos(el), -cos(30)*cos(el), -sin(el))
    # ~= (0.5, -0.86, -0.09), a 3/4 view where the camera sees the lit
    # front plus the body's right-side shadow.
    azimuth, elevation = 210.0, 5.0
    V = _build_view_matrix(azimuth, elevation)
    # Higher pixel resolution for crisp PDF rendering of triangle edges.
    W_px, H_px = 560, 1080

    print("  Rasterising S_ab panels...")
    # Sab values range over [0, T_0*S_inc] = [0, 0.536]. Use a perceptually
    # uniform, colour-blind-safe colormap (viridis): zero maps to deep
    # purple (clearly distinguishable from the white page background) and
    # the upper end is bright yellow.
    sab_a_norm = np.clip(sab_convex / sab_max, 0, 1)
    sab_b_norm = np.clip(sab_visible / sab_max, 0, 1)
    cmap = "viridis"
    img_a = render_zbuffer(vertices, sab_a_norm, normals, W_px, H_px, V,
                           pad_factor=1.02, cmap_name=cmap)
    img_b = render_zbuffer(vertices, sab_b_norm, normals, W_px, H_px, V,
                           pad_factor=1.02, cmap_name=cmap)

    # Trim the white margins that the rasteriser leaves around the body
    # silhouette (rasteriser fills with white; find non-white extent).
    def _trim_white(img, margin_px=4):
        m = np.any(img < 0.999, axis=2)
        if not m.any():
            return img
        ys = np.where(m.any(axis=1))[0]
        xs = np.where(m.any(axis=0))[0]
        y0 = max(0, ys.min() - margin_px)
        y1 = min(img.shape[0], ys.max() + 1 + margin_px)
        x0 = max(0, xs.min() - margin_px)
        x1 = min(img.shape[1], xs.max() + 1 + margin_px)
        return img[y0:y1, x0:x1]

    img_a = _trim_white(img_a)
    img_b = _trim_white(img_b)

    # Phantom is tall and narrow. Pick a tight aspect so the body fills
    # the panel width without leaving a large empty strip.
    fig_w, fig_h = fig_size_ieee(columns=2, aspect=0.40)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    # Layout: (a), (b), then colorbar. Save room on the far right for the
    # colorbar tick labels and label so nothing gets clipped.
    left_pad = 0.005
    cbar_w = 0.014
    cbar_gap = 0.012
    right_pad = 0.072
    panels_w = 1.0 - left_pad - cbar_gap - cbar_w - right_pad
    pw = panels_w / 2

    # Font sizes matched to body text (10 pt) modulo the standard scaling
    # for ticks/labels at this figure size.
    label_fs = 9
    tick_fs = 8
    panel_fs = 9

    bottom = 0.02
    height = 0.96

    ax_a = fig.add_axes([left_pad, bottom, pw, height])
    ax_a.imshow(img_a, aspect="equal", interpolation="none")
    ax_a.axis("off")
    # Minimal subpanel label; main caption carries the explanation.
    ax_a.text(0.02, 0.985, "(a)", transform=ax_a.transAxes,
              ha="left", va="top", fontsize=panel_fs)

    ax_b = fig.add_axes([left_pad + pw, bottom, pw, height])
    ax_b.imshow(img_b, aspect="equal", interpolation="none")
    ax_b.axis("off")
    ax_b.text(0.02, 0.985, "(b)", transform=ax_b.transAxes,
              ha="left", va="top", fontsize=panel_fs)

    # Single arrow annotating the most visually obvious self-shadow patch
    # in panel (b): the underside of the chin/jaw on the lit side. This
    # is the only label that lands clearly on a dark patch in the rendered
    # 3/4 view. Other self-shadowed regions (inner wrists, medial thighs)
    # are described in the caption but are too small to label without
    # adding visual clutter.
    ax_b.annotate(
        "self-shadowed",
        xy=(0.62, 0.86),
        xytext=(0.78, 0.94),
        xycoords="axes fraction", textcoords="axes fraction",
        ha="left", va="center", fontsize=tick_fs,
        arrowprops=dict(arrowstyle="-", color="black", lw=0.5,
                        shrinkA=0, shrinkB=2),
    )

    # Shared colorbar (immediately right of panel b)
    cax = fig.add_axes([left_pad + 2 * pw + cbar_gap, 0.10, cbar_w, 0.80])
    sm = ScalarMappable(cmap=plt.colormaps[cmap], norm=Normalize(0, sab_max))
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax)
    cb.outline.set_linewidth(0.6)
    cb.ax.tick_params(labelsize=tick_fs, width=0.6)
    cb.set_label(r"$\mathrm{APD}\;(\mathrm{W}\,\mathrm{m}^{-2})$",
                 fontsize=label_fs, labelpad=3)

    pdf_path = out_path_base.with_suffix(".pdf")
    png_path = out_path_base.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"  Wrote: {pdf_path} and .png")


def main():
    print(f"Loading mesh: {STL}")
    vertices, normals, centroids = load_stl_binary(STL)
    n_tris = vertices.shape[0]
    print(f"  {n_tris:,} triangles")

    # Compute triangle areas for area-weighted statistics.
    edge1 = vertices[:, 1] - vertices[:, 0]
    edge2 = vertices[:, 2] - vertices[:, 0]
    tri_areas = 0.5 * np.linalg.norm(np.cross(edge1, edge2), axis=1)
    A_total = float(tri_areas.sum())
    print(f"  total surface area: {A_total:.4f} m^2")

    # === Figure 1: eta phantom for Paper B ===
    eta_npz = CACHE_DIR / "eta_thelonious.npz"
    n_samples = 128
    if eta_npz.exists():
        print(f"Loading cached eta: {eta_npz}")
        d = np.load(eta_npz)
        eta = d["eta"]
        cached_ns = int(d["n_samples"][0]) if "n_samples" in d.files else 0
        if eta.shape[0] != n_tris or cached_ns < n_samples:
            print("  Cache mismatch or undersampled, recomputing...")
            eta = compute_eta(centroids, normals, vertices, n_samples=n_samples)
            np.savez(eta_npz, eta=eta, n_samples=np.array([n_samples]))
    else:
        print(f"Computing eta(r) with {n_samples} samples ...")
        eta = compute_eta(centroids, normals, vertices, n_samples=n_samples)
        np.savez(eta_npz, eta=eta, n_samples=np.array([n_samples]))

    eta_mean_area = float(np.sum(tri_areas * eta) / A_total)
    print(f"  area-weighted mean eta = {eta_mean_area:.4f}")
    print(f"  unweighted mean eta = {float(np.mean(eta)):.4f}")

    render_eta_paperB(
        vertices, normals, eta, eta_mean_area,
        out_path_base=FIGURE_DIR / "eta_phantom_paperB",
    )

    # === Figure 2: S_ab pair for Paper A ===
    # Parameters: skin at 28 GHz, S_inc = 1 W/m^2, frontal illumination
    # k_hat = (0, +1, 0): wave traveling in +y direction (Thelonious has
    # face at -y, so this lights up the body's front). Source at -y.
    k_hat = np.array([0.0, 1.0, 0.0])
    T_0 = 0.536  # skin at 28 GHz
    S_inc = 1.0

    # Cosine factor mu = n . (-k_hat)
    mu = normals @ (-k_hat)
    cos_pos = np.maximum(mu, 0.0)

    sab_max = S_inc * T_0  # full-scale colorbar

    # Panel (a): convex limit V=1
    sab_convex = S_inc * T_0 * cos_pos

    # Panel (b): V(r, k_hat) computed by ray casting
    V_npz = CACHE_DIR / f"V_thelonious_kx{int(k_hat[0])}_ky{int(k_hat[1])}_kz{int(k_hat[2])}.npz"
    if V_npz.exists():
        print(f"Loading cached visibility: {V_npz}")
        V = np.load(V_npz)["V"]
    else:
        print(f"Computing V(r, k_hat) for k_hat={k_hat}")
        V = compute_visibility(centroids, normals, vertices, k_hat)
        np.savez(V_npz, V=V)
    sab_visible = S_inc * T_0 * cos_pos * V.astype(np.float64)

    print(f"  panel (a) integrated power: {(sab_convex * 0.0001).sum():.3e} (rough)")
    print(f"  panel (b) integrated power: {(sab_visible * 0.0001).sum():.3e} (rough)")
    print(f"  fraction shadowed (front-facing only): "
          f"{1 - (sab_visible.sum() / max(sab_convex.sum(), 1e-30)):.3f}")

    render_sab_pair_paperA(
        vertices, normals, sab_convex, sab_visible, sab_max,
        out_path_base=FIGURE_DIR / "sab_phantom_pair",
    )

    # === Single-panel renderings for LaTeX subfigure layout ===
    # Rendered with the jet colormap and a common image width across
    # all three views so the subfigures appear at consistent scale.
    print("Rendering single-panel phantom figures...")
    panels = [
        dict(scalar=sab_visible, vmax=sab_max,
             cbar_label=r"$\mathrm{APD}$ [W/m$^{2}$]",
             view_az=210.0, view_el=5.0,
             out_path=FIGURE_DIR / "sab_phantom_visible.pdf"),
        dict(scalar=eta, vmax=1.0,
             cbar_label=r"$\eta$",
             view_az=180.0, view_el=5.0,
             out_path=FIGURE_DIR / "eta_phantom_front.pdf"),
        dict(scalar=eta, vmax=1.0,
             cbar_label=r"$\eta$",
             view_az=90.0, view_el=5.0,
             out_path=FIGURE_DIR / "eta_phantom_side.pdf"),
    ]
    _render_panels_aligned(vertices, normals, panels, cmap_name="jet")

    print("Done.")


def _render_panels_aligned(vertices, normals, panels, *, cmap_name):
    """Render multiple phantom panels with a shared image width.

    Each panel is rasterised, white-trimmed, then padded to the maximum
    trimmed width across panels so the resulting per-panel PDFs land
    in LaTeX subfigures at a consistent visual scale. Output figures
    are sized to match a typical 0.32*\\textwidth subfigure box at IEEE
    two-column 10pt so the colorbar fonts render at ~10pt.
    """
    apply_monograph_style(mode="pdf")
    W_px, H_px = 560, 1080
    images = []
    for p in panels:
        V = _build_view_matrix(p["view_az"], p["view_el"])
        norm = np.clip(p["scalar"] / p["vmax"], 0, 1) if p["vmax"] > 0 else p["scalar"]
        img = render_zbuffer(vertices, norm, normals, W_px, H_px, V,
                             pad_factor=1.04, cmap_name=cmap_name)
        m = np.any(img < 0.999, axis=2)
        if m.any():
            ys = np.where(m.any(axis=1))[0]
            xs = np.where(m.any(axis=0))[0]
            img = img[max(0, ys.min() - 4):ys.max() + 5,
                      max(0, xs.min() - 4):xs.max() + 5]
        images.append(img)

    # Pad every trimmed image to the same dimensions so each subfigure
    # PDF has the same physical aspect ratio and content scale.
    # content_scale < 1 shrinks the body by padding the canvas
    # horizontally only, so the body occupies content_scale of the width
    # and still fills the height (no white bands above or below). The
    # figure height follows the wider aspect and stays tight to the body,
    # so the body and colorbar shrink together at print size while the
    # label/tick fonts keep their absolute point size.
    content_scale = 0.70
    max_w = max(im.shape[1] for im in images)
    max_h = max(im.shape[0] for im in images)
    new_w = int(round(max_w / content_scale))
    new_h = max_h
    aligned = []
    for im in images:
        h, w = im.shape[:2]
        canvas = np.ones((new_h, new_w, 3), dtype=im.dtype)
        x0 = (new_w - w) // 2
        y0 = (new_h - h) // 2
        canvas[y0:y0 + h, x0:x0 + w] = im
        aligned.append(canvas)
    max_w, max_h = new_w, new_h

    # Match the source-PDF width to the actual displayed subfigure
    # width (~0.32 of IEEE two-column textwidth) so a 10pt source font
    # remains 10pt at print size.
    fig_w_in = 0.32 * 7.16  # ~2.29 in
    panel_aspect = max_h / max_w  # height / width of the image content

    for img, p in zip(aligned, panels):
        # Allocate width: left pad + panel + cbar gap + cbar + tick area
        panel_frac = 0.78
        cbar_gap = 0.02
        cbar_frac = 0.045
        right_pad = 0.155
        # Figure height matches panel content aspect plus slim bottom pad.
        fig_h_in = fig_w_in * panel_frac * panel_aspect + 0.08
        fig = plt.figure(figsize=(fig_w_in, fig_h_in), facecolor="white")
        ax = fig.add_axes([0.01, 0.02, panel_frac, 0.96])
        ax.imshow(img, aspect="equal", interpolation="none")
        ax.axis("off")
        cax_left = 0.01 + panel_frac + cbar_gap
        cax = fig.add_axes([cax_left, 0.10, cbar_frac, 0.80])
        sm = ScalarMappable(cmap=plt.colormaps[cmap_name],
                            norm=Normalize(0, p["vmax"] if p["vmax"] > 0 else 1))
        sm.set_array([])
        cb = fig.colorbar(sm, cax=cax)
        cb.outline.set_linewidth(0.6)
        cb.ax.tick_params(labelsize=10, width=0.6, length=3.0)
        cb.set_label(p["cbar_label"], fontsize=10, labelpad=4)
        # Avoid the right-pad area being clipped by tight bbox.
        del right_pad
        fig.savefig(p["out_path"], bbox_inches="tight", pad_inches=0.02)
        fig.savefig(p["out_path"].with_suffix(".png"), dpi=300,
                    bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        print(f"  Wrote: {p['out_path']}")


if __name__ == "__main__":
    main()
