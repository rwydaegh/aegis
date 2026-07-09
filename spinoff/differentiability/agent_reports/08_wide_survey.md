# 08 wide survey: every industry that optimizes wrt an electrically large smooth object

Lens: breadth first, then ruthless grading. I am the widest net in the study. Raw list below is 60+
lines before any filter, which is the job. Then two filters (physics validity, then market), then a
ranked survivor list, then the acoustic bonus answered concretely against the code.

Claims are marked `verified` (I saw the source), `inferred` (I reasoned to it from physics or from
the code), or `could-not-check`. Unmarked = inferred.

No NEEDS_CONTEXT blocker. I used WebSearch to name incumbents; I did not need Reddit or paywalled
papers for this lens. One thing worth a Gemini Deep Research pass is flagged at the very end.

---

## 0. The one fact that organizes the whole survey

AEGIS is valid in two disjoint regimes, and they have different frequency rules. This matters
because the seed list conflates them.

- **Lossy-dielectric-transmission regime (AEGIS as coded today).** Needs skin depth much less than a
  millimetre, so roughly f > 6 GHz for tissue-like media. This is the *absorbed* half, `T0`. Narrow.
- **Conductor / coated-conductor reflectance regime (PO by electrical size, any frequency).** Valid
  whenever the object is many wavelengths across and smooth on the wavelength scale, at *any*
  frequency. This is the *scattered* half the brief flags in 2.2(a): swap transmittance for
  reflectance, evaluate the PO radiation integral toward an observer. `verified` against the code:
  `fresnel_operator.py` already computes both the geometry (`mu`, TE/TM basis) and the complex
  coefficients; today it keeps `t_s, t_p` (transmission). A reflectance variant keeps `r_s, r_p` from
  the same `_fresnel_core` call and radiates instead of absorbs. That is a coefficient swap, not new
  physics.

Almost every large market in the seed list lives in the second regime, not the first. The
dosimetry-anchored studies only ever looked at the first. That is the single biggest thing this
survey adds.

And the market fact that ties it all together, `verified` by search: the incumbents in the
electrically-large-PO space are **Ansys Savant / HFSS SBR+** (SBR + PTD + UTD + creeping wave),
**Altair Simcenter FEKO** (MLFMM + asymptotic PO/large-element-PO), **Remcom XGtd**, **CST asymptotic
(SBR) solver**, and for reflector antennas **TICRA GRASP** (which is literally PO already). Every one
of them is a *forward* solver. None of them is differentiable end to end. That absence is the wedge
for this entire report.

---

## 1. Raw list (diverge). Frequency, electrical size, PO verdict, one line

Verdict key: **VALID** (surface first-order PO applies), **PARTIAL** (applies to one sub-problem or
one regime), **NONSENSE** (wrong physics: resonant, volumetric, sub-wavelength, or needs full-wave).

EM, conductor/coated, reflectance regime (PO by size):

