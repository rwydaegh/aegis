# Seismic AVO / AVA as a market for AEGIS: an honest re-examination

Status: killed topic, re-opened for stress-test.
Date: 2026-07-06.
Verdict grade (skip to the bottom for the reasoning): **DEAD as a company direction, NICHE-PAPER-ONLY at the most generous reading.**

I was asked to re-examine the earlier decision to kill seismic AVO/AVA, honestly, with physics and light numbers and real web research, and not to force either a burial or a resurrection. This is that write-up. Short version: the earlier kill was correct, but for a sharper reason than the one originally given. The reason is not "FWI already owns differentiability" (true but secondary). The reason is that seismic AVO is a medium-parameter *estimation* problem with no controllable excitation vector, and AEGIS's entire moat is *design of a controllable excitation*. There is no `x` to put in `x^H Q x`. That is the load-bearing mismatch.

## 1. The physics map: where AVO lands on the assumption ladder

First, the part that genuinely maps. Zoeppritz is elastic Fresnel. A plane P-wave hitting a planar interface between two elastic half-spaces splits into reflected P, reflected S, transmitted P, transmitted S, and the amplitudes are the solution of a 4x4 linear system in the boundary conditions. That is exactly the same shape of object as the electromagnetic Fresnel coefficient, just with mode conversion (P-to-S) that EM does not have unless you count polarization. So assumption **A4 (locally planar interface, local plane-wave interaction law)** holds cleanly. The AVA curve `R_pp(theta)` is a local, differentiable function of the two media's `(Vp, Vs, rho)`. Differentiating a Zoeppritz coefficient is real physics and it is easy. No argument there.

Now the part that does not map, in order of severity.

**A2 (first bounce dominates) is violated by construction, not by approximation.** In AEGIS the wave hits one body once and the first specular interaction carries essentially all the recorded power. Seismic reflection is the opposite by design. The recorded trace is the superposition of primary reflections from a *vertical stack* of hundreds of interfaces spread over kilometres of depth. To reach the interface at 3 km, the wavefront must transmit *down* through every overlying interface, reflect once at the target, and transmit *back up* through every overlying interface. Each of those downgoing and upgoing transmissions changes amplitude (transmission coefficients), bends the ray (Snell across velocity contrasts), converts modes, and disperses. The "primaries only" workhorse of AVO looks superficially like a first-bounce model, but a primary is not a first bounce off a single boundary. It is one reflection wrapped inside a long two-way transmission path through a heterogeneous volume. AEGIS has no representation of that path. It has no transmission-through-a-stack, no ray bending, no moveout. Multiples (energy that bounces two or more times between interfaces) are a separate headache that AVO practitioners spend real money to *remove* before inversion, and AEGIS would have no way to model them either.

**A3 (surface confinement, high loss or PEC) fails completely, and the ladder already predicts the consequence.** The Earth is penetrable and low-loss. That is the whole point: seismic energy is supposed to travel kilometres down and come back. This is the exact opposite of the high-loss or PEC body that lets AEGIS collapse a 3D absorption problem onto a 2D surface. Per the ladder's own rule of thumb, penetrable and low-loss means `Q` stops being a surface integral and becomes a volume Gram matrix. It is still PSD, still in principle QCQP-able, but the millisecond-cheap surface miracle is gone. Seismic is the textbook case where A3 dies.

So what does "the body surface" even correspond to in seismic? Not one scatterer boundary. It corresponds to a *stack* of laterally-extensive interfaces embedded in a volume, and the data is a volume tomography of that stack, not a surface-scattering measurement off a single object. The analogy "interface = body surface" holds for one isolated reflector in isolation and breaks the moment you have more than one, which is always.

**A1 (linear superposition) holds, and the Q-calculus rides on A1 alone, but there is nothing for it to ride to.** This is the subtle and, I think, decisive point. The Q-operator algebra needs A1 plus a *controllable excitation vector* `x`. In AEGIS `x` is the MIMO precoder: you own a coherent transmit array with many independent degrees of freedom and you *design* `x` to shape `x^H Q x` (concentrate absorbed power, minimise scattered power, and so on). Seismic AVO has no such `x`. The source is a fixed airgun or vibroseis sweep. The unknowns are the *medium* parameters `(Vp, Vs, rho)` as a function of depth. AVO is parameter estimation of a passive medium, not design of an active excitation. The mathematical shape is different: `min over m of ||d - F(m)||`, a nonlinear least-squares in the medium, versus `max over x of x^H Q x subject to constraints`, a quadratic form in a controllable vector. AEGIS's moat is the second shape. Seismic hands you the first. There is no precoder to optimise, so the closed-form Hermitian-operator calculus, the actual crown jewel, has no home here even though A1 is satisfied.

