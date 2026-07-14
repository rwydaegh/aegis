# Focused ultrasound (HIFU) treatment planning: does the ECBF machine transplant to acoustics?

Author: dispatched feasibility subagent
Date: 2026-07-06
Scope: pressure-test the claim that AEGIS's exposure-constrained beamforming (ECBF) transplants from EM dosimetry to acoustic therapy planning by swapping impedance. Grade honestly. Separate the clean part from the hard parts.

## One-paragraph answer

The planning jewel transplants. The acoustic pressure field is linear in the transducer excitation `x`, so the entire Q calculus and the ECBF QCQP survive the swap from the EM dyadic Green function to the acoustic scalar-pressure Green function, and the per-region sparing constraints that AEGIS already ships (`multibody_ecbf.py`, `x^H Q^(u) x <= L^(u)` per body) are exactly the rib, skull, skin, and nerve sparing structure that transcostal and transcranial HIFU need. That is the real, defensible claim. But three things are honestly true and must be stated up front. First, the millisecond surface-speed miracle is dead, because ultrasound penetrates and the target is a volume focus deep in tissue, so Q becomes a volume Gram matrix and the fast first-bounce surface evaluator does not apply. Second, constrained convex optimization for exactly this problem is not new to the field. The HIFU and RF-hyperthermia planning literatures already use semidefinite relaxation, QCQP, and per-region SAR constraints, so AEGIS is not inventing the category, it is offering a specific closed-form and differentiable instance of it. Third, the real clinical objective is thermal dose (CEM43), a time-integral of a nonlinear function of temperature, and the therapeutic focal field is genuinely nonlinear (MPa pressures, shock, boiling), so the QCQP on absorbed power is a linear planning proxy that needs an outer thermal-and-nonlinear validation loop. Grade below.

## 1. The physics transplant, made honest

### What swaps cleanly

The EM-to-acoustic dictionary for the linear layer:

- Dyadic Green function `G_tilde(r)` in C^{3 x M_ant} (three field components) becomes the acoustic scalar-pressure Green function `g(r)` in C^{1 x M_ant} (one pressure component). The field is `p(r) = g(r) x`.
- Wave impedance becomes the acoustic characteristic impedance `Z = rho c` (about 1.5 MRayl for soft tissue, versus 377 ohm for free space in EM).
- Absorbed power density becomes acoustic absorption. Time-averaged intensity is `I = |p|^2 / (2 rho c)` and the local volumetric heat deposition is `q(r) = 2 alpha(r) I(r) = alpha(r) |p(r)|^2 / (rho c)`, where `alpha` is the pressure absorption coefficient and is frequency dependent (roughly linear in frequency for soft tissue).

Now the operator. In AEGIS the exposure operator is built in `exposure_operator.py` as

```
Q = sum_m area_m * G_tilde[m]^H @ G_tilde[m]        # surface integral, EM
```

The acoustic analogue is structurally identical, a Gram matrix, but the integral is over a VOLUME and carries the absorption weight:

```
Q_ac = sum_v (vol_v * alpha_v / (rho c)) * g[v]^H @ g[v]     # volume integral, acoustics
```

`Q_ac` is Hermitian positive-semidefinite by construction, exactly like the EM Q, because it is a weighted sum of rank-1 outer products with nonnegative weights. Total absorbed power in a region is `P_abs = x^H Q_ac x`, the same quadratic form. Everything downstream of Q in `ecbf.py` and `multibody_ecbf.py` (the eigendecomposition, the Lagrange bisection or Newton dual ascent, the closed-form `x* = (lambda Q + nu I)^{-1} h*`) is agnostic to whether Q came from a surface EM integral or a volume acoustic integral. It just needs a Hermitian PSD matrix and a target vector.

Verdict on the solver: this is a CHANNEL SWAP, not a rewrite, for the sparing constraints. Feed `solve_ecbf` an acoustic h and an acoustic Q and it runs unchanged. The one genuine generalization needed is the objective, discussed next.

