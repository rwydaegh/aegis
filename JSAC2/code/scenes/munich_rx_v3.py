"""RX picker v3 -- corrects the LOS / NLOS classification bug in v2.

The v2 picker used Sionna's geometric LOS test from BS at z=35 m down to
the street at z=1.5 m. With the BS sitting on a building edge, that test
returns True for many cells that are *not* visible from the user's
viewpoint -- the ray simply goes over short buildings and back down.

Robin's manual inspection of the dual_scan map confirmed:
  - true LOS lives in the open plaza north-west of the BS
    (negative x, 20 < y < 60),
  - cells in the courtyards south and east are *not* LOS even though the
    Sionna test passed for them.

The fix is to constrain LOS to that open-plaza rectangle (still verified
by Sionna's LOS test) and to constrain NLOS to street cells outside the
plaza that are blocked from the BS at street level.

We reuse the existing dual_scan.npz (open_ground + bs_sees on a 4 m
grid) so this picker is essentially zero-cost: no re-tracing, just a
smarter selection rule, then a render and an updated munich_rx.json.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

OUT = Path("/home/user/aegis/JSAC2/code/outputs/munich")
SCENE_JSON = Path("/home/user/aegis/JSAC2/code/scenes/munich_rx.json")
PHONE_Z = 1.5
D_MIN = 15.0
D_MAX_NLOS = 70.0

# Robin's empirical LOS region (the open plaza visible from the BS panel).
LOS_X_MAX = 0.0
LOS_Y_MIN = 20.0
LOS_Y_MAX = 60.0

N_LOS = 16
N_NLOS = 14

SEED = 42


def main():
    d = np.load(OUT / "dual_scan.npz", allow_pickle=False)
    xs, ys = d["xs"], d["ys"]
    open_ground = d["open_ground"]    # (Ny, Nx) bool, True = ground (no roof)
    bs_sees = d["bs_sees"]              # (Ny, Nx) bool, True = Sionna LOS from BS
    bs_pos = d["bs_pos"]
    print(f"BS at {bs_pos}; grid {len(xs)}x{len(ys)} cells")

    # --- LOS pool --------------------------------------------------------
    los_pool = []
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            if not open_ground[iy, ix]:    continue
            if not bs_sees[iy, ix]:        continue
            if not (LOS_X_MAX > x):         continue
            if not (LOS_Y_MIN < y < LOS_Y_MAX): continue
            d_xy = float(np.hypot(x - bs_pos[0], y - bs_pos[1]))
            if d_xy < D_MIN: continue
            los_pool.append((float(x), float(y), d_xy))
    print(f"LOS pool: {len(los_pool)}")

    # --- NLOS pool: street cells with no direct LOS, outside the plaza --
    nlos_pool = []
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            if not open_ground[iy, ix]: continue
            if bs_sees[iy, ix]:         continue
            in_los_box = (LOS_X_MAX > x and LOS_Y_MIN < y < LOS_Y_MAX)
            if in_los_box: continue
            d_xy = float(np.hypot(x - bs_pos[0], y - bs_pos[1]))
            if not (D_MIN <= d_xy <= D_MAX_NLOS): continue
            nlos_pool.append((float(x), float(y), d_xy))
    print(f"NLOS pool: {len(nlos_pool)}")

    rng = np.random.default_rng(SEED)

    def _pick_with_distance_spread(pool, n):
        """Maximin pick over distance: greedily add the candidate whose
        distance is farthest from already-picked ones, so we cover the
        full distance range without leaving empty buckets."""
        if len(pool) <= n:
            return list(pool)
        pool = sorted(pool, key=lambda p: p[2])
        # Seed with closest + farthest, then add maximin until n.
        sel = [pool[0], pool[-1]]
        rest = pool[1:-1]
        while len(sel) < n and rest:
            sel_d = np.array([s[2] for s in sel])
            best_i, best_gap = 0, -1.0
            for i, c in enumerate(rest):
                gap = float(np.min(np.abs(sel_d - c[2])))
                if gap > best_gap:
                    best_gap, best_i = gap, i
            sel.append(rest.pop(best_i))
        return sorted(sel, key=lambda p: p[2])

    sel_los = _pick_with_distance_spread(los_pool, N_LOS)
    print(f"  selected {len(sel_los)} LOS")
    sel_nlos = _pick_with_distance_spread(nlos_pool, N_NLOS)
    print(f"  selected {len(sel_nlos)} NLOS")

    # --- Write munich_rx.json -------------------------------------------
    rxs = []
    for k, (x, y, _) in enumerate(sel_los):
        rxs.append({"x": x, "y": y, "z": PHONE_Z,
                    "label": f"LOS_{k:02d}", "los_flag": "LOS"})
    for k, (x, y, _) in enumerate(sel_nlos):
        rxs.append({"x": x, "y": y, "z": PHONE_Z,
                    "label": f"NLOS_{k:02d}", "los_flag": "NLOS"})
    SCENE_JSON.write_text(json.dumps(
        {"bs_pos_xyz_m": bs_pos.tolist(),
         "phone_z_m": PHONE_Z,
         "rx": rxs}, indent=2))
    print(f"Wrote {len(rxs)} RX to {SCENE_JSON}")

    # --- Render -----------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 11))
    bg = OUT / "los_scan_bg.png"
    if bg.exists():
        img = plt.imread(bg)
        ax.imshow(img, extent=[xs.min() - 5, xs.max() + 5,
                                ys.min() - 5, ys.max() + 5],
                  origin="upper", alpha=0.7)

    # Underlying scan dots: roof (grey), open+LOS (light green), open+NLOS (light red)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    roof = ~open_ground
    ax.scatter(X[roof], Y[roof], c="black", s=6, marker="s", alpha=0.20)
    pool_los = open_ground & bs_sees
    pool_nlos = open_ground & ~bs_sees
    ax.scatter(X[pool_los], Y[pool_los], c="lightgreen", s=10, alpha=0.6)
    ax.scatter(X[pool_nlos], Y[pool_nlos], c="lightcoral", s=10, alpha=0.45)

    # User's LOS region rectangle
    from matplotlib.patches import Rectangle
    rect = Rectangle((-72, LOS_Y_MIN), 72 + LOS_X_MAX, LOS_Y_MAX - LOS_Y_MIN,
                     fill=False, edgecolor="lime", linewidth=2,
                     linestyle="--", label="user-defined LOS region")
    ax.add_patch(rect)

    for k, (x, y, _) in enumerate(sel_los):
        ax.plot(x, y, "o", color="lime", markersize=14, mec="black", mew=1.2,
                zorder=10)
        ax.annotate(str(k), (x, y), xytext=(7, 7), textcoords="offset points",
                    fontsize=9, color="white",
                    bbox={"facecolor": "lime", "alpha": 0.95,
                          "edgecolor": "none", "pad": 1.5}, zorder=11)
    for k, (x, y, _) in enumerate(sel_nlos):
        ax.plot(x, y, "o", color="red", markersize=14, mec="black", mew=1.2,
                zorder=10)
        ax.annotate(str(k), (x, y), xytext=(7, 7), textcoords="offset points",
                    fontsize=9, color="white",
                    bbox={"facecolor": "red", "alpha": 0.95,
                          "edgecolor": "none", "pad": 1.5}, zorder=11)

    # BS + broadside arrow
    ax.plot(bs_pos[0], bs_pos[1], "x", color="yellow", markersize=22, mew=4,
            zorder=20)
    ax.annotate("BS", (bs_pos[0], bs_pos[1]), xytext=(8, 8),
                textcoords="offset points", fontsize=13, color="yellow",
                fontweight="bold", zorder=20)
    target = np.array([-7.0, 42.0])
    arrow = (target - bs_pos[:2])
    arrow = arrow / np.linalg.norm(arrow) * 25.0
    ax.annotate("", xy=(bs_pos[0] + arrow[0], bs_pos[1] + arrow[1]),
                xytext=(bs_pos[0], bs_pos[1]),
                arrowprops={"arrowstyle": "->", "color": "yellow",
                             "lw": 3.5}, zorder=20)
    ax.text(bs_pos[0] + arrow[0] * 1.1, bs_pos[1] + arrow[1] * 1.1,
            "panel\nbroadside", color="yellow", fontsize=11,
            fontweight="bold", zorder=20)

    ax.set_xlim(xs.min() - 5, xs.max() + 5)
    ax.set_ylim(ys.min() - 5, ys.max() + 5)
    ax.set_aspect("equal")
    ax.set_xlabel("world x [m]"); ax.set_ylabel("world y [m]")
    ax.set_title(f"Munich RX selection (v3): {len(sel_los)} LOS + "
                 f"{len(sel_nlos)} NLOS, BS at "
                 f"({bs_pos[0]}, {bs_pos[1]}, {bs_pos[2]:.0f} m)")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    out_png = OUT / "rx_v3_grid.png"
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()
