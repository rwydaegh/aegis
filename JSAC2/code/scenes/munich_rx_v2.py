"""Robin's RX picker protocol:
  1. Take a regular sky grid around the BS.
  2. For each cell, drop a downward ray; if first hit z > z_thresh,
     the cell sits on a building roof -- drop.
  3. If horizontal distance to BS < d_min, drop.
  4. Trace BS -> (cell at street z=1.5) via Sionna with the same
     max_depth/diffraction setup as the main sweep; if total path
     count below n_paths_min, drop.
  5. Classify LOS by has-direct-path; sample n_los/n_nlos uniformly
     across the surviving candidates.
  6. Render top-down annotated map with BS position, BS broadside
     direction (panel normal arrow), and selected RX positions.

Outputs:
  outputs/munich/rx_v2_scan.npz        full scan data (open, los, n_paths)
  outputs/munich/rx_v2_grid.png        annotated render
  scenes/munich_rx.json                 OVERWRITES with new selections
"""
from __future__ import annotations
import contextlib, json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from sionna.rt import (load_scene, scene as sc, Transmitter, Receiver,
                        PlanarArray, PathSolver)

OUT = Path("/home/user/aegis/JSAC2/code/outputs/munich")
BS_POS = np.array([8.5, 21.7, 35.0])
PHONE_Z = 1.5
ROOF_Z_THRESH = 0.5     # m: ray-cast first hit z above this -> roof
D_MIN = 15.0            # m: horizontal distance from BS minimum
N_PATHS_MIN_LOS = 8     # min path count for a LOS candidate
N_PATHS_MIN_NLOS = 2    # min path count for a NLOS candidate (multipath via diffraction/refl)
MAX_DEPTH = 5
N_LOS = 16              # how many LOS RX to keep
N_NLOS = 16             # how many NLOS RX to keep

# Coarse first-pass scan grid (8 m step, ~150m x 150m around BS).
# Coarser than the dual_scan because we then trace in earnest, costly.
xs = np.arange(-72.0, 72.1, 8.0)
ys = np.arange(-44.0, 100.1, 8.0)


def reset(s):
    for nm in list(s.transmitters.keys()) + list(s.receivers.keys()):
        with contextlib.suppress(Exception):
            s.remove(nm)


def downward_first_hit_z(solver, s, x, y):
    """Returns z of the first surface a downward ray from (x,y,100) hits.
    If no path between (x,y,100) and (x,y,0.001) at all -> return -1
    (something blocked). If LOS -> returns 0 (street). Buildings give
    z > 0 because the LOS test at z=0.001 fails when a roof is in the way.

    We use a two-step probe: try (x,y,0.001) first; if blocked, binary
    search z to find the roof height.
    """
    reset(s)
    s.add(Transmitter("tx", position=[float(x), float(y), 100.0]))
    s.add(Receiver("rx", position=[float(x), float(y), 0.001]))
    p = solver(scene=s, los=True, specular_reflection=False,
               diffuse_reflection=False, refraction=False, max_depth=0)
    a = np.asarray(p.a[0])
    has_los = bool(np.any(np.abs(a) > 1e-30))
    if has_los:
        return 0.0
    # blocked by something above; find its height by binary search
    lo, hi = 0.001, 100.0
    for _ in range(20):
        mid = 0.5 * (lo + hi)
        reset(s)
        s.add(Transmitter("tx", position=[float(x), float(y), 100.0]))
        s.add(Receiver("rx", position=[float(x), float(y), float(mid)]))
        p = solver(scene=s, los=True, specular_reflection=False,
                   diffuse_reflection=False, refraction=False, max_depth=0)
        a = np.asarray(p.a[0])
        if bool(np.any(np.abs(a) > 1e-30)):
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)  # roof z (~ height of building)


def trace_count(solver, s, bs_xyz, rx_xyz):
    """Trace BS -> rx with full multipath; return (n_paths, has_LOS)."""
    reset(s)
    s.add(Transmitter("tx", position=[float(bs_xyz[0]), float(bs_xyz[1]),
                                       float(bs_xyz[2])]))
    s.add(Receiver("rx", position=[float(rx_xyz[0]), float(rx_xyz[1]),
                                    float(rx_xyz[2])]))
    p = solver(scene=s, los=True, specular_reflection=True,
               diffuse_reflection=False, refraction=True,
               diffraction=True, edge_diffraction=True,
               max_depth=MAX_DEPTH, samples_per_src=10_000_000,
               max_num_paths_per_src=200_000)
    a, _ = p.cir()
    a = np.asarray(a)
    a_mag = np.sqrt(np.abs(a[0, 0, 0, 0, 0, :, 0]) ** 2
                  + np.abs(a[1, 0, 0, 0, 0, :, 0]) ** 2)
    valid = a_mag > 1e-30
    n_paths = int(valid.sum())
    # LOS detection: separate los-only solve (cheap)
    reset(s)
    s.add(Transmitter("tx", position=[float(bs_xyz[0]), float(bs_xyz[1]),
                                       float(bs_xyz[2])]))
    s.add(Receiver("rx", position=[float(rx_xyz[0]), float(rx_xyz[1]),
                                    float(rx_xyz[2])]))
    p_los = solver(scene=s, los=True, specular_reflection=False,
                   diffuse_reflection=False, refraction=False, max_depth=0)
    a_los = np.asarray(p_los.a[0])
    has_los = bool(np.any(np.abs(a_los) > 1e-30))
    return n_paths, has_los


