# JSAC and JSAC2: an archeology of the spines

*Reconstructed from `JSAC/` and `JSAC2/`: the planning archeology, both paper lineages (seven `paper_jsac` versions, four `rihb_theory` versions, four `jsac2` versions), the critiques, the PoC findings, and the audit reports.*

## The one-sentence answer

These are two attempts at the same paper, and both have the same plot: a body digital twin looking for a constraint that binds. **JSAC** put the twin on the base-station side to control exposure, and died when exposure turned out not to bind. **JSAC2** moved the twin onto the phone, dropped exposure to a read-out, and made *pose* the control variable instead. The idea that survives every rewrite is not any of the spines. It is the fact that `Q = Jᵀ M J` can be computed in milliseconds instead of FDTD-hours.

---

## Part one: JSAC, April 21 to May 30

### The seed

`thinking_no_ai.txt` and `conversation.md` start from a hardware observation, not a physics one. Uplink is the bottleneck, the 23 dBm cap is SAR-driven rather than battery-driven, and the iPhone 12 ANFR episode is Apple publicly admitting they design right up against the SAR wall. The first idea is: if SAR is the wall, then a better dosimetry model buys throughput.

Two things in that file matter more than the idea itself. One is the realization, arrived at by staring at the operator, that the exposure matrix is purely geometric, which is what makes a one-time phone body-scan plausible. The other is the note to self, in caps: **"BE VANILLA FFS."** That tension, ambition against vanilla, is the engine of everything that follows.

### The fork, and the branch that won

Two directions split on April 22. **Direction 4** was spatial APD: the ICNIRP 4 cm² local limit replaces whole-body SAR at FR2, so track a family of `Q_local(r₀)` over surface patches and steer around hotspots. It was killed by its own result. The "stable worst patch" turned out to be a geometric artefact, not a coherent hotspot, so there was nothing for a beamformer to chase. It never reached a paper.

**Direction 5** asked whether `Q` can be recovered from the channel `h` alone. The answer was a no-go theorem, which forced three routes: the BS runs its own ray tracer, the UE reports AoA, or you calibrate against a phantom. Route B died within a day of contact with reality. The April 23 hardware dive found that phones have two mmWave modules with one active at a time, analog beamforming inside the RFIC, no per-element IQ at baseband, and no standardized AoA export. The "three panels at 120°" everyone repeats is folklore. Route A won by elimination, and "the BS runs its own RT" became load-bearing rather than ornamental.

### The brainstorm rounds, and Robin killing his own darlings

Round one went maximally ambitious: twin the body rather than the ordinance, pose-differentiable `Q(θ)` through SMPL-X linear blend skinning, a Löwner SDP as a cutting plane in pose space, a pose neural network with Sobolev supervision. Round two is Robin pushing back at his own generated ideas. The Cauchy bound with `D ≤ 2` obsoletes the Löwner machinery. The pose NN is unnecessary because pose-to-cross-section is deterministic. The rank-one plaza limit means the "quiet subspace" is just an ordinary zero-forcing nullspace. Round three brought agents back with the news that ISAC vital-sign sensing at plaza range does not exist in the literature, so ISAC demoted to presence detection.

The most instructive line in the whole archive is Robin catching the model being a sycophant: *"have you told me why we gave up on coherent?"* The coherent operator got restored and stayed the mother formalism.

### The seven versions, and the slow inversion

`paper_jsac_evolution.md` is the honest autopsy, and its thesis is that the spine inverts twice while the twin's role shrinks monotonically.

The precoder starts as a closed-form ECBF, `w_k = (Σ λ_u Q^(u) + νI)⁻¹ g_k`, which generalizes Ying 2015 to multiple bodies and reduces to ZF in the rank-one limit. Then v1 hits the wall: on real plaza data the Brussels reference level is slack by four orders of magnitude, all five precoders collapse to one operating point, and pose information buys nothing. The handoff report is blunt about the choice made there. Rather than manufacture a Pareto, the paper reported the null.

