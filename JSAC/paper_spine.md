# The paper, plain language

*Zooming out after round 3 + agent results. No formulas unless essential.
The goal: make every ingredient's job obvious, and kill anything that's
there for no reason.*

## 1. You were right on the NN — it's a distractor

You wrote: *"you can go from pose to ACS instantly, right? That's the whole
point. It's just a matter of a lookup table, frankly."*

Yes. ACS from pose is a **deterministic function**: AEGIS Part I does it in
closed form once you know the body mesh, its normals, and the incident
direction. Pose → mesh is closed-form (SMPL-X is just linear-blend
skinning). So pose → ACS is a direct computation, not a learning problem.

The GPU benchmark confirms this is cheap at pose cadence: 7.5 ms per body
at SMPL-X triangle count (~2.4 k tri), 66 ms at full Thelonious (~25 k
tri). For 50 bodies and 100 ms pose refresh, a vmap + factored-Fresnel
fix gets us under 100 ms cleanly. **No NN needed between pose and ACS.**

Where I was sloppy: I was conflating two different problems and calling
them both "the pose NN":

| Problem | Where it lives | What actually solves it |
|---|---|---|
| IMU → pose reconstruction | Tier-A/B body's own phone, firmware | Madgwick / VQF / a small inertial-mocap net. Already solved in the sensor-fusion literature. Cite, don't invent. |
| Pose → ACS | Network-side twin | Direct AEGIS evaluation. No ML. |

I had a paragraph in §IV advertising a "small NN surrogate
$\sigma_\phi(\theta)$". Kill it. The paper cites the inertial-mocap
literature for IMU → pose, then says "with pose in hand, ACS is a direct
AEGIS evaluation at pose-refresh cadence." Cleaner and honest.

**Action:** §IV of `paper.tex` gets simplified. Remove the NN paragraph.
Keep the Cauchy worst-case paragraph for tier-C bodies (no telemetry).

## 2. How the BS learns the "angle of attack"

This is the question I never answered clearly. Let me split it.

**Two different angles, only one matters for exposure.**

- **UE-side AoA** — direction from which the body sees the beam. This is
  what you'd worry about at the UE: "what direction is the RF coming
  from." *We do not need this.*
- **BS-side AoD** — direction from which the BS radiated the path that hit
  the body. This is what exposure-constrained beamforming cares about,
  because the precoder $\mathbf{w}$ applies to the BS array and has to
  know which BS-side directions to null or budget. *This is what we need.*

**How the BS gets BS-side AoD for every body:** the BS runs its own ray
tracer on a scene model (OSM buildings + ground + body positions) and
reads off the departure direction(s) toward each body. The BS does not
need the body to tell it anything about angles; the BS already knows its
own geometry and its own scene. The only thing it needs from the body is
**position**.

So the real question is **how does the BS know position**, and here the
three tiers diverge:

| Tier | What the BS knows | How |
|---|---|---|
| A: served user | Position, pose | UL CSI + MNO location services + phone IMU streamed over MNO app |
| B: cooperating non-user (phone on, registered, no active traffic) | Position, pose | Same — UL pilot gives coarse location, MNO app streams IMU |
| C: bystander (airplane mode / no phone) | Position only | Monostatic RCS return on BS aperture (ISAC); pose falls back to Cauchy worst case |
| "Tier D": regulator-defined occupancy envelope | Envelope of where bodies could be | Ordinance-level, not a sensing tier |

Rank-check agent output reinforces this: the empirical rank of
$\mathbf{Q}^{(u)}$ in the plaza LOS regime is 3–4, which is roughly the
number of distinct BS-side directions (LOS + ground + a couple of
facades). The rank of $\mathbf{Q}^{(u)}$ is **set by how many BS-side
angles illuminate the body**. That's the "angle of attack" quantity,
supplied by the BS's own ray tracer.

**Pose** enters as a scalar multiplier of the operator's magnitude in
that regime — the ACS modulates how much of each BS-side ray the body
actually soaks up. Position + ray tracer give the directions; pose gives
the cross-section per direction.

**Position sources, honestly:**

- Tier A/B position is 3GPP-standard. Nothing to engineer.
- Tier C position via ISAC RCS is what agent prompt 01 is checking.
  Expected answer: standard monostatic radar gives position + angular cell
  (~6° azimuth on an 8×8 at 26 GHz, ~5 m resolution at 50 m range). That's
  enough for the BS ray tracer to know "there is a body in this angular
  cell at this range."
