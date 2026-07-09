# Automotive radar and the pedestrian as an electrically large scatterer at 77 GHz

Lens report 04. Author: agent 04. Date: 2026-07-09. Grades against BRIEF.md sections 3, 5, 7.

Verdict up front. The market is real, large, and mandate-backed, which is rare and valuable. But the
orchestrator's headline hypothesis (gradient-based adversarial pose search to find the vulnerable
pedestrian) is the *weakest* differentiability story in this lens, for two reasons I can defend with
evidence: the low-RCS optimum the gradient marches toward is exactly the multipath-null regime where
first-order PO is least valid (brief section 2.3 bites hardest here), and the safety-relevant hard
cases are kinematic (zero radial velocity, occlusion, standing still), which a sweep over ~20
canonical poses already captures. The differentiability-essential plays in this lens are elsewhere:
the smooth dielectric fascia and radome (AEGIS's actual validity regime, but deep Ansys turf with
published differentiable-PO prior art), and a certified or prioritized worst-case *coverage* search
over the pose-configuration continuum (aligned with the brief's patent-move, throttled by the same PO
validity ceiling). Net: a genuine market, a hard entry, and differentiability that is more decorative
than essential for the pedestrian-detection framing that motivated the lens.

No NEEDS_CONTEXT blockers. One flag: I could not verify list prices for any commercial simulation
tool. I mark those `could-not-check` rather than invent numbers.

---

## 1. Diverge: raw idea list (unfiltered)

1. Adversarial pose search: SMPL-X pose that minimizes monostatic RCS at a given aspect (the headline).
2. Micro-Doppler collapse: gait or limb configuration that flattens the range-Doppler spectrogram.
3. Classifier-defeating pose: adversarial against a specific pedestrian-vs-clutter perception net.
4. Synthetic radar training data with exact Jacobians d(signature)/d(pose) for Sobolev supervision of a neural sensor model.
5. Differentiable radome or bumper-fascia dielectric stackup design against installed radar performance.
6. Emblem, logo, and heater-grid geometry optimization to minimize boresight radar degradation.
7. Differentiable sensor placement on the car body: mount position or aim that minimizes self-occlusion and vehicle multipath.
8. Pedestrian-dummy RCS fidelity check: does the UN R152 / Euro NCAP articulated dummy match a real human across pose, with AEGIS as the reference.
9. Certified worst-case coverage: Lipschitz or branch-and-bound bound over pose x orientation x range giving a guaranteed minimum detectable RCS for a dossier.
10. Ghost-target and false-alarm prediction from pedestrian-plus-ground-plus-vehicle multipath.
11. Rare-VRU coverage: cyclist, child, wheelchair user, stroller, using the parametric body pipeline.
12. Radar-conspicuity wearable design: retroreflective corner structures optimized to *boost* pedestrian RCS (the protective inverse).
13. Differentiable road-surface two-ray multipath: the elevation nulls where a pedestrian vanishes at range.
14. Cross-traffic occlusion by parked cars: partial-occlusion of the pedestrian signature, differentiable through the Fock gate.
15. Corner-reflector geometry between leg and ground or body and vehicle: the RCS enhancement that safety systems actually rely on.
16. Digital-twin calibration: fit pose plus clothing dielectric to measured radar returns (inverse problem).
17. Joint antenna-taper plus radome co-design: high-dimensional, essential-differentiability.
18. Weather and rain-attenuation coupling to the VRU detection margin (not diff-essential, listed for completeness).
19. Worst-case scenario *mining* for a certification dossier: gradient walk in (pose, orientation, range, clothing) to reach the min-margin case faster than random sampling.
20. Physics-anchored neural sensor model: use AEGIS gradients to keep a fast learned radar model physical in the rare tail (gradient-regularized domain randomization).
21. Interference and radar-to-radar ghosting (not body-related, out of lens, noted and dropped).

---

## 2. What AEGIS actually has for this lens, verified in the repo

- SMPL-X parametric bodies, four phantoms, pose streams at 30 Hz, and an inertial-mocap error model.
  `src/aegis/geometry/pose_stream.py` loads AMASS-derived axis-angle streams; `virtual_imu.py`
  simulates a consumer IMU pose estimator (4 deg per-joint RMS default). `verified` by reading both
  files. This is the raw material for a micro-Doppler generator: limb kinematics over time.
