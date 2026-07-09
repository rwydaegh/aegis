# 02 competitive moat: is "we are the differentiable EM engine" true?

Lens: honest head-to-head against everyone who already ships differentiable electromagnetics. This is
the report that can kill the study, so the default posture is adversarial. Bottom line up front, then
the divergent list, then the evidence, then the three ordered answers, then the grades.

## NEEDS_CONTEXT

Nothing blocked me hard. Two soft gaps, flagged inline and not silently downgraded:

- The Sionna RT technical report PDF (arXiv:2504.21719) is 10 MB+ and truncated by the fetch tool. I
  read the HTML v2 and the abstract-level claims. A human should confirm one specific thing: whether
  Sionna 2.x exposes a per-primitive surface-current or absorbed-power tensor. I could not find it
  documented and I mark that as `could-not-check`, leaning "no public API for it."
- The ACES 2021 RCS-AD paper and the RFDT 2026 paper I read at abstract/metadata level only. Claims
  from them are marked `inferred` where I reasoned past the abstract.
- Reddit MCP not attempted (known 403 from last study). No community-opinion sourcing here.

## Bottom line

The sentence "we are the differentiable EM engine" is **false as written and defensible only after
three qualifiers are bolted on**. Differentiable EM is a fifteen-year-old commercial category (CST
adjoint S-parameter sensitivity, ~2011) and a crowded current research category (Sionna RT, DiffeRT,
RFDT, meep-adjoint, ceviche, MoM-with-AD for RCS). AEGIS is not the differentiable EM engine.

What is actually unoccupied, from everything I could find, is a narrower triple:
**per-triangle surface-field observable + electrically-large scatterer + millisecond analytic PO,
differentiated end to end.** Every shipping differentiable-EM tool differentiates either a
transceiver channel scalar (Sionna, DiffeRT, RFDT), a device S-parameter (CST, HFSS, FEKO), or a
wavelength-scale device field (meep, ceviche, Lumerical). None of them differentiates a *spatial
field distribution painted on the surface of an electrically large body*. That gap is real. It is a
**feature with a head start plus one genuinely defensible correctness claim (the Fock-smoothed
silhouette gradient)**, not a structural moat. A motivated NVIDIA could close the observable gap in
roughly one to two engineer-months. The thing that does not fall to NVIDIA in two months is the
*domain stack around* the gradient (tissue Fresnel/Cole-Cole `T0`, phantoms, ICNIRP mapping,
certified suprema), and that stack is not "differentiability." So differentiability is the mechanism,
not the moat.

## Diverge first: 18 candidate differentiators and gaps, one line each

Unranked, unfiltered, including weak ones.

1. Per-triangle **surface-field** observable vs everyone else's transceiver-channel observable. (strong)
2. Fock-transition **physically-derived** soft visibility vs Sionna/DiffeRT/RFDT **heuristic** smoothing. (strong, narrow)
3. Analytic first-order PO in milliseconds vs MoM/FEM/FDTD adjoint in minutes-to-hours. (speed, real)
4. Electrically-large scalability that MoM-AD (ACES 2021) and meep/ceviche structurally cannot reach. (real, but PO-only)
5. Closed-form eigen-operator `Q = J^T M J` and `λ_max(Q)` supremum over excitation continuum. (prior art exists, VOP)
6. Certified suprema over the **configuration** continuum (pose/position/orientation) via Lipschitz + branch-and-bound. (novel, unproven)
7. The discarded reflected half `1 - T0` reused for RCS / radar / sensing from the *same* `G_tilde`. (feature, not differentiator)
8. Mesh-native, no XML scene format, no port abstraction. (convenience, weak)
9. JAX caller-differentiates design (library has zero jax.grad, caller owns the graph). (architecture, matches DiffeRT)
10. End-to-end tx-position gradient through a trace, FD-validated at rtol 1e-3. (matches Sionna/DiffeRT)
11. Exact IEC/ISO-GUM sensitivity coefficients `c_i = dy/dx_i` in one pass. (billable, but CST already does this for S-params)
12. Human digital twin (SMPL-X pose to vertices) as the differentiable input surface. (domain asset, not gradient)
13. Tissue-layer physics (Cole-Cole, layered Fresnel `T0`) that no ray tracer carries. (domain asset)
14. ICNIRP/compliance observable mapping. (domain asset)
15. Gradient wrt per-triangle coating impedance at 10^4-10^5 dimension. (real high-dim, shared-able by SBR tools)
16. Gradient direction correctness near silhouettes (the 2.3 risk): a differentiator only if it survives testing. (unproven)
17. RIS element-phase gradients at 10^3-10^4 dimension. (DiffeRT and Sionna both target this already)
18. Inverse recovery of shape/material/pose from observed scattering. (RFDT 2026 already does the channel version)

