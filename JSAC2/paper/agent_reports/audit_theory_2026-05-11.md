# JSAC2 v3 physics audit, 2026-05-11

Numerical verification of load-bearing claims in Sec III, Sec IV, Sec V, Sec IX,
and Appendices A, B, C of `jsac2_v3.tex`, plus supplement S1.

---

## TL;DR

Five substantive errors. Three are clear bugs that propagate into the entire
physics chapter; two are looser formulations that work numerically but fail the
stated proof bounds. None of the issues invalidates the qualitative conclusions
(squared-norm form is a useful reduction; calibration absorbs scale errors), but
the published proofs and quoted bounds are wrong as stated.

| # | Issue | Severity | Status |
|---|---|---|---|
| 1 | Pseudo-Brewster collapse claim is for `(T_s+T_p)/2`, not `T_s` and `T_p` individually | High | Misstatement of summary-paper result; physical claim is wrong as written |
| 2 | `K = j k_0 r_0` with `r_0 = 1 - T_0` confuses power and amplitude; should be `sqrt(1-T_0)` | High | Algebra bug; 3.36 dB error in body channel power |
| 3 | Approximation 1 inner-product bound `O(1/|n|^2) ~ 4%` is wrong; actual TM cross-term P_abs error reaches 35% | High | Proof in S1 is sloppy; TM-TM cross-term error grossly understated |
| 4 | Approximation 2 bound `<= 0.44%` is wrong; actual `|1-Gamma_nn'|` reaches 2.65% (6x) | Medium | Supp expansion bounds the wrong quantity (`|1-|Gamma||` not `|1-Gamma|`) |
| 5 | Translation phasor identity stated as "diagonal on BS-element axis" — it is diagonal on PATH axis | Medium | Algebra bug in Remark, line 660 |
| 6 | Factor-of-2 inconsistency between eq.(Sab-single) line 449 and eq.(exposure-channel) line 549 | Low | Notational, but the missing 1/2 propagates |
| 7 | ICNIRP comparison line 1205 mixes W (whole-body absorbed) and W/m^2 (peak surface APD) | Low-medium | Apples vs oranges; need explicit area normalization |
| 8 | `sigma/(4 alpha_n)` derivation is correct but undocumented in the paper | None | Verified |
| 9 | Q_abs = J^H M(theta) J factorization is OK for the claimed use case | None | Verified |
| 10 | Identifiability proof phrasing is loose but not wrong | None | Verified |
| 11 | Scene-loss-band baseline comparison is apples-to-apples | None | Verified |

---

## Issue 1: Pseudo-Brewster collapse misstatement

**Paper claim** (Sec III.B, line 460-467):
> For materials with `|n_tilde| >= 2 + sqrt(3) ~ 3.73`, the TE and TM power
> transmittances pinch together at all incidence angles below the critical angle.
> ... At 28 GHz both transmittances lie within 5% of a single scalar
> `T_eff = 0.54` across `theta_n in [0, 80]`.

**Numerical reality** (skin at 28 GHz, `n_tilde = 4.49 - 1.79j`, `|n_tilde| = 4.83`):

| theta | T_s | T_p | T_avg = (T_s+T_p)/2 |
|---|---|---|---|
| 0 | 0.539 | 0.539 | 0.539 |
| 30 | 0.488 | 0.589 | 0.539 |
| 45 | 0.422 | 0.662 | 0.542 |
| 60 | 0.321 | 0.784 | 0.553 |
| 75 | 0.182 | 0.941 | 0.562 |
| 80 | 0.126 | 0.948 | 0.537 |

So `T_s` falls from 0.54 at normal incidence to 0.13 at 80°, while `T_p` rises
to 0.95. Neither stays within 5% of 0.54: `T_s` is 76% off and `T_p` is 77% off.
What DOES stay within ~4% of 0.54 across the full range is the polarization
average `(T_s+T_p)/2`.

This matches the summary-paper formulation exactly (`/home/user/aegis/theory/summary_paper.tex` lines
321-327): "T_avg(theta) ~ T_0 ... is the pseudo-Brewster compensation. For skin
at 28 GHz, T_avg/T_0 stays within 4% over [0, 75°]."

**The JSAC paper drops the polarization-average, mistakenly claiming the per-polarization
T_s and T_p individually pinch together.** This is incorrect; only their mean does.

