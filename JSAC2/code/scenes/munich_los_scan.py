"""Coarse LOS coverage scan from BS to a grid of ground points.

Outputs a heatmap of LOS=1 / NLOS=0 over a 200x200 m area at z=1.5 m,
so we can pick Rx coordinates from genuinely LOS-visible spots.
"""

from __future__ import annotations

import json
from pathlib import Path

import contextlib
import numpy as np
import matplotlib.pyplot as plt
from sionna.rt import (load_scene, scene as sc, Camera, PlanarArray,
                        Transmitter, Receiver, PathSolver)

OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs/munich")
BS_JSON = Path(__file__).with_name("munich_bs.json")
GRID_NPZ = OUT_DIR / "los_scan.npz"

PHONE_Z = 1.5
GRID_HALF = 90.0     # +/- 90 m around BS
GRID_STEP = 10.0     # 10 m step -> 19x19 = 361 points
SOLVER = PathSolver()


def los_solve_batch(scene, bs_pos, rx_xyz_list):
    """Sionna v2 supports multiple receivers in one solve. Add all
    Rx, run los-only with max_depth=0, return per-rx LOS bool."""
    for o in list(scene.transmitters.keys()) + list(scene.receivers.keys()):
        with contextlib.suppress(Exception):
            scene.remove(o)
    scene.tx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                  polarization="V")
    scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                  polarization="V")
    scene.add(Transmitter("tx", position=[float(bs_pos[0]),
                                          float(bs_pos[1]),
                                          float(bs_pos[2])]))
    for i, (x, y, z) in enumerate(rx_xyz_list):
        scene.add(Receiver(f"rx_{i}",
                           position=[float(x), float(y), float(z)]))
    paths = SOLVER(scene=scene, los=True, specular_reflection=False,
                   diffuse_reflection=False, refraction=False, max_depth=0)
    a = np.asarray(paths.a[0])  # (rx, tx, num_paths) for the real component
    # paths.a is a tuple (real, imag) in Sionna v2; sum magnitudes across paths
    a_re = np.asarray(paths.a[0])
    a_im = np.asarray(paths.a[1]) if len(paths.a) > 1 else np.zeros_like(a_re)
    mag = np.sqrt(a_re ** 2 + a_im ** 2)
    # mag shape: (num_rx, num_tx, num_paths). Sum over tx & paths.
    while mag.ndim > 1:
        mag = mag.sum(axis=-1)
    has_los = mag > 1e-30
    return np.asarray(has_los, dtype=bool)


def main():
    bs_pos = np.array(json.loads(BS_JSON.read_text())["bs_pos_xyz_m"])
    print(f"BS pos: {bs_pos}")
    s = load_scene(sc.munich)

    xs = np.arange(bs_pos[0] - GRID_HALF, bs_pos[0] + GRID_HALF + 0.1,
                   GRID_STEP)
    ys = np.arange(bs_pos[1] - GRID_HALF, bs_pos[1] + GRID_HALF + 0.1,
                   GRID_STEP)
    XX, YY = np.meshgrid(xs, ys, indexing="xy")
    pts = np.stack([XX.flatten(), YY.flatten(),
                    np.full_like(XX.flatten(), PHONE_Z)], axis=1)
    print(f"Solving {len(pts)} grid points ...")

    # Sionna can struggle with very many simultaneous Rx; split in chunks.
    LOS = np.zeros(len(pts), dtype=bool)
    chunk = 32
    for i in range(0, len(pts), chunk):
        sub = pts[i:i + chunk]
        flags = los_solve_batch(s, bs_pos, sub.tolist())
        LOS[i:i + chunk] = flags
        print(f"  {i + len(sub):3d}/{len(pts)} done, "
              f"running LOS frac = {LOS[:i + len(sub)].mean():.2f}")
    LOS = LOS.reshape(XX.shape)

    np.savez(GRID_NPZ, xs=xs, ys=ys, LOS=LOS, bs_pos=bs_pos)
    print(f"  wrote {GRID_NPZ}, total LOS fraction = {LOS.mean():.2f}")

    # Render: top-down camera + LOS heatmap overlay
    cx, cy = float(bs_pos[0]), float(bs_pos[1])
    cam = Camera(position=(cx, cy, 250.0), look_at=(cx, cy, 0.0))
    s.render_to_file(camera=cam,
                     filename=str(OUT_DIR / "los_scan_bg.png"),
                     resolution=(1024, 1024))
    img = plt.imread(OUT_DIR / "los_scan_bg.png")
    fig, ax = plt.subplots(figsize=(10, 10))
    fov_half = 250.0 * np.tan(np.deg2rad(35.0 / 2))
    ax.imshow(img, extent=[cx - fov_half, cx + fov_half,
                           cy - fov_half, cy + fov_half],
              origin="upper")
    ax.set_xlim(cx - fov_half, cx + fov_half)
    ax.set_ylim(cy - fov_half, cy + fov_half)
    # LOS overlay
    ax.scatter(XX[LOS], YY[LOS], c="lime", s=80, marker="o",
               edgecolors="black", linewidths=0.5, alpha=0.85,
               label=f"LOS ({LOS.sum()})")
    ax.scatter(XX[~LOS], YY[~LOS], c="red", s=20, marker="x",
               linewidths=1.0, alpha=0.5,
               label=f"NLOS ({(~LOS).sum()})")
    ax.plot(cx, cy, "X", color="yellow", markersize=20, mec="black",
            mew=2, zorder=10)
    ax.text(cx + 4, cy + 4, "BS", color="yellow", fontsize=12, zorder=10,
            bbox={"facecolor": "black", "alpha": 0.7, "edgecolor": "none"})
    ax.set_aspect("equal")
    ax.set_xlabel("world x [m]"); ax.set_ylabel("world y [m]")
    ax.legend(loc="upper right", fontsize=10)
    ax.set_title(f"Munich LOS coverage from BS=({cx:.1f}, {cy:.1f}, "
                 f"{bs_pos[2]:.0f} m), step={GRID_STEP:.0f} m, z={PHONE_Z} m")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "los_scan.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {OUT_DIR / 'los_scan.png'}")


if __name__ == "__main__":
    main()
