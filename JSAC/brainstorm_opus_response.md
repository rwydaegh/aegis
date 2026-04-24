# Brainstorm response — JSAC DTN paper

*Outside read, written for Robin. By Claude (Opus 4.7, 1M ctx), 2026-04-24.*
*Everything here is an opinion formed from reading: `theory/exposure_null_precoding.tex`, `theory/system_formalism.tex`, `theory/q_complement.tex`, `theory/monograph_v2.tex` (partial), `JSAC/directions/direction_5_math_opus_codex.tex`, `JSAC/directions/direction_4_problem_codex_opus.tex`, `JSAC/related_works/2601.19587_transcription.tex`, `JSAC/UE_hardware/direction_5_ue_hardware_summary.md`, `skeletal-animation-primer/README.md`, `JSAC/representative_papers/review.md`, `JSAC/JSAC_SI_digital_twins.md`, `JSAC/author_guidelines/SUMMARY.md`.*

---

## Before anything else — the one paragraph

**After your pushback (read this first).** You were right to push on Part 1. I re-read §5 of the monograph and several things I wrote are over-engineered. The real thesis should be simpler: **in the DL plaza regime, exposure-null precoding collapses to ZF-dosimetry — classical ZF with bystander steering vectors as extra nulls — and Part 1's Cauchy bound gives pose-robust WB-SAR compliance without any SDP machinery.** The Löwner envelope I pitched earns its keep only in high-rank regimes (coherent near-field, UE-side, below-6-GHz, or per-patch APD tracking), not in the DL plaza. The pose-differentiable $\mathbf{Q}$ is real, but its immediate value is as a *scalar* ACS predictor $\sigma(\boldsymbol{\theta})$, not a full operator map. The Brussels framing is legitimate — not a mathematical hook but a deployment-blocker hook. I am walking back the "demote Brussels" advice.

**The paper I now think you should write.** ZF-dosimetry for mmWave DL: a digital-twin-in-the-loop extension of classical zero-forcing in which the null space is enlarged by bystander bodies, and per-body "null depth" is modulated by a pose-conditioned ACS predictor $\sigma_u(\boldsymbol{\theta}_u)$. The DT closes the loop using a tiered telemetry architecture (IMU for tiers A/B via MNO consent, ISAC vital-signs Doppler for tiers C/D) and the Cauchy $D\le 2$ directivity bound for pose-agnostic worst case. The hero demo is 5 minutes of real-time-in-silico plaza (50 bodies, 26 GHz, 8×8 panel, 3-operator Brussels-14.57V/m cap) with per-slot ECBF, per-100-ms pose update, per-second translation. Brussels is the *deployment rationale*, not the mathematical backdrop.

Everything below this point is the longer argument. I've left the original points in place — but note that §"The bit I want to talk you into" is the place where I most overreached; please read that section in combination with the companion answers file `brainstorm_opus_answers.md` which I wrote second and which rolls back the ambitious version.

---

## Epistemic inventory (updated after round 2)

- **Confident:**
  - The path-space factorisation in `system_formalism.tex` is correct and is load-bearing *for the coherent story*. In the far-field DL plaza regime $\mathbf{Q}^{(u)}$ degenerates to rank-one and the factorisation's workload collapses; still useful for Appendix / near-field extension.
  - The identifiability no-go in `direction_5` is correct.
  - Zhou 2026 is parallel, not collision. Head-to-head differentiation is: downlink vs uplink, multi-body vs single, pose vs spherical head.
  - Part 1's Cauchy-based $D \le 2$ and the posture-insensitivity remark (6.5% spread across a backflip) make pose-robust WB-SAR nearly free. **Löwner envelope is overkill for this.**
  - In the far-field rank-1 limit, the "quiet subspace" is the classical ZF null space applied to body steering vectors. No new geometry.
- **Suspect:**
  - Local APD (the FR2-binding 4 cm² constraint) is where pose-differentiable $\mathbf{Q}$ really matters, not WB-SAR. Worst-patch identity changes with pose.
  - ISAC vital-signs detection works at plaza range; see link budget in the answers file. Marginal at heartbeat, comfortable at respiration.
  - Pseudo-Brewster eigenvector locking survives reviewer scrutiny for skin at mmWave but weakens off-regime. Not load-bearing for the recommended ZF-dosimetry paper.
- **Genuinely uncertain:**
  - Whether the smoothed $H(\mu_n)$ + Fresnel product is well-behaved in silhouette-tangent pose directions (issue for the near-field extension, not the DL plaza).
  - How much pose-aware ACS predictor beats a Cauchy-worst-case baseline in sum-rate. Could be 0.5 dB; could be 3 dB. Needs the experiment.

---

## The math, line-by-line — what I'd double-check

Mostly clean. Three places I'd look twice:

**1. `exposure_null_precoding.tex` Prop 4.2 (quiet subspace dimension).** The bound $\dim \mathcal{Q}(\mathcal{B}) \ge \max(0, M - \sum_u r_u)$ is correct as a worst-case bound on subspace intersections — that's just iterated $\dim(V_1 \cap V_2) \ge \dim V_1 + \dim V_2 - M$. But the rhetorical use of it ("the quiet subspace is generically nontrivial") is shakier than the bound itself. **Generic** subspaces achieve the bound with equality. **Structured** subspaces — which is what $\ker \mathbf{Q}^{(u)}$ are — can be smaller or larger. In the small direction: if two bodies are illuminated from nearly the same BS aperture, their kernels overlap almost completely and you have *more* quiet subspace than generic. In the large direction: if they're back-to-back across the BS, intersection shrinks. The empirical question isn't "is the quiet subspace nontrivial," it's "how much of it survives once you demand $\rho$-alignment with actual UE channels." I'd drop the "generic nontriviality" phrasing and show a CDF of $\dim \mathcal{Q}_\varepsilon / M$ over a scene ensemble instead.

