# Envelope prior art and the VOP question

Agent report 01 for the military / high-power RF study. Written 2026-07-09. Answers the dispatch plus
the orchestrator's four mid-task sharpenings (one-sidedness, the Siemens VOP family, the orthogonal
compressions, and the 4 cm^2 patch mapping). Read `AGENT_BRIEF.md` first. This report attacks Findings
A and B. It is deliberately adversarial.

## 1. Verdict

The certifiable exposure envelope is a real, regulator-blessed instrument and it is **not novel and not
defensible IP**, because its exact object and its two key refinements are published three times over
(MRI VOPs by Eichfelder and Gebhardt 2011, the same as a granted Siemens supervisor patent from 2009,
and the identical eigenvalue-plus-SDP construction for mmWave array power density by Xu et al. 2018 in
AEGIS's own domain). The property that actually makes it a certificate is one-sidedness, which VOP owns
and AEGIS does not yet possess. What survives as defensible is narrow and does not include the envelope:
the fast, differentiable, measurement-free, no-volumetric-solve **surface construction of the field
channel** in an arbitrary ray-traced environment at mmWave.

## 2. The three things that most changed my view

1. **The full envelope, including the constrained version the brief called an open question, is already
   published in AEGIS's own domain.** Xu, Gustafsson, Shi, Zhao, Ying, He, "Radio frequency exposure
   compliance of multiple antennas for cellular equipment based on semidefinite relaxation," IEEE Trans.
   Electromagn. Compat. 2018, pp. 327-336, DOI 10.1109/TEMC.2018.2832445. It models RF exposure as a
   quadratic form in the multi-antenna excitation, states that "when the total transmitted power is
   fixed, the maximum exposure can be determined by an eigenvalue decomposition" (that is Finding A's
   lambda_max(Q) certificate), and that "if an individual antenna has additional power constraint, the
   exposure maximization problem can be relaxed to a semidefinite program," and applies both to
   millimeter-wave array power density. The brief's Finding A explicitly flagged the constrained
   supremum under per-element power limits as the real object that "someone must actually compute." Xu
   et al. computed and published it in 2018, for mmWave power density, which is exactly AEGIS's regulated
   quantity above 6 GHz.

2. **The load-bearing property is one-sidedness, and AEGIS does not have it.** What turns a quadratic
   form into a certificate is not the eigenvalue (that is the 1900s Rayleigh-Ritz theorem, unpatentable)
   but the provable guarantee that the bound never underestimates, with a controlled and pre-quantified
   overestimation. VOP achieves this by Loewner matrix domination (Eichfelder Eq. 7 gives the a-priori
   overestimation bound, tunable by a cap on the complementing matrix norm). AEGIS's lambda_max(Q) is
   the exact supremum over beams of an approximate operator. Because Q is built from a first-bounce
   physical-optics surface channel that is accurate to 3 to 10 percent but two-sided, AEGIS's envelope
   can under-estimate the true worst case. As built it is a best estimate of the worst case, not a
   certified bound on it. That is the single most important gap between what Finding A claims and what
   the code produces.

3. **The FDA precedent is real and verified, but it blesses the runtime supervisor, which is the version
   the military dislikes.** Clinical dynamic parallel-transmit 7T MRI was FDA-cleared in 2024 (Siemens
   Magnetom Terra.X, 510(k)), and its RF safety is a runtime VOP supervisor that measures forward power
   and cuts RF when predicted local SAR exceeds the limit (Fiedler et al., MRM 2025, DOI
   10.1002/mrm.30643). That is software in the safety loop with hardware measurement and abort, the exact
   thing the brief says NOSSA and the Navy boards resist. Finding A sells the opposite, a static
   certificate. The medical precedent supports the general credibility of quadratic-form exposure
   instruments, but it does not directly precedent AEGIS's static artifact, and it is FDA and IEC, not a
   military board.

## 3. What I verified, inferred, and could not check

