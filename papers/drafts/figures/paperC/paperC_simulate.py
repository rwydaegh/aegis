"""Paper C canonical-scenario simulations.

Generates the four numerical-demonstration figures and supporting tables
for "A closed-form exposure operator for coherent millimetre-wave".

Scenario:
- 8x8 (M=64) URA at half-wavelength spacing, 28 GHz.
- Thelonious phantom (z=up, ~1.18 m tall).
- BS at (0, -3, 1.0) m (3 m in front of phantom centre, head height).
- UE positions:
    (a) (0, 5, 1.0) m  -- in front, aligned-with-body case
    (b) (0, -5, 1.0) m -- behind, geometrically protected case
- 40 multipath rays per element: synthetic spread of paths around LOS
  (30-degree cone, random polarisations and amplitudes).

Outputs (in same folder):
- paperC_results.npz
- paperC_summary.csv
- approx_error_budget.{pdf,png}
- ecbf_pareto.{pdf,png}
- rho_landscape.{pdf,png}
- hotspot_pair.{pdf,png}
- spectrum.{pdf,png}
- README.md
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import LogNorm, Normalize

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    compute_rho,
    eigendecompose_Q,
)
from aegis.coherent.fresnel_operator import compute_fresnel_operator
from aegis.constants import C_0, Z_0
from aegis.geometry.mesh import BodyMesh
from aegis.tissue.fresnel import xi_from_mu

# ---------------------------------------------------------------------------
# Scenario constants
# ---------------------------------------------------------------------------

FREQ_HZ = 28e9
LAMBDA = C_0 / FREQ_HZ  # ~1.07 cm
ARRAY_NX = 8
ARRAY_NY = 8
M_ANT = ARRAY_NX * ARRAY_NY
SPACING = LAMBDA / 2

# Tissue: skin at 28 GHz (paper C spec eps_r=16.55, sigma=25.8)
SKIN_EPS_R = 16.55
SKIN_SIGMA = 25.8
N_TILDE = np.sqrt(SKIN_EPS_R - 1j * SKIN_SIGMA / (2 * np.pi * FREQ_HZ * 8.854187817e-12))

# Geometry (z is up; mesh is centred so feet at z ~ -0.97, head at z ~ 0.21)
# We translate the mesh so feet are at z=0 (head at ~1.18) and centre at (0,0).
PHANTOM_Z_OFFSET = 0.97  # add this to mesh z to put feet at z=0

# BS position: 3 m in front of phantom (negative y direction), head height
BS_CENTER = np.array([0.0, -3.0, 1.0])
# Array points in +y direction (toward phantom). Element grid in xz plane.

# UE positions (paper C spec)
UE_FRONT = np.array([0.0, 5.0, 1.0])  # behind phantom relative to BS
UE_BEHIND = np.array([0.0, -5.0, 1.0])  # behind BS relative to phantom

# Path geometry: clusters shared across elements (realistic far-field model).
# 40 clusters x 64 elements = 2560 element-paths. The LOS cluster sits at
# index 0 and has unit amplitude; remaining clusters span a 30 deg cone.
N_CLUSTERS = 40
CONE_HALF_ANGLE_DEG = 15.0  # half-angle, so cone diameter = 30 deg
LOS_AMPLITUDE_FACTOR = 1.0  # LOS path
SCATTERER_AMPLITUDE_RANGE = (0.05, 0.5)  # secondary path amplitude factors

# Mesh subsampling: limits memory of the (M_tri, N_paths, 3) intermediate.
# Full mesh has 23826 triangles; 4000 keeps geometric fidelity at 2560 paths.
MAX_TRIANGLES = 4000

P_TX_DBM = 30.0  # 1 W per array (so per-element 1/64 W = ~12 dBm)
P_TX_W = 10 ** ((P_TX_DBM - 30) / 10.0)  # 1 W

OUT_DIR = Path(__file__).parent.resolve()


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def build_ura_positions(center: np.ndarray, nx: int, ny: int, spacing: float) -> np.ndarray:
    """8x8 URA centred at `center`, in the x-z plane (vertical wall facing +y).

    Element (i, j) sits at (x_i, y_center, z_j) with i in nx, j in ny.
    """
    xs = (np.arange(nx) - (nx - 1) / 2) * spacing
    zs = (np.arange(ny) - (ny - 1) / 2) * spacing
    grid = np.array([[x, 0.0, z] for z in zs for x in xs])  # (M, 3) row-major (z-major)
    return center + grid  # (M, 3)


def load_thelonious(max_triangles: int | None = None) -> BodyMesh:
    """Load Thelonious mesh and translate so feet are at z=0, centred in xy.

    Subsamples uniformly to `max_triangles` to bound memory of (M, N, 3) intermediates.
    """
    mesh = BodyMesh.load("/home/user/aegis/data/thelonious.stl", name="thelonious")
    new_vertices = mesh.vertices.copy()
    bb_min, bb_max = mesh.bounding_box
    new_vertices[:, :, 0] -= (bb_min[0] + bb_max[0]) / 2
    new_vertices[:, :, 1] -= (bb_min[1] + bb_max[1]) / 2
    new_vertices[:, :, 2] -= bb_min[2]
    normals = mesh.normals
    if max_triangles is not None and new_vertices.shape[0] > max_triangles:
        # Use deterministic uniform subsampling so identical seeds reproduce
        idx = np.linspace(0, new_vertices.shape[0] - 1, max_triangles, dtype=int)
        new_vertices = new_vertices[idx]
        normals = normals[idx]
    return BodyMesh.from_arrays(new_vertices, normals=normals, name="thelonious_translated")


# ---------------------------------------------------------------------------
# Synthetic propagation paths
# ---------------------------------------------------------------------------


def _orthonormal_basis(k_hat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return two unit vectors orthogonal to k_hat (and to each other)."""
    if abs(k_hat[2]) < 0.9:
        ref = np.array([0.0, 0.0, 1.0])
    else:
        ref = np.array([1.0, 0.0, 0.0])
    e1 = np.cross(k_hat, ref)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(k_hat, e1)
    e2 /= np.linalg.norm(e2)
    return e1, e2


