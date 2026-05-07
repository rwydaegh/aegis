# Direction 5 — ambitious ideas, expanded

Date: 2026-04-23. This document expands four candidate directions for the JSAC Route B PoC after reading the Qualcomm 2024 whitepaper "Millimeter wave antenna module placement: A quantitative framework for Smartphones" and the QTM547 product brief.

---

## Honest re-read of the Qualcomm whitepaper

Before the ideas, a correction: my earlier pitch overstated what the whitepaper actually gives us. Here is the clean ledger.

### What the whitepaper DOES give us

- **Module geometry (§2.1, Fig. 2-1):** 1×5 dual-polarized linear array, or 2×5 dual-polarized planar array. λ/2 spacing (5.36 mm at 28 GHz). So 10 or 20 ports per module.
- **Beam codebook (§5.1, p. 18):** explicit statement of a **size-9 analog beamforming codebook** per module, designed to steer energy toward boresight ±45°. So one module = 9 beams, each covering ~10° of its ~90° scan cone.
- **Phone-chassis model (§3.1, Fig. 3-3):** 18 candidate surface regions (3 each on top/bottom short edges, 3 each on left/right long edges, 6 on the back face). This is a discrete placement space, not 18 patterns.
- **16 hand-grip use-cases (§3.2 + Appendix A):** 5 portrait + 8 landscape + 3 miscellaneous grips, each described by **which of the 18 surface regions are blocked** (boolean list), plus a probability mass function in Table 3-2 for how likely each grip is in portrait-heavy, landscape-heavy, and equal-weight usage modes.
- **Orientation prior (§3.3):** θ_orientation ≈ 30° + Uniform(-15°, 15°) for the plane-of-phone tilt from horizontal.
- **Angular prior on dominant MPCs (§3.5, Fig. 3-5):** in a downtown San Francisco outdoor deployment, azimuth uniform over [0°, 360°], zenith concentrated in [85°, 130°] (roughly horizontal with slight downward tilt because BS is typically rooftop).
- **Empirical blockage loss (§4, Fig. 4-1):** 90th/80th/50th/20th percentile hand-blockage EIRP losses of 8.6 / 10.6 / 12.2 / 17.2 dB.
- **EIRP targets (Table 5-1):** for n261 a representative operator demands 27.5 / 21.0 / 14.5 dBm at 100th / 50th / 20th percentile.
- **ONE illustrative antenna pattern with/without blockage (Fig. 2-4b, 2-4c):** a single measured pattern in an anechoic chamber with a hand phantom covering one module. This is one example, not a library.
- **References:**
  - [7] Raghavan et al., "Hand and body blockage measurements with form-factor user equipment at 28 GHz," *IEEE T-AP* 70(1):607–620, Jan. 2022 — the actual measurement paper backing the whitepaper. This is where the 16-grip measurement data would live, if public.
  - [2] Raghavan et al., "Antenna placement and performance tradeoffs with hand blockage in mmWave systems," *IEEE T-Comm* 67(4):3082–3096, Apr. 2019.
  - [3] Raghavan et al., "Spatio-temporal impact of hand and body blockage for mmWave UE design at 28 GHz," *IEEE CommMag* 56(12):46–52, Dec. 2018.

### What the whitepaper does NOT give us

- **Not 16 antenna patterns.** The paper describes a framework that takes 16 patterns as input and uses them to compute weighted EIRP. Patterns themselves come from anechoic chamber measurements (like Fig. 2-4) or EM simulation with a hand phantom. They are not tabulated in the PDF.
- **Not the beam-codebook steering vectors.** Just the size (9) and the scan range (±45° from boresight). The actual complex weights are implementation-specific.
- **Not per-element measurements or IQ.** The paper confirms the analog-beamforming architecture but does not publish any per-element data.
- **Not phone-specific measurements for iPhone / Galaxy / Pixel.** Qualcomm's analysis is of a generic 2-module handset.

### What we would need to procure or simulate to close the gap

1. **Per-grip antenna gain patterns.** Options, in order of ambition:
   - Simulate: build a CAD phone model + hand phantom (CST, HFSS, FEKO, or open-source openEMS) and run the 16 grip configurations. Export complex gain patterns on a θ,φ grid.
   - Extract from Raghavan T-AP 2022 figures: the paper has published measured beam patterns for **five concrete grip/subarray combinations** (Figs. 3a, 4a, 7a, 8a–c — a 4×1 patch under hard hand grip, loose grip, a 2×1 dipole under hard grip, a 2×1 dipole under loose grip, a 4×1 patch under intermediate landscape grip). These can be digitized to give us 5 ground-truth patterns covering the hard / loose / intermediate grip categories. Combined with the whitepaper's 16-grip blocked-region list, we can bucket the 16 grips into the 5 measurement classes and use the corresponding measured pattern — procuring 5 patterns instead of 16 and covering the full space to a reasonable approximation.
   - Assume parametric: use one of the measured "blocked" patterns as a template and deform it according to each grip's blocked-region list (amplitude/phase scale per blocked region).
   - Collect: Robin has IMEC connections — possibly request measured patterns from an industry partner under NDA. Slowest path; highest fidelity.
2. **A concrete beam codebook.** The Qualcomm whitepaper describes a size-9 codebook per module. Raghavan T-Comm 2019 uses 8–12 beams per module (12 for face design = 4 per 2×2 patch subarray + 2 per dipole subarray; 12 for edge design = 4 beams per polarization of 4×1 patch × 2 polarizations; 24–48 in the maximalist Designs 3/4). Raghavan T-AP 2022 uses a minimal 3-beam codebook per subarray (boresight, +30°, −30° for 4×1 patch; ±45° for 2×1 dipole) for explicit measurement study. **For the PoC, adopt a 3-beam codebook per subarray × 3 subarrays per module × 3 modules ≈ 27 beams total across the UE** — consistent with Raghavan's measurement setup, easy to defend. Use 5-bit phase shifters (T-Comm 2019) for the quantization.
3. **Per-polarization port patterns C_R^(1), C_R^(2).** These are the "two linearly independent port patterns" in Prop. 5.1. Raghavan T-AP 2022 §II.A + T-Comm 2019 §III.B confirm the UE has exactly **2 RF chains per module, each excited by one orthogonal polarization**. The two port patterns are therefore the H and V polarization radiation patterns of the active subarray, steered by the same analog beamformer. Dual-slant ±45° is the typical 3GPP convention. Concrete port patterns come bundled with the measured patterns from point 1.