### The one real code change: rank-1 focus to volume-target objective

The shipped `solve_ecbf` maximizes `|h^T x|^2`, a rank-1 objective. That is a single focal point, `h` being the transducer-to-focus channel vector. HIFU frequently wants a target VOLUME (a tumor), which is either swept as many single points (electronic steering, one `solve_ecbf` call per point, already supported) or expressed directly as a quadratic objective `x^H Q_tgt x` where `Q_tgt` is the target-region Gram matrix. Maximizing a quadratic subject to a quadratic constraint is the same QCQP FAMILY, solved by a generalized eigenproblem or the same SDR the field already uses. The shipped code does not do the `x^H Q_tgt x` objective directly (its objectives are rank-1 focus power and log-SINR sum-rate), so this is a modest, well-posed extension inside the existing machinery, not a new theory. `multibody_ecbf.py` already carries the multi-region per-body absorbed-power budgets `x^H Q^(u) x <= L^(u)`, which is precisely the rib-plus-skull-plus-skin sparing set. That half is done.

### (a) Skull aberration for transcranial HIFU: where it sits

The skull is the hardest part of transcranial focusing. It introduces strong phase distortion, refraction, absorption, and mode conversion of the incident longitudinal wave into shear waves in bone. Crucially, none of this breaks linearity. For a KNOWN skull (segmented from CT, with density and sound-speed maps), the map from transducer drive `x` to the pressure field anywhere in the brain is still a linear operator. The aberration is fully baked into the channel `h` and the operator `Q`. So aberration does not touch the QCQP at all. It sits ENTIRELY inside the computation of h and Q.

What it does kill is the analytic Green function. You cannot write h and Q in closed form through an aberrating heterogeneous skull. You must compute them with a full-wave heterogeneous solver (k-Wave, Sim4Life, Stride, or a boundary-integral or hybrid-angular-spectrum method) once per patient geometry, then hand the resulting h and Q to ECBF. This is the same posture AEGIS already takes for realistic bodies, where it swaps analytic paths for a ray-traced or full-wave channel. So the honest statement is: AEGIS does not solve skull aberration, the full-wave forward solver does, and AEGIS consumes its output. The differentiator is not aberration correction (the field has many methods for that, from time reversal to deep learning) but what you do with the channel once you have it, namely a closed-form constrained optimum rather than a heuristic.

### (b) Nonlinear acoustics at the focus: this breaks A1 locally

At therapeutic focal intensities the field is nonlinear. Harmonics are generated, shocks form, and at the extreme end boiling and cavitation occur. This VIOLATES the linear-superposition assumption A1 at the focus. The nonlinearity is not in the transducer-to-field channel (that stays linear for the planning-level drive) but in the field-to-field self-interaction at high amplitude, governed by the Westervelt or KZK equations, not the linear Helmholtz equation.

The honest split: AEGIS's QCQP optimizes a LINEAR field computed at a reference drive amplitude. It gives you the optimal phase-and-amplitude PATTERN (the shape of `x`), which is largely amplitude-invariant in the linear regime. You then scale the drive to therapeutic power and validate the actual deposited heat with a nonlinear forward simulation (Westervelt or KZK) plus a thermal solve. So nonlinearity does not break the planner, it breaks the interpretation of the planner's objective as the true deposited dose. It demands an outer validation loop. See the light calculation in section 2 for where nonlinearity starts to bite.

### (c) Thermal dose (CEM43) is the real objective, and it needs an outer loop

The clinical endpoint is not instantaneous absorbed power. It is the thermal dose, expressed as cumulative equivalent minutes at 43 C (CEM43), computed by integrating a nonlinear (Arrhenius-like, `R^(43-T)`) function of the temperature history. The temperature history itself comes from the Pennes bioheat equation, which adds heat conduction and a perfusion sink term to the acoustic heat source `q(r) = alpha |p|^2 / (rho c)`. Ablation requires roughly CEM43 of 240 minutes, and the tissue between the transducer and the focus must stay below damage thresholds.

