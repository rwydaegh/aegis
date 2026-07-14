# Acoustics feasibility report: is "room acoustics is dead" actually right?

Author: solo technical assessment for the AEGIS spin-off, before the Tom meeting.
Scope: I stress-test the verdict that room acoustics cannot host the AEGIS core. I do this per acoustic sub-regime, with the wavelength numbers spelled out, and I grade each one separately. The short answer is that "room acoustics" proper is dead, but that phrase is doing a lot of hiding. Two acoustic cousins are not dead, and one of them (array radiation) is a physically cleaner fit for the AEGIS calculus than tissue dosimetry is.

## What has to hold for the AEGIS core to transfer

I use the assumption ladder from the brief. Restating it so the grading is auditable:

- A1 linear superposition. This alone buys the whole Q-operator calculus. A power quantity becomes `x^H Q x` with `Q` Hermitian, `Q_ab + Q_re + Q_mi = I`, and constrained design collapses to a QCQP or a closed-form eigenproblem. Wave-agnostic, source-agnostic.
- A2 first bounce dominates. Buys the cheap surface evaluation with no ray tracing. Dies when late diffuse reverberation, multi-bounce, or modal build-up carry the energy.
- A3 surface confinement (hard or high-loss boundary). Buys the 3D to 2D reduction onto the scatterer surface.
- A4 locally planar interface, facet large and smooth versus wavelength. Buys the Fresnel/Kirchhoff local interaction law.
- A5 pseudo-Brewster scalar collapse. Tissue-EM specific. Does not transfer to acoustics. So the millisecond-cheapness argument is gone the moment we leave EM dosimetry.

Two consequences I keep coming back to. First, the Q-calculus travels on A1 alone, so anything that is a linear superposition of sources is in principle in scope, regardless of A2 to A4. Second, the fast specular surface evaluator needs A2 and A3 and A4 together, and acoustics never gets A5 back, so speed is not a moat here. The only durable moat in acoustics is the same as in EM: differentiability wired to an inverse-design objective, plus the closed-form Q algebra. I will hold every sub-regime to that standard, not to the "we are fast" standard.

## The wavelength argument, made quantitative

Speed of sound in air `c = 343 m/s`, so `lambda = c / f`.

| Frequency | Wavelength | What is "large versus lambda" here |
|-----------|-----------|-------------------------------------|
| 100 Hz | 3.43 m | Nothing in a room. A whole wall is ~1 to 2 lambda. Pure modal regime. |
| 1 kHz | 0.343 m (34 cm) | A large flat panel (1 to 2 m) is a few lambda. Furniture, moldings, people (~0.2 to 0.5 m) are order lambda. |
| 10 kHz | 3.43 cm | Most flat surfaces are large versus lambda. But air absorption is high and rooms are fully diffuse by now. |
| 40 kHz (air ultrasound) | 8.6 mm | Any smooth surface is strongly specular. Sensing regime, not room regime. |
| 1 MHz (medical, tissue c~1540 m/s) | 1.54 mm | Deep specular/Kirchhoff regime. Owned by the medical/NDT report. |

The Kirchhoff (physical optics) local law that A4 encodes is the acoustic analog of AEGIS's Fresnel facet law, and the textbook validity threshold is roughly `ka > 3` for a facet of radius `a`, with roughness small versus lambda. Computing `ka` for a flat panel:

