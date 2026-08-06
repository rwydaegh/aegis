# Scattering-surface synthesis: RCS/low-observable and RIS/reflectarray/metasurface

Pressure-test of two markets that both rest on the AEGIS scattered-power operator Q_re. I went in expecting both to survive. One does, conditionally. The other is a capability with no reachable near-term market. This note grades them separately and says what would have to be true.

Scope of the shared core. AEGIS is a differentiable physical-optics surface engine plus a closed-form quadratic-operator calculus. Power in a mode is x^H Q x. The relevant operator here is Q_re, the specularly scattered-power Gram integral over the surface, defined in `theory/q_complement.tex` eq:Qref (IMPLEMENTED as theory, and the assembly machinery for its sibling Q_ab is IMPLEMENTED in `src/aegis/coherent/exposure_operator.py`). Q_re is the monostatic RCS operator for the first-bounce specular return. The whole calculus travels on assumption A1 (linear superposition). Fast evaluation needs A2 (first bounce dominates), A3 (surface confinement), A4 (locally planar Fresnel/Kirchhoff). The crux of this whole note is what A2 throws away.

---

## 1. Physics map

### 1a. What Q_re actually computes, and what it drops

Q_re integrates the Fresnel specular reflection of the incident plane-wave superposition over the front-facing surface, with the ReLU-cosine visibility gate (`theory/q_complement.tex` def:Qref, eq:Rn, eq:gref). Monostatic RCS in a direction is then read off the mode x that lights the surface from that direction and collects the back-scattered specular amplitude. For a large, smooth, singly-curved body this is exactly the physical-optics (PO) approximation, and PO is genuinely good near specular. That is the part that works.

A2 drops everything that is not a first-bounce specular current:

- edge diffraction (the fringe currents that Physical Theory of Diffraction adds on a sharp edge),
- tip and corner diffraction,
- traveling waves that run down a long thin body and reflect off the far end,
- creeping waves that wrap around a shadowed convex surface,
- multiple bounces inside gaps, cavities, inlets, and dihedral/trihedral corners,
- resonances when a feature is wavelength-comparable.

`q_complement.tex` rem:ignored lists exactly these as the terms excluded from the Q_ab + Q_re = Q_in identity. This is not a footnote. For a low-observable target these dropped terms are not a correction to the answer, they ARE the answer.

### 1b. Stealth/RCS: the explore-vs-certify wall

The specular return of a well-shaped stealth body is deliberately steered away from the threat radar, so by construction the residual RCS in the threat direction is set by precisely the mechanisms A2 misses. A faceted stealth shape (F-117 lineage) is faceted on purpose: flat plates give a narrow, predictable specular flash you can point at the sky, and sharp edges convert the rest into edge diffraction. The design objective is the -30 to -40 dBsm diffraction floor, not the +20 dBsm specular spike that PO nails.

Numerically (see section 2a), PO tracks the specular peak and the first few sidelobes of a flat plate within about 1 to 3 dB, then predicts nulls that go to minus infinity. Real plates do not have infinitely deep nulls. Edge diffraction fills them to a floor 30 to 40 dB below the specular peak. A gradient optimizer running on Q_re alone will happily drive a design into a "null" that its own physics says is perfectly black and that a real radar sees lit. That is the certify failure stated concretely: the optimizer is blind exactly where the customer cares.

So the honest verb is explore, not certify. AEGIS can take a smooth electrically-large body, differentiate the specular RCS with respect to surface normals, and push the specular flash off-threat. That is a real capability and it is the same trick the graphics community already shipped (section 3a). It cannot tell you the actual low-observable signature, because that number lives in physics AEGIS does not carry.

How much does `fock.py` recover? This matters and I checked the code. `src/aegis/kernels/fock.py` is a real, validated creeping-wave correction. It solves the Leontovich impedance-Fock pole against an exact PEC/dielectric cylinder oracle (`_leontovich_pole`, `fock_impedance_param`), reproduces the dominant creeping eigenvalue to three digits, and gives the correct shadow power-decay law exp(-sqrt3 q_p |xi|). `level6_diffraction.py` wires it into the surface integral as a gate. So AEGIS genuinely recovers the creeping-wave contribution on smooth convex bodies, which is more than textbook PO. But two things:

