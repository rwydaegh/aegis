# The discarded half: differentiable scattering, RCS, and inverse design

Agent 03. Lens: the reflected fraction `1 - T0`, physical-optics RCS of electrically large
smoothish objects, and high-dimensional inverse design of their surfaces. Written 2026-07-09 against
`BRIEF.md`. Every claim tagged `verified`, `inferred`, or `could-not-check`.

## Bottom line up front

1. The brief's physics claim in 2.2(a) is **correct at the code level**, not just in spirit. The
   Fresnel reflection coefficients are already computed in the same function that computes
   transmission, and then thrown away. Emitting a first-order monostatic and bistatic PO RCS is
   **weeks, not a year**. `verified` (code) + `inferred` (cost).

2. But the obvious headline product, **differentiable-PO shape optimization for stealth**, is the
   weakest thing in this study for Robin. It was **published as a standalone paper in 2025** (Fang,
   Wu, Ye, IEEE JMMCT, DOI 10.1109/JMMCT.2025.3569766), it lives in PO's least valid regime
   (silhouettes and edges), and its only real customer is defense procurement, which the previous
   study already closed to a two-person EU firm. Do not build the company on it.

3. The idea worth keeping splits off cleanly: **coating and impedance optimization on a fixed
   smooth body**. It is genuinely high-dimensional (10^4-10^5 triangles), gradients are the only
   way to solve it, and crucially it stays inside PO's valid regime because the shape and its
   silhouette do not move. That is the one place where differentiability is essential *and* the
   physics is trustworthy. The civilian markets for it are real but thinner than they first look.

4. A quieter winner that nobody framed this way: the transmission half AEGIS already ships **is a
   radome / radar-transparent-structure engine**. Automotive radar covers, emblems, and 77 GHz
   fascia are a large, growing, purely civilian supplier problem, and the design objective
   (maximize transmission, minimize boresight error and insertion RCS) is exactly what AEGIS's
   existing `T0` operator computes, differentiated. This does not even need the discarded half.

---

## 1. Is the physics claim right? (verified)

### The reflected field is computed and discarded

`src/aegis/tissue/fresnel.py::_fresnel_core` returns six quantities:

```
return r_s, r_p, T_s, T_p, t_s, t_p
```

`r_s, r_p` are the amplitude **reflection** coefficients. `t_s, t_p` are the amplitude
**transmission** coefficients. `verified` by reading lines 42-59.

The coherent dosimetry pipeline uses only the transmission half. `fresnel_operator.py::fresnel_coeffs_from_mu`
(line 97) calls `_fresnel_core` and keeps only `t_s_out, t_p_out`. `apply_fresnel_operator` (line
149) builds `F_psi = t_s*psi_s*e_s + t_p*psi_p*e_p`, the transmitted field. `body_channel.py`
assembles `G_tilde` from that transmitted field and `exposure_operator.py` forms `Q = sum area * G^H G`.
Nowhere is `r_s` or `r_p` consumed. `verified`. The only callers of the reflection coefficients are
the convenience wrappers `fresnel_reflection` / `fresnel_amplitude` in the same file, and a grep
shows those are not imported anywhere in the coherent pipeline. `verified` (grep of `src/` for
`r_s|r_p|fresnel_reflection` outside `tissue/fresnel.py` returns nothing in the coherent path).

A full-repo grep for `rcs|radar cross|monostatic|bistatic|scattered field|radiation integral`
returns zero electromagnetic-scattering code. Every "scatter" is `scatter-add` (einsum
accumulation) and every "far field" is antenna directivity or the plane-wave source limit, never a
scattered far field. `verified`. So the brief is exactly right: AEGIS keeps `T0`, discards
`1 - T0`, and the discarded half is sitting one variable swap away.

### What is actually missing to emit RCS

The existing machinery gives you, per triangle `t`:

- centroid `r_t`, area `A_t`, outward normal `n_t` (geometry, already differentiable end to end,
  `tests/test_jax_grad.py:242,267`, `verified`),
