# Radome and radar-transparent-part design

Honest feasibility read on whether the AEGIS surface engine generalizes into radome design: automotive 77 GHz radar behind painted bumper fascia, aircraft nose radomes, phone back covers, antenna housings. This is the transmission side of the Fresnel surface law, the Q_in / transmission-coefficient T. We thought it would work. I pressure-tested it.

Verdict up front: **CONDITIONAL**, and the honest breakdown is more brutal than that single word. The part of the problem AEGIS already does (flat painted-stack transmission and back-reflection) is real physics but too small to be a product. The part that is a real product (curved-shell boresight error and full-pattern degradation) is a bigger build where first-bounce physical optics fights the exact effects that matter and where HFSS and FEKO are entrenched.

## 1. Two problems, not one

The task is to keep these separate, because AEGIS's competence flips between them.

### Problem (a): flat-panel transmission and back-reflection design

Minimize insertion loss and back-reflection into the radar through a layered stack (paint / primer / plastic / matching foil). This is a 1D stratified-medium transfer-matrix problem. Angle of incidence and frequency in, complex transmission t and reflection r out, differentiable in every layer thickness and permittivity.

This is exactly A4 (locally planar) with a stratified-medium transfer matrix, and it is exactly what `src/aegis/tissue/fresnel.py` already does, one layer at a time, for skin over fat. The math does not care whether the stack is skin/fat or paint/primer/TPO. AEGIS does this well. It is trivially in the wheelhouse and it is differentiable today.

### Problem (b): full curved-radome electromagnetic performance

Boresight error (apparent angular shift of a target), beam deflection, main-lobe gain loss, sidelobe degradation, flash lobes off the radome shoulder, and their variation over scan angle. This needs the surface integral of the transmitted complex field over the curved dielectric shell, followed by coherent recombination into the far-field pattern. This is where AEGIS's assumption ladder starts to bleed:

- A2 (first bounce dominates) misses multiple reflections bouncing between the antenna aperture and the concave inner wall, tip and joint diffraction at the radome apex, and creeping/edge contributions. These are precisely the mechanisms that generate boresight error slope and flash lobes, the numbers a radome engineer is paid to control.
- The per-point wall response itself is fine under A4 (each patch sees a locally planar multilayer), and AEGIS already carries complex amplitude transmission (`fresnel_amplitude` returns complex `t_s`, `t_p`), so the phase that tilts the wavefront is representable. The gap is not the local law. The gap is everything the first-bounce assumption throws away in the recombination.

So: AEGIS does the local wall response and the coherent surface integral. AEGIS does not, without extra machinery, capture antenna-to-wall multibounce and tip diffraction, and those are the residual that separates a 4 mrad prediction from a measured 6 mrad.

## 2. Light calculations for 77 GHz automotive

Wavelength in air at 77 GHz: lambda_0 = c/f = 3e8 / 77e9 = **3.90 mm**.

### Half-wave matching condition

A lossless dielectric slab is reflectionless when its thickness is a half-integer number of wavelengths in the dielectric. Wavelength in the wall is lambda_d = lambda_0 / sqrt(eps_r), and the transparency condition is

    d = m * lambda_0 / (2 * sqrt(eps_r)),  m = 1, 2, 3, ...

For polycarbonate-class bumper plastic, eps_r ~ 2.9, sqrt(eps_r) = 1.703, so lambda_d = 2.29 mm and the half-wave increment is **1.14 mm**. A real bumper wall of 2.3 to 3.4 mm is 2 to 3 of these half-waves. This is why bumper thickness is a designed radar parameter, not an afterthought.

### Insertion loss sensitivity to thickness

Computed for three plausible wall permittivities (single-interface power reflection R_face, worst-case slab reflection R_max at quarter-wave detuning, worst-case insertion loss, and the quarter-wave detuning distance):

| eps_r | n = sqrt(eps_r) | lambda_d (mm) | half-wave (mm) | R_face | R_max slab | worst IL (dB) | quarter-wave (mm) |
|-------|-----------------|---------------|----------------|--------|------------|---------------|-------------------|
| 2.5   | 1.581           | 2.46          | 1.23           | 0.051  | 0.184      | 0.88          | 0.62              |
| 2.9   | 1.703           | 2.29          | 1.14           | 0.068  | 0.237      | 1.18          | 0.57              |
| 3.5   | 1.871           | 2.08          | 1.04           | 0.092  | 0.309      | 1.60          | 0.52              |

