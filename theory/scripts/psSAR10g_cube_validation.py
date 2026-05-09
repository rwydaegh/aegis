"""
Validate the closed-form psSAR_10g formulas against a numerical 62704-style
cube expansion on the Thelonious phantom.

Setup
-----
- Plane-wave illumination at S_inc = 1 W/m^2.
- Three-layer planar tissue model (skin 2 mm / fat 10 mm / muscle inf),
  homogeneous everywhere on the body, IT'IS-style dielectric properties.
- Sample N points on the phantom surface.  At each point, treat the body as a
  local half-space with the surface normal taken from the STL face.
- Sweep frequency, k_hat direction, and polarization (TE / TM).

For each configuration we compute three psSAR estimates:
  (A) Cauchy projection:    psSAR = (S_inc T_lay) / (rho L)  *  (|kx|+|ky|+|kz|)
  (B) Cosine law:           psSAR = S_ab(r) / (rho L_*)         with L_* = (m / (0.9 rho))^(1/3)
  (C) Numerical 62704:      voxelize a local box, scan axis-aligned cubes that
                            enclose 10 g of tissue, enforce <=10% air and no
                            entirely-air face, take the maximum mass-averaged SAR.

The script saves an NPZ of the sweep and a comparison scatter plot.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import trimesh

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EPS0 = 8.8541878128e-12
MU0 = 1.25663706212e-6
C0 = 1.0 / np.sqrt(EPS0 * MU0)
ETA0 = np.sqrt(MU0 / EPS0)  # 376.73 ohm
RHO = 1000.0  # uniform tissue density for mass / SAR (kg/m^3)
M_TARGET = 0.010  # 10 g
F_AIR_MAX = 0.10  # IEC/IEEE 62704-1 rule
L_NOMINAL = (M_TARGET / RHO) ** (1.0 / 3.0)  # 21.54 mm
L_STAR = (M_TARGET / (0.9 * RHO)) ** (1.0 / 3.0)  # 22.31 mm at 10% air

# Layer geometry
D_SKIN = 2e-3
D_FAT = 10e-3

# Tabulated IT'IS-style (eps_r, sigma) per layer at the sweep frequencies.
# Pulled from IT'IS v5 Cole-Cole fits at the listed frequencies.  Approximate;
# good to a few percent which is plenty for a sanity check.
TISSUE_TABLE = {
    2.45e9: {"skin": (38.0, 1.46),  "fat": (5.30, 0.10), "muscle": (52.7, 1.74)},
    6.0e9:  {"skin": (34.5, 3.92),  "fat": (5.05, 0.27), "muscle": (48.2, 5.20)},
    10.0e9: {"skin": (31.3, 8.01),  "fat": (4.60, 0.59), "muscle": (42.8, 10.6)},
    28.0e9: {"skin": (16.6, 25.8),  "fat": (3.10, 1.55), "muscle": (24.4, 30.2)},
    60.0e9: {"skin": ( 7.9, 36.4),  "fat": (3.00, 3.00), "muscle": (12.9, 52.7)},
}


# ---------------------------------------------------------------------------
# Layered Fresnel (3 layers above semi-inf muscle) via direct linear system
# ---------------------------------------------------------------------------

def n_complex(eps_r: float, sigma: float, freq_hz: float) -> complex:
    """Complex refractive index n = sqrt(eps_r - j sigma/(omega eps_0))."""
    omega = 2 * np.pi * freq_hz
    return np.sqrt(eps_r - 1j * sigma / (omega * EPS0))


def _kz(n: complex, kx: float, k0: float) -> complex:
    """Perpendicular wavenumber for forward wave under exp(-i kz z) convention.

    np.sqrt's principal branch already gives the correct sign:
      - Tissue (lossy n): result has Im(kz) < 0, so exp(-i kz z) decays for z>0.
      - Air evanescent (kx > k0 n): pure-imag with Im(kz) > 0, also decaying.
    """
    return np.sqrt((k0 * n) ** 2 - kx ** 2 + 0j)


@dataclass
class LayeredSolution:
    """Field amplitudes inside the 3-layer stack.

    For TE the linear system is in E_y amplitudes (incident E_y = 1).
    For TM the linear system is in H_y amplitudes (incident H_y = 1).
    Either way, T_lay = 1 - |r|^2 is the power transmission coefficient.
    """
    r: complex
    A1: complex; B1: complex   # skin
    A2: complex; B2: complex   # fat
    A3: complex                # muscle (forward only; semi-infinite)
    kx: float                  # tangential wavenumber (real, conserved)
    kz0: complex; kz1: complex; kz2: complex; kz3: complex
    n0: complex; n1: complex; n2: complex; n3: complex
    sigma_skin: float; sigma_fat: float; sigma_muscle: float
    polarization: str


def solve_3layer(
    freq_hz: float,
    theta_inc: float,
    polarization: str,
) -> LayeredSolution:
    """Solve the boundary-value problem for air | skin | fat | muscle.

    Phase reference for each layer is at its own top.
    Skin spans z in [0, d1]; fat spans [d1, d1+d2]; muscle z > d1+d2.
    Incident |E| = 1 in air at z = 0-.
    """
    props = TISSUE_TABLE[freq_hz]
    eps_skin, sig_skin = props["skin"]
    eps_fat, sig_fat = props["fat"]
    eps_muscle, sig_muscle = props["muscle"]

    n0 = 1.0 + 0j
    n1 = n_complex(eps_skin, sig_skin, freq_hz)
    n2 = n_complex(eps_fat, sig_fat, freq_hz)
    n3 = n_complex(eps_muscle, sig_muscle, freq_hz)

    omega = 2 * np.pi * freq_hz
    k0 = omega / C0
    kx = k0 * n0.real * np.sin(theta_inc)
    kz0 = _kz(n0, kx, k0)
    kz1 = _kz(n1, kx, k0)
    kz2 = _kz(n2, kx, k0)
    kz3 = _kz(n3, kx, k0)

    P1 = np.exp(-1j * kz1 * D_SKIN)
    P2 = np.exp(-1j * kz2 * D_FAT)

    # For TE the matched continuity uses kz directly.
    # For TM the matched continuity uses kz/n^2 (= kz/eps_r in nonmagnetic media).
    if polarization == "TE":
        a0, a1, a2, a3 = kz0, kz1, kz2, kz3
    elif polarization == "TM":
        a0 = kz0 / n0**2
        a1 = kz1 / n1**2
        a2 = kz2 / n2**2
        a3 = kz3 / n3**2
    else:
        raise ValueError(polarization)

    # Linear system M @ x = b, x = [r, A1, B1, A2, B2, A3]
    M = np.zeros((6, 6), dtype=complex)
    b = np.zeros(6, dtype=complex)

    # E continuity at z = 0
    M[0] = [-1, 1, 1, 0, 0, 0]
    b[0] = 1.0
    # H continuity at z = 0:  a0 (1 - r) = a1 (A1 - B1)
    M[1] = [a0, a1, -a1, 0, 0, 0]
    b[1] = a0
    # E continuity at z = d1:  A1 P1 + B1/P1 = A2 + B2
    M[2] = [0, P1, 1 / P1, -1, -1, 0]
    # H continuity at z = d1:  a1 (A1 P1 - B1/P1) = a2 (A2 - B2)
    M[3] = [0, a1 * P1, -a1 / P1, -a2, a2, 0]
    # E continuity at z = d1 + d2:  A2 P2 + B2/P2 = A3
    M[4] = [0, 0, 0, P2, 1 / P2, -1]
    # H continuity at z = d1 + d2:  a2 (A2 P2 - B2/P2) = a3 A3
    M[5] = [0, 0, 0, a2 * P2, -a2 / P2, -a3]

    sol = np.linalg.solve(M, b)
    r, A1, B1, A2, B2, A3 = sol

    return LayeredSolution(
        r=r, A1=A1, B1=B1, A2=A2, B2=B2, A3=A3,
        kx=float(kx),
        kz0=kz0, kz1=kz1, kz2=kz2, kz3=kz3,
        n0=n0, n1=n1, n2=n2, n3=n3,
        sigma_skin=sig_skin, sigma_fat=sig_fat, sigma_muscle=sig_muscle,
        polarization=polarization,
    )


def transmitted_power(sol: LayeredSolution, theta_inc: float) -> float:
    """Real power transmitted from air into the body, normalized to S_inc.

    Equals 1 - |r|^2 for both polarizations because the air carries forward
    and reflected waves with the same impedance and the layers are below.
    """
    return float(1.0 - np.abs(sol.r) ** 2)


def _E2_in_layer(
    A: complex, B: complex, kz: complex, kx: float, n: complex, polarization: str
) -> tuple[np.ndarray, np.ndarray]:
    """Return (a, b) such that |E(z)|^2 = a |fwd|^2 + b |bwd|^2 + 2 Re(c fwd bwd*)
    is given through the helper below.  Used to build SAR.

    For TE (A,B are E_y amplitudes):
        |E|^2 = |A exp(-i kz z) + B exp(+i kz z)|^2  (single transverse component)
    For TM (A,B are H_y amplitudes), Maxwell gives
        E_x = -(kz/(omega eps)) (A_- - B_+),   E_z = +(kx/(omega eps)) (A_- + B_+)
    with omega eps = (k0/eta0) n^2.  Then
        |E|^2 = (eta0^2 / (k0^2 |n^2|^2)) * (|kz|^2 |A_- - B_+|^2 + kx^2 |A_- + B_+|^2)
    """
    raise NotImplementedError  # see sar_at_depth below


def sar_at_depth(d: np.ndarray, sol: LayeredSolution) -> np.ndarray:
    """SAR(d) inside the body at depth d below the surface (d >= 0).

    Returns SAR in W/kg under S_inc = 1 W/m^2 normalization in air.
    Handles both TE and TM correctly:
      - TE: A,B are E_y amplitudes; |E|^2 = |A_- + B_+|^2; scaled by 2*eta0
        (so that S_inc = |E_inc|^2/(2 eta0) = 1).
      - TM: A,B are H_y amplitudes; |E|^2 = (eta0^2/(k0^2 |n^2|^2)) *
        (|kz|^2 |A_-_-_B_+|^2 + kx^2 |A_-_+_B_+|^2); scaled by 2/eta0
        (so that S_inc = eta0 |H_inc|^2/2 = 1).
    """
    d = np.asarray(d)
    sar = np.zeros_like(d, dtype=float)
    in_skin = d < D_SKIN
    in_fat = (d >= D_SKIN) & (d < D_SKIN + D_FAT)
    in_muscle = d >= D_SKIN + D_FAT

    omega = None  # we go through k0 directly
    k0 = abs(sol.kz0)  # at normal kz0=k0; for oblique kz0^2+kx^2=k0^2 so k0=sqrt(kz0^2+kx^2)
    # More robust: derive k0 from any layer:  (k0 n)^2 = kz^2 + kx^2.
    k0 = float(np.sqrt(np.real(sol.kz0 ** 2 + sol.kx ** 2)))
    if k0 == 0:
        k0 = abs(sol.kz0)  # fallback

    pol = sol.polarization

    def layer_sar(A, B, kz, n, sigma, z):
        fwd = A * np.exp(-1j * kz * z)
        bwd = B * np.exp(+1j * kz * z)
        if pol == "TE":
            E2 = np.abs(fwd + bwd) ** 2
            scale = 2.0 * ETA0
        else:  # TM
            n2_abs2 = float(np.abs(n ** 2) ** 2)
            kz_abs2 = float(np.abs(kz) ** 2)
            E2 = (ETA0 ** 2) / (k0 ** 2 * n2_abs2) * (
                kz_abs2 * np.abs(fwd - bwd) ** 2 + (sol.kx ** 2) * np.abs(fwd + bwd) ** 2
            )
            scale = 2.0 / ETA0
        return sigma * E2 * scale / (2.0 * RHO)

    if np.any(in_skin):
        sar[in_skin] = layer_sar(
            sol.A1, sol.B1, sol.kz1, sol.n1, sol.sigma_skin, d[in_skin]
        )
    if np.any(in_fat):
        sar[in_fat] = layer_sar(
            sol.A2, sol.B2, sol.kz2, sol.n2, sol.sigma_fat, d[in_fat] - D_SKIN
        )
    if np.any(in_muscle):
        sar[in_muscle] = layer_sar(
            sol.A3, 0.0 + 0j, sol.kz3, sol.n3, sol.sigma_muscle, d[in_muscle] - D_SKIN - D_FAT
        )
    return sar


# ---------------------------------------------------------------------------
# Closed-form psSAR estimates
# ---------------------------------------------------------------------------

def psSAR_cauchy(S_inc: float, T_lay: float, k_hat: np.ndarray) -> float:
    """Cauchy projection formula (the disputed corollary)."""
    proj = float(np.abs(k_hat[0]) + np.abs(k_hat[1]) + np.abs(k_hat[2]))
    return S_inc * T_lay / (RHO * L_NOMINAL) * proj


def psSAR_cosine(S_inc: float, T_lay: float, theta_inc: float) -> float:
    """Cosine law with L_* (10% air saturation) -- the variant used in the report.

    NB: under the strict no-face-entirely-air rule of 62704, the 10%-air optimal
    placement is actually invalid for face-flush axis-aligned cubes on smooth bodies
    (the top face sits in air).  See psSAR_cosine_nominal for the L=21.54mm variant.
    """
    S_ab = S_inc * T_lay * max(np.cos(theta_inc), 0.0)
    return S_ab / (RHO * L_STAR)


def psSAR_cosine_nominal(S_inc: float, T_lay: float, theta_inc: float) -> float:
    """Cosine law with L_nominal = 21.54 mm (cube fully in tissue, top at surface).

    This matches the optimal valid 62704 placement for face-flush axis-aligned
    cubes on a smooth body: the top face touches the surface, no air, no
    face-entirely-air violation.
    """
    S_ab = S_inc * T_lay * max(np.cos(theta_inc), 0.0)
    return S_ab / (RHO * L_NOMINAL)


# ---------------------------------------------------------------------------
# Numerical 62704 cube expansion on a planar half-space
# ---------------------------------------------------------------------------

def numerical_psSAR(
    n_hat: np.ndarray,
    sol: LayeredSolution,
    *,
    n_samples: int = 200_000,
    n_centers: int = 32,
    seed: int = 0,
) -> dict:
    """Numerical psSAR via Monte Carlo cube integration on a planar half-space.

    Geometry: planar body, surface through origin, outward normal n_hat (unit, global frame).
    Cube is axis-aligned in the global frame, side L, centered at (-d_off) * n_hat.

    For each candidate cube center along the body normal:
      - Generate N MC samples uniformly in the unit cube (reused across the bisection on L).
      - Bisect L until tissue mass = 10 g (within 1%).
      - Check 10% air rule (the standard's R3a) and no-face-entirely-air rule (R3b).
      - Compute mean SAR over tissue samples.
    Among all valid placements, return the maximum.

    Why Monte Carlo and not a regular voxel grid?  At 60 GHz the SAR penetration
    depth is 0.24 mm.  A voxel grid coarse enough to keep memory reasonable
    (dx=0.5 mm) puts the topmost voxel center 0.25 mm below the cube face,
    missing the surface SAR peak by a factor of e (visibly biases results
    low by ~40% even at 28 GHz).  MC samples are uniform in the cube and
    we evaluate the analytical 1D SAR(d) profile exactly at each sample.
    """
    n_hat = np.asarray(n_hat, dtype=float)
    n_hat = n_hat / np.linalg.norm(n_hat)
    rng = np.random.default_rng(seed)

    # Reused MC samples in the unit cube [-0.5, 0.5]^3.  Sharing them across
    # cube centers and L candidates removes a chunk of variance.
    u = rng.random((n_samples, 3)) - 0.5

    # Concentrate sampling near the face-flush optimum (d_off ~ L_NOMINAL/2 = 10.77 mm)
    # to handle the no-face-air cliff cleanly while still covering the broad range.
    # Also explicitly include d_off = L_NOMINAL/2 (the gamma=0 optimum where cube top is exactly at surface).
    broad = np.linspace(0.0, 22e-3, max(int(n_centers * 0.4), 8))
    fine = np.linspace(L_NOMINAL / 2 - 3e-3, L_NOMINAL / 2 + 4e-3, max(int(n_centers * 0.6), 16))
    critical = np.array([L_NOMINAL / 2])
    cube_centers = np.unique(np.concatenate([broad, fine, critical]))
    L_lo0, L_hi0 = 18e-3, 28e-3

    best = {
        "psSAR": 0.0, "L_opt": np.nan, "f_air": np.nan,
        "depth_offset": np.nan, "n_valid": 0,
    }

    for d_off in cube_centers:
        center = -d_off * n_hat

        # Bisect L on tissue mass (mass = f_tissue * rho * L^3).
        L_lo, L_hi = L_lo0, L_hi0
        for _ in range(22):
            L = 0.5 * (L_lo + L_hi)
            pts = center + u * L
            depth = -pts @ n_hat
            f_tissue = float((depth > 0).mean())
            mass = f_tissue * RHO * L ** 3
            if mass < M_TARGET:
                L_lo = L
            else:
                L_hi = L
        L = 0.5 * (L_lo + L_hi)
        pts = center + u * L
        depth = -pts @ n_hat
        is_tissue = depth > 0
        f_tissue = float(is_tissue.mean())
        mass = f_tissue * RHO * L ** 3
        if not (0.97 * M_TARGET < mass < 1.03 * M_TARGET):
            continue
        f_air = 1.0 - f_tissue
        if f_air > F_AIR_MAX:
            continue

        # No-face-entirely-air check.  For axis-aligned cube + planar body, a face
        # is entirely in air iff all of the face lies above the body surface, i.e.
        # iff the corner of the cube nearest the body (along that face's outward
        # normal) is still above the surface.  Equivalently, for face k=+/-x, +/-y, +/-z,
        # we check whether the closest-to-body corner of the face has depth > 0.
        face_invalid = False
        for axis in range(3):
            for sign in (-1, +1):
                # Face at center[axis] + sign * L/2 in the cube-axis direction.
                # Its 4 corners differ from the face center by +/- L/2 in the other 2 axes.
                # The corner with maximum -n_hat·r (=max depth) is closest to body.
                corner = center.copy()
                corner[axis] += sign * L / 2
                for a2 in range(3):
                    if a2 == axis:
                        continue
                    corner[a2] += np.sign(-n_hat[a2]) * L / 2 if n_hat[a2] != 0 else L / 2
                # Treat depth = 0 (corner exactly on surface) as valid boundary.
                if -np.dot(corner, n_hat) < 0:
                    face_invalid = True
                    break
            if face_invalid:
                break
        if face_invalid:
            continue

        sar = sar_at_depth(depth[is_tissue], sol)
        cube_sar = float(sar.mean())
        best["n_valid"] += 1
        if cube_sar > best["psSAR"]:
            best.update({
                "psSAR": cube_sar, "L_opt": L,
                "f_air": f_air, "depth_offset": d_off,
            })

    return best


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

def sample_surface(stl_path: Path, n_points: int, seed: int = 0):
    mesh = trimesh.load(stl_path, force="mesh")
    rng = np.random.default_rng(seed)
    pts, face_idx = trimesh.sample.sample_surface_even(mesh, n_points, seed=seed)
    if len(pts) < n_points:
        # sample_surface_even may return fewer; top up with regular sampling
        more, more_idx = mesh.sample(n_points - len(pts), return_index=True)
        pts = np.vstack([pts, more])
        face_idx = np.concatenate([face_idx, more_idx])
    normals = mesh.face_normals[face_idx]
    return pts, normals, mesh


def run_sweep(
    stl_path: Path,
    n_points: int = 30,
    freqs: tuple = (2.45e9, 10e9, 28e9, 60e9),
    pols: tuple = ("TE", "TM"),
    k_dirs: tuple | None = None,
    seed: int = 0,
):
    if k_dirs is None:
        # A few representative directions in the body frame.
        # Mostly horizontal incidence (a person standing, BS in front / side / above).
        k_dirs = (
            np.array([0, 0, -1.0]),                  # straight down
            np.array([0, -1.0, 0]),                  # horizontal, frontal
            np.array([-1.0, 0, 0]),                  # horizontal, side
            np.array([-1.0, 0, -1.0]) / np.sqrt(2),  # 45 deg above horizon
            np.array([-1.0, -1.0, -1.0]) / np.sqrt(3),  # along body diagonal
        )

    pts, normals, mesh = sample_surface(stl_path, n_points, seed=seed)
    print(f"[sweep] mesh bbox = {mesh.bounds}")
    print(f"[sweep] sampled {len(pts)} points")

    rows = []
    t0 = time.time()
    n_total = len(pts) * len(freqs) * len(pols) * len(k_dirs)
    n_done = 0

    for ip, (r_s, n_hat) in enumerate(zip(pts, normals)):
        n_hat = n_hat / np.linalg.norm(n_hat)
        for f in freqs:
            for pol in pols:
                for k_hat in k_dirs:
                    n_done += 1
                    mu = float(np.dot(n_hat, -k_hat))  # cos(theta_inc)
                    if mu <= 1e-3:
                        # Body surface points away from wave; no incidence.
                        continue
                    theta_inc = float(np.arccos(np.clip(mu, 0.0, 1.0)))

                    sol = solve_3layer(f, theta_inc, pol)
                    T_lay = transmitted_power(sol, theta_inc)
                    S_ab = T_lay * mu  # S_inc = 1
                    S_inc = 1.0

                    A_cauchy = psSAR_cauchy(S_inc, T_lay, k_hat)
                    B_cosine_star = psSAR_cosine(S_inc, T_lay, theta_inc)
                    C_cosine_nom = psSAR_cosine_nominal(S_inc, T_lay, theta_inc)

                    num = numerical_psSAR(n_hat, sol)

                    rows.append(dict(
                        ip=ip, freq=f, pol=pol,
                        kx=float(k_hat[0]), ky=float(k_hat[1]), kz=float(k_hat[2]),
                        nx=float(n_hat[0]), ny=float(n_hat[1]), nz=float(n_hat[2]),
                        mu=mu, T_lay=T_lay, S_ab=S_ab,
                        psSAR_cauchy=A_cauchy,
                        psSAR_cosine_star=B_cosine_star,
                        psSAR_cosine_nom=C_cosine_nom,
                        psSAR_num=num["psSAR"],
                        L_opt=num["L_opt"], f_air=num["f_air"],
                        n_valid=num["n_valid"],
                    ))

                    if n_done % 25 == 0:
                        dt = time.time() - t0
                        print(f"  [{n_done}/{n_total}] {dt:.1f}s "
                              f"f={f/1e9:.2f}GHz pol={pol} mu={mu:.2f} "
                              f"num={num['psSAR']:.3f}")

    print(f"[sweep] done in {time.time()-t0:.1f}s, {len(rows)} valid records")
    return rows


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_results(rows, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = [r for r in rows if r["psSAR_num"] > 0]
    if not rows:
        print("[plot] no valid rows")
        return

    num = np.array([r["psSAR_num"] for r in rows])
    cau = np.array([r["psSAR_cauchy"] for r in rows])
    cos_s = np.array([r["psSAR_cosine_star"] for r in rows])
    cos_n = np.array([r["psSAR_cosine_nom"] for r in rows])
    mu = np.array([r["mu"] for r in rows])
    freq = np.array([r["freq"] for r in rows])

    # Scatter: each closed-form vs numerical
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
    panels = [
        (cau,   "Cauchy projection"),
        (cos_s, "Cosine law (L_*)"),
        (cos_n, "Cosine law (L_nominal)"),
    ]
    for ax, (pred, label) in zip(axes, panels):
        sc = ax.scatter(num, pred, c=mu, cmap="viridis", s=18, alpha=0.7)
        lo = min(num.min(), pred.min()); hi = max(num.max(), pred.max())
        ax.plot([lo, hi], [lo, hi], "k--", lw=1)
        ax.set_xlabel(r"Numerical 62704 [W/kg]")
        ax.set_ylabel(f"{label} [W/kg]")
        ax.set_title(label)
        ax.set_xscale("log"); ax.set_yscale("log")
    fig.colorbar(sc, ax=axes.ravel().tolist(), label=r"$\cos\theta_i$", shrink=0.8)
    fig.suptitle("psSAR$_{10\\,g}$ closed form vs numerical 62704 (Thelonious, 3-layer)")
    fig.savefig(out_dir / "scatter_formula_vs_numerical.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # Ratio vs incidence cosine
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
    for ax, (pred, label) in zip(axes, panels):
        ratio = pred / np.maximum(num, 1e-12)
        sc = ax.scatter(mu, ratio, c=np.log10(freq / 1e9), cmap="plasma", s=18, alpha=0.7)
        ax.axhline(1.0, color="k", ls="--", lw=1)
        ax.set_xlabel(r"$\cos\theta_i$")
        ax.set_ylabel(f"{label} / numerical")
        ax.set_yscale("log")
        ax.set_title(label)
    fig.colorbar(sc, ax=axes.ravel().tolist(), label=r"log$_{10}$ f [GHz]", shrink=0.8)
    fig.suptitle("Formula / numerical ratio vs incidence cosine")
    fig.savefig(out_dir / "ratio_vs_mu.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # Per-frequency summary
    print("\nSummary  (median formula / numerical, by frequency)")
    print(("-" * 70))
    print(f"{'f [GHz]':>10}  {'N':>4}  {'Cauchy/num':>12}  {'CosL*/num':>12}  {'CosLnom/num':>12}")
    for f in sorted(set(freq)):
        mask = freq == f
        if not mask.any():
            continue
        m_cau = float(np.median(cau[mask] / num[mask]))
        m_cs = float(np.median(cos_s[mask] / num[mask]))
        m_cn = float(np.median(cos_n[mask] / num[mask]))
        print(f"{f/1e9:>10.2f}  {int(mask.sum()):>4}  {m_cau:>12.3f}  {m_cs:>12.3f}  {m_cn:>12.3f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    aegis_root = Path(__file__).resolve().parents[2]
    stl_path = aegis_root / "data" / "thelonious.stl"
    out_dir = aegis_root / "theory" / "scripts" / "psSAR10g_validation_out"
    if not stl_path.exists():
        sys.exit(f"missing STL: {stl_path}")

    n_points = int(os.environ.get("N_POINTS", 25))
    rows = run_sweep(stl_path, n_points=n_points)

    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_dir / "sweep.npz",
        **{k: np.array([r[k] for r in rows]) for k in rows[0].keys()},
    )
    plot_results(rows, out_dir)
    print(f"\n[done] outputs in {out_dir}")


if __name__ == "__main__":
    main()