1. Platform RCS / radar signature of aircraft, ships, missiles, drones. 1-18 GHz, 10^2-10^4 wl. **VALID.** The canonical PO/SBR problem. Specular-dominated, PO strongest here.
2. Installed antenna performance on aircraft/ship/vehicle/satellite. 0.1-40 GHz, large. **VALID.** Savant/FEKO home turf.
3. Ship topside EMI and antenna siting. HF-SHF, large in UHF+. **PARTIAL.** VHF/UHF the mast is resonant; SHF fine.
4. Reflector / dish antenna surface-error compensation. 1-100 GHz, 10^2-10^4 wl. **VALID.** TICRA GRASP is PO. Fully lit aperture, no silhouette problem.
5. Radome shape and multilayer layup. Radar bands, large surface / half-wave wall. **VALID (surface) + local transfer-matrix (wall).** Good fit for a per-facet layered coefficient.
6. Automotive radar radome / bumper / emblem transparency. 76-81 GHz, curved surface many wl. **VALID.** Local multilayer transmission on a curved skin. High-volume civilian.
7. Wind turbine radar interference (RAM layup + blade shape). L/S/X band, blade 10-100 wl. **VALID.** Regulated EU fight, real.
8. RIS / metasurface panel on curved substrate. sub-6 to mmWave. **PARTIAL.** Macroscopic impedance-boundary model = per-facet reflection phase; element internals are sub-wl full-wave.
9. Corner reflectors, calibration targets, Luneburg lenses. Any radar band, large. **VALID** but a solved, low-value design problem.
10. SAR / ISAR of ships, ice, buildings, terrain. 1-30 GHz, huge. **VALID (forward model).** Scattering prediction, an inversion target.
11. Space-debris and RSO radar/optical signature. Microwave-optical, small-to-large. **PARTIAL.** Many objects are sub-wl or resonant.
12. Drone / bird / bat detection radar. 1-10 GHz. **PARTIAL.** Birds/bats sub-wl and lossy-resonant, not smooth PO; drones VALID.
13. Weather radar and hydrometeors. S/C/X, drops sub-wl. **NONSENSE.** Rayleigh/Mie, not surface PO.
14. Automotive keyless entry, presence sensing, smart-home mmWave. sub-6 to 60 GHz. **PARTIAL.** Body sensing at 60 GHz is VALID (this is the dosimetry twin); UHF keyless is resonant NONSENSE.
15. Lightning protection. Quasi-static / kHz. **NONSENSE.**
16. EMC of large enclosures, cavity resonance. Broadband. **NONSENSE.** Resonant interior, needs full-wave/statistical.
17. Reverberation chamber design. GHz, overmoded cavity. **NONSENSE** for PO (statistical field, not deterministic surface).
18. Anechoic chamber absorber layout / quiet-zone. GHz+, large. **PARTIAL.** Absorber ferrite/pyramid is resonant; wall-bounce geometry is PO-able.
19. 5G/6G OTA and near-field test-range chamber design. mmWave. **PARTIAL.** Same as 18.
20. 5G/6G network planning with body/vehicle blockage. 3.5-60 GHz. **PARTIAL.** Blockage geometry VALID at mmWave (this is AEGIS's own ray-trace bridge); building multipath is a ray-tracer job, not PO surface.

EM, lossy-dielectric-transmission regime (AEGIS as coded):

21. Human mmWave dosimetry / pre-compliance. 6-100 GHz. **VALID.** The existing product. Out of remit here (section 5 of brief).
22. THz / mmWave airport body scanners. 24-100 GHz. **VALID.** Body is the lossy scatterer, this is a sensing/imaging inverse of AEGIS.
23. Industrial mmWave heating / drying / curing. If 24-100 GHz VALID; but most industrial is 2.45 GHz **NONSENSE** (volumetric).
24. Food processing uniform heating. 0.915 / 2.45 GHz. **NONSENSE.** Volumetric penetration, wrong physics (seed list already flags this).
25. Medical hyperthermia / RF ablation / catheters. 0.4-2.45 GHz, near-field. **NONSENSE.** Deep penetration, near-field, small vs wl.
26. MRI bore / coil / B1 shimming. 64-300 MHz. **NONSENSE for PO** (this is the VOP world, already dead per brief section 5).
27. Microwave imaging (breast, brain). 1-10 GHz. **NONSENSE.** Diffraction tomography, penetrating, inverse-scattering not PO.

EM, resonant / sub-wavelength / cavity (PO invalid, listed to kill fast):

28. Particle-accelerator RF structures. Cavity eigenmodes. **NONSENSE.**
29. Fusion ICRH antennas / plasma-facing components. MHz, plasma. **NONSENSE.**
30. Ground-penetrating radar, concrete/rebar imaging. sub-GHz, penetrating. **NONSENSE.**
31. NDT eddy-current / microwave. kHz-GHz. **NONSENSE** (near-field/penetrating).
32. Wireless power transfer near-field. kHz-MHz coils. **NONSENSE.** Beamed WPT at mmWave is PARTIAL (a beamforming-onto-a-rectenna problem, PO-able).
33. Metamaterial-absorber / FSS unit-cell design. Resonant. **NONSENSE** for PO; the *macro* array on a curved body is PARTIAL (same as RIS).

Acoustic / elastic analogues (scalar Kirchhoff-Helmholtz):

34. Transcranial HIFU aberration correction through skull. 0.2-1.5 MHz, skull 10-100 wl. **VALID (scalar).** Phased-array focus through a lossy layer.
35. HIFU / focused-ultrasound tumour ablation, general. 1-3 MHz in tissue. **VALID (scalar)** for the transducer-to-tissue interface; volumetric heating is a separate solver.
36. Sonar target strength of ships/subs/mines. 1-100 kHz in water, targets many wl. **VALID (scalar, fluid).**
37. Ultrasonic NDT of metals/composites. 1-20 MHz. **PARTIAL.** Fluid-coupled surface VALID; shear-mode conversion in solids breaks scalar model.
38. Room / architectural acoustics. audible, high-f geometric. **PARTIAL.** High-frequency surface reflection VALID; modal low end NONSENSE.
39. Underwater acoustic comms / beamforming. kHz. **VALID (scalar)** as a channel-shaping problem.
40. Loudspeaker / horn / array directivity on a baffle. audio-ultrasonic. **PARTIAL.**

Optical / lidar analogues:

41. Automotive/robotics lidar signature and retroreflector design. 905/1550 nm, huge in wl. **VALID (PO/GO)** but a crowded rendering field.
42. Optical scatterometry / surface metrology. visible-IR. **PARTIAL.** Smooth-surface VALID; sub-wl gratings NONSENSE.
43. Radio-astronomy dish surface metrology / holography. GHz, huge. **VALID.** Same as item 4.
44. Stray-light / baffle design in telescopes. optical. **PARTIAL** (GO/PO ray, crowded by Zemax/FRED).
45. Solar-concentrator / heliostat surface-error. optical, huge. **VALID (GO)** but not an EM sale.

Extra breadth (the "extend by double" mandate):

46. Satellite mega-constellation inter-satellite and feeder-link antenna placement on bus. Ka/V band. **VALID.**
47. Aircraft de-icing / conformal-antenna integration under a skin. mmWave. **VALID.**
48. Hypersonic vehicle antenna windows and plasma-sheath radome. radar+. **PARTIAL** (plasma sheath is a volumetric mess).
49. Naval integrated-mast (APAR-style) mutual coupling and blockage. SHF. **VALID.**
50. Vehicle-to-everything (V2X) rooftop shark-fin antenna co-siting. sub-6/mmWave. **PARTIAL.**
51. Ground-station / VSAT reflector panel adjustment. Ku/Ka. **VALID.**
52. RCS of urban infrastructure for 6G ISAC (integrated sensing and communication). mmWave. **VALID.** The 6G sensing layer is exactly "scatter off large smooth things."
53. Automotive radar ghost-target / multipath off guardrails and trucks. 77 GHz. **VALID.** PO scattering scene for radar-perception training data.
54. Wearable / on-body antenna detuning by the human body. mmWave. **VALID** (dosimetry twin, sensing side).
55. Cochlear/hearing-aid ultrasonic and RF coupling. small. **NONSENSE.**
56. Wind-farm weather-radar clutter *prediction* for siting approval (not blade design). L/S band. **VALID (forward)** and it is the regulatory deliverable, distinct from item 7.
57. Radar-absorbing-structure (RAS) layup for UAV/loyal-wingman skins. X-Ku, large. **VALID.** High-dim coating design.
58. Conformal load-bearing antenna (CLAS) shape + feed co-design. VHF-SHF. **PARTIAL.**
59. Spacecraft multipactor / passive-intermodulation on large reflectors. microwave. **NONSENSE for PO** (it is a surface-physics/power problem, not scattering).
60. Ice-accretion radar signature change on turbine/aircraft (condition monitoring). radar. **VALID (forward/inverse).**
61. Sports / livestock / gait micro-Doppler radar. 24-60 GHz. **PARTIAL.** Body sensing VALID; the value is in Doppler ML not surface PO.
62. Terahertz security material ID and concealed-object imaging. 0.1-1 THz. **VALID (surface).**
63. Beamed power to rectenna arrays (space solar / drone recharge). 5.8/24 GHz. **VALID.** Aperture-to-aperture PO focusing with a large collector.
64. Acoustic-lens / metalens design for ultrasound (scalar). MHz. **VALID (scalar).**

That is 64 lines. Roughly 30 VALID or PARTIAL, ~15 outright NONSENSE, the rest sensing/inverse
variants of the same operator.

---

## 2. Physics filter: what survives, grouped

Kill fast (NONSENSE, wrong physics, do not revisit): food/industrial 2.45 GHz heating (24, 23),
hyperthermia/ablation/MRI/microwave-imaging (25, 26, 27), accelerator/fusion/GPR/eddy-current
(28-31), near-field WPT coils (32a), unit-cell FSS internals (33a), reverb/EMC cavities (16, 17),
weather-radar hydrometeors (13), bird/bat targets (12a), lightning (15), keyless UHF (14b),
multipactor/PIM (59), hypersonic plasma sheath (48b). These are volumetric, resonant, sub-wavelength,
near-field, or penetrating. PO is nonsense for all of them. Moving on.

The physics survivors collapse into **six families**:

- **F1. Signature / RCS + installed-antenna co-design on platforms.** Items 1, 2, 3(SHF), 46-49, 51,
  57, 58. One operator, one market cluster (aero/defense/space).
- **F2. Reflector and dish surface-figure compensation.** Items 4, 43, 51. TICRA GRASP is the PO
  incumbent, which is unusually clean.
- **F3. Radome / radar-transparent-skin layup.** Items 5, 6 (automotive), 47. Local multilayer
  transmission on a curved surface. Two sub-markets: defense radomes and 77 GHz automotive.
- **F4. Wind-turbine radar mitigation and siting.** Items 7, 56, 60. Regulated, EU, niche.
- **F5. RIS / metasurface / beamed-power aperture shaping.** Items 8, 33b, 63. High element count,
  differentiable phases, but PO is only the macroscopic model.
- **F6. Acoustic PO (scalar Kirchhoff).** Items 34-39, 64. The bonus. A kernel swap, analyzed in
  section 5.

Sensing/imaging inverses (10, 22, 52, 53, 62) share the operator but are a different business shape
(data/perception, not design). I treat them as an upside adjacency, not a ranked survivor, because
the customer there buys a dataset or a chip, not a design tool.

---

## 3. Market filter and the four mechanisms, applied per family

For each: design-vector dimension (mechanism a needs > ~10), which of the four brief mechanisms fires,
the named incumbent, EU/two-person reachability, and whether differentiability is *essential* or
*decorative*. The last is the whole study.

### F1. Platform signature + installed-antenna co-design
- Design vector: **very high.** Per-facet coating impedance (RAM stackup) is 10^4-10^5; add shape
  morph and antenna placement. Mechanism (a) fires hard, plus (b) inversion (fit measured RCS to
  recover coating) and (d) certified worst-case-over-aspect-angle supremum. `inferred`.
- Incumbent: **Ansys Savant/SBR+, Altair FEKO, Remcom XGtd, CST asymptotic.** `verified` by search.
  None differentiable. A gradient wrt 10^4 coating cells is where a differentiable PO annihilates a
  forward solver plus a genetic algorithm.
- Reachability: **poor for the obvious buyer.** This is defense/aero. EU has non-ITAR primes (Airbus,
  Dassault, Saab, Leonardo, Thales, MBDA) so it is not US-supply-chain-gated the way the military RF
  study was, but a two-person BV selling signature-optimization to primes is a long, cleared,
  slow-procurement sale. `inferred`.
- Differentiability: **essential.** 10^4 parameters, no sweep survives.
- Ethics: in scope. Brief section 4 explicitly admits "survivability and signature management of
  platforms." This is defensive signature reduction, not lethality. Clean.

### F2. Reflector / dish surface-figure compensation
- Design vector: **medium-high.** Deformable-reflector actuator commands or panel adjusters, 10^2-10^3;
  for a shaped-reflector synthesis, the surface expansion coefficients, 10^2-10^3. Mechanism (a) and,
  strongly, (b) inversion: recover the surface error from a measured far-field (antenna holography is
  exactly this) and (c) exact sensitivity of gain/sidelobe to each panel. `inferred`.
- Incumbent: **TICRA GRASP / CHAMP** (PO reflector-antenna suite, ESA-heritage) and **Ansys HFSS
  reflector flows.** `verified` GRASP is PO; `could-not-check` whether GRASP exposes any adjoint. I
  believe it does not (it is a forward PO integral-equation tool). `inferred`.
- Reachability: **good.** Space/satcom is EU-strong (ESA, Airbus DS, Thales Alenia Space, and TICRA
  itself is Danish). Academic-to-industry sale, not cleared-defense. A two-person team can credibly
  ship an adjoint layer for reflector synthesis. `inferred`.
- Differentiability: **essential and least risky.** Here is the ranking argument the brief's section
  2.3 demands: a reflector aperture is **fully illuminated**, there is no silhouette or shadow
  boundary in the working region, so `∇(PO)` is furthest from the region where PO's edge/creeping
  errors corrupt the gradient. Of all survivors this one is the most defensible against "the deepest
  technical risk." That is a real, specific, physics-grounded advantage, not marketing.

### F3. Radome / radar-transparent-skin layup (defense radome + 77 GHz automotive)
- Design vector: **high.** Per-zone layer thicknesses and permittivities on a curved skin, 10^2-10^4.
  Mechanism (a) plus (c) exact sensitivity coefficients, which is the certification hook: automotive
  radar radomes must hold boresight-error and transmission-loss budgets, and IEC/OEM specs want the
  sensitivity of those to layer tolerance. `inferred`.
- Incumbent: **CST Studio, Ansys HFSS, Altair FEKO** for the EM, plus in-house OEM tools. `verified`
  FEKO does radome analysis. None differentiable. `inferred`.
- Reachability of the **automotive** sub-market: **excellent and this is the surprise.** 76-81 GHz is
  squarely in AEGIS's as-coded lossy/dielectric regime, the surface is smooth and many wavelengths,
  and the Tier-1 buyers are **EU** (Bosch, Continental, ZF, Valeo, HELLA, Marelli). The bumper/paint
  stack in front of an automotive radar detunes and squints it; designing the local layup and the
  local thickness to preserve the beam is a real, high-volume, recurring pre-compliance problem. It
  is the same *shape* of business as the mmWave device pre-compliance beachhead the brief says is
  already presumed, but for a different, larger customer. `inferred`.
- Differentiability: **essential for the shape/layup dimension**, decorative for a single-stack
  design (which is a 1D transfer-matrix sweep). The value is when thickness varies across a curved,
  painted, multi-material bumper: then it is a high-dim per-facet fit.

### F4. Wind-turbine radar mitigation and siting
- Design vector: **medium.** RAM layer stackup on the blade (10^1-10^3) plus blade-shape tweaks
  constrained by aerodynamics. Mechanism (a) and (b). `inferred`.
- Incumbent: **Remcom XGtd, ATDI HTZ** (siting/coverage), **QinetiQ** (stealth-blade consulting),
  **Sandia WTRIM** (US gov program). `verified` by search.
- Reachability: **real but small.** This is a live, regulated European fight (aviation and weather
  radar vs onshore wind), so the pain is genuine and the buyer is identifiable (turbine OEMs Vestas,
  Siemens Gamesa, both EU; and radar authorities). But it is a consulting-sized market, and QinetiQ
  plus the OEMs' own RAM work already occupy it. `inferred`.
- Differentiability: essential for the coating layup, but the aero constraint caps the shape
  dimension hard, and much of the win is material selection (discrete, not gradient-friendly). Middle
  of the pack.

### F5. RIS / metasurface / beamed-power aperture
- Design vector: **very high.** 10^3-10^4 element phases. Mechanism (a) screams. `inferred`.
- Incumbent: **fragmented.** No dominant vendor; academic plus startups (Greenerwave, Pivotal
  Commware history, Metawave). `could-not-check` current market leader. This is a red flag by the
  brief's own rule: if you cannot name who they buy from, it may not be a market yet.
- Differentiability: essential in dimension, but **PO is the wrong-altitude model.** A RIS element is
  a sub-wavelength resonator; PO only captures the macroscopic impedance boundary. AEGIS would model
  the *panel-scale* phase profile, not the element, and the element design (where the real
  engineering and IP sit) needs full-wave. So the differentiable-PO contribution is thin. Downgrade.

### F6. Acoustic PO
- Analyzed concretely in section 5. Physics survives cleanly for fluid media (HIFU, sonar). The
  question the brief asks is whether it is a rewrite or a one-function swap. Answer: swap.

---

## 4. Ranked survivors (converge)

Physics filter left six families. Market filter (real pain, nameable incumbent, EU-two-person
reachability, differentiability *essential*) ranks them:

**1. Reflector / dish surface-figure compensation (F2).**
The cleanest fit in the entire survey. The incumbent (TICRA GRASP) is *already a PO code*, so there
is zero "is PO valid here" argument to win, and the customer already trusts PO numbers. AEGIS adds
the one thing GRASP lacks: exact gradients of far-field metrics wrt hundreds of surface/panel
parameters, which turns holographic surface recovery and deformable-reflector control from a
finite-difference or forward-sweep loop into a single adjoint pass. It is the **only** survivor where
the working region is fully lit, so it is maximally immune to the brief's deepest risk (bad `∇PO`
near shadow boundaries). Market is EU-native (ESA, Airbus DS, Thales Alenia, TICRA is Danish),
academic-adjacent, non-cleared. Design vector 10^2-10^3. Differentiability essential. This one the
dosimetry studies never touched, and it is the safest technical bet.