OK, with that cleaned up, here are the four ambitious ideas in detail.

---

## Updates from the Raghavan paper set (2018–2022)

Robin supplied three Qualcomm papers after the initial brainstorm. They are the primary sources behind the 2024 whitepaper and meaningfully sharpen the picture. Key facts and how they affect the ideas below.

### Hard facts now nailed down

- **2 RF chains at the UE, one per polarization.** Confirmed explicitly in Raghavan T-AP 2022 §II.A ("the UE considered in this work has two RF chains, which are used for polarization-based transmissions") and T-Comm 2019 §III.B ("the base-station and all the UE designs considered in this work are powered by two RF chains, where each RF chain is excited by one (orthogonal) polarization"). This is the structural reason per-element IQ cannot reach baseband — there is no hardware path for it. It also fixes the two "port patterns" C_R^(1), C_R^(2) in Route B's Prop. 5.1 as the two polarization patterns, not a pair of independent digital beamforms.
- **3 modules is the canonical commercial edge design.** T-AP 2022 uses a 3-module prototype (two long edges + top short edge). T-Comm 2019 compares 2-module face vs. 3-module edge and concludes the edge design wins on implementation ease, exposure, and spherical coverage, at comparable beamforming performance. Whitepaper's 2-module analysis was a minimum-case simplification.
- **Per-module subarray count is richer than whitepaper let on.** T-AP 2022 prototype has per module: a **4×1 dual-pol patch subarray + two 2×1 dipole subarrays**, each with dual polarization, routed through 2 RF chains. Total antenna-element count per module is 4 patches + 4 dipoles = 8 radiating elements × 2 pol = 16 port counts, but only 2 RF chains through analog combining.
- **Actual codebook sizes measured:** 3 beams per 4×1 patch subarray (boresight, ±30°) for the detailed blockage study (T-AP 2022); 12 beams per module in the full commercial design study (T-Comm 2019 Table I face and edge designs).
- **Blockage loss statistics with Gaussian fits** (T-AP 2022 Table VII and CommMag 2018 Fig. 2b):
  - Hard hand grip, full envelopment: mean 15.3 dB, std 3.8 dB. 20th/50th/90th percentile ≈ 11 / 16 / 18 dB.
  - Loose hand grip: mean 3.6–5.3 dB, std 4.6–4.7 dB. Much lower.
  - Intermediate landscape grip: mean ≈ 15.9 dB.
  - Body blockage (pedestrians walking nearby): mean 8.5 dB, std 2.5 dB.
- **Link degradation timescales (CommMag 2018 §Temporal Impact, Fig. 4):** median time for RSSI to fall from steady state to minimum is **240 ms for hand blockage, 200–480 ms for body blockage, worst case > 120 ms**. This number matters a lot — see Idea #2 update below.
- **Beam scanning periodicity in the prototype: 40 ms** for a full 20-beam UE sweep (5 beams × 4 subarrays) — so ~5–10 complete UE beam sweeps fit inside one blockage coherence window.

### The reflection-gain finding (important for Q estimation)

Across all three papers, the authors repeatedly emphasize something we glossed over: **the hand does not just attenuate signal — it reflects it.** Parts of the sphere that had weak freespace gain can gain 15–25 dB when a hand is present, because fingers and palm reflect energy into previously weak directions (T-AP 2022 Figs. 5c, 6 and the R_2 region-of-interest definition). This is why the naive "gain × blockage mask" model for the hand understates what is actually happening at the antenna.

**Implications for Q estimation:**

- The antenna pattern under a grip is not a subset of the freespace pattern; it is a *redistribution*. Q_grip ≠ Q_freespace × mask; the full pattern must be used.
- Reflection gains mean that "blocked" does not mean "no energy delivered to the body"; it means energy goes somewhere different. For exposure calculations this could worsen or improve the absorbed-power distribution depending on geometry. Must be modelled correctly.
- It is further motivation for Idea #3: grip-aware Q is not a minor correction; it is essential whenever grip uncertainty exceeds ~30° of pattern structure.

### Concrete blockage models the paper can cite

Raghavan proposes a simple replacement for 3GPP TR38.901's flat 30 dB blocked-region loss: **Model 2 — lognormal loss N(15.26 dB, 3.8 dB) over the same 3GPP-defined blockage region** (T-Comm 2019 Table II). This is a citable, calibrated, operator-grade blockage model we should adopt directly rather than the 3GPP pessimistic one. Paper rationale: "TR38.901 overestimates; our commercial-hardware measurements give these numbers."

### What this does to each idea

- **Idea #2 (motion synthetic aperture):** MUCH stronger than I thought. Coherence window is 120–480 ms (measured at 28 GHz on real hardware), not the ~100 ms conservative estimate I used. A full UE beam sweep is 40 ms. That gives 3–12 independent "beam-sweep snapshots" inside one coherence window, with the module moving several centimeters between them. Native SAR-style processing is clearly feasible. See Idea #2 update below.
- **Idea #3 (grip-aware Q):** more tractable than I thought. Paper 1 publishes 5 measured patterns spanning the hard/loose/intermediate grip space. Combined with the whitepaper's 16-grip blocked-region list, we can bucket the 16 whitepaper grips into 5 measured-pattern classes and use the measured patterns directly, instead of EM-simulating 16 patterns from scratch. This cuts the procurement problem by ~3x.
- **Idea #4 (reciprocity split):** the "2 RF chains per polarization" confirmation makes the architecture cleaner. The UE's dual-pol SRS literally IS the two-port sounding that Prop. 5.1 needs, just moved onto the uplink. Its identifiability proof carries over without caveat.
- **Idea #5 (crowdsourced):** no direct update; still "future work" in scope.

---

## Idea #2: Motion synthetic aperture — plain-English version

### The intuition

You never hold your phone perfectly still. Your hand drifts, rotates, trembles. Over half a second it moves a few centimeters and a few degrees. This is usually an annoyance — we design phone sensors to *ignore* it. What if we *used* it?

At 28 GHz the wavelength is about 1 cm. A casual half-second of natural hand motion covers several wavelengths of linear travel. That turns out to be the magic ingredient.

### Why motion matters — the radar analogy

Imagine you are standing in one spot and someone shines a flashlight at you from across the room, but through a doorway so you cannot see the source directly. You can tell there is light but not exactly where it is coming from.

