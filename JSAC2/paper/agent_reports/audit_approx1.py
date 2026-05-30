"""Issue #3: Approximation 1 error budget.

The supplement S1 proof (lines 81-125) shows:
  - Self-terms unaffected (since |e_p|^2 = |e_p'|^2 = 1).
  - TM-TM cross-term inner product e_p'_n . e_p'_n':
      = cos(theta_t,n) cos(theta_t,n') + sin(theta_t,n) sin(theta_t,n')
    Approximated by:
      e_p,n . e_p,n' = cos(theta_n) cos(theta_n') + sin(theta_n) sin(theta_n')
    So the substitution error is sin(theta_n) sin(theta_n') - sin(theta_t,n) sin(theta_t,n').
    With sin(theta_t) = sin(theta) / |n|, this is O(1/|n|^2) for the diff.
    But actually sin(theta_n) sin(theta_n') is O(1), not O(1/|n|^2)!
    So the substitution error is O(1) - O(1/|n|^2) = O(1) for the difference.

The proof's logic is subtle. Let me re-trace:
  e_p'_n . e_p'_n' = cos(t,n) cos(t,n') + sin(t,n) sin(t,n')
  e_p,n . e_p,n' = cos(n) cos(n') + sin(n) sin(n')

The DIFFERENCE between these two:
  delta = [cos(n) cos(n') - cos(t,n) cos(t,n')] + [sin(n) sin(n') - sin(t,n) sin(t,n')]

For small theta_t (~12 deg), cos(t) ~ 1 - 0.022, so cos(t)cos(t') ~ 1 - 0.044.
For sin: sin(theta) - sin(theta_t) = sin(theta) - sin(theta)/|n|, so the second
bracket is ~ sin(n)sin(n') (1 - 1/|n|^2) which is O(1) not O(1/|n|^2).

So the error in the INNER PRODUCT of polarization vectors is NOT O(1/|n|^2).
It's O(1). The proof seems to confuse "the normal-component contribution to
||E_trans||^2 is O(1/|n|^2)" with "the substitution error in cross-terms
is O(1/|n|^2)". The first is true. The second is not exactly the same.

Let me compute numerically.

But there's another subtlety: the absorbed power formula is
  Sab = |x|^2 / Z_0 * (T_s |psi_s|^2 + T_p |psi_p|^2) [mu]+
which is bilinear in |psi_s|^2 and |psi_p|^2 -- there's no cross term!
The "cross-term" in the proof refers to the cross-PATH cross-term, when
TWO different paths n and n' both have TM components and we compute:
  E_trans_n . conj(E_trans_n') = t_p,n t_p,n'^* (e_p'_n . e_p'_n') |psi_p|^2 etc.

Then ||E_trans_total||^2 = sum_n |E_n|^2 + 2 Re sum_{n != n'} E_n . conj(E_n').

The cross-term factor (e_p'_n . e_p'_n') is being approximated by (e_p,n . e_p,n').

Compute the substitution error numerically.
"""
import numpy as np

n = 4.49 - 1.79j

def cos_theta_t(theta_n_deg):
    """Refracted angle cosine."""
    th = np.radians(theta_n_deg)
    sin_t = np.sin(th) / n
    cos_t = np.sqrt(1 - sin_t**2)  # take principal value (Re > 0)
    if np.real(cos_t) < 0:
        cos_t = -cos_t
    return cos_t, sin_t

def inner_prod_TM_refracted(theta_n_deg, theta_np_deg):
    """e_p'_n . e_p'_n' (in the incidence plane assuming both planes share tangent)"""
    cos_t, sin_t = cos_theta_t(theta_n_deg)
    cos_tp, sin_tp = cos_theta_t(theta_np_deg)
    return cos_t * cos_tp + sin_t * sin_tp

def inner_prod_TM_incident(theta_n_deg, theta_np_deg):
    """e_p,n . e_p,n' (using incident-side directions)"""
    th = np.radians(theta_n_deg)
    thp = np.radians(theta_np_deg)
    return np.cos(th) * np.cos(thp) + np.sin(th) * np.sin(thp)

