# 12 wildcard: the things nobody else in the study will say

Agent 12. No discipline, no filter. Lens is the brief's own permission: *"bro go partner with someone
who builds crazy antennas and go test it on a human."* Written 2026-07-09 against `BRIEF.md`,
`jsac_archeology.md`, the code, and the three sibling reports (01 diff-render, 02 competitive moat,
03 RCS/coatings/radome). I deliberately steer away from what those three own. Every claim tagged
`verified` (source or code cited), `inferred` (reasoning shown), or `could-not-check`.

## NEEDS_CONTEXT

Nothing blocked me from writing. Four things I could not verify here and that gate the top bets. If
Robin wants the ambitious version, these are the exact asks:

1. **PO/Kirchhoff validity for focused ultrasound through soft tissue and through skull.** This is
   the falsifier for bet 1 (HIFU). I need a literature read on how well the Rayleigh-Sommerfeld /
   Kirchhoff surface integral predicts the focal spot versus a full-wave acoustic solver (k-Wave)
   for (a) transcostal / soft-tissue focusing and (b) transcranial focusing. Gemini Deep Research
   prompt at the bottom.
2. **Whether Sim4Life / ZMT already ships a differentiable acoustic (not just RF) treatment planner,
   and whether Insightec/Profound/EDAP planning is FDTD or ray/Kirchhoff.** Competitive read for
   bet 1. Prompt at bottom.
3. **Does the tissue-Fresnel discriminator actually separate live skin from a silicone mask at
   60 GHz** (bet 3, liveness). Needs the dielectric of prosthetic silicone at 60 GHz versus skin.
   I could not find silicone's mmWave permittivity here. Prompt at bottom.
4. **Reddit MCP** returned 403 for every agent last study, and I did not attempt community sourcing.

---

## Diverge first: 40 ideas, unfiltered, most of them bad

Object need not be human, solid, or still. Wave need not be EM. Gradient need not flow to a design
parameter. Differentiability need not be used to optimize at all. In that spirit, one line each. The
winces are marked `[wince]`.

1. **HIFU / focused-ultrasound therapy planning.** Scalar Green's function, acoustic-impedance
   Fresnel. Maximize focal dose, constrain rib/skin heating. Same Q machinery, sign flipped.
2. **Transcranial focused ultrasound (tFUS) neuromodulation**, skull aberration correction as a
   differentiable phase-fit. Harder physics, hotter field.
3. **Lithotripsy / kidney-stone shockwave targeting**, differentiable focus through a body twin.
4. **HIFU cosmetic devices** (skin tightening, Ultherapy-class), dose-uniformity design. `[wince]`
5. **Directional parametric-audio "sound rain"**: aim an ultrasonic audio beam at one head in a
   crowd, gradient to array phases, object = a head. `[wince]`
6. **Cochlear / hearing-aid beamforming in a head-and-torso twin** (acoustic), differentiable HRTF.
7. **Room-acoustics loudspeaker-array design** with the crowd as a field of absorbers, gradient to
   speaker placement and phase.
8. **Sonar hull classification**: differentiable PO forward model, invert observed echo to hull
   shape/material. `[wince]` (defense-adjacent, likely dead by brief section 5 logic).
9. **Ocean-surface differentiable scattering** for sea-state / altimetry calibration. `[wince]`
10. **Crop-canopy microwave scattering** for soil-moisture retrieval calibration (SMAP-class).
    Object = a wheat field. `[wince]`
11. **Livestock / poultry industrial dielectric heating uniformity**, differentiable applicator.
    Object = a chicken on a conveyor. `[wince]`
12. **Shipping-container acoustic tomography** for cargo/void detection, differentiable interior.
13. **mmWave occupancy / people-counting** with a differentiable crowd twin, gradient to count.
    Privacy-preserving (verdict, not image) for retail/building HVAC.
14. **Contactless vital-signs + fall detection** (elder care), differentiable human twin as the
    physics-correct synthetic-data and inverse-estimation engine.
15. **In-cabin child-presence detection (CPD)** radar, Euro NCAP mandated, occupant twin. (Cavity
    physics kills single-bounce PO, see below.)
