# Differentiable radiative heat transfer and view-factor design: re-examining the kill

Topic: differentiable radiative heat transfer / view-factor optimization as an AEGIS generalization vertical. Applications in scope: spacecraft thermal design, building facade solar-gain and inter-building shading, furnace and receiver design, concentrated-solar heliostat fields, bifacial-PV yield.

Status of this document: a re-examination of an earlier KILL verdict. The first pass was enthusiastic. The second pass killed it on the grounds that "differentiable rendering (Mitsuba 3, nvdiffrast) already does differentiable radiative transport, and view factors are ancient and commoditized, so AEGIS brings nothing new." My job here is to stress-test that kill with physics and real toolchain research, and to grade it honestly.

## TL;DR

- Verdict: **WORTH-A-SECOND-LOOK**, but narrowly. The blanket kill was reasoning from a category error. The corrected conclusion is not "revive across the board" and not "dead," it is "one vertical survives."
- The kill's premise is wrong on the facts. Differentiable, adjoint-style radiative design is **not** shipped in the engineering thermal toolchain that spacecraft, building, and solar engineers actually use. It lives almost entirely in graphics research (Mitsuba/Dr.Jit) and in one-off academic prototypes (openMDAO, level-set adjoint papers). No spacecraft thermal engineer is going to rebuild a certified ESATAN model inside a path tracer, so "Mitsuba already does it" does not close the engineering gap.
- But the kill's conclusion is roughly right for most verticals for a **different** reason than the one given: low design-variable counts (so finite difference is fine), certification moats, and entrenched heuristic/GA incumbents. The gap is real but usually not worth closing.
- Single best beachhead: **concentrated-solar heliostat field layout**. It is the one place where the design-variable count is genuinely large (thousands of continuous coordinates), the objective is smooth in geometry, the incumbent (SolarPILOT) is pattern-and-parametric rather than gradient-based, and AEGIS's exact core primitive (ReLU cosine visibility plus ambient occlusion) is literally the shading-blocking-cosine efficiency of a heliostat field.
- Biggest risk: the CSP market is small and slow-growing versus PV, so even a clean technical win lands in a modest TAM, and the published gradient-based heliostat methods already exist without having displaced the heuristic incumbent, which tells me the market friction is real.

## 1. The physics fit, quantitative

Radiative heat transfer is the friendliest possible regime for the AEGIS core, more so than the EM-dosimetry problem AEGIS was built for. The assumption ladder lands almost entirely on the good side.

**A3 (surface confinement) is free.** Radiative exchange between opaque surfaces is natively a surface-to-surface power-exchange problem. There is no 3D-to-2D reduction to justify, the problem is already 2D-on-boundaries. AEGIS's whole architecture (per-element local interaction, integrate over the surface) is the natural discretization, not an approximation.

**A5 (scalar collapse) transfers for the wrong reason but still transfers.** The pseudo-Brewster tissue collapse does not carry over, but it does not need to. Emissivity in engineering thermal is routinely treated as a scalar per surface (graybody, diffuse), which is exactly the role AEGIS's transmission constant `T0` plays. The monograph is explicit about this. In `theory/monograph_v2.tex` line 1076: "This is the emissive view-factor formula of radiative heat transfer, with `T0` replacing emissivity." So the AEGIS view-factor engine already *is* a graybody radiative-exchange engine, and Kirchhoff's law (absorptivity equals emissivity) is precisely the AEGIS absorption-emission duality.

**A1 (linear superposition) is where the whole Q-calculus travels, and radiative exchange satisfies it strongly.** The radiosity balance is a linear system in the emissive sources. With radiosity `B_i = E_i + rho_i * sum_j F_ij B_j`, in matrix form `(I - R F) B = E`, so `B = (I - R F)^{-1} E`, linear in the driving emissive powers `E`. A matrix inverse is differentiable. Net exchange between surfaces `i` and `j` runs through the Gebhart total-exchange-factor matrix acting on the emissive-power vector `e = sigma T^4`, and net heat is a bilinear form `e^T G e` in that vector. That is exactly the Hermitian quadratic-operator structure `x^H Q x` the AEGIS Q-calculus is built around. So the closed-form operator algebra maps over cleanly onto radiative exchange.

