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

- 2026-06-08 L13 (from the unified-report C-metric derivation; CORRECTS the Phase B
  distal gate before it is wired). Formalizing the distal angular-clearance gate
  (theory/unified/sec_08_distal_cmetric.tex) surfaced three errors in the spec's
  `fock_xi_distal` that must be fixed when the distal gate is implemented (Phase B):
  * SIGN: the spec wrote xi_d = -(k R_occ/2)^{1/3} c w_nf. Under the locked
    conventions (c>0 = clear, xi>0 = lit) that minus zeros the gate on every clear
    direction. Correct: xi_d = m_occ * c / w_nf (clear maps to the lit branch). The
    spec's minus is only meaningful if c is reinterpreted as shadow depth s=-c.
  * NEAR-FIELD FACTOR PLACEMENT: w_nf = sqrt(d1/(d1+d2)) multiplies the WIDTH
    (DIVIDES the detour: xi_d = m_occ c / w_nf), NOT multiplies xi. Near field
    NARROWS the penumbra; the spec's "w_nf * xi" inverts the trend. Matches the
    2026-06-06 self-shadowing spec's validated sigma_ke ~ sqrt(d1/(d1+d2)).
  * KNIFE-EDGE IS A SEPARATE WIDTH, not a naive R_occ->inf limit. The finite knife
    penumbra comes from the Fresnel PATH detour (distance-set), absent from the
    Fock curvature variable. The distal gate must carry BOTH widths: Fock-curvature
    sigma_Fock = 2^{5/6}(k R_occ)^{-1/3} AND Fresnel sigma_ke ~ (k L)^{-1/2}. The
    sharp-edge limit recovers the old erf self-shadowing gate exactly (Phi_lit IS
    that erf gate). Crossover R_occ* ~ L sqrt(kL) (~1 const): at 28 GHz few-cm
    standoff R_occ* ~ 10 cm, so a finger/limb is Fock, a wall edge is knife.
  Carry these into the Phase B distal implementation; do NOT copy the spec's
  fock_xi_distal sign/placement verbatim. Now formally derived in the report.
- 2026-06-08 L12 (real-phantom E2E validation, post-CI). Ran the full pipeline on
  the real duke phantom (56024 triangles) under diffraction_model none vs fock,
  far-field plane wave + random psi: incoherent L3 IDENTICAL (no gate at L3,
  correct), L6 finite & sab>=0, pointwise max |fock-none|/max = 40.8% near
  terminators (the penumbra, expected), WHOLE-BODY SAR change 6.58%, sub-second.
  Coherent L7 (with precoder) finite & sab>=0, lit-region max unchanged (consistent
  with L9). No NaN, no crash, ~1-3s on 56k tris. NOTE: the whole-body change vs
  ReLU is ~6-7% on a real one-side-lit phantom, ABOVE the cylinder oracle's 2-4%
  (F5) - a real phantom has far more grazing/shadowed area under a single plane
  wave, so the penumbra reweighting matters more. Physically sensible (fock adds
  the real penumbra+creeping leakage that hard-ReLU cuts); not a bug. The "2-4%"
  claim is cylinder-specific; quote ~6-7% for real phantoms vs ReLU. CI fully
  green (ruff + basedpyright 0 + full pytest + benchmarks) on the branch.
- 2026-06-08 L11 (final review gap, follow-up). `src/aegis/coherent/_fast.py` (the
  JAX-accelerated twins compute_body_channel_factored_jax / compute_q_for_body /
  compute_q_batch_vmap, used by the JSAC v0.33 batched ECBF solver) did NOT
  receive the Fock gate, while the NumPy reference compute_body_channel_factored
  did. No live src/ caller routes user-facing dose through the JAX twins today
  (only tests + the JSAC batched solver), so nothing is silently ungated in the
  product. But if the batched solver is later wired into a user/paper dose path it
  will diverge from the engine fock default. Tracked as a follow-up (thread fock_R
  + representative q_F into the _fast.py twins, JAX-traceable). Not in this PR to
  keep it focused; the PR's final holistic review approved with this as a noted
  Minor.
- 2026-06-08 L10 (Task 7 design). The kernel takes a SCALAR static `q_F_h`. The
  hard eigenvalue drifts with per-triangle kR, but that drift is ~20% on a shadow
  tail of ~1e-6 of lit dose (F5) - dose-negligible. So the engine passes a single
  representative impedance-corrected hard q_F per (band, body): kR_rep =
  k * median(fock_R[finite]), q_F_h = fock_impedance_param(eta, kR_rep, "hard")
  (one cached mpmath solve). Soft uses PEC (q_F_s=None). This captures the big
  impedance effect (ratio ~1.7 vs PEC 2.295); the secondary per-triangle drift is
  a documented, dose-negligible approximation. A per-triangle eigenvalue-array
  path was deliberately NOT added (it would need another fock.py + kernel
  signature change for no dose benefit). Revisit only if a distal/deep-shadow use
  case (Phase B) makes the drift dose-relevant.