def synthetic_paths_for_target(
    bs_positions: np.ndarray,
    target_position: np.ndarray,
    n_clusters: int,
    cone_half_angle_deg: float,
    p_tx_w_per_element: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build synthetic propagation paths from a BS array to a target point.

    Generates `n_clusters` shared scatterer clusters (the LOS direction is
    cluster 0). Each cluster produces M_ant paths -- one per element -- that
    share the cluster's far-field direction k_hat and polarisation, but
    pick up element-specific phase from the array geometry (k_hat . r_elem).
    Cluster amplitudes are randomised; the LOS cluster has unit amplitude.

    This yields N = M_ant * n_clusters element-tied paths with strong
    correlation across elements (the realistic far-field model), so the
    exposure operator Q has effective rank << M for small n_clusters.

    Returns
    -------
    k_hat : (N, 3)
    psi : (N, 3) complex (polarisation-amplitude vector)
    element_index : (N,) int
    delay : (N,) float (path-length seconds)
    """
    M = bs_positions.shape[0]
    array_centre = bs_positions.mean(axis=0)
    cone_rad = np.deg2rad(cone_half_angle_deg)
    k0 = 2 * np.pi * FREQ_HZ / C_0

    # LOS direction from array centre to target
    los_vec = target_position - array_centre
    d_los = float(np.linalg.norm(los_vec))
    k_los = los_vec / d_los
    e1_los, e2_los = _orthonormal_basis(k_los)

    # Generate cluster directions and base amplitudes
    cluster_k_hat = np.zeros((n_clusters, 3))
    cluster_amp = np.zeros(n_clusters)
    cluster_pol = np.zeros((n_clusters, 3), dtype=complex)
    cluster_d = np.zeros(n_clusters)
    for c in range(n_clusters):
        if c == 0:
            k_hat = k_los.copy()
            d = d_los
            amp = LOS_AMPLITUDE_FACTOR
        else:
            # Scattered: random direction within cone (uniform on spherical cap)
            ct = 1.0 - rng.uniform() * (1.0 - np.cos(cone_rad))
            st = np.sqrt(max(0.0, 1.0 - ct * ct))
            phi = rng.uniform(0.0, 2 * np.pi)
            k_hat = ct * k_los + st * (np.cos(phi) * e1_los + np.sin(phi) * e2_los)
            k_hat /= np.linalg.norm(k_hat)
            # Cluster path length is a bit longer (10-40%)
            d = d_los * (1.0 + 0.1 + rng.uniform(0.0, 0.3))
            amp = rng.uniform(*SCATTERER_AMPLITUDE_RANGE)

        # Random polarisation perpendicular to k_hat (per-cluster, shared across elements)
        e_a, e_b = _orthonormal_basis(k_hat)
        theta_pol = rng.uniform(0.0, 2 * np.pi)
        phase_pol = rng.uniform(0.0, 2 * np.pi)
        ellip = rng.uniform(0.7, 1.0)
        re_part = np.cos(theta_pol) * e_a + ellip * np.sin(theta_pol) * e_b
        im_part = -ellip * np.sin(theta_pol) * e_a + np.cos(theta_pol) * e_b
        pol_vec = np.cos(phase_pol) * re_part + 1j * np.sin(phase_pol) * im_part
        pol_vec /= np.linalg.norm(pol_vec)

        cluster_k_hat[c] = k_hat
        cluster_amp[c] = amp
        cluster_pol[c] = pol_vec
        cluster_d[c] = d

    # Expand to per-element paths
    N_total = M * n_clusters
    k_hats = np.zeros((N_total, 3))
    psi_arr = np.zeros((N_total, 3), dtype=complex)
    elem_idx = np.zeros(N_total, dtype=np.intp)
    delays = np.zeros(N_total)

    for c in range(n_clusters):
        k_hat = cluster_k_hat[c]
        amp = cluster_amp[c]
        pol_vec = cluster_pol[c]
        d_cluster = cluster_d[c]
        # E-field amplitude using the cluster's nominal path length
        E_amp = np.sqrt(2 * Z_0 * p_tx_w_per_element / (4 * np.pi)) / d_cluster * amp
        # Per-element path length using element offset projected onto k_hat
        offsets = bs_positions - array_centre  # (M, 3)
        # The element-to-target distance is approximately
        #   d_j ~ d_cluster - k_hat . (r_elem - r_centre)
        # The wave from element j arrives at the target with phase
        #   exp(-j k0 d_j) = exp(-j k0 d_cluster) * exp(+j k0 k_hat . offset)
        elem_phase = np.exp(1j * k0 * (offsets @ k_hat))  # (M,)
        # Common cluster phase
        common_phase = np.exp(-1j * k0 * d_cluster)
        for j in range(M):
            base_idx = j * n_clusters + c  # element-major order
            psi_arr[base_idx] = E_amp * pol_vec * common_phase * elem_phase[j]
            k_hats[base_idx] = k_hat
            elem_idx[base_idx] = j
            delays[base_idx] = d_cluster / C_0

    return k_hats, psi_arr, elem_idx, delays


def channel_h_from_paths(
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    ue_position: np.ndarray,
    n_elements: int,
) -> np.ndarray:
    """Build UE-side channel vector h from the same path realisation.

    h_j = sum_{n: j(n)=j} (something_n) * exp(-j k0 k_hat_n . r_UE)

    For a scalar reception channel we use a fixed reference receive polarisation
    (vertical: z-projected perpendicular to k_hat) and project psi onto it.
    """
    k0 = 2 * np.pi * FREQ_HZ / C_0
    N = k_hat.shape[0]
    contributions = np.zeros((N,), dtype=complex)
    z_axis = np.array([0.0, 0.0, 1.0])
    for n in range(N):
        k = k_hat[n]
        # Vertical-polarised receive antenna: ref vector perpendicular to k
        # in plane of incidence with z-axis
        e_pol = z_axis - np.dot(z_axis, k) * k
        norm = np.linalg.norm(e_pol)
        e_pol = e_pol / norm if norm > 1e-12 else np.array([1.0, 0.0, 0.0])
        # h component is e_pol . psi * exp(-j k0 k . r_UE)
        scalar = np.dot(e_pol, psi[n])
        phase = np.exp(-1j * k0 * np.dot(k, ue_position))
        contributions[n] = scalar * phase

    h = np.zeros(n_elements, dtype=complex)
    for n in range(N):
        h[element_index[n]] += contributions[n]
    return h


# ---------------------------------------------------------------------------
# Exact-Lambda exposure operator (no Approximation 2)
# ---------------------------------------------------------------------------


def compute_exposure_operator_exact(
    normals: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    n_tilde: complex,
    sigma: float,
    freq_hz: float,
    n_elements: int,
) -> np.ndarray:
    """Compute Q under the full Lambda matrix (Approximation 1 only).

    P_abs = (sigma / 2) sum_n sum_{n'} Lambda_{nn'} <E_n^trans, E_{n'}^trans>
        Lambda_{nn'} = 1 / (alpha_n + alpha_{n'} - i (beta_{n'} - beta_n))

    With alpha, beta evaluated at each (triangle, path) pair from k0 * xi.

    This is the reference Q (no Approx 2). It still uses Approx 1 (incident
    TM polarisation direction) because the implementation of compute_fresnel_operator
    bakes that in.

    Parameters mirror compute_body_channel; returns Q (M_ant, M_ant) Hermitian PSD.
    """
    M_tri = normals.shape[0]
    N_paths = k_hat.shape[0]
    k0 = 2 * np.pi * freq_hz / C_0

    # Fresnel components
    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n_tilde)
    # Convert to numpy in case JAX backend
    mu = np.asarray(mu)
    t_s = np.asarray(t_s)
    t_p = np.asarray(t_p)
    e_s = np.asarray(e_s)
    e_p = np.asarray(e_p)

    # alpha, beta from xi (per (M_tri, N_paths))
    xi = np.asarray(xi_from_mu(mu, n_tilde))
    k0_xi = k0 * xi
    beta = np.real(k0_xi)  # (M, N) phase rate inside tissue along normal
    alpha = -np.imag(k0_xi)  # (M, N) decay rate
    alpha = np.maximum(alpha, 1e-30)

    # F @ psi for each (m, n): (M, N, 3)
    psi_s = np.einsum("mnj,nj->mn", e_s, psi)
    psi_p = np.einsum("mnj,nj->mn", e_p, psi)
    F_psi = (t_s * psi_s)[:, :, None] * e_s + (t_p * psi_p)[:, :, None] * e_p  # (M, N, 3)

    # Geometric phase on the surface: exp(-j k0 k_hat . r_m)  shape (M, N)
    phase_arg = -k0 * (centroids @ k_hat.T)
    surf_phase = np.exp(1j * phase_arg)  # (M, N)

    # Absorption per triangle is sum_n sum_{n'} Lambda_{nn'} <F_psi_n, F_psi_n'>
    # For Q assembly we need x^H Q x = P_abs where the per-element x is involved.
    # Define u_n(r) = F_psi[m, n, :] * surf_phase[m, n].  (M, N, 3)
    # Then for each (m), P_abs(m) = (sigma/2) sum_{nn'} Lambda_{m,n,n'} u^*_n . u_{n'}
    # The exposure operator entry Q[a,b] = (sigma/2) sum_m area_m sum_{n in elem a} sum_{n' in elem b}
    #  Lambda_{m,n,n'} u^*_n(m) . u_{n'}(m)  with x being absorbed into u as identity.
    # Strictly: u_n(m) does not include x (that's the purpose of Q). Use:
    # u_n(m, x) = x_{j(n)} * F_psi[m, n] * surf_phase[m, n]  ->  P_abs = sigma/2 * sum...
    # So Q[a,b] = (sigma/2) sum_m area_m sum_{n: j(n)=a, n': j(n')=b} Lambda_{m,n,n'} <U_n(m)*, U_{n'}(m)>
    # where U_n(m) = F_psi[m, n] * surf_phase[m, n]  (M, N, 3) without x.

    U = F_psi * surf_phase[:, :, None]  # (M, N, 3)

    # Assembly is O(M_tri * N^2). For M_tri ~24k, N ~ 64*40 = 2560: 24k * 2560^2 ~ 1.6e11
    # too expensive without subsampling. The result is summed over m (with area weighting),
    # so we can collapse the per-triangle sum without per-pair Lambda:
    # Q[a,b] = (sigma/2) sum_{n: j(n)=a, n': j(n')=b} [ sum_m area_m Lambda_{m,n,n'} <U_n(m)*, U_{n'}(m)> ]
    # The bracket is an inner product over surface points, weighted by Lambda (a per-(m,n,n') scalar).
    # Lambda_{m,n,n'} = 1 / (alpha_{m,n} + alpha_{m,n'} - j (beta_{m,n'} - beta_{m,n}))
    # That depends on m through alpha and beta, so we cannot factor it out.
    #
    # Strategy: do full M_tri x N x N pair evaluation in chunks over m to keep memory bounded.
    # Memory per chunk: chunk_size * N * N * 16 bytes (complex128). For N=2560 that is huge.
    # Instead, downsample triangles uniformly: this is acceptable for an error budget figure
    # because the relative error ||Delta Q|| / ||Q|| does not depend strongly on the triangle
    # discretisation as long as both the Approx-2 and exact Q use the same triangles.

    # Downsample to ~3000 triangles for tractable exact Lambda computation
    if M_tri > 3000:
        idx = np.linspace(0, M_tri - 1, 3000, dtype=int)
        M_sub = len(idx)
        normals_s = normals[idx]
        centroids_s = centroids[idx]
        areas_s = areas[idx] * (M_tri / M_sub)  # rescale to preserve total area
        # Recompute the per-pair structures on subsampled triangles
        return _exact_Q_from_subsampled(
            normals_s,
            centroids_s,
            areas_s,
            k_hat,
            psi,
            element_index,
            n_tilde,
            sigma,
            freq_hz,
            n_elements,
        )
    else:
        # Full
        return _exact_Q_from_subsampled(
            normals,
            centroids,
            areas,
            k_hat,
            psi,
            element_index,
            n_tilde,
            sigma,
            freq_hz,
            n_elements,
        )


def _exact_Q_from_subsampled(
    normals: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    n_tilde: complex,
    sigma: float,
    freq_hz: float,
    n_elements: int,
) -> np.ndarray:
    """Exact-Lambda Q assembly on (sub)sampled triangles."""
    M_tri = normals.shape[0]
    N_paths = k_hat.shape[0]
    k0 = 2 * np.pi * freq_hz / C_0

    mu, t_s, t_p, e_s, e_p = compute_fresnel_operator(normals, k_hat, n_tilde)
    mu = np.asarray(mu)
    t_s = np.asarray(t_s)
    t_p = np.asarray(t_p)
    e_s = np.asarray(e_s)
    e_p = np.asarray(e_p)

    xi = np.asarray(xi_from_mu(mu, n_tilde))
    k0_xi = k0 * xi
    beta = np.real(k0_xi)
    alpha = -np.imag(k0_xi)
    alpha = np.maximum(alpha, 1e-30)

    psi_s = np.einsum("mnj,nj->mn", e_s, psi)
    psi_p = np.einsum("mnj,nj->mn", e_p, psi)
    F_psi = (t_s * psi_s)[:, :, None] * e_s + (t_p * psi_p)[:, :, None] * e_p  # (M, N, 3)

    phase_arg = -k0 * (centroids @ k_hat.T)
    surf_phase = np.exp(1j * phase_arg)  # (M, N)
    U = F_psi * surf_phase[:, :, None]  # (M, N, 3)

    # Pre-mask back-facing paths (transmission is zero -> already in F_psi)
    # Build N_paths x N_paths exposure-Gram per (chunked) triangles
    Q_path = np.zeros((N_paths, N_paths), dtype=complex)

    # Chunk over triangles to limit memory use
    chunk = max(1, min(M_tri, max(1, int(2e8 / (N_paths * N_paths)))))
    chunk = max(chunk, 1)
    for start in range(0, M_tri, chunk):
        stop = min(M_tri, start + chunk)
        a_chk = areas[start:stop][:, None, None]  # (cm, 1, 1)
        # Lambda_{m,n,n'} = 1 / (alpha_n + alpha_n' - j (beta_n' - beta_n))
        a1 = alpha[start:stop, :, None]  # (cm, N, 1)
        a2 = alpha[start:stop, None, :]  # (cm, 1, N)
        b1 = beta[start:stop, :, None]
        b2 = beta[start:stop, None, :]
        Lam = 1.0 / (a1 + a2 - 1j * (b2 - b1))  # (cm, N, N)
        # Inner products <U_n(m)*, U_n'(m)> = sum_j conj(U[m, n, j]) * U[m, n', j]
        Uchk = U[start:stop]  # (cm, N, 3)
        # G_pair[m, n, n'] = sum_j conj(U[m, n, j]) * U[m, n', j]
        G_pair = np.einsum("mnj,mkj->mnk", np.conj(Uchk), Uchk)  # (cm, N, N)
        # Sum over m with area * Lambda weighting
        Q_path += np.einsum("mab,mab,mab->ab", a_chk * np.ones_like(Lam), Lam, G_pair) * (sigma / 2.0)

    # Push N_paths x N_paths to M_ant x M_ant via element_index
    Q = np.zeros((n_elements, n_elements), dtype=complex)
    # Q[a, b] = sum_{n: j(n)=a, n': j(n')=b} Q_path[n, n'] but with the convention
    # P_abs = x^H Q x = sum_{a,b} conj(x_a) Q[a,b] x_b
    # The N x N Q_path was built with U not weighted by x, so: P_abs = sum_{n,n'}
    # conj(x_{j(n)}) x_{j(n')} Q_path[n, n'] (using <U_n*, U_{n'}> convention)
    # which gives Q[a, b] = sum_{n: j(n)=a} sum_{n': j(n')=b} Q_path[n, n']
    for n in range(N_paths):
        a = element_index[n]
        for nn in range(N_paths):
            b = element_index[nn]
            Q[a, b] += Q_path[n, nn]
    # Hermitian cleanup
    Q = (Q + np.conj(Q).T) / 2.0
    return Q


# ---------------------------------------------------------------------------
# Pareto sweep helpers
# ---------------------------------------------------------------------------


def absorbed_power(x: np.ndarray, Q: np.ndarray) -> float:
    return float(np.real(np.conj(x) @ Q @ x))


def signal_power(x: np.ndarray, h: np.ndarray) -> float:
    return float(np.abs(h @ x) ** 2)


def mrt_precoder(h: np.ndarray, P: float) -> np.ndarray:
    h_conj = np.conj(h)
    norm = np.linalg.norm(h_conj)
    if norm < 1e-30:
        x = np.zeros_like(h)
        x[0] = np.sqrt(P)
        return x
    return np.sqrt(P) * h_conj / norm


def gep_precoder(h: np.ndarray, Q: np.ndarray, P: float) -> np.ndarray:
    """Q^{-1} h*, scaled to ||x||^2 = P. Uses pseudo-inverse for safety."""
    eigvals, V = np.linalg.eigh(Q)
    eigvals = np.maximum(eigvals, 0.0)
    rank_tol = max(Q.shape) * np.finfo(eigvals.dtype).eps * float(eigvals.max(initial=0.0))
    inv = np.zeros_like(eigvals)
    mask = eigvals > rank_tol
    inv[mask] = 1.0 / eigvals[mask]
    Qinv_hconj = V @ np.diag(inv) @ V.conj().T @ np.conj(h)
    norm = np.linalg.norm(Qinv_hconj)
    if norm < 1e-30:
        return mrt_precoder(h, P)
    return np.sqrt(P) * Qinv_hconj / norm


def random_unit_precoders(n_samples: int, M_ant: int, P: float, rng: np.random.Generator) -> np.ndarray:
    """Random complex unit vectors on the M-sphere, scaled to ||x||^2 = P."""
    z = rng.standard_normal((n_samples, M_ant)) + 1j * rng.standard_normal((n_samples, M_ant))
    norms = np.linalg.norm(z, axis=1, keepdims=True)
    return np.sqrt(P) * z / norms


def random_phase_precoder(h: np.ndarray, P: float, rng: np.random.Generator, n_samples: int) -> np.ndarray:
    """Incoherent baseline: per-element MRT amplitudes but random phases.

    Decoheres the array. Returns (n_samples, M_ant) sample matrix.
    """
    M_ant = h.shape[0]
    amp = np.abs(h) / np.linalg.norm(h)  # MRT amplitudes
    phases = rng.uniform(0.0, 2 * np.pi, size=(n_samples, M_ant))
    return np.sqrt(P) * amp[None, :] * np.exp(1j * phases)


def ecbf_pareto_curve(
    h: np.ndarray, Q: np.ndarray, P: float, n_lambdas: int = 50
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sweep ECBF over a logarithmic ladder of P_abs_max values.

    Returns
    -------
    pabs : (n,) absorbed power per unit transmit power (scaled to P=1)
    psig : (n,) signal power per unit transmit power
    lambdas : (n,) the P_abs_max ladder used
    """
    # MRT bounds the ladder above; the GEP minimum bounds it below.
    x_mrt = mrt_precoder(h, P)
    p_abs_mrt = absorbed_power(x_mrt, Q)
    x_gep = gep_precoder(h, Q, P)
    p_abs_gep = absorbed_power(x_gep, Q)

    p_low = max(p_abs_gep, p_abs_mrt * 1e-4)
    p_high = p_abs_mrt
    if p_low >= p_high:
        p_low = p_high * 0.99
    p_abs_max_grid = np.geomspace(p_low * 1.001, p_high * 0.999, n_lambdas)
    pabs_arr = np.zeros(n_lambdas)
    psig_arr = np.zeros(n_lambdas)
    for i, p_max in enumerate(p_abs_max_grid):
        x_star = np.asarray(solve_ecbf(h, Q, p_max, P))
        pabs_arr[i] = absorbed_power(x_star, Q)
        psig_arr[i] = signal_power(x_star, h)
    return pabs_arr / P, psig_arr / P, p_abs_max_grid


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


@dataclass
class ScenarioData:
    bs_positions: np.ndarray
    body: BodyMesh
    k_hat: np.ndarray
    psi: np.ndarray
    element_index: np.ndarray
    delays: np.ndarray
    Q: np.ndarray
    Q_exact: np.ndarray | None
    eigenvalues: np.ndarray
    h: np.ndarray
    rho: float
    label: str = ""


def build_scenario(ue_position: np.ndarray, label: str, rng_seed: int,
                   max_triangles: int | None = None) -> ScenarioData:
    rng = np.random.default_rng(rng_seed)
    bs_positions = build_ura_positions(BS_CENTER, ARRAY_NX, ARRAY_NY, SPACING)
    body = load_thelonious(max_triangles=max_triangles or MAX_TRIANGLES)
    p_per_elem = P_TX_W / M_ANT  # per-element baseline transmit power for path amplitude
    k_hat, psi, elem_idx, delays = synthetic_paths_for_target(
        bs_positions,
        ue_position,
        N_CLUSTERS,
        CONE_HALF_ANGLE_DEG,
        p_per_elem,
        rng,
    )
    G_tilde = compute_body_channel(
        body.normals,
        body.centroids,
        k_hat,
        psi,
        elem_idx,
        N_TILDE,
        SKIN_SIGMA,
        FREQ_HZ,
        n_elements=M_ANT,
    )
    Q = np.asarray(compute_exposure_operator(G_tilde, body.areas))
    eigvals, _ = eigendecompose_Q(Q)
    eigvals = np.asarray(eigvals)
    h = channel_h_from_paths(k_hat, psi, elem_idx, ue_position, M_ANT)
    rho_val = compute_rho(h, Q, lambda_max=float(eigvals[0]))
    return ScenarioData(
        bs_positions=bs_positions,
        body=body,
        k_hat=k_hat,
        psi=psi,
        element_index=elem_idx,
        delays=delays,
        Q=Q,
        Q_exact=None,
        eigenvalues=eigvals,
        h=h,
        rho=rho_val,
        label=label,
    )


# ---------------------------------------------------------------------------
# Figure 1: approximation error budget
# ---------------------------------------------------------------------------


def figure_approx_error(scenario: ScenarioData) -> dict:
    """Compute exact-Lambda Q on a smaller path subset, compare to Approx-2 Q.

    Full scenario has N=2560 paths -> exact-Lambda would need 2560^2 storage
    on ~3000 triangles ~ 18 GB. Subsample paths to N_sub ~ 256 per scenario
    while keeping exact-Lambda tractable.
    """
    print("Figure 1: approximation error budget...")
    rng = np.random.default_rng(2026)
    body = scenario.body
    # Subsample paths uniformly
    N_total = scenario.k_hat.shape[0]
    N_sub = min(256, N_total)
    sub_idx = rng.choice(N_total, size=N_sub, replace=False)
    sub_idx.sort()
    k_hat_sub = scenario.k_hat[sub_idx]
    psi_sub = scenario.psi[sub_idx]
    elem_sub = scenario.element_index[sub_idx]

    # Approx-2 Q on the subsampled paths
    G_tilde_sub = compute_body_channel(
        body.normals,
        body.centroids,
        k_hat_sub,
        psi_sub,
        elem_sub,
        N_TILDE,
        SKIN_SIGMA,
        FREQ_HZ,
        M_ANT,
    )
    Q_approx = np.asarray(compute_exposure_operator(G_tilde_sub, body.areas))
    # Exact-Lambda Q on the same paths
    t0 = time.time()
    Q_exact = compute_exposure_operator_exact(
        body.normals,
        body.centroids,
        body.areas,
        k_hat_sub,
        psi_sub,
        elem_sub,
        N_TILDE,
        SKIN_SIGMA,
        FREQ_HZ,
        M_ANT,
    )
    t_exact = time.time() - t0
    print(f"  exact-Lambda Q took {t_exact:.1f} s")

    # Errors
    delta = Q_exact - Q_approx
    err_frob = float(np.linalg.norm(delta) / np.linalg.norm(Q_exact))
    err_spec = float(np.linalg.norm(delta, ord=2) / np.linalg.norm(Q_exact, ord=2))

    eigvals_exact = np.linalg.eigvalsh(Q_exact)[::-1]
    eigvals_approx = np.linalg.eigvalsh(Q_approx)[::-1]
    eigvals_exact = np.maximum(eigvals_exact, 0.0)
    eigvals_approx = np.maximum(eigvals_approx, 0.0)
    rel_eig_err = np.abs(eigvals_exact - eigvals_approx) / np.maximum(eigvals_exact, 1e-30)

    # Figure
    fig, ax = plt.subplots(figsize=(5.2, 3.2), dpi=150)
    nz = eigvals_exact > eigvals_exact.max() * 1e-6
    ax.semilogy(np.arange(M_ANT)[nz], np.abs(rel_eig_err[nz]) * 100, "o-", color="C0", lw=1.2, ms=4)
    ax.axhline(5.0, ls="--", color="C3", lw=1.0, label="5% bound (paper claim)")
    ax.set_xlabel(r"Eigenvalue index $k$")
    ax.set_ylabel(r"$|\lambda_k(Q_{\rm exact}) - \lambda_k(Q_{\rm approx})| / \lambda_k(Q_{\rm exact})$ [%]")
    ax.set_title(
        rf"$\| \Delta Q \|_F / \| Q \|_F = {err_frob*100:.2f}\%$"
        rf" (spectral: ${err_spec*100:.2f}\%$, $N={N_sub}$ paths)"
    )
    ax.legend(loc="best")
    ax.grid(True, which="both", ls=":", lw=0.5)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "approx_error_budget.pdf")
    fig.savefig(OUT_DIR / "approx_error_budget.png", dpi=180)
    plt.close(fig)
    print(f"  Frob rel err = {err_frob*100:.3f}%, spectral rel err = {err_spec*100:.3f}%")
    return {
        "frobenius_rel_error_pct": err_frob * 100,
        "spectral_rel_error_pct": err_spec * 100,
        "max_eigenvalue_rel_error_pct": float(np.max(rel_eig_err[nz]) * 100) if np.any(nz) else 0.0,
        "n_paths_subsampled": int(N_sub),
        "exact_lambda_seconds": float(t_exact),
    }


# ---------------------------------------------------------------------------
# Figure 2: ECBF Pareto
# ---------------------------------------------------------------------------


def figure_ecbf_pareto(s_a: ScenarioData, s_b: ScenarioData) -> dict:
    print("Figure 2: ECBF Pareto curve...")
    rng = np.random.default_rng(31415)
    P = 1.0  # transmit-power normalisation
    summary = {}

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0), dpi=150, sharey=True)
    for ax, scenario, label in zip(
        axes,
        (s_a, s_b),
        ("(a) UE at (0, 5, 1) m – aligned", "(b) UE at (0, -5, 1) m – protected"),
        strict=True,
    ):
        Q = scenario.Q
        h = scenario.h

        # ECBF curve
        pabs_curve, psig_curve, _ = ecbf_pareto_curve(h, Q, P, n_lambdas=50)

        # MRT
        x_mrt = mrt_precoder(h, P)
        pabs_mrt, psig_mrt = absorbed_power(x_mrt, Q) / P, signal_power(x_mrt, h) / P

        # GEP
        x_gep = gep_precoder(h, Q, P)
        pabs_gep, psig_gep = absorbed_power(x_gep, Q) / P, signal_power(x_gep, h) / P

        # Random precoder cloud
        x_rand = random_unit_precoders(200, M_ANT, P, rng)
        pabs_rand = np.array([absorbed_power(x, Q) for x in x_rand]) / P
        psig_rand = np.array([signal_power(x, h) for x in x_rand]) / P

        # Incoherent baseline (random phases per element)
        x_inc = random_phase_precoder(h, P, rng, 200)
        pabs_inc = np.array([absorbed_power(x, Q) for x in x_inc]) / P
        psig_inc = np.array([signal_power(x, h) for x in x_inc]) / P

        # Plot
        ax.scatter(pabs_rand, psig_rand, s=8, alpha=0.25, color="0.65", label="Random precoders (200)")
        ax.scatter(pabs_inc, psig_inc, s=8, alpha=0.45, color="C2", label="Incoherent (random phases)")
        ax.plot(pabs_curve, psig_curve, "-", color="C0", lw=1.6, label="ECBF Pareto family")
        ax.scatter([pabs_mrt], [psig_mrt], s=80, marker="*", color="C3", zorder=5, label="MRT (max signal)")
        ax.scatter([pabs_gep], [psig_gep], s=80, marker="D", color="C1", zorder=5, label="GEP (min ratio)")

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"Absorbed body power $x^H Q x / P$  [W/W]")
        if ax is axes[0]:
            ax.set_ylabel(r"Received signal $|h^T x|^2 / P$")
        ax.set_title(label, fontsize=10)
        ax.grid(True, which="both", ls=":", lw=0.4)
        ax.legend(fontsize=7.5, loc="lower right", framealpha=0.85)

        # Headline metric: ECBF dB savings at half MRT signal power
        target_psig = psig_mrt / 2.0
        # Find ECBF point with psig closest to target_psig
        idx = np.argmin(np.abs(psig_curve - target_psig))
        savings_dB = 10 * np.log10(pabs_mrt / max(pabs_curve[idx], 1e-30))
        summary[f"{scenario.label}_pabs_mrt"] = pabs_mrt
        summary[f"{scenario.label}_psig_mrt"] = psig_mrt
        summary[f"{scenario.label}_pabs_gep"] = pabs_gep
        summary[f"{scenario.label}_savings_dB_at_half_signal"] = float(savings_dB)
        summary[f"{scenario.label}_rho"] = scenario.rho
        summary[f"{scenario.label}_lambda_max_Q"] = float(scenario.eigenvalues[0])

    fig.suptitle("Coherent MIMO ECBF Pareto: signal power vs whole-body absorbed power", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "ecbf_pareto.pdf")
    fig.savefig(OUT_DIR / "ecbf_pareto.png", dpi=180)
    plt.close(fig)
    print(f"  rho_aligned = {s_a.rho:.4f}, rho_protected = {s_b.rho:.4f}")
    return summary


