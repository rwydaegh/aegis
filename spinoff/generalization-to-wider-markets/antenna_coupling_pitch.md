# The concrete pitch for Tom: differentiable installed-antenna performance and co-site coupling

Companion to `generalization_map.md` (section 7) and `fable_review_verbatim.md`. This is the
one wedge, made concrete: what the object is, the anchor problem, the workflow it unlocks,
why it fits Tom specifically, a buildable proof-of-concept, and the honest boundaries.

## Why this one, and why for Tom

Both my pass and Fable's independently put **installed-antenna performance** at the top.
Fable added the sharpest facet: **co-site coupling**, the antenna-to-antenna `Q^(u,v)`
cross-term. Three things line up on it:

1. Market: existing, large, EDA-native (Altair FEKO and Ansys sell installed-antenna and
   co-site tools today), and less export-gated than stealth.
2. Closeness to what is built: it is the reflection operator `Q_re` from `q_complement.tex`
   with a receive aperture on the other end. The algebra exists; it needs coding and
   validation, not new theory.
3. Audience fit, the decisive one for this meeting: **coupling is S-parameters** (the
   off-diagonal `S_ij`). Tom Dhaene's field is surrogate/macromodels of S-parameters from
   expensive full-wave, out of Agilent/Keysight. This lands in his vocabulary on the first
   sentence.

## The technical object, concretely

"Installed-antenna performance" is two coupled questions on an electrically-large platform
(car roof, aircraft fuselage, satellite bus):

- **Installed pattern**: a single antenna's far-field is distorted because the platform
  reflects and diffracts its radiation. The platform-scattered field interferes with the
  direct field.
- **Co-site coupling**: multiple antennas on the same platform couple to each other. That
  coupling is the S-parameter `S_ij`, and it drives interference, desensitization, and EMC
  failures.

In the AEGIS operator language, with the platform as a metal (PEC or coated) surface mesh:

- Excite antenna `u` with port/element vector `x_u`. Its radiated field induces physical-
  optics currents on the lit platform surface, `J_s = 2 n_hat x H_inc` on the visible region
  (the ReLU-gated, ambient-occluded lit set, exactly the dosimetry visibility machinery).
- Those induced currents re-radiate. The re-radiated field, weighted by antenna `v`'s
  receive aperture, is the platform-mediated coupling `S_vu`.