**A2 (first bounce dominates) is where it bites, and AEGIS already has the fix.** Pure single-bounce view factors miss interreflection. A real enclosure (a satellite bay, a furnace, the gap between heliostats and the receiver) needs the radiosity interreflection solve. That solve is the `(I - R F)^{-1}` above, still linear, still differentiable, so A2 does not break A1. And AEGIS's own monograph already derived the interreflection correction as a scalar recapture factor. From `monograph_v2.tex` eq:radiosity-C: summing the geometric series of bounces gives an enhancement `C(f) = 1 / (1 - Rbar * f)`, where `f` is the fraction of reflected power recaptured by the body and `Rbar` is the flux-weighted reflectance. The recapture fraction is bounded by `f <= 1 - eta`, i.e. it is one minus the exposure fraction, which is the diffuse view-factor interreflection term by another name. So the multi-bounce radiosity closure is not net-new physics for AEGIS, it is a quantity the monograph already writes down. The engineering version just needs the full matrix solve rather than the scalar body-averaged version AEGIS ships today.

**The temperature nonlinearity is an outer coordinate change, not a QCQP-breaker.** Radiative exchange is linear in the emissive-power sources `e` but `e = sigma T^4` is nonlinear in temperature. This does not break the Hermitian operator structure, because the operator lives in `e`-space. If the design variables are geometry (view factors) or emissivities with temperatures prescribed, the QCQP stays clean and the `T^4` is a monotone chain-rule factor on the outside. It only becomes a genuine nonlinear coupled solve when temperatures are unknowns coupled to conduction (a SINDA-style resistor network), in which case radiative design becomes an outer Newton loop wrapped around the linear-in-`e` operator. That is standard and still differentiable, it just is not a single closed-form eigenproblem.

Net: geometrically this is the *best-fit* regime AEGIS has found in the generalization scan. That is exactly why the first pass was excited, and that excitement is physically justified. The question is never physics fit here, it is whether differentiability is a product wedge in the real toolchain.

## 2. Light calculations

### Differentiable view factor and its gradient

Take the simplest non-trivial case: facet 1 (a small element `dA_1`) and facet 2 (area `A_2`, small compared with the separation), separated by distance `r`. Facet 2 faces facet 1 (`theta_2 = 0`). Facet 1 is tilted by angle `theta` away from facing facet 2. For `A_2 << r^2` the point-to-facet view factor is

```
F_{1->2}(theta) = (A_2 / (pi r^2)) * cos(theta) * cos(theta_2)
               = (A_2 / (pi r^2)) * cos(theta)
```

The gradient with respect to the tilt angle, the thing an optimizer needs, is closed form:

```
dF/dtheta = -(A_2 / (pi r^2)) * sin(theta)
```

Plug in `A_2 = 0.01 m^2` (a 10 cm by 10 cm patch), `r = 1 m`, `theta = 30 deg`:

- `F = 0.01/pi * cos(30) = 0.0031831 * 0.86603 = 0.0027565`
- `dF/dtheta = -0.0031831 * 0.5 = -0.0015915 per radian`
- Relative sensitivity `dF/F = -tan(theta) = -0.5774 per radian = -0.0101 per degree`

So at a 30 degree tilt, every additional degree of tilt sheds about **1.0 percent of the radiative flux** exchanged between the two facets. That is what a differentiable view factor buys concretely: the engineer gets the exact marginal effect of a geometric knob in one evaluation, rather than re-meshing and re-solving at `theta` and `theta + delta` and differencing.

### Why the gradient is a category advantage only at large N

The AEGIS pitch is not "we can differentiate one facet," it is reverse-mode over many facets. For `N` geometric design variables:

- Finite difference: `N + 1` forward solves (one baseline plus one perturbation per variable).
- Adjoint / reverse-mode: all `N` sensitivities in roughly one backward pass, cost independent of `N`.

This matters only when `N` is large. In the published spacecraft thermal optimization (openMDAO, below) `N = 15`, so finite difference is 16 solves, trivially affordable overnight. Adjoint's constant-cost-in-N property becomes decisive at `N` in the hundreds or thousands: free-form radiator shape or topology, facade louver arrays, and above all heliostat fields with thousands of `(x, y)` coordinates. That is the dividing line I use in the verdict.