**Why it matters**: when the wave is polarized (which the paper handles
explicitly via `psi_s, psi_p`), the per-polarization transmittance is what
multiplies `|psi_{s,p}|^2`. Replacing both `T_s` and `T_p` by `T_0 = 0.54`
(eq. line 469) introduces errors of up to 76%/77%, not 5%, for purely
TE-polarized or TM-polarized incident waves.

**Fix**: either (a) restate as "the unpolarized-average transmittance T_avg
stays within 4% of T_0", which is what the summary paper (correctly) claims, or
(b) restrict the scalarization claim to unpolarized averages and keep the
polarization-aware formula explicit elsewhere.

The lossless Brewster angle for a real n=3.73 material is `arctan(3.73) = 75°`,
which matches where T_p peaks in the lossy 28-GHz skin case (~78°). The
condition `|n_tilde| >= 2 + sqrt(3)` is the threshold for the transmittance
spread to balance out in the AVERAGE sense, not for individual TE/TM to pinch
together.

---

## Issue 2: K = j k_0 (1-T_0) is an algebra bug (3.36 dB)

**Paper claim** (eq. kernel, line 631-636):
> Here `K = j k_0 r_0` is the pseudo-Brewster reflection amplitude with
> `r_0 = 1 - T_eff_skin ~ 0.46`.

**Reality**: `T_0 = 0.54` is a power transmittance (per eq. Sab-single line 449,
`T_s = |t_s|^2 Re(xi)/mu`, which is the standard Born-Wolf power transmittance,
verified by `T_s + R_s = 1` exactly at all angles). Therefore `1 - T_0 = R_0` is
the power REFLECTANCE, not an amplitude.

The amplitude reflection coefficient at normal incidence is

```
r_s(0) = (1 - n_tilde)/(1 + n_tilde) = -0.671 + 0.107j,  |r_s(0)| = 0.679 = sqrt(R_0).
```

So `r_0` should be `sqrt(1 - T_0) = sqrt(0.46) = 0.679`, not `1 - T_0 = 0.46`.

**Quantitative impact**: the body-mediated channel coefficient `h_body` scales
linearly in K. The paper's K = jk_0 * 0.46 vs the correct K ~ jk_0 * 0.679 gives
an amplitude error factor of 0.679/0.461 = 1.47, equivalent to **3.36 dB error
in body-mediated channel power**. This propagates into every Kirchhoff-render
prediction.

**Mitigation**: the per-path beta_n calibration (line 699) absorbs absolute
amplitude scale, so the closed-loop performance survives. But the FORMULA is
wrong, and any "first-principles" body-channel prediction without calibration
is off by 3.36 dB.

**Fix**: rewrite as `K = j k_0 sqrt(1 - T_0)`, or equivalently `K = j k_0 |r_0|`
with `r_0` the actual amplitude reflection coefficient at normal incidence.
The summary paper uses `sqrt(T_0)` for the (transmission) amplitude in the
analogous coherent reduction (line 806 of `summary_paper.tex`).

---

## Issue 3: Approximation 1 error bound is wrong (4% claim, ~35% reality)

**Paper claim** (Prop. approx1, line 511-518; Prop. approx1-app, line 1471-1481;
Prop. S-approx1, line 83-94):
> The error on TM-TM cross-terms is `O(1/|n_tilde|^2) ~ 4%` for skin at 28 GHz.

**Proof in S1** (lines 96-116):
The proof argues `sin(theta_t,n) = O(1/|n|)` so `sin*sin' = O(1/|n|^2)`. Then
the inner product mismatch
```
e_p,n . e_p,n' - e_p',n . e_p',n'
= [cos(n)cos(n') - cos_t,n cos_t,n'] + [sin(n)sin(n') - sin_t,n sin_t,n']
```
is asserted to be `O(1/|n|^2)`.

**The bug**: the second bracket evaluates to `sin(n)sin(n')(1 - 1/|n|^2)` which
is `O(1)`, not `O(1/|n|^2)`. The proof confuses "sin_t * sin_t' is O(1/|n|^2)"
with "the substitution error sin*sin - sin_t*sin_t' is O(1/|n|^2)". The latter
is in fact `O(1)` because sin*sin alone is `O(1)`.

**Numerical reality** (sweep 36 angle pairs in [0, 85°]^2):

- Inner-product substitution error `|e_p . e_p' - e_p' . e_p'|` reaches 0.90
  (90% relative) at `(0°, 85°)` — far from the claimed 4%.
