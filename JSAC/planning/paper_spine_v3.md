# JSAC paper spine v3

*Successor to `paper_spine.md` (May 4). Reflects: rib.tex Pareto bound, audit findings (`paper_jsac_audit.md`), Zhou 2026 transcription, and the closed-loop discussion of 2026-05-09.*

## One-paragraph thesis

Per-body chronic absorbed dose is the controlled state variable a digital twin network needs to maintain under European EM-field reference-level regulation. We close the loop with a multi-rate controller built around a per-body exposure operator, using Lyapunov virtual-queue optimization to convert the instantaneous reference-level cap into a long-term budget the controller can optimize against. Two further results frame why a communication engineer should care: (i) the same body that tightens the regulator opens a second propagation channel as a passive scatterer, and capacity from that channel is hard-bounded by absorbed dose on the same body — one Pareto frontier, not two; (ii) the empirical effective rank of the per-body exposure operator (3 to 4 at 99% trace) is the per-body capacity ceiling that body-as-scatterer multi-user gain saturates at. Built on the network's own ray tracer, demonstrated at plaza scale on 50 SMPL-X bodies in Brussels Grand Place at 26 GHz.

## Why this fits the JSAC SI

The SI brief explicitly asks for "twin-in-the-loop architectures for real-time feedback and control", "cross-layer optimization", "convergence and stability for feedback-driven DTNs", and "latency-bounded DT synchronization". The current paper claims the vocabulary but does not deliver the architecture. The v3 spine commits to a real multi-rate closed loop, with measurable state (per-body dose), measurable cost (sum-rate), provable convergence (Lyapunov on the dose virtual queue), and a tight rate-dose duality that makes the loop's setpoint physically meaningful.

## Three contributions

1. **Body twin object** — per-body coherent exposure operator $\mathbf{Q}^{(u)} \in \mathbb{C}^{M \times M}$ and bistatic scattering matrix $\mathbf{F}_b^{(u)}(\hat{\mathbf{k}}_\text{out})$, both computed from the network's ray tracer with the same surface integral (per rib.tex §2.2). Tiered telemetry A/B/C populates the twin from served users (uplink CSI + IMU pose), cooperating non-users (uplink presence + IMU pose), and ISAC-sensed bystanders (radar return + Cauchy envelope).

2. **Closed-loop dose controller** — multi-rate hierarchy:
   - **Outer loop, regulatory window (6 min Brussels / 24 hr Italy):** Lyapunov virtual queue per body $u$ accumulates dose deficit $D_u(t) - D^*_u$. Updates per-body Lagrange multiplier $\lambda_u(t)$ via the standard Lyapunov drift-plus-penalty step.
   - **Inner loop, per slot (1 ms):** QCQP solver consumes current $\{\lambda_u\}$ and produces precoder $\mathbf{W}(t)$ in closed form. Reduces to regularized ZF in the rank-1 degenerate limit.
   - **Mid loop, pose update (100 ms):** twin re-evaluates $\mathbf{Q}^{(u)}$ from latest pose; ISAC scheduler probes tier-C bystanders driven by twin uncertainty.
   
   Architecturally a downlink, multi-body, scene-aware extension of Zhou 2026's UL/single-handset/thermal Lyapunov-virtual-queue solver. The mathematical scaffolding (V-Q drift-plus-penalty, per-slot closed-form inner solve) is the same; the geometry, scope, and state are different.

3. **Capacity-exposure Pareto bound** (Theorem 1, from rib.tex). Per-direction pseudo-Brewster locking gives:
   $$G_\text{body}(\mathbf{X}) \le K_b \log\left(1 + \tfrac{1}{N_0}\tfrac{1-T_0}{T_0}\,\mathcal{K}_\text{rx}\,D(\mathbf{X})\right) + O(5\%).$$
   Each watt of body-mediated capacity costs at least $T_0/(1-T_0) \approx 0.32$ W of absorbed dose. Body-mediated rank lift is hard-capped by per-body absorbed power. The controller's setpoint $D^*_u$ traces the Pareto frontier the inequality describes.