The one place seismic *does* expose a controllable coherent excitation is acquisition-side: simultaneous-source encoding, dispersed source arrays, wavefield focusing, time-reversal / RTM. There you do design a source wavefield. I searched this specifically. It is a real and active area (source encoding to cut FWI/RTM cost, dispersed source arrays shaped to give desired angular spectra in the subsurface). But two things kill it as an AEGIS wedge: the coherent aperture control in exploration seismic is coarse compared to a phased array (you do not have thousands of independently-driven, phase-coherent elements the way 5G does), and the objective there is still to *image the medium*, not to concentrate energy on a chosen target for its own sake. Focusing is a means, not the product.

## 2. Light calculations that decide the regime

Wavelength. `lambda = v / f`.
- 30 Hz, 3000 m/s: `lambda = 100 m`.
- 10 Hz, 1500 m/s: `lambda = 150 m`.
- 100 Hz, 5000 m/s: `lambda = 50 m`.

So seismic wavelengths are tens to ~150 m, call it 50-100 m typical.

Is a single interface "electrically large and smooth" at those wavelengths? Laterally, yes. A geological interface is coherent over kilometres. The first Fresnel zone radius at depth `d` is roughly `r ~ sqrt(lambda d / 2)`. At `lambda = 100 m`, `d = 2000 m`: `r ~ sqrt(100 * 2000 / 2) = sqrt(1e5) ~ 316 m`, so a Fresnel zone ~600 m across against an interface that runs for kilometres. Locally flat and many-zones-wide, so a single interface is a legitimate physical-optics / Kirchhoff reflector. Roughness: specular reflection dominates when interface height deviations stay under about `lambda/8 = 12 m` over a Fresnel zone, which typical bedding satisfies. So the *specular-reflector-off-one-interface* regime that A4 needs is genuinely satisfied. That is not the problem.

The problem is the vertical stacking density relative to wavelength. Reservoir tuning thickness is `lambda/4 ~ 12-25 m`. Many targets are *thinner* than a wavelength, so their top and base reflections interfere within one wavelet: you do not get clean isolated bounces, you get tuned composite reflections. And a seismic column stacks hundreds of such reflectors over 2-5 km, i.e. tens of wavelengths of depth packed with interfaces every fraction of a wavelength. A one-bounce surface model (A2) cannot represent even two stacked interfaces correctly, let alone hundreds with interference and two-way transmission. The number that decides it: **AEGIS models 1 interaction; a seismic trace integrates O(100s) of stacked interactions plus their two-way transmission paths.** That is a two-to-three-order-of-magnitude structural gap, and it is not a fidelity knob, it is a different problem.

One more number on the "speed moat." The Zoeppritz-convolutional AVA forward (compute `R_pp(theta)` per interface, convolve with a wavelet) is already cheap: a handful of small linear solves and one 1D convolution per trace, microseconds. There is no expensive forward here for AEGIS to accelerate. The expensive thing in seismic is the wave-equation propagation (RTM/FWI), which is precisely the volume solve AEGIS refuses to do. So the speed miracle would have to be delivered on the exact operation A3 forbids.

## 3. The real state of the art (web research)