# ---------------------------------------------------------------------------
# Figure 3: rho landscape
# ---------------------------------------------------------------------------


def figure_rho_landscape(scenario_template: ScenarioData) -> dict:
    print("Figure 3: rho landscape...")
    # Use lower-resolution mesh for sweep speed (231 sims; geometric content is preserved)
    body = load_thelonious(max_triangles=2000)
    bs_positions = scenario_template.bs_positions

    xs = np.linspace(-1.0, 1.0, 11)
    ys = np.linspace(-2.0, 5.0, 21)
    rho_grid = np.zeros((len(ys), len(xs)))
    pabs_grid = np.zeros_like(rho_grid)

    rng = np.random.default_rng(2024)
    p_per_elem = P_TX_W / M_ANT
    P = 1.0

    # Reuse Q from a single representative path realisation rather than rebuilding
    # per UE position (paths depend on UE LOS direction; the canonical scenario does
    # rebuild paths per UE). For sensible computation budget, build new paths/Q
    # only at each grid point but reuse mesh.
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            ue = np.array([x, y, 1.0])
            sub_rng = np.random.default_rng(10000 + 100 * j + i)
            k_hat, psi, elem_idx, _ = synthetic_paths_for_target(
                bs_positions, ue, N_CLUSTERS, CONE_HALF_ANGLE_DEG, p_per_elem, sub_rng
            )
            G_tilde = compute_body_channel(
                body.normals,
                body.centroids,
                k_hat,
                psi,
                elem_idx,
                N_TILDE,
                SKIN_SIGMA,
                FREQ_HZ,
                M_ANT,
            )
            Q = np.asarray(compute_exposure_operator(G_tilde, body.areas))
            eigvals = np.linalg.eigvalsh(Q)[::-1]
            h = channel_h_from_paths(k_hat, psi, elem_idx, ue, M_ANT)
            rho = compute_rho(h, Q, lambda_max=float(eigvals[0]))
            x_mrt = mrt_precoder(h, P)
            pabs = absorbed_power(x_mrt, Q)
            rho_grid[j, i] = rho
            pabs_grid[j, i] = pabs

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.5), dpi=150)
    extent = [xs.min(), xs.max(), ys.min(), ys.max()]
    im0 = axes[0].imshow(
        rho_grid, origin="lower", extent=extent, aspect="auto", cmap="viridis", vmin=0, vmax=rho_grid.max()
    )
    axes[0].set_title(r"$\rho$ (signal–exposure alignment)")
    axes[0].set_xlabel("UE x [m]")
    axes[0].set_ylabel("UE y [m]")
    plt.colorbar(im0, ax=axes[0], shrink=0.85)

    im1 = axes[1].imshow(
        pabs_grid,
        origin="lower",
        extent=extent,
        aspect="auto",
        cmap="magma",
        norm=LogNorm(vmin=max(pabs_grid.min(), 1e-12), vmax=pabs_grid.max()),
    )
    axes[1].set_title(r"$P_{\rm abs}$ under MRT [W/W]")
    axes[1].set_xlabel("UE x [m]")
    plt.colorbar(im1, ax=axes[1], shrink=0.85)

    # Phantom silhouette: project body footprint onto xy plane (top-down view)
    bb_min, bb_max = body.bounding_box
    for ax in axes:
        # Phantom is centred at (0,0) in xy after translation
        ax.add_patch(
            plt.Rectangle(
                (bb_min[0], bb_min[1]),
                bb_max[0] - bb_min[0],
                bb_max[1] - bb_min[1],
                linewidth=1.3,
                edgecolor="white",
                facecolor="none",
                ls="-",
            )
        )
        # BS marker
        ax.plot([BS_CENTER[0]], [BS_CENTER[1]], marker="s", color="cyan", ms=8, mec="black")
        ax.annotate("BS", (BS_CENTER[0], BS_CENTER[1]), color="cyan", fontsize=8, xytext=(6, 6),
                    textcoords="offset points")
        # UE markers
        ax.plot([UE_FRONT[0]], [UE_FRONT[1]], marker="^", color="red", ms=9, mec="white")
        ax.annotate("UE (a)", (UE_FRONT[0], UE_FRONT[1]), color="red", fontsize=8,
                    xytext=(6, 6), textcoords="offset points")
        ax.plot([UE_BEHIND[0]], [UE_BEHIND[1]], marker="v", color="orange", ms=9, mec="white")
        ax.annotate("UE (b)", (UE_BEHIND[0], UE_BEHIND[1]), color="orange", fontsize=8,
                    xytext=(6, 6), textcoords="offset points")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "rho_landscape.pdf")
    fig.savefig(OUT_DIR / "rho_landscape.png", dpi=180)
    plt.close(fig)
    rho_at_a = float(rho_grid[np.argmin(np.abs(ys - UE_FRONT[1])), np.argmin(np.abs(xs - UE_FRONT[0]))])
    rho_at_b = float(rho_grid[np.argmin(np.abs(ys - UE_BEHIND[1])), np.argmin(np.abs(xs - UE_BEHIND[0]))])
    print(f"  rho range: [{rho_grid.min():.3f}, {rho_grid.max():.3f}]")
    return {
        "rho_min": float(rho_grid.min()),
        "rho_max": float(rho_grid.max()),
        "rho_mean": float(rho_grid.mean()),
        "rho_at_UE_front": rho_at_a,
        "rho_at_UE_behind": rho_at_b,
        "n_grid_points": int(rho_grid.size),
    }