## What changes vs current paper

### Kept

- Per-body coherent exposure operator $\mathbf{Q}^{(u)}$ and the path-space factorization $\mathbf{Q}^{(u)} = \mathbf{J}^T \mathbf{M}^{(u)} \mathbf{J}$ (current §II).
- Scene path dictionary built once over the static BS+scene geometry (current §IV.A).
- CSI calibration of dictionary amplitudes via ridge LS against served-user uplink CSI (current §IV.B).
- Tiered telemetry A/B/C and refresh cadences (current §IV.C, §IV.D).
- Empirical rank measurement: median 3–4 at 99% trace fraction (current §V.B).
- Plaza scenario: 50 SMPL-X bodies, AMASS walk cycles, 8×8 panel at 26 GHz, Brussels Grand Place geometry.
- Two regulatory pathways: BR audit + RL footprint mitigation (current §VI).
- Cauchy bound + conditional-tightness measurement (current §V.I, App. C).

### Promoted (changes role, not content)

- **Chronic dose ECDF** (current §V.D): from descriptive metric to *controlled state variable*. Becomes the readback of the controller, not a measurement of the world.
- **Cauchy bound** (current App. C): from worst-case safety net to one half of the Pareto duality, paired with Theorem 1 (capacity ceiling).
- **Closed-loop language**: from rhetorical to architectural. The multi-rate hierarchy is named, sized, and analyzed.
- **Rank-3-4 result**: from "low-rank generically" to "the dimension of the body's contribution to the multi-user channel basis, predicted by per-direction locking, observed empirically." Theorem-meets-experiment.

### Rewritten

- **§III solver derivation** (audit C1, T12, paper_jsac_section_iiia_review.md): drop WMMSE/Christensen-Shi pretense; rewrite as MMSE-with-exposure caps (matches code at `multibody_ecbf.py:530-549`). Cite Joham 2002, Peel-Hochwald 2005, Ying 2015. Then layer the Lyapunov virtual queue on top, citing Zhou 2026 for the V-Q construction.
- **§V.A binding regime arithmetic** (audit T4, R8): reconcile $r^*$ formula with the table; settle on one $T_0$ value (audit C4).
- **All `20 s` references** (audit R1, R2, R3, R14): replace with `5 min`. Six sites.
- **All `31 ms median solve` references** (audit C8, R15): replace with regime-split values. Six sites.
- **§III iteration claim** vs §VII.D `max_outer = 8` (audit C7, T18, R16): reconcile.
- **All dangling `\cref{tab:slack}` and `\cref{sec:multibody-ecbf}`** (audit T1, T2): fix or remove.

### Demoted

- **Current §V.E spatial deposition map**: kept but moved into §VI (regulatory framing) as the RL-footprint visualization, not as a standalone result.
- **Current §V.G ISAC tier-C link budget**: compressed to one paragraph in §III mid-loop description, citing the link-budget calculation as supporting work in an appendix.
- **Current §V.H CSI calibration**: kept but moved into §V deployment-realism block, not a standalone result subsection.

### New

- **§III closed-loop architecture section** with the multi-rate hierarchy, Lyapunov drift analysis, and convergence theorem.
- **§IV Pareto bound section** with Theorem 1 (from rib.tex §6) and a derivation of the per-direction pseudo-Brewster locking that supports it.
- **New experiment 1: dose-controller demo.** Run the 5-min plaza trace with the V-Q controller wired in vs the current per-slot solver. Show: realized chronic dose tracks the setpoint $D^*_u$, sum-rate higher than per-slot enforcement at matched compliance, controller stable across initial conditions.
- **New experiment 2: Pareto bound validation.** Sweep precoders (MRT/ZF/oracle/V-Q controller) over the plaza data; plot realized sum-rate vs realized average per-body dose; overlay Theorem 1 envelope. Show the bound is tight on the upper-right corner.
- **Optional new experiment 3: bystander twin ISAC schedule.** Show twin uncertainty drops monotonically with probe count when the scheduler is uncertainty-driven, and stays flat with fixed-cadence sensing.

