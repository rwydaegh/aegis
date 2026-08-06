# Certified suprema over continua: the patent relocation

Lens 07. Author: certified-suprema agent. Date: 2026-07-09.

NEEDS_CONTEXT (non-blocking, for tightening one claim only): the word "certified" in the strict
sense hinges on whether a rigorous, computable, one-sided physical-optics error bound exists for a
lossy penetrable convex 3D body. I read abstracts but could not read the primary sources. If you
want that question closed, fetch: Chandler-Wilde, Graham, Langdon, Spence, "Numerical-asymptotic
boundary integral methods in high-frequency acoustic scattering," Acta Numerica 21 (2012), and any
explicit PO error bound for penetrable scatterers in terms of curvature radius over wavelength. My
verdict below (no usable a-priori constant, only a validated empirical margin) stands on the
literature I could see, but those two would confirm or break it.

---

## 0. Verdict in three sentences

The supremum over the **excitation** continuum (the eigenvalue of Q) is prior art and cannot be the
claim, as the previous study established. The supremum over the **configuration** continuum is
**genuinely novel in method but has low value in AEGIS's own domain**, because in the electrically
large smooth-body regime where physical optics is valid, the absorbed-power functional is provably
smooth in configuration, so testing four canonical postures already captures the true worst case to
within about 4 percent, which is smaller than the model's own 3 to 10 percent error and far smaller
than the 2.2x safety factor the field already applies. The one genuinely new and defensible technical
result is narrow and beautiful: **the Fock shadow-transition is what makes the local certificate
finite rather than vacuous**, because a hard-visibility gate gives an infinite Lipschitz constant and
the physically correct penumbra gives a finite one, but this enables a low-value certificate, so it
is a moat around a small castle.

---

## 1. Raw idea list (diverge first, 21 ideas, one line each)