1. It is a smooth-convex-body correction. It closes the creeping gap, not the edge/tip/traveling-wave gap. `fock.py` has no Physical Theory of Diffraction fringe-current term and no cavity multibounce. The docstring is explicit that it is the "smooth-convex-body (Fock) shadow-edge transition."
2. It closes the gap for exactly the wrong shape class. Stealth designs are faceted, edged, and cavity-laden. Creeping waves matter for a smooth cylinder or a nose cone. They do not set the signature of an edged planform. So the one non-PO mechanism AEGIS owns is the one that matters least for the flagship stealth use case.

Ansys Savant/HFSS SBR+, the industry standard, hybridizes GO+PO with PTD and UTD precisely to capture edges and discontinuities (section 3a). AEGIS carries Fock but not PTD/UTD. That is the measurable physics gap versus the incumbent.

### 1c. RIS/reflectarray/metasurface: engineered surface, clean array-factor problem

This case inverts the difficulty. The surface is engineered, not given. Each unit cell has a tunable local reflection coefficient Gamma_n (phase, sometimes amplitude), and I steer a scattered beam by choosing the Gamma_n. This is A1 beamforming on a scattering aperture. For the main beam of a reflectarray or RIS, first-bounce specular IS the physics, because a passive reflecting aperture is a single-bounce device by design. So A2 is not a lie here, it is close to exact for the quantity of interest.

That makes it a clean Q_re eigen/QCQP problem. Maximizing scattered power into a target direction under a total-power or per-element constraint is exactly x^H Q_re x maximization, which is the top-eigenvector problem, and adding constraints (an interference null, an exposure limit, a second beam) turns it into the same QCQP that `src/aegis/coherent/ecbf.py` already solves for the dosimetry product. The step from "exposure-constrained beamforming" to "constrained reflectarray aperture synthesis" is a variable rename, not a new solver. That is the strongest structural argument for this market.

The honest caveat is the unit cell. Gamma_n does not come from AEGIS. It comes from a periodic full-wave unit-cell solve (HFSS/CST/Feko Floquet or eigenmode) under the local-periodicity approximation: you simulate an infinite array of identical cells, read the reflection phase, and assume each cell in the real aperture behaves like its infinite-array twin. The literature is blunt that this is where RIS accuracy actually lives and where it breaks: "the local periodicity approximation cannot be used to accurately design the unit cells of finite-sized metasurfaces," and mutual coupling between non-identical neighbors "can significantly alter the idealized responses" (section 3b). AEGIS models none of this. It has no unit-cell solver, no Floquet mode, no inter-cell coupling.

So the clean division of labor is: AEGIS owns the array-factor / aperture-synthesis layer (given the per-element Gamma library, place the phases to synthesize the field), and depends on an external unit-cell library for Gamma itself. That is a defensible position only if you say it out loud. AEGIS is the outer loop, the unit-cell full-wave solve is the inner loop, and the design error budget is dominated by the inner loop AEGIS does not own.

---

## 2. Light calculations

### 2a. Specular vs diffraction dynamic range (flat plate, 10 GHz)

Take a square plate, side a = 0.3 m = 10 lambda at 10 GHz (lambda = 0.03 m), area A = 0.09 m^2.

Broadside PO RCS:

sigma_spec = 4 pi A^2 / lambda^2 = 4 pi (0.09)^2 / (0.03)^2 = 4 pi (0.0081/0.0009) = 4 pi (9) = 113 m^2 = 20.5 dBsm.

Off broadside the PO main lobe follows sigma(theta) approx sigma_spec [sinc(k a sin theta)]^2 cos^2 theta. The first sidelobe of a uniform aperture sits at -13.2 dB, the second near -18 dB, and PO tracks these within a couple of dB. Between lobes PO predicts exact nulls (minus infinity). Measured plates never show that. Edge diffraction (the PTD fringe current AEGIS lacks) fills the nulls and sets a wide-angle floor around -10 to -20 dBsm, i.e. 30 to 40 dB below the specular peak.

