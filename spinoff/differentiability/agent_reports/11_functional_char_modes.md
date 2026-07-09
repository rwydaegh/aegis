# The operator as an EDA primitive: is "differentiable functional characteristic modes" real?

Agent 11. Lens: take Robin's coined phrase seriously and either build it into something real or kill it.
Written 2026-07-09 against `BRIEF.md`, `before-tom-meeting/`, and the patent files. Every claim tagged
`verified` (found the source), `inferred` (reasoned, reasoning shown), or `could-not-check`.

## NEEDS_CONTEXT

Nothing blocking. Two flags: (1) arxiv 2110.05312 and 2110.13460 would only return raw PDF binary to
`WebFetch`, so my reading of them is from the abstract/search summaries, not full text, marked
accordingly. If the IP decision leans on either, pull the PDFs. (2) I did not find a paper using the exact
phrase "differentiable characteristic modes" or "functional characteristic modes." That is a real negative
result from four targeted searches, but absence of a phrase is not absence of the idea, and the idea's
pieces are all published (below). Treat the negative as `could-not-check` for a hidden paper, `verified`
for "not a standard named object."

---

## Bottom line up front

**The phrase is mostly a rebrand, and as a phrase it is a liability, not a moat.** Decompose it:

- "**functional**" (a named quadratic power metric as a Hermitian operator, a whole family of them,
  optimized or bounded): **owned** by Capek, Jelinek, Gustafsson and co. at CTU Prague and Lund. Their
  "Fundamental Bounds to Time-Harmonic Quadratic Metrics in Electromagnetism" is exactly "any quadratic EM
  functional as `xᴴAx`, bounded by convex optimization," covering absorbed, scattered, stored energy, Q,
  efficiency. `verified` (Liska, Jelinek, Capek, arXiv 2110.05312, title and framing confirmed).
- "**characteristic modes**": owned by Harrington and Mautz (1971) and shipped in **FEKO, CST, and Ansys
  HFSS**. `verified` (Ansys ships a "Theory of Characteristic Mode Analysis" solver page; FEKO and CST CMA
  are well established). And critically, TCM modes live in a **different space** from AEGIS's `Q` modes (see
  Q1), so borrowing the name invites an expert to map your object onto theirs and then dismiss it.