16. **RF face liveness / anti-spoofing**: distinguish live skin from photo/silicone mask by the
    reflected field, using AEGIS's unique tissue-Fresnel model as the discriminator.
17. **RF gesture interface** (Soli-class), inverse hand pose from the reflected coherent field.
18. **"Make it disappear"**: solve for the illumination that nulls the scattered field toward an
    observer. Active signature control of a *platform* (in scope), or background suppression as a
    lab metrology trick.
19. **Installed-antenna-on-platform**: the "electrically large smoothish object" is the antenna's own
    car roof / drone body / satellite bus. Differentiable placement + conformal shaping.
20. **Wind-turbine-blade radar clutter** mitigation, differentiable PO of a rotating blade. `[wince]`
21. **Automotive radome / 77 GHz fascia** transmission design. (Sibling 03 already owns this.)
22. **Wireless-power-transfer safety+efficiency co-optimization** to a device on a body.
23. **Deep-tissue wireless charging of medical implants**, differentiable focusing through layered
    tissue, thermal constraint.
24. **Optimal probe placement for compliance measurement**: gradient of the measured quantity w.r.t.
    probe position tells a test lab where to put the probe to catch worst case.
25. **D-optimal / Fisher-information experiment design**: which few postures x frequencies to
    physically measure so the model is maximally constrained. Sell to labs, not designers.
26. **Certified worst-case posture over a continuum** (Lipschitz + branch-and-bound), the brief's
    patent-move, but applied to *measurement* certification not design.
27. **Sensitivity-ranked model reduction**: use gradients to auto-prune triangles/tissues/paths and
    emit a certified fast surrogate. Sell the surrogate-builder to Tom Dhaene's world.
28. **Standards "load-bearing clause" analysis**: gradient of a compliance verdict w.r.t. each
    assumption in IEC 62232, tell the committee which clause actually controls the outcome. `[wince]`
29. **Exact ISO-GUM sensitivity coefficients** as a billable one-pass deliverable. (Sibling 02
    flagged this; I extend it to the continuum in bet 2.)
30. **Explainability / saliency for black-box channel models**: attribute an exposure or channel
    outcome back onto body geometry ("which body part caused this"). `[wince]`
31. **Adversarial-robustness / Lipschitz certificate for an RF perception classifier** that ingests
    the differentiable forward model. `[wince]`
32. **Cramer-Rao bound as a product** for ISAC/6G sensing vendors: where to put antennas so a target
    parameter is estimable. Design service, not software.
33. **OTA / anechoic-chamber calibration inversion**: fit the twin to sparse probe measurements,
    recover chamber and probe errors. Sell to CTIA/OTA labs.
34. **Chamber-free antenna measurement**: differentiable model + a handful of near-field probes
    reconstructs the full pattern (physics-regularized compressed sensing).
35. **Photoacoustic / thermoacoustic imaging** forward model, differentiable reconstruction. `[wince]`
36. **THz airport body scanner** reconstruction with a body twin, privacy-preserving (threat verdict,
    no image). `[wince]`
37. **Biometric-payment RF depth liveness** (a specialization of 16), anti-fraud angle.
38. **Drone acoustic-signature reduction**, platform signature, acoustic kernel. `[wince]`
39. **Active-learning "which simulation to run next"** for anyone building an EM surrogate: gradient
    of surrogate error w.r.t. the training sample tells you the next scene to simulate.
40. **Differentiable phantom-to-human transfer**: fit the model on the phantom you can measure, use
    gradients to bound the error when you extrapolate to the human you cannot. The metrology bridge.

Winces I stand behind: the chicken (11), the wheat field (10), the sound-rain (5), the poultry
conveyor is genuinely a real industrial-microwave problem and I am embarrassed it might be the safest
one on the list.

---

## The three I would bet on

I pick for **wildcard distance from the siblings** plus **defensibility**. That rules out anything
in RCS/coatings/radome (sibling 03), diff-render moat (01), or pure competitive positioning (02).
What is left and strong: a non-EM kernel swap into a therapeutic market, a gradient that flows to a
*measurement* rather than a design, and a *sensing* use of the discarded reflected half that leans on
the one asset no radar company has (tissue dielectrics).

---