### Stefan-Boltzmann radiator sizing sanity number

A spacecraft radiator rejecting `Q = 1 kW` to deep space (`T_sink ~ 2.7 K`, negligible) at `T = 300 K` with emissivity `eps = 0.85`:

```
Q = eps * sigma * A * (T^4 - T_sink^4)
eps * sigma * T^4 = 0.85 * 5.670e-8 * 8.1e9 = 390.4 W/m^2
A = 1000 / 390.4 = 2.56 m^2
```

The design sensitivities an optimizer would chase:

- `dA/deps = -A/eps = -3.01 m^2` per unit emissivity. Improving a coating from `eps = 0.85` to `0.90` shrinks the radiator by 0.15 m^2, about 6 percent.
- `A ~ T^-4`, so `dA/A = -4 * dT/T`. Letting the radiator run 10 K hotter at 300 K (a 3.3 percent rise) shrinks it 13 percent.

These are exactly the closed-form sensitivities the Q-calculus is good at, and they are real levers in mass-constrained spacecraft design. The physics is not the obstacle.

## 3. The real engineering toolchain and whether differentiability is actually shipped there

This is the crux. The kill assumes differentiable radiative design is a solved, shipped thing. I searched the tools engineers actually use, per vertical. The finding is consistent: in the shipped engineering-thermal toolchain, design is parametric sweep, finite-difference numerical optimization, or heuristic/genetic search. Adjoint-style differentiability is a research literature, not a product feature.

### Spacecraft thermal (Thermal Desktop / SINDA-FLUINT, ESATAN-TMS, Thermica)

