# JSAC2 paper spine plan — v2

**Target venue.** IEEE JSAC SI — *Digital Twins for Wireless Networks: Enabling Application-Aware and Closed-Loop Optimization*. Submission 2026-05-01. Publication Q4 2026.

**Status of this document.** Supersedes `JSAC_SPINE_PLAN.md` (v1). v1 made several wrong calls under the influence of an over-aggressive fresh-eyes critique; v2 keeps the surviving structural recommendations and reverses the wrong ones. v4 (`rihb_theory_v4.tex`) is a planning artefact, not a publishable draft — what's being judged is the *spine*, not v4's prose.

---

## 1. Deltas vs. v1

| Item | v1 said | v2 says | Why |
|---|---|---|---|
| Live SAR receipt | Defer to a separate paper | **Keep in main paper** as Section XI (1 col) | Two-products-on-one-machinery is the structural strength, not a flaw. The receipt earns extra justification by being epidemiologically useful (Röösli-cohort feed; CLUE-H link) |
| Röösli citations | Drop entirely | **Drop from §I polemic, keep in §XI as forward link to RF-epi cohort use** | Genre-correct location: epi citation in the methods-for-epi paragraph, not in the wireless-failure-modes opening |
| RIS literature comparison | Add full RIS-cascaded-channel-estimation lit review | **One sentence acknowledging the analogy; keep the cheeky brain joke; no serious RIS lit engagement** | RIHB is framing, not a research claim against Wei/He/Zhou |
| DTN literature | Add Chen/Saad/Mozaffari/Hashash | **Confirmed: add, this is where venue fit lives** | The CFP is a DTN special issue; we have to engage the DTN canon |
| App UX section | Cut entirely | **Cut three-screen narrative + metaphors; keep one paragraph in §VII reframed as "human-in-the-loop pose-gradient control"** | Genre-correct, content survives |
| Convergence experiment | "Convergence demo" (2 days) | **Three-part in-silico study: existence / reachability / failure-modes** (3-4 days) | Robin's reframe — the right question isn't "does our descent converge" but "does a good solution always exist, and when does the loop find it" |
| Pose dimensionality | 1-DOF torso-yaw figures | **N-D SMPL-X with proper visualisation: per-joint sensitivity bar chart + comfort-vs-rate curve + convergence trace** | Honest about the high-D nature of the optimisation |
| Network-centric architecture | Body-twin-centric diagram | **RAN controller on the left, twin in middle as agent, semantic outputs (rate-target + receipt) on right** | DTN-fit lives or dies on this diagram |
| Page budget | 14 pp double-col | **~12-13 pp typeset (10 body + 1.5 refs + 1 appendix); SI ~15-20 pp** | v4's 23 pp single-col converts to ~13 pp double-col (calibrated against v5: 15,229 words → 17 pp = 895 w/p) |
| §XIII "Connection to v5" | Reframe | **Cut entirely** | Citing your own unpublished prior draft is unhelpful and looks self-referential |
| "What this is not" + "Loose threads" | Cut | **Confirmed: cut** | Dissertation-chapter mannerisms |
| Opening framing | Drop polemic | **Keep punchy "mmWave routes through the body twice" hook (from NEW_ANGLE.md), drop polemic *register*** | The framing is good marketing; only the "has not won the argument" tone needs to go. See §3 below for the four-paragraph opening template |

---

## 2. The non-negotiable structural pivots

Two changes carry the v2 spine; everything else is local optimisation.

### Pivot 1: network-centric architecture, not body-centric

The v1 spine had the body-twin as the protagonist and the BS as a boundary condition. The CFP wants *the network* as the active subject, with twins as agents inside it. v2 puts the RAN controller on the left of every architecture diagram, the bidirectional UL-pilot / DL-precoder channel as the spine, the on-device body-twin in the middle as the wireless-native intelligent agent, and two semantic outputs on the right: the pose suggestion (consumed by the user, fed back via IMU + UL pilots) and the live SAR receipt (consumed by the user as semantic feedback, optionally aggregated to an epi cohort). One diagram, all CFP keywords realised structurally.

### Pivot 2: convergence as a research question, not a demo

The right question for the closed-loop section is not "did our gradient descent reach the optimum on one example pose" but **"is there always a good pose, and when does the loop find it?"** Three nested experiments answer this:

