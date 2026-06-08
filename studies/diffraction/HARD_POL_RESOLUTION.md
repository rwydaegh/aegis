# Hard-pol (TE_z / p-pol) deep-shadow decay: resolved

Date: 2026-06-08. Analysis: `studies/diffraction/hard_pol_analysis.py` (read-only
layer over `cylinder_oracle.py` and `poles.py`, neither modified).

## Answer

The contradiction was a refractive-index sign-convention bug, not new physics.
The exact-dielectric oracle and the pole tracker were both fed
`SKIN_28GHZ.n_complex = 4.493 - 1.786j` (Im < 0). Under the oracle's `e^{-iwt}` /
outgoing-`H^(1)` convention a passive lossy medium **must** have Im(n) > 0, so the
stored constant makes the oracle model a **gain cylinder**. The gain pumps the
surface-hugging p-pol creeping wave and produces method B's slow / anti-Fock /
"slope decreasing with kR" / even-growing decay. With the physically correct
index (the conjugate, Im n > 0) the exact-dielectric hard wave is **clean Fock**:
a single impedance-shifted creeping pole, well separated from interior
resonances, that reproduces the exact field to 0.03%. **Method A (Leontovich) was
right; method B was the artifact.** A soft/hard Fock gate with skin-impedance
constants is sufficient for p-pol shadow dose; no surface-wave term is needed.

## The bug (convention-free proof)

AEGIS's Fresnel layer builds `eps = eps' - i*sigma/(w*eps0)` (engineering
`n - ik`, i.e. `e^{+iwt}`). The hand-rolled cylinder oracle uses `e^{-iwt}` with
outgoing `H^(1)`, which needs `n + ik`. Mismatch -> gain. Proof needing no sign
choice (Q_sca = (2/ka) sum |b_n|^2 is manifestly positive; absorption can only
*reduce* Q_sca below its lossless value):

| index (ka=40)        | TM Q_sca | TE Q_sca | TM Q_abs | TE Q_abs |
|----------------------|---------:|---------:|---------:|---------:|
| lossless n=4.493     |   2.377  |  2.237   |  +0.000  |  +0.000  |
| stored  n=4.493-1.79j|   2.959  |  4.933   | **-0.88**| **-3.58**|  (Q_sca > lossless = gain)
| conjugate n=4.493+1.79j| 1.622  |  1.363   |  +0.460  |  +0.711  |  (physical absorber, Q_ext->2)

Only the **conjugate** is physical. (Independently, the inward surface Poynting
the oracle returns, `Im(Psi conj Psi')`, is positive only for the conjugate.)

**Why only the hard channel broke.** The soft (TM) wave has a near-node at the
surface, barely penetrates, and is sign-robust: TM shadow slope is 8.0 (stored)
vs 7.2 (conj) at kR=20, and 22.3 vs 21.6 at kR=320 - essentially identical, which
is why soft was "validated" either way. The hard (TE) wave hugs and penetrates
the lossy/gain surface, so the sign flips it from Fock-decaying to flat/growing.

**Why the sphere oracle looked clean.** `sphere_oracle.py` uses `miepython`,
whose convention is `n - ik` (line 28), so the stored constant is *correct there*.
The corrected cylinder now agrees with the sphere (lit GO recovery, Fock shadow,
no p-pol enhancement). The FINDINGS narrative "double curvature kills the 2D
resonance" was wrong: it was the convention. The lit-region p-pol "1.4-5x
enhancement / closed-cylinder resonance" (erratic 2.08, 2.17, 2.40, **29.4**,
8.45 across kR) is the same gain artifact; with the physical index lit p-pol
|P|/mu is flat at 0.702 to three digits (clean GO).

## (a) The physical pole, isolated and verified

Dominant exact-dielectric TE pole (physical index), three independent routes agree:

| kR  | analytic zero of D(nu)   | matrix-pencil from exact field | 2 Im nu (slope) | interior-res. proximity |
|-----|--------------------------|--------------------------------|-----------------|-------------------------|
| 40  | 42.515 + 2.826j          | 42.515 + 2.826j                | 5.65            | ~4e28                   |
| 80  | 83.446 + 3.750j          | 83.446 + 3.750j                | 7.50            | ~2e58                   |
| 160 | 164.690 + 5.043j         | 164.690 + 5.043j               | 10.09           | ~1e118                  |

