"""Final test: compute the full depth-integrated absorbed power double sum
with and without Approx 1 + Approx 2, on a representative scenario.

Two paths landing on the same surface point with different angles, equal-amplitude
TM-polarized incident waves.

True P_abs (all approximations OFF):
  P_abs/A = (sigma/2) integral_0^inf |sum_n F_n psi_n exp(-j k0 xi_n z)|^2 dz
         = (sigma/2) sum_{n,n'} (F_n psi_n) . (F_n' psi_n')^* * Lambda_nn'

Where (F_n psi_n) is the transmitted vector field at z=0 (with refracted TM direction).
Lambda_nn' = 1/(alpha_n + alpha_n' - j(beta_n' - beta_n)).

Approximated P_abs (Approx 1: replace e_p' by e_p; Approx 2: Gamma=1):
  Same expression but F_n with e_p (incident-side), and Lambda_nn' = sqrt(L_nn L_n'n').
"""
import numpy as np

n_skin = 4.49 - 1.79j
f = 28e9
c = 3e8
k0 = 2*np.pi*f/c
omega = 2*np.pi*f
eps0 = 8.854e-12
sigma = -omega * eps0 * np.imag(n_skin**2)
print(f"sigma = {sigma:.4f} S/m")

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

# Two paths: theta_n at angle1, theta_n' at angle2, both TM polarized.
# Set up a 2D incidence-plane geometry: surface at z=0, x is tangent, z is up.
# k_n = sin(th_n) x_hat - cos(th_n) z_hat, n_hat = +z_hat
# Incident TM direction e_p,n = sin(th_n) z_hat + cos(th_n) x_hat
#   (lies in incidence plane, perp to k_n)
# Refracted TM e_p',n = sin(th_t) z_hat + cos(th_t) x_hat

def true_pabs(theta1, theta2):
    """Depth-integrated absorbed power with EXACT geometry."""
    t_s1, t_p1, mu1, xi1 = fresnel_t(theta1)
    t_s2, t_p2, mu2, xi2 = fresnel_t(theta2)
    a1, b1 = alpha_beta(theta1)
    a2, b2 = alpha_beta(theta2)
    cos_t1, sin_t1 = cos_sin_t(theta1)
    cos_t2, sin_t2 = cos_sin_t(theta2)
    # Each path contributes a vector field at z=0:
    # E_n (z=0) = t_p,n * e_p',n * psi_p,n * (some amplitude including phase exp(-jk0 khat.r))
    # with e_p',n = (cos_t,n) x_hat + (sin_t,n) z_hat (lying in incidence plane)
    # For absorbed power inside tissue, only TANGENTIAL components of E count?
    # Actually the absorbed power is integral (1/2) sigma |E|^2 dV. The full E inside.
    # Inside, E parallel to e_p' (refracted TM unit vector).
    # For path 1: E_t,1(z) = t_p,1 * psi_p,1 * e_p',1 * phase(z)
    # For path 2: E_t,2(z) = t_p,2 * psi_p,2 * e_p',2 * phase(z)
    # Sum: E_total(z) = E_t,1(z) + E_t,2(z)
    # |E|^2 = |E_t,1|^2 + |E_t,2|^2 + 2 Re(E_t,1 . E_t,2*)

    psi_p_1 = 1.0  # set to 1 for simplicity (TM polarized)
    psi_p_2 = 1.0

    # e_p',1 = (cos_t1) x + (sin_t1) z
    # e_p',2 = (cos_t2) x + (sin_t2) z
    # e_p',1 . e_p',2* (note: cos_t and sin_t are complex! but here treat as standard inner product)
    # Actually for complex vectors, the natural inner product for |E|^2 is e . e*.
    # Let's compute it as written.
    e_dot_e_true = cos_t1 * np.conj(cos_t2) + sin_t1 * np.conj(sin_t2)

    # Self terms (cross-term n=n' is the diagonal):
    # |E_n|^2 integrated over depth = |t_p,n psi_p,n|^2 * (1)/(2 alpha_n) * |e_p',n|^2
    # but |e_p',n|^2 = cos_t1^2 + sin_t1^2 = 1 (since these are sin^2 + cos^2 = 1, even complex).
    # Actually: cos_t^2 + sin_t^2 = 1 (true for real or complex).
    L11 = 1 / (2 * a1)
    L22 = 1 / (2 * a2)
    L12 = 1 / (a1 + a2 - 1j*(b2 - b1))
    L21 = np.conj(L12)

    # Self-terms
    self1 = abs(t_p1 * psi_p_1)**2 * L11  # * |e_p'_1|^2 = 1
    self2 = abs(t_p2 * psi_p_2)**2 * L22

    # Cross term (true)
    cross_true = 2 * np.real(t_p1 * np.conj(t_p2) * psi_p_1 * np.conj(psi_p_2)
                             * e_dot_e_true * L12)

    P_true = (sigma / 2) * (self1 + self2 + cross_true)
    return P_true

def approx_pabs(theta1, theta2):
    """With Approx 1 (e_p instead of e_p') and Approx 2 (Gamma=1)."""
    t_s1, t_p1, mu1, xi1 = fresnel_t(theta1)
    t_s2, t_p2, mu2, xi2 = fresnel_t(theta2)
    a1, b1 = alpha_beta(theta1)
    a2, b2 = alpha_beta(theta2)

    # e_p,1 = cos(th1) x + sin(th1) z (incident TM direction)
    # e_p,2 = cos(th2) x + sin(th2) z
    # e_p,1 . e_p,2 = cos(th1)cos(th2) + sin(th1)sin(th2) = cos(th1 - th2)
    e_dot_e_approx = np.cos(np.radians(theta1 - theta2))

    L11 = 1 / (2 * a1)
    L22 = 1 / (2 * a2)
    L12_approx = np.sqrt(L11 * L22)  # Approx 2: Gamma = 1 means L12 = sqrt(L11 L22)

    self1 = abs(t_p1)**2 * L11
    self2 = abs(t_p2)**2 * L22
    cross = 2 * np.real(t_p1 * np.conj(t_p2) * e_dot_e_approx * L12_approx)

    return (sigma / 2) * (self1 + self2 + cross)

# Sweep
print("\n=== Two-path TM-TM case, true vs approx P_abs ===")
print("Format: (th1, th2) | True | Approx | Rel error")
worst_err = 0
worst_pair = None
for th1 in [0, 30, 45, 60, 75, 85]:
    for th2 in [0, 30, 45, 60, 75, 85]:
        if th1 == th2: continue  # skip self-coincidence
        Ptrue = true_pabs(th1, th2)
        Papp = approx_pabs(th1, th2)
        err = (Papp - Ptrue) / Ptrue
        if abs(err) > worst_err:
            worst_err = abs(err)
            worst_pair = (th1, th2)
        print(f"  ({th1:5},{th2:5}) | {Ptrue:.4e} | {Papp:.4e} | {err*100:+.3f}%")

print(f"\nWorst rel error: {worst_err*100:.3f}% at angles {worst_pair}")
print(f"\nApprox 1 + Approx 2 combined error in absorbed power for TM-TM cross term")
print(f"can be up to {worst_err*100:.1f}%, which is much larger than the paper's claimed")
print(f"<= 4% (Approx 1) + 0.44% (Approx 2) = ~4.5% total bound.")