Now take one step sideways. The light changes subtly — intensity and angle shift. Take another step. Over ten steps, you trace an arc. From that arc of observations you can triangulate the source quite well.

That is exactly how **synthetic aperture radar (SAR)** works on aircraft. A plane flies over the ground carrying a modest antenna. At every moment its single antenna records a snapshot of the ground's reflection. Over a flight line several kilometers long, those snapshots combine mathematically into an image as if a kilometers-wide antenna had been there all along. No actual kilometers-wide antenna exists — it is *synthesized* from motion + knowledge of where the antenna was at each moment.

### Why this works for a smartphone

A phone's mmWave module is about 2 cm wide physically — its inherent angular resolution is set by that aperture and gives you a roughly 25° beamwidth. That is what the phone "sees" at one instant.

Over 300 ms of natural hand motion, the module moves maybe 5–10 cm — more importantly, it rotates a few degrees. That trajectory, tracked by the phone's IMU (gyroscope + accelerometer), is a 3D path of the module through space. If we record a channel snapshot every ~1–5 ms during that 300 ms window, we get maybe 60–300 snapshots taken at known positions and orientations.

Coherently combining those snapshots — weighting each by the known position and orientation — is equivalent to having a much bigger antenna array. The effective aperture is no longer 2 cm but the extent of the motion trajectory (5–10 cm). Angular resolution improves by the ratio — roughly 3–5× better than the single-instant hardware gives.

### Why it genuinely works (the less-jargon version of the physics)

Four things must be true for this to hold:

1. **The environment must be stationary** over the sensing window. Walls do not move in 300 ms. A person walking through the room would break this. For a seated / standing user with a fixed physical environment, this is fine.
2. **The radio signal from the BS must stay phase-coherent** over the window. Raghavan et al. CommMag 2018 measured this directly on the Qualcomm 28 GHz 5G-NR prototype: median link-degradation time is 240 ms for hand blockage and 200–480 ms for body blockage, with worst-case above 120 ms (their Fig. 4). So the window we need (100–300 ms) sits comfortably below the measured degradation timescale. This is now a hard empirical data point, not a hand-wave.
3. **We must know where the module was** at each snapshot, to sub-wavelength precision. At 28 GHz a wavelength is 10.7 mm, so we need position known to ≈ 1 mm and orientation to ≈ 0.5°. Modern smartphone IMUs (e.g., Bosch BMI270, Apple U1/U2) achieve sub-mm position drift and sub-degree orientation over hundreds of ms when integrated carefully. Tighter than needed.
4. **The BS must cycle reference signals** frequently enough to give us many snapshots in the window. The Raghavan prototype does a full UE-side 20-beam sweep in 40 ms (CommMag 2018) — so within one 240-ms coherence window we get ~6 full UE beam sweeps at different module positions. In 5G NR FR2 with CSI-RS / SRS configured per slot (125 µs at 120 kHz SCS), an even finer temporal grid is available (~2000 observations in 240 ms).

### What the UE does

Conceptually: while holding still-ish, the phone keeps IMU running and logs a fast sequence of mmWave pilot measurements. It notes the IMU-derived position and orientation of each module at each moment. Then a SAGE-like or OMP-like estimator on the main baseband combines all snapshots, accounting for the known motion, to produce a fine-grained AoA estimate for each dominant path.

### What the paper gets out of it

Three numbered contributions for the JSAC paper:

- Show that the **effective angular resolution** of a smartphone's mmWave frontend under natural hand motion is 3–5× the static-hardware limit.
- Show that this brings Route B's identifiability proof into the operational regime on commercial hardware **without any standards change**.
- Quantify how the improved AoA feeds through the AEGIS exposure operator Q into **tighter SAR_wb and APD_4cm² closed-loop control**, vs. a static-UE baseline.

### Risks and caveats

- Claim #1 depends on wrist-motion statistics that are not trivially available. There is HCI literature on natural tremor (Parkinson's tremor analog papers, for instance) and on casual hand drift (AR/VR pose papers), but we would need to justify a motion distribution explicitly.
- If the user actually is very still (on a table, in a car cradle), synthetic aperture gains collapse. Honest reporting requires per-posture breakdown.
- Pilots in real networks are not always dense enough; we may need to assume a modest standards tweak (e.g., "UE-requested SRS densification during Q-refresh window").

### PoC footprint

- Sionna canyon scene with a UE at a fixed location, simulated hand-motion trajectory as a small jitter around that location (generated from a parametric wrist-motion model with amplitude ≈ 3–10 mm rms and a ≈ 1–3 Hz bandwidth).
- Generate per-snapshot channel impulse responses from Sionna (this is the core compute cost).
- Run a static-UE baseline estimator and a motion-aware SAGE estimator on the same data.
- Compare AoA RMSE and downstream Q / SAR / APD accuracy.
- Benchmark directly against Raghavan's measured 240-ms link-degradation-time window — if we stay under 200 ms integration we are operationally safe; if we push to 480 ms we are at the body-blockage coherence limit and can quantify degradation.

---

## Idea #3: Grip-aware Bayesian Q estimation (corrected)

### Marginalization in plain language

The UE does not know with certainty which grip the user is currently using. It has noisy evidence: capacitive touch pattern on the screen edges, accelerometer (phone orientation), maybe microphone (voice call vs. video), maybe proximity sensor (face near screen). From this evidence the UE can form a probability distribution over the 16 possible grips — for instance, "70% Portrait use-case 2, 20% Portrait use-case 5, 10% other."

That distribution is the **grip posterior** — the posterior probability over grips given the evidence.

**Marginalizing** just means: instead of picking the single most likely grip and computing Q for it, compute Q for every plausible grip, then average weighted by how likely each grip is. Written out:

Q_marginal = Σ_i p(grip_i | evidence) · Q(grip_i)

If the UE is very sure of the grip, most of the probability mass is on one grip and Q_marginal collapses to that grip's Q. If the UE is uncertain between two, Q_marginal is a weighted average. If the UE has no evidence, p reverts to the prior from Qualcomm's Table 3-2 (18%/6%/25%/etc.) and Q_marginal averages over all 16 with those priors.

This matters because: the antenna pattern — and therefore the mapping from precoder x to absorbed power Sab — changes under each grip. A grip that covers one module with the hand blocks that module's beams; a grip that leaves a module free preserves them. Q depends on which elements are radiating how, so Q depends on grip.