- The strongest counter-evidence to a revive is real and I want to state it up front: SINDA/FLUINT ships an "advanced design" Solver module inside Thermal Desktop that does automated design optimization (minimum-weight structures, heat-pipe spacing, box placement on radiator panels, and model correlation to test data by varying optical properties, with radiation exchange factors recomputed on the fly). See the C&R Technologies ICES paper "Parametric Thermal Analysis and Optimization" (crtech.com/sites/default/files/files/00ICES-266.pdf). So it is not true that spacecraft thermal is 100 percent manual sweep.
- But the Solver is a numerical optimizer driven by repeated full forward solves with finite-difference-style sensitivities, not an adjoint that differentiates analytically through the view-factor/radiation kernel. It re-runs the model per perturbation. That scales as O(N) in design variables and is why the published gradient work exists at all.
- The one genuinely gradient-based spacecraft thermal paper, "Gradient-based optimization of spacecraft and aircraft thermal design" (Aviation, 2020), does not extend ESATAN or Thermal Desktop. It rebuilds the thermal model inside **openMDAO** (a research MDO framework), derives analytic partial derivatives of the steady-state heat-transfer equation, and drives SLSQP over 15 design variables and 10 constraints. That is a research prototype in a research framework, not a shipped tool feature.
- The tell that gradients are wanted but not native: a wave of ML-surrogate papers exists specifically to *get* cheap gradients the native solvers do not expose. Physics-informed / POD-reduced neural surrogates for spacecraft thermal (e.g. "Thermal surrogate model for spacecraft systems using physics-informed machine learning with POD data reduction," Int. J. Heat Mass Transfer 2023, and Neural Concept's satellite thermal whitepaper). You do not bolt a neural surrogate onto ESATAN to obtain backprop gradients if ESATAN already gives you adjoint gradients.
- Even the very recent numerical-methods literature is still about *forward* accuracy, not differentiable design: arXiv 2511.04277 (Nov 2025), "Novel Numerical Methods for Accurate Space Thermal Analysis: Enforcing View Factors and Modeling Diffuse Reflectivity," is about getting view factors and diffuse reflection right in the forward solve, not about design gradients.

Verdict for this vertical: parametric plus finite-difference numerical optimization is shipped. Adjoint differentiability is not. The gap is real but small-N, and the domain is certification-bound (ECSS, correlation-to-test, flight heritage), which is a brutal moat for a startup engine with zero heritage.

### Building performance and solar (Radiance, EnergyPlus, Ladybug/Honeybee, ClimateStudio)

- Optimization here is overwhelmingly **genetic-algorithm and parametric**, not gradient. The standard stack is Grasshopper plus Ladybug/Honeybee (which wrap Radiance/Daysim for daylight and EnergyPlus for energy), with optimization delegated to Galapagos, Octopus, or Wallacei, all evolutionary/GA solvers. My searches for "differentiable solar-gain / shading optimization" returned only GA and parametric multi-objective studies, no differentiable pipelines.
- Radiance itself is a validated forward ray tracer with no autodiff. EnergyPlus is the code-compliance reference engine (ASHRAE 140), also not differentiable. ClimateStudio is a faster Radiance-based forward tool, still not a gradient optimizer.
- The objective landscape is partly discrete (glazing types, louver counts, code-compliance thresholds), which blunts the value of smooth gradients even if you had them.

Verdict for this vertical: no differentiable solar-gain design is shipped, but the incumbent GA workflow is entrenched and "good enough," the objectives are partly discrete, and code-compliance means EnergyPlus/Radiance are the trusted oracles. Low appetite for a differentiable replacement.

### Concentrated solar heliostat fields (SolarPILOT, Tonatiuh)

- SolarPILOT (NREL) lays out fields using **fixed geometric patterns** (radial staggered, radial cornfield, north-south variants) with parametric refinement and cost/efficiency objectives. It is pattern-and-parametric, not gradient-based.
- Gradient-based heliostat layout genuinely exists, but only in the research literature and it has **not** displaced the pattern/heuristic incumbent. Key papers: "On using a gradient-based method for heliostat field layout optimization" (Energy Procedia 2014) and "Pattern-free heliostat field layout optimization using physics-based gradient" (Solar Energy 2020), which splits insolation-weighted optical efficiency into shading/blocking and non-shading/blocking terms and differentiates it. The competing modern approaches are still GA, particle swarm, differential evolution, and biomimetic spiral heuristics (multiple Solar Energy papers 2022 to 2025).
- This is the interesting vertical because the design-variable count is huge (thousands of continuous heliostat coordinates), the objective (annual optical efficiency = cosine loss + shading + blocking + spillage + atmospheric) is smooth in geometry, and the exact primitive AEGIS ships (ReLU cosine visibility gated by ambient occlusion) *is* the shading-blocking-cosine physics. The published pattern-free gradient work is a proof of concept that this thesis holds, and the fact that it exists on paper but is not the productized default is precisely the white space.

Verdict for this vertical: gradient methods are proven-in-research, not shipped as the default. Genuine gap, large N, smooth objective, AEGIS-native primitive.

### Bifacial PV (bifacialvf, bifacial_radiance, NREL)

- NREL ships two forward models: `bifacialvf` (an analytic view-factor irradiance model, isotropic-scatter assumption) and `bifacial_radiance` (a Radiance ray-trace wrapper). Both are forward yield calculators. My searches for differentiable/gradient versions returned nothing, only validation comparisons of the two forward models.
- The geometric design DOF is small (row pitch, tilt, tracker geometry, ground albedo), so this is a low-N problem where finite difference over a handful of variables is entirely adequate.

Verdict for this vertical: not differentiable, but also does not need to be. Small N, forward-model market.

## 4. The honest counter-argument to our own kill

The kill said: "Mitsuba/nvdiffrast already do differentiable radiative transport, so AEGIS brings nothing." That is a category error, and here is the plain version.

Differentiable rendering solves inverse *graphics*: recover scene parameters (geometry, BRDF, textures, camera) from images, in RGB or spectral radiance, optimized with autodiff in Dr.Jit/PyTorch. It is genuinely excellent at that. But no spacecraft thermal engineer, no CSP field designer, and no building-energy modeler runs their design problem in Mitsuba. Their objectives are heat rejection in watts, node temperatures against ECSS margins, annual optical efficiency against LCOE, kWh yield against code compliance. Their models are certified forward solvers (ESATAN, EnergyPlus, SolarPILOT) validated against test data and standards. The mathematics of differentiable light transport being solved in a graphics package does not put a gradient into ESATAN, and it does not survive contact with flight-heritage requirements. So "the math is solved in graphics" and "differentiable design is shipped in engineering thermal" are two different claims, and only the first is true. The kill conflated them.

That counter-argument holds. It is a legitimate reason to reopen the topic.

But I will not force a resurrection, because the same research shows why the topic still mostly does not become a product:

1. **Design-variable counts are usually small.** The flagship spacecraft study used 15 variables. Adjoint's decisive advantage (cost independent of N) only shows up at N in the hundreds or thousands. At N = 15, finite-difference optimization (already shipped in SINDA/FLUINT's Solver) is fine. So for spacecraft and PV, AEGIS's differentiability is a convenience, not a category win.