- incident field direction `k_hat`, incident polarization `psi`,
- the reflection operator `r_s, r_p` and the TE/TM basis `e_s, e_p` (already built), `verified`.

To get a scattered far field toward an observer direction `k_obs` you need to add three things, none
of which is research:

1. **Reflected surface field / equivalent currents.** Swap `t_s,t_p` for `r_s,r_p` in the same
   operator to get the reflected tangential E, or form the PO current `J_t = 2 (n_t x H_inc)` on the
   lit side. Directly reuses `apply_fresnel_operator`. `inferred`, straightforward.

2. **Observation Green's function / radiation phase.** The surface field channel today carries the
   *incident* phase `exp(-i k0 k_hat . r)` (`field_channel.py:62`). The radiation integral needs the
   *observation* phase `exp(+i k0 k_obs . r)`, so the per-triangle far-field contribution is
   `A_t * (reflected field) * exp(i k0 (k_hat - k_obs) . r_t) * sinc-factor`. For monostatic,
   `k_obs = -k_hat`. This is the standard Ludwig PO triangle integral (a closed-form phase integral
   over the triangle, or a centroid-plus-area approximation for electrically small facets).
   `inferred` from standard PO; the phase structure is identical to what `field_channel.py` already
   assembles, only the sign of the exponent and the summation target change (sum over triangles
   toward one observer, instead of accumulate at each surface point).

3. **RCS normalization.** `sigma = lim 4 pi R^2 |E_scat|^2 / |E_inc|^2`, a scalar reduction of the
   coherent sum. Trivial.

The bistatic case is the same integral with `k_obs` free. A monostatic sweep is a loop over
incidence = observation directions. All of it is a coherent sum with a phase and an area weight,
which is *exactly the operation AEGIS is built around*, run toward an observer instead of at the
skin. Because it is the same einsum with autodiff-friendly ops, the gradient wrt vertices, material,
frequency, and incidence comes for free from the existing JAX backend. `inferred`, high confidence.

### Engineering cost, honestly

- **Rough monostatic single-bounce PO RCS demo on an existing mesh: about a week.** The pieces are
  all present; you are re-summing them. `inferred`.
- **Credible bistatic + monostatic PO engine with polarization, validated against a sphere Mie
  series and a flat-plate closed form: 3-6 weeks.** AEGIS already has the Mie regression harness as
  its CI canary (`CLAUDE.md`, `verified`), so the validation oracle exists. `inferred`.
- **PTD edge diffraction (Ufimtsev fringe currents): add 1-2 months.** It is genuinely a per-edge
  add-on, not a rewrite (see section 2), but it needs edge extraction from the mesh, the fringe-current
  coefficients, and diffraction-cone bookkeeping. `inferred`.
- **Multi-bounce (SBR, corner reflectors, cavities): months to a year, and it is a different
  algorithm** (ray tree + PO painting). This is where "a first-order PO on each triangle" stops
  being enough. `inferred`.

So the brief's "a week or a year" question resolves to: **a week for a toy, ~2 months for a
publishable single-bounce differentiable PO-plus-PTD engine, a year if you want the multi-bounce
low-RCS regime.** The cheap version is real and fast. The expensive version is exactly the stealth
regime, which is the one Robin should not chase anyway.

---

## 2. Where first-order PO breaks, and the shape-vs-coating split (this is the crux)

### PO is good where AEGIS is already good, and bad where stealth lives

PO is excellent for the **specular return from an electrically large smooth body** and progressively
wrong for the mechanisms that dominate *low* RCS:

- edge diffraction (fixed by PTD / Ufimtsev, an add-on), `verified` (this is textbook and the
  Hindawi 2012 shell-projectile paper explicitly documents PO's failure near shadow boundaries and a
  Fourier-filter patch),
- creeping and travelling waves along shadowed curvature,
- multiple bounce and corner-reflector / cavity returns (needs SBR),
- the deep nulls between specular flashes, where the true field is set by the very terms PO omits.

