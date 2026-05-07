"""
Verify all numerical claims in RIGOROUS_FRESNEL_DERIVATION.md
"""
import numpy as np
from scipy import integrate
from scipy.optimize import minimize_scalar

EPS_0 = 8.854187817e-12

def get_n_complex(eps_r, sigma, freq_hz):
    omega = 2 * np.pi * freq_hz
    eps_complex = eps_r - 1j * sigma / (omega * EPS_0)
    n_tilde = np.sqrt(eps_complex)
    if np.real(n_tilde) < 0:
        n_tilde = -n_tilde
    return n_tilde

def fresnel_correct(mu, n_tilde):
    """Correct Fresnel using T = 1 - |r|^2"""
    mu = np.asarray(mu, dtype=complex)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)
    
    n2 = n_tilde**2
    xi = np.sqrt(n2 - 1 + mu**2)
    xi = np.where(np.real(xi) < 0, -xi, xi)
    
    r_s = (mu - xi) / (mu + xi)
    r_p = (n2 * mu - xi) / (n2 * mu + xi)
    
    T_s = np.real(1 - np.abs(r_s)**2)
    T_p = np.real(1 - np.abs(r_p)**2)
    
    if scalar_input:
        return float(T_s[0]), float(T_p[0])
    return T_s, T_p

def fresnel_lossless(mu, n):
    """Fresnel for lossless dielectric"""
    mu = np.asarray(mu)
    scalar_input = mu.ndim == 0
    mu = np.atleast_1d(mu)
    
    sin2 = 1 - mu**2
    cos_t = np.sqrt(np.maximum(0, 1 - sin2/n**2))
    xi = n * cos_t
    
    # Handle total internal reflection (not applicable here since n > 1)
    r_s = (mu - xi) / (mu + xi)
    r_p = (n**2 * mu - xi) / (n**2 * mu + xi)
    
    T_s = 1 - r_s**2
    T_p = 1 - r_p**2
    
    if scalar_input:
        return float(T_s[0]), float(T_p[0])
    return T_s, T_p

def T_avg(mu, n_tilde):
    T_s, T_p = fresnel_correct(mu, n_tilde)
    return 0.5 * (T_s + T_p)

def T_avg_lossless(mu, n):
    T_s, T_p = fresnel_lossless(mu, n)
    return 0.5 * (T_s + T_p)

# =============================================================================
print("="*70)
print("TABLE 1: T_avg vs angle for skin at 28 GHz (lossy)")
print("="*70)

n_tilde = get_n_complex(17.0, 25.0, 28e9)
print(f"n_tilde = {n_tilde:.4f}, |n_tilde| = {np.abs(n_tilde):.4f}")
print()

T_0 = T_avg(1.0, n_tilde)
print(f"{'theta':>6} {'T_s':>8} {'T_p':>8} {'T_avg':>8} {'T_avg/T_0':>10}")
print("-"*45)
for theta in [0, 30, 45, 60, 70, 75, 78, 80]:
    mu = np.cos(np.radians(theta))
    T_s, T_p = fresnel_correct(mu, n_tilde)
    Ta = 0.5 * (T_s + T_p)
    print(f"{theta:>6}° {T_s:>8.3f} {T_p:>8.3f} {Ta:>8.3f} {Ta/T_0:>10.3f}")

# =============================================================================
print()
print("="*70)
print("TABLE 2: T_avg vs angle for LOSSLESS dielectric with n = 4.84")
print("="*70)

n_lossless = 4.84
T_0_ll = T_avg_lossless(1.0, n_lossless)
print(f"n = {n_lossless}")
print()

print(f"{'theta':>6} {'T_s':>8} {'T_p':>8} {'T_avg':>8} {'T_avg/T_0':>10}")
print("-"*45)
for theta in [0, 45, 60, 75, 78.3]:
    mu = np.cos(np.radians(theta))
    T_s, T_p = fresnel_lossless(mu, n_lossless)
    Ta = 0.5 * (T_s + T_p)
    print(f"{theta:>6.1f}° {T_s:>8.3f} {T_p:>8.3f} {Ta:>8.3f} {Ta/T_0_ll:>10.3f}")