- "**differentiable**": EM shape optimization by method-of-moments plus automatic differentiation is
  already a titled paper ("Electromagnetic Sensitivity Analysis and Shape Optimization Using Method of
  Moments and Automatic Differentiation", `verified` title via listing), and Capek's **topology
  sensitivity** gives cheap analytic shape gradients of MoM metrics, ~100x faster than pixel methods,
  "real-time" shape modification. `verified` (Capek, Jelinek, Gustafsson, "Shape Synthesis Based on Topology
  Sensitivity", IEEE TAP 67(6):3889, 2019).

So each of the three words maps to owned ground, and the union of "differentiable" + "quadratic functional"
+ "eigenmodes for antenna design" is essentially the CTU Prague research program, minus the branding.

**What genuinely survives is narrower and should not be called characteristic modes at all.** It is the one
intersection none of the incumbents occupy: a **task-defined excitation operator on an electrically large
external object, differentiated with respect to that object's geometry, at physical-optics cost.** TCM and
the CTU bounds machinery both need a full `N x N` MoM factorization and die on electrically large `N`; the
MIMO channel SVD and the MRI VOP never differentiate the scatterer; AEGIS is the only one of the four that
is simultaneously (i) in excitation space, (ii) task-defined, (iii) large-object PO-cheap, and (iv)
differentiable in the object geometry. That residue is real but small, and it is the same anchor the brief's
section 5 already found (certified supremum over the *configuration* continuum). **Recommendation: kill the
phrase, keep the residue, and do not let it become the headline of the patent.**

---

## Q1. Is "functional characteristic modes" a coherent novel idea, or a rebrand?

### The one distinction that matters: current space vs excitation space

This is the crux and it is worth being pedantic, because the pedantry is exactly what a KU Leuven or CTU
reviewer will apply in the first thirty seconds.

**Classical TCM** diagonalizes the MoM impedance operator of a *structure*: `X Jₙ = λₙ R Jₙ`, with `Z=R+jX`
of size `N x N`, `N` = number of RWG basis functions (10³ to 10⁵). The eigenvectors `Jₙ` are **current
distributions on the structure**, dimension `N`. They are **excitation-independent**: a property of the
metal alone, computed with no source. `verified` (multiple sources: "characteristic modes are independent
of any excitation", "determined purely by the geometry and material of a structure"). Designers use them for
*insight*: which mode a chassis supports, where to put a feed to excite it.

**AEGIS's `Q = Σ_t area_t · G̃_tᴴ G̃_t`** is `M x M`, `M` = number of antenna elements (10 to 256). Its
eigenvectors are **excitation vectors** `x`, dimension `M`, ordered by how much of the chosen functional
they deposit on the object. They are the opposite of excitation-independent: they *are* the excitation
modes, and they depend on the object, the array, and the functional jointly.

These are not the same modes in a different notation. They live in different vector spaces (`N` current DOF
vs `M` port DOF), they answer different questions (what does the structure resonate at vs which feed weights
maximize my task), and they are computed by different operators (reaction/impedance of the structure vs Gram
of a task channel). `inferred`, high confidence, and it is standard once you write both eigenproblems down.

### So what *is* AEGIS's `Q` eigendecomposition, named honestly?

It is the **SVD / eigenmode decomposition of a channel operator**, weighted by a task. In three established
literatures it already has a name:

- MIMO: the eigenbeams / transmit eigenmodes of `HᴴH`. `verified` (standard, the water-filling
  eigenmode decomposition).
- MRI safety: the **Q-matrix / Virtual Observation Point** machinery, `λ_max` = worst-case SAR over all
  excitations. `verified` (brief section 5, Eichfelder & Gebhardt MRM 2011; ZMT Q-matrix toolbox).
- mmWave exposure: Xu et al. IEEE T-EMC 2018 published the eigenvalue certificate and the per-element
  SDP for exactly this operator on arrays near a body. `verified` (brief section 5).

So the excitation-space eigen-operator, given fixed geometry, is **not novel**. It is channel SVD wearing a
dosimetry hat. This kills candidate answer (i) from the brief ("the functional can be anything"): the CTU
group already treats an arbitrary quadratic functional as an operator and bounds it, and MIMO already treats
the channel Gram's eigenmodes as the design object. A *family of functionals from one surface channel* is a
nice packaging but it is not an invention: `Q_ab, Q_re, Q_in` are just three weightings of one `G̃`, and
"one operator, many quadratic metrics" is the literal thesis of Liska-Jelinek-Capek. `inferred` from their
abstract, `could-not-check` on whether they enumerate the same three power partitions.

### What is left after the prior art is subtracted

Candidate answer (ii) from the brief, differentiability w.r.t. the *object's geometry*, is the only one with
a pulse, and even it is heavily encircled:

- Shape/topology gradients of MoM antenna metrics: **published and fast**. Capek topology sensitivity (TAP
  2019) is a gradient-based shape synthesis, inversion-free, ~100x faster than pixeling, explicitly "used
  for gradient-based topology synthesis." `verified`. Density-based (SIMP-style) MoM topology optimization
  for Q-factor also exists. `verified` (title "Density-Based Topology Optimization in Method of Moments:
  Q-factor Minimization"). MoM + automatic differentiation for shape optimization is a titled paper.
  `verified` (title only).
- Differentiable PO w.r.t. shape for RCS: **published** (Fang, Wu, Ye, IEEE JMMCT 2025). `verified` (agent
  03).
- Eigenvalue derivatives of characteristic modes: **published**, w.r.t. frequency, with degeneracy handled
  (Lundgren & Gustafsson 2025, "Fundamental Limits of Characteristic Mode Slopes"). `verified`.

So "differentiate an eigenvalue of an EM operator w.r.t. a design parameter" is textbook plus several 2019-
2025 papers. The genuinely unoccupied cell is the **conjunction**: excitation-space + task-defined + on an
electrically large external scatterer where MoM cannot factorize + differentiable in that scatterer's
geometry. TCM/CTU are current-space and small-`N`. MIMO SVD and VOP never move the scatterer. Fang moves the
scatterer but for RCS in current-free PO with no task-operator eigenstructure and no excitation space. I
could not find the conjunction as one published object. `verified` for the four components existing
separately, `could-not-check` for a hidden paper doing the conjunction.

**Verdict on Q1.** "Functional characteristic modes" is a rebrand of the channel/VOP eigenmode dressed in
TCM's vocabulary. It is coherent as an *analogy* (both are eigendecompositions used for design) but it is not
a novel *object*, and the TCM half of the name is actively misleading because AEGIS's modes are not
structure modes. The defensible residue is one narrow conjunction, and it deserves its own honest name
("differentiable task-channel operator on large scatterers"), not TCM's borrowed prestige.

---

## Q2. Eigenvalue derivatives and degeneracy: how bad is it?

### The clean case

When `λ_max(Q(p))` is **simple** (multiplicity 1), it is analytic in `p` and

```
dλ_max/dp = v_maxᴴ (dQ/dp) v_max        (Hellmann-Feynman)
```

with `v_max` the unit top eigenvector. `verified` (standard perturbation theory; identical in form to
Gustafsson's mode-slope `λ′ = Iᴴ(X′ − λR′)I / IᴴRI`, and to Robin's own note `dλ₁ = v₁ᴴ dQ v₁`). This is
cheap and exact and needs no autodiff at all: given `dQ/dp` you read the gradient off in closed form. That is
worth flagging, because it means *for the eigen-operator itself differentiability is decorative*, you get the
gradient from Hellmann-Feynman whether or not the graph is autodiff.

### The degenerate case, and why antenna designers live in it

When `λ_max` has multiplicity `m > 1`, it is **not differentiable**. It is still directionally
differentiable: the derivative in direction `δp` is `λ_max` of the `m x m` matrix `[v_iᴴ (∂Q·δp) v_j]`,
a max-of-quadratics, which is convex but nonsmooth. The correct object is the **Clarke subdifferential**,
which for `λ_max` of a symmetric matrix is

```
∂λ_max = { V S Vᴴ : S ⪰ 0, tr S = 1 }
```

`V` spanning the top eigenspace. `inferred` from the standard nonsmooth-eigenvalue-optimization results
(Overton, Lewis; this is the textbook subdifferential of the max eigenvalue). Degeneracy is **common exactly
where antenna designers work**, because symmetric structures (dipoles, patches, symmetric chassis) force
paired modes, and Gustafsson's slope paper confirms it: "degeneracies arise due to geometrical symmetries...
treated by decomposing the CM formulation into orthogonal subspaces free from degenerate modes." `verified`.
Naive gradient ascent on `λ_max` through a crossing will chatter or stall, and the eigenvector "flips"
between branches, which is the mode-tracking pain the TCM community writes whole papers about. `verified`
(mode tracking, "sharp peaks in eigenvalue traces are particularly challenging").

### How bad for AEGIS specifically: less bad than for TCM, and there is a clean fix

Two facts make this a "respect it, do not fear it" problem rather than a wall.

1. **AEGIS's `Q` is data-driven, so exact degeneracy is measure-zero.** TCM degeneracy is *exact* because it
   comes from the exact geometric symmetry of an idealized PEC. AEGIS's `Q` is a floating-point PO channel
   Gram on a real mesh with a real array; exact eigenvalue coincidence has probability zero. What you
   actually hit is **near-degeneracy** (clustered eigenvalues), where `λ_max` is technically differentiable
   but the gradient is ill-conditioned and the top eigenvector rotates fast. So the practical failure mode
   is ill-conditioning, not nondifferentiability. `inferred`, high confidence.

2. **The fix is already in the repo.** Replace the hard `λ_max` objective with a **spectral softmax**:

   ```
   J_β(Q) = (1/β) log Σ_i exp(β λ_i) = (1/β) log tr exp(β Q)
   ```

   which is smooth everywhere (even through crossings), lower-bounds and converges to `λ_max` as `β→∞`, and
   has gradient `Σ_i softmax_β(λ_i) · v_iᴴ (dQ/dp) v_i`, a softmax-weighted Hellmann-Feynman that averages
   over a near-degenerate cluster instead of picking a fighting branch. `inferred`, standard. This is the
   *same* LogSumExp trick AEGIS already uses to soften the peak `S_ab` in `src/aegis/optim/mimo_peak.py`
   (brief section 2.1, `verified`). Applied to the spectrum rather than the surface, it dissolves the
   degeneracy problem for optimization. `inferred`.

**Verdict on Q2.** Degeneracy genuinely breaks *naive* `λ_max` gradients and it is common in the symmetric
regime designers care about, so anyone claiming "just differentiate the top mode" is wrong. But it does not
break *mode engineering*: the honest object near a crossing is the Clarke subdifferential / max-of-quadratics
(solve a tiny `m x m` SDP for the steepest direction), and the practical object is the trace-exp spectral
softmax, which is smooth and which AEGIS already ships in a different guise. Net: a real caveat, a known and
mild one, and mildly *in AEGIS's favor* versus TCM because its degeneracies are approximate rather than
exact. This is a good story to tell Tom, because it shows physical + numerical maturity rather than naivety.

---

## Q3. The EDA pitch and the IP go/no-go

### Does differentiability carry the EDA pitch? Mostly no, and here is the specific reason.

The pitch "we bring differentiability to characteristic-mode / quadratic-functional design" collides head-on
with the CTU Prague program, which already has (a) the quadratic-functional-as-operator calculus, (b) convex
*bounds* on those functionals, (c) **analytic shape/topology sensitivities** that are inversion-free and
~100x faster than the pixel methods, and (d) memetic/gradient inverse design built on top. `verified` (three
CTU papers above). Against that group, "we have autodiff gradients of the operator" is not a moat: they get
shape gradients of MoM metrics analytically and fast, and they publish the fundamental *limits* AEGIS cannot
even compute (AEGIS optimizes a *given* feasible array; it does not bound what *any* current could do). So on
the antenna-modes turf, AEGIS is *behind* the academic frontier, not ahead of it.

Differentiability carries the pitch **only** where the CTU/TCM machinery structurally cannot follow, which is
exactly the residue from Q1: **electrically large external scatterers where the MoM factorization is
infeasible.** That is AEGIS's home (PO surface channel, `M x M`, milliseconds). There, "differentiable
task-operator eigenmodes on a large object" has no incumbent because the incumbent's method does not run.
`inferred`, high confidence. But note this is a *market* statement (large-object regime), not a *method
novelty* statement, and it is exactly the installed-antenna / co-site / radome / RCS-explore territory that
agents 03 and the feasibility synthesis already graded CONDITIONAL, gated by the explore-not-certify wall.

### The IP go/no-go, specifically, for Alessandro

Robin's own IP tension is correct and this study sharpens it. Let me state the broadest claim that survives
prior art, and the ones that do not.

**Does NOT survive (do not anchor the independent claim here):**

- "Quadratic power functional of an EM structure as a Hermitian operator, optimized/bounded" -> anticipated
  by Liska/Jelinek/Capek quadratic-metrics bounds. `verified` framing.
- "Eigendecomposition of the exposure/channel operator, `λ_max` = worst-case over excitations" -> Xu 2018,
  VOP/Eichfelder 2011, Siemens US8,547,097B2. `verified` (brief section 5).
- "Differentiable characteristic modes" / "differentiable EM shape optimization" -> Capek topology
  sensitivity, density-based MoM topology opt, MoM+AD shape opt, Fang 2025 PO-RCS. `verified` titles.
- "Functional characteristic modes" as a named eigen-object -> even if the exact phrase is unpublished, it
  reads as an obvious combination of TCM + quadratic-metric-operators, which is an obviousness problem, not
  just a novelty one. `inferred`.

**The broadest claim I believe still novel over TCM + VOP + Xu 2018 + MIMO-eigenmode + CTU-bounds:**

> A computer-implemented method that computes, for an electrically large external scatterer represented as a
> surface mesh and a set of `M` coherent sources, a task-weighted Hermitian excitation operator `Q` from a
> first-order local-interaction surface field channel **without a volumetric or full method-of-moments
> factorization of the scatterer**, and that produces an **exact gradient of a spectral functional of `Q`
> (its extremal eigenvalue, or a smooth spectral surrogate thereof) with respect to the scatterer's geometry
> and/or the source configuration**, and uses that gradient to certify a bound or drive an inverse design
> over the geometry/configuration continuum.

The three load-bearing limitations, each of which dodges a specific piece of prior art:

1. "**without a full MoM factorization** / at surface-PO cost on an electrically large object" — dodges TCM
   and CTU-bounds, which are `O(N³)` current-space and die on large `N`. This is the true novelty and it
   depends on differentiability *essentially* only when paired with limitation 3.
2. "**task-weighted excitation operator**, gradient w.r.t. the **external scatterer's geometry**" — dodges
   MIMO SVD and VOP, which never differentiate the scatterer, and dodges TCM, which is structure-intrinsic
   and excitation-free.
3. "**certify a bound / supremum over the geometry-or-configuration continuum**" — dodges Fang (point
   optimization, no certificate) and Xu (supremum over excitation only, fixed geometry). This is the brief's
   section-5 anchor (Lipschitz / branch-and-bound certificate over pose/position/shape) and it is the single
   place where differentiability is *essential and unowned*.

**Go/no-go recommendation: broaden, but do NOT broaden onto "functional characteristic modes."** Broaden
onto limitations 1+2+3 above, i.e. the large-object task-operator gradient and the *configuration-continuum
certificate*. Keep the tissue pseudo-Brewster dosimetry method as the strong, clean, separately defensible
embodiment underneath (it is the one thing with no prior-art cloud at all, per the memory and the feasibility
synthesis). Explicitly instruct Alessandro that the FTO search must now cover: characteristic-mode analysis
(Harrington, and the FEKO/CST/Ansys CMA solvers), the CTU/Lund quadratic-metrics and topology-sensitivity
portfolio (Capek, Jelinek, Gustafsson), differentiable rendering / differentiable ray tracing (Mitsuba,
Sionna RT), and MIMO eigenmode / VOP exposure IP. That is a materially bigger and more expensive search than
the dosimetry-only portfolio, and it is the real cost to weigh. `inferred`, but I am confident the four
clusters above are the exact FTO surface.

One sharper warning for the room: if the independent claim recites anything that reads onto "eigenvector of a
Gram of a channel" without the large-object-no-MoM and configuration-certificate limitations, it is
anticipated on its face by VOP + MIMO. The novelty is not the eigen-operator. It is that the eigen-operator
is cheap on a big object *and* differentiable through the big object's geometry *and* used to certify over a
continuum. All three, or it collapses back into prior art.

---

## Q4. Divergence: 20 things a differentiable, task-defined surface eigen-operator on large objects enables

Unfiltered, one line each. `S` = scattering-Gram (RCS/coating customer), `A` = antenna/coupling customer,
`X` = exposure/sensing customer. Grades come in Q5/table.

1. `A` Antenna placement on a platform by eigenvalue gradient: descend `dλ_max(Q_in)/d(position)` to seat a
   feed where the platform delivers the most captured power. (Robin's seed.)
2. `A` Feed synthesis to excite a chosen scattering/coupling mode: project a target mode onto the excitation
   eigenbasis and solve the QCQP for the weights.
3. `S` **Coating saliency map**: the top eigenvector of the scattering Gram tells you which surface patches
   dominate the return, i.e. a differentiable "put absorber here" heat map on a fixed shape. (Robin's seed,
   and the best of the divergence: it uses PO in its valid regime and is genuinely interpretable.)
4. `X` Worst-case-illumination analysis: `λ_max` over incidence direction + polarization + array weights, a
   certified worst-case over the illumination continuum for a fixed structure.
5. `A/S` RIS / reflectarray phase design: the scattering-Gram eigenmode is the aperture excitation that
   maximizes scattered power toward a target under a per-element constraint (the feasibility synthesis'
   top PURSUE, reuses `ecbf.py`).
6. `A` MIMO capacity bound on a body/platform-mediated channel: `Σ log(1+λ_i)` over the task-channel
   spectrum, differentiable in geometry, for co-design of array and platform.
7. `S` Fundamental bound on absorbed/scattered power for a given object shape, Gustafsson-style but in the
   large-object PO regime the CTU MoM bounds cannot reach.
8. `A/S` Mode-based model-order reduction: keep the top-`k` eigenmodes of `Q` as a rank-`k` surrogate of the
   object's coupling, turning a 10⁵-triangle object into a `k`-mode block for a fast outer loop.
9. `A/S` The eigenmodes as an interpretable basis for a neural surrogate: train the net in the `Q`-eigenbasis
   so its latent coordinates are physical power modes, not opaque features.
10. `X/S` Manufacturing-tolerance sensitivity of the mode structure: `∂λ_i/∂(geometry noise)`, a differentiable
    robustness budget (this is mechanism (c) in the brief, the mandated sensitivity coefficients).
11. `A` **Degenerate-mode splitting as a design objective**: maximize or minimize `λ₁-λ₂` by shape gradient
    to engineer or destroy a paired mode, e.g. tune circular-polarization mode balance or deliberately break
    a symmetry. (This turns the Q2 "problem" into a feature: you differentiate the *gap*, which is smooth
    even when each eigenvalue is not.)
12. `A` Co-site coupling matrix `Q^(u,v)` as a differentiable object: place two antennas on a platform to
    minimize the largest coupling eigenvalue between them.
13. `X` Compliance certificate over the pose/position continuum: Lipschitz + branch-and-bound on `λ_max(Q_ab)`
    over all human postures, the brief's section-5 anchor and the strongest essential-differentiability idea.
14. `X` Inverse illumination design: gradient-fit the source configuration so a measured surface field
    matches a target (calibration of a body-scanner illuminator).
15. `S` Shape-from-scattering: the direction-resolved capture spectrum is the object's brightness function,
    convex-hull recoverable (Aleksandrov), and its coherent lift is differentiable (memory's latent IP spine).
16. `X` Sub-region operator: `Q` restricted to a triangle patch (an organ, a rib, a target zone) gives a
    differentiable "power here, not there" objective, the HIFU/hyperthermia sparing problem verbatim.
17. `A/X` Wireless power transfer co-design: two operators (`Q_in` on the rectenna, `Q_ab` on bystanders),
    joint eigen/QCQP, differentiable in device placement.
18. `S` Radar-transparent structure (radome/emblem) design via the *transmission* eigenmode: minimize the
    boresight-distorting mode of the transmitted-field Gram (uses the half AEGIS already ships, agent 03's
    sleeper).
19. `A/S` Differentiable eigenvalue-crossing avoidance: use the spectral-softmax objective to route a design
    trajectory smoothly through mode crossings that trap TCM mode-trackers.
20. `X` Reciprocal self-calibrating compliance array: the Kirchhoff dual makes `Q_ab` a receive operator, so
    an array can estimate its own low-rank `Q` from body backscatter with no phantom (memory's hardware-IP idea).

---

## Q5. Reality check: would anyone pay for a better TCM?

**Honest answer: TCM is a beloved academic technique with real but shallow industrial adoption, and the
antenna-mode customer is the wrong target. The scattering/coating customer is better, and even that is not
great.**

- **Incumbents (named).** CMA ships in **Altair FEKO**, **Dassault CST Studio Suite**, and **Ansys HFSS**
  (the last has a "Theory of Characteristic Mode Analysis" solver page). `verified` for Ansys and FEKO,
  `inferred`/well-known for CST. So a "better TCM" competes with three flagship EM suites that already give
  it away as a feature inside a full solver.
- **Adoption reality.** TCM "grew from a niche topic to a mainstream topic" academically, but multiple
  sources concede "the gap between theoretical understanding and practical industrial implementation remains
  a challenge," and bounds "do not confirm whether a realizable antenna design can attain" them. `verified`.
  My read (`inferred`): designers use TCM for *intuition* (where to feed a chassis, which mode gives which
  pattern) far more than as an optimization engine, precisely because it is hard to interpret, mode-tracking
  is fiddly, and the modes are excitation-blind so the last-mile feed design is still manual. That is a
  "loved for insight, rarely in the critical path" technique. Nobody is writing a purchase order for "TCM,
  but differentiable." The people advancing it (CTU, Lund) are academics publishing bounds, not a market.
- **The frontier is already ahead of AEGIS on this turf.** The CTU/Lund groups publish fundamental *limits*
  (what any current can do) with analytic shape sensitivities. AEGIS optimizes a *given feasible* array and
  cannot compute those limits. So "differentiable functional characteristic modes" walks into a room where
  the domain experts are strictly ahead on the antenna-mode problem. Do not lead there. This is also exactly
  the room (Vandenbosch at KU Leuven, one hour away) where the phrase would first be judged, which makes the
  branding risk concrete rather than hypothetical. `inferred`.
- **Scattering modes are the better target, with a caveat.** The scattering-Gram top eigenvector as a
  **differentiable coating-saliency map on a fixed large smooth object** (idea 3) is the one genuinely
  attractive thing in this lens: it uses PO in its valid regime (fixed silhouette, specular return), it is
  interpretable (a heat map of which patches matter), differentiability is essential (10⁴-10⁵ patch impedance
  field), and TCM/CTU cannot compute it on a large object. But agent 03 already showed the accessible
  civilian slices (radome/emblem, wind-turbine RAM) are often solved at low zone count where gradients are
  decorative, and the high-dimensional pure version is stealth-coating, which is defense and closed to Robin.
  So the better customer is still a thin or gated one. `verified` (agent 03's grading), consistent here.

---

## Grading (brief section 7 criteria)

| Idea | Problem exists | Robin can fill | Patentable over TCM+VOP+Xu+MIMO+CTU | Doable 2y/2p | Market / incumbent | Differentiability |
|---|---|---|---|---|---|---|
| "Diff. functional characteristic modes" as a **product/brand** | Weak (TCM insight, not a purchase) | No, CTU is ahead | No (rebrand, obviousness) | n/a | FEKO/CST/HFSS give CMA free | Decorative (Hellmann-Feynman gives the gradient without autodiff) |
| **Configuration-continuum certificate** (`λ_max(Q_ab)` over pose/position, large object) | Yes (standards test a few postures) | Yes (owns the large-object PO channel) | **Yes**, narrow (limitations 1+2+3) | Certificate is hard but scoped | Regulators / test labs; no incumbent does over-continuum | **Essential** |
| **Coating-saliency scattering eigenmode** (idea 3) | Yes but thin/gated | Yes (engine exists, discarded half) | Maybe, crowded (Fang 2025 nearby) | Yes (weeks-months, agent 03) | RCS/coating; defense-gated at high-dim | Essential at high-dim, decorative at low zone count |
| **Degenerate-mode-splitting / spectral-softmax design** (ideas 11,19) | Niche | Yes | Unclear | Yes | Antenna designers; small | Essential (it is the gradient method through crossings) |

---

## Direct answers to the four questions, condensed

1. **Real or rebrand?** Rebrand, and a risky one. The functional-operator calculus is CTU's, the eigen-modes
   are channel-SVD/VOP, the differentiable-shape part is Capek topology sensitivity + Fang PO. The residue is
   one narrow conjunction (task operator, large object, no MoM, differentiable in geometry, certify over a
   continuum) that deserves its own name, not TCM's. `verified` prior art, `inferred` residue.

2. **Eigenvalue derivatives / degeneracy.** Simple: Hellmann-Feynman, exact, cheap, and differentiability is
   *decorative* because you get the gradient in closed form. Degenerate: nonsmooth, Clarke subdifferential
   `{VSVᴴ: S⪰0, trS=1}`, common in the symmetric regime designers use. Not fatal: AEGIS's data-driven `Q`
   degenerates only approximately (ill-conditioning, not nondifferentiability), and the trace-exp spectral
   softmax (already in the repo for peak `S_ab`) is smooth through crossings. Mildly in AEGIS's favor vs TCM.

3. **IP go/no-go.** Broaden, but not onto "functional characteristic modes." Anchor on: large-object
   task-operator gradient at PO cost + configuration-continuum certificate + keep tissue dosimetry as the
   clean embodiment. The broadest surviving claim and its three load-bearing limitations are spelled out in
   Q3. Tell Alessandro the FTO search now covers CMA (FEKO/CST/HFSS), CTU/Lund quadratic-metrics + topology
   sensitivity, differentiable rendering/RT, and VOP/MIMO exposure IP, a materially larger search.

4. **Diverge.** 20 in Q4. The three worth keeping: configuration-continuum certificate (13), coating-saliency
   scattering eigenmode (3), degenerate-mode splitting via spectral softmax (11/19).

5. **Reality check.** TCM is loved-for-insight, thin in the critical path, and given away inside three
   flagship suites; the frontier group (CTU/Lund) is ahead of AEGIS on antenna modes. The scattering/coating
   eigenmode is the better customer but is thin or defense-gated. Downgrade the antenna-mode framing; do not
   lead a Keysight/Ansys conversation with it.

## Where this lands relative to the study's converging thesis

This lens confirms rather than overturns the feasibility synthesis: the durable asset is the differentiable
closed-form *constrained-focusing* operator (`ecbf.py`) used to *design a controllable excitation*, and the
value is *essential*-differentiable only in the certificate-over-a-continuum use (brief section 5). Reframing
that same operator as "characteristic modes" adds a misleading label and a bigger FTO bill without adding a
defensible object. **Kill the phrase. Keep the certificate.**