If we pick the wrong grip for Q computation, the precoder x* we compute from Q will not actually satisfy the exposure constraint on the *real* channel. Marginalizing is the Bayesian way to hedge against grip uncertainty.

### What the Qualcomm paper actually provides for this

- The **structure** of the posterior: 16 discrete grips + prior probabilities for each (Whitepaper Table 3-2).
- The **blocked-region list** for each grip (Whitepaper Appendix A): which of the 18 phone-surface partitions are covered by the hand.
- An **example pattern** of blocked vs. unblocked single-element gain (Whitepaper Fig. 2-4b, 2-4c).
- A **mathematical framework** (Whitepaper §3.6, p. 14) for averaging array gain over grip states:
  G_eff(θ,φ) = Σ_i p_i · [I_i^11 G_unb,unb + I_i^10 G_unb,b + I_i^01 G_b,unb + I_i^00 G_b,b]
  where I_i^{ab} are grip-dependent indicator variables for which module is blocked.

This framework is exactly the structure we need; it marginalizes G over grip states, weighted by grip probability and module-blockage indicators. We would lift the same structure from G (a 2D array gain) to Q (an M_ant × M_ant exposure operator) — the math carries through.

### What the Raghavan T-AP 2022 paper adds

- **5 concrete measured patterns** (Figs. 3a, 4a, 7a, 8a–c) covering the hard / loose / intermediate × patch / dipole × portrait / landscape grip space. These are digitizable from the published color scans.
- **Explicit blockage-loss statistics** per grip class (Table VII): mean / median / std / sphere-coverage for each of 5 studies.
- **R_1 and R_2 region-of-interest definitions** — R_1 is the naive "bright region of freespace pattern"; R_2 augments with regions where the hand-induced reflection lights up the pattern. This matters for Q: ignoring R_2 underestimates absorbed power in reflection-gain directions.
- Lognormal blockage-loss model N(15.26, 3.8) dB (T-Comm 2019 Model 2) as a concrete replacement for the 3GPP flat 30 dB.

### What Qualcomm does NOT give us

- The full 16 antenna patterns themselves — we get 5 measured + a framework to extrapolate.
- Specific C_R^(1), C_R^(2) port patterns at polarization granularity — but the 2-RF-chain confirmation tells us these are just the H and V polarizations of the measured pattern.
- Specific beam codebook steering vectors — but the T-AP 2022 3-beam codebook (boresight, ±30°) per subarray is a defensible reference.

Procurement effort has dropped meaningfully: from "simulate 16 patterns from scratch" to "digitize 5 published patterns + extrapolate by grip class."

### The JSAC connection (CVaR-ECBF from answer.md)

The JSAC paper sketch in `/home/user/aegis/JSAC/answer.md` proposes a CVaR-risk extension of the Hochwald-style exposure-constrained beamformer:

maximize log|I + (1/σ²)H F F^H H^H|
s.t. CVaR_α[tr(R(θ) F F^H)] ≤ Q_0

CVaR interpolates between worst-case (α → 0, Hochwald) and expected-value (α → 1) over a latent state θ (the gesture / pose). The 16-grip posterior from the Qualcomm whitepaper is **literally** a sensible concrete parameterization of θ for the CVaR-ECBF. The paper pipeline becomes:

1. UE collects touch + IMU + (optional) proximity-sensor evidence e.
2. UE / BS computes the grip posterior p(grip_i | e) (a 16-vector). The posterior comes from a small discriminative model trained on labeled grip data.
3. UE / BS computes per-grip Q_i (either at runtime via AEGIS or pre-computed on the server side and cached).
4. CVaR-robust precoder solves the constrained maximization with R(θ) = Q_i drawn from the posterior.
5. Closed-loop: UE reports SAR/APD compliance; BS adjusts.

### Scope estimate

- Moderate engineering weight. EM-simulating the 16 grips is the slow part (order of days on a workstation per grip for a detailed hand+phone FDTD simulation). Could be bootstrapped with a simplified analytic blockage model (amplitude attenuation + phase distortion per blocked region) for a first PoC.
- The AEGIS integration is lightweight: grip becomes a new axis in Q caching, posterior becomes a config param.
- Paper contribution is narrow (makes CVaR-ECBF concrete) but lifts the JSAC paper's rigor.

---

## Idea #4: Reciprocity split — BS-side Q via uplink SRS, UE-side only for pose

This idea needs more air time because the user rightly flagged it as the most interesting one. Expanding.

### TDD reciprocity in one paragraph

5G NR FR2 (28 GHz) is **time-division duplex (TDD)**: uplink and downlink share the same frequency, different time slots. Because they are on the same frequency, the *physical propagation channel* is identical in both directions — this is called **channel reciprocity**. If the phone transmits a reference signal (SRS = Sounding Reference Signal), what reaches the base station antennas is the same physics that governs what reaches the phone when the base station transmits. The numerical channel vectors may differ by a calibration factor if the hardware RF chains are not identical, but the geometry, the path set, the scatterer configuration are shared.

### What each side actually sees — the key asymmetry

The big picture is: **per-element access is cheap at the base station and expensive at the phone.**

- **BS side:** 64–256 antennas, each with its own RF chain, each digitized separately. The BS can therefore capture the full per-element complex baseband. Classical super-resolution AoA/AoD algorithms (MUSIC, ESPRIT, tensor methods) work directly on this data.
- **UE side:** 2 modules of 10 ports each, analog-combined in the RFIC into one IQ pair per polarization per active module. Per-element access is locked inside the RFIC. Only the post-beam scalar gets to baseband.

Now when the UE transmits an SRS through one of its beams:
- The UE's transmit beamforming applies a complex weight vector w_UE = codebook[b] to its 10 physical elements.
- The signal radiates with an effective pattern w_UE^H · A_UE(k̂) where A_UE is the UE's per-element steering vector function at direction k̂.
- The path set (multipath from scatterers) carries the signal to the BS, with each path having (delay τ_n, UE-side departure direction k̂_UE,n, BS-side arrival direction k̂_BS,n, complex gain α_n, polarization state).
- At each BS antenna m the received sample is y_BS,m = Σ_n α_n · (w_UE^H A_UE(k̂_UE,n)) · (w_BS,m^H A_BS(k̂_BS,n)) · e^{-i 2π τ_n f} · s(t)

