"""Load the canonical Sionna RT Munich scene, place a BS, render top-down.

Renders three views to JSAC2/code/outputs/munich/:
  topdown_full.png   -- whole scene, BS marked
  topdown_zoom.png   -- 200 m x 200 m around BS, with grid overlay
  perspective.png    -- oblique view from above for context

The BS coordinates are persisted to munich_bs.json so downstream
scripts (Rx grid, path tracing) load the same value.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from sionna.rt import load_scene, scene as sc, Camera

OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs/munich")
BS_JSON = Path(__file__).with_name("munich_bs.json")

# Canonical BS placement: scene-centre rooftop. The Munich scene's bbox
# is roughly (-805, -688) -- (670, 517) m, with buildings up to ~99 m
# tall. We pick a rooftop near the central plaza area (Marienplatz
# region in the canonical Sionna scene). Height 35 m is a typical
# macro-cell mast height above ground level; we'll bump if the local
# rooftop is taller after inspecting the top-down.
BS_POS = np.array([8.5, 21.7, 35.0])


def render_topdown_full(scene, bs_pos: np.ndarray, out_path: Path) -> None:
    """Top-down render of the full Munich bbox with BS marked."""
    bb = scene.mi_scene.bbox()
    cx, cy = float(bb.center()[0]), float(bb.center()[1])
    cam = Camera(position=(cx, cy, 800.0), look_at=(cx, cy, 0.0))
    scene.render_to_file(camera=cam, filename=str(out_path),
                         resolution=(1024, 1024))
    # Overlay BS marker on the rendered PNG.
    img = plt.imread(out_path)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(img)
    h, w = img.shape[:2]
    ext_x = float(bb.max[0] - bb.min[0])
    ext_y = float(bb.max[1] - bb.min[1])
    # Pixel coords: (x_world - cx)/ext_x maps to [-0.5, 0.5] of width.
    # Image origin is top-left; world +y typically maps to image -y.
    px = w / 2 + (bs_pos[0] - cx) / ext_x * w
    py = h / 2 - (bs_pos[1] - cy) / ext_y * h
    ax.add_patch(Circle((px, py), radius=12, color="red", fill=False, lw=2))
    ax.plot(px, py, "rx", markersize=14, mew=2)
    ax.text(px + 18, py - 6, f"BS @ ({bs_pos[0]:.0f}, {bs_pos[1]:.0f}, {bs_pos[2]:.0f})",
            color="red", fontsize=10,
            bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none"})
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"Munich (Sionna RT canonical) -- bbox "
                 f"{bb.min[0]:.0f},{bb.min[1]:.0f} -- {bb.max[0]:.0f},{bb.max[1]:.0f} m")
    fig.tight_layout()
    fig.savefig(out_path.with_name("topdown_full_annotated.png"), dpi=150,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path.with_name('topdown_full_annotated.png')}")


def render_topdown_zoom(scene, bs_pos: np.ndarray, out_path: Path,
                        half_width: float = 100.0) -> None:
    """Top-down zoom around BS (default 200 m x 200 m), grid overlay."""
    cam = Camera(position=(float(bs_pos[0]), float(bs_pos[1]), 250.0),
                 look_at=(float(bs_pos[0]), float(bs_pos[1]), 0.0))
    scene.render_to_file(camera=cam, filename=str(out_path),
                         resolution=(1024, 1024))
    img = plt.imread(out_path)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(img, extent=[bs_pos[0] - half_width, bs_pos[0] + half_width,
                           bs_pos[1] - half_width, bs_pos[1] + half_width],
              origin="upper")
    # Match camera FOV: at z=250 m looking down, perspective camera FOV is
    # ~35 deg horiz by default in Sionna -> half-angle 17.5 deg ->
    # half-width ~ 250 * tan(17.5deg) = 78.8 m. Adjust extent.
    fov_half = 250.0 * np.tan(np.deg2rad(35.0 / 2))
    ax.set_xlim(bs_pos[0] - fov_half, bs_pos[0] + fov_half)
    ax.set_ylim(bs_pos[1] - fov_half, bs_pos[1] + fov_half)
    ax.set_aspect("equal")
    # Draw 25 m grid.
    for g in np.arange(int(bs_pos[0] - fov_half), int(bs_pos[0] + fov_half) + 1, 25):
        ax.axvline(g, color="cyan", alpha=0.25, lw=0.5)
    for g in np.arange(int(bs_pos[1] - fov_half), int(bs_pos[1] + fov_half) + 1, 25):
        ax.axhline(g, color="cyan", alpha=0.25, lw=0.5)
    ax.add_patch(Circle((bs_pos[0], bs_pos[1]), radius=2.5, color="red",
                        fill=True, alpha=0.9, zorder=5))
    ax.plot(bs_pos[0], bs_pos[1], "rx", markersize=14, mew=2, zorder=6)
    ax.text(bs_pos[0] + 5, bs_pos[1] + 5,
            f"BS @ ({bs_pos[0]:.1f}, {bs_pos[1]:.1f}, {bs_pos[2]:.0f})",
            color="red", fontsize=10,
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"},
            zorder=6)
    ax.set_xlabel("world x [m]"); ax.set_ylabel("world y [m]")
    ax.set_title(f"Munich -- top-down zoom (~{2 * fov_half:.0f} m x {2 * fov_half:.0f} m)")
    fig.tight_layout()
    fig.savefig(out_path.with_name("topdown_zoom_annotated.png"), dpi=150,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path.with_name('topdown_zoom_annotated.png')}")


def render_perspective(scene, bs_pos: np.ndarray, out_path: Path) -> None:
    """Oblique view from above for context."""
    cam = Camera(position=(float(bs_pos[0]) + 150.0, float(bs_pos[1]) - 150.0, 200.0),
                 look_at=(float(bs_pos[0]), float(bs_pos[1]), 0.0))
    scene.render_to_file(camera=cam, filename=str(out_path),
                         resolution=(1024, 768))
    print(f"  wrote {out_path}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Loading Munich scene ...")
    s = load_scene(sc.munich)
    bb = s.mi_scene.bbox()
    print(f"  bbox: {bb.min} -- {bb.max}")
    print(f"  BS pos: {BS_POS}")
    render_topdown_full(s, BS_POS, OUT_DIR / "topdown_full.png")
    render_topdown_zoom(s, BS_POS, OUT_DIR / "topdown_zoom.png")
    render_perspective(s, BS_POS, OUT_DIR / "perspective.png")
    BS_JSON.write_text(json.dumps({"bs_pos_xyz_m": BS_POS.tolist()}, indent=2))
    print(f"  wrote {BS_JSON}")


if __name__ == "__main__":
    main()
