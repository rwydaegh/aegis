"""More detailed analysis of the Kirchhoff K factor.

The surface PO current is J_t = 2 (n_hat x H_inc) V_nt, per paper line 605-606.
The radiated electric field at observer r_p from a surface current J on Sigma is
(Stratton-Chu / vector PO):
  E_rad(r_p) = -j omega mu_0 / (4 pi) integral G(r,r_p) [J - (J . eta) eta] dA

where G = exp(jk_0 R)/R for some sign convention, and eta = (r_p - r)/||r_p - r||.

For a far-field observer (R >> wavelength) and tangential J, this simplifies.

But the paper writes the body-mediated channel coefficient h_body as:
  h_body = sum_n a_n integral K_n(r; r_p) dA
with K_n(r; r_p) = K * g_UE^H(eta) psi * G(r,r_p) * exp(-j k_0 khat_n . r)
and K = j k_0 r_0 with r_0 = 1 - T_0 ~ 0.46.

Let me derive what K should be carefully.

The incident E-field at r is:
  E_inc(r) = psi * x_j(n) * a_n^H beta_n * exp(-j k_0 khat . r)
The incident H-field is:
  H_inc(r) = (1/Z_0) khat x E_inc(r)

The PO surface current: J = 2 n_hat x H_inc.
For tangential E (normal incidence assumed for simplification, though
generalize is the goal):
  J = 2 n_hat x H_inc = (2/Z_0) n_hat x (khat x E_inc)
                     = (2/Z_0) [(n_hat . E_inc) khat - (n_hat . khat) E_inc]

For tangential E (E perpendicular to n_hat) and normal incidence (khat = -n_hat):
  J = (2/Z_0) [0 - (-1) E_inc] = 2 E_inc / Z_0.

So at normal incidence, |J| = 2 |E_inc| / Z_0.

The far-field radiation from surface current J on a small patch dA at distance R = ||r - r_p||:
  E_rad ~ -j omega mu_0 / (4 pi R) [J - (J . eta) eta] exp(-jk_0 R) dA

For R observation direction along normal, J is tangential, so J . eta ~ 0, and
  |E_rad| ~ omega mu_0 |J| / (4 pi R) dA
        = (k_0 c mu_0) * (2 |E_inc| / Z_0) / (4 pi R) dA
        = k_0 (c mu_0 / Z_0) * 2 |E_inc| / (4 pi R) dA

Now c mu_0 = sqrt(mu_0 / eps_0) = Z_0. So c mu_0 / Z_0 = 1.
  |E_rad| = k_0 * 2 |E_inc| / (4 pi R) dA
         = j k_0 * (2/4 pi R) |E_inc| dA  (with the j from omega mu_0)

Hmm, but this is for a perfect-conductor PO (full reflection, r = -1). For a
DIELECTRIC body, the PO current is not 2 n x H_inc (that's only for PEC).
The Fresnel-corrected PO current is:
  J = 2 (1 + r_perp) n_hat x H_inc  for TE-like (or similar with r_para for TM)
where r is the Fresnel REFLECTION coefficient (amplitude).

Hmm actually the standard "physical optics" with Fresnel correction uses the
REFLECTION coefficient. The reflected field amplitude is r * E_inc, so the
effective re-radiation has amplitude (1 + r) * E_inc on the surface (incident +
reflected at z=0+), or if we think about the equivalent current at z=0+ for the
reflected wave alone, it's r * 2 (n x H_inc). So:
  J^reflected = -2 r (n_hat x H_inc)   (for TE)
  or
  J^reflected = +2 r (n_hat x H_inc)   (for TM, sign depends on convention)

Either way the reflected re-radiation kernel scales as r * |E_inc|, NOT R = |r|^2 or 1 - T = R.

So K should scale as r ~ sqrt(R) = sqrt(1 - T_0) ~ 0.68, NOT 1 - T_0 ~ 0.46.

Let me also verify with energy conservation:
The reflected power from the body is integral over surface of |r|^2 * S_inc * cos(theta) dA
                                       = integral R * S_inc * cos(theta) dA
And the absorbed power is integral T * S_inc * cos(theta) dA.
Sum = R + T = 1. So R = 1 - T_0 = 0.46.

The reflected POWER (not amplitude) is R * S_inc = 0.46 * S_inc.
The reflected AMPLITUDE is sqrt(R) = 0.68 * |E_inc|.

The body-mediated channel coefficient is an AMPLITUDE quantity (the channel,
which is a complex transfer function). So K should use the amplitude
reflection ~ sqrt(R) = sqrt(1 - T_0) = 0.68.

Confirmed: K = jk_0 r_0 with r_0 = 1 - T_0 IS WRONG. It should be sqrt(1 - T_0) ~ 0.68.

This causes a 3.4 dB error in the body-mediated channel POWER, which is large.

But actually, how does this compare to the calibration headroom? The paper says
the body-side gamma calibration absorbs 'the dielectric mismatch'. So the
absolute amplitude scale of K is absorbed by the per-path beta_n and per-element
gamma. So this might be calibrated away in practice. But the math is still wrong.
"""
print("Algebra bug check for K = j k_0 r_0:")
print("Paper's r_0 = 1 - T_0 = 0.46 = R_0 (power reflectance)")
print("Correct amplitude reflection ~ sqrt(R_0) = 0.68")
print("Difference: factor 1.47 in amplitude, 3.36 dB in body channel power")
print()
print("Both numerical and conceptual bug.")
print("Mitigated only because the per-path beta_n / per-element gamma calibration")
print("absorbs the absolute amplitude scale.")