Read the eps_r = 2.9 row. Perfectly matched, the wall reflects nothing and insertion loss is just dielectric absorption. Detune the thickness by a quarter-wave-in-dielectric, about **0.57 mm**, and up to **24%** of the power reflects, roughly 1.2 dB one-way, ~2.4 dB round trip. A thickness error of one eighth-wave, ~0.29 mm, already moves you a large fraction of that swing. Injection-molded bumper tolerances are near this scale, which is why the industry adds a thin matching foil (0.1 to 1 mm, confirmed in the Tier-1 patent literature below) to buy back the margin. That thickness, and the foil permittivity, is exactly the differentiable knob: minimize |r_stack(angle, f)|^2 plus insertion loss over {d_i, eps_i} with the transfer matrix, closed-form gradient dIL/dd_i. AEGIS can do this. So can a photonics grad student in an afternoon (see section 3).

### The paint problem is a material problem, not an optimization problem

A primer/basecoat/clearcoat stack is ~50 to 150 microns total. At eps ~ 3 that is lambda_d/20 to lambda_d/7 electrically, a thin capacitive perturbation you can tune out. The killer is not thickness, it is the metallic effect pigment. Aluminum flake is highly conductive and, per the coatings patents, imposes "too strong damping of radar waves." Real-world metallic paints can cost multiple dB one-way, enough to erase detection range, and no amount of thickness optimization recovers a lossy conductor. The industry fix is a material substitution (radar-transparent effect pigments, PVD indium layers, non-conductive flakes), not a geometry optimization. AEGIS optimizes geometry and lossless-ish permittivity. It has nothing to say about inventing a new pigment. This bounds how much of the automotive pain AEGIS can actually address.

### Aircraft radome boresight error, order of magnitude

Boresight error is the angular lie the radome tells the seeker. For a well-designed tangent-ogive nose radome it lands in the low single-digit milliradians (1 to a few mrad, where 1 mrad = 0.057 deg), and the quantity that actually drives guidance-loop stability and miss distance is the boresight error slope, dBSE/dscan. Predicting BSE to sub-mrad over a full gimbal scan is the hard, valuable deliverable, and it is dominated by wall phase plus the multibounce and tip-diffraction terms that first-bounce PO under-resolves. This is the number defense radome houses buy full-wave tools to get right.

## 3. Incumbents and the gap

Radome EM design today is owned by the general full-wave and asymptotic solvers:

- **Ansys HFSS** (FEM), **Altair FEKO** (MoM, plus PO and large-element PO for electrically large radomes), **CST Studio Suite** (multi-solver, FDTD/FEM/MoM in one frame). These simulate reflectivity of complex shapes and materials, and they explicitly model the phase-front tilt that produces boresight error. FEKO's asymptotic PO/large-element PO is the closest incumbent to AEGIS's own method and is already the standard for electrically large radomes.
- Dedicated boresight-error test rigs exist as hardware products (Ideal Aerosmith BSE test systems), which tells you the defense side still trusts measurement over simulation for acceptance.

Two hard truths for the AEGIS angle:

1. **The flat-stack optimizer is not defensible.** Differentiable transfer-matrix method with adjoint gradients over layer thickness and index is a solved, published tool in photonics (differentiable scattering-matrix and differentiable TMM papers, arXiv 2009.10933 and the multilayer inverse-design literature). Anyone can `pip`-assemble a differentiable 1D stack solver. A painted-bumper stack optimizer is that same object with three layers. It is a feature, not a company.

2. **The curved-shell optimizer is where value lives, and it is where AEGIS is weakest relative to incumbents.** HFSS and FEKO already ship gradient/adjoint and optimization drivers, and they carry the full-wave accuracy that captures the multibounce and diffraction terms AEGIS's first bounce drops. AEGIS's one genuine wedge is end-to-end differentiability of the whole curved surface integral for gradient-based shape-plus-stack co-design, faster than full-wave. But that wedge only closes if PO first-bounce is accurate enough for BSE, and BSE is exactly the regime where first-bounce is shakiest. That is the crux risk.

How Tier-1s actually work it: the patent and testing literature (radome transmission/reflection test apparatus, matching-foil patents, decorative-radome patents) shows an intensely measurement-driven process. They mold, coat, put it on a bench or in a chamber, measure transmission and reflection over angle, iterate the foil and thickness. Simulation informs the first guess; measurement decides. A differentiable simulator competes for the first-guess budget, not the acceptance budget.

## 4. Market and buyer