Stealth design is the business of pushing the specular flashes into a few narrow angles and living
in the low-RCS floor everywhere else. **That floor is precisely where PO is least valid.** So
first-order differentiable PO is a poor *stealth-design* tool and this is not a detail you can wave
away. `inferred`, high confidence, and it is the same warning the brief raises in 2.3.

### But that does not kill RCS *prediction* of ordinary objects

For aircraft, ships, vehicles, drones, wind turbines, buildings, and human bodies at their *natural*
(un-optimized, specular-dominated) RCS, PO is the industry workhorse and 3-10% value error is fine.
`verified` that PO/SBR is the commercial standard: Ansys HFSS SBR+ / Savant, Altair FEKO's PO and
SBR solvers, and the GPU-SBR literature all rest on PO currents. So a differentiable PO engine is a
legitimate *forward predictor* for ordinary targets even if it cannot design a stealth jet.

### The split the brief asked me to think about carefully

**Shape optimization marches toward silhouettes and edges. Coating optimization does not.**

- **Shape optimization** (move the vertices to reduce RCS) drives the design straight into the
  region where PO omits edge diffraction and where the gradient is largest and least trustworthy.
  The brief's 2.3 worry is real here. And the general method is now **published prior art**: Fang,
  Wu & Ye 2025, "End-to-End Differentiable RCS Optimization on 3D Geometry Based on Physical Optics
  Method," IEEE JMMCT, DOI 10.1109/JMMCT.2025.3569766, explicitly "without dimension reduction" over
  3D geometry. `verified` (found via IEEE Xplore listing and R Discovery abstract; could not read the
  full PDF, IEEE returned HTTP 418, so framework/JAX-vs-PyTorch details are `could-not-check`).
  Gradient-based RCS shape optimization by adjoint methods goes back twenty years (Bondeson et al.,
  Wiley IJNME 2004; an ACES paper does it with adjoint + automatic differentiation on MoM).
  `verified`. Shape optimization is therefore **both physically shaky in PO and no longer novel**.
  Downgrade hard.

- **Coating / impedance optimization on a fixed shape** keeps the geometry, the silhouette, and the
  shadow boundary frozen. You are choosing a per-triangle surface impedance or a per-triangle
  absorber stackup to suppress the specular return where PO is *most* valid. The gradient wrt a
  material field does not push the geometry into the edge-diffraction regime at all, because the
  geometry is not a variable. **This is the one place where differentiability is essential and PO is
  simultaneously trustworthy.** `inferred`, high confidence, and it is the cleanest technical
  argument in this report.

### On the Fock-gate moat claim (2.2b), for RCS specifically

The brief hypothesizes AEGIS's shadow-boundary gradients are less biased than hard-visibility
differentiable ray tracers because the Fock transition function is the physically correct smoothing.
For *shape* gradients that touch the silhouette, this would be a genuine edge over Sionna-RT /
DiffeRT / Mitsuba stacks. `inferred`. But two caveats: (1) the Fock gate models the shadow
*transition of the transmitted/absorbed* field, and its correctness for the *back-scattered* field
at grazing is not something I can confirm from the code, `could-not-check`; (2) even a correct
shadow-boundary gradient does not add the missing PTD edge-diffraction *physics*, it only makes the
visibility term smooth. So the moat, if real, helps shape optimization exactly where the underlying
model is still incomplete. It matters much less for coating optimization, where the moat is not
needed. Net: the Fock-gate story is more of a differentiable-rendering / sensing asset than an
RCS-design asset. Worth a targeted test (compare grad-PO vs grad-Mie wrt radius near the shadow
boundary, as the brief suggests) before anyone claims it in a pitch.

---

## 3. Divergence: 22 markets and framings, one line each

Unfiltered, defense-and-civilian mixed, before grading.