### Bet 1: focused-ultrasound therapy planning (the therapeutic market RF hyperthermia never became)

**The one-sentence pitch.** AEGIS is, structurally, a machine that computes absorbed power density on
a body from a phased array and differentiates it. Therapeutic focused ultrasound is the *same
computation with the sign of the objective flipped*: you want a hotspot on the tumour and you want to
not cook the ribs and skin on the way in. Swap the electromagnetic Green's function for the scalar
acoustic one, swap the tissue-EM Fresnel coefficients for acoustic-impedance ones, and the entire
Q = J^T M J / λ_max / per-triangle-density / differentiable-precoder stack transfers intact. `inferred`
from `field_channel.py` (the geometric core is a scalar phasor accumulation `exp(-i k0 k_hat·r)` with
a polarization vector `psi`; drop `psi` to a scalar and it is already the acoustic Kirchhoff kernel)
`verified` (code, lines 59-69) + `inferred` (kernel swap).

**Why this is the wildcard nobody says.** The brief spells it out and no sibling touched it: *"HIFU is
the therapeutic focused-energy market that RF hyperthermia never became."* RF hyperthermia stayed a
niche because you cannot focus a 1 m EM wave tightly inside a body. Ultrasound has a sub-millimetre
wavelength in tissue, so it focuses to a rice-grain, and it is a real, growing, reimbursed clinical
market: essential-tremor and Parkinson thalamotomy (Insightec Exablate), prostate ablation (EDAP
Focal One), uterine fibroids, and the fast-moving transcranial-neuromodulation research field.

**Who is the customer.** Two tiers. Tier one, the device makers who ship a planning workstation with
the machine: Insightec, Profound Medical (Tulsa-Pro), EDAP TMS, Carthera (SonoCloud), and the
academic tFUS labs (there are dozens in the EU). Tier two, and this is the realistic two-person entry,
the *research* tFUS community that today plans with k-Wave (a free full-wave acoustic solver, minutes
to hours per configuration on GPU) or Kranion. A millisecond differentiable planner is a research
tool they would adopt to run the sweeps and closed-loop optimizations k-Wave cannot. `inferred`
(market structure) `could-not-check` (exact planning-software incumbency, see NEEDS_CONTEXT 2).

**The physics, honestly.** Kirchhoff / Rayleigh-Sommerfeld surface diffraction is the *standard*
workhorse of acoustic-array beamforming for soft tissue, and PO's validity objection from brief 2.3
(edges, silhouettes) is far weaker here because a therapeutic transducer illuminates a smooth convex
target through smooth tissue interfaces, not a silhouette. `inferred`. The AEGIS layered-Fresnel
`T0` becomes the acoustic transmission across skin/fat/muscle/bone impedance jumps, which the code
already computes as a layered stack. `verified` (the tissue module is layered; `tissue/fresnel.py`
returns per-interface coefficients). The differentiable-focus problem is genuinely high-dimensional
in exactly the way brief section 3(a) demands: 256 to 1024 transducer elements, complex, and the real
clinical objective is *multi-focal thermal-dose shaping under an organ-at-risk constraint*, which is a
constrained QCQP over the excitation continuum. That is λ_max(Q) with a constraint, which is precisely
the AEGIS coherent stack. `inferred`.

**What breaks it (the falsifier).** The skull. Transcranial focusing has strong aberration, mode
conversion (shear waves in bone), and multiple internal reflections that first-order Kirchhoff does
not capture. If bet 1 tries to enter through the brain, PO validity fails exactly where sibling 03
warned it fails for RCS: at the hard interface. **So the honest beachhead is transcostal and
soft-tissue HIFU (liver, prostate, breast, fibroids), where Kirchhoff is trustworthy, and transcranial
is a research-collaboration stretch, not the product.** The single experiment that decides it: take one
CT-derived rib cage or one soft-tissue path, compute the focal field with the AEGIS-acoustic kernel,
and compare focal-spot location, width, and the rib-surface heating map against k-Wave. If focal
position agrees to a wavelength and the rib heating agrees to ~20%, the beachhead is real. If the
skull case diverges (it will), you have quantified exactly where the product stops, which is a feature
not a bug for a certification-minded founder.

