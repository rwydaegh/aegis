"""Case study for direction_4_problem.tex.

Question: in coherent MIMO, when does the ICNIRP 4 cm^2 averaged absorbed
power density (APD) bind before whole-body SAR_wb?

Setup: a flat skin patch (~30 cm x 30 cm) illuminated by N antenna
elements, each radiating one plane wave toward the patch from a random
direction inside a half-angle alpha. The UE channel h is chosen so that
MRT aligns all N paths at the patch centre (worst-case hotspot).

We compute, as functions of N and alpha:

  eta_4    = max_{r0 in patch} APD_4(r0) / <S_ab>_patch
  P_abs_budget_SAR = 0.08 * m_body              (W, adult m=70, public)
  P_abs_budget_APD = 20 * A_body * <S_ab>/max APD_4   (hypothetical scaling)

Results are dumped as a JSON file to be consumed by the tex figure.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.constants import Z_0
from aegis.geometry.averaging import precompute_averaging_matrix
from aegis.tissue.dielectric import SKIN_28GHZ


_PANEL_CACHE: dict = {}


def build_flat_panel(side_m: float = 0.30, pitch_m: float = 2.5e-3):
    """Build a structured flat triangular mesh on z=0, normals +z.

    side_m: side length of the square panel.
    pitch_m: triangle side length; triangles are isoceles right with legs
    of this length, so each has area = pitch_m^2 / 2.
    """
    n = int(np.round(side_m / pitch_m))
    x = np.linspace(-side_m / 2, side_m / 2, n + 1)
    y = np.linspace(-side_m / 2, side_m / 2, n + 1)
    xx, yy = np.meshgrid(x, y, indexing="ij")

    # Two triangles per grid square: (i,j),(i+1,j),(i,j+1) and (i+1,j),(i+1,j+1),(i,j+1)
    tris = []
    for i in range(n):
        for j in range(n):
            v00 = (xx[i, j], yy[i, j], 0.0)
            v10 = (xx[i + 1, j], yy[i + 1, j], 0.0)
            v01 = (xx[i, j + 1], yy[i, j + 1], 0.0)
            v11 = (xx[i + 1, j + 1], yy[i + 1, j + 1], 0.0)
            tris.append([v00, v10, v01])
            tris.append([v10, v11, v01])

    vertices = np.array(tris, dtype=float)  # (M_tri, 3, 3)
    centroids = vertices.mean(axis=1)
    # Outward normal +z (away from body interior)
    normals = np.tile(np.array([0.0, 0.0, 1.0]), (vertices.shape[0], 1))
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    areas = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
    return centroids, normals, areas


def build_paths(N: int, alpha_rad: float, seed: int = 0, freq_hz: float = 28e9):
    """N antennas, each one plane wave from direction in a cone of half-angle alpha
    around the -z axis (so all paths propagate downward into the body).

    Each plane wave has |psi|^2 = 2*Z_0 so the per-path incident power density
    |psi|^2/(2 Z_0) = 1 W/m^2. The per-antenna transmit power is then set by
    the precoder x. The polarisation direction for each path is chosen linear
    along the surface-parallel x-axis component after projecting out k_hat.
    """
    rng = np.random.default_rng(seed)
    # uniform over solid angle cap |cos theta| > cos(alpha)
    u = rng.uniform(np.cos(alpha_rad), 1.0, size=N)  # cos(theta)
    theta = np.arccos(u)
    phi = rng.uniform(0.0, 2 * np.pi, size=N)
    # k_hat: propagation direction = down + lateral, pointing from above into body
    # Let arrival direction be from angle (theta) off +z axis above, then k_hat
    # (propagation) = -(sin theta cos phi, sin theta sin phi, cos theta).
    k_hat = np.column_stack(
        [
            -np.sin(theta) * np.cos(phi),
            -np.sin(theta) * np.sin(phi),
            -np.cos(theta),
        ]
    )

    # Polarisation: choose linear pol along x (project to perpendicular to k_hat)
    e_x = np.array([1.0, 0.0, 0.0])
    pol = e_x[None, :] - (k_hat @ e_x)[:, None] * k_hat
    pol_norm = np.linalg.norm(pol, axis=1, keepdims=True)
    pol = pol / pol_norm
    # |psi|^2 = 2*Z_0 => unit incident power density per path
    psi = np.sqrt(2 * Z_0) * pol.astype(complex)

    element_index = np.arange(N, dtype=np.int64)
    return k_hat, psi, element_index


def mrt_at_center(k_hat, psi, freq_hz):
    """Choose h so that MRT x = sqrt(P) h*/||h|| aligns all paths at r=0.

    At r=0 the phase factor exp(-i k0 k_hat . 0) = 1. We want the contribution
    of each antenna j to the field at r=0 to be co-phased and to sum
    constructively. Under MRT, x_j = (P/||h||)^{1/2} * h_j^*. The field at
    r=0 from antenna j is g_j(0) = psi_{j} (single path per antenna).
    The contribution of antenna j to the body-field at r=0 is x_j * g_j.

    Picking h_j = sum of psi_j components (projected onto a reference pol)
    would align phases. Simpler: take h_j = complex conjugate of a scalar
    proxy of g_j so x_j = proxy_j. For unit amplitude, just set h_j = 1
    (all antennas co-phased at UE) - this gives a constructive hotspot at
    r=0 if the per-path psi vectors are co-polarised (they are, since we
    built psi along a projection of the same e_x direction).
    """
    N = k_hat.shape[0]
    h = np.ones(N, dtype=complex)
    return h


def simulate(N: int, alpha_deg: float, P_tx: float = 1.0, freq_hz: float = 28e9,
             seed: int = 0, verbose: bool = False):
    tissue = SKIN_28GHZ
    n_tilde = tissue.n_complex
    sigma = tissue.sigma

    cache_key = ("panel", 0.30, 2.5e-3)
    if cache_key not in _PANEL_CACHE:
        centroids, normals, areas = build_flat_panel(side_m=0.30, pitch_m=2.5e-3)
        G_avg = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        _PANEL_CACHE[cache_key] = (centroids, normals, areas, G_avg)
        if verbose:
            print(f"mesh: {len(areas)} triangles, total area {areas.sum():.4f} m^2")
    centroids, normals, areas, G_avg = _PANEL_CACHE[cache_key]

    alpha_rad = np.deg2rad(alpha_deg)
    k_hat, psi, elem = build_paths(N, alpha_rad, seed=seed, freq_hz=freq_hz)

    G_tilde = compute_body_channel(
        normals, centroids, k_hat, psi, elem,
        n_tilde=n_tilde, sigma=sigma, freq_hz=freq_hz, n_elements=N,
    )
    h = mrt_at_center(k_hat, psi, freq_hz)
    # MRT precoder: x = sqrt(P) h* / ||h||
    x = np.sqrt(P_tx) * h.conj() / np.linalg.norm(h)

    # S_ab per triangle
    field = np.einsum("mia,a->mi", np.asarray(G_tilde), x)
    sab = np.real(np.sum(field.conj() * field, axis=1))
    sab = np.maximum(sab, 0.0)

    # Panel total absorbed power
    P_abs_panel = float(np.sum(areas * sab))
    S_panel_avg = P_abs_panel / float(areas.sum())

    # ICNIRP 4 cm^2 averaging (G_avg cached above)
    apd4 = np.asarray(G_avg @ sab)
    apd4_max = float(apd4.max())
    sab_peak = float(sab.max())

    # Exposure operator
    Q = compute_exposure_operator(G_tilde, areas)
    eigs = np.linalg.eigvalsh(np.asarray(Q))
    lam_max = float(np.maximum(eigs, 0.0).max())

    # Scalar summary
    return dict(
        N=N,
        alpha_deg=alpha_deg,
        P_tx=P_tx,
        P_abs_panel=P_abs_panel,
        S_panel_avg=S_panel_avg,
        sab_peak=sab_peak,
        apd4_max=apd4_max,
        lam_max=lam_max,
        # concentration ratios
        eta_peak=sab_peak / S_panel_avg,        # peak S_ab / panel-average
        eta_4cm=apd4_max / S_panel_avg,         # worst 4 cm^2 average / panel-average
    )


if __name__ == "__main__":
    out = Path(__file__).parent / "hotspot_scaling_results.json"
    rows = []

    # Main sweep: N vs alpha (3 seeds for speed; reduced N list)
    N_VALUES = [1, 2, 4, 8, 16, 32, 64]
    ALPHAS = [10.0, 30.0, 60.0]
    N_SEEDS = 3
    import sys
    import time
    t0 = time.time()
    for alpha_deg in ALPHAS:
        for N in N_VALUES:
            ratios_peak = []
            ratios_4cm = []
            for seed in range(N_SEEDS):
                r = simulate(N=N, alpha_deg=alpha_deg, seed=seed)
                ratios_peak.append(r["eta_peak"])
                ratios_4cm.append(r["eta_4cm"])
            rec = dict(
                N=N,
                alpha_deg=alpha_deg,
                eta_peak_mean=float(np.mean(ratios_peak)),
                eta_peak_std=float(np.std(ratios_peak)),
                eta_4cm_mean=float(np.mean(ratios_4cm)),
                eta_4cm_std=float(np.std(ratios_4cm)),
            )
            rows.append(rec)
            print(
                f"N={N:3d} alpha={alpha_deg:5.1f} deg  "
                f"eta_peak={rec['eta_peak_mean']:6.2f}  eta_4cm={rec['eta_4cm_mean']:6.2f}  "
                f"[{time.time()-t0:5.1f}s]",
                flush=True,
            )
            sys.stdout.flush()

    out.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {out}")