2. **The incumbents are trusted oracles, and a startup engine has zero trust.** Spacecraft thermal is standards-bound and correlation-to-test bound. Building energy is code-compliance bound (EnergyPlus is the reference). CSP is CAPEX/LCOE bound with NREL's SolarPILOT as the accepted tool. Replacing the physics engine is a multi-year trust battle even with a real technical edge.

3. **AEGIS ships first-bounce plus scalar recapture, not the full radiosity solve.** For a real enclosure AEGIS would have to add the `(I - R F)^{-1}` interreflection matrix solve, plus band models (solar band versus IR band with distinct alpha and eps), plus specular-versus-diffuse handling and temperature-dependent properties. It is all differentiable and all consistent with the monograph, but it is net-new engine work in a domain with no dosimetry synergy. That is a real cost with no reuse dividend.

4. **Where N is large, the incumbent is heuristic and the objective is smooth, the gradient method is already published and still did not win.** The pattern-free gradient heliostat papers exist and SolarPILOT still ships patterns. That non-adoption is informative: the annual-average objective requires integration over many sun positions, is non-convex, and GA gets "close enough" for a field you build once. The friction is not that no one thought of gradients, it is that the marginal LCOE from a better layout has not justified switching tools.

## 5. Verdict

Graded per vertical, then overall.

| Vertical | Grade | Why |
|---|---|---|
| Spacecraft thermal | NICHE-PAPER-ONLY | Gap is real (no adjoint in ESATAN/TD) but N is small, SINDA/FLUINT already ships FD optimization, and certification/flight-heritage is a fatal startup moat. |
| Building solar / shading | DEAD to NICHE | GA/parametric incumbent entrenched, objectives partly discrete, EnergyPlus/Radiance are code-compliance oracles, low appetite. |
| Concentrated-solar heliostat layout | WORTH-A-SECOND-LOOK | Large-N continuous geometry, smooth objective, heuristic/pattern incumbent (SolarPILOT), and AEGIS's ReLU-cosine-plus-occlusion primitive *is* the shading-blocking-cosine physics. Gradient methods proven-in-research, not productized: genuine white space. |
| Bifacial PV | NICHE | Not differentiable today, but small N so it does not need to be. |

**Overall verdict: WORTH-A-SECOND-LOOK, gated entirely to concentrated-solar heliostat field layout.** I am upgrading from the earlier DEAD, because the kill's stated reason ("Mitsuba already owns this") is a category error and does not survive the toolchain research. I am *not* upgrading to REVIVE, because the resurrection is narrow: it survives in exactly one vertical, and even there the incumbent's non-adoption of already-published gradient methods is a warning about market friction.

**Single best beachhead: concentrated-solar heliostat fields.** This is the only vertical that clears all four bars at once: large design-variable count (so adjoint is a category advantage, not a convenience), objective smooth in continuous geometry, incumbent is heuristic/pattern rather than a certified black box, and AEGIS's core visibility primitive maps one-to-one onto the physics (cosine efficiency plus shading plus blocking is ReLU cosine plus ambient occlusion, which is what AEGIS computes natively and differentiably).

### What would have to be true for the CSP beachhead