**Does differentiability matter essentially or decoratively.** Essentially, but only in the
constrained/multi-focal regime. A single-focus plan is closed-form time-reversal and needs no
gradient (decorative there, be honest). The moment you add an organ-at-risk thermal constraint, or ask
for a multi-focal boiling-history-shaped dose, or want patient-specific aberration correction over
1000 elements, it becomes a high-dimensional constrained optimization where gradients are the only
way and where the millisecond forward pass is the enabler. That is the same discovery the archeology
made about the RF operator: the value is *speed enabling optimization*, not the operator itself.
`inferred`.

**First month.** (1) Fork the coherent kernel, replace `psi` with a scalar pressure amplitude and the
EM Fresnel with acoustic-impedance reflection/transmission, keep the exact Q/λ_max/grad plumbing. (2)
Validate against the analytic field of a focused spherical-cap transducer (closed form, textbook) to
prove the kernel is right to machine precision. (3) Validate against k-Wave for one soft-tissue path.
(4) Reproduce one published Insightec/EDAP-style focal spot. Deliverable at day 30: a plot of
AEGIS-acoustic focal spot overlaid on k-Wave, computed 100 to 1000x faster, with the gradient of focal
intensity w.r.t. all element phases shown.

**The photograph that drops the jaw.** A schlieren or thermal-phantom image of a real ultrasound focal
spot painted inside a tissue-mimicking gel, next to the AEGIS-acoustic prediction of the same spot
computed in milliseconds, next to the k-Wave prediction that took an hour. Three-panel: reality,
us-fast, incumbent-slow. This is the acoustic twin of the KU Leuven 28 GHz thermal shot the RF study
already identified, and it is *cheaper to shoot*, because a gel phantom and a research HIFU transducer
live in half the ultrasound labs in Flanders. `inferred`.

**Grade.** Problem exists: yes, treatment planning is a real clinical bottleneck. Robin can fill it:
partially, the kernel swap is a month but clinical validation and CE-marking a planning tool is years
and needs a clinical partner. Patentable: the *differentiable* acoustic treatment planner over a
constraint continuum is plausibly novel and does not collide with the RF-VOP prior art that killed the
exposure envelope (different physics, different claim). Doable by two in two years: the research-tool
version yes, the clinical product no. Market: large and reimbursed, but slow and regulated. Value
depends on differentiability: essentially, in the constrained regime. **The biggest ceiling on the
list and the biggest regulatory drag. Bet it as a research tool and a patent, not as the BV's revenue
in year one.**

---

### Bet 2: gradients that flow to a measurement, not a design (the "where to measure" company)

**The one-sentence pitch.** Every other idea points the gradient at a thing you build. Point it at a
thing you *measure*. A differentiable forward model tells a compliance or OTA test lab the minimum set
of measurements that certifies a device, and exactly where to place each probe and which posture and
frequency to test, to capture the true worst case, with a certificate that says "no untested
configuration is worse than this." That is a measurement company that happens to own a model, which
the brief explicitly floats as a legitimate shape for the business.

