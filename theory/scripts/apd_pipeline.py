"""
APD Pipeline: Compute Absorbed Power Density on Human Body Mesh

This script implements the simplified APD formula using ReLU (positive-part) notation:

    APD(r) = S_inc * T_0 * [μ(r)]₊

where:
    - S_inc: incident power density (W/m²)
    - T_0: normal-incidence Fresnel transmission
    - μ(r) = n̂(r) · (-k̂): cosine of local incidence angle
    - [μ]₊ = max(0, μ): positive part (ReLU function)

The positive-part operator elegantly combines BOTH:
    - The geometric projection factor (cos θ)
    - The visibility function (illuminated vs shadowed)

Note: The sharp discontinuity at μ=0 (shadow boundary) is a geometric optics
idealization. In reality, diffraction smooths this transition over a Fresnel
zone width ~√(λR). The ICNIRP 4 cm² spatial averaging naturally regularizes
this discontinuity for compliance purposes.

Also computes the full Fresnel formula for comparison.

Author: PRL EMT Project
Date: 2026-02-06
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Optional
from pathlib import Path

# Shared helpers
from _fresnel import EPS_0, fresnel_transmission, n_complex as n_complex_from_params
from _geom import load_stl_binary, triangle_areas

# Physical constants
C_0 = 299792458.0        # m/s


@dataclass
class TissueParams:
    """Tissue electromagnetic properties."""
    name: str
    eps_r: float
    sigma: float
    freq_hz: float
    
    @property
    def n_complex(self) -> complex:
        """Complex refractive index."""
        return n_complex_from_params(self.eps_r, self.sigma, self.freq_hz)
    
    @property
    def T_0(self) -> float:
        """Normal incidence transmission."""
        n = self.n_complex
        r = (1 - n) / (1 + n)
        return float(1 - np.abs(r)**2)


# Standard tissue parameters
TISSUES = {
    'skin_28GHz': TissueParams('Skin 28 GHz', 17.0, 25.0, 28e9),
    'skin_60GHz': TissueParams('Skin 60 GHz', 7.9, 36.4, 60e9),
    'muscle_28GHz': TissueParams('Muscle 28 GHz', 25.0, 30.0, 28e9),
    'fat_28GHz': TissueParams('Fat 28 GHz', 4.0, 2.0, 28e9),
}



def positive_part(x: np.ndarray) -> np.ndarray:
    """
    Compute the positive part (ReLU) of an array.
    
    [x]₊ = max(0, x)
    
    This is the key operation in the simplified APD formula:
        APD(r) = S_inc * T_0 * [μ(r)]₊
    
    where μ = n̂ · (-k̂) is the cosine of the local incidence angle.
    
    The positive-part elegantly combines:
    - Geometric projection factor (cos θ for illuminated surfaces)
    - Visibility function (0 for shadowed surfaces)
    
    Note: The sharp discontinuity at μ=0 is a geometric optics idealization.
    In reality, diffraction smooths this over a Fresnel zone width ~√(λR).
    """
    return np.maximum(0, x)


def compute_mu_positive(normals: np.ndarray, k_hat: np.ndarray) -> np.ndarray:
    """
    Compute [μ]₊ = [n̂ · (-k̂)]₊ for each surface element.
    
    This is the core geometric factor in the simplified APD formula:
        APD(r) = S_inc * T_0 * [μ(r)]₊
    
    Returns the positive part of the cosine of the local incidence angle.
    Encodes both geometric projection AND visibility in one operation.
    """
    mu = np.sum(normals * (-k_hat), axis=1)
    return positive_part(mu)


def compute_visibility_simple(centroids: np.ndarray, normals: np.ndarray,
                              k_hat: np.ndarray) -> np.ndarray:
    """
    Simple visibility: illuminated if normal faces toward source.
    
    V = 1 if μ = n̂ · (-k̂) > 0, else 0
    
    This is equivalent to: V = H(μ) where H is the Heaviside step function.
    
    Note: With the ReLU notation, visibility is implicit in [μ]₊:
        [μ]₊ = μ * V = μ * H(μ)
    
    This function is kept for backward compatibility and explicit visibility maps.
    This ignores self-shadowing (occlusion by other body parts).
    """
    # Dot product of normal with direction toward source
    mu = np.sum(normals * (-k_hat), axis=1)
    return (mu > 0).astype(float)


def compute_visibility_raycast(vertices: np.ndarray, centroids: np.ndarray, 
                               normals: np.ndarray, k_hat: np.ndarray) -> np.ndarray:
    """
    Ray-cast visibility: check if each triangle is occluded.
    
    For each triangle centroid, cast a ray toward the source and check
    if it intersects any other triangle.
    
    This is O(N²) - for large meshes, use a BVH acceleration structure.
    """
    n_triangles = len(centroids)
    visibility = np.ones(n_triangles)
    
    # First, eliminate back-facing triangles
    cos_theta = np.sum(normals * (-k_hat), axis=1)
    back_facing = cos_theta <= 0
    visibility[back_facing] = 0
    
    # For front-facing triangles, check occlusion
    # Ray origin: centroid + small offset along normal (to avoid self-intersection)
    ray_origins = centroids + 1e-6 * normals
    ray_dir = -k_hat  # Direction toward source
    
    # Möller–Trumbore intersection algorithm
    for i in range(n_triangles):
        if visibility[i] == 0:
            continue
        
        origin = ray_origins[i]
        
        # Check intersection with all other triangles
        for j in range(n_triangles):
            if i == j:
                continue
            
            v0, v1, v2 = vertices[j]
            edge1 = v1 - v0
            edge2 = v2 - v0
            
            h = np.cross(ray_dir, edge2)
            a = np.dot(edge1, h)
            
            if abs(a) < 1e-10:
                continue  # Ray parallel to triangle
            
            f = 1.0 / a
            s = origin - v0
            u = f * np.dot(s, h)
            
            if u < 0.0 or u > 1.0:
                continue
            
            q = np.cross(s, edge1)
            v = f * np.dot(ray_dir, q)
            
            if v < 0.0 or u + v > 1.0:
                continue
            
            t = f * np.dot(edge2, q)
            
            if t > 1e-6:  # Intersection found
                visibility[i] = 0
                break
    
    return visibility


def compute_apd(vertices: np.ndarray, normals: np.ndarray, centroids: np.ndarray,
                k_hat: np.ndarray, tissue: TissueParams, S_inc: float = 1.0,
                use_raycast: bool = False, use_full_fresnel: bool = False,
                polarization: str = 'unpolarized', e_hat: Optional[np.ndarray] = None
                ) -> Tuple[np.ndarray, dict]:
    """
    Compute APD on mesh surface using the elegant ReLU (positive-part) notation.
    
    The simplified APD formula is:
    
        APD(r) = S_inc * T_0 * [μ(r)]₊
    
    where:
        - μ(r) = n̂(r) · (-k̂) is the cosine of the local incidence angle
        - [μ]₊ = max(0, μ) is the positive part (ReLU function)
    
    The positive-part operator elegantly combines BOTH:
        - Geometric projection factor (cos θ for illuminated surfaces)
        - Visibility function (0 for shadowed surfaces)
    
    IMPORTANT: The simplified formula ONLY works for unpolarized light!
    For polarized sources, use_full_fresnel=True is required.
    
    Note on the shadow boundary: The sharp discontinuity at μ=0 is a geometric
    optics idealization. Diffraction smooths this over ~√(λR). The ICNIRP 4 cm²
    spatial averaging naturally regularizes this discontinuity.
    
    Parameters
    ----------
    vertices : (N, 3, 3) array
        Triangle vertices
    normals : (N, 3) array
        Triangle normals
    centroids : (N, 3) array
        Triangle centroids
    k_hat : (3,) array
        Incident wave direction (unit vector)
    tissue : TissueParams
        Tissue electromagnetic properties
    S_inc : float
        Incident power density (W/m²)
    use_raycast : bool
        If True, use ray-casting for visibility (slow but accurate)
    use_full_fresnel : bool
        If True, compute full angle-dependent Fresnel (for comparison)
    polarization : str
        'unpolarized', 'TE', 'TM', or 'linear'
        For 'linear', must also provide e_hat
    e_hat : (3,) array, optional
        Electric field polarization direction (for linear polarization)
        Must be perpendicular to k_hat
    
    Returns
    -------
    apd : (N,) array
        APD at each triangle (W/m²)
    info : dict
        Additional information (visibility, angles, etc.)
    """
    k_hat = np.asarray(k_hat)
    k_hat = k_hat / np.linalg.norm(k_hat)
    
    n_triangles = len(centroids)
    n_complex = tissue.n_complex
    T_0 = tissue.T_0
    
    # Compute μ = n̂ · (-k̂) for each triangle
    mu = np.sum(normals * (-k_hat), axis=1)
    
    # Compute [μ]₊ = max(0, μ) - the positive part (ReLU)
    # This elegantly combines geometric projection AND visibility
    mu_positive = positive_part(mu)
    
    # For backward compatibility, also compute explicit visibility
    if use_raycast:
        visibility = compute_visibility_raycast(vertices, centroids, normals, k_hat)
        # Apply raycast visibility (handles self-shadowing)
        mu_positive = mu_positive * visibility
    else:
        visibility = (mu > 0).astype(float)
    
    # Simplified APD using ReLU notation: APD = S_inc * T_0 * [μ]₊
    apd_simple = S_inc * T_0 * mu_positive
    
    # Full Fresnel APD (for comparison)
    # APD = S_inc * T_avg(μ) * [μ]₊
    if use_full_fresnel:
        # Use mu_positive for Fresnel calculation (avoids issues at μ<0)
        mu_for_fresnel = np.clip(mu, 0, 1)
        T_s, T_p = fresnel_transmission(mu_for_fresnel, n_complex)
        T_avg = 0.5 * (T_s + T_p)
        apd_full = S_inc * T_avg * mu_positive
    else:
        apd_full = None
        T_s = T_p = T_avg = None
    
    info = {
        'visibility': visibility,
        'mu': mu,                    # Raw μ = n̂ · (-k̂)
        'mu_positive': mu_positive,  # [μ]₊ = max(0, μ)
        'cos_theta': mu_positive,    # Backward compatibility alias
        'T_0': T_0,
        'n_complex': n_complex,
        'T_s': T_s,
        'T_p': T_p,
        'T_avg': T_avg,
        'apd_full': apd_full,
        'n_illuminated': np.sum(mu > 0),
        'n_shadowed': np.sum(mu <= 0),
    }
    
    return apd_simple, info


def estimate_curvature(vertices: np.ndarray, normals: np.ndarray,
                       centroids: np.ndarray) -> np.ndarray:
    """
    Estimate local curvature at each triangle.
    
    Uses a simple approach: for each triangle, find nearby triangles
    and estimate curvature from normal variation.
    
    Returns mean curvature κ = (1/R1 + 1/R2)/2 for each triangle.
    """
    n_triangles = len(centroids)
    curvatures = np.zeros(n_triangles)
    
    # Build a simple spatial index (for small meshes)
    # For each triangle, find neighbors within a distance threshold
    # and estimate curvature from normal variation
    
    # Estimate characteristic length scale
    areas = triangle_areas(vertices)
    char_length = np.sqrt(np.mean(areas))
    search_radius = 3 * char_length  # Look at nearby triangles
    
    for i in range(n_triangles):
        # Find nearby triangles
        distances = np.linalg.norm(centroids - centroids[i], axis=1)
        nearby = (distances < search_radius) & (distances > 0)
        
        if np.sum(nearby) < 3:
            continue
        
        # Estimate curvature from normal variation
        # κ ≈ |dn/ds| where s is arc length
        nearby_normals = normals[nearby]
        nearby_centroids = centroids[nearby]
        
        # Compute normal differences
        dn = nearby_normals - normals[i]
        ds = np.linalg.norm(nearby_centroids - centroids[i], axis=1, keepdims=True)
        ds = np.maximum(ds, 1e-10)  # Avoid division by zero
        
        # Mean curvature estimate
        curvatures[i] = np.mean(np.linalg.norm(dn, axis=1) / ds.flatten())
    
    return curvatures


def compute_curvature_correction(curvatures: np.ndarray, cos_theta: np.ndarray,
                                 wavelength: float) -> np.ndarray:
    """
    Compute the curvature correction factor C(r).
    
    C ≈ cos(θ) / (k * R) = cos(θ) * κ / k
    
    where κ = 1/R is the curvature and k = 2π/λ.
    """
    k = 2 * np.pi / wavelength
    # C = cos(theta) * curvature / k
    correction = cos_theta * curvatures / k
    return correction


def compute_total_absorbed_power(apd: np.ndarray, areas: np.ndarray) -> float:
    """Compute total absorbed power by integrating APD over surface."""
    return np.sum(apd * areas)


def analyze_mesh(filepath: str, k_hat: np.ndarray, tissue: TissueParams,
                 S_inc: float = 1.0, use_raycast: bool = False) -> dict:
    """
    Full analysis pipeline for a mesh.
    
    Returns comprehensive statistics and comparison between
    simplified and full Fresnel formulas.
    """
    print(f"Loading mesh: {filepath}")
    vertices, normals, centroids = load_stl_binary(filepath)
    n_triangles = len(centroids)
    print(f"  {n_triangles} triangles")
    
    areas = triangle_areas(vertices)
    total_area = np.sum(areas)
    print(f"  Total surface area: {total_area*1e6:.1f} mm²")
    
    print(f"\nTissue: {tissue.name}")
    print(f"  n = {tissue.n_complex:.4f}")
    print(f"  |n| = {np.abs(tissue.n_complex):.4f}")
    print(f"  T_0 = {tissue.T_0:.4f}")
    
    print(f"\nIncident wave direction: {k_hat}")
    print(f"Incident power density: {S_inc} W/m²")
    
    # Compute APD with both methods
    print("\nComputing APD...")
    apd_simple, info = compute_apd(
        vertices, normals, centroids, k_hat, tissue, S_inc,
        use_raycast=use_raycast, use_full_fresnel=True
    )
    apd_full = info['apd_full']
    
    print(f"  Illuminated triangles: {info['n_illuminated']}")
    print(f"  Shadowed triangles: {info['n_shadowed']}")
    
    # Statistics on illuminated region
    illuminated = info['visibility'] > 0
    
    if np.any(illuminated):
        # Angle statistics
        theta_deg = np.degrees(np.arccos(info['cos_theta'][illuminated]))
        print(f"\nIncidence angle statistics (illuminated region):")
        print(f"  Min: {theta_deg.min():.1f}°")
        print(f"  Max: {theta_deg.max():.1f}°")
        print(f"  Mean: {theta_deg.mean():.1f}°")
        
        # APD statistics
        print(f"\nAPD statistics (simplified formula):")
        print(f"  Min: {apd_simple[illuminated].min():.4f} W/m²")
        print(f"  Max: {apd_simple[illuminated].max():.4f} W/m²")
        print(f"  Mean: {apd_simple[illuminated].mean():.4f} W/m²")
        
        print(f"\nAPD statistics (full Fresnel):")
        print(f"  Min: {apd_full[illuminated].min():.4f} W/m²")
        print(f"  Max: {apd_full[illuminated].max():.4f} W/m²")
        print(f"  Mean: {apd_full[illuminated].mean():.4f} W/m²")
        
        # Error analysis - exclude near-grazing incidence where both values are tiny
        # Only consider triangles with theta < 75° (cos > 0.26)
        non_grazing = illuminated & (info['cos_theta'] > 0.26)
        if np.any(non_grazing):
            error = (apd_simple[non_grazing] - apd_full[non_grazing]) / apd_full[non_grazing]
            print(f"\nError (simplified vs full) for theta < 75°:")
            print(f"  N triangles: {np.sum(non_grazing)}")
            print(f"  Min: {error.min()*100:.2f}%")
            print(f"  Max: {error.max()*100:.2f}%")
            print(f"  Mean: {error.mean()*100:.2f}%")
            print(f"  RMS: {np.sqrt(np.mean(error**2))*100:.2f}%")
        
        # Also show error for all illuminated triangles (including grazing)
        all_error = np.abs(apd_simple[illuminated] - apd_full[illuminated])
        print(f"\nAbsolute error (all illuminated):")
        print(f"  Mean: {all_error.mean():.4f} W/m²")
        print(f"  Max: {all_error.max():.4f} W/m²")
        
        # Total absorbed power
        P_simple = compute_total_absorbed_power(apd_simple, areas)
        P_full = compute_total_absorbed_power(apd_full, areas)
        print(f"\nTotal absorbed power:")
        print(f"  Simplified: {P_simple*1e3:.4f} mW")
        print(f"  Full Fresnel: {P_full*1e3:.4f} mW")
        print(f"  Error: {(P_simple - P_full)/P_full*100:.2f}%")
        
        # Projected area
        A_perp = np.sum(areas[illuminated] * info['cos_theta'][illuminated])
        print(f"\nProjected area: {A_perp*1e6:.1f} mm²")
        print(f"Theoretical P_abs = S_inc * T_0 * A_perp = {S_inc * tissue.T_0 * A_perp * 1e3:.4f} mW")
    
    return {
        'vertices': vertices,
        'normals': normals,
        'centroids': centroids,
        'areas': areas,
        'apd_simple': apd_simple,
        'apd_full': apd_full,
        'info': info,
    }


if __name__ == '__main__':
    import sys
    
    # Default mesh path
    mesh_paths = [
        Path(__file__).parent.parent / 'data' / 'thelonious.stl',
        Path(__file__).parent / 'thelonious.stl',
    ]
    
    mesh_path = None
    for path in mesh_paths:
        try:
            with open(path, 'rb'):
                mesh_path = path
                break
        except FileNotFoundError:
            continue
    
    if mesh_path is None:
        print("ERROR: Could not find thelonious.stl mesh file")
        print("Looked in:", mesh_paths)
        sys.exit(1)
    
    # Incident wave from +z direction (top-down)
    k_hat = np.array([0, 0, -1])
    
    # Tissue parameters
    tissue = TISSUES['skin_28GHz']
    
    # Run analysis
    print("=" * 70)
    print("APD PIPELINE - ANALYTICAL DOSIMETRY")
    print("=" * 70)
    
    results = analyze_mesh(mesh_path, k_hat, tissue, S_inc=1.0, use_raycast=False)
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
