"""Place ~16 phone Rx positions in Munich, classify LOS/NLOS, render.

Strategy: hand-pick candidate positions in the central plaza around
BS=(8.5, 21.7, 35) -- a mix of open-plaza positions (expected LOS),
side-street positions, and behind-building positions (expected NLOS).
For each candidate we run a single-path Sionna solve (LOS only) and
check whether a direct path exists; mark green if it does, red if not.

Outputs:
  outputs/munich/rx_grid_annotated.png  -- top-down with markers
  scenes/munich_rx.json                -- locked Rx coords + LOS labels
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from sionna.rt import (
    load_scene, scene as sc, Camera,
    Transmitter, Receiver, PlanarArray, PathSolver,
)

OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs/munich")
BS_JSON = Path(__file__).with_name("munich_bs.json")
RX_JSON = Path(__file__).with_name("munich_rx.json")

# Phone height: standard chest height for a held mmWave handset.
PHONE_Z = 1.5

# Candidate Rx positions (x, y) in Munich world coords. Picked from
# dual_scan.npz (open-ground AND BS-LOS classifier):
#   LOS picks  = open ground in the central plaza, BS sees them
#                directly. All at neg x and 20<y<60 along the open
#                plaza strip running NW from BS.
#   NLOS picks = open ground on actual streets (not building interiors)
#                that are shadowed from BS by intervening buildings.
#                Mix of distances 35-65 m and N/E/S/W directions.
CANDIDATES = [
    # ---- 8 LOS (open + BS-LOS, in the plaza strip neg x, 20<y<60) ----
    ( -4.0, 26.0, "LOS_plaza_close_N"),
    ( -8.0, 30.0, "LOS_plaza_NW_close"),
    ( -8.0, 38.0, "LOS_plaza_NW_mid"),
    ( -4.0, 42.0, "LOS_plaza_N_mid"),
    (-12.0, 42.0, "LOS_plaza_W_mid"),
    ( -8.0, 50.0, "LOS_plaza_NW_far"),
    ( -4.0, 54.0, "LOS_plaza_N_far"),
    ( -8.0, 58.0, "LOS_plaza_NW_edge"),
    # ---- 8 NLOS (open street + NOT BS-LOS, mixed dirs and distances) ----
    ( -8.0,-14.0, "NLOS_S_close"),       # ~37 m, south alley behind BS block
    ( 20.0,-22.0, "NLOS_SE_close"),      # ~46 m, south-east street
    (-12.0,-22.0, "NLOS_SW_close"),      # ~48 m, south alley west
    ( 40.0, -6.0, "NLOS_E_mid"),         # ~42 m, east street
    (-44.0, -2.0, "NLOS_W_mid"),         # ~58 m, west avenue south
    (-52.0, 10.0, "NLOS_W_far"),         # ~62 m, far west avenue
    ( 32.0,-30.0, "NLOS_SE_far"),        # ~57 m, south-east deep street
    (-20.0,-38.0, "NLOS_SSW_far"),       # ~65 m, south-southwest deep
]


def classify_rx(scene, bs_pos, rx_xy, rx_z=PHONE_Z):
    """Return 'LOS' if Sionna finds a LOS path from BS to (rx_xy, rx_z),
    else 'NLOS'. Uses a single-element TX/RX and los_only=True solve."""
    import contextlib
    for name in ("tx_los_test", "rx_los_test"):
        with contextlib.suppress(ValueError, KeyError):
            scene.remove(name)
    scene.tx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                  polarization="V")
    scene.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                  polarization="V")
    scene.add(Transmitter("tx_los_test", position=[float(bs_pos[0]),
                                                    float(bs_pos[1]),
                                                    float(bs_pos[2])]))
    scene.add(Receiver("rx_los_test", position=[float(rx_xy[0]),
                                                 float(rx_xy[1]),
                                                 float(rx_z)]))
    solver = PathSolver()
    paths = solver(scene=scene, los=True, specular_reflection=False,
                   diffuse_reflection=False, refraction=False,
                   max_depth=0)
    # paths.a shape: (rx, tx, num_paths). If any non-zero amplitude => LOS.
    a = np.asarray(paths.a[0]) if hasattr(paths, "a") else None
    if a is None or a.size == 0:
        return "NLOS"
    # Sionna v2 returns complex amplitude per path; LOS exists if abs(a) > 0
    has_los = bool(np.any(np.abs(a) > 1e-30))
    return "LOS" if has_los else "NLOS"


def render_rx_grid(scene, bs_pos, candidates_with_labels, out_path):
    """Top-down render of Munich with BS + all Rx markers (green=LOS,
    red=NLOS). Loads a fresh scene to avoid leftover Sionna sphere
    renders from the LOS solves."""
    import contextlib
    # Strip any leftover tx/rx so the rendered PNG is clean.
    for name in list(scene.transmitters.keys()) + list(scene.receivers.keys()):
        with contextlib.suppress(Exception):
            scene.remove(name)
    cx, cy = float(bs_pos[0]), float(bs_pos[1])
    cam = Camera(position=(cx, cy, 250.0), look_at=(cx, cy, 0.0))
    scene.render_to_file(camera=cam, filename=str(out_path),
                         resolution=(1024, 1024))
    img = plt.imread(out_path)
    fig, ax = plt.subplots(figsize=(10, 10))
    fov_half = 250.0 * np.tan(np.deg2rad(35.0 / 2))
    ax.imshow(img, extent=[cx - fov_half, cx + fov_half,
                           cy - fov_half, cy + fov_half],
              origin="upper")
    ax.set_xlim(cx - fov_half, cx + fov_half)
    ax.set_ylim(cy - fov_half, cy + fov_half)
    ax.set_aspect("equal")
    # BS marker
    ax.plot(cx, cy, "x", color="red", markersize=18, mew=2.5, zorder=10)
    ax.text(cx + 4, cy + 4, "BS", color="red", fontsize=11, zorder=10,
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"})
    # Rx markers
    for i, (x, y, label, los_flag) in enumerate(candidates_with_labels):
        color = "lime" if los_flag == "LOS" else "red"
        ax.plot(x, y, "o", color=color, markersize=10, mec="black",
                mew=1.0, zorder=8)
        ax.annotate(f"{i}", (x, y), xytext=(6, 6),
                    textcoords="offset points",
                    fontsize=8, color="white",
                    bbox={"facecolor": color, "alpha": 0.9, "edgecolor": "none",
                          "pad": 1.5},
                    zorder=9)
    # Legend
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="x", color="red", lw=0, markersize=12,
               mew=2.5, label="BS"),
        Line2D([0], [0], marker="o", color="lime", lw=0, markersize=10,
               mec="black", label="LOS Rx"),
        Line2D([0], [0], marker="o", color="red", lw=0, markersize=10,
               mec="black", label="NLOS Rx"),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=10)
    ax.set_xlabel("world x [m]"); ax.set_ylabel("world y [m]")
    ax.set_title(f"Munich Rx grid: BS at ({cx:.1f}, {cy:.1f}, "
                 f"{bs_pos[2]:.0f} m), phone at z={PHONE_Z:.1f} m")
    fig.tight_layout()
    out_anno = out_path.with_name("rx_grid_annotated.png")
    fig.savefig(out_anno, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_anno}")


def main():
    bs_pos = np.array(json.loads(BS_JSON.read_text())["bs_pos_xyz_m"])
    print(f"Loaded BS pos: {bs_pos}")
    print(f"Loading Munich scene ...")
    s = load_scene(sc.munich)

    print(f"Classifying {len(CANDIDATES)} candidate Rx (LOS/NLOS):")
    candidates_with_labels = []
    rx_records = []
    for x, y, label in CANDIDATES:
        flag = classify_rx(s, bs_pos, (x, y))
        candidates_with_labels.append((x, y, label, flag))
        rx_records.append({
            "x": x, "y": y, "z": PHONE_Z,
            "label": label, "los_flag": flag,
        })
        print(f"  rx[{len(rx_records) - 1:2d}] ({x:+6.1f}, {y:+6.1f}) "
              f"-> {flag}  [{label}]")

    n_los = sum(1 for r in rx_records if r["los_flag"] == "LOS")
    n_nlos = len(rx_records) - n_los
    print(f"  totals: {n_los} LOS, {n_nlos} NLOS")

    render_rx_grid(s, bs_pos, candidates_with_labels,
                   OUT_DIR / "rx_grid.png")

    RX_JSON.write_text(json.dumps({
        "bs_pos_xyz_m": bs_pos.tolist(),
        "phone_z_m": PHONE_Z,
        "rx": rx_records,
    }, indent=2))
    print(f"  wrote {RX_JSON}")


if __name__ == "__main__":
    main()