**Why this is a wildcard.** The whole study, and both dead papers, assumed the gradient flows to a
design variable (precoder, pose, shape, coating). The archeology's deepest lesson is that *nobody
wanted the design output* (exposure never binds, MCS cap eats rate). But the sensitivity-coefficient
mandate is the one place brief section 3(c) says gradients are *legally required and billable*. The
non-obvious move is to stop selling the optimum and sell the **experiment design**: the gradient and
the Fisher information tell you which measurements are informative and which are redundant, and the
Lipschitz bound over the configuration continuum (brief's patent-move, section 5) turns "we tested a
few postures and hoped" into "we certify the sup over all postures." Applied to *measurement*, not
design, this sidesteps every corpse in section 5, because it never needs an exposure limit to bind
and never sells a rate-dB. It sells *test coverage and certified worst-case*, which is what a lab is
legally on the hook for. `inferred`.

**Who is the customer.** The EMF/OTA compliance test labs and the near-field scanner vendors who serve
the mmWave device pre-compliance beachhead the brief says is already warm. You are not competing with
that beachhead, you are selling the *test-planning layer* underneath it: "here are the 6 probe
positions and 3 postures that certify this phone, instead of the 200 you measure today, and here is the
proof that nothing you skipped is worse." Named incumbents: the labs buy scanner hardware and software
from ART-Fi, cSAR3D (SPEAG/ZMT), and the IEC/IEC 62232 + 63195 test procedures they follow are today
executed by exhaustive scanning. `verified` (SPEAG/ZMT cSAR3D and IEC 62232/63195 are the real
compliance stack; brief section 5 names ZMT). Nobody sells "the minimal certified test plan derived
from a differentiable model." `inferred`.

**The physics, honestly.** This is the *safest* bet on physics because it does not need PO to be right
in an absolute sense, only to rank sensitivities correctly and bound Lipschitz constants. And it uses
the part of AEGIS the study has most confidence in: the exact end-to-end gradients that are already
FD-validated (`tests/test_jax_grad.py`, brief section 2.1). `verified` (the gradients exist and are
tested).

**What breaks it (the falsifier).** Finite differences might be good enough. If the design/config space
is small (a handful of probe positions, a handful of postures), 2N finite-difference simulations are
cheap and the exact gradient buys nothing, which downgrades the whole thing to "decorative
differentiability." The bet only survives if the continuum is genuinely high-dimensional: full 6-DoF
probe pose x continuous device orientation x frequency x SMPL-X posture is easily 70+ dimensions, and
there the Lipschitz-certified sup over the continuum is something finite differences *cannot* produce
at all (they sample, they do not bound). **The single experiment that falsifies it:** take one real
compliance scenario, compute the certified worst-case over a continuous posture-and-position ball with
the Lipschitz/branch-and-bound method, then run a dense finite-difference/random search over the same
ball and check that the certificate is (a) not violated by any sample and (b) tight enough to be
useful. If the certificate is loose by 10 dB it is worthless; if it is tight to a dB it is a product.
This is the same experiment the brief's patent-move needs, so it does double duty.

**Does differentiability matter essentially or decoratively.** Essentially *only in the certified-sup
version*, decoratively in the sensitivity-coefficient version (CST already emits adjoint S-parameter
sensitivities, sibling 02). So the defensible core is the **certificate over the continuum**, not the
one-pass GUM coefficients. Lead with the certificate.

**First month.** (1) Implement the Lipschitz/branch-and-bound sup over a posture+position ball on top
of the existing gradients (the gradient magnitudes bound the Lipschitz constant directly). (2) Run the
falsification experiment above. (3) Frame the output as a "certified test plan" document a lab could
hand a notified body. Deliverable at day 30: for one phantom and one source, a certificate "the peak
absorbed density over this continuous 6-DoF ball is at most X, achieved near configuration c*," with a
dense random search failing to beat it.

**The photograph.** Less visual than HIFU, but the investor image is a heat-map of a body with a single
red dot labelled "certified worst case, found in 4 seconds" over a caption "the standard tests 6
postures and hopes; we certify the other infinity." `inferred`.

**Grade.** Problem exists: yes, and it is *mandated*, which is the strongest possible form of a
problem. Robin can fill it: yes, this is the most reachable bet, it needs no new physics and no
clinical partner, only the certificate machinery on top of existing gradients. Patentable: this *is*
the brief's identified patent-move (sup over configuration continuum), so it is the one that keeps the
IDF alive, and applying it to *measurement certification* is a cleaner, less-crowded claim than
applying it to design. Doable by two in two years: yes. Market: smaller than HIFU, but adjacent to the
warm pre-compliance beachhead and it is boring-and-billable, which the brief explicitly values.
Value depends on differentiability: essentially, in the certificate version. **This is the bet I would
actually start Monday. Lowest risk, ties directly to the surviving patent claim, needs no partner.**

---

### Bet 3: RF liveness and anti-spoof, using the one asset no radar company owns (tissue dielectrics)

**The one-sentence pitch.** Sibling 03 took the discarded reflected half and pointed it at RCS shape
design (and correctly said the defense market is closed). Point the *same* reflected half at *sensing*
instead, at the one problem where AEGIS has an unfair advantage: telling live human skin from a photo,
a screen, or a silicone mask, because AEGIS is the only differentiable scatterer that carries the
actual dielectric of skin (Cole-Cole, layered Fresnel). A pure geometry radar sees a face-shaped
reflector; AEGIS sees that the reflection coefficient is *skin's*, not silicone's or glass's.

**Why this is the wildcard.** The brief dangles it directly: *"What if it is a face and the goal is
liveness detection for anti-spoofing?"* and *"pose estimation is a relatively easy engineering task, so
building a good human digital twin is somewhat doable."* Face-ID spoofing (photos, replayed video,
3D-printed and silicone masks) is a live, funded security problem, and the optical/IR liveness defenses
are in a permanent arms race with better masks. An RF liveness channel is orthogonal: it sees through
the mask to the material underneath and it sees the 3D reflection geometry a flat photo cannot fake.
The differentiable body/face twin lets you *fit* the observed reflected field and score how well a real
layered-skin face explains it versus a flat or wrong-dielectric surface. `inferred`.