So `x^H Q x` (instantaneous absorbed power in a region) is a PROXY for the true objective. It is a good proxy, because absorbed power is the source term that drives the whole thermal chain, and minimizing absorbed power on ribs or skull is exactly what keeps those structures under their thermal limit. But the exact clinical objective is a time-integral of a nonlinear function of a PDE solution, which is not a quadratic form in `x` and cannot be. The clean architecture is a two-level loop: the inner level is the AEGIS closed-form QCQP that gives an optimal `x` for the absorbed-power surrogate in milliseconds-to-seconds (fast because closed-form given the channel), and the outer level runs Pennes plus CEM43 on the resulting field and adjusts the per-region budgets `L^(u)` and the target until the thermal dose map is clinically acceptable. This is exactly how RF-hyperthermia planning (Plan2Heat and similar) already works, with SAR optimization inside and a temperature check outside.

### Summary of the honest split

| Physics reality | Does AEGIS handle it? |
|---|---|
| Linear pressure field, `p = g x` | Yes, cleanly. This is the A1 core. |
| Constrained focusing (max target, spare ribs/skull/skin/nerves) | Yes. `multibody_ecbf.py` per-region budgets are exactly this. |
| Volume-target objective `x^H Q_tgt x` | Modest extension, same QCQP family, not shipped. |
| Skull aberration | Not AEGIS. Lives in the full-wave forward solver that computes h and Q. Linear, so QCQP unchanged after. |
| Nonlinearity at focus (shock, harmonics, boiling) | No. Breaks A1 at the focus. Needs an outer nonlinear (Westervelt/KZK) validation. |
| Thermal dose CEM43 | No. Needs an outer Pennes-plus-CEM43 loop. AEGIS's `x^H Q x` is the surrogate driving it. |
| Millisecond surface-speed | Dead. Volume Gram matrix, no first-bounce surface confinement. |

## 2. Light calculations

Tissue and acoustic property values used: sound speed in soft tissue `c = 1540 m/s`, density `rho = 1000 kg/m^3`, characteristic impedance `Z = rho c = 1.54e6 Rayl = 1.54 MRayl`, bulk modulus proxy `rho c^2 = 2.37e9 Pa`, pressure absorption coefficient `alpha_0 approx 0.5 dB/cm/MHz = 0.0576 Np/cm/MHz`, nonlinearity coefficient `beta = 1 + B/2A approx 4` (B/A about 6 to 7 for soft tissue).

### Wavelength

`lambda = c / f`.

- 1 MHz (typical body HIFU): `lambda = 1540 / 1e6 = 1.54 mm`.
- 1.5 MHz: `lambda = 1.03 mm`.
- 650 kHz (common transcranial): `lambda = 1540 / 650e3 = 2.37 mm`.
- 250 kHz (deep transcranial neuromodulation): `lambda = 6.16 mm`.

These are sub-centimeter, so the focal region and the target are resolved on a millimeter grid, but the beam PATH from transducer to focus is many centimeters. The mismatch between a millimeter focus and a decimeter path is the whole point of the volume-Gram argument below.

### Absorption over a focal depth (A3 is dead)

One-way pressure attenuation over path length `L` at frequency `f`:  `p/p0 = exp(-alpha_0 f L)` with `alpha_0 = 0.0576 Np/cm/MHz`.

At 1 MHz over a 10 cm liver-depth path: exponent `= 0.0576 * 1 * 10 = 0.576`, so `p/p0 = exp(-0.576) = 0.562`, and intensity `I/I0 = (p/p0)^2 = 0.316`. About 68 percent of the beam intensity is deposited along the 10 cm path, NOT at a surface. That deposited energy is spread through the entire intervening volume of skin, fat, muscle, and any ribs in the window. This is the concrete statement that A3 (surface confinement) does not hold. The healthy-tissue exposure operator Q is a genuine volume integral over the beam corridor, and there is no first-bounce surface on which to run the fast evaluator. The ms-speed miracle is gone. What survives is the closed-form-given-the-channel property, which still makes the OPTIMIZATION step fast once the (expensive) volume channel is computed.