**2. Automotive radar radome / bumper transparency at 76-81 GHz (F3-automotive).**
The largest *civilian, EU-reachable, recurring* market that fits AEGIS as it is coded today, not
after a reflectance rewrite. 77 GHz on a smooth curved painted bumper is exactly the lossy-dielectric
transmission regime AEGIS already implements. The pain is real and growing (every ADAS radar ships
behind a decorated fascia that squints the beam), the buyers are EU Tier-1s (Bosch, Continental, ZF,
Valeo, HELLA), and the deliverable is the same pre-compliance shape as the presumed mmWave-device
beachhead but with a bigger customer and a per-facet layup design vector (10^2-10^4). Incumbents
(CST, HFSS, FEKO) are forward solvers. Differentiability essential for the varying-thickness curved
layup, decorative for a flat single stack, so the pitch must be "curved, multi-material, per-zone."
Not considered by the dosimetry studies.

**3. Platform signature + installed-antenna co-design (F1).**
By far the biggest market and the highest-dimensional design vector (10^4-10^5 coating cells), and it
is the direct cash-out of the brief's 2.2(a) observation that AEGIS discards exactly the RCS half.
The incumbents (Savant, FEKO, XGtd) are named, dominant, and non-differentiable, so the wedge is
sharp. It ranks third only because reachability is hard: defense/aero primes, slow cleared
procurement, and a two-person BV is a hard sell into that world even in the non-ITAR EU. The
right move is not to sell a product but to co-author a benchmark with an EU academic RCS group and
let a prime pull it. Ethically in scope (defensive signature, section 4). Exposure to the deepest
risk is *moderate*: specular lobes (where the design action is) are where PO is most accurate, but
low-observable design lives in the sidelobe/shadow-boundary nulls where PO gradient is least trusted,
so the Fock-gate validation (section 6) must be shown to hold there before this is credible.

