# Deep-tissue volumetric heating: re-examining a killed topic

Scope: microwave/RF tumor ablation, RF/microwave hyperthermia treatment planning, and industrial RF/microwave heating. The prior verdict killed all of it on one sentence: "surface confinement fails below 6 GHz, so the spatial deposition map does not reduce to a surface and the 3D-to-2D speed trick dies." That sentence is correct. This report tests whether it kills the whole opportunity or only half of it.

Bottom line up front. The surface-speed miracle is genuinely dead here, and the physics below confirms it with centimeter-scale penetration at every therapeutic frequency. But the differentiable constrained-focusing planner rides on A1 (linearity of the field in the excitation) alone, and A1 is not just intact, it is the established daily workflow of the hyperthermia community. For deep regional phased-array hyperthermia the planning jewel transfers more cleanly than it does for HIFU, because this is EM (AEGIS home physics, not an acoustic port), the standard clinical metric is literally a ratio of two quadratic forms, and the incumbents still solve it with metaheuristics. I upgrade that one sub-application from DEAD to WORTH-A-SECOND-LOOK bordering REVIVE, and hold the rest at NICHE or DEAD.

## 1. The physics, quantitative

I model muscle as a lossy dielectric using Gabriel / IT'IS 4-Cole-Cole values for relative permittivity and conductivity, and compute the field penetration depth from the plane-wave attenuation constant. The attenuation constant is

    alpha = omega * sqrt( mu0 * eps' / 2 * ( sqrt(1 + (sigma/(omega eps'))^2) - 1 ) )   [Np/m]

with eps' = eps_r * eps0. The field penetration depth is d_field = 1/alpha (E-field falls to 1/e = 37%). The power / SAR penetration depth is d_pow = 1/(2 alpha) (SAR is proportional to E^2, so it falls to 1/e at half the field depth). I also report the in-medium wavelength lambda_med = 2 pi / beta, because it sets whether a body region is many wavelengths (tight focusing possible) or one to two wavelengths (focusing is soft and constrained).

Tissue properties used (muscle):

| Frequency | eps_r | sigma (S/m) | loss tan |
|-----------|-------|-------------|----------|
| 70 MHz    | 63.0  | 0.69        | 3.1      |
| 100 MHz   | 62.2  | 0.72        | 2.1      |
| 140 MHz   | 60.0  | 0.74        | 1.6      |
| 434 MHz   | 56.9  | 0.805       | 0.586    |
| 915 MHz   | 54.8  | 0.948       | 0.340    |
| 2.45 GHz  | 52.7  | 1.74        | 0.242    |
| 6 GHz     | 48.2  | 5.20        | 0.323    |
| 10 GHz    | 42.8  | 10.6        | 0.445    |
| 28 GHz    | 29.5  | 33.6        | 0.731    |

Computed penetration depths:

| Frequency | d_field (cm) | d_pow / SAR (cm) | lambda_med (cm) | regime |
|-----------|--------------|------------------|-----------------|--------|
| 70 MHz    | 8.62         | 4.31             | 38.2            | deep volume, regional HT band |
| 100 MHz   | 7.48         | 3.74             | 29.6            | deep volume |
| 140 MHz   | 6.66         | 3.33             | 23.1            | deep volume |
| 434 MHz   | 5.17         | 2.58             | 8.81            | deep volume, ISM |
| 915 MHz   | 4.20         | 2.10             | 4.37            | volume, ablation ISM |
| 2.45 GHz  | 2.23         | 1.12             | 1.67            | volume, ablation / industrial ISM |
| 6 GHz     | 0.72         | 0.36             | 0.71            | transition |
| 10 GHz    | 0.34         | 0.17             | 0.45            | surface returning |
| 28 GHz    | 0.09         | 0.05             | 0.19            | surface confined (AEGIS home) |

