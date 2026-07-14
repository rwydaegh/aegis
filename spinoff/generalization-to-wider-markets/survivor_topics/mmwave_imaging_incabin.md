# mmWave imaging and automotive in-cabin radar

Honest feasibility read for two body-EM-sensing markets that sit inside AEGIS's best physical regime. Both read the scattered-power operator Q_re instead of the absorbed operator Q_ab, and both keep the human body as the target, so there is essentially zero physics-transfer risk. The question is not the physics. It is whether the product (a differentiable forward model, a synthetic-data generator, a sensor-placement optimizer) is something imaging and automotive buyers will pay for, or something they roll themselves.

Solo author, first-person. Grades at the end of each section.

## What is reused vs what is new

The forward model is shipped. AEGIS already computes body surface scattering: the mesh, the local frame n_hat(r), directivity, Fresnel coefficients, and the quadratic operators live in `src/aegis/` and are validated in `papers/TAP_paper/paper.tex`. The scattered-power channel and its Gram, the operator Q_re, and the Kirchhoff dual that turns Q_ab into a receive operator are worked out in `theory/q_complement.tex` (sections "A scattered-power channel matrix and its Gram", "Kirchhoff dual: Q_ab is also a receiver", and the JSAC-duality sketch). So a scanner or radar would REUSE the forward scatter and gain almost nothing new on that axis.

What is genuinely new for these markets is the inverse and the design layer:
- the reconstruction / inverse operator (image from scattered field), which AEGIS does not ship,
- the sensor and illuminator placement optimizer (differentiable through the forward model),
- physically accurate synthetic signature generation for training learned classifiers.

That split matters for the verdict. AEGIS is not selling an imager or a radar. It is selling the fast differentiable body forward model that sits underneath one, plus the optimization that the forward model unlocks. IMPLEMENTED = body scatter forward model. ASPIRATIONAL = reconstruction, placement optimizer, synthetic-data product.

## Assumption ladder, both apps sit in the home regime

- A1 linear superposition holds. Gives the Q calculus.
- A2 first-bounce dominates. Largely valid for a human body at 24 to 100 GHz. The caveat, from `q_complement.tex` section "Where the book-keeping breaks down", is multi-bounce between body parts (torso onto arm) and clothing. The note already gives the Neumann-series correction Q_ab^(inf) = Q_ab + Q_ab R Q_re + ... with convergence bounded by mean albedo times self-visibility. So multi-bounce is a known, bounded, addressable correction, not a wall.
- A3 surface confinement. This is the key one and it holds hard at mmWave. See the skin-depth number below. This is AEGIS's exact home regime.
- A4 locally planar, A5 pseudo-Brewster. Both apply to tissue. `q_complement.tex` gives the mean mmWave body albedo as roughly 1 - T0, about 0.37, so the body reflects roughly a third of incident power specularly, which is exactly the signal a scanner or radar reads.

Bottom line on physics: both apps are in AEGIS's single-bounce pseudo-Brewster regime, the same regime the monograph and the TAP paper validate. No new physics is needed to produce a forward signature.

## Light calculations

### Wavelengths and why the scanners live where they live

- 24 GHz: lambda = c/f = 3e8 / 24e9 = 12.5 mm.
- 30 GHz: lambda = 10 mm.
- 60 GHz: lambda = 5.0 mm.
- 70 GHz: lambda = 4.28 mm.
- 80 GHz: lambda = 3.75 mm.

Airport walk-through scanners (Rohde and Schwarz QPS, L3 ProVision) operate in the 70 to 80 GHz band precisely because concealed-object detection needs millimeter cross-range resolution. A knife or a ceramic blade under clothing is a few mm across, so you need lambda of a few mm.

### Resolution vs aperture

Near-field aperture imaging gives cross-range resolution of order

  delta_x ~ lambda * R / (2 D)

for a synthetic aperture of extent D at standoff R, and it saturates near the diffraction floor delta_x ~ lambda / (2 sin(theta_max)) when the aperture subtends a wide angle. A body scanner has a roughly 1 m by 0.7 m panel at R ~ 0.3 to 0.5 m, so theta_max is large and resolution approaches lambda/2. At 75 GHz that is about 2 mm cross-range. That is the whole reason the band is 70 to 80 GHz: it buys mm-scale imaging of concealed objects. Down-range (depth) resolution is set by bandwidth, delta_R = c/(2B); a 10 GHz sweep gives delta_R = 3e8/(2e10) = 15 mm, coarse in depth, which is why these systems are essentially 2.5D surface imagers, not tomographs. That coarse-depth, fine-cross-range profile is exactly a surface-scattering regime, which is what AEGIS models.