**4. Radome shape + layup for defense/aero (F3-defense).**
Same operator as (2) and (3), older and more entrenched market (nose radomes, conformal apertures).
Ranked below automotive purely on reachability: defense radome design is a cleared, prime-gated,
slow sale, whereas automotive is a commercial Tier-1 sale. Strong physics, high design vector, named
incumbents (FEKO/CST/HFSS), differentiability essential. A natural second vertical once (2) proves
the layup-gradient story on friendlier customers.

**5. Acoustic PO for transcranial HIFU aberration correction (F6).**
Kept on the ranked list, not dismissed, because the brief asked me to think about it and because the
code answer (section 5) is genuinely favourable: it is a one-function swap. The market is real
(neuro-HIFU for essential tremor, Parkinson, and blood-brain-barrier opening is a growing clinical
field), the focusing problem is a 256-to-1024-element phase-optimization through an aberrating skull
layer (design vector 10^2-10^3, mechanism a and b), and the current tooling is academic (k-Wave
full-wave, slow) plus vendor-internal planners. Incumbents: **Insightec (Exablate), Profound Medical
(Sonalleve)**; simulation backend is mostly **k-Wave** in research. `verified` the 256-channel
phased-array planning workflow exists. It ranks fifth because it is a medical-device regulatory
world (FDA/CE, clinical validation, long cycles) that a two-person EU BV cannot enter alone, and
because the AEGIS surface-PO models the *skull interface* but not the volumetric nonlinear heating,
so it is half the planner, not the whole one. Best as a research collaboration or a licensed module,
not a company.