- The full TM-TM cross-term error in P_abs (depth-integrated) reaches **35%**
  at `(0°, 75°)` and is worst when one path is nearly normal and the other
  is grazing.

When weighted by Fresnel coefficients (which suppress small-angle TM, since
`|t_p(0)| = |t_s(0)|` is the smallest TM-end coefficient), the worst case in
absorbed power normalized by `sqrt(T_p,n T_p,n')` is 8.5% (still 2x the claim).

**Why the difference is real**: at small theta_n (~0°) the actual e_p,n is nearly
horizontal in the incidence plane, while at large theta_n' (~75°) e_p,n' is nearly
vertical. The geometric inner product `cos(0°) cos(75°) + sin(0°) sin(75°) = 0.26`.
In the tissue, both refracted directions are nearly horizontal (cos_t ~ 1, sin_t ~ 0),
so e_p',n . e_p',n' ~ 1. The mismatch (0.26 vs 1) is ~74%, dominating the
inner-product error.

The cross-term in P_abs picks up this factor multiplicatively, weighted by
the Fresnel coefficients. Because `t_p(0)` is small (no Brewster pumping at
normal incidence) and `t_p(75°)` is large (near pseudo-Brewster), the cross-term
isn't proportionately suppressed, and the 35% number stands.

**Fix**: re-derive the bound. The correct leading-order behavior is

```
e_p,n . e_p,n' - e_p',n . e_p',n' = sin(n) sin(n') (1 - 1/|n|^2) + O(higher).
```

For the WORST case with both angles near 90°, this is `(1)(1)(1 - 1/|n|^2) ~
1 - 0.04 ~ 0.96`. For widely separated angles (one near 0°, the other near 90°),
the absolute mismatch is `sin(0)*sin(90)*1 - 0 = 0`. The actual worst case
involves the multiplication by Fresnel coefficients and shows up at ~ (0°, 75°).

The simple `O(1/|n|^2)` claim is wrong and a more careful per-angle-pair bound
is needed, OR the bound should be restated as a flux-weighted average over the
body surface (where most cross-terms are suppressed by spatial-phase
oscillations).

---

## Issue 4: Approximation 2 bound is wrong (0.44% claim, 2.65% reality)

**Paper claim** (Prop. approx2, line 521-537; supp Prop. S-approx2, line 129-181):
> `|1 - Gamma_nn'| <= 0.44%` with mean 0.17% for skin at 28 GHz over `(theta_n, theta_n') in [0, 85]^2`.

**Proof in S1** (lines 162-173):
> `|1 - Gamma_nn'| <= (1/2)(d_alpha/alpha_bar)^2 + (1/4)(d_beta/alpha_bar)^2 + O(delta^3)`

with `delta ~ 0.02`. The proof asserts `(d_alpha/alpha_bar)^2` and
`(d_beta/alpha_bar)^2` are both `O(delta^2) ~ 0.04%`, giving a total bound
~ 0.05% (matching the table claim of 0.44% in the right order).

**The bug**: the expansion is for `|1 - |Gamma||`, not `|1 - Gamma|`. Let me
walk through:

Set `u = (alpha_n - alpha_n')/alpha_bar`, `v = (beta_n - beta_n')/alpha_bar`.
Then `Gamma = sqrt(1 - u^2/4) / (1 + j v/2)`.

Expanding to leading order:
- `Re(Gamma) ~ 1 - u^2/8 - v^2/4`
- `Im(Gamma) ~ -v/2`
- `|1 - Gamma|^2 ~ (u^2/8 + v^2/4)^2 + v^2/4`
- `|1 - Gamma| ~ |v|/2` to leading order (for small u, v)

The supp formula `(1/2)u^2 + (1/4)v^2` is the bound on `|1 - |Gamma||`, NOT
`|1 - Gamma|`. The leading-order behavior of the latter is `|v|/2 = (1/2)|d_beta|/alpha_bar`,
which is FIRST-ORDER in the spread, not second-order.

**Numerical confirmation** (skin 28 GHz, sweep over [0, 85]^2):

| Quantity | Computed | Paper claim |
|---|---|---|
| max `|1 - Gamma_nn'|` | 2.65% | 0.44% |
| max `|1 - |Gamma_nn'||` | 0.04% | (would need to be the claim) |
| max `|1 - Re(Gamma)|` | 0.08% | |
| max `|Im(Gamma)|` | 2.65% | |
| supp formula at worst pair | 0.09% | claimed bound |

