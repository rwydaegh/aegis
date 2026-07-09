# Can differentiability carry a business? The synthesis

Orchestrator's consolidation of a thirteen-agent study, 2026-07-09. Reports in `agent_reports/`,
shared ground truth in `BRIEF.md`. This is my own read, not a staple of theirs. Where the evidence
made me disagree with an agent, or with myself, I say so.

Two agents ran at max reasoning effort and settled the study: report 10 measured the gradient against
exact solutions, and report 07 measured the certificate against the real body. Both returned results
that contradicted the brief I wrote for them. That is the most useful thing that happened here.

---

## The verdict, in one paragraph

Differentiability does not carry a business, and the reason is structural rather than fixable.
Gradients pay only when the design vector is high-dimensional, and AEGIS's one genuinely
high-dimensional knob, the precoder, has a closed-form eigenvector optimum that makes gradients
worthless there. The knobs where gradients would pay, per-triangle coating and object shape, sit in
the regime where first-order physical optics is least trustworthy, and report 10 measured exactly how
untrustworthy: values under-predicted by 3 to 16x near the terminator, incidence gradients 2 to 20x
too steep, and the size and frequency derivative of absorbed power sign-flipped at every frequency
tested, on both an exact cylinder and an exact Mie sphere. The value converges while the derivative
inverts. Meanwhile the certification pitch, which was my own contribution and which I believed was the
patent's escape route, was measured and found to tighten the smallest term in the error budget.
**One thing survives, and it is narrow, true, and nobody else can say it: the Fock shadow transition
is what makes a local Lipschitz certificate finite instead of infinite, so hard-visibility
differentiable ray tracers are wrong about the Lipschitz constant at silhouettes, and no tuning of a
heuristic smoothing width fixes it.** That is a correctness claim about competitors rather than a
feature claim about AEGIS, it is the only claim in this study that is simultaneously novel, testable,
and unreachable by Sionna RT or DiffeRT, and it is not yet enabled because the pose-to-vertex map is
severed from the autodiff graph.

---

## What I got wrong, first, so it is not re-inherited

**I claimed differentiability was unused in AEGIS.** I counted `jax.grad` calls inside `src/` and
found one. That is the wrong metric. A differentiable library has zero internal calls because the
caller differentiates, and `engine.py:753` (`compute_sab()`) exists precisely to be wrapped in
`jax.grad`, as its docstring says. `tests/test_jax_grad.py` proves finite-difference-validated
gradients through every level 0 to 6 with respect to power, with respect to the complex precoder, and
end to end with respect to antenna position. Robin corrected me and he was right.

**I claimed AEGIS is "half an engine" and the discarded reflected half is the generalization.** True,
but it is Robin's own finding, written down months ago as `Q_re` in
`spinoff/before-tom-meeting/generalization_map.md` section 2, Knob B, with the observation that
`Q_re` is literally a monostatic RCS operator sharing eigenvectors with `Q_ab`. I re-derived his
document and presented it as discovery. What is actually new is that report 03 verified `r_s` and
`r_p` are computed on the same line as `t_s` and `t_p` in `tissue/fresnel.py::_fresnel_core` and then
discarded, and priced the build at roughly one week for a monostatic toy and two months for a
validated bistatic engine with PTD.

**I claimed the Fock gate is a physically derived soft rasterizer giving unbiased silhouette
gradients.** Half false, verified in source by reports 01 and 10. `level6_diffraction.py:51` gates on
`mu = n_hat . (-k_hat)`, and normals depend on vertices, so the *self-shadow terminator* of a smooth
convex body genuinely is smooth in geometry. But inter-part occlusion is a hard numba BVH closest-hit
test, int8-quantized, baked, with `R_occ` constant in the pose gradient (`fock.py:565`), and
`compute_sab` never sees it at all. AEGIS has a smooth terminator and a hard inter-part shadow. And
report 10 measured a 12x magnitude bias even on the terminator it does cover, because the Fock gate
smooths the visibility ReLU while leaving the Fresnel grazing collapse `T(mu -> 0) -> 0` un-smoothed.
It fixes the wrong discontinuity.