**6. Wind-turbine radar mitigation (F4).** Real, regulated, EU, but consulting-sized and already
occupied by QinetiQ and OEM RAM programs. Keep as a warm reference application, not a spine.

**Dropped at the market filter: F5 (RIS).** High dimension but no nameable dominant incumbent (fails
the brief's market test) and PO is the wrong-altitude model for the element design where the IP lives.

---

## 5. Bonus: is the acoustic analogue a rewrite or a swap? Concrete, against the code

Answer: **a swap of one function plus dropping the polarization dimension.** Not a rewrite. Here is
the evidence, file by file, all `verified` by reading the source.

**What is EM-specific and must change (one file).** `fresnel_operator.py` is the entire vector
apparatus: `te_tm_basis()` builds `e_s, e_p` (TE/TM unit vectors), and `apply_fresnel_operator()`
projects `psi` onto them and scales by `t_s, t_p`. All of this exists only because EM has
polarization. Acoustic pressure is a scalar field. At a fluid-fluid or fluid-solid interface the
pressure reflection/transmission coefficient is a single scalar function of the incidence cosine and
the impedance ratio, `R(mu) = (Z2 mu - Z1 mu_t)/(Z2 mu + Z1 mu_t)`, structurally the same shape as
the normal-incidence Fresnel expression but with no s/p split. So `te_tm_basis()` is deleted
entirely and `apply_fresnel_operator()` collapses to a scalar multiply. That is one ~30-line function
replaced by a ~10-line one.

**What is already kernel-agnostic and does not change (everything downstream).**
- `field_channel.py`: the phase term `exp(-i k0 k_hat . r)` is `verified` scalar and identical in
  acoustics; only the constant changes, `k0 = 2*pi*f/C_0` becomes `omega/c_sound`. The `psi` array
  drops from `(N, 3)` to `(N,)` and `G` from `(M, 3, M_ant)` to `(M, 1, M_ant)` (or `(M, M_ant)`).
  One dtype/shape edit.
- `exposure_operator.py`: `Q = einsum("m,mia,mib->ab", areas, conj(G), G)` is `verified` unchanged.
  The `i` index just runs over 1 instead of 3. `eigendecompose_Q`, `lambda_max`, `compute_rho` are
  pure linear algebra on `Q` and are untouched.
- `ecbf.py` / `multibody_ecbf*.py`: the eigen-beamformer and ECBF solver operate on `Q`, so the
  entire coherent optimization layer carries over with no edit.
- The autodiff: because the caller differentiates (brief 2.1) and every downstream op is JAX linear
  algebra, the gradients wrt element phases/amplitudes (the acoustic precoder `x`) and wrt transducer
  position come for free. `inferred` from the fact that these are the same ops the EM path already
  finite-difference-validates.

**A bonus the brief did not anticipate: the diffraction layer is *more* natural in acoustics.** The
Fock gate (`kernels/fock.py`, `geometry/fock_gate.py`) already carries **soft and hard** creeping
constants (`q_F_s`, `q_F_h` in `body_channel.py:_fock_gate_factors`). Fock's original theory is
scalar, and soft/hard are exactly the acoustic **pressure-release** and **rigid** boundary
conditions. In EM these two are an approximation to the TE/TM impedance; in acoustics they are the
literal boundary conditions. So AEGIS's shadow-boundary diffraction model transfers to acoustics with
*less* approximation than it carries in its home domain. That is a genuine, checkable selling point
for the sonar/HIFU pitch. `inferred` from the code plus the `project_diffraction_fock` memory that
records the soft/hard impedance table.

**Where the scalar swap breaks (be honest).** Elastic solids (ultrasonic NDT of metal, item 37)
support shear waves and mode conversion at the interface, which a scalar pressure model cannot
represent. So the swap is clean for **fluid media only**: water (sonar), soft tissue and the
water-bath coupling in HIFU, and air (room acoustics high end). Metal NDT needs the full elastic
kernel and is out. That still leaves the two large markets (sonar, therapeutic ultrasound) intact.

Net: an acoustic AEGIS is roughly a one-file rewrite plus a shape change, not a new codebase. If
Robin wants a second product on the same operator, this is the cheapest one to prototype, and the
diffraction-layer point is a real differentiator over k-Wave (which is a full-wave FDTD-style solver,
far slower, and not built for gradient-based array design).

---

## 6. The deepest risk, mapped onto the ranking

The brief's section 2.3 (`∇PO` may point the wrong way near silhouettes) is not uniform across
survivors, and that non-uniformity *is* a ranking tool:

- **Least exposed: F2 reflector compensation.** Fully lit aperture, no shadow boundary in the
  working region. Safest.
- **Moderately exposed: F3 radome/automotive.** The beam passes through, near-boresight, where PO
  transmission is accurate; edge-of-radome diffraction is a smaller contributor. Manageable.
- **Most exposed: F1 low-observable signature.** LO design deliberately works in the deep nulls and
  shadow boundaries where PO omits PTD/creeping/travelling-wave contributions and where the gradient
  is largest and least trustworthy. This is precisely why Savant bolts PTD+UTD+creeping onto SBR. So
  F1's differentiable-PO story is *not credible until* the in-house test the brief demands (compare
  `∇PO` to `∇` of the exact Mie/cylinder solution wrt radius/frequency/angle, and check gradient
  cosine similarity near the shadow boundary) is run and passes. `inferred`. That test should be run
  before any signature-reduction claim is made to a prime.