Automotive radar volume is enormous and growing (multiple radars per ADAS vehicle, hundreds of millions of sensor units per year this decade, imaging/4D radar pushing higher channel counts). But volume of radar units is not the same as budget for radome design software. The bumper/paint transparency problem is largely owned by the OEMs and paint suppliers (BASF, PPG and similar with radar-transparent coating lines) and is solved mostly with measurement plus material science. The addressable "design tool" slice is thin and already served by HFSS/CST/FEKO seats the Tier-1s own. This is a nice patent embodiment (it demonstrates the transmission operator Q_in on a commercially legible object) more than a standalone business.

Aerospace and defense radome design is lower volume, higher value per program, and stickier, but it is a relationship-and-certification market where a startup PO tool without a validation pedigree against measured BSE will not displace FEKO on a missile program. It is a credibility mountain, not a download.

The most honest buyer framing: this is a **complement to the antenna-and-coupling story, not its own market**. If AEGIS is already in a Tier-1 or defense account for the near-field / antenna-coupling reason, "and it also optimizes your radome stack differentiably in the same engine" is a genuine attach. As a cold standalone pitch to a radome team, it loses to the incumbent on accuracy and to the grad-student script on the easy part.

## 5. Verdict

**Grade: CONDITIONAL** (with the flat-stack sub-problem honestly rated OVERRATED, and the curved-shell sub-problem SOLID-but-unbuilt).

- **Strongest angle.** Differentiable co-design of the curved shell shape and the layered wall stack together, in one surface-integral engine, exposing gradients of boresight error and insertion loss with respect to geometry and every layer's thickness and permittivity. Nobody sells exactly that as a fast differentiable object, and it is a natural attach to the antenna-coupling embodiment. The local wall physics is already in `fresnel.py`, and the coherent surface integral is AEGIS's home turf.

- **Biggest risk.** First-bounce PO (A2) drops the antenna-to-wall multibounce and tip diffraction that dominate boresight error and flash lobes, which is the one number the market pays for. If AEGIS cannot predict BSE to the accuracy a radome engineer needs, the differentiable-gradient advantage is a fast route to a wrong answer, and the incumbents (FEKO's PO, HFSS's FEM) win on the metric that matters.

- **What would have to be true.** (1) A validation study showing AEGIS first-bounce plus the existing complex transmission phase predicts boresight error on a canonical tangent-ogive radome within a few tenths of a mrad of full-wave and measurement, or a cheap second-order correction (a limited internal-reflection term) that closes the gap while staying differentiable. (2) The N-layer transfer matrix built as a drop-in replacement for the current single-interface Fresnel, so the wall stack carries full through-thickness phase (small, well-scoped build). (3) A design partner already engaged for antenna coupling, so radome ships as an attach and never has to win a cold standalone bake-off against FEKO.

If those three hold, this is a defensible attach feature and a strong patent embodiment. On its own, as a business, it is not a bet I would make: the easy half is a commodity and the valuable half is a full-wave incumbent's home field.

## Sources

- [TPO/bumper transmission loss and matching foil, radome patents](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11592544)
- [Method for testing transmission and reflection of an automotive radome body](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10288661)
- [Radome for a radar sensor of a motor vehicle (matching-foil 0.1 to 1 mm, metallic paint)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11592551)
- [Decorative radome and method of producing the same](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12080942)
- [Radar frequency transparent effect pigment mixture and coatings](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11421111)
- [Radar attenuating paint (aluminum-pigment damping)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/4606848)
- [Microwave-transparent metallic metamaterials for autonomous driving](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11130274/)
- [HFSS, CST and FEKO features and pricing](https://www.epsilonforge.com/post/commercial-electromagnetic-software/)
- [Ansys HFSS product page](https://www.ansys.com/products/electronics/ansys-hfss)
- [EM simulation solver comparison (FEM/MoM/PO)](https://www.gsc-3d.com/blog/what-electromagnetic-simulation-software-is-the-best/)
- [Differentiable scattering matrix for optimization of photonic structures (arXiv 2009.10933)](https://arxiv.org/pdf/2009.10933)
- [Boresight errors induced by missile radomes (IEEE)](https://ieeexplore.ieee.org/document/1142193/)
- [Radome boresight error and compensation for electronically scanned arrays (DTIC)](https://apps.dtic.mil/sti/citations/ADA344639)
- [Radome boresight error test system (Ideal Aerosmith)](https://www.ideal-aerosmith.com/products/radome-boresight-error-test-system/)