1. Certified sup over excitation (lambda_max of Q). DEAD, it is the MRI VOP.
2. Certified sup over body pose/orientation via Lipschitz branch and bound. The thesis. Novel method, low value (this report).
3. Certified sup over antenna / array position (same machinery, position DOF).
4. Certified sup over frequency band (worst frequency in an operating band).
5. Certified/robust sup over tissue-permittivity uncertainty (a bound holding for every skin epsilon in the IT'IS interval).
6. Certified sup over array manufacturing tolerance (worst exposure over the calibration-error ball).
7. Certified sup over the user population (worst body in a parametric SMPL-X shape family).
8. Certified sup over the joint excitation x configuration product (the honest "complete" worst case).
9. Certified sup over a time-varying trajectory (worst instant over a motion path).
10. Worst-case link budget: min SINR over configuration (flip the sign, comms QoS guarantee).
11. Worst-case interference to a victim receiver (max leakage over precoders), an EMC coexistence certificate.
12. Robust minimax design: a coating / RIS / array phase set optimal for the worst object orientation.
13. Certified worst-case RCS over aspect angle (the discarded reflectance half, signature management).
14. Certified sensing coverage: min detectability over target pose (guarantee a sensor sees the target).
15. Certified safety envelope for near-field focusing arrays (the one regime where position sampling can miss a focal spot).
16. Certified worst-case SAR in healthy tissue during hyperthermia over patient position (protect, not harm).
17. Minimax emitter placement to minimize the worst-case public exposure over all standing positions.
18. Certification-as-a-service: a signed worst-case certificate API for array + environment + body class.
19. A single certified power-reduction-factor curve that bounds exposure for all configs, replacing the statistical 95th percentile with a guaranteed one.
20. Differentiable ISO-GUM sensitivity coefficients c_i = dy/dx_i in one autodiff pass (mechanism c, boring, billable).
21. Certified worst-case for genuinely new systems that have no statistical model yet (RIS, cell-free, ISAC), where worst-case is the only defensible bound.

Ranking and defence in section 6. The short version: 1 is dead, 2 is the assigned thesis and it is
weak, and the survivors that carry differentiability essentially are 5/6/7 (uncertainty
certificates), 13/14 (the discarded half, another lens), and 21 (novel systems with no standard yet).

---

## 2. The mathematics: the bound, its hypotheses, and where it fails

### 2.1 The inner supremum over excitation is closed form and exact (for the model)

For a fixed configuration theta, absorbed power is a quadratic form in the excitation x. With
`Q(theta) = sum_t area_t * G_t(theta)^H G_t(theta)` (Hermitian PSD, built in `exposure_operator.py`,
verified), and `||x||^2 <= 1`,

```
sup_x  x^H Q(theta) x  =  lambda_max(Q(theta))                       (total absorbed power)
sup_x  ||G_t(theta) x||^2  =  sigma_max(G_t(theta))^2                 (pointwise density at triangle t)
sup_x  x^H Q_A(theta) x  =  lambda_max(Q_A(theta)),  Q_A = sum_{t in A} area_t G_t^H G_t   (4 cm^2 patch)
```

All three are exact and in closed form. This is the Virtual Observation Point move
(Eichfelder-Gebhardt 2011, `verified` via search PubMed 21604294, and the ZMT Q-Matrix toolbox). It is prior
art and is not the claim. Everything below is about the **outer** supremum.

### 2.2 The outer supremum over configuration: the proposed certificate

Let Theta be a compact box in configuration space (orientation, position, and in principle pose), and
let `f(theta) = lambda_max(Q_A(theta))` be the worst-patch worst-excitation absorbed density. I want
`B >= sup_{theta in Theta} f(theta)`, computed in finite time and provably an upper bound.

The machinery is Lipschitz branch and bound, made sound by two eigenvalue facts.

**Weyl (the crossing-proof Lipschitz bound).** For Hermitian A, B, `|lambda_max(A) - lambda_max(B)|
<= ||A - B||_2`. Hence `|f(theta) - f(theta')| <= ||Q_A(theta) - Q_A(theta')||_2 <= L_Q ||theta -
theta'||`, where `L_Q = sup_{Theta} ||dQ_A/dtheta||_2`. This holds with no assumption that the
eigenvalue is simple, so eigenvalue crossings do not break it.

**Branch and bound.** Cover Theta with boxes {B_i} of radius r_i. On each box,
`f(theta) <= f(center_i) + L_Q r_i`. The running upper bound `U = max_i [f(center_i) + L_Q r_i]` is a
valid certified upper bound at every step, and refining the box that attains U drives `U` down to
`sup_theta f` monotonically from above. To tolerance epsilon the worst-case node count is
`O((L_Q diam(Theta)/epsilon)^d)` in dimension d, but far fewer when f is smooth (few local maxima),
which section 3 shows it is.

**The gradient, for seeding and for efficiency.** By Hellmann-Feynman, when lambda_max is simple,
`d lambda_max/d theta = v^H (dQ/d theta) v` with v the top unit eigenvector. This is the exact
gradient AEGIS's autodiff already delivers (`compute_sab()` returns raw JAX arrays for the caller to
differentiate, `engine.py:753`, and transmitter-position gradients are finite-difference validated at
`rtol=1e-3`, `tests/test_jax_grad.py:242,267`, `verified`). At a crossing lambda_max is convex but
nondifferentiable, and the Clarke subdifferential is the convex hull of `{v_i^H (dQ/d theta) v_i}`
over the top eigenspace (Lewis-Overton nonsmooth eigenvalue optimization applies). **Important
practical point: the certificate does not use the gradient, it uses the Weyl operator-norm bound, so
the nonsmoothness is only an efficiency problem for seeding, never a soundness problem.**

### 2.3 The Lipschitz constant is finite, and here is why it is not vacuous

The brief's central hope was that the Fock soft-gate bounds the derivative where a hard shadow makes
it infinite. The answer is yes, but scoped, and the scoping is the interesting part.

**Aggregate metric (lambda_max of the full or patch Q): the Fock gate is not needed for finiteness.**
Analytically, near the terminator the gate derivative scales as `m = (kR/2)^(1/3)` in the incidence
angle, but the penumbra band that contributes has angular width `~ 1/m`, so in the surface integral
the `m` and the `1/m` cancel and the relative Lipschitz constant of the integral is `O(1)` per radian
independent of frequency. Measured on the 20908-triangle SMPL-X body at 28 GHz over a full
orientation revolution (289 points, 1.25 degree steps, `verified`):

