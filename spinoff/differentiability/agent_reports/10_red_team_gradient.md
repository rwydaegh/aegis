# Red team: is the gradient of a wrong model a useful gradient?

Report 10. Lens: everything in this study assumes that because AEGIS's *value* is
nearly right, its *derivative* is nearly right. That does not follow, and nobody
had tested it. I tested it in this repo against exact solutions. The answer is
worse than the brief feared, and it is worse in a specific, decision-relevant way.

`NEEDS_CONTEXT:` none. Everything below was computed in-repo with `.venv/bin/python`
against the committed exact oracles (`studies/diffraction/cylinder_oracle.py`,
`sphere_oracle.py`) and `miepython`. Reproduction script:
`spinoff/differentiability/agent_reports/10_grad_quality_experiment.py`.

---

## Verdict up front

1. The gradient of AEGIS physical optics is **excellent deep in the lit region**
   (a few percent), **2 to 20 times too steep near the terminator**, and
   **sign-flipped for the size/frequency derivative of absorbed power at every
   frequency**. The value converges to the exact answer while the derivative
   points the wrong way. This is the textbook failure the brief warned about,
   now measured. (verified)

2. The Fock gate does **not** rescue the shadow-boundary gradient. It makes the
   mid-penumbra gradient *worse* than plain ReLU and stays an order of magnitude
   too steep at the terminator. It is smooth and wrong, which is worse than
   obviously broken because it converges confidently. (verified)

3. The moat claim in 2.2(b) is **half false in code**. AEGIS has a smooth,
   differentiable, physically-correct *terminator* but a hard, int8-quantized,
   ray-cast, non-differentiable *inter-part shadow* that is absent from the
   autodiff entry point entirely. (verified from source)

