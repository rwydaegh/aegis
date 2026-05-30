"""Cross-check Fresnel power transmittance with multiple conventions.

Standard textbook (Born & Wolf, Hecht):
  Power transmittance for lossless dielectric:
    T_s = (n2*cos(theta_t)/n1*cos(theta_i)) * |t_s|^2
    T_p = (n2*cos(theta_t)/n1*cos(theta_i)) * |t_p|^2
  where t_s, t_p are amplitude coefficients.

For lossy: in Born & Wolf, the *power flux* into the medium normalized
by incident flux:
  T = Re(n_t * cos(theta_t)) / (n_i * cos(theta_i)) * |t|^2

The paper writes T_s = |t_s|^2 * Re(xi_n) / mu_n.
Here xi_n = sqrt(n^2 - 1 + mu^2). Since sin^2(theta_i) = 1 - mu^2,
  xi_n^2 = n^2 - sin^2(theta_i) = (n*cos(theta_t))^2  (Snell with n1=1)
So xi_n = n_t * cos(theta_t) (complex). Re(xi_n) = Re(n_t * cos(theta_t)).
And mu_n = cos(theta_i). So T_s in the paper is the standard power
transmittance. Good.

Standard Fresnel (with n1=1, n2=ntilde):
  t_s = 2 cos(theta_i) / (cos(theta_i) + n_t cos(theta_t))
       = 2 mu / (mu + xi)   ... Yes, matches paper.
  t_p = 2 cos(theta_i) / (n_t cos(theta_i) + cos(theta_t)/n_t * ... )
  Actually the standard t_p has multiple conventions. Let me compute
  both Hecht and Born-Wolf forms and see.

Hecht form for t_p (E parallel to incidence plane, amplitude ratio):
  t_p^Hecht = 2 n1 cos(theta_i) / (n2 cos(theta_i) + n1 cos(theta_t))

With n1=1, n2=ntilde:
  t_p^Hecht = 2 cos(theta_i) / (ntilde cos(theta_i) + cos(theta_t))
           = 2 mu / (ntilde mu + xi/ntilde)    [since cos(theta_t) = xi/ntilde]
           = 2 mu * ntilde / (ntilde^2 mu + xi)

OK so paper's t_p = 2 ntilde mu / (ntilde^2 mu + xi) MATCHES Hecht.

Born-Wolf form for t_p sometimes has an extra factor. Let me verify the
power transmittance.

Power transmittance for TM (Hecht Section 4.6):
  T_p = (n2 cos(theta_t)) / (n1 cos(theta_i)) * |t_p|^2
        ... where t_p relates E_t to E_i (parallel components, Hecht convention)

With Hecht convention, this gives T_s + R_s = 1, T_p + R_p = 1.

Let me verify: at normal incidence,
  t_s = 2/(1+n) = 2/(1+4.83 e^{-i*0.38})  ... |t_s| = ?
  T_s = |t_s|^2 * n   (cos terms = 1)

Take ntilde = 4.49 - 1.79j:
  t_s(0) = 2 / (1 + 4.49 - 1.79j) = 2 / (5.49 - 1.79j)
"""
import numpy as np

n = 4.49 - 1.79j

# At theta=0
mu = 1.0
xi0 = np.sqrt(n**2 - 1 + 1)  # = n
print(f"xi(0) = {xi0}, n = {n}")

t_s0 = 2*mu / (mu + xi0)
t_p0 = 2*n*mu / (n**2 * mu + xi0)
print(f"t_s(0) = {t_s0}, |t_s|^2 = {abs(t_s0)**2:.6f}")
print(f"t_p(0) = {t_p0}, |t_p|^2 = {abs(t_p0)**2:.6f}")

T_s0 = abs(t_s0)**2 * np.real(xi0)/mu
T_p0 = abs(t_p0)**2 * np.real(xi0)/mu
print(f"T_s(0) = {T_s0:.6f}")
print(f"T_p(0) = {T_p0:.6f}")

# Reflection coefficients (compare):
r_s0 = (mu - xi0) / (mu + xi0)
r_p0 = (n**2 * mu - xi0) / (n**2 * mu + xi0)
R_s0 = abs(r_s0)**2
R_p0 = abs(r_p0)**2
print(f"R_s(0) = {R_s0:.6f}, T_s(0)+R_s(0) = {T_s0+R_s0:.6f}")
print(f"R_p(0) = {R_p0:.6f}, T_p(0)+R_p(0) = {T_p0+R_p0:.6f}")

# Sweep angles
print("\nAngular sweep:")
print("theta  T_s     T_p     R_s     R_p     T_s+R_s  T_p+R_p")
for th_deg in [0, 15, 30, 45, 60, 70, 75, 78, 80, 85, 89]:
    th = np.radians(th_deg)
    mu = np.cos(th)
    xi = np.sqrt(n**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    t_s = 2*mu / (mu + xi)
    t_p = 2*n*mu / (n**2 * mu + xi)
    r_s = (mu - xi) / (mu + xi)
    r_p = (n**2 * mu - xi) / (n**2 * mu + xi)
    T_s = abs(t_s)**2 * np.real(xi)/mu
    T_p = abs(t_p)**2 * np.real(xi)/mu
    R_s = abs(r_s)**2
    R_p = abs(r_p)**2
    print(f"{th_deg:5.1f}  {T_s:.4f}  {T_p:.4f}  {R_s:.4f}  {R_p:.4f}  {T_s+R_s:.4f}   {T_p+R_p:.4f}")

# Now also check: maybe paper convention differs. Some texts use
# T = Re(n_t)/n_i * Re(cos(theta_t)) * |t|^2  vs  T = Re(n_t * cos(theta_t)) * |t|^2.
# These differ for lossy media.
print("\nTwo conventions for power transmittance:")
print("Convention A (paper, Born-Wolf):  T = Re(xi)/mu * |t|^2")
print("Convention B (some textbooks):    T = Re(n)*Re(cos_t)/mu * |t|^2 = Re(n)/mu * Re(xi/n) * |t|^2")
for th_deg in [0, 30, 45, 60, 75]:
    th = np.radians(th_deg)
    mu = np.cos(th)
    xi = np.sqrt(n**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    t_s = 2*mu / (mu + xi)
    t_p = 2*n*mu / (n**2 * mu + xi)
    Ts_A = abs(t_s)**2 * np.real(xi)/mu
    Ts_B = abs(t_s)**2 * np.real(n) * np.real(xi/n) / mu  # alternative
    print(f"theta={th_deg}: A) T_s={Ts_A:.4f}  B) T_s={Ts_B:.4f}")
