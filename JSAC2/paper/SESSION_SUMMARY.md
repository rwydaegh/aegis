# Session summary — JSAC2 v1 paper draft

**Outcome:** First true IEEE 2-column draft compiles to **12 pages** at `/home/user/aegis/JSAC2/paper/jsac2_v1.pdf` with 8 figures wired in, all numerical results from completed agents folded in, and only a few placeholders remaining (reachability/failure-mode subsections + appendices A/B/C, all flagged as TODO boxes).

## Paper file

`/home/user/aegis/JSAC2/paper/jsac2_v1.tex` — IEEE Trans 10pt twocol, 12 typeset pages.

Section order (classical IEEE / IMRAD-adjacent):
- I. Introduction (mutant 6-beat: tech setup, mmWave deployment frictions, body-twin SoTA, three-gap statement, this-work + numbered novelty enumerate)
- II. System model and DTN architecture (with **Fig 1**: closed-loop block diagram)
- III. RIHB physics (with **Fig 2**: incidence-plane geometry, lifted from theory/figures)
- IV. UE-anchored Kirchhoff render (with **Fig 3**: per-triangle render schematic)
- V. Closed-loop calibration (γ-corrected IMU numbers folded in: 1.06% violation at σ=4° vs 2.47% uncalibrated)
- VI. Pose-differentiable rate + human-in-the-loop control (with **Algorithm 1**: K-iter UL-corrected gradient descent)
- VII. Numerical study (with **Fig 4**: hero pose before/after + SINR trajectory; **Fig 5**: existence sweep across regimes; **Fig 6**: per-joint sensitivity; **Fig 7**: comfort-vs-rate Pareto; reachability + failure-mode subsections still TODO pending the in-flight reachability agent)
- VIII. Live exposure reading + connection to RF-EMF cohort studies (with **Fig 8**: baselines comparison; **Fig 9**: 3-panel SAR reading visualisation; CLUE-H + COSMOS + HERMES + van Wel cited as placeholders)
- IX. Discussion (bandwidth+compute table, privacy delta, limitations, future work)
- X. Conclusion (folded in headline numbers)
- Appendices A/B/C: TODO

## Completed agent work

| Agent | Output | Key number |
|---|---|---|
| SMPL-X integration | `scene_smplx.py`, `pose_sweep_smplx_*.npz`, `anim_pose_sweep_smplx.gif` | 21.3 dB SINR variation in NLOS regime |
| Peak-local APD | `peak_local_apd.py`, `peak_local_apd_*.npz` | **0.58% of ICNIRP limit at 43 dBm / 30 m** |
| IMU γ-overlay | `imu_gamma_overlay.{npz,pdf,png}` | γ-corrected closed loop dominates dual-ascent at all σ; 1.06% vs 2.47% at σ=4° |
| Existence sweep (200 scenes from AMASS) | `existence_sweep.npz`, `fig_existence.{pdf,png}` | 26-49% of scenes admit ≥6 dB pose-bounded gain |
| Per-joint sensitivity (50 AMASS poses) | `fig_per_joint_sensitivity.{pdf,png}` | Top-6 torso joints carry >80% of gradient mass |
| Comfort-vs-rate Pareto | `fig_comfort_pareto.{pdf,png}` | 6 dB gain at 1 comfort unit; saturates at 9.6 dB above C≈3 |
| Baselines comparison | `baselines.npz`, `fig_baselines.{pdf,png}` | RIHB +7.1% over no-twin MRT in binding regime; +13.8% in NLOS |
| Live SAR reading viz | `fig_sab_receipt.{pdf,png}` | 30-s dose distribution sits 12× below ICNIRP equivalent |

## Still in flight

- **Reachability sweep** (in background): K-iter gradient descent success rate vs (K, UL-SNR, IMU σ) on existence-positive subset. Will produce `fig_reachability.{pdf,png}` and an updated `agent_existence_reachability.md` log when done. Will need a small failure-mode classifier downstream.

## Outstanding items (TODOs in red boxes)

- §VII.E Reachability subsection (waiting on agent)
- §VII.F Failure-mode taxonomy subsection (downstream of reachability)
- App. A Per-path Fresnel transmission operator (1 pp distillation from monograph)
- App. B Approximations 1+2 error budget (table from monograph)
- App. C Identifiability proof (½ pp standard truncated SVD argument)
- Bibliography fact-check: CLUE-H, van Wel, Chen-Saad-Mozaffari-Hashash DTN refs are placeholders marked **[verify at draft-review]**
- Title: current "Reflective Intelligent Human Bodies: A Closed-Loop Body Digital Twin for mmWave Capacity and Live Exposure Readings" — receipt → reading swap done, exposure features

## Style sweep notes

- "receipt" → "reading" — global swap done (~30 instances)
- imaginary unit `i` → `j` (engineering convention) — done
- Equation termination `\,.` / `\,,` inside equation env — partially done; could do another sweep
- `~` before all units — done in new content; existing equations partially covered
- Glossaries package — NOT applied yet (per Robin "not focus right now")
- Cheeky RIHB joke neutered to single deadpan acronym sentence with "intelligence" in setup
- "We adopt RIS lingo... informal" introspective meta-commentary — removed
- Stakeholder paragraph — not added (per Robin's call)
- No separate Related Work section — DTN refs folded into intro paragraph
- No separate regulatory subsection — Brussels/Italian/Geneva referenced inline as "look how bad it is"

## Structure reflection

Saved at `/home/user/aegis/JSAC2/paper/STRUCTURE_REFLECTION.md`. Robin's 4 batched answers to the structural decisions are baked in; one tweak applied (IMU detail moved from §II.B to §V); two tweaks deferred (§V+§VI merge possibility, §VIII subsection re-ordering).

## Figure quality

All figures rendered with TAP-paper visual standard via `theory/scripts/_plot_style.py` (`apply_monograph_style(mode='png')` + `fig_size_ieee(columns=N, aspect=...)`). Multiple iteration passes applied to:
- DTN architecture (TikZ): v1 → v3 (dropped redundant labels, color-coded headers, dashed return arrows)
- Hero pose before/after (matplotlib): v1 → v3 (switched regime to NLOS for max contrast, brightened colormap, 3-panel layout with SINR trajectory)
- Kirchhoff schematic (TikZ): v1 → v2 (removed equation overlap, body-shaped silhouette)

Each figure was reviewed as PNG with critical pass and iterated. Spec from `papers/how_to_write_good/figures_extreme_quality.md` followed: minimum information, open markers, sentence-case captions, units in brackets, legend in 1pt rectangle, color-blind friendly palette.

## What needs Robin's eye on return

1. Confirm reachability + failure-mode sections when agent finishes (in next ~30 minutes)
2. Verify CLUE-H + van Wel + Chen-Saad-Mozaffari-Hashash citations
3. Title decision: keep current vs. shorten further
4. App A/B/C: I can fill these by lifting from monograph if you want, or you can do at draft-review
5. Whether to re-iterate any specific figure that you find too busy or too plain
6. Bandwidth/compute table numbers (currently rough order-of-magnitude estimates from prior code timings)