- 2026-06-08 L9 (from Task 6 implementation). The D2 "coherent >= incoherent by
  construction" claim needs a precise qualifier. `compute_fresnel_operator` hard-
  zeros the transmission (t_s = t_p = 0) for mu <= 0, so the coherent body channel
  carries field ONLY in the lit + penumbra region. The coherent-local Fock gate
  therefore modulates the penumbra rolloff (complex, exact, where the dose lives)
  but injects NO creeping FIELD into the deep geometric shadow, whereas the
  incoherent fock_local adds |creep|^2 there independent of t. Consequence:
  * Lit + penumbra (dose-relevant): coherent >= incoherent holds (constructive
    phase headroom). Verified by trace(Q_complex) == trace(Q_magnitude) exactly
    (|g_complex|^2 = |g|^2, the complex gate loses no total dose vs the magnitude
    gate) and matched-filter dose n_elem*lambda_max(Q) >= trace(Q) >= isotropic.
  * Deep geometric shadow (mu < 0): coherent-local is identically 0 (no field)
    while incoherent has |creep|^2 ~ 1e-6 of lit, so coherent is ~1e-6 BELOW
    incoherent there. Dose-negligible (F5), documented, NOT a pointwise D2
    violation worth fixing in Phase A. Carrying the complex creeping FIELD into
    the coherent deep shadow is the same follow-up family as coherent-distal
    (D9/A3): it needs the creeping geodesic field vector, which the Fresnel
    operator does not provide. Deferred with coherent-distal.
- 2026-06-08 L8 (from Task 4 implementation). The legacy `diffraction` bool maps
  to a diffraction_model differently at the two layers, to keep back-compat while
  still making Fock the user-facing default (D7):
  * KERNEL (`spatial_kernel`): explicit `diffraction_model` wins; else legacy bool
    True -> "gelu", False -> "none". This preserves byte-identical behavior for
    the ~10 existing direct kernel callers (tests, viewer dosimetry, chunking
    suite) that pass `curvature_H` but no `fock_R`. Making the kernel bool default
    to fock would raise fock_R-missing ValueErrors in all of them.
  * ENGINE (`engine.compute`, Task 7): `diffraction_model` defaults to "fock" (the
    new D7 default); the engine ALWAYS computes and supplies `fock_R`, and maps
    its own legacy bool True -> "fock", False -> "none", passing the resolved
    EXPLICIT diffraction_model down to the kernel (so the kernel's bool mapping is
    bypassed). Net effect: end users get Fock by default via the engine/frontend;
    direct kernel callers keep gelu. Task 9 rebaselines the goldens that move
    under the new fock default.
- 2026-06-08 L7 (from Task 2 implementation). The schematic Fock impedance
  parameter q_F_hard = i m eta (leading-order Leontovich) does NOT reproduce the
  exact dielectric pole at body-scale kR: it overshoots the hard pole by ~17% at
  kR=40 (6.08 vs target 5.65), worsening with kR, and the discrepancy is
  eta-dependent (no universal rotation fixes it) - the irreducible finite-kR
  pre-asymptotic error of leading-order Fock. Resolution (the right one):
  `fock_impedance_param` solves the EXACT Leontovich creeping pole (via mpmath,
  the same method as studies/diffraction/poles.py, which reproduces
  HARD_POL_RESOLUTION.md table a to 3 digits) and returns the equivalent
  q_F = Ai'(t*)/Ai(t*). Feeding that to the Newton _impedance_roots recovers the
  dominant pole to rel err < 0.002 (5.654/7.503/10.099 vs targets exactly).
  q_eff drift 1.13 -> 1.80 over kR 4 -> 2048 and soft/hard ratio 1.94 -> 1.57
  over kR 20 -> 320 both match the doc. Cost: adds mpmath as a runtime dep (was
  transitive); used only at table-build time (cached per band), PEC path stays
  mpmath-free (lazy import). Eigenvalues are constants fed into the xp gate, so
  differentiability w.r.t. xi/mu is preserved. Spec's "q_F ~ i m eta" is now
  marked as the schematic leading-order form, superseded by the exact pole solve.
