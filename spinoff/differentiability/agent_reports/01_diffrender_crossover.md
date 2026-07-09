# Differentiable rendering, transplanted to RF

Agent 01. Lens: computer-graphics differentiable rendering as the structural twin of AEGIS. Written
2026-07-09 against the code and the diff-render literature. Marks: `verified` (source cited),
`inferred` (reasoning shown), `could-not-check`.

## NEEDS_CONTEXT

None blocking. One thing I could not run here and it is load-bearing: the section 2.3 test
(gradient cosine similarity of PO vs an exact Mie/cylinder oracle near the shadow boundary). It needs
a compute run against `studies/diffraction/cylinder_oracle.py`. I flag it as the single experiment
that decides whether the moat claim in part 1 is real or cosmetic. If Robin wants it run, that is a
half-day in-house job, not a web task.

---

## Part 1: verify or destroy claim 2.2(b)

Short version: the framing is **correct**, the moat is **real but narrower than the brief states**,
and the exact wording matters. The Fock gate is a soft function of *local geometry* (normal plus
curvature), not of direction only, so it does smooth the vertex-position gradient. But it smooths
only the *self-shadow terminator of a smooth convex body*. It does not, in the autodiff path, give
correct silhouette gradients for general inter-part or non-convex occlusion. State it that way or a
reviewer kills it.

### 1a. Is "visibility discontinuity is the central obstruction" right?

Yes, verified. This is the defining problem statement of the whole subfield.