Differentiable AVO with the *exact* Zoeppritz equation is not a gap. It is being published right now. A December 2025 preprint does nonlinear AVO inversion with the exact Zoeppritz equation and adjoint-state gradients for `Vp, Vs, rho`, explicitly derived through a Lagrangian, and explicitly argues the adjoint-state method beats automatic differentiation on cost (two wavefield simulations regardless of parameter count) ([arXiv:2512.13172](https://arxiv.org/html/2512.13172)). Earlier work already did constrained non-linear AVO via adjoint-state optimisation ([Ahmed et al., Computers & Geosciences 2022](https://dl.acm.org/doi/abs/10.1016/j.cageo.2022.105214)) and AVA inversion of elastic and attenuative parameters directly from Zoeppritz in viscoelastic media ([ScienceDirect S0926985122001148](https://www.sciencedirect.com/science/article/abs/pii/S0926985122001148)). The adjoint-state method itself is a decades-old, reviewed, standard tool in geophysics ([Plessix review, ResearchGate](https://www.researchgate.net/publication/227737987)).

The volume-accurate differentiable inversion stack is mature and largely open source:
- **Deepwave**: FWI in PyTorch, wave propagation as a differentiable layer, gradients by autodiff.
- **Devito**: JIT compiler for stencil finite-difference wave modelling, the propagation engine under many workflows.
- **JUDI.jl**: Julia Devito Inversion framework from Georgia Tech SLIM, on-prem or cloud, differentiable-programming FWI/LS-RTM ([SLIM, The Leading Edge 2023](https://slim.gatech.edu/Publications/Public/Journals/TheLeadingEdge/2023/louboutin2023lmi/le_software.html)).
- **j-Wave**: JAX-based differentiable wave simulator, full autodiff and JIT ([arXiv:2207.01499](https://arxiv.org/pdf/2207.01499)).
- General autodiff-FWI with flexible workflows is an active 2024-2025 line ([arXiv:2412.00486](https://arxiv.org/pdf/2412.00486)).

Commercial AVO forward modelling and inversion is commodity too. SLB Petrel does AVO synthetic-gather generation from Zoeppritz and joint lithofacies/elastic inversion in its Rock Physics and Inversion plug-in ([SLB Petrel geophysics](https://www.software.slb.com/products/petrel/petrel-geophysics/rock-physics-inversion-plug-in)). CGG/GeoSoftware Hampson-Russell has a dedicated AVO module ([GeoSoftware HampsonRussell](https://www.geosoftware.com/hampsonrussell)).

Now the honest question the brief asked: is there a gap for a *fast differentiable reflectivity surrogate above FWI*, the way AEGIS pitches itself as a differentiable design layer above full-wave EM? I looked hard and the answer is no, for a specific reason. The AEGIS-above-EM pitch works because the thing it sits above (full-wave EM solvers) is genuinely expensive, and the cheap differentiable surface layer is genuinely novel there. In seismic, the object that would play the role of "cheap differentiable surrogate" is the Zoeppritz-convolutional forward, and that is *already* cheap and *already* differentiable and *already* shipped in Petrel and Hampson-Russell. There is nothing to surrogate. The genuinely expensive object is the volume wave propagation, and the surrogates people actually build for *that* are neural operators (Fourier Neural Operator and friends, e.g. [arXiv:2209.11955](https://arxiv.org/pdf/2209.11955)), not a reflectivity calc. So both niches are taken: the cheap-forward niche is commoditised, and the expensive-forward-surrogate niche is a neural-operator problem AEGIS's physics does not address. The "pre-screen layer above FWI" story has no vacancy.

## 4. Who would pay, and is it the wrong buyer

The market is large on paper. Geophysical software service is quoted around USD 17.9 B for 2025, seismic data processing and imaging software around USD 9.8 B ([Fortune Business Insights](https://www.fortunebusinessinsights.com/geophysical-software-service-market-106236), [Coherent Market Insights](https://www.coherentmarketinsights.com/industry-reports/seismic-data-processing-and-imaging-software-market)). But it is a closed oligopoly: SLB (Petrel), Halliburton (DecisionSpace), CGG/GeoSoftware (Hampson-Russell), Emerson/AspenTech (Paradigm). On-prem, deeply integrated, multi-year procurement, sold to oil and gas majors and service companies who trust incumbents and run validated workflows.

Is the buyer *genuinely* wrong for a UGent EM-dosimetry spin-off, or is that an excuse? It is genuine, on four independent axes:
1. Domain credibility. The spin-off has zero geophysics track record, zero seismic references, zero network inside the exploration community. In a conservative field that trusts incumbents, that is close to disqualifying for a first sale.
2. Sales motion. Enterprise on-prem geoscience software with year-long cycles is the opposite of the spin-off's world. It would consume the company.
3. Mission and ESG. The founding thesis is wave-exposure *health* (5G dosimetry, ICNIRP compliance). Pivoting the flagship method into fossil-fuel exploration is off-brand, would confuse the story for VLAIO/iStart and academic partners, and rides a secularly declining exploration-capex trend.
4. Moat already occupied and ahead. As above, differentiable AVO and differentiable FWI are mature, published, and partly open source, from exactly the groups (SLIM, and the vendors) who own the customers.

So this is not an excuse. It is the wrong buyer, in the wrong industry, with the wrong sales motion, against an entrenched and technically-ahead incumbent set, and off the company's mission.

## 5. Verdict

**Grade: DEAD as a company direction. NICHE-PAPER-ONLY is the ceiling.**

The kill decision was right. I would upgrade the *reason*. The original reason ("FWI already owns differentiability") is true but is the second-strongest argument. The strongest argument is structural: AVO is medium-parameter *estimation* with no controllable excitation, and AEGIS's entire durable moat is closed-form *design of a controllable excitation* via `x^H Q x`. Seismic AVO hands you an inverse problem of the wrong shape. On top of that, A2 and A3 both fail (stacked interfaces and a penetrable low-loss volume), so even the fast forward evaluator has no regime to live in, and the one physics overlap that survives (A4, Zoeppritz = elastic Fresnel) is a solved, cheap, commoditised calculation.

**Single strongest surviving angle.** Not AVO estimation. The only place a controllable `x` and the Q-calculus could live in an elastic-wave setting is *coherent-array energy focusing in a penetrable medium* (design the excitation to concentrate elastic power on a chosen region, subject to constraints, differentiably). In exploration seismic that is weak (coarse aperture, imaging not focusing is the goal). But that same one-sentence description, "controllable coherent phased array, penetrable low-loss medium, design the drive vector to shape a quadratic power functional, end-to-end differentiable," is an almost exact description of **therapeutic ultrasound / HIFU and ultrasonic NDT phased arrays**, where you *do* own thousands of independently-driven coherent elements and you *do* design the drive to concentrate acoustic power on a target. That is where the elastic-wave generalisation of the Q-calculus actually wants to go. It is a different topic from seismic AVO and deserves its own memo. For seismic AVO specifically, the door stays closed.

**What would have to be true for seismic to become worth pursuing** (all of these, not any one):
1. The target application exposes a genuinely controllable, many-DOF coherent source aperture (borehole/cross-well arrays, permanent reservoir-monitoring arrays), so that a real `x` exists.
2. The paying objective is *design of the excitation* (focusing, illumination shaping, survey design), not *estimation of the medium*.
3. Either the medium is effectively surface-confined for the quantity of interest, or the customer accepts a volume `Q` and the loss of the millisecond speed story.
4. A buyer exists outside oil-and-gas exploration (monitoring, geothermal, CO2 storage, or a non-geoscience elastic-wave buyer), reachable without an incumbent's sales machine.

None of those four is true for exploration AVO today. So: dead, with a one-line academic footnote and a redirect toward ultrasound rather than a resurrection of seismic.

---

Sources consulted:
- Nonlinear AVO inversion with exact Zoeppritz + adjoint-state, arXiv:2512.13172 (Dec 2025): https://arxiv.org/html/2512.13172
- Constrained non-linear AVO via adjoint-state optimisation, Computers & Geosciences 2022: https://dl.acm.org/doi/abs/10.1016/j.cageo.2022.105214
- AVA inversion of elastic and attenuative parameters via Zoeppritz, viscoelastic media: https://www.sciencedirect.com/science/article/abs/pii/S0926985122001148
- Plessix, adjoint-state method review (geophysics): https://www.researchgate.net/publication/227737987
- SLIM learned multiphysics inversion with differentiable programming (JUDI/Devito), The Leading Edge 2023: https://slim.gatech.edu/Publications/Public/Journals/TheLeadingEdge/2023/louboutin2023lmi/le_software.html
- j-Wave JAX differentiable wave simulator, arXiv:2207.01499: https://arxiv.org/pdf/2207.01499
- Autodiff-based FWI with flexible workflows, arXiv:2412.00486: https://arxiv.org/pdf/2412.00486
- Neural-operator seismic waveform surrogates, arXiv:2209.11955: https://arxiv.org/pdf/2209.11955
- SLB Petrel Rock Physics and Inversion plug-in (Zoeppritz AVO modelling): https://www.software.slb.com/products/petrel/petrel-geophysics/rock-physics-inversion-plug-in
- CGG/GeoSoftware HampsonRussell AVO module: https://www.geosoftware.com/hampsonrussell
- Market sizing: https://www.fortunebusinessinsights.com/geophysical-software-service-market-106236 and https://www.coherentmarketinsights.com/industry-reports/seismic-data-processing-and-imaging-software-market