# =============================================================================
print()
print("="*70)
print("TABLE 3: Frequency dependence of R_sphere")
print("="*70)

skin_params = [
    (10e9, 40.0, 10.0),
    (28e9, 17.0, 25.0),
    (60e9, 7.9, 36.4),
    (100e9, 6.0, 45.0),
]

print(f"{'Freq':>8} {'|n|':>8} {'T_0':>8} {'<T_avg>':>8} {'R':>8}")
print("-"*45)

for freq, eps_r, sigma in skin_params:
    n_t = get_n_complex(eps_r, sigma, freq)
    T_0 = T_avg(1.0, n_t)
    I_avg, _ = integrate.quad(lambda mu: T_avg(mu, n_t), 0, 1)
    R = T_0 / I_avg
    print(f"{freq/1e9:>6.0f} GHz {np.abs(n_t):>8.2f} {T_0:>8.3f} {I_avg:>8.3f} {R:>8.3f}")

# =============================================================================
print()
print("="*70)
print("TABLE 4: TE vs TM vs Unpolarized ratios for skin at 28 GHz")
print("="*70)

n_tilde = get_n_complex(17.0, 25.0, 28e9)
T_s_0, T_p_0 = fresnel_correct(1.0, n_tilde)
I_s, _ = integrate.quad(lambda mu: fresnel_correct(mu, n_tilde)[0], 0, 1)
I_p, _ = integrate.quad(lambda mu: fresnel_correct(mu, n_tilde)[1], 0, 1)
I_avg, _ = integrate.quad(lambda mu: T_avg(mu, n_tilde), 0, 1)

print(f"T_s(0) = {T_s_0:.3f}, <T_s> = {I_s:.3f}, R_TE = {T_s_0/I_s:.2f}")
print(f"T_p(0) = {T_p_0:.3f}, <T_p> = {I_p:.3f}, R_TM = {T_p_0/I_p:.2f}")
print(f"T_0    = {0.5*(T_s_0+T_p_0):.3f}, <T_avg> = {I_avg:.3f}, R_avg = {0.5*(T_s_0+T_p_0)/I_avg:.2f}")

# =============================================================================
print()
print("="*70)
print("PSEUDO-BREWSTER VERIFICATION")
print("="*70)

def find_pseudo_brewster(n_tilde):
    def neg_Tp(mu):
        _, T_p = fresnel_correct(mu, n_tilde)
        return -T_p
    result = minimize_scalar(neg_Tp, bounds=(0.01, 0.99), method='bounded')
    return np.degrees(np.arccos(result.x)), -result.fun

theta_pB, T_p_max = find_pseudo_brewster(n_tilde)
theta_arctan = np.degrees(np.arctan(np.abs(n_tilde)))

print(f"Numerical pseudo-Brewster: {theta_pB:.1f}°")
print(f"arctan|n_tilde|: {theta_arctan:.1f}°")
print(f"T_p at pseudo-Brewster: {T_p_max:.3f}")

# =============================================================================
print()
print("="*70)
print("VARIATION QUANTIFICATION")
print("="*70)

angles = np.linspace(0, 75, 76)
T_avgs = np.array([T_avg(np.cos(np.radians(a)), n_tilde) for a in angles])
T_0 = T_avgs[0]

print(f"For skin at 28 GHz, theta in [0°, 75°]:")
print(f"  T_avg(0°) = {T_0:.4f}")
print(f"  max(T_avg) = {np.max(T_avgs):.4f} at {angles[np.argmax(T_avgs)]:.0f}°")
print(f"  min(T_avg) = {np.min(T_avgs):.4f} at {angles[np.argmin(T_avgs)]:.0f}°")
print(f"  Variation (max-min)/T_0 = {100*(np.max(T_avgs)-np.min(T_avgs))/T_0:.1f}%")