### Cut or repurposed

- **Current §V.F pose-information ablation**: the experiment is real-pose-vs-T-pose-Cauchy, which is a Cauchy-envelope-tightness statement, not a pose-estimation-quality statement. Repurpose as a one-paragraph result inside §IV (Pareto / Cauchy duality): "tighter Cauchy envelope from real pose moves the operating point closer to the Pareto frontier by X dB." Drop the "4.7× violation reduction" framing.
- **Current §V.D stand-alone chronic-dose section**: subsumed into §III as the controller readback experiment.

## Section structure (target)

- **§I Introduction.** Three-beat hook: (a) Brussels-style RL caps are conservative free-space proxies; we measure ~4 OoM of slack on the actual basic-restriction quantity in plaza geometry, billions of euros of unused link budget. (b) The same body is a passive scatterer; capacity from body-mediated paths is hard-bounded by absorbed dose on the same body — one Pareto, not two. (c) A body-side digital twin maintains both, in a closed multi-rate loop on the network's own ray tracer.
- **§II Body twin object.** $\mathbf{Q}^{(u)}$ and $\mathbf{F}_b^{(u)}(\hat{\mathbf{k}}_\text{out})$ from one ray-traced surface integral. Per-direction pseudo-Brewster locking. Scene path dictionary + tiered telemetry + refresh cadences.
- **§III Closed-loop dose controller.** Multi-rate architecture. Inner loop: MMSE-with-exposure QCQP, closed-form, ZF as rank-1 limit. Outer loop: Lyapunov virtual queue on per-body chronic dose, drift-plus-penalty $\lambda_u$ update. Mid loop: twin-uncertainty-driven ISAC scheduler. Convergence theorem. Sized cadences and bounds.
- **§IV Capacity-exposure Pareto bound.** Theorem 1 from per-direction locking. What the bound says about DTN allocation. Empirical rank as the predicted ceiling.
- **§V Plaza-scale evaluation.** Scenario (Brussels Grand Place, 50 bodies, 5-min walk, 8×8 panel, 26 GHz). Slack regime: dose ECDF separates by tier, controller readback. Binding regime: controller pre-emptively tightens, recovers rate vs per-slot. Pareto frontier validation. Bystander twin ISAC schedule (if scope allows).
- **§VI Regulatory framing.** Two pathways. RL-footprint visualization. Brussels 6-min vs Italy 24-hr averaging windows mapped onto the controller's outer-loop window.
- **§VII Discussion.** What binding-regime fallback rates mean operationally; Pareto bound looseness conditional on direction set; deployment posture.
- **§VIII Conclusion.**
- **Appendices.** A: Per-path Fresnel transmission operator. B: V-Q controller drift analysis + convergence proof. C: Per-direction pseudo-Brewster locking proof.

## What we explicitly do not contribute

- **IMU → SMPL-X pose estimation.** Madgwick / VQF / inertial-mocap-net: cite, do not implement. The paper consumes pose at 100 ms cadence as an exogenous input. Per spine v1: this is sensor-fusion literature, not communication-engineering contribution.
- **Per-tissue near-field FDTD validation.** TAP submission (separate paper) handles the PO-vs-FDTD residual at ≤5%.
- **Multi-cell / multi-operator Shapley/cooperation gap.** Future work, one-line acknowledgment in discussion.
- **RIS-EMF compliance buyback.** Future work.
- **Foundation-model-based DT context understanding.** Not relevant to this paper; the SI brief mentions it but our contribution is on the control-theoretic side.

## Relation to representative papers