- "Tier D" (undetected) is the regulator-assumed occupancy envelope:
  the fallback is "assume the worst in the public region the BS cannot
  sense" — classical exclusion zone applied only to the occupancy-
  indeterminate part of the cell.

## 3. The spine of the paper, in prose

**The problem.** City-level EMF reference-level caps (Brussels
14.57 V/m outdoor, equivalent in Italy and Geneva) are 10–30× tighter
than ICNIRP and are the real blocker to mmWave downlink deployment in
those jurisdictions. The cap is a free-space proxy for tissue absorption
on actual bodies; the gap between the proxy and the physical quantity it
bounds is the capacity operators currently discard.

**The move.** Place a digital twin of every body in the cell inside the
base-station precoder. Each body contributes one coherent exposure
operator (a $64 \times 64$ Hermitian PSD matrix at an 8×8 panel). The
precoder maximises sum-rate while keeping every body's absorbed power
under its regulatory budget. Classical zero-forcing is the rank-one
degenerate case — so the algorithm is a drop-in replacement, not a new
solver to engineer.

**Why a twin.** Because the bodies being constrained include *bystanders*
the BS doesn't serve. The BS has no uplink from them. Their constraint
has to come from somewhere; that somewhere is the twin, populated from
(i) phone telemetry for cooperating bodies and (ii) monostatic ISAC
detection + Cauchy worst-case pose for the rest.

**Why it closes the loop.** Position, pose, and scene refresh at their
native rates; the operator $\mathbf{Q}^{(u)}$ inherits the rate of the
slowest refresh; the precoder re-solves every slot. No human in the
loop, no offline compliance simulation, no hand-tuned exclusion zones.

**Why JSAC DTN SI.** The SI's thesis is "networks as substrate, twins
as closed-loop controllers for application-aware operation." The
application here is tissue-protection compliance. None of the ten
representative papers twins the body.

## 4. The ingredient pyramid — every block has a job

```
                 ┌─────────────────────────────┐
                 │ Compliance-aware sum-rate   │
                 │ (the outcome)               │
                 └──────────────▲──────────────┘
                                │
            ┌───────────────────┴───────────────────┐
            │ Multi-body exposure-constrained       │
            │ precoder  (§III)                      │
            │ - closed-form, ZF is its rank-1 limit │
            │ - needs {Q^(u)}_u, {h_k}_k, {L^(u)}_u │
            └─────────────────▲─▲───────────────────┘
                              │ │
                ┌─────────────┘ └──────────────────┐
                │                                  │
 ┌──────────────┴──────────┐       ┌───────────────┴──────────┐
 │ Per-body Q^(u)  (§II)   │       │ Per-body budget L^(u)   │
 │ built from:             │       │ from:                    │
 │ - path set via BS       │       │ - ICNIRP BR (5.6 W WB)   │
 │   ray tracer (§V)       │       │ - Brussels RL (0.19 W)   │
 │ - pose for ACS per path │       │ - min() binding          │
 │   (§IV)                 │       └──────────────────────────┘
 └─────▲─────────▲─────────┘
       │         │
       │         │
 ┌─────┴───┐  ┌──┴───────────────────┐
 │ Path    │  │ Pose                 │
 │ set     │  │ - Tier A/B: IMU→pose │
 │ from BS │  │   via MNO app        │
 │ RT on   │  │ - Tier C: Cauchy     │
 │ scene   │  │   worst case D≤2    │
 │ model   │  └──────────────────────┘
 └────▲────┘
      │
 ┌────┴──────────────┐
 │ Position          │
 │ - Tier A/B: 3GPP  │
 │   + MNO location  │
 │ - Tier C: RCS ISAC│
 │ - Tier D: env. of │
 │   undetected      │
 └───────────────────┘
```

Reading upward: position → (path set + pose) → $\mathbf{Q}^{(u)}$ →
precoder. The twin is the composition of the bottom four boxes.

## 5. What the experiment actually runs