What this says. At every therapeutic frequency the SAR deposits over 1 to 4 cm of tissue depth. At the regional hyperthermia band (70 to 140 MHz, the Sigma-Eye / Sigma-60 operating range) the field reaches 6 to 9 cm deep, which is the entire point of that band: you want to heat a pelvic tumor 10 to 15 cm inside the body. The skin depth is not sub-millimeter, so the deposition is a genuine 3D volume field and there is no surface to integrate over. A3 (surface confinement, the 3D-to-2D reduction) is dead at these frequencies, full stop. It only comes back at 10 to 28 GHz, where d_pow drops to 0.5 to 1.7 mm and the surface trick is exactly AEGIS home turf.

Crucially, A1 is untouched by any of this. The electric field at any interior point r is still a linear function of the array excitation vector x, E(r) = sum_n x_n g_n(r), where g_n(r) is the field per unit excitation of element n (the "per-channel basis field"). Loss and depth change what g_n(r) looks like, they do not break the superposition. So the mean SAR over any region R,

    P_R(x) = integral_R (sigma/(2 rho)) |E(r)|^2 dV = x^H Q_R x,   Q_R = integral_R (sigma/(2 rho)) g(r) g(r)^H dV,

is still a Hermitian PSD quadratic form. The only thing that changed from AEGIS surface dosimetry is that Q_R is now a volume Gram matrix instead of a surface Gram matrix, and its entries g_n(r) come from a volume field model rather than a cheap Fresnel-on-mesh evaluation. The Q-calculus, the identity structure, and the QCQP/eigen planner are all structurally identical. This is the whole argument, and the physics supports it exactly.

## 2. The application landscape and whether the planning problem is real

### 2a. Deep regional RF/microwave hyperthermia (the strong case)

The Pyrexar (ex-BSD) Sigma-Eye applicator is 24 dipole antennas in three rings of eight, driven by 12 RF channels at 70 to 140 MHz, and treatment is delivered by choosing the per-channel phase and amplitude to steer the SAR focus onto a deep tumor while sparing healthy tissue and, in practice, while respecting patient-reported hot-spot pain. Stated abstractly: choose x (12 complex weights) to maximize tumor SAR subject to healthy-region SAR bounds. That is ECBF on a volume, verbatim.

The metric the field actually optimizes makes the fit even tighter than I expected. The standard objective is HTQ, the hotspot-to-target quotient, defined as the ratio of the mean SAR in the top 1% hottest healthy tissue to the mean SAR in the tumor. Both numerator and denominator are region-mean SARs, so both are quadratic forms x^H Q x. HTQ is therefore a ratio of two quadratic forms,

    HTQ(x) = (x^H Q_hotspot x) / (x^H Q_tumor x),

which is a generalized Rayleigh quotient. Minimizing it is a generalized eigenvalue problem, solved in closed form as the smallest generalized eigenpair of (Q_hotspot, Q_tumor). This is precisely AEGIS's eigen route, and it is precisely the ECBF/QCQP jewel. The planning problem here is not merely analogous to what AEGIS does. In its dominant metric it is the same mathematical object.

Is it underserved on the differentiability axis? Yes, meaningfully. From the literature the current optimizers are metaheuristic: differential evolution, particle swarm, genetic algorithms, and time reversal (Iero et al.; the breast-heating DE study on a 36-element array compares DE, TR, PSO, and GA over 200 iterations with 50 restarts). These are global stochastic searches over a problem whose dominant metric has a closed-form eigen solution and whose constrained form is a QCQP. Metaheuristics on a QCQP is exactly the inefficiency the AEGIS planner erases. The frontier is already moving this way (a 2025 "local power synthesis algorithm" paper explicitly offers a "fast deterministic alternative to meta-heuristic methods," and a 2018 Phys Med Biol paper studied "constrained SAR focusing" for head and neck), so AEGIS would not be first to notice that metaheuristics are the wrong tool, but the closed-form differentiable operator formulation is not the standard, and no one is selling a differentiable constrained-focusing layer as a product.

