# Self-reflection on jsac2_v1.tex structure

## Current shape (8 pages compiled)

```
I.    Introduction (4-paragraph template; cheeky RIHB; contributions table)
II.   System model and DTN architecture
III.  RIHB physics: per-triangle Fresnel and the body-PO scatterer
IV.   UE-anchored Kirchhoff render of the body channel
V.    Closed-loop calibration: UL pilots and γ
VI.   Pose-differentiable rate and human-in-the-loop control
VII.  Numerical study: existence, reachability, failure modes
VIII. Live SAR receipt and connection to RF-EMF cohort studies
IX.   Discussion (bandwidth, privacy, limitations, future work)
X.    Conclusion
App. A. Per-path Fresnel transmission operator
App. B. Approximations 1 and 2 error budget
App. C. Identifiability of K-mode SVD calibration
```

This is **classical IEEE Trans / IMRAD-adjacent**:
intro → system model → physics → method → algorithm → numerical → application → discussion → conclusion. Robin's stated preference.

## Verdict

**Structure is right. Small tweaks only.**

## What works (don't touch)

- **§I 4-paragraph opening** lands cleanly on the rendered page: punch ¶1, DTN bridge ¶2, cheeky RIHB ¶3, contributions ¶4.
- **§II → §III ordering** (architecture before physics) is correct for JSAC. The DTN framing wins page 2; the physics earns its keep in service of the framing. Reverse order would suit a TAP submission, not this one.
- **§III → §IV ordering** (physics before Kirchhoff render) is correct: per-triangle PO law has to land before the integral that consumes it.
- **§IV Kirchhoff render as the load-bearing technical contribution** reads cleanly. The complexity argument as a Proposition is the right rhetorical weight.
- **§VII as a three-question study** (existence / reachability / failure) is the strongest framing. It converts the convergence claim from advocacy to empirical contribution.
- **§VIII Receipt placed after the rate-optimization cluster** clusters all rate material (§IV-VII) together and lets the receipt land as its own self-contained second contribution. Counterargument considered (place receipt right after §IV) and rejected.
- **Contributions table on p.2** does the at-a-glance work the reader expects.

## Tweaks worth making

### Tweak 1 (applied): Move IMU pose-error detail from §II to §V

Currently §II.B has the full IMU error model with eq:imu-pose (lag + drift + white). This is a sensor model, not a system-model element. It belongs in §V where the body-side calibration γ absorbs it. §II should just say "pose comes from IMU + UL pilots; the IMU model is in §V/SI."

Effect: §II becomes tighter (architecture-only), §V gets the input it needs to motivate the residual decomposition naturally.

### Tweak 2 (deferred): Consider merging §V and §VI

Both sections are about the closed loop — §V is the BS-side calibration, §VI is the user-side control. Could merge as one §V "Closed-loop calibration and pose-differentiable control" with two subsections.

**Pro**: tighter narrative, fewer top-level sections (9 instead of 10).
**Con**: blurs the distinction between two distinct contributions (calibration is a regression problem; control is an optimization problem). JSAC reviewers usually want clear method-section separation.

**Verdict**: keep separate for v1. Reconsider after the convergence-study agent results are in — if the calibration story turns out to be one-paragraph rather than one-section, fold into §VI.

### Tweak 3 (deferred): Receipt subsection ordering

§VIII currently goes: what / why-not-done / cohort connection. Consider re-ordering as: what (computation, paragraph 1) / cohort connection (the punch, paragraph 2) / why-not-done (closing observation, paragraph 3). Lifts the CLUE-H link earlier and answers "why is this in this paper" sooner.

Pending Robin's CLUE-H reference; will revisit when fleshing out.

## Count of placeholders

13 `\limbo{}` blocks. Their breakdown by what unblocks them:

| Blocked on | Count | Items |
|---|---|---|
| SMPL-X agent (running) | 4 | §VII setup, existence figure, reachability figure, per-joint sensitivity figure |
| Failure-mode classifier (depends on SMPL-X + reachability) | 1 | failure-mode taxonomy figure |
| Comfort-Pareto agent (depends on SMPL-X) | 1 | comfort-vs-rate Pareto figure |
| Baselines agent (depends on SMPL-X) | 1 | baselines comparison table |
| IMU agent (running) | 0 in main text, 1 in §V cross-ref | already covered by SI H pointer |
| Bandwidth/timing data | 1 | §IX.A bandwidth table |
| Receipt-viz agent (after SMPL-X) | 0 in main, used in §VIII figure |
| Robin's CLUE-H reference | 2 | §VIII paragraph 3, SI K |
| Paper-writing (no code dependency) | 4 | §II.D DTN-lit positioning, §V.C closed-loop paragraph, §VI.C semantic-feedback paragraph, §VIII paragraph 3, app A/B/C content, abstract numerical-study placeholder, conclusion numerical paragraph, references list |
| TikZ diagram (paper-writing) | 1 | §II.C closed-loop block diagram |

Net: ~7 are paper-writing tasks I can do without further data; ~6 are blocked on agent runs.

## Page count projection

- v1 compiled: **8 pages** with all placeholders rendering as boxes
- Placeholders → real text + figures: **+3-4 pages** (each figure ~0.5pp, paragraphs ~0.3pp)
- Final estimate: **11-12 pages typeset** + ~1.5 pp refs = **12.5-13.5 pp total**, comfortably under JSAC's 14 pp soft cap

## Open structural questions (no immediate answer needed)

1. Should the IMU sensitivity sweep figure live in main text §V or only in SI H?
2. Should the closed-loop block diagram in §II be one figure or two (one architecture, one timing/cadence)?
3. Should §VII present existence/reachability/failure as three subsections (current) or as a single "convergence study" subsection with three sub-subsections?
4. Should the contributions table (Table I) live in §I or be moved to §II as a system-overview table?

I'd default to keeping current choices unless the evidence-from-figures suggests otherwise.