# ---------------------------------------------------------------------------
# Figure 4: hotspot pair
# ---------------------------------------------------------------------------


def figure_hotspot_pair(scenario: ScenarioData) -> dict:
    print("Figure 4: MRT vs ECBF hotspot pair...")
    # For visualisation use a denser mesh than the simulation mesh.
    body = load_thelonious(max_triangles=12000)
    P = 1.0
    h = scenario.h
    Q = scenario.Q

    # MRT
    x_mrt = mrt_precoder(h, P)
    p_abs_mrt = absorbed_power(x_mrt, Q)

    # Compute MRT-driven sab map on the dense body
    G_tilde = compute_body_channel(
        body.normals,
        body.centroids,
        scenario.k_hat,
        scenario.psi,
        scenario.element_index,
        N_TILDE,
        SKIN_SIGMA,
        FREQ_HZ,
        M_ANT,
    )
    sab_mrt = np.real(np.einsum("mia,a->mi", G_tilde, x_mrt))
    sab_mrt_imag = np.imag(np.einsum("mia,a->mi", G_tilde, x_mrt))
    field_mrt = np.einsum("mia,a->mi", G_tilde, x_mrt)
    sab_mrt = np.real(np.sum(np.conj(field_mrt) * field_mrt, axis=1))

    # ECBF at 50% MRT signal power -> equivalently, at the P_abs that gives
    # |h^T x_ECBF|^2 = 0.5 * |h^T x_MRT|^2.
    # Use bisection over the lambda parameter via solve_ecbf with a sweep.
    psig_mrt = signal_power(x_mrt, h)
    target_psig = 0.5 * psig_mrt

    # ECBF Pareto sweep at fine granularity in the lower P_abs region
    pabs_curve, psig_curve, p_max_grid = ecbf_pareto_curve(h, Q, P, n_lambdas=80)
    idx = int(np.argmin(np.abs(psig_curve - target_psig)))
    p_abs_target = pabs_curve[idx] * P
    x_ecbf = np.asarray(solve_ecbf(h, Q, p_abs_target, P))
    p_abs_ecbf = absorbed_power(x_ecbf, Q)
    psig_ecbf = signal_power(x_ecbf, h)

    field_ecbf = np.einsum("mia,a->mi", G_tilde, x_ecbf)
    sab_ecbf = np.real(np.sum(np.conj(field_ecbf) * field_ecbf, axis=1))

    # Render: top-down view (looking down -z) and front view (looking +y).
    centroids = body.centroids
    vmax = float(max(sab_mrt.max(), sab_ecbf.max()))
    vmin = max(vmax * 1e-3, 1e-12)

    fig = plt.figure(figsize=(11.0, 5.5), dpi=150)
    titles = [
        f"MRT: $P_{{abs}}$ = {p_abs_mrt:.3e} W, $S$ = {psig_mrt:.3e}",
        f"ECBF (50% signal): $P_{{abs}}$ = {p_abs_ecbf:.3e} W, $S$ = {psig_ecbf:.3e}",
    ]
    for col, (sab, title) in enumerate(zip([sab_mrt, sab_ecbf], titles, strict=True)):
        # Front view (xz plane) -- project onto x and z
        ax_front = fig.add_subplot(2, 2, col + 1)
        sc = ax_front.scatter(
            centroids[:, 0], centroids[:, 2], c=sab, cmap="inferno", s=2,
            norm=LogNorm(vmin=vmin, vmax=vmax),
        )
        ax_front.set_aspect("equal")
        ax_front.set_xlabel("x [m]")
        ax_front.set_ylabel("z [m]")
        ax_front.set_title(title + "\nFront view (xz)", fontsize=9)
        plt.colorbar(sc, ax=ax_front, label=r"$S_{ab}$ [W/m$^2$]", shrink=0.85)

        # Side view (yz plane)
        ax_side = fig.add_subplot(2, 2, col + 3)
        sc = ax_side.scatter(
            centroids[:, 1], centroids[:, 2], c=sab, cmap="inferno", s=2,
            norm=LogNorm(vmin=vmin, vmax=vmax),
        )
        ax_side.set_aspect("equal")
        ax_side.set_xlabel("y [m]")
        ax_side.set_ylabel("z [m]")
        ax_side.set_title("Side view (yz)", fontsize=9)
        plt.colorbar(sc, ax=ax_side, label=r"$S_{ab}$ [W/m$^2$]", shrink=0.85)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "hotspot_pair.pdf")
    fig.savefig(OUT_DIR / "hotspot_pair.png", dpi=180)
    plt.close(fig)

    # Peak displacement: where on the body each peaks
    peak_mrt = centroids[int(np.argmax(sab_mrt))]
    peak_ecbf = centroids[int(np.argmax(sab_ecbf))]
    displacement = float(np.linalg.norm(peak_mrt - peak_ecbf))
    print(f"  P_abs MRT={p_abs_mrt:.3e} W, ECBF={p_abs_ecbf:.3e} W, "
          f"reduction={10*np.log10(p_abs_mrt/p_abs_ecbf):.1f} dB")
    return {
        "pabs_mrt": float(p_abs_mrt),
        "pabs_ecbf_50pct": float(p_abs_ecbf),
        "psig_mrt": float(psig_mrt),
        "psig_ecbf_50pct": float(psig_ecbf),
        "ecbf_dB_reduction_at_50pct_signal": float(10 * np.log10(p_abs_mrt / max(p_abs_ecbf, 1e-30))),
        "peak_mrt_xyz": peak_mrt.tolist(),
        "peak_ecbf_xyz": peak_ecbf.tolist(),
        "peak_displacement_m": displacement,
        "sab_max_mrt": float(sab_mrt.max()),
        "sab_max_ecbf": float(sab_ecbf.max()),
    }