**Verified from primary sources this session:**
- The full Eichfelder and Gebhardt 2011 paper (PDF in this directory). Equations 1 to 9, the Loewner
  domination construction, the SDP compression, the closed-form two-matrix solution via the spectral
  split Q = Q_+ minus Q_-, the a-priori overestimation bound (Eq. 7), and the explicit page-1474
  statement that the spectral norm of each VOP equals the worst-case local SAR per unit excitation.
- US8547097B2 text (Google Patents). "SAR calculation for multichannel MR transmission systems."
  Assignee Siemens AG, now Siemens Healthineers. Priority 2009-06-26. Inventors Gebhardt and Vester.
  Claim 1 is a runtime quadratic-form SAR supervisor limited to MR by its claim language.
- US8653818B2 text. "Parallel transmission RF pulse design with local SAR constraints." Assignees
  Siemens Healthineers, MIT, MGH. Priority 2011-04-08. Claims designing the excitation under VOP local
  SAR constraints.
- US11940477B2 text. Assignee Notre Dame, priority 2018-01-12. All three independent claims require
  transmitting and measuring. Spec defines local SAR as tr{R_d R_x} with R_d = (sigma/2rho) E^H E.
- Xu et al. 2018 citation and DOI (10.1109/TEMC.2018.2832445), and its scope as quoted above.
- Lee et al. 2012 (DOI 10.1002/mrm.23140), Graesslin et al. 2012 (DOI 10.1002/mrm.24138), Orzada et al.
  2017 (DOI 10.1002/mrm.26398), Fiedler et al. 2025 (DOI 10.1002/mrm.30643).
- IEC 60601-2-33:2022 operating-mode and SAR-limit structure and its requirement of conservative local
  SAR estimates for multi-channel Tx. IEC 62232:2022 actual-maximum beamforming approach. IEC/IEEE
  63195-1 and -2:2023 scope. 7T MRI FDA clearances (Terra 2017, Terra.X 2024) and the research-vs-clinical
  pTx split.

**Inferred, reasoned not quoted:**
- The full FDA-to-VOP mechanism chain in section 8. Each link is sourced, the chain is my synthesis.
- That AEGIS claim 9's operator language collapses onto the Fresnel-surface novelty of claims 1 to 5.
- The obviousness assessment in section 7 (composability of the two compressions).

**Could not check:**
- Verbatim FDA press-release text and the exact 510(k) K-numbers. The FDA press-announcement URL 404s
  and the accessdata 510(k) summary PDFs would not open. Original Terra is widely cited as K173167,
  unconfirmed. Terra.X 2024 confirmed by Siemens and trade press, K-number unconfirmed. Not blocking,
  but pull the two summaries before this goes on a funding slide.
- Xu et al. 2018 full text (ResearchGate 403, IEEE paywalled). Citation, DOI, and the two load-bearing
  sentences are corroborated across two independent searches. If a claim is built on distinguishing it,
  buy or retrieve the full text. This is the one genuine NEEDS_CONTEXT candidate.
- Full claim text of US9417298 / US20130300414A1 (Siemens SAR-hopping) and US11428767, located not read.
- Specific IEC clause numbers. Not invented here.
- US8929828 and the Cluster-1/4/5 device patents are carried from the repo landscape doc, not re-verified.

## 4. Question 1: how bad is the VOP prior art, exactly

Bad for the concept, harmless to the drafted method, and worse than the paper alone because there is a
matching live patent family.

### What Eichfelder and Gebhardt 2011 discloses

Local SAR in subvolume v is a quadratic form in the multichannel drive vector U(t):

```
SAR(S_v) = integral_dt  U^H(t) . S_v . U(t)
```

S_v is Hermitian positive-semidefinite, rank at most 3 (three E-field components). This is the exposure
operator, one matrix per body region, about 300,000 of them at 10 g averaging. VOP replaces them with a
small dominating set A_1..A_N such that A_j minus S_v is PSD (Loewner order), giving U^H S_v U <= U^H A_j U
for all U in C^n. The compression is solved by semidefinite programming, with a closed form for the
two-matrix case via the spectral split Q = Q_+ minus Q_-. The a-priori overestimation is bounded (Eq. 7)
and tunable. And the identity Finding A relies on is stated verbatim on page 1474: the spectral norm of
each VOP equals the worst-case local SAR per unit excitation.