1. Low-observable aircraft / UAV shape design. Export-controlled, PO-invalid regime, Fang 2025 prior art. Weak for Robin.
2. **Radar-absorbing-material (RAM) / surface-impedance layout on a fixed body.** High-dim, gradients essential, PO valid. Strong engine, market access is the question.
3. **Radome and radar-transparent-structure design.** Uses AEGIS's transmission half directly. Civilian, growing. Strong.
4. Ship topside signature management. Naval, defense, closed to Robin.
5. Drone / small-UAS signature prediction and counter-UAS detectability. Dual-use, civilian drone-cert angle possible.
6. Automotive body / pedestrian RCS for AV radar sensor simulation. Huge market, prediction not design, incumbents strong.
7. RCS of space debris and satellites for space situational awareness. Civilian (ESA/space agencies), electrically large, PO natural.
8. SAR calibration corner-reflector / trihedral design. Low-dim, and corners are multibounce = PO poor. Weak.
9. Maritime navigation radar reflector design (SOLAS RCS compliance for small craft, lifeboats, buoys). Real regulatory RCS spec, civilian, niche.
10. Chaff and decoy design. Munitions-adjacent. Out on ethics and access.
11. Anechoic-chamber pyramidal-absorber layout optimization. Real test-lab market, moderate dimensionality.
12. RIS / reconfigurable-surface panel design (element phases 10^3-10^4). 6G, high-dim, adjacent to AEGIS coherent.
13. Conformal metasurface layout on a curved platform. High-dim, dual-use.
14. **Wind-turbine radar interference: predict and certify turbine RCS impact, and design blade RAM zoning.** Real, growing EU regulatory fight. Civilian. Strong access.
15. Radar-transparent building materials / 5G-transparent facades. Civilian construction/telecom.
16. Installed-antenna-on-platform performance (co-site, pattern distortion by the body). Same PO; Savant/HFSS market.
17. Airport / weather-radar clutter prediction from nearby structures (siting studies). Civilian planning.
18. Differentiable RCS measurement-range uncertainty budgets (sensitivity coefficients c_i = d(sigma)/dx_i). Mechanism (c), boring, billable, small.
19. Inverse scattering: shape/material recovery from measured RCS for NDT or security imaging (mmWave body scanners). Mechanism (b), civilian sensing, back to the human body in-scope.
20. Automotive radar dynamic-target-simulator calibration. Niche instrumentation.
21. Building-scatterer channel modeling for 5G/6G coverage (AEGIS RT bridge already exists). Telecom.
22. Ice-detection / dosimetry-style surface diagnostics on wind-turbine blades from radar returns. Speculative.

---

## 4. Convergence: the top four, graded

Grading axes (from brief 7): problem exists, Robin can fill it reliably, patentable, doable in two
years by two people, market size, and **does the value depend on differentiability essentially or
decoratively**. Incumbent named for each.

### Idea A. High-dimensional coating / surface-impedance optimization on a fixed body (the brief's mechanism-(a) test case)

This is the idea the brief flagged as possibly the strongest in the whole study. I tested it hard.

- **Problem exists?** Yes, but read the fine print. Choosing an absorber stackup or a metasurface
  unit-cell distribution over a curved electrically large body, so that the specular return is
  suppressed over a band and an angular window, is a real and hard problem. The literature confirms
  "design of coatings on curved surfaces is extremely complex" (EPJ Applied Metamaterials 2019 and
  the ScienceDirect hybrid-metasurface work, `verified`). `verified` that the problem is hard.
- **Genuinely high-dimensional?** For a *per-triangle continuous impedance field over 10^4-10^5
  facets*, yes, and there a sweep is flatly impossible and gradients are the only option. This is
  the cleanest differentiability-is-essential argument in the report. `inferred`, strong. **But**
  the honest caveat: most *civilian* coating problems are not solved at per-triangle granularity.
  They are solved as a handful of zones or a single homogeneous layer, which is 3-10 parameters,
  where a sweep or a surrogate wins and gradients are worth nothing (brief 3(a)). The purest
  high-dimensional version, painting a bespoke impedance on every facet of a whole platform, is a
  **stealth** problem, which is defense. So the dimensionality argument is real *physics* but its
  purest instance sits in the market Robin cannot enter. This tension is the key finding: the
  strongest technical idea points at the least accessible customer.
