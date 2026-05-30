"""More realistic comparison: many paths with random angles, evaluating the
TOTAL P_abs error.

Note that in the depth-integrated formula, the cross-term is also multiplied
by the spatial phase exp(j k_0 (k_n' - k_n) . r) -- which oscillates wildly
across the body surface and AVERAGES OUT over an extended scatterer.

For the SQUARED-NORM property of the per-point S_abs(r), the per-point cross
terms are kept. So my previous test is the right one for the per-point metric.

Let me also check: what if both paths are TE-polarized? Approx 1 doesn't kick in
(it only changes the TM direction).
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

# Pure TE-TE case: e_s,n is perpendicular to incidence plane (= y_hat for both
# if both incidence planes contain x and z axes). Then e_s,n . e_s,n' = 1
# regardless of theta. Approx 1 doesn't change e_s. So Approx 1 error = 0 for TE-TE.
# Only Approx 2 matters (the depth coupling Gamma).

def true_pabs_TE(th1, th2):
    t_s1, _, _, xi1 = fresnel_t(th1)
    t_s2, _, _, xi2 = fresnel_t(th2)
    a1, b1 = alpha_beta(th1); a2, b2 = alpha_beta(th2)
    L11 = 1/(2*a1); L22 = 1/(2*a2)
    L12 = 1/(a1+a2 - 1j*(b2-b1))
    cross = 2*np.real(t_s1 * np.conj(t_s2) * L12)  # e_s . e_s = 1
    return (sigma/2) * (abs(t_s1)**2 * L11 + abs(t_s2)**2 * L22 + cross)

def approx_pabs_TE(th1, th2):
    t_s1, _, _, _ = fresnel_t(th1)
    t_s2, _, _, _ = fresnel_t(th2)
    a1, b1 = alpha_beta(th1); a2, b2 = alpha_beta(th2)
    L11 = 1/(2*a1); L22 = 1/(2*a2)
    L12 = np.sqrt(L11 * L22)  # Approx 2: Gamma=1
    cross = 2*np.real(t_s1 * np.conj(t_s2) * L12)
    return (sigma/2) * (abs(t_s1)**2 * L11 + abs(t_s2)**2 * L22 + cross)

print("TE-TE case (only Approx 2 active):")
worst = 0
for th1 in [0, 30, 45, 60, 75, 85]:
    for th2 in [0, 30, 45, 60, 75, 85]:
        if th1 == th2: continue
        Pt = true_pabs_TE(th1, th2)
        Pa = approx_pabs_TE(th1, th2)
        err = (Pa - Pt)/Pt
        if abs(err) > worst:
            worst = abs(err); wp = (th1, th2)
        # print only worst pairs
        if abs(err) > 0.01:
            print(f"  ({th1:5},{th2:5}) | err = {err*100:+.3f}%")
print(f"Worst TE-TE error: {worst*100:.2f}% at {wp}")
print(f"Note: this is the standalone Approx 2 error in P_abs for TE-TE coherent paths.")
print(f"Paper claims Approx 2 error <= 0.44%.")
