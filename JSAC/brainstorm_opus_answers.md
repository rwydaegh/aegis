# Brainstorm answers — round 2

*Response to your reply, 2026-04-24. This answers your direct questions. The companion file `brainstorm_opus_response.md` has the edited main doc (backup in `brainstorm_opus_response_backup.md`).*

## TL;DR on your pushbacks

You're mostly right. After re-reading Part 1 (§5 "Geometric framework", especially the directivity bounds and the 51-frame backflip remark), several things I wrote are over-engineered relative to what your own framework already gives for free. I'm rolling back:

- **The Löwner envelope as the headline robustification.** Your Cauchy-based bound $D(\hat{k}) \le 2$ (with empirical $D_{\max} \approx 1.22$ for Thelonious, and 6.5% posture spread across a backflip) makes the whole-body-SAR worst case *nearly pose-independent already*. Löwner is a legitimate tool for *coherent* ECBF where $\mathbf{Q}$ is high-rank, but it is overkill for the DL plaza story. I was reaching for a hammer when your screwdriver already worked.
- **The claim that the pose-differentiable $\mathbf{Q}$ is the main contribution.** In the far-field (plaza) regime it isn't, because $\mathbf{Q}^{(u)}$ collapses toward rank-one and the pose enters mostly as a *scalar* absorption cross-section. The differentiable-twin story is the right one for near-field / UE-side / below-6-GHz, where the operator structure survives. I'll re-position it.
- **The Brussels-as-vignette advice.** Your response makes me think this was too glib. Brussels is not a mathematical hook, it is a *deployment-blocker* hook, and that's a legitimate thing for a JSAC paper to lean into when you're trying to move Qualcomm engineers and standards people. I'll keep it louder than I first said.

Below are your questions, answered.

---

## 1. What is a Löwner envelope (and why Part 1 obsoletes it for WB-SAR)

**Definition.** For a family of Hermitian PSD matrices $\{\mathbf{Q}(\theta)\}_{\theta\in\Theta}$, a Löwner envelope is any single PSD matrix $\overline{\mathbf{Q}}$ that dominates every member in the semidefinite (Löwner) order:
$$
\overline{\mathbf{Q}} \succeq \mathbf{Q}(\theta) \quad \forall \theta \in \Theta.
$$
"$A \succeq B$" means $A - B$ is PSD, equivalently $\mathbf{x}^H A \mathbf{x} \ge \mathbf{x}^H B \mathbf{x}$ for every $\mathbf{x}$. The *tightest* envelope (minimum trace, say) is the solution of a semidefinite program.

**Why I brought it up.** In the multi-pose ECBF formulation, you want a pose-robust constraint: "for every plausible pose $\theta \in \Theta$, absorbed power below limit." The sharp robust constraint is $\sup_\theta \mathbf{x}^H \mathbf{Q}(\theta) \mathbf{x} \le L$, which is an intersection of infinitely many ellipsoids — not a convex quadratic constraint in $\mathbf{x}$. The Löwner envelope replaces it by a single quadratic: if $\overline{\mathbf{Q}} \succeq \mathbf{Q}(\theta)$ for every $\theta$, then $\mathbf{x}^H \overline{\mathbf{Q}} \mathbf{x} \le L$ is sufficient. Trades looseness for convexity. It's the standard trick in robust QP.

**Why your Part 1 obsoletes it (for WB-SAR).** From your §5:
$$
P_{\text{abs}}(\hat{k}) = S_{\text{inc}} \cdot T_0 \cdot \frac{A_{\text{ab}}}{4} \cdot D(\hat{k})
$$
with $\langle D \rangle = 1$ and $D(\hat{k}) \le 2$ (Cauchy), empirically $D_{\max} \approx 1.22$ on Thelonious, and a 6.5% posture spread across a 51-frame backflip. So: the worst-case whole-body absorbed power, over *any* plane-wave direction and *any* physiologically admissible pose, is
$$
P_{\text{abs}}^{\text{wc}} \le S_{\text{inc}} \cdot T_0 \cdot \frac{A_{\text{ab}}^{\max}}{4} \cdot D^{\max}
$$
with $A_{\text{ab}}^{\max}$ bounded by the convex hull area (your §5.3, $A_{\text{CH}}/A \approx 1.20$ for Thelonious) and $D^{\max} \le 2$ (or $\le 1.5$ as a pragmatic pose-aware bound). That's a pose-independent worst-case compliance check with *no SDP*. Two numbers and an arithmetic.