# ---------------------------------------------------------------------------
# Figure 5: spectrum
# ---------------------------------------------------------------------------


def figure_spectrum(scenario_template: ScenarioData, ue_position: np.ndarray) -> dict:
    print("Figure 5: M*P spectrum sweep over N...")
    # Smaller mesh for the spectrum sweep so 200 paths/element fits in memory
    body = load_thelonious(max_triangles=2000)
    bs_positions = scenario_template.bs_positions
    p_per_elem = P_TX_W / M_ANT

    Ns = [10, 30, 60, 100]  # paths per element
    fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=150)
    eff_ranks = {}
    for n_per in Ns:
        rng = np.random.default_rng(7 * n_per + 13)
        k_hat, psi, elem_idx, _ = synthetic_paths_for_target(
            bs_positions, ue_position, n_per, CONE_HALF_ANGLE_DEG, p_per_elem, rng
        )
        G_tilde = compute_body_channel(
            body.normals,
            body.centroids,
            k_hat,
            psi,
            elem_idx,
            N_TILDE,
            SKIN_SIGMA,
            FREQ_HZ,
            M_ANT,
        )
        Q_n = np.asarray(compute_exposure_operator(G_tilde, body.areas))
        eigvals = np.linalg.eigvalsh(Q_n)[::-1]
        eigvals = np.maximum(eigvals, 0.0)
        cumfrac = np.cumsum(eigvals) / max(np.sum(eigvals), 1e-30)
        ax.plot(np.arange(1, M_ANT + 1), cumfrac, label=f"N/elem = {n_per}", lw=1.4)
        # Effective rank: smallest k s.t. cumfrac[k-1] >= 0.99
        eff_rank = int(np.searchsorted(cumfrac, 0.99) + 1)
        eff_ranks[n_per] = eff_rank
        print(f"  N/elem={n_per}: eff_rank(99%) = {eff_rank}")

    ax.axhline(0.99, ls="--", color="0.5", lw=0.8)
    ax.set_xlabel("Eigenvalue rank $k$")
    ax.set_ylabel(r"Cumulative fraction $\sum_{i\leq k}\lambda_i / \mathrm{tr}(Q)$")
    ax.set_title(f"Effective rank of Q ({M_ANT}-element URA)")
    ax.legend(fontsize=8)
    ax.grid(True, ls=":", lw=0.5)
    ax.set_xlim(1, M_ANT)
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "spectrum.pdf")
    fig.savefig(OUT_DIR / "spectrum.png", dpi=180)
    plt.close(fig)
    return {f"effective_rank_99pct_N{n}": v for n, v in eff_ranks.items()}