1. AEGIS adds an annual-integrated optical-efficiency objective (a weighted sum over sun positions across the year) and exposes the shading-plus-blocking view-factor gradient. This reuses AEGIS's existing differentiable occlusion machinery almost verbatim, so the engine lift is small relative to the other verticals.
2. Reverse-mode scales as advertised on realistic fields: thousands of heliostat `(x, y)` DOFs, all sensitivities in roughly one backward pass versus thousands of finite-difference forward solves. That 100x-to-1000x is the only durable moat, and it has to be demonstrated, not asserted.
3. Forward optical efficiency validates against SolarPILOT on a reference field (PS10 is the standard benchmark) to within about 1 percent. Without matching the trusted oracle on the forward problem, the gradient is irrelevant.
4. A design partner who feels the LCOE pain from layout (a CSP developer or heliostat vendor) is willing to co-develop. Absent a pull, this stays a paper.

### Biggest risk

The CSP market is small and slow-growing next to PV, so even a clean 100x-to-1000x differentiability win lands in a modest addressable market. And the published pattern-free gradient heliostat methods already exist without displacing SolarPILOT, which is direct evidence that the market friction (non-convex annual objective, build-once fields, "good enough" GA) is real and has resisted exactly this idea before. AEGIS would be entering a space where the technical thesis is already proven and still commercially stalled. That is the honest headwind.

## Sources

- Adjoint-based shape optimization for radiative transfer using level-set and volume penalization, Int. J. Heat Mass Transfer 2023: https://www.sciencedirect.com/science/article/abs/pii/S0017931023003113
- Inverse design optimization of spatial emissivity distribution via continuous adjoint (Liu and Hasegawa), SSRN: https://doi.org/10.2139/ssrn.4813082
- Gradient-based optimization of spacecraft and aircraft thermal design (openMDAO, SLSQP, 15 vars), Aviation 2020: https://journals.vilniustech.lt/index.php/Aviation/article/view/13045
- Novel Numerical Methods for Accurate Space Thermal Analysis: Enforcing View Factors and Modeling Diffuse Reflectivity, arXiv 2511.04277: https://arxiv.org/pdf/2511.04277
- SINDA/FLUINT Solver, Parametric Thermal Analysis and Optimization (C&R Technologies ICES): https://www.crtech.com/sites/default/files/files/00ICES-266.pdf
- ESATAN-TMS Python API application cases (parametric/case-based workflows), ICES 2024: https://ttu-ir.tdl.org/server/api/core/bitstreams/cfa6d6cd-9c09-46a4-96bc-a28f17dd8b09/content
- Thermal surrogate model for spacecraft systems using physics-informed ML with POD, Int. J. Heat Mass Transfer 2023: https://www.sciencedirect.com/science/article/abs/pii/S0017931023004829
- Neural Concept, smarter satellite design for thermal constraints (ML surrogate): https://www.neuralconcept.com/post/satellites-a-smarter-design-regarding-the-thermal-constraints
- On using a gradient-based method for heliostat field layout optimization, Energy Procedia 2014: https://www.sciencedirect.com/science/article/pii/S1876610214006067
- Pattern-free heliostat field layout optimization using physics-based gradient, Solar Energy 2020: https://www.sciencedirect.com/science/article/abs/pii/S0038092X20306435
- Heliostat field optimization, biomimetic spiral vs radial-staggered layouts, Solar Energy 2022: https://www.sciencedirect.com/science/article/abs/pii/S0038092X22002833
- NREL bifacial_radiance (Radiance ray-trace PV toolkit): https://github.com/NREL/bifacial_radiance
- NREL bifacialvf (view-factor PV model): https://github.com/NREL/bifacialvf
- Understanding Bifacial PV Modeling: Raytracing and View Factor Models (NREL): https://docs.nrel.gov/docs/fy20osti/75628.pdf
- Mitsuba 3, gradient-based optimization / inverse rendering (graphics, for contrast): https://mitsuba.readthedocs.io/en/v3.5.1/src/inverse_rendering/gradient_based_opt.html
- Dr.Jit: a just-in-time compiler for differentiable rendering (graphics, for contrast): https://www.researchgate.net/publication/362206556_DRJIT_a_just-in-time_compiler_for_differentiable_rendering
- Coupling conduction, convection and radiative transfer in a single path space (infrared rendering, graphics): https://dl.acm.org/doi/10.1145/3592121
- AEGIS monograph, `T0`-as-emissivity and radiosity recapture factor: `/home/user/aegis/theory/monograph_v2.tex` lines 1076 to 1077 and eq:radiosity-C (lines 2137 to 2148)