Trust regime, stated as a number: first-bounce PO is trustworthy from the specular peak down to roughly 10 to 15 dB below peak (main lobe and first sidelobes). Below that, in the 30-to-40-dB-down band that defines low observability, the return is set by edge, tip, and traveling-wave diffraction and PO collapses. Low-RCS design lives entirely in the collapsed band. This is the quantitative statement of the certify wall.

A canonical cylinder (radius 0.1 m, length 1 m) has broadside monostatic sigma = k a L^2 = (2 pi/0.03)(0.1)(1) = 20.9 m^2 = 13 dBsm, and here the axial/shadow return is where creeping waves live. This is the one regime `fock.py` actually recovers. Note it is a smooth convex body, not a stealth planform.

### 2b. RIS/reflectarray aperture (N elements)

Take a 32x32 RIS, N = 1024 cells at lambda/2 spacing. Effective aperture A = N (lambda/2)^2 = 256 lambda^2.

Aperture directivity:

D = 4 pi A / lambda^2 = 4 pi (256) = 3217 = 35 dBi.

Coherent array-factor gain scales as N in the main beam (N amplitudes add coherently, |sum|^2 = N^2 over N radiated units). Half-power beamwidth approx 0.886 lambda / (sqrt(N) d) = 0.886 (2)/32 = 0.055 rad = 3.2 degrees. Beam steering is a linear phase gradient across the aperture, and the steered gain rolls off as cos(theta_steer) with the usual scan-loss and grating-lobe limits past roughly 60 degrees at lambda/2 pitch.

QCQP scaling. The ECBF solver (`ecbf.py`) eigendecomposes Q once, O(M^3), then does bisection O(M) per step on the Lagrange multipliers. For a RIS, M = N.

- N = 1024: eigendecomposition approx 10^9 flops, sub-second, Q is 8 MB complex128.
- N = 10^4 (100x100): approx 10^12 flops, order minutes, Q is 1.6 GB. Feasible but heavy.

Two mitigations already implicit in the code. The unconstrained main-beam steer is rank-1 (top eigenvector of Q_re, or literally the conjugate-phase / matched aperture), so you never touch the full QCQP for vanilla steering. The full QCQP only earns its cost when you add constraints (an exposure cap, an interference null toward a co-channel user, a second simultaneous beam), which is exactly the niche where AEGIS has something classical synthesis does not. Above about 10^4 elements you would want the JAX-vmap / factored path the dosimetry side already uses, not the dense eigendecomposition.

---

## 3. Incumbents and the gap

### 3a. Stealth/RCS incumbents

Differentiable RCS-style shape optimization is already a thing, and it arrived from computer graphics, not defense.

- Stealth Shaper (arXiv 2305.05944, cs.GR, SIGGRAPH-adjacent graphics venue) optimizes a 3D surface for low reflectivity using differential rendering, treating the surface normal as the free variable. It is ray-based specular, differentiable by autodiff through a differentiable renderer, and it targets "stealth aircraft and Sci-Fi vehicles" as a stylization tool. Its own framing concedes that real stealth design solves a wave equation resolving surface features at the radar wavelength, which ray-based rendering does not. This is almost exactly the AEGIS explore-not-certify capability, already published, in the open, two years ago.
- The adjoint-optimization and differentiable-EM literature is large and mature (Stealth Shaper aside, the photonic/metasurface inverse-design community has run adjoint shape and topology optimization for a decade: arXiv 2410.13074, 2405.03930, 1705.07188). Differentiable EM shape optimization is not novel ground.
- The certifying incumbent is Ansys HFSS SBR+ and Ansys Savant. SBR+ paints PO currents via GO ray tracing for multibounce and adds PTD and UTD for edges and discontinuities. This is the tool defense actually uses for electrically-large RCS, and it carries the exact diffraction physics AEGIS omits. POFACETS (a free MATLAB PO RCS predictor from the Naval Postgraduate School) occupies the low end and is also PO-based, so even the free tool covers the specular regime AEGIS would compete in.