print("Substitution error in TM-TM inner product (Approximation 1):")
print("Format: theta_n, theta_n' | e'_p . e'_p | e_p . e_p | abs(diff) | rel(diff)/|n|^2 expected ~4%")
max_abs = 0
max_rel = 0
for tn in [0, 30, 45, 60, 75, 85]:
    for tnp in [0, 30, 45, 60, 75, 85]:
        ipr = inner_prod_TM_refracted(tn, tnp)
        ipi = inner_prod_TM_incident(tn, tnp)
        diff = ipi - ipr
        if abs(diff) > max_abs:
            max_abs = abs(diff)
            max_pair = (tn, tnp)
        rel = abs(diff) / abs(ipr) if abs(ipr) > 0 else float('inf')
        if rel > max_rel:
            max_rel = rel
        print(f"  ({tn:5.1f},{tnp:5.1f}) | {ipr:+.4f}{ipr.imag:+.4f}j | {ipi:+.4f} | {abs(diff):.4f} | {rel*100:.2f}%")
print(f"\nMax absolute error: {max_abs:.4f} at pair {max_pair}")
print(f"Max relative error: {max_rel*100:.2f}%")
print(f"O(1/|n|^2) = {1/abs(n)**2*100:.2f}%")

# But the cross-term error is also weighted by t_p,n t_p,n'^*, so the propagated
# error in the absorbed power is delta * (t_p,n t_p,n'^* psi_p,n psi_p,n'^*).
# With |t_p|^2 already in the self-term contribution.

# Now also check: does the cross-term enter the SAB formula as written?
# Actually the absorbed POWER (energy conservation) is sum over n of T_n |psi_n|^2,
# the diagonal sum. The cross-term in the field (E . E^*) integrates over the
# tissue depth and gives the depth coupling Lambda_nn'. This is Approximation 2's
# territory.
# But the polarization direction (Approx 1) governs whether the t_p,n e_p,n term
# of path n is parallel to the t_p,n' e_p,n' term of path n'.
# With Approx 1, these are taken parallel (e_p,n . e_p,n'). Without, the actual
# direction is e_p',n . e_p',n'.
# The error in cross-term magnitude is t_p,n t_p,n'^* * (e_p,n . e_p,n' - e_p',n . e_p',n').
# Compute this numerically.
print("\nFull cross-term substitution error (with Fresnel coefficients):")
print("Format: (theta_n, theta_n') | t_p factor | inner-product diff | full err")
for tn, tnp in [(30, 60), (45, 75), (60, 60), (75, 75)]:
    cos_n = np.cos(np.radians(tn))
    cos_np = np.cos(np.radians(tnp))
    xi_n = np.sqrt(n**2 - 1 + cos_n**2)
    xi_np = np.sqrt(n**2 - 1 + cos_np**2)
    if np.real(xi_n) < 0: xi_n = -xi_n
    if np.real(xi_np) < 0: xi_np = -xi_np
    t_p_n = 2*n*cos_n / (n**2 * cos_n + xi_n)
    t_p_np = 2*n*cos_np / (n**2 * cos_np + xi_np)
    ipr = inner_prod_TM_refracted(tn, tnp)
    ipi = inner_prod_TM_incident(tn, tnp)
    err = t_p_n * np.conj(t_p_np) * (ipi - ipr)
    # Self-term magnitude for reference
    self_n = abs(t_p_n)**2 * np.real(xi_n) / cos_n
    self_np = abs(t_p_np)**2 * np.real(xi_np) / cos_np
    self_geom_mean = np.sqrt(self_n * self_np)
    print(f"  ({tn:3.0f},{tnp:3.0f}): |t_p_n||t_p_n'|={abs(t_p_n*t_p_np):.4f} "
          f"diff={ipi-ipr:.4f} err={abs(err):.4f} self_mean={self_geom_mean:.4f} "
          f"rel_to_self={abs(err)/self_geom_mean*100:.2f}%")