**Setup:** single $8\times 8$ BS panel at 26 GHz on a building facade
overlooking a plaza approximating Brussels Grand Place. Fifty bodies
split roughly 25 / 15 / 10 across tiers A, B, C. Five minutes of wall-clock
simulation, real-time-in-silico on a single GPU. Pose trajectories from
AMASS walk-cycle mocap, one per body, at 30 Hz. IMU virtualised from
ground-truth kinematics with an ICM-20948 noise model.

**The ingredients in one run:**

| Refreshed | Cadence | Source | Consumed by |
|---|---|---|---|
| CSI $\mathbf{h}_k$ | 1 ms | 3GPP pilot from served UEs | precoder solve |
| Precoder $\mathbf{w}_k$ | 1 ms | closed-form $(Q_{\mathrm{tot}}+\nu I)^{-1}\mathbf{g}_k$ | transmit |
| Position $\mathbf{t}_u$ | ~1 s | IMU+GPS (A/B) or ISAC (C) | BS ray tracer |
| Ray set per body | ~100 ms | BS-side ray tracer on OSM scene | $\mathbf{Q}^{(u)}$ |
| Pose $\bm\theta_u$ | ~100 ms | phone IMU (A/B) or Cauchy (C) | $\mathbf{Q}^{(u)}$ |
| $\mathbf{Q}^{(u)}$ | ~100 ms | AEGIS direct evaluation | precoder solve |
| Scene 3D | static | OSM + 3D Tiles | BS ray tracer |

**What we measure:**

1. Per-body exposure CDF vs. regulatory budgets $L^{(u)}_{\mathrm{BR}}$
   and $L^{(u)}_{\mathrm{RL}}$.
2. Violation rate at the Brussels RL (should be zero under our precoder
   in configurations where MRT or plain ZF violates).
3. Served sum-rate vs. baselines: MRT / ZF to users / worst-case power
   back-off / pose-known oracle / ours.
4. Pose-information gain: how much of the oracle's sum-rate margin does
   tier-A/B pose telemetry recover? (Honest possible answer: 0.5 dB.
   That would not kill the paper — it means Cauchy worst case does most
   of the work and pose is a small bonus.)
5. Rank spectrum of $\mathbf{Q}^{(u)}$ — *already measured*, median 3–4 in
   the LOS plaza regime, validating the "rank-few" observation in
   Remark 4.5.
6. Wall-clock per Q-refresh — *already measured*, 7.5 ms/body at SMPL-X
   mesh on an RTX 3090, 3.8× over the 100 ms budget at 50 bodies un-batched
   un-factored; within budget after vmap + factored-Fresnel. The paper can
   claim "in-silico real-time on a workstation GPU."

**Hero figure:** compliance violation rate vs served sum-rate, under
Brussels 14.57 V/m, across baselines. If the baselines violate $\gtrsim$
10 % of slot-body configurations and ours violates $<1$ %, the paper
lands. If the baselines rarely violate at all, we lean on the
chronic-dose argument (§VII): even when instantaneous compliance is easy,
bystander 24/7 DL dose reduction at near-zero sum-rate cost is a
deployable value proposition independent of any cap.

## 6. What's in the paper because it earns its place

| Ingredient | Why it's there | Would dropping it break the paper? |
|---|---|---|
| Coherent $\mathbf{Q} = \mathbf{J}^T \mathbf{M} \mathbf{J}$ factorisation | Fast per-slot refresh via translation phasor; keeps theory general | Yes — needed for multi-mode bodies, near-field extension, cleanness |
| Cauchy 1841 $D \leq 2$ bound | Pose-agnostic worst case for tier-C bodies; closes compliance loop without sensing pose | Yes — without it, bystander compliance requires pose estimation we can't do |
| SMPL-X body model | Pose parameterisation for tier-A/B bodies; differentiable for future-work | Could swap for SMPL; SMPL-X's face/hands are not used — maybe downgrade to SMPL |
| Multi-body QCQP + closed-form precoder | The actual algorithm | Yes — this is the method |
| Budgeted (not hard-null) formulation | DoF economy at high body counts | Yes — hard nulls exhaust DoF at $K+B \gtrsim M$ |
| BS-side ray tracer | Supplies path set per body → "angle of attack" | Yes — this is how the BS knows the BS-side directions |
| Tiered telemetry architecture | Covers the "who counts as known" question honestly | Yes — paper lives or dies on the bystander story |
| Monostatic RCS ISAC for tier-C | Bystander detection; still load-bearing but the vital-signs claim is out | Yes — replacement pending agent 01, may retreat to occupancy-envelope |
| Pose-conditioned ACS | Tightens tier-A/B compliance; pose-information gain | Possibly no — if gain is < 1 dB the paper leans on Cauchy and calls pose a bonus |
| Pose → ACS NN surrogate | **No real job.** Direct AEGIS evaluation at pose cadence is cheap. | No — **drop this**, cite IMU→pose mocap literature instead |
| $\mathbf{q}_{\mathrm{complement}}$ duality | Theoretical aside; motivates future-work ISAC on non-hard-nulled bodies | No — optional, one paragraph |
| Multi-operator cooperative aggregation | Brussels cumulative-cap semantics | Partially — can reference without developing the Shapley angle |
| Translation phasor identity | Per-slot refresh is one phase diagonal, not a new integral | Partially — per-slot refresh matters for the real-time-in-silico claim |
| Brussels vignette | The paper's reason to exist in DL | Yes — without the regulator angle, DL exposure is rarely binding |
| Two-pronged regulatory story | BR audit (industry standards) + RL jurisdictional reality | Yes — needed after I walked back the BR "slam dunk" |