**I proposed a unifying thesis: standards protect by sampling continua, and coherent agile systems
break sampling, so AEGIS's value is computing the supremum.** Report 07 measured it on the real
20908-triangle SMPL-X body with a coherent 4x4 array at 28 GHz. The true worst case over a fine
orientation grid exceeds the max over four canonical orientations by **0.9 percent in total power and
3.8 percent in local density**, and adding a second configuration dimension does not grow the gap. The
exposure functional is smooth in configuration. The thesis is false in AEGIS's own validity domain.

**I ran a rank-of-Q calculation and published numbers from it.** Two of my own drivers disagreed at
identical settings while their `build_G` functions returned bit-identical arrays. Report 13 found the
bug: the phantom meshes are **already in meters**, and three of my four scripts divided by 1000
unconditionally, shrinking a 1.8 m human to a 1.8 mm speck. At 3 m that subtends 0.0006 rad, an
unresolved point source, so all 256 steering vectors coincide and `Q` collapses to exact rank one.
My `bugfind.py` then "proved" the two `build_G` functions identical *because it applied the corrupting
divide before calling either of them*, so they agreed by being equally wrong. My inference, "the
functions match so the bug is elsewhere," was exactly backwards. It was one layer up.

The settled answer, which the repo and report 13's independent calculation agree on: algebraic rank of
`Q` is `min(M, 3 n_tri)`, which is full. **Effective rank is 8 eigenvalues to 90 percent of the trace
and about 23 to 99 percent** (measured 7 and 23 on the real ray-traced grid), with the top mode holding
45 to 60 percent. Frequency-invariant at half-wavelength spacing, confirmed across 8 to 28 GHz while
the aperture shrinks from 28 cm to 8 cm. And the physical statement, which is the useful one: **the low
effective rank is not a property of the body.** The body's surface kernel is intrinsically high-rank.
What is low-rank is what survives projection through the array's finite angular aperture.

Report 13 also caught a scar in the paper's own numbers. In AEGIS's far-field model a single cluster
gives `G_t = v_t a^H`, so `Q = (sum_t area_t |v_t|^2) a a^H` is *exactly* rank one, and `rank(Q) <= C`
for `C` clusters. The synthetic-cone "rank about 5" was therefore partly an artifact of using few
clusters in a shared-direction model, which is why the ray-traced factory number came out higher.

The pattern is worth naming. Every one of those errors was me reasoning from structure and naming
rather than from measurement. The two agents who measured produced the only durable results.

---

## What differentiability actually buys, graded by measurement

The brief proposed four mechanisms. Three of them fail, and the fourth fails in the direction I
pointed it.

**(a) High-dimensional design.** Gradients beat sweeps only above roughly ten parameters. AEGIS's
design vectors:

| knob | nominal dimension | verdict |
|---|---|---|
| precoder `x` | 512 real (M=256 complex), but the objective lives in an **8-to-23-dimensional subspace** (report 13) | **closed-form eigenvector optimum** (`level8_ecbf.py:106`). Gradients worthless. |
| SMPL-X pose | 63, effectively 32 (VPoser) | severed from the graph (`parametric.py:51`, `torch.no_grad()`), and where it was plumbed, gradient ascent beat 100 random shots on 9 of 18 scenes, a coin flip |
| per-triangle coating impedance | 10^4 to 10^5 | genuinely high-dimensional, genuinely needs gradients, and lands in the exact regime where report 10 measured the PO gradient to be worst |
| mesh vertices | 10^5 | same, worse |

The mechanism holds in exactly one place and that place is where the physics fails. This is not a
coincidence and it is the study's central structure.

Report 13 sharpened the first row into a proof. A gradient walk over a 512-real precoder is optimizing
an objective that lives in an 8-dimensional subspace at 90 percent of the trace, with one mode holding
half of it, and the optimum of that objective is an eigenvector you already have in closed form. The
honest qualifier: the per-element-power-constrained variant is not a single eigenvector and needs an
SDP, where autodiff has marginal value, but **Xu et al. 2018 already published that SDP**, so even the
marginal case is not novel.