### Focal-spot size (a volume focus, not a surface patch)

For a focused aperture of diameter `D` and focal length `F`, F-number `Fn = F/D`. Lateral full width at -6 dB and axial length:

`w_lat approx lambda * Fn`,  `L_ax approx 7 * lambda * Fn^2`.

Representative body HIFU: `f = 1 MHz` (`lambda = 1.54 mm`), `D = 12 cm`, `F = 12 cm`, so `Fn = 1`.
- `w_lat approx 1.5 mm`, `L_ax approx 10.8 mm`. Focal ellipsoid volume `approx (pi/6) * 1.5 * 1.5 * 10.8 approx 13 mm^3`, a millimeter-scale cigar sitting centimeters deep.

Transcranial: `f = 650 kHz` (`lambda = 2.37 mm`), hemispherical array `Fn approx 1`: `w_lat approx 2.4 mm`, `L_ax approx 17 mm`. The focus is a small deep volume, the target is a volume, and the sparing structures (skull, ribs) are extended surfaces the beam must cross. Everything is volumetric. This is the acoustic reality that removes surface confinement and confirms the volume-Gram regime.

### A1 holds at planning intensities, and where nonlinearity starts

Intensity from pressure: `I = p^2 / (2 rho c)`, `2 rho c = 3.08e6`.
- `p = 0.5 MPa`: `I = (5e5)^2 / 3.08e6 = 8.1e4 W/m^2 = 8.1 W/cm^2`.
- `p = 1 MPa`: `I = 32.5 W/cm^2`.
- `p = 5 MPa` (therapeutic focal peak): `I = 811 W/cm^2`.

Nonlinearity onset via the shock parameter over a path `x`: `sigma = beta * epsilon * k * x`, with acoustic Mach number `epsilon = p / (rho c^2)` and wavenumber `k = 2 pi / lambda`. At 1 MHz, `k = 4080 /m`. `sigma = 1` marks the onset of full shock.

- `p = 1 MPa`: `epsilon = 1e6 / 2.37e9 = 4.2e-4`. Over `x = 5 cm`: `sigma = 4 * 4.2e-4 * 4080 * 0.05 = 0.34`. Harmonics are present but no fully developed shock.
- `p = 3 MPa`: `sigma approx 1.0` over 5 cm. Shock forming.
- `p = 5 MPa` and above: fully shocked, plus boiling and cavitation regimes.

Conclusion: below roughly 0.5 to 1 MPa (intensity below about 8 to 30 W/cm^2), the field is quasi-linear and A1 holds well, so the transducer-to-field channel and Q are accurate and amplitude-invariant. Diagnostic and planning-level fields live here. Therapeutic focal fields at several MPa and hundreds of W/cm^2 are firmly nonlinear. So the correct workflow is: compute the linear channel and run the QCQP at planning level to get the optimal PATTERN, then scale up and validate the nonlinear deposited dose. This matches the honest split in section 1.

## 3. Incumbents and the differentiability gap

### Forward-simulation incumbents

- k-Wave (open-source, pseudospectral k-space time-domain, MATLAB and C++/CUDA) is the dominant academic acoustic solver and the de facto standard for transcranial simulation. It was the reference in the transcranial benchmark intercomparison of compressional-wave models (PMC9553291).
- Sim4Life (ZMT), which is AEGIS's SAME first dosimetry customer, already has an acoustics and ultrasound module. Its documentation describes a multi-GPU FDTD acoustic solver supporting both the linear acoustic pressure wave equation and the nonlinear Westervelt-Lighthill equation (dispersion and frequency mixing), validated for transcranial focused ultrasound, with a coupled thermal solver for HIFU ablation. This is the single most strategically important fact in this report and I return to it in section 4.
- Ansys via OnScale (acoustics/piezo) and Stride and j-Wave (JAX-based, differentiable) round out the solver landscape.

