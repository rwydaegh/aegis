"""
Visualize exposure fraction eta outputs produced by compute_exposure_fraction_eta.py.

This script intentionally avoids heavy plotting dependencies (matplotlib can be
fragile in some environments). It renders PNGs using Pillow.

Outputs (default):
- figures/eta_hist_zoom_<phantom>.png : histogram zoomed to show structure below eta=1
- figures/eta_cdf_<phantom>.png       : empirical CDF
- figures/eta_normal_latlon_<phantom>.png : equirectangular map of mean eta binned by normal direction
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import numpy as np


def infer_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    root = infer_repo_root()
    p = argparse.ArgumentParser(description="Visualize eta.npz outputs.")
    p.add_argument(
        "--eta_npz",
        type=str,
        default=str(root / "artifacts" / "eta" / "thelonious" / "eta.npz"),
        help="Path to eta.npz (contains eta, centroids, normals).",
    )
    p.add_argument("--phantom", type=str, default=None, help="Override phantom name used in figure filenames.")
    p.add_argument("--bins", type=int, default=60, help="Histogram bins.")
    p.add_argument("--zoom_max", type=float, default=0.98, help="Max eta shown in zoomed histogram (values above go to overflow bin).")
    p.add_argument("--nlon", type=int, default=360, help="Longitude bins for normal map.")
    p.add_argument("--nlat", type=int, default=180, help="Latitude bins for normal map.")
    return p.parse_args()


def _safe_import_pil():
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Pillow is required for visualize_eta.py (pip install Pillow).") from e
    return Image, ImageDraw, ImageFont


def _draw_axes(draw, x0: int, y0: int, x1: int, y1: int) -> None:
    draw.rectangle([x0, y0, x1, y1], outline=(0, 0, 0), width=2)


def save_hist_zoom_png(eta: np.ndarray, out_path: Path, phantom: str, bins: int, zoom_max: float) -> None:
    Image, ImageDraw, ImageFont = _safe_import_pil()
    font = ImageFont.load_default()

    eta = np.asarray(eta, dtype=np.float64)
    eta = np.clip(eta, 0.0, 1.0)

    # Bin [0, zoom_max] with last bin reserved for overflow (zoom_max..1]
    zoom_max = float(zoom_max)
    zoom_max = min(max(zoom_max, 0.01), 0.999999)
    edges = np.linspace(0.0, zoom_max, bins + 1)
    counts, _ = np.histogram(np.minimum(eta, zoom_max), bins=edges)
    overflow = int((eta > zoom_max).sum())
    counts[-1] += overflow

    W, H = 980, 520
    pad_l, pad_r, pad_t, pad_b = 85, 20, 60, 75
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    x0, y0 = pad_l, pad_t
    x1, y1 = pad_l + plot_w, pad_t + plot_h

    im = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(im)

    title = f"eta histogram (zoom <= {zoom_max:.2f}, overflow folded into last bin): {phantom}"
    dr.text((pad_l, 20), title, fill=(0, 0, 0), font=font)

    _draw_axes(dr, x0, y0, x1, y1)

    maxc = float(np.max(counts)) if counts.size else 1.0
    maxc = max(maxc, 1.0)
    bar_w = plot_w / bins
    for i, c in enumerate(counts):
        h = (float(c) / maxc) * plot_h
        bx0 = x0 + i * bar_w
        bx1 = x0 + (i + 1) * bar_w
        by0 = y1 - h
        dr.rectangle([bx0, by0, bx1, y1], fill=(76, 114, 176), outline=None)

    dr.text((pad_l, H - 42), "eta (zoomed)", fill=(0, 0, 0), font=font)
    dr.text((pad_l, H - 22), f"note: last bin includes {overflow} samples with eta>{zoom_max:.2f}", fill=(0, 0, 0), font=font)
    dr.text((15, pad_t + plot_h / 2), "triangle count", fill=(0, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="PNG")


def save_cdf_png(eta: np.ndarray, out_path: Path, phantom: str) -> None:
    Image, ImageDraw, ImageFont = _safe_import_pil()
    font = ImageFont.load_default()

    eta = np.asarray(eta, dtype=np.float64)
    eta = np.clip(eta, 0.0, 1.0)
    xs = np.sort(eta)
    n = xs.size
    ys = (np.arange(n, dtype=np.float64) + 1.0) / float(n)

    W, H = 980, 520
    pad_l, pad_r, pad_t, pad_b = 85, 20, 60, 75
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    x0, y0 = pad_l, pad_t
    x1, y1 = pad_l + plot_w, pad_t + plot_h

    im = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    dr.text((pad_l, 20), f"eta empirical CDF: {phantom}", fill=(0, 0, 0), font=font)
    _draw_axes(dr, x0, y0, x1, y1)

    # Downsample for drawing (avoid huge polyline)
    step = max(1, n // 3000)
    xs_d = xs[::step]
    ys_d = ys[::step]

    pts = []
    for xv, yv in zip(xs_d, ys_d):
        px = x0 + float(xv) * plot_w
        py = y1 - float(yv) * plot_h
        pts.append((px, py))
    if len(pts) >= 2:
        dr.line(pts, fill=(220, 50, 32), width=2)

    dr.text((pad_l, H - 42), "eta", fill=(0, 0, 0), font=font)
    dr.text((pad_l, H - 22), "CDF", fill=(0, 0, 0), font=font)
    dr.text((15, pad_t + plot_h / 2), "probability", fill=(0, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="PNG")


def save_normal_latlon_png(normals: np.ndarray, eta: np.ndarray, out_path: Path, phantom: str, nlon: int, nlat: int) -> None:
    """
    Equirectangular map of mean eta binned by normal direction.
    lon in [-pi, pi], lat in [-pi/2, pi/2].
    """
    Image, ImageDraw, ImageFont = _safe_import_pil()
    font = ImageFont.load_default()

    normals = np.asarray(normals, dtype=np.float64)
    eta = np.asarray(eta, dtype=np.float64)
    eta = np.clip(eta, 0.0, 1.0)

    n = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(n > 0, n, 1.0)
    nx, ny, nz = normals[:, 0], normals[:, 1], normals[:, 2]

    lon = np.arctan2(ny, nx)  # [-pi, pi]
    lat = np.arcsin(np.clip(nz, -1.0, 1.0))  # [-pi/2, pi/2]

    # bins
    lon_u = (lon + np.pi) / (2 * np.pi)  # [0,1]
    lat_u = (lat + np.pi / 2) / np.pi   # [0,1]
    ix = np.clip((lon_u * nlon).astype(np.int32), 0, nlon - 1)
    iy = np.clip(((1.0 - lat_u) * nlat).astype(np.int32), 0, nlat - 1)  # image y down

    acc = np.zeros((nlat, nlon), dtype=np.float64)
    cnt = np.zeros((nlat, nlon), dtype=np.int32)
    np.add.at(acc, (iy, ix), eta)
    np.add.at(cnt, (iy, ix), 1)
    mean = acc / np.where(cnt > 0, cnt, 1)

    # Simple colormap: blue(low) -> yellow(high)
    def cmap(v: float) -> Tuple[int, int, int]:
        v = float(np.clip(v, 0.0, 1.0))
        # piecewise: blue->cyan->green->yellow
        if v < 0.33:
            t = v / 0.33
            r, g, b = 0.0, t, 1.0
        elif v < 0.66:
            t = (v - 0.33) / 0.33
            r, g, b = 0.0, 1.0, 1.0 - t
        else:
            t = (v - 0.66) / 0.34
            r, g, b = t, 1.0, 0.0
        return int(255 * r), int(255 * g), int(255 * b)

    W = max(960, nlon)
    H = max(520, nlat + 90)
    pad_t = 60
    im = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    dr.text((20, 20), f"mean eta binned by normal direction (lon-lat map): {phantom}", fill=(0, 0, 0), font=font)

    # render map
    for y in range(nlat):
        for x in range(nlon):
            if cnt[y, x] == 0:
                color = (240, 240, 240)
            else:
                color = cmap(mean[y, x])
            im.putpixel((x, y + pad_t), color)

    # outline box
    dr.rectangle([0, pad_t, nlon - 1, pad_t + nlat - 1], outline=(0, 0, 0), width=2)
    dr.text((20, pad_t + nlat + 15), "lon: -π..π (x),  lat: +π/2..-π/2 (y)", fill=(0, 0, 0), font=font)
    dr.text((20, pad_t + nlat + 35), "gray = no samples in bin", fill=(0, 0, 0), font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="PNG")


def main() -> None:
    args = parse_args()
    eta_npz = Path(args.eta_npz)
    phantom = args.phantom or eta_npz.parent.name

    root = infer_repo_root()
    figures_dir = root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    d = np.load(eta_npz)
    eta = d["eta"]
    normals = d["normals"]

    save_hist_zoom_png(
        eta,
        figures_dir / f"eta_hist_zoom_{phantom}.png",
        phantom=phantom,
        bins=int(args.bins),
        zoom_max=float(args.zoom_max),
    )
    save_cdf_png(eta, figures_dir / f"eta_cdf_{phantom}.png", phantom=phantom)
    save_normal_latlon_png(
        normals,
        eta,
        figures_dir / f"eta_normal_latlon_{phantom}.png",
        phantom=phantom,
        nlon=int(args.nlon),
        nlat=int(args.nlat),
    )

    print("Wrote:")
    print(f"  {figures_dir / f'eta_hist_zoom_{phantom}.png'}")
    print(f"  {figures_dir / f'eta_cdf_{phantom}.png'}")
    print(f"  {figures_dir / f'eta_normal_latlon_{phantom}.png'}")


if __name__ == "__main__":
    main()