v2 through v4 walk that back by constructing a binding regime instead, raising power to 43 dBm and tightening the cap from 14.57 V/m to 6 V/m to 3 V/m. Along the way v2 claims a WMMSE solver the code never implemented, and the audit catches it. v3 rolls the math back and introduces primal projection, motivated as a fix for the dual ascent failing to find a feasible point 92 to 96 percent of the time.

v5 is where it turns over. Under the operational 5G FR2 rate model, per-stream MCS27 caps you at 7.4 bps/Hz, and regularized ZF on a 64-element panel saturates that cap with about 12 dB of SINR margin to spare. So the exposure-constrained QCQP collapses to choosing one scalar, the projection amplitude `α`. The elaborate solver from v1 through v4 becomes a baseline in Appendix C. It is the strongest result in the lineage and it hollows out the paper, because the body twin's remaining job is to estimate `P_abs` so the projection can pick `α`. Twin as controller, then as constraint-set provider, then as a scalar supplier.

Two more collapses land in v5. A multi-seed cross-check at seed 1729 reverses the headline ordering, so projected ZF and the tuned dual ascent are statistically tied on compliance and the real case for ZF is 700× wall-clock. And the chronic-dose value pitch, which was the fallback, shrinks to "the twin tightens the median by 37 percent" rather than any solve-versus-fail distinction.

Robin's `somethoughts.md`, written around here, is the emotional truth of it: *"coming to the realization that ive been working weeks on spine and never ever felt satisfied. so JSAC was ALWAYS a wildcard. you'll just have to run with the best solution there is."* And, separately, *"the brussels framing, esp old reg, has alwaaays been engineered."*

There was one more rescue attempt, `paper_spine_v3.md`, which tried to make chronic dose the controlled state of a Lyapunov virtual-queue controller and to import the capacity-exposure Pareto bound from `rib.tex`. That bound is the bridge to what happens next: each watt of body-mediated capacity costs at least `T₀/(1-T₀) ≈ 0.32` W of absorbed power on the same body. One Pareto frontier, not two.

---

## Part two: JSAC2, the pivot

### The new angle

`NEW_ANGLE.md` is nineteen lines and it reframes everything. mmWave was declared dead for two reasons, blockage and public fear, and both route through the human body. Rarely, you want a genuinely huge download. At that moment a pop-up asks for your pose. Your pose is differentiable with respect to the SMPL-X parameters. The base station donates its ray-traced scene, calibrated by your uplink pilots, and you and the network negotiate a better body configuration until the download flies. Exposure comes along free.

And the joke that carries the branding: *humans are reflectors at mmWave, they are also mounted with a highly intelligent organ called the brain, therefore they are Reflective Intelligent Human Bodies.*

The inversion from JSAC is total. The twin moves from the BS to the phone, the objective moves from compliance to rate, and the control variable moves from the precoder to the user's body.

### Four theory versions, each one an honest correction

`rihb_theory.tex` v1 proposed pose as a control variable with a joint capacity-exposure loss and a "gait-action principle." The critique found six killers, and they are good ones. The novelty is thin because the theorems are chain rules on smooth integrands. The Pareto bound binds only on the body-mediated channel component, which is not where the hero scenario lives. The visibility-gate operator inequality is simply wrong, since the gate gives a trace inequality and not an eigenvalue one. The MCS cap zeroes the rate gradient exactly when a pose move succeeds.

And the one Robin reacted to out loud (`user_messages.txt`, message 5, in full): **"a fraunhofer distance of 300 m ??!"** The body's Fraunhofer distance at 28 GHz is about 300 m. The phone is 30 cm away. The entire body-to-phone leg had been modeled with far-field machinery lifted from `rib.tex`. That is a load-bearing modeling error, not a loose thread.

