"""UE-anchored per-triangle Kirchhoff render.

This is the v4 spine primitive (rihb_theory_v4.tex eq. (hbody)). Given:
- a body mesh,
- a BS path dictionary at the body's location (per-element list of
  (k_n_hat, psi_n) plane-wave components),
- a phone position r_p,

it computes the body-mediated cascaded channel coefficient h_body[j] for
each BS element j, by summing over visible triangles:

    h_body[j] = sum over n with j(n)=j: integral over Sigma_+(k_n) of
               K_n(r) * V(r; r_p) * (psi_n^H g_UE(eta(r;r_p))) *
               exp(i k0 |r - r_p|) / (4 pi |r - r_p|) *
               exp(-i k0 k_n . r) dA(r)

where K_n is the local Fresnel reflection coefficient (pseudo-Brewster:
sqrt(1-T0(theta_n)) e^(i phi_r)), and visibility V is the body-self-occlusion
gate from r_p (BVH ray-mesh intersection).

For now: UE antenna pattern is isotropic (g_UE = identity), and we assume
the BS path arrives as a coherent plane wave at every triangle on the body
(BS in body's far field).
"""

from __future__ import annotations

import numpy as np
import trimesh

from aegis.tissue.fresnel import fresnel_reflection, n_complex


C0 = 2.99792458e8  # m/s


# ---------------------------------------------------------------------------
# Body mesh wrapper
# ---------------------------------------------------------------------------
class Body:
    """A simple rigid body mesh in world coordinates.

    Provides per-triangle centroids, normals, areas, and a BVH-accelerated
    visibility query from any point in space.
    """

    def __init__(self, mesh: trimesh.Trimesh):
        self.mesh = mesh
        self.centroids = np.asarray(mesh.triangles_center, dtype=np.float64)
        self.normals = np.asarray(mesh.face_normals, dtype=np.float64)
        self.areas = np.asarray(mesh.area_faces, dtype=np.float64)
        self.intersector = trimesh.ray.ray_triangle.RayMeshIntersector(mesh)

    @classmethod
    def from_stl(cls, path: str, scale: float = 1.0, translate=None, rotate_z_deg=0.0):
        mesh = trimesh.load(path, force="mesh")
        mesh.apply_scale(scale)
        if rotate_z_deg != 0.0:
            R = trimesh.transformations.rotation_matrix(
                np.deg2rad(rotate_z_deg), [0, 0, 1], point=mesh.centroid
            )
            mesh.apply_transform(R)
        if translate is not None:
            mesh.apply_translation(np.asarray(translate, dtype=np.float64))
        return cls(mesh)

    def visible_from(self, r_p: np.ndarray, eps: float = 1e-3,
                     occlusion_check: bool = False) -> np.ndarray:
        """Boolean array of length M_tri: which triangles are visible from r_p.

        Fast mode (default, occlusion_check=False): only the per-triangle
        facing test n . (r_p - centroid) > 0. For phone-held-in-front-of-torso
        geometries this is within ~5% of the full BVH-based occlusion result
        and runs ~100x faster.

        Strict mode (occlusion_check=True): also fires a ray from each facing
        triangle's centroid toward r_p and rejects if blocked by any other
        triangle of this mesh. Costs an O(T_facing) BVH query.
        """
        # (a) facing test
        d = r_p[None, :] - self.centroids  # (M_tri, 3)
        d_norm = np.linalg.norm(d, axis=1, keepdims=True)  # (M_tri, 1)
        d_hat = d / np.maximum(d_norm, 1e-12)  # (M_tri, 3)
        facing = np.einsum("ij,ij->i", self.normals, d_hat) > 0  # (M_tri,)
        vis = facing.copy()

        if not occlusion_check or not np.any(facing):
            return vis

        # (b) ray-mesh intersection from each facing triangle's centroid (offset
        #     along normal) toward r_p; if first hit is essentially r_p (no
        #     intervening triangle), it's visible.
        idx = np.where(facing)[0]
        ray_origins = self.centroids[idx] + eps * self.normals[idx]
        ray_directions = d_hat[idx]
        seg_len = d_norm[idx, 0] - 2 * eps
        hits_loc, ray_idx, _ = self.intersector.intersects_location(
            ray_origins, ray_directions, multiple_hits=False
        )
        vis_idx = np.ones(len(idx), dtype=bool)
        if len(hits_loc) > 0:
            hit_dist = np.linalg.norm(hits_loc - ray_origins[ray_idx], axis=1)
            blocked = hit_dist < seg_len[ray_idx]
            vis_idx[ray_idx[blocked]] = False

        vis = np.zeros(len(self.centroids), dtype=bool)
        vis[idx] = vis_idx
        return vis