- Fock-regime limb scattering. `geometry/fock_gate.py` and `kernels/level6_diffraction.py` implement
  the impedance-corrected Fock creeping-wave gate, validated against an exact cylinder solution per
  the `project_diffraction_fock` memory. `verified` in code; the cylinder validation is `inferred`
  from the memory note, not re-run here.
- No scattered far field. Grep confirms AEGIS keeps the absorbed fraction `T0` and discards the
  reflected `1 - T0`. The only radar code, `src/aegis/sensing/rcs.py`, is a *link-budget* module:
  it takes RCS as a scalar input (`rcs_dbsm: float = 0.0`, line 171) and explicitly says it "omits
  ... micro-Doppler, polarimetric processing." `verified` by reading the file. So the radar signature
  the lens needs is not built. It is reachable from the same `G̃_t` operator (swap transmittance for
  reflectance, evaluate the PO radiation integral toward the sensor instead of at the surface), which
  is the brief's "discarded half," but it is engineering that does not exist today, not a feature.
- SMPL-X pose to vertices runs in PyTorch (`geometry/parametric.py`), so the pose to signature chain
  is not one autodiff graph yet. `verified`. Same known bridge the brief flags in 2.1.

Implication: every idea in this lens that needs a radar signature (1, 2, 3, 4, 8, 9, 10, 11, 13, 14,
15, 16, 19, 20) requires building the PO scattered-field forward model first. That is real work, and
it is the pivot from a dosimetry library to a sensing library. Ideas 5, 6, 7, 12, 17 (the fascia and
wearable side) need the same scattered-field model but on a dielectric panel rather than a body.

---

## 3. The market. Who sells radar sensor simulation, and how do they model a pedestrian

Named incumbents, `verified` they exist and target this market (web sources listed at end):

- **Ansys** AVxcelerate Sensors, HFSS SBR+, and Perceive EM (perCVM). SBR+ since 2021 R2 assigns
  dielectric materials to fascia, bumpers, radomes, and lenses and propagates rays by Snell's law
  inside the dielectric. Perceive EM is a GPU shooting-and-bouncing-ray PO channel and radar solver
  (per the internal `project_ansys_perceive_em` memory and the 2024 webinar source). `verified`.
- **dSPACE** AURELION: deterministic real-time camera, radar, lidar, ultrasonic sensor simulation for
  HIL, SIL, VIL. `verified`.
- **Siemens** Simcenter (Prescan lineage): HIL radar-based perception simulation, markets pedestrian
  safety explicitly. `verified`.
- **MathWorks** Radar Toolbox and Automated Driving Toolbox, plus RoadRunner Scenario for Euro NCAP
  VRU scenarios. `verified`.
- **Scenario and validation platforms**: IPG CarMaker, Applied Intuition, Foretellix (Foretify),
  aiSim (aiMotive). `verified` they exist and sell scenario-based ADAS validation. Their radar is
  typically a phenomenological or point-target model fed by an external EM tool, not an in-house PO
  solver. `inferred` from the point-scatterer literature below, not confirmed per-vendor.

How they model the pedestrian, and the suspicion the brief asked me to check. The literature is
explicit and it confirms the suspicion with a twist:

- The two mainstream methods are the **point-scatterer** model (markers at head, torso, arms, knees,
  feet driven by mocap, cheap, runs at radar PRF) and **shooting-and-bouncing-ray PO** (accurate,
  too slow for PRF, "usually used only for still human poses"). `verified` (Deep et al., IET RSN
  2020; the SBR corner-case papers).
- The point-scatterer model "has shown excellent correlation in ... micro-Doppler and micro-range
  features" but "is very inaccurate in estimating RCS magnitude ... does not include the effects of
  shadowing and multipath interactions between different body parts." `verified` (same source).
- MathWorks' own tutorial models a pedestrian as "an isotropic scatterer with 1 square meter RCS."
  `verified`.

So the incumbent pedestrian model is either a static or motion-driven point cloud that gets
micro-Doppler roughly right and RCS magnitude badly wrong, or a slow SBR pass on a frozen pose. The
gap AEGIS's speed claim points at is exactly this: a physics-based, shadowing-aware, articulated
signature fast enough to run across pose and time, sitting between the cheap-but-wrong point model
and the accurate-but-slow SBR. That gap is real. `verified` the gap exists; whether AEGIS's
first-order PO is accurate *enough* to be worth the extra cost over a point model is the open
question of section 5.