## 7. What I'd change in the tex file on a second read

1. **§IV: kill the NN.** Replace with: "pose → ACS is a direct AEGIS
   evaluation at pose-refresh cadence (7.5 ms/body at SMPL-X mesh,
   GPU-measured). For bodies without pose telemetry, the Cauchy bound
   $D \leq 2$ applies."
2. **Keep the IMU→pose step short and cite.** One sentence: Madgwick /
   VQF filters and the HAR literature give IMU → SMPL-X pose. Paper
   consumes that as input.
3. **§V.3 real-time-in-silico claim.** Rewrite around the measured
   numbers: at SMPL-X mesh resolution on an RTX 3090, after a
   straightforward factored-Fresnel + vmap optimisation, 50-body Q
   refresh fits 100 ms. At native Thelonious mesh it does not —
   translation-phasor preprocessing is the alternative.
4. **§IV Remark 4.5 rank claim.** Tighten to "empirical rank 3–4 at
   $\epsilon=10^{-2}$ in LOS plaza on 8×8, 26 GHz, Thelonious." No longer
   a range.
5. **Drop or defer the pose-differentiable story.** It lives in a
   follow-up paper. The JSAC paper uses pose as a parameter to a direct
   evaluation, not a variable to differentiate through.

## 8. The risk I haven't fully addressed

The paper's value hinges on one empirical question: **does the Brussels
RL actually bind under baseline (MRT / ZF) precoding in realistic
plaza geometries?** If yes, the hero figure writes itself. If not, the
paper leans entirely on the chronic-dose argument, which is softer.
Running the 8×8 plaza scenario against the Brussels cap with MRT and
with ZF-to-users is the next measurement. Fast to run in AEGIS once the
scene is set up.

If MRT violates ≥10 % of (body, slot) configurations: the paper is an
easy write. If MRT violates ~1 %: the paper lives on chronic dose. If
MRT violates < 0.1 %: the paper pivots to a near-field / small-cell /
higher-EIRP scenario where the binding is real.

---

## Quick summary of the two agent results

**03 rank check (committed in `JSAC/experiments/rank_check/`):** rank-few
holds, at the low end — median 3 at $\epsilon=10^{-1}$, median 4 at
$\epsilon=10^{-2}$, max 4 at $\epsilon=10^{-3}$ for both plaza specular
and 3GPP UMa-LOS models. Paper §II.7 and Remark 4.5 are validated; I
tighten "3–10" to "3–4" in the committed plaza regime and flag that NLOS
geometry pushes higher (handled by the coherent formalism).

**04 GPU bench (pulled from remote):** 7.5 ms/body at SMPL-X mesh on an
RTX 3090, 66 ms/body at native Thelonious. Per-body fits 10 ms slot
cadence at SMPL-X mesh already. Full-50-body refresh at native mesh is
3.3 s (33× over 100 ms); at SMPL-X mesh it is 378 ms (3.8× over);
factored-Fresnel + vmap land it under 100 ms. Real-time-in-silico claim
holds with one structural fix. Paper §V.3 rewrite is straightforward.

Both results push the paper *toward* simpler, not more complex. That's
the right direction.