So the risk analysis reinforces the ranking: the safest markets (reflector, then automotive radome)
are also the ones where AEGIS's approximation is most defensible, and the biggest market (signature)
is gated on a validation that has not been done.

---

## 7. What the dosimetry-anchored studies never considered (explicit, as asked)

Everything in families F1-F6 except the sensing twin of item 21. Specifically new here:

- The **reflector-surface-compensation** vertical against TICRA GRASP (item 4). Cleanest fit in the
  study, and a PO incumbent already exists to displace-by-differentiation.
- **Automotive 77 GHz bumper/radome transparency** (item 6) as the civilian, EU-Tier-1, high-volume
  twin of device pre-compliance. AEGIS runs it *as coded*, no reflectance rewrite.
- The whole **reflectance / RCS half** as concrete verticals (F1), turning the brief's 2.2(a)
  structural note into named markets and named incumbents (Savant, FEKO, XGtd).
- The **acoustic swap** proven to be one file, with the diffraction-layer-is-more-natural bonus.

The dosimetry lineage only ever optimized the absorbed `T0` half of one object class (humans). This
survey's contribution is that the *same operator* addresses the reflected half and non-human smooth
scatterers, that the incumbents there are all non-differentiable PO/SBR codes, and that two of those
verticals (reflector compensation, automotive radome) are more EU-reachable for two people than
anything in the defense-signature space the biggest market lives in.

---

## 8. One Gemini Deep Research prompt worth running

I could not verify from open search whether TICRA GRASP, Ansys Savant, or Altair FEKO expose any
adjoint / differentiable / sensitivity-gradient capability (as opposed to finite-difference
optimization wrappers). That single fact decides how wide the wedge is for F1 and F2. Suggested
prompt: *"Do any commercial high-frequency asymptotic electromagnetic solvers (Ansys HFSS SBR+ /
Savant, Altair Simcenter FEKO, Remcom XGtd, CST asymptotic solver, TICRA GRASP) provide analytic
adjoint gradients or automatic differentiation of far-field / RCS / installed-antenna metrics with
respect to geometry, coating impedance, or reflector surface parameters, as of 2026? Cite release
notes or docs. Distinguish true adjoint sensitivity from finite-difference optimization loops and
from ML surrogate add-ons."* If the answer is "none," every ranking above holds. If Ansys shipped an
adjoint, F1 narrows sharply.