So:
- `|1 - Gamma|` worst-case is **6x** the paper's claimed bound.
- The supp formula bounds the wrong quantity. Even WITH the supp formula, the
  numerical answer 0.09% does not match the table value 0.44%.
- The actual `|1 - Gamma|` is dominated by the imaginary part, which the proof
  ignores.

**The dominant term**: `|d_beta|/alpha_bar`. Because `beta = k_0 Re(xi)` and
`alpha = -k_0 Im(xi)`, with `Re(xi) ~ 4.5 k_0` and `|Im(xi)| ~ 1.8 k_0`, the
ratio is `Re(xi)/|Im(xi)| ~ 2.5`. So a 2% spread in `xi` gives `d_beta/alpha_bar
~ 5%`, and `|1 - Gamma| ~ 2.5%`. The 2.65% number reflects exactly this.

**Why it nevertheless still works**: in the absorbed-power double sum, the
imaginary part of `Gamma` couples to the imaginary part of the cross-term
coefficient (which involves `t_p,n t_p,n'^*` and the spatial phase). For
TE-only paths at the same surface point, my numerical test shows the actual
P_abs error from Approx 2 alone is only 0.07% — well within the 0.44% claim.
This is because the imaginary part of `Gamma` enters as `Re(coefficient * Im(Gamma))`,
which has a partial cancellation when summed over coefficient phases.

But the bound `|1 - Gamma| <= 0.44%` as stated is WRONG in the worst-case sense,
even though the IMPACT on P_abs is mitigated by phase averaging.

**Fix**: restate the bound. Either
(a) "max `|1 - |Gamma||` <= 0.44%" (a different, smaller quantity), or
(b) "max `|1 - Gamma|` <= 2.65%" (the actual bound, dominated by `|v|/2`), or
(c) "RMS |1 - Gamma| over coherent paths is bounded by ~0.5% after path-phase
averaging" — but this requires a separate argument involving the coefficient
phase distribution.

---

## Issue 5: Translation phasor remark, line 660

**Paper claim** (Remark, line 660-667):
> For a small body displacement t (e.g., a walking step), the operator transforms
> as `Lambda_KH(r_0 + t) = Phi(t)^H Lambda_KH(r_0)`, with Phi(t) **a diagonal
> phasor matrix on the BS-element axis**.

**Reality**: under a rigid body+phone translation by t, each Kirchhoff-operator
entry picks up a phase

```
exp(-j k_0 khat_n . t)
```

This is per-PATH (n axis), NOT per-BS-element (m axis). The path direction
khat_n varies across the BS-traced multipath bundle.

The relation as stated is INCORRECT. The correct statement is:

```
Lambda_KH^new[m, t] = sum_{n -> t} [a_n]_m * exp(-j k_0 khat_n . dt) * (rest of K_n)
```

which factors as a diagonal multiply on the PATH axis (after factoring through
the path dictionary J), not the BS-element axis. The "one diagonal multiply"
optimization is correct in spirit but mis-stated in axis.

For a BS panel with M elements and N paths, this is an N-dimensional diagonal
phasor, not an M-dimensional one.

**Fix**: change "BS-element axis" to "path-dictionary axis" or just remove the
axis claim and write "Phi(t) a diagonal phasor matrix indexed by the per-path
arrival direction khat_n".

The numerical magnitude of the phase per step is `k_0 * 0.5 m = 293 rad ~ 47
wavelengths` at 28 GHz, so the phase rotates rapidly across one stride and is
not "small" in any sense.

---

## Issue 6: Factor of 2 in eq. Sab-single

**Paper writes** (line 448-451):
```
S_ab(n)(r) = (|x_j(n)|^2 / Z_0) * (T_s,n |psi_s,n|^2 + T_p,n |psi_p,n|^2) [mu_n]+
```

**Reality from depth integration** (per summary paper line 837):
```
S_ab(r) = (sigma/2) integral_0^inf | sum_n F_n psi_n x exp(-j k_0 ...) exp(-j k_0 xi_n z) |^2 dz
```

For a single TE path (psi_p = 0), this gives:
```
S_ab = (sigma / 2) * |t_s psi_s x|^2 / (2 alpha) = sigma/(4 alpha) |t_s|^2 |psi_s|^2 |x|^2
     = (1/(2 Z_0)) * Re(xi) * |t_s|^2 |psi_s|^2 |x|^2  (using sigma = 2 alpha Re(xi)/Z_0)
     = (|x|^2 / (2 Z_0)) * T_s |psi_s|^2 * mu                       (since T_s = |t_s|^2 Re(xi)/mu)
```