- 2026-06-08 L6 (from Task 1 implementation). Two refinements surfaced building
  kernels/fock.py against the oracle:
  * The creeping residue series is a SHADOW-SIDE asymptotic: with nu_p =
    q_p exp(-i pi/3), |exp(i nu_p xi)| GROWS for xi > 0 (lit). The additive
    composite g = Phi_lit + Psi_shadow therefore requires Psi_shadow to be
    windowed to vanish in the lit (evaluate the creeping phase at min(xi,0) and
    taper by (1 - Phi_lit)). In deep shadow the window is the identity, so the
    validated sqrt3*q_p decay law and the 2.295 ratio are recovered exactly
    (~0.5% in tests). The spec's "Psi_shadow -> 0 deep lit" was only true with
    this windowing; spec updated to state it.
  * PEC oracle observables are polarization-dependent: the hard (TE) observable
    is the surface FIELD (angle-independent GO), giving a clean kR-independent
    field-gate terminator |g(0)|^2 ~ 0.488 (amplitude 0.70, ABOVE the knife 0.5:
    the creeping wave adds CONSTRUCTIVELY, so use residue MAGNITUDES). The soft
    (TM) observable is the surface CURRENT (~sin^2 GO, diverges as 1/sin^2 at the
    terminator) and cannot anchor a field-gate terminator; soft is validated via
    its shadow decay instead. One shared Fock prefactor is pinned to the hard
    terminator.
  * LIMITATION (carry to Phase B): a 3-pole additive composite with one prefactor
    cannot simultaneously match the terminator value AND the deep-shadow creeping
    amplitude; pinning the terminator under-predicts the deep shadow by ~3-4x.
    Accepted for Phase A (local gate): the penumbra/terminator (dose-relevant) is
    matched to ~0.09 abs on |g|^2, and deep-shadow dose is ~1e-6 of lit (F5), so
    a 3-4x error there is ~4e-6 of lit, negligible. BUT the DISTAL occlusion gate
    (Phase B) reuses fock_g in deeper shadow where dose can matter (hand
    shadowing cheek); revisit the deep-shadow amplitude there (more poles, or a
    separate deep-shadow amplitude anchor, or the tabulated Pekeris/Logan Fock
    function) before relying on distal deep-shadow magnitudes.
- 2026-06-08 L5. Spec-review loop complete (3 iterations, strict reviewer vs the
  actual codebase). Outcome and physics/design clarifications now baked into the
  spec:
  * Coherent gate goes into `coherent/body_channel.py` (the G_tilde -> Q dose
    path), NOT `field_channel.py` (G, which is not in the dose path). Verified.
  * Fock radius is the IN-INCIDENCE-PLANE principal radius via Euler's theorem
    (`principal_curvatures` + `fock_radius`), NOT `R = 2/H`. For a cylinder
    `2/H = 2R` would be 2x off (penumbra width off by 2^{1/3}), and the cylinder
    is a primary oracle. This supersedes A1's "mean curvature for v1".
  * Single xi convention pinned document-wide: xi > 0 lit, xi < 0 shadow; the
    creeping exponent is nu_p = q_p exp(-i pi/3) (so |exp(i nu_p xi)| decays for
    xi < 0). The gate is an additive uniform composite g = Phi_lit(xi) +
    Psi_shadow(xi), Phi_lit = 0.5 erfc(-xi/sqrt2).
  * Build order: local far-field gate (kernels/fock.py + geometry/curvature.py +
    spatial.py/body_channel.py + frontend) ships first with NO unmerged
    dependency. Distal gate is a HARD prerequisite on the 2026-06-06 visibility
    spec (not on master). Near-field local gate depends on PR #834. inter_body is
    lowest-priority/optional.
  * Lambda->0 recovers ReLU asymptotically (not bit-exact; bit-exact is
    diffraction_model="none"). Mie canary is unaffected (it never calls the
    kernel). Convex-body goldens DO move under the new fock default.
- 2026-06-08 L4. q_hard exposed as a precomputed `fock_q_hard_table(band)`
  interpolator over a log-kR grid (the hard eigenvalue drifts with kR, L2);
  d q_hard/d freq dropped from autodiff as a documented negligible term.
- 2026-06-08 L3. fock.py sign convention pinned: AEGIS stores n - ik (e^{+iwt}),
  so eta = 1/n already has Im(eta) > 0 (physical inductive skin). q_F_hard =
  i m eta, q_F_soft = -i m/eta. Regression asserts the hard pole (5.654 vs
  5.652 at kR=40) to guard the sign.

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