- **Patentable?** The general "differentiable PO for RCS optimization" claim is now blocked by Fang
  2025 and the older adjoint-AD RCS work. A narrower claim, a *certified* optimum or a Lipschitz
  bound over a *material* continuum via differentiable PO, might survive, but I could not verify
  freedom to operate. `could-not-check`.
- **Doable by two people in two years?** The forward engine yes. A credible RAM material library
  (frequency-dependent surface impedance for real absorbers) is extra work but tractable via the
  same Cole-Cole / dielectric machinery AEGIS already has for tissue. `inferred`.
- **Market and incumbent.** Today this work is done inside Ansys HFSS SBR+, Altair FEKO, and
  in-house defense codes, mostly by parameter sweeps over a few coating zones. `verified` that those
  are the incumbents. The civilian slices are anechoic-chamber absorber layout and wind-turbine
  blade RAM (see Idea B).
- **Differentiability: essential** at high granularity, **decorative** at the low-zone-count
  granularity most civilian buyers actually use. This is the whole downgrade. **Grade: strong
  engine, compromised go-to-market. Keep as the technical core, not as the standalone product.**

### Idea B. Wind-turbine radar interference: prediction, certification, and blade-RAM design

- **Problem exists?** Strongly yes, and it is *growing and regulatory*, which dosimetry-adjacent
  ideas rarely are. Wind farms degrade primary and secondary surveillance radar; consents are
  delayed or refused over it. The EU angle is live: the ~2 million euro offshore-wind "Symbiosis
  Project" is led by the Brussels European Defence Agency and 2025 material cites "measurable
  degradation in radar performance" for NATO and EU member states. The US runs a federal WTRIM
  working group with 5/10/20-year mitigation horizons. Vestas has a "stealth blade" and RAM is being
  laminated into blades. `verified` (DOE WTRIM 2024/2025 docs, IEEE Spectrum offshore-wind-radar,
  the RAM-blade patent US10330075).
- **Robin can fill it reliably?** This is the best *market-access* fit in the report: purely
  civilian, EU-centered, planning-and-consent driven, no clearance and no US supply chain needed.
  It is dual-use in flavor but the deliverable is "will this wind farm break this radar, and how do
  we mitigate," which is survivability-of-radar and siting, squarely in scope (brief 4). `inferred`.
- **Where differentiability bites.** Prediction of a turbine's enormous RCS is PO's home turf but
  differentiability is *decorative* for prediction. It becomes *essential* only for the design
  sub-problem: optimize the blade RAM zoning / lay-up (a coating problem, Idea A restricted to a
  blade) or optimize turbine siting/orientation against a radar. The blade is electrically gigantic
  and smooth, so PO is valid and a per-panel impedance field is high-dim. `inferred`.
- **Patentable?** Application-specific claims (differentiable blade-RAM zoning under a rotation-
  averaged RCS objective) may be open; I did not check FTO. `could-not-check`.
- **Doable by two?** Forward turbine RCS + a blade-coating optimizer is a focused 6-12 month build
  on the existing engine. The rotor-rotation Doppler/micro-Doppler part is extra but not required
  for the consent-level RCS question. `inferred`.
- **Market and incumbent.** Today: consultancies running FEKO / HFSS-SBR studies for wind
  developers and aviation authorities, plus radar-vendor mitigation. `verified` (SBR is the tool;
  the consultancy structure is `inferred`). Market is real but fragmented and project-based, not
  seat-license SaaS.
- **Grade: best civilian access, real regulatory pull, differentiability essential only in the
  design sub-problem. Strongest single go-to-market in this report even though the pure-tech
  novelty is lower than Idea A.**