- Panel radius `a = 0.5 m`: `ka = 9.2` at 1 kHz, `ka = 92` at 10 kHz. Kirchhoff is fine for a smooth 1 m panel from ~1 kHz up.
- Room-clutter feature `a = 0.1 m` (chair edge, molding, a person's head): `ka = 1.8` at 1 kHz. Below threshold, so these scatter diffusely, not specularly, exactly where speech and music energy lives.

So A4 does not fail everywhere. It fails on room clutter at speech/music frequencies, which is what actually shapes a room's sound. A single large flat isolated panel at 1 kHz would pass A4. That distinction is the whole report: AEGIS's engine is fine on big smooth flats and hopeless on the cluttered, wavelength-scale, multi-bounce interior that defines "room acoustics."

The A2 argument is separate and, for rooms, decisive. Early specular reflections (the first ~50 to 80 ms, first and maybe second order) are perceptually real and are exactly what image-source and beam-tracing auralization compute. But the steady-state energy in an ordinary room is dominated by the late diffuse reverberant tail, which is many-bounce and statistical. RT60, clarity C50, speech transmission index STI, all the metrics people actually buy software to predict, are late-field quantities. A first-bounce engine cannot see them. A2 is not marginally violated for room reverberation, it is the entire quantity of interest.

## Sub-regime mapping onto the ladder

### Room reverberation, RT60, C50, STI, speech intelligibility design
A1 holds. A2 fails hard (the deliverable IS the late diffuse field). A3 partially holds but is irrelevant once A2 is gone. A4 fails on clutter at mid-band. This is the "room acoustics is dead" case and the verdict is correct. Nothing about the AEGIS engine touches a reverberant tail. Verdict: DEAD.

### Early-reflection / first-order specular auralization and reflection control
A1 holds. A2 holds only inside the early-time window and only for the large flat surfaces (stage shells, ceiling reflectors, a proscenium), which do pass A4 above ~1 kHz. This is the one place inside "rooms" where AEGIS's physics is not obviously wrong: first-order specular reflections off big smooth surfaces are exactly a physical-optics surface integral, and differentiating reflector geometry against an early-energy objective is a real inverse-design problem. But (see SOTA) this is already the target of published differentiable image-source and differentiable radiance-transfer work, and the market for "optimize my stage reflector" is a handful of concert halls per year. Verdict: NICHE-PAPER-ONLY.

### Loudspeaker / transducer array beamforming into free or half space
This is the important one and it is qualitatively different from the others, because it is radiation, not scattering. There is no wall, no bounce, no facet. A2, A3, A4 do not even enter. The field is a pure linear superposition of driver contributions `p(r) = sum_n x_n g_n(r)`, so it rides on A1 alone. Any power-like objective (radiated power into a target sector, on-axis SPL, sidelobe/leakage energy into a protected zone, contrast between bright and dark zones in personal-sound-zone systems) is a Hermitian quadratic form `x^H Q x` in the driver weights `x`, with the identical `Q_in + Q_mi = I` bookkeeping AEGIS already has for captured-versus-missed power. This is the cleanest possible instance of the Q-calculus, cleaner than tissue dosimetry, because there is no A4/A5 approximation to defend. The honest caveat is that this problem is also well-posed and convex, and the field already solves it (see below). So the question is not "can AEGIS do it" (yes, trivially) but "what does AEGIS's closed-form eigen/QCQP machinery add over existing convex array design." Verdict: WORTH-A-SECOND-LOOK.

### Noise barriers and large flat outdoor surfaces
Superficially the best A4 fit in the whole report: a highway barrier is a big smooth flat wall, `ka` is huge. But the physics of what a barrier DOES is diffraction over the top edge into the shadow zone, which is precisely the edge phenomenon A2 throws away. Every source I read (barrier reviews, the outdoor-propagation literature, the metamaterial-edge work) says top-edge diffraction is the dominant transmission mechanism behind the barrier. AEGIS's engine models the specular face reflection, which is the part of a barrier that does not matter for insertion loss. So the surface AEGIS can see is not the surface that determines performance. Verdict: DEAD (for the AEGIS engine specifically), and note that differentiable barrier design is already claimed by JAX-BEM below.

### Ultrasonic / sonar / medical acoustics
Boundary note only, these are owned by other reports. Physically this is where the AEGIS regime is genuinely comfortable: at 40 kHz to 1 MHz, lambda is 1.5 to 8.6 mm, `ka` is large, and smooth hulls/transducers/tissue interfaces are specular Kirchhoff scatterers. If any acoustic regime deserves the AEGIS surface engine on physics grounds, it is high-frequency specular, not rooms. I flag the boundary and defer.

## State of the art, and whether the differentiability gap is already filled

It is largely filled. This is the finding that most constrains the verdict.

Incumbent forward solvers and market:
- Geometric acoustics: Odeon (ray + image-source, the de-facto concert-hall standard, ~EUR 5,000+) and CATT-Acoustic/TUCT (~EUR 2,000 to 3,000). Mature, validated, entrenched.
- Wave-based and hybrid: Treble (VC-funded, cloud, wave-based at low frequency + geometric at high frequency, claims 100 to 1000x speedups over prior wave solvers). COMSOL Acoustics, Actran for FEM/BEM.
- Python/open: pyroomacoustics (fast C++ image-source + ray tracing, the standard research library, not itself differentiable).

Differentiable acoustics already published (this is the crowded part):
- A Differentiable Image Source Model for Room Acoustics Optimization (Zhi, Sharma, IEEE 2023): fully differentiable ISM for gradient-based optimization of geometry and material, shoebox-limited.
- DART, Differentiable Acoustic Radiance Transfer (arXiv 2509.15946, 2025): gradient-based optimization of material properties, arbitrary geometry.
- Differentiable Room Acoustic Rendering with Multi-View Vision Priors (arXiv 2504.21847, 2025) and the "misuka" open-source differentiable renderer.
- TU Berlin "Differentiable Acoustic Path Tracing" project.
- JAX-BEM: Gradient-Based Acoustic Shape Optimisation via a Differentiable Boundary Element Method (Hipperson, Hargreaves, Cox, University of Salford, arXiv 2604.21431). This is the direct competitor to any AEGIS acoustic-inverse-design pitch: differentiable BEM in JAX with adjoint/AD through GMRES, demonstrated on loudspeaker horn, muffler, and noise barrier. It already occupies the "differentiable wave solver for acoustic device design" slot, and it does it with full-wave BEM, not a first-bounce approximation, so it has no A2/A4 regime limit.
- Neural acoustic fields (NeRAF arXiv 2405.18213, and 2025 reciprocity/latent-field work). Different paradigm (learned fields), but eating the "learn/optimize an acoustic scene" narrative.
- Gradient/autograd beamforming for arrays is also already appearing (autograd differential microphone-array beamforming, arXiv 2511.19403 and 2508.17607), plus decades of convex loudspeaker-array beamforming.

Net read: the "nobody has made acoustics differentiable" opening that AEGIS exploited in EM dosimetry is not available here. Multiple groups shipped differentiable room-acoustic and differentiable-BEM tooling in 2023 to 2026, and one of them (JAX-BEM) is exactly the differentiable-inverse-design-for-acoustic-devices product, built on a full-wave solver that dominates AEGIS's first-bounce approximation on accuracy. AEGIS would enter as the least accurate physics in an already-differentiable field, with A5 (and hence the speed edge) gone. The Q-operator algebra is the only thing AEGIS brings that I did not find already published, and it only clearly buys something in the pure-A1 radiation case.

## Verdict, graded per sub-regime

| Sub-regime | Grade | One-line reason |
|-----------|-------|-----------------|
| Room reverberation / RT60 / C50 / STI | DEAD | Deliverable is the late diffuse field, A2 fails entirely, clutter fails A4 at mid-band. |
| Early-reflection / specular auralization | NICHE-PAPER-ONLY | Physically valid on big flats in the early window, but tiny market and already done by differentiable ISM/DART. |
| Loudspeaker / transducer array beamforming (free/half space) | WORTH-A-SECOND-LOOK | Pure A1 radiation, cleanest Q-operator fit in acoustics, but convex and already solved, so the moat is unproven. |
| Noise barrier / large flat outdoor | DEAD | Barrier performance is edge diffraction (A2 discards it), and JAX-BEM already does differentiable barrier design. |
| Ultrasonic / sonar / medical | DEFER | Physically the best-fit regime (high ka specular), owned by other reports. |

## The one strongest surviving angle

Loudspeaker/transducer array beamforming into free or half space. It is the only acoustic sub-regime that needs A1 and nothing else, so none of the room-acoustics objections (A2 diffuse reverb, A4 clutter, A5 loss of speed) apply. A power target in a spatial zone is exactly `x^H Q x`, the captured/missed identity carries over verbatim, and constrained beam design becomes the same closed-form eigen/QCQP AEGIS already runs for MIMO precoding. It is essentially the AEGIS coherent Q-operator engine with the acoustic Green's function swapped in for the EM channel, and no surface approximation at all.

What would have to be true for it to be a real business, not just a valid physics port:
1. The closed-form Q eigen/QCQP has to beat existing convex array beamformers (LP/SOCP, DSP-based) on something a customer pays for: joint geometry-plus-weights inverse design, multi-zone contrast with hard constraints, or differentiable co-design of array layout and drive at once. Plain fixed-geometry beamforming is already a solved convex problem, so matching it is not enough.
2. There has to be a buyer whose problem is design (place and drive the array to hit a spatial power spec) rather than runtime DSP. Candidates: personal sound zones / in-car audio, parametric and directional PA, ultrasonic transducer arrays (which also lands in the favorable high-ka regime). Runtime adaptive beamforming is not our game, it is a DSP-vendor game.
3. It has to survive the fact that autograd array optimization already exists in the literature, so the pitch is the closed-form operator algebra and joint geometry co-design, not "we made it differentiable."

If those three do not clear, the honest conclusion is that acoustics as a whole is a paper, not a market, and the only physically native home for AEGIS's specular surface engine in acoustics is high-frequency ultrasonic/sonar/NDT, which other reports own.

## Sources

- [Differentiable Room Acoustic Rendering with Multi-View Vision Priors (arXiv 2504.21847)](https://arxiv.org/abs/2504.21847)
- [A Differentiable Image Source Model for Room Acoustics Optimization (IEEE Xplore 10248140)](https://ieeexplore.ieee.org/document/10248140/)
- [Differentiable Acoustic Radiance Transfer / DART (arXiv 2509.15946)](https://arxiv.org/html/2509.15946v1)
- [Differentiable Acoustic Path Tracing, TU Berlin](https://www.tu.berlin/en/ak/research/projects/differentiable-acoustic-path-tracing)
- [JAX-BEM: Gradient-Based Acoustic Shape Optimisation via a Differentiable Boundary Element Method (arXiv 2604.21431)](https://arxiv.org/pdf/2604.21431)
- [pyroomacoustics (LCAV, GitHub)](https://github.com/LCAV/pyroomacoustics)
- [NeRAF: 3D Scene Infused Neural Radiance and Acoustic Fields (arXiv 2405.18213)](https://arxiv.org/abs/2405.18213)
- [Design of Differential Loudspeaker Line Array for Steerable Frequency-Invariant Beamforming (MDPI Sensors 24/19/6277)](https://www.mdpi.com/1424-8220/24/19/6277)
- [Frequency-Invariant Beamforming via Autograd and Concentric Circular Microphone Arrays (arXiv 2511.19403)](https://arxiv.org/html/2511.19403v1)
- [Acoustic Scattering Models from Rough Surfaces: A Brief Review and Recent Advances (MDPI Applied Sciences 10/22/8305)](https://www.mdpi.com/2076-3417/10/22/8305)
- [Harnessing diffraction with metamaterial noise barriers (Materials Horizons, RSC)](https://pubs.rsc.org/en/content/articlehtml/2026/mh/d5mh02051d)
- [Best Acoustic Design Software in 2026 buyer's guide (AcousPlan)](https://acousplan.com/blog/best-acoustic-design-software-2026)
- [Treble acoustic simulation platform](https://www.treble.tech/acoustics-suite)