1. **Existence.** For each of N random (BS-geometry, scene, baseline-pose) tuples, does *any* comfortable pose move (within budget C(Δθ) ≤ ρ) achieve ≥ X dB rate improvement? Sweep N = 200; report the fraction by regime (LOS-attenuated, binding, NLOS-deep). Likely answer: ~100% in LOS-attenuated, ~80% in binding, ~30% in deep NLOS (deep NLOS scenes have no good pose because the body cannot create paths that don't exist).
2. **Reachability under gradient descent.** Given existence, does noisy K-iteration UL-pilot-corrected gradient descent reach within 1 dB of the comfortable optimum? Report success rate vs (iteration budget K, UL-SNR, IMU σ_joint, calibration-class K_99 vs Tier C vs Tier D).
3. **Failure-mode taxonomy.** When the loop fails, *why*? Categorise: (a) no good solution exists, (b) local minimum trap, (c) MCS-cap saturation (∂R/∂θ ≡ 0), (d) calibration drift, (e) IMU noise floor, (f) comfort-budget too tight. Report fractions across the sweep.

This converts the App-UX section from advocacy into an empirical contribution. It also generates the headline numerical figure for free.

---

## 3. The opening template (after Robin's "keep the punch, bolt on DTN")

```
¶1 (the hook, kept from NEW_ANGLE).
Two things slowed mmWave 5G past schedule, and both route through
the human body. Bodies in LOS of an FR2 channel cost 25-40 dB
of received power [MacCartney 2017, Maccartney 2017blockage].
Public concern about exposure carries the second cost: deployment
frictions that ICNIRP compliance numbers have not, on their own,
dissolved [ICNIRP2020]. Both blockers locate at the same point in
the propagation graph: the body in the cell.

¶2 (the DTN bridge).
This paper proposes that an on-device digital twin of the user's
body, calibrated by uplink pilots and operating inside the radio
control loop, addresses both. As an intelligent agent in the
wireless control loop, the body-twin computes (i) a live, transparent
receipt of how much power the body is currently absorbing, and (ii) a
pose-differentiable cascaded channel against which sub-degree pose
suggestions are issued back to the user via a low-bandwidth feedback
signal. The user actuates, the IMU + UL pilots resolve the new state,
the BS adapts its precoder, and the loop closes. The architecture
realises twin-in-the-loop optimisation in the sense of [DTN-CFP scope].

¶3 (the cheeky kept; one-sentence RIS analogy, no lit comparison).
A reconfigurable intelligent surface (RIS) is a passive panel of
phase shifters [DiRenzo 2020, Wu 2019]. A human body at mmWave is
a passive scatterer whose surface phase pattern is fixed by pose,
and whose only tuning is the user's posture. Humans are reflectors
at mmWaves; they are also mounted with a highly intelligent organ
called the brain; they are therefore Reflective Intelligent Human
Bodies. We adopt RIS lingo throughout (cascaded channel, surface
phase mask, re-pointing) but the analogy is informal — the body
is hardly a panel — and we do not relitigate the RIS estimation
literature.

¶4 (contributions).
The two-products-one-machinery table.
```

Röösli stays out of §I and goes to §XI where it lands as a forward-citation: *"the receipt produces a per-individual absorbed-energy time series of the kind that current cohort studies on RF exposure approximate via self-report (Röösli 2010, 2021); cohort-scale aggregation of opt-in receipts is a methods improvement for studies in the lineage of [CLUE-H, COSMOS, HERMES, MOBI-Kids]."* That sentence justifies *both* citations being in the paper, in the genre-correct register.

---

## 4. Section ordering and page budget — IEEE Trans 2-column 10pt

Calibration: v5 = 15,229 words → 17 pp at ~895 w/p. v4 = 12,003 words → would be ~13 pp double-col before deltas.

| § | Title | Target words | pp | Notes |
|---|---|---|---|---|
| I | Intro (4-paragraph template above) | 700 | 0.8 | CFP framing in ¶2 |
| II | DTN architecture: body-twin in the wireless control loop | 600 | 0.7 | **The network-centric figure**; ties to CFP scope sentence; one-paragraph DTN-lit positioning |
| III | RIHB physics, abridged | 1000 | 1.1 | Fresnel + pseudo-Brewster collapse boxed; **incidence-plane figure** (`theory/figures/incidence_plane_fig.pdf`) anchoring Approximation 1; full derivation in SI |
| IV | Body PO scatterer + Q_abs | 800 | 0.9 | SMPL-X parameterisation, per-triangle frame; Approx 1 + 2 boxed; squared-norm form of Q_abs |
| V | UE-anchored Kirchhoff render of h_body | 1000 | 1.1 | The load-bearing primitive; complexity argument in 2-3 sentences; pose-telemetry sources subsection (lift verbatim from JSAC v5 §sec:imu) |
| VI | Closed loop: UL pilots calibrate the twin | 1200 | 1.3 | Residual decomposition (β BS-side recap, γ body-side); three candidate γ-parametrisations evaluated empirically; K_99 SVD picked; **calibration-recovery figure** |
| VII | Pose-differentiable rate + human-in-the-loop control | 800 | 0.9 | Cascaded SINR, ∇θ R, MCS27 saturation note; one paragraph on the gradient-with-feedback control loop (replaces App UX) |
| VIII | Closed-loop convergence study (the new headline) | 1500 | 1.7 | **Existence / reachability / failure-mode three-part study**; 3-panel headline figure (per-joint sensitivity bar + comfort-vs-rate Pareto + convergence trace with body silhouettes) |
| IX | Live SAR receipt | 700 | 0.8 | One column. Computation, semantic-feedback role, **CLUE-H consortium forward link**: receipts upgrade the exposure side of prospective RF-EMF cohort studies from self-reported questionnaire proxies to per-individual measured absorbed-energy time series, against which the cohorts' bio/health outcomes can be linked at higher resolution (Röösli 2010, 2021) |
| X | Discussion + baselines | 700 | 0.8 | Comparison vs no-twin ZF, no-twin MRT, T-pose-prior twin; bandwidth/compute table; privacy delta over a model-only baseline |
| XI | Conclusion | 200 | 0.2 | Two paragraphs |
| Refs | | — | 1.5 | ~50 refs |
| App. A | Per-path Fresnel transmission operator | — | 0.5 | |
| App. B | Approximations 1 + 2 error budget | — | 0.5 | |
| **Total** | | **9200** | **~12.8** | Comfortable under JSAC soft cap |

### SI (~15-20 pp, no length limit)

| Section | Content | pp |
|---|---|---|
| SI A | Full Maxwell → PO derivation; polarisation-aware Stokes; curvature; GELU diffraction; inter-body radiosity (lift from TAP paper, cite-and-reproduce-table) | 4 |
| SI B | Layered skin (Chew recursion, Fabry-Pérot) for sub-6 GHz | 2 |
| SI C | Compliance metrics: SARwb / psSAR10g / peak-local APD; which one binds at which frequency | 1 |
| SI D | Calibration recovery: full SNR×K table, Tier D/C/B(K), close-BS vs far-BS | 2 |
| SI E | SVD spectrum sweep, regime transition diagnosis | 1 |
| SI F | UE-anchored render complexity proof | 1 |
| SI G | Bandwidth + per-component refresh cadences + on-device feasibility | 1 |
| SI H | Virtual-IMU model (lift JSAC v5 §V.A) + IMU sensitivity sweep with γ-corrected closed-loop overlay | 2 |
| SI I | Existence-experiment full sweep (200 scenes); reachability tables; failure-mode bar chart | 2 |
| SI J | Notation + acronym summary | 0.5 |
| SI K | Receipt-as-epi-cohort-data: aggregation protocol, privacy considerations, sample size to detectable-effect calculation, link to CLUE-H consortium objectives (cohort-prospective bio outcome assessment with high-quality exposure side) | 1.5 |

---

## 5. Code work still needed

Sorted by load-bearingness and dependency.

| # | Task | Load-bearing for | Effort | Status |
|---|---|---|---|---|
| 1 | SMPL-X swap in `pose_sweep.py`: `make_body(yaw, pos)` → `make_body_smplx(theta_axis_angle, pos)` via `aegis.geometry.parametric.ParametricBody`; preserve the `Body` interface so downstream code is untouched | All hero figs | 1 d | TODO |
| 2 | **Existence experiment** (`existence_sweep.py`): 200 random (BS-geom, scene-loss, baseline-pose) tuples; for each, brute-force search over pose moves with C(Δθ) ≤ ρ; report fraction achieving ≥ X dB improvement, stratified by regime | §VIII existence panel | 2 d | TODO |
| 3 | **Reachability experiment** (`reachability_sweep.py`): for the existence-positive subset, run K-iteration UL-pilot-corrected gradient descent from cold start; report success rate vs K, UL-SNR, σ_joint | §VIII reachability panel | 2 d | TODO |
| 4 | **Per-joint sensitivity** (`per_joint_sensitivity.py`): compute `\|∂R/∂θ_j\|` at baseline; rank; produce horizontal bar chart with anatomical inset showing top-5 joints | §VIII sensitivity panel | 0.5 d | TODO |
| 5 | **Comfort-vs-rate Pareto** (`comfort_pareto.py`): rate gain (dB) vs total comfort cost C(Δθ) across the comfort ball; one curve | §VIII Pareto panel | 0.5 d | TODO |
| 6 | **Failure-mode classifier** (`failure_taxonomy.py`): for each failed trajectory in the reachability sweep, label why it failed (no-soln, local min, cap-saturation, calibration-drift, IMU-floor, comfort-tight); bar chart of fractions | §VIII failure-mode panel | 1 d | TODO |
| 7 | **Live SAR receipt visualisation** (`sab_receipt_viz.py`): per-triangle Sab on SMPL-X with cumulative-dose number, time-integrated over a representative slot; one figure for §IX | §IX figure | 1.5 d | TODO |
| 8 | **DTN-architecture TikZ** in LaTeX (no code): RAN-controller LEFT, twin MIDDLE, semantic outputs RIGHT, with bidirectional UL/DL channel | §II figure | 1 d | TODO |
| 9 | **Adapted physics figure**: incidence-plane fig (`theory/figures/incidence_plane_fig.pdf`) — already exists, just include + caption | §III figure | 0.25 d | done modulo inclusion |
| 10 | **Baselines run** (`baselines.py`): no-twin ZF, no-twin MRT, T-pose-prior MRT — for the same convergence-experiment sweep as #2-3, so we have a comparison column | §X discussion + table | 1.5 d | TODO |
| 11 | **IMU sensitivity re-run with γ overlay** — adapt JSAC v5 imu_sweep.py to overlay the γ-corrected closed-loop curve; produce SI H figure | SI H | 1 d | TODO (data already exists in `JSAC/code/experiments/plaza_run/figures/imu_sweep.npz`) |
| 12 | **Bandwidth + compute table refresh** from current code timings (Kirchhoff render, calibration LS, gradient FD, etc.) → table for §X | §X | 0.5 d | TODO |
| 13 | **Plaza-scale numerical example** (one served user in Brussels Grand Place geometry from `JSAC/code/experiments/plaza_run/scenario.py`) — *deferred*, optional | §VIII headline replacement | 3 d | DEFERRED to extension paper |
| 14 | **Peak-local APD** computation (4 cm² surface average above 6 GHz) for SI C | SI C | 0.5 d | TODO |
| **Total committed** | | | **12.5 d** | |
| **Total optional** | | | **3 d** | |

### Code dependency graph (do in this order)

```
[1] SMPL-X swap
    ↓
[2] Existence sweep ────┐
    ↓                   │
[3] Reachability sweep  │ all parallel after [1]
    ↓                   │
[6] Failure taxonomy    │
                        ↓
[4] Per-joint sens. ────┤
[5] Comfort-Pareto  ────┤
[7] Receipt viz     ────┤
[10] Baselines      ────┤
[11] IMU γ-overlay  ────┘
                        ↓
[8] DTN arch TikZ (paper)
[9] Incidence-plane fig (paper)
[12] Bandwidth table (paper)
[14] Peak APD (SI)
```

Items 2-7 + 10-11 generate every numerical figure for the paper. Items 8-9-12 are LaTeX-only. The paper-writing can start on the spine the day item 1 lands; figures fill in as their generators complete. Critical path is **~5 working days** if items 2-3 and 4-7 run in parallel by you working on different scripts on different days, longer if strictly serial.

---

## 6. Timing

Per Robin: timing is not a blocker on this submission. Work proceeds at quality cadence; the 2026-05-01 nominal deadline is not load-bearing on the spine.

---

## 7. What dies and what lives, one-line summary

**Dies in v2 (vs. v4 prose):** Röösli polemic phrasing; "what this is not" section; "loose threads and conjectures" section; App UX three-screen narrative; metal-detector metaphor as a section; "connection to v5" subsection citing unpublished work; six pages of full Fresnel derivation in main text; one-DOF synthetic torso-yaw as the headline numerical evidence.

**Lives in v2:** the punchy "two failure modes route through the body" hook; the cheeky humans-have-brains RIHB joke; two-products-on-one-machinery framing; live SAR receipt (with epi-cohort-data forward link justifying the kept Röösli citations); UE-anchored Kirchhoff render as the central new primitive; K_99 SVD calibration; pseudo-Brewster collapse + Approximations 1 & 2 as boxed results; translation phasor identity; the incidence-plane figure as the §III physics anchor; Thelonious in SI for compliance traceability + SMPL-X in main for differentiability.

**New in v2:** network-centric DTN architecture diagram; closed-loop convergence study as three-part empirical contribution (existence, reachability, failure-modes); honest N-D pose visualisation (per-joint sensitivity + comfort-vs-rate Pareto + convergence trace); baselines column (no-twin ZF, no-twin MRT, T-pose-prior MRT); CLUE-H / Röösli forward link in §IX; one-paragraph DTN-lit positioning in §II.

End of v2.