### Idea C. Radome and radar-transparent-structure design (uses the half AEGIS already has)

The neat twist: this does **not** need the discarded reflected half at all. Radome design optimizes
*transmission* (maximize power through, minimize boresight/phase error, minimize the radome's own
insertion RCS). AEGIS's entire existing pipeline computes exactly the transmitted field `T0` through
a lossy dielectric interface, per triangle, differentiably. `verified` (that is what
`body_channel.py` / `fresnel_operator.py` compute today).

- **Problem exists?** Yes, and it is civilian and growing fast: 77-79 GHz automotive radar behind
  bumpers, fascia, and 3D-logo emblems. An emblem is "a sophisticated RF element that often degrades
  radar detection range and accuracy"; a bad radome makes low-RCS pedestrians disappear or appear at
  wrong azimuth (boresight error). `verified` (Microwave Journal 2018 emblem study, R&S QAR
  application note).
- **Robin can fill it reliably?** Yes. It is the transmission physics he already validated for
  tissue, retargeted to a multilayer plastic stackup. The design vector (per-region thickness,
  permittivity, layer count over a curved emblem) is moderately high-dim and curved-surface, where
  gradients help. `inferred`.
- **Differentiability: essential-ish.** Multilayer + curved-shape + boresight objective is enough
  parameters that gradient design beats sweeps, though a skilled RF engineer does solve simple radomes
  by hand. Honest grade: essential for the hard 3D-emblem case, decorative for a flat window.
  `inferred`.
- **Patentable?** Unclear and probably crowded (radome patents are dense, e.g. US12255385 on
  radar-transparent illuminated symbols). `could-not-check`.
- **Doable by two?** Yes, arguably the fastest to a demo because it reuses the transmission half
  unchanged and just adds a multilayer transfer-matrix per facet and a boresight-error readout.
  `inferred`.
- **Market and incumbent.** Today: Ansys HFSS and Altair FEKO for design; Rohde & Schwarz QAR for
  *measurement* (an instrument, not a design tool, so there is a design-side gap). `verified`. Tier-1
  automotive suppliers and emblem makers are the buyers, a concrete civilian customer set.
- **Grade: cleanest fit to existing code, purely civilian, concrete customer, moderate novelty.
  This is the sleeper. It sidesteps the entire "is the discarded half worth building" question by
  monetizing the half already built.**

### Idea D. Inverse scattering / sensing (mechanism (b)), civilian imaging

- **Problem exists?** Yes: mmWave security body scanners, NDT, and shape/material recovery from
  measured scattering. A differentiable forward scatter model turns any measurement into a
  gradient-descent fit for shape, pose, or material. `inferred`. This also loops back to the human
  body in an *in-scope* way (sensing, not harming, brief 4).
- **Differentiability: essential.** Inversion by gradient descent is the canonical use of a
  differentiable forward model, and it is one of the four mechanisms the brief endorses. `verified`
  (mechanism b).
- **But** the incumbents are entrenched (existing scanner vendors, and the whole inverse-scattering
  academic field) and the forward model needed for imaging usually wants multi-bounce and edge
  physics that first-order PO lacks. Reliability for Robin is unproven. `inferred`.
- **Grade: promising and differentiability-native, but further from the existing code and from a
  nameable first customer than A/B/C. Keep on the list, do not lead with it.**

---

## 5. Direct answers to the four investigation questions

1. **Physics claim right?** Yes, verified in code. Reflection coefficients are computed beside
   transmission in `_fresnel_core` and discarded. Emitting monostatic + bistatic single-bounce PO
   RCS is ~1 week for a toy, ~2 months for a validated differentiable engine, ~a year for the
   multi-bounce low-RCS regime. The Mie CI canary is the ready-made validation oracle.

