# AEGIS as a differentiable physics surrogate above full-wave

Verdict: CONDITIONAL. This is the most licensable framing I have and the one Tom Dhaene will parse in ten seconds, but it is also the weakest as defensible IP and it carries one hard technical risk that decides everything. It survives as a product only if I concede the domain of validity honestly and lead with the one thing his own toolbox does not give him for free: exact adjoint gradients and a closed-form eigenstructure, not a fitted response surface.

## What the play actually is

Position AEGIS not as a competitor to HFSS, FEKO, CST or Ansys Perceive EM, but as the fast analytic layer that sits above them. Do the design-space exploration and the gradient steps inside AEGIS, the closed-form physical-optics surface model, and call the full-wave solver only to certify the final one or two candidates. In surrogate-modeling vocabulary this is a coarse model or low-fidelity model driving a fine model. That vocabulary is exactly Tom's field, which is both the opportunity (he will immediately understand it) and the trap (he has seen every version of it since the 1990s).

The generalizable AEGIS core underneath the pitch is real and largely built, not a slide:

- A differentiable physical-optics surface engine (the incoherent forward model, `src/aegis/kernels/level0_bound.py` through `level6_diffraction.py`, the nine-level fidelity ladder in `theory/monograph_v2.tex`).
- A closed-form quadratic-operator calculus for the coherent regime: power deposited is a Hermitian quadratic form `x^H Q x` in the excitation `x`, with `Q` built in closed form from the ray-traced paths, its eigendecomposition giving worst-case and best-case excitation modes directly, and a closed-form exposure-constrained beamformer (ECBF) solving the QCQP (`papers/coherent-exposure-operator/paperC.tex`, `src/aegis/coherent/exposure_operator.py`, `ecbf.py`).

So the multi-fidelity analytic surrogate is implemented. The question is not "can they build it" but "is the physics good enough to rank candidates and point the gradient the right way, and is any of it defensible."

## The honest accuracy picture, quantified

The surrogate pitch lives or dies on the number, so here is the real one from `papers/TAP_paper/paper.tex`, with the domain caveat that matters more than the number itself.

Speed. Whole-body absorbed power is a single matrix-vector multiply evaluated in under 10 ms on a GPU (paper.tex L134-135, L169), against FDTD sweeps over incidence directions that take "weeks on GPU clusters" (L165). That is the six-orders-of-magnitude gap that makes a pre-screen layer worth building at all.

Accuracy, in-domain. In the mmWave surface-dosimetry regime the closed form "reproduces FDTD to within the tissue dielectric uncertainty, at a small fraction of the cost" (L194-195). Concretely:

- Mie validation on lossy spheres: agreement "at the fourth significant figure" in the geometric-optics regime (L524).
- Fresnel approximation error: 5.3% worst case pointwise, 1.2% typical direction-averaged (L1347-1349).
- Diffraction (sharp-shadow idealization): 10% worst case on a torso-scale Mie sphere, 1.2% typical integrated (L1350-1352).
- Inter-body multi-bounce omission: 4% worst case diffuse bound, 1% typical specular at mmWave (L1353-1355).
- The dominant residual is not the model, it is the input: dielectric spread of +/-20% on epsilon and sigma gives +/-7% on skin transmission (L1345-1347). "In the typical case every model error stays below the dielectric uncertainty" (L1356). Validated across 108 volunteers and 5 FDTD phantoms (L226-227).

That is a genuinely excellent surrogate. Right to roughly 1-5% integrated, worst case 10%, and the gradient direction is trustworthy because the errors are smooth and bounded, not oscillatory.

The caveat that I must not bury. Every one of those numbers is for absorbed power on a large, smooth, lossy human body at mmWave, where the assumption ladder A2 (first bounce), A3 (surface confinement) and A4 (locally planar) is physically close to true. This is precisely the regime where physical optics is supposed to work. It is NOT evidence that first-bounce PO is within 10% of a resonant microstrip filter, a coupled antenna array, or any structure whose behavior is dominated by multiple bounces, near-field coupling, or cavity resonance. In Tom's classic microwave-circuit domain the AEGIS surrogate would be poor. So the correct claim to Tom is narrow and defensible: "my surrogate is accurate where the physics is surface-scattering-dominated and electrically large," not "my surrogate is accurate for EM design in general." Overclaiming the latter is the fastest way to lose credibility with someone who has fitted metamodels to filters for thirty years.

## Where a physics surrogate beats a data-driven one, and where it does not

Tom's world is data-driven surrogates: Gaussian processes, neural nets, polynomial chaos, all fitted from full-wave samples, with adaptive sampling (the SUMO toolbox, Gorissen, Crombecq, Couckuyt, Dhaene) deciding where to sample next. AEGIS is a different animal: a physics-based surrogate that needs zero training samples and returns exact gradients of the physics, not fitted ones.

Where that genuinely helps:

- High dimension. Data-driven surrogates suffer the curse of dimensionality: sample count for a fixed accuracy grows badly with input dimension, and Gaussian-process regression in particular becomes awkward above a few tens of parameters. A physics surrogate has no sample budget at all, so its cost does not blow up with design dimension. For a large array with hundreds of excitation degrees of freedom, `x^H Q x` is exact and instant while a GP would need an infeasible design of experiments.
- Exact gradients for free. Adjoint or autodiff gradients of the analytic model are exact and cost about one forward evaluation. Data-driven surrogates give you the gradient of the fit, which is only as good as the fit and is often the first thing to go wrong between samples. Gradient-enhanced GPs exist but need the expensive gradients as training data. AEGIS hands them over at no marginal cost.
- No cold start. A GP is useless until it is trained. AEGIS is useful on the first evaluation of a never-seen geometry.

Where it does not help, and Tom will say so:

- The A2 accuracy ceiling is fixed, not tunable. A data-driven surrogate converges to the truth as you add samples. A physics surrogate is stuck at whatever first-bounce PO gives you. You cannot sample your way to certification, which is exactly why you still need the full-wave certifier. That is honest and fine, but it means AEGIS is strictly an inner loop, never the final judge.
- It is not a competitor to Tom's outer loop. The right architecture is AEGIS as the analytic inner loop (cheap exploration and gradient steps) inside his adaptive-sampling and UQ outer loop (which decides which AEGIS candidates to spend full-wave certification on, and quantifies the surrogate-to-fine gap). Framing it as replacing his metamodels is both wrong and needlessly adversarial. Framing it as the physically-informed coarse model his framework has always wanted is correct and flattering.

## The prior art that decides novelty: space mapping

This pitch has a named intellectual parent, and I have to say its name out loud before Tom does: space mapping, John Bandler, mid-1990s onward. Space mapping is precisely "use a fast coarse physics model to accelerate an expensive fine model," with the coarse model optimized in a mapped parameter space and the fine model called sparingly. The modern microwave-design literature is full of it, including trust-region variants for convergence safety and multi-fidelity mesh variants (Bandler et al., and a large follow-on literature through 2025). The coarse model in space mapping is explicitly described as "a physically-based representation of the structure," which is exactly AEGIS's role.

So the blunt question: is AEGIS-as-coarse-model just space mapping with autodiff? Mostly the mechanism is the same, and I should concede that. But there are two things that are genuinely not in classical space mapping:

1. Exact adjoint or autodiff gradients through the coarse model. Classical space mapping maps parameters between coarse and fine spaces and typically works from coarse-model responses, not from exact end-to-end differentiable gradients of a fully autodiff coarse model. AEGIS being differentiable end to end means gradient-based design in the coarse space is exact and free, not finite-differenced. This is a real, if incremental, advance over the 1990s formulation.
2. The closed-form Q eigenstructure. For the coherent excitation-design problem, AEGIS does not iterate a coarse optimizer at all. The worst-case and optimal excitations are eigenvectors of a Hermitian `Q`, available in closed form (paperC.tex L92, L201, L234, L733-747). That is a stronger statement than "fast coarse model": it is a closed-form solution to the inner design problem in the excitation variables. Space mapping has no analogue of that because its coarse models are generic simulators, not a quadratic form with known spectrum.

Honest reading: the overall paradigm (coarse physics model screens, fine model certifies) is prior art and not patentable. The differentiability is an incremental improvement on a known idea. The one thing that is genuinely novel and potentially defensible is the closed-form quadratic exposure operator and its eigen-inverse-design, but that novelty lives in the dosimetry-specific `Q`, not in the generic "surrogate layer" framing. The framing is the sales pitch, the `Q` operator is the IP. Do not confuse them.

## The Tom framing specifically

Single sharpest positioning, one sentence: "You spend your samples building a metamodel from scratch for every new geometry; I hand you a physics-based coarse model that needs zero samples and returns exact gradients and, in the coherent case, the optimal excitation in closed form, so your adaptive sampling only has to certify, not discover."

What impresses him:

- Exact gradients at the cost of one forward eval, in a field where gradient-enhanced surrogates are a whole sub-literature precisely because gradients are expensive to get.
- The closed-form `Q` eigenstructure. A surrogate-modeling expert who has seen every response surface has probably not seen the inner design problem collapse to an eigenvector of a closed-form Hermitian operator. That is the one slide that makes him lean in.
- Sub-10-ms whole-body evaluation with a bounded, quantified error budget dominated by input uncertainty rather than model error. He respects a clean error budget.

What he pokes immediately, and my prepared answer:

- "Your accuracy numbers are for human-body mmWave dosimetry, not for the resonant structures I design. First-bounce PO will be badly wrong on a filter." Correct, and I concede it. The surrogate is valid where scattering is surface-dominated and the target is electrically large. That is a real market (large reflectors, radomes, mmWave exposure, platform-scale scattering, wearables near tissue), just not his filter market. I sell into the domain of validity, not past it.
- "The coarse-model gradient can point the wrong way exactly near the optimum, where higher-order physics you dropped dominates." This is the real risk (next section) and I do not have a clean answer beyond a trust-region safeguard, which the space-mapping literature already uses.
- "This is space mapping." Yes, the paradigm is. My addition is exact differentiability and the closed-form operator. I will not pretend the paradigm is new.

