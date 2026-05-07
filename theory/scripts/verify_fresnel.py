"""
Rigorous verification of Fresnel transmission formulas for lossy media.
This script independently derives and verifies the key claims.
"""

import numpy as np
from scipy import integrate
from scipy.optimize import minimize_scalar

# Shared helpers (correctness anchor)
from _fresnel import fresnel_transmission as fresnel_correct
from _fresnel import n_complex as get_n_complex

def fresnel_code_formula(mu, n_tilde):
    """
    The formula used in the existing code (potentially incorrect for T_p).
    """
    mu = np.asarray(mu, dtype=complex)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)
    
    n2 = n_tilde**2
    abs_n2 = np.abs(n_tilde)**2
    xi = np.sqrt(n2 - 1 + mu**2)
    xi = np.where(np.real(xi) < 0, -xi, xi)
    
    Re_xi = np.real(xi)
    mu_real = np.real(mu)
    
    denom_s = np.abs(mu + xi)**2
    denom_p = np.abs(n2 * mu + xi)**2
    
    T_s = 4 * mu_real * Re_xi / denom_s
    T_p = 4 * abs_n2 * mu_real * Re_xi / denom_p  # This is the suspect formula
    
    if scalar_input:
        return float(T_s[0]), float(T_p[0])
    return T_s, T_p

def T_avg(mu, n_tilde):
    """Average (unpolarized) transmission coefficient."""
    T_s, T_p = fresnel_correct(mu, n_tilde)
    return 0.5 * (T_s + T_p)

def compute_sphere_ratio(n_tilde):
    """Compute R_sphere = T_0 / integral(T_avg)."""
    T_0 = T_avg(1.0, n_tilde)
    I_avg, _ = integrate.quad(lambda mu: T_avg(mu, n_tilde), 0, 1)
    return T_0 / I_avg, T_0, I_avg

def find_pseudo_brewster(n_tilde):
    """Find pseudo-Brewster angle where T_p is maximized."""
    def neg_Tp(mu):
        _, T_p = fresnel_correct(mu, n_tilde)
        return -T_p
    
    result = minimize_scalar(neg_Tp, bounds=(0.01, 0.99), method='bounded')
    mu_pB = result.x
    theta_pB = np.degrees(np.arccos(mu_pB))
    _, T_p_max = fresnel_correct(mu_pB, n_tilde)
    return theta_pB, T_p_max

