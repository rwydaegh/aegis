"""Exact dielectric-cylinder oracle for the diffraction model question.

A limb is, to leading order, a circular dielectric cylinder. The 2D
plane-wave scattering by a homogeneous dielectric cylinder has a closed-form
Bessel-Hankel series solution, so the surface absorbed power around the
cylinder, from the lit point through the penumbra into the deep shadow, is
known exactly. That makes it the perfect judge for the question the surface
law cannot answer by itself: does a limb's shadow edge behave like a knife
edge (transition width scaling as (kR)^{-1/2}) or like Fock diffraction by a
smooth convex body (width scaling as (kR)^{-1/3})?

The test is a similarity collapse. Fock theory predicts the normalised
surface field is a universal function of xi = (kR/2)^{1/3} * theta, where
theta is the signed angle past the geometric terminator. If the exact curves
for many kR collapse onto a single curve when plotted against xi, but spread
out when plotted against the knife-edge variable zeta = theta * sqrt(kR),
then the limb is Fock, not knife-edge. We run that test for both
polarisations (TM_z = soft, TE_z = hard) with real skin permittivity.

Conventions: time factor e^{-i w t}; outgoing waves are H_n^{(1)}. Incidence
travels +x (k_hat = +x). A surface point at azimuth phi has outward normal
(cos phi, sin phi); the projected-area cosine is mu = n_hat . (-k_hat) =
-cos phi. The geometric terminator (mu = 0) is at phi = pi/2; we measure the
signed angle past it as theta = phi - pi/2 (theta > 0 lit, toward phi = pi;
theta < 0 into the lower shadow), so mu = sin theta and GO power ~ max(sin theta, 0).
"""

from __future__ import annotations

import numpy as np
from scipy.special import h1vp, hankel1, jv, jvp


def _log_deriv_J(z: complex, nmax: int) -> np.ndarray:
    """Stable D_n(z) = J_n'(z)/J_n(z) for n=0..nmax via downward recurrence.

    Uses q_n = J_n(z)/J_{n-1}(z) computed downward (q_n = 1/(2n/z - q_{n+1})),
    then D_n = n/z - q_{n+1}. Valid for large complex z (lossy interior), where
    direct evaluation of J_n(z) overflows. D_{-n} = D_n.
    """
    start = nmax + 15 + int(np.abs(z))
    qs = np.zeros(start + 2, dtype=complex)
    q = 0.0 + 0.0j
    for n in range(start, 0, -1):
        q = 1.0 / (2.0 * n / z - q)
        qs[n] = q  # J_n/J_{n-1}
    D = np.array([n / z - qs[n + 1] for n in range(nmax + 1)], dtype=complex)
    return D


def dielectric_cylinder_surface_field(ka: float, n_complex: complex, phi: np.ndarray, pol: str):
    """Exact absorbed power per area around a lossy dielectric cylinder, vs azimuth.

    The absorbed power per unit surface area is the inward radial Poynting flux,
    P_abs(phi) ~ Im(Psi * conj(d_rho Psi)) from the EXTERIOR total field at
    rho = a (stable: argument k0 a is real). Psi = E_z (TM, soft) or H_z (TE,
    hard). The interior enters only through the stable log derivative
    D_n = J_n'(k1 a)/J_n(k1 a). This is exactly the quantity AEGIS's S_ab models.
    """
    k0a = ka
    k1a = n_complex * ka
    N = int(ka + 14 * max(ka, 1.0) ** (1.0 / 3.0) + 25)
    ns = np.arange(-N, N + 1)
    absn = np.abs(ns)

    Jn0 = jv(ns, k0a)
    Jp0 = jvp(ns, k0a)
    Hn0 = hankel1(ns, k0a)
    Hp0 = h1vp(ns, k0a)
    Dn = _log_deriv_J(k1a, N)[absn]  # D_{-n} = D_n

    # Boundary admittance g: TM uses k1 D, TE uses (k1/eps_r) D = (k0/n) D.
    #   k0(J0'+bH0')/(J0+bH0) = g  ->  b = (g J0 - k0 J0')/(k0 H0' - g H0)
    g = (k1a * Dn) if pol == "TM" else ((k0a / n_complex) * Dn)
    b = (g * Jn0 - k0a * Jp0) / (k0a * Hp0 - g * Hn0)

    e = np.exp(1j * np.outer(phi, ns))
    psi_c = (1j ** ns) * (Jn0 + b * Hn0)
    dpsi_c = (1j ** ns) * (Jp0 + b * Hp0)  # d/d(k0 rho); common k0 factor drops in shape
    Psi = (psi_c[None, :] * e).sum(axis=1)
    dPsi = (dpsi_c[None, :] * e).sum(axis=1)
    return np.imag(Psi * np.conj(dPsi))  # inward Poynting ~ absorbed power per area