### Skin depth, confirming A3

Dry skin at 60 GHz has roughly eps_r ~ 8 - j*10, giving a field penetration (skin) depth on the order of 0.4 to 0.5 mm, and it drops further toward 0.3 mm near 100 GHz. Sub-millimeter penetration against a body feature scale of cm means the interaction is a thin-surface Fresnel reflection. A3 (surface confinement) is not an approximation here, it is physically exact. This is the single strongest reason both apps are AEGIS home turf: the codebase confines the interaction to the surface, and at mmWave the physics does too.

### In-cabin, the real discriminant is micro-Doppler not static RCS

At 60 GHz, lambda = 5 mm. Human skin at 60 GHz behaves like a strong near-conductive specular reflector (confirmed in the mmWave-reflection literature), so a broadside adult torso presents an RCS on the order of 0 dBsm (order 1 m^2), a small child perhaps -5 to -10 dBsm, and an empty fabric-and-foam seat lower and geometry-dependent. But static RCS is a weak classifier: it swings tens of dB with pose and aspect, and a slumped adult can look like a big child. The signal that actually separates a living child from a bag or an empty seat is vital-sign micro-Doppler.

A chest wall moving by d over one breath produces a radar phase swing

  delta_phi = 4*pi*d / lambda.

For an infant chest excursion d ~ 1 mm at 60 GHz, delta_phi = 4*pi*1/5 = 2.5 rad, trivially detectable. Breathing rate separates further: infants at roughly 30 to 40 breaths/min against adults at 12 to 20. So in-cabin classification is a range-angle occupancy volume plus a micro-Doppler vital-sign fingerprint, not a static cross-section. This is the important honest point for the fit: AEGIS's forward model is a STATIC surface-scattering model. It nails the geometry, the specular return, the occupancy footprint, and the antenna placement, but it does NOT natively produce the breathing micro-Doppler time series that the classifier keys on. That requires animating the mesh (a moving chest surface) and running the forward model per frame. Feasible, since the forward model is fast and differentiable, but it is real added work, not a free readout.

## Incumbents and the gap, application A: mmWave and THz imaging

Who builds the scanners: Rohde and Schwarz (QPS walk-through family, 70 to 80 GHz), L3Harris (ProVision), Smiths Detection, and various THz NDT vendors. Their reconstruction is dominated by fast wavenumber-domain / holographic SAR back-projection: range-migration and Fourier-domain focusing that assume free-space propagation and treat the body as a collection of independent point scatterers. My searches on reconstruction surfaced exactly this family: holographic imaging systems, Ka-band LFM holographic imaging, near-field back-projection focusing operators, and MIMO-SAR FMCW 3D reconstruction. The common thread is that the forward model baked into the reconstruction is crude on purpose: point scatterers or a first-order physical-optics kernel, chosen because it inverts in closed form and runs fast.

Where a differentiable physics forward model is a real gap: the fast-growing branch is learned and optimization-based reconstruction, and my searches confirm this is an active, hot area (differentiable SAR renderers with analytic gradients back-propagating from image to target geometry and scattering, differentiable ray tracing to learn surface scattering parameters from SAR, neural volumetric FMCW reconstruction, hybrid-learning mmWave imaging). Every one of these needs a differentiable forward model, and the ones in the literature build ad-hoc renderers. AEGIS ships an accurate, validated, differentiable body-specific forward model. That is a genuine and defensible edge over a point-scatterer kernel: a better forward operator means better learned reconstruction, better resolution out of the same hardware, and physically correct synthetic training pairs (scene, image) that these pipelines are starved for.

Where it breaks, honestly:
- Concealed-object detection is the actual airport use case, and the object under clothing is NOT a human body. AEGIS models the body superbly and the concealed object not at all. You would be selling the accurate-body-background half of a two-part problem (body plus foreign object). Useful (a good body prior helps anomaly detection) but it is not the whole imager.
- Clothing is a dielectric layer between antenna and skin. AEGIS's single-surface Fresnel model does not natively do the through-fabric multilayer transmission that concealed-object imaging depends on. This is the A2/A4 caveat biting where it hurts most for this specific market.
- Multi-bounce (arm-to-torso) matters for a full-body image and is the bounded correction from `q_complement.tex`, addressable but not free.

