"""Exact Mie sphere oracle: the doubly-curved cross-check for the p-pol question.

The cylinder cannot quantify the hard / p-pol curvature-polarization coupling
because a closed 2D cylinder resonates the slowly-decaying p-pol surface wave.
A sphere has double curvature and no 2D line resonance, so it is the clean
intermediate oracle between the cylinder and the real mesh.

Geometry: plane wave along +z, x-polarized. A surface point at polar angle
theta (from +z) has outward normal r_hat, so mu = n_hat . (-k_hat) = -cos theta:
the lit pole is theta = 180 deg (normal incidence), the terminator theta = 90 deg,
shadow theta < 90 deg. The incident E (along x) lies in the plane of incidence
for the phi = 0 cut (p-pol, E-plane) and perpendicular to it for phi = 90 deg
(s-pol, H-plane).

Observable: absorbed power per area = inward radial Poynting from the exterior
total field just outside r = a, P_abs = -(1/2) Re(E_theta conj(H_phi) -
E_phi conj(H_theta)). Fields come from miepython's near-field routine
(validated against the Mie Qabs canary), so there is no hand-rolled Mie bug.
"""

from __future__ import annotations

import miepython as mp
import numpy as np

from aegis.tissue.dielectric import SKIN_28GHZ as S

M = S.n_complex  # n - i k convention (miepython)


def sphere_surface_absorbed(x: float, theta: np.ndarray, phi: float):
    """Inward Poynting (absorbed power per area) just outside the sphere, vs theta.

    x = k0 a (size parameter). theta in radians. phi a scalar cut (0 = p-pol,
    pi/2 = s-pol). Returns an array the shape of theta.
    """
    lam0 = 2.0 * np.pi  # so k0 = 1
    d = 2.0 * x  # diameter in these units (a = x)
    r = x * (1.0 + 1e-4)  # just outside the surface
    th = np.atleast_1d(theta).astype(float)
    ph = np.full_like(th, phi)
    rr = np.full_like(th, r)
    E, H = mp.eh_near(lam0, d, M, 1.0, rr, th, ph, include_incident=True)
    # spherical components (3, ...): index 0=r, 1=theta, 2=phi
    Et, Ep = E[1], E[2]
    Ht, Hp = H[1], H[2]
    S_r_out = 0.5 * np.real(Et * np.conj(Hp) - Ep * np.conj(Ht))  # outward radial Poynting
    return -S_r_out  # inward = absorbed (passive sphere)


def fresnel_TsTp(mu):
    n2 = M**2
    xi = np.sqrt(n2 - (1 - mu**2))
    rs = (mu - xi) / (mu + xi)
    rp = (n2 * mu - xi) / (n2 * mu + xi)
    return 1 - np.abs(rs) ** 2, 1 - np.abs(rp) ** 2


def go_recovery_test():
    """Does exact/GO -> const (clean) or stay erratic (resonance) as x grows?

    On the cylinder, p-pol was erratic (closed-loop resonance). The sphere has
    no such resonance, so both pols should converge. Prints exact/(T*mu) at
    fixed incidence vs x; a stable column means GO is recovered (the constant
    absorbs the field-normalisation factor).
    """
    incs = [30, 50, 70]  # incidence angle in degrees (0 = normal)
    print("sphere exact/(T*mu) at fixed incidence vs x (stable column => clean, no resonance)")
    print(f"  {'x':>6s} | " + " | ".join(f"s {i}d    p {i}d " for i in incs))
    for x in (30, 60, 120, 240, 480):
        cells = []
        for inc in incs:
            th = np.deg2rad(180 - inc)  # lit side; mu = -cos(theta) = cos(inc)
            mu = np.cos(np.deg2rad(inc))
            Ts, Tp = fresnel_TsTp(mu)
            P_s = sphere_surface_absorbed(x, np.array([th]), np.pi / 2)[0]  # s-pol cut
            P_p = sphere_surface_absorbed(x, np.array([th]), 0.0)[0]  # p-pol cut
            cells.append(P_s / (Ts * mu))
            cells.append(P_p / (Tp * mu))
        print(f"  {x:>6d} | " + " | ".join(f"{cells[2*j]:6.3f} {cells[2*j+1]:6.3f}" for j in range(len(incs))))


def lit_profile():
    """Curvature-polarization ratio across the lit hemisphere at one large x.

    exact/(flat-Fresnel GO), anchored to the exact in the near-normal region so
    the field normalisation drops out. Tells us how much the doubly-curved
    surface departs from flat Fresnel per polarization.
    """
    x = 240.0
    inc = np.linspace(2, 86, 43)  # incidence angle
    th = np.deg2rad(180 - inc)
    mu = np.cos(np.deg2rad(inc))
    Ts, Tp = fresnel_TsTp(mu)
    Ps = sphere_surface_absorbed(x, th, np.pi / 2)
    Pp = sphere_surface_absorbed(x, th, 0.0)
    # anchor each to exact at inc=10-25 deg (near normal, GO trustworthy)
    anch = (inc > 10) & (inc < 25)
    gs = Ts * mu
    gp = Tp * mu
    gs *= np.sum(gs[anch] * Ps[anch]) / np.sum(gs[anch] ** 2)
    gp *= np.sum(gp[anch] * Pp[anch]) / np.sum(gp[anch] ** 2)
    print(f"\nsphere lit-region exact/GO at x={x:.0f} (1.0 = flat Fresnel correct):")
    print(f"  {'inc(deg)':>8s} {'s-pol':>8s} {'p-pol':>8s}")
    for j in range(0, len(inc), 4):
        print(f"  {inc[j]:8.0f} {Ps[j]/gs[j]:8.3f} {Pp[j]/gp[j]:8.3f}")


def validate_total_absorbed():
    """Integrate surface Poynting over the sphere; compare to Qabs (sanity)."""
    x = 60.0
    th = np.linspace(1e-3, np.pi - 1e-3, 400)
    phs = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    # axisymmetric in neither; integrate over both. P_abs(theta,phi).
    TH, PH = np.meshgrid(th, phs, indexing="ij")
    E, H = mp.eh_near(2 * np.pi, 2 * x, M, 1.0, np.full(TH.size, x * (1 + 1e-4)),
                      TH.ravel(), PH.ravel(), include_incident=True)
    Et, Ep, Ht, Hp = E[1], E[2], H[1], H[2]
    Pabs = (-0.5 * np.real(Et * np.conj(Hp) - Ep * np.conj(Ht))).reshape(TH.shape)
    # integrate P_abs * a^2 sin(theta) dtheta dphi ; absorbed cross section = that / S_inc
    da = (x**2) * np.sin(TH)
    W = np.trapezoid(np.trapezoid(Pabs * da, phs, axis=1), th, axis=0)
    S_inc = 0.5  # |E0|^2/(2 Z) with miepython's Z=1 normalization (E0=1)
    Cabs = W / S_inc
    Qabs_mine = Cabs / (np.pi * x**2)
    qe, qs, _, _ = mp.efficiencies(M, 2 * x, 2 * np.pi)
    print(f"\ntotal-absorbed sanity at x={x:.0f}: Qabs(surface integral)={Qabs_mine:.4f}  "
          f"Qabs(miepython)={qe-qs:.4f}  ratio={Qabs_mine/(qe-qs):.3f}")
    print("  (ratio should be ~constant O(1); a clean number confirms the Poynting normalisation)")


if __name__ == "__main__":
    go_recovery_test()
    lit_profile()
    validate_total_absorbed()