It is the impedance-shifted Fock creeping pole (Re nu ~ ka + (ka/2)^{1/3} q,
just outside ka), **not** an interior resonance: |J_nu(n ka)| is 10^28-10^118 from
zero. A broad 280-seed scan over Re nu in [0.7,1.25]ka, Im nu in [0.2,14] finds no
slower physical pole; the planar Zenneck order (Re nu < ka, leaky/fast) is not a
discrete pole. Residue reconstruction (fit pole amplitudes to the exact complex
field, both terminators):

| kR  | 1-pole err | 2-pole err | 3-pole err |
|-----|-----------:|-----------:|-----------:|
| 40  |   6.5%     |   0.51%    |  0.044%    |
| 160 |   5.5%     |   0.36%    |  0.026%    |

The shadow field is the creeping-pole ladder. No separate surface-wave term.

## (b) Method A vs B, quantified

- **B is the gain artifact.** Matrix-pencil on the *gain*-index exact field gives
  dominant slope 2.05 (kR40), 1.30 (kR80), **-0.61** (kR160) - the wave grows into
  shadow at kR160. That is exactly method B's "anti-Fock, decreasing with kR."
- **A was right and sign-robust** (its constant impedance pole is reactance-
  dominated). With the correct sign the Leontovich pole matches the exact
  dielectric pole to three digits: 5.654 vs 5.652, 7.503 vs 7.499, 10.099 vs 10.085.
- **No genuine Zenneck mode.** The inductive skin (Z_s/Z0 = 0.192 + 0.076j) does
  support a planar p-pol surface wave, but on the convex cylinder it is leaky
  (Re nu < ka) and radiation-damped far beyond the creeping pole (planar slope
  1.1-4.5 vs actual 4.6-10). Deep-shadow local slopes are constant to the back
  point (kR160: 9.1, 10.0, 10.1, 10.0 over 10-85 deg) - no slow tail.

## (c) The true numbers (physical index, exact skin cylinder)

Shadow power-decay slope (1/rad), measured field vs dominant pole 2 Im(nu):

| kR  | TM meas | TM pole | TE meas | TE pole | TM/TE |
|-----|--------:|--------:|--------:|--------:|------:|
| 20  |  7.23   |  8.38   |  3.70   |  4.32   | 1.95  |
| 40  |  9.67   | 10.64   |  5.11   |  5.65   | 1.89  |
| 80  | 12.81   | 13.50   |  7.08   |  7.50   | 1.81  |
| 160 | 16.75   | 17.09   |  9.81   | 10.09   | 1.71  |
| 320 | 21.56   | 21.62   | 13.58   | 13.71   | 1.59  |

**Scaling.** TM is clean Fock, exponent ~1/3 (PEC control: 0.325 -> 0.333). TE is
Fock asymptotically but with a *drifting coefficient*: the effective hard
eigenvalue q_eff(TE) = Im(nu)/[(ka/2)^{1/3} sin60] grows 1.20 -> 1.35 -> 1.59 ->
1.84 over kR = 40 -> 2560, migrating from the PEC-hard value 1.019 toward the
PEC-soft value 2.338, because the Fock impedance parameter ~ (ka)^{1/3}/n grows
with kR (the surface looks progressively "softer" to the hard creeping wave).
q_eff(TM) stays pinned at ~2.3 (soft). Consequences: the TE local log-log
exponent rises to ~0.45 near kR ~ 320-640 then declines back toward 1/3; the
soft/hard ratio falls from ~1.95 toward 1 (1.88 -> 1.26 at kR 40 -> 2560). Over
body-relevant kR (limb radius 1-10 cm at 28 GHz gives kR ~ 6-90; most parts
20-90) the effective TE exponent is ~0.41-0.43 and the soft/hard ratio ~1.7-1.95.

Boundary admittances re-derived and verified: dielectric TM g = n*ka*D, TE
g = (ka/n)*D with D = J_nu'(n ka)/J_nu(n ka); D -> -i as |n| -> inf (Leontovich
g = -i*ka*n / -i*ka/n); PEC soft H_nu = 0 -> q1 = 2.343 (Ai zero 2.338), PEC hard
H_nu' = 0 -> q1 = 1.025 (Ai' zero 1.019); dielectric pole -> PEC-hard pole as
|n| -> inf.

## Recommendation

One line: **use a soft/hard Fock gate with the impedance-Fock (Leontovich)
eigenvalue at the correct sign (Im n > 0) - it reproduces the exact dielectric
p-pol shadow to 3 digits, so no extra surface-wave term is needed - but tabulate
the hard eigenvalue as q_hard(kR, band) (it drifts ~1.0 -> 2.3, not the fixed PEC
1.019), and fix the gain-sign bug in `cylinder_oracle.py` and `poles.py` by
conjugating the index.**