One honest strengthening point on the forward model. AEGIS cannot compute the volume basis fields g_n(r) below 6 GHz. That needs an FDTD or FEM solve (Sim4Life, COMSOL, CST, HFSS). But the hyperthermia community already precomputes exactly these per-channel E-field maps once per patient and then does phase-amplitude steering by superposition. AEGIS does not need to own the forward solve. It consumes the per-channel E-field library that the incumbent solver already produces, assembles the Q matrices (cheap once g_n are known), and returns the optimal x in closed form. So the value AEGIS adds is a differentiable planning layer riding on someone else's volume solve, which is precisely the "design-and-optimization layer above incumbent solvers" position from the generalization map. That the superposition step is already the community's standard practice means A1 is not a hopeful assumption here, it is the installed workflow.

A note on temperature. Clinicians ultimately care about temperature, not SAR, and metaheuristics are partly used because people optimize thermal endpoints. But steady-state Pennes bioheat with linear perfusion makes the temperature rise a linear response to the SAR source, so tumor and healthy-tissue temperatures are themselves quadratic forms of x (with a thermal-Green's-function-weighted kernel replacing sigma/(2 rho)). The QCQP structure survives the move from SAR to linear-bioheat temperature. It is only nonlinear thermoregulation (temperature-dependent perfusion) that breaks strict quadraticity, and that is a perturbation you would handle by re-linearizing and iterating, not a structural kill. This is a genuinely favorable surprise and worth stating in the room.

### 2b. Microwave/RF tumor ablation, 915 MHz / 2.45 GHz (the weak case)

Ablation is a different flavor. Penetration at 915 MHz and 2.45 GHz is 2 to 4 cm in field, but clinically ablation uses one or a few interstitial applicators inserted into the tumor, and the ablation zone is dominated by near-field heating plus thermal conduction over minutes, not by array beamforming. The planning problem, confirmed by the literature (NeuWave simulation software, the Tandf 2025 automated MWA parameter algorithm, the digital-twin MWA model), is geometric: where to place the antenna, at what angle, at what power and time, to cover the tumor with a 5 mm margin. Those planners translate and rotate antenna poses in 3D and run in about 5 minutes per case. There is no complex excitation vector x to solve a QCQP over. AEGIS's beamforming jewel does not grab here. A coherent multi-applicator array driven for interference focusing would recover a QCQP, but that is not the clinical practice and would be a research bet, not a market.

### 2c. Industrial RF/microwave heating, 915 MHz / 2.45 GHz multimode cavities (poor fit)

Industrial heating of food, drying, and plastics is done in multimode cavities. A2 (first bounce dominates) fails hard, because the whole design principle of a multimode cavity is many reflections and mode stirring. The objective is uniformity, not focusing, and the field is a cavity eigenmode superposition, not a physical-optics scatter. The field is still linear in the source excitation, so a formally quadratic uniformity objective exists, but the physics AEGIS is good at (PO surface scatter) is the wrong physics, and the market does not buy differentiable focusing planners. I see no fit here.

## 3. Incumbents and the differentiability gap

- Plan2Heat (Amsterdam UMC, C++/Linux) and its online-adaptive module Adapt2Heat are the academic reference planners, validated against the AMC-2, AMC-4/ALBA-4D, and Pyrexar Sigma-30 and Sigma-60 phased arrays. They predict SAR focus location and size from phase-amplitude settings.
- Sim4Life (ZMT / SPEAG, FDTD) has a thermal-therapies module that does automatic phase-amplitude optimization with multiple weighted treatment regions to maximize tumor coverage while sparing sensitive tissue. This is AEGIS's same first dosimetry customer, and it already ships the exact optimization AEGIS would improve. That makes this an extension of an existing relationship, not a cold new market.
- Sigma HyperPlan is Pyrexar's dedicated planner bundled with the BSD-2000.
- General EM solvers used for the forward solve: COMSOL, Ansys HFSS, CST.
- The optimizers on top are still largely metaheuristic (DE, PSO, GA, time reversal), with a live research push toward deterministic and deep-learning surrogates (a 2025 encoder-decoder net predicts head SAR in 4 seconds vs 10 minutes for FDTD).

The gap is real: the dominant metric (HTQ) has a closed-form generalized-eigen solution and the constrained problem is a QCQP, yet the shipping tools optimize it with stochastic global search or, at best, ad-hoc deterministic heuristics. A differentiable closed-form constrained-focusing layer that plugs into the per-channel E-field library from Sim4Life or COMSOL is a defensible, non-obvious product. The caveat is that the gap is being noticed by others, so this is a "move now" window, not an open field forever.

## 4. The honest split

Two claims, kept separate, per the generalization map's own instruction:

- Surface-speed claim (A2 + A3 + A4, the millisecond surface-mesh evaluator). DEAD across all three sub-applications. The physics in section 1 is unambiguous: penetration is 1 to 9 cm at every therapeutic frequency, there is no surface to reduce to, and AEGIS cannot compute the interior basis fields cheaply below 6 GHz. This must be conceded plainly.

- Differentiable constrained-focusing planning claim (A1 alone, the Q-calculus and ECBF/QCQP). ALIVE for deep regional hyperthermia, weak for ablation, dead for industrial heating. For hyperthermia it is not merely alive, it is the native mathematical form of the field's own standard metric, riding on a superposition workflow the community already uses.

Comparison to HIFU. HIFU was rated the strong survivor because A1 (the planner) transfers while A3 (the speed) dies. Deep regional RF/microwave hyperthermia is the same shape, and on three axes it is a better fit than HIFU:

1. Physics home. HIFU requires porting the whole engine from EM impedance to acoustic impedance. Hyperthermia is EM, the exact Maxwell-plus-tissue machinery AEGIS already has. Nothing to port on the physics side, only the Q assembly moves from surface to volume.
2. Metric match. The hyperthermia standard metric HTQ is literally a ratio of two quadratic forms, so AEGIS's eigen route drops in with no reframing. HIFU objectives are also quadratic but the field does not hand you a named generalized-Rayleigh-quotient metric on a plate.
3. Customer. ZMT/Sim4Life is AEGIS's first dosimetry customer and ships both an acoustics module (the HIFU hook) and a thermal-therapies hyperthermia module (this hook). Hyperthermia extends the same relationship into a product line ZMT already sells.

The one axis where hyperthermia is clearly worse than HIFU is market size. HIFU is a real commercial device market (Insightec, Profound Medical, EDAP, hundreds of millions to low billions). Deep phased-array regional hyperthermia is thin: the aggregate "hyperthermia devices" market figures from market-research sites lump in superficial applicators and oncothermia and are not a fair proxy. The deep phased-array segment is concentrated in a handful of academic centers (Amsterdam, Rotterdam, Munich, Duke and a few others), is reimbursement-challenged, and sits outside most oncology guidelines. So the planning problem is beautiful and underserved, but the addressable install base for a standalone planner is small.

Net: hyperthermia deserves at least the HIFU rating on physics and method fit, and arguably a cleaner transfer, discounted by a thinner market. It is best pursued as a module extension of the ZMT relationship and a credibility/publication play, not as a standalone revenue market.

## 5. Verdict

Graded by sub-application:

- Deep regional RF/microwave phased-array hyperthermia planning (Sigma-Eye / Plan2Heat / Sim4Life class): WORTH-A-SECOND-LOOK bordering REVIVE for the planning jewel. Surface speed DEAD, differentiable constrained-focusing planner ALIVE and unusually clean.
- Microwave/RF tumor ablation (915 MHz / 2.45 GHz interstitial): NICHE-PAPER-ONLY. It is a geometric placement and dose-time problem, not a beamforming QCQP. The Q-calculus does not grab unless someone builds a coherent multi-applicator array, which is a research bet.
- Industrial RF/microwave heating (multimode cavities): DEAD. A2 and A3 both fail, the objective is uniformity not focusing, and the physics is cavity-mode not physical optics.
- Surface-speed claim, all sub-applications: DEAD, confirmed by centimeter-scale penetration.

Strongest surviving angle. Deep regional hyperthermia treatment planning. The standard clinical metric HTQ is a ratio of two volume-Gram quadratic forms, so minimizing it is a generalized eigenproblem and the constrained version is AEGIS's ECBF QCQP verbatim. The incumbents (Plan2Heat, Sigma HyperPlan, and the research literature) still solve it with differential evolution, particle swarm, and genetic algorithms over a problem that has a closed-form solution. AEGIS supplies a differentiable closed-form constrained-focusing layer that consumes the per-channel E-field library the incumbent FDTD/FEM solver already produces, which is exactly how the field already superposes. And it extends AEGIS's existing ZMT/Sim4Life relationship, which already ships a hyperthermia module.

What would have to be true:
1. AEGIS accepts the per-channel volume E-fields from an external solver (Sim4Life, COMSOL) as its basis g_n(r), and does not attempt to compute them itself below 6 GHz. Own the optimizer, not the forward solve.
2. The thin deep-hyperthermia market is acceptable as a module-extension and credibility play rather than a standalone revenue line. If the goal is a large independent market, this is not it, and HIFU or dosimetry remain the bigger fish.
3. ZMT wants a differentiable closed-form planning layer for its thermal-therapies module, and the closed-form-eigen/QCQP advantage over its current optimizer is large enough in speed and reproducibility to matter clinically (online adaptive replanning during treatment is the obvious pull, since that is where metaheuristic wall-clock hurts and where Adapt2Heat already lives).

If those hold, this stops being a killed topic and becomes the EM-native sibling of the HIFU survivor.

## Sources

- Plan2Heat / phased-array validation: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11754364/ and https://link.springer.com/article/10.1007/s00066-024-02264-0
- Adapt2Heat online adaptive replanning: https://pubmed.ncbi.nlm.nih.gov/35109742/ and https://www.tandfonline.com/doi/full/10.1080/02656736.2022.2032845
- Robust on-line adaptive HTP (phase-amplitude steering under tissue uncertainty): https://www.tandfonline.com/doi/full/10.1080/02656736.2025.2483433
- Constrained SAR focusing (Phys Med Biol 2018, head and neck): https://iopscience.iop.org/article/10.1088/1361-6560/aaf0c4
- Differential Evolution vs TR/PSO/GA for microwave focused hyperthermia (36-element array, HTQ objective): https://pmc.ncbi.nlm.nih.gov/articles/PMC10144698/
- Local Power Synthesis Algorithm, deterministic alternative to metaheuristics (2025): https://pubmed.ncbi.nlm.nih.gov/40940909/
- Deep-learning SAR surrogate, 4 s vs 10 min: https://pmc.ncbi.nlm.nih.gov/articles/PMC12479143/
- Role of simulations in RF hyperthermia planning (Sim4Life, COMSOL, HFSS, CST context): https://ncbi.nlm.nih.gov/pmc/articles/PMC6735211
- Sim4Life thermal-therapies / hyperthermia module (ZMT): https://zmt.swiss/applications/thermal-therapies
- Pyrexar BSD-2000 / Sigma-Eye applicator and Sigma HyperPlan: https://www.pyrexar.com/hyperthermia/product-overview and https://www.pyrexar.com/hyperthermia/bsd-2000-3d
- Microwave ablation planning (geometric antenna placement, NeuWave, ~5 min/case): https://www.techvir.com/article/S1089-2516(18)30077-5/pdf and https://www.tandfonline.com/doi/full/10.1080/02656736.2025.2473391
- Tissue dielectric properties: Gabriel / IT'IS 4-Cole-Cole muscle values (IT'IS Foundation tissue database).