Ranking after evidence: #1 and #2 are the only two that survive a head-to-head as things competitors
do not already ship. #3, #4, #6 are conditional. Everything else is either shared with an incumbent
or is a domain asset that is not "differentiability."

## The field, product by product

### NVIDIA Sionna RT `verified`

- Built on Mitsuba 3 / Dr.Jit, TensorFlow front for field transforms. Sources: arXiv:2303.11103
  (2023), technical report arXiv:2504.21719 (2025, v2 HTML read), `sionna-rt` on PyPI.
- Differentiates wrt: **radio materials, scattering coefficients, antenna patterns, array geometries,
  transmitter/receiver positions and orientations.** `verified` from both the 2023 abstract and the
  2025 report abstract, quoted nearly verbatim across NVIDIA's own pages.
- Geometry / vertex gradients: Mitsuba 3 supports differentiable geometry in the graphics domain, but
  the Sionna radio pipeline does **not** advertise vertex-position gradients as a supported observable,
  and the path-existence set is discontinuous in geometry (the classic silhouette problem). `inferred`:
  Sionna inherits the same biased/undefined silhouette-gradient issue that the differentiable-rendering
  field has fought for a decade. The report does not describe an unbiased edge-sampling estimator for it.
- Observable: **channel impulse response** `h(tau) = sum a_n delta(tau - tau_n)` between transceivers,
  plus **radio maps** which are received power bucketed onto a *measurement grid in the environment*,
  not surface power on a scattering body. `verified`.
- Per-triangle absorbed power out of Sionna: no documented output tensor. `could-not-check`, leaning no.
  It computes the field at each ray-surface interaction internally (it must, to propagate), so the
  *ingredients* exist. Getting per-triangle absorbed power is an aggregation-and-expose task, not a new
  physics task. This is the crux of answer (c).

### DiffeRT (Jerome Eertmans, JAX) `verified`

- Sources: DiffeRT docs (differt.eertmans.be), arXiv:2510.16172 (2025), DiffeRT2d JOSS, and crucially
  Eertmans, Jacques, Oestges, **"Fully Differentiable Ray Tracing via Discontinuity Smoothing for
  Radio Network Optimization," EuCAP 2024.**
- Differentiates wrt: **vertex positions and material properties**, plus tx/rx positions. `verified`
  (the 2025 paper fetch explicitly lists geometry/vertex positions). DiffeRT is actually *more* geometry
  differentiable than Sionna in this respect.
- Discontinuity handling: **explicit heuristic smoothing** of the visibility discontinuity. `verified`
  from the EuCAP 2024 title and the docs guide "Smoothing Discontinuities for Fully Differentiable Ray
  Tracing." This is a chosen smoothing kernel, not a Maxwell-derived transition. This is exactly the
  contrast the brief's 2.2b wants.
- Observable: **channel impulse response / path coefficients between transceivers.** Not per-triangle
  surface fields. `verified`.
- Physical model: geometric ray tracing with reflection/diffraction path mechanisms, not a PO surface
  integral. `inferred` (docs frame it as path-based, ML-path-sampling tutorials).
- Strategic note: Robin contributes to DiffeRT and Jerome is a warm contact. That is a collaboration
  asset and a competitive tell at once. DiffeRT is the closest architectural sibling (JAX,
  caller-differentiates, vertex gradients). The two things AEGIS has that DiffeRT does not are the
  surface-field observable and the physically-derived smoothing.

### Ansys Perceive EM `verified` for what it is, `inferred` for the negative

- GPU-accelerated **shooting-and-bouncing-rays** solver using geometric + physical optics, NVIDIA-
  accelerated, integrated with NVIDIA AODT and Omniverse for 6G. Claims up to 1e6x vs x86 CPU solvers.
  Sources: ansys.com Perceive EM product page and blogs (2024-2025), Supermicro solution brief.
- Differentiable? **No public differentiability claim anywhere I found.** `inferred` (absence of
  evidence, but a strong absence: none of Ansys's Perceive EM marketing, which is extensive, mentions
  gradients, adjoint, or inverse design for this product). It is a fast forward solver.
- Observable: coherent channel response over time/frequency/space. Not per-triangle absorbed surface
  power on a human body.
