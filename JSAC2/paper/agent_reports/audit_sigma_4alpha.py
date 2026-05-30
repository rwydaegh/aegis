"""Issue #11: Where does sqrt(sigma/4*alpha_n) come from?

The absorbed power density INSIDE a lossy medium is
  S_abs = (1/2) sigma |E|^2

(in the time-averaged sense, for sigma the conductivity, E the peak field).
Some conventions use rms field, some peak. Let's keep peak.

The transmitted field at depth z inside the tissue is
  E(z) = E_t(0) exp(-alpha_n z) exp(-j beta_n z)
where E_t(0) = F_n psi x_j is the surface-tangential transmitted field.

The power absorbed per unit area (depth-integrated) is
  P_abs/A = integral_0^inf (1/2) sigma |E(z)|^2 dz
         = (1/2) sigma |E_t(0)|^2 / (2 alpha_n)
         = sigma / (4 alpha_n) * |E_t(0)|^2

So sqrt(sigma/(4 alpha_n)) is the factor that gives sqrt of absorbed power density.
That makes sense: the squared norm form needs each column to carry sqrt of the
per-path power density contribution.

Cross-term: integral_0^inf (1/2) sigma E_n(z) E_n'(z)* dz
         = (1/2) sigma E_n(0) E_n'(0)* / (alpha_n + alpha_n' - j(beta_n' - beta_n))
         = (sigma/2) E_n(0) E_n'(0)* * Lambda_nn'

The diagonal: alpha_n + alpha_n + 0 = 2 alpha_n, so Lambda_nn = 1/(2 alpha_n),
and (sigma/2) Lambda_nn = sigma / (4 alpha_n). ✓ matches.

Off-diagonal: Lambda_nn' = 1/(alpha_n + alpha_n' - j(beta_n' - beta_n)).

With Approx 2: Lambda_nn' ~ sqrt(Lambda_nn Lambda_n'n') = 1/(2 sqrt(alpha_n alpha_n')).
So (sigma/2) Lambda_nn' ~ (sigma/2) / (2 sqrt(alpha_n alpha_n'))
                       = (sigma/4) / sqrt(alpha_n alpha_n')
                       = sqrt((sigma/4 alpha_n)(sigma/4 alpha_n'))
                       = sqrt(sigma/4 alpha_n) * sqrt(sigma/4 alpha_n')

So the column-j of G_tilde gets sqrt(sigma/4 alpha_n) per path n, and the cross-term
becomes sqrt(sigma/4 alpha_n) * sqrt(sigma/4 alpha_n'). ✓ This is exactly what's
needed for the squared-norm form.

So the formula is dimensionally consistent. Let's verify units:
  sigma (conductivity) has units S/m = (Omega m)^-1.
  alpha_n has units 1/m.
  sigma/4*alpha_n has units S/m / (1/m) = S = 1/Ohm.
  sqrt(sigma/4*alpha_n) has units sqrt(S) = sqrt(1/Ohm).

Now |E|^2 has units V^2/m^2. So sqrt(sigma/4*alpha_n) * E has units
  sqrt(S) * V/m = sqrt(W/V^2) * V/m ... wait. S = A/V = (V/Omega)/V = 1/Omega.
  So sqrt(S) * V/m = V/(m sqrt(Omega)).
  Squared: V^2/(m^2 Omega) = V^2/(m^2 Omega) = (W/Ohm)/m^2 ... hmm, let me redo.

Actually power density: S_abs has units W/m^2 (surface absorbed power density).
It should equal sigma/(4 alpha_n) * |E_t(0)|^2.
  sigma/(4 alpha_n) has units (S/m) / (1/m) = S = 1/Omega.
  |E|^2 has units V^2/m^2.
  Product: V^2/(m^2 Omega) = V*A / m^2 / Omega * Ohm = ... wait.
  V^2/Omega = V * (V/Omega) = V * A = W. ✓ So V^2/(m^2 Omega) = W/m^2. ✓

Great, so the formula gives W/m^2 as expected.

Now let me verify the EQUIVALENCE to the surface-deposited formula
S_abs(r) = Sinc * T0 * [mu]+:
  S_inc = (1/2) |E_inc|^2 / Z_0  (Poynting)
  T0 = power transmittance
  S_abs/A = Sinc * T0 * [mu]+

So S_abs/A = (1/2) |E_inc|^2 / Z_0 * T0 * [mu]+.

And from depth integration:
  S_abs/A = sigma/(4 alpha) * |E_t|^2 = sigma/(4 alpha) * |t|^2 |E_inc|^2.

For TE: |t_s|^2 |E_inc|^2 should give T0 * |E_inc|^2 / Z_0 * [mu]+ * 2.
  T_s = |t_s|^2 * Re(xi)/mu  (paper definition).
  So |t_s|^2 = T_s * mu / Re(xi).
  Then sigma/(4 alpha) * |t_s|^2 |E_inc|^2
     = sigma/(4 alpha) * T_s * mu / Re(xi) * |E_inc|^2
     ?= (1/2) T_s |E_inc|^2 / Z_0 * mu  [the surface formula]

  Equality requires:
    sigma / (4 alpha Re(xi)) = 1/(2 Z_0)
    => sigma = 2 alpha Re(xi) / Z_0

Test: alpha = -k_0 Im(xi), so for n = 4.49 - 1.79j at theta=0:
  alpha = k_0 * 1.79
  Re(xi) = 4.49
  2 alpha Re(xi) / Z_0 = 2 * k_0 * 1.79 * 4.49 / 377
                      = 2 * (2*pi*28e9/3e8) * 1.79 * 4.49 / 377
                      = 2 * 586.4 * 1.79 * 4.49 / 377
                      = 2 * 4711 / 377
                      = 25.0 S/m

And the IT'IS skin conductivity at 28 GHz?
  Per IT'IS database: skin conductivity at 28 GHz ~ 25-26 S/m typically.
  Actually let me compute: ntilde^2 = eps_r - j sigma/(omega eps_0)
  = (4.49 - 1.79j)^2 = 4.49^2 - 1.79^2 - 2*4.49*1.79j
  = 20.16 - 3.20 - 16.07j = 16.96 - 16.07j
  So eps_r' = 16.96, eps_r'' = 16.07 (with negative sign from complex form).
  sigma = omega * eps_0 * eps_r''
       = 2*pi*28e9 * 8.854e-12 * 16.07
       = 1.76e11 * 8.854e-12 * 16.07
       = 25.0 S/m  ✓

So the relation sigma = 2 alpha Re(xi)/Z_0 should hold at theta=0.
Verify: alpha(0) = k_0 * 1.79 = 586.4 * 1.79 = 1049.7 m^-1
  2*1049.7 * 4.49 / 377 = 24.99 S/m  ✓✓

OK so the formulas are dimensionally and numerically consistent. sqrt(sigma/(4*alpha_n))
makes sense.

But wait: alpha_n depends on theta_n (it's per-path), while sigma is just a material
property. The formula uses alpha_n which is correct. And the EQUALITY
sigma = 2 alpha Re(xi)/Z_0 only holds at theta=0 (where xi = n).

Let me check at other angles:
"""
import numpy as np