Direct answers to the sub-questions in the dispatch:

- Quadratic form: disclosed (Eq. 2).
- Compression: disclosed (the entire method).
- Worst-case-over-all-excitations bound: disclosed explicitly, and named as the spectral norm.
- One-sided controlled overestimation: disclosed (Loewner domination plus Eq. 7). This is the crown
  jewel and it is theirs.
- Online supervision: disclosed and referenced, deployed today (Fiedler 2025).
- Differentiability: not disclosed.
- Surface construction: not disclosed. VOP is fully volumetric.

### Claim-by-claim map against Robin's set

| AEGIS claim | Disclosed by VOP 2011 | Verdict |
|---|---|---|
| 1 surface mesh, surface integration, dimensionality reduction | No, VOP is volumetric voxels | Safe |
| 2 normals, incident PD, ReLU shadow gate | No | Safe |
| 3 scalar T0 | No, VOP uses full E-fields | Safe |
| 4 Fresnel pseudo-Brewster | No | Safe |
| 5 angle-dependent transmission | No | Safe |
| 6 above 6 GHz skin regime | No, VOP is 297 MHz near field | Safe |
| 7 below 6 GHz layered | No | Safe |
| 8 near-field view-factor, spherical harmonics | No | Safe |
| 9 core: differentiable end-to-end graph | No | Safe from VOP, pressured by Sionna and DeepSig per landscape doc |
| 9 dependent: closed-form exposure operator, coherent MIMO beamforming vector, worst-case envelope | **Yes, the object and the bound are fully disclosed** | The envelope concept is dead as novelty. Only entries-from-Fresnel plus surface plus differentiable survive, and those are claims 1 to 5 restated |

### The Siemens patent family, which is worse than the paper (orchestrator point 2)

A paper is prior art under novelty and obviousness. A live patent is also a freedom-to-operate problem.
The Siemens family exists and is in force.

- **US8547097B2, priority 2009-06-26, Gebhardt and Vester, Siemens.** This is the SAR supervisor itself,
  and it predates the VOP paper. Claim 1 computes a cross-correlation matrix of the drive vector (the
  x x^H outer product), multiplies it by a "hotspot sensitivity matrix" (a compressed set of about 100
  to 1000 hotspot points, a sibling of VOPs), scales by dielectricity to get per-hotspot SAR, and
  reduces or deactivates a channel when a limit is exceeded. That is the quadratic-form compressed-matrix
  runtime supervisor, patented, priority 2009, so in force until roughly 2029 to 2030.
- **US8653818B2, priority 2011-04-08, Siemens plus MIT plus MGH.** Designs the excitation under VOP local
  SAR constraints. This is the design-under-quadratic-constraint, that is AEGIS's ECBF concept, patented.
- **US9417298 / US20130300414A1, Siemens.** Local SAR reduction via SAR-hopping. Adjacent, less central.

Does the MRI limitation save Robin? For FTO, yes. For novelty, no. Two separate answers the orchestrator
asked for:

- **FTO: the MRI claim limitation saves Robin.** Every independent claim of US8547097 and US8653818 is
  tied to a "magnetic resonance tomography system," an "RF pulse," an "examination subject," and MR
  parameters like dielectricity at hotspot points. AEGIS applied to a radar or a base station is not an
  MR system and does not read on these claims. The preamble and the body-of-claim MR limitations are
  genuine scope limits. So AEGIS does not infringe the Siemens family, as long as AEGIS stays out of MRI.
- **Novelty: the MRI limitation does not save Robin.** A patent's MR-only claim scope does not limit its
  effect as prior art. The specification and drawings of US8547097 disclose the quadratic-form
  compressed-matrix supervisor and are citable against Robin's claim 9 regardless of the MR preamble.
  So the Siemens disclosures pile onto Eichfelder and Xu as novelty and obviousness references against
  any AEGIS claim that reads on the operator or the envelope. They do not touch claims 1 to 8.

### The brutal summary of Q1

