"""Render what survives of the 2026-06-01 Ghent run: traced geometry + the 24 exposures."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import PolyCollection

RUN = Path("/home/user/aegis/results/cities/ghent")
OUT = Path("/tmp/claude-1001/-home-user-aegis/98174141-2b87-4aa8-b9ac-06b234469d0b/scratchpad")

z = np.load(RUN / "exposure.npz")
p = z["p_abs_w"]
is_user = z["is_user"]

fig, (ax, bx) = plt.subplots(1, 2, figsize=(13.5, 6.2))

# left: the city that was actually ray traced
layers = [
    ("scene_concrete.ply", "0.78", "buildings"),
    ("scene_asphalt.ply", "0.92", "road"),
    ("scene_water.ply", "#bcd6e8", "water"),
]
for fname, color, label in layers:
    fp = RUN / "city" / fname
    if not fp.exists():
        continue
    m = trimesh.load(fp, process=False)
    v = np.asarray(m.vertices)
    f = np.asarray(m.faces)
    tris = v[f][:, :, :2]
    zmax = v[f][:, :, 2].max(axis=1)
    order = np.argsort(zmax)
    ax.add_collection(
        PolyCollection(tris[order], facecolors=color, edgecolors="none", zorder=1 if label == "buildings" else 0)
    )
    print(f"{label:10s} {len(f):7d} tris  z {v[:, 2].min():7.1f} to {v[:, 2].max():7.1f} m")

ax.set_aspect("equal")
ax.autoscale_view()
ax.set_xlabel("x [m] east")
ax.set_ylabel("y [m] north")
ax.set_title("Ghent scene as traced (28 GHz, Sionna RT)", fontsize=11)

# right: the 24 numbers, users vs bystanders
rng = np.random.default_rng(0)
for mask, color, marker, label in [
    (is_user, "#c1121f", "o", f"served users (n={is_user.sum()})"),
    (~is_user, "#3d5a80", "s", f"bystanders (n={(~is_user).sum()})"),
]:
    xj = rng.normal(0 if label.startswith("served") else 1, 0.045, mask.sum())
    bx.scatter(xj, p[mask] * 1e6, c=color, marker=marker, s=70, edgecolors="black", linewidths=0.6, label=label)
    bx.hlines(np.median(p[mask]) * 1e6, -0.3 if label.startswith("served") else 0.7,
              0.3 if label.startswith("served") else 1.3, colors=color, lw=2)

bx.set_yscale("log")
bx.set_xticks([0, 1])
bx.set_xticklabels(["served", "bystander"])
bx.set_xlim(-0.5, 1.5)
bx.set_ylabel(r"absorbed power [$\mu$W]")
bx.set_title("Per-person whole-body absorbed power", fontsize=11)
bx.grid(axis="y", alpha=0.3)
bx.legend(frameon=True, fontsize=9)

fig.tight_layout()
out = OUT / "ghent_what_exists.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nwrote {out}")

print("\n--- the 24 numbers, microwatts ---")
for i in np.argsort(-p):
    print(f"  agent {i:2d}  {'USER ' if is_user[i] else '     '} {p[i]*1e6:8.3f}")
print(f"\nusers      median {np.median(p[is_user])*1e6:7.3f} uW   max {p[is_user].max()*1e6:7.3f}")
print(f"bystanders median {np.median(p[~is_user])*1e6:7.3f} uW   max {p[~is_user].max()*1e6:7.3f}")
print(f"ratio of medians  {np.median(p[is_user])/np.median(p[~is_user]):.2f}x")
print(f"overall median {np.median(p)*1e6:.3f} uW  p95 {np.percentile(p,95)*1e6:.3f} uW  spread {p.max()/p.min():.1f}x")