**Who is the customer.** Biometric and secure-payment vendors, phone OEMs, and access-control makers who
already ship anti-spoof (FaceTec, iProov, Apple/Face-ID-class, the automotive driver-monitoring Tier-1s).
The incumbent today is *optical* liveness (depth from structured light or dot projector, texture and
micro-motion analysis) plus IR. `verified` (Apple Face ID uses a dot projector and IR; optical liveness
is the category). Nobody sells a *tissue-dielectric-aware differentiable RF liveness* discriminator.
`inferred`.

**The physics, honestly.** A face is ~15-18 cm, at 60 GHz the wavelength is 5 mm, so the face is
electrically ~30 wavelengths, comfortably "electrically large smoothish object." First-order PO on a
smooth face is in a reasonable regime (convex, few silhouettes in the illuminated patch). The
discriminator is the reflection coefficient magnitude and phase: skin at 60 GHz has a specific complex
permittivity (high water content, `T0`~0.62 transmission per brief 2.2a, so ~0.38 reflected), which
differs from silicone, latex, paper, and glass. AEGIS computes this per triangle already for the
transmission half; the reflection half is one variable swap (sibling 03 verified `r_s, r_p` are
computed and discarded). `verified` (sibling 03, `tissue/fresnel.py` returns `r_s, r_p`).