def main():
    print("Loading Munich ...")
    s = load_scene(sc.munich)
    s.frequency = 28e9
    s.tx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    s.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    solver = PathSolver()

    # Phase 1: roof/ground classification
    print("Phase 1: roof/ground classification ...")
    n_cells = len(xs) * len(ys)
    grid_xy = np.array([(x, y) for y in ys for x in xs])
    roof_z = np.full(n_cells, np.nan)
    for i, (x, y) in enumerate(grid_xy):
        roof_z[i] = downward_first_hit_z(solver, s, x, y)
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{n_cells} ({np.sum(roof_z[:i+1] <= ROOF_Z_THRESH)} ground)")

    # Phase 2: filter candidates
    on_ground = roof_z <= ROOF_Z_THRESH
    dist_xy = np.linalg.norm(grid_xy - BS_POS[None, :2], axis=1)
    far_enough = dist_xy >= D_MIN
    candidate_mask = on_ground & far_enough
    print(f"Phase 2: {candidate_mask.sum()} candidates after roof + d_min "
          f"(of {n_cells})")

    # Phase 3: trace each survivor
    print("Phase 3: trace each candidate ...")
    cand_idx = np.where(candidate_mask)[0]
    n_paths = np.zeros(n_cells, dtype=int)
    has_los_arr = np.zeros(n_cells, dtype=bool)
    for k, i in enumerate(cand_idx):
        x, y = grid_xy[i]
        np_i, hl_i = trace_count(solver, s, BS_POS, (x, y, PHONE_Z))
        n_paths[i] = np_i
        has_los_arr[i] = hl_i
        if (k + 1) % 10 == 0:
            print(f"  {k+1}/{len(cand_idx)} traced (last: {x:+5.0f},{y:+5.0f} "
                  f"-> {np_i} paths, LOS={hl_i})")

    # Phase 4: pick LOS + NLOS sets
    los_mask = candidate_mask & has_los_arr & (n_paths >= N_PATHS_MIN_LOS)
    nlos_mask = candidate_mask & (~has_los_arr) & (n_paths >= N_PATHS_MIN_NLOS)
    los_indices = np.where(los_mask)[0]
    nlos_indices = np.where(nlos_mask)[0]
    print(f"Phase 4: {len(los_indices)} LOS, {len(nlos_indices)} NLOS survive")

    # Sample uniformly across each pool
    rng = np.random.default_rng(42)
    if len(los_indices) > N_LOS:
        # spread across distance buckets
        sel_los = []
        bins = np.linspace(D_MIN, dist_xy[los_indices].max(), N_LOS + 1)
        for b0, b1 in zip(bins[:-1], bins[1:]):
            in_bucket = los_indices[(dist_xy[los_indices] >= b0)
                                     & (dist_xy[los_indices] < b1)]
            if len(in_bucket) > 0:
                sel_los.append(rng.choice(in_bucket))
        sel_los = np.array(sel_los[:N_LOS])
    else:
        sel_los = los_indices
    if len(nlos_indices) > N_NLOS:
        sel_nlos = []
        bins = np.linspace(D_MIN, dist_xy[nlos_indices].max(), N_NLOS + 1)
        for b0, b1 in zip(bins[:-1], bins[1:]):
            in_bucket = nlos_indices[(dist_xy[nlos_indices] >= b0)
                                       & (dist_xy[nlos_indices] < b1)]
            if len(in_bucket) > 0:
                sel_nlos.append(rng.choice(in_bucket))
        sel_nlos = np.array(sel_nlos[:N_NLOS])
    else:
        sel_nlos = nlos_indices

    print(f"Selected: {len(sel_los)} LOS, {len(sel_nlos)} NLOS")

    # Save scan + selection
    np.savez(OUT / "rx_v2_scan.npz",
             grid_xy=grid_xy, roof_z=roof_z, n_paths=n_paths,
             has_los=has_los_arr, candidate=candidate_mask,
             sel_los=sel_los, sel_nlos=sel_nlos,
             bs_pos=BS_POS, d_min=D_MIN, roof_thresh=ROOF_Z_THRESH)

    # Build new munich_rx.json
    rxs = []
    for k, i in enumerate(sel_los):
        x, y = grid_xy[i]
        rxs.append({
            "x": float(x), "y": float(y), "z": PHONE_Z,
            "label": f"LOS_{k:02d}", "los_flag": "LOS"
        })
    for k, i in enumerate(sel_nlos):
        x, y = grid_xy[i]
        rxs.append({
            "x": float(x), "y": float(y), "z": PHONE_Z,
            "label": f"NLOS_{k:02d}", "los_flag": "NLOS"
        })
    Path("/home/user/aegis/JSAC2/code/scenes/munich_rx.json").write_text(
        json.dumps({"bs_pos_xyz_m": BS_POS.tolist(), "phone_z_m": PHONE_Z,
                    "rx": rxs}, indent=2))
    print(f"Wrote {len(rxs)} RX to munich_rx.json")

    # Render
    print("Rendering top-down ...")
    bg_path = OUT / "los_scan_bg.png"
    fig, ax = plt.subplots(figsize=(11, 11))
    if bg_path.exists():
        img = plt.imread(bg_path)
        ax.imshow(img, extent=[xs.min() - 5, xs.max() + 5,
                                ys.min() - 5, ys.max() + 5],
                  origin="upper", alpha=0.7)
    # Faint background showing roofs (grey) and ground candidates (light)
    roof_x = grid_xy[~on_ground, 0]
    roof_y = grid_xy[~on_ground, 1]
    ax.scatter(roof_x, roof_y, c="black", s=8, marker="s", alpha=0.25,
               label="building roof")
    # Ground but too close (excluded)
    too_close = on_ground & (~far_enough)
    ax.scatter(grid_xy[too_close, 0], grid_xy[too_close, 1], c="orange",
               s=8, marker="x", alpha=0.6, label=f"too close (d<{D_MIN:.0f}m)")
    # Selected LOS / NLOS
    for k, i in enumerate(sel_los):
        x, y = grid_xy[i]
        ax.plot(x, y, "o", color="lime", markersize=12, mec="black", mew=1.0)
        ax.annotate(str(k), (x, y), xytext=(6, 6), textcoords="offset points",
                    fontsize=8, color="white",
                    bbox={"facecolor": "lime", "alpha": 0.9,
                          "edgecolor": "none", "pad": 1.5})
    for k, i in enumerate(sel_nlos):
        x, y = grid_xy[i]
        ax.plot(x, y, "o", color="red", markersize=12, mec="black", mew=1.0)
        ax.annotate(str(k), (x, y), xytext=(6, 6), textcoords="offset points",
                    fontsize=8, color="white",
                    bbox={"facecolor": "red", "alpha": 0.9,
                          "edgecolor": "none", "pad": 1.5})
    # BS + facing arrow (panel-normal points toward LOS plaza centroid)
    ax.plot(BS_POS[0], BS_POS[1], "x", color="yellow", markersize=22, mew=3,
            zorder=20)
    ax.annotate("BS", (BS_POS[0], BS_POS[1]), xytext=(8, 8),
                textcoords="offset points", fontsize=12, color="yellow",
                fontweight="bold", zorder=20)
    target = np.array([-7.0, 42.0])
    arrow_dir = target - BS_POS[:2]
    arrow_dir = arrow_dir / np.linalg.norm(arrow_dir) * 25.0
    ax.annotate("", xy=(BS_POS[0] + arrow_dir[0], BS_POS[1] + arrow_dir[1]),
                xytext=(BS_POS[0], BS_POS[1]),
                arrowprops={"arrowstyle": "->", "color": "yellow",
                             "lw": 3, "shrinkA": 0, "shrinkB": 0},
                zorder=20)
    ax.text(BS_POS[0] + arrow_dir[0] * 1.1, BS_POS[1] + arrow_dir[1] * 1.1,
            "panel\nbroadside", color="yellow", fontsize=10,
            fontweight="bold", zorder=20)
    ax.set_xlim(xs.min() - 5, xs.max() + 5)
    ax.set_ylim(ys.min() - 5, ys.max() + 5)
    ax.set_aspect("equal")
    ax.set_xlabel("world x [m]"); ax.set_ylabel("world y [m]")
    ax.set_title(f"Munich RX selection: {len(sel_los)} LOS + {len(sel_nlos)} NLOS, "
                 f"BS at ({BS_POS[0]}, {BS_POS[1]}, {BS_POS[2]:.0f}\\,m)")
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "rx_v2_grid.png", dpi=140, bbox_inches="tight")
    print(f"  wrote {OUT / 'rx_v2_grid.png'}")


if __name__ == "__main__":
    main()
