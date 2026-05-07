"""
Ellipsoid Validation for APD Framework
======================================

IMPORTANT NOTE ON THE EXACT SOLUTION:
-------------------------------------
For a general triaxial ellipsoid, the exact EM scattering solution requires
ellipsoidal wave functions (Lamé functions), which are extremely complex.

However, for a SPHERE (special case a=b=c), we have MIE THEORY which gives
the exact solution as an infinite series of vector spherical harmonics.

Our strategy:
1. Implement Mie theory for spheres (exact)
2. Compare our simplified formula against Mie theory
3. This validates the framework for the spherical case
4. For general ellipsoids, we use physical optics approximation

The key physics question: How much power "leaks" into the shadow region
due to diffraction? Our formula says APD=0 in the shadow. Mie theory
will tell us the exact answer.


This script validates the simplified APD formula against exact/semi-analytical
solutions for electromagnetic scattering from ellipsoids.

The key question: Our framework assigns APD = 0 on shadowed (occluded) regions.
How accurate is this compared to the exact solution which includes diffraction?

Physics Background:
------------------
For a homogeneous dielectric ellipsoid illuminated by a plane wave, the problem
has been solved analytically in various regimes:

1. Rayleigh limit (ka << 1): Internal field is uniform, given by depolarization factors
2. Physical optics (ka >> 1): Geometric optics + diffraction corrections
3. Intermediate regime: Requires full wave solution (ellipsoidal wave functions)

For our validation, we'll use:
- Exact Mie theory for spheres (as a limiting case of ellipsoid)
- Physical optics approximation with Fresnel diffraction for general ellipsoids
- Comparison with our simplified ReLU-based formula

Author: Analysis for APD paper validation
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import special
from scipy.integrate import quad, dblquad
from typing import Tuple, Callable

# =============================================================================
# Part 1: Material Properties (from paper)
# =============================================================================

def complex_refractive_index(eps_r: float, sigma: float, freq: float) -> complex:
    """
    Compute complex refractive index for a lossy dielectric.
    
    Parameters:
    -----------
    eps_r : float
        Relative permittivity (real part)
    sigma : float
        Conductivity in S/m
    freq : float
        Frequency in Hz
    
    Returns:
    --------
    complex
        Complex refractive index n - i*kappa (with kappa > 0 for lossy media)
    """
    eps_0 = 8.854e-12  # F/m
    omega = 2 * np.pi * freq
    
    # Complex permittivity
    eps_complex = eps_r - 1j * sigma / (omega * eps_0)
    
    # Complex refractive index (principal square root)
    n_complex = np.sqrt(eps_complex)
    
    return n_complex


def T0_normal_incidence(n_complex: complex) -> float:
    """
    Power transmission coefficient at normal incidence.
    
    T0 = 4n / [(1+n)^2 + kappa^2]
    
    where n_complex = n - i*kappa
    """
    n = n_complex.real
    kappa = -n_complex.imag  # Note: our convention has Im(n) < 0 for lossy
    
    T0 = 4 * n / ((1 + n)**2 + kappa**2)
    return T0


def skin_properties(freq: float) -> Tuple[complex, float]:
    """
    Get skin tissue properties at given frequency.
    
    Returns complex refractive index and T0.
    
    Using approximate values from IT'IS database for skin.
    """
    # Approximate skin properties (simplified model)
    # These vary with frequency; using representative values
    if freq < 10e9:
        eps_r = 40.0
        sigma = 1.0 + freq / 1e9  # Rough approximation
    elif freq < 30e9:
        eps_r = 20.0 - (freq - 10e9) / 10e9 * 5
        sigma = 15.0 + (freq - 10e9) / 10e9 * 15
    else:
        eps_r = 15.0 - (freq - 30e9) / 70e9 * 8
        sigma = 30.0 + (freq - 30e9) / 70e9 * 30
    
    # More accurate: use paper values at 28 GHz
    if abs(freq - 28e9) < 1e9:
        eps_r = 17.0
        sigma = 25.0
    
    n_complex = complex_refractive_index(eps_r, sigma, freq)
    T0 = T0_normal_incidence(n_complex)
    
    return n_complex, T0


# =============================================================================
# Part 2: Ellipsoid Geometry
# =============================================================================

class Ellipsoid:
    """
    Represents an ellipsoid with semi-axes (a, b, c).
    
    Surface parametrization:
        x = a * sin(theta) * cos(phi)
        y = b * sin(theta) * sin(phi)
        z = c * cos(theta)
    
    where theta in [0, pi], phi in [0, 2*pi]
    """
    
    def __init__(self, a: float, b: float, c: float):
        """
        Initialize ellipsoid with semi-axes a, b, c.
        
        Convention: a >= b >= c (a is longest axis)
        """
        self.a = a
        self.b = b
        self.c = c
        
    def surface_point(self, theta: float, phi: float) -> np.ndarray:
        """Get point on surface at (theta, phi)."""
        x = self.a * np.sin(theta) * np.cos(phi)
        y = self.b * np.sin(theta) * np.sin(phi)
        z = self.c * np.cos(theta)
        return np.array([x, y, z])
    
    def surface_normal(self, theta: float, phi: float) -> np.ndarray:
        """
        Get outward unit normal at (theta, phi).
        
        For ellipsoid x²/a² + y²/b² + z²/c² = 1,
        the gradient is (2x/a², 2y/b², 2z/c²), so normal is proportional to this.
        """
        x, y, z = self.surface_point(theta, phi)
        
        # Gradient of F = x²/a² + y²/b² + z²/c² - 1
        grad = np.array([2*x/self.a**2, 2*y/self.b**2, 2*z/self.c**2])
        
        # Normalize
        norm = np.linalg.norm(grad)
        if norm < 1e-12:
            return np.array([0, 0, 1])  # Degenerate case
        return grad / norm
    
    def surface_area_element(self, theta: float, phi: float) -> float:
        """
        Compute the surface area element dS at (theta, phi).
        
        dS = |r_theta × r_phi| d(theta) d(phi)
        """
        # Partial derivatives
        r_theta = np.array([
            self.a * np.cos(theta) * np.cos(phi),
            self.b * np.cos(theta) * np.sin(phi),
            -self.c * np.sin(theta)
        ])
        
        r_phi = np.array([
            -self.a * np.sin(theta) * np.sin(phi),
            self.b * np.sin(theta) * np.cos(phi),
            0
        ])
        
        # Cross product magnitude
        cross = np.cross(r_theta, r_phi)
        return np.linalg.norm(cross)
    
    def total_surface_area(self, n_theta: int = 100, n_phi: int = 200) -> float:
        """Compute total surface area by numerical integration."""
        theta_vals = np.linspace(0, np.pi, n_theta)
        phi_vals = np.linspace(0, 2*np.pi, n_phi)
        
        dtheta = theta_vals[1] - theta_vals[0]
        dphi = phi_vals[1] - phi_vals[0]
        
        area = 0.0
        for theta in theta_vals[:-1]:
            for phi in phi_vals[:-1]:
                area += self.surface_area_element(theta + dtheta/2, phi + dphi/2) * dtheta * dphi
        
        return area
    
    def principal_curvatures(self, theta: float, phi: float) -> Tuple[float, float]:
        """
        Compute principal curvatures at a point.
        
        For an ellipsoid, the principal curvatures can be computed analytically.
        """
        x, y, z = self.surface_point(theta, phi)
        
        # For ellipsoid, curvature formula involves the normal and position
        # This is a simplified version
        n = self.surface_normal(theta, phi)
        
        # Gaussian curvature K = 1/(a²b²c²) * (abc/|grad F|)^4
        # Mean curvature H is more complex
        
        # For now, use approximate formula based on local radius
        # R ≈ (a*b*c)^(1/3) as rough estimate
        R_approx = (self.a * self.b * self.c)**(1/3)
        
        return 1/R_approx, 1/R_approx  # Simplified


# =============================================================================
# Part 3: Our Simplified APD Formula
# =============================================================================

def apd_simplified(ellipsoid: Ellipsoid, k_hat: np.ndarray, S_inc: float, 
                   T0: float, theta: float, phi: float) -> float:
    """
    Compute APD using our simplified formula.
    
    APD = S_inc * T0 * [n · (-k)]_+
    
    Parameters:
    -----------
    ellipsoid : Ellipsoid
        The ellipsoid geometry
    k_hat : np.ndarray
        Unit vector in direction of wave propagation
    S_inc : float
        Incident power density (W/m²)
    T0 : float
        Normal incidence transmission coefficient
    theta, phi : float
        Surface coordinates
    
    Returns:
    --------
    float
        APD at the given point (W/m²)
    """
    n_hat = ellipsoid.surface_normal(theta, phi)
    mu = np.dot(n_hat, -k_hat)  # cos(incidence angle)
    
    # ReLU: positive part
    mu_plus = max(0, mu)
    
    return S_inc * T0 * mu_plus


# =============================================================================
# Part 4: Test with a simple case
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Ellipsoid APD Validation - Part 1: Setup and Basic Tests")
    print("=" * 60)
    
    # Create a test ellipsoid (human torso-like proportions)
    # Semi-axes in meters: a=0.15 (front-back), b=0.20 (side), c=0.35 (height)
    ellipsoid = Ellipsoid(a=0.15, b=0.20, c=0.35)
    
    print(f"\nEllipsoid semi-axes: a={ellipsoid.a}m, b={ellipsoid.b}m, c={ellipsoid.c}m")
    
    # Compute surface area
    area = ellipsoid.total_surface_area()
    print(f"Surface area (numerical): {area:.4f} m²")
    
    # Approximate formula for ellipsoid surface area (Knud Thomsen's formula)
    p = 1.6075
    area_approx = 4 * np.pi * ((ellipsoid.a**p * ellipsoid.b**p + 
                                 ellipsoid.a**p * ellipsoid.c**p + 
                                 ellipsoid.b**p * ellipsoid.c**p) / 3)**(1/p)
    print(f"Surface area (Thomsen approx): {area_approx:.4f} m²")
    
    # Material properties at 28 GHz
    freq = 28e9
    n_complex, T0 = skin_properties(freq)
    print(f"\nAt {freq/1e9:.0f} GHz:")
    print(f"  Complex refractive index: {n_complex:.3f}")
    print(f"  |n|: {abs(n_complex):.3f}")
    print(f"  T0 (normal incidence): {T0:.3f}")
    
    # Wave coming from +z direction (top-down)
    k_hat = np.array([0, 0, 1])  # Propagating in +z direction
    S_inc = 10.0  # W/m² (ICNIRP reference level)
    
    print(f"\nPlane wave: k_hat = {k_hat}, S_inc = {S_inc} W/m²")
    
    # Test APD at a few points
    print("\nAPD at selected points (simplified formula):")
    test_points = [
        (0, 0, "North pole (top)"),
        (np.pi, 0, "South pole (bottom)"),
        (np.pi/2, 0, "Equator, +x"),
        (np.pi/2, np.pi/2, "Equator, +y"),
        (np.pi/4, 0, "45° from top"),
    ]
    
    for theta, phi, desc in test_points:
        apd = apd_simplified(ellipsoid, k_hat, S_inc, T0, theta, phi)
        n_hat = ellipsoid.surface_normal(theta, phi)
        mu = np.dot(n_hat, -k_hat)
        print(f"  {desc}: APD = {apd:.3f} W/m², μ = {mu:.3f}")
    
    print("\n" + "=" * 60)
    print("Part 1 complete. Next: Exact solution comparison.")
    print("=" * 60)
