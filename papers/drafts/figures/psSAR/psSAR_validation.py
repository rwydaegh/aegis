"""
Validation figure for the closed-form cube psSAR_10g letter.

The closed form, valid in the thin-skin limit alpha L >> 1, is

    <SAR>_cube = (S_inc T_0 / (rho_m L)) * (|k_x| + |k_y| + |k_z|).

In the face-flush configuration that dominates regulatory practice
(cube placed with one face tangent to the body surface), the sum
contracts to the single component |k_z|; in the tilted configuration
the cancellation between cos(gamma) in S_ab and 1/cos(gamma) in
patch area returns the same constant.

Two panels:

(a) Closed form vs surface integral as a function of body tilt
    gamma at axis-aligned k_hat = -z_hat. Both are flat at the
    energy-conservation value S_inc T_0 / (rho_m L), confirming
    the cancellation noted in the source.

(b) The dependence of the closed-form psSAR on incidence direction
    in the face-flush case. The ridge follows |k_z| = cos(theta),
    superimposed on direct integration markers that match to
    machine precision.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/user/aegis/theory/scripts")
import matplotlib.pyplot as plt  # noqa: E402
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

# physical constants (skin at 28 GHz)
RHO_M = 1000.0
M_CUBE = 0.01
L_CUBE = (M_CUBE / RHO_M) ** (1.0 / 3.0)
T0 = 0.539
S_INC = 10.0


def closed_form_full(khat: np.ndarray) -> float:
    return S_INC * T0 / (RHO_M * L_CUBE) * float(np.sum(np.abs(khat)))


def reference_surface_integral(
    khat: np.ndarray, nhat: np.ndarray, n_grid: int = 250
) -> float:
    """
    Brute-force evaluation of the cube psSAR via the surface integral
    int_{Sigma cap C} S_ab dA / m, body surface plane through cube
    centre.
    """
    axis = int(np.argmax(np.abs(nhat)))
    u_axes = [a for a in (0, 1, 2) if a != axis]
    L = L_CUBE
    edges = np.linspace(-L / 2.0, L / 2.0, n_grid + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    du = L / n_grid
    U, V = np.meshgrid(centres, centres, indexing="ij")

    r = np.zeros((n_grid, n_grid, 3))
    r[..., u_axes[0]] = U
    r[..., u_axes[1]] = V
    r[..., axis] = -(nhat[u_axes[0]] * U + nhat[u_axes[1]] * V) / nhat[axis]
    inside = np.all(np.abs(r) <= L / 2.0 + 1e-12, axis=-1)

    cos_axis = abs(nhat[axis])
    dA = du * du / cos_axis

    mu = float(np.dot(nhat, -khat))
    if mu <= 0.0:
        return 0.0
    Sab = S_INC * T0 * mu
    P_abs = float(Sab * dA * inside.sum())
    m_tissue = RHO_M * L ** 3
    return P_abs / m_tissue


# ---------- panel (a): tilt sweep, k_hat = -z ----------
gammas = np.linspace(0.0, np.deg2rad(40.0), 41)
khat_a = np.array([0.0, 0.0, -1.0])
cf_a = np.zeros_like(gammas)
ref_a = np.zeros_like(gammas)
# break the cancellation explicitly to show the components
sab_a = np.zeros_like(gammas)
patch_factor_a = np.zeros_like(gammas)
for i, g in enumerate(gammas):
    nhat = np.array([np.sin(g), 0.0, np.cos(g)])
    cf_a[i] = closed_form_full(khat_a)
    ref_a[i] = reference_surface_integral(khat_a, nhat, n_grid=400)
    sab_a[i] = S_INC * T0 * abs(float(np.dot(nhat, -khat_a)))  # cos gamma
    patch_factor_a[i] = 1.0 / abs(nhat[2])  # 1 / cos gamma

# ---------- panel (b): polar plot of closed form vs theta ----------
n_th = 60
n_ph = 1
thetas = np.linspace(0.0, np.deg2rad(89.0), n_th)
nhat_b = np.array([0.0, 0.0, 1.0])
cf_b_phi0 = np.zeros(n_th)
ref_b_phi0 = np.zeros(n_th)
cf_b_phi45 = np.zeros(n_th)
ref_b_phi45 = np.zeros(n_th)
for i, th in enumerate(thetas):
    # phi = 0
    khat = -np.array([np.sin(th), 0.0, np.cos(th)])
    cf_b_phi0[i] = S_INC * T0 / (RHO_M * L_CUBE) * abs(khat[2])
    ref_b_phi0[i] = reference_surface_integral(khat, nhat_b, n_grid=80)
    # phi = 45 deg (along x = y diagonal)
    khat = -np.array([
        np.sin(th) * np.cos(np.pi / 4),
        np.sin(th) * np.sin(np.pi / 4),
        np.cos(th)
    ])
    cf_b_phi45[i] = S_INC * T0 / (RHO_M * L_CUBE) * abs(khat[2])
    ref_b_phi45[i] = reference_surface_integral(khat, nhat_b, n_grid=80)

# ---------- plotting ----------
apply_monograph_style(mode="pdf")
fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.45))

# panel (a): show two components and their product
ax = axes[0]
gd = np.rad2deg(gammas)
val0 = S_INC * T0 / (RHO_M * L_CUBE)
ax.plot(gd, sab_a / S_INC / T0,
        "--", lw=1.2, color="C2",
        label=r"$\langle S_{\mathrm{ab}}\rangle/(S_{\mathrm{inc}}T_0)=\cos\gamma$")
ax.plot(gd, patch_factor_a, ":", lw=1.2, color="C1",
        label=r"$A_\gamma / L^2 = 1/\cos\gamma$")
ax.plot(gd, ref_a / val0,
        "o", ms=3.0, color="C0",
        label=r"surface integral / const")
ax.plot(gd, cf_a / val0,
        "-", lw=1.4, color="C3",
        label=r"closed form / const")
ax.set_xlabel(r"body tilt $\gamma$ (deg)")
ax.set_ylabel(r"normalised quantity")
ax.set_title(r"(a) tilt cancellation, $\hat{\mathbf{k}}=-\hat{\mathbf{z}}$")
ax.set_ylim(0.0, 1.6)
ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.32),
          frameon=False, fontsize=6.5)

# panel (b): theta dependence at two azimuths
ax = axes[1]
td = np.rad2deg(thetas)
ax.plot(td, np.cos(thetas), "-", lw=1.4, color="C3",
        label=r"$|k_z|=\cos\theta$")
ax.plot(td, ref_b_phi0 / val0, "o", ms=2.5, color="C0",
        label=r"reference, $\phi=0$")
ax.plot(td, ref_b_phi45 / val0, "s", ms=2.5, color="C2", alpha=0.7,
        label=r"reference, $\phi=45^\circ$")
ax.set_xlabel(r"polar angle $\theta$ (deg)")
ax.set_ylabel(r"$\langle\mathrm{SAR}\rangle_{\mathrm{cube}}/(S_{\mathrm{inc}}T_0/(\rho_{\mathrm{m}}L))$")
ax.set_title(r"(b) face-flush, hemisphere of $\hat{\mathbf{k}}$")
ax.legend(loc="upper right", frameon=False, fontsize=7.5)
ax.set_xlim(0, 90)
ax.set_ylim(0.0, 1.05)

fig.tight_layout()
out_pdf = Path("/home/user/aegis/papers/drafts/figures/psSAR/psSAR_validation.pdf")
out_png = out_pdf.with_suffix(".png")
fig.savefig(out_pdf)
fig.savefig(out_png, dpi=150)
print(f"Wrote {out_pdf}")
print(f"Wrote {out_png}")

# numerical summary
err_a = (cf_a - ref_a) / ref_a * 100
err_b0 = (cf_b_phi0 - ref_b_phi0) / np.where(ref_b_phi0 > 0, ref_b_phi0, np.nan) * 100
err_b45 = (cf_b_phi45 - ref_b_phi45) / np.where(ref_b_phi45 > 0, ref_b_phi45, np.nan) * 100
print(f"Panel (a) max |err| % = {np.max(np.abs(err_a)):.3e}")
print(f"Panel (b) phi=0 max |err| % = {np.nanmax(np.abs(err_b0)):.3e}")
print(f"Panel (b) phi=45 max |err| % = {np.nanmax(np.abs(err_b45)):.3e}")