# =============================================================================
# MAIN VERIFICATION
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("RIGOROUS FRESNEL VERIFICATION")
    print("=" * 70)
    
    # Skin at 28 GHz
    eps_r = 17.0
    sigma = 25.0
    freq_hz = 28e9
    n_tilde = get_n_complex(eps_r, sigma, freq_hz)
    
    print(f"\nTissue: Skin at 28 GHz")
    print(f"  eps_r = {eps_r}")
    print(f"  sigma = {sigma} S/m")
    print(f"  n_tilde = {n_tilde:.4f}")
    print(f"  |n_tilde| = {np.abs(n_tilde):.4f}")
    print(f"  n = {np.real(n_tilde):.4f}")
    print(f"  kappa = {np.imag(n_tilde):.4f}")
    
    # ==========================================================================
    # Part 1: Compare formulas
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PART 1: Formula Comparison (Code vs Correct)")
    print("=" * 70)
    
    print("\nAngle(deg)  T_s(code)  T_s(corr)  T_p(code)  T_p(corr)  T_p error")
    print("-" * 70)
    
    for theta in [0, 15, 30, 45, 60, 75, 80, 85]:
        mu = np.cos(np.radians(theta))
        T_s_code, T_p_code = fresnel_code_formula(mu, n_tilde)
        T_s_corr, T_p_corr = fresnel_correct(mu, n_tilde)
        err = 100 * (T_p_code - T_p_corr) / T_p_corr if T_p_corr > 0.001 else 0
        print(f"{theta:5.0f}       {T_s_code:.5f}    {T_s_corr:.5f}    {T_p_code:.5f}    {T_p_corr:.5f}    {err:+.2f}%")
    
    # ==========================================================================
    # Part 2: T_avg vs angle (the key claim)
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PART 2: T_avg(theta) Uniformity (Key Claim)")
    print("=" * 70)
    
    print("\nAngle(deg)    T_s       T_p       T_avg     T_avg/T_0")
    print("-" * 60)
    
    T_0 = T_avg(1.0, n_tilde)
    for theta in [0, 10, 20, 30, 40, 50, 60, 70, 75, 78, 80, 85]:
        mu = np.cos(np.radians(theta))
        T_s, T_p = fresnel_correct(mu, n_tilde)
        T_a = 0.5 * (T_s + T_p)
        ratio = T_a / T_0
        print(f"{theta:5.0f}        {T_s:.4f}    {T_p:.4f}    {T_a:.4f}    {ratio:.4f}")
    
    # ==========================================================================
    # Part 3: Sphere ratio
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PART 3: Sphere Ratio R = T_0 / <T_avg>")
    print("=" * 70)
    
    R, T_0, I_avg = compute_sphere_ratio(n_tilde)
    print(f"\nT_0 (normal incidence) = {T_0:.4f}")
    print(f"Integral of T_avg over [0,1] = {I_avg:.4f}")
    print(f"R_sphere = {R:.4f}")
    
    # Also compute for TE and TM separately
    I_s, _ = integrate.quad(lambda mu: fresnel_correct(mu, n_tilde)[0], 0, 1)
    I_p, _ = integrate.quad(lambda mu: fresnel_correct(mu, n_tilde)[1], 0, 1)
    T_s_0, T_p_0 = fresnel_correct(1.0, n_tilde)
    
    print(f"\nTE only: R_s = T_s(0) / <T_s> = {T_s_0:.4f} / {I_s:.4f} = {T_s_0/I_s:.4f}")
    print(f"TM only: R_p = T_p(0) / <T_p> = {T_p_0:.4f} / {I_p:.4f} = {T_p_0/I_p:.4f}")
    
    # ==========================================================================
    # Part 4: Pseudo-Brewster angle
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PART 4: Pseudo-Brewster Angle")
    print("=" * 70)
    
    theta_pB, T_p_max = find_pseudo_brewster(n_tilde)
    theta_arctan = np.degrees(np.arctan(np.abs(n_tilde)))
    
    print(f"\nPseudo-Brewster angle: {theta_pB:.1f} deg")
    print(f"T_p at pseudo-Brewster: {T_p_max:.4f}")
    print(f"arctan|n_tilde| = {theta_arctan:.1f} deg")
    print(f"Difference: {theta_pB - theta_arctan:.1f} deg")
    
    # ==========================================================================
    # Part 5: Frequency sweep
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PART 5: Frequency Dependence")
    print("=" * 70)
    
    # Approximate skin parameters at different frequencies (from ITIS)
    skin_params = [
        (10e9, 40.0, 10.0),   # 10 GHz
        (28e9, 17.0, 25.0),   # 28 GHz
        (60e9, 7.9, 36.4),    # 60 GHz
        (100e9, 6.0, 45.0),   # 100 GHz
    ]
    
    print("\nFreq(GHz)  |n|     n       kappa   T_0     R_sphere  theta_pB")
    print("-" * 70)
    
    for freq, eps_r, sigma in skin_params:
        n_t = get_n_complex(eps_r, sigma, freq)
        R, T_0, _ = compute_sphere_ratio(n_t)
        theta_pB, _ = find_pseudo_brewster(n_t)
        print(f"{freq/1e9:5.0f}      {np.abs(n_t):.3f}   {np.real(n_t):.3f}   {np.imag(n_t):.3f}   {T_0:.4f}  {R:.4f}    {theta_pB:.1f}")
    
    # ==========================================================================
    # Part 6: Variation of T_avg
    # ==========================================================================
    print("\n" + "=" * 70)
    print("PART 6: Quantifying T_avg Variation")
    print("=" * 70)
    
    # Compute T_avg at many angles
    angles = np.linspace(0, 80, 81)
    T_avgs = [T_avg(np.cos(np.radians(a)), n_tilde) for a in angles]
    T_avgs = np.array(T_avgs)
    
    T_max = np.max(T_avgs)
    T_min = np.min(T_avgs)
    T_mean = np.mean(T_avgs)
    
    print(f"\nFor skin at 28 GHz, angles 0-80 deg:")
    print(f"  T_avg max = {T_max:.4f} at {angles[np.argmax(T_avgs)]:.0f} deg")
    print(f"  T_avg min = {T_min:.4f} at {angles[np.argmin(T_avgs)]:.0f} deg")
    print(f"  T_avg mean = {T_mean:.4f}")
    print(f"  Variation: (max-min)/mean = {100*(T_max-T_min)/T_mean:.1f}%")
    print(f"  Max deviation from T_0: {100*max(abs(T_max-T_0), abs(T_min-T_0))/T_0:.1f}%")
    
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