**(b) Inversion.** Report 05 built the demo instead of arguing: SMPL-X pose to coherent PO scattered
field to a multistatic array, fully autodiff. Gradient descent recovers one degree of freedom weakly
and collapses at three or more. At 21 degrees of freedom the vertex RMSE is 696 mm and the loss
*decreases* while the pose error *grows*. Gradient cosine to the true direction is 0.1 to 0.2, and on
one seed negative at -0.49, even 5 mrad from the truth. The cause is physical and clean: **the
coherent phase basin is about one wavelength (1 cm at 28 GHz) while a pose change moves the surface
about 10 cm**, so every gradient step samples an uncorrelated speckle realization. This is why RF
human sensing is machine-learning-dominated, stated as physics rather than as sociology. It also
retires the sentence "nobody has a differentiable forward model of a human body scattering RF":
Tsinghua's DIPR/PPPR (ACM IMWUT 2025) does differentiable mmWave pose recovery today.

**(c) Exact sensitivity coefficients.** Report 06 benchmarked it in-repo. Reverse mode costs about one
forward pass. Finite differences cost 2N. For the 10 to 30 scalar inputs a GUM budget mandates, and a
millisecond forward model, the entire finite-difference budget completes in under a minute. Autodiff
saves seconds. Nobody buys seconds. Worse, the FDTD uncertainty budget is dominated by
*non-differentiable* numerical rows (staircasing, absorbing boundaries, convergence) that autodiff
cannot touch. The mechanism becomes essential only at 10^3 to 10^5 field-valued coefficients, which no
standard mandates. And note the sting from report 10: an exact sensitivity coefficient of a model
whose derivative is sign-flipped is an exactly wrong number, and wrong-signedness is a defect in a
certification budget at any magnitude.

**(d) Certified suprema over continua.** This was mine, and report 07 killed it with a table:

```
configuration-sampling penalty (what the certificate removes):   ~4 %
PO model error, two-sided (what the certificate cannot remove):  3 to 10 %
customary VOP safety factor the field already applies:           120 %  (the 2.2x)
```

The certificate tightens the smallest term. A regulator is not short of the 4 percent. They are short
of a defensible margin on the 3 to 10 percent and a rationale for the 120 percent. And the goal is
anticipated: De Greef et al., *Phys Med Biol* 56 (2011) already computed worst-case SAR over patient
position in MRI, by discrete sampling plus a generalized eigenvalue plus a 2.2x factor. Meanwhile IEC
62232 is moving *toward* statistical 95th-percentile methods (Thors, Colombi) and *away* from
worst-case bounding. A certificate that makes the reported number larger is a product the market is
actively walking away from.

Report 07 also found the structural reason, which is the most elegant sentence in the study and cannot
be engineered around:

> Where a certificate would be valuable, in spiky resonant implant-scale low-frequency metrics that
> hide peaks between samples, physical optics is invalid. Where physical optics is valid, on
> electrically large smooth mmWave bodies, the metric is smooth and the certificate is low-value.

That is a domain mismatch, not an engineering gap.

---

## The measurement that should change how the company talks