```
relative Lipschitz of lambda_max(Q(theta))  =  0.55 / rad   (both fock and none)
lambda_max swing over a full turn           =  26.6 %  (fock),  27.7 % (none)
top eigengap (lam1-lam2)/lam1               =  0.72 everywhere  (no eigenvalue crossings occur)
```

A hard ReLU ("none") gate gives the same 0.55/rad, because for a curved body the silhouette sweeps
continuously and the integral is Lipschitz regardless of the gate. So the Fock gate's value for the
aggregate certificate is accuracy, not finiteness.

**Local metric (per-triangle or sub-patch density) under self-occlusion: the Fock gate is essential
and this is the real result.** When one body part shadows another, a hard-visibility gate (a ray-cast
occlusion test, as in Sionna RT or DiffeRT) flips the local density from full to zero as the occluder
edge sweeps past, so `d(density)/d theta -> infinity` as the mesh refines and the Lipschitz constant
is +infinity, and the branch-and-bound certificate is **vacuous** (`U = +infinity`). The Fock gate
replaces the step with the physically correct transition of finite width `~ (k R_occ)^(-1/3)`.
Measured directly on the gate function `fock_g` (`verified`):

```
max_xi | d |g(xi)|^2 / d xi |  =  0.68   (soft and hard, grid-independent, converged)
=> local-density configuration-Lipschitz <= m_occ * 0.68,  m_occ = (k R_occ / 2)^(1/3)
   = 1.6 /rad  (28 GHz, R_occ = 5 cm)   ...   3.8 /rad  (60 GHz, R_occ = 30 cm)      FINITE
vs a hard step: max |d/dc| = 1.7e3, 1.7e4, 1.7e5 at grids of 2e3, 2e4, 2e5    DIVERGES as 1/dc
```

The deep point is not numerical convenience. The **true** field near a smooth-convex self-shadow also
has a finite Fock penumbra, so the physically correct Lipschitz constant is finite and about
`m_occ * 0.68`. A hard-visibility differentiable ray tracer is therefore not merely inconvenient at
silhouettes, it is **wrong about the Lipschitz constant** (it reports infinity where physics says a
few per radian). This is the sharpest, most defensible technical statement available here, and it is
exactly the moat claim of brief section 2.2(b), now made quantitative. Caveat, stated plainly:
AEGIS's production coherent self-occlusion (the distal gate) is not yet the clean `fock_g` transition
on the coherent path. Testing the shipped `distal_gate` (exp2) showed a knife-edge component that
reintroduces a sharp feature, and the memory notes the coherent path injects no creeping field into
deep shadow. So the finite-Lipschitz property is a `verified` property of the Fock gate math and an
`inferred`, not-yet-wired property of the end-to-end coherent self-shadow certificate. It is
bridgeable, but it is not done.

### 2.4 The bound, assembled, with hypotheses and failure modes

```
B_model      =  max_i [ lambda_max(Q_A(center_i)) + L_Q * r_i ]           (branch-and-bound cover)
B_conservative =  B_model * (1 + m_PO_validated)                          (one-sided model margin)
```

Hypotheses:
- H1 the body is electrically large and smooth (kR >~ 25, R > 2.5 lambda) so PO is valid and the Fock
  penumbra is resolved. (`R > 2.5 lambda` is the standard rule of thumb, `verified` via search.)
- H2 single-bounce is dominant. AEGIS's one specular recapture is a ray-cast pass excluded from the
  autodiff path (brief 2.1, `verified`), so concave multi-bounce focusing is outside the certificate.
- H3 L_Q is finite over Theta. Finite iff the shadow transition is smooth (Fock). Hard visibility
  gives L_Q = infinity and a vacuous B. (`verified`, section 2.3.)
- H4 the configuration-to-Q map is one differentiable graph. True for rigid orientation and position
  (`verified`). **Not yet true for SMPL-X pose**: the pose-to-vertex map runs in PyTorch, outside the
  JAX graph (brief 2.1, `verified`), so L_Q over pose is not computable end to end today. The pose
  certificate is therefore **not enabled** in the sense a patent examiner means, until that bridge is
  built.