- This is the memory's stance too (project_ansys_perceive_em): incumbent 6G channel layer, complement
  not competitor. Confirmed: it is not a differentiable-EM competitor today, it is a fast-forward-SBR
  competitor. If Ansys ever makes Perceive EM differentiable, that is the real threat, and they have
  the SBR-PO forward model to hang it on.

### Commercial CEM adjoint: CST, HFSS, FEKO, XFdtd `verified` (category), `inferred` (limits)

- **CST Studio Suite** has shipped **adjoint / broadband sensitivity** since ~2011: derivatives of
  S-parameters wrt geometric and material parameters from a single broadband run, used for yield and
  optimization. Source: CST 2011 press release and Microwave Journal coverage. `verified`.
- **HFSS** exposes derivatives/optimetrics and gradient-based optimization. FEKO is MoM (surface
  integral equations). XFdtd is FDTD. `verified` category, `could-not-check` for a true shape-adjoint
  in each.
- The key limitation for our purposes: the observable is a **device/port S-parameter or far-field
  pattern**, and the electrical size is small-to-moderate (an antenna, a connector, a filter). These
  are not surface-field maps on an electrically large external body, and full-wave FEM/MoM does not
  scale to a whole human at mmWave without heroics. `inferred`.
- Consequence for the pitch: **"differentiable EM" is not new as a category.** It is old and shipping.
  The company must never claim the category. It can only claim a specific unoccupied cell of it.

### Photonics adjoint: meep, ceviche, Lumerical lumopt `verified`

- meep (MIT, FDTD + adjoint), ceviche (differentiable FDFD/FDTD, autograd), Lumerical lumopt
  (continuous adjoint). Mature, widely used for nanophotonic inverse design. Sources: meep docs,
  ceviche repo, Ansys/Lumerical lumopt docs. `verified`.
- Domain: wavelength-scale devices. FDTD/FDFD is structurally infeasible for an electrically-large
  human at 28-60 GHz. So this is the same "differentiable EM is old" point in a different subfield,
  and it does not reach AEGIS's regime. Not a direct competitor, but it demolishes any "first
  differentiable Maxwell" claim.

### Academic differentiable RCS / PO `verified` for what exists, `inferred` for the gap

- **Li, Bai, Qu, "Radar Cross Section Reduction and Shape Optimization using Adjoint Method and
  Automatic Differentiation," ACES Journal, 2021.** MoM with CFIE + automatic differentiation
  (tangent/adjoint modes) + free-form deformation, observable is far-field RCS, target is a flying-wing
  aircraft. `verified`. This is the closest published prior art to "differentiable EM for shape
  optimization of an electrically large object." It is **full-wave MoM (accurate but slow, does not
  scale the way PO does) and its observable is far-field RCS, not a surface field.**
- **Chen, Zhang, Zheng, Fang, Li, Lu, Li, "Physically Accurate Differentiable Inverse Rendering for
  RF Digital Twin" (RFDT), arXiv:2603.18026, March 2026.** Differentiable inverse rendering for RF that
  explicitly tackles path-visibility discontinuity and specular reflection, for reconstructing digital
  twins from real RF measurements and for RF-sensing test-time adaptation. `verified` at abstract level.
  This is the newest and most dangerous neighbor: it is exactly "differentiable RF forward model,
  discontinuity-aware, inverse problems." Observable is the RF channel/measurement, not surface fields.
  `inferred` from abstract that it is transceiver-observable, not per-triangle-surface.