### Clinical HIFU planning incumbents

- Insightec Exablate: MR-guided focused ultrasound, FDA-cleared for essential tremor and Parkinson tremor (transcranial thalamotomy), the leading transcranial neuro platform. Planning is done on the Exablate workstation from MR images with a CT-derived skull correction.
- Profound Medical Sonalleve MR-HIFU and TULSA-PRO: 256-channel individually programmable amplitude-and-phase transducer, CE-marked for bone-metastasis pain palliation, TULSA cleared for prostate.
- EDAP Ablatherm/Focal One: 510(k)-cleared for prostate ablation (2015).

These all pair a phased-array transducer with MR or ultrasound guidance and a planning workstation that computes phase-amplitude settings.

### Is the optimization already gradient-based or closed-form? The honest read

This is the crux, and the answer is nuanced and NOT fully in AEGIS's favor.

What the field uses today:
1. Time reversal / phase conjugation is the workhorse for aberration correction and single-focus steering. It is fast and physically motivated but it is a HEURISTIC for the constrained problem. It focuses at the target but does not, by itself, minimize energy on ribs or skull, and its wavefront sampling causes forward-reverse mismatch (noted in the transcostal literature).
2. Constrained convex optimization for exactly the rib-sparing and skull-sparing problem ALREADY EXISTS in the literature. The transcostal work recasts refocusing as an iterative sparse semidefinite-relaxation problem (Researchgate 322561265) and reports a 50 percent reduction in peak rib-surface pressure for only a 4 percent focal-pressure loss versus plain spherical focusing (IOPscience 0031-9155/57/24/8471). The RF-hyperthermia community solves the same shape of problem, maximizing target SAR subject to healthy-tissue SAR constraints, as an SDP/QCQP to global optimality on human voxel models (PMC7281622, "Constrained Radiofrequency Induced Hyperthermia"), and Plan2Heat is a deployed phased-array planning system doing SAR optimization with a temperature check.
3. Gradient descent and differentiable solvers are an active and growing area. There is gradient-descent optimization of acoustic holograms for transcranial FUS (arXiv 2401.14756), j-Wave is an explicitly differentiable wave solver, JAX-BEM does gradient-based acoustic shape optimization, and deep-learning aberration correction is a 2025 hot topic (multiple Ultrasonics and iRADIOLOGY reviews).

So the differentiability gap is REAL but PARTIAL, and this is the most important honest correction to the internal thesis. AEGIS's actual moat elsewhere (per the patent-landscape memo) is the differentiable design loop, not the physics. In HIFU the story is weaker than in the EM/base-station case, because (a) constrained convex optimization for rib and skull sparing is already published and in some cases deployed, and (b) differentiable acoustic solvers already exist. What is genuinely thinner in the field is a CLOSED-FORM, per-region-constrained QCQP that is fast enough to sit inside an interactive planner and be re-solved instantly as the clinician drags budgets, together with a differentiable end-to-end pipeline from transducer geometry to thermal dose. AEGIS has the closed-form constrained-focusing kernel today. That is a real and specific contribution, but it is an improvement on an occupied field, not an empty one.

## 4. Strategic angle

The strongest strategic fact is the ZMT/Sim4Life overlap. Sim4Life is simultaneously AEGIS's first dosimetry customer AND already ships an acoustics-plus-ultrasound-plus-thermal module aimed at HIFU. This is a double-edged sword and I want to be honest about both edges.

The upside: it means the extension does not require a new customer relationship, a new sales motion, or a new validation partner. The same conversation with ZMT that covers EM dosimetry can cover "we have a closed-form, differentiable constrained-focusing planner that plugs on top of your existing acoustic forward solver." AEGIS would not compete with Sim4Life's forward solver, it would consume its pressure fields (h and Q) and add the optimization layer. This moves AEGIS from safety-compliance (a cost center that regulators force on device makers) toward therapy planning (a value center that hospitals and device makers pay for because it directly improves outcomes and treatment time). That is a genuinely better place to sell from.

