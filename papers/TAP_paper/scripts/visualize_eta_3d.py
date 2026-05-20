"""
3D visualization of exposure fraction η mapped onto the Thelonious phantom mesh.

Outputs
-------
- figures/eta_3d_thelonious.png         : clean 3/4-view render (default)
- figures/eta_3d_<phantom>.html         : interactive Plotly HTML (optional)

Usage
-----
    python scripts/visualize_eta_3d.py                     # default PNG
    python scripts/visualize_eta_3d.py --html              # also generate HTML
    python scripts/visualize_eta_3d.py --dpi 300           # higher resolution

Requires: numpy, matplotlib.  Plotly only needed for --html.
"""

from __future__ import annotations

import argparse
import struct
import time
from pathlib import Path
from typing import Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def infer_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_stl_binary(filepath: str | Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load binary STL → vertices (N,3,3), normals (N,3), centroids (N,3)."""
    with open(str(filepath), "rb") as f:
        f.read(80)  # header
        n = struct.unpack("<I", f.read(4))[0]
        vertices = np.zeros((n, 3, 3), dtype=np.float64)
        normals = np.zeros((n, 3), dtype=np.float64)
        for i in range(n):
            normals[i] = struct.unpack("<3f", f.read(12))
            for j in range(3):
                vertices[i, j] = struct.unpack("<3f", f.read(12))
            f.read(2)
    centroids = np.mean(vertices, axis=1)
    nrm = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(nrm > 0, nrm, 1.0)
    return vertices, normals, centroids


# ---------------------------------------------------------------------------
# Software Z-buffer rasteriser (orthographic, painter + per-pixel depth)
# ---------------------------------------------------------------------------

def _build_view_matrix(azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    """
    Orthographic camera view matrix for a given azimuth and elevation.

    Returns a 3×3 matrix whose rows are (right, up, forward) in world coords.
    Screen X = right, screen Y = up, depth = forward.
    """
    az = np.radians(azimuth_deg)
    el = np.radians(elevation_deg)
    fwd = np.array([
        -np.sin(az) * np.cos(el),
         np.cos(az) * np.cos(el),
        -np.sin(el),
    ])
    fwd /= np.linalg.norm(fwd)
    world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(fwd, world_up)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    up /= np.linalg.norm(up)
    return np.array([right, up, fwd])


def render_zbuffer(
    vertices: np.ndarray,
    eta: np.ndarray,
    normals: np.ndarray,
    W: int,
    H: int,
    view_matrix: np.ndarray,
    pad_factor: float = 1.08,
    cmap_name: str = "RdYlBu_r",
) -> np.ndarray:
    """
    Rasterise the triangle mesh into a (H, W, 3) float64 RGB image using a
    painter's-algorithm Z-buffer with per-pixel depth test.
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    # Transform to view space
    flat_v = vertices.reshape(-1, 3) @ view_matrix.T
    rot_v = flat_v.reshape(-1, 3, 3)
    rot_n = normals @ view_matrix.T

    # Fit to image frame
    all_xy = flat_v[:, :2]
    bmin_xy, bmax_xy = all_xy.min(0), all_xy.max(0)
    range_xy = bmax_xy - bmin_xy
    scale = min(W / (range_xy[0] * pad_factor), H / (range_xy[1] * pad_factor))
    center = (bmin_xy + bmax_xy) / 2
    offset = np.array([W / 2, H / 2]) - center * scale

    # Colour + shading
    cmap_obj = plt.colormaps[cmap_name]
    colors = cmap_obj(Normalize(0, 1)(eta))[:, :3]

    light = np.array([0.3, 0.35, 1.0])
    light /= np.linalg.norm(light)
    shade = np.clip(0.38 + 0.62 * np.abs(rot_n @ light), 0.28, 1.0)
    shaded = colors * shade[:, None]

    # Painter sort
    order = np.argsort(rot_v.mean(axis=1)[:, 2])

    img = np.ones((H, W, 3), dtype=np.float64)
    zbuf = np.full((H, W), -np.inf, dtype=np.float64)

    for idx in order:
        tri_xy = rot_v[idx, :, :2] * scale + offset
        tri_z = rot_v[idx, :, 2].mean()
        c = shaded[idx]

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
        img[ymin + ys, xmin + xs] = c
        zbuf[ymin + ys, xmin + xs] = tri_z

    return img[::-1]  # flip Y so Z points up


# ---------------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------------

def create_eta_phantom_png(
    vertices: np.ndarray,
    eta: np.ndarray,
    normals: np.ndarray,
    out_path: Path,
    dpi: int = 200,
    azimuth: float = -30.0,
    elevation: float = 10.0,
) -> None:
    """Render a clean single-view PNG with colorbar."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    V = _build_view_matrix(azimuth, elevation)

    W_px, H_px = 480, 780
    print("  Rasterising...", end=" ", flush=True)
    t0 = time.time()
    img = render_zbuffer(vertices, eta, normals, W_px, H_px, V, pad_factor=1.08)
    print(f"{time.time() - t0:.1f} s", flush=True)

    fig = plt.figure(figsize=(5.8, 9.2), facecolor="white")

    # Image panel
    ax_img = fig.add_axes([0.0, 0.0, 0.80, 1.0])
    ax_img.imshow(img, aspect="equal")
    ax_img.axis("off")

    # Colorbar
    ax_cb = fig.add_axes([0.835, 0.20, 0.038, 0.45])
    sm = ScalarMappable(cmap=plt.colormaps["RdYlBu_r"], norm=Normalize(0, 1))
    sm.set_array([])
    cb = fig.colorbar(sm, cax=ax_cb)
    cb.set_ticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    cb.ax.tick_params(labelsize=11)

    # η label above colorbar
    fig.text(0.854, 0.67, r"$\eta$", fontsize=18, ha="center", va="bottom",
             math_fontfamily="dejavuserif")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out_path), dpi=dpi, bbox_inches="tight",
                facecolor="white", pad_inches=0.1)
    plt.close(fig)
    print(f"  Wrote: {out_path}")


def create_plotly_html(
    vertices: np.ndarray,
    eta: np.ndarray,
    out_path: Path,
    title: str,
) -> None:
    """Interactive Plotly Mesh3d HTML with per-face η colours and colorbar."""
    import plotly.graph_objects as go

    n_tri = vertices.shape[0]
    all_v = vertices.reshape(-1, 3)

    colorscale = [
        [0.0,  "rgb(15,0,80)"],
        [0.2,  "rgb(30,60,180)"],
        [0.4,  "rgb(0,160,180)"],
        [0.6,  "rgb(50,200,80)"],
        [0.8,  "rgb(240,200,0)"],
        [0.95, "rgb(255,120,0)"],
        [1.0,  "rgb(200,0,0)"],
    ]
    bp = [(0.0,(15,0,80)),(0.2,(30,60,180)),(0.4,(0,160,180)),
          (0.6,(50,200,80)),(0.8,(240,200,0)),(0.95,(255,120,0)),(1.0,(200,0,0))]

    def _rgb(val: float) -> str:
        val = float(np.clip(val, 0, 1))
        for k in range(len(bp) - 1):
            v0, c0 = bp[k]; v1, c1 = bp[k + 1]
            if val <= v1:
                t = (val - v0) / (v1 - v0) if v1 > v0 else 0.0
                return "rgb({},{},{})".format(
                    int(c0[0] + t * (c1[0] - c0[0])),
                    int(c0[1] + t * (c1[1] - c0[1])),
                    int(c0[2] + t * (c1[2] - c0[2])))
        return f"rgb({bp[-1][1][0]},{bp[-1][1][1]},{bp[-1][1][2]})"

    mesh = go.Mesh3d(
        x=all_v[:, 0], y=all_v[:, 1], z=all_v[:, 2],
        i=np.arange(0, 3 * n_tri, 3),
        j=np.arange(1, 3 * n_tri, 3),
        k=np.arange(2, 3 * n_tri, 3),
        facecolor=[_rgb(e) for e in eta],
        flatshading=True,
        hovertext=[f"\u03b7 = {e:.3f}" for e in eta],
        hoverinfo="text",
        lighting=dict(ambient=0.5, diffuse=0.6, specular=0.2, roughness=0.5),
        lightposition=dict(x=1000, y=1000, z=2000),
    )
    cbar_trace = go.Scatter3d(
        x=[None], y=[None], z=[None], mode="markers",
        marker=dict(size=0.001, color=[0, 1], colorscale=colorscale,
                    cmin=0, cmax=1,
                    colorbar=dict(title="\u03b7", thickness=25, len=0.7,
                                  tickvals=[0, 0.2, 0.4, 0.6, 0.8, 1.0]),
                    showscale=True),
        hoverinfo="skip", showlegend=False,
    )

    mean_eta = float(np.mean(eta))
    median_eta = float(np.median(eta))
    frac_1 = float(np.mean(eta == 1.0)) * 100

    fig = go.Figure(data=[mesh, cbar_trace])
    fig.update_layout(
        title=dict(
            text=(f"{title}<br><span style='font-size:13px;color:#555'>"
                  f"mean \u03b7={mean_eta:.3f} | median={median_eta:.3f} | "
                  f"\u03b7=1: {frac_1:.1f}% | {n_tri:,} tri</span>"),
            x=0.5, font=dict(size=18)),
        scene=dict(
            xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
            aspectmode="data",
            camera=dict(eye=dict(x=1.5, y=0.5, z=0.5),
                        up=dict(x=0, y=0, z=1)),
            bgcolor="rgb(240,240,245)"),
        margin=dict(l=0, r=0, t=80, b=0), width=1100, height=800,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path), include_plotlyjs=True)
    print(f"  Wrote: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    root = infer_repo_root()
    p = argparse.ArgumentParser(
        description="Render exposure-fraction η on a phantom mesh.")
    p.add_argument("--stl", type=str,
                   default=str(root / "data" / "thelonious.stl"))
    p.add_argument("--eta_npz", type=str,
                   default=str(root / "data" / "eta_thelonious.npz"))
    p.add_argument("--out_png", type=str, default=None,
                   help="PNG path (default: figures/eta_3d_<phantom>.png)")
    p.add_argument("--out_html", type=str, default=None,
                   help="HTML path (default: figures/eta_3d_<phantom>.html)")
    p.add_argument("--html", action="store_true",
                   help="Also generate interactive HTML.")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--azimuth", type=float, default=-30.0,
                   help="Camera azimuth in degrees (0 = front).")
    p.add_argument("--elevation", type=float, default=10.0,
                   help="Camera elevation in degrees.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = infer_repo_root()

    stl_path = Path(args.stl)
    phantom = stl_path.stem

    print(f"Loading mesh: {stl_path}")
    vertices, normals, centroids = load_stl_binary(stl_path)
    n_tri = vertices.shape[0]
    print(f"  {n_tri:,} triangles")

    print(f"Loading eta: {args.eta_npz}")
    d = np.load(args.eta_npz)
    eta = d["eta"]
    print(f"  mean eta = {eta.mean():.4f},  eta=1: {(eta == 1.0).mean() * 100:.1f}%")
    assert eta.shape[0] == n_tri

    # --- PNG (always) ---
    png_path = (Path(args.out_png) if args.out_png
                else root / "figures" / f"eta_3d_{phantom}.png")
    print(f"Creating PNG: {png_path}")
    create_eta_phantom_png(vertices, eta, normals, png_path,
                           dpi=args.dpi,
                           azimuth=args.azimuth,
                           elevation=args.elevation)

    # --- HTML (optional) ---
    if args.html:
        html_path = (Path(args.out_html) if args.out_html
                     else root / "figures" / f"eta_3d_{phantom}.html")
        print(f"Creating HTML: {html_path}")
        create_plotly_html(vertices, eta, html_path,
                           title=f"Exposure fraction η — {phantom} phantom")


if __name__ == "__main__":
    main()