In operator terms: $\lambda_{\max}(\mathbf{Q}^{(u)})$ is bounded by the same physics, just via a spherical-harmonic expansion of $D(\hat{k})$ (your §5.6 gives $L=6$ for 1% RMS). So the "worst-case operator norm" for whole-body SAR doesn't need Löwner at all — it's a precomputed scalar per body.

**When does Löwner actually earn its keep?** Three cases I can think of:

- **Coherent precoding at high aperture** where the operator is not rank-one and you want to tighten beyond the scalar Cauchy bound.
- **Local APD constraint** (4 cm² averaged, the FR2 binding one), because the per-patch operator family $\{\mathbf{Q}_{\text{loc}}(\mathbf{r}_0)\}$ of your `direction_4` changes *identity* of the active patch with pose — the scalar Cauchy bound doesn't give you per-patch robustness.
- **UE-side / near-field** where body geometry is resolved by the array.

If the JSAC paper is DL plaza, only the second case is relevant, and even there the alternative (hotspot-tracking ECBF from `direction_4`) is arguably cleaner than Löwner SDP. I'd drop Löwner from the paper and keep it as a footnote pointing at `exposure_null_precoding.tex` and future near-field work.

---

## 2. What is the quiet subspace (and why I probably shouldn't have used that word)

**Definition.** Set of precoders $\mathbf{x}$ that radiate zero expected absorbed power to any body in the scene:
$$
\mathcal{Q}(\mathcal{B}) = \{\mathbf{x} \in \mathbb{C}^M : \mathbf{x}^H \mathbf{Q}^{(u)} \mathbf{x} = 0 \ \forall u \in \mathcal{B}\} = \bigcap_u \ker \mathbf{Q}^{(u)}.
$$