Failure modes:
- F1 concavities (armpit, between the legs, a hand over the face) break H2 and can under-predict.
- F2 resonant or small structures, or low frequency, break H1. This is the crux, see section 5.
- F3 no rigorous m_PO exists, so B_conservative is validated, not certified. Section 4.
- F4 pose chain not closed, so the headline "certify over all postures" is not yet enabled. H4.

---

## 3. The sampling critique, quantified: the thesis is weak in AEGIS's domain

The thesis is that standards sample configuration and a coherent agile system can hide the true
supremum between the samples. I tested this on the coherent operator with the real code. The finding
is that in AEGIS's valid regime the exposure functional is smooth in configuration, so sampling is
near optimal and the certified supremum adds little.

### 3.1 What the standards actually sample (`verified` via search)

- IEC/IEEE 62209-1528:2020 (device SAR) measures at a **handful of discrete positions**: left cheek,
  left tilt, right cheek, right tilt against the SAM head phantom, plus flat-phantom body positions.
- IEC/IEEE 63195-1:2022 (6 to 300 GHz power density) is likewise a discrete-position measurement.
- ICNIRP 2020 samples space with the 4 cm^2 averaging area and time with the 360 s window.
- IEC 62232 for 5G massive MIMO is moving in the **opposite direction from worst case**: the "actual
  maximum" method (Thors, Colombi and colleagues) applies a power-reduction factor from the 95th
  percentile of the time-averaged exposure CDF, and a 24-hour Monte Carlo measurement found the true
  maximum "well below the theoretical maximum and lower than existing statistical models predict."
  The industry is deliberately replacing worst case with statistics because worst case is too
  conservative. Selling a tighter worst case is swimming against this tide.

So yes, standards sample configuration. The question is how much the true supremum exceeds the
sampled maximum.

### 3.2 How much the sup exceeds the sampled max (`verified`, this repo)

Coherent operator, SMPL-X neutral body, 4x4 UPA at 1.5 m, 28 GHz, worst excitation at every
configuration (the eigenvalue). Configuration-sampling penalty = (true sup over a fine grid) minus
(max over canonical samples), relative:

```
1-D orientation continuum (289-point fine grid), penalty at 4 canonical orientations:
   aggregate lambda_max(Q):   0.9 %
   local peak density:        3.8 %
   (adding samples to 8/12/24 does not reduce it, the max is a broad plateau)

2-D (yaw x pitch) continuum (19 x 9 fine grid), penalty at 4 yaw x 3 pitch canonical:
   aggregate lambda_max(Q):   0.0 %   (the canonical corners literally hit the max)
   local peak density:        4.0 %   (5.4 % vs yaw-only)
   total dynamic range over the whole 2-D space:  1.3x aggregate, 1.5x local
```

Going from one dimension to two did not grow the penalty. The far-field dosimetry literature agrees:
posture changes peak SAR by a single-digit percent (search summary quoted "within 6.8 %",
`could-not-verify` the exact source). And the MRI world already reaches worst-case-over-position by
**discretely** sampling models and positions (De Greef et al., "Analysis of the local worst-case SAR
exposure caused by an MRI multi-transmit body coil in anatomical models," Phys Med Biol 56 (2011),
DOI 10.1088/0031-9155/56/15/002, `verified` via search, plus 161-position and multi-model studies),
combined with a generalized eigenvalue over the discrete set and a 2.2x VOP safety factor.

### 3.3 Why the metric is smooth, and the contrast with the excitation axis

The absorbed-power functional is a bounded surface integral over a curved body with no resonances in
PO, so it is intrinsically Lipschitz-smooth in configuration (relative constant ~0.5/rad, section
2.3). Contrast the **excitation** axis, which is genuinely sharp: at a fixed pose, the eigenvalue
beats a fixed beam by a scenario-dependent factor (`verified`, this repo):

```
lambda_max / best-of-16-beam-DFT-codebook  =  1.03x   (this LOS scenario is nearly rank-1)
lambda_max / best-of-256-random-beams      =  2.55x
lambda_max / isotropic (trace/M)           =  12.2x
Q spectrum (normalized):  [1, 0.255, 0.047, 0.007, ...]
```