def pec_cylinder_surface_field(ka: float, phi: np.ndarray, pol: str):
    """Exact surface field on a PEC cylinder (the textbook Fock case).

    TM (soft, E_z=0): observable is the surface current ~ |dE_z/drho|^2, the
    soft Fock current function. TE (hard, dH_z/drho=0): observable is the
    surface field |H_z(a)|^2, the hard Fock function. No interior field.
    """
    N = int(ka + 12 * max(ka, 1.0) ** (1.0 / 3.0) + 20)
    ns = np.arange(-N, N + 1)
    Jn = jv(ns, ka)
    Jp = jvp(ns, ka)
    Hn = hankel1(ns, ka)
    Hp = h1vp(ns, ka)
    if pol == "TM":
        # E_z = sum i^n [J + b H]; b = -J/H. Surface current ~ d/drho E_z ~ k(J' + b H').
        b = -Jn / Hn
        coeff = (1j ** ns) * ka * (Jp + b * Hp)
        f = (coeff[None, :] * np.exp(1j * np.outer(phi, ns))).sum(axis=1)
        return np.abs(f) ** 2
    else:
        # H_z = sum i^n [J + b H]; Neumann b = -J'/H'. Observable |H_z(a)|^2.
        b = -Jp / Hp
        coeff = (1j ** ns) * (Jn + b * Hn)
        f = (coeff[None, :] * np.exp(1j * np.outer(phi, ns))).sum(axis=1)
        return np.abs(f) ** 2


def go_anchored_gate(P, theta, lit_lo=25.0, lit_hi=40.0):
    """Convert an exact surface-power curve to a GO-anchored gate g(theta).

    In the deep-lit region GO holds: P -> C * sin(theta). Fit C there, then
    g = P / (C * sin theta) tends to 1 in the lit region and 0 in shadow.
    """
    lit = (theta > np.deg2rad(lit_lo)) & (theta < np.deg2rad(lit_hi))
    C = np.median(P[lit] / np.sin(theta[lit]))
    with np.errstate(invalid="ignore", divide="ignore"):
        g = P / (C * np.sin(np.maximum(theta, 1e-6)))
    return g, C