Who is the buyer. `inferred`: for development and coverage testing, the OEM and Tier-1 perception
teams and the sensor vendor. For the tool itself, the validation-tooling vendor (Applied Intuition,
Foretellix, dSPACE) who would embed a better pedestrian model, or Ansys who would extend SBR+. A
two-person EU firm sells *to* the tooling vendors or *to* an OEM advanced-engineering group, not a
new platform against dSPACE and Ansys.

Pricing: `could-not-check`. EDA-grade EM tools and HIL sensor simulators are enterprise-licensed,
commonly five to six figures per seat-year, but I did not find and will not invent a number. The
Ansys academic Perceive EM line is 3,300 EUR/yr non-commercial per the internal memory, which is a
credibility-anchor price, not a product price.

---

## 4. The regulation. Is there a mandate that creates a buyer

This is the strongest part of the lens and the brief said it is the single most important question,
so I answer it directly.

Yes, a mandate exists, and it is unusually hard. `verified`:

- **EU General Safety Regulation (EU) 2019/2144 (GSR II)** makes advanced emergency braking
  mandatory on new M1 and N1 types, and AEB that detects and responds to **pedestrians and cyclists**
  became mandatory from **7 July 2024**. This is a legal requirement, not a consumer program.
- **UN Regulation No. 152** (02 series) is the technical AEBS regulation listed in Annex I of GSR II,
  and it defines the car-to-pedestrian and car-to-bicycle detection and braking requirements.
- **Euro NCAP** VRU AEB/LSS protocols (current VRU assessment protocol v11.4, AEB LSS VRU test
  protocol v4.3) drive the consumer five-star rating on top of the legal floor.

So there is a buyer created by law, which is the EMF-compliance analogy the brief wanted. But two
qualifications cut against a naive read:

- The *accepted* homologation and rating test is still **physical track testing** with a standardized
  articulated soft pedestrian target that has a **calibrated radar signature**. Simulation today is
  used for development, coverage, and pre-selection of physical test cases, not as the accepted
  homologation proof for the *radar-perception* path. `verified` in outline; the precise share of
  simulation permitted per UN R152 annex I could not be pinned to a clause and is `could-not-check`.
- **Euro NCAP Vision 2030** does expand virtual testing, but its virtual-testing focus is
  **crashworthiness** (frontal, whiplash, occupant diversity), where the model credibility problem is
  tractable, not radar-perception active safety. `verified` (Vision 2030 roadmap and the ESV
  crashworthiness paper). The regulator's own confidence bar for accepting a *sensor-physics*
  simulation as proof is not yet met, and closing it is a standards-body multi-year process.

Consequence for the sale. The mandate creates a large *development and coverage* market (discretionary
but well funded, because every OEM must pass and wants to minimize expensive track runs). It does not
yet create a *mandated simulation deliverable* the way IEC 62232 mandates an EMF uncertainty budget.
The closest thing to a mandated, billable, differentiability-native deliverable in this lens is the
**test-dummy fidelity and coverage argument** a manufacturer files to justify simulation credibility,
which is idea 8 plus idea 9. That is a wedge, not a market on its own.

---

## 5. The physics validity. Is first-order PO adequate for a pedestrian at 77 GHz

The regime is favorable in the ways the brief predicted and fatal in one way it warned about.

Favorable, `verified`:

- A pedestrian at 76 to 81 GHz is electrically large (a torso is hundreds of wavelengths) and skin
  depth is negligible, so the surface-current PO ansatz is physically apt on the lit, smooth,
  convex parts (torso, thighs, back). This is AEGIS's validity regime.
- Measured pedestrian RCS at 77 GHz is well documented, which means a validation target exists:
  median about -11.1 dBsm at 6.2 m, and a Gaussian aspect distribution with mean about -9.4 dBsm and
  std 4.2 dBsm (JRC and academic measurement studies). `verified`. Polarimetric and RCS-pattern
  datasets also exist (arXiv 1910.13706 and the JRC 24/77 GHz dummy-versus-human study). So a company
  can validate a PO signature against real numbers, not just against another simulator.

Fatal for the headline idea, `verified` by reasoning from the same literature and brief 2.3:

- The point-scatterer literature states plainly that a primitive or first-order model "does not
  include the effects of shadowing and multipath interactions between different body parts" and is
  "very inaccurate in estimating RCS magnitude." First-order PO on triangles has the *same* blind
  spot: no leg-to-torso multi-bounce, no leg-to-ground corner reflector, no ground two-ray, no edge
  diffraction (PTD) off the shoulders and limbs. The Fock gate fixes creeping waves around single
  smooth cylinders, not multi-body interactions.
- The low-RCS configurations an adversarial optimizer seeks are precisely the *nulls*: aspect angles
  and poses where the strong specular returns cancel and what remains is multipath, edges, and creeping
  waves, that is, everything first-order PO omits. So the model is least trustworthy exactly at the
  optimum the gradient marches toward. This is brief section 2.3 realized in the worst possible place.
  A pose that PO says is a deep null may be a modest return in reality once the leg-ground corner and
  ground bounce are included. `inferred`, and it is a strong inference from measured-versus-PO
  disagreement in the RCS-magnitude literature.

Testable in-house before betting anything. Compare grad(PO-RCS) against grad(measured or SBR RCS)
with respect to aspect angle and a one-parameter pose (for example arm-swing phase), and report the
gradient cosine similarity as a function of how close you are to a null. If similarity collapses near
nulls, ideas 1, 2, 3, 9, 19 are on sand and must be labeled coverage-heuristics, not certificates.
AEGIS already has the cylinder-validation harness (`tests/test_fock_diffraction.py`) to extend. This
is the single most important experiment before the lens is pitched. `inferred` it is doable in-house.

Published measured pedestrian RCS to validate against: yes, named above. `verified`.

---

## 6. Converge: the ideas that survive, graded

Grading axes from brief 7: problem exists, Robin can fill it reliably, patentable, doable in two
years by two people, market size, and the decisive one, does value depend on differentiability
essentially or decoratively.

### 6.1 Differentiable fascia and radome plus antenna co-design (ideas 5, 6, 17)

- Problem exists: yes, and it is expensive. Bumper paint (especially metallic), emblems, heater
  grids, and variable-thickness fascia degrade installed radar boresight and sidelobes. `verified`
  that the problem is real and that Ansys SBR+ is sold specifically to model it.
- Fit to AEGIS validity: best in the whole lens. A fascia panel is a smooth, electrically large,
  lossy dielectric layer, which is where first-order PO is *strongest*, not weakest. No articulated
  nulling body, no micro-Doppler. AEGIS's `T0`-plus-Fresnel machinery is already a layered-dielectric
  model.
- Differentiability: essential, not decorative. The design vector is per-triangle coating impedance
  and local thickness, that is 10^4 to 10^5 parameters (brief 3a's high-dimensional candidate). A
  sweep is hopeless there, gradients win.
- Patentable: weak. "End-to-End Differentiable RCS Optimization on 3D Geometry Based on Physical
  Optics" is already published (IEEE Xplore doc 11002686), and adjoint-plus-AD RCS shape optimization
  goes back to Bondeson 2004 and the ACES adjoint-AD paper. `verified`. So differentiable-PO-for-RCS
  is not novel as a method. Any patent would have to be narrow (the specific fascia-plus-installed-
  antenna co-design loop, or the speed mechanism), and it sits in Ansys's core EDA territory.
- Doable by two people in two years: the forward model yes, competing with HFSS SBR+ on trust no.
- Market: real and moneyed (radar Tier-1s and OEM fascia teams) but owned by Ansys.
- Grade: strongest *physics* fit, weakest *defensibility*. This is a paper and a consulting wedge,
  not a company, because the incumbent is Ansys and the method is published.

### 6.2 Certified or prioritized worst-case VRU coverage over the pose-configuration continuum (ideas 9, 19, 8)

- Problem exists: yes. An OEM must argue its AEB detects a pedestrian across the continuum of poses,
  orientations, and ranges, and today it samples a handful and hopes (brief section 5's exact
  observation, restated for radar). A tool that finds the min-margin configuration faster than random
  sampling, or bounds it, is genuinely wanted for a certification and coverage dossier.
- Differentiability: essential. This is the brief's patent-move applied to sensing: a supremum (here
  an infimum of detectability) over the *configuration* continuum, which nobody offers because nobody
  had a differentiable geometry-to-signature map. It aligns exactly with brief section 5.