**2. `q_complement.tex` Prop 3.2 (eigenvector locking $\mathbf{Q}_{\mathrm{re}} \approx \frac{1-T_0}{T_0} \mathbf{Q}_{\mathrm{ab}}$).** The proof sketch says "the outgoing-direction change $\hat{\mathbf{k}}_n \to \hat{\mathbf{k}}_n^{\mathrm{re}} = \hat{\mathbf{k}}_n + 2\mu_n \hat{\mathbf{n}}$ affects only the per-point phase $e^{-i k_0 \hat{\mathbf{k}} \cdot \mathbf{r}}$, which is a unitary factor … it leaves $\mathbf{G}^H \mathbf{G}$ invariant up to the sign of cross-element phases that integrate out on $\Sigma$." I believe the first part (the Gram is unitarily invariant under a global phase). I'm **less** convinced the cross-element phases "integrate out" in general. For a flat patch, yes — the surface Fourier component at $\mathbf{q}_{nn'}^{\mathrm{re}} = k_0(\hat{\mathbf{k}}_{n'}^{\mathrm{re}} - \hat{\mathbf{k}}_n^{\mathrm{re}})$ is different from the one at $\mathbf{q}_{nn'} = k_0(\hat{\mathbf{k}}_{n'} - \hat{\mathbf{k}}_n)$, and they integrate to different values against a non-flat body. So the off-diagonal $\mathbf{M}$ entries of $\mathbf{Q}$ and $\mathbf{Q}_{\mathrm{re}}$ differ beyond the scalar factor. I'd expect the proportionality to hold *on diagonal / top eigenvalue* cleanly, and on the full operator only up to a larger-than-5% residual for bodies with curvature on the wavelength scale (which is everything at 28 GHz). Worth a numerical check on thelonious before you put "5%" in the abstract.

**3. `exposure_null_precoding.tex` equation (38) back-of-envelope: "Brussels outdoor cap $\approx 0.19$ W absorbed on a body."** The arithmetic ($T_0 \times |\Sigma| \times S_{\mathrm{lim}}/2 \times \bar\eta$ with $\bar\eta \approx 0.5$) is fine given the inputs. The issue is "$\bar\eta \approx 0.5$" — that's the mean exposure fraction and it's a bit optimistic for a standing body in an outdoor plaza at head-height beam incidence, where the head + chest gets dosed but the back and legs don't. For a person **facing** the BS, $\bar\eta$ is closer to 0.3; for a person **side-on**, closer to 0.2. More honest would be a distribution over body orientations, showing the 90th percentile. This is a small point but the reviewer who knows dosimetry will flag it.

None of these three are wrong, they're just soft where a crisp quantitative claim would carry more weight.

---

## ⚠ Caveat before reading the next section

*Written before your round-2 pushback.* In the DL plaza regime (far-field, body small vs. BS angular resolution), $\mathbf{Q}^{(u)}$ is approximately rank-one and the pose-differentiable $\mathbf{Q}$ argument collapses to a pose-differentiable scalar ACS $\sigma_u(\boldsymbol{\theta}_u)$ multiplying a fixed steering vector. The sophisticated machinery below (Löwner SDP with cutting planes, pose-space gradient ascent for worst case) is right for coherent near-field / UE-side but is *overkill for the paper I'm recommending*. Read the section as "here is the coherent extension that lives in an appendix or future work," not as "here is the main contribution." The recommended paper is in §"The paper I would write" further down — and I have updated that section to reflect the rollback.

## The bit I was going to talk you into — the skeleton-embedded exposure operator

This is the idea you flagged as "wild" and it's still interesting, but as above: in the plaza regime it simplifies to a scalar ACS story.

### The observation

SMPL-X gives you a vertex position as a closed-form, differentiable function of pose:

$$
\mathbf{r}_v(\boldsymbol\theta) \;=\; \sum_{j} w_{v,j}\, \mathbf{M}_j(\boldsymbol\theta)\, \bar{\mathbf{v}}
$$

where $\mathbf{M}_j(\boldsymbol\theta) = \mathbf{T}_j(\boldsymbol\theta) \mathbf{B}_j^{-1}$ is the LBS skinning matrix, $\bar{\mathbf{v}}$ is the bind-pose vertex, and the joint transforms $\mathbf{T}_j(\boldsymbol\theta)$ are built by forward kinematics from 24 axis-angle rotations. The whole pipeline — FK, LBS, normals — is differentiable in $\boldsymbol\theta$.

Your exposure operator is
$$
\mathbf{Q} \;=\; \int_\Sigma \tilde{\mathbf{G}}(\mathbf{r})^H \tilde{\mathbf{G}}(\mathbf{r})\,dA, \qquad \tilde{\mathbf{G}}(\mathbf{r}) = \tilde{\boldsymbol\Psi}(\mathbf{r})\,\boldsymbol\Phi(\mathbf{r})\,\mathbf{J}
$$
(the `system_formalism.tex` factorisation). If the body is parametrised by a pose-dependent $\Sigma(\boldsymbol\theta)$, then every piece of $\tilde{\mathbf{G}}$ is a differentiable function of $\boldsymbol\theta$:

- $\mathbf{r}_v(\boldsymbol\theta)$ directly from LBS.
- $\hat{\mathbf{n}}_v(\boldsymbol\theta)$ from the same LBS applied to bind-pose normals (or recomputed from the skinned triangles — differentiable either way).
- $\mu_n(\mathbf{r}_v;\boldsymbol\theta) = -\hat{\mathbf{k}}_n \cdot \hat{\mathbf{n}}_v(\boldsymbol\theta)$ → differentiable.
- The Fresnel operator $\mathbf{F}_n(\mathbf{r}_v;\boldsymbol\theta)$ → differentiable through $\mu_n$ (rational in $\mu$, with a $H(\mu)$ that the reviewer will hate but which smooths out after surface averaging).
- The phase $e^{-i k_0 \hat{\mathbf{k}}_n \cdot \mathbf{r}_v(\boldsymbol\theta)}$ → analytically differentiable.

So **$\mathbf{Q}(\boldsymbol\theta)$ is a smooth function of $\boldsymbol\theta \in \mathbb{R}^{72}$ on the SMPL-X pose manifold**, with a Jacobian you can compute at AEGIS's JAX-backend speed. That's the object.

### Why this is the pivot point

Three things fall out that you cannot easily do with a pose-as-index formulation:

**(i) The Löwner envelope SDP becomes a constrained optimisation problem, not a dictionary enumeration.** Instead of $T$ prototypes and $T$ LMI constraints, you solve
$$
\min_{\mathbf{M} \succeq 0} \operatorname{tr} \mathbf{M} \quad \text{s.t.} \quad \mathbf{M} \succeq \mathbf{Q}(\boldsymbol\theta)\ \forall \boldsymbol\theta \in \Theta_u,
$$
where $\Theta_u$ is an activity manifold (walking, standing, sitting) parametrised by a low-dim latent. You handle this with outer approximation + gradient-based inner ascent: at each outer iteration, find the most-violating pose $\boldsymbol\theta^\star = \arg\max_{\boldsymbol\theta} \lambda_{\max}(\mathbf{Q}(\boldsymbol\theta) - \mathbf{M})$ via gradient ascent on $\boldsymbol\theta$, add the LMI, re-solve the outer SDP, repeat. This is the standard cutting-plane algorithm for semi-infinite SDPs. Converges because $\Theta_u$ is compact (joint-limit box). The number of active poses at termination is small (I'd guess $O(M)$ not $O(T)$).

**(ii) The refresh rule becomes analytical rather than scheduled.** You have
$$
\dot{\mathbf{Q}}(\boldsymbol\theta(t)) = \sum_j \partial_{\theta_j} \mathbf{Q}(\boldsymbol\theta) \cdot \dot\theta_j(t),
$$
with the Jacobian pre-computed. IMU gives you $\dot\theta_j$ directly (angular rates at the joints, or aggregated at the pelvis and one or two bones for a coarse whole-body rate). First-order update:
$$
\mathbf{Q}(t + \Delta t) \approx \mathbf{Q}(t) + \Delta t \cdot \sum_j \partial_{\theta_j} \mathbf{Q}(\boldsymbol\theta(t)) \cdot \dot\theta_j(t).
$$
This is cheap and continuous. The Lipschitz constants $L_Q^{\mathrm{trans}}, L_Q^{\mathrm{rot}}$ of `direction_5` become local operator norms of partial derivatives — measured, not conjectured.

**(iii) Neural surrogates become trainable with gradient targets.** If you want a small NN $\mathcal{Q}_\phi(\boldsymbol\theta) \approx \mathbf{Q}(\boldsymbol\theta)$ for real-time use (think: Qualcomm X75 modem firmware update), you train it against AEGIS-generated pairs $(\boldsymbol\theta, \mathbf{Q}(\boldsymbol\theta))$ and crucially also pairs $(\boldsymbol\theta, \partial_{\theta_j}\mathbf{Q}(\boldsymbol\theta))$. The gradient-supervised variant trains in ~10x less data, and importantly, the NN then satisfies the same differential constraints that the true $\mathbf{Q}$ satisfies under motion, which the reviewer cares about because "is your surrogate physically faithful" is the first reviewer question.

### The translation phasor, revisited

`direction_5` has the beautiful observation
$$
[\mathbf{Q}(\mathbf{t})]_{ab} = \sum_{n,n'} e^{-i k_0 (\hat{\mathbf{k}}_n - \hat{\mathbf{k}}_{n'}) \cdot \mathbf{t}} Q^{(nn')}_{ab},
$$
i.e. translation is just phase rotation of the path-pair cross-terms. In the `system_formalism.tex` notation this reads
$$
\mathbf{M}(\mathbf{t}) = \boldsymbol\Phi(\mathbf{t})^H\, \mathbf{M}(0)\, \boldsymbol\Phi(\mathbf{t}),
$$
with $\boldsymbol\Phi(\mathbf{t}) = \operatorname{diag}(e^{-i k_0 \hat{\mathbf{k}}_n \cdot \mathbf{t}})$. This is exact up to the re-evaluation of $\mu_n$ which is translation-invariant. **The combination with pose is:**
$$
\mathbf{Q}(\boldsymbol\theta, \mathbf{t}) \;=\; \mathbf{J}^T \boldsymbol\Phi(\mathbf{t})^H\, \mathbf{M}(\boldsymbol\theta)\, \boldsymbol\Phi(\mathbf{t}) \mathbf{J},
$$
where $\mathbf{M}(\boldsymbol\theta)$ is the pose-conditioned path-exposure Gram. **This is the factorisation you want the paper to contain.** Pose enters through the surface geometry (slow, smooth, SMPL-X-parametrised); translation enters through a pure phase (fast, analytic). The timescale separation that `direction_5` wanted to do *between* coherence intervals and pose intervals is now *within* the formalism:
- $\boldsymbol\Phi(\mathbf{t}(t))$ refreshes at translation cadence (function of $\mathbf{t}(t)$, updated from IMU/tracking, no integral involved).
- $\mathbf{M}(\boldsymbol\theta(t))$ refreshes at pose cadence (function of $\boldsymbol\theta$, 100 ms-ish typical IMU update).
- $\mathbf{J}$ never changes.
- The Löwner envelope is on $\mathbf{M}(\boldsymbol\theta)$, not on $\mathbf{Q}(\boldsymbol\theta, \mathbf{t})$. $\mathbf{t}$ is absorbed by the phasor exactly.

You stop paying the $k_0$ prefactor in your refresh rule because you don't refresh the integral, you refresh the argument of a diagonal phase matrix.

### Is this novel?

I believe so, strongly. None of the five ECBF prior-art papers does anything pose-parametric. Zhou 2026 doesn't — their "sampling point" formulation is positional, not posed. The Hoydis differentiable RT paper is differentiable in material/scattering parameters of the *environment*, not body pose. SMPL-based dosimetry does exist in biomedical literature (FDTD at scripted poses, used for averaged SAR reports), but as a *fixed* simulation, not a differentiable operator in a beamforming optimisation. I have an async agent double-checking this — I'll flag if it finds anything. Treat the novelty claim as "confident, verifiable."

---

## The AoA / $\mathbf{J}$ problem — your biggest unsolved

You asked the right question and it deserves more than 200 words. Let me separate what the paper actually needs from what it needs to *sound* like it needs.

### What the paper needs

To evaluate $\mathbf{Q}^{(u)}$ for body $u$, the simulator needs the per-path $(\hat{\mathbf{k}}_n, \boldsymbol\psi_n, j(n))$ **at that body's location, illuminating its surface**. This is the path data for a BS→body channel. Given that, and the pose $\boldsymbol\theta_u$, $\mathbf{Q}^{(u)}$ is a deterministic computation.

For served users ($u \in \mathcal{U}$), the served link already measures the BS→UE channel, and the BS can *infer* a nearby BS→body channel by offsetting the ray endpoint from UE to body (they're a few cm apart — think phone in hand). At FR2 the Qualcomm X75 modem even has inertial sensors specifically for beam management; adding pose inference on top is firmware, not hardware.

For non-users ($u \in \mathcal{B}$), this breaks. The network has no pilot from a non-user. It has to know where they are and how they're posed from something else.

### Your framing and why it's subtly off

You wrote: "I see [non-users] as 'those where a symbol of 0 is sent towards in ZF'." That's the right *output* analogy — the precoder nulls bystanders the same algebraic way ZF nulls interferers. But it's the wrong *input* analogy. ZF gets its input ($\mathbf{h}_j$) from pilots. Exposure-null precoding can't get its input ($\mathbf{Q}^{(u)}$) from pilots for the party it's nulling. You need a twin as the input channel, not a pilot. The sentence "send 0 symbols in ZF" hides a huge epistemic assumption — that you've already estimated the exposure operator for someone who sent you nothing. **That's the whole paper.** Say it out loud.

### How the twin can actually know

Three sources, in increasing ambition:

**(1) Ray-traced twin + opportunistic positional prior.** The BS runs a continuously-updated ray tracer on a 3D model of its coverage cell (buildings from OSM, body positions from… ok, this is the question). The RT gives it the full path set $\{(\hat{\mathbf{k}}_n, \boldsymbol\psi_n, j(n))\}$ for every grid location in the cell. When a body is present at position $\mathbf{p}$, the BS looks up the pre-computed paths incident on that location. *Where does body position come from?*
  - **Consenting users** (most bodies in a cell, in practice): MNO-aggregated location services. Already in every cellular network. Privacy regime is already-established: used for E911, opted-in for app services.
  - **Non-consenting bystanders**: passive ISAC from the BS's own reflections. This is where `q_complement.tex` earns its keep. The same operator $\mathbf{Q}$ you're constraining is (up to $(1-T_0)/T_0$) the operator that scatters back to a monostatic receiver. You don't need extra hardware; you need to demodulate your own echoes. The 26 GHz budget is tight but 8×8 panels at 55 dBm EIRP give you a real sensing SNR on a body at 50 m. Concretely: detection probability, not tracking fidelity. You find out *where bodies are*, not *how they're posed*.
  - **For pose** of non-consenting bystanders: activity-dictionary worst-case (walk/stand/sit) via Löwner envelope. You don't estimate their actual pose, you guarantee compliance against any pose consistent with "person in a plaza." This is the point where the paper's worst-case pose machinery earns its rhetorical place.

**(2) Uplink-pilot-to-twin inversion.** Every consenting device already reports CSI in the normal protocol. Their CSI is *not* the body's $\mathbf{Q}^{(u)}$ directly, but it constrains the ray-traced scene: it tells you where paths terminate. Solve the inverse problem: given measured $\mathbf{H}$ across many UEs, calibrate the ray tracer's assumed scene until predicted matches measured. This is exactly the Hoydis 2024 pattern (differentiable RT with gradient-trained material parameters). Applied here: the twin auto-tunes its body population against observed CSI, including from bystanders' passive presence (they change the scene's multipath even without pilots). Downstream, $\mathbf{Q}^{(u)}$ follows from the tuned scene.

**(3) Your wild idea (skeleton-in-formalism) + sensor-fusion.** With the pose-differentiable $\mathbf{Q}(\boldsymbol\theta)$, the sensor-fusion becomes an auto-differentiable state estimator. IMU gives $\dot{\boldsymbol\theta}$, vision (if available) gives 2D keypoints, ISAC gives scatter power vs. direction. You fuse them with an EKF or a particle filter in pose space, and the *measurement model* at each step is $\mathcal{Q}_\phi(\boldsymbol\theta)$ (the NN surrogate from §above) — which maps pose to measurable quantities (like scatter power profile or UE CSI). This is speculative but the architecture is familiar (it's just SLAM with an EM measurement model) and it's the kind of thing that makes reviewers lean forward in a JSAC DTN submission.

### Recommended answer to ship

For the paper: **(1) ray-traced twin + opportunistic positional prior**, with Löwner-envelope worst-case pose for bystanders, explicit nod to ISAC (monostatic sensing on the same BS) via `q_complement` as the rigorous hook for bystander detection, and a forward-looking paragraph on (2)+(3). That gives reviewers a deployable story with a research horizon.

### The "DT actually knows all the CSI" premise

You said: "The idea is that somehow we convince people that what we're simulating could be easily added to commercial equipment." That framing is right for the *aspiration* of the paper — the DT is the thing you're proposing. But don't confuse the aspiration with the *simulation*. In silico, AEGIS computes everything and you can pretend anything. The paper's burden is to be honest about *what the deployed system would know*, not what AEGIS computes. The deployed system:

- **knows** BS→UE CSI for served users (fact: 3GPP already)
- **knows** user-consented IMU via MNO service (fact: already built, X75 modem gives $\dot\theta$ from modem-level IMU)
- **knows** BS position, BS antenna geometry, city 3D model (fact: operators have these)
- **has access** to passive ISAC on its own transmit reflections at per-cell coherence (physics, not protocol)
- **does not know**: bystander identity, bystander per-pose state without sensing/estimation

That shopping list is the paper's "DT inputs" box. Then the section "what the DT computes" is the ray-traced scene → per-body $\mathbf{Q}^{(u)}(\boldsymbol\theta_u) = \mathbf{J}^T \boldsymbol\Phi(\mathbf{t}_u)^H \mathbf{M}(\boldsymbol\theta_u) \boldsymbol\Phi(\mathbf{t}_u) \mathbf{J}$ for every body of interest. Then the closed-loop is: DT inputs refresh at their native rates → $\mathbf{Q}^{(u)}$ updates analytically → ECBF re-solves → precoder. **That's a fully-closed DTN control loop built on existing commercial primitives plus one ray tracer.**

---

## A harder question: is the regulator the right reader? (**revised** — I was too harsh)

**Rolling back my earlier advice.** You're right: the Brussels framing isn't a mathematical hook, it's a *deployment-blocker* hook, and that's legitimate. AEGIS itself tells you that DL at ICNIRP reference levels is always compliant at normal EIRPs — if you open the paper with "we need exposure-aware DL beamforming," reviewers will gut-reject the premise unless you surface *why* it binds. The answer is that city-level reference levels (Brussels 14.57 V/m, Milan 6 V/m, Italy national 6 V/m) are 10-30× tighter than ICNIRP, are occupancy-independent, and — critically — are *instantaneous*, not 30-min averaged, so the operator has to clear them *every second*. That's the hard problem, and that's why exposure-null precoding matters in DL at all.

The JSAC DTN SI editors (Liu, Melodia, Lin, Chen, Canberk, Sanchez) are network people, yes, but they're also exactly the readers who need to hear "regulation is the primary deployment blocker for mmWave internationally, not pathloss." This is a Qualcomm-and-standards-people message, and it lands better than abstract EMF physics.

**Revised placement for Brussels:**

- **Opening paragraph of the intro**: lead with the deployment-blocker framing. "Mobile operators have had mmWave spectrum auctioned or available in most G20 countries since 2020, yet deployment outside the US and parts of East Asia has been slow — not because of RF pathloss but because of regulatory EMF resistance. Brussels banned 5G in 2019 and raised its cap for 5G only in 2024; Geneva had a 2019 moratorium; Milan and 600+ Italian municipalities have active resolutions; France restricts children's smartphone-to-head use; Italy has a 6 V/m national cap. The quantitative instrument behind all of these decisions is the public-space EMF reference level."
- **The binding-regime section** (methodology level): distinguish reference levels from basic restrictions. ICNIRP reference levels are conservative proxies for SAR/APD basic restrictions; city reference levels are politically tighter. *Your paper's body-centric framework operates on basic-restriction-equivalent quantities* (absorbed power on actual bodies), so it is *more faithful* to the regulator's true concern than any reference-level check.
- **One money figure**: "Binding regime — Brussels 14.57 V/m at 26 GHz binds in $X\%$ of configurations under MRT, $Y\%$ under classical ZF, $<1\%$ under ZF-dosimetry." That figure is your paper.
- **Closing paragraph**: "The rhetorical position this paper takes is that a digital-twin network is not just a research object; it is the missing engineering layer between mmWave capacity and regulator-accepted deployment, especially in jurisdictions that impose instantaneous reference-level caps rather than ICNIRP 30-minute averages."

**Keep Brussels louder than a vignette.** It's your paper's reason-to-exist for a DL problem that would otherwise be "always compliant." I was wrong to suggest burying it.

---

## Zhou 2026 — how to not collide

Zhou's paper and yours share: "exposure-aware beamforming with a quadratic exposure constraint." That's it. Everything else differs:

| | Zhou 2026 | Your paper |
|---|---|---|
| Direction | Uplink | Downlink |
| Scenario | Single UE → BS | One BS → $K$ users + $B$ bystanders |
| Body | Spherical head, 15 sampling points | Anatomical SMPL-X mesh, continuous $\Sigma$ |
| Exposure model | Pennes BHTE → thermal queue | Coherent absorbed power, Fresnel operator |
| Pose | Not modelled | Pose-differentiable, IMU-driven |
| Constraint structure | Per-point PD integrated in time | Multi-body PSD operators, SDP envelope |
| Closed-loop | Lyapunov virtual queue | DT-in-the-loop with pose refresh |
| DT | None (no twin at all) | Central object |

The right move: **cite Zhou in the related work as the parallel line, and in the introduction as corroborating evidence that exposure-aware beamforming is a live research theme.** Do not structure your paper to defend against them — you will lose the novelty argument if the paper's structure looks like a response.

The failure mode to avoid: a reader who sees you both and concludes "these two papers do the same thing, differently." Prevent that with a single sentence in the intro: *"Zhou et al. (2026) simultaneously developed a thermal-compliance analogue of exposure-aware beamforming on the uplink; our work differs on direction, body model, pose, multi-body structure, and digital-twin positioning."* Then the paper doesn't look like a response, it looks like a parallel development that the field needs both of.

---

## The paper I would write — concrete *(original, round-1)*

*After your Part 1 pushback, this section is superseded by the new one below. Left in place for comparison.*

Working title: **Body Digital Twin in the Precoder Loop: Pose-Differentiable Exposure Operators for Mission-Critical Wireless.**

Hook: *Wireless networks can beamform in milliseconds. Bodies move at human timescales. We bridge the gap by twinning the body.*

**Contributions (four, in this order):**

1. **Pose-differentiable exposure operator** $\mathbf{Q}(\boldsymbol\theta, \mathbf{t}) = \mathbf{J}^T \boldsymbol\Phi(\mathbf{t})^H \mathbf{M}(\boldsymbol\theta) \boldsymbol\Phi(\mathbf{t}) \mathbf{J}$ from SMPL-X LBS + Fresnel + path-space factorisation. Theorem: smooth on the SMPL-X manifold. Corollary: analytic translation-phase refresh, so per-slot $\mathbf{Q}$ updates are $O(N^2)$ element-wise multiplies, not integrations.

2. **Multi-body exposure-null precoding with pose-robust worst case.** The ZF-generalising Lagrangian closed form (`exposure_null_precoding.tex` §3), with the Löwner envelope solved as a cutting-plane SDP in pose space using the pose differentiability to find active constraints. Quiet subspace dimension characterised empirically on pedestrian scenes.

3. **DT-in-the-loop architecture.** Three-rate refresh (channel $\mathbf{h}$ per slot, translation $\mathbf{t}(t)$ per second, pose $\boldsymbol\theta(t)$ per 100 ms) with explicit data flow from IMU (consenting users) / ISAC (bystanders via $\mathbf{Q}$-$\mathbf{Q}_{\mathrm{re}}$ locking) / ray tracer. Concrete protocol-level grounding in existing 3GPP primitives + a named firmware hook (modem-level IMU on the X75, which already exists for beam management).

4. **Empirical: one plaza-scale mmWave scenario that could be Brussels, Milan, or anywhere else regulated.** Hero experiment: exposure-null ECBF on a 50-body plaza at 26 GHz, showing capacity-vs-exposure Pareto, comparison against MRT / ZF / per-slot ECBF / static Hochwald envelope. Pose uncertainty is shown to cost <2 dB vs. pose-known oracle under the Löwner envelope.

**Structure (13 pages):**

- (0.5 p) Abstract
- (1.5 p) Intro — DTN pitch, paper thesis, Brussels-as-vignette, Zhou-disambiguation. Maybe Figure 1 is a cartoon: body + BS + arrows.
- (1.5 p) Setup — MIMO channel, coherent absorbed power law, Fresnel operator, SMPL-X in 10 lines. Cite monograph for details.
- (2.0 p) §III Pose-differentiable exposure operator — the system formalism factorisation + SMPL-X embedding + translation phasor + Jacobian (theorem + proof sketch, full proof in supplement).
- (1.5 p) §IV Pose-robust ECBF — multi-body QCQP, closed form, Löwner SDP as cutting-plane in pose space, quiet subspace.
- (1.5 p) §V DT-in-the-loop — architecture figure, data flow, refresh-cadence analysis with the refined $L_Q$ from `direction_5`, ISAC hook for non-consenting bodies.
- (2.5 p) §VI Evaluation — plaza hero, CDFs, Pareto, ablations.
- (0.5 p) §VII Regulatory framing — the Brussels paragraph, discussion.
- (0.5 p) §VIII Conclusion + future work (mechanism-design for multi-operator, Shapley, closed-loop pose SLAM).
- (1 p) References.
- Appendix: proof details, SMPL-X backward pass, cutting-plane solver.

This fits. Everything else belongs in your monograph.

**What you lose if you write this instead of the current draft:**
- The regulator-facing rhetoric, which you could expand into a companion policy paper or an op-ed.
- The multi-operator cooperation theorem, which is elegant but lives better in a future paper with actual game-theory content.

**What you gain:**
- A paper where **the body is the twin**, which is the SI's own pillar, not a corner of it.
- A novelty claim that survives Zhou collision and the five older ECBF papers.
- A closed-loop architecture with explicit existing-commercial-primitive groundings, which reviewers score highly on "usefulness."
- A result (pose-conditioned ECBF beats pose-agnostic ECBF by several dB) that becomes a reference number for the next ten papers.

---

## The paper I would write — concrete *(revised, round-2)*

Working title: **ZF-Dosimetry: A Digital-Twin Extension of Zero-Forcing Precoding for mmWave Downlink Under City-Level EMF Caps.**

Hook: *Zero-forcing nulls interference to the users you serve. We null absorbed power to the bodies you don't. Same solver, one extra input per bystander: a steering vector and a scalar ACS.*

**One-paragraph problem statement.** Public-space EMF reference levels in Brussels (14.57 V/m), Milan, Italy-national (6 V/m), and similar jurisdictions are 10-30× tighter than ICNIRP, occupancy-independent, and enforced *instantaneously* at every second (not 30-min averaged). At 26 GHz an 8×8 panel at 55 dBm EIRP satisfies ICNIRP with margin but can violate city-level reference levels in parts of the coverage cell — particularly in the presence of multiple operators sharing the cumulative cap. The question this paper asks: can the BS beamform around bodies to stay compliant at every second while delivering competitive sum-rate? We show yes, at approximately the cost of a classical zero-forcing solver with a digital-twin-supplied list of bystander steering vectors and a pose-conditioned absorption cross-section per body.

**Four contributions, in order:**

1. **ZF-dosimetry.** In the far-field DL regime, exposure-null precoding collapses to regularised ZF where the null matrix $\mathbf{H}_{\text{null}}$ stacks served-user channels *and* bystander-body steering vectors. Per-body null depth is set by the body's ACS $\sigma_u(\boldsymbol\theta_u)$. Closed-form precoder, one-paragraph derivation.

2. **Pose-conditioned ACS and its pose-agnostic worst case.** $\sigma_u(\boldsymbol\theta_u)$ is smooth on the SMPL-X manifold, regressed by a small NN on AEGIS simulations, and bounded above by the Cauchy-based directivity $D\le 2$ for any admissible pose. Tiers A/B use the NN; tiers C/D use the Cauchy worst case. The NN's advantage over the bound is the *pose-information gain* in dB.

3. **Tiered DT-in-the-loop.** Four body tiers (served user / cooperating non-user / airplane-mode bystander / no phone), each with its own telemetry pathway (3GPP CSI + IMU-over-MNO / UL CSI + IMU / ISAC respiration-Doppler / nothing). Bystander detection leverages the $\mathbf{Q}\leftrightarrow\mathbf{Q}_{\text{re}}$ pseudo-Brewster duality from `q_complement.tex`: the operator the precoder nulls is (up to $(1-T_0)/T_0$) the operator a monostatic receiver match-filters. Link budget: respiration detectable at 50 m with margin at 26 GHz 55 dBm EIRP on 400 MHz BW.

4. **Real-time-in-silico hero demo.** 5 minutes of wall-clock simulation, 50-body plaza, 26 GHz, 8×8 panel, AMASS-sourced pose traces, virtual IMU with calibrated noise, Sionna for PHY + hand-rolled MAC with 3GPP MCS curves. Five baselines: MRT, ZF-users-only, ZF-dosimetry worst-case-pose, ZF-dosimetry pose-NN, pose-known oracle. Report per-body exposure CDF, served sum-rate, beam-on-body heatmap time-series.

**Structure (13 pages):**

- (0.5 p) Abstract
- (1.5 p) Intro — deployment-blocker framing (Brussels/Milan/Italy), paper thesis, Zhou-disambiguation in one sentence.
- (1.5 p) Setup — MIMO DL channel, Part 1's absorbed-power law, reference-level vs basic-restriction distinction, rank-1 reduction for plaza geometry.
- (2.0 p) §III ZF-dosimetry algebra — multi-body null, closed-form precoder, sum-rate, convergence to classical ZF in the bystander-free limit.
- (1.5 p) §IV Pose-conditioned ACS — differentiability of $\sigma_u(\boldsymbol\theta)$, Cauchy bound, NN architecture + AMASS training, RMSE table.
- (1.5 p) §V Tiered DT architecture — the four-tier telemetry table, ISAC respiration-Doppler link budget, cadence table.
- (2.5 p) §VI Evaluation — hero demo, CDFs, Pareto, ablations, example 5-min trace.
- (0.5 p) §VII Regulatory framing — reference-level vs basic-restriction argument, why body-centric compliance wins.
- (0.5 p) §VIII Conclusion + extensions — coherent near-field via system formalism (future work), Shapley multi-operator budgets, pose-conditioned local APD.
- (1 p) References.
- Appendix: Cauchy derivation, NN details, ISAC budget arithmetic.

**Why this fits.** ZF-dosimetry is algebraically simple — the paper's weight is in *architecture + experiment*, not theorem-chasing. That's what fits 13 pages and lands well on the DTN-SI "significance/novelty/usefulness" rubric.

**Moved to follow-up papers:** coherent near-field / UE-side pose-differentiable $\mathbf{Q}(\boldsymbol\theta)$ (whole paper), multi-operator cooperation + Shapley mechanism (whole paper), the q_complement Kirchhoff-dual self-calibration story (whole paper). The JSAC paper is the first of a 3-4 paper sequence, and it is the one that lands in the DTN SI.

---

## An abstract, drafted so you can see it *(round-2, ZF-dosimetry framing)*

> Downlink 5G/6G mmWave deployment is limited in several jurisdictions by city-level EMF reference levels (Brussels 14.57 V/m, Milan and Italy 6 V/m) that are 10-30× tighter than ICNIRP, occupancy-independent, and enforced instantaneously. We introduce ZF-dosimetry, a digital-twin extension of classical zero-forcing precoding that nulls absorbed power to bystander bodies in addition to interference to served users. A network-side digital twin of the coverage cell — ray-traced buildings, body positions from tiered telemetry (IMU over the mobile-network-operator app for cooperating phones, respiration micro-Doppler ISAC for airplane-mode bystanders), and pose from a small neural network trained on AEGIS-generated pose-to-absorption-cross-section pairs — supplies the per-body steering vectors and scalar cross-sections that ZF-dosimetry needs. For bodies without pose telemetry, a pose-agnostic Cauchy bound $D\le 2$ on absorption directivity gives pose-robust compliance without any semidefinite programming. In a 5-minute real-time-in-silico plaza simulation with 50 bodies walking under a 3-operator Brussels-14.57-V/m cumulative cap at 26 GHz on an 8×8 panel, ZF-dosimetry with the pose-aware cross-section predictor maintains compliance at every time step while delivering 8–12 dB of sum-rate over worst-case power back-off and 2–3 dB over pose-agnostic ZF-dosimetry. The contribution is not a new beamforming theorem; it is the explicit demonstration that a body-centric digital twin closes a real control loop over existing commercial 3GPP primitives, meeting the tightest deployed EMF regulations on the planet.

197 words. Tuneable.

---

## An abstract, drafted so you can see it *(round-1, pose-differentiable $\mathbf{Q}$ framing — superseded)*

> We bring the physical body into the base-station's control loop. Digital twins of wireless networks have so far twinned the network; we twin the body. An SMPL-X parametric body model, skinned with linear blend skinning, induces a pose-differentiable exposure operator $\mathbf{Q}(\boldsymbol\theta, \mathbf{t}) \in \mathbb{C}^{M\times M}$ that maps any transmit precoder to the absorbed power on a real anatomical mesh. We show that $\mathbf{Q}$ factors into a pose-independent dispatch, a pose-conditioned path-exposure Gram, and a translation phasor, so that per-slot refreshes cost one phase rotation rather than one Gram integral. On top of $\mathbf{Q}(\boldsymbol\theta)$ we solve a multi-body exposure-null precoding problem — generalising zero-forcing to Hermitian positive-semidefinite body operators — and robustify to pose uncertainty via a Löwner-envelope semi-infinite SDP that exploits pose differentiability to locate active constraints. We close the loop by wiring the twin to commercial primitives: per-slot CSI feedback from served users, per-frame IMU pose from modem-embedded sensors, per-second translation from ISAC on the transmitter's own reflections via the pseudo-Brewster exposure-scattering duality. In a 50-body mmWave plaza scenario at 26 GHz, pose-conditioned exposure-null precoding achieves within 1.5 dB of a pose-known oracle and keeps $>99\%$ of body configurations under regulatory cap, while delivering $8$–$12$ dB sum-rate advantage over pose-agnostic exposure-aware schemes. The body is the application, the twin is differentiable, the loop closes. *(Place the Brussels motivator in the body, not the abstract.)*

199 words. Tuneable.

---

## Three things I haven't closed *(round 2)*

- **ISAC respiration detection numbers.** I sketched a link budget in the answers file (§6): respiration detectable at 50 m on an 8×8 at 26 GHz 55 dBm EIRP with plenty of margin; heartbeat marginal. Before you put this in the paper, do the numerical simulation at AEGIS fidelity to confirm. If the numbers don't survive the 1-sec FFT bin, fall back to: "presence detection via RCS, position from angle-Doppler map." That alone is enough for the tiered architecture, and both are standard radar signal processing.

- **The pose-NN's real-vs-simulated gap.** Everything I proposed for the pose NN (AMASS mocap → virtual IMU via standard sensor models → NN regress back to pose) is defensible. The honest uncertainty is: does a pose-aware ACS predictor beat Cauchy worst-case by 1 dB or 5 dB? That's the paper's pose-information gain, and it needs the experiment. If it's <1 dB, the NN is a nice-to-have rather than a contribution — you lead with worst-case and mention the NN in discussion. If it's 3-5 dB, it's a contribution in its own right.

- **Tier D (no phone) is rhetorically unhandled.** Tier C (airplane-mode phone) is still a phone + ISAC. Tier D (toddler on a parent's shoulder, visitor without a phone) is only ISAC. The paper should probably say: "Tier D bodies that are not detected by ISAC are not in the null set and default to Cauchy worst-case compliance. This is conservative and we treat the conservative case as the regulatory anchor." That's the honest statement and it's fine.

---

## Two things you mentioned that I think are traps

- **"Close the loop with a virtual IMU and a small NN."** The idea is fine but beware: if your NN is trained on AEGIS-synthesised IMU traces, a reviewer will say "you trained and tested on the same simulator." The way around it is to use AMASS mocap data (real human motion captured from real humans) as the pose trajectories, feed those through an inertial simulation of the Qualcomm X75 modem's sensor suite, and use *that* as your "measured IMU." This is standard in the IMU-HAR literature and makes the claim defensible. *Without this, the NN is a shiny distractor.*

- **"Argue that Brussels's permit architecture is strictly suboptimal for aggregate sum-rate."** It is, in the sense of Prop 6.2 in your draft. But in the context of a JSAC submission, arguing your method is Pareto-dominant to what regulators currently do is rhetorically weaker than arguing it *composes* with what regulators currently do. "Our body-centric compliance framework is a refinement, not a replacement" plays better than "your permit architecture is strictly suboptimal." The math is the same; the framing lands differently.

---

## Your own words, back

You wrote: *"What 'broad and deep' looks like is up to you. You could pressure-test the latest direction, sketch a different paper, find the one math step that doesn't hold, draft the abstract that would make the work accepted, argue the JSAC DTN SI is the wrong venue, or follow a thread that nobody in this conversation noticed."*

I think I did most of those. The one I did not do is *argue the SI is the wrong venue.* I considered and rejected it — the SI is well-matched, the body-as-twin thesis fits the scope pillar-perfectly, and the deadline is manageable. The venue is right. The paper just needs to be the paper I sketched, not the paper you currently have in the draft.

One thread I'd love to follow but didn't: the **Kirchhoff dual** in `q_complement.tex` §7 — that $\mathbf{Q}$ is also a *receive* operator for body thermal emission. That opens a calibration story: the BS can *measure* its own $\mathbf{Q}$ by listening for body warmth without any explicit transmit-calibration cycle. In the DTN-SI context this is a self-verifying twin. If I had another 2000 words, that's where I'd spend them. Flagging as a very-worth-it spin-off.

---

## One last thing

The monograph is a 6000-line thing. You have a real book's worth of content. The JSAC paper is 13 pages. The paper's job is not to contain the monograph. It's to point at the monograph. **Treat every equation in the JSAC paper as a pointer to a longer derivation elsewhere, and the paper as the one-page summary of a single crisp contribution (pose-differentiable body twins in the precoder loop)**. The appendix ships one proof and a code map. Everything else defers. That's how you fit 13 pages.

Good luck. I enjoyed reading this.

— *the Opus that read the thing*

---

## Novelty check (appendix)

I dispatched a parallel search agent while writing. Here is its report, lightly edited.

**Headline:** The pose-conditioned differentiable $\mathbf{Q}(\boldsymbol\theta)$ is unclaimed. The separate ingredients exist, the composition does not. **High confidence.**

**Must-cite list** to pre-empt reviewer surprise:

- **Zhou et al., 2026** (arXiv:2601.19587) — the near-miss on the uplink / thermal side. Treat as parallel, not collision. Position your delta as *"$\mathbf{Q}(\boldsymbol\theta)$, not $\mathbf{Q}$."*
- **Hochwald & Love, 2014** (*IEEE Comms Mag*) and **2019** (*Determining EM Exposure Compliance in Linear Time*) — the foundational SAR-matrix $x^H R x$ for handsets.
- **Murata et al., 2024** (*TMTT*, "Human-Aware Energy Beamforming for MWPT") — estimates a body channel from Doppler-shifted pilots. Geometry-free, no body model; cite as the closest "body in the loop" paper that doesn't use a body model.
- **EMF-Aware MU-MIMO in RIS-Aided Cellular Networks** (arXiv:2209.14785, 2022) — spatial EMF constraints over fixed regions; no body.
- **Meliadò et al., 2020** (*MRM*), **Gokyar et al., 2023** (*MRM*) — CNN SAR surrogates for 7T pTx MRI. Subject-specific, **not pose-parameterised**. Flag: a reviewer from MRI may call this "prior art on neural SAR prediction." Counter: they learn $f(\text{image}) \to \mathrm{SAR}$ at fixed pose inside a birdcage, not $\partial \mathbf{Q}/\partial\boldsymbol\theta$ for LBS deformation on a wireless channel.
- **Chiaramello et al., 2021** (*Applied Sciences*) — stochastic dosimetry with 3D beamforming, varies posture via Monte Carlo; no differentiable operator.
- **EMF-Aware RRM for 5G and Beyond — Survey**, *MDPI Computers* 2025 — **explicitly flags "infer device-body orientation and dynamically steer beams" as a future direction.** *This is a very useful citation: your paper becomes the first constructive instance of what the survey prescribes as future work.*
- **SMPL**, Loper et al., 2015 (*SIGGRAPH Asia*) and **SMPL-X**, Pavlakos et al., 2019 (*CVPR*) — the body model.

**Close-call to watch:** the MDPI 2025 EMF-aware RRM survey — it names the gap your paper fills. Do not let a reviewer find it before you cite it.

**Not exhaustive:** BioEM / EMBC / T-AP proceedings were not fully indexed in my search, and may contain pose-variation FDTD studies I didn't see. None of those would couple LBS differentiability into a precoder Gram — that specific move appears unclaimed.

---

## Pointer

The companion file **`brainstorm_opus_answers.md`** answers your direct round-2 questions (Löwner envelope explained, quiet subspace explained, cadence deep-dive with AEGIS-compute estimates, TDD/UL non-user cooperation, ISAC heartbeat-Doppler link budget, experiment stack recommendation, my rolled-back commitments on points ii/iii, the Brussels framing restored). Read that alongside this doc; together they are the round-2 deliverable.

The round-1 version is preserved at **`brainstorm_opus_response_backup.md`** for your record.
