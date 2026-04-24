# Brainstorm response — JSAC DTN paper

*Outside read, written for Robin. By Claude (Opus 4.7, 1M ctx), 2026-04-24.*
*Everything here is an opinion formed from reading: `theory/exposure_null_precoding.tex`, `theory/system_formalism.tex`, `theory/q_complement.tex`, `theory/monograph_v2.tex` (partial), `JSAC/directions/direction_5_math_opus_codex.tex`, `JSAC/directions/direction_4_problem_codex_opus.tex`, `JSAC/related_works/2601.19587_transcription.tex`, `JSAC/UE_hardware/direction_5_ue_hardware_summary.md`, `skeletal-animation-primer/README.md`, `JSAC/representative_papers/review.md`, `JSAC/JSAC_SI_digital_twins.md`, `JSAC/author_guidelines/SUMMARY.md`.*

---

## Before anything else — the one paragraph

The strongest paper hiding in what you've got is **not** the Brussels paper. It's the paper where **the body itself is the twin** — pose-conditioned, differentiable, and wired into the precoder via the system-formalism's $\mathbf{Q} = \mathbf{J}^T \mathbf{M} \mathbf{J}$. Brussels is a motivator you mention in 200 words of the intro and cite on a figure caption. The monograph already gives you a pre-diagonalised coherent dosimetry pipeline; `system_formalism.tex` is genuinely beautiful and is what makes this paper land; `direction_5` gives you the translation phasor that turns pose motion into an analytic refresh; `q_complement` gives you a sensing-exposure duality that closes the loop for non-users without needing their pilots. That's the package. The Brussels framing is a good vignette, not a thesis.

If you spend 50% of the paper on Brussels ordinances and cumulative-operator QCQPs, reviewers will put it in their "regulatory-compliance MIMO" bucket, where it competes with Zhou 2026 and the five older ECBF prior-art papers. If you spend 50% on pose-differentiable exposure operators and DT-closed-loop compliance, it goes in a bucket where it is the only paper. The CFP's bucket, incidentally.

So: **twin the body, not the ordinance.** Everything below is me thinking through why, and what has to be true for it to work.

---

## Epistemic inventory

Because you asked me to be honest about confidence — here's where I stand before I argue anything.

- **Confident (≈ reasonably sure, checked myself):**
  - The path-space factorisation in `system_formalism.tex` is correct and is load-bearing.
  - The identifiability no-go in `direction_5` is correct (construction works).
  - Translation kills $\mathbf{Q}$ sub-wavelength at 28 GHz (the $k_0$ prefactor argument).
  - Zhou 2026 is parallel, not collision — different problem setting.
  - None of the ten representative papers twins the body or treats APD as a first-class control objective.
- **Suspect (plausible, not checked end-to-end):**
  - The Löwner low-rank conjecture will fail in general but hold in useful subsets.
  - The pseudo-Brewster eigenvector locking survives reviewer scrutiny for skin at 28 GHz but weakens off-pseudo-Brewster (below 6 GHz).
  - The quiet subspace will be less generous than `prop:dim` suggests, because real $\mathbf{Q}^{(u)}$ are structured, not random.
