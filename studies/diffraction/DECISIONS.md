# Fock diffraction framework: decisions, assumptions, findings log

Running log. Newest entries appended under each section. Started 2026-06-08,
overnight autonomous session (Robin asleep, full decision authority granted).

Branch: `feature/fock-diffraction`. Spec:
`docs/superpowers/specs/2026-06-08-fock-diffraction-framework-design.md`.
Supersedes/absorbs `2026-06-06-self-shadowing-visibility-design.md`.

## Locked decisions (from the conversation)

- D1. Replace the heuristic GeLU shadow gate with a physically exact Fock
  transition function. The current GeLU width scales as `(kR)^{-1/2}`; the
  exact convex-body penumbra scales as `(kR)^{-1/3}` (validated on the cylinder
  oracle, exponents 0.35-0.39). The gate is therefore wrong in functional form,
  not just constant, 1.6x-2.7x too narrow at 28 GHz.
- D2. The Fock transition is ONE complex function `g(xi)`. Incoherent levels
  use `|g|^2` on power; coherent levels use the full complex `g` on the field.
  This guarantees coherent >= incoherent by construction (Robin's requirement).
- D3. Closed-form uniform `g(xi)` (lit Fresnel-transition core + shadow residue
  series), differentiable, not a shipped table. Validated, not fitted, against
  the cylinder and sphere oracles. If the closed form cannot be pinned to a few
  percent against the oracle, fall back to an oracle-anchored representation
  with a closed-form shadow tail (documented if invoked).
- D4. Soft/hard polarization split carried by reusing `te_tm_power_weights`
  (already shipped in #835): `g = w_s g_soft(xi) + w_p g_hard(xi)`. PEC
  soft/hard decay ratio 2.295 validated on the cylinder.
- D5. Impedance-corrected shadow constants for skin per (band, tissue), from the
  Airy-root solve `Ai'(t) - q Ai(t) = 0` with `q` from the surface impedance
  `eta = 1/n`. Low stakes (shadow dose is small) but included for the hard
  polarization, whose PEC constant is inadequate on a lossy surface. May lean on
  the parallel `studies/diffraction/poles.py` (cron-agent work) for the exact
  dielectric creeping pole.
- D6. Proper per-triangle curvature radius `R` promoted into `geometry/`
  (quadric/normal-cycle estimate), cached, shared by the local gate and the
  visibility bake. Replaces the crude viewer-only mean-|delta-n| proxy.
- D7. Orthogonal axis: a single selector `diffraction_model in {none, gelu,
  fock}`, composing with levels 2-6 and the existing fresnel/polarisation/
  curvature flags. NO new fidelity levels (avoid level-soup, keep the table a
  clean grid). Inter-body reflection is a SEPARATE optional flag
  `inter_body in {off, specular1}`, not folded into the diffraction axis.
- D8. Inter-body B1 (single specular recapture, reusing the visibility BVH) is
  included in this spec as an optional, off-by-default flag. Earlier report:
  body-averaged enhancement <= 8%, specular recapture ~ diffuse (not 1/3),
  worst concavity 1.85x.
- D9. Coherent scope boundary (the one genuine seam): coherent-LOCAL gets the
  exact complex phase (cheap, validatable on convex oracles). Coherent-DISTAL
  ships at amplitude `|g|` with the virtual-direct phase as a DOCUMENTED
  approximation (so coherent never overpredicts the shadow and is exact where
  the dose lives: lit + local penumbra). The rigorous distal-coherent
  diffracted-geodesic phase is a FOLLOW-UP gated on a two-body oracle
  (analytic multi-cylinder via coherent/translation.py first, FDTD homogeneous
  phantom as the 3D confirmation). Reason for the seam: validatability, not
  compute (the gate is one complex (M,N) multiply, negligible vs Q).
- D10. OUT of scope: multi-edge / double diffraction (additive deep-shadow that
  converges toward full RT). Not justified by dose impact. Single binding edge
  only, matching the old self-shadowing spec.
- D11. Both near field and far field must work concretely and be tested. Far:
  shared per-path direction, `d1 -> inf`. Near: per-triangle direction to the
  point source, finite `d1` in the Fock width via the `d1/(d1+d2)` wavefront
  factor (already in the old spec's sigma). Near-field path is the phone module.
- D12. Frontend: a clear selector for `diffraction_model` plus the `inter_body`
  toggle, wired through the Zustand store, HUD, compute payload, and backend.

## Physics findings (validated)

- F1. Limb diffraction is Fock not knife-edge: shadow decay scales `(kR)^{1/3}`
  (cylinder exponents PEC 0.35-0.39, skin-soft 0.402, skin-hard 0.455), not
  `(kR)^{1/2}`. (skin numbers post sign-fix, see F4b.)
- F2. Soft/hard PEC decay ratio converges to the textbook 2.295 (Ai vs Ai'
  zeros) as kR grows (1.96 -> 2.28 over kR 10 -> 320).
- F3. On a sphere (double curvature, no 2D resonance, surface Poynting validated
  to 0.7% of Mie Qabs), flat Fresnel is accurate to ~1% out to 66 deg incidence
  for BOTH polarizations; the only departure is the penumbra within ~15 deg of
  grazing (1.46 s-pol, 1.35 p-pol at 82 deg), nearly polarization-symmetric.
- F4. The large p-pol "curvature enhancement" seen on the cylinder (1.4x-5x) was
  TWO artifacts stacked: (a) a gain-medium sign bug (AEGIS n-ik fed to the
  e^{-iwt} oracle = gain cylinder, corrupts the surface-bound hard wave), now
  fixed by conjugating to Im(n)>0; and (b) a closed-cylinder surface-wave
  resonance, gone on the sphere. With both fixed, the corrected cylinder and the
  sphere AGREE: lit-region exact/GO -> -1.00 for both pols at all incidences by
  kR=320. There is NO p-pol lit-region curvature-Fresnel coupling at body scale.
  Do not model one.
- F4b. Corrected lossy-skin cylinder: shadow exponents are clean Fock for BOTH
  pols (soft 0.402, hard 0.455). The soft/hard decay ratio is 1.6-1.9 (below PEC
  2.295, decreasing with kR): the lossy impedance damps the hard creeping wave
  and shrinks the soft/hard asymmetry, pulling the hard q1 from PEC 1.019 up
  toward ~1.4. This is the regime the impedance-Fock solve (D5) captures. The
  earlier "skin hard decays anomalously slowly, ratio explodes" was the sign
  bug, not physics.
- F5. Whole-body SAR is essentially immune to the diffraction model (2-4%
  integrated on the cylinder); the gain is pointwise near shadow edges. Deep-
  shadow leakage is real but dose-negligible (~1e-6 of lit) for the local
  terminator. (Distal occlusion is the regime where shadow dose can matter.)

## Assumptions (to revisit / flag in code)

- A1. `R = 2/H` mapping from twice-mean-curvature to a scalar radius for the
  Fock variable, isotropic (mean) curvature. The in-incidence-plane radius
  varies with direction; mean curvature is a first approximation. Direction-
  resolved principal curvatures are a possible refinement (chosen to keep mean
  for v1 unless the oracle says otherwise). VERIFY against the sphere/cylinder.
- A2. Single binding edge for distal occlusion (nearest occluder). Overlapping
  penumbrae and additive multi-edge deep shadow are second order / out (D10).
- A3. Coherent-distal virtual-direct phase (D9) is an approximation; flagged in
  code and docs; not claimed validated until the two-body oracle exists.
- A4. PEC soft/hard constants bracket the true dielectric split; the impedance
  correction (D5) refines the hard constant. Corrected cylinder (F4b) now gives
  the target: the lossy-skin soft/hard ratio is 1.6-1.9, so the impedance solve
  should pull the hard q1 from PEC 1.019 up toward ~1.4 (soft q1 stays ~2.338).
  The exact dielectric hard pole may still differ from Leontovich; treat the
  impedance constant as refinable and cross-check against poles.py when ready.

## Decision log (made autonomously overnight)

- 2026-06-08 L2. The parallel cron agent's `HARD_POL_RESOLUTION.md` (rigorous
  Q_sca/Q_abs positivity proof + matrix-pencil pole extraction + 280-seed pole
  scan) independently reached the SAME sign-bug conclusion and goes further,
  RESOLVING A4 and refining D5/#5 implementation:
  * The impedance-Fock (Leontovich) creeping pole at the correct sign reproduces
    the exact dielectric p-pol shadow field to 3 digits (pole 5.654 vs exact
    5.652 at kR40, etc.). No separate Zenneck/surface-wave term is needed: the
    skin's planar p-pol surface wave is leaky (Re nu < ka) and radiation-damped
    far beyond the creeping pole on a convex body. Method A (Leontovich) right,
    method B (pole-track on stored gain index) was the artifact.
  * KEY IMPLEMENTATION REFINEMENT: the hard eigenvalue is NOT the fixed PEC
    q1=1.019. The Fock impedance parameter scales as (kR)^{1/3}, so q_hard DRIFTS
    with kR: q_eff(TE) grows 1.20 -> 1.35 -> 1.59 -> 1.84 over kR=40 -> 2560,
    migrating from PEC-hard 1.019 toward PEC-soft 2.338 (surface looks
    progressively "softer" to the hard wave). q_eff(TM) stays pinned ~2.3.
    Consequence: TE effective shadow exponent peaks ~0.45 near kR~320-640 then
    declines back toward 1/3; soft/hard ratio falls 1.95 -> 1.26 over kR
    40 -> 2560. Over body-relevant kR (limb 1-10 cm at 28 GHz -> kR ~6-90, most
    20-90): TE exponent ~0.41-0.43, soft/hard ratio ~1.7-1.95.
  * So `kernels/fock.py` must compute the hard constant from the Leontovich
    impedance-Fock solve `Ai'(t) - q Ai(t) = 0` with q carrying the (kR/2)^{1/3}
    impedance factor (NOT a fixed q), giving a kR- and band-dependent
    q_hard(kR, band). Soft uses the PEC q1=2.338 (impedance-robust). Boundary
    admittances to use: dielectric TM g = n*ka*D, TE g = (ka/n)*D,
    D = J_nu'(n ka)/J_nu(n ka); Leontovich limit g -> -i*ka*n (soft),
    -i*ka/n (hard). This UPDATES A4 from "refinable open question" to "resolved,
    tabulate q_hard(kR,band)".
- 2026-06-08 L1. Discovered and fixed a gain-medium sign bug in the cylinder
  oracle (AEGIS stores n-ik for e^{+iwt}; the oracle uses e^{-iwt} outgoing
  Hankels needing Im(n)>0; feeding Im(n)<0 modelled a gain cylinder). Fix:
  conjugate to Im(n)>0 at the top of the dielectric solver. Re-ran decay and
  GO-recovery: skin TE exponent 0.045 (corrupted) -> 0.455 (clean); lit-region
  p-pol enhancement vanished (both pols -> -1.00 GO). This revised F4 and
  sharpened A4 (see F4b). No spec decision changed: D1-D12 stand; the sphere had
  already de-risked the lit region with the correct convention (miepython), so
  the framework scope was never built on the corrupted numbers.
