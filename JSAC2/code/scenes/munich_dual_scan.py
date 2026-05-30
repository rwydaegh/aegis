"""Dense dual-scan: for each (x,y) grid point, test
  (a) is_open_ground: downward ray from z=100 reaches z=0.001 (no roof above)
  (b) bs_sees: LOS from BS at z=35 to phone at z=1.5

Phone-realistic positions = (open_ground AND any BS link). Pick:
  LOS picks  = open_ground AND bs_sees
  NLOS picks = open_ground AND NOT bs_sees   (street user shadowed by buildings)
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

# Scan dense grid covering ~120m × 120m around BS
xs = np.arange(-80.0, 80.1, 4.0)
ys = np.arange(-50.0, 110.1, 4.0)


def reset(s):
    for nm in list(s.transmitters.keys()) + list(s.receivers.keys()):
        with contextlib.suppress(Exception):
            s.remove(nm)


def has_path(solver, s, tx_xyz, rx_xyz):
    reset(s)
    s.add(Transmitter("tx", position=[float(tx_xyz[0]), float(tx_xyz[1]), float(tx_xyz[2])]))
    s.add(Receiver("rx", position=[float(rx_xyz[0]), float(rx_xyz[1]), float(rx_xyz[2])]))
    p = solver(scene=s, los=True, specular_reflection=False,
               diffuse_reflection=False, refraction=False, max_depth=0)
    a = np.asarray(p.a[0])
    return bool(np.any(np.abs(a) > 1e-30))


def main():
    print("Loading Munich ...")
    s = load_scene(sc.munich)
    s.frequency = 28e9
    s.tx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    s.rx_array = PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    solver = PathSolver()

    open_ground = np.zeros((len(ys), len(xs)), dtype=bool)
    bs_sees = np.zeros_like(open_ground)
    n_total = open_ground.size
    print(f"Scanning {n_total} cells ({len(xs)}x{len(ys)}) ...")
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            # (a) sky -> ground: True means open
            open_ground[i, j] = has_path(solver, s, (x, y, 100.0),
                                         (x, y, 0.001))
            if open_ground[i, j]:
                # only test BS LOS for open-ground points
                bs_sees[i, j] = has_path(solver, s, BS_POS, (x, y, PHONE_Z))
        print(f"  row y={y:+5.1f} : open={int(open_ground[i].sum()):2d} / "
              f"bs_los={int(bs_sees[i].sum()):2d}")

    np.savez(OUT / "dual_scan.npz", xs=xs, ys=ys,
             open_ground=open_ground, bs_sees=bs_sees, bs_pos=BS_POS)
    print(f"  wrote {OUT / 'dual_scan.npz'}")

    # Render: shaded background topdown + colored overlay
    bg_path = OUT / "los_scan_bg.png"  # already has scene rendered
    fig, ax = plt.subplots(figsize=(11, 11))
    if bg_path.exists():
        img = plt.imread(bg_path)
        # Reuse existing extent: this PNG was rendered for los_scan;
        # ranges should match scan_bg generation. Approximate via xs/ys span.
        ax.imshow(img, extent=[xs.min() - 5, xs.max() + 5,
                                ys.min() - 5, ys.max() + 5],
                  origin="upper", alpha=0.7)
    XS, YS = np.meshgrid(xs, ys)
    # Underground/inside-building (NOT open) -> black squares
    closed_mask = ~open_ground
    ax.scatter(XS[closed_mask], YS[closed_mask], c="black", s=12,
               marker="s", alpha=0.4, label="under roof / inside")
    # Open ground but no BS link -> red dot (NLOS street)
    nlos_open = open_ground & (~bs_sees)
    ax.scatter(XS[nlos_open], YS[nlos_open], c="red", s=24,
               marker="o", alpha=0.9, label="open + NLOS")
    # Open + LOS -> green dot (clean LOS street/plaza)
    los_open = open_ground & bs_sees
    ax.scatter(XS[los_open], YS[los_open], c="lime", s=28,
               marker="o", edgecolors="black", linewidths=0.6,
               label="open + LOS")
    ax.plot(BS_POS[0], BS_POS[1], "x", color="yellow",
            markersize=22, mew=3, zorder=20, label=f"BS@{BS_POS[2]:.0f}m")
    ax.set_xlim(xs.min() - 5, xs.max() + 5)
    ax.set_ylim(ys.min() - 5, ys.max() + 5)
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
    ax.set_title("Munich open-ground + BS LOS classification "
                 f"(step {xs[1]-xs[0]:.0f} m, BS at "
                 f"({BS_POS[0]}, {BS_POS[1]}, {BS_POS[2]:.0f} m))")
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "dual_scan.png", dpi=140, bbox_inches="tight")
    print(f"  wrote {OUT / 'dual_scan.png'}")


if __name__ == "__main__":
    main()