4. The deepest structural finding is a **pincer**: the places where the AEGIS
   gradient is trustworthy are exactly the places the previous three studies
   proved the objective does not bind (deep-lit pose, slack exposure), and the
   one place a high-dimensional gradient would genuinely pay (per-triangle
   inverse design of an object's signature) is exactly where the PO gradient is
   least trustworthy (edges, silhouettes, wide bistatic angles). Gradient
   quality and gradient value are anti-correlated across the use cases. (inferred,
   from my numerics plus `papers/jsac_archeology.md`)

I conclude differentiability, as a general property of this PO model, is not by
itself a business. A narrow, defensible slice survives, stated at the end, and it
is not the slice the brief expected.

---

## Diverge: 20 attacks and failure modes, one line each

1. `d(PO)/d(size,freq)` of total absorbed power is sign-flipped vs exact for both sphere and cylinder at every frequency. (verified)
2. `d(PO)/d(incidence)` is 2 to 20x too steep near the terminator. (verified)
3. Local value error near the terminator is 3 to 16x, not 3 to 10%. The "3 to 10%" only survives because the aggregate is deep-lit-dominated. (verified)
4. The Fock gate smooths the self-terminator but inter-part occlusion is a hard numba BVH closest-hit, int8-quantized, baked per body, absent from `compute_sab`. (verified)
5. The "unbiased silhouette shape gradient" moat fails twice: no inter-part occlusion, and 12x magnitude bias even on the self-terminator it does cover. (verified + inferred)
6. The highest-dimensional knob, the precoder (512 real), has a closed-form eigenvector optimum, so gradients are worthless there. (verified)
7. Pose gradients are severed at the source: SMPL-X runs under `torch.no_grad()` then `.numpy()`, so pose to exposure is not one graph at all. (verified)
8. Gradient quality is anti-correlated with gradient value across the surface and across the use cases. (inferred)
9. The half-engine is real: the scattered field is recoverable from the complex `G̃`, but "swap transmittance for reflectance" is an oversimplification and the honest angular sector is near-specular only. (verified + inferred)
10. PO backscatter is a narrow specular cone, and wide-bistatic and shadow-region RCS gradients are unreliable because PO zeroes the shadow current and misses the creeping return. (inferred, no scattering engine to test)
11. "Exact autodiff sensitivity coefficients" are exact for the model but can be wrong-signed vs reality, and where they are reliable the input dimension is small enough that finite differences already work. (verified sign, inferred economics)
12. The Fock gate smooths the visibility ReLU but not the Fresnel grazing collapse `T(mu to 0) to 0`, and the grazing collapse dominates the near-terminator value error. It fixes the wrong discontinuity. (verified)
13. In the geometric shadow the base term is hard-zeroed by the Fresnel mask, so creeping-wave absorbed power survives only through the curvature sliver. (verified)
14. A Lipschitz or branch-and-bound certificate over configuration continua built on `d(PO)` certifies the model's worst case, not reality's, and can miss a true worst case at a grazing configuration. (inferred)
15. "Differentiability" is a property, not a spine: the fourth iteration of "a beautiful operator looking for a binding constraint" (JSAC exposure, JSAC2 pose, military envelope, now gradients). (inferred)
16. Even where pose gradients were plumbed, VPoser 32-dim gradient ascent beat 100 random shots on only 9 of 18 scenes, a coin flip. (verified from archeology)
17. Autodiff optima on PO are candidate adversarial examples living at the edges and terminator where PO is most wrong, so descent can converge confidently to a full-wave-suboptimal design. (inferred, this is the testable core risk)
18. The gradient error is the derivative of the model error, and I measured that derivative to be O(1) relative near the terminator and sign-flipped for size, so a small smooth value bias still corrupts optimization. (verified)
19. Mesh faceting injects a non-physical per-face-normal gradient (staircasing) that an optimizer can exploit, separate from the PO error. (inferred, not measured)
20. The company's target bands (FR2/FR3, `kR ~ 6 to 40` for body parts) sit where the `(kR)^{-1/3}` penumbra is widest and the PO asymptotic is weakest, so the bad-gradient annulus is a large fraction of the body precisely in-band. (verified trend, x=40 vs 160)

Converging on 1, 2, 3, 4, 8, 9, 17.

---

## Task 1: settling it numerically

### Setup and what counts as truth

I compare AEGIS's per-triangle absorbed-power density against two exact solutions:
the lossy dielectric infinite cylinder (Bessel-Hankel series,
`dielectric_cylinder_surface_field`) and the lossy dielectric sphere (exact Mie
near field via `miepython`, plus `miepython.efficiencies` for `Q_abs`, the same
tool the CI Mie canary uses). Skin at 28 GHz, `n_tilde = 4.493 - 1.786j`.

The AEGIS side is not a strawman. I reconstructed the exact per-point density the
level-6 kernel computes and validated it against `engine.compute(...).sab` on a
5120-triangle sphere: level 3 matches to `0.0` relative error, level 6 matches to
3.4% over the whole lit hemisphere and 0.4% in the near-terminator band (the 3.4%
is mesh faceting, not a formula difference). The differentiated quantity is then
the real AEGIS kernel: `aegis.kernels.fock.fock_local` and
`aegis.kernels._base.fresnel_weights` under `AEGIS_ARRAY_BACKEND=jax`, wrapped in
`jax.grad`. (verified)

I parameterise position by distance to the terminator (`d2term = 90 deg - inc`,
where `inc` is the local incidence angle, `inc = 0` is normal incidence at the lit
pole, `inc = 90 deg` is the grazing terminator). I unify radius and frequency into
the size parameter `x = kR`, since both enter the diffraction physics only through
`x` (the material dispersion `dn/df` is an additional AEGIS-only frequency term I
note separately). I compare **log-sensitivities** `d ln P / d p`, which are free of
the unknown global field-normalisation constant between oracle units and AEGIS
`S_inc` units. The key identity:

```
d ln(S_PO)/dp  -  d ln(P_exact)/dp   =   d ln(model error)/dp
```

The gradient error *is* the derivative of the model error. It is zero only if the
error is `p`-independent. Chebyshev closeness in value bounds the error, not its
derivative. This is the crux made computable.

### Finding A: the value error is 3 to 16x near the terminator, not 3 to 10%

Cylinder, `x = kR = 40`, ratio of AEGIS level-6 density to exact (anchored to 1 in
the deep lit):

| dist to terminator | 70 deg | 50 | 35 | 25 | 18 | 12 | 8 | 5 | 3 | 1.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| S_PO / exact | 1.000 | 0.975 | 0.882 | 0.733 | 0.573 | 0.408 | 0.290 | 0.196 | 0.125 | 0.064 |

Deep in the lit region PO is within 1%. Within 25 degrees of the terminator it
collapses, reaching a **16x local under-prediction** at 1.5 degrees out. The cause
is verified in code: `fresnel_weights` clips `mu` to `[0, 1]` and zeroes `T` for
`mu < 1e-10`, so the Fresnel transmission grazing collapse `T(mu to 0) to 0` is
un-smoothed and dominates. The Fock gate smooths the *visibility* ReLU, but the
absorbed density also carries the *transmission* factor `T_avg(mu)`, which
independently collapses at grazing and is not smoothed. The gate fixes the wrong
discontinuity. The exact solution, by contrast, keeps roughly 10% of peak density
right at the terminator because curvature couples grazing energy into the surface.
The "3 to 10% wrong" figure is real only for the aggregate (below), which is
dominated by the deep-lit region where PO is genuinely excellent. (verified)

### Finding B: the incidence gradient is right deep-lit, 2 to 20x too steep near the terminator, and the Fock gate does not rescue it

`d ln P / d inc` (the dominant gradient component), exact vs AEGIS level 3 (ReLU)
and level 6 (Fock), cylinder `x = 40`:

| d2term | exact | L3 ReLU | L6 Fock | L6 over-steep |
|---|---|---|---|---|
| 70 deg | -0.357 | -0.36 | -0.38 | 1.1x |
| 35 | -1.230 | -1.33 | -1.92 | 1.6x |
| 18 | -2.038 | -3.06 | -4.61 | 2.3x |
| 8 | -2.733 | -9.03 | -8.68 | 3.2x |
| 3 | -3.154 | -31.0 | -20.8 | 6.6x |
| 1.5 | -3.287 | -68.5 | -41.1 | 12.5x |

The exact log-slope saturates around -3 (the penumbra is smooth and its relative
steepness is bounded). Both PO models blow up because `S_PO to 0` faster than the
truth at grazing. Two things kill the "the Fock gate makes silhouette gradients
correct" story:

- **The Fock gate over-steepens the mid-penumbra relative to plain ReLU** (1.6x
  vs 1.1x at 35 degrees, 2.3x vs the ReLU's own ratio at 18 degrees). It only
  becomes *less bad* than ReLU within about 5 degrees of the terminator, and even
  there it is 12.5x too steep.
- Increasing `kR` to 160 pushes the accurate region closer to the terminator (the
  over-steepness at 1.5 degrees drops from 12.5x to 7.5x) but never removes it. In
  the company's target band, body parts have `kR ~ 6 to 40`, the small-`kR` end
  where this is worst. (verified)

Answer to the brief's precise question: the Fock soft-gate makes the shadow-boundary
gradient smooth and wrong, not correct. (verified)

### Finding C: the size and frequency gradient of absorbed power is sign-flipped at every frequency

This is the headline. The total absorbed power (cylinder `W = integral P dphi`,
sphere `Q_abs`) is 3 to 11% low and **converging** to the geometric-optics limit
as `kR` grows, exactly as the Mie canary certifies. But its derivative with respect
to `kR` has the wrong sign everywhere:

| geometry | kR | AEGIS/exact value | `dln/dkR` exact | `dln/dkR` AEGIS | |
|---|---|---|---|---|---|
| cylinder | 40 | 0.893 | -0.00102 | +0.00050 | SIGN FLIP |
| cylinder | 80 | 0.927 | -0.00038 | +0.00019 | SIGN FLIP |
| cylinder | 160 | 0.952 | -0.00014 | +0.00007 | SIGN FLIP |
| cylinder | 320 | 0.970 | -0.00005 | +0.00002 | SIGN FLIP |
| sphere | 40 | | -0.00219 | +0.00086 | SIGN FLIP |
| sphere | 80 | | -0.00078 | +0.00035 | SIGN FLIP |
| sphere | 160 | | -0.00027 | +0.00013 | SIGN FLIP |

The exact absorbed power approaches the GO limit **from above** (finite-size
absorption enhancement decays as the body grows, `d/dkR < 0`). AEGIS approaches
**from below** (it under-predicts and the deficit shrinks, `d/dkR > 0`). Same
limit, opposite finite-size correction, so the derivative is inverted at every
finite frequency. I verified this is not a Mie ripple: exact cylinder `W(kR)` is
monotone decreasing across `kR = 40` to `400`, and exact sphere `Q_abs` from
`miepython` is monotone decreasing across `kR = 30` to `160`. I verified it is not
an FD artifact: the exact log-derivative is converged to four digits across step
sizes. I verified the AEGIS sign comes from the base Fresnel-times-gate term (the
gate sharpens toward 1 as `kR` grows), not the curvature sliver. (verified)

Note the cruel detail. Level 3 (ReLU) gives `d/dkR = 0` exactly (it has no size
dependence). Level 6 (Fock) *adds* a size dependence with the wrong sign. The Fock
gate converts an agnostic zero gradient into a confidently wrong-signed one. That
is the precise meaning of "smooth and wrong is worse than obviously broken."
(verified)

Honest calibration. The magnitude is small: absorbed power is nearly flat in
frequency for a large lossy body, so `dln/dkR ~ 1e-3`. The significance is not the
magnitude, it is three things. First, it is a clean proof that value convergence
(the Mie canary) does not imply gradient correctness, which is the entire epistemic
assumption of this study. Second, a wrong-signed sensitivity coefficient is a defect
for a certification uncertainty budget at any magnitude. Third, for other
observables (near-terminator local density, thin-layer resonances, the scattered
field) the wrong-signed term is not guaranteed to be small. I measured the case
AEGIS actually computes. (verified for absorbed power, inferred for other
observables)

### Does the terminator error stay local, or contaminate the aggregate

It contaminates. Only 5.4% of the cylinder's absorbed power lives within 15 degrees
of the terminator and 2.2% in the geometric shadow, yet the aggregate's `kR`
gradient is still sign-flipped, because the gradient is dominated by the region
where model and truth diverge. So "the peak is deep-lit, so we are safe" protects
the *value* but not the *derivative*. (verified)

### On cosine similarity

The brief asked for cosine similarity of the gradient vectors. I computed it for the
2-vector `[d ln P / d kR, d ln P / d inc]` and it is +1.000 everywhere, which is
**uninformative here**: the incidence component is 100 to 10000x larger than the
size component and has a consistent sign, so it dominates the cosine trivially. The
honest metrics are the per-component sign and magnitude ratios in Findings B and C.
I am flagging this because a cosine-similarity number near 1 would look reassuring
and would be meaningless. (verified, methodological)

---

## Task 2: the two structural claims

### 2.2(a) the half engine: the information is there, the readout is not, and the honest sector is narrow

Verified from code. `coherent/field_channel.py` builds `G` of shape
`(n_tri, 3, M_ant)`, **complex**, carrying the incident propagation phase
`exp(-i k0 k_hat . r)` accumulated per antenna element. `tissue/fresnel.py`
`_fresnel_core` returns the amplitude *reflection* coefficients `r_s, r_p`
alongside the transmission `t_s, t_p`, and `fresnel_reflection` exposes them. So
the phase, the per-element structure, and the reflectance are all present. Absorbed
power `|G̃_t x|^2` discards phase, but `G̃` itself does not. The information needed
for a scattered field is retained. (verified)

But "swap transmittance for reflectance and evaluate the radiation integral" is an
oversimplification in two ways. First, the PO scattered field is not a Fresnel
readout at the surface, it is the physical-optics current (`J_s = 2 n_hat x H_inc`
on the lit region, zero in shadow) radiated to an observer with the
observer-direction phase `exp(+i k_obs . r)` and a surface integral. That reuses
`G`'s phase and element structure but is a genuinely new module (a few hundred
lines), and grep confirms none of it exists in `src` (every "scatter" is
scatter-add accumulation). Second, and this is the load-bearing limit, PO
backscatter from a smooth convex body is a stationary-phase (specular flash)
contribution. It is accurate in a narrow cone around the specular direction and is
known to be poor at wide bistatic angles, near grazing, and in the shadow region,
where it sets the current to zero and misses the creeping-wave return. Combined
with Finding B, the scattered-field gradient inherits the same silhouette and
wide-angle unreliability. So the half-engine is real, buildable, and points at a
larger market, but its *differentiable* usable sector is the specular neighbourhood,
not the full bistatic sphere. (verified code, inferred angular bound from PO theory,
not measured because there is no scattering engine to differentiate yet)

### 2.2(b) the soft rasterizer: smooth terminator, hard shadow, moat half false

This is the concrete, checkable, load-bearing fact the brief asked me to find and
state plainly. I found it.

The Fock gate is a smooth function of `mu = n_hat . (-k_hat)`, the incidence
direction relative to the *local surface normal*. In `kernels/level6_diffraction.py`
the gate is `fock_local(mu, ...)`, and `mu = normals @ (-k_hat).T`. This is the
grazing locus of a single smooth convex surface, the self-terminator. There the
Fock function is the physically correct smoothing of the visibility step, validated
against the exact cylinder, and it is differentiable. That much of the moat claim is
true. (verified)

The occlusion of one body part by another is a completely different discontinuity,
and it is resolved by a hard ray cast, not the Fock gate:

- `geometry/occlusion.py` `_ray_mesh_closest_hit_numba` (lines 437 to 523) is a
  numba nearest-hit loop, `if t > 0.0 and t < best_t: best_t = t; best_tri = ti`.
  Non-differentiable `argmin`. (verified)
- `geometry/visibility.py` bakes the result into a per-body LUT with the clearance
  **quantized to int8** (`CLEARANCE_SCALE = 0.5/127` rad per LSB, `np.round`). Doubly
  non-differentiable: a rounded integer gather. (verified)
- There is zero `jax` and zero `grad` anywhere in `visibility.py` or
  `occlusion.py`. (verified)
- In `kernels/fock.py` `distal_gate`, the occluder radius `R_occ` is "baked so the
  switch is constant in the pose gradient". (verified, source comment)
- Decisively, the autodiff entry point `engine.compute_sab` has **no `self_shadow`
  parameter at all** and never calls `_distal_inputs`. Self-shadowing is absent from
  the differentiable path. The specular recapture is also explicitly excluded from
  autodiff (its docstring says so). (verified)

So AEGIS has a smooth, differentiable, physically-correct terminator and a hard,
int8-quantized, baked, non-differentiable inter-part shadow that the autodiff path
does not see. The moat claim, "hard-visibility differentiable ray tracers have
biased shape gradients and AEGIS's are correct," is:

- true for the self-terminator of a single smooth convex body, and
- false or absent for the occlusion of one object or part by another, which is
  precisely the visibility discontinuity SoftRas, redner, and Mitsuba were built to
  handle.

And even on the self-terminator it does cover, Finding B shows the gradient
*magnitude* is up to 12x biased near the silhouette (the normal-tilt gradient a
vertex perturbation induces is proportional to `d/d inc`, so the 12x transfers). The
gate delivers a finite, correctly-signed terminator gradient, which is better than
a naive hard-visibility zero, but "unbiased" is quantitatively false by an order of
magnitude. (verified value, inferred vertex-to-normal mapping)

---

## Task 3: attack the economics of the dimension argument

Mechanism (a) says gradients only pay above roughly ten design parameters. Walking
the study's favourites:

- **Precoder `x` (512 real, genuinely high-dim).** Has a closed-form optimum. The
  eigen-beamformer is `eigendecompose_Q(Q)` and the optimal excitation is the top
  eigenvector (`kernels/level8_ecbf.py:106`, `x_star` from the eigendecomposition).
  Gradients are not merely unnecessary here, they are strictly dominated by a one-shot
  linear-algebra call. The single highest-dimensional knob in the system is the one
  place gradients add nothing. That irony is worth stating in the patent discussion:
  the differentiability story cannot lean on the precoder. (verified)

- **Pose (63-dim, 32-dim VPoser).** Two independent problems. It is low-rank and
  multimodal in practice: JSAC2 found 32-dim gradient ascent beat 100 random shots on
  only 9 of 18 scenes, a coin flip (`papers/jsac_archeology.md`). And it is not even
  connected: `geometry/parametric.py` runs SMPL-X under `torch.no_grad()` then
  `.numpy()` (lines 51 to 54), severing the graph. Pose to exposure is not one
  autodiff chain today, and where a related pose gradient was plumbed it barely beat
  random. (verified)

- **Per-triangle coating impedance (1e4 to 1e5, genuinely high-dim and non-degenerate).**
  This is the one candidate where the dimension argument holds cleanly. But you do
  not coat a human. Per-triangle material design is a property of *objects*, which
  points straight back to 2.2(a), the scattered-field engine that does not exist, and
  into the market where the PO gradient is least reliable (Finding B, wide-angle and
  silhouette). (verified dimension, inferred market)

- **Mesh vertices (1e5).** High-dim, but free-form shape optimisation of a human is
  not a product, and the vertex chain is the severed PyTorch path above. (inferred)

- **RIS element phases (1e3 to 1e4).** High-dim, but RIS phase design is driven by the
  RIS-to-channel model, not the body absorbed-power operator. AEGIS is not obviously
  the tool. (inferred)

The dimension argument therefore supports **inverse design of objects** (coating,
free-form shape, signature), not a human-body differentiability business. And the
object case depends on the missing scattering half and lands in the low-reliability
gradient regime. (inferred)

---

## Task 4: attack the premise from the top

Robin has now had three programmes in which a beautiful operator went looking for a
binding constraint. JSAC put exposure on the base station and exposure did not bind.
JSAC2 moved the twin to the phone and made pose the control, and the MCS cap ate the
gains while exposure still did not bind. The military angle built an envelope and
prior art killed it. The archeology's own verdict is that the only thing that
survived every rewrite was speed, `Q = J^T M J` in milliseconds, and that the novel
thing was never the spine.

"Differentiability" is not even a spine. It is a property. That makes it the fourth
and most abstract iteration of the same error: a capability in search of a problem.
The prior three at least named an application. This one names a Jacobian.

What would make this time different is a single discipline the previous rounds
skipped: **prove the gradient is worth more than its cheapest substitute on a task
whose objective lives where the gradient is accurate, and prove the optimum is not a
model artifact.** The previous spines never had to clear that bar because they never
got as far as trusting a gradient. My numerics show why the bar matters: the gradient
is accurate where the objective does not bind, and the objective binds (high-dim
inverse design) where the gradient is not accurate.

### The two-week falsification test

Run this. It is designed to return a clean no, or a defensible yes, within two weeks
and two people, mostly in-repo.

**Week 1, in-repo, the substitution test.** Take the one genuinely high-dimensional
non-degenerate task: per-triangle surface impedance (coating) of a smooth convex
object, objective = shape the absorbed-power profile toward a target (absorbed power
needs no new engine, it is what AEGIS already computes). Race four optimisers to a
fixed target: (i) `jax.grad` plus L-BFGS, (ii) finite-difference gradient plus L-BFGS,
(iii) CMA-ES, (iv) a Gaussian-process surrogate with expected-improvement. Metric:
does autodiff reach the target with more than a 5x reduction in forward evaluations
*and* a better final objective than all three. If it ties, as pose did on 9 of 18
scenes, differentiability is decorative and you are done, the answer is no.

**Week 1b, in-repo, the adversarial-example test (this is the decisive one).** Take
the autodiff-found optimum and evaluate it in the exact oracle (Mie or cylinder for a
smooth body, or a MoM or FDTD reference for a real shape). Does the PO-optimal design
stay optimal under the exact model, or did gradient descent exploit the PO error and
converge to something the exact model rates as mediocre? Concretely, define
`degradation = (objective_exact_at_PO_optimum - objective_exact_at_exact_optimum) /
objective_exact_at_exact_optimum`. If degradation is under about 10%, the PO gradient
is trustworthy for design and the thesis has a leg. If the PO optimum sits at the
edges or terminator and degrades badly under full-wave, the gradient is exploiting
model error, and no amount of speed saves it. My Findings A to C predict this test
will fail whenever the target profile has structure near a silhouette or shadow, and
pass for smooth deep-lit targets. That prediction is itself the experiment.

**Week 2, one customer call.** For the object-signature market only (RCS, coating,
device-housing), not the human-body market the prior studies retired, confirm one
buyer will pay for a 5x design-cycle speedup that is validated against full-wave.
Incumbent to name: adjoint-based full-wave inverse design (Ansys HFSS and CST with
adjoint, and in the photonics analogue Lumerical, Tidy3D or Flexcompute). If the buyer
says "I will not ship a design my full-wave tool did not sign off," then the
differentiable PO is a *pre-filter* that hands candidates to full-wave, not a
replacement, and you must price it as a pre-filter.

Distinguishing signal, stated so it cannot be fudged. Differentiability is the
business only if week 1 shows more than 5x advantage, week 1b shows under 10%
full-wave degradation, and week 2 finds a buyer for the object case. If week 1b fails,
the honest conclusion is that AEGIS's gradient is a fast local *heuristic* that must be
validated by a slower exact model at every optimum, which is a real but modest tool,
not a moat.

---

## What survives

Not "differentiability is a business." What survives is narrower and honest.

1. **The fast forward value model.** 3 to 11% aggregate accuracy, converging,
   milliseconds, is genuinely good and genuinely fast. This is the thing the
   archeology already identified as the survivor. It does not need gradients to be
   valuable. (verified)

2. **The deep-lit incidence and pose sensitivity, where it is a few percent accurate.**
   Useful for anything whose operating point stays away from silhouettes. The catch,
   from the prior three studies, is that those objectives do not bind. So this is a
   correct gradient in search of a paying objective, which is the study's whole risk in
   one sentence. (verified accuracy, inferred market gap)

3. **Certified suprema over configuration continua (mechanism d), but only with a
   guardrail.** A Lipschitz or branch-and-bound certificate is the one use where
   differentiability is essential rather than decorative. But Finding C means a
   certificate built on `d(PO)` bounds the *model's* worst case, and near grazing
   configurations the model's worst case is not reality's. The guardrail is to certify
   with a bound that includes the measured PO gradient error near silhouettes, which
   turns the clean certificate into a padded one. Whether a regulator accepts a padded
   certificate is the open question, and it is a better question than any the prior
   spines reached. (inferred, and I think this is the strongest surviving thread)

4. **The scattered-field half, as a pre-filter for full-wave object inverse design.**
   Real market, real incumbent, but contingent on building the radiation module,
   restricted to the specular sector, and gated by the week-1b adversarial test. Grade
   it a maybe, not a yes. (inferred)

The one-line answer to the brief's question. The gradient of this wrong model is a
useful gradient exactly where the value is already good and the objective does not
bind, and an actively misleading gradient exactly where a high-dimensional design
problem would make it valuable. Differentiability does not rescue AEGIS from the
pattern in the archeology. It is the same operator, looking for the same constraint,
now through a Jacobian. The honest next move is the week-1b test, because it is the
first experiment in this whole lineage that can return a hard no about the gradient
itself.

---

## Ethics note

Nothing in this analysis drifted toward optimising harm to a person. The work is
characterisation of a model's gradient quality against exact physics. No line of
inquiry required the out-of-scope direction.

---

## Claim ledger

Verified (source or measured, reproducible via the script):
- Value error 3 to 16x near terminator, ~1% deep lit, Findings A. 
- Incidence gradient 2 to 20x too steep near terminator, Fock over-steepens the mid-penumbra, Finding B.
- Size/frequency gradient of absorbed power sign-flipped at every frequency, sphere and cylinder, Finding C, robust to FD step, monotone (not ripple), driven by the base term.
- Aggregate value 3 to 11% and converging, yet its `kR` gradient is sign-flipped.
- Analytic AEGIS density validated against `engine.compute().sab` (L3 exact, L6 within faceting).
- 2.2(a): `G` complex with propagation phase, `r_s, r_p` available, no scattering code in `src`.
- 2.2(b): Fock gate on `mu`. Inter-part occlusion is numba closest-hit, int8-quantized, baked, no jax. `R_occ` baked constant in pose grad. `compute_sab` has no `self_shadow`. Specular recapture excluded from autodiff.
- Precoder optimum is closed-form eigenvector (`level8_ecbf.py:106`).
- SMPL-X pose runs under `torch.no_grad()` then `.numpy()` (`parametric.py:51-54`).
- VPoser gradient beat 100 random shots on 9 of 18 scenes (from `jsac_archeology.md`).

Inferred (reasoned, shown):
- Gradient-quality / gradient-value anti-correlation across use cases.
- 12x silhouette bias transfers from `d/d inc` to the vertex-normal shape gradient.
- PO scattered-field gradient is reliable only in the specular sector.
- Dimension argument supports object inverse design, not human-body differentiability.
- Padded-certificate guardrail for mechanism (d).

Could-not-check:
- Scattered-field gradient accuracy directly (no radiation module exists to differentiate).
- Mesh-faceting staircase gradient exploitation (plausible, not measured).
- Whether a regulator accepts a padded Lipschitz certificate.