- **Genuinely uncertain (where I'd want to run something):**
  - Whether SMPL-X LBS differentiability carries through the surface Fourier kernel cleanly (the skeleton-embedding claim).
  - Whether a small NN can reliably regress $\mathbf{Q}(\theta)$ from pose — training data story is thin.
  - Whether ISAC-based pose estimation of bystanders is accurate enough at 26 GHz on a single 8×8 panel.

I'll flag confidence again as things come up.

---

## The math, line-by-line — what I'd double-check

Mostly clean. Three places I'd look twice:

**1. `exposure_null_precoding.tex` Prop 4.2 (quiet subspace dimension).** The bound $\dim \mathcal{Q}(\mathcal{B}) \ge \max(0, M - \sum_u r_u)$ is correct as a worst-case bound on subspace intersections — that's just iterated $\dim(V_1 \cap V_2) \ge \dim V_1 + \dim V_2 - M$. But the rhetorical use of it ("the quiet subspace is generically nontrivial") is shakier than the bound itself. **Generic** subspaces achieve the bound with equality. **Structured** subspaces — which is what $\ker \mathbf{Q}^{(u)}$ are — can be smaller or larger. In the small direction: if two bodies are illuminated from nearly the same BS aperture, their kernels overlap almost completely and you have *more* quiet subspace than generic. In the large direction: if they're back-to-back across the BS, intersection shrinks. The empirical question isn't "is the quiet subspace nontrivial," it's "how much of it survives once you demand $\rho$-alignment with actual UE channels." I'd drop the "generic nontriviality" phrasing and show a CDF of $\dim \mathcal{Q}_\varepsilon / M$ over a scene ensemble instead.

**2. `q_complement.tex` Prop 3.2 (eigenvector locking $\mathbf{Q}_{\mathrm{re}} \approx \frac{1-T_0}{T_0} \mathbf{Q}_{\mathrm{ab}}$).** The proof sketch says "the outgoing-direction change $\hat{\mathbf{k}}_n \to \hat{\mathbf{k}}_n^{\mathrm{re}} = \hat{\mathbf{k}}_n + 2\mu_n \hat{\mathbf{n}}$ affects only the per-point phase $e^{-i k_0 \hat{\mathbf{k}} \cdot \mathbf{r}}$, which is a unitary factor … it leaves $\mathbf{G}^H \mathbf{G}$ invariant up to the sign of cross-element phases that integrate out on $\Sigma$." I believe the first part (the Gram is unitarily invariant under a global phase). I'm **less** convinced the cross-element phases "integrate out" in general. For a flat patch, yes — the surface Fourier component at $\mathbf{q}_{nn'}^{\mathrm{re}} = k_0(\hat{\mathbf{k}}_{n'}^{\mathrm{re}} - \hat{\mathbf{k}}_n^{\mathrm{re}})$ is different from the one at $\mathbf{q}_{nn'} = k_0(\hat{\mathbf{k}}_{n'} - \hat{\mathbf{k}}_n)$, and they integrate to different values against a non-flat body. So the off-diagonal $\mathbf{M}$ entries of $\mathbf{Q}$ and $\mathbf{Q}_{\mathrm{re}}$ differ beyond the scalar factor. I'd expect the proportionality to hold *on diagonal / top eigenvalue* cleanly, and on the full operator only up to a larger-than-5% residual for bodies with curvature on the wavelength scale (which is everything at 28 GHz). Worth a numerical check on thelonious before you put "5%" in the abstract.

**3. `exposure_null_precoding.tex` equation (38) back-of-envelope: "Brussels outdoor cap $\approx 0.19$ W absorbed on a body."** The arithmetic ($T_0 \times |\Sigma| \times S_{\mathrm{lim}}/2 \times \bar\eta$ with $\bar\eta \approx 0.5$) is fine given the inputs. The issue is "$\bar\eta \approx 0.5$" — that's the mean exposure fraction and it's a bit optimistic for a standing body in an outdoor plaza at head-height beam incidence, where the head + chest gets dosed but the back and legs don't. For a person **facing** the BS, $\bar\eta$ is closer to 0.3; for a person **side-on**, closer to 0.2. More honest would be a distribution over body orientations, showing the 90th percentile. This is a small point but the reviewer who knows dosimetry will flag it.

None of these three are wrong, they're just soft where a crisp quantitative claim would carry more weight.

---

## The bit I want to talk you into — the skeleton-embedded exposure operator

This is the idea you flagged as "wild" and I think it's the strongest move available.

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

## A harder question: is the regulator the right reader?

Your current draft positions the paper *for* a regulator — "we propose to give Bruxelles Environnement an auditable twin." That framing has a subtle trap.

The JSAC DTN SI's guest editors (Liu, Melodia, Lin, Chen, Canberk, Sanchez) are *network* people. Their evaluation criteria (significance / novelty / usefulness) are network-research criteria, not regulatory-science ones. A reviewer from Northeastern or NVIDIA reading "Brussels ordinance permit architecture is strictly suboptimal for aggregate sum-rate" thinks "interesting, irrelevant to my decision loop on whether this paper teaches me something new about DTNs." A reviewer reading "body-pose-differentiable exposure operator closes a DT-in-the-loop at IMU cadence, achieving 12 dB gain over pose-agnostic ECBF and never violating compliance" thinks "this is the template I will show my students."

**Keep the Brussels story, but demote it.** It belongs in:
- **One figure**: "Binding regime — the Brussels 14.57 V/m cap at 26 GHz binds in $X\%$ of pedestrian configurations under MRT, $Y\%$ under classical ZF, and $<1\%$ under pose-conditioned ECBF." This is the paper's money figure.
- **One paragraph in the intro**: "Regulatory caps at the city scale (Brussels 2024, Italian municipalities, Geneva 2019) are tightening faster than ICNIRP, which makes compliance a binding design variable at mmWave rather than a margin-check. A body-centric DT that bounds absorbed power on actual bodies is both more permissive and more defensible than the free-space exclusion-zone approach."
- **One paragraph in the discussion**: "The body-centric compliance framework we develop is compatible with regulator-facing audit protocols." One reference to a future paper on that.

Do not write the paper *to* the Brussels regulator. The regulator isn't a reviewer. Write *through* Brussels *to* the JSAC reviewer.

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

## The paper I would write — concrete

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

## An abstract, drafted so you can see it

> We bring the physical body into the base-station's control loop. Digital twins of wireless networks have so far twinned the network; we twin the body. An SMPL-X parametric body model, skinned with linear blend skinning, induces a pose-differentiable exposure operator $\mathbf{Q}(\boldsymbol\theta, \mathbf{t}) \in \mathbb{C}^{M\times M}$ that maps any transmit precoder to the absorbed power on a real anatomical mesh. We show that $\mathbf{Q}$ factors into a pose-independent dispatch, a pose-conditioned path-exposure Gram, and a translation phasor, so that per-slot refreshes cost one phase rotation rather than one Gram integral. On top of $\mathbf{Q}(\boldsymbol\theta)$ we solve a multi-body exposure-null precoding problem — generalising zero-forcing to Hermitian positive-semidefinite body operators — and robustify to pose uncertainty via a Löwner-envelope semi-infinite SDP that exploits pose differentiability to locate active constraints. We close the loop by wiring the twin to commercial primitives: per-slot CSI feedback from served users, per-frame IMU pose from modem-embedded sensors, per-second translation from ISAC on the transmitter's own reflections via the pseudo-Brewster exposure-scattering duality. In a 50-body mmWave plaza scenario at 26 GHz, pose-conditioned exposure-null precoding achieves within 1.5 dB of a pose-known oracle and keeps $>99\%$ of body configurations under regulatory cap, while delivering $8$–$12$ dB sum-rate advantage over pose-agnostic exposure-aware schemes. The body is the application, the twin is differentiable, the loop closes. *(Place the Brussels motivator in the body, not the abstract.)*

199 words. Tuneable.

---

## Three things I haven't closed

- **The ISAC-for-bystanders claim is optimistic without evidence.** You and I both want `q_complement` to earn its keep, but "monostatic detection of an unpiloted 50 kg body at 50 m on an 8×8 panel at 26 GHz EIRP" is a real radar problem and a reviewer will ask for the link budget. I think it works at low-confidence detection (is there a body in this angular cell) and fails at tracking (how fast is this body walking). The paper should over-claim detection, under-claim tracking, and show that the Löwner envelope over walk/stand/sit dictionary is what makes the under-claim OK.

- **The pose-differentiable $\mathbf{Q}$ is pretty but needs one empirical check.** The Fresnel $\mathbf{F}_n(\mathbf{r}; \boldsymbol\theta)$ has an indicator $H(\mu_n)$ that is non-differentiable at $\mu_n = 0$ (the silhouette). In practice you replace it with a smooth $\mathrm{sigmoid}(\mu_n/\epsilon)$ or a diffraction-smoothed version (Part I of the monograph has this). But the smoothed version has a corresponding Jacobian support that blows up at silhouette — the self-shadowing transitions of `direction_5` §3.4. I think this is fine *on average* (silhouette is a measure-zero subset of $\Sigma$) but may have some bad pose directions where a joint rotation near a silhouette tangent gives a large Jacobian. Needs a plot. If it works, great; if not, the mitigation is "Löwner envelope over a box around the silhouette region," which is a small epsilon ball, and you still get the architecture.

- **The pose source for non-consenting bystanders is the paper's weakest link.** I've argued for "activity-dictionary worst-case with ISAC locator." A stronger but more speculative move: opt-in public pose broadcasting via a standardised privacy-preserving protocol ("safety beacon"), where phones voluntarily broadcast a coarse activity-class label without identity. This would be its own paper elsewhere, but a nod in the Discussion ("a public-pose privacy layer could strengthen bystander guarantees") threads the needle without sending your paper down a non-technical rabbit hole.

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