Compare to the JSAC formula:
```
S_ab(JSAC) = (|x|^2 / Z_0) * T_s |psi_s|^2 * mu
```

**The JSAC formula is OFF BY A FACTOR OF 2** (a missing 1/2 from time-averaged
Poynting). The same factor inconsistency is in eq. (exposure-channel) line 549:

```
g_tilde_j has sqrt(sigma/(4 alpha_n)) per path
```

So `||tilde G x||^2 = (1/2 Z_0) sum (Re xi_n)|t_n|^2 |psi_n|^2 |a_n^H x|^2`,
which is the depth-integrated `S_ab` correctly with the 1/2.

But the surface formula on line 449 has NO 1/2. The two formulas differ by 2x.

**Fix**: insert the missing 1/2 in eq. (Sab-single):
```
S_ab(r) = (|x_j|^2 / (2 Z_0)) * (T_s |psi_s|^2 + T_p |psi_p|^2) [mu]+
```

OR adjust the meaning of `psi` to include sqrt(2) (RMS vs peak amplitude
convention). Either way, the surface and the depth formulas should
self-consistently produce the same numerical S_ab.

---

## Issue 7: ICNIRP comparison (line 1205) is dimensionally suspect

**Paper writes**:
> P_abs sits at 0.58% of the ICNIRP general-public reference of 4 W/m^2
> surface-equivalent power density.

**Issue**: P_abs is whole-body absorbed power (W per line 502: "P_abs = integral
S_ab dA"). 4 W/m^2 is a peak surface APD limit (averaged over 4 cm^2 per ICNIRP
2020 spatial-averaging window). The percentage 0.58% requires P_abs/X to be
compared to 4 W/m^2 in the same units.

If 0.58% means `P_abs / (A_body * 4 W/m^2)` with `A_body ~ 1.7 m^2` (typical
adult), then `P_abs ~ 0.58% * 4 * 1.7 = 39.4 mW`, which matches the "milliwatts
(instantaneous)" scale on line 1202.

If 0.58% means `(P_abs / A_4cm^2) / 4 W/m^2` with the 4-cm^2 window, the
numerator would be ~1.5 W/m^2 if P_abs concentrates on 4 cm^2 — but the paper
explicitly disclaims peak-local Sab on line 1221-1228.

**The comparison is dimensionally wrong as stated**. The paper compares a scalar
P_abs to a surface APD without specifying the area-normalization scheme. Either
the body area should be written explicitly, or the ICNIRP reference should be
the whole-body SAR limit (`0.08 W/kg averaged over 6 minutes` for general public,
which gives ~5.6 W absorption for a 70-kg adult). At ~40 mW, P_abs would be
40/5600 = 0.71% of the whole-body SAR limit, which is ~ matches the 0.58% if
you adjust for body weight.

**Fix**: either (a) add an explicit body-area normalization "P_abs / A_body
sits at 0.58% of the 4 W/m^2 limit", or (b) compare to the whole-body SAR limit
"P_abs sits at 0.58-0.71% of the ICNIRP whole-body limit (5.6 W for a 70-kg
adult)".

Note: the paper at line 1281-1282 says "the orange dashed line marks the 4 W/m^2
ICNIRP general-public reference. The user distribution lies well below it." This
confirms the comparison is intended to be in W/m^2 units, but the missing area
normalization makes the percentage opaque.

---

## Issues that check out (no bug)

### Issue 8: sqrt(sigma/(4 alpha_n)) derivation (Sec III, line 549)

The factor `sqrt(sigma/(4 alpha_n))` per column of the exposure channel matrix
is correct. Derivation:
```
S_ab depth-integrated for one TE path = (sigma/2) integral |t_s psi_s x|^2 e^(-2 alpha z) dz
                                     = (sigma/2) * |t_s psi_s x|^2 / (2 alpha)
                                     = sigma/(4 alpha) * |t_s psi_s x|^2
```
So the squared norm column needs sqrt(sigma/(4 alpha_n)) per path.