- Patentable: this is the most promising patent angle in the lens, because it is the configuration-
  continuum certificate rather than the excitation-continuum eigenvalue (which is prior art) and
  rather than differentiable-PO-RCS (which is prior art). The novelty would be the *certified coverage
  over pose-space for a VRU detection dossier*, not the gradient itself. `inferred`, needs an FTO pass.
- The fatal caveat, stated honestly: a coverage *certificate* is only as trustworthy as the PO
  gradient in the low-RCS tail, and section 5 shows that is exactly where PO is least valid. A
  certified *lower bound* on detectability built from a model that over-predicts RCS in the nulls is
  unsafe in the one direction that matters. So the honest product is a **coverage-gap finder and
  test-case prioritizer** ("here are the poses your track test should include, ranked"), not a
  safety certificate. Reframed that way, the PO error is tolerable because a human re-checks the top
  candidates physically. Framed as a certificate, it is dangerous and I will not endorse it.
- Doable by two people: the prioritizer yes, the branch-and-bound certificate no without a validated
  PO error bound.
- Grade: best differentiability-essential and patent-aligned story, but demoted from "certificate" to
  "prioritizer" by the physics. As a prioritizer it competes with the adversarial-scenario-generation
  literature (AdvSim, STRIVE, diffusion methods), which operates at the trajectory level and treats
  the sensor as a black box. AEGIS's differentiator is that it perturbs *pose and geometry through the
  sensor physics*, which that literature does not. `verified` that literature is trajectory-level.

### 6.3 Physics-based articulated pedestrian signature as a data and model asset (ideas 4, 11, 20)

- Problem exists: yes, synthetic radar data for perception training and rare-VRU coverage (child,
  wheelchair, stroller) is bought today, and the parametric body pipeline generates those geometries
  cheaply. `verified` the market buys synthetic sensor data.
- Differentiability: the plain synthetic-data use is decorative (a non-differentiable SBR pass also
  produces labeled cubes). The essential-differentiability twist is Sobolev supervision: hand the
  neural sensor model not just the signature but d(signature)/d(pose), so it learns the *local
  response surface*, which is what makes a learned model generalize into the tail. That is a genuine
  and defensible use of gradients, but its value is unproven and it is a research bet.
- Grade: a complement to the incumbents, not a wedge against them. Worth one experiment, not a plan.

### 6.4 The headline the lens was named for: adversarial pose search (ideas 1, 2, 3), graded and downgraded

The brief told me to test this rather than assume it, and it does not survive its own test as a
business.

- Would a sweep over 20 canonical poses be good enough. Largely yes. The safety-relevant hard cases
  are kinematic and known: a pedestrian crossing perpendicular has near-zero radial velocity and thus
  near-zero bulk Doppler; a standing pedestrian has no micro-Doppler; a partially occluded pedestrian
  loses returns; elevation nulls from the ground two-ray drop the target at specific ranges. These are
  captured by a modest structured sweep over orientation, gait phase, range, and occlusion, not by a
  63-dimensional gradient hunt. The high dimensionality of SMPL-X pose is real but most of it
  (finger-level and fine posture) does not move the 77 GHz signature enough to matter. So the design
  space that *matters* is not high-dimensional, which is brief 3a's own kill criterion.
- The PO-gradient-in-the-null problem (section 5) means the sub-degree pose the optimizer finds as a
  "deep null" is probably a PO artifact, not a physical vulnerability.
- Therefore differentiability here is decorative. This is the honest answer to the lens's central
  bet.

Ethics, as brief section 4 requires. The identical computation is "find the pose that makes a
pedestrian invisible to a car's radar" and "find the coverage gap the manufacturer must harden
against." The sign of the objective and the consent of the person decide which it is. The
defensible framing, and the only one I would publish or ship, is the coverage-gap and test-case
prioritizer delivered to the OEM or regulator, whose objective is to *close* the gap, with the human
being protected. A deliverable whose output is an evasion recipe handed to someone who wants a person
not to be seen by a braking car is out of scope and I would refuse it. I would publish the method as
"worst-case VRU detectability for AEB robustness," release the coverage finding rather than an
evasion cookbook, and never ship a "how to be invisible to radar" mode in a product. This is a
paragraph of tension, not a refusal, exactly as the brief framed it: the same math serves both, and
the protective sign is the one to build.

---

## 7. Bottom line and recommendation

- The market is real, large, and mandate-backed (GSR II plus UN R152, pedestrian AEB mandatory since
  July 2024). That is a genuinely strong point and rarer than most lenses in this study will find.
  `verified`.