## Incumbents and the gap, application B: automotive in-cabin radar

The regulatory tailwind is real and specific. Euro NCAP updated its 2023 protocol to require child presence detection for a full five-star rating, worth up to four points for two-row direct-sensing CPD, and the requirement keeps ratcheting through 2025 and 2026. Direct sensing means detecting breathing, heartbeat, or movement, across all seat positions, which is exactly what 60 GHz radar does. That is a hard, dated, money-linked mandate, not a maybe.

Who supplies it: Vayyar (60 GHz single-chip in-cabin radar, explicitly positioned for Euro NCAP CPD compliance), Infineon (BGT60 60 GHz family and an in-cabin monitoring system product line), and Texas Instruments (mmWave radar sensors with a 4x4 array and on-chip neural-net classification, marketing ~98% human-vs-object accuracy). These are silicon and system vendors with their own DSP and ML stacks. My searches also confirm the pain point AEGIS could address: multiple groups build simulation frameworks to generate synthetic 60 GHz radar training data (a 60 GHz indoor-radar deep-learning simulation framework, RadSimReal physical radar simulation, RACPIT synthetic-data augmentation for human activity classification). They do this because real labeled in-cabin data (especially of children, which you cannot ethically collect at scale) is scarce and expensive. Synthetic data is a known, acknowledged, actively-pursued need.

