"""Quick visualization of the sphere_apd_full.npz the user uploaded.

Three-panel sanity check:
  1. 3D phantom (sphere) painted by APD per vertex.
  2. APD vs cos(incidence angle) - should be linear inside the lit hemisphere
     (cosine-law absorption) and exactly 0 in shadow.
  3. Histogram of non-zero APD values.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

NPZ = "/home/user/aegis/validation/sphere_apd_full.npz"
OUT = "/home/user/aegis/validation/sphere_apd_probe_viz.png"
ETA0 = 376.730313668
SINC = 1.0 / (2 * ETA0)  # at E = 1 V/m

d = np.load(NPZ)
verts = d["vertices_m"]
faces = d["faces"]
apd = d["apd_w_m2"]  # per-vertex (kNode), W/m²

# Map per-vertex → per-triangle by averaging the 3 vertex values
apd_face = apd[faces].mean(axis=1)

# Recover the wave direction: peak APD vertex points away from source, so
# k_hat ≈ -n_out_peak. Empirically we found k = +z to give corr=+0.996.
center = verts.mean(axis=0)
n_out = (verts - center) / np.linalg.norm(verts - center, axis=1, keepdims=True)
k_hat = np.array([0.0, 0.0, 1.0])
mu = -n_out @ k_hat

# ---- Figure ---------------------------------------------------------------
fig = plt.figure(figsize=(15, 5.5))

# Panel 1: 3D sphere painted by APD
ax1 = fig.add_subplot(1, 3, 1, projection="3d")
norm = plt.Normalize(vmin=0, vmax=float(apd.max()))
fc = cm.viridis(norm(apd_face))
poly = Poly3DCollection(verts[faces], facecolors=fc, edgecolors="none")
ax1.add_collection3d(poly)
ax1.set_xlim(verts[:, 0].min(), verts[:, 0].max())
ax1.set_ylim(verts[:, 1].min(), verts[:, 1].max())
ax1.set_zlim(verts[:, 2].min(), verts[:, 2].max())
try:
    ax1.set_box_aspect(np.ptp(verts, axis=0))
except AttributeError:
    pass
ax1.view_init(elev=10, azim=-70)
ax1.set_title(f"Sphere APD (per-vertex)\nR=2 cm, V={len(verts)}, k=+z")
sm = cm.ScalarMappable(norm=norm, cmap="viridis")
sm.set_array([])
fig.colorbar(sm, ax=ax1, shrink=0.55, fraction=0.04, label="APD [W/m²]")

# Panel 2: APD vs cos(incidence)
ax2 = fig.add_subplot(1, 3, 2)
ax2.scatter(mu, apd, s=2, alpha=0.3, c=apd, cmap="viridis")
# Best-fit line through the lit half (mu > 0)
front = mu > 0.01
slope = np.sum(apd[front] * mu[front]) / np.sum(mu[front] ** 2)
mu_fit = np.linspace(0, 1, 100)
ax2.plot(mu_fit, slope * mu_fit, "r--", lw=1.5, label=f"linear fit (slope = {slope:.3e} W/m²)")
ax2.axvline(0, color="k", lw=0.5, alpha=0.5)
ax2.set_xlabel(r"$\mu = -\hat{n} \cdot \hat{k}$  (cos incidence)")
ax2.set_ylabel("APD [W/m²]")
corr = float(np.corrcoef(mu[front], apd[front])[0, 1])
ax2.set_title(f"APD vs cos(incidence)   corr={corr:+.4f}")
ax2.legend(loc="lower right", fontsize=9)
ax2.grid(alpha=0.3)

# Panel 3: histogram + reference markers
ax3 = fig.add_subplot(1, 3, 3)
nonzero = apd[apd > 1e-8]
ax3.hist(nonzero * 1e3, bins=80, color="C0", alpha=0.75)
ax3.axvline(SINC * 1e3, color="g", lw=1.5, ls="--", label=f"Sinc at E=1V/m = {SINC * 1e3:.3f} mW/m²")
ax3.axvline(apd.max() * 1e3, color="r", lw=1.5, ls=":", label=f"peak APD = {apd.max() * 1e3:.3f} mW/m²")
ax3.set_xlabel("APD [mW/m²]")
ax3.set_ylabel("# vertices")
ax3.set_title(f"APD histogram (lit fraction = {(apd > 1e-8).mean():.2%})")
ax3.legend(fontsize=9)
ax3.grid(alpha=0.3)

fig.suptitle(
    'Sim4Life GenericSAPDEvaluator → Outputs["APD(x,y,z,f0)"]   (40 mm sphere, kNode field)', fontsize=12, y=1.01
)
fig.tight_layout()
fig.savefig(OUT, dpi=130, bbox_inches="tight")
print(f"wrote {OUT}")
print(f"\nPhysics summary:")
print(f"  R = 2 cm, V = {len(verts)} nodes, T = {len(faces)} triangles")
print(f"  k_hat = +z (wave propagates upward)")
print(f"  Lit fraction = {(apd > 1e-8).mean():.3f} (expected 0.5 for plane wave on sphere)")
print(f"  APD peak  = {apd.max() * 1e3:.3f} mW/m²")
print(f"  Sinc at E=1V/m = {SINC * 1e3:.3f} mW/m²")
print(f"  APD/Sinc peak = {apd.max() / SINC:.3f}")
print(f"  Linear regression slope (APD ~ slope·mu, lit half): {slope:.3e} W/m²")
print(f"  → effective T_eff = slope/Sinc = {slope / SINC:.3f}")
