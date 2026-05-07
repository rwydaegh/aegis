"""
Plot posture sensitivity figure for the monograph.

Reads:  artifacts/postures/<model>/posture_summary.csv
Writes: monograph/figures/posture_sensitivity.png
        monograph/figures/posture_sensitivity.pdf

The default dataset is the "salto" demo (6 sampled animation frames).

This script is intentionally lightweight (numpy + matplotlib) and reuses the repo's
binary STL loader to optionally render simple silhouette thumbnails.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# Allow importing other scripts regardless of current working directory.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _plot_style as ps  # noqa: E402
import compute_projected_area_table as cap  # noqa: E402


@dataclass(frozen=True)
class PostureRow:
    pose_name: str
    frame: int
    stl_path: Path
    D_max: float
    D_min: float
    D_p50: float
    D_p95: float
    sh_rms_L6: float


def _parse_frame(pose_name: str) -> int:
    """
    Extract frame index from pose names like "frame_0020".
    Falls back to row order if parsing fails.
    """
    s = str(pose_name)
    if s.startswith("frame_"):
        tail = s.split("frame_", 1)[1]
        try:
            return int(tail)
        except ValueError:
            pass
    # Try to extract trailing integer
    digits = "".join([c for c in s if c.isdigit()])
    return int(digits) if digits else -1


def _read_summary_csv(path: Path) -> list[PostureRow]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[PostureRow] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        required = {"pose_name", "stl_path", "D_max", "D_min", "D_p50", "D_p95", "sh_rms_L6"}
        missing = required - set(r.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing columns: {sorted(missing)}")
        for row in r:
            pose_name = str(row["pose_name"])
            frame = _parse_frame(pose_name)
            stl_path = Path(str(row["stl_path"]))
            rows.append(
                PostureRow(
                    pose_name=pose_name,
                    frame=frame,
                    stl_path=stl_path,
                    D_max=float(row["D_max"]),
                    D_min=float(row["D_min"]),
                    D_p50=float(row["D_p50"]),
                    D_p95=float(row["D_p95"]),
                    sh_rms_L6=float(row["sh_rms_L6"]),
                )
            )
    # Sort by frame if available, else stable order.
    if all(r.frame >= 0 for r in rows):
        rows.sort(key=lambda x: x.frame)
    return rows


def _downsample_triangles(vertices: np.ndarray, *, target: int = 9000) -> np.ndarray:
    m = int(vertices.shape[0])
    if m <= target:
        return vertices
    step = max(1, m // target)
    return vertices[::step]


def _silhouette_line_segments(vertices: np.ndarray, *, view: str = "xz") -> np.ndarray:
    """
    Build (N, 2, 2) line segments for a simple mesh-outline thumbnail.
    """
    if view not in ("xz", "yz", "xy"):
        raise ValueError("view must be one of: 'xz', 'yz', 'xy'")
    # Center for stable thumbnails
    v = np.asarray(vertices, dtype=np.float64)
    v = v.reshape(-1, 3)
    v = v - np.mean(v, axis=0, keepdims=True)
    v = v.reshape(-1, 3, 3)

    if view == "xz":
        p = v[..., (0, 2)]
    elif view == "yz":
        p = v[..., (1, 2)]
    else:
        p = v[..., (0, 1)]

    # Edges per triangle: (0-1), (1-2), (2-0)
    e01 = np.stack([p[:, 0], p[:, 1]], axis=1)
    e12 = np.stack([p[:, 1], p[:, 2]], axis=1)
    e20 = np.stack([p[:, 2], p[:, 0]], axis=1)
    seg = np.concatenate([e01, e12, e20], axis=0)
    return seg


def _format_frame_label(frame: int) -> str:
    return f"Frame {frame:g}"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot posture sensitivity figure for the monograph.")
    p.add_argument(
        "--csv",
        type=Path,
        default=_repo_root() / "artifacts" / "postures" / "salto" / "posture_summary.csv",
        help="Input posture_summary.csv (default: artifacts/postures/salto/posture_summary.csv)",
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=_repo_root() / "monograph" / "figures",
        help="Output directory (default: monograph/figures)",
    )
    p.add_argument("--basename", type=str, default="posture_sensitivity", help="Output file base name")
    p.add_argument(
        "--thumbnails",
        action="store_true",
        help="Add a top strip of simple STL silhouettes (recommended).",
    )
    p.add_argument(
        "--thumbnail-view",
        choices=["xz", "yz", "xy"],
        default="xz",
        help="2D projection view for thumbnails (default: xz).",
    )
    p.add_argument(
        "--thumbnail-target-tris",
        type=int,
        default=9000,
        help="Downsample triangles per frame for thumbnails (default: 9000).",
    )
    p.add_argument("--dpi", type=int, default=300, help="PNG DPI (default: 300)")
    return p.parse_args()


def _plot_with_thumbnails(rows: list[PostureRow], *, out_png: Path, out_pdf: Path, dpi: int,
                          thumb_view: str, thumb_target_tris: int) -> None:
    ps.apply_monograph_style(mode="png", constrained_layout=False, extra_rc={"axes.grid": False})

    # Layout: 2 rows — top: 6 thumbnails, bottom: main plot spanning full width.
    n = len(rows)
    n_thumb = min(6, n)
    thumb_idx = (
        np.linspace(0, max(n - 1, 0), num=n_thumb, dtype=int).tolist()
        if n_thumb > 0
        else []
    )
    fig = plt.figure(figsize=ps.fig_size_textwidth(aspect=0.60, scale=1.0))
    gs = fig.add_gridspec(nrows=2, ncols=max(n_thumb, 1), height_ratios=[1.0, 2.2], hspace=0.22, wspace=0.02)

    # Thumbnails
    for i, idx in enumerate(thumb_idx):
        r = rows[int(idx)]
        ax_t = fig.add_subplot(gs[0, i])
        try:
            vertices, _normals, _centroids = cap.load_stl_binary(r.stl_path)
            vertices = _downsample_triangles(vertices, target=int(thumb_target_tris))
            seg = _silhouette_line_segments(vertices, view=str(thumb_view))
            lc = LineCollection(seg, colors="black", linewidths=0.18, alpha=1.0)
            ax_t.add_collection(lc)
            ax_t.set_aspect("equal", adjustable="box")
            ax_t.autoscale_view()
        except Exception as e:
            ax_t.text(0.5, 0.5, "thumbnail\nerror", ha="center", va="center")
            ax_t.text(0.5, 0.15, str(e), ha="center", va="center", fontsize=6)
        ax_t.axis("off")
        ax_t.set_title(_format_frame_label(r.frame if r.frame >= 0 else idx), fontsize=8, pad=1.5)

    # Main plot
    ax = fig.add_subplot(gs[1, :])
    x = np.array([r.frame if r.frame >= 0 else i for i, r in enumerate(rows)], dtype=float)
    D_max = np.array([r.D_max for r in rows], dtype=float)
    D_min = np.array([r.D_min for r in rows], dtype=float)
    D_p50 = np.array([r.D_p50 for r in rows], dtype=float)
    D_p95 = np.array([r.D_p95 for r in rows], dtype=float)
    sh_L6 = np.array([r.sh_rms_L6 for r in rows], dtype=float)

    ax.fill_between(x, D_min, D_max, color="#4c72b0", alpha=0.18, linewidth=0, label=r"$[D_{\min}, D_{\max}]$")
    ax.plot(x, D_max, "o-", color="#4c72b0", label=r"$D_{\max}$")
    ax.plot(x, D_min, "o-", color="#4c72b0", alpha=0.75, label=r"$D_{\min}$")
    ax.plot(x, D_p95, "o-", color="#dd8452", label=r"$D_{p95}$")
    ax.plot(x, D_p50, "o-", color="black", label=r"$D_{p50}$")
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1.0)

    # Annotation: D_max variation
    i_min = int(np.argmin(D_max))
    i_max = int(np.argmax(D_max))
    dmin = float(D_max[i_min])
    dmax = float(D_max[i_max])
    rel = (dmax - dmin) / dmin * 100.0 if dmin > 0 else np.nan
    ax.text(
        0.01,
        0.97,
        rf"$D_{{\max}}$: {dmin:.3f} → {dmax:.3f}  ({rel:.1f}\% spread)",
        transform=ax.transAxes,
        ha="left",
        va="top",
        bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.75},
    )
    ax.text(
        0.01,
        0.87,
        rf"SH fit RMS at $L=6$: {np.max(sh_L6):.4f} max",
        transform=ax.transAxes,
        ha="left",
        va="top",
        bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.75},
    )

    ax.set_xlabel("Animation frame")
    ax.set_ylabel(r"Directivity $D$")
    ax.set_xlim(np.min(x) - 2, np.max(x) + 2)
    ax.set_ylim(min(0.84, float(np.min(D_min) - 0.02)), max(1.16, float(np.max(D_max) + 0.02)))
    ax.grid(True, axis="y", alpha=0.20)
    ax.legend(
        ncol=2,
        frameon=True,
        loc="upper right",
        fontsize=ps.MONOGRAPH.legend_fontsize_pt,
    )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=int(dpi))
    try:
        fig.savefig(out_pdf)  # vector output (mathtext, no TeX dependency)
    finally:
        plt.close(fig)


def _plot_data_only(rows: list[PostureRow], *, out_png: Path, out_pdf: Path, dpi: int) -> None:
    ps.apply_monograph_style(mode="png", constrained_layout=False)
    fig, ax = plt.subplots(1, 1, figsize=ps.fig_size_textwidth(aspect=0.52, scale=1.0))

    x = np.array([r.frame if r.frame >= 0 else i for i, r in enumerate(rows)], dtype=float)
    D_max = np.array([r.D_max for r in rows], dtype=float)
    D_min = np.array([r.D_min for r in rows], dtype=float)
    D_p50 = np.array([r.D_p50 for r in rows], dtype=float)
    D_p95 = np.array([r.D_p95 for r in rows], dtype=float)
    sh_L6 = np.array([r.sh_rms_L6 for r in rows], dtype=float)

    ax.fill_between(x, D_min, D_max, color="#4c72b0", alpha=0.18, linewidth=0, label=r"$[D_{\min}, D_{\max}]$")
    ax.plot(x, D_max, "o-", color="#4c72b0", label=r"$D_{\max}$")
    ax.plot(x, D_min, "o-", color="#4c72b0", alpha=0.75, label=r"$D_{\min}$")
    ax.plot(x, D_p95, "o-", color="#dd8452", label=r"$D_{p95}$")
    ax.plot(x, D_p50, "o-", color="black", label=r"$D_{p50}$")
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1.0)

    i_min = int(np.argmin(D_max))
    i_max = int(np.argmax(D_max))
    dmin = float(D_max[i_min])
    dmax = float(D_max[i_max])
    rel = (dmax - dmin) / dmin * 100.0 if dmin > 0 else np.nan
    ax.text(
        0.02,
        0.96,
        rf"$D_{{\max}}$: {dmin:.3f} → {dmax:.3f}  ({rel:.1f}\% spread)",
        transform=ax.transAxes,
        ha="left",
        va="top",
    )
    ax.text(
        0.02,
        0.86,
        rf"SH fit RMS at $L=6$: {np.max(sh_L6):.4f} max",
        transform=ax.transAxes,
        ha="left",
        va="top",
    )

    ax.set_xlabel("Animation frame")
    ax.set_ylabel(r"Directivity $D$")
    ax.set_xlim(np.min(x) - 2, np.max(x) + 2)
    ax.set_ylim(min(0.84, float(np.min(D_min) - 0.02)), max(1.16, float(np.max(D_max) + 0.02)))
    ax.grid(True, axis="y", alpha=0.20)
    ax.legend(
        ncol=2,
        frameon=True,
        loc="upper center",
        fontsize=ps.MONOGRAPH.legend_fontsize_pt,
    )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=int(dpi))
    try:
        fig.savefig(out_pdf)
    finally:
        plt.close(fig)


def main(argv: Iterable[str] | None = None) -> int:
    _ = argv
    args = _parse_args()
    rows = _read_summary_csv(Path(args.csv))

    outdir = Path(args.outdir)
    out_png = outdir / f"{args.basename}.png"
    out_pdf = outdir / f"{args.basename}.pdf"

    if bool(args.thumbnails):
        _plot_with_thumbnails(
            rows,
            out_png=out_png,
            out_pdf=out_pdf,
            dpi=int(args.dpi),
            thumb_view=str(args.thumbnail_view),
            thumb_target_tris=int(args.thumbnail_target_tris),
        )
    else:
        _plot_data_only(rows, out_png=out_png, out_pdf=out_pdf, dpi=int(args.dpi))

    print(f"[posture_plot] Wrote: {out_png}")
    print(f"[posture_plot] Wrote: {out_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

