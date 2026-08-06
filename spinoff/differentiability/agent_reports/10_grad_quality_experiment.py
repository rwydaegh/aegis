"""Reproduction script for report 10 (red team: is the gradient of a wrong model
a useful gradient?).

Run with the repo venv:  .venv/bin/python spinoff/differentiability/agent_reports/10_grad_quality_experiment.py

It computes, for a lossy-dielectric sphere (exact Mie via miepython) and infinite
cylinder (exact Bessel-Hankel series), the AEGIS physical-optics absorbed-power
density and its parameter gradients (jax.grad through the real AEGIS kernels),
versus the exact solution, as a function of distance to the shadow terminator.

Three headline findings are printed:
  A. value error: ~0-1% deep lit, 3-16x local under-prediction near the terminator.
  B. incidence gradient d ln P/d inc: correct sign everywhere, but 2-20x too steep
     near the terminator; the Fock gate reduces but does not remove the over-steepness.
  C. size/frequency gradient d ln(total absorbed power)/d(kR): SIGN-FLIPPED at every
     frequency for both sphere and cylinder. Exact absorbed power approaches the GO
     limit from above (grad<0), AEGIS approaches from below (grad>0). The value
     converges (Mie canary passes); the derivative points the wrong way.
"""
import os
os.environ["AEGIS_ARRAY_BACKEND"] = "jax"
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "studies", "diffraction"))

import numpy as np
import jax
import jax.numpy as jnp
import miepython as mp

from aegis.kernels import fock
from aegis.kernels._base import fresnel_weights
from aegis.tissue.dielectric import SKIN_28GHZ as S
from aegis.tissue.fresnel import T0 as T0_fn
from aegis.constants import C_0
from cylinder_oracle import dielectric_cylinder_surface_field

n_tilde = complex(S.n_complex)
T0 = float(T0_fn(n_tilde))
FREQ = 28e9
k0 = 2 * np.pi * FREQ / C_0
eta = 1.0 / n_tilde


# --- AEGIS per-point absorbed density (validated == engine.compute .sab) --------
def aegis_density(mu, x, qh, geom, level):
    Ccurv = 1.0 if geom == "cyl" else 2.0  # H/k0 = 1/x (cyl) or 2/x (sph)
    if level == 3:
        _, _, Tavg = fresnel_weights(jnp.asarray(mu), n_tilde)
        return Tavg * jnp.maximum(mu, 0.0)
    R = x / k0
    g = fock.fock_local(mu, R, FREQ, 0.5, 0.5, None, qh)
    _, _, Tavg = fresnel_weights(jnp.asarray(mu), n_tilde)
    return Tavg * g + T0 * (Ccurv / x) * g**2


# --- exact truth ----------------------------------------------------------------
def exact_cyl(x, inc_deg):
    inc = np.deg2rad(np.atleast_1d(inc_deg))
    phi = np.pi / 2 + (np.pi / 2 - inc)
    return 0.5 * (dielectric_cylinder_surface_field(x, n_tilde, phi, "TM")
                  + dielectric_cylinder_surface_field(x, n_tilde, phi, "TE"))


def qabs_mie(x):
    qe, qs, _, _ = mp.efficiencies(n_tilde, 2 * x, 2 * np.pi)
    return qe - qs


# --- A + B: value ratio and incidence gradient vs distance to terminator --------
def part_AB(x=40.0):
    qh = fock.fock_impedance_param(eta, float(np.clip(x, 4, 2048)), "hard")
    incs = np.array([20., 40., 55., 65., 72., 78., 82., 85., 87., 88.5])
    inc_fit = np.array([12., 16., 20., 24.])
    S6f = np.array([float(aegis_density(float(np.cos(np.deg2rad(i))), x, qh, "cyl", 6)) for i in inc_fit])
    C = np.sum(S6f * exact_cyl(x, inc_fit)) / np.sum(exact_cyl(x, inc_fit) ** 2)
    print(f"\n[A,B] cylinder x=kR={x:.0f}  (value ratio, incidence log-gradient)")
    print(" d2term  value_ratio | dlnP/dinc  exact    L3(ReLU)   L6(Fock)   over-steep L6")
    for inc in incs:
        mu = float(np.cos(np.deg2rad(inc)))
        P0 = exact_cyl(x, inc)[0]
        ex = (exact_cyl(x, inc + 1e-2)[0] - exact_cyl(x, inc - 1e-2)[0]) / (2 * np.deg2rad(1e-2)) / P0
        S6 = float(aegis_density(mu, x, qh, "cyl", 6))
        l3 = float(jax.grad(lambda ir: aegis_density(jnp.cos(ir), x, qh, "cyl", 3))(float(np.deg2rad(inc)))) \
            / float(aegis_density(mu, x, qh, "cyl", 3))
        l6 = float(jax.grad(lambda ir: aegis_density(jnp.cos(ir), x, qh, "cyl", 6))(float(np.deg2rad(inc)))) / S6
        print(f" {90 - inc:5.1f}    {S6 / (C * P0):6.3f}    | {ex:8.3f} {l3:9.2f} {l6:9.2f}     {l6 / ex:5.1f}x")