# ---------------------------------------------------------------------------
# Save raw + summary
# ---------------------------------------------------------------------------


def save_raw_data(s_a: ScenarioData, s_b: ScenarioData) -> None:
    np.savez_compressed(
        OUT_DIR / "paperC_results.npz",
        Q_a=s_a.Q,
        Q_b=s_b.Q,
        h_a=s_a.h,
        h_b=s_b.h,
        eig_a=s_a.eigenvalues,
        eig_b=s_b.eigenvalues,
        k_hat_a=s_a.k_hat,
        k_hat_b=s_b.k_hat,
        psi_a=s_a.psi,
        psi_b=s_b.psi,
        elem_idx_a=s_a.element_index,
        elem_idx_b=s_b.element_index,
        bs_positions=s_a.bs_positions,
        ue_a=UE_FRONT,
        ue_b=UE_BEHIND,
        bs_center=BS_CENTER,
        freq_hz=FREQ_HZ,
        skin_eps_r=SKIN_EPS_R,
        skin_sigma=SKIN_SIGMA,
        n_tilde=N_TILDE,
        n_clusters=N_CLUSTERS,
        cone_half_angle_deg=CONE_HALF_ANGLE_DEG,
    )


def write_summary_csv(rows: list[tuple[str, str, float | str]]) -> None:
    """rows: list of (figure, key, value)."""
    with open(OUT_DIR / "paperC_summary.csv", "w") as f:
        f.write("figure,key,value\n")
        for fig_name, key, val in rows:
            f.write(f"{fig_name},{key},{val}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 72)
    print("Paper C canonical scenario simulator")
    print(f"Output directory: {OUT_DIR}")
    print(f"Frequency: {FREQ_HZ/1e9:.1f} GHz, lambda = {LAMBDA*1000:.2f} mm")
    print(f"Array: {ARRAY_NX}x{ARRAY_NY} URA at lambda/2 = {SPACING*1000:.2f} mm spacing")
    print(f"BS at {BS_CENTER}, UE_a={UE_FRONT}, UE_b={UE_BEHIND}")
    print(f"Skin tissue: eps_r={SKIN_EPS_R}, sigma={SKIN_SIGMA} S/m, n_tilde={N_TILDE:.2f}")
    print(f"Paths: {N_CLUSTERS}/element, cone half-angle {CONE_HALF_ANGLE_DEG} deg")
    print("=" * 72)

    rows: list[tuple[str, str, float | str]] = []

    # Build both scenarios
    print("\nBuilding scenario A (UE in front)...")
    s_a = build_scenario(UE_FRONT, label="aligned", rng_seed=42)
    print(f"  rho_a = {s_a.rho:.4f}, lambda_max(Q) = {s_a.eigenvalues[0]:.3e}")
    print("Building scenario B (UE behind, geometrically protected)...")
    s_b = build_scenario(UE_BEHIND, label="protected", rng_seed=43)
    print(f"  rho_b = {s_b.rho:.4f}, lambda_max(Q) = {s_b.eigenvalues[0]:.3e}")

    # Figure 2 first (most important)
    pareto_meta = figure_ecbf_pareto(s_a, s_b)
    for k, v in pareto_meta.items():
        rows.append(("ecbf_pareto", k, v))

    # Save raw early, in case later figures fail
    save_raw_data(s_a, s_b)

    # Figure 5 (spectrum)
    spec_meta = figure_spectrum(s_a, UE_FRONT)
    for k, v in spec_meta.items():
        rows.append(("spectrum", k, v))

    # Figure 4 (hotspot pair, scenario A)
    hot_meta = figure_hotspot_pair(s_a)
    for k, v in hot_meta.items():
        rows.append(("hotspot_pair", k, v if not isinstance(v, list) else json.dumps(v)))

    # Figure 1 (approximation error budget) -- can be slow
    try:
        approx_meta = figure_approx_error(s_a)
        for k, v in approx_meta.items():
            rows.append(("approx_error", k, v))
    except Exception as e:
        print(f"  WARNING: approx error budget failed: {e}")
        rows.append(("approx_error", "error", str(e)))

    # Figure 3 (rho landscape) -- second-priority but cheap
    try:
        rho_meta = figure_rho_landscape(s_a)
        for k, v in rho_meta.items():
            rows.append(("rho_landscape", k, v))
    except Exception as e:
        print(f"  WARNING: rho landscape failed: {e}")
        rows.append(("rho_landscape", "error", str(e)))

    write_summary_csv(rows)
    print("\nAll figures generated.")


if __name__ == "__main__":
    main()