- As an operator this is a bilinear form `S_vu ~ x_v^H Q^(vu) x_u`, where `Q^(vu)` is the
  platform-scattering cross-operator (built from the same `Q_re` reflection kernel, one leg
  carrying `u`'s field to the platform, the other carrying it back to `v`).
- The single-antenna installed gain toward a direction is the same construction with `v = u`
  and a far-field steering vector: `G_installed(dir) ~ x^H Q_gain(dir) x`.

Everything above is a differentiable function of the antenna positions `p_u`, their
orientations, and the platform shape. One backward pass gives `dS_ij/dp_k`. **That gradient
is the thing no full-wave or SBR tool hands you**, and it is the whole point.

## The anchor problem (lead with automotive, scale to aero/space)

Anchor on the **automotive roof antenna farm**. A modern shark-fin plus roof module packs
GNSS, 4G/5G MIMO, V2X, SDARS, and more into tens of centimeters. They couple, and their
patterns sit on a curved conductive roof that reshapes coverage. Today an engineer picks a
few candidate layouts, runs a full-wave or SBR solve per layout (minutes to hours each),
reads the S-matrix and patterns, nudges, repeats. It is a manual coarse grid search with no
gradient, so you cannot continuously optimize, and you certainly cannot jointly place 8
antennas against a coupling budget.

Higher-value cousins, same machinery: **blade antennas on an aircraft fuselage** (FEKO's
flagship demo) and **antenna placement on a satellite bus**. Automotive is the beachhead
because the volume is huge and the export/procurement friction is low.

## The workflow it unlocks

With a differentiable coupling matrix `S(p)`:

- **Gradient placement.** Descend antenna positions to minimize worst-case coupling
  `max_{i != j} |S_ij|` subject to each antenna's installed gain staying above threshold
  toward its required coverage cone. A real continuous optimization, not a grid search.
- **Joint N-antenna layout** under a single coupling/EMC budget, in one loop.
- **Worst-case-robust design in closed form.** The coupling operator's top eigenpair gives
  the worst coupling mode, and the operator shape-derivative `d lambda_1 = v_1^H (dQ/dp) v_1`
  gives its placement gradient directly. This is the "differentiable functional
  characteristic modes" handle, made concrete: the modes are tied to the coupling objective,
  and they move differentiably as you move the antenna.
- **Pre-screen for full-wave.** Explore thousands of layouts in AEGIS, pass the best handful
  to FEKO/HFSS to certify. Surrogate-assisted optimization, which is Tom's paradigm.

## The framing that is built for Tom

Pitch AEGIS here as a **physics-based analytical surrogate for the platform-scattered part
of the S-parameters**. Versus a data-driven surrogate (his bread and butter), it has two
properties his community wants and rarely gets cleanly:

1. It needs **zero training samples** for the geometry dependence. The physics is the model.
2. It hands you **exact gradients** for free, where a fitted surrogate gives approximate ones.

The collaboration writes itself, and it is exactly his research area (physics-informed +
data-driven hybrid surrogates):

> AEGIS provides the cheap, differentiable, analytical PO core. Tom's adaptive-sampling,
> macromodeling, and UQ machinery wraps it to (a) learn the *residual*, the surface-wave and
> near-field coupling that PO misses, from a small number of full-wave samples, and (b)
> steer sampling and quantify uncertainty where PO is least trustworthy.

Analytical base plus data-driven residual correction is a fundable, paper-shaped, and
Tom-shaped project. It is the honest version of the pitch too, because it names what PO
cannot do and gives his methods the job of fixing it.

## A proof-of-concept Robin can actually build

Bounded software task, crisp and Tom-legible:

1. Canonical geometry: two monopoles (or patches) on a finite ground plane, then on a
   cylinder (fuselage proxy) and a curved plate (roof proxy).
2. Implement the reflection operator `Q_re` and the platform-scattered coupling (the theory
   is in `q_complement.tex`; the body-side `Q_ab` is already coded, so this is the sibling).
3. Validate `S21(separation, position)` against FEKO/HFSS (or the analytic result for the
   ground-plane case).
4. Show the gradient `dS21/dp` and run a 2-antenna placement optimization that minimizes
   coupling while holding gain.
5. Headline: milliseconds and a gradient, versus full-wave's minutes-per-point and no
   gradient, validated to X% on the platform-scattered term.

This is also a clean IOF deliverable and the seed of a joint paper with Tom.

## Honest boundaries (say these before Tom asks, he is an expert)

- AEGIS computes the **platform-reflection-mediated** coupling and installed-pattern
  distortion. It **misses** direct near-field coupling between close antennas, surface and
  creeping waves along the platform (a real co-site contributor), and cavity effects. First-
  bounce PO (assumption A2) is the ceiling. So this is a fast differentiable **explorer and
  surrogate, not a certifier**. Full-wave still certifies the final candidates. That is a
  feature of the pitch (it feeds FEKO/HFSS, does not threaten them), not a weakness to hide.
- The scalar pseudo-Brewster `T0` trick does **not** apply here (metal, not tissue). You run
  full angle-dependent PEC/coated reflection. So the "million-x faster" dosimetry number does
  not carry. The honest speed claim is "milliseconds versus minutes for the PO-capturable
  part," and the real moat is **differentiability and the operator/QCQP inverse design**, not
  raw speed. Do not sell speed to a solver vendor (per Fable's Engine-A point).
- "Closed-form given the paths" is favorable here: a platform in free space has cheap first-
  bounce paths (direct visibility plus one reflection), so this is the good case, not the
  clutter case.

## The three-minute meeting version

1. AEGIS turns installed-antenna performance and co-site coupling into a **differentiable
   S-parameter surrogate**: you get `dS_ij/d(position)` in one pass, so antenna placement
   becomes gradient optimization instead of manual grid search.
2. It is a **physics-based** surrogate, so no training data for geometry and exact gradients,
   and it feeds FEKO/HFSS for final certification rather than replacing them.
3. It misses the surface-wave and near-field residual, which is exactly where **your**
   surrogate and UQ methods come in. Analytical core plus learned residual. Shall we scope a
   PoC on the two-antennas-on-a-cylinder benchmark and a joint paper?

The ask of Tom: is this framing credible to a Keysight/Ansys licensing conversation, and is
the analytical-core-plus-learned-residual collaboration one he wants to co-build for the IOF.

## Validated against how the industry actually works (and one overclaim corrected)

An independent research pass on the real automotive installed-antenna loop confirms the wound
and sharpens the claim. These points make the pitch precise and defensible.

**What the industry actually does**, and note it is the same architecture as the FMM syllabus
and the doorknob/scene-operator idea (rigorous element region, asymptotic body coupling):

1. element on a canonical/simplified ground plane (cheap full-wave), iterate freely there;
2. installed on the real CAD body via domain decomposition: full-wave near the antenna,
   coupled to the electrically-large body by equivalent sources through MLFMM or an asymptotic
   ray method (SBR, PO/UTD). Tools: FEKO (MoM+MLFMM+PO/UTD), HFSS+SBR+, CST/XFdtd;
3. co-site judged on S-parameters (isolation), ECC, total efficiency, receiver desense (Ansys
   EMIT Datalink builds the RFI model straight from the installed 3D model);
4. prototype and chamber (OTA, turntable cuts).

All three of our threads (this pitch, the FMM chapter, the doorknob idea) describe that one
architecture. They are a single technical bet, not three.

**The "change" step is largely expert-driven / gradient-free.** When automated it is
GA/PSO/Nelder-Mead/trust-region plus data-driven surrogates (Kriging/GP, Bayesian optimization
via optiSLang / DesignXplorer). Surrogates dominate the installed-car problem precisely because
you cannot afford hundreds of full-platform evals and there are no gradients. It is slow and
structurally painful: single sims run tens of minutes to hours, and objective evaluation is the
bottleneck.

**The gap is genuinely open, and its cause is exactly AEGIS's trick.** Full end-to-end
differentiability through the installed electrically-large problem is an open gap, not a
solved-but-unadopted one. The reason: the solvers that make the body tractable are asymptotic
(SBR/PO/MLFMM), and SBR in particular has no clean deployed differentiable path because
differentiating through discrete ray launching/bouncing and hard visibility is nasty. AEGIS's
core construction, a closed-form PO surface integral with smooth (GELU) visibility instead of
discrete ray launch and occlusion, is precisely the thing that makes the asymptotic body-
coupling leg differentiable. So the sharp claim is not "AEGIS is a differentiable EM solver"
(generic, and photonics autodiff already exists for small volumes). It is:

> AEGIS makes differentiable the exact leg the industry cannot differentiate, the asymptotic
> body coupling, by replacing ray launching with a smoothly-gated analytic surface integral.

**AEGIS sidesteps the differentiability wall, it does not hit it.** The wall people cite
(reverse-mode through full-wave time-stepping) is about autodiffing a huge volumetric FDTD:
field-history memory plus ray-launch discontinuity. AEGIS is neither a volumetric time-stepping
solve nor a discrete ray tracer, so it pays neither cost. It is differentiable by construction
at PO fidelity. The honest tradeoff is not "AEGIS also cannot differentiate the large problem";
it is "AEGIS can, but at PO fidelity, so it misses surface waves, near-field, and cavities."

**Overclaim to correct (was in the earlier draft above).** HFSS Optimetrics does give analytic
derivatives of S/Y/Z and far-field quantities with respect to design variables, so "full-wave
gives no gradient" is wrong. Two precise distinctions preserve the moat:

- They are FORWARD-mode (tangent) derivatives: cost scales with the NUMBER of parameters.
  AEGIS is REVERSE-mode: all gradients in a small multiple of one forward pass, independent of
  parameter count. So AEGIS wins decisively only in HIGH parameter dimension (many antennas,
  plus orientation, plus decoupling-structure shape, plus platform-shape co-design), not on a
  2-antenna 6-DOF toy where Optimetrics is already fine. Scope the pitch to high dimension.
- Those analytic derivatives live in the FULL-WAVE region. Through the asymptotic body coupling
  (the actual installed-car case) there is no deployed differentiable path. That leg is AEGIS's.

**Why this strengthens the Tom framing.** The industry already relies on data-driven surrogates
(GP/Kriging) for exactly this problem. GP surrogates need a DOE (dozens to hundreds of full-
platform evals to build), give only approximate gradients, and degrade badly above roughly
20-30 dimensions (curse of dimensionality). AEGIS is a physics-based differentiable surrogate:
zero DOE, exact gradients, scales to high dimension. So AEGIS beats the incumbent surrogate
method exactly where GP is weakest, which is precisely Tom's expertise. The collaboration is
cleaner than before: AEGIS analytical core, Tom's adaptive sampling / macromodeling / UQ for
the learned residual (the surface-wave and near-field part) and the confidence bounds.

**Orthogonal, not competing, with photonics autodiff.** rfx (2026, JAX FDTD) and the photonics
adjoint tools (Meep, ceviche, Tidy3D) differentiate small element-region volumes. AEGIS
differentiates the electrically-large body-coupling leg. Together they would be an end-to-end
differentiable installed-antenna pipeline. AEGIS occupies the part none of them touch.
