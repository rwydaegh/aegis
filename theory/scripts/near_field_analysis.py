"""
Near-field analysis: compute key quantitative results for the near-field
extension of the dosimetry framework.

Computes:
1. Near-field correction factors for canonical shapes (sphere, disk)
2. Practical scenario analysis at mmWave frequencies
3. Reactive near-field distances
4. Solid-angle calculations
5. Wavefront curvature error estimates
"""

import numpy as np
import sys
import os

# Ensure we can import from the scripts directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fresnel import fresnel_transmission, n_complex

# =============================================================
# Physical constants and tissue parameters
# =============================================================

C0 = 3e8  # speed of light (m/s)

def wavelength(f_ghz):
    return C0 / (f_ghz * 1e9)

def get_skin_n(f_ghz):
    """Get complex refractive index for skin from Gabriel 4-Cole-Cole model.
    Uses approximate values matching the monograph's IT'IS v5 database."""
    # Approximate skin tissue properties (from IT'IS database, Gabriel model)
    tissue_data = {
        # f_GHz: (eps_r, sigma S/m)
        0.9:  (41.4, 0.87),
        1.8:  (38.9, 1.18),
        2.45: (38.0, 1.46),
        3.5:  (36.3, 1.96),
        5.0:  (33.8, 3.06),
        10.0: (26.9, 8.01),
        26.0: (16.6, 25.3),
        28.0: (15.9, 27.2),
        39.0: (12.5, 36.4),
        60.0: (8.87, 51.5),
    }
    
    # Find closest frequency
    freqs = np.array(list(tissue_data.keys()))
    idx = np.argmin(np.abs(freqs - f_ghz))
    f_key = freqs[idx]
    eps_r, sigma = tissue_data[f_key]
    
    return n_complex(eps_r, sigma, f_ghz * 1e9)