- **Zhou 2026 (UL/single-UE/thermal/Lyapunov-V-Q):** structural template for the controller. We extend the V-Q machinery to DL/multi-body/dose. Acknowledged explicitly as the closed-loop precedent.
- **Hochwald 2014, Ying 2015/2017, Castellanos 2020:** single-handset SAR-matrix prior art. We generalize from single-body to heterogeneous body population.
- **Joham 2002, Peel-Hochwald 2005:** MMSE multi-user precoding precedent for the inner solve.
- **D-REC (Zhang/Liu/Chen 2024):** twin-in-the-loop with constrained MDP. Closest DTN-side template; we sit alongside as a different application domain (exposure compliance vs reliability intervention).
- **Hoydis 2024 (DiffeRT):** differentiable RT precedent. We use ray tracing offline for the dictionary and online for CSI calibration; differentiability is acknowledged, not invoked.

## Empirical work plan (compute order)

1. **Audit free-fixes pass.** ~half day. R1/R2/R5/R6/R7/R8/R10/R11/R13/T1/T2/T4/T8/T9. No new compute. Establishes a clean baseline.
2. **Solver-derivation rewrite (Path A).** ~1-2 days LaTeX. §III.A and App. B rewritten as MMSE-with-exposure. Drop WMMSE pretense.
3. **Pareto bound validation.** ~1 day GPU. Run the existing 5 precoders on the existing 5-min plaza trace; plot realized sum-rate vs realized per-body dose; overlay Theorem 1 envelope. Validates Theorem 1 numerically.
4. **V-Q controller implementation + dose-controller experiment.** ~3-5 days code + ~1 day GPU. Wire dose accumulator + drift-plus-penalty into `slot_loop.py`; run 5-min trace × 3 setpoints × 2 controller gains; show controller stability + rate gain vs per-slot enforcement.
5. **Bystander ISAC scheduler (optional).** ~1 week code + ~1 day GPU. Twin uncertainty per tier-C body, scheduler picks probe direction, monitor RMSE drop.
6. **Convergence theorem.** ~2 days math. Lyapunov on $\sum_u (D_u - D^*_u)^2$, drift-plus-penalty bound, asymptotic optimality gap. Standard V-Q analysis adapted to our QCQP inner.

## Spine risks and mitigations

- **Risk: Theorem 1 (Pareto bound) is too loose to be interesting.** rib.tex flags Hadamard-loose plus visibility-relaxation-loose. Mitigation: experiment 3 (Pareto validation) tells us before we commit. If the bound is loose, demote from contribution to "structural insight" and lean harder on the controller as the paper's anchor.
- **Risk: V-Q controller doesn't actually deliver rate gain over per-slot enforcement at matched chronic compliance.** Mitigation: both regimes (slack and binding) have different stories. In slack, controller delivers rate by relaxing $\lambda$; in binding, controller delivers stability by integrating dose. If neither holds, fall back to the descriptive chronic-dose ECDF result.
- **Risk: Reviewers read "extension of Zhou 2026" as derivative.** Mitigation: lead with the geometry difference (multi-body, downlink, scene-aware ray tracer, non-spherical mesh, network-side twin) and the Pareto bound (which Zhou does not have), not with the V-Q machinery.
- **Risk: ~4 OoM slack means the controller has nothing to do in the demonstrated regime.** Mitigation: this is actually the result. The controller demonstrates the slack exists, hands the rate back, and the chronic-dose ECDF reads out where on the Pareto we sit. The binding regime is the corner where the controller earns its keep, and we report both.

## Decisions still open

1. **Theorem 1 anchor or controller anchor as the paper's headline?** Both are real; both fit the SI. Theorem 1 is more striking, controller is more architectural. Could be either. Need Robin's preference.
2. **6-min Brussels or 24-hr Italy averaging window for the controller demo?** Brussels = 10,800 slots at 33 ms (~6 min); doable in one job. Italy = 24 hr; needs sub-sampling or a much shorter reference trace.
3. **Bystander ISAC scheduler in v1 or future work?** It's the most JSAC-darling piece and the most expensive to build. In or out depends on timeline.
4. **Keep `rib.tex` as a separate companion paper or merge the relevant pieces into the JSAC submission?** rib.tex itself is standalone-paper-worthy; merging Theorem 1 + per-direction locking into the JSAC paper is feasible without losing the rest.
