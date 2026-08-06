# Inversion: a differentiable forward model is an inverse solver

Lens 05, for the differentiability study. Written 2026-07-09 after reading the brief, the JSAC
archeology, the coherent and parametric-body code, a web literature scan, and after building and
running a working toy inverse-scattering demo in this repo's venv.

Bottom line up front, so nobody has to dig for it:

1. The white-space claim in the brief ("nobody in RF has a differentiable forward model of a human
   body scattering RF") is **false as of late 2025**. Differentiable RF forward models are now a
   crowded, fast-moving area. Sionna RT has shipped one since 2023. A December 2025 paper from
   Tsinghua does differentiable pose recovery from mmWave specifically. A recent IEEE paper does
   differentiable *surface physical optics* for RCS. AEGIS is not alone in the room.
2. AEGIS still occupies a **narrow, genuinely under-populated corner**: differentiable surface PO on
   a *parametric deforming body mesh*, with pose gradients, at high frequency. Nobody I found does
   exactly that. But the corner is narrow, and the reason it is empty may be that it does not work
   well, not that nobody thought of it.
3. I built the toy demo the brief asked for and **it mostly fails**, in an instructive and
   physically robust way. Gradient descent through a coherent PO surface operator into SMPL-X pose
   recovers a single degree of freedom weakly and falls apart at three or more. The loss goes down
   while the pose error goes up. This is not a bug in my code, it is the physics: the coherent phase
   loss at 28 GHz has a convergence basin of order one wavelength (about 1 cm), and a pose change
   moves the body surface by 10 cm or more, so the optimiser starts tens of wavelengths outside the
   basin in a speckled, multimodal landscape. This is exactly why the entire field uses machine
   learning (which learns the global map) instead of gradient descent (which only refines locally).
4. The honest role for differentiability in RF human sensing is therefore **local refinement given a
   good initialisation, plus exact sensitivity and uncertainty**, not from-scratch inversion.
   From-scratch inversion is where ML wins and will keep winning.
5. The one place inversion has a real, physics-shaped buyer is **not human sensing at all**. It is
   the closed digital-twin calibration loop (recover the *environment* and array state from pilots,
   AEGIS's own JSAC2 idea) and array/near-field metrology, where the "training data" is a specific
   deployment that will never be seen twice, so ML has nothing to train on. Human sensing is the
   wrong target. Scene and hardware self-calibration is the right one.

No `NEEDS_CONTEXT` blockers. Everything below I either verified against a source, ran myself, or
marked as inference.

---

## 1. Diverge: the raw idea list (applications of a differentiable inverse solver)

Unfiltered, one line each. Grading comes later. `[ess]` = I expect differentiability to be
essential, `[dec]` = decorative (a sweep, surrogate, or ML would do as well or better), `[?]` =
argued below.

1. Gradient-based SMPL-X pose recovery from mmWave returns (the headline idea). `[?]`
2. Body *shape* (betas, 10-300 dim) recovery from returns, pose fixed. `[?]`
3. Gait and micro-motion recovery over time from a coherent sequence. `[dec]`
4. Vital-sign sensing (respiration, heartbeat) as a 1-3 dim chest-wall phase fit. `[dec]`
5. Fall detection for elderly care. `[dec]`
6. Occupancy and people-counting. `[dec]`
7. Airport and stadium mmWave body-scanner image reconstruction (24-30 GHz surface scattering). `[dec]`
8. Concealed-object detection as a residual between measured returns and a fitted clean-body model. `[?]`
9. Through-wall search-and-rescue localisation. `[dec]`
10. Automotive in-cabin child-presence and occupant classification (Euro NCAP, 60 GHz). `[dec]`
11. Material and clothing identification from the reflectance spectrum. `[dec]`
12. Array calibration by fitting a *known* phantom in a known pose. `[?]`
13. Recovering *environment* geometry rather than the body (scene reconstruction). `[?]`
14. Digital-twin correction of a ray-traced scene from uplink pilots (the JSAC2 closed loop). `[ess]`
15. Antenna near-field to far-field transformation and radome distortion correction. `[?]`
16. SAR and ISAR autofocus (recover platform motion that maximises image sharpness). `[dec]`
17. RIS phase-configuration inversion (recover the surface state that explains a channel). `[ess]`
18. Joint calibration of material EM properties and geometry for an RF digital twin. `[ess]`
19. Breast/limb phantom reconstruction for medical microwave imaging. `[dec]`
20. Body-worn-antenna placement inverse design against a measured on-body channel. `[?]`
21. "Physics prior" as a differentiable regulariser inside an ML sensing net (best of both). `[ess]`

That last one, 21, is the sleeper and I return to it. It is the honest way physics enters a field
that ML already owns.

---

## 2. Does it already exist? (verified literature)

The brief's instruction was to search hard and note that classical inverse scattering is volumetric
and low-frequency while AEGIS is surface and high-frequency. That distinction holds, but the gap it
implies is smaller than the brief hoped.

### 2.1 Differentiable RF forward models already exist and are not rare

- **Sionna RT** (NVIDIA, Hoydis et al., arXiv 2303.11103, IEEE 2023). *verified.* A differentiable
  ray tracer for radio propagation. Computes gradients of the channel impulse response with respect
  to material properties, antenna patterns, array geometries, and transmitter/receiver positions and
  orientations. Explicitly marketed for ISAC, localisation, digital twins, and RIS. This is the
  incumbent differentiable RF forward model, it is free, GPU-native, and NVIDIA-backed. It does *not*
  ship a parametric body or pose gradients, and it uses hard-visibility (Mitsuba) ray tracing, which
  is the exact object of the brief's moat hypothesis 2.2(b). But "nobody has a differentiable RF
  forward model" is simply not true, and Robin should stop saying it.
- **DiffeRT** (Eertmans, Robin's own collaborator). *verified by memory + brief.* Differentiable RT.
  Same category. This one is inside Robin's network, which is an asset, not a threat.
- **DIPR / PPPR** (Han et al., Tsinghua, arXiv 2512.23054, published in ACM IMWUT / Ubicomp 2025).
  *verified, read the HTML.* Claims "the first fully differentiable simulation of the mmWave radar
  process from human kinematic primitives," and does exactly the headline idea: gradient descent on
  observed radar heatmaps to recover human pose, with kinematic plus electromagnetic constraints.
  Crucially it is **not** surface PO. It models each joint as a Gaussian primitive carrying scattering
  intensity and Doppler signature, and re-renders a heatmap through an analytic FMCW signal pipeline
  (signal modulation, Doppler, array phase, two-way path loss). It is phenomenological, not Maxwell.
  So AEGIS's surface-PO-with-Fresnel forward model is more physical, but the flag on "differentiable
  pose recovery from mmWave" is already planted, in a top venue, five months before this study.
- **PODM-mmHPE** (IEEE Xplore 11321285, 2025). *verified (abstract).* Uses a physical-optics RF
  simulation pipeline to generate synthetic RF from 3D human meshes, then a diffusion model to make
  it realistic, then trains an ML pose estimator. PO is used as a *data generator*, not an inverse
  operator. ML still wins at inference. This is the pattern to expect: physics feeds the ML, it does
  not replace it.

### 2.2 Differentiable inverse scattering is also already a field

- **DeepCSI** (arXiv 2508.10555, Aug 2025). *verified.* Differentiable contrast source inversion,
  fully autodiff, handles full-data, phaseless, and multi-frequency. This is the classical
  volumetric/low-frequency corner going differentiable, exactly as the brief predicted. Confirms the
  brief's framing that classical ISP is volumetric.
- **End-to-End Differentiable RCS Optimization on 3D Geometry Based on Physical Optics** (IEEE Xplore
  11002686). *verified (title + abstract).* Differentiable *surface* PO, used for RCS shape
  optimisation (stealth design), gradients to shape without dimension reduction. This is the single
  most direct hit on the brief's 2.2(a) claim that "the discarded half is RCS." Someone already built
  a differentiable surface-PO RCS engine. It is aimed at design, not sensing, but the primitive AEGIS
  would need for the RCS story is published prior art now.
- Classical adjoint RCS (Sciopen S1000-6893.2024.30347). *verified (abstract).* Adjoint Maxwell with
  absorbing material, gradients wrt shape, material, coating thickness. The design-side inverse
  problem is mature.

### 2.3 Human sensing is ML-dominated, and everyone knows why

- **RF-Pose, RF-Pose3D, RF-Avatar** (Katabi group, MIT CSAIL, CVPR 2018 onward). *verified.*
  Through-wall pose and 3D mesh from WiFi-band signals, pure deep learning, trained by cross-modal
  supervision from a synchronised camera because "humans cannot annotate radio signals." RF-Pose3D
  reports ~4-5 cm per-keypoint error. This is the canonical RF human-sensing result and it is 100%
  data-driven. It exists *because* there was no usable differentiable physical forward model to invert.
- **WiFi CSI sensing generalization surveys** (arXiv 2503.08008 and the awesome-wireless-sensing-
  generalization list). *verified.* The field's central open problem, stated plainly, is the domain
  gap: models trained in one environment collapse in an unseen one. This is the single best argument
  for a physics forward model, and I develop it in section 5.

Net: the corner AEGIS uniquely occupies is "differentiable surface PO on a parametric deforming body
mesh with pose gradients, for sensing." I found no paper doing exactly that. But the neighbours are
all occupied, and by well-funded incumbents.

---

## 3. Is the inverse problem well posed? The toy demo, and what it says

The brief said a working toy demo beats three pages of speculation. I built one in this repo's venv.

### 3.1 What I built (real code, real SMPL-X, real autodiff)

`scratchpad/inv_scatter.py`. The chain is: SMPL-X body_pose (63 dim, PyTorch, differentiable) ->
10475 vertices -> triangle facets -> a coherent physical-optics *scattered*-field forward model
(reflectance not transmittance, radiation integral toward observers, the brief's "discarded half")
-> a complex multistatic channel `h` at an 8x8 transmit/receive arc at 2 m, 28 GHz. This is torch
end to end, so `loss.backward()` propagates from the channel residual through the PO integral and
through SMPL-X linear blend skinning into pose. I verified the SMPL-X pose gradient is finite and
nonzero (norm ~7000), so the autodiff graph is real and the brief's "bridge not absence" gap (SMPL-X
in torch, AEGIS field channel in JAX) is easily closed by simply doing the whole thing in torch, as
I did. The PO forward model uses smooth softplus illumination and receive gates (the differentiable-
render trick) and a sharp specular lobe. Self-shadowing is omitted, which is a real limitation and
sits exactly where the brief's 2.3 gradient risk lives.

The experiment: pick a true pose by perturbing N joints, simulate `y = g(theta_true)`, start from a
perturbed guess, and run Adam on `||g(theta) - y||^2`.

### 3.2 What happened (this is the finding)

Recovery, single frequency, 8x8 multistatic, increasing pose dimension (from `inv_scatter.py`):

```
dims=1  : pose err 0.088 -> 0.063 rad,  vert RMSE   2.3 mm   (weak recovery)
dims=3  : pose err 0.558 -> 0.659 rad,  vert RMSE  17.7 mm   (loss down, pose WORSE)
dims=6  : pose err 0.417 -> 0.653 rad,  vert RMSE  24.1 mm   (loss down, pose WORSE)
dims=12 : pose err 0.967 -> 0.798 rad,  vert RMSE  86.6 mm   (marginal, unreliable)
dims=21 : pose err 1.114 -> 2.088 rad,  vert RMSE 696.0 mm   (diverges hard)
```

In every multi-parameter case the loss dropped by 2-3x while the pose error stayed flat or grew.
That is the signature of a **non-injective, multimodal** inverse problem: a *different* pose fits the
observed returns as well or better than the true one. Widening to a 2 GHz, five-tone band did not
rescue it (dims=6: 0.417 -> 0.691). More antennas did not rescue it either.

Two follow-up experiments (`scratchpad/inv_basin.py`, `scratchpad/inv_fast.py`) pin the mechanism:

Basin sweep, coherent single frequency, 6 dims, Adam lr 0.02, starting *close* to the truth:

```
init 0.007 rad -> final 0.242 rad   (diverges)
init 0.014 rad -> final 0.290 rad   (diverges)
init 0.028 rad -> final 0.331 rad   (diverges)
init 0.070 rad -> final 0.535 rad   (diverges)
init 0.417 rad -> final 0.633 rad   (diverges)
```

Even a 7 milliradian start (surface motion well under a wavelength) walks *away* from the truth. And
the gradient direction quality, measured as cos(-gradient, direction-to-truth) averaged over 6 seeds:

```
dist 0.005 rad: mean cos +0.17     dist 0.050 rad: mean cos +0.06
dist 0.010 rad: mean cos +0.18     dist 0.100 rad: mean cos +0.15
dist 0.020 rad: mean cos -0.01     dist 0.200 rad: mean cos +0.19
```

For a well-posed problem this cosine should approach +1 as the distance shrinks. Instead it sits near
0.1-0.2 and even crosses zero (and on another seed it was -0.49, pointing actively *away*). The
coherent gradient is **nearly orthogonal to, or anti-aligned with, the direction that would fix the
pose**, at every distance, dominated by speckle phase-winding. A learning-rate control confirms this
is not a step-size artefact: from a 0.02 rad start, lr 2e-2 wanders off (0.041 -> 0.315 rad), and
lr 5e-4 down to 1e-4 simply freezes in place (0.041 -> 0.041 to 0.044 rad) because there is no
downhill-toward-truth direction to follow. A 4 GHz seven-tone band did not help either (0.014 ->
0.377 rad). The gradient does not point anywhere useful, even 5 mrad from the truth.

### 3.3 Why, and why it is robust (the wavelength-basin argument)

This is not a code artefact, it is the physics of coherent high-frequency scattering, and it is the
core well-posedness answer the brief demanded.

At 28 GHz the wavelength is 1.07 cm. The coherent channel `h(theta) = sum_t a_t exp(-j k d_t(theta))`
is a sum over ~10^4 facets of terms whose phase winds through 2*pi every time a round-trip path
length `d_t` changes by one wavelength. A pose change of a few tenths of a radian at a joint moves
distal surface points by 10-30 cm, which is 10-30 wavelengths, so every facet phase winds many full
turns. The result is a speckled loss landscape whose local minima are spaced on the order of a
wavelength in surface-displacement terms. Gradient descent has a capture basin of at most ~lambda.
Starting a pose optimisation 10 cm away is starting 10+ basins away. The gradient points into the
nearest speckle trough, not toward the truth.

I checked whether simply discarding phase (a magnitude-domain observable `||h| - |y||^2`) helps.
It does not, at single frequency. The gradient cosine is if anything *worse*:

```
dist 0.01 rad: coherent +0.18   magnitude +0.07
dist 0.05 rad: coherent +0.06   magnitude -0.00
dist 0.10 rad: coherent +0.15   magnitude -0.02
dist 0.20 rad: coherent +0.19   magnitude +0.08
```

so I will not claim the magnitude domain rescues it. The magnitude of a single-frequency coherent sum
is itself speckled. What real radar sensing systems actually use is *range-Doppler* processing, which
smooths by integrating over bandwidth and over time (motion), a genuinely different transform I did
not implement. That is a real and important caveat: my toy uses the hardest instantaneous observable,
and a range-Doppler front end plus learned priors is why RF-Pose, RF-Avatar, and DIPR work at all.
The honest reading is that a naive differentiable-fit on either the coherent or the magnitude
observable is ill-posed, and the field is empirical for good physical reasons.

**Consequence for the business.** The 63-dim SMPL-X pose is where gradients would matter *if the
landscape were benign* (gradient-free CMA-ES or particle filters die by the curse of dimensionality
above ~10 dim, verified in the pose-tracking literature). But the landscape is not benign, so
gradients do not save you globally either. Differentiability buys you *local* refinement inside one
basin, which means you need an initialisation already within a wavelength or two, which means you
need an ML pose estimator or a tracker to hand you that init. Physics refines what ML proposes. That
is idea 21, and it is the only human-sensing framing that survives this experiment.

### 3.4 The gradient-fidelity risk (brief 2.3), marked could-not-check

I did not test `grad(PO)` against `grad(truth)`, because I have no full-wave ground truth for a body
in this environment. The brief's cylinder/Mie comparison is the right test and it remains unrun here.
`could-not-check`. My experiment fails for a reason upstream of PO fidelity (the landscape is
multimodal even with a *perfect* forward model, since I invert the same PO I simulate), so PO
accuracy is not even the binding constraint for from-scratch pose recovery. It would become binding
for the local-refinement use, and there the brief's concern is live and untested.

---

## 4. Converge: the surviving ideas, graded

Grading axes from the brief: problem exists, Robin can fill it, patentable, doable by two people in
two years, market size, incumbent named, and the decisive one, is differentiability essential or
decorative.

### Idea A: digital-twin / scene + array self-calibration from pilots (JSAC2 closed loop). Top pick.

Recover the *environment* geometry, material EM properties, and array/hardware state that best
explain observed uplink pilots or channel soundings, by gradient descent through a differentiable
propagation model. This is AEGIS's own JSAC2 "the network donates its ray-traced scene, calibrated
by your uplink pilots" idea, generalised and pointed away from the body.

- Problem exists: **yes, and it is the RF digital-twin field's stated bottleneck.** A twin is
  worthless until it is calibrated to the specific site, and every site is unique. *verified* that
  Sionna RT markets exactly this (learning materials and orientations by gradient descent, RF-DT
  calibration for ISAC).
- Differentiability: **essential.** The calibration vector is high-dim (per-surface materials,
  per-element phase/gain, positions), and there is no training set because the deployment is
  one-of-a-kind. Finite differences cost 2N forward solves, a sweep is hopeless, and ML has nothing to
  learn from. This is the cleanest "gradients essential" case in the whole study.
- Incumbent: **Sionna RT / NVIDIA, and DiffeRT.** This is a feature, not a market Robin owns. He
  would be a small player against NVIDIA's free tool. The differentiator would have to be the surface
  PO speed (`Q = J^T M J` in ms vs ray-tracing a scene) and the correct soft-visibility gradients
  (2.2(b), unproven).
- Doable by two people: the machinery exists in-repo. Yes.
- Patentable: hard, Sionna RT is prior art for gradient-based RF scene calibration. Narrow claims
  only.
- Verdict: **strategically the right target, competitively crowded.** Grade B+. Differentiability is
  essential here, which is why it belongs at the top, but Robin is not the incumbent and cannot become
  it in the environment sensing corner.

### Idea B: physics prior as a differentiable regulariser inside an ML sensing net (idea 21). Sleeper.

Do not fight ML, feed it. Use the differentiable PO body model as a physics-consistency loss term
(re-render the predicted mesh, compare to the measured return) that regularises an ML pose/mesh
estimator, so the network cannot hallucinate physically impossible configurations. This is precisely
what DIPR and PODM-mmHPE already do with weaker forward models.

- Problem exists: **yes, the domain-gap problem** (section 5). *verified* it is WiFi/mmWave sensing's
  central open problem.
- Differentiability: **essential.** The physics term must be backpropagated jointly with the network.
- Incumbent: **DIPR (Tsinghua, IMWUT 2025) and PODM-mmHPE** already occupy this with Gaussian-primitive
  and PO-augmentation forward models. AEGIS's angle is a *more physical* forward model (surface PO +
  Fresnel + Fock diffraction), which might generalise better across bodies and environments.
- Doable: yes, but it is a research contribution, not obviously a company. It sells as a paper or a
  licensed module, not a product.
- Verdict: **the most intellectually honest human-sensing play, but it is academia, not a BV.**
  Grade B. Good for a paper with Hirata or a sensing group, weak as a business.

### Idea C: array / near-field metrology and calibration against a known target. Solid niche.

Invert a differentiable forward model to recover *hardware* state (per-element phase/gain errors,
mutual coupling, radome distortion, near-field-to-far-field transform) from measurements of a *known*
reference. Here the unknown is the instrument, not the world, and the geometry is known and rigid, so
the landscape is far better behaved than the body case.

- Problem exists: **yes.** *verified* that near-field-to-far-field transformation and array
  calibration are standing metrology problems with real budgets (antenna test ranges, mmWave MIMO
  production calibration).
- Differentiability: **argued essential at high element count.** For a 256-1024 element array the
  calibration vector is 500-2000 real params, above the gradient-free ceiling. Below that a classical
  least-squares or sweep wins, so the value is specifically at massive-MIMO/mmWave scale. `inferred`.
- Incumbent: classical NFFFT (spherical-wave expansion) and vendor calibration routines (Rohde &
  Schwarz, Keysight test ranges). These are entrenched and mostly good enough.
- Doable: yes, small and rigid problem, and AEGIS's "fit a known phantom" trick (JSAC Direction 5,
  Route C) is exactly this. It needs a measurement chamber Robin does not have, but the KU Leuven
  WaveCoRE 28 GHz array (one hour away, in his network) could supply data.
- Verdict: **the most tractable inversion idea and the one whose landscape actually cooperates.**
  Grade B. Real but small. A features-and-services line, not a venture.

### Idea D: concealed-object detection as a clean-body residual. Interesting, hard to enter.

mmWave body scanners (24-30 GHz) are a surface-scattering inverse problem. Fit a clean parametric
body to the returns, then flag the residual (the part the body cannot explain) as a concealed object.

- Problem exists: **yes**, and it is a real, funded market (aviation security).
- Incumbent: **Rohde & Schwarz QPS201, Smiths Detection, Rapiscan.** *verified* R&S QPS uses
  thousands of Tx/Rx at mmWave, holographic reconstruction, then ML anomaly detection. They are
  entrenched, certified (TSA/ECAC), and already do the reconstruction with backprojection, not with a
  parametric body fit.
- Differentiability: **decorative.** Their reconstruction is a linear holographic backprojection, not
  a 63-dim optimisation, and the detection is ML. A differentiable body prior might improve the
  residual, but it is a marginal upgrade to an entrenched, regulated product.
- Doable by two EU people with no chamber and no certification path: **no.** Grade C. Right physics,
  unreachable market.

### Ideas that fail the differentiability test (correctly downgraded)

- **Vital signs (4), fall detection (5), occupancy (6), people-counting, gait (3), through-wall S&R
  (9), in-cabin child presence (10):** all `[dec]`. These are 1-3 dimensional or classification
  problems. Vital signs is a chest-wall phase fit in ~2 dof, verified to be handled by physics
  micro-motion models plus DL for harmonic separation, no high-dim inverse anywhere. In-cabin CPD is
  a mandated (Euro NCAP 2025) 60 GHz market, verified, but it is presence/vital detection solved by
  TI's AWRL6432 reference design and ML, with no role for a 63-dim differentiable body. Gradients are
  decorative because the dimension is low, and the brief's own rule (gradients beat sweeps only above
  ~10 dim) kills them. These are large markets that AEGIS's differentiability does *not* unlock.