The quadratic-form exposure envelope, its worst-case-over-all-beams eigenvalue certificate, and its
one-sided controlled-overestimation property are disclosed by a 2011 paper, embodied in a granted
Siemens supervisor patent with 2009 priority, sold as a product (ZMT Sim4Life, which exports Q-matrices
and VOPs with "guaranteed conservativeness for all possible shimming configurations" to meet regulatory
requirements), and independently republished for mmWave array power density by Xu et al. 2018. Robin's
claim 9 as drafted is not anticipated because it hangs the operator off differentiability and
Fresnel-surface entries, but the operator wording carries no independent weight and must not be relied
on. One FTO landmine: if AEGIS ever adds VOP-style Loewner compression of its per-triangle operators, it
would practice Eichfelder and the Siemens family directly. AEGIS as built keeps every triangle and does
not compress, so it is clear today. Keep it that way.

## 5. What actually makes it a certificate: one-sidedness (orchestrator point 1)

This deserves its own section because it reorganizes everything. The commercially and regulatorily
load-bearing property of VOP is not the quadratic form and not the eigenvalue. It is that the bound is
provably one-sided (it never underestimates) with a controlled, pre-quantified overestimation. That is
what a safety board buys. An estimate that is sometimes low is not a certificate at any price.

Three consequences for AEGIS, all sharp:

1. **VOP owns the standard method for making a set of quadratic forms one-sided.** Loewner domination
   plus the Eq. 7 overestimation bound is exactly the recipe. So AEGIS cannot claim "produce a
   conservative exposure bound by dominating a set of exposure matrices." That is Eichfelder and the
   Siemens family.

2. **AEGIS's envelope is exact for Q but Q is a two-sided approximation, so the envelope is not yet a
   certificate.** lambda_max(Q) is the true supremum over beams of x^H Q x, tight and correct as a
   function of Q. But Q is assembled from a first-bounce physical-optics surface channel (assumption A2)
   validated to 3 to 10 percent above 6 GHz. That error is two-sided. It omits higher-order bounces and,
   below 6 GHz, volumetric penetration. So lambda_max(Q_AEGIS) is the exact worst case of an approximate
   model, which can sit below the true worst case. Calling it certifiable without a conservative margin
   is the one claim in Finding A that the physics does not currently support.

3. **The genuinely novel work, if anyone does it, is a provably conservative surface bound, and it is not
   the eigenvalue and not the domination trick.** To reach VOP-grade certifiability, AEGIS would need a
   validated margin added to G_t or to Q that guarantees non-underestimation across the physical-optics
   error envelope, plus scan-sector and per-element excitation constraints. Nobody has published a
   provably conservative physical-optics surface exposure bound for phased arrays. That specific
   artifact, a one-sided surface operator with a validated PO-error margin, is open. But it is unbuilt
   and unvalidated, and its novelty lives in the conservativeness proof, not in the operator or the
   envelope. This is simultaneously the sharpest kill (AEGIS is not a certificate yet) and the clearest
   path (build and validate the margin).

## 6. Question 2: other prior art on worst-case exposure over all beam states

Owned from four independent directions. Two of them, Xu 2018 and the Ericsson and IT'IS EMF-compliance
line, sit inside AEGIS's own domain and are closer than MRI.