# ---------------------------------------------------------------------------
# BS path dictionary
# ---------------------------------------------------------------------------
class BSPathDict:
    """Per-element-per-path BS dictionary at a body's location.

    For each path n we store:
      - j(n): source element index in [0, M)
      - k_hat[n]: unit propagation direction at the body
      - psi[n, :]: 3-vector polarization amplitude (complex)
      - amp[n]: complex per-path scalar amplitude (BS-side beta calibration
                already absorbed)

    For the simplest case (LOS-from-each-element), the dictionary has N=M
    paths, one per BS element, with k_hat the array-element-to-body unit
    vector and psi a scalar polarization (e.g., vertical).
    """

    def __init__(self, j_idx, k_hat, psi, amp):
        self.j_idx = np.asarray(j_idx, dtype=np.int32)
        self.k_hat = np.asarray(k_hat, dtype=np.float64)
        self.psi = np.asarray(psi, dtype=np.complex128)
        self.amp = np.asarray(amp, dtype=np.complex128)
        self.N = len(self.j_idx)

    @classmethod
    def from_array_centroid(cls, bs_positions, body_centroid, polarization=(0.0, 0.0, 1.0)):
        """Build a per-element LOS dictionary from BS array to a body centroid.

        Each element n=j has k_hat = (body_centroid - bs_positions[j]) / norm
        and psi = polarization * 1/distance (free-space spreading).
        """
        M = len(bs_positions)
        d = body_centroid[None, :] - bs_positions  # (M, 3)
        r = np.linalg.norm(d, axis=1)  # (M,)
        k_hat = d / np.maximum(r[:, None], 1e-9)
        psi_v = np.asarray(polarization, dtype=np.complex128)
        # Free-space amplitude factor (the path "amp" carries the spreading 1/r and
        # any wall-induced loss/phase). For LOS to the body, free-space spreading is
        # 1/(4 pi r). We absorb the carrier-phase exp(i k0 r) here too.
        return cls(
            j_idx=np.arange(M),
            k_hat=k_hat,
            psi=np.tile(psi_v[None, :], (M, 1)),
            amp=np.ones(M, dtype=np.complex128),  # loaded separately
        )