def make_figures():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.special import erf

    from aegis.tissue.dielectric import SKIN_28GHZ as S

    n_complex = S.n_complex
    kR_list = [10, 20, 40, 80, 160]
    theta = np.deg2rad(np.linspace(-35, 40, 1201))
    phi = np.pi / 2 + theta
    cmap = plt.cm.viridis(np.linspace(0, 0.9, len(kR_list)))

    # Columns: (TM vs xi), (TE vs xi), (TM vs zeta). Rows: PEC, skin.
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for row, (label, solver) in enumerate(
        [("PEC", lambda kR, ph, pol: pec_cylinder_surface_field(kR, ph, pol)),
         ("skin", lambda kR, ph, pol: dielectric_cylinder_surface_field(kR, n_complex, ph, pol))]
    ):
        for ci, (pol, xvar, xlabel) in enumerate(
            [("TM", "xi", r"$\xi=(kR/2)^{1/3}\,\theta_{shadow}$"),
             ("TE", "xi", r"$\xi=(kR/2)^{1/3}\,\theta_{shadow}$"),
             ("TM", "zeta", r"$\zeta=\sqrt{kR}\,\theta_{shadow}$")]
        ):
            ax = axes[row, ci]
            for c, kR in enumerate(kR_list):
                P = solver(kR, phi, pol)
                g, _ = go_anchored_gate(P, theta)
                th_sh = -theta  # +into shadow
                x = (kR / 2) ** (1 / 3) * th_sh if xvar == "xi" else np.sqrt(kR) * th_sh
                ax.plot(x, g, color=cmap[c], lw=1.3, label=f"kR={kR}")
            # overlay current GeLU gate (sigma=(kR)^-1/2 in mu) for the largest kR
            kR = kR_list[-1]
            mu = np.sin(theta)
            sig = (kR) ** (-0.5)
            gelu = 0.5 * (1 + erf(mu / sig))
            th_sh = -theta
            xg = (kR / 2) ** (1 / 3) * th_sh if xvar == "xi" else np.sqrt(kR) * th_sh
            ax.plot(xg, gelu, "r--", lw=1.6, label="GeLU (current)")
            ax.set_xlim(-2, 4)
            ax.set_ylim(-0.05, 1.5)
            ax.axhline(0.5, color="gray", lw=0.5, ls=":")
            ax.axvline(0, color="gray", lw=0.5, ls=":")
            ax.set_title(f"{label}  {pol}  (gate vs {xvar})")
            ax.set_xlabel(xlabel)
            if ci == 0:
                ax.set_ylabel("GO-anchored gate g")
            if row == 0 and ci == 0:
                ax.legend(fontsize=7, loc="upper right")
    fig.suptitle("Diffraction model discrimination: exact cylinder gate vs Fock and knife scalings", fontsize=12)
    fig.tight_layout()
    out = "studies/diffraction/cylinder_collapse.png"
    fig.savefig(out, dpi=110)
    print("wrote", out)