- **Material/clothing ID (11), SAR/ISAR autofocus (16):** autofocus is a handful of motion params
  (decorative), and material ID is a low-dim spectral fit (decorative).

---

## 5. The business question: where is RF training data actually unobtainable?

The brief's honest suspicion is right: ML wins wherever training data is cheap, physics wins only
where data is expensive, safety-critical, certifiable, or the corner case is rare by construction. I
tested it against the sensing landscape.

Where RF training data is **cheap** (ML wins, physics decorative): pose, gait, activity, fall,
occupancy, vital signs, in-cabin. You put a camera next to the radar, cross-modally supervise (exactly
RF-Pose's method, *verified*), and collect millions of frames. The domain-gap problem is real but the
field is attacking it with more data and domain generalisation, not with physics. A two-person firm
cannot out-data MIT CSAIL, Tsinghua, or the automotive Tier-1s.

Where RF training data is **expensive or unobtainable** (physics has a shot):

- **One-of-a-kind deployments.** An RF digital twin of a specific factory or stadium has no training
  set, because that exact scene exists once. Calibration must be model-based. This is idea A, and it
  is why A is the top pick despite the crowded incumbent. *inferred*, well-grounded.
- **Instrument self-characterisation.** A specific antenna array's per-element errors are unique to
  that unit. You calibrate against a known target with a model, not against a dataset. Idea C.
- **Certification and uncertainty.** Not sensing at all, but this is where "physics not data" is
  *legally* required (brief 3c: IEC 62232/63195, ISO GUM sensitivity coefficients). ML cannot supply
  a `c_i = dy/dx_i` uncertainty budget, autodiff can, in one pass. This is boring and it is the
  strongest physics-over-data link in the whole study, and it is orthogonal to inversion. My lens
  points at it sideways: the same differentiable forward model that would do inversion also emits the
  sensitivity coefficients a regulator demands. That deliverable does not care that inversion is
  ill-posed.

The uncomfortable synthesis: **inversion of a human body is the wrong place to sell physics.** The
data is cheap there and the inverse problem is ill-posed there. Physics sells where the target is a
unique deployment or a unique instrument (no data), or where a regulator mandates a sensitivity
budget (no ML allowed). Inversion is the mechanism, but the buyer is in calibration and certification,
not in human sensing.

---

## 6. Grading summary and the differentiability verdict

| Idea | Problem real | Robin can fill | Patentable | 2yr/2ppl | Market | Incumbent | Diff essential? | Grade |
|---|---|---|---|---|---|---|---|---|
| A. Twin/scene+array self-cal from pilots | yes | partly | narrow | yes | large | Sionna RT/NVIDIA | **essential** | B+ |
| B. Physics prior inside ML sensing net | yes | yes | weak | yes (paper) | n/a | DIPR, PODM | **essential** | B |
| C. Array/near-field metrology cal | yes | yes | narrow | yes | mid | R&S/Keysight/NFFFT | essential at scale | B |
| D. Concealed-object residual | yes | no | weak | no | large | R&S QPS/Smiths | decorative | C |
| Pose recovery from scratch (headline) | yes | **no (ill-posed)** | maybe | demo only | large | DIPR/RF-Avatar | essential but insufficient | C- |
| Vital/fall/occupancy/in-cabin | yes | no | no | yes | large | TI/ML vendors | **decorative** | D |

**Is differentiability essential or decorative for the inversion thesis?** Split verdict, and the
split is the finding:

- For *from-scratch human pose/shape recovery*, differentiability is **essential but insufficient.**
  You need gradients (the 63-dim space kills gradient-free search), but gradients alone lose to the
  multimodal coherent landscape, so you also need an ML init, at which point the ML is doing the hard
  part and physics is polishing. My toy demo is the evidence: gradients present, autodiff correct,
  recovery still fails from a realistic start. This is the idea the lens was built to test, and it
  does not carry a business on its own.
- For *scene and instrument calibration* (unique deployment, unique hardware, high-dim unknown, no
  training data), differentiability is **essential and sufficient**, and this is where inversion earns
  money. The landscape is better behaved because the geometry is known and rigid, and there is
  genuinely no data to train an ML alternative.
- For *low-dimensional sensing* (vital signs, occupancy, fall, in-cabin), differentiability is
  **decorative** and those markets, large as they are, are not unlocked by AEGIS's gradients.

The lens's own headline idea (backprop into SMPL-X pose from returns) is the weakest of the survivors.
The lens's strongest contribution is negative and clarifying: it shows *why* RF human sensing is
ML-dominated (the coherent inverse problem is ill-posed by wavelength), and it redirects the
inversion value to calibration, where the physics-over-data logic is airtight and the data genuinely
does not exist.

---

## 7. Claims ledger

- Sionna RT is differentiable, gradients wrt materials/positions/orientations, marketed for ISAC and
  digital twins: **verified** (arXiv 2303.11103, IEEE 2023).
- DIPR/PPPR does differentiable mmWave pose recovery with a non-PO Gaussian-primitive forward model,
  Tsinghua, ACM IMWUT 2025: **verified** (arXiv 2512.23054, read HTML).
- PODM-mmHPE uses PO as a data generator plus diffusion plus ML: **verified** (IEEE 11321285 abstract).
- DeepCSI differentiable contrast source inversion, volumetric, phaseless/multifreq: **verified**
  (arXiv 2508.10555).
- Differentiable surface-PO RCS shape optimisation already published: **verified** (IEEE 11002686 title/abstract).
- RF-Pose/RF-Avatar are pure ML with cross-modal visual supervision, WiFi band, through-wall,
  ~4-5 cm keypoint error: **verified** (rfpose.csail.mit.edu, rfavatar.csail.mit.edu, CVPR 2018).
- WiFi CSI sensing's central open problem is the domain gap to unseen environments: **verified**
  (arXiv 2503.08008 survey).
- R&S QPS201 body scanner uses thousands of Tx/Rx at mmWave, reconstruction plus ML anomaly detection:
  **verified** (rohde-schwarz.com product page).
- Euro NCAP mandates child presence detection from 2025, direct sensing (60 GHz radar / TI AWRL6432,
  NOVELIC): **verified** (euroncap.com protocol, ti.com SSZT046, novelic.com).
- Gradient-free search (particle filters/CMA-ES) suffers curse of dimensionality above ~10 dim while
  gradient methods scale: **verified in spirit** (pose-tracking particle-filter literature, the exact
  10-dim threshold is my rounding of the brief's own figure, **inferred**).
- The coherent PO pose inverse problem is multimodal with a ~lambda basin, recovery fails from a
  realistic 10 cm start and even from a 7 mrad start: **verified by my own experiment**
  (`scratchpad/inv_scatter.py`, `scratchpad/inv_basin.py`, `scratchpad/inv_fast.py`, run in this
  repo's venv 2026-07-09). The wavelength-basin explanation is **inferred** from the results plus
  standard coherent-imaging theory.
- The coherent gradient cosine to the truth direction stays near 0.1-0.2 (sometimes negative) at all
  distances down to 5 mrad, i.e. the gradient is nearly orthogonal to the pose fix: **verified by my
  own experiment**. A magnitude-domain (phase-discarded) observable is no better and often worse:
  **verified**. Range-Doppler processing over bandwidth and time was **not** implemented and is the
  right smoothing front end, so my toy tests the hardest case: **stated as a caveat**.
- `grad(PO)` vs `grad(truth)` fidelity near shadow boundaries: **could-not-check** (no full-wave
  ground truth available in this environment, and the brief's cylinder/Mie test remains the right unrun
  experiment).
- SMPL-X pose->vertices is differentiable in torch with finite nonzero gradient, and the whole
  pose->scattered-field chain runs as one autodiff graph if kept in torch: **verified** (I ran it).

Reproduce: the three scripts are preserved in the repo at
`spinoff/differentiability/inverse_sensing_demo/`: `inv_scatter.py` (forward model + recovery
dimension sweep), `inv_basin.py` (basin sweep), `inv_fast.py` (gradient-cosine and magnitude-domain).
They are self-contained (SMPL-X + torch, no AEGIS imports needed), about 120 lines total, and were run
with this repo's `.venv/bin/python` on 2026-07-09. Run `inv_scatter.py 4` for a fast (subsampled)
pass.