## The biggest technical risk: gradient fidelity near the optimum

A surrogate right to 10% with the correct gradient direction is a superb pre-screen. A surrogate right to 3 dB but with the wrong gradient sign near the optimum is worse than useless because it walks the optimizer away from the true design. This is the crux and I will not paper over it.

The in-domain evidence is reassuring: the AEGIS error terms (Fresnel, diffraction smoothing, multi-bounce) are smooth, bounded, and slowly varying, and the diffraction correction is a monotone erf smoothing of the shadow edge (paper.tex L1293-1296), not an oscillatory term. Smooth bounded error is exactly the regime where the gradient direction survives even when the magnitude is off. In the surface-dosimetry domain I am fairly confident the first-bounce gradient points the right way.

The danger is out of domain, which is precisely where the "generalize AEGIS to EDA" ambition wants to go. When the expensive physics that A2 drops (multiple bounces, cavity resonance, near-field mutual coupling) is what actually creates the optimum, the cheap gradient is not just inaccurate, it is computed from the wrong physics, and its sign near that optimum is untrustworthy. Space mapping hit exactly this wall and the literature's honest finding is that output-space-mapping corrections "may actually increase the mismatch" away from the calibration point, which is why trust regions became mandatory. AEGIS inherits the same failure mode. The mitigation is the same trust region plus periodic full-wave gradient correction, which is sound engineering but is also an admission that the surrogate alone cannot be trusted to converge, only to accelerate.

## Verdict and what would have to be true

CONDITIONAL. This is the cleanest licensing narrative in the whole generalization question and the one most likely to carry a first conversation with Tom, because it speaks his language and because the underlying engine genuinely exists. But it is the least defensible as IP: the paradigm is space mapping (prior art, unpatentable), the differentiability is incremental, and the only genuinely novel and defensible artifact is the closed-form `Q` operator, which is dosimetry-specific and does not itself require the surrogate framing to have value.

Strongest angle: exact adjoint gradients for free plus the closed-form Q eigenstructure, sold explicitly as the physics-based coarse model inside Tom's adaptive-sampling and UQ outer loop, scoped honestly to the surface-scattering, electrically-large, mmWave domain where the PO physics is actually valid and the error budget is real.

Biggest risk: gradient fidelity near the optimum out of domain. The cheap model's gradient is computed from the wrong physics exactly where the dropped higher-order terms create the design optimum, so its sign is untrustworthy there, and the mitigation (trust region plus full-wave gradient correction) concedes that the surrogate accelerates rather than converges on its own.

What would have to be true to turn this into a licensing deal or LoIs:

1. A demonstrated design study where AEGIS-guided pre-screening plus a handful of full-wave certifications reaches the same optimum as full-wave-only at a fraction of the solver calls, on a target inside the valid domain (a large reflector, a radome, a wearable near tissue, an exposure-constrained array). One clean speed-vs-quality curve beats any slide.
2. An empirical gradient-agreement study: cosine similarity between the AEGIS gradient and the full-wave adjoint gradient, sampled across the design space and specifically near optima. If that stays positive in-domain, the pre-screen thesis is proven. If it flips sign near optima even in-domain, the play is downgraded.
3. Positioning as a complement that consumes Tom's outer loop rather than replacing his metamodels, ideally co-developed so the IP that matters (the `Q` operator and the differentiable engine) stays with AEGIS while the integration rides on his framework.

If those three land, this is a SOLID licensable layer for a specific domain. Absent the gradient-agreement evidence, it is a good slide and a fair research collaboration, not yet a product.

## Sources

- [Multi-fidelity local surrogate model for microwave component design (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6651435/)
- [Advanced space mapping with shared coarse model, tunable filters (arXiv 2507.14220)](https://arxiv.org/html/2507.14220v1)
- [Robust trust-region space-mapping algorithms for microwave design (IEEE Xplore)](https://ieeexplore.ieee.org/document/5499445/)
- [Space-mapping optimization of microwave circuits exploiting surrogate models (ResearchGate)](https://www.researchgate.net/publication/3121406_Space-mapping_optimization_of_microwave_circuits_exploiting_surrogate_models)
- [Fast calculation of the knowledge gradient for optimization of deterministic engineering simulations, Dhaene group (arXiv 1608.04550)](https://arxiv.org/pdf/1608.04550)
- [Active learning for approximation of expensive functions, Dhaene group (arXiv 1608.05225)](https://arxiv.org/pdf/1608.05225)
- [Physics-constrained deep learning for high-dimensional surrogate modeling and UQ (arXiv 1901.06314)](https://arxiv.org/pdf/1901.06314)
- [Enhanced data efficiency using DNN and Gaussian processes for aerodynamic design (arXiv 2008.06731)](https://arxiv.org/pdf/2008.06731)
- AEGIS internal: `papers/TAP_paper/paper.tex` (accuracy and speed numbers), `papers/coherent-exposure-operator/paperC.tex` (closed-form Q, QCQP, eigen-inverse-design), `theory/monograph_v2.tex` (nine-level fidelity ladder), `src/aegis/kernels/`, `src/aegis/coherent/`.
