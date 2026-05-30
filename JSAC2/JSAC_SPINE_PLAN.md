# JSAC2 paper spine plan

**Target venue.** IEEE JSAC SI — *Digital Twins for Wireless Networks: Enabling Application-Aware and Closed-Loop Optimization* (CFP at https://www.comsoc.org/publications/journals/ieee-jsac/cfp/digital-twins-wireless-networks-enabling-application-aware-and). Submission: 2026-05-01. Publication: Q4 2026.

**One-line pitch (CFP-resonant).** A wireless-native body-twin acts as an *intelligent agent* in the radio control loop: uplink pilots calibrate the on-device twin in real time, the twin returns (a) a live SAR receipt — semantic, user-facing — and (b) a pose-differentiable mmWave channel on which a metal-detector-style UI helps the user ride a gradient toward MCS-cap rate. One body twin, two closed loops, one piece of per-triangle Kirchhoff machinery.

**CFP keywords to salt throughout.** *twin-in-the-loop*, *closed-loop optimization*, *cross-layer feedback*, *differentiable control*, *application-aware*, *semantic-aware*, *real-time decision-making*, *foundation-model-grade DT intelligence* (light), *trustworthy data collection*, *open interfaces*. The CFP is literally asking for: differentiable control of DTNs (we have it), real-time semantic feedback to users (the SAR receipt is exactly this), DT-driven wireless adaptation (gradient-driven pose UI hands a control signal back to the BS).

---

## 1. What we already have

### Theory (rihb_theory_v4.tex, 23pp single-column A4)

Fully self-contained ground-up derivation. Every section can be lifted into JSAC2 with light editing. Order:
1. §1 Intro — RIHB framing, two-products-on-one-machinery table
2. §2 Fresnel at a lossy half-space → pseudo-Brewster collapse (T0 ≈ 0.54 at 28 GHz, ≤2% TE/TM split, valid n≥3.73)
3. §3 SMPL-X body PO, per-triangle local frame, BS array, far-field-from-BS path dictionary J
4. §4 Qabs operator including **Approximations 1 & 2** inline (TM-pol direction ≲4% on cross-terms, universal depth coupling ≤0.5%)
5. §5 UE-anchored Kirchhoff render (the central new primitive replacing the rank-1-radar `Frib(θ, k_out)` machinery)
6. §6 Complexity argument — backward path tracing > forward radiosity at sparse UE counts
7. §7 Closed loop with body-side γ; tier D / C / B ladder evaluated empirically; K_99 SVD picked as winner
8. §8 Pose-differentiable rate (cascaded SINR, MCS27 cap, ∇θ R)
9. §9 Block diagram + bandwidth budget
10. §10 App UX — gradient-with-feedback, three-screen, metal-detector metaphor, single-user
11. §11 Live SAR receipt (informational, not optimised against)
12. §12 PoC results
13. §13 Connection to v5 (β calibration parallel)
14. §14 What this is not / §15 loose threads / §16 summary
15. SI: calibration recovery evidence, layered Fabry–Pérot for sub-6 GHz, compliance metrics (SARwb / psSAR10g / peak-local APD), notation summary

### Code (JSAC2/code/)

- `kirchhoff.py` — per-triangle Kirchhoff render primitive (visibility cull from r_p, vectorised over triangles, pseudo-Brewster K = i k0 r0). ~100 ms/pose, single CPU core.
- `scene_nlos.py` — BSArray (8×8 URA, λ/2, 28 GHz), `los_path_dict`, `los_h_at_phone` with scene-loss knob.
- `pose_sweep.py` — torso-yaw sweep across 3 regimes (LOS-attn 35 dB, binding 55 dB, NLOS 80 dB).
- `calibration.py` + `calibration_run.py` — synthesise UL pilots + fit Tier D / Tier C (R=6) / Tier B (K-mode SVD with cached U).
- `svd_spectrum.py` — Λ singular spectrum across BS distances (30/10/5/3 m); rank-1 → rank-many regime transition.
- `animate_pose.py` — 4-panel GIF (body Sab heatmap, body Kirchhoff-to-phone, top-down scene, SINR+rate trajectory).
- `plots.py` — fig1 (pose-sweep hero), fig1b (diagnostics), fig2 (SVD spectrum), fig3 (calibration recovery).

### Figures + data (JSAC2/code/outputs/)

| File | What it shows | Status |
|---|---|---|
| fig1_pose_sweep.png/pdf | SINR / rate / ‖h_b‖ vs torso yaw, 3 regimes | Hero candidate |
| fig1b_pose_sweep_diagnostics.png/pdf | Phase / cos-similarity / ‖h_LOS‖ ratio | Appendix |
| fig2_svd_spectrum.png/pdf | Λ spectrum + cum-mass for 4 BS distances | Sec. 7 (regime transition) |
| fig3_calibration.png/pdf | Tier D/C/B(K) recovery vs SNR | Sec. 7 |
| fig4_setup.png/pdf | Geometry diagram | Sec. 9 helper |
| anim_pose_sweep.gif | 36-frame ±30° yaw sweep | Companion artefact, not in PDF |
| pose_sweep_S2/S3/S2bind.npz | Raw arrays | For SI tables |
| svd_spectrum.npz | SVs + K_99 per geometry | For SI tables |
| calibration_recovery_far30m/close5m.npz | Recovery curves | For SI tables |

### Hero numbers we can quote today

- 9 dB cascaded-SINR swing from torso yaw alone in body-shadowed LOS; 20+ dB in NLOS
- 32% rate variation in the binding regime from yaw alone
- K_99 = 1 at 30 m BS (sub-beamwidth body), K_99 = 4 at 5 m (super-resolved)
- 1% body-channel reconstruction at 40 dB pilot SNR with K=8 SVD basis (far BS)
- 3% Tier C reconstruction at 40 dB pilot SNR (close BS, body resolved)
- 100 ms / pose UE-anchored Kirchhoff render on a single CPU core (vs >25 s/pose with strict BVH visibility — 250×)
- v5 plaza already ran at 74.0 Gbps MCS27 sum-cap with 0.53% violation under virtual IMU σ=4° (this is the point we connect to)

### Reusable prior-work assets (validated, in repo)

- `src/aegis/geometry/parametric.py` — SMPL-X loader, gender-neutral, returns mesh + faces
- `src/aegis/geometry/virtual_imu.py` — Madgwick-style noise model (drift+lag+white), σ_joint knob
- `src/aegis/geometry/pose_stream.py` — AMASS pose ingest
- `src/aegis/coherent/{exposure_operator, field_channel, multibody_ecbf, multibody_ecbf_jax}.py` — Q operator + ECBF solver, JAX-vmap'd
- `JSAC/code/experiments/plaza_run/scenario.py` — Brussels Grand Place geometry, 26 GHz, 8×8 UPA, 25/15/10 tier split, AMASS walks
- `data/poses/plaza_run_walks/` — 50 ingested AMASS walks
- `papers/TAP_paper/paper.tex` line 326 — **the TikZ flowchart**: Exact → Unpolarised → Geom → Whole, plus sub-6 GHz Fabry-Pérot branch, plus Regulatory outputs (APD, SAR10g, SARwb), plus Inputs+Corrections boxes. This is our IIIa figure.
- `theory/monograph_v2.tex` lines 4201, 4344 — Approximation 1 + 2 with proofs
- `JSAC/paper/paper_jsac_v5.tex` lines 542, 1206, 1310 — virtual-IMU and IMU-sweep sections we lift verbatim into JSAC2 §V

---

## 2. What's missing — be ambitious

### A. SMPL-X integration (currently we ship Thelonious in figures)

The user is right: every figure should be SMPL-X, not Thelonious. SMPL-X is the differentiable mesh that lets the gradient flow from θ → channel. Thelonious is the FDTD-validated dosimetry phantom but is non-parametric. The fix is straightforward:

- Replace `make_body(yaw, world_centroid)` in `pose_sweep.py` with an SMPL-X version that takes a θ vector (axis-angle, 22 joints, 66 DOF), runs `ParametricBody` forward, applies world transform, returns the same `Body` interface.
- For "torso yaw" we set the L4–L5 joint axis-angle to ±yaw·z_hat; everything else stays at canonical T-pose offset by a comfortable seated pose `θ⁰`.
- Re-render fig1, fig1b, GIF with SMPL-X mesh. Visually: body looks human; same numbers (within Kirchhoff render tolerance), since per-triangle physics is mesh-agnostic.
- Cost: ~1 day, single PR.

### B. Headline numerical example for JSAC2

What scenario screams "digital twin closing the wireless loop"? Two strong candidates, recommend (1):

**(1) Plaza window-side seated user [recommended].** Brussels Grand Place geometry (already in `plaza_run/scenario.py`), one served user inside a café window at 30 m range from a rooftop BS at 26 GHz. The user's torso partially shadows LOS; sub-degree pose moves un-shadow. We instrument:
- the live SAR receipt (Sab heatmap on the user's body, dose number in mWh),
- the body-mediated channel coefficient h_b(θ) from the UE-anchored Kirchhoff render,
- the cascaded SINR + MCS27 rate,
- one round of UL-pilot calibration that updates γ (3 candidate parametrisations evaluated empirically),
- the gradient-with-feedback UI loop (3–5 small pose moves in succession).

This concretely realises the CFP's "DT-driven wireless adaptation" + "twin-in-the-loop" + "real-time semantic feedback to user" + "differentiable control" in one geometry, using prior-work plaza assets.

**(2) Plaza-scale 50-body run with one served RIHB.** Reuse the v5 plaza_run pipeline, mark one user as the RIHB-opt-in served user, and show the rate envelope across her walk (AMASS) under (a) no pose suggestion, (b) IMU-only gradient suggestion, (c) full closed loop. Bigger but heavier-lift; better as an extension paper. Park as JSAC2 future-work paragraph.

We pick (1) for headline; cite (2) as roadmap.

### C. Convergence demo for the gradient-with-feedback UX

The App UX claim — "metal detector, the user rides the gradient" — is currently a story without evidence. We need a small experiment:

- Initial pose θ⁰ at typical seated baseline.
- BS suggests a unit-norm gradient direction; user takes a small step (sub-degree to few-degree) along it; UL pilots resolve a new γ; new gradient suggested.
- Plot rate(θ) over 5–10 iterations from a cold start; show convergence to within 1 dB of the grid-optimum from a sweep.
- This is the *headline* figure for §X (App UX). Without it, the App UX section is hand-wavy. With it, the section earns its existence.

Code lift: ~2 days. New `JSAC2/code/closed_loop_descent.py` that wraps `kirchhoff_h_body` + `calibration.fit_tier_b` + a finite-difference gradient on θ.

### D. Block diagram TikZ

Lift the TAP-paper flowchart at `papers/TAP_paper/paper.tex:326-441` (Exact → Unpolarised → Geom → Whole, with sub-6 GHz, Inputs, Corrections, and Regulatory-outputs boxes). Adapt for JSAC2 IIIa: collapse the regulatory-outputs box into "live SAR receipt" + "Q_abs to compliance precoder," and add a forward branch into "h_body Kirchhoff render → cascaded SINR → MCS." This is **the** figure that places our work on the same page as ICNIRP and as the rate stack — exactly what JSAC reviewers want to see.

### E. IMU-section placement

JSAC v5 §sec:imu (lines 542-590) treats virtual IMU as the *canonical* pose-information source feeding the twin. JSAC2 inherits the same telemetry stream but the closed-loop dynamics are different: now the UL pilots can *correct* the IMU pose via the channel residual. So we need:

- A short §V.B in main text: "Pose telemetry sources." One paragraph: GPS+IMU (Madgwick σ_joint = 4°), virtual IMU model from v5, T-pose fallback. **Lift verbatim**, ~1/2 page.
- A subsection in §VII (closed loop): "γ also absorbs IMU pose error." The body-side γ in the K-mode SVD basis is exactly what corrects residual IMU pose mis-estimation — the same coefficients that absorb mesh-dielectric mismatch absorb pose mismatch. Important pedagogical link to v5.
- An SI appendix carrying the JSAC v5 IMU sensitivity sweep figure (fig:imu-sweep, the σ ∈ [0°, 16°] curve), with one paragraph re-running it under the new γ-corrected closed loop. **Re-run**, ~1 day; data already exists in `JSAC/code/experiments/plaza_run/figures/imu_sweep.{npz,py}`.

### F. CFP framing tone

The introduction (and conclusion) must be re-voiced with CFP keywords. Right now §1 is a pitch about mmWave deployment, which is great but *generic* for a digital-twin SI. The opening should put the body-twin as a *DT instance*: "we treat the user's body as a wireless-native digital twin that operates inside the radio control loop." Then mmWave is the application, not the framing. This is one rewrite of two paragraphs.

### G. Numerical Stokes/curvature/GELU appendix (TAP paper imported)

The TAP paper has the full polarisation-aware Stokes vector treatment, the curvature correction (1/(kR) per body part), the GELU diffraction smoothing, the inter-body reflection radiosity series. v4 currently ducks all of this. For JSAC2 SI we want a "complete physics" appendix that says: "the per-triangle PO law we use is the geometric corner of a hierarchy. The Stokes-vector / curvature / diffraction / inter-body corrections are each below 5% on whole-body Sab and below 8% pointwise on small features (ear edges, fingertips); see TAP paper for proofs." Half-page in the SI with the TAP error-budget table reproduced.

### H. Architecture / interface diagram

Add one TikZ diagram (separate from the TAP-style flowchart) showing the full closed loop:
- BS-side path dictionary J + per-path β calibration (v5)
- UL pilots → on-device twin
- Twin computes h_body and Sab from per-triangle Kirchhoff
- ∇θ R → small pose suggestion → user's brain → user moves → new IMU pose
- Sab → user-facing receipt (semantic feedback)

This is the "twin-in-the-loop" figure the CFP asks for. ~1 day.

---

## 3. Pacing and page targets — IEEE Trans 2-column

JSAC main text = **14 typeset pages** (with 18p hard cap including refs). The current 23pp single-column A4 of v4 maps to roughly **13 pp double-column** in IEEE Trans format — already at target, with room only by surgical compression. The plan trades depth for the SI freely (the SI in JSAC has no page limit and is reviewed alongside).

### Main text page budget (target 14 pp of body, +2 pp refs/bio)

| § | Title | pp | Notes |
|---|---|---|---|
| I | Introduction (CFP-aligned) | **1.5** | 2 paragraphs on mmWave + RIHB, 1 paragraph CFP framing, 1 paragraph contributions, table of two products |
| II | RIHB physics in one page | **1.0** | Fresnel + pseudo-Brewster collapse, T0 ≈ 0.54 boxed result, defer derivation to SI; reproduce TAP-paper TikZ flowchart |
| III | Body as PO scatterer | **1.5** | SMPL-X parameterisation, per-triangle frame, J path dictionary, far-field-from-BS test (Fraunhofer per anatomical patch), Approximations 1 & 2 stated as boxed propositions with 1-sentence proof sketches |
| IV | Q_abs operator + live SAR receipt | **1.5** | Squared-norm form, translation phasor identity, define h_body alongside; semantic-feedback paragraph on the receipt; compliance metric pointer |
| V | UE-anchored Kirchhoff render of h_body | **1.5** | The body-to-phone integral, near-field-by-construction, complexity argument (backward beats forward at sparse UE), pose telemetry sources sub-section (verbatim from v5 IMU §) |
| VI | Closed loop: UL pilots calibrate the twin | **2.0** | Residual decomposition, β (BS-side) recap, γ (body-side) candidate parametrisations evaluated empirically (figure: calibration recovery), K_99 SVD picked, IMU pose error as one component γ absorbs |
| VII | Pose-differentiable rate + App UX | **1.5** | Cascaded SINR, ∇θ R, gradient-with-feedback metal-detector UI, one-shot fails / closed loop succeeds (figure: convergence demo) |
| VIII | Numerical study | **2.0** | Plaza window-side seated user; SMPL-X mesh; 3 figures: (a) hero pose sweep with SINR/rate/Sab triple-axis, (b) the convergence demo, (c) live SAR receipt heatmap |
| IX | DTN architecture | **1.0** | Block diagram, bandwidth budget, refresh cadences from v5, where the loop sits in the radio stack (CFP keywords concentrated here) |
| X | Discussion | **0.75** | Privacy delta, bystander handling, scaling, sub-6 GHz pointer |
| XI | Conclusion | **0.25** | Two-sentence wrap |

Rule of thumb: every section that has a derivation in main text has a "complete derivation" companion in SI (II→app, III→app, IV→app, V→app, VI→app). Main text only gives the boxed result + 1-sentence sketch + figure. The reader who wants the full derivation reads the SI; the reviewer who reads only main text gets the spine.

### What goes in appendices (printed with the paper, contributing to main page count)

The IEEE Trans appendix-vs-SI line is:
- **Appendices** = part of the typeset paper, count toward the 18p limit. Reserve only for short proofs essential to a main-text claim.
- **SI / "supplementary materials"** = separate downloadable PDF, no length limit, peer-reviewed alongside.

JSAC reviewers read the main text + appendices; they spot-check SI. So we use appendices only for things that gate trust in a main-text proposition, and dump everything heavy into SI.

| Where | Content | Size |
|---|---|---|
| App. A | Per-path Fresnel transmission operator F_n (1 page proof) | 1 pp |
| App. B | Approximations 1 & 2 error budget (table + 1 paragraph each) | 1 pp |
| App. C | Identifiability proof for K-mode SVD calibration | 0.5 pp |

### What goes in the SI (no length limit)

The SI is where we earn "but it's complete." Targets approximate:

| Section | Content | Length |
|---|---|---|
| SI A | Full Maxwell → PO derivation, polarisation-aware Stokes vector, curvature correction, GELU diffraction smoothing, inter-body radiosity (lifted from TAP paper) | 6 pp |
| SI B | Layered skin model for sub-6 GHz (Chew recursion, Fabry-Pérot), with frequency sweep | 3 pp |
| SI C | Compliance metrics: SARwb / psSAR10g / peak-local APD with definitions and which one binds at which frequency | 2 pp |
| SI D | Calibration recovery experiment: full SNR×K table, Tier D vs Tier C vs Tier B(K), close-BS vs far-BS regimes | 4 pp |
| SI E | SVD spectrum sweep across BS distances, regime-transition diagnosis | 2 pp |
| SI F | UE-anchored render complexity argument: backward path tracing big-O analysis, why forward radiosity loses | 2 pp |
| SI G | Bandwidth and compute budgets in detail (per-component refresh cadences, FLOPs, on-device feasibility) | 2 pp |
| SI H | Virtual-IMU model (lift JSAC v5 §V.A), IMU sensitivity sweep figure with the new γ-corrected closed loop overlaid | 3 pp |
| SI I | Connection to the v5 line of work: β calibration parallel, ECBF precoder review, plaza-scale evaluation | 2 pp |
| SI J | Notation and acronym summary, glossary | 1 pp |
| SI K | Full pose-sweep numerical tables (3 regimes × yaw grid) | 2 pp |
| **SI total** | | **~30 pp** |

JSAC SI peer-reviewed alongside main paper. Plenty of CFP-relevant homes here for the "we did the full Maxwell" defence.

---

## 4. Section ordering inside the paper

Two natural orderings, each with trade-offs:

**(A) Physics-first (what v4 does).** Fresnel → Body PO → Q_abs → Kirchhoff render → Closed loop → Rate → UX → Eval. Cleanest for a theory reviewer. Risk: the JSAC reviewer skims, gets to §IX before seeing the DTN framing, and parks the paper as "another SAR paper."

**(B) DTN-architecture-first [recommended].** §I Intro + §II "The body twin as a wireless-native DT" (one-page architectural diagram with the closed-loop block), then §III physics, §IV Q_abs + receipt, §V Kirchhoff h_body, §VI closed loop, §VII rate + UX, §VIII numerical study, §IX discussion + conclusion. The reader sees the DTN frame on page 2; the physics is in service of the architecture, not vice versa. CFP-aligned.

Recommend **(B)**. The block diagram is the reader's anchor. Same content, different ordering. ~1 day to re-shuffle.

---

## 5. The Thelonious-vs-SMPL-X decision

**Decision: re-render with SMPL-X for all paper figures. Keep Thelonious for compliance-metric validation only (in SI C).**

Rationale:
- SMPL-X is differentiable — `θ → mesh` is the gradient that ∇_θ R rides. Without SMPL-X the App UX section is incoherent.
- Thelonious is FDTD-validated (Sim4Life / TAP paper), but our pose-differentiable claim does not need FDTD validation; it needs the PO-Kirchhoff regime, where SMPL-X serves perfectly.
- The compliance numbers (SARwb, psSAR10g) ride on Thelonious in the SI for traceability — that's where FDTD validation matters, not in the rate figures.
- Cost: 1 day to re-run pose_sweep + animate_pose + svd_spectrum + calibration_run with SMPL-X. The Kirchhoff primitive is mesh-agnostic; only the mesh loader changes.

The path: `JSAC2/code/scene_smplx.py` wraps `aegis.geometry.parametric.ParametricBody.from_pretrained("smplx")` and exposes the same `(yaw, world_centroid)` API as `make_body`. Then re-render every figure.

---

## 6. The TikZ flowchart and the IIIa "physics in one figure" gambit

Lift the TAP-paper flowchart at `papers/TAP_paper/paper.tex:326-441`. It does in one figure what 4 pages of derivation can't: shows the reader how *every* compliance metric drops out of the *one* per-triangle PO law via three named approximations (three conditions → unpolarised → pseudo-Brewster). For JSAC2 we adapt by:

- Top spine unchanged: Exact → Unpolarised → Geometric → Whole-body
- Sub-6 GHz branch unchanged: Geom + layered T_lay
- Right-side outputs box: keep APD, SAR10g, SARwb (compliance), but **add a parallel forward branch** "Geometric → Kirchhoff Render → h_body → SINR → Rate" so the reader sees in one figure that SAR receipt and rate optimisation are two outputs of the same machinery.
- Bottom: Inputs box stays (tissue ε, normals, k̂, V, S_inc) + add "BS path dict J" + "UL pilots" as the closed-loop inputs.

This is **the** figure the JSAC reviewer remembers. Make it § II (Architecture), full-column.

---

## 7. Code work that's still to do

Sorted by load-bearingness for the paper:

| # | Task | Load-bearing for | Effort |
|---|------|---|---|
| 1 | SMPL-X swap in `pose_sweep.py` + re-render fig1, fig1b, GIF | All hero figs | 1 day |
| 2 | Closed-loop convergence demo (`closed_loop_descent.py`) → new fig5 | App UX section §VII | 2 days |
| 3 | Live SAR receipt visualisation: per-triangle Sab on SMPL-X, time-integrated dose number → new fig6 | §IV / §VIII | 2 days |
| 4 | DTN architecture TikZ diagram (LaTeX, no code) | §II | 1 day |
| 5 | Adapted TAP flowchart TikZ for §II | §II | 0.5 day |
| 6 | IMU sensitivity re-run with γ-corrected closed loop overlay → SI H fig | SI H | 1 day |
| 7 | Bandwidth/compute table refresh from current code timings → §IX | §IX | 0.5 day |
| 8 | Plaza-scale numerical study (one served user, café-window-style) replacing pure synthetic geometry | §VIII headline | 3 days (optional, see §10 below) |
| 9 | Re-tune scene_loss to reflect Brussels Grand Place LOS path attenuation realistically | §VIII | 0.5 day |
| 10 | New: peak-local APD computation on a 4 cm² surface average above 6 GHz | SI C | 0.5 day |

**Total optimistic effort: ~12 days of focused work** (matches the deadline if we start now).

---

## 8. Risks and decisions still to make

- **Page count risk.** 14 main + 4 appendix = 18 pp matches the JSAC hard cap exactly. Any spillover and we lose IIIa or the DTN diagram. Mitigation: write the SI first, then trim main text to fit by deferring proofs to SI. Aim for 13 pp main + 3 pp appendix = 16 pp typeset, leaving 2 pp slack.
- **The IMU section placement.** Decision made: short subsection in §V (telemetry sources, lift verbatim), long IMU sensitivity sweep in SI H. Rationale: the JSAC v5 paper *was* about IMU-pose-aware compliance precoding; here IMU is one input of many, not the headline. Keeping it terse in main text avoids re-litigating v5.
- **What we are NOT doing.** No multi-user / cooperative scenario (excised per user feedback, single-user only). No FDTD re-validation (TAP paper handles it). No real ray tracer (use analytical multipath + Kirchhoff render). No multi-frequency sweep in main text (sub-6 GHz lives in SI B). No semantic-foundation-model angle on the dose receipt (would be tempting CFP-bait but is scope creep; we let the SAR-receipt-as-semantic-feedback land naturally in the discussion).
- **Title.** Working title: "Reflective Intelligent Human Bodies: A Closed-Loop Body Digital Twin for Application-Aware mmWave Capacity and Live SAR Receipts." Alt: "User-as-RIS, Twin-in-the-Loop: A Closed-Loop Body Digital Twin..." First fits the CFP keyword "application-aware" + "closed-loop" + nods to RIS without misappropriating the term. Decide before submission.
- **Author list.** Currently single-author (Robin). v5 was also single-author. Decide whether to invite a co-author from the AEGIS-spinoff cofounder side or keep single-author for IDF / IP-sensitivity reasons.

---

## 9. The numerical example through the CFP lens

The CFP scope sentence: *"DTNs act not merely as digital representations but as intelligent agents that dynamically reconfigure wireless resources in response to evolving application requirements, sensor inputs, and environmental conditions."*

Our numerical example must demonstrate every italicised noun:
- **Intelligent agent**: the on-device body twin selects pose suggestions via gradient.
- **Dynamically reconfigures wireless resources**: the BS sees a changed h_body and re-fits its precoder x*.
- **Evolving application requirements**: the user starts a "big download" notification — semantic application trigger.
- **Sensor inputs**: GPS + IMU pose + UL pilots cascade into the twin.
- **Environmental conditions**: the plaza scene with windowed LOS to a rooftop BS.

Figure 1 in §VIII becomes the *one figure* that shows all of these in a single multi-panel: (a) plaza top-down with BS, café, window, body trajectory; (b) Sab heatmap on SMPL-X mesh during a slot; (c) closed-loop convergence trace from cold-start pose to MCS27-cap rate over 5 iterations. Three panels, one paragraph caption, all CFP scope nouns ticked.

---

## 10. Build order and timeline (to 2026-05-01 submission)

| Week | Milestone | Deliverable |
|---|---|---|
| Week 1 (now) | Spine plan, decisions locked | This file, plus a 1-pager outline of every section |
| Week 2 | SMPL-X swap, re-render existing figs, write §II + §III | Code task 1; LaTeX §I rewritten with CFP framing; §II adapted TikZ flowchart |
| Week 3 | Closed-loop convergence demo, App UX figure | Code task 2; §VII updated |
| Week 4 | SAR receipt visualisation, plaza-scale numerical example | Code tasks 3, 8, 9; §VIII written |
| Week 5 | DTN architecture diagram, IMU sensitivity re-run, SI H | Code tasks 4, 6; SI written through §H |
| Week 6 | SI A–G drafted (heavy lifting, mostly imported from monograph + TAP paper) | SI complete |
| Week 7 | SI I–K + appendices A–C + bandwidth table | Paper feature-complete |
| Week 8 | Internal review, polish, references, abstract iteration | Submission-ready PDF |

If we start the week of 2026-05-10 and need 8 weeks, we miss the 2026-05-01 deadline by **9 days**. **Decision needed: do we** (a) **submit late** (CFPs sometimes accept up to 2 weeks past), (b) **accept reduced scope** — drop the plaza-scale §VIII demo for the synthetic-geometry version we already have, save 1 week, submit on time, or (c) **target the next CFP cycle** if the SI runs another round.

Recommend (b): the synthetic geometry already shows the full closed loop; the plaza dressing is a paper-readability improvement, not a scientific necessity. Park the plaza version for an extension (TWC or follow-up JSAC).

---

## 11. Cross-references

- v4 paper: `JSAC2/rihb_theory_v4.tex` (23 pp single-column A4)
- Old JSAC v5: `JSAC/paper/paper_jsac_v5.tex` (especially §sec:imu, §sec:cadence, §sec:eval-imu)
- TAP paper: `papers/TAP_paper/paper.tex` (especially the TikZ flowchart at line 326 and §sec:corrections)
- Monograph: `theory/monograph_v2.tex` (Approximations 1, 2 in §sec:fresnel-operator + §sec:approx2)
- Plaza scene: `JSAC/code/experiments/plaza_run/scenario.py`
- SMPL-X loader: `src/aegis/geometry/parametric.py`
- Virtual IMU model: `src/aegis/geometry/virtual_imu.py`
- Code home for new work: `JSAC2/code/`
- SI digital-twins planning: `JSAC/planning/JSAC_SI_digital_twins.md` (canonical CFP record)

End of spine plan.