| Source | What it owns | AEGIS distinction | Threat type |
|---|---|---|---|
| VOP Eichfelder 2011, US8547097 (Siemens, prio 2009), US8653818 (Siemens, MIT, MGH, prio 2011), ZMT Sim4Life | Quadratic-form envelope from computed fields, Loewner compression, one-sided controlled overestimation, worst-case over all excitations, and pulse design under that constraint | Volumetric FDTD vs surface Fresnel, 297 MHz vs mmWave, not differentiable, fixed coil vs arbitrary environment | Novelty (fatal to the envelope and to one-sidedness-by-domination), FTO only if AEGIS enters MRI or adds VOP compression |
| **Xu et al. 2018, IEEE T-EMC, DOI 10.1109/TEMC.2018.2832445** | Exposure as a quadratic form in the array excitation, max over beams by eigenvalue for fixed total power, SDP for per-antenna power constraints, applied to mmWave array power density | Body-coupled surface operator from a ray-traced environment vs device-emission model, differentiable | Novelty. This is the closest in-domain prior art to Finding A and it includes the constrained version the brief thought was open |
| Hochwald US11940477 (Notre Dame, prio 2018) | tr{R_d R_x} = x^H R_d x, inferring exposure of all possible transmitted signals | Zero measurement, closed-form, design not just characterization | Novelty on the operator, FTO clean (every independent claim requires transmitting and measuring) |
| Hochwald US8929828 (prio 2012, active ~2032) and SAR codes (CISS 2013, IEEE Comm Mag 2014) | Design transmit weights under a quadratic SAR constraint, near-field, device-side | Closed-form continuous-x QCQP and differentiable | FTO and novelty on the precoder, carried from landscape doc |
| IEC 62232:2022, IEC/IEEE 63195-1/-2:2023, and the Ericsson and IT'IS EMF-compliance line (Thors et al. IEEE T-EMC 2016, Baracca and Colombi Monte-Carlo actual-max, Neufeld, Christ, Kuster on the 4 cm^2 averaging area, Bioelectromagnetics 2018) | Standardized worst-case-beam compliance, envelope beam patterns, actual-maximum statistical EIRP, the 4 cm^2 APD averaging area and its conservativeness | Continuous sup by eigendecomposition of a body-coupled operator vs empty-space envelope pattern and statistical power | Novelty on the framing (standardized, so not novel as a concept) |
| Handset SAR-backoff thicket (Qualcomm US11729728 / US11184863, Samsung US12369129, Apple and Qualcomm time-averaged-per-antenna-group US11917559 / US12177797, US12143938) | Time-averaged exposure budget across beams and antenna groups, pick the beam with the most headroom, cap power | No body-coupled operator, runtime device-emission control not design-time bound | FTO only if AEGIS ships a runtime device controller, novelty on budgeting exposure across beams |
| Radar and EW null steering and keep-out zones (US5343211 wide-null phased array, adaptive nulling, sidelobe cancellers, satellite radial keep-out) | Steer a null, paint a static empty-space zone | No body in the loop, no absorbed-power operator, no worst-case-over-beams bound | Prior art for the control action only. Confirms the brief's gap is real |
| HIFU and focused-ultrasound phased arrays | Coherent array drive vectors, grating and side-lobe hazards, safety by output-power monitoring and shutdown | No published quadratic-form-over-all-drive-vectors envelope located | Weak, the envelope math did not cross into acoustics in crisp form |
| Laser and optics MPE and AEL (ANSI Z136, IEC 60825) | Worst-case exposure limits, worst-case pupil, highest power | Scalar single-aperture worst case, not a quadratic form over array weights | Not prior art for the object, analogy only |