Report 10 is the first experiment in this lineage that could return a hard no about the gradient
itself, and it did. Against the committed exact oracles (`studies/diffraction/cylinder_oracle.py`,
`sphere_oracle.py`, and `miepython`, the CI canary's own tool), with the differentiated function first
validated against `engine.compute().sab` to zero relative error at level 3:

- **Deep-lit value and gradient: good.** About 1 percent. The method works where it claims to.
- **Near-terminator value: 3 to 16x under-predicted.** The "3 to 10 percent" figure survives only
  because the aggregate is deep-lit-dominated.
- **Near-terminator incidence gradient: 2 to 20x too steep.** The Fock gate makes the mid-penumbra
  *worse* than a plain ReLU and remains about 12x too steep at the terminator.
- **Size and frequency gradient of absorbed power: sign-flipped at every `kR` tested**, on both
  geometries. Exact absorbed power approaches the geometric-optics limit from above, AEGIS from below.
  Same limit, opposite finite-size correction, inverted derivative everywhere. Level 3 gives an honest
  zero. Level 6 manufactures a confidently wrong sign.

Calibration, in fairness: `dln/dkR` is about 1e-3, because absorbed power is nearly flat in frequency
for a large lossy body. The sign flip is a flip of a small derivative. Its importance is not magnitude.
It is that **value convergence does not imply gradient correctness**, proven, in the one place where
the repo's own CI canary certifies the value. Everything this study assumed rested on that implication.

And the contamination result matters: only 5.4 percent of the cylinder's absorbed power lives within
15 degrees of the terminator, yet the aggregate's `kR` gradient is still sign-flipped, because the
gradient is dominated by the region where model and truth diverge. "The peak is deep-lit, so we are
safe" protects the value and not the derivative.

### The one place this cuts the other way

An over-steep gradient is fatal to descent and harmless to bounding. A Lipschitz constant that is too
large makes a branch-and-bound certificate *looser*, never *unsound*. Conservatism is the correct
failure direction for a safety bound. And the supremum of absorbed power over configuration lives at
normal incidence, deep-lit, where report 10 measured the gradient to be accurate. So the gradient does
not kill the certificate.

The 3 to 16x local *value* under-prediction near the terminator does. A certificate bounds the model,
and a model that locally under-predicts by 16x cannot be made one-sided without a validated margin.
That margin remains, as the previous study also concluded, the only genuinely novel unbuilt object in
the vicinity, and its novelty would live in the conservativeness proof rather than in any eigenvalue.

---

## The one thing that is genuinely AEGIS's alone

Report 07, section 2.3, made the brief's hand-waving quantitative. For the local metric under
self-occlusion:

- a **hard** visibility gate gives an **infinite** Lipschitz constant, so a branch-and-bound
  certificate built on it is vacuous,
- the **Fock** gate gives a **finite** one, `max_xi |d|g|^2 / d xi| = 0.68`, grid-independent,
- and 0.68 is the *physically correct* value, because the penumbra width `(kR)^{-1/3}` is fixed by
  Maxwell rather than chosen.

Verified competitor positions, from report 01 and report 02: **Sionna RT does not handle visibility
discontinuities at all** (its own documentation states paths cannot appear or disappear), so its shape
gradients are biased or zero at silhouettes. **DiffeRT smooths with a tunable heuristic width**, a
configurable parameter, which is the RF twin of SoftRas. Neither has a physical anchor, and neither
has an `R` with which to set the width.

So the sentence is:

> Hard-visibility and heuristically-smoothed differentiable ray tracers are wrong about the Lipschitz
> constant at silhouettes. AEGIS is right, because the physics chose the smoothing kernel.

This is a correctness claim about competitors, not a feature claim about AEGIS. It is narrow enough to
survive VOP, Xu 2018, the Theory of Characteristic Modes, and the CTU Prague and Lund quadratic-metrics
portfolio. It is the only claim in this study with that property.

Two conditions, both hard. It is **not enabled**: `parametric.py:51` runs SMPL-X under
`torch.no_grad()` and returns numpy, so `L_Q` over pose is not currently computable end to end, and an
unenabled claim is a dead claim. And it is a claim about the *terminator*, which report 10 shows AEGIS
gets smooth but 12x too steep, so the constant is finite and correct in *form* while the reported
magnitude needs its own validation before the word "correct" is used in front of an examiner.

---

## What died in this study

- **"We are the differentiable EM engine."** The category is fifteen years old. CST has shipped adjoint
  S-parameter sensitivity since about 2011. Photonics has `meep-adjoint`, ceviche, and Lumerical's
  `lumopt`. Radio has Sionna RT and DiffeRT. (Report 02.)
- **Differentiable physical-optics RCS as novel method.** Published: Fang, Wu, Ye, *IEEE JMMCT* 2025
  (DOI 10.1109/JMMCT.2025.3569766). Li, Bai, Qu, ACES 2021 (MoM plus AD on a flying wing). Bondeson
  2004 for gradient-based RCS shape optimization. (Reports 02, 03, 04.)
- **"Differentiable functional characteristic modes" as a phrase and as a patent anchor.** Each word is
  owned. "Functional" belongs to Liska, Jelinek, Capek, *Fundamental Bounds to Time-Harmonic Quadratic
  Metrics in Electromagnetism* (arXiv 2110.05312), which is literally any quadratic EM functional as
  `x^H A x` bounded by convex optimization. "Characteristic modes" belongs to Harrington and Mautz and
  ships in FEKO, CST, and HFSS, and names an object in a *different vector space* than `Q`, so
  borrowing the name invites an expert to map yours onto theirs and dismiss it. "Differentiable" is
  Capek's topology sensitivity. Report 11's verdict, which I endorse: **kill the phrase, keep the
  certificate.**
- **Adversarial pedestrian pose for automotive radar.** My own hypothesis, killed by report 04. The
  low-RCS pose the gradient marches toward is the multipath-null regime, which first-order PO fills
  incorrectly (leg-to-ground corner reflector, leg-torso multi-bounce, edge diffraction). And a
  twenty-pose sweep suffices, because the safety-relevant hard cases are kinematic and known. AEGIS's
  PO is *weakest* on the articulated nulling pedestrian and *strongest* on the smooth dielectric bumper
  fascia.
- **Gradient-based RF human pose recovery from scratch.** Report 05's demo, above. The speckle basin is
  one wavelength wide.
- **The certified supremum over the configuration continuum, as the patent's escape route.** Report 07.
- **Spinoff-to-acquire into big EDA.** Report 09 verified every deal: Synopsys-Ansys ($35B, closed Jul
  2025), Siemens-Altair (~$10.6B, Mar 2025), Renesas-Altium ($5.9B, Aug 2024), Cadence-BETA CAE
  ($1.24B, May 2024), Ansys-Lumerical (~$107.5M, 2020). The word "differentiable" appears in zero deal
  theses. Ansys bought Lumerical, which *already shipped adjoint inverse design*, for a category and
  not for its gradients. Hot money (PhysicsX ~$2.4B, Neural Concept, Luminary Cloud) goes to *learned
  surrogates*, not differentiable solvers. And "gradients cannot be retrofitted without a rewrite" is
  false for Synopsys-Ansys, who ship adjoint in Fluent today. Dassault, Robin's named target, was not
  even an acquirer in this wave.

---

## What survives, ranked

**1. The Fock finite-Lipschitz correctness result, as one paper and one narrow method claim.** It is
true, it is nobody else's, it is checkable, and it explains why a physics-derived kernel beats a tuned
one. Publish before someone in the differentiable-rendering community claims silhouette gradients for
RF. Prerequisites, in order: close the pose-to-vertex autodiff bridge (`parametric.py:51`), exhibit a
global Lipschitz bound, and validate the terminator magnitude against the exact cylinder, because
report 10 says the form is right and the magnitude is 12x off.

**2. Point the certified-supremum machinery at the uncertainty axis, not the configuration axis.**
Report 07 measured `lambda_max` moving **13.1 percent** over a plus/minus 20 percent box in skin
permittivity and conductivity. That is three times the configuration gap, comparable to the PO error
itself, and it is the axis ISO GUM, IEC 62232, and IEC 63195 *legally require you to report*. A bound
that holds for every tissue value in the IT'IS interval, computed by interval or affine arithmetic
through the same differentiable operator, is a different axis from the prior-art excitation eigenvalue
and converts a mandated line item into a guaranteed one. It also sells into the pre-compliance
beachhead that already exists.

**3. Compressed exposure sensing and the self-calibrating compliance array.** The number that kills
excitation-side gradients is the number that enables this, and report 13 ran the test
`generalization_map.md` section 7.5 asked for. `rank(Q) << M` is confirmed: **8 pilots recover 90
percent of the operator and about 23 recover 99 percent, against M = 256**. So an array that estimates
its own `Q` in situ from a handful of pilots, with no phantom and no measurement house, is on solid
physical ground. It depends on the low rank *essentially*, it is hardware and firmware IP rather than
software, and it has a concrete buyer in base-station self-compliance. Marked `could-not-check`: no
rich outdoor macro-cell scene is shipped, and if a diffuse deployment pushed the effective rank into
the hundreds, this idea and the one above would both flip. The ask is one Sionna RT macro scene with a
body at 30 to 100 m.

Separately, report 13 found that the effective rank is the Bucci-Franceschetti and Landau-Pollak
spatial degrees-of-freedom count, set by the illumination aperture rather than by the phantom, and that
**the monograph derives this independently and never cites it**. That is a citation to add and possibly
a short paper: the exposure operator's effective rank has a closed-form physical formula, which makes
it a result rather than a nuisance.

**4. Gradients that flow to a measurement rather than a design.** Report 12's second bet, and the
cross-cutting observation the archeology supports: every time the gradient pointed at a *design*
variable, the market did not want the design, and its consistent value was as a *certification and
transparency readout*. Where to place the probe. Which posture to test. Which clause is load-bearing.
Which of the 27 uncertainty inputs can be retired because the model says three of them matter. This
never requires an exposure limit to bind, which is precisely why it sidesteps every corpse in
`jsac_archeology.md`.

**5. The radome and radar-transparent-structure wedge, which runs on the transmission half already
built.** Reports 03, 04, and 08 converged on it independently from three lenses. Automotive 77 to
81 GHz bumper fascia, emblems, and paint stacks are a real, unglamorous, well-funded Tier-1 pain point
(Bosch, Continental, Valeo). It is the smooth dielectric surface where PO is *strongest*, it needs no
scattering module, and it does not depend on differentiability being the moat.

**6. Reflector and dish surface-figure compensation.** Report 08's top survivor, chosen on the right
criterion: it has a **fully lit working region**, no shadow boundary, so it is the one market immune to
report 10's finding. Incumbent is TICRA GRASP, itself a PO code, and not differentiable.

**Not ranked, but noted:** report 12's focused-ultrasound bet is the largest ceiling in the study and
the cleanest kernel swap (report 08 verified only `fresnel_operator.py` changes, to a scalar pressure
reflection coefficient, and that the Fock gate's soft and hard creeping constants are literally the
acoustic pressure-release and rigid boundary conditions, so the diffraction layer transfers with *less*
approximation than in EM). It is also the furthest from Robin's competence, his network, and his
regulator. Carry it as a breadth argument, not a plan.

---

## The single highest-value action

Two weeks, in this order, and the first week decides everything.

**Week 1: close the enablement gap and validate the one true claim.** Replace `torch.no_grad()` in
`parametric.py:51` with a JAX or `torch.func` path so pose flows to exposure in one graph. Then
reproduce report 07's `0.68` on the coherent self-shadow path rather than on the gate math in
isolation, and validate the terminator gradient magnitude against `studies/diffraction/cylinder_oracle.py`,
because report 10 says it is 12x too steep. If the constant is finite, physically anchored, and
correct in magnitude after a stated correction, there is a paper and a claim. If it is finite but the
magnitude cannot be validated, there is a paper and no claim.

**Week 1b, in parallel, the adversarial-example test that report 10 asks for.** Take a small coating or
shape optimization, descend the PO gradient to its optimum, and evaluate that optimum in a full-wave
solver. If the PO-optimal design is full-wave-suboptimal, gradient descent exploited model error at the
edges and every inverse-design idea in this study is dead. This is the cheapest hard no available and
nobody in four research programmes has run it.

**Week 2: only if week 1 passes.** Draft the narrow method claim around the physically pinned Lipschitz
constant, and give Alessandro the prior art this study surfaced, which is substantial and which he does
not have: Liska/Jelinek/Capek arXiv 2110.05312, Capek's topology sensitivity, Harrington-Mautz TCM as
shipped in FEKO/CST/HFSS, Fang/Wu/Ye JMMCT 2025, Li/Bai/Qu ACES 2021, Bondeson 2004, De Greef *Phys Med
Biol* 56 (2011), and the DIPR/PPPR differentiable mmWave pose work (ACM IMWUT 2025). Add these to the
Eichfelder 2011, US8,547,097, US8,653,818, Xu 2018, and ZMT Sim4Life set the previous study found.

---

## The thing this study kept circling

Report 10 states it and the archeology proves it. Differentiability is the fourth iteration of the same
pattern: a beautiful operator looking for a binding constraint. JSAC looked for it in exposure and found
four orders of magnitude of slack. JSAC2 looked for it in pose and found the user at 0.001x the basic
restriction. The military study looked for it in the exclusion-zone envelope and found a 2 percent wash.
This study looked for it in the Jacobian.

And each time, the thing that actually survived the rewrite was the same thing Robin named in the first
message of the JSAC2 archive, before any of it: *"you can make this matrix really quickly and compute it
very fast, much faster than FDTD, and that's really the enabler."*

The asset is the millisecond forward model. Report 06 found that AEGIS's speed, not its gradient, is
what obviates the incumbent (stochastic dosimetry via PCE and Kriging surrogates exists *because* FDTD
is too slow to Monte-Carlo). Report 09 found that acquirers buy categories, not derivatives. Report 07
found that the fast forward model plus four canonical postures already captures the worst case to 4
percent.

Differentiability is a genuine and well-implemented property of a genuinely valuable fast model. It is
not, on this evidence, the thing anyone will pay for. Sell the speed, publish the Lipschitz result, and
stop looking for a constraint that binds.