The downside, and it is real: ZMT already OWNS the forward acoustic solver and the thermal solver, which are the expensive, defensible assets. AEGIS would be contributing the optimization kernel, which as section 3 shows is a known category. If the value is "closed-form constrained QCQP on top of your fields," ZMT can plausibly build that themselves or license it cheaply, because they have the physics and the customer. AEGIS's leverage is strongest if it brings the DIFFERENTIABLE END-TO-END loop (transducer layout and drive to thermal dose, with gradients) rather than just the per-solve optimizer, because the differentiable-design story is where the patent moat lives and it is harder to reproduce than a single QCQP solve.

The regulatory reality is the hard gate and it is categorically different from EDA licensing. Clinical treatment-planning software that computes the delivered dose is a regulated medical device (Software as a Medical Device, and specifically it drives an ablation, so it is high-risk). That means IEC 62304 software lifecycle, ISO 13485 quality system, clinical validation, and FDA 510(k) or PMA and EU MDR CE marking, on a multi-year timeline with real cost. This is a completely different and much slower path than shipping an EDA plug-in to a simulation vendor. There are two ways to live with this. Path A, the near-term one, positions the tool as RESEARCH software and a planning AID (not the dose-of-record), sold to academic FUS labs and to device makers' R and D teams, which sidesteps the device classification. Path B, the long-term one, embeds the kernel inside a partner (ZMT, Insightec, Profound) who already carries the regulatory apparatus, so AEGIS is a component supplier and the partner owns the clearance. Path B is the realistic route to clinical revenue and it depends entirely on the partner relationship, which loops back to the ZMT double-edge above.

## 5. Verdict

I grade this by sub-application, because they do not deserve the same grade.

- Linear constrained-focusing QCQP as a research and planning-aid tool (transcostal liver, and general body HIFU): SOLID. The transplant is clean on A1, the per-region sparing constraints are already shipped, the volume-target objective is a modest extension, and there is a real (if partial) gap for a fast closed-form differentiable optimizer. The near-term, non-regulated research-software route is reachable through the existing ZMT relationship. This is the part to build.

- Transcranial neuromodulation and transcranial ablation planning: CONDITIONAL. The QCQP is unchanged and correct once you have the channel, but the value depends entirely on a high-quality full-wave heterogeneous channel through the aberrating skull, which AEGIS does not own and must consume from k-Wave or Sim4Life, and the field is crowded with time-reversal, gradient, and deep-learning aberration methods. AEGIS adds the constrained optimum on top, which is real but incremental.

- Clinical dose-of-record treatment planning (the value-center dream): CONDITIONAL bordering on a long game. The physics proxy (absorbed power to CEM43) requires an outer thermal-and-nonlinear loop that AEGIS does not have today, and the medical-device regulatory path is slow and expensive and only realistic embedded inside a cleared partner.

Overall single grade if forced to one: SOLID, not STRONG-BET. The internal "strongest surprise survivor" framing overstates the physics novelty a notch, because constrained convex optimization for rib and skull sparing already exists in print and differentiable acoustic solvers already exist. It is not overrated as an opportunity, the market and the ZMT overlap are real, but it is overrated if the pitch is "we invented constrained acoustic focusing." The honest pitch is "we have a closed-form, differentiable, per-region-constrained focusing kernel that drops onto an existing acoustic forward solver and re-solves instantly."

Strongest angle: the ZMT/Sim4Life overlap. Same first customer, they already have the acoustic and thermal forward solvers, and AEGIS's closed-form constrained-focusing plus differentiable-design layer plugs directly on top, moving AEGIS from cost-center compliance to value-center therapy planning without a new sales motion. Ship the linear constrained QCQP with a volume-target objective and a per-region sparing set as a research planning aid first.

