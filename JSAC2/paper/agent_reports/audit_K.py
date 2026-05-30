"""Issue #2: r_0 = 1 - T_0 vs sqrt(1 - T_0).

The paper writes K = j*k_0*r_0 with r_0 = 1 - T_epskin ~ 0.46 and calls it
the 'pseudo-Brewster reflection amplitude'.

But T_0 = T_epskin = 0.54 is a *power* transmittance per eq. (Sab-single).
So 1 - T_0 = 0.46 is a *power* reflectance R_0, and the *amplitude*
reflection coefficient would be sqrt(R_0) = sqrt(0.46) ~ 0.68.

For normal incidence on n=4.49-1.79j, the actual amplitude reflection is:
  r_s(0) = (1 - n) / (1 + n)
  r_p(0) = (n^2 - n) / (n^2 + n) ... wait, at normal incidence r_s = -r_p.
"""
import numpy as np

n = 4.49 - 1.79j

# Normal incidence amplitude reflection (Fresnel)
mu = 1
xi = n
r_s0 = (mu - xi) / (mu + xi)
r_p0 = (n**2 * mu - xi) / (n**2 * mu + xi)
print(f"At normal incidence:")
print(f"  Fresnel r_s(0) = {r_s0}, |r_s(0)| = {abs(r_s0):.4f}")
print(f"  Fresnel r_p(0) = {r_p0}, |r_p(0)| = {abs(r_p0):.4f}")
print(f"  Power reflectance R_0 = |r_s|^2 = {abs(r_s0)**2:.4f}")
print(f"  T_0 = 1 - R_0 = {1 - abs(r_s0)**2:.4f}")
print(f"  sqrt(R_0) = sqrt(1 - T_0) = {np.sqrt(1 - abs(r_s0)**2):.4f}")
print(f"  1 - T_0 = {1 - abs(r_s0)**2:.4f} (this is the paper's r_0)")

# So sqrt(1-T0) = 0.679 vs 1-T0 = 0.461
# This is a HUGE difference: a factor of 0.679/0.461 = 1.47 in amplitude
# In channel power: factor (0.679/0.461)^2 = 2.17 ~ 3.4 dB
print(f"\nRatio sqrt(R_0)/(1-T_0) = {np.sqrt(1-abs(r_s0)**2)/(1-abs(r_s0)**2):.4f}")
print(f"Power ratio = {(np.sqrt(1-abs(r_s0)**2)/(1-abs(r_s0)**2))**2:.4f}")
print(f"In dB: {10*np.log10((np.sqrt(1-abs(r_s0)**2)/(1-abs(r_s0)**2))**2):.2f} dB")

# Now the question is what the paper REALLY needs at line 635-636.
# Let me look at Kirchhoff render carefully. The kernel is
# K_n = K * g_UE^H psi * G(r,r_p) * exp(-j k_0 khat_n . r)
# K is a constant scalar, the paper says K = j k_0 r_0 with r_0 = 1 - T_0.
#
# Standard Kirchhoff PO: the surface current is J_t = 2 (n_hat x H_inc) V_nt.
# The radiated field at r_p from a surface current is
#   E(r_p) = -j omega mu_0 / (4 pi) integral G(r,r_p) [J_t - (J_t.eta_hat) eta_hat] dA
# in the far field of each surface element.
# Using H_inc = (1/Z_0) (k_hat x E_inc), J_t has magnitude proportional to E_inc / Z_0.
# The far-field re-radiated E is then proportional to k_0 E_inc (after canceling Z_0).
#
# The PO-Fresnel correction: replace 2 (n x H) with the Fresnel reflected current.
# For TE: r_s = (mu - xi)/(mu + xi), so the reflected E amplitude is r_s E_inc.
# For TM: r_p = (n^2 mu - xi)/(n^2 mu + xi), reflected E amplitude is r_p E_inc.
# In the PO/Kirchhoff combination, the reflected field amplitude carries r_{s,p}, NOT
# 1 - T = R = |r|^2.
#
# So K = j k_0 r_0 with r_0 = AMPLITUDE reflection, e.g., sqrt(1 - T) (modulo phase).
# But the paper writes r_0 = 1 - T_0. This is a power quantity.
# That is a SIGNIFICANT algebra bug.

# Verify by comparing magnitudes:
print(f"\nFor skin at 28 GHz:")
print(f"  Average amplitude reflection at normal incidence:")
print(f"    |r_s(0)| = {abs(r_s0):.4f}")
print(f"  Paper's r_0 = 1 - T_0 = {1 - 0.5386:.4f}")
print(f"  sqrt(1 - T_0) = {np.sqrt(1 - 0.5386):.4f}")

# Note that |r_s(0)| = sqrt(R_0) = sqrt(1 - T_0). They MATCH at normal incidence.
# So the paper conflates power and amplitude. Either:
#   (a) it should be K = j k_0 sqrt(1 - T_0) (correct amplitude), or
#   (b) the K^2 (power) should use (1 - T_0) (power), and the final |h_body|^2
#       should be in units of power. But then the integrand |K_n|^2 would be
#       |k_0|^2 |1-T_0|^2 = |k_0|^2 |1-T_0|^2 ~ |k_0|^2 * 0.21
#       whereas amplitude-wise it should be |k_0|^2 |1-T_0| ~ |k_0|^2 * 0.46
# So the channel coefficient is off by a factor sqrt(2.17) ~ 1.47 in amplitude.
# That is ~3.4 dB in channel power, much bigger than the calibration headroom.

print(f"\nThe algebra bug:")
print(f"  Paper: K = j k_0 (1-T_0) = j k_0 * 0.46  (power-as-amplitude)")
print(f"  Correct: K = j k_0 sqrt(1-T_0) ~ j k_0 * 0.68 + phase")
print(f"  Channel amplitude error: factor {np.sqrt(0.46)/0.46:.3f} = {20*np.log10(np.sqrt(0.46)/0.46):.2f} dB")
print(f"  Channel power error: factor {(np.sqrt(0.46)/0.46)**2:.3f} = {10*np.log10((np.sqrt(0.46)/0.46)**2):.2f} dB")