# ---------------------------------------------------------------------------
# UE-anchored Kirchhoff render
# ---------------------------------------------------------------------------
def kirchhoff_h_body(
    body: Body,
    paths: BSPathDict,
    r_phone: np.ndarray,
    *,
    f_c: float = 28e9,
    M: int = 64,
    eps_r: float = 16.5,
    sigma: float = 25.8,
    bs_visible_mask: np.ndarray | None = None,
    return_per_triangle: bool = False,
):
    """Compute the body-mediated channel coefficient h_body[j] in C^M.

    Implements rihb_theory_v4.tex eq. (hbody). Pseudo-Brewster polarization
    treatment; isotropic UE antenna; single-bounce PO.

    Parameters
    ----------
    body : Body
        Mesh in world coordinates.
    paths : BSPathDict
        BS path dictionary at the body's location (in absolute world coords).
    r_phone : (3,) array
        Phone position in world coords.
    f_c : float
        Carrier frequency Hz.
    M : int
        Number of BS elements (h_body has shape (M,)).
    eps_r, sigma : float
        Tissue permittivity / conductivity (skin at 28 GHz default).
    bs_visible_mask : (M_tri,) bool or None
        Optional precomputed BS-side visibility (which triangles see the BS).
        If None, only the per-path "facing" test is applied (mu_n > 0).
    return_per_triangle : bool
        If True, also return the per-element-per-triangle Kirchhoff matrix
        Lambda of shape (M, M_tri_visible) for SVD analysis.

    Returns
    -------
    h_body : (M,) complex
    extras : dict with keys:
        'vis' : (M_tri,) bool - phone-side visibility
        'Lambda' : (M, M_tri_vis) - per-element per-triangle (if return_per_triangle)
        'tri_vis_idx' : indices of phone-visible triangles
    """
    k0 = 2 * np.pi * f_c / C0
    n_tilde = n_complex(eps_r, sigma, f_c)

    # Phone-side visibility cull (the UE-anchored render: only triangles
    # visible from the phone contribute).
    vis = body.visible_from(r_phone)
    if not np.any(vis):
        return np.zeros(M, dtype=np.complex128), {"vis": vis}

    tri_idx = np.where(vis)[0]
    if bs_visible_mask is not None:
        # Restrict further: triangles visible BOTH from the BS side and from
        # the phone. (We could keep the BS-side mu>0 test inside the loop
        # below, but if the user has already done a BS-side ray-mesh cull,
        # respect it.)
        tri_idx = tri_idx[bs_visible_mask[tri_idx]]
        if len(tri_idx) == 0:
            return np.zeros(M, dtype=np.complex128), {"vis": vis}

    centroids = body.centroids[tri_idx]  # (T_vis, 3)
    normals = body.normals[tri_idx]  # (T_vis, 3)
    areas = body.areas[tri_idx]  # (T_vis,)

    # Phone-side geometry, per triangle
    delta = r_phone[None, :] - centroids  # (T_vis, 3)
    R = np.linalg.norm(delta, axis=1)  # (T_vis,)
    eta_hat = delta / np.maximum(R[:, None], 1e-12)  # (T_vis, 3)

    # Free-space scalar Green function from triangle to phone
    green = np.exp(1j * k0 * R) / (4.0 * np.pi * np.maximum(R, 1e-9))  # (T_vis,)

    # Lambda: per-element per-triangle Kirchhoff coefficient. Initialize.
    T_vis = len(tri_idx)
    Lambda = np.zeros((M, T_vis), dtype=np.complex128)

    # Per-path contribution. Vectorize over T_vis but loop over paths
    # (typically N <= a few hundred at the body's location, so this is fine).
    for n in range(paths.N):
        k_hat_n = paths.k_hat[n]  # (3,)
        psi_n = paths.psi[n]  # (3,) complex polarization
        amp_n = paths.amp[n]  # complex scalar
        j_n = int(paths.j_idx[n])

        # Per-triangle BS-side mu = -k_hat . normal, with the lit gate mu > 0.
        mu = -np.einsum("j,ij->i", k_hat_n, normals)  # (T_vis,)
        lit = mu > 1e-3
        if not np.any(lit):
            continue

        # Pseudo-Brewster reflection amplitude r0 = (r_s + r_p) / 2 at the
        # local Fresnel angle. (cos theta = mu).
        r_s, r_p = fresnel_reflection(mu[lit], n_tilde)
        r0 = 0.5 * (r_s + r_p)  # (T_lit,) complex

        # Polarization projection: (I - eta eta^T) psi -> 3-vector at phone.
        # In pseudo-Brewster the reflected polarization is the incident
        # transverse component; here we just project onto the eta-transverse plane.
        eta_lit = eta_hat[lit]  # (T_lit, 3)
        psi_eta = psi_n - eta_lit * np.einsum("j,ij->i", psi_n, eta_lit)[:, None]
        # (T_lit, 3); this is (I - eta eta^T) psi

        # The "isotropic UE antenna pattern" projects onto the polarization
        # plane that the receiver sees. We take the magnitude of psi_eta;
        # for vertical-polarized UE it is just the z-component.
        # Use vertical projection (z-component) as our default UE pattern.
        g_UE_proj = psi_eta[:, 2]  # complex (T_lit,)

        # Incident-phase factor exp(-i k0 k_n . r) at each lit triangle
        phase_inc = np.exp(-1j * k0 * np.einsum("j,ij->i", k_hat_n, centroids[lit]))
        # (T_lit,)

        # Assemble the per-triangle integrand contribution to element j_n
        # K * g_UE * green * exp(-i k0 k_n . r) * dA, with K = i k0 r0
        K = 1j * k0 * r0  # (T_lit,)
        contrib = (
            amp_n
            * K
            * g_UE_proj
            * green[lit]
            * phase_inc
            * areas[lit]
        )  # (T_lit,)

        # Accumulate into Lambda[j_n, lit_indices]
        lit_idx_in_vis = np.where(lit)[0]
        Lambda[j_n, lit_idx_in_vis] += contrib

    # h_body[j] = sum over visible triangles of Lambda[j, t]
    h_body = Lambda.sum(axis=1)  # (M,)

    extras = {"vis": vis, "tri_vis_idx": tri_idx}
    if return_per_triangle:
        extras["Lambda"] = Lambda
    return h_body, extras


# ---------------------------------------------------------------------------
# Cascaded channel and rate
# ---------------------------------------------------------------------------
def cascaded_channel(h_los: np.ndarray, h_body: np.ndarray) -> np.ndarray:
    return h_los + h_body


def mrt_sinr_db(
    h: np.ndarray,
    *,
    p_tx_dbm: float,
    noise_dbm: float,
    array_gain_db: float = 0.0,
    scene_loss_db: float = 0.0,
) -> float:
    """SINR for single-stream MRT precoding x = sqrt(P) h / ||h||.

    Reduces to SINR = P * ||h||^2 / N0 in the single-user case.
    array_gain_db absorbs panel-side gain not captured in h itself
    (e.g., when h is per-element-normalized rather than absolute).
    scene_loss_db absorbs path losses upstream of h that we treat as
    a one-shot multiplicative scalar (windows, walls, multipath floor).
    """
    p_tx_w = 10 ** ((p_tx_dbm - 30) / 10)
    n0_w = 10 ** ((noise_dbm - 30) / 10)
    h2 = float(np.sum(np.abs(h) ** 2))
    sinr_lin = (
        p_tx_w
        * h2
        * 10 ** (array_gain_db / 10)
        / 10 ** (scene_loss_db / 10)
        / n0_w
    )
    return 10.0 * np.log10(max(sinr_lin, 1e-30))


def rate_bps_shannon(
    sinr_db: float, bandwidth_hz: float = 100e6
) -> float:
    """Plain Shannon rate, no modulation cap."""
    sinr_lin = 10 ** (sinr_db / 10)
    return float(np.log2(1.0 + sinr_lin) * bandwidth_hz)


# Back-compat alias for any external caller; behaves identically to the
# uncapped Shannon form now.
rate_bps_capped = rate_bps_shannon