Then the proof of concept ran, and reality arrived. The S1 window scenario predicted +14 dB. It measured **+2.63 dB SINR** at a 15° torso turn, which is +14.5% rate and +87 Mbps. The dB-per-degree lemma was off by 3×, because the lever arm is the outstretched arm holding the phone and not the spine offset. Body visibility never falls below 0.59, because a Fresnel zone at 30 m has a 40 cm radius and a torso is 21 cm thick, so a body simply cannot block a mmWave LOS the way intuition says. And Robin filed the correction that reorganizes the entire paper: **on the downlink the user is at roughly 0.001× the basic restriction, so the exposure term in the loss is structurally zero.**

That is the same discovery as JSAC v1's four orders of magnitude of slack, arrived at from the opposite side of the link. Exposure does not bind. It never did.

So v3 dropped exposure from the optimization and kept it as a display, which produced the structure the paper still has: **two products, one piece of machinery.** The same per-triangle physical-optics evaluation yields a live absorbed-power reading (for the user, for regulators, and as a genuine methods upgrade for RF-EMF cohort studies like CLUE-H, replacing self-reported questionnaire proxies with measured per-individual time series) and a pose-differentiable channel (for rate).

v4 is Robin's message 6 rendered as physics. He rejected the inherited far-field radar framing and asked for the derivation from the ground up, with an analogy to how Blender renders: *"you can do the rendering pass from the UE and back up the chain, since I dont care what the fields are on any OTHER location besides the UE antenna."* That became the UE-anchored Kirchhoff render, which is the actual technical primitive of JSAC2, and it is backward path tracing beating forward radiosity because the receiver count is one. He also asked for the loop to genuinely close, with uplink pilots calibrating the on-device twin rather than the BS just donating a scene.

### The paper, and the reckoning

The spine plan went through the same self-correction. v1 of the plan was body-centric with an app-UX section. Robin's response was that no research paper talks about app screens, and that the right question is not "does our gradient descent converge on one example" but **"does a good pose always exist, and when does the loop find it?"** That converted advocacy into an empirical contribution with three parts: existence, reachability, and a failure-mode taxonomy.

The papers `jsac2_v1` through `v4` built that out on 18 Sionna RT Munich scenes, 9 LOS and 9 NLOS, with a 32-dimensional VPoser latent. v4's abstract reports 0.6 to 8.6 dB of cascaded-SINR gain, mean 1.7 dB on LOS and 4.1 dB on NLOS, with projected gradient ascent reaching within 1 dB of the reference optimum in 20 steps on 16 of 18 scenes. Note that the v4 title quietly drops the RIHB branding: "On-Device Body Digital Twins for Pose-Aware mmWave Links and Live Exposure Readings."

Then the May 11 audit ran seven parallel agents at it, and the verdict is that the storyline is plausible while nearly every number is wrong. The Kirchhoff reflection coefficient is coded as `(r_s + r_p)/2`, but under the standard Fresnel sign convention those have opposite signs at normal incidence, so the coefficient **vanishes exactly on the specularly-aligned triangles that dominate the body channel**, suppressing `h_body` by 16 to 22 dB. Sionna's `paths.cir()` returns real and imaginary parts, and the code read them as theta and phi polarization components, destroying carrier phase across paths in a paper whose whole thesis is coherent superposition. The "naturalness ball" is anchored at the origin rather than at the user's actual pose, so 17 of 18 scenes begin outside it. The "brute-force optimum" is 100 random shots in 32 dimensions, which gradient ascent beats on 9 of 18 scenes. The baselines table is 80 percent saturated at the MCS cap. And a separate audit found the body is never inserted into the ray-traced scene at all, so the claim that `h = h_BS + h_body` is "exact by Maxwell linearity" is only true if `h_BS` is the body-removed reference of a body-present trace, which it is not.

---

## What the archeology actually teaches

Four things recur across both papers, and they are the real findings.

**Exposure never binds, and it took two full papers and one PoC to accept it.** Direction 4 found the worst patch was a geometric artefact. JSAC v1 found four orders of magnitude of slack. The JSAC2 PoC found the user sits at 0.001× the basic restriction. Every time, the response was to engineer a tighter regime, and every time Robin eventually said so out loud. The final position is the right one: exposure is a transparency product, not a constraint.

