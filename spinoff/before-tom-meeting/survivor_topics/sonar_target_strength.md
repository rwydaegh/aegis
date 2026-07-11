# Sonar and underwater target strength: pressure-test

Topic: acoustic target strength (TS), the underwater analog of radar cross section, for quiet-hull design and sonar-array optimization. This is Q_re for acoustics. I placed it as a Tier-2 survivor. Below I try to break it.

Verdict up front: **OVERRATED**. The physics that AEGIS does well maps onto the closed defense market (large smooth rigid hulls, deep in the physical-optics regime), and the markets a UGent spin-off can actually reach (fisheries, small-AUV obstacle sensing) sit in the ka ~ 1 resonant regime where physical optics is weakest. That is a scissors, and both blades cut against us. The one honest non-overrated framing is a narrow explore-tool for acoustic calibration targets, reflector arrays, and decoys, and that does not sustain a company.

## 1. Physics: mapping hull target strength onto the ladder

The acoustic swap is clean at leading order. EM wave impedance Z0 becomes the acoustic impedance Z = rho*c, and the Kirchhoff surface-scattering integral is textbook sonar physics. For a metal pressure hull in water the impedance contrast is enormous. Steel is rho*c ~ 4.7e7 Pa*s/m against water at 1.5e6 Pa*s/m, a contrast near 30, so the hull is a nearly rigid (pressure-release-complement) scatterer and specular surface reflection is a sensible leading model. That is exactly A3 (surface confinement) holding for the same reason it holds for a metal plate in EM. The AEGIS object I would reuse is Q_re from `theory/q_complement.tex`, defined in `Cref{eq:Qref}` as the Hermitian PSD operator whose quadratic form x^H Q_re x is the total power specularly scattered into the exterior half-space (`theory/q_complement.tex`, section "The reflection operator", def:Qref around line 267). That operator is the acoustic-RCS object with an impedance swap and nothing more conceptually new.

Now the honest part. Real submarine target strength is dominated by exactly what A2 (first-bounce dominates) throws away:

- **Elastic waves in the pressure hull.** A steel shell in water carries flexural (Lamb) waves. Near the coincidence/critical frequency, where the plate flexural wavespeed matches the water sound speed, the shell radiates strongly and the scattered field is not specular at all. For a 3 cm steel plate I get a coincidence frequency near 8 kHz (formula f_c ~ c_water^2 / (1.8 * c_L * h), c_L ~ 5000 m/s), which sits right inside the 1 to 100 kHz active-sonar band. This is not a small correction. It is often the dominant off-broadside return and it is precisely the physics naval designers care about because it fills the specular nulls where a stealth hull is supposed to be dark.
- **Structural and internal resonances.** Bulkheads, frames, ballast tanks, and internal reflectors ring and re-radiate. None of this is a surface first-bounce.
- **Anechoic coatings.** Alberich-style rubber tiles with embedded voids are resonant absorbers tuned around a quarter-wavelength, not a fixed surface impedance. Their whole job is a frequency-and-angle-dependent resonant response that A4 (locally planar Kirchhoff with a static impedance) cannot represent. The literature explicitly models these with FEM/Galerkin resonant-absorber schemes, not Kirchhoff (see the anechoic-coating sources below).
- **Edge diffraction and the creeping-wave analog.** AEGIS has partial machinery here, `src/aegis/kernels/fock.py` (creeping-wave / Fock) and `src/aegis/kernels/level6_diffraction.py`, which is a genuine plus over a pure Kirchhoff code, but it addresses the geometric-diffraction slice, not the elastic-shell physics.

So the verdict is the same shape as the stealth-RCS verdict. AEGIS can gradient-explore hull shape for the specular envelope. It cannot certify a low target strength, because the number that decides detectability is set by elastic returns, resonances, and coatings that live outside the assumption ladder. Explorer, not certifier. This is not a defect I can engineer away with more mesh resolution. It is a different physics (structural acoustics of a fluid-loaded elastic shell) bolted onto the surface problem.

The BeTSSi benchmark community says this in their own words. The generic 1700-ton submarine model exists specifically "to show the limitations of the numerical codes," and the accepted tool hierarchy runs from "approximative codes, such as Kirchhoff-approximation codes and raytracing codes" up to "full field codes (boundary integral equations / finite elements)" for exactly the elastic-coupled cases (FOI / BeTSSi II sources below). AEGIS would enter that hierarchy as a fast approximative Kirchhoff code, the bottom rung, and the field already has several of those.

## 2. Light calculations: where physical optics is trustworthy

Sound speed in water c ~ 1500 m/s. Wavelengths across the active-sonar band:

| Frequency | Wavelength |
|---|---|
| 1 kHz | 150 cm |
| 10 kHz | 15 cm |
| 100 kHz | 1.5 cm |

Hull size in wavelengths, for a 100 m x 10 m submarine (radius a = 5 m):

| Frequency | ka (a = 5 m) | Length in wavelengths (L = 100 m) |
|---|---|---|
| 1 kHz | 21 | 67 |
| 10 kHz | 209 | 667 |
| 100 kHz | 2094 | 6667 |

