"""Robustness check: maybe the paper has in mind a real-valued |n| in Snell,
so that theta_t is real and small. Compare."""
import numpy as np

n_skin = 4.49 - 1.79j
abs_n = abs(n_skin)  # 4.83

# Real-valued Snell: sin(theta_t) = sin(theta) / |n|
# Then cos(theta_t) = sqrt(1 - sin^2/|n|^2) (real, > 0)

def cos_sin_t_real(theta_deg):
    th = np.radians(theta_deg)
    sin_t = np.sin(th) / abs_n
    cos_t = np.sqrt(1 - sin_t**2)
    return cos_t, sin_t

# Inner product e_p',n . e_p',n' with real Snell
def ip_real(th1, th2):
    c1, s1 = cos_sin_t_real(th1)
    c2, s2 = cos_sin_t_real(th2)
    return c1*c2 + s1*s2

# vs incident-side
def ip_inc(th1, th2):
    return np.cos(np.radians(th1 - th2))

print("With REAL-valued Snell (theta_t = arcsin(sin(theta)/|n|)):")
worst = 0
for th1 in [0, 30, 45, 60, 75, 85]:
    for th2 in [0, 30, 45, 60, 75, 85]:
        ipr = ip_real(th1, th2)
        ipi = ip_inc(th1, th2)
        diff = ipi - ipr
        if abs(diff) > worst:
            worst = abs(diff); wp = (th1, th2)
        print(f"  ({th1:3},{th2:3}): e_p'.e_p' = {ipr:+.4f}, e_p.e_p = {ipi:+.4f}, "
              f"diff = {diff:+.4f}")
print(f"Worst diff: {worst:.4f} at {wp}")

# Even with real Snell, the inner product difference is large (up to ~0.9 at (0,85)).
# So the 'small refraction angle' argument doesn't fix the inner product mismatch.
# The right comparison is: sin_t * sin_t' is O(1/|n|^2), but the SUBSTITUTION
# replaces it with sin*sin (O(1)). The DIFFERENCE in the inner product is
# precisely the difference between sin*sin (incident) and sin_t*sin_t' (refracted),
# which is O(1) - O(1/|n|^2) = O(1) for general angle pairs.