The excitation gap is large when Q is high rank (rich multipath, or the 8 to 32 channel MRI pTx
setting) and small when it is rank-1 (LOS mmWave). Either way it is the eigenvalue, which is prior
art. **The sup that has teeth (excitation) is anticipated, and the sup that is novel (configuration)
has little bite in the domain where PO is valid.** That sentence is the honest core of this report.

### 3.4 The one number that kills the pitch

Put the error terms in the same units:

```
configuration-sampling penalty (what the certificate removes):   ~4 %
PO model error (two-sided, what the certificate cannot remove):  3 to 10 %
mandated / customary safety factor (VOP practice):               120 % (the 2.2x)
```

The certificate tightens the smallest term in the budget. A regulator or a liability lawyer is not
short of the 4 percent. They are short of a defensible margin on the 3 to 10 percent and a rationale
for the 120 percent. This is the strategic error in the thesis: it optimizes the term that is already
smallest.

---

## 4. The soundness trap: "certified" is not honestly available, "validated conservative" is

lambda_max(Q) is the **exact** supremum of an **approximate** model. First-order PO is 3 to 10
percent wrong and the error is **two-sided**, so the eigenvalue certificate can under-estimate the
true worst case. A conservative certificate needs a one-sided margin m_PO that provably bounds the
under-prediction. Grading the three ways to get it, honestly:

