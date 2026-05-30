# Critique of `rihb_theory.tex` v1

Reviewer voice: a JSAC SI guest editor, plus my own honest read after a few hours of distance. References below are to v1 of `rihb_theory.tex`. Issues are graded **killer** (must fix in v2 or the paper dies on first review), **important** (defensible but weak as written), or **cosmetic** (annoyances that don't change the verdict).

I list 18 things. Six are killers; six are important; six are cosmetic. The killers are the meat of v2.

---

## Killers (must fix in v2)

### K1. What is actually new is too thin

The contribution list reads to a careful reviewer as: "compose two known things (LBS smoothness, surface-integral smoothness) and call the composition a theorem." Theorem 4.1 (`thm:Q-diff`) is not a deep result; it is a chain rule on a smooth integrand. Theorem 5.1 (`thm:pareto-1`) is a one-line corollary of `rib.tex` Theorem 8.1 with a visibility gate. Corollary 5.2 (`cor:gait`) is a re-statement of the eigenvector identity. The closed-loop architecture in §6 is a sketch with an information-budget table.

The paper as written has zero new theorems that survive removal of `rib.tex` as a citation. **A JSAC reviewer who reads this asks: what would not exist if this paper were rejected?**

The honest answer is: the *integration* — pose-as-control-variable, the closed-loop architecture, the gradient-passing privacy split, the gait-action statement. These are framings, not theorems.

**Fix.** v2 must add at least one technical result that does not collapse under "compose two known things." Candidates:
- A *quantitative* statement about how the rate gradient `||∂R/∂θ||` scales with body shadow geometry. This is the load-bearing quantity for the empirical claim and is *not* in `rib.tex`.
- A pose-noise-aware Pareto bound: the bound of Theorem 5.1 with an explicit dependence on the pose estimator's covariance `Σ_θ`, showing how IMU noise widens the operating window. This connects `rihb_theory` to the JSAC v5 IMU machinery in a non-trivial way.
- A characterisation of the LOS-shadow regime that explains *when* the Pareto bound binds versus when LOS un-shadowing dominates. The current treatment is qualitative (Remark 5.3); a quantitative split would be a real result.

I would pick all three. Each adds 1-2 pages.

### K2. The Pareto bound binds where it doesn't matter

Theorem 5.1 bounds the *body-mediated* contribution to receive power by the absorbed dose times `(1-T₀)/T₀`. Remark 5.3 honestly admits that in the body-shadowed LOS scenario (the hero scenario), the LOS un-shadowing term dominates the rate gradient, and that term is *not* covered by the Pareto bound.

So in the regime the empirical figure operates in, the load-bearing analytical result does not bind.

This is the same kind of structural mismatch that killed JSAC v5: the strongest math is in a regime the operational claim does not live in.

**Fix.** Either:
- Add a *LOS un-shadowing bound* — a separate theorem that bounds the rate gain from un-shadowing by the dose change. Sketch: `ΔR ≤ log(1 + α · ΔP_abs)` where α is a body-geometry constant. This requires modeling the un-shadowed path's amplitude as a function of how much body is in the way, which couples to the per-triangle visibility integral that already exists in the code.
- Or reframe the spine so the hero scenario is a regime where the body-mediated term *does* dominate. NLOS coffee-shop (S2) is exactly this regime: no LOS exists, all rate is body- or wall-mediated. Move S2 to be the hero and demote S1 to a preview.

I lean toward fixing the bound. The hero-LOS scenario is more compelling on intuition grounds; rewriting the bound to cover it is the right move.

### K3. The phone is in the body's near field, theory is in far field

The body's Fraunhofer distance at 28 GHz is `D²/λ ≈ 300 m`. The phone is at 30 cm. The body scattering matrix `F_b(k_out)` from `rib.tex` is a far-field object. The exposure operator `Q_abs` is built from incoming-from-BS waves only and is fine because the BS is at 30 m (far field). But the body-to-phone leg is deep near field.

This means the body-mediated component of the channel — the Pareto-bounded part — is incorrectly modeled in v1. The bound's slope `(1-T₀)/T₀` may not even hold in near field; the receive amplitude scaling is wrong; the directional locking statement is wrong.

This is mentioned as loose thread #9 in v1. It is not a loose thread; it is a load-bearing modeling error.

**Fix.** v2 must derive the near-field version of `F_b` and the corresponding near-field Pareto bound. `rib.tex` §12 has the integral; we need to actually do the work and get the modified slope. Two approaches:
- Treat the phone as a point receiver in the body's Fresnel zone. Use the Stratton-Chu kernel; the Pareto bound becomes `(1-T₀)/T₀ · g_NF(d_phone, body)` where `g_NF` accounts for finite-distance corrections.
- Or scope the construction so the receiver of interest for the Pareto bound is the *next user* in a multi-user scenario (S3), which is at meters away (far field). The phone-to-self leg is then the LOS, which is bypass-the-Pareto.

I lean toward the second — it scopes cleanly and makes S3 (multi-user) the natural test bed for the Pareto, while S1 is the LOS-un-shadowing test bed.

### K4. The MCS cap kills the rate gradient at the top

Equation (15) caps `R(θ)` at `R_max = 7.4 · B` bps. Above this SINR, more channel quality buys nothing. So the rate gradient `∂R/∂θ` is zero whenever the precoder is already saturating the cap.

In the body-shadowed regime, baseline is far below the cap so this is fine. But once a pose move opens the LOS, the SINR can jump well past 22 dB and the gradient *vanishes*. The user is told "stop, you've maxed out" — fine. But the Pareto figure now has a flat plateau on its right edge: the dB-gain saturates at 7.4 bps/Hz regardless of how much extra dose the user is willing to take.

This is fine and even good for the story (the dose receipt sells itself: "you are at the cap, more pose move buys nothing, more dose is wasted"). But v1 doesn't analyze it. A reviewer will spot it.

**Fix.** v2 should include a one-paragraph treatment of the MCS-cap regime in §5, with the explicit statement that the gradient is zero on the saturation plateau and that the Pareto frontier collapses to a vertical at `R_max`. Add a corollary: "the optimal pose at fixed dose is the lowest-dose pose that reaches `R_max`." This is actually a clean engineering statement.

### K5. The gait-action principle is over-stated

Corollary 5.2 (`cor:gait`) says the body-mediated capacity-per-dose ratio is invariant under pose moves. This is true *only for the body-mediated channel component*, and only at the eigenvector that maximises both `Q_bist^(k_out)` and `Q_abs^(k_out)`.

In the LOS-shadowed scenario, pose moves change the LOS path, which is exempt from the bound (Remark 5.3). So the invariance does not apply to the realised rate gain; it only applies to the body-mediated *contribution* to that gain. The corollary as written reads as if it applies to total rate, which would be false.

**Fix.** Restate cor:gait carefully: "*the body-mediated component* of capacity-per-dose is invariant under pose, with universal slope `T_0/(1-T_0)`. The total capacity-per-dose ratio is *not* invariant; it depends on the LOS path and on which pose move is being considered."

This makes the corollary true but less marketable. It's the right trade.

### K6. The visibility-gate operator inequality is sloppy

Theorem 5.1 sketch:

> Bound `Q_abs^(k_out)(θ) ⪯ V_out(θ) · Q_abs(θ)` since the `k_out`-visibility gate restricts integration to a fraction `V_out` of the lit area.

This is wrong as an operator inequality. The visibility gate restricts the domain of integration to a subset; the resulting Q is `⪯ Q_abs` (since the integrand is positive semi-definite), but the *prefactor* `V_out` is a trace ratio, not an operator-inequality factor. The eigenvalues of the restricted Q can be at most equal to those of Q_abs but are not bounded by `V_out · λ_max(Q_abs)` in general.

**Fix.** Two approaches:
- Replace the operator inequality with a trace inequality: `tr Q_abs^(k_out)(θ) ≤ V_out(θ) · tr Q_abs(θ)`. This holds. Then Theorem 5.1 bounds `tr` of the body-mediated power, not the eigenvalue. This is weaker but defensible.
- Or drop V_out from the bound entirely and just use `Q_abs^(k_out) ⪯ Q_abs`, giving a body-universal slope `(1-T_0)/T_0` independent of geometry. Loosest but cleanest.

I lean toward the first. v2 should fix this carefully — it is the kind of thing a careful theorist will spot in five minutes and lose trust over.

---

## Important (should fix)

### I1. The 1% opt-in survival claim is asserted

§1 third bullet says the architecture survives at small opt-in fractions because cooperating users' bodies lift others' channels. No calculation. A reviewer can read this two ways: (a) the claim is well-founded but space-constrained, or (b) the claim is hand-waved.

**Fix.** Either drop the claim or back it with a one-paragraph calculation: at opt-in fraction `f`, expected number of cooperating-body-mediated paths to a generic user is `~f · K · ⟨V_cross⟩`, where `K` is the local crowd size and `⟨V_cross⟩` is the average cross-body visibility. At plaza scale (K~50, V_cross~0.05), `f = 0.05` gives ~0.13 cooperating paths per user, marginal. Below S4 reliability.

This is the same number that scenario S4 will measure. v2 should include this back-of-envelope calculation in §1 with a forward reference to S4 for empirical confirmation.

### I2. Comfort cost weights are pulled from thin air

Equation (5) has weights `c_i` set such that `C ≤ 1` corresponds to a 5° torso rotation. The choice of which DOF gets which weight, and the relative weighting between torso/neck/arm, is undocumented. A reviewer will ask: "have you read RULA, OWAS, or REBA?" Those are the standard ergonomic-load scoring schemes used in industrial pose evaluation.

**Fix.** v2 should cite RULA or REBA as the source of the cost-weight calibration and note that a 5° torso turn corresponds to a RULA score increment of `~1` (low load), while a 30° torso turn is `~3` (significant). The numbers don't have to be precise; the citation establishes that the construction has anchor points in established practice.

### I3. Privacy story needs more care

§6.4 claims the user-side variant has the privacy property that body data stays on-device. This is true for `β` and `θ` themselves, but the BS still sees the *acceptance pattern* of pose suggestions over time. From the acceptance pattern an operator can infer the user's pose distribution, response latency, and likely activity. For a known room geometry the inference is sharp.

**Fix.** Add one paragraph to §6.4 acknowledging the inference risk, noting that the strong privacy property is "the operator does not see body geometry" (true), not "the operator learns nothing about the user" (false). Differential privacy on the acceptance signal is the obvious mitigation but is its own paper.

### I4. Convergence under a non-cooperative user

§7 (`prop:descent`) assumes the user follows pose suggestions. In practice the user reads the suggestion and decides; if they ignore it, the inner-precoder adapts to the user's chosen pose, but the outer-loop's convergence guarantee no longer holds because the outer optimiser is suggesting moves the user does not take.

**Fix.** Add a remark or a sub-section: "convergence under partial compliance." The natural model is a probabilistic acceptance with rate `p_accept(θ*)` that decreases with `||θ* - θ⁰||`. Under this model the outer loop converges to a *biased stationary point* whose bias scales as `(1 - p_accept) · ρ_comfort`. This is a paper-friendly result and not hard to state.

### I5. Trace vs quadratic-form consistency

Equations (16), (17), (19), (20) variously use `tr Q_abs`, `x^H Q_abs x`, and `P_abs(θ, x) = x^H Q_abs x` for different quantities. A careful reviewer will lose track. v2 should fix one notation and use it everywhere; my preference is `P_abs(θ, x) = x^H Q_abs(θ) x` consistently, with `tr Q_abs(θ) = M · ⟨P_abs⟩` defined explicitly when needed for averages.

### I6. Rate of pose-induced channel change is missing

The empirical claim ("a few-degree pose move buys 10+ dB on capacity") rests on the magnitude of `||∂h/∂θ||`. v1 does not analyze this. A reviewer asks: "what is the dB/degree on the channel?" The answer is geometry-dependent: in a body-shadowed LOS, it is dominated by the un-shadowing rate, which scales as `(BS-to-body distance) × tan(δθ) / body width`. A back-of-envelope: at 30 m BS-distance and 30 cm body width, `δθ = 1°` un-shadows about 18% of body width per degree, i.e., several dB per degree once the LOS shadow is being modulated.

**Fix.** v2 should include a Lemma in §4: "the per-degree LOS un-shadowing rate scales linearly with `BS-to-body distance / body width` and is order-of-magnitude `5 dB/degree` at S1's geometry." This is the load-bearing prediction the empirical figure will test, and stating it explicitly in the theory locks in the falsification condition.

---

## Cosmetic

### C1. No block diagram of the loop

§6 describes the loop in prose. A TikZ block diagram of (BS → path dictionary → UE; UE → pose estimate → BS; UE → user notification → user → pose action → IMU → pose estimate) would make the architecture readable in one glance. Add to v2.

### C2. The "what this is not" misses "no new hardware"

§9 lists five things this is not. It misses one: "this requires no new hardware on either side." The BS is a vanilla 5G FR2 panel; the UE is a vanilla smartphone with IMU. Add to v2 — it's a deployment-pitch point.

### C3. The XR connection is aspirational

§8 last bullet claims XR-adjacency. The argument is "headsets expose pose," which is true, but headset pose is not full-body pose; the construction needs body geometry not headset orientation. The XR claim is thinner than v1 implies. Either drop or back with a concrete XR application sentence.

### C4. The information-budget table arithmetic

§6.2 says "50 paths × 4 floats × 10 Hz = 16 kbps." A path is more like 8 floats (k_hat 3D, polarization 3D complex = 6 reals, delay 1, amplitude 1). So 50 × 8 × 4 bytes × 10 Hz = 16 kB/s = 128 kbps. Still negligible against the data rate, but the arithmetic should be right.

### C5. Style nits

- Section 4 is dense and could use a worked example (one path, one triangle, the chain rule explicitly).
- The abstract is long (210 words). 150 is plenty.
- "The hero claim is the empirical one" — kill the word "hero" in the abstract; keep it for internal docs.

### C6. The comfort cost example is a `(δθ/5°)²` quadratic — it should also include a barrier for joint limits

A quadratic alone allows the gradient to push past anatomical joint limits. Need a log-barrier or a hard projection. v1 mentions this in §3.2 but doesn't carry it through to the loss in §4. v2 should be consistent: either drop the joint-limit barrier from §3 or carry it into the loss in §4.

---

## What v2 should look like

Same skeleton, but:

1. New §4.5 (after the Jacobian theorem): **Lemma on the dB-per-degree rate gradient in body-shadowed LOS.** Closed-form for a half-space-blocking torso. (Addresses K1, I6.)

2. New §5.4: **The MCS-cap saturation plateau.** Corollary that the gradient vanishes above the SINR cap; the optimal pose is the lowest-dose pose that reaches the cap. (Addresses K4.)

3. Restated Theorem 5.1 with the trace bound, and a separate **LOS un-shadowing theorem** that bounds rate gain by `log(1 + α · ΔP_abs)`. (Addresses K2, K6.)

4. New §5.5: **Pose-noise-aware Pareto.** The bound under pose-estimator covariance `Σ_θ`. (Addresses K1.)

5. New §6 sub-section: **The near-field correction for body-to-phone propagation.** Modified `F_b` and modified Pareto slope. (Addresses K3.)

6. Restated Corollary 5.2 with the careful "body-mediated component only" language. (Addresses K5.)

7. New §7.4: **Convergence under partial compliance.** Bias of the outer-loop stationary point under probabilistic acceptance. (Addresses I4.)

8. Tightened §6.4 with the acceptance-pattern inference acknowledgement. (Addresses I3.)

9. Cosmetic fixes throughout (C1-C6).

10. Added 1% opt-in calculation in §1. (Addresses I1.)

11. Added RULA/REBA citation for comfort weights. (Addresses I2.)

12. Notation cleanup: `P_abs(θ, x) = x^H Q_abs(θ) x` everywhere. (Addresses I5.)

Length budget: v1 is ~12 pages. v2 will be ~16-18 pages with these additions.

## What I won't fix

- The "wandering companion" tone. v1's tone is right for the SI; this is a theory document, not a paper. The companion-style is what makes `rib.tex` and `q_complement.tex` readable.
- The reliance on `rib.tex` results. The whole point of this construction is that `rib.tex` did the heavy lifting; this paper integrates and extends. Re-deriving `rib.tex` results in this document would be a waste.
- The conjecture-vs-theorem hierarchy. v1 is honest about which is which. v2 doesn't need to prove the conjectures; it needs to make the theorems load-bearing.

## What this critique does not address

- Whether the *empirical* hero number (S1) lands. That's the PoC's job, not the theory's.
- Whether Wout, the SI editors, or actual reviewers will buy the framing. We will know after the PoC and after one round of human review.
- The companion paper to JSAC2 (RIB / RIHB physics). It exists in `rib.tex`; this critique is on `rihb_theory.tex` only.

---

**One-line recommendation.** v2 needs at least three new technical results (rate-gradient lemma, LOS un-shadowing theorem, pose-noise-aware Pareto), the visibility-gate operator inequality fixed, and the near-field correction plumbed through. The framing and structure are right; the math needs more meat.