### Joint AoA/AoD estimation — what can be recovered

With the BS capturing per-element samples over a block of SRS transmissions and **over multiple UE beam indices b**, the BS has:

- Access to the per-element output on its 64–256 antennas → can extract AoD from the BS (which is AoA from the UE's perspective via reciprocity).
- Access to the per-beam output of the UE across the 9-beam codebook (the UE cycles through beams over successive SRS slots — this is standard "SRS beam sweep" behavior specified in Rel-17 and deployed in some operators today).
- Access to both polarizations of the UE (standard dual-pol SRS resources).

So the BS collects a three-dimensional tensor: (BS-antenna-index, UE-beam-index, UE-polarization-index) per SRS slot. With the BS's 64 antennas, 9 UE beams, and 2 UE polarizations, that is a 64 × 9 × 2 = 1152-element complex measurement vector per slot. With a few tens of slots in an SRS burst, thousands of effective measurements.

Path parameters to estimate: for each of 3–5 dominant paths, (k̂_BS,n, k̂_UE,n, τ_n, α_n, polarization_n) — on the order of 30–50 unknowns total. 1000+ measurements, 50 unknowns → extremely over-determined.

**Crucially, k̂_UE,n is recovered directly here.** The UE beam sweep injects known angular filters (the 9 codebook beams); the BS observes different linear combinations of the paths under each filter; inverting the codebook gives k̂_UE. The per-element-IQ requirement of classical methods is traded away for a beam sweep + per-element-at-BS requirement, which is easily available.

### How Route B's identifiability proof survives

Prop. 5.1 needed two linearly independent port patterns at the UE to invert ψ_n in the plane ⊥ k̂_UE. The UE has two port patterns: the dual polarizations. In the reciprocity-split architecture, those polarizations are *imprinted into the uplink signal via the UE's dual-pol SRS resources*. The BS observes them as structured phase/amplitude differences across SRS slots. The identifiability-inducing 2×2 linear system of Prop. 5.1 now lives in the BS-side joint estimator. The math is the same; the hardware locus has moved.

**The 2-RF-chain confirmation from Raghavan T-AP 2022 §II.A and T-Comm 2019 §III.B strengthens this materially.** Each RF chain is "excited by one orthogonal polarization" (T-Comm 2019). This is not a design choice we assumed — it is Qualcomm's documented commercial architecture. Therefore the dual-pol SRS is not just a plausible mapping to the Prop. 5.1 port patterns; it is precisely what exists on shipping hardware. No new hardware assumption is needed in the paper for the identifiability proof to translate.

### Protocol cost — what the new signaling has to carry

This is where it gets beautifully cheap:

- The UE's beam codebook is already known to the BS in principle (standardized, or at least vendor-reported at registration).
- The UE's dual-pol SRS is standard.
- The UE does not have to expose per-element anything.
- The UE does need to report **pose / grip state** periodically (kilobytes per second, over existing RRC signaling).
- The body geometry is the reusable AEGIS body model, pre-shared with the BS via a session-setup "exposure profile" exchange (kilobytes, once).

No major new signaling. Rel-17/18 already specifies most of the beam-sweep and dual-pol SRS. The novel bits are (a) pose/grip reporting and (b) BS-side Q inversion using AEGIS.

### Who computes Q — the architectural theorem

Here is the crisp JSAC framing. Define a **DTN split**: a mapping from (path-data, body-geometry, precoder) to (SAR_wb, APD_4cm², precoder_out) that is distributed across BS and UE.

Five natural splits:

| Split | UE role | BS role | Load on UE | Load on BS | Accuracy |
|---|---|---|---|---|---|
| **A. UE-centric Route B (original)** | Estimate k̂_n, ψ_n from per-element IQ; compute Q | Receive Q | Very high (impossible on current HW) | Low | Ideal |
| **B. Pure BS Route A** | Nothing | RT everything + pose | Zero | Very high (RT stale fast) | Stale |
| **C. Reciprocity split (this idea)** | SRS beam sweep + pose reporting | Joint AoA/AoD from UL SRS + body-model Q inversion | Low (SRS is cheap) | Moderate (64-ant 2D MUSIC + AEGIS Q) | Fresh, accurate |
| **D. Crowdsourced (Idea #5)** | Pose + beam-report aggregation | Multi-UE scene-reconstruction + per-UE Q | Medium | High but amortized | Highest for dense UE sets |
| **E. Full UE autonomy (Idea #2)** | Motion-SAR AoA + Q estimation locally | Nothing | Medium | Zero | Medium (motion-dependent) |

The paper's core theoretical contribution for Idea #4 becomes: **prove that split C achieves the same Route B identifiability as split A, with an error bound depending only on SRS length, beam codebook angular support, and BS per-element noise.** Then PoC the error bound against ground-truth Sionna RT.

### Why this is strong for JSAC DTN

- It is fundamentally a **distributed computation / architecture** contribution, which JSAC's DT/DTN special issue wants more than it wants signal-processing incrementalism.
- It sidesteps the paper-breaking hardware obstacle (per-element UE IQ) by moving the computation to where the data actually is.
- It keeps the UE's role minimal and realistic (pose + standard SRS), which makes adoption tractable.
- It keeps the BS's role natural (BSs already do AoA/AoD estimation for beam management; adding AEGIS's Q inversion is an additional compute stage).
- The DTN angle is explicit: BS holds the environment twin (the ray-traced scene), UE holds the body twin (the pose + grip posterior), both are fused at the BS to compute Q. Each party maintains the twin of what it is closest to physically. That is textbook DTN.

### Risks and caveats

- BS-side per-element IQ access for arbitrary handsets is not always available to the operator depending on vendor baseband support. Modern O-RAN / open-RAN deployments do expose it; proprietary basebands may not. Paper claims should assume O-RAN-capable BS.
- If multipath is dense (indoor corridors with many reflectors), joint 2D AoA/AoD estimation is harder — path count exceeds well-posed recovery. mmWave sparsity helps (3–5 dominant paths typical, per the Qualcomm whitepaper §2.2) but is not guaranteed.
- Calibration: UE and BS RF chains have relative phase offsets that must be calibrated. Standard in TDD systems but nontrivial.
- Latency: BS-side Q computation + downlink precoder update adds one round-trip to the closed loop. For SAR compliance (which is a 6-min ICNIRP averaging window or local 4 cm² peak), this is fine. For beam management (ms-scale) it is also fine.

### PoC footprint

- Same Sionna canyon scene as Idea #2.
- Model both UE and BS. BS with a 8×8 planar array (64 elements) with digital per-element access. UE with 2 modules of 1×5 dual-pol, 9-beam codebook.
- UE transmits SRS cycling through all 9 beams × 2 polarizations = 18 slots per burst.
- BS captures per-antenna IQ per slot → (64, 18) complex matrix per SRS burst.
- Run joint angle/delay OMP (or tensor-ESPRIT) on the (64, 18, delay) tensor.
- Recover k̂_UE,n, k̂_BS,n, ψ_n for each of the dominant paths.
- Build Q from recovered path set using AEGIS `compute_exposure_operator`.
- Compare Q_recovered vs. Q_oracle (from Sionna ground-truth paths).
- Compute the MRT/ECBF precoder from Q_recovered, apply it to the oracle channel, measure the actual SAR_wb and peak APD_4cm² — this is the closed-loop accuracy metric.

This is a clean, well-scoped PoC with an unambiguous success criterion.

---

## Idea #5: Crowdsourced DTN — honest feasibility read

### The concept

A cell contains many UEs in the same physical environment — an open-plan office, a restaurant, an airport, a train carriage. Each UE collects its local beam-RSRP sweep, its pose, and any other sensing it can provide. All of this flows to the gNB, which fuses the sensor streams into a **dense reconstruction of the physical scene** — positions of reflectors, walls, people — which it can then use as an environment twin (Route A) for *every* UE in the cell. Each UE receives back a personalized Q derived from the shared scene + its own pose.

### Why it is attractive

- It gets around the single-UE information bottleneck. One smartphone has 9 beams; 30 phones in the same cafe have 270 beam measurements of the same physical scene.
- It amortizes the environment-twin freshness problem. Scene changes (someone moves a chair, a person walks in) are detected by whichever UE happens to notice, and the update propagates.
- It is the "true" DTN architecture — environment twin centralized at the cell, body twin distributed at UEs, fused in real time. Every DTN paper in the JSAC issue will want something like this.

### Why it is not a good v1 paper

- Scope explosion. Multi-UE Sionna scenes, crowd mobility models, aggregation algorithms, privacy/anonymization constraints, inter-UE inconsistency handling. Each of these is an open research subproblem. Addressing them rigorously is a 6-author paper over 18 months, not a 2-month push before the May 2026 deadline.
- Limited tractable theory. For Idea #4 we can state a clean theorem (BS-side identifiability of Route B from UL SRS + UE beam sweep). For Idea #5 the theorem is either trivial ("more data is better") or intractable ("optimal multi-UE fusion under privacy constraints"). Reviewers prefer papers with one sharp theorem.
- The closed-loop story is much harder to instrument. With a single UE you can point at a single SAR/APD number; with a crowd you are comparing distributions of distributions.

### What is feasible in the current paper scope

A two-UE appendix showing that idea #4 generalizes: with a second UE in the same cell transmitting SRS, the BS's scene reconstruction improves, and the original UE's Q estimate improves in consequence. This establishes the scaling story without requiring a full multi-UE simulation framework.

Scope: roughly one figure (Q-estimation error vs. number of cooperating UEs, K = 1, 2, 4, 8) and half a page of text.

### Recommendation

Keep Idea #5 as an explicit "Extensions" section of the paper, with the two-UE mini-result as the substance. Do not commit PoC effort beyond that for v1. Flag in the paper's conclusion as the most natural next step.

---

## Revised recommendation for the paper spine

With the expanded analysis, my lean has shifted:

**Primary spine: #4 + #2 + mini #5 as the extension.**

- **#4 (reciprocity split)** is the paper's architectural contribution and the clean theorem. It reframes Route B from an impossible UE-side problem into a tractable BS-side problem with a minimal UE-side role. The identifiability proof lifts cleanly.
- **#2 (motion synthetic aperture)** is the paper's headline figure and the nontrivial signal-processing contribution. It shows that even in a *pure-UE-side* regime (no BS cooperation, no reciprocity), the UE can still recover useful AoA by exploiting hand motion — giving an alternate fallback to #4.
- **Mini #5 (two-UE extension)** earns the "DTN" in the paper title by showing the architecture scales.

What I am **not recommending now**:

- #3 (grip-aware Bayesian Q) in its own right — it is too narrow and too dependent on procuring antenna patterns we do not have. **Instead, fold the grip posterior into the pose state that #4 reports to the BS.** That keeps the Bayesian flavor and the CVaR-ECBF connection without requiring a separate contribution section.

### Why this spine is stronger than the previous recommendation

- Two contributions instead of three, with a clear primary / secondary structure. Easier to write coherently.
- Each is independently valuable: even if motion-SAR fails to live up to its promise in simulation, #4 still stands as the paper. Defensive structuring.
- Both have clean theorems (identifiability + error bounds).
- Both have concrete PoC plans with unambiguous metrics (closed-loop SAR/APD vs. oracle).
- The JSAC DTN angle is explicit via the BS/UE split + multi-UE extension.

---

## Open questions for Robin

1. Commit to the #4 + #2 + mini-#5 spine? Or swap in a different ordering (e.g., #2 as primary, #4 as secondary)?
2. For the UE-side antenna model, are we comfortable with the "DFT 9-beam codebook, 1×5 dual-pol, two modules, one active" model as a defensible reference UE? Or do you want me to investigate getting actual measured patterns via IMEC / industry contacts?
3. For the BS-side model in #4, is O-RAN-style per-element IQ access a safe assumption? Or should the paper hedge with both O-RAN and proprietary-baseband scenarios?
4. For #2, do we have an existing wrist-motion dataset (AEGIS or IMEC), or do we need to pick one from the HCI / AR-VR literature?
5. Dedicated subdirectory: propose `/home/user/aegis/JSAC/direction_5_poc/` with `sim/`, `estimators/`, `figures/`, `scenes/`. Acceptable?

---

# Zoom out — re-ranking under "time is no issue, Q is solved"

Robin asked: given that AEGIS gives fast/accurate Q, given time is not the constraint, what is actually the missing ingredient to close the DTN loop? And be creative — new ideas welcome.

This reframes the paper. The earlier ranking over-fixated on Route B — the "can the UE infer paths?" question. With an unlimited scope assumption and AEGIS's Q already mature, the real bottleneck is elsewhere: **Q needs inputs that nobody currently estimates well in real time on commercial hardware.**

## The honest reframing — what are Q's inputs, and who estimates each?

AEGIS's Q requires:

| Input | Today's best source | Real-time? | Bottleneck? |
|---|---|---|---|
| Body mesh (which phantom) | Generic library (Duke, Eartha) | Offline | YES — personalization missing |
| Body pose (head/torso relative to phone) | Unknown — usually assumed | Not estimated anywhere | **CRITICAL GAP** |
| Phone antenna geometry | Device-reported | Yes | OK |
| Antenna element patterns under grip | Offline EM sim or measurement | Static | Grip changes it in real-time |
| Phone position + orientation in world | IMU + GPS | Yes | OK for self, not for BS-side view |
| Propagation paths (ψ, k̂) | RT (if scene known) or UE-measured | RT slow; UE measurement hardware-limited | Route A/B problem |

The two biggest gaps are **body pose** and **grip-conditioned antenna pattern**. Both are "twins" the BS cannot see directly. Route B was trying to solve the paths input. But if pose is unknown, paths don't help.

## The new question the paper should actually ask

*"How does the DTN estimate, in real time, the minimal sufficient state about the user's body, grip, and phone orientation to compute an exposure-compliant precoder — and who owns which part of the twin?"*

That question spans several technical pieces, admits several new ideas, and gives the paper a "closed-loop DTN" narrative that JSAC's DT special issue will love.

---

## New idea A — **BS-side ISAC body-twin: the gNB sees bodies via its own uplink**

**Score: 10/10**

This is the single best idea on the table. It is the strongest DTN story, addresses a gap no one currently tackles, and uses everything AEGIS already has.

**The concept.** In TDD FR2, when the UE transmits uplink SRS, the BS's 64–256 antennas receive not only the direct-path signal but also reflections off scatterers in the cell — including human bodies, which are strong mmWave scatterers with a characteristic radar-cross-section signature. The BS is running an analog-to-digital chain per element, so it has the full spatial channel. Processing this as a radar return — ISAC, Integrated Sensing and Communication, which is a headline 6G topic — the BS can identify human-shaped scatterers, estimate their positions, their coarse postures, and their velocity. No new hardware at the UE or the BS — only new baseband DSP.

**Why this is transformational for exposure-aware beamforming.** Right now the entire exposure-aware MIMO literature (Hochwald, Ying, Castellanos, Zhou) considers ONLY the served UE's body. But a high-EIRP mmWave beam that satisfies SAR at the served UE may violate exposure limits on a bystander two meters away in the main lobe. No paper addresses this because no system currently knows where the bystanders are. ISAC + AEGIS solves this. The BS builds a twin of all bodies in the cell; AEGIS computes per-body Q; the precoder optimization adds a per-body exposure constraint for every inferred body. Closed-loop, cell-wide, reviewer-friendly.

**Pipeline.**
1. SRS + passive reflections → BS-side multi-target radar signal processing (known techniques from automotive radar, OFDM-radar, literature solid).
2. Human-body detection: classify scatterer tracks as human by kinematics (walking speed, limb articulation at cm-scale).
3. Per-body pose inference: from cross-section signature + IMU of served UE (if they hold the phone), estimate head/torso position per body. Coarse — shoulder-high vs. waist-high blob is enough at first pass.
4. For each inferred body, AEGIS computes a coarse Q(body_i) using a generic phantom anchored at the inferred position.
5. Precoder optimization: max sum-rate, subject to SAR_wb_i ≤ limit AND APD_4cm²_i ≤ limit for every i. Standard QCQP but with M × K constraints instead of 1.
6. SRS refresh rate (ms) feeds the loop; the twin is updated each TTI.

**Novelty claim.** *First work to consider exposure compliance for non-served bystanders via passive mmWave sensing at the base station.* This is a clean statement that will survive any JSAC review.

**DTN mapping.** The BS owns the environment + multi-body-pose twin. Each UE contributes its own high-quality self-twin (Idea B below) to improve the served-user's accuracy. Twin fusion is explicit: coarse BS-side pose + fine UE-side pose at the served UE, crude BS-side poses for bystanders.

**Risks.** Human-body radar cross-section at 28 GHz is well-measured (NIST, NYU) but pose classification from sparse scatterer returns is an open problem. Acceptable — paper can use "coarse pose bucketing" (standing/sitting/prone) and show this is sufficient for a 3-dB exposure-margin precoder design.

**PoC footprint.** Sionna scene with multiple body meshes at known positions, generate BS uplink SRS capture, run target-tracking and body-classification on the simulated capture, compare inferred poses to ground truth, feed into AEGIS, compute multi-body-constrained precoder, verify per-body exposure on oracle.

This is the paper that would actually land in JSAC's DT SI and get cited.

---

## New idea B — **On-device sensor-fused body+grip twin via front camera + IMU + capacitive + proximity**

**Score: 9/10**

**The concept.** Modern smartphones have: a 9-axis IMU (gyro + accelerometer + magnetometer), a capacitive touch grid under the entire screen, a proximity sensor (talk mode), a front-facing RGB camera (often 4K + depth on Pro models), sometimes a Face-ID dot projector (structured IR, gives face mesh), sometimes LiDAR (depth sensor). iPhones have UWB. Combined, these are an extraordinary on-device sensing stack that is wasted on emoji reactions.

Train a neural network that fuses these sensors to output, in real time on-device:
- **Grip class** (posterior over the 16 Qualcomm grips).
- **Phone pose in world frame** (tilt, orientation, position drift from IMU dead-reckoning).
- **Body-phone geometry** (head distance + orientation, upper torso position — from front camera pose estimation, Face-ID, or a small pose-net model).

The output is a real-time "UE-side body twin" state that gets reported up to the BS via RRC signaling (few hundred bytes per second).

**Why this matters.** Once AEGIS has accurate pose + grip, the Q computation is deterministic. The entire SAR/APD compliance story reduces to "can we estimate pose and grip cheaply, reliably, and with acceptable latency on a phone?" No one has shown this end-to-end.

**Novelty claim.** *First demonstration of a real-time, on-device body+grip+phone-pose twin that feeds a commercial exposure-aware precoder, with verified compliance on hardware.*

**DTN mapping.** UE owns its local body twin + grip twin + phone-pose twin. BS owns the environment twin + precoder. Twin exchange is the RRC uplink. Each twin is refreshed by its local sensor stream.

**Risks.** Dataset. Need labeled grip / pose / body-position data across many users and scenarios. Paper could bootstrap with publicly available mobile-phone sensor datasets (there are several HCI ones) plus a small custom collection. Sim2real gap exists but is tractable.

**PoC footprint.** Can be partially done without new hardware: collect sensor traces from a test phone, train pose/grip heads, simulate Q-compliance assuming perfect SRS/channel, show closed-loop compliance vs. "oblivious" baselines. A brave version would drive an actual phone prototype.

---

## New idea C — **Predictive Kalman-filtered DTN — forecast Q, precode against the future**

**Score: 8/10**

**The concept.** Pose and grip change at human timescales (10–100 ms). SRS refreshes at TTI scale (0.125 ms). But Q computation in the BS is likely one of the slower parts of the pipeline. If we just react, we're always one Q behind the reality.

Use the sensor streams — IMU, capacitive, front-camera — as the observation model of an extended Kalman filter whose state is the full body+grip+phone-pose twin. The filter predicts the state 50–100 ms ahead. AEGIS computes Q on the predicted state. The precoder is chosen for the near future, not the present.

Because the dynamics are smooth (bodies don't teleport; grip changes take 100+ ms), the prediction is well-posed. The closed loop becomes: sense → predict → Q → precode → transmit, with the precoder matched to the state during the transmission window.

**Novelty claim.** *First predictive twin-in-the-loop formulation for exposure-aware beamforming: sensing latency hidden via state-space prediction.*

**DTN mapping.** Each node maintains its local twin as a Kalman filter. The predicted state is the object exchanged, not the raw sensor data. Minimal signaling.

**This pairs beautifully with Ideas A + B.** A + B provide observations; C provides the prediction layer. Natural integration.

---

## New idea D — **Personalized body mesh from phone LiDAR (or front camera SfM)**

**Score: 7/10**

**The concept.** AEGIS ships with generic phantoms. A real user is not Duke. A phone's LiDAR (iPhone Pro 12+) or a short front-camera structure-from-motion scan can produce a rough personalized mesh of the user's upper body + face in a minute. Anchored to the phone coordinate system via SLAM, this mesh replaces the generic phantom for Q computation. The exposure numbers become specific to this user, not averaged over a synthetic population.

**Why it matters.** Regulatory compliance is always averaged over the worst-case population — but *operational* compliance (what's really happening to this specific user right now) is personalized. Personalized Q gives the precoder 2–5 dB of additional feasible power before hitting true limits.

**Novelty claim.** *First personalized-body-twin exposure-aware precoder using on-device 3D scanning.*

**Limitations.** LiDAR only on Pro phones; SfM is noisy; privacy concerns with body scanning (solvable via on-device-only processing). Smaller contribution on its own but is a natural add-on to Ideas A + B.

---

## New idea E — **Radar-based grip inference via phone's own mmWave leakage**

**Score: 6/10**

**The concept.** When a phone transmits uplink at mmWave, some energy couples into nearby reflectors — including the user's own hand gripping the device. The reflection changes with grip. The phone's baseband, if given access to a self-listening receiver path (some modems support this for calibration), could in principle do short-range radar on the user's hand to infer the grip.

This is creative but hardware-dependent. Whether a commercial modem exposes this path is unknown.

**Score it low** for PoC unless Robin has a specific hardware route.

---

## Re-ranking summary — with scores

| # | Idea | Score | JSAC DTN fit | Novel |
|---|---|---|---|---|
| **A** | **BS-side ISAC body-twin + multi-body exposure precoder** | **10/10** | Perfect | Yes |
| **B** | **On-device sensor-fused body+grip+pose twin** | **9/10** | Strong | Yes |
| **C** | Predictive Kalman twin | 8/10 | Strong | Yes |
| 2 (old) | Motion synthetic aperture | 7/10 | Medium | Partial |
| 4 (old) | Reciprocity-split Route B | 7/10 | Medium | Theorem-clean |
| **D** | Personalized body mesh (LiDAR) | 7/10 | Medium | Yes |
| 3 (old) | Grip-aware Bayesian Q | 6/10 | Medium (subsumed by B) | Partial |
| **E** | Self-radar grip inference | 6/10 | Weak | Speculative |
| 5 (old) | Crowdsourced DTN (two-UE appendix) | 5/10 | Natural extension | No |

## New recommended spine

**Primary: A + B + C together as one coherent paper.** The story:

- **Setup.** The exposure compliance problem is not about the served UE; it is about every body in the main lobe. DT technology gives us the tools to treat the cell as a collection of bodies with their own Q.
- **BS-side contribution (A).** The BS builds a multi-body twin using ISAC-style processing of its own uplink SRS. No new hardware; only new baseband processing.
- **UE-side contribution (B).** The served UE builds its own high-accuracy self-twin from sensor fusion, and reports it to the BS. This improves the served-user's Q beyond what ISAC alone can provide.
- **Dynamics contribution (C).** A Kalman-filtered predictive twin eliminates sensing latency, so the precoder is matched to the state at TX time, not the state at sense time.
- **Closed-loop compliance.** The precoder optimization includes per-body exposure constraints drawn from the twin. Each TTI the twin is updated and the precoder adapts.
- **PoC.** Sionna canyon + multiple body meshes + simulated UE sensor streams → full pipeline → compliance metric over time.
- **Theorem.** The core technical theorem is the error bound on ISAC-inferred body pose as a function of SRS length and BS antenna count, and the resulting bound on the exposure margin the precoder must maintain.

**Old Route B (reciprocity-split, motion-SA) gets demoted to one paragraph in "Alternative UE-side twin sources."** These are clean results but they are subcomponents, not the main paper.

**Old Idea 5 (crowdsourced) stays as "Future Work" with a two-body-in-cell mini-extension in the appendix to preview.**

## Direct answer to "what is the missing ingredient"

The single missing ingredient is **a real-time multi-body pose twin the BS can construct without requiring cooperation from anyone but the served UE**. That unlocks everything downstream: per-body Q, multi-body exposure constraints, personalized precoder, closed-loop compliance at the cell scale.

ISAC-processed uplink SRS at the BS is the natural answer. It costs no new hardware. It scales to any number of bodies in view. It's an untouched gap. That is the paper.