**What breaks it (the falsifier).** Two things. First, a good silicone mask might reflect close enough
to skin at 60 GHz that the discriminator has no margin. That is a pure measurement question and it is
the falsifying experiment: measure the 60 GHz reflection of live skin versus 3 mask materials, and see
if there is a separable feature. If silicone at 60 GHz looks like skin, bet 3 dies. `could-not-check`
(I could not find silicone's mmWave permittivity, NEEDS_CONTEXT 3). Second, near-field: a phone-distance
face is ~20-30 cm from the antenna, which is near-field at 60 GHz for a face-sized aperture, so the
far-field plane-wave source model in AEGIS needs the near-field extension (the same gap the archeology
flagged as the 300 m Fraunhofer error). That is a real code lift, not a swap. `inferred`.

**Does differentiability matter essentially or decoratively.** Weakest of the three on this axis, be
honest. Liveness is a *classification* problem, and you could train a black-box net on synthetic RF
signatures without ever needing a gradient at inference. Differentiability earns its keep in two
narrower places: (a) analysis-by-synthesis, fitting the twin's pose and dielectric to the observed
field and using the residual as the liveness score (gradient-based fit), and (b) generating hard
adversarial spoof examples to harden the classifier (gradient to the mask parameters). If neither
proves necessary, this is "a differentiable model used to make synthetic training data," which is a
fine business but not a differentiability business. **Downgrade accordingly and lead with the
tissue-dielectric moat, not the gradient.**

**First month.** (1) Swap in the reflection coefficients, evaluate the PO radiation integral toward a
single observer (the phone antenna), reuse the UE-anchored Kirchhoff-render primitive the JSAC2 work
already built (`rihb_theory_v4.tex`). (2) Simulate the reflected 60 GHz signature of a skin face versus
a flat photo, a glass screen, and a silicone mask, using the tissue database. (3) Show whether a simple
feature separates them. Deliverable at day 30: a scatter plot of live-skin versus 3 spoof materials in
the RF-feature space, with a decision boundary, all synthetic, plus the honest note that it must be
confirmed on a real 60 GHz measurement.

**The photograph.** A face wearing a hyper-realistic silicone mask that fools the iPhone camera, and
next to it the AEGIS RF signature lighting up red "SPOOF: dielectric is not skin." That is a
jaw-dropper for a security investor. It needs a real 60 GHz measurement to be honest, and KU Leuven
WaveCoRE has the hardware. `inferred`.

**Grade.** Problem exists: yes, and it is a security spend, which is well-funded. Robin can fill it:
partially, needs the near-field lift and a measurement partner. Patentable: tissue-dielectric-aware RF
liveness is plausibly novel, but the differentiability is decorative-to-weak, so the patent would rest
on the *material discrimination*, not the gradient, which weakens the study's thesis for this idea.
Doable by two in two years: the demo yes, a shipped anti-spoof product no (long security sales cycles,
certification). Market: large security market, hard entry. Value depends on differentiability:
decoratively, mostly. **The most surprising idea and the best photograph, but the weakest on the
study's actual question. Bet it as a demo and a patent on material discrimination, not as the
differentiability business.**

---

## Cross-cutting observation the siblings will not make

The archeology's real lesson is not "exposure does not bind." It is that **every time the gradient
pointed at a design variable, the market did not want the design.** Exposure did not bind, the MCS cap
ate the rate, the coating market is thin, the stealth market is closed. The one place the gradient
consistently had value was as a *transparency / certification* readout (JSAC2's live exposure display,
the GUM sensitivity mandate, the CLUE-H methods upgrade). So the highest-expected-value direction is
not "optimize something," it is **"certify or measure something," where the gradient's job is to bound,
rank, or place, not to descend.** Bet 2 is the pure form of that insight, which is why it is the one I
would start Monday. Bet 1 is the biggest swing because it is the one market where the design output
(a therapeutic focal spot) is *the whole point* and the customer genuinely wants the optimum. Bet 3 is
the most fun and the least aligned with the thesis.

One more: the two winces I cannot fully dismiss are industrial dielectric heating (11) and room
acoustics (7), because both are large, civilian, non-human, and in PO's valid regime (smooth loads,
smooth reflectors), and neither is in section 5's graveyard. I flag them for a later pass rather than
bet on them, because I could not name the incumbent or the buyer with confidence in the time I had.

---

## Deep-research prompts (for Robin to run)

**Prompt A (bet 1 falsifier).** "How accurate is the Rayleigh-Sommerfeld / Kirchhoff surface-integral
(physical optics) approximation for predicting the focal-spot location, width, and intensity of a
phased focused-ultrasound transducer (256-1024 elements, 0.5-1.5 MHz) (a) through homogeneous soft
tissue, (b) transcostal through a rib cage, and (c) transcranial through skull bone, compared to
full-wave solvers such as k-Wave? Cite quantitative error figures and the regimes where Kirchhoff
fails. Also: do Insightec, Profound Medical, EDAP, or academic tFUS planning tools (Kranion, k-Plan)
use ray/Kirchhoff or full-wave methods for treatment planning, and is any of them differentiable?"

**Prompt B (bet 2 incumbency).** "In IEC 62232 and IEC 63195 mmWave/SAR device compliance testing, how
is the worst-case measurement configuration (probe position, device orientation, body posture)
currently determined? Is it exhaustive scanning, a fixed protocol, or model-guided? Do SPEAG/ZMT
(cSAR3D, Sim4Life), ART-Fi, or any vendor sell a model-derived minimal test plan or a certified
worst-case-over-configurations bound? What does ISO GUM require for sensitivity coefficients in an EMF
uncertainty budget?"

**Prompt C (bet 3 falsifier).** "What is the complex relative permittivity of (a) human facial skin,
(b) prosthetic/special-effects silicone, (c) latex, and (d) glass at 60 GHz? Is there a separable
difference in reflection coefficient at 60 GHz that could distinguish live skin from a silicone mask?
Has anyone published mmWave/60 GHz RF face liveness or anti-spoofing?"