n = 4.49 - 1.79j
f = 28e9
c = 3e8
k0 = 2*np.pi*f/c
Z0 = 377
eps0 = 8.854e-12
omega = 2*np.pi*f

eps_r2 = n**2  # eps_r' - j*sigma/(omega*eps_0)
sigma = -omega * eps0 * np.imag(eps_r2)
print(f"sigma = {sigma:.4f} S/m")

# Check sigma = 2 alpha Re(xi) / Z_0 at various angles
print(f"\nVerify sigma = 2 alpha Re(xi)/Z_0 across angles:")
for th in [0, 30, 45, 60, 75, 85]:
    mu = np.cos(np.radians(th))
    xi = np.sqrt(n**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    alpha = -k0 * np.imag(xi)
    rhs = 2 * alpha * np.real(xi) / Z0
    print(f"  theta={th}: 2 alpha Re(xi)/Z_0 = {rhs:.4f}, sigma = {sigma:.4f}, "
          f"diff = {(rhs-sigma)/sigma*100:.2f}%")

# So sigma = 2 alpha Re(xi)/Z_0 actually holds at all angles!
# Because Im(xi^2) = Im(n^2 - 1 + mu^2) = Im(n^2) (since mu real).
# And Im(xi^2) = 2 Re(xi) Im(xi). So Im(n^2) = 2 Re(xi) Im(xi).
# And -Im(n^2) = sigma/(omega eps_0) = sigma * Z_0 / k_0  (using k_0 = omega/c, Z_0 = 1/(c eps_0)).
# So 2 Re(xi) (-Im(xi)) = sigma Z_0 / k_0
# => 2 Re(xi) alpha / k_0 = sigma Z_0 / k_0
# => sigma = 2 Re(xi) alpha / Z_0  ✓ Holds at all angles.

print("\nGood. sigma = 2 alpha Re(xi)/Z_0 is an identity, not an approximation.")
print("So the universal coupling constant sqrt(sigma/(4 alpha_n)) is per-path:")
print("  sqrt(sigma/(4 alpha_n)) = sqrt(Re(xi_n) / (2 Z_0))")
print("This is well-defined.")

# But the paper text describes it as a 'universal coupling constant' suggesting
# it doesn't depend on n. Per the formula it DOES depend on n via alpha_n.
# Hmm. Re-reading the paper: 'isolates the frequency-dependent depth integral
# into the universal coupling constant of Approx 2'. So 'universal' means
# 'same form for all paths', not 'angle-independent'.

# Let me also verify the simpler form: with sigma = 2 alpha Re(xi)/Z_0,
#   sqrt(sigma/(4 alpha_n)) = sqrt(Re(xi_n) / (2 Z_0))
# And T_s = |t_s|^2 Re(xi)/mu, T_p = |t_p|^2 Re(xi)/mu.
# So the squared-norm column gets:
#   |sqrt(sigma/(4 alpha_n)) * t_n|^2 * |psi|^2 / something
# = (sigma/(4 alpha_n)) * |t_n|^2 * |psi|^2
# = (Re(xi_n)/(2 Z_0)) * |t_n|^2 * |psi|^2
#
# For TE (psi=psi_s):
#   Surface-absorbed S_abs = (Re(xi_n)/(2 Z_0)) * |t_s|^2 * |psi_s|^2 / mu * mu
#   But the sqrt-norm should give |x|^2 (psi etc.).
# Hmm, where is the factor 1/mu? Oh right, [mu]+ in the formula. And the
# integration over surface gives ... let me leave this for now.

# Actually let's also verify with the surface S_abs formula:
# S_abs = (|x|^2 / Z_0) * (T_s |psi_s|^2 + T_p |psi_p|^2) [mu]+
# vs
# S_abs = ||tilde G x||^2 = sum over paths of (sigma/4 alpha_n) |F_n psi_n a_n^H x|^2
#       (when only diagonal cross-terms, e.g., orthogonal psi).
# For one path, one element:
# ||sqrt(sigma/(4 alpha_n)) F_n psi_n a_n^H x ||^2
#  = (sigma/(4 alpha_n)) |t_s,n psi_s,n + t_p,n psi_p,n|^2 (after Approx 1)
#  ... wait, with Approx 1 and the rank-2 F_n in the (e_s, e_p) basis,
#  F_n psi_n = t_s,n psi_s,n e_s + t_p,n psi_p,n e_p.
#  ||F_n psi_n||^2 = |t_s,n|^2 |psi_s,n|^2 + |t_p,n|^2 |psi_p,n|^2.
# So:
#  S_abs (single path n) = (sigma/(4 alpha_n)) * (|t_s|^2 |psi_s|^2 + |t_p|^2 |psi_p|^2) |a^H x|^2
#
# And (sigma/(4 alpha_n)) = Re(xi_n)/(2 Z_0).
#
# So S_abs (single path) = Re(xi_n)/(2 Z_0) * (|t_s|^2 |psi_s|^2 + |t_p|^2 |psi_p|^2) |a^H x|^2.
#
# Compare to the surface formula:
#  S_abs = (|x|^2 / Z_0) * (T_s |psi_s|^2 + T_p |psi_p|^2) [mu]+
#       = (1/Z_0) * (|t_s|^2 Re(xi)/mu * |psi_s|^2 + |t_p|^2 Re(xi)/mu * |psi_p|^2) [mu]+ * |a^H x|^2
#       = (Re(xi)/Z_0) * (|t_s|^2 |psi_s|^2/mu + |t_p|^2 |psi_p|^2/mu) [mu]+ * |a^H x|^2
#  Hmm, with [mu]+ matching mu, the 1/mu cancels:
#       = (Re(xi)/Z_0) * (|t_s|^2 |psi_s|^2 + |t_p|^2 |psi_p|^2) * |a^H x|^2
#
# vs from the squared-norm formula:
#       = Re(xi)/(2 Z_0) * (|t_s|^2 |psi_s|^2 + |t_p|^2 |psi_p|^2) * |a^H x|^2.
#
# So the squared-norm form is OFF BY A FACTOR OF 2! It gives HALF the surface-formula
# absorbed power.
#
# Possible resolution: the surface-formula already includes a factor of 1/2 from
# time-averaging that the depth-integral derivation doesn't.
# But both should be time-averaged power. Let me re-derive.

print("\n=== Discrepancy check ===")
mu = np.cos(np.radians(45))
xi = np.sqrt(n**2 - 1 + mu**2)
if np.real(xi) < 0: xi = -xi
alpha = -k0 * np.imag(xi)
t_s = 2*mu / (mu + xi)
T_s = abs(t_s)**2 * np.real(xi)/mu
print(f"At theta=45:")
print(f"  Surface formula factor (in S_abs): T_s/Z_0 * mu = {T_s/Z0 * mu:.6e}")
print(f"  Norm-form factor: sigma/(4 alpha) * |t_s|^2 = {sigma/(4*alpha) * abs(t_s)**2:.6e}")
print(f"  Ratio (surface/norm): {(T_s/Z0 * mu) / (sigma/(4*alpha) * abs(t_s)**2):.4f}")

# OK confirmed: surface formula is 2x the depth-integrated norm formula.
# Resolution: factor of 1/2 from peak vs rms field amplitude convention.
# In radio engineering: |E|^2/(2 Z_0) for peak amplitude E.
# In physics depth-integration: integral (1/2) sigma |E|^2 dz.
# The factor of 1/2 in time-averaged Poynting equals the factor of 1/2 in
# time-averaged Joule heating. So both should match.

# Let me redo: time-avg Poynting = (1/2) Re(E x H*) = (1/2) |E|^2 / Z_0 * khat (for plane wave).
# Time-avg Joule heating density = (1/2) sigma |E|^2.
# Hmm so depth-integrated joule = (1/2) sigma |E_t|^2 / (2 alpha) = sigma/(4 alpha) |E_t|^2.
# This matches the squared-norm formula.
# Surface S_inc = (1/2) |E_inc|^2 / Z_0. So S_inc * T0 = (1/2) T0 |E_inc|^2/Z_0.
#
# The paper's surface formula at line 449 is:
# S_abs = (|x|^2 / Z_0) (T_s |psi_s|^2 + T_p |psi_p|^2) [mu]+
#
# Without the (1/2) factor! Maybe the convention is psi = sqrt(2) E or similar?
# Or maybe x is the precoder weight that is already amplitude-normalized differently.

# Let me compute what they should be assuming consistent conventions:
# S_inc = (1/2) |E_inc|^2 / Z_0 = (1/2) |a^H x|^2 |psi|^2 / Z_0 * |beta|^2 (etc.)
# S_abs = S_inc * T0 * [mu]+

# So the paper's eq (Sab-single) should have a (1/2) factor:
# S_abs = (|x|^2 / (2 Z_0)) (T_s |psi_s|^2 + T_p |psi_p|^2) [mu]+
# OR they're using rms convention.

# This is an off-by-2 factor in the surface formula.
print("\nMissing factor of 1/2 in surface formula? (Paper's eq Sab-single, line 449)")
print("S_abs depth-integrated = sigma/(4 alpha) |E|^2 (peak amplitude).")
print("vs S_abs surface-form = (|x|^2 / Z_0) T |psi|^2 [mu]+.")
print("These match only if either (1) a hidden 1/2 from rms convention, or (2) bug.")
