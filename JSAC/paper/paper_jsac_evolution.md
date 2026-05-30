# JSAC paper evolution: spine, sims, fit

Seven versions exist on disk, in chronological order:

1. `JSAC/planning/paper.tex` (v0a, 1222 L)
2. `JSAC/planning/paper_v2.tex` (v0b, 1334 L)
3. `JSAC/paper/paper_jsac.tex` (v1, 1369 L)
4. `JSAC/paper/paper_jsac_v2.tex` (v2, 1434 L)
5. `JSAC/paper/paper_jsac_v3.tex` (v3, 1511 L)
6. `JSAC/paper/paper_jsac_v4.tex` (v4, 1494 L)
7. `JSAC/paper/paper_jsac_v5.tex` (v5, 1981 L) — current

Length growth is real but not the story. The story is that the **spine inverts twice** along the way, and the **role of the body twin shrinks** in the version that has the strongest math. This file is about the spine, the simulations, the diffs, and the SI fit. It is not a re-summary.

---

## 1. The spine

### 1.1 What the central algorithmic claim *is* in each version

| Ver | Central algorithmic claim | What's the "thing"? |
|-----|---------------------------|---------------------|
| v0a | Closed-form ECBF: `w_k = (Σ_u λ_u Q^(u) + νI)^{-1} g_k`, generalises Ying-2015 to multi-body, reduces to ZF in rank-one limit. | The closed-form precoder. |
| v0b | Same closed-form precoder, but framed as a **DTN problem**: body is the application, twin is in the loop. | The DTN. |
| v1  | Same closed-form precoder. Body twin = 3 ingredients (Q-operator + scene path dictionary + tiered telemetry). | The body twin. |
| v2  | **WMMSE-ECBF**: outer block-coordinate descent on `(u_k, v_k)` + dual ascent on `(λ, ν)`. Adds virtual-IMU pose estimator. | A WMMSE-flavoured solver. |
| v3  | **MMSE-with-exposure** (renamed honestly per audit C1) + **dual ascent** + **primal projection** as solver-fallback safety net. | The dual-ascent solver, glued together by a projection. |
| v4  | Same as v3, tighter regime (E_RL = 3 V/m). | Same. |
| v5  | **Per-slot primal projection on regularised ZF** is the algorithm. Proposition: under MCS27 cap with SINR-margin condition, projected ZF attains the K-stream upper bound. ECBF/dual-ascent demoted to App. C, kept for two named niches (uncapped-Shannon, min-TX-power). | A one-line scaling. |

**Two inversions** along the way:

- **v1 → v2**: the precoder changed math (WMMSE adds the inter-user Gram H) — but the code never implemented WMMSE. Audit C1 caught the mismatch; v3 took Path A and rolled the math back to MMSE.
- **v4 → v5**: the precoder changed kind. From a hard QCQP solver to a one-line scaling on regularised ZF. The QCQP solver became a *baseline*, not the protagonist.

### 1.2 The body twin's role across versions

This is the diff that matters most for SI fit.

- **v0a/v0b/v1**: twin is a **controller**. Each body's Q^(u) shapes the precoder direction through its λ_u in the dual. Pose information rotates the leading mode of Q^(u), which moves the precoder.
- **v2/v3/v4**: twin is a **constraint set provider**. The dual ascent treats Q^(u) as a per-body PSD constraint and shapes around them.
- **v5**: twin is a **per-body absorbed-power estimator**. It computes P_abs^(u) so the projection can set `α = √(η_S · min_u L^(u)/P_abs^(u))`. That's it. Pose accuracy matters at sub-percent scale; "the IMU-vs-T-pose gap is the one degree of freedom the body twin buys for the dual ascent" — paper's own words (v5:1591–94). For the projected-ZF main method, the twin's role has structurally shrunk.

This shrink is the central tension the spine inversion creates. v5 is honest about it. The shrink is what makes v5 the strongest paper to a math reviewer and the weakest to a DTN-SI reviewer.

### 1.3 What survives across all seven versions

Things that look stable:

- Per-body coherent exposure operator factorisation `Q^(u) = J^T M^(u) J` (separating array hardware from body-and-scene Gram). Stable from v0a.
- The rank-one ZF degeneracy proposition (`prop:ZFlimit`). Stable from v0a; only the hosting section moves.
- Empirical effective rank 3-4 at the 99% trace fraction in both plaza-specular and 3GPP UMa-LOS path models. Stable from v1 onward (numbers don't move).
- Cauchy bound tightness experiment: 21–27 dB slack on LOS steering, 49–70% violation by random/ECBF precoders, +2.86 to +6.34 dB median ratios. Stable from v1; verified against `cauchy_tightness/summary.json`.
- Tiered telemetry: tier-A served users, tier-B cooperating non-users, tier-C ISAC bystanders. Stable from v0a; tier-D undetected occupancy added in v4.
- 7.5 ms per-body GPU Q-refresh. Stable from v0b.

Things that moved a lot:

- The headline empirical metric (slack regime ECDF tier ratios → binding regime violation rates → MCS-cap saturation).
- The wall-clock claim (31 ms in v1 → 350 ms in v3/v4 for the dual ascent → 0.5 ms in v5 for projected ZF).
- The chronic-dose value pitch (qualitative tier separation in v1 → quantitative 37%/2.6× tightening in latest v5 commit `67b0f913`).

### 1.4 What got dropped without replacement

- **Pseudo-Brewster coupling** subsection (v0a §II.E "Pseudo-Brewster coupling to backscatter" + §V.E "Pseudo-Brewster duality as a sensing aside"). Gone from v1 onward. Was a sensing-side hook on the rank-deficient body coupling. Either move it to the companion paper or accept it's gone.
- **Pose-information gain in dB** (v0a/v0b ablation). v5 has a `pose_info_gain` figure but no longer in dB; it's a violation-rate ablation. The dB framing was clearer.
- **Cooperative multi-operator aggregation** (v0a §III.E). Mentioned in v5 discussion as a future direction. Probably the right call.
- **Operator multiplicity ablation** (v0a §VI.E). Gone. The cumulative-cap framing in the abstract is now unsupported by an experiment.

---

## 2. The simulations

### 2.1 What changed in the sim stack

| Ver | Production data | Trace length | Regime | Wall-clock |
|-----|-----------------|--------------|--------|------------|
| v0a | TODO/placeholders. | 5 min target | undefined | undefined |
| v0b | Binding envelope: r* = 13 m at K=1, 2.7 m at K=25 (4-operator MRT, 55 dBm) — back-of-envelope only. Explicit hedge: "if MRT doesn't violate, fall back on chronic dose." | TODO | binding-by-construction at near-BS | TODO |
| v1  | 600 slots = 20 s, plaza-specular + UMa-LOS, Brussels 14.57 V/m, 30 dBm. Hero result: "5 precoders collapse to one operating point" (slack regime). | 20 s | slack | 31 ms median |
| v2  | 9000 slots = 5 min, 43 dBm, E_RL = 6 V/m. ECBF 99% feasibility / ZF 16.7% / MRT 35.1%. Abstract STILL cites 20 s window (audit R1/R2/R14). | 5 min | binding | "31 ms" still in body |
| v3  | 5 min, 43 dBm, E_RL = 6 V/m, T0 = 0.4 reconciled. Primal projection introduced (says unprojected ECBF has 92–96% solver-fallback rate). | 5 min | binding | 350 ms ECBF |
| v4  | 50 s window, 43 dBm, E_RL = **3 V/m** (Italian rural, Brussels pre-2014). Per-body budget shrinks 27.7 mW → 6.9 mW. ZF 14.6% / ECBF+proj 1.3% IMU / 0.0% oracle. | 50 s | tighter binding | same ECBF cost |
| v5  | 1500-slot trace × **K=25/10/5** × **bystander-binding geometry** + multi-seed cross-check (seed 1729) + per-tier breakdown + NF=6dB sanity + K=50 stress. MCS28 → MCS27 corrected (TS 38.214). | 1500 slots × regimes | binding | 0.5 ms projected ZF / 350 ms ECBF |

The sim stack itself improved monotonically (low-rank Q + lazy decomp + JAX vmap + warm-start λ + tuned noise regulariser). That's fine. The framing of the sim moved more than the sim moved.

### 2.2 The regime drift is a design choice, not a bug

v1 lived in the slack regime and confessed "5 precoders collapse to one operating point" — which is intellectually honest but kills the algorithmic-contribution story. v2 jumped to a binding regime by raising power 30 → 43 dBm and tightening the cap 14.57 → 6 V/m. v4 went further to 3 V/m. This is the right move for an algorithm paper, but it is a *constructed* binding regime: the worked instance is the most aggressive of four candidate configs in the codebase (`binding_43dbm_6vpm.json`, then `brussels_2007_strict.json`). Reviewers will read this as a worst-case demo, which it is. v5 partially rehabilitates it by sweeping K and constructing a bystander-binding geometry, which makes the story regime-aware rather than regime-cherry-picking.

### 2.3 The seed-1729 reversal is the most honest moment in v5

Headline of v5 §VI.D Table II: at K=25, ZF+proj (deployable) is 1.2% violation, dual ascent 2.4%. Caption says "1.05× to 19× margin on violation rate." Then prose admits: a multi-seed cross-check at seed 1729 reverses the K=25 ordering (ZF+proj 0.58%, ECBF 0.32%). They write: "the two methods are therefore statistically tied on aggregate compliance with the dual ascent showing larger seed-to-seed variance."

This is the right thing to do, and it's a flag that the v5 headline ("ZF+proj dominates ECBF") doesn't actually hold. The honest version of the v5 claim is:

> Both methods saturate the MCS sum-cap at zero violations on the detected set. The case for projected ZF over ECBF is wall-clock (~700×) and feasibility-by-construction at every slot, not a strictly tighter aggregate violation rate.

That's the conclusion the latest commit 67b0f913 ("honest chronic-dose framing") is heading toward. v5's main claim should be wall-clock, not compliance.

### 2.4 The chronic-dose value pitch has quietly collapsed

- v1 abstract: "cooperating non-users absorb 0.40× of served-user median, bystanders 0.92×." Numbers from the slack-regime 600-slot static run (audit R14/C9).
- v3/v4: kept the tier-stratified ECDF with corrected B/C ratios.
- v5 latest commit (`67b0f913`): "all compliance-aware variants (WC, projected ZF, dual ascent) clear the budget for every body in the trace. The body-twin advantage is **real but quantitative (~37% tighter median than projected ZF, ~2.6× tighter than WC), not a solve-vs-fail distinction**."

The old story was: chronic dose is where the body twin shines because instantaneous compliance is easy and the deployment value is the cumulative ratio. The new story is: every reasonable precoder clears the chronic budget; the body twin tightens the median by 37%. That's a much smaller pitch. The paper hasn't found a new value pitch to replace it — the deployment-value paragraph in §VII has been "softened" but not rewritten.

### 2.5 The MCS-cap insight is the real discovery

The single new fact v5 brings that no other version has is:

> Under the operational 5G NR FR2 rate model (per-stream MCS27 cap of 7.4 bps/Hz at 22.25 dB linear SINR), regularised ZF on a tens-of-element panel saturates the cap with ~12 dB of SINR margin. The QCQP under per-body exposure caps then collapses to a one-scalar amplitude problem: the projection scale α absorbs the worst-margin body's overshoot without dropping any served stream below the clip.

This is genuinely new. It is also the insight that makes the elaborate WMMSE/MMSE/dual-ascent machinery in v1-v4 unnecessary in the operational regime. v5 keeps the dual-ascent solver in the appendix for academic completeness and names two regimes where it still earns its keep (uncapped-Shannon, min-TX-power), which is the right scoping move.

The proposition statement is honest: it doesn't single out projected ZF as unique, only as one method that attains the K-stream upper bound. The case for *choosing* projected ZF is operational (wall-clock, feasibility-by-construction), not optimality.

---

## 3. Diffs that materially change the message

### 3.1 v1 → v2: SI keywords return, math doubles down on a wrong claim

**Good**: "Closed-Loop" goes back into the title. Virtual-IMU pose estimator added — gives the twin a deployable telemetry story. Switch to binding regime makes the algorithm matter.

**Bad**: WMMSE-ECBF framing is mathematically wrong against the code (audit C1). At this point the abstract, intro, §III, and App. B all describe a WMMSE solver that the production code doesn't run. v3 had to undo this.

### 3.2 v2 → v3: math reconciliation, primal projection introduced

**Good**: WMMSE rolled back to MMSE-with-exposure. The h_k^* RHS replaces u_k v_k h_k. App. B becomes "Weighted-MMSE generalisation" (kept honestly as an extension, not the main result).

**Bad**: §V.C primal projection is motivated as a *fix for the dual ascent's 92-96% solver fallback rate*. That's a damning admission about the dual ascent. v5 will eventually capitalise on this by noting that if projection fixes the solver, projection alone might suffice — which is exactly what happens.

### 3.3 v3 → v4: numerical regime tightening, story unchanged

**Good**: Italian rural / Brussels pre-2014 reading sharpens the binding regime. The 6.9 mW per-body budget is more credible than 27.7 mW because the latter relies on the η-bar = 0.5 and T0 = 0.4 product reconciliation that the audit (C4, R8) flagged as drifty.

**Bad**: 50-second window is a step *back* from v2/v3's 5-min run. Picked because the v6_aware NPZ was the only one with zf_proj stored at the time. Should be 5 min on the same trace.

### 3.4 v4 → v5: algorithmic inversion + math wins + twin loses

**Good**:
- The MCS-cap proposition is the strongest new theoretical result in the lineage.
- ECBF demoted with named use cases: clean scoping.
- Head-to-head subsection with K-sweep + bystander-binding geometry + per-tier breakdown.
- Multi-seed cross-check disclosed (seed 1729 reverses K=25 ordering).
- NF=6dB sanity check, K=50 stress test — robust empirical bracket.

**Bad**:
- Title regresses to a SP-journal title ("Compliance-Aware mmWave Downlink: Per-Slot Primal Projection") with no DTN keyword.
- Body twin's role structurally shrinks to "P_abs estimator that supplies α."
- The IMU section now reads as oversold given the proposition: pose accuracy buys at most a sub-percent compliance differential under projected ZF.
- The deployment-value pitch has quietly lost the chronic-dose lever and hasn't found a new lever.
- Length growth is real (1494 → 1981 lines), and most of it is the head-to-head + extended discussion + multiple sanity checks. Not all of it survives a page-limit pass.

---

## 4. SI fit

The SI ([JSAC_SI_digital_twins.md](../planning/JSAC_SI_digital_twins.md)) is "Digital Twins for Wireless Networks: Application-Aware and Closed-Loop Optimization." Topic clusters: closed-loop optimization, application-aware design, twin-in-the-loop, semantic-aware data abstraction.

| Ver | SI keyword in title | Twin role in main result | DTN framing in intro |
|-----|--------------------|--------------------------|---------------------|
| v0a | "Body Digital Twins in the Precoder Loop" | controller | strong |
| v0b | "A Body-Twin in the Precoder Loop: **Application-Aware, Closed-Loop**" | controller | **strongest** ("body is the application", DTN explicit) |
| v1  | "Body digital twin in the multi-user mmWave precoder loop" | controller | implicit |
| v2  | "**Closed-Loop Body Digital Twins** for Exposure-Constrained mmWave Downlink" | constraint provider | implicit |
| v3  | "Body Digital Twins for Exposure-Constrained mmWave Downlink: **A Multi-Body QCQP**" | constraint provider | implicit |
| v4  | same as v3 | constraint provider | implicit |
| v5  | "Body Digital Twins for **Compliance-Aware** mmWave Downlink: **Per-Slot Primal Projection**" | P_abs estimator | absent |

The SI-fit trajectory is the *opposite* of the math-rigor trajectory. v0b had the strongest SI framing and the weakest experiments. v5 has the strongest experiments and the weakest SI framing.

The SI guest editors will look for:

1. A twin-in-the-loop architecture story. v0b/v1/v2 have one; v5 doesn't quite, because the loop is now `Q^(u) → α → ZF scaling`, which reads as a feedback gain rather than a control loop.
2. Application-aware design. v0b's "body is the application the network must serve safely" is exactly the SI's framing. v5 has lost this sentence.
3. Cross-layer optimization. v5's MCS-cap proposition IS a cross-layer optimization (PHY rate model interacts with the precoder structure), but it isn't framed as one.
4. Closed-loop optimization. v5's projection is feedback (measure P_abs^(u), set α). It just isn't called that.

So the v5 result actually maps onto SI keywords cleanly — it's a cross-layer (PHY MCS cap shapes the precoder) closed-loop (feedback on per-body P_abs measurements) optimization driven by an application-aware twin (the body). v5 just doesn't say it that way.

---

## 5. Is v5 the best across the board?

Direct answer: **no, but it is the best math-and-experiment paper, and it is the right *content* base if you re-skin it for the SI.**

| Dimension | Best version | Comment |
|-----------|--------------|---------|
| Mathematical rigor | v5 | MCS-cap proposition, ECBF correctly scoped |
| Experimental strength | v5 | K-sweep, bystander-binding, multi-seed, per-tier, K=50 stress |
| Honesty about what works | v5 | Seed-1729 reversal disclosed, chronic-dose softened, ECBF named for niches |
| Audit-issue residual | v5 | Most issues from `paper_jsac_audit.md` round 1+2 are resolved here |
| **Spine clarity** | **v5** | "Twin enables a one-line precoder under MCS cap" is the cleanest thesis in the lineage |
| **SI fit (title + framing)** | **v0b** | "Body is the application", "closed-loop DTN", "verifiable through standards-aligned audit" |
| **Twin centrality** | **v0a/v0b/v1** | Twin is a controller, not an estimator |
| **Deployment-value pitch** | **v3** | Binding regime + primal projection rescues a hard solver = real deployment story |
| **Length** | v0a/v0b | 1222–1334 lines vs v5's 1981; trim is independent of which version you base on |
| **Storytelling drama** | **v3/v4** | "Solver fails 92–96% of the time, projection rescues it" is a great narrative; v5 disowns it |

The right submission is **v5's content under v0b's framing**, with §V's proposition reframed as "the twin is what makes a one-line precoder feasible" rather than "the QCQP collapses under MCS cap." The current v5 puts the math first and the twin second; the SI pitch needs the twin first and the math as the engine that makes it deployable.

---

## 6. Concrete recommendations

In priority order:

1. **Restore a closed-loop / DTN / application-aware title.** v2 ("Closed-Loop Body Digital Twins for Exposure-Constrained mmWave Downlink") is the best title in the lineage. v0b's subtitle ("Application-Aware, Closed-Loop Exposure Control for Regulated mmWave Downlink") is a viable alternative. v5's title actively obscures the SI fit.

2. **Reframe `prop:projection-optimality` as a twin-enabling result.** Current statement: "under MCS cap with SINR margin, projected ZF attains the K-stream upper bound." Rewrite as: "the body twin's per-slot P_abs^(u) estimate is what makes a one-line precoder feasible at every slot in the binding regime; the alternative without a twin is a worst-case backoff that costs 10s of dB on α." That sentence does not currently exist anywhere in v5. Without it, the twin reads as decorative.

3. **Cut the IMU oversell.** v2-v5 all carry a Virtual-IMU subsection that promises a deployable pose estimator. Under the v5 main result, pose accuracy modulates compliance at sub-percent. Either move the IMU to a "telemetry plumbing" subsection at half the length, or push it to the companion paper.

4. **Decide what the deployment value is now that chronic-dose has collapsed.** Three candidates that v5 doesn't pick between:
   - **The α-vs-WC gap**: per-body twin estimates buy back N dB of α relative to a worst-case envelope. Quantify this.
   - **The undetected-tier-C floor**: the per-tier breakdown shows ZF+proj has 6.0% tier-C residual vs ECBF's 11.9%. Both are sensing-pipeline floors; the closed-form scaling's uniform amplitude cut is what gives ZF+proj the smaller floor. This is the cleanest "value of compliance-by-construction" story.
   - **The wall-clock**: 700× faster solver at the same compliance and rate. Most directly defensible but least novel.

5. **Keep the seed-1729 disclosure but move it to a bracketing paragraph instead of a sub-paragraph.** The honest reading is that ZF+proj and the tuned dual ascent are statistically tied on compliance. Lead with that, then say "the case for projected ZF is wall-clock and feasibility-by-construction." This is more defensible than the current "1.05× to 19×" framing in the table caption.

6. **Reconsider the bystander-binding geometry framing.** v5 constructs a geometry where served are at 25–50 m and the 35 non-served bodies cluster at 5–12 m. ZF+proj still wins, by 0.5 ms vs 19 ms wall-clock. But the geometry is hand-constructed to test when the dual ascent should win. A reviewer will read this as a stacked deck. Either add an OSM-realistic bystander-binding scenario (auditorium, bus stop) or remove the synthetic geometry and lean on the K-sweep alone.

7. **Length: cut ~400–500 lines from v5 by:**
   - Compressing the IMU subsection (item 3 above).
   - Compressing App. C ECBF derivation (it's an app, not a competitor).
   - Folding the head-to-head's three-paragraph mechanism explanation into one paragraph + the table.
   - Compressing the discussion's six limitations (most are well-handled; some are repeats of audit items).

8. **Reinstate a one-paragraph DTN/SI framing in the intro.** v0b had "the JSAC DTN special issue's thesis is that future wireless networks are not the thing being twinned — they are the adaptive substrate over which twins of the application run a closed control loop. This paper addresses an application that has hitherto been absent from the DTN literature: the human body in the coverage cell." That paragraph is the SI pitch in two sentences. v5 has nothing equivalent.

---

## 7. The one-line summary

v5 is the right base. It needs v0b's framing wrapper, v2's title, a reframe of the main proposition that puts the twin first, a replacement for the chronic-dose value pitch, and ~400 lines of trim. The math and the experiments are there. The SI fit is not.
