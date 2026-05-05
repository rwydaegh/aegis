"""Detect plaza openings by raycasting outwards from the plaza centre.

For each angle θ around the plaza centre, walks a ray outward and records
the distance to the first building wall it intersects (or `r_max` if it
never does). Local maxima in this radial profile mark the street
openings — an opening is a direction where the building polygon has a gap.

Saves two artefacts:
  - `plaza_openings_polar.png` — polar plot of free distance vs θ
  - `plaza_openings_marked.png` — top-down map with detected openings
    drawn as orange diamonds, plus the configured ENTRY_NODES_M as red
    circles, so the iteration target is "every diamond should match a
    circle".
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from scipy.signal import find_peaks

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scenario import BS_X_M, BS_Y_M, ENTRY_NODES_M  # noqa: E402

MESH_PATH = Path("data/scenes/brussels_grand_place/mesh.npz")


def _load_walls():
    m = np.load(MESH_PATH)
    verts = m["vertices"]
    tris = m["triangles"]
    tri_z = verts[tris][:, :, 2]
    wall_mask = tri_z.max(axis=1) > 0.5
    return verts, tris[wall_mask]


def _ray_segment_intersect(o, d, p1, p2):
    """Ray (o + t·d, t≥0) vs segment p1-p2; return t or +inf."""
    seg = p2 - p1
    denom = d[0] * seg[1] - d[1] * seg[0]
    if abs(denom) < 1e-9:
        return np.inf
    diff = p1 - o
    t = (diff[0] * seg[1] - diff[1] * seg[0]) / denom
    s = (diff[0] * d[1] - diff[1] * d[0]) / denom
    if t < 0 or s < 0 or s > 1:
        return np.inf
    return t


def _wall_segments_xy(verts, tris):
    """Project wall triangles to xy and dedupe edges (segments)."""
    seen = set()
    segments = []
    for tri in tris:
        a, b, c = tri
        for u, v in [(a, b), (b, c), (c, a)]:
            key = (min(u, v), max(u, v))
            if key in seen:
                continue
            seen.add(key)
            p1 = verts[u, :2]
            p2 = verts[v, :2]
            if np.allclose(p1, p2):
                continue
            segments.append((p1, p2))
    return segments


_PLAZA_CENTRE_XY = np.array([0.0, 5.0])


def detect_openings(
    centre_xy: np.ndarray | None = None,
    n_rays: int = 720,
    r_max: float = 60.0,
    peak_prominence: float = 4.0,
    peak_min_radius: float = 18.0,
):
    if centre_xy is None:
        centre_xy = _PLAZA_CENTRE_XY
    verts, tris = _load_walls()
    segments = _wall_segments_xy(verts, tris)
    angles = np.linspace(-np.pi, np.pi, n_rays, endpoint=False)
    radii = np.full(n_rays, r_max, dtype=np.float64)
    for i, th in enumerate(angles):
        d = np.array([np.cos(th), np.sin(th)])
        best = r_max
        for p1, p2 in segments:
            t = _ray_segment_intersect(centre_xy, d, p1, p2)
            if t < best:
                best = t
        radii[i] = best
    # Wrap-aware peak detection: pad with one period on each side, find peaks,
    # then keep peaks falling in the central period.
    padded = np.concatenate([radii, radii, radii])
    peaks, _ = find_peaks(padded, prominence=peak_prominence)
    peaks = peaks - n_rays
    peaks = peaks[(peaks >= 0) & (peaks < n_rays)]
    # Drop peaks too close to centre (interior dwells, not openings).
    peaks = peaks[radii[peaks] >= peak_min_radius]
    return angles, radii, peaks, centre_xy


def render(out_dir: Path, half_extent: float = 50.0):
    angles, radii, peaks, centre = detect_openings()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Polar plot.
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
    ax.plot(angles, radii, color="#2266aa", lw=1.0)
    ax.scatter(angles[peaks], radii[peaks], c="#ee6622", s=80, zorder=5, edgecolors="black", lw=0.8)
    for p in peaks:
        ax.annotate(
            f"{np.rad2deg(angles[p]):.0f}°\n{radii[p]:.1f}m",
            xy=(angles[p], radii[p]),
            xytext=(angles[p], radii[p] + 5),
            fontsize=8,
            ha="center",
        )
    ax.set_title("Free distance from plaza centre vs θ (peaks = openings)")
    fig.savefig(out_dir / "plaza_openings_polar.png", dpi=120)
    plt.close(fig)

    # Top-down map with both detected openings (orange diamonds at ray endpoint)
    # and configured entry nodes (red circles).
    verts, tris = _load_walls()
    polys = verts[tris][:, :, :2]
    pc = PolyCollection(polys, facecolors="#9aa0aa", edgecolors="none", alpha=0.85, zorder=2)

    fig, ax = plt.subplots(figsize=(14, 14), dpi=140)
    ax.set_aspect("equal")
    ax.set_facecolor("#f0eee8")
    ax.add_collection(pc)
    ax.axhline(0.0, color="#ccc", lw=0.4, zorder=1)
    ax.axvline(0.0, color="#ccc", lw=0.4, zorder=1)
    ax.scatter([BS_X_M], [BS_Y_M], marker="s", s=160, c="#cc4422", edgecolors="black", lw=1.0, zorder=4)
    ax.annotate("BS", xy=(BS_X_M, BS_Y_M), xytext=(BS_X_M + 2, BS_Y_M + 2), fontsize=10, color="#882211")

    for name, (x, y) in ENTRY_NODES_M.items():
        ax.scatter([x], [y], marker="o", s=140, c="#cc1144", edgecolors="black", lw=1.0, zorder=5)
        ax.annotate(name, xy=(x, y), xytext=(x + 1.5, y + 1.5), fontsize=8, color="#aa1133")

    cx, cy = centre
    for p in peaks:
        rx = cx + 0.95 * radii[p] * np.cos(angles[p])
        ry = cy + 0.95 * radii[p] * np.sin(angles[p])
        ax.scatter([rx], [ry], marker="D", s=110, c="#ee6622", edgecolors="black", lw=0.8, zorder=6)
        ax.annotate(
            f"{np.rad2deg(angles[p]):.0f}°", xy=(rx, ry), xytext=(rx + 1, ry - 2.5), fontsize=8, color="#aa3300"
        )
        ax.plot([cx, rx], [cy, ry], color="#ee6622", lw=0.4, alpha=0.4, zorder=1)

    ax.set_xlim(-half_extent, half_extent)
    ax.set_ylim(-half_extent, half_extent)
    ax.grid(color="#cccccc", lw=0.3, alpha=0.5)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title("Detected openings (orange) vs configured ENTRY_NODES_M (red)")
    fig.tight_layout()
    fig.savefig(out_dir / "plaza_openings_marked.png", dpi=120)
    plt.close(fig)
    return out_dir


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=Path("JSAC/code/experiments/plaza_run/figures"))
    args = p.parse_args()
    out = render(args.out_dir)
    print(f"wrote into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