Biggest risk: the differentiability-and-optimization moat is thinner here than in EM. The rib-sparing SDP/QCQP and the RF-hyperthermia constrained-SAR optimizer and j-Wave-style differentiable solvers already exist, so a savvy incumbent (including ZMT itself) can reproduce the per-solve optimizer. The defensible position is only the full differentiable end-to-end loop, not the single QCQP. Second risk, slower but harder: clinical dose-of-record software is a regulated medical device on a multi-year path, so real clinical revenue requires embedding inside a cleared partner.

What would have to be true for STRONG-BET: (1) AEGIS delivers the differentiable end-to-end pipeline (transducer geometry and drive to CEM43, with gradients) not just the per-solve QCQP, so the moat is the design loop and not the optimizer, and (2) ZMT commits to integrating AEGIS as the optimization layer on top of Sim4Life acoustics rather than building it in-house, and (3) the near-term product is scoped as research and planning-aid software to avoid the medical-device gate while the clinical path matures through a partner.

## Sources

- ECBF QCQP formulation and shipped solver: `src/aegis/coherent/ecbf.py`, `src/aegis/coherent/exposure_operator.py`, `src/aegis/coherent/multibody_ecbf.py` (per-region `x^H Q^(u) x <= L^(u)` budgets), `papers/coherent-exposure-operator/paperC.tex`, `theory/exposure_null_precoding.tex`.
- Transcostal constrained optimization for rib sparing: [Optimization of transcostal phased-array refocusing using iterative sparse semidefinite relaxation](https://www.researchgate.net/publication/322561265), [Optimization of acoustic fields for ablative therapies in the upper abdomen (IOPscience)](https://iopscience.iop.org/article/10.1088/0031-9155/57/24/8471), [Simulation of transrib HIFU propagation and phased-array activation (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S1875389215009803).
- Transcranial focusing and aberration correction: [Benchmark problems for transcranial ultrasound simulation (k-Wave intercomparison)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9553291/), [Gradient descent optimization of acoustic holograms for transcranial FUS](https://arxiv.org/html/2401.14756), [Systematic review of phase aberration correction algorithms (iRADIOLOGY 2025)](https://onlinelibrary.wiley.com/doi/full/10.1002/ird3.112), [Transcranial phase correction using hybrid angular spectrum (Sci Rep)](https://www.nature.com/articles/s41598-021-85535-5), [Time-reversal transcranial focusing using a k-space method (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3366238/).
- Differentiable acoustic solvers: [j-Wave / End-to-end sparse ultrasound probe optimization](https://arxiv.org/pdf/2603.29014), [JAX-BEM gradient-based acoustic shape optimization](https://arxiv.org/pdf/2604.21431), [Ultrasound autofocusing via differentiable beamforming](https://arxiv.org/pdf/2410.03008).
- RF-hyperthermia constrained optimization analog: [Solving the constrained RF-induced hyperthermia problem (PMC7281622)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7281622/), [Validation of phased-array heating in Plan2Heat](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11754364/), [Field and temperature shaping for microwave hyperthermia](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10000666/).
- Thermal dose and bioheat: [Relationship between Arrhenius models and CEM43 thermal dose](https://www.researchgate.net/publication/252808677), [Integrating temperature-dependent tissue properties into FUS planning (Int J Hyperthermia 2025)](https://www.tandfonline.com/doi/full/10.1080/02656736.2025.2606701).
- Incumbent forward solver (ZMT): Sim4Life acoustics module description (multi-GPU FDTD, linear LAPWE and nonlinear Westervelt-Lighthill, transcranial-validated, coupled thermal) as reported in the [computational feasibility study using Sim4Life](https://arxiv.org/pdf/2507.05702).
- Clinical HIFU systems and regulatory status: [ExAblate transcranial MRgFUS for essential tremor (clinicaltrials protocol)](https://cdn.clinicaltrials.gov/large-docs/04/NCT01827904/Prot_000.pdf), Profound Sonalleve MR-HIFU (256-channel, CE-marked bone-metastasis pain palliation), EDAP Ablatherm 510(k) prostate clearance (2015), as summarized across the [HIFU planning search results](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4265975/).