- Li, Aittala, Durand, Lehtinen, "Differentiable Monte Carlo Ray Tracing through Edge Sampling",
  ACM TOG 2018 (redner). The rendering integral contains a visibility term that is discontinuous in
  scene parameters. Naive autodiff of a Monte Carlo estimator samples the interior and **misses the
  Dirac-delta boundary term** that appears when the discontinuity location moves with the parameter.
  Their fix is to explicitly sample the silhouette edges to recover that term. `verified`
  (https://people.csail.mit.edu/tzumao/diffrt/, ACM TOG 37(6)).
- Loubet, Holzschuch, Jakob, "Reparameterizing Discontinuous Integrands for Differentiable
  Rendering", SIGGRAPH Asia 2019. Same problem, different fix: a change of variables so the
  discontinuity does not move w.r.t. the samples, letting ordinary autodiff capture everything
  unbiasedly. This is what Mitsuba 3 / Dr.Jit ships. `verified` (rgl.epfl.ch/publications/
  Loubet2019Reparameterizing).
- Liu, Li, Chen, Li, "Soft Rasterizer" (SoftRas), ICCV 2019. Replaces the hard binary visibility of
  a triangle with a **sigmoid of signed distance to the edge**, width `sigma` a free
  hyperparameter. Removes the discontinuity by softening the forward model itself. `verified`
  (arXiv 1904.01786).

So the three canonical strategies are: sample the boundary term (edge sampling), reparameterize it
away (Loubet / Mitsuba 3), or soften the forward model with a heuristic kernel (SoftRas). AEGIS is a
member of the third family. That placement is exactly right and it is the useful frame.

### 1b. Do Sionna RT and DiffeRT actually have the problem, or have they solved it?

This is the part the brief asked to check hardest, and the answer is clean.

- **Sionna RT (NVIDIA) has the problem and does not solve it.** From the Sionna RT paper and its
  own docs: gradients flow w.r.t. material properties, antenna patterns, array geometry, and
  transmitter/receiver positions and orientations, but *"discontinuities such as a change of
  visibility are not considered, i.e., paths cannot appear or disappear."* So a Sionna RT gradient
  w.r.t. object shape or position is either zero or biased exactly at the silhouette, because a path
  blinking in or out is a step the autodiff never sees. `verified` (arXiv 2303.11103; NVlabs/sionna
  discussion #602).
- **DiffeRT (Jerome Eertmans) solves it, but with a heuristic width, not physics.** Eertmans,
  Jacques, Oestges, "Fully Differentiable Ray Tracing via Discontinuity Smoothing for Radio Network
  Optimization", EuCAP 2024. They replace the non-continuous visibility with *"a smoothing function
  that can be exchanged with any function having similar properties, configurable via a parameter
  that determines how smooth the approximation should be."* That is a tunable sigmoid. It is the RF
  twin of SoftRas, and its width is a free knob with no physical meaning. `verified` (arXiv
  2401.11882; eertmans.be/posts/eucap2024).

This is the pivot for the whole moat claim. The competitor stack is split: Sionna leaves the
discontinuity unhandled (biased/zero shape gradients), DiffeRT handles it with a made-up width.
Neither uses the width Maxwell dictates. AEGIS does. That gap is genuine.

### 1c. The load-bearing question: soft function of geometry, or of direction only?

I read the code. It is a soft function of **local geometry**, not direction only. But "local" is the
word that scopes the moat.

The incoherent gate is `fock_local(mu, R, freq_hz, ...)` in `src/aegis/kernels/fock.py:436`, driven
by `xi = m*theta / w_nf`, `theta = arcsin(mu)`, `mu = n_hat . (-k_hat)`, and
`m = (pi f R / c)^(1/3)`. `verified` (read fock.py:436-468, level6_diffraction.py:51-67).

- `mu` depends on the surface normal `n_hat`, which is a function of vertex positions. So under a
  vertex perturbation the gate value changes smoothly. It is **not** direction-only. `verified`.
- The transition width depends on `R`, the in-incidence-plane curvature radius (`fock_radius`,
  `geometry/curvature`), which is also a function of geometry. So both the *location* and the
  *width* of the soft terminator move with the mesh. `verified` (fock_gate.py:36-52).
- The penumbra width is `(kR)^(-1/3)`, pinned to the exact PEC/impedance cylinder oracle, not a
  tuned hyperparameter. The terminator gate value `|fock_g(0,"hard")|^2 ~ 0.488` is calibrated to
  the Mie oracle, `_TERMINATOR_GATE_SQ_HARD = 0.488`. `verified` (fock.py:97-99, 347-364; docstring
  cites tests/test_fock.py and studies/diffraction).

So for the **self-shadow terminator of a smooth convex body** the claim holds fully. There the
silhouette *is* the locus `n_hat . (-k_hat) = 0`, the local normal already determines it, and the
Fock kernel supplies the physically correct soft transition. A hard PO integrator uses `ReLU(mu)`,
which is C0 (continuous but kinked) at `mu=0`; its vertex gradient is defined in the interior but
has a kink at the terminator and, integrated over the surface, misses the moving-boundary
correction. AEGIS's smooth kernel removes the kink and, because it is smooth, interior autodiff of
`P_abs = sum_t area_t f_t` is unbiased for the softened model with no separate boundary term needed.
`inferred` (from the SoftRas equivalence plus the code structure; the discrete triangle sum has no
moving intra-domain discontinuity once the gate is smooth).

**Where it stops.** Two honest limits, both from the code:

1. The local gate only knows the body's own curvature turning away from the source. Global
   occlusion, one body part shadowing another, is handled by a *separate* `distal_gate(clearance,
   R_occ, ...)`. Its curvature radius `R_occ` is **baked**: the docstring says *"R_occ is baked so
   the switch is constant in the pose gradient"* and *"v1 uses a hard switch on the baked R_occ"*.
   So the occluder-side width is frozen in the pose gradient. The gradient flows through the
   angular `clearance` but not through the occluder's shape. That is a partially-frozen soft
   visibility, weaker than the self-terminator case. `verified` (fock.py:501-566).
2. The single specular recapture is a ray-cast pass, excluded from the autodiff path (brief 2.1,
   `compute_sab` docstring). So the one genuinely global visibility test in the pipeline is not
   differentiated at all. `could-not-check` in code directly, taking the brief's statement.

### 1d. Verdict on 2.2(b)

**Survives, scoped.** The defensible sentence is:

> For the self-shadow silhouette of an electrically large smooth convex scatterer, AEGIS produces a
> soft-visibility field gate whose transition width and value are fixed by the Fock/Leontovich
> diffraction solution, not by a hyperparameter. This yields silhouette gradients that are
> physically calibrated where Sionna RT leaves them undefined and where DiffeRT and SoftRas use a
> tunable width with no physical anchor.

Do **not** claim general correct silhouette gradients. Inter-part occlusion is partially frozen and
the specular recapture is not differentiated. Overclaiming here is the fastest way to lose the point
in front of Eertmans or an NVIDIA reviewer, both of whom Robin may meet.

**The one thing that could still destroy it** is 2.3: even with the right *width*, is the PO
gradient *direction* right near the terminator? PO omits PTD edge diffraction and creeping-wave
value corrections precisely there. A correct soft width on a biased-direction model is a beautifully
smooth wrong answer. The Fock gate fixes the *shadow-boundary* physics that SoftRas fakes, which is
more than the competition has, but it does not make first-order PO into full-wave. The gradient
cosine-similarity test against the Mie oracle is mandatory before this becomes a patent sentence.
`inferred` + `could-not-check`.

---

## Part 2: mining the graphics field for transplantable ideas

For each money-or-career use of diff-rendering, the RF analogue on an electrically large smooth
object, and whether AEGIS enables it. Marked E (AEGIS enables today), N (needs the discarded
scattered-field half from brief 2.2a), X (does not fit).

1. Inverse rendering, recover shape from images -> recover object shape from measured scattered
   field (RCS/ISAR inversion, RF digital twin). **N** (needs the reflectance half).
2. SVBRDF / material capture -> recover per-triangle surface impedance / coating from backscatter.
   AEGIS already has per-triangle `n_tilde`; it is literally a material map. **N**.
3. Pose estimation from a photo -> human pose and position from mmWave scattering (RF sensing,
   presence, fall detection). Robin's own hint. **N** (forward is scattered field), partly **E**
   (dosimetry-style absorbed-power sensing).
4. NeRF / neural radiance fields -> "neural radio fields", learn a scene from sparse RF
   measurements, with AEGIS as the physics prior (NeRF2, WiNeRF exist). **N**.
5. Camera calibration -> antenna-array calibration, recover per-element phase/gain from a known
   target's scattering. Brief mechanism (b). **E/N**.
6. Adversarial texture design -> optimized coating or shaping to control a platform's radar
   signature (stealth shaping) or, inverted, to make road users *more* detectable to automotive
   radar. **N**. Ethics: platform signature management in scope, defeating a targeting classifier
   drifts out (brief 4).
7. Appearance / style transfer -> transfer a scattering signature to a decoy. Silly, listed anyway.
   **N**.
8. Gradient-based antialiasing / variance reduction -> smooth the Monte Carlo channel estimate.
   DiffeRT already owns this. **X** (commoditized).
9. Differentiable rasterizer as an ML data engine -> generate labelled synthetic RF datasets
   (channel, RCS, dose maps) with gradients, to train downstream nets. Sionna's whole business
   model. **E/N**.
10. Shape-from-shading -> shape from RCS angular signature (classical inverse scattering / ISAR).
    **N**.
11. Relighting without re-rendering -> predict the channel or dose for a *new* transmitter position
    from the differentiable model, without re-tracing. Network planning, exposure-map preview. **E**.
12. Face/avatar capture -> a privacy-preserving human digital twin driven by RF instead of cameras.
    **N**.
13. Differentiable SLAM / camera-pose tracking -> RF-SLAM, joint localization and mapping,
    differentiable. **N**.
14. Photogrammetry texture optimization -> weak, effective-surface-response fit for clothing/hair
    feeding the PO model. **E**.
15. Neural BRDF / learned material -> learn the effective EM surface response of complex fine
    structure (fabric, hair) as a differentiable layer on top of PO. **E**.
16. Differentiable lens/optics design -> the direct RF twin is differentiable **antenna, lens, and
    RIS design against a body/scene in the loop**. High-dim (RIS 10^3-10^4 phases). **E** (this one
    is squarely AEGIS's coherent path).
17. Uncertainty from the Jacobian -> exact sensitivity coefficients for a certification uncertainty
    budget. No graphics analogue at all, which is the tell that it might be the real business
    (part 3). **E**.

---

## Part 3: the hard question. Diff-rendering barely monetizes. Why would diff-RF?

Take it seriously, because the null answer is defensible and I nearly landed on it.

**The graphics precedent is bleak, and it is honest to say so.** Mitsuba 3 is academic. nvdiffrast
is a free NVIDIA research tool. redner is a paper repo. PyTorch3D is Meta open source. The field is
enormous and the *renderer* captures almost none of the value. Three reasons, and each has an RF
mirror worth checking:

1. In graphics the forward model is real-time. When the forward is cheap, a sweep or a learned
   surrogate competes with the gradient, so the gradient's marginal value is small. `verified`
   (this is why SoftRas-grade approximations are good enough for most ML pipelines).
2. The ground truth (photographs) is free and infinite, so inverse rendering mostly feeds a neural
   net, and the **net, not the renderer, is the product**. The gradient is plumbing.
3. There is no regulator anywhere demanding a differentiated image. Nobody certifies a render.

Now the RF mirrors, which is where the structural differences actually live:

**Difference 1, the alternative simulation is not cheap.** In RF the ground-truth forward model is
FDTD or MoM, which is FDTD-hours per configuration. AEGIS's founding observation is that the PO
surface operator is built in milliseconds. So the speed that graphics' real-time rasterizer erased
is *restored as economic value* in RF. Gradients on top of a 10^5-times-cheaper forward model are
worth something a fast rasterizer's gradients are not. `verified` (brief 2, Robin's JSAC quote).

**Difference 2, and this is the one that carries a business: regulation makes the gradient a
mandated, billable line item.** Graphics has no IEC. RF exposure certification does. IEC 62232
(base stations), IEC 63195 (mmWave device power density), and ISO/IEC GUM all *require* an
uncertainty budget built from sensitivity coefficients `c_i = dy/dx_i`. Today those are obtained by
finite differences (2N simulations at FDTD-hours each) or simply assumed. Autodiff produces the
exact `c_i` in one pass. This is the only place in this entire study where differentiability stops
being a nice property and becomes a thing a customer is *legally obligated to buy*. `verified`
(brief 3c; IEC 62232 / 63195 / GUM require sensitivity coefficients). There is no graphics analogue,
which is the point.

**Difference 3, dimensionality.** Graphics inverse problems are mostly low-dim per object (6-DoF
pose, a handful of materials) or absorbed into an NN prior. RF design vectors are genuinely large:
precoder `x` (M=256 complex = 512 real), RIS phases (10^3-10^4), per-triangle coating impedance
(10^4-10^5). Above ~10 parameters gradients beat sweeps and surrogates decisively. `verified`
(brief 3a).

**The sober counter, which must be stated.** NVIDIA is doing to differentiable RF exactly what it
did to differentiable rendering: giving Sionna away free to sell GPUs. "We have RF gradients" is
already being commoditized. And a brand-new entrant is in the inverse-rendering lane specifically:
"Physically Accurate Differentiable Inverse Rendering for Radio Frequency Digital Twin" (arXiv
2603.18026, 2026-03). `verified` (search result, title and date only, did not read the body).

**Conclusion.** Differentiability alone does **not** carry a business, same verdict as graphics. The
gradient is plumbing everywhere it competes with a cheap forward model or a free NVIDIA tool. What
carries a business is the one deliverable that (a) a regulator forces the customer to buy, (b)
requires differentiability essentially, and (c) sits on a vertical asset NVIDIA will not build: the
human body model, the IT'IS tissue database, the phantom library, and the mapping to IEC clauses.
Differentiability is essential to that deliverable and decorative to almost everything else. So the
answer to Robin's question is a qualified yes, and the qualifier is the whole company: **sell the
regulated deliverable, not the derivative.**

---

## Diverge: 17 raw ideas, one line each

1. Autodiff uncertainty budget (sensitivity coefficients `c_i`) as an IEC 62232/63195 compliance
   deliverable.
2. Certified supremum over the *pose/position* continuum via Lipschitz bound from the gradient
   (branch-and-bound certificate, the brief-section-5 patent move).
3. Differentiable RCS / signature engine from the discarded reflectance half (brief 2.2a).
4. Automotive-radar detectability optimization: shape a bumper/fascia so pedestrians and cyclists
   read *louder* to 77 GHz radar (safety, civilian, in scope).
5. Human pose-and-position estimation from mmWave scattering (RF sensing digital twin).
6. Antenna-array calibration from a known target's measured scattering.
7. Differentiable RIS / metasurface phase design with a body in the loop.
8. Neural-radio-field scene reconstruction with AEGIS as the physics prior.
9. Synthetic labelled RF dataset generator with gradients (Sionna-style, dosimetry vertical).
10. Relighting: predict dose/channel for a new transmitter placement without re-tracing.
11. Coating / radar-absorbing-material characterization from backscatter (material capture twin).
12. Inverse-design of a wearable (garment, headset) to reshape its own scattering/exposure.
13. Differentiable phantom fitting: recover a subject's body shape from a few dose or field probes.
14. Effective-surface-response learning for fabric/hair as a differentiable PO layer.
15. Gradient-based worst-case posture search for a fixed device (find the hand pose that maximizes
    local power density, for pre-compliance).
16. ISAR / shape-from-angular-signature inversion for non-cooperative objects.
17. Differentiable exposure-map preview in the viewer (already partly built) sold as a design tool.

---

## Converge: top ideas, graded on brief section 7

Grading axes: problem exists / Robin can fill it reliably / patentable / doable in 2y by 2 people /
market size / **differentiability essential or decorative** / named incumbent.

### Rank 1: certified sensitivity-coefficient uncertainty budget for EM-exposure compliance

(ideas 1 + 15, one product)

- Problem exists: **yes, verified.** IEC 62232 / 63195 / GUM legally require an uncertainty budget
  with sensitivity coefficients; today done by finite differences or assumed.
- Robin can fill it: **yes.** It is a software layer over the existing compliance flow, and AEGIS
  already emits the JAX arrays (`engine.compute_sab`) and FD-validated gradients w.r.t. position,
  frequency, precoder. `verified` (tests/test_jax_grad.py, test_fock_diffraction.py).
- Patentable: **partial.** The *use* of autodiff for sensitivity coefficients is not novel in
  general, but the specific mapping onto IEC clauses plus the body-coupled forward model may be a
  method claim. The stronger IP is Rank 2.
- Doable in 2y by 2 people: **yes.** No fab, no chamber, pure software plus a regulatory-mapping
  document.
- Market: **medium, real, recurring.** Every certified 5G/mmWave device and base station. Test
  houses (SGS, TÜV, Bureau Veritas) and their tool vendors are the buyers or channel.
- Differentiability: **essential.** The whole deliverable *is* the derivative. Finite differences
  are the incumbent method and cost 2N FDTD runs, so autodiff is a genuine 10-100x cost collapse,
  not a decoration. This is the cleanest "essential" in the study.
- Incumbent: **ZMT Sim4Life / SPEAG DASY, and in-house FD scripts at test houses.** Named.

### Rank 2: certified supremum over the configuration continuum (the patent)

(idea 2)

- Problem exists: **yes, inferred + verified.** Standards bodies test a handful of postures and
  hope. A guaranteed bound over *all* poses/positions is what a regulator actually needs and cannot
  get today. `verified` that prior art gives the supremum over the *excitation* continuum (VOP
  eigenvalue, brief section 5) but not over the *configuration* continuum.
- Robin can fill it: **plausible, with work.** Needs a Lipschitz constant from the gradient plus
  branch-and-bound. AEGIS has the gradient; the certificate machinery is new code. `inferred`.
- Patentable: **yes, this is the move.** Depends on differentiability *essentially* (no
  configuration-continuum certificate without a differentiable geometry-to-field map, which nobody
  else has). This is where the brief says the patent must go and I agree.
- Doable in 2y by 2 people: **borderline.** The math (Lipschitz bounds on a PO operator) is a real
  research risk. Tractable but not a sure thing.
- Market: **same buyers as Rank 1**, sold as the premium/defensible version.
- Differentiability: **essential and load-bearing.** Fails the whole idea without it.
- Incumbent: **nobody sells a configuration-continuum certificate.** The absence is the
  opportunity and the risk.

### Rank 3: differentiable RCS for automotive-radar detectability (the clean civilian dark horse)

(ideas 3 + 4)

- Problem exists: **yes.** 77 GHz automotive radar under-detects pedestrians and cyclists (low,
  variable RCS). Shaping and coating of vehicle surfaces and of vulnerable-road-user reflectors to
  raise and stabilize their radar return is a live safety problem.
- Robin can fill it: **needs the discarded half first.** The `G_tilde` operator gives the scattered
  far field by swapping transmittance for reflectance and evaluating the PO radiation integral to an
  observer (brief 2.2a). That is a real build, not a config flag, but it reuses the existing
  operator. `inferred`.
- Patentable: **maybe**, differentiable-shape-plus-coating co-design against a scattering objective
  for a smooth electrically large object. Crowded near Ansys.
- Doable in 2y by 2 people: **the forward is, verified adequacy of first-order PO for RCS is the
  risk.** PO is decent for specular RCS of smooth large objects, weak at edges (PTD), which is the
  same 2.3 worry.
- Market: **large**, automotive is bigger than dosimetry, and it is squarely "optimize w.r.t. an
  electrically large smoothish object" with a benign, in-scope objective (make road users more
  visible).
- Differentiability: **essential** for the high-dim shape+coating vector, decorative if you only
  tweak a handful of parameters.
- Incumbent: **Ansys HFSS SBR+ and Altair FEKO.** Named, well-funded, and not differentiable in the
  autodiff sense, which is the wedge.

### Rank 4 (hold, do not lead with): RF pose / human digital twin from mmWave

(ideas 5 + 8 + 12)

- Big market, Robin's own hint, but **the gradient is decorative here**: NN and NeRF-style methods
  dominate RF sensing, the body-model asset is the moat, not the derivative, and a fresh competitor
  is already in this exact lane (arXiv 2603.18026). Keep as an asset-leverage play, not the spine.
  `verified` competitor exists; `inferred` that gradient is decorative.

### What I would tell Robin in one line

Differentiability does not sell, the same way it never sold in graphics. The one exception is the
place graphics has no counterpart: a *regulator* that forces the customer to buy a derivative.
Rank 1 and 2 are that exception, and the Fock-gate moat from part 1 is what makes the derivative
trustworthy enough near silhouettes for a certificate to mean anything. Verify 2.3 before you put
the moat sentence in the patent.