2. **Does PO's breakdown kill it?** It kills *stealth shape design* (low-RCS regime, edge/creeping/
   multibounce dominated, and Fang 2025 already published the differentiable-PO shape method). It
   does **not** kill *RCS prediction of ordinary objects* (specular-dominated, PO's home) nor
   *coating optimization on a fixed shape* (PO stays valid because the silhouette does not move). The
   shape-vs-coating split is the decisive insight: **coating optimization is where differentiability
   is essential AND PO is trustworthy.** PTD is a genuine per-edge add-on (~1-2 months), not a
   rewrite, and edges are differentiable, so a PTD-corrected differentiable PO is buildable, but it
   still will not reach the deep-null stealth floor.

3. **Markets:** 22 listed in section 3. Top four defended in section 4.

4. **The dimensionality argument:** real physics, and the single strongest *technical* claim, but I
   am downgrading it on go-to-market. Per-triangle impedance over 10^4-10^5 facets is a true
   gradients-only problem, but its purest instance is stealth-coating layout, which is defense and
   closed to Robin. The civilian instances (anechoic-absorber layout, wind-turbine blade RAM, radar-
   transparent zoning) are often solved at low zone count where a sweep suffices and gradients are
   decorative. So the mechanism is sound but the accessible market for it is thinner than it looks.
   The way to keep it alive is to attach it to a civilian carrier problem where the high-dimensional
   version is actually wanted, and the best carrier is wind-turbine blade RAM (Idea B) or a curved
   automotive radome/emblem (Idea C).

---

## 6. Ranking

1. **Idea C, radome / radar-transparent structures.** Fastest to a demo, purely civilian, concrete
   Tier-1 automotive customer, monetizes the transmission half already built, sidesteps the
   discarded-half question entirely. Lead with this.
2. **Idea B, wind-turbine radar interference.** Best regulatory pull and EU market access, civilian,
   dual-use-flavored but in-scope. Differentiability essential in the blade-RAM design sub-problem.
3. **Idea A, high-dim coating engine.** The technical core and the strongest differentiability
   argument, but its purest market is defense. Ship it *as the engine under B and C*, not as a
   standalone stealth product.
4. **Idea D, inverse scattering / sensing.** Differentiability-native, civilian, but furthest from
   the code and from a first customer.

## 7. Ethics note (brief 4)

I stayed in scope. Signature *prediction* and *survivability* of platforms, radar-transparency,
radome design, wind-turbine-vs-radar coexistence, and inverse sensing are all in the allowed set. I
deliberately did **not** develop: stealth aircraft shape design as a product (idea A1, flagged and
dropped, both on PO-validity and on defense-access grounds), ship topside signature (naval defense),
chaff/decoy design (munitions-adjacent). None of the surviving top-four ideas has "harm to a human"
as its deliverable. The one idea that touches the human body (Idea D, mmWave scanning) is a sensing
application, which the brief explicitly places in scope.

## 8. What I could not check (no NEEDS_CONTEXT blocker, but flag these)

- The full text of Fang, Wu & Ye 2025 (IEEE returned HTTP 418). I confirmed title, venue, DOI, and
  abstract framing via the IEEE listing and R Discovery, but not their framework, their exact design
  variables, or whether they handle PTD. If patentability of any shape-optimization claim matters,
  Robin should pull this PDF. A Gemini Deep Research prompt worth running: *"Summarize IEEE JMMCT
  2025 DOI 10.1109/JMMCT.2025.3569766 (Fang, Wu, Ye, End-to-End Differentiable RCS Optimization on
  3D Geometry Based on Physical Optics): design variables, autodiff framework, whether edge
  diffraction/PTD is included, and what they claim as novel. Then list any 2023-2026 papers or
  patents on differentiable physical-optics RCS optimization with respect to surface material or
  impedance (not shape)."*
- FTO for any coating-impedance or certified-material-supremum patent claim. `could-not-check`.
- Whether the Fock gate gives a correct *back-scattered* shadow-boundary gradient (it is validated
  for the transmitted/absorbed field, not obviously for reflection). Testable in-house per brief 2.3.