# --- C: size/frequency gradient of the aggregate observable ---------------------
def part_C():
    phi = np.linspace(0, 2 * np.pi, 3001, endpoint=False)
    mu_np = -np.cos(phi)

    def W_cyl_exact(x):
        P = 0.5 * (dielectric_cylinder_surface_field(x, n_tilde, phi, "TM")
                   + dielectric_cylinder_surface_field(x, n_tilde, phi, "TE"))
        return np.trapezoid(P, phi)

    def W_cyl_aegis(x, qh):
        g = fock.fock_local(jnp.asarray(mu_np), x / k0, FREQ, 0.5, 0.5, None, qh)
        _, _, Tavg = fresnel_weights(jnp.asarray(mu_np), n_tilde)
        return jnp.trapezoid(Tavg * g + T0 * (1.0 / x) * g**2, jnp.asarray(phi))

    print("\n[C] SIGN of the size/frequency gradient of TOTAL absorbed power")
    print("  geometry  x=kR   value(aegis/exact)   dln/d(kR) exact   dln/d(kR) aegis   verdict")
    for x in [40., 80., 160., 320.]:
        qh = fock.fock_impedance_param(eta, float(np.clip(x, 4, 2048)), "hard")
        We, Wa = W_cyl_exact(x), float(W_cyl_aegis(x, qh))
        hx = x * 1e-3
        de = (W_cyl_exact(x + hx) - W_cyl_exact(x - hx)) / (2 * hx) / We
        da = float(jax.grad(lambda xv: W_cyl_aegis(xv, qh))(x)) / Wa
        print(f"  cylinder {x:5.0f}      {Wa / We:5.3f}        {de:+12.5f}   {da:+12.5f}   "
              f"{'SIGN FLIP' if de * da < 0 else 'ok'}")
    # sphere via exact Mie Qabs
    def W_sph_aegis(x, qh):
        th = np.linspace(1e-3, np.pi - 1e-3, 1500)
        mu = -np.cos(th)
        g = fock.fock_local(jnp.asarray(mu), x / k0, FREQ, 0.5, 0.5, None, qh)
        _, _, Tavg = fresnel_weights(jnp.asarray(mu), n_tilde)
        return jnp.trapezoid((Tavg * g + T0 * (2.0 / x) * g**2) * jnp.asarray(np.sin(th)), jnp.asarray(th))
    for x in [40., 80., 160.]:
        qh = fock.fock_impedance_param(eta, float(np.clip(x, 4, 2048)), "hard")
        Qe = qabs_mie(x)
        hx = x * 1e-3
        de = (qabs_mie(x + hx) - qabs_mie(x - hx)) / (2 * hx) / Qe
        da = float(jax.grad(lambda xv: W_sph_aegis(xv, qh))(x)) / float(W_sph_aegis(x, qh))
        print(f"  sphere   {x:5.0f}        n/a        {de:+12.5f}   {da:+12.5f}   "
              f"{'SIGN FLIP' if de * da < 0 else 'ok'}")


if __name__ == "__main__":
    print("=" * 84)
    print("Report 10: gradient quality of AEGIS physical optics vs exact Mie / cylinder")
    print("skin at 28 GHz, n_tilde =", n_tilde)
    print("=" * 84)
    part_AB(40.0)
    part_AB(160.0)
    part_C()