Even at the low end (1 kHz) ka ~ 21, and by 10 kHz the hull is hundreds to thousands of wavelengths across. This is deep in the physical-optics regime (ka >> 1), so the geometric specular part is exactly where Kirchhoff/PO is supposed to be accurate. That is the good news and it is real. The dynamic-range caveat is where it dies: PO reproduces the bright specular envelope near broadside to roughly 20 to 30 dB below the specular peak, and then the field is filled by elastic and diffracted contributions that PO does not carry. Stealth engineering lives in that filled-in floor, 20 to 40 dB down, at off-broadside aspects. PO gives you the peaks you already knew about and is blind in the valleys that matter.

Canonical target strength, rigid finite cylinder at broadside, TS = 10*log10(a*L^2 / (2*lambda)):

- a = 5 m, L = 100 m, 1 kHz: TS ~ +42 dB re 1 m^2
- same at 10 kHz: TS ~ +52 dB re 1 m^2

These are the idealized specular broadside highlights. Real measured beam-aspect submarine TS is far lower (order +10 to +30 dB) once you leave perfect broadside, and it collapses tens of dB at bow/stern aspects. Anechoic coatings then subtract another order 10 to 20 dB. The gap between the +42 to +52 dB rigid-specular number and the real single-digit-to-30 dB number is exactly the coating-plus-elastic-plus-aspect physics that AEGIS does not model. For scale, a 1 m rigid sphere is TS = 10*log10(a^2/4) = -6 dB, so a fish or a small mine sits tens of dB below a hull and its return is set by resonance, not specular geometry.

## 3. Incumbents and the gap

**Who owns this.** Target-strength prediction is a mature, mostly defense-lab and specialist-vendor field. The reference community is BeTSSi (Benchmark Target Strength Simulation), run through FWG Kiel and FOI Sweden, with benchmark workshops (BeTSSi II 2014, BeTSSi IIB / III 2016 to 2017) where national labs compare codes on a generic 1700-ton submarine. The established methods are Kirchhoff/raytracing approximate codes at the fast end and BEM/FEM full-field acoustic-elastic coupled codes at the accurate end (Helmholtz-Kirchhoff integral plus FEM for the solid coupling). Commercial full-field acoustics is COMSOL, Actran, VA One, and coupled FEM/BEM houses. None of these are a UGent spin-off's customer.

**Is differentiable TS shape optimization a gap.** Partly, and this is the one interesting finding. The differentiable-BEM idea already exists in the open literature: JAX-BEM ("Gradient-Based Acoustic Shape Optimisation via a Differentiable Boundary Element Method") is differentiable from the domain solution back to mesh vertices with reverse-mode AD, validated on a rigid sphere and applied to horn directivity. Differentiable point-scattering models for radar target characterization also exist. So the "differentiable acoustic scattering to mesh" primitive is published and not novel. What is genuinely less crowded is a *fast differentiable physical-optics surface* engine coupled to the Q-operator QCQP calculus, meaning you optimize an array excitation x (via `src/aegis/coherent/exposure_operator.py` and the ECBF solver in `src/aegis/coherent/ecbf.py`) rather than only the geometry. That reuse step is clean: Q_re is already Hermitian PSD, so minimizing x^H Q_re x for a projector array or maximizing it for a monostatic receiver is the same eigenproblem AEGIS already solves. But note the customer for array-excitation optimization is a sonar-array designer, and hull TS is a geometry problem, not an excitation problem, so the QCQP reuse is more natural for sonar-array/beamforming design than for hull stealth. The two halves of the pitch want different buyers.

**Business blockers, weighed honestly.** This is the decisive column.

- The submarine-TS buyer set is national navies and their contractors (Naval Group, BAE, Thyssen, GD Electric Boat, plus the defense labs themselves). It is tiny, closed, security-cleared, and largely ITAR / EAR / national-classification bound. A hull-shape or coating tool touches classified signature data by construction.
- A UGent spin-off with no clearance, no defense-prime relationship, and an EU academic footprint is structurally shut out of the part of this market where the physics fits. The generic BeTSSi hull exists precisely because the real geometries are classified, which tells you the whole field routes around a wall the spin-off cannot cross.
- Sales cycles are multi-year government procurement. Reference customers cannot publish. That kills the normal SaaS/land-and-expand motion the rest of the AEGIS commercialization plan relies on.

The physics is a green light and the market is a red light, and for a spin-off the market wins.

## 4. Verdict