The cross-term sigma/2 * Lambda_nn' = sigma/(2(alpha_n + alpha_n' + ...)) factors
into sqrt(sigma/(4 alpha_n)) * sqrt(sigma/(4 alpha_n')) under Approx 2. ✓

Furthermore, `sigma = 2 alpha_n Re(xi_n) / Z_0` is an exact algebraic identity
(at all angles, not an approximation), since `Im(xi^2) = 2 Re(xi) Im(xi)` and
`Im(n^2) = -sigma * Z_0 / k_0`. Verified to ~0.1% numerically for IT'IS skin
parameters.

### Issue 9: Q = J^H M(theta) J factorization

The factorization separates:
- J (M x N): BS-to-body-region path dictionary, function of body LOCATION.
- M(theta) (N x N): triangle-and-path geometry Gram matrix, function of joint
  angles theta.

For the closed-loop ascent on the latent pose z (joint angles only, body
centroid fixed by per-Rx geometry), J is constant and M refreshes per pose. The
factorization is valid for the use case.

For body translations (walking step), J changes and would need re-tracing. The
paper's "per-pose body refresh" text at line 562-563 is accurate for joint
changes but not body translations. Could be more precise.

### Issue 10: Identifiability proof (App. C)

The bound `SNR_ul >= K sigma_K^{-2}` is dimensionally consistent (assuming the
Lambda_KH amplitude scale is unitless after beta_n calibration). The "K" factor
is heuristic (loose-bound multi-mode penalty), but the inequality is OK.

The proposition phrasing "exactly identifiable when the residual lies in
span(U_K)" conflates "identifiability of the LS solution" (needs only sigma_K > 0)
with "exact recovery of the true gamma" (needs r in span(U_K)). Loose, not wrong.

### Issue 11: Scene-loss-band baselines (Sec VIII.G)

The 35/55/80 dB bands are a parametric scalar-loss companion (per supp S2 line
272-283) — a free-space LOS link with a fixed scalar attenuation, NOT a Sionna
RT scene loss. All four precoder families (no-twin ZF, no-twin MRT, T-pose-prior,
RIHB) see the same propagation budget, so the comparison is apples-to-apples.

---

## Recommended actions

In order of urgency:

1. **Fix issue 2 (K = j k_0 sqrt(1-T_0))**: pure algebra bug. One-line fix in
   the kernel definition. Affects the absolute amplitude of every Kirchhoff-
   render prediction by 3.4 dB.

2. **Fix issue 1 (pseudo-Brewster claim)**: rewrite as the polarization-average
   statement that the summary paper makes. Either (a) restrict the scalar-T_0
   collapse to unpolarized averages and keep the polarization-aware form for
   per-pol calculations, or (b) defer to Approximation 1+2 to handle the
   per-polarization spread.

3. **Fix issue 3 and 4 (Approx 1, 2 error budgets)**: re-derive the bounds
   carefully. Either tighten the proofs to match the actual numerical worst-
   case (much weaker than claimed), or restate the bounds as flux-weighted /
   phase-averaged quantities.

4. **Fix issue 5 (translation phasor axis)**: one-word fix. "BS-element axis"
   -> "path-dictionary axis".

5. **Fix issue 6 (factor of 2)**: insert 1/2 in eq.(Sab-single), or document
   the convention.

6. **Fix issue 7 (ICNIRP units)**: write the body-area normalization explicitly,
   or switch to whole-body SAR comparison.

None of these affect the qualitative conclusions of the paper (beamforming
exploits the body channel, calibration absorbs scale errors, IMU drift is
tolerable). But the published proofs and quoted error bounds will not survive
careful review.

---

## Numerical verification scripts (in /tmp/)

- `audit_fresnel.py`, `audit_fresnel2.py`, `audit_fresnel3.py`: pseudo-Brewster
- `audit_K.py`, `audit_K2.py`: K = j k_0 r_0 algebra
- `audit_approx1.py`, `audit_approx1b.py`: Approximation 1 inner-product error
- `audit_approx2.py`, `audit_approx2b.py`, `audit_approx2c.py`: Approximation 2
  Gamma analysis
- `audit_sigma_4alpha.py`: derivation of sigma/(4 alpha) and units
- `audit_full_compare.py`, `audit_full_compare2.py`, `audit_full_compare3.py`:
  combined Approx 1+2 P_abs error
- `audit_total_pabs.py`: many-path realistic scenario error
- `audit_translation_icnirp.py`, `audit_identifiability.py`,
  `audit_Qfactorization.py`, `audit_realsnell.py`: misc