**What it is in the far-field rank-1 limit (your paper's regime).** If body $u$ is small compared to the BS angular resolution, $\mathbf{Q}^{(u)} \approx \sigma_u^2 \mathbf{a}^{(u)} \mathbf{a}^{(u) H}$ where $\mathbf{a}^{(u)}$ is the BS-array steering vector toward the body and $\sigma_u^2$ is its absorption cross-section. Then
$$
\ker \mathbf{Q}^{(u)} = \{\mathbf{x} : \mathbf{a}^{(u) H} \mathbf{x} = 0\}
$$
is just "precoders orthogonal to the body-direction steering vector." The quiet subspace is the joint orthogonal complement of $\{\mathbf{a}^{(u)}\}$, which has dimension $M - B$ generically (B bodies, M antennas). **This is the ordinary ZF null space**, with bodies treated as extra "users to null." It's $\mathbf{W} = (\mathbf{H}_{\text{all}}^H \mathbf{H}_{\text{all}})^{-1} \mathbf{H}_{\text{served}}^H$ with $\mathbf{H}_{\text{all}}$ stacking served-user channels and body steering vectors.

So: in your paper's regime, the quiet subspace is not a new mathematical object. It's ZF with a bigger $\mathbf{H}$. I used "quiet subspace" because it reads well, but in the plaza setting, "ZF-dosimetry" is more honest and reviewer-friendly.

**When is the quiet subspace richer?** When $\mathbf{Q}^{(u)}$ is high-rank — coherent near-field, UE-side, below-6 GHz. There, the nullspace of a single body can be a subspace (not just a hyperplane), and the joint quiet subspace is a genuinely larger object. That's where "exposure-null precoding generalizes ZF" has real content.

---

## 3. (ii) and (iii) — am I committing to them, or were they just abstract?

Honestly, they were sketchy. Let me be concrete on each.

### (ii) Translation phasor analytic refresh

**The claim:** $\mathbf{M}(\mathbf{t}) = \boldsymbol{\Phi}(\mathbf{t})^H \mathbf{M}(0) \boldsymbol{\Phi}(\mathbf{t})$ says a translation of the body is a pure phase rotation of the path-exposure Gram; no integral re-computed.

**What I'm committing to:** This is algebraically clean and `direction_5` proves it. It's a real computational win *if* the BS's slot-rate refresh bottleneck is the Gram integral. Your 3 ms/body on a 4-CPU machine with numba says the integral is already cheap for a single body. Per-slot at ms cadence, re-integrating 50 bodies × 25K triangles × M paths once every 100 ms (not every slot) is ≈ 150 ms — tractable for a demo but not real-time if you want translation updates per slot.

**But here is the thing I should have said louder:** in the rank-1 far-field limit, translation updates the steering vector $\mathbf{a}^{(u)}(\mathbf{t}) = \mathbf{a}(\mathbf{p}_u + \mathbf{t})$, which is analytical from the array geometry and body position. No integral, no phase trick. The translation phasor identity is the operator-level analogue of the steering-vector update, and in rank-1 they agree. So: in the plaza regime, per-slot refresh is steering-vector update — $O(M)$ complex exponentials, µs-scale on a GPU.

The translation phasor matters more in high-rank (coherent) regimes, where it gives you the operator update without redoing the Gram. It's still a nice identity, just not load-bearing for the DL plaza paper.

**Revised commitment:** keep as a footnote / Appendix result for the coherent extension; don't build the paper's cadence argument on it.

### (iii) NN surrogate for $\mathbf{Q}(\boldsymbol{\theta})$ with gradient supervision

**The claim:** Train $\mathcal{Q}_\phi(\boldsymbol{\theta}) \approx \mathbf{Q}(\boldsymbol{\theta})$ with pairs $(\boldsymbol{\theta}, \mathbf{Q})$ and *also* $(\boldsymbol{\theta}, \partial \mathbf{Q}/\partial \theta_j)$ → faster convergence, more physical surrogate.

**Honest assessment:** the "faster with gradient supervision" part is real in general (PINN-ish, Sobolev training) but not obviously load-bearing here. In the far-field rank-1 regime, $\mathbf{Q}(\boldsymbol{\theta})$ degenerates to a scalar $\sigma(\boldsymbol{\theta}) \cdot \mathbf{a}\mathbf{a}^H$, so the "surrogate" is a scalar regression from 72-dim pose to 1-dim ACS. That's a 1-afternoon ML project (your words). No need for fancy Sobolev training; ordinary supervised regression works. The $\partial \sigma/\partial \theta$ samples are cheap to generate in AEGIS and could improve sample efficiency but it's not necessary for the paper to work.

**Revised commitment:** replace "neural surrogate with gradient supervision" with "scalar ACS predictor $\sigma(\boldsymbol{\theta})$ trained on AEGIS simulations, evaluated per-body at pose-update cadence." That's the real story. Simpler, truer, fits-in-one-paragraph.

---

## 4. Cadence, concrete

You asked for a deep dive. Here's one. This is the version I'd put in the paper.

### What has to refresh, and how fast

Four things:

- **CSI for served users $\mathbf{h}_k$.** Refresh per channel coherence interval. At FR2 outdoor, $T_c \sim 1$–$10$ ms. 3GPP pilot schedule. Nothing to design.
- **Body position $\mathbf{p}_u(t)$.** Refresh on the order of seconds for walking users. Translation updates the steering vector $\mathbf{a}^{(u)}(\mathbf{p}_u)$, which is an analytical $O(M)$ update. Cost is negligible.
- **Body pose $\boldsymbol{\theta}_u(t)$.** Changes on the order of 100 ms for walking pedestrians. The ACS $\sigma_u(\boldsymbol{\theta}_u)$ is the thing that updates. For the WB-SAR version, this is a small regression (scalar). For the APD version (per-patch), the worst-patch identity can change with pose, so you update a low-dim representation (SH expansion of local $\mathbf{Q}_{\text{loc}}(\mathbf{r}_0)$ as a function of $\boldsymbol{\theta}$).
- **Scene geometry (buildings).** Static. OSM + 3D tiles. Loaded once.

### Compute envelope

On your 4-CPU 8-GB machine you get 3 ms/body at 25K triangles with Part 1 physics. Scaling that up to 50 bodies × 25K triangles → 150 ms/frame per-frame pose-full-exposure recomputation. That is your pose-refresh budget, which is 100 ms-ish, so you're roughly at real-time with a pose-rate update. That's also on a CPU; on a GPU you are many times faster.

Per-slot updates are just:
- Steering vector update: $O(M)$ per body per slot → negligible.
- ACS update: 1 scalar per body per pose-rate slot → negligible.
- Precoder solve: ZF with $K + B$ constraints → $O((K+B)^2 M)$ per slot. At $K=25, B=25, M=64$, this is $\sim 10^5$ flops per slot, so sub-µs on a modern AP processor.

**Bottom line:** the DT-in-the-loop at plaza scale is *real-time-in-silico feasible*, not aspirational. This is a strong thing to show in the paper. No abstract proof needed — just do the experiment.

### What the reviewer actually wants to see

Not a theorem on cadence. A plot: "running AEGIS-DT-in-the-loop at 100 ms pose cadence, 1 ms slot cadence, 50 bodies, measured compliance achieved, measured sum-rate." This is exactly the "experiment wins ambition" move you suggested, and I think it's right.

### Real-time in silico — is it too wild?

Not at all. Sionna runs PHY at real-time-equivalent rates on a single GPU. AEGIS runs Part 1 physics at 150 ms/scene on a CPU, and much faster on a GPU. IMU simulation is sub-ms (it's literally a particle on a rigid body). The bottleneck is probably the pose-generation side — using AMASS mocap traces keeps this trivial. You could literally loop 5-minute real-time-synchronous simulation of 50 bodies walking, and record every slot's precoder, exposure, and throughput. That's a hero demo.

---

## 5. TDD, UL/DL, and non-user IMU — you're right

My framing ("the BS can't get anything from a non-user because they don't pilot") was wrong. Let me re-state.

In 5G NR TDD:
- Slots alternate UL/DL per some TDD pattern (typical 4:1 DL:UL for eMBB or 3:2 for URLLC).
- A UE in RRC_CONNECTED or RRC_IDLE state is *registered* with the network even if no app is sending/receiving. Measurement reports, tracking-area updates, and keepalives flow in UL.
- So a "cooperating non-user" — phone on, not using an app — can absolutely send periodic IMU to the BS via a standard MNO-app uplink. The cost is a few kbit/s of UL data over seconds.
- The *true* airplane-mode bystander — phone off or radio disabled — is the only case where no UL signal exists.

So the paper's user tiering should be:

| Tier | UL | DL | IMU available? | Example |
|---|---|---|---|---|
| A: Served user | CSI + app data | App data | Yes (if app/MNO consent) | Someone video-calling on the plaza |
| B: Cooperating non-user | CSI + IMU | None | Yes | Phone-in-pocket, no active app |
| C: Airplane-mode bystander | None | None | No | Tourist with airplane mode |
| D: No phone | None | None | No | Child on a parent's shoulder |

For the paper, all four tiers exist in a realistic plaza. A/B you cover with IMU telemetry. C/D you cover with ISAC + worst-case pose (Cauchy's $D \le 2$ is enough for WB-SAR even without pose estimation).

**AoA for non-users (your specific unsolved):** in the rank-1 far-field, you don't need AoA *at the non-user* — you need the BS-to-non-user direction (i.e., the BS departure angle toward the body position). That is computable from body position alone, which you get from (B) IMU+GPS, (C) ISAC position, or (D) passive vision. **No UE-side AoA algorithm is required.** Your worry "how tf are we gonna get AoA" dissolves when you realize that in the DL plaza regime, the only direction you need is the *BS-side* one, not the *body-side* one. That's the rank-1 simplification earning its keep.

---

## 6. Heartbeat Doppler for airplane-mode bystanders

Cool idea. Worth a half-page in the paper if the numbers work. Let me sketch.

**Physics.** Breathing at 0.2-0.5 Hz with thoracic displacement ~5-10 mm; heartbeat at 1-1.5 Hz with ~0.5 mm displacement. At 26 GHz ($\lambda = 1.15$ cm), these produce Doppler micro-phase modulations at Doppler frequencies $f_d = 2 v / \lambda$ where $v$ is the chest-wall velocity. Peak velocity from breathing is $\sim 2\pi \cdot 0.5 \cdot 5$ mm = 1.5 cm/s, giving $f_d \approx 2.6$ Hz. From heartbeat, $f_d \approx 0.5$ Hz. Both well within a 1-sec integration bandwidth.

**Detection budget.** Link budget for 26 GHz BS at 55 dBm EIRP, monostatic reflection from a human torso (RCS ~0 dBsm) at 50 m, one-way 400 MHz BW, 1-sec integration:

- Two-way path loss at 50 m, 26 GHz: $\sim 98$ dB (twice one-way FSPL plus body RCS).
- Reflected signal at BS: $55 - 98 = -43$ dBm ≈ 50 nW.
- Noise floor over 400 MHz at 290 K noise temp + 5 dB NF: $-174 + 86 + 5 = -83$ dBm.
- Raw SNR at antenna element: $-43 - (-83) = 40$ dB.
- Array gain from 8×8 (64 elements): 18 dB.
- Gross SNR: 58 dB.
- But we're detecting a *modulation* at sub-Hz rates on a CW-like return. The modulation index is $\Delta\phi = 4\pi \cdot \text{displacement} / \lambda$ → for 5 mm displacement, $\Delta\phi = 5.4$ rad → strong modulation; for 0.5 mm, $\Delta\phi = 0.55$ rad → weak but detectable. Processing gain from 1-sec FFT at 400 MHz BW is huge (~86 dB in a narrow Doppler bin).

**The answer:** respiration is detectable with margin at 50 m; heartbeat at 50 m is marginal but possible. **Per-body localization** (angular cell from which the modulation returns) is straightforward: standard micro-Doppler imaging gives you an angle-Doppler map, and the breathing signature flags occupied cells. Sufficient to say "there is a body at direction $\hat{\mathbf{k}}$ in this 5° cell." You do *not* recover pose.

**For the paper:** this is the ISAC prong. "Even for airplane-mode bystanders, the BS localizes them via respiration micro-Doppler at plaza range; pose is then bounded by the Cauchy $D \le 2$ worst case." Clean story. I'd draw the link budget in a sidebar figure. Cite: Adib+Katabi (MIT) "Multi-Person Localization via RF Body Reflections" 2014, Wang+Gupta (UCSD) "Vital-radio" 2016, anything from Harvard or Georgia Tech's mmWave vital-signs group (there's recent work at 24/28/77 GHz). The q_complement duality ($\mathbf{Q}_{\text{re}} \approx (1-T_0)/T_0 \cdot \mathbf{Q}$) is the rigorous hook that says *the same precoder optimization that minimizes exposure maximizes backscatter* — which is a bonus the paper delivers essentially for free.

This makes the paper's closed-loop more airtight: ISAC → position + presence → DT → $\mathbf{Q}^{(u)}$ (pose-worst-case) → ECBF → next beamforming interval. For airplane-mode bystanders, worst-case pose replaces pose estimation. **That closes the loop even for the D-tier.**

---

## 7. Experiment stack

Your instinct (100s of users walking, intermittent UL/DL, real-time in silico) is right. Here's my recommended stack.

**PHY layer (channel, precoder, SNR):** Sionna (NVIDIA). Best-in-class for MU-MIMO FR2 simulation, JAX/TF-based, GPU-accelerated. It already handles 3GPP-compliant OFDM numerology, realistic antenna arrays, Rayleigh/Rician/ray-traced channels. You can plug AEGIS-computed channels directly into Sionna's `Channel` interface.

**Higher-layer (MAC, scheduling, app traffic):** You have three choices, pick the simplest.

- **DON'T** use OpenAirInterface or srsRAN — these are real-time-SDR stacks designed for hardware-in-the-loop experiments. You'll lose weeks to build issues and gain nothing the paper needs.
- **MAYBE** use ns-3 5G-LENA module (or Simu5G on OMNeT++). They do MAC + scheduling + HARQ + BLER realistically. But integration with Sionna is fiddly.
- **YES, BEST:** use Sionna alone + a hand-rolled MAC. The "MAC" is just: "each served user has a Bernoulli traffic model, each slot the BS allocates all served users, per-slot SNR → MCS selection → BLER via 3GPP tables → throughput. End-of-hour throughput is the metric." Non-users do not get allocated (they're not served). IMU is simulated as "sample $\boldsymbol{\theta}(t)$ from AMASS, add Gaussian noise, predict with a small NN." 500 lines of Python. This is what every JSAC paper on the rate-vs-[constraint] Pareto does.

**Pose generation.** Use AMASS mocap traces. There are thousands of hours of real human motion captured on SMPL-X; download the walk-cycle subset (CMU-MOCAP-walk, AMASS subset). Translate across the plaza by prescribing trajectories (small NN that respects walking dynamics, or just straight lines with random orientations).

**IMU virtualization.** Given ground-truth $\boldsymbol{\theta}(t)$ from AMASS:
- Virtual accelerometer: $\mathbf{a}(t) = R_{\text{IMU}}^T(\ddot{\mathbf{p}}_{\text{IMU}} + g\hat{z})$ plus Gaussian noise ~0.01 m/s² + bias drift.
- Virtual gyroscope: $\boldsymbol{\omega}(t) = R_{\text{IMU}}^T \dot R_{\text{IMU}}$ plus noise.
- Virtual magnetometer: $\mathbf{B}_{\text{local}}(t)$ plus noise + bias.
- Small NN (MLP, maybe LSTM for smoothing) regresses back to $\boldsymbol{\theta}(t)$ from these.

Reviewers won't ask hard questions about this part if you cite the Madgwick-filter literature and a standard IMU noise model from the ICM-20948 or BMI160 datasheets (these are the actual sensors inside modern phones).

### The hero demo

Five minutes of wall-clock simulation, 50-body plaza, 26 GHz, 8×8 panel, 3-operator cumulative cap, per-slot ECBF, per-100-ms pose update, per-second translation. Plot: (a) per-body exposure cdf over the 5-min window, (b) served-user sum-rate vs. time, (c) one heatmap of "beam power incident on body u vs. time" showing the exposure shaping. You compare against (MRT, ZF-to-users-only, static-worst-case ECBF, ZF-dosimetry-oracle, ZF-dosimetry-with-pose-NN, the full thing).

That figure is the paper.

---

## 8. Why a differentiable pose twin helps — honest version

After Part 1 pushback, here's the smaller and more honest claim:

**Not for:** pose-robust WB-SAR compliance. Cauchy bounds give that to within 6.5% without differentiability.

**Yes for:**
1. **Closed-loop real-time ACS updates.** $\sigma(\boldsymbol{\theta}(t))$ is a smooth function; if you have $\dot{\boldsymbol{\theta}}(t)$ from IMU, a first-order update $\sigma(t+\Delta t) \approx \sigma(t) + (\partial_\theta \sigma) \cdot \dot\theta \cdot \Delta t$ is cheap. No need to re-ray-trace.
2. **Gradient-trained ACS predictor.** You have ground-truth $\sigma(\boldsymbol{\theta})$ from AEGIS. Train a small NN with both $\sigma$ targets and $\partial \sigma/\partial \theta$ targets (Sobolev training). Helps sample efficiency — not essential but defensible for a future-work claim about UE-side runtime.
3. **Per-patch APD worst-case tracking.** For the FR2-binding 4 cm² APD constraint, the worst patch *identity* changes with pose. A differentiable $\mathbf{Q}_{\text{loc}}(\mathbf{r}_0; \boldsymbol{\theta})$ lets you do projected gradient descent for $\arg\max_{\mathbf{r}_0} \mathbf{x}^H \mathbf{Q}_{\text{loc}}(\mathbf{r}_0; \boldsymbol{\theta}) \mathbf{x}$ jointly over $\mathbf{r}_0$ and $\boldsymbol{\theta}$, instead of enumerating patches.
4. **Positioning against Zhou.** Zhou has no pose at all (spherical head). The pose angle is your sole genuine novelty axis against them if you go head-to-head on "exposure-aware beamforming." You need some story here and "$\sigma(\boldsymbol{\theta})$ with IMU telemetry" is the minimum-viable one.

**What I would actually put in the paper.** A half-page subsection "Pose-aware exposure: a scalar predictor." One paragraph of math (define $\sigma(\boldsymbol{\theta})$, say it's differentiable in $\boldsymbol{\theta}$ because SMPL-X is and the Gram integral is smooth in geometry). One paragraph of NN architecture (MLP, trained on 10k AMASS-sampled poses, RMSE vs. ground truth). One figure.

Everything else about pose-differentiable $\mathbf{Q}$ lives in the supplementary or in a follow-up paper on the coherent near-field regime.

---

## 9. Brussels framing, your way (I was too harsh)

Re-reading your reply I think you have a real point that I dismissed. Let me re-state what you said so you can correct me:

- AEGIS shows DL is always compliant at ICNIRP reference levels for normal EIRPs. **So in a paper that opens with "we need to be exposure-aware in DL," reviewers will gut-reject the premise.** The fix isn't to hide the fact; it's to surface it and explain what regime actually binds.
- Brussels/Milan/etc. *reference levels* (in V/m) are 10-30× tighter than ICNIRP and are not averaged over 30 min — they are "every second, at every public point." This is harder on the operator than ICNIRP. **And this does bind**, per your 8×8 back-of-envelope (§9.3 in `exposure_null_precoding.tex`).
- Some jurisdictions use *basic restrictions* (direct SAR/APD limits) rather than reference levels. Those are harder to compute but more physically meaningful. ICNIRP reference levels are conservative surrogates for their basic restrictions; city reference levels are just politically tighter. Paper should distinguish.
- More broadly: the paper's pitch to Qualcomm and the standards world is *regulation is the primary deployment blocker for mmWave internationally, not pathloss*. That's the deployable hook. "Ban in Brussels 2019, Geneva moratorium 2019, 600+ Italian resolutions, Milan 2024" — you have a real list.
- ZF-dosimetry against *bystanders* is the product move, and the long-term 24/7 DL-low-level-high-duty vs UL-high-level-low-duty argument is the general EMF concern that motivates GOLIAT and all the EU-funded EMF work. This is not mathematical, it's epidemiological: exposure = dose × time, and DL is the 24/7 term.

**Revised paper framing on Brussels:**

- Open paragraph: "Mobile operators have had mmWave spectrum auctioned or available in most G20 countries since 2020, yet deployment outside the US and parts of East Asia has been slow — not because of RF pathloss but because of regulatory EMF resistance. Brussels banned 5G in 2019 and raised its cap for 5G only in 2024; Geneva had a moratorium; Milan and 600+ Italian municipalities have active resolutions; France banned children's smartphone-to-head use; Italy has a 6 V/m national cap. The quantitative instrument behind all of this is the public-space EMF reference level. This paper asks: can the mmWave radio network, via a digital-twin control loop, deliver competitive capacity while satisfying these reference levels continuously?"
- Mid-paper: "We work at the ZF-dosimetry extension of classical ZF precoding: the BS nulls energy to both served-user-interfered-channels and to bystander directions. The 'bystander null' uses a body-centric compliance framework — compliance on bodies that exist, not on every free-space point. For bodies we know (tiers A/B via IMU), we use an actual pose-conditioned ACS; for bodies we detect without telemetry (tiers C/D via ISAC), we use a pose-agnostic worst-case bound (from Cauchy's $D \le 2$)."
- Closing paragraph: "The resulting system satisfies Brussels-strength instantaneous reference-level compliance while delivering [X dB] sum-rate over a naive power-back-off baseline. The rhetorical position this paper takes is that a digital-twin network is not just a research object; it is the missing engineering layer between mmWave capacity and regulator-accepted deployment."

This is the Brussels story done your way. I'll patch the main doc.

---

## 10. Papers I'd want (if fetching is cheap)

These are either things I want to cite with confidence, or things I want to pull a specific equation from:

- **Chiaramello et al. 2021** (*Applied Sciences* 11(4):1751) — stochastic dosimetry with 3D beamforming. I want their posture-sampling protocol and their Monte Carlo integration counts, to compare against AEGIS's SH approach.
- **GOLIAT project reports** — what's the official EU-funded EMF-in-5G benchmark story? The paper's "long-term DL dose" motivation benefits from citing it.
- **Qualcomm X75 modem whitepaper** — there's a "sensor-modem-RF solution for mmWave beam management" claim in the prod brief; I want to see the actual technical content around IMU-in-modem for beam management. This is the deployment hook for the paper's "IMU → pose → ACS" channel.
- **Wang & Gupta (UCSD) "Vital-Radio" 2016** (UbiComp), **Mercuri et al. 2019** (*Nat Electron*), **Adib & Katabi (MIT) 2013** (SIGCOMM) — for the heartbeat-Doppler prong. I want to confirm the link-budget numbers I sketched in §6 match published.
- **Bruxelles Environnement 2024 ordinance text** — exact wording of the 14.57 V/m cap. I want to confirm it's *instantaneous*, not 30-min-averaged. I think you said it is; a citation locks it.
- **Zhou 2026 full PDF** (you have `2601.19587v1.pdf` in `JSAC/`). I read the tex transcription; if there's a figure or numerical comparison I'm missing that matters for differentiation, flag it.

Worth you fetching these if you can. Not critical, not urgent.

---

## 11. One last thing I didn't answer before

You asked "what are we putting on what timescales" and I realize I only partially answered in §4 above. Let me consolidate into a single table the paper could lift wholesale:

| Quantity | What it depends on | Who supplies it | Cadence | Cost per update |
|---|---|---|---|---|
| $\mathbf{h}_k(t)$ | BS↔UE $k$ channel | 3GPP pilot | slot (ms) | O(M), free |
| $\mathbf{a}^{(u)}(\mathbf{p}_u)$ | BS→body $u$ steering | ray tracer + $\mathbf{p}_u$ | seconds | O(M) per body |
| $\sigma_u(\boldsymbol{\theta}_u)$ | body $u$ pose-conditioned ACS | NN from IMU (A/B) or worst-case (C/D) | 100 ms | O(1) per body |
| $\mathbf{p}_u(t)$ | body position | IMU+GPS (A/B), ISAC (C/D) | 0.1–1 s | O(1) per body |
| $\boldsymbol{\theta}_u(t)$ | body pose | IMU → NN (A/B), worst-case (C/D) | 100 ms | O(1) per body |
| Scene 3D | building geometry | OSM + 3D Tiles | static | once |
| Precoder $\mathbf{W}(t)$ | all of above | ZF-dosimetry solve | slot (ms) | O((K+B)² M) |

The reviewer reads this and thinks "OK, I know what to ask for." That's the paper's DT-architecture figure in table form.

---

*That's the round-2 reply. The backup of the first brainstorm is at `brainstorm_opus_response_backup.md`. The updated main doc is next — I'll rewrite the "paper I would write" section, simplify the skeleton-embedding claim, and restore the Brussels framing properly.*