**Grade: OVERRATED.** Not because the Kirchhoff/PO acoustic mapping is wrong (it is correct, standard, and AEGIS's fock.py and diffraction kernel even push slightly past a naive PO code), but because of a double bind: where the AEGIS physics is strong (large smooth rigid hulls, ka in the hundreds to thousands) the buyer is closed and classified, and where the buyer is open (fisheries, small AUV) the targets are resonant ka ~ 1 gas-filled or elastic bodies where PO is the wrong model. On top of that, the number that certifies a quiet hull is set by elastic shell waves, structural resonances, and resonant anechoic coatings, all outside the assumption ladder, so AEGIS is an explorer of specular shape and never a certifier of target strength. The differentiable-BEM primitive is already published, so even the "differentiable" hook is not a moat here.

**Strongest angle.** The least-bad framing is not submarines at all. It is a fast differentiable design tool for *engineered rigid acoustic geometry* where PO genuinely fits and the buyer is not classified: sonar calibration targets, corner-reflector arrays (the corner-reflector-array literature shows real specular design payoff, order 5 dB gains), acoustic decoys, and large-UUV specular-shape screening as an early-stage explore tool that hands off to a navy's FEM certifier. Pair that with the Q-operator sonar-array-excitation optimization, which is a clean reuse of the ECBF QCQP machinery. This is a real niche but a small one, and it is a feature inside someone else's naval toolchain, not a company.

**Biggest risk.** The market is closed and classified for the only application (quiet hulls) big enough to matter, and the spin-off cannot legally or practically reach it. Every path that stays open (commercial fisheries, calibration targets, AUV sensing) is either the wrong physics regime or too small to fund a team.

**What would have to be true to upgrade.** All three at once: (1) a cleared defense-prime partner who fronts the classified market and just licenses AEGIS as the fast explore layer, (2) an accepted validation story where PO-specular-only is explicitly the design-screen and a coupled elastic FEM is the certifier downstream, and (3) a beachhead in the open commercial acoustic-target / reflector-array / sonar-array-design niche to survive while the defense channel matures. Absent a cleared prime, I would not chase this.

## Sources

- [Target echo strength modelling at FOI, incl. BeTSSi II workshop (arXiv 1604.02257)](https://arxiv.org/pdf/1604.02257)
- [BeTSSi II benchmarking workshop on target echo strength, FOI report FOI-R--4086--SE](https://www.foi.se/en/foi/reports/report-summary.html?reportNo=FOI-R--4086--SE)
- [BeTSSi II submarine target strength modeling workshop, UACE2017 proceedings](https://www.uaconferences.org/docs/2017_papers/391_UACE2017.pdf)
- [Acoustic scattering by a submarine: benchmark TS simulation workshop results](https://www.researchgate.net/publication/27256874_Acoustic_scattering_by_a_submarine_Results_from_a_benchmark_target_strength_simulation_workshop)
- [Investigation and numerical simulation of acoustic target strength of an underwater submarine vehicle (Helmholtz-Kirchhoff + FEM)](https://www.researchgate.net/publication/365950545_Investigation_and_Numerical_Simulation_of_the_Acoustic_Target_Strength_of_the_Underwater_Submarine_Vehicle)
- [JAX-BEM: gradient-based acoustic shape optimisation via a differentiable BEM (arXiv 2604.21431)](https://arxiv.org/pdf/2604.21431)
- [Differentiable point scattering models for efficient radar target characterization (arXiv 2206.02075)](https://arxiv.org/pdf/2206.02075)
- [Radar cross section analysis using physical optics applied to marine targets](https://www.researchgate.net/publication/276264056_Radar_Cross_Section_Analysis_Using_Physical_Optics_and_Its_Applications_to_Marine_Targets)
- [Acoustic scattering characteristics of underwater corner reflector linear arrays (PMC11991147)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11991147/)
- [Elastic loss characteristics of acoustic echoes from underwater corner reflectors (PMC12197120)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12197120/)
- [Anechoic tile (Wikipedia)](https://en.wikipedia.org/wiki/Anechoic_tile)
- [Design and testing of a novel Alberich anechoic acoustic tile](https://www.researchgate.net/publication/288614716_Design_and_testing_of_a_novel_alberich_anechoic_acoustic_tile)
- [Anechoic coating design knowledge fields, Uitdenbogerd, UACE2019](https://www.uaconferences.org/docs/2019_papers/UACE2019_1054_Uitdenbogerd.pdf)
- [From local structure to overall performance: design of an acoustic coating (MDPI Materials)](https://www.mdpi.com/1996-1944/12/16/2509)
- [Accuracy of Kirchhoff-approximation vs FE for fish swimbladder scattering (PMC3653833)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3653833/)
- [Target strength in fisheries acoustics (Springer)](https://link.springer.com/chapter/10.1007/978-94-017-1558-4_6)

## AEGIS internal references

- `theory/q_complement.tex` - Q_re reflection/scattered-power operator (def:Qref, section "The reflection operator"), the acoustic-RCS object under an impedance swap. IMPLEMENTED as theory.
- `src/aegis/coherent/exposure_operator.py`, `src/aegis/coherent/ecbf.py` - the Hermitian-Q QCQP / eigenproblem machinery a differentiable TS array-excitation optimizer would reuse directly. IMPLEMENTED.
- `src/aegis/kernels/fock.py`, `src/aegis/kernels/level6_diffraction.py` - creeping-wave and edge-diffraction kernels that push slightly past naive PO. IMPLEMENTED but address geometric diffraction, not elastic-shell structural acoustics.
- Elastic Lamb/flexural returns, structural resonances, resonant anechoic coatings - NOT implemented and outside the assumption ladder. These are the certify-grade physics that AEGIS structurally cannot provide.