**The MCS cap eats every gain.** It collapsed the v1-v4 QCQP into one scalar in v5. It compressed the PoC's +2.63 dB of SINR into +0.58 dB of rate. It saturated 80 percent of the JSAC2 baselines table. Any spine that sells a channel-quality improvement has to sell it in SINR or Mbps, never in rate-dB.

**The thing that is actually novel was never the spine.** Robin says it plainly in the first message of the JSAC2 conversation: *"the main thing I realized was you can make this matrix really quickly and compute it very fast, much faster than FDTD, and that's really the enabler."* Both papers keep trying to find an application worthy of the operator. `Q = Jᵀ M J`, the translation-phasor identity, the rank-3-to-4 empirical regime, and the per-triangle PO kernel survive every rewrite untouched.

**The honesty ratchet works, and it costs.** Each version discloses more and claims less. The seed-1729 reversal, the null result in v1, the PoC falsification gate, the self-commissioned audit that found its own showstoppers. This is why the work is trustworthy and also why no spine has ever felt satisfying. The archive is a record of someone repeatedly refusing to let a paper be true by construction.

Where it stands: `jsac2_v4` is the live manuscript, and the audit says the two showstopper bugs (the Kirchhoff coefficient and the Sionna phase unpack) have to be fixed and all 18 scenes re-run before any number in the abstract means what it says.

---

## Source map

| Document | What it is |
|---|---|
| `JSAC/planning/thinking_no_ai.txt` | The seed, written without AI. "BE VANILLA FFS" |
| `JSAC/planning/conversation.md` | Uplink-is-SAR-limited exchange, the iPhone 12 / ANFR proof point |
| `JSAC/planning/ARCHEOLOGY.md` | Prior reconstruction of the JSAC trajectory, Apr 21 to May 4 |
| `JSAC/planning/directions/` | Direction 4 (spatial APD, archived) and Direction 5 (Q from channel, became the spine) |
| `JSAC/planning/UE_hardware/` | The hardware dive that killed Route B |
| `JSAC/planning/brainstorm_opus_round{1,2,3}.md` | Ambition, pushback, agent reality-check |
| `JSAC/planning/somethoughts.md` | "JSAC was ALWAYS a wildcard" |
| `JSAC/planning/paper_spine_v3.md` | The Lyapunov / dose-as-controlled-state rescue attempt |
| `JSAC/paper/paper_jsac_evolution.md` | The seven-version autopsy. The single best document in either tree |
| `JSAC/paper/paper_jsac_v5.tex` | Final JSAC manuscript. MCS-cap proposition, twin reduced to α-supplier |
| `JSAC/paper/rib.tex` | The "Reflective Intelligent Bodies" random walk. Pareto bound, per-direction locking |
| `JSAC2/NEW_ANGLE.md` | The pivot, in nineteen lines |
| `JSAC2/critique_v1.md` | Six killers, including the 300 m Fraunhofer distance |
| `JSAC2/critique_v2.md` | Exposure leaves the loss. "Double paper" structure emerges |
| `JSAC2/poc/s1_window/findings.md` | The PoC that falsified the +14 dB estimate and confirmed the spine at +2.63 dB |
| `JSAC2/rihb_theory_v4.tex` | Ground-up physics. The UE-anchored Kirchhoff render |
| `JSAC2/JSAC_SPINE_PLAN_v2.md` | Network-centric pivot. Convergence as a research question |
| `JSAC2/body_transparent_raytracer.md` | The body is not in the ray-traced scene |
| `JSAC2/paper/jsac2_v4.tex` | Live manuscript |
| `JSAC2/paper/agent_reports/AUDIT_SYNTHESIS_2026-05-11.md` | Two showstoppers, thirteen serious issues |
| `JSAC2/user_messages.txt` | Robin's raw messages across the JSAC2 session |