- Neural-network RCS surrogates trained with AD (FNO, physics-informed nets, "Physics-Informed
  Hierarchical Neural Network for Microwave Scattering of 3D PEC Targets," arXiv:2508.03774, 2025):
  these give gradients through a *learned surrogate*, not through the physics, so their gradient is only
  as trustworthy as the training set and they are not analytic. `verified` that they exist, `inferred`
  on the quality caveat.
- **Did anyone publish a differentiable analytic first-order PO surface operator on a triangle mesh
  with gradients wrt vertices AND a per-triangle surface-field output?** I could not find one.
  `could-not-check` in the strong sense (proving a negative), but the search was deliberate and came up
  empty: the PO-RCS work outputs far-field RCS, the MoM-AD work is full-wave, the ray-tracing work
  outputs channels. This absence is the strongest single piece of evidence for the moat, and it is an
  absence, so treat it as suggestive not proven.

## The three ordered answers

### (a) What AEGIS's gradient does that none of these do, as one testable sentence

> AEGIS returns exact gradients of a **per-triangle surface field / absorbed-power distribution on an
> electrically large scatterer**, computed by analytic first-order physical optics in milliseconds and
> differentiated by the caller, with the visibility discontinuity replaced by the Maxwell-derived Fock
> transition rather than a heuristic smoothing kernel.

Testable falsifier: name one shipping tool that emits gradients of a *per-primitive surface field* on
an electrically-large body. Sionna and DiffeRT and RFDT emit gradients of a channel scalar. CST/HFSS/
FEKO emit gradients of an S-parameter or far-field pattern. meep/ceviche/Lumerical emit gradients of a
device field but cannot reach electrical largeness. MoM-AD (Li 2021) emits gradients of far-field RCS.
If someone finds a counterexample, the sentence is dead. I could not find one.

### (b) Moat, feature, or rounding error?

**Feature with a head start, plus one narrow real moat.** Broken out:

- The **surface-field observable** (#1): a real, currently-unoccupied capability, but it is an
  *engineering* difference, not a physics moat. Every ray tracer already computes the field at each
  surface interaction; exposing and aggregating it per triangle is plumbing. So it is a feature and a
  head start, and it is exactly what answer (c) says NVIDIA could copy. Grade: **feature.**
- The **Fock physically-derived soft visibility** (#2, brief 2.2b): this is the single most defensible
  technical statement in the company. DiffeRT and RFDT *explicitly* use heuristic smoothing; Sionna's
  radio path solver has biased/undefined silhouette gradients. AEGIS uses the transition function
  Maxwell actually produces at a shadow boundary. **If** the gradient-correctness holds up (2.3), this
  is a genuine, paper-worthy, plausibly patentable moat, because it is a *correctness* claim, not a
  *feature* claim, and correctness is the one thing a fast copy cannot fake. Grade: **narrow moat,
  conditional on 2.3.**
- The **half-engine / RCS reuse** (#7, brief 2.2a): expands the addressable market (radar, sensing,
  signature) but does not defend it, because Sionna and Perceive EM already produce scattered fields and
  RCS. It is a market-expansion feature. Grade: **feature, not differentiator.**
- Everything about "we have gradients" in general: **rounding error.** CST has had adjoint S-parameter
  gradients since 2011. Claiming gradients as such is claiming a fifteen-year-old category.

### (c) If NVIDIA added per-triangle surface-power output to Sionna, how many engineer-weeks, and does that end the company?

Engineer-weeks: **roughly 4 to 8 for a competent Sionna/Mitsuba engineer** to expose a per-primitive
absorbed-power (and scattered-power) tensor as a differentiable output. `inferred`, reasoning:

- Sionna already computes the polarized field at every ray-surface interaction (required to propagate),
  and its radio-map solver already buckets power onto a grid. Re-bucketing incident field times
  `(1 - |Gamma|^2)` onto mesh primitives instead of onto a measurement grid is a variant of code that
  exists. The autodiff plumbing (Dr.Jit) already carries gradients through the field transforms.
- What NVIDIA would NOT get for free in those weeks: (i) the layered-tissue Fresnel `T0` and Cole-Cole
  dispersion that turns "reflected field" into "absorbed dose in skin," (ii) the human phantom + SMPL-X
  differentiable body pipeline, (iii) the ICNIRP/IEC compliance mapping and the certified-supremum
  operator `Q`, and (iv) the Fock-correct silhouette gradient. Those are domain assets and a correctness
  claim, not gradient plumbing.

Does it end the company? **It ends the "we are the differentiable EM engine" positioning, and it should
never have been the positioning.** It does not end a company whose defensible layer is the domain stack
(tissue physics + phantoms + compliance + certified suprema) and the one correctness claim (Fock
gradient). Read the other way: NVIDIA has no commercial reason to build human-dosimetry-grade tissue
physics and ICNIRP mapping, so the realistic threat is not "NVIDIA eats dosimetry," it is "NVIDIA makes
surface-power a checkbox and the *generic* surface-field differentiator evaporates, leaving only the
domain and correctness layers to defend on." The strategic instruction that falls out: **do not sell
the gradient, sell the certified dosimetry/compliance deliverable that the gradient makes possible, and
publish the Fock-gradient correctness result fast to plant a flag before RFDT-style heuristic-smoothing
work claims the silhouette-gradient space.**

## Grading the brief's structural claims as competitive differentiators

### 2.2a half-engine (keep `T0`, the discarded `1 - T0` is RCS) — **feature, not differentiator**

`verified` that `src/` has no scattering (confirmed the `scatter` = scatter-add einsum, e.g.
`exposure_operator.py` einsum `"m,mia,mib->ab"`; the operator is transmittance-only). The physics claim
that the same `G_tilde` yields the scattered far field by swapping `T0` for reflectance is sound
`inferred`. But competitively it is not a differentiator: Sionna, Perceive EM, and every SBR-PO/MoM tool
already produce scattered field and RCS. The half-engine widens AEGIS's *market* (into sensing/radar)
but does not *defend* it against anyone. Grade as a market-expansion feature, not a moat. Its real value
is optionality: one operator serves dosimetry and RCS, which matters for a two-person company choosing a
beachhead, not for defensibility.

### 2.2b Fock physically-derived soft rasterizer — **the moat claim, and it survives contact, conditionally**

This is the one claim in the whole competitive picture that is both true and hard to copy. The
competitive evidence is now concrete and in AEGIS's favor:

- DiffeRT: **heuristic** discontinuity smoothing (EuCAP 2024, explicit). `verified`.
- RFDT 2026: explicitly "resolves path-visibility discontinuities" as an engineered fix. `verified`
  at abstract level.
- Sionna RT: path solver with a discontinuous path-existence set, no documented unbiased silhouette
  estimator. `inferred`.
- Differentiable rendering generally (SoftRas, redner/Li et al.): heuristic softening or expensive edge
  sampling. `verified` as background (well-known in the field).
- AEGIS: the smoothing kernel is the Fock transition function, i.e. what the field physically does,
  validated in *value* against an exact cylinder (project_diffraction_fock memory,
  test_fock_diffraction.py). `verified` for value; **not** verified for gradient.

So the differentiator is: everyone smooths, AEGIS is the only one whose smoothing is derived from
Maxwell rather than chosen for convenience. That is a correctness moat if and only if 2.3 holds. Grade:
**strongest differentiator in the company, conditional on the 2.3 test.** Recommend Robin fund the 2.3
test before making this claim to an investor or a patent examiner, because the claim is worthless if the
gradient is wrong and priceless if it is right.

### 2.3 does grad(PO) approximate grad(truth)? — **respected, and it is the gate on 2.2b and on the whole patent move**

I take this as seriously as the brief demands. The critical, under-appreciated point:
**value-accuracy does not imply gradient-accuracy.** The Fock model was validated in value against the
exact cylinder. That says nothing about whether `d(PO)/d(radius, angle, frequency)` points the same way
as `d(Mie)/d(same)` near the shadow boundary, which is exactly where PO drops PTD edge diffraction,
creeping waves, and travelling waves, and exactly where a gradient-based optimizer will march because
the gradient is largest there. `inferred`, and it is a standard failure mode of asymptotic methods.

Consequences if the test fails (gradient cosine similarity poor near silhouettes):

- 2.2b collapses from a moat to a liability: AEGIS would be the tool that confidently produces a
  physically-motivated but *wrong-direction* shape gradient.
- The brief's proposed patent move (certified suprema over the configuration continuum via Lipschitz +
  branch-and-bound) is undermined at the root, because a certificate built on a wrong gradient field
  certifies the wrong thing.
- Several of the divergent-list items (#6, #16, #18-shape) die with it.

The test is cheap and in-house (compare grad(PO) vs grad(analytic Mie/cylinder) wrt radius, frequency,
incidence angle, report cosine similarity as a function of angular distance from the shadow boundary). I
recommend it be the **first** thing built in this study, before any positioning is committed, because it
is the single largest source of variance in whether the moat exists at all. Until it is run, treat every
gradient-correctness claim as `could-not-check`.

## One honest closing calibration

The company's real defensibility is not "we differentiate EM." It is the stack: layered-tissue
absorption physics + human phantoms + ICNIRP/IEC compliance mapping + a certified supremum, with
differentiability as the *mechanism* that makes the certified-supremum-over-configurations deliverable
possible. Differentiability is load-bearing (the config-continuum certificate needs it *essentially*,
per brief section 5), but it is the engine, not the fence. The fence is domain + certification + the
Fock-gradient correctness result. If the pitch is "differentiable EM engine," a knowledgeable investor
who has heard of CST adjoint, Sionna, and Perceive EM will correctly discount it. If the pitch is
"the only certified dosimetry/compliance engine whose sensitivity coefficients and worst-case bounds
come out exact and fast, over poses and positions no incumbent can sweep," that is both true and
defensible, and differentiability is why it is possible.
