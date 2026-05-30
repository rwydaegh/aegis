"""Check: in a realistic many-path scenario, what fraction of P_abs comes from
TM-TM cross-terms? If it's small, the 35% per-cross-term error is mitigated.
"""
import numpy as np

n_skin = 4.49 - 1.79j
f = 28e9
c = 3e8
k0 = 2*np.pi*f/c
omega = 2*np.pi*f
eps0 = 8.854e-12
sigma = -omega * eps0 * np.imag(n_skin**2)

def fresnel_t(theta_deg):
    th = np.radians(theta_deg)
    mu = np.cos(th)
    xi = np.sqrt(n_skin**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    t_s = 2*mu / (mu + xi)
    t_p = 2*n_skin*mu / (n_skin**2 * mu + xi)
    return t_s, t_p, mu, xi

def alpha_beta(theta_deg):
    _, _, _, xi = fresnel_t(theta_deg)
    return -k0 * np.imag(xi), k0 * np.real(xi)

def cos_sin_t(theta_deg):
    th = np.radians(theta_deg)
    sin_t = np.sin(th) / n_skin
    cos_t = np.sqrt(1 - sin_t**2)
    if np.real(cos_t) < 0:
        cos_t = -cos_t
    return cos_t, sin_t

# Many paths with random angles, all TM-polarized for worst case
np.random.seed(0)
N = 8
errors = []
for trial in range(200):
    # Sample N angles uniformly in [10, 80]
    angles = np.random.uniform(10, 80, N)
    # Random complex amplitudes (proxy for psi*beta*a^Hx)
    amps = np.random.randn(N) + 1j*np.random.randn(N)

    # Build true and approx
    P_true = 0
    P_approx = 0
    for i in range(N):
        for j in range(N):
            _, t_pi, _, _ = fresnel_t(angles[i])
            _, t_pj, _, _ = fresnel_t(angles[j])
            ai, bi = alpha_beta(angles[i])
            aj, bj = alpha_beta(angles[j])
            # True
            L_true = 1/(ai + aj - 1j*(bj - bi))
            cos_ti, sin_ti = cos_sin_t(angles[i])
            cos_tj, sin_tj = cos_sin_t(angles[j])
            e_dot_true = cos_ti * cos_tj + sin_ti * sin_tj
            P_true += np.real(t_pi * np.conj(t_pj) * amps[i] * np.conj(amps[j])
                              * e_dot_true * L_true)
            # Approx
            if i == j:
                L_approx = L_true  # diagonal exact
            else:
                L_approx = np.sqrt((1/(2*ai)) * (1/(2*aj)))
            e_dot_approx = np.cos(np.radians(angles[i] - angles[j]))
            P_approx += np.real(t_pi * np.conj(t_pj) * amps[i] * np.conj(amps[j])
                                * e_dot_approx * L_approx)
    P_true *= sigma/2
    P_approx *= sigma/2
    err = (P_approx - P_true)/P_true if P_true != 0 else 0
    errors.append(err)

errors = np.array(errors)
print(f"With N={N} random TM-polarized paths, random complex amplitudes, theta in [10,80]:")
print(f"  Mean rel error: {np.mean(errors)*100:+.3f}%")
print(f"  Std rel error: {np.std(errors)*100:.3f}%")
print(f"  Max abs error: {np.max(np.abs(errors))*100:.3f}%")
print(f"  10th percentile: {np.percentile(errors, 10)*100:+.3f}%")
print(f"  90th percentile: {np.percentile(errors, 90)*100:+.3f}%")

# Repeat with a more focused angle range
print()
N = 8
errors = []
for trial in range(200):
    angles = np.random.uniform(20, 70, N)  # more typical body-illumination range
    amps = np.random.randn(N) + 1j*np.random.randn(N)
    P_true = 0; P_approx = 0
    for i in range(N):
        for j in range(N):
            _, t_pi, _, _ = fresnel_t(angles[i])
            _, t_pj, _, _ = fresnel_t(angles[j])
            ai, bi = alpha_beta(angles[i])
            aj, bj = alpha_beta(angles[j])
            L_true = 1/(ai + aj - 1j*(bj - bi))
            cos_ti, sin_ti = cos_sin_t(angles[i])
            cos_tj, sin_tj = cos_sin_t(angles[j])
            e_dot_true = cos_ti * cos_tj + sin_ti * sin_tj
            P_true += np.real(t_pi * np.conj(t_pj) * amps[i] * np.conj(amps[j])
                              * e_dot_true * L_true)
            if i == j:
                L_approx = L_true
            else:
                L_approx = np.sqrt((1/(2*ai)) * (1/(2*aj)))
            e_dot_approx = np.cos(np.radians(angles[i] - angles[j]))
            P_approx += np.real(t_pi * np.conj(t_pj) * amps[i] * np.conj(amps[j])
                                * e_dot_approx * L_approx)
    P_true *= sigma/2; P_approx *= sigma/2
    err = (P_approx - P_true)/P_true if P_true != 0 else 0
    errors.append(err)
errors = np.array(errors)
print(f"\nWith N=8 paths in [20,70] (typical body range):")
print(f"  Mean rel error: {np.mean(errors)*100:+.3f}%")
print(f"  Max abs error: {np.max(np.abs(errors))*100:.3f}%")
