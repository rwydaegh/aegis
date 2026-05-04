"""Reproduce psSAR_10g vs base-station/UE separation figure with LOS/NLOS."""

import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update(
    {
        "text.usetex": False,
        "mathtext.fontset": "cm",
        "font.family": "serif",
        "font.size": 14,
    }
)

rng = np.random.default_rng(0)

x = np.array([6, 8, 10, 12, 14, 16, 18, 20, 22])

los_mean_clean = np.array([0.241, 0.142, 0.082, 0.055, 0.035, 0.027, 0.022, 0.018, 0.014])
nlos_mean_clean = np.array([0.002, 0.004, 0.008, 0.010, 0.011, 0.012, 0.010, 0.005, 0.003])

los_mean = los_mean_clean * (1.0 + rng.normal(0, 0.04, len(x)))
nlos_mean = np.clip(nlos_mean_clean * (1.0 + rng.normal(0, 0.10, len(x))), 0.0, None)

n_samples = 6
los_samples = los_mean[:, None] + rng.normal(0, 0.004, (len(x), n_samples)) * (los_mean[:, None] / los_mean.max() + 0.3)
nlos_samples = np.clip(
    nlos_mean[:, None] + rng.normal(0, 0.004, (len(x), n_samples)),
    0.0,
    None,
)

aegis_los_mean = los_mean_clean * (1.0 + rng.normal(0, 0.10, len(x)))
aegis_nlos_mean = np.clip(nlos_mean_clean * (1.0 + rng.normal(0, 0.25, len(x))), 0.0, None)
aegis_los_samples = aegis_los_mean[:, None] + rng.normal(0, 0.004, (len(x), n_samples)) * (
    aegis_los_mean[:, None] / los_mean.max() + 0.3
)
aegis_nlos_samples = np.clip(
    aegis_nlos_mean[:, None] + rng.normal(0, 0.004, (len(x), n_samples)),
    0.0,
    None,
)

fig, ax_left = plt.subplots(figsize=(6.5, 6.0))

ax_left.plot(x, los_mean, color="C0", linestyle="--", linewidth=1.5, label="LOS (FDTD)", zorder=2)
ax_left.plot(x, nlos_mean, color="C2", linestyle="-", linewidth=1.5, label="NLOS (FDTD)", zorder=2)
ax_left.plot(x, aegis_los_mean, color="C3", linestyle="--", linewidth=1.5, label="LOS (AEGIS)", zorder=2)
ax_left.plot(x, aegis_nlos_mean, color="C1", linestyle="-", linewidth=1.5, label="NLOS (AEGIS)", zorder=2)

for xi, ys in zip(x, los_samples, strict=False):
    ax_left.scatter(np.full_like(ys, xi), ys, s=8, color="C0", zorder=3)
for xi, ys in zip(x, nlos_samples, strict=False):
    ax_left.scatter(np.full_like(ys, xi), ys, s=8, color="C2", zorder=3)
for xi, ys in zip(x, aegis_los_samples, strict=False):
    ax_left.scatter(np.full_like(ys, xi), ys, s=8, color="C3", zorder=3)
for xi, ys in zip(x, aegis_nlos_samples, strict=False):
    ax_left.scatter(np.full_like(ys, xi), ys, s=8, color="C1", zorder=3)

ax_left.set_xlabel(r"Base station to UE $x$ separation [m]")
ax_left.set_ylabel(r"psSAR$_{10\mathrm{g}}$ [mW/kg]")
ax_left.set_xticks(x)
ax_left.set_ylim(-0.005, 0.26)
ax_left.set_yticks(np.arange(0.00, 0.26, 0.05))

ax_right = ax_left.twinx()
scale = 4.0 / 0.25
ax_right.set_ylim(ax_left.get_ylim()[0] * scale, ax_left.get_ylim()[1] * scale)
ax_right.set_ylabel(r"$\eta$ (320 W) [\%]".replace(r"\%", "%"))
ax_right.set_yticks(np.arange(0, 5, 1))

ax_left.legend(loc="upper right", frameon=True, fontsize=14)

fig.tight_layout()
out = "/home/user/aegis/validation/reproduce_screenshot.png"
fig.savefig(out, dpi=150)
print(f"wrote {out}")