- AEGIS's assets do line up on paper (parametric bodies, pose streams, Fock limbs, a ray-tracing
  bridge, a speed claim that targets the exact point-versus-SBR gap). But the fit is inverted from the
  hypothesis: AEGIS's physics is *weakest* on the nulling articulated pedestrian (multipath, ground
  corner, edges, which first-order PO omits) and *strongest* on the smooth dielectric fascia, which is
  Ansys's owned turf with published differentiable-PO prior art.
- Differentiability is decorative for the pedestrian-detection framing that named the lens, and
  essential only for the fascia design and the pose-coverage prioritizer, of which the latter is the
  one novel, patent-aligned, protective-sign play, and even it is demoted from "certificate" to
  "prioritizer" by the PO validity ceiling.
- Do this before betting: run the grad(PO-RCS) versus grad(measured or SBR-RCS) cosine-similarity
  experiment near nulls (section 5). It is cheap, it is in-house, and it decides whether any of the
  signature-based ideas are certificates, prioritizers, or noise. If the gradients hold up near nulls,
  idea 6.2 as a prioritizer plus a KU Leuven 28 GHz array measurement partner (brief section 6) is a
  credible paper and possibly a wedge. If they do not, this lens is a synthetic-data complement to the
  incumbents and nothing more.
- Overall grade for the lens as a *company*: weak-to-moderate. As a *paper plus wedge* aligned with
  the patent-move: moderate, contingent on the null-gradient experiment. Do not build the company on
  "adversarial pedestrian pose."

---

## Sources

Marked by what they support. All are `verified` as retrieved on 2026-07-09 unless noted.

- Pedestrian RCS and micro-Doppler at 77 GHz: JRC "Radar Cross Section Measurements of Pedestrian
  Dummies and Humans in the 24/77 GHz Frequency Bands" (publications.jrc.ec.europa.eu, JRC78619);
  "Polarimetric Radar Cross-Sections of Pedestrians at Automotive Radar Frequencies" (arXiv
  1910.13706); "Micro-Doppler characteristics of pedestrians and bicycles ... at 77 GHz"
  (ResearchGate 317396901).
- Point-scatterer versus SBR fidelity: Deep et al., "Radar cross-sections of pedestrians at
  automotive radar frequencies using ray tracing and point scatterer modelling," IET Radar Sonar Nav
  2020; Chipengo, "From Antenna Design to High Fidelity, Full Physics Automotive Radar Sensor Corner
  Case Simulation," Modelling and Simulation in Engineering 2018; MathWorks "Modeling Target Radar
  Cross Section."
- Simulation tools: dSPACE AURELION product page; Ansys AVxcelerate Sensors and "New HFSS SBR+
  Technology in 2021 R2"; Ansys SBR+ installed-antenna application brief; Siemens Simcenter HiL
  pedestrian-safety blog; MathWorks RoadRunner Euro NCAP AEB.
- Regulation: EUR-Lex Regulation (EU) 2019/2144; ATIC UN R152 AEBS homologation notes; Euro NCAP AEB
  LSS VRU Test Protocol v4.3 and VRU Assessment Protocol v11.4; Euro NCAP Vision 2030 roadmap PDF;
  Klug et al. "Euro NCAP Virtual Testing - Crashworthiness" (ESV 27-000284); TUV SUD simulation-
  validation for homologation.
- Adversarial and worst-case scenario generation (trajectory-level, sensor as black box): AdvSim
  (CVPR 2021); STRIVE and related diffusion and RL adversarial-scenario papers (arXiv 2410.08453,
  2408.03200, 2505.11247).
- Differentiable PO RCS prior art: "End-to-End Differentiable RCS Optimization on 3D Geometry Based
  on Physical Optics Method" (IEEE Xplore 11002686); Bondeson et al., "Shape optimization for radar
  cross sections by a gradient method," IJNME 2004; ACES "RCS Reduction and Shape Optimization using
  Adjoint Method and Automatic Differentiation."
- Internal: `src/aegis/sensing/rcs.py`, `src/aegis/geometry/{pose_stream,virtual_imu,fock_gate,
  parametric}.py`; memory `project_ansys_perceive_em` (Perceive EM is PO-based SBR, non-differentiable,
  3,300 EUR/yr academic).
</content>
</invoke>
