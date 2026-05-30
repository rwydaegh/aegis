"""Issues #6 and #10.

#6: Translation phasor identity (line 660-666):
  Lambda_KH(r_0 + t) = Phi(t)^H Lambda_KH(r_0)
  with Phi(t) a 'diagonal phasor matrix on the BS-element axis'.

Lambda_KH is M x T_vis (M = BS elements, T_vis = visible triangles per the text).

If we translate the WHOLE body rigidly by t (all triangle centroids c_t -> c_t + t),
then the per-triangle integrand of K_n at the new centroid becomes
  K_n(c_t + t; r_p) = K * g_UE^H(eta) psi * G(c_t + t, r_p) * exp(-j k_0 khat_n . (c_t + t))
                   = K_n(c_t; r_p_translated) * exp(-j k_0 khat_n . t) * (G ratio)

Note: G(c_t + t, r_p) != G(c_t, r_p), the Green's function changes because the
distance to the phone changes. Unless r_p ALSO translates with the body (the
phone is on the body, so it does!). If r_p -> r_p + t, then G(c_t + t, r_p + t) =
G(c_t, r_p) (translation invariance of free-space). And eta also stays the same.

So under joint body+phone translation by t:
  K_n(c_t + t; r_p + t) = K * g_UE^H(eta) psi * G(c_t, r_p) * exp(-j k_0 khat_n . (c_t + t))
                       = K_n(c_t; r_p) * exp(-j k_0 khat_n . t)

The Kirchhoff operator entry is:
  Lambda_KH[m, t] = sum_{n -> t} [a_n]_m beta_n S_t K_n(c_t; r_p)

After translation:
  Lambda_KH^new[m, t] = sum_{n -> t} [a_n]_m beta_n S_t K_n(c_t + t_vec; r_p + t_vec)
                     = sum_{n -> t} [a_n]_m beta_n S_t K_n(c_t; r_p) * exp(-j k_0 khat_n . t_vec)

The phase factor exp(-j k_0 khat_n . t_vec) is per-PATH (depends on khat_n), NOT per-BS-element.
The BS-element axis is m. The path axis is n.

The relation Phi(t)^H Lambda_KH(r_0) requires Phi to be diagonal on the m axis.
But the phase factor is per-n, not per-m. So unless every BS element has its own
unique path (one-to-one mapping between m and n), the phase factor IS NOT diagonal
in m.

Generally a single BS element m has multiple paths n through it (or many BS elements
share the same path due to the URA's planewave model). So the relation as stated
is INCORRECT.

What IS correct is:
  Lambda_KH^new = Lambda_KH * Diag_n(exp(-j k0 khat_n . t)) * (something)
But this multiplies on the n-axis which is INSIDE the inner sum, not on the m-axis.
Specifically:
  Lambda_KH[m, t]^new = sum_{n -> t} [a_n]_m beta_n S_t K_n exp(-j k0 khat_n . t_vec)

Equivalently, define a per-path phase column-multiplier on the path-dictionary J:
  J^new[m, n] = J[m, n] * exp(-j k0 khat_n . t_vec)
Then h_body uses J^new instead of J. So Phi(t) is diagonal on the n-axis (path axis),
NOT the m-axis (BS-element axis).

The paper's claim 'diagonal phasor matrix on the BS-element axis' is WRONG.

Maybe what they meant: if we translate r_p alone (the phone moves but body is fixed),
then K_n(c_t; r_p + t) involves a different Green's function. In the far field of
the body (||r_p - c_t|| >> wavelength), G(c_t, r_p + t) ~ G(c_t, r_p) * exp(jk_0 etahat . t)
where etahat = (r_p - c_t)/||r_p - c_t||. So the per-triangle phase factor is
exp(jk_0 etahat . t), and etahat also varies per-triangle. So this still wouldn't
give a per-BS-element diagonal.

Alternative: maybe they meant a translation of the PHONE only, and Phi acts on the
SURFACE-AXIS (T_vis-dim), not the BS-element axis. Let me re-read.

Per line 663-664: 'Phi(t) a diagonal phasor matrix on the BS-element axis'.
That's wrong by inspection.

#10: ICNIRP comparison.
'P_abs sits at 0.58% of ICNIRP general-public reference of 4 W/m^2 surface-equivalent
power density'

P_abs in W (whole-body integrated). ICNIRP reference is 4 W/m^2 (peak surface APD,
NOT whole-body). To compare, you need to either:
(a) Divide P_abs by some area to get average APD: P_abs/A_body. With A_body ~ 1.7 m^2
    (typical adult), then P_abs/A_body in W/m^2.
(b) Convert ICNIRP to whole-body limit. ICNIRP also has a whole-body SAR limit:
    0.08 W/kg averaged over 6 minutes, for general public. With 70 kg adult:
    0.08 * 70 = 5.6 W. So P_abs limit ~ 5.6 W.

If P_abs = 0.58% of 4 W/m^2 = 0.0232 W/m^2 ... that's an APD, not a power.
If P_abs = 0.58% of 5.6 W = 0.0325 W ... that's ~32 mW.

Let me see what number the paper uses elsewhere (e.g., 'milliwatts (instantaneous)'
on line 1202).
"""
print("Issue #6: Translation phasor identity")
print("Paper: 'Lambda_KH(r_0 + t) = Phi(t)^H Lambda_KH(r_0), with Phi(t)")
print("       a diagonal phasor matrix on the BS-element axis.'")
print()
print("Reality: under body translation by t (with phone moving with it),")
print("the per-entry phase factor is exp(-j k_0 khat_n . t).")
print("This is per-PATH (n-axis), NOT per-BS-element (m-axis).")
print("The relation as stated is WRONG. The correct form is:")
print("  Lambda_KH^new = sum_n [a_n]_m * exp(-j k0 khat_n . t) * (rest of K_n entry)")
print("which is a diagonal multiply on the PATH axis (after factoring through J).")
print()

# Numerical check: at 28 GHz, a body translation of 0.5m (one stride):
import numpy as np
k0 = 2*np.pi*28e9/3e8
t_step = 0.5  # meters
phase = k0 * t_step
print(f"Phase magnitude per step: k_0 * 0.5m = {phase:.2f} rad = {np.degrees(phase):.0f} deg")
# That's ~270 wavelengths, huge phase rotation.

print()
print("=== Issue #10: ICNIRP comparison ===")
print("Paper: 'P_abs sits at 0.58% of ICNIRP general-public reference of 4 W/m^2")
print("       surface-equivalent power density'")
print()
print("4 W/m^2 is the PEAK SURFACE APD limit (averaged over 4 cm^2, time-averaged).")
print("0.58% of 4 W/m^2 = 0.0232 W/m^2 (an APD).")
print("But P_abs is whole-body integrated (W), not surface APD (W/m^2).")
print("To compare apples-to-apples, EITHER:")
print("  (a) Divide P_abs by some area A: P_abs/A in W/m^2.")
print("  (b) Convert to whole-body absorption: ICNIRP whole-body SAR = 0.08 W/kg.")
print()
print("Paper line 1202 says 'displayed in milliwatts'. So P_abs is in mW.")
print("If P_abs ~ 0.58% * 4 W/m^2 * A_body ~ 0.58% * 4 * 1.7 = 39 mW (if A_body=1.7 m^2)")
print("This is plausible. But the comparison is implicit. The paper compares a SCALAR")
print("P_abs / ICNIRP_APD without explicitly stating the body-area normalization.")
print()
print("If 0.58% means 'P_abs in mW divided by some W' rather than W/m^2,")
print("the percentage is meaningless / dimensionally wrong.")