Business blockers, which here dominate the physics. RCS/low-observable software and technical data are squarely inside ITAR / the US Munitions List, and the EU has parallel dual-use controls. A Belgian university spin-off selling stealth-shaping software walks into export-license regimes, defense-primes procurement cycles measured in years, and customers who will not touch an un-cleared foreign tool for signature work. Even if the physics were certifiable, the go-to-market is a multi-year, license-gated, clearance-gated slog with a handful of buyers, none of whom are AEGIS's current 6G/EMF network. This is the wrong first market for a small commercial spin-off regardless of the code.

### 3b. RIS/reflectarray/metasurface incumbents

- Sionna RT (NVIDIA, arXiv 2303.11103 and the 1.0 technical report 2504.21719) is the serious incumbent. It is a fully differentiable, GPU-accelerated ray tracer for radio propagation, Apache-2.0, and it has shipped RIS support since v0.18. It does the end-to-end channel-aware, multibounce version of the problem AEGIS would attack in closed form. If a customer wants "optimize this RIS in this environment," Sionna already does it, free, backed by NVIDIA, with the multibounce channel AEGIS's A2 drops.
- Classical reflectarray/RIS main-beam synthesis is a solved problem. Conjugate-phase matching (set each cell's phase to cancel the incident phase and add the desired progressive gradient) gives the main beam directly. Array-factor synthesis, Woodward-Lawson, and convex pattern synthesis are decades old and shipped in every antenna toolbox. Vanilla beam steering is not a market gap.
- The unit-cell inner loop is owned by full-wave vendors (HFSS, CST, Feko) and increasingly by deep-learning surrogates trained for full-wave accuracy on aperiodic layouts and mutual coupling (arXiv 2512.12625, 2603.15430). This is the layer where money and accuracy concentrate, and AEGIS is not in it.

Who would pay. RIS is still pre-commercial in the RAN. Nokia and Ericsson treat it as a research topic, not a shipping product. The nearer-term buyers are satcom and fixed-wireless reflectarray makers and RIS startups (Greenerwave, Pivotal/Metawave-lineage, various academic spinouts) who need aperture synthesis under real constraints. Their spend is modest and their in-house EM teams already run HFSS. The willingness-to-pay for a pure aperture-synthesis layer, on top of a unit-cell solve they already own, is the open question.

The one genuine white space. Constrained, closed-form aperture synthesis. Nobody ships a closed-form QCQP that steers a RIS beam while holding a human-exposure (EMF) cap, or while nulling a co-channel user, or while co-optimizing a second beam. That is the exact ECBF machinery AEGIS already has, and it is a natural bridge from the dosimetry core because EMF-compliant RIS steering IS a dosimetry-plus-scattering problem. This is where the Q_re = (1-T0)/T0 Q_ab shared-eigenvector identity from `q_complement.tex` (prop:lock) becomes a product feature, not a curiosity: exposure-aware and scatter-optimal are the same eigenbasis, so an EMF-compliant RIS synthesizer falls out of the operator AEGIS already assembles.

---

## 4. Verdicts

### (A) Stealth / RCS / low-observable: CONDITIONAL, explorer not certifier, and business-gated

Strongest angle. Differentiable specular-shape exploration on smooth electrically-large bodies, with the free Q_re = Q_ab eigenvector duality thrown in. AEGIS can gradient-push a specular flash off-threat cheaply and end-to-end, and `fock.py` adds a validated creeping-wave term textbook PO lacks.

Biggest risk. Three independent kill shots. First, the physics: the low-RCS floor is set by edge/tip/traveling/cavity diffraction that A2 structurally omits, so AEGIS can explore but cannot certify, and `fock.py` closes the creeping gap for smooth convex bodies, i.e. the wrong shape class for faceted stealth. Second, the incumbents: differentiable specular RCS optimization is already published (Stealth Shaper, graphics) and the certifying tool (HFSS SBR+ with PTD/UTD) already carries the missing physics. Third, the market: ITAR/USML and EU dual-use controls plus multi-year defense procurement make this unreachable for a small EU spin-off in the near term.

What would have to be true. AEGIS would need a PTD/UTD fringe-current term and cavity multibounce to certify (a research program, not a rename), an export-control and clearance path, and a defense channel. None are close. As a standalone market I would call it OVERRATED. As a latent capability that rides for free on the dosimetry engine, CONDITIONAL. Do not build a business here now. Keep the Q_re-as-RCS result as a JSAC/sensing talking point, not a product.

### (B) RIS / reflectarray / metasurface: SOLID, conditional on the constrained-synthesis niche and an external unit-cell library

Strongest angle. Closed-form constrained aperture-synthesis QCQP, reusing `ecbf.py` verbatim, for the problem nobody ships in closed form: EMF-compliant RIS steering, multi-beam with interference nulls, exposure-capped scatter maximization. First-bounce is close to exact for a passive reflecting aperture's main beam, so A2 is honest here, and the Q_re eigen/QCQP is the right and cheap tool up to a few thousand elements.

Biggest risk. Two. The unit-cell dependency (local periodicity plus mutual coupling) owns the real design error budget and AEGIS is not in that layer, so the value proposition must be scoped explicitly to the array-factor layer above a bought-in Gamma library. And Sionna RT already ships free, NVIDIA-backed, differentiable, channel-aware RIS optimization, which eats the end-to-end version of the pitch. Vanilla beam steering is also a solved classical problem, so the value is thin unless it is the constrained/multi-objective case.

What would have to be true. The wedge has to be the constrained QCQP that classical synthesis and autodiff-through-RT do not give cheaply: exposure-aware steering, hard interference nulls, closed-form multi-beam, all faster than backpropagating through a ray tracer because the aperture-only problem is a single eigendecomposition. It must integrate with (not replace) an HFSS/CST/Feko or surrogate unit-cell library. If AEGIS positions as the fast closed-form constrained aperture-synthesis layer that bolts onto a customer's existing unit-cell solve and inherits EMF-compliance for free from the dosimetry core, the value survives the unit-cell dependency. If it positions as a general RIS design tool, Sionna and the full-wave vendors win. The aperture-synthesis value is real, but only in the constrained niche, hence SOLID and not STRONG-BET.

---

## Sources

- AEGIS internal: `theory/q_complement.tex` (Q_re def:Qref, prop:lock eigenvector locking, rem:ignored), `src/aegis/kernels/fock.py` (validated creeping-wave / Leontovich-Fock gate), `src/aegis/kernels/level6_diffraction.py`, `src/aegis/coherent/ecbf.py` (QCQP solver), `src/aegis/coherent/exposure_operator.py`.
- [Stealth Shaper: Reflectivity Optimization as Surface Stylization (arXiv 2305.05944, cs.GR)](https://arxiv.org/abs/2305.05944)
- [Ansys HFSS SBR+ / Savant (SBR + PO + PTD/UTD)](https://www.ansys.com/blog/new-hfss-sbr-technology-in-ansys-2021-r2), [SBR overview (Wikipedia)](https://en.wikipedia.org/wiki/Shooting_and_bouncing_rays)
- [Sionna RT: Differentiable Ray Tracing for Radio Propagation (arXiv 2303.11103)](https://arxiv.org/pdf/2303.11103), [Sionna RT 1.0 Technical Report (arXiv 2504.21719)](https://arxiv.org/pdf/2504.21719)
- [Deep-learning inverse design of large-scale metasurfaces with full-wave accuracy (arXiv 2512.12625)](https://arxiv.org/pdf/2512.12625), [Unit Cell Design for Aperiodic Metasurfaces (arXiv 2211.11588)](https://arxiv.org/pdf/2211.11588), [Physics-Informed DNN design of reactively loaded metasurfaces (arXiv 2603.15430)](https://arxiv.org/html/2603.15430)
- [Adjoint / differentiable shape optimization background (arXiv 2410.13074](https://arxiv.org/pdf/2410.13074), [2405.03930](https://arxiv.org/pdf/2405.03930), [1705.07188)](https://arxiv.org/pdf/1705.07188)
- [ITAR overview and small-business burden (Wikipedia)](https://en.wikipedia.org/wiki/International_Traffic_in_Arms_Regulations), [FD Associates ITAR small-business note](https://fdassociates.net/what-the-latest-itar-revisions-mean-for-small-businesses-september-2025/)
</content>
</invoke>
