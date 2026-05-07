"""
Render Thelonious as a flat-gray phantom with transparent background,
matching the camera angle of figure 4a (azimuth=210, elevation=5).
Output: thelonious_gray.png with alpha channel.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "theory" / "scripts"))

from compute_exposure_fraction_eta import load_stl_binary  # noqa: E402
from visualize_eta_3d import _build_view_matrix  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
STL = REPO_ROOT / "data" / "thelonious.stl"


def render_gray_alpha(vertices, normals, W, H, view_matrix, pad_factor=1.04,
                     base_gray=0.78):
    """Painter's-algorithm raster, single gray tone, with alpha channel.

    Returns (H, W, 4) RGBA float64 in [0, 1]. Pixels not covered by any
    triangle have alpha=0 (transparent). Covered pixels are shaded gray.
    """
    flat_v = vertices.reshape(-1, 3) @ view_matrix.T
    rot_v = flat_v.reshape(-1, 3, 3)
    rot_n = normals @ view_matrix.T

    all_xy = flat_v[:, :2]
    bmin_xy, bmax_xy = all_xy.min(0), all_xy.max(0)
    range_xy = bmax_xy - bmin_xy
    scale = min(W / (range_xy[0] * pad_factor), H / (range_xy[1] * pad_factor))
    center = (bmin_xy + bmax_xy) / 2
    offset = np.array([W / 2, H / 2]) - center * scale

    # Soft directional light, mostly from upper-left, identical to fig 4a feel
    light = np.array([0.3, 0.35, 1.0])
    light /= np.linalg.norm(light)
    shade = np.clip(0.55 + 0.45 * np.abs(rot_n @ light), 0.45, 1.0)

    # Painter's sort by mean z
    order = np.argsort(rot_v.mean(axis=1)[:, 2])

    img = np.zeros((H, W, 4), dtype=np.float64)  # transparent black
    zbuf = np.full((H, W), -np.inf, dtype=np.float64)

    for idx in order:
        tri_xy = rot_v[idx, :, :2] * scale + offset
        tri_z = rot_v[idx, :, 2].mean()
        g = base_gray * shade[idx]

        xmin = max(0, int(np.floor(tri_xy[:, 0].min())))
        xmax = min(W - 1, int(np.ceil(tri_xy[:, 0].max())))
        ymin = max(0, int(np.floor(tri_xy[:, 1].min())))
        ymax = min(H - 1, int(np.ceil(tri_xy[:, 1].max())))
        if xmin > xmax or ymin > ymax:
            continue

        PX, PY = np.meshgrid(
            np.arange(xmin, xmax + 1, dtype=np.float64),
            np.arange(ymin, ymax + 1, dtype=np.float64),
        )
        ax_, ay_ = tri_xy[0]
        bx_, by_ = tri_xy[1]
        cx_, cy_ = tri_xy[2]
        denom = (by_ - cy_) * (ax_ - cx_) + (cx_ - bx_) * (ay_ - cy_)
        if abs(denom) < 1e-10:
            continue
        w0 = ((by_ - cy_) * (PX - cx_) + (cx_ - bx_) * (PY - cy_)) / denom
        w1 = ((cy_ - ay_) * (PX - cx_) + (ax_ - cx_) * (PY - cy_)) / denom
        w2 = 1.0 - w0 - w1
        mask = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
        mask &= zbuf[ymin:ymax + 1, xmin:xmax + 1] < tri_z
        ys, xs = np.where(mask)
        img[ymin + ys, xmin + xs, 0] = g
        img[ymin + ys, xmin + xs, 1] = g
        img[ymin + ys, xmin + xs, 2] = g
        img[ymin + ys, xmin + xs, 3] = 1.0
        zbuf[ymin + ys, xmin + xs] = tri_z

    return img[::-1]


def main():
    print(f"Loading mesh: {STL}")
    vertices, normals, _ = load_stl_binary(STL)
    print(f"  {vertices.shape[0]:,} triangles")

    # Same camera as fig 4a (sab_phantom_visible.pdf)
    view = _build_view_matrix(210.0, 5.0)

    W_px, H_px = 800, 1600
    print("Rasterising gray phantom with alpha...")
    img = render_gray_alpha(vertices, normals, W_px, H_px, view, pad_factor=1.02)

    # Trim transparent margins
    alpha = img[..., 3]
    ys = np.where(alpha.any(axis=1))[0]
    xs = np.where(alpha.any(axis=0))[0]
    pad = 6
    y0 = max(0, ys.min() - pad)
    y1 = min(H_px, ys.max() + 1 + pad)
    x0 = max(0, xs.min() - pad)
    x1 = min(W_px, xs.max() + 1 + pad)
    img = img[y0:y1, x0:x1]
    print(f"Trimmed to {img.shape[1]} x {img.shape[0]}")

    out = OUT_DIR / "thelonious_gray.png"
    plt.imsave(out, img)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