- **A-priori rigorous bound.** For smooth convex **impenetrable** scatterers the high-frequency
  scattering literature gives orders: algebraic O(1/kR) error in the lit region, exponentially small
  error in the deep shadow (the neglected creeping wave), and the slowest O((kR)^(-1/3)) convergence
  in the penumbra (`verified` in spirit via search: "smooth convex impenetrable scatterers incur an
  exponentially small frequency-dependent error ... neglecting the exponentially small creeping wave
  fields"). But a **computable one-sided constant for a lossy penetrable 3D body** is not something I
  could find (`could-not-check`, see NEEDS_CONTEXT). **So a rigorous m_PO does not exist off the
  shelf.**
- **Empirically validated margin.** AEGIS already validates against the exact 2D dielectric cylinder
  (`tests/test_fock_diffraction.py`, `studies/diffraction/cylinder_oracle.py`) and the Mie sphere,
  and the Fock gate reproduces the exact p-pol shadow to 0.03 percent and the whole-body integral to
  2 to 4 percent (`verified`, project memory and tests). A one-sided inflation factor validated
  against these oracles **is** obtainable, and it has direct regulatory precedent (the VOP 2.2x).
- **Probabilistic bound.** Possible but weaker than the deterministic tools the field already uses.

There is one physical argument that helps the upper-bound property. The certificate is a bound on the
**maximum over the body**, and the maximum sits in the lit region, where PO error is the smallest
O(1/kR). The deep-shadow under-prediction (exponentially small true field, and AEGIS's coherent path
injects no creeping field there) lowers a quantity that is not the maximum anyway, so it does not
threaten the hotspot bound. This holds unless a concavity focuses energy into a geometric shadow
(F1), which is exactly the case AEGIS's autodiff path excludes.

**Bottom line, in bold as the brief demands: no sound one-sided a-priori PO margin exists today, so
the word "certified" must not be used for a bound on the truth. It may be used only for the supremum
of the model. A defensible product says "validated conservative bound," carries an empirically
validated inflation factor against the Mie and cylinder oracles, and states the residual model
uncertainty explicitly. Anything stronger is overclaiming, and in a compliance product overclaiming
is a liability, not a feature.**

---

## 5. The central mismatch (the deepest finding)

Where a certified supremum would be **valuable**, the metric must be non-smooth in configuration, so
that sampling genuinely misses hidden peaks: resonant structures, small or wire-like objects,
implants, and low-frequency near-field coupling. That is precisely the regime where **physical optics
is invalid** (H1 fails: not electrically large, near field, resonances). Where physical optics is
**valid** (electrically large smooth bodies at mmWave, AEGIS's home), the metric is smooth, so the
certificate removes only single-digit percent and is swamped by model error.

```
                         metric smooth in config?        PO valid?        certificate value
electrically-large mmWave       yes (~4% gap)               yes              low
resonant / implant / low-freq   no (can hide peaks)         no               high but PO can't compute
```

This is not a fixable engineering gap, it is a domain mismatch. It is the strongest reason the patent
should **not** relocate to "certified supremum over body configuration" as an independent claim. The
regime that needs the certificate is the regime AEGIS cannot serve, and the regime AEGIS serves does
not need it.

The narrow exceptions where the two overlap, and the certificate has real bite in AEGIS's domain:
- **Near-field focusing arrays** (idea 15). In the radiating near field of a large aperture the beam
  focuses at a range, with a depth of focus of centimeters, so a person moving through the focus sees
  a sharp position dependence that a standard's coarse distance samples can miss. PO in the radiating
  near field is defensible for a large smooth body. This is the one exposure regime where position
  sampling genuinely fails, and AEGIS's hotspot-tomography work (52 to 168x focused/unfocused gain,
  project memory) is exactly here. But note: finding the worst range is a cheap 1-D scan or a gradient
  ascent, it does not need the heavy branch-and-bound certificate, so even here differentiability is
  useful decoratively (fast scan) more than essentially (high-dim certificate).
- **Genuinely new systems with no statistical model yet** (idea 21): RIS, cell-free massive MIMO,
  ISAC. The IEC statistical machinery lags the technology, so for a brand-new waveform there is no
  95th-percentile model and worst case is the only defensible bound. This is a real, if small and
  transient, niche.

---

## 6. Patentability, and the ranked survivors

### 6.1 Patentability of the configuration certificate

- **Broad claim, "certified worst-case exposure over a continuum of body configurations":**
  anticipated in **goal** (De Greef worst-case over position and anatomy, MRI RF shimming over
  multiple body models, `verified`) and in **method** (Lipschitz branch and bound is a mature field:
  ReachLipBnB arXiv 2211.00608, alpha-beta-CROWN, beta-CROWN, DeepPoly, interval bound propagation,
  all `verified` via search). Dead or near-dead as an independent claim, and an examiner will pair
  the VOP eigenvalue with ReachLipBnB and reject on obviousness.
- **Narrow claim, "a method of obtaining a finite Lipschitz (or curvature) bound on the exposure
  operator by replacing the hard visibility function with the physically-derived Fock
  shadow-transition, thereby rendering a continuous configuration supremum non-vacuous for a local
  exposure metric under self-occlusion":** this is the one non-obvious hook. Nobody in the dosimetry
  world states it (they use FDTD, which has no analytic Lipschitz constant), and nobody in the
  verification world does EM. It is the "physics picked the smoothing kernel, and the smoothing kernel
  is what makes the certificate finite and correct" insight. It is defensible but **narrow**, its
  value is limited by section 5, and its **enablement is at risk** on two counts: L_Q over full pose
  is not yet a closed autodiff graph (H4), and a rigorous global Lipschitz bound over the pose
  manifold (as opposed to a local or empirical one) is not demonstrated. An unenabled claim is a dead
  claim, so before filing anything here the pose chain must be closed and a global L_Q must be
  exhibited, not just a local finite-difference.

### 6.2 The stronger patent direction: the uncertainty axis, not the configuration axis

The certified-supremum machinery is far more valuable pointed at **uncertainty** than at
configuration, because uncertainty quantification is **legally mandated** (ISO GUM, IEC 62232, IEC
63195 all require an uncertainty budget) and today it is done by finite differences or Gaussian
propagation, not by a guaranteed bound. Measured (`verified`, this repo): lambda_max moves **13.1
percent** over a plus/minus 20 percent box in skin permittivity and conductivity, which is larger than
the entire configuration-sampling penalty and comparable to the PO error itself. A bound that holds
for **every** tissue value in the IT'IS interval (ideas 5, 6, 7) is a different axis from the prior-art
excitation eigenvalue, it uses interval or affine arithmetic through the same differentiable operator,
and it converts a mandated line item into a guaranteed one. This is where I would point the IP energy
if any is to be spent on certification.

### 6.3 Ranked survivors, graded

Grades: P = a real problem exists, R = Robin can fill it reliably in the environment he has, N =
patentable/novel, D2 = doable in 2 years by 2 people, M = market size, E = does value depend on
differentiability essentially (E+) or decoratively (E-). Incumbent named.

**Rank 1. The Fock-enabled finite-Lipschitz method as the technical core (idea 2's residue).**
P: yes for local self-occlusion hotspots. R: mostly, the gate exists, the coherent wiring and a global
L_Q do not. N: yes but narrow, this is the only genuinely novel claim. D2: yes for the math, the
enablement work is the risk. M: it is not a market, it is a patent hook that protects the certificate
features. E+: essential, the whole result is a statement about a derivative. Incumbent: none states
it, hard-visibility renderers (Sionna RT, DiffeRT, Mitsuba) get it wrong. Verdict: file this narrow,
do not build a company on it.

**Rank 2. Guaranteed uncertainty certificate over tissue, tolerance, and body population (ideas
5/6/7/20).** P: yes, uncertainty budgets are mandated and currently hand-waved. R: yes, it is the same
operator plus interval arithmetic. N: application-level, interval propagation through a forward model
is known, the EM specialization is the novelty. D2: yes. M: same pre-compliance beachhead as the
device story, sold as a premium "guaranteed uncertainty" tier. E+: essential, you need Lipschitz or
interval bounds over the uncertainty ball, which is autodiff. Incumbent: Sim4Life and ZMT do
sensitivity and Monte Carlo, nobody ships a guaranteed interval bound. Verdict: the strongest
certified-supremum business, and it rides the existing beachhead rather than opening a new front.

**Rank 3. Certified worst-case for novel systems with no standard yet, and near-field focusing (ideas
21, 15).** P: yes but emerging and small. R: yes. N: the system is novel, the method is not. D2: yes.
M: small today, larger later, transient (the standards catch up). E: mixed, a fast scan often suffices
(E-), high-dim RIS phase spaces make it essential (E+). Incumbent: none, because the systems are new,
which is the whole point. Verdict: a research-credibility and first-mover play, not a near-term
revenue line.

**Rank 4 (flag to other lenses, do not build here). The discarded half (ideas 13, 14).** Certified
worst-case RCS over aspect and certified sensing coverage over target pose use exactly this machinery
on the reflectance channel, and those markets are larger than dosimetry (brief 2.2a). But that is the
sensing/RCS lens, not the exposure lens, and the "sup over aspect angle" there is a low-dimensional
sweep that a fast operator handles without the heavy certificate. Worth a cross-reference, not a
claim here.

**Dead. Idea 1 (excitation eigenvalue, VOP). Idea 8's configuration part (low value). Idea 18
(certification-as-a-service over configuration): a feature at best, and pointed at the axis with the
smallest gap, so not a business.**

---

## 7. Ethics

Every idea above is defensive: characterize a hazard, protect a person, certify a device, bound an
uncertainty, or guarantee a sensor sees a target. Ideas 16 and 17 are explicitly protective (minimize
worst-case exposure, protect healthy tissue). Nothing here optimizes a system to increase harm to a
person, and the sign of every objective is toward protection or transparency. Brief section 4 is
satisfied and I did not have to steer away from anything.

---

## 8. What I would tell Robin in one paragraph

Do not relocate the patent to "certified supremum over body configuration." It is novel in method but
the previous study's instinct was too optimistic about its value: in the electrically large smooth-body
regime where your physical optics is valid, the exposure functional is smooth in configuration, four
canonical postures already capture the worst case to about 4 percent, and that 4 percent is smaller
than your own model error and dwarfed by the 2.2x safety factor the field already applies. The one
beautiful, true, defensible technical result is that the Fock shadow-transition is what makes the
**local** certificate finite instead of infinite, and that hard-visibility differentiable ray tracers
are literally wrong about the Lipschitz constant at silhouettes. File that narrow method claim if you
file anything, but first close the pose-to-vertex autodiff bridge and exhibit a global Lipschitz
bound, or the claim is unenabled. And point the certified-supremum energy at the **uncertainty** axis,
not the configuration axis: a guaranteed bound over the tissue and tolerance intervals is mandated by
GUM, moves 13 percent, uses the same operator, and sells into the pre-compliance beachhead you already
have, whereas the configuration certificate is a solution to a problem your own physics tells you is
already solved.