def main():
    print("=" * 72)
    print("NEAR-FIELD EXTENSION: QUANTITATIVE ANALYSIS")
    print("=" * 72)
    
    # =============================================================
    # 1. TISSUE PROPERTIES ACROSS FREQUENCY
    # =============================================================
    print("\n1. TISSUE PROPERTIES (skin, IT'IS v5 approximation)")
    print("-" * 60)
    
    freqs = [0.9, 1.8, 2.45, 3.5, 5.0, 10.0, 26.0, 28.0, 39.0, 60.0]
    
    print(f"\n{'f (GHz)':>10} {'n_tilde':>18} {'|n|':>6} {'T0':>8} {'delta(mm)':>10} {'lam(mm)':>10}")
    print("-" * 72)
    
    for f in freqs:
        n_t = get_skin_n(f)
        lam = wavelength(f) * 1000  # mm
        
        # Normal-incidence transmission
        T0_s, T0_p = fresnel_transmission(np.array([1.0]), n_t)
        T0 = float(T0_s[0])
        
        # Skin depth: delta = lam / (2*pi*kappa) where n_tilde = n - i*kappa
        kappa = -n_t.imag
        delta = lam / (2 * np.pi * kappa)
        
        print(f"{f:10.0f} {n_t.real:8.2f}{n_t.imag:+8.2f}i {abs(n_t):6.2f} "
              f"{T0:8.3f} {delta:10.2f} {lam:10.1f}")
    
    # =============================================================
    # 2. KEY INSIGHT: LOCAL LAW VALIDITY
    # =============================================================
    print("\n\n2. LOCAL ABSORPTION LAW VALIDITY")
    print("-" * 60)
    print("   The Fresnel half-space model applies point-by-point")
    print("   whenever the wavefront is locally plane over ~3 wavelengths.")
    print("   This requires d >> lambda (radiating near-field regime).")
    print("   The Fresnel coefficient T(theta) is wavefront-independent.")
    
    # =============================================================
    # 3. WAVEFRONT CURVATURE ERROR
    # =============================================================
    print("\n\n3. WAVEFRONT CURVATURE: PHASE ERROR ACROSS BODY PATCH")
    print("-" * 60)
    print("   For source at distance d, body patch of size L:")
    print("   Phase error ~ pi * L^2 / (4 * lambda * d)")
    print("   For this to be < pi/8: d > 2*L^2/lambda (Fraunhofer)")
    
    print(f"\n{'Scenario':<25} {'d (m)':>6} {'L (m)':>6} {'f (GHz)':>8} {'d/lam':>8} "
          f"{'d/L':>6} {r'FF err (\%)':>10}")
    print("-" * 80)
    
    scenarios = [
        ("Phone at head", 0.01, 0.15, 28),
        ("Phone at head", 0.01, 0.15, 3.5),
        ("Laptop on lap", 0.05, 0.30, 28),
        ("Small cell 2m", 2.0, 0.85, 28),
        ("Small cell 5m", 5.0, 0.85, 28),
        ("Base stn 10m", 10.0, 0.85, 28),
        ("Base stn 20m", 20.0, 0.85, 28),
        ("Base stn 50m", 50.0, 0.85, 28),
        ("Indoor AP 3m", 3.0, 0.85, 60),
        ("Small cell 5m", 5.0, 0.85, 3.5),
    ]
    
    for name, d, L, f in scenarios:
        lam = wavelength(f)
        d_fraunhofer = 2 * L**2 / lam
        # Far-field error estimate: (L/(2d))^2 / 2 * 100%
        ff_err = (L / (2 * d))**2 / 2 * 100
        print(f"{name:<25} {d:6.2f} {L:6.2f} {f:8.1f} {d/lam:8.1f} "
              f"{d/L:6.1f} {ff_err:10.2f}")
    
    # =============================================================
    # 4. REACTIVE NEAR-FIELD BOUNDARY
    # =============================================================
    print("\n\n4. REACTIVE NEAR-FIELD BOUNDARY: d < lam/(2*pi)")
    print("-" * 60)
    print("   Below this distance, evanescent/reactive fields dominate.")
    print("   The Fresnel/Poynting framework BREAKS DOWN.")
    
    print(f"\n{'f (GHz)':>10} {'lam (mm)':>10} {'lam/2pi (mm)':>14} {'3*lam (mm)':>10}")
    print("-" * 50)
    
    for f in [0.9, 3.5, 10, 28, 39, 60]:
        lam = wavelength(f) * 1000  # mm
        reactive = lam / (2 * np.pi)
        local_law = 3 * lam
        print(f"{f:10.1f} {lam:10.1f} {reactive:14.2f} {local_law:10.1f}")
    
    # =============================================================
    # 5. SOLID ANGLE COMPUTATION: DISK ABSORBER
    # =============================================================
    print("\n\n5. SOLID ANGLE: DISK (flat body surface facing source)")
    print("-" * 60)
    print("   Source at distance d from center of disk radius R.")
    print("   S(rho)/S(0) = d^2/(d^2 + rho^2)")
    print("   Half-power at rho = d")
    print("   Exact: P = P_t T_0 d / (4pi) int dA / (rho^2 + d^2)^{3/2}")
    print("         = P_t T_0 / 2 * (1 - d/sqrt(R^2 + d^2))")
    print("   Far-field: P = P_t T_0 R^2 / (4 d^2)")
    
    print(f"\n{'d/R':>8} {'P_exact/P_FF':>14} {r'Error (\%)':>12}")
    print("-" * 40)
    
    for d_R in [10, 5, 3, 2, 1.5, 1.0, 0.7, 0.5, 0.3]:
        # Exact: P_exact = T_0/2 * (1 - d/sqrt(R^2 + d^2))
        # Far-field: P_FF = T_0 R^2 / (4 d^2)
        # Ratio: P_exact/P_FF = 2 d^2/R^2 * (1 - d/sqrt(R^2 + d^2))
        #       = 2 (d/R)^2 * (1 - (d/R)/sqrt(1 + (d/R)^2))
        x = d_R  # d/R
        p_exact = 0.5 * (1 - x / np.sqrt(1 + x**2))
        p_ff = 1 / (4 * x**2)
        ratio = p_exact / p_ff
        err = (ratio - 1) * 100
        print(f"{d_R:8.1f} {ratio:14.4f} {err:+12.2f}%")
    
    # =============================================================
    # 6. SOLID ANGLE: SPHERE INTERCEPTOR (whole body)
    # =============================================================
    print("\n\n6. SOLID ANGLE: SPHERE (whole body approximation)")
    print("-" * 60)
    print("   Body approximated as sphere radius a, source at distance d.")
    print("   Exact: P = P_t T_0 / 2 * (1 - sqrt(1 - (a/d)^2))")  
    print("   Far-field: P = P_t T_0 a^2 / (4 d^2)")
    
    print(f"\n{'d/a':>8} {'Omega (sr)':>12} {'P_exact/P_FF':>14} {r'Error (\%)':>12}")
    print("-" * 52)
    
    for d_a in [20, 10, 5, 3, 2, 1.5, 1.2, 1.05]:
        # sin(alpha) = a/d, alpha = half-angle
        sin_alpha = 1.0 / d_a
        if sin_alpha >= 1:
            continue
        omega_body = 2 * np.pi * (1 - np.sqrt(1 - sin_alpha**2))
        # Exact: T_0/2 * (1 - cos(alpha)) = T_0 * omega / (4pi)
        p_exact_norm = 0.5 * (1 - np.sqrt(1 - sin_alpha**2))
        # Far-field: T_0 * a^2 / (4 d^2)
        p_ff_norm = sin_alpha**2 / 4
        ratio = p_exact_norm / p_ff_norm
        err = (ratio - 1) * 100
        print(f"{d_a:8.1f} {omega_body:12.4f} {ratio:14.4f} {err:+12.2f}%")
    
    # =============================================================
    # 7. ABSORBED POWER FORMULA
    # =============================================================
    print("\n\n7. ABSORBED POWER = P_t * T_0 * Omega_body / (4*pi)")
    print("-" * 60)
    print("   Far-field: Omega_body approx A_perp / d^2")
    print("   Near-field: use exact solid angle")
    
    T0_28 = 0.54  # approximate at 28 GHz
    a_body = 0.85 / 2  # body half-width ~ 0.425 m
    
    print(f"\n{'d (m)':>6} {'Omega_FF (sr)':>22} {'Omega/4pi':>10} {'P_abs/P_t (T0=0.54)':>22}")
    print("-" * 66)
    
    for d in [1, 2, 3, 5, 10, 20, 50]:
        # Approximate body as sphere with a = 0.425 m
        A_perp = np.pi * a_body**2
        omega_ff = A_perp / d**2
        frac = omega_ff / (4 * np.pi)
        p_abs = T0_28 * frac
        print(f"{d:6.0f} {omega_ff:22.4f} {frac:10.6f} {p_abs:22.6f}")
    
    # =============================================================
    # 8. DISTANCE REGIME TABLE  
    # =============================================================
    print("\n\n8. DISTANCE REGIME TABLE")
    print("-" * 60)
    
    print(f"\n{'':>20}", end='')
    for f in [0.9, 3.5, 28, 60]:
        print(f"  {f:>6.0f} GHz", end='')
    print()
    print("-" * 60)
    
    print(f"{'lam (mm)':>20}", end='')
    for f in [0.9, 3.5, 28, 60]:
        print(f"  {wavelength(f)*1000:>9.1f}", end='')
    print()
    
    print(f"{'Reactive lam/2pi mm':>20}", end='')
    for f in [0.9, 3.5, 28, 60]:
        lam = wavelength(f) * 1000
        print(f"  {lam/(2*np.pi):>9.1f}", end='')
    print()
    
    print(f"{'Local law 3*lam mm':>20}", end='')
    for f in [0.9, 3.5, 28, 60]:
        lam = wavelength(f) * 1000
        print(f"  {3*lam:>9.1f}", end='')
    print()
    
    print(f"{'Fraunhofer 2L^2/lam':>20}", end='')
    for f in [0.9, 3.5, 28, 60]:
        lam = wavelength(f)
        d_ff = 2 * 0.85**2 / lam
        print(f"  {d_ff:>9.1f}", end='')
    print(" m (L=0.85m)")
    
    # =============================================================
    # 9. ERROR BUDGET SUMMARY
    # =============================================================
    print("\n\n9. ERROR BUDGET SUMMARY (28 GHz, skin)")
    print("-" * 72)
    
    nf_5m = (0.85 / (2 * 5))**2 / 2 * 100
    nf_10m = (0.85 / (2 * 10))**2 / 2 * 100
    nf_20m = (0.85 / (2 * 20))**2 / 2 * 100
    
    print(f"""
Error source             | Magnitude       | Notes
-------------------------|-----------------|----------------------------------------
Fresnel (T_avg ~ T_0)   | ~1% integrated  | Pseudo-Brewster, 28 GHz
                         | ~5% local       | Worst at theta > 75 deg
Diffraction              | ~10% torso      | Sphere worst case, 28 GHz
Curvature                | ~0.5%           | Most body regions
Tissue uncertainty       | ~10%            | IT'IS database variability
Near-field LOCAL law     | ~0%             | For d > 3*lam (3 cm at 28 GHz)
Near-field FF approx     | ~{nf_5m:.1f}%            | Base station at 5m, whole body
                         | ~{nf_10m:.2f}%           | Base station at 10m
                         | ~{nf_20m:.3f}%          | Base station at 20m
Reactive near field      | BREAKS          | d < 1.7 mm at 28 GHz
""")
    
    print("=" * 72)
    print("ANALYSIS COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