def decay_analysis():
    """Model-free discriminator: the deep-shadow exponential decay rate.

    Creeping-wave theory predicts P_abs(theta_sh) ~ exp(-sqrt3 q1 (kR/2)^{1/3} theta_sh)
    in the shadow. So:
      (1) the decay slope scales as (kR)^{1/3} (Fock), not (kR)^{1/2} (knife);
      (2) the soft(TM)/hard(TE) slope ratio is q1_soft/q1_hard = 2.338/1.019 = 2.295
          for PEC, shifted by the surface impedance for skin.
    No GO-anchoring, no gate fitting: just fit the log-linear shadow decay.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from aegis.tissue.dielectric import SKIN_28GHZ as S

    n_complex = S.n_complex
    kR_list = [10, 20, 40, 80, 160, 320]
    # Shadow window: past the penumbra, before the back point (theta_sh=90) where
    # the two terminators' creeping waves meet. Fit where ln(P) is linear.
    th_sh = np.deg2rad(np.linspace(8, 45, 400))
    phi = np.pi / 2 - th_sh  # into the lower shadow (phi < pi/2)

    def slope(kR, pol, kind):
        if kind == "PEC":
            P = pec_cylinder_surface_field(kR, phi, pol)
        else:
            P = np.abs(dielectric_cylinder_surface_field(kR, n_complex, phi, pol))
        y = np.log(np.maximum(P, 1e-300))
        # robust linear fit over the central, most-linear half of the window
        lo, hi = len(th_sh) // 4, 3 * len(th_sh) // 4
        A = np.polyfit(th_sh[lo:hi], y[lo:hi], 1)
        return -A[0]  # decay slope (1/rad), positive

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    # Panel 1: ln P vs theta_sh, skin, both pols, a few kR
    ax = axes[0]
    cmap = plt.cm.viridis(np.linspace(0, 0.85, len(kR_list)))
    for c, kR in enumerate(kR_list):
        for pol, ls in (("TM", "-"), ("TE", "--")):
            P = np.abs(dielectric_cylinder_surface_field(kR, n_complex, phi, pol))
            ax.plot(np.rad2deg(th_sh), np.log(P / P[0]), ls, color=cmap[c], lw=1.2,
                    label=f"kR={kR} {pol}" if kR in (10, 320) else None)
    ax.set_xlabel("angle into shadow (deg)")
    ax.set_ylabel("ln P_abs (normalised)")
    ax.set_title("skin: shadow decay (solid=TM soft, dash=TE hard)")
    ax.legend(fontsize=7)

    # Panel 2: decay slope vs kR, log-log, with (kR)^1/3 and (kR)^1/2 references
    ax = axes[1]
    kk = np.array(kR_list, float)
    for kind, mk in (("PEC", "o"), ("skin", "s")):
        for pol, col in (("TM", "C0"), ("TE", "C3")):
            s = np.array([slope(kR, pol, kind) for kR in kR_list])
            ax.loglog(kk, s, mk + "-", color=col, ms=5,
                      label=f"{kind} {pol}", alpha=0.8 if kind == "skin" else 1.0,
                      mfc="none" if kind == "skin" else col)
    s0 = slope(kR_list[0], "TM", "PEC")
    ax.loglog(kk, s0 * (kk / kk[0]) ** (1 / 3), "k-", lw=1, label="(kR)^1/3 (Fock)")
    ax.loglog(kk, s0 * (kk / kk[0]) ** (1 / 2), "k:", lw=1, label="(kR)^1/2 (knife)")
    ax.set_xlabel("kR")
    ax.set_ylabel("shadow decay slope (1/rad)")
    ax.set_title("decay slope scaling: Fock vs knife")
    ax.legend(fontsize=7)

    # Panel 3: soft/hard slope ratio vs kR (PEC -> 2.295; skin shifted)
    ax = axes[2]
    for kind, mk in (("PEC", "o-"), ("skin", "s--")):
        ratio = [slope(kR, "TM", kind) / slope(kR, "TE", kind) for kR in kR_list]
        ax.semilogx(kk, ratio, mk, label=kind)
    ax.axhline(2.295, color="k", lw=1, ls=":", label="PEC soft/hard = 2.295")
    ax.axhline(1.0, color="gray", lw=0.5)
    ax.set_xlabel("kR")
    ax.set_ylabel("TM/TE decay-slope ratio")
    ax.set_title("soft/hard polarization split")
    ax.legend(fontsize=8)
    ax.set_ylim(0.5, 3.0)

    fig.tight_layout()
    out = "studies/diffraction/cylinder_decay.png"
    fig.savefig(out, dpi=120)
    print("wrote", out)

    # Print the numbers and the log-log fitted exponent.
    print("\n=== shadow-decay scaling exponent (slope ~ (kR)^p; Fock p=1/3, knife p=1/2) ===")
    for kind in ("PEC", "skin"):
        for pol in ("TM", "TE"):
            s = np.array([slope(kR, pol, kind) for kR in kR_list])
            p = np.polyfit(np.log(kk), np.log(s), 1)[0]
            print(f"  {kind:4s} {pol}: fitted exponent p = {p:.3f}")
    print("\n=== soft/hard decay-slope ratio (PEC theory = 2.295) ===")
    for kind in ("PEC", "skin"):
        r = [slope(kR, "TM", kind) / slope(kR, "TE", kind) for kR in kR_list]
        print(f"  {kind:4s}: " + "  ".join(f"kR={kR}:{rr:.2f}" for kR, rr in zip(kR_list, r, strict=True)))


if __name__ == "__main__":
    # The decisive, model-free analysis is the shadow decay rate.
    decay_analysis()
