"""More careful Approximation 1 analysis.

The actual cross-term that appears in ||E_trans_total||^2 (depth-integrated)
includes:
  Real part of: t_p,n t_p,n'^* (e_p',n . e_p',n') psi_p,n psi_p,n'^* * Lambda_nn'
where Lambda_nn' is the depth coupling.

The substitution Approx 1 replaces (e_p',n . e_p',n') with (e_p,n . e_p,n').

Question: is the worst-case relative error in the FULL cross-term magnitude
bounded by ~4% as the paper claims?

Let me sweep over a 2D angle grid and measure the CROSS-TERM error normalized
by the SELF-TERM (geometric mean), which is the relevant scale.
"""
import numpy as np

n = 4.49 - 1.79j

def fresnel_t_p(theta_deg):
    th = np.radians(theta_deg)
    mu = np.cos(th)
    xi = np.sqrt(n**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    t_p = 2*n*mu / (n**2 * mu + xi)
    T_p = abs(t_p)**2 * np.real(xi) / mu
    return t_p, T_p

def cos_sin_t(theta_deg):
    th = np.radians(theta_deg)
    sin_t = np.sin(th) / n
    cos_t = np.sqrt(1 - sin_t**2)
    if np.real(cos_t) < 0:
        cos_t = -cos_t
    return cos_t, sin_t

# Sweep 2D
NA = 89
thetas = np.linspace(0, 85, NA)
max_err = 0
sum_err = 0
count = 0
worst = None
errs = []
for tn in thetas:
    for tnp in thetas:
        t_p_n, T_p_n = fresnel_t_p(tn)
        t_p_np, T_p_np = fresnel_t_p(tnp)
        cos_t_n, sin_t_n = cos_sin_t(tn)
        cos_t_np, sin_t_np = cos_sin_t(tnp)
        ipr = cos_t_n * cos_t_np + sin_t_n * sin_t_np
        ipi = (np.cos(np.radians(tn)) * np.cos(np.radians(tnp))
               + np.sin(np.radians(tn)) * np.sin(np.radians(tnp)))
        # Cross-term contribution to ||E_trans||^2 (taking psi_p,n = psi_p,n' = 1):
        true_cross = t_p_n * np.conj(t_p_np) * ipr
        approx_cross = t_p_n * np.conj(t_p_np) * ipi
        err = abs(true_cross - approx_cross)
        # Reference scale: geometric mean of self-terms (the only thing we have)
        # Self-term: |t_p,n|^2 (depth-integrated includes Lambda_nn = 1/(2*alpha_n))
        # For now use just |t_p|.
        self_mean = abs(t_p_n) * abs(t_p_np)
        rel = err / self_mean if self_mean > 0 else 0
        errs.append((tn, tnp, rel))
        if rel > max_err:
            max_err = rel
            worst = (tn, tnp)
        sum_err += rel
        count += 1

print(f"Cross-term substitution error (Approx 1) normalized by |t_p,n||t_p,n'|:")
print(f"  Max: {max_err*100:.2f}% at angles {worst}")
print(f"  Mean: {sum_err/count*100:.2f}%")

# Now use also the power transmittance as scale (since power is what's compared):
# Scale: |t_p,n|^2 |t_p,n'|^2 = self-term in power. Cross-term in power is the same scale.
# Re-do: rel = err / sqrt(T_p,n T_p,n') (power normalization).
errs2 = []
max_err2 = 0
worst2 = None
for tn in thetas:
    for tnp in thetas:
        t_p_n, T_p_n = fresnel_t_p(tn)
        t_p_np, T_p_np = fresnel_t_p(tnp)
        cos_t_n, sin_t_n = cos_sin_t(tn)
        cos_t_np, sin_t_np = cos_sin_t(tnp)
        ipr = cos_t_n * cos_t_np + sin_t_n * sin_t_np
        ipi = (np.cos(np.radians(tn)) * np.cos(np.radians(tnp))
               + np.sin(np.radians(tn)) * np.sin(np.radians(tnp)))
        true_cross = t_p_n * np.conj(t_p_np) * ipr
        approx_cross = t_p_n * np.conj(t_p_np) * ipi
        err = abs(true_cross - approx_cross)
        # Normalize by sqrt(T_p,n T_p,n') (self-term power scale)
        self_pwr = np.sqrt(T_p_n * T_p_np)
        rel = err / self_pwr if self_pwr > 0 else 0
        errs2.append((tn, tnp, rel))
        if rel > max_err2:
            max_err2 = rel
            worst2 = (tn, tnp)

print(f"\nCross-term error normalized by sqrt(T_p,n T_p,n') (power scale):")
print(f"  Max: {max_err2*100:.2f}% at angles {worst2}")
sum2 = sum(r for _,_,r in errs2)
print(f"  Mean: {sum2/len(errs2)*100:.2f}%")