Where AEGIS fits: the best-in-class human body forward model can generate physically accurate synthetic radar signatures (occupancy footprint, specular return, and with an animated chest, vital-sign micro-Doppler) across body sizes, poses, and seat positions, plus optimize antenna placement in the cabin (differentiable through the forward model, a natural fit for AEGIS's placement-optimization angle). The child-vs-adult-vs-seat classification margin is a data problem, and AEGIS could feed it better physics.

Where it breaks, honestly:
- The classifier keys on micro-Doppler, and AEGIS is a static scatterer. Producing the training data means animating the mesh and running the forward model per frame. Doable and fast, but it is a build, and the existing synthetic-data frameworks (RadSimReal, the 60 GHz sim, RACPIT) already do a serviceable job with simpler human models. AEGIS's edge is fidelity, and the honest question is whether the classifier accuracy is already good enough (TI claims 98%) that better physics does not move the business needle.
- The cabin is a metal box, so multipath and cavity resonance dominate the channel. First-bounce-dominates (A2) is weaker inside a reflective cavity than in free space. This is arguably the biggest physics caveat for B: the body scatter is home turf, but the cabin around it is not, and the incumbents' whole value is handling that messy cavity channel empirically.
- The buyers are silicon vendors with deep in-house DSP and ML teams. They roll their own. Selling them a forward-model library is a tools sale into sophisticated buyers who may not want a dependency.

## Strategic read

Both apps carry zero physics-transfer risk. This is the same body-scattering computation AEGIS already ships and validates, just reading Q_re instead of Q_ab, and both sit in the single-bounce pseudo-Brewster mmWave regime the monograph was built for. The physics is not the risk. The product is.

The honest tension is the same for both: AEGIS is selling a forward model / synthetic-data generator / placement optimizer, and both markets are served by sophisticated incumbents (R&S and L3 in imaging, Vayyar/Infineon/TI in automotive) who build their own reconstruction and DSP. The value is real (a better differentiable forward model beats point-scatterer kernels, and better synthetic data beats simplistic human models) but it is a component sale or a tools/IP-licensing sale into buyers with strong in-house teams, not a product they are missing. That caps it at feature-or-component scale unless the fidelity edge is large enough to change accuracy in a way they cannot match.

Reachability. Airport scanners (R&S QPS) are literally in the RF-EMF backyard: the same 70 to 80 GHz band, the same company universe, the same body-scattering physics AEGIS already talks about publicly. That is the most reachable incumbent relationship of anything in the survivor set. In-cabin is a longer, slower automotive-tier-1 sales cycle but has the mandate pulling it.

Dual-use and privacy. Body scanners are a security / surveillance technology. A differentiable body model that improves concealed-object imaging carries export-control and privacy sensitivity that a dosimetry-compliance tool does not. This is a reputational and regulatory flag for a university spin-off, worth a conscious decision before pursuing A hard. In-cabin radar is comparatively clean (safety mandate, private cabin, no imaging of the body's surface detail).

## Verdicts

### A: mmWave and THz imaging -- CONDITIONAL

Strongest angle: sell the differentiable, validated body forward model as the physics engine underneath learned / optimization-based reconstruction, where the whole field currently improvises ad-hoc renderers and point-scatterer kernels. AEGIS's forward model is measurably better than what these pipelines use, and R&S is a reachable, same-band, same-backyard partner.

Biggest risk: the airport use case is concealed-object detection, and the object is not a body. AEGIS models the body-background beautifully and the foreign object not at all, plus clothing is a multilayer dielectric its single-surface model does not natively handle. So it is half of the problem, dressed as a body prior. Add the dual-use/privacy overhang for a university spin-off.

What would have to be true: a scanner vendor or a reconstruction group must want a physics forward model as a component and be unable or unwilling to build one of equal fidelity, AND the body-prior half must demonstrably lift concealed-object detection (anomaly against an accurate body background), AND the spin-off must be comfortable with the security/surveillance positioning.

### B: automotive in-cabin radar -- SOLID (the stronger of the two)

Strongest angle: ride the Euro NCAP CPD mandate. AEGIS generates physically accurate synthetic radar signatures of children, adults, and empty seats across sizes and poses, solving the acknowledged and ethically-forced scarcity of real child data, and it optimizes cabin antenna placement through the same differentiable forward model. The tailwind is dated, mandatory, and money-linked, which is worth more than any imaging pitch.

Biggest risk: the classifier keys on micro-Doppler vital signs, which a static surface scatterer does not natively produce (needs an animated mesh, a real build), the reflective-cabin channel weakens the first-bounce assumption that is AEGIS's home comfort, and the buyers (Vayyar, Infineon, TI) have strong in-house ML and already use serviceable synthetic-data frameworks. The value may be a feature, not a business.

What would have to be true: better body physics must move classifier accuracy or reduce data-collection cost enough that a tier-1 or a chip vendor pays for it, the animated-chest micro-Doppler extension must be built and shown to matter, and AEGIS must accept a component/synthetic-data supplier role rather than owning the sensor. If the value is "10x cheaper compliant training data, especially for children you cannot record," that is a real business. If it is "2% more accuracy on top of TI's 98%," it is a feature.

Net: B beats A. B has a regulatory tailwind and clean positioning but likely lands as a high-value component/synthetic-data play rather than a standalone product. A is more reachable through the R&S relationship but is only half the imaging problem and carries a privacy/dual-use overhang. Neither is a physics gamble. Both are product/go-to-market gambles.

## Sources

- Euro NCAP, NIO 2023 updated safety tests (CPD added): https://www.euroncap.com/en/press-media/press-releases/nio-sets-the-bar-high-in-euro-ncap-s-newly-updated-2023-safety-tests/
- Euro NCAP protocols hub: https://www.euroncap.com/protocols/
- Vayyar, Euro NCAP child presence detection compliance (60 GHz in-cabin): https://vayyar.com/auto/solutions/in-cabin/cpd/
- Infineon in-cabin monitoring system / 60 GHz radar: https://www.infineon.com/application/automotive-in-cabin-radar
- TI in-cabin radar sensor (4x4 array, on-chip NN, human-vs-object): https://www.allaboutcircuits.com/news/ti-reveals-radar-sensor-and-audio-ics-to-elevate-auto-in-cabin-designs/
- 60 GHz indoor radar deep-learning simulation framework (synthetic data): https://www.mdpi.com/2072-4292/16/21/4028
- RadSimReal, physical radar simulation for synthetic training data: https://arxiv.org/html/2404.18150v1
- RACPIT, synthetic-data augmentation for radar human activity classification (Infineon BGT60): https://pmc.ncbi.nlm.nih.gov/articles/PMC8878229/
- Differentiable SAR renderer and target reconstruction (analytic gradients image-to-geometry): https://arxiv.org/pdf/2205.07099
- Learning surface scattering parameters from SAR via differentiable ray tracing: https://arxiv.org/pdf/2401.01175
- SpINR, neural volumetric reconstruction for FMCW radar (differentiable forward model): https://arxiv.org/pdf/2503.23313
- Near-field back-projection focusing operators for planar multistatic microwave imaging: https://arxiv.org/pdf/2603.01810
- Ka-band holographic imaging (LFM radar): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7697175/
- Vehicle occupant detection based on mmWave radar: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11175036/