Takeaway. Worst-case exposure over all beam states is thoroughly owned in RF medicine (VOP, Siemens,
Hochwald) and in RF telecom (Xu 2018, Ericsson and IT'IS, IEC 62232, IEC 63195). Xu 2018 is the single
most damaging reference for Finding A because it is in-domain and it already published both the
eigenvalue certificate and the per-element-constrained SDP for mmWave power density. The specific object
AEGIS uses, a body-coupled surface operator constructed by the Fresnel law in a ray-traced environment,
differentiable, is still not matched by any of them, and the envelope math is essentially absent as a
formal object in acoustics and optics and as an applied object in the military domain.

## 7. Question 3: where is the defensible novelty, and the two compression questions

The dispatch hypothesis is that novelty relocates to the fast surface construction of Q, differentiably,
at mmWave, in an arbitrary environment, and its use to certify an agile array. Correct in direction, one
level too high. The novelty is the construction of the complex surface **field channel** G_t, the
per-triangle (3, M) block, from the Fresnel-surface law in a ray-traced environment, without measurement
and without a volumetric solve. Once G_t exists, forming Q and taking lambda_max is the trivial step
that VOP, Hochwald, and Xu already teach. The operator and the envelope are parasitic on the channel.

### Straight answer on the two orthogonal compressions (orchestrator point 3)

The question is whether composing Loewner-order spatial compression (VOP, across patches) with low-rank
array compression (Robin's top-8-modes-equal-92.5-percent structure, across the M array ports) is a
novel claimable combination or an obvious combination two examiners would reject.

It is an obvious combination. Straight answer, no hedging on the headline. Reasons:

- Both are standard published techniques. Spatial Loewner compression is Eichfelder and the Siemens
  family. Low-rank truncated-eigen array compression is textbook, and it is literally inside the VOP
  paper's own machinery, which eigendecomposes each matrix as Q_+ minus Q_- and keeps dominant modes.
- They act on orthogonal indices, space and array port, and compose with no interaction. Composing two
  dimensionality reductions along independent axes is the textbook shape of an obvious combination under
  the KSR and the EPO problem-solution frameworks.
- The low-rank array structure is a measured property of the scene, not an invented technique. You find
  it by applying standard truncated eigendecomposition, which VOP already uses.
- Adjacent prior art already manipulates the VOP eigenstructure for compression (Orzada et al. 2017,
  phase-agnostic max local SAR) and Xu 2018 uses the eigendecomposition of the exposure Gram matrix
  directly.

The only thing that could rescue a sliver is a demonstrated surprising technical effect, for example a
proof that this specific composition yields a strictly tighter one-sided bound at a cost neither
achieves alone. AEGIS has not shown such an effect. Absent it, the composition is obvious. Do not build a
claim on it.

### The 4 cm^2 APD patch mapping (orchestrator point 4)

The observation is correct and elegant. The ICNIRP-regulated quantity above 6 GHz is APD averaged over a
4 cm^2 patch, so for patch P it is x^H Q_P x with Q_P a weighted sum of per-triangle operators, and peak
compliance is max_P x^H Q_P x, a max of quadratic forms over patches, which is structurally the VOP
problem. Has anyone written it down? The ingredients are all published, and the mmWave half is explicit:

- The array-excitation half, max over beams of the power-density quadratic form by eigenvalue and SDP,
  is Xu et al. 2018, for mmWave array power density.
- The spatial-max-over-patches-by-compressed-dominating-matrices half is Eichfelder VOP and the Siemens
  family.
- The 4 cm^2 averaging area and its conservativeness are IEC 63195 and Neufeld, Christ, Kuster
  (Bioelectromagnetics 2018).

What I did not find verbatim is the exact sentence "the peak-patch APD compliance of a phased array is a
max over 4 cm^2 patches of quadratic forms, solved by VOP-style Loewner compression over the patches."
So there is a narrow sliver that nobody has printed in that precise form. But by point 3 it is an obvious
combination of Xu 2018 plus VOP plus IEC 63195, and an examiner would combine exactly those three and
reject. Two further reasons the sliver is not worth chasing:

- Xu 2018 already does the array-side worst case for power density. The only missing verbatim piece is
  "compress the patches with VOP," which is applying a known tool to a known problem.
- VOP compression may be unnecessary in AEGIS's regime. VOP exists to squeeze millions of MRI voxels to
  hundreds. A body has only thousands of 4 cm^2 patches, so you can evaluate all of them directly. A
  claim to an optimization nobody needs is weak on its face and easy to design around.

So the mapping is functionally dead as a standalone claim. Note it as insight, not as IP.

### Strongest surviving independent claim I can actually defend

A computer-implemented method for certifying electromagnetic exposure of a body to a coherent antenna
array of M elements, comprising:
1. representing the body as a surface mesh of triangles, each with centroid, area, and unit normal.
2. for each of the M elements, computing a complex vector surface field channel at each centroid by
   propagating that element's field through a reconstructed environment and applying a Fresnel
   transmission coefficient and a shadow-gating factor equal to a rectified dot product of the normal and
   the reversed propagation direction, forming a per-triangle block G_t of shape (3, M), and doing so
   without a volumetric field solve of the body interior and without physical exposure measurement.
3. forming a per-triangle Hermitian operator Q_t = G_t^H G_t and an aggregate Q = sum_t area_t G_t^H G_t.
4. certifying a worst-case local absorbed power density over all unit-norm excitations as lambda_max(Q_t),
   and a worst-case total absorbed power as lambda_max(Q), against a personnel RF exposure limit.
5. wherein steps 1 to 4 form a differentiable computation graph permitting gradients of the certified
   values with respect to excitation weights, element positions, and array geometry.

Honest weaknesses, stated plainly. Steps 3 and 4 in isolation are anticipated by VOP, Hochwald, and Xu.
The claim survives only tied to step 2 (surface channel, no measurement, no volumetric solve) and step 5
(differentiable). The examiner's best rejection is obviousness, take a known surface dosimetry method to
get a per-point field then apply the known eigenvalue envelope math. The rebuttal is that no reference
teaches the combination of a complex per-element surface channel for a coherent array, an end-to-end
differentiable graph, and the no-measurement no-volumetric-solve construction. That is a winnable
obviousness argument, not a clean anticipation defense, and it rests entirely on claims 1 to 8 holding
against the real non-patent threat named in the landscape doc (Kodera 2024, Li 2019, Bamba 2012 and 2015,
Castellanos 2016 on the surface transmission coefficient). If those fall, the operator claims fall with
them. And if the product is to be sold as a certificate, step 4 needs the one-sided margin of section 5,
which is a separate build.

Is the answer "nothing survives"? For the envelope as an independent claim, yes, nothing survives, and it
is now triply anticipated including in-domain by Xu 2018. For the differentiable measurement-free surface
engine that happens to produce an envelope, a narrow obviousness-fight claim survives. Draft around the
engine, never around the envelope.

## 8. Question 4: is the FDA and IEC precedent real

Yes, verified, with four caveats that bound the military transfer.

### The mechanism, link by link

- 7T MRI is FDA-cleared. Terra 2017 (first clinical 7T), Terra.X 2024. Pathway is 510(k), substantial
  equivalence.
- Clinical dynamic parallel transmit was cleared in 2024 (Terra.X). In the 2017 Terra, pTx was
  research-mode only and clinical mode was single channel. So the clinically-cleared pTx precedent is
  recent.
- The governing RF-safety standard is IEC 60601-2-33 (the MR particular standard, an FDA-recognized
  consensus standard). It sets SAR limits (normal 2 W/kg whole body, first-level-controlled 4 W/kg under
  medical supervision, local 10 g limits, 6-minute and 10-second windows) and requires multi-channel
  transmit coils to be controlled by conservative estimates of local SAR.
- The manufacturer satisfies that with a VOP-based online supervisor, precompute Q-matrices from EM
  simulation, compress to VOPs, measure forward power at runtime, apply the VOP quadratic forms, cut RF
  if predicted local SAR exceeds the 10-second or 6-minute limit (Fiedler 2025, Graesslin 2007 to 2012).
  ZMT sells the VOP-generation half.

So the chain is 510(k) recognizes IEC 60601-2-33, which requires a conservative local-SAR estimate for
multi-channel Tx, which the manufacturer produces with a VOP quadratic-form supervisor, which the FDA
then clears. The regulator accepts the quadratic-form envelope as the compliance evidence through a
general conservative-estimate performance requirement. IEC 60601-2-33 does not name VOP. There is no
clause that mandates VOP, there is a clause that mandates a conservative estimate, and VOP is the accepted
way to produce it.

### It is a genuine rebuttal, but narrower than "FDA accepts software envelopes"

Strong and defensible: a live, clinical, FDA-cleared, IEC-anchored precedent that a quadratic-form
exposure model, the same object as AEGIS's Q, is accepted as the safety instrument for a beamforming RF
transmitter operating on a human. That refutes "no regulator will accept a software-computed exposure
envelope." First slide.

Four caveats before anyone over-claims the transfer to a military board:

1. Different regulator, different standard, no cross-recognition. MRI is FDA plus IEC 60601-2-33, a
   medical-device standard. Military RADHAZ is DoDI 6055.11, IEEE C95.1-2345, MIL-STD-464, and NOSSA,
   Navy LSRB, AFNIRSB review. The MRI precedent has zero formal standing with a military board. It is
   persuasive rhetoric, not controlling precedent.
2. MRI is closed and calibrated, a ship topside is open. Known phantom in a known coil, E-fields
   simulated once and validated, drive vector under the scanner's control. VOP's regulatory credibility
   rests on that controlled model. A ship deck has uncertain body positions, uncertain multi-emitter
   far-field geometry, and classified antenna data. AEGIS's application does not inherit VOP's
   controlled-model credibility.
3. The MRI precedent blesses the runtime supervisor, which is the version the military dislikes. The
   cleared mechanism measures power, predicts SAR, and aborts. That is software in the safety loop with
   an abort. Finding A sells the opposite, a static certificate with no runtime software. So the right
   sentence is not "MRI VOP proves the Navy will accept AEGIS's static envelope." It is "MRI already
   clears the harder runtime version of this instrument, so the static version AEGIS proposes is
   strictly easier to certify." A static worst-case bound for a fixed emitter does not even need VOP
   compression.
4. Conservativeness is the currency, and AEGIS is not yet provably conservative. VOP is accepted because
   it provably over-estimates with a tunable, a-priori-known overestimation, per section 5. AEGIS's
   lambda_max(Q) is the exact worst case of an approximate first-bounce operator, not a guaranteed upper
   bound on the true worst case. To earn MRI-grade certifiability, AEGIS must add and validate a
   conservative margin, which is the section 5 build.

### The unifying point

Findings A and B are one fact from two sides. The thing that guts the envelope IP (VOP and Xu are the
identical object, published, granted, commercial, in-domain) is the same thing that de-risks the
regulatory path (a quadratic-form exposure instrument is regulator-accepted). You cannot take the gift
without conceding the threat. Stop treating the envelope as crown-jewel IP or as a novel product. Point
to the medical precedent for its acceptability, and put the IP weight and the pitch on the differentiable
mmWave surface engine that produces the envelope in open, arbitrary, far-field, agile-array environments
where the MRI and the base-station toolchains structurally do not go, and on the one-sided PO-error margin
that would make it a real certificate.

## 9. What would kill this, as a one-week test

Two falsifiable tests, either of which changes the verdict.

**Kill the IP story, half a day.** Ask UGent-appointed counsel one question. Read Eichfelder 2011,
US8547097, and Xu et al. 2018 and answer whether AEGIS claim 9's exposure-operator and worst-case-envelope
language is anticipated or obvious independent of claims 1 to 5. My prediction is that it is, and that the
operator claim needs the Fresnel-surface and no-measurement and differentiable limitations as hard claim
elements to survive. If counsel finds a broader surviving operator claim, I am wrong.

**Kill the certificate claim, one week.** Build one mmWave scene with a phased array and a body mesh.
Compute lambda_max(Q) from AEGIS's surface operator. Compute the true worst-case absorbed power by a
higher-fidelity reference (full-wave or multi-bounce) over a sampled set of beams. If AEGIS ever
under-estimates the reference, the word certifiable cannot be used without the section 5 margin, and the
Finding A product framing needs that margin built and validated first. If AEGIS is always at or above the
reference, the envelope is a genuine bound in that regime. This experiment sits at the center of the whole
Finding A thesis and does not appear to have been run.

## 10. Highest-value next action, and who

Redraft the patent around the engine, not the envelope, before any public disclosure. Robin with UGent
TechTransfer counsel (Filip, Anniek). Concretely: demote the closed-form-exposure-operator and
worst-case-envelope language from anything that reads as independent novelty, convert entries-from-Fresnel,
without-a-volumetric-solve, without-measurement, and differentiable into hard claim limitations, and
anchor the coherent claim to the surface field channel construction. Add Eichfelder 2011, US8547097,
US8653818, US11940477, Xu et al. 2018, and ZMT Sim4Life to the IDF prior-art section with the delta
articulated, so a UGent reviewer or examiner cannot surface them first. The envelope is not the asset. The
differentiable surface engine that builds it in environments MRI and base-station tools cannot reach is
the asset, and a provably one-sided version of its bound is the only thing here that could become a true
certificate and the only thing worth the patent spend.
