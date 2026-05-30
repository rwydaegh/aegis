# Critique of `rihb_theory_v2.tex`

**After reading `paper_jsac_v5.tex` end-to-end and Robin's corrections on
the role of exposure.** Reviewer voice: same as v1 critique; this round
finds bigger structural issues than v1 did. I list 9 things, in roughly
descending severity. Six trigger a v3 rewrite; three are cosmetic.

The v2 file is honest and technically careful, but it is solving the wrong
problem in two ways. (a) It treats exposure as part of the optimization
loss; Robin says exposure is purely informational. (b) It positions the
spine as a fresh re-targeting of "the body twin" without acknowledging
that v5 already runs a complete BS-side compliance loop with the same
twin. Both are framing fixes; v3 makes them and gets simpler in the
process.

---

## Killers (must fix in v3)

### K1. Exposure is informational, not part of the optimization

**Robin's correction filed mid-PoC, made explicit on second read.**
The downlink user is always far below ICNIRP basic restrictions; the
European reference-level caps (3-15 V/m) are conservative regulatory
proxies, not safety binding. v5 handles those at the BS via projected ZF
(`eq:primal-projection`), and the user is not part of that loop except
as a body in the population.

For JSAC2 the consequence is structural. The loss in v2 §5,
`L = -R + lambda_E [P_abs - L_RL]_+ + lambda_M C`, has `lambda_E = 0`
in operational deployment. The penalty term is empty. The whole
"Pareto" framing in v2 §6 (Theorem 5.1, the gait-action principle, the
LOS-vs-RIS regime split) is an optimization-vs-constraint analysis on
a constraint that does not bind operationally.

**Fix.** v3's loss is

> `L = -R(theta, x) + lambda_M C(theta - theta_0)`

Plain rate maximization in pose, subject only to comfort. No exposure
term. The dose receipt is computed and displayed for transparency, but
it does not enter the gradient. v2's Section 5 (joint loss + Pareto)
collapses to a one-page section on the rate-only loss; v2's Section 6
(Pareto bound, gait-action) becomes a one-paragraph "informational
dose-receipt physics" appendix. The Pareto bound from `rib.tex` is still
mathematically true, but it is decorative for this paper.

This is a major simplification, not a loss. The v2 spine was carrying
the exposure-as-trade burden on every page and never quite earned it.
The cleaner spine is "user pose as a differentiable rate-maximizer."

### K2. v2 doesn't acknowledge or position against v5

**v2 §1 says "the body twin is decorative under the v5 result; we make
it load-bearing again by treating pose as a control variable."** This
is right but it doesn't say: **v5 already runs the body twin in the
production BS-side compliance loop**, with a per-body Q, a path
dictionary, a virtual IMU pose estimator, a translation phasor
identity, the works. The twin in v5 IS load-bearing for the operator's
compliance pipeline, just not for the rate.

JSAC2 is therefore not a re-targeting of "the" body twin, it is the
**user-side counterpart** to v5's BS-side compliance use of the same
twin. They are complementary, not competing.

**Fix.** v3 §1 explicitly positions:

> v5 (`paper_jsac_v5.tex`) ran the body twin on the BS side to enforce
> compliance via projected ZF. This paper runs the same body twin
> machinery on the UE side to optimize the user's own rate via pose.
> The two loops are complementary: the BS loop guarantees compliance
> for everyone in the cell; the UE loop helps each opted-in user find
> a more favorable channel via small pose adjustments. The shared
> machinery is the per-body Q operator, the path dictionary with
> translation-phasor refresh, and the SMPL-X body model. The new
> ingredient is differentiability of Q in the pose, plus a pose-update
> outer loop on the UE side.

This positioning makes JSAC2 unambiguously a JSAC SI fit (closed-loop +
differentiable + UE-side digital twin) without claiming territory v5
already owns.

### K3. The "two regimes" split (LOS un-shadow vs RIB) is overcomplicated

Once exposure is informational, the LOS-un-shadowing-as-Pareto-dominant
story (v2 Theorem 5.1) loses its punch. There's no Pareto, just rate.
The two-regime split was useful for organizing the dose-vs-rate trade;
without that trade, it's a distinction without operational difference.

A pose move that opens LOS gives `dR/dtheta` from un-shadowing geometry.
A pose move that orients body for backscatter gives `dR/dtheta` from
the bistatic operator. Both are just terms in the same gradient. The
spine doesn't need to split them into separate sections.

**Fix.** v3 has one section (§4) on the rate gradient `dR/dtheta` that
includes both the un-shadowing geometric term and the bistatic
backscatter term as additive contributions. Examples illustrate which
dominates in which scenario. No Pareto subsections.

### K4. The translation-phasor speed identity isn't credited

v5 §III.C (eq 25) has the **translation phasor identity**

> `M(r0 + t, theta) = Phi(t)^H M(r0, theta) Phi(t)`

which makes per-slot Q-refresh under body translation cost O(N) instead
of re-running the surface integral. The same identity makes per-pose
Q-evaluation **fast on the gradient-update path**: each candidate pose
in the gradient sweep gets a phasor sandwich, not a full surface
integral. This is the actual speed enabler that makes the JSAC2 closed
loop deployable.

v2 talks about "15 ms per VJP on a phone-class GPU" without explaining
where the speed comes from. The honest accounting:
- One-time per-pose: build the static M_static at the body's local
  coordinate frame (~7.5 ms per body, per v5).
- Per-slot per-pose-candidate: translation phasor on M_static
  (sub-ms per evaluation).
- Per-gradient-step: VJP through the LBS-to-Q chain (15 ms).

The 15 ms VJP is what's needed for the gradient. The translation
phasor is what makes evaluating Q at many candidate poses cheap, which
matters if we want a Newton-style or Adam-style update rather than
pure gradient descent. v3 should explain the cost decomposition and
credit v5 for the identity.

### K5. The "rate gradient" lemma in v2 is wrong by 3x

**PoC measured ~0.7 dB SINR per degree at the relevant geometry; v2
Lemma 4.2 estimated ~2 dB/deg.** I diagnosed this in `findings.md`
already — the lemma's spine-offset estimate (8 cm) is irrelevant; the
actual lever arm is the phone-arm extension (55 cm). v3 fixes this and
states the lemma against the right geometry.

A bigger issue: the PoC also showed that visibility never goes to zero
even at the body's worst-shadowing pose (only to 0.59). The body covers
~30% of the Fresnel zone at 30 m; most of the LOS energy gets through.
This means LOS un-shadowing in this geometry buys at most ~5 dB SINR,
not the 25 dB I'd naively estimated. v3 should be honest about this:
the un-shadowing gain is body-cross-section-vs-Fresnel-zone limited,
which at mmWave puts it in the few-dB range for any reasonable single-body
geometry.

**Fix.** v3's Lemma 4.2 is rewritten with the right lever-arm geometry
and the realistic Fresnel-zone fraction. Its predicted gain matches
the PoC.

### K6. v2's rank story misses what v5 already proved

v5 §VI.A: empirical effective rank of Q^(u) is **3 to 4 at the 99% trace
fraction**, regardless of multipath density. The mechanism is BS-side
angular resolution at the panel (~14 deg HPBW for 8x8 at 26 GHz). This
is in v5's `fig:rank-cdf`.

v2 doesn't mention this. It should. The pose-gradient calculations are
**effective rank limited**: even though Q is M x M with M = 64, only
3-4 modes carry trace-mass, so the gradient `dQ/dtheta` and its
contraction with the precoder x are dominated by 3-4 directions.
Concretely:

> The pose-gradient `dR/dtheta` factors as a sum over the rank-r
> singular modes of Q(theta), with r ~ 3-4 in the plaza geometry. The
> dominant term is the rotation of the leading mode in pose. This both
> bounds the achievable rate gradient (the user can only move r modes,
> not M of them) and explains why a small pose move can produce a
> noticeable channel change (it rotates a low-dimensional subspace).

v3 makes this explicit. The rank-3-4 fact is a v5 result that JSAC2
inherits.

---

## Important (should fix)

### I1. v2's bandwidth/byte arithmetic in §6.2 is right, but rough

v5 logs cadence very carefully (`tab:cadence`). v3 should align its
information-budget table with v5's structure: per-quantity cadence
plus per-update bytes plus per-update wall-clock. The arithmetic is
not the issue; the consistency with v5's framing is.

### I2. The privacy story misses the v5 reference

v5 §III.B describes the tier-A/B telemetry as flowing through the
operator's application channel: GPS + IMU. v2 §6.4 talks about
"user-side variant with shape staying local," but v5 already has
shape-and-pose flowing to the BS in the production loop. v3 should
acknowledge that v5's deployment assumes this telemetry flow, and the
privacy improvement of the JSAC2 user-side gradient is to keep the
*pose-update suggestion derivation* on-device while still sharing the
estimated pose for compliance purposes (which v5 needs anyway).

### I3. The Cauchy-bound finding is news for the spine

v5 `cauchy_tightness/README.md` documents that the rank-1 Cauchy bound
is **breached by 49-70% of precoders** with median ratios up to +6 dB.
This means a no-twin BS using the unconditional Cauchy envelope **does
not actually protect bystanders** — the bound goes to zero as
`|a^H x|^2` shrinks but the actual `x^H Q x` does not. v5 flagged this
and proposed the conditional bound (`thm:cauchy-cond` in the
appendix).

For JSAC2 this is interesting because it locks in why the body twin
is needed: there's no analytical fallback that protects compliance
without it. The user-side gradient computation, which uses the same
twin, doesn't escape this either: the precoder shape that maximizes
the user's rate may also redirect power into the body's principal
exposure mode, which is rarely aligned with the LOS steering direction
(`<v_top, a/||a||>^2` in [0.000, 0.19] per v5). v3 can note this in a
remark.

---

## Cosmetic

### C1. The §8 SI-keyword mapping in v2 reads as box-checking

Robin's feedback memory says don't check boxes in open-ended brainstorms.
The v2 §8 list of "differentiable control / closed loop / cross-layer /
... " maps each SI keyword to a section of the construction. This reads
as performative. v3 either drops the explicit keyword list or condenses
it into one paragraph that says, in plain English, why a JSAC SI editor
would care.

### C2. Theorem 4.1 (Q diff in pose) is over-formal

v2 Theorem 4.1 is "Q is C-infinity in theta." The proof is composition.
For a wandering-companion-style document, this can be a one-paragraph
remark: LBS is smooth, the surface integrand is smooth, GELU smooths
the visibility, composition is smooth. No need for a boxed theorem.

### C3. v2's title is honest but long

"Pose-Differentiable Body Twins: First Principles for User-Adaptive
mmWave Capacity and Exposure" — drop "and Exposure" since exposure is
no longer load-bearing. v3 title: "Pose-Differentiable Body Twins for
User-Adaptive mmWave Capacity."

---

## What v3 should look like

Same skeleton as v2, but smaller. Sections marked **[reframe]** are
substantively rewritten; **[trim]** lose pages; **[merge]** absorb
into adjacent sections.

| v2 section | v3 status |
|---|---|
| §1 Why | **[reframe]** Position as user-side complement to v5; drop "the twin is decorative" framing |
| §2 Setup | **[trim]** Same notation; one paragraph on translation-phasor identity from v5 |
| §3 User as control variable | unchanged |
| §4 Differentiability | **[merge]** Theorem 4.1 -> Remark; new subsection on rate gradient with right geometry |
| §5 Joint loss | **[reframe]** Capacity-only loss; `lambda_E` term gone |
| §6 Two regimes | **[merge]** One section on `dR/dtheta` with un-shadowing + bistatic terms |
| §7 Pareto bound | **[trim]** One paragraph + figure reference, in dose-receipt appendix |
| §8 Closed loop | **[reframe]** Align with v5's cadence table; clarify privacy delta vs v5 |
| §9 SI keyword mapping | **[trim]** Drop the explicit list; one paragraph in §1 instead |
| §10 What this is not | **[reframe]** Add "not a compliance paper -- v5 owns that" |
| §11 Loose threads | unchanged |
| §12 Empirical claim | unchanged; reference companion experiment |
| §A Dose-receipt physics | **NEW** Pareto bound and per-direction locking, displayed-only |

Length budget: v2 is 13 pages. v3 should be 8-10 pages. The
simplification is the point.

## What this critique does not change

- The PoC findings stand. The PoC measured a real rate gradient at
  realistic geometry; the spine survives the falsification gate.
- The differentiability theorem is right; it just doesn't need to be
  a theorem.
- The information-budget table is right; it just needs to align with
  v5's.
- The closed-loop architecture is right; it just needs to acknowledge
  v5 holds the BS side.

## What v5 inherits to v3 explicitly

- Rank-3-to-4 of Q^(u) at 99% trace fraction (v5 §VI.A)
- Translation-phasor identity (v5 §III.C, eq 25)
- Per-body Q factorization Q = J^T M J (v5 eq 24)
- The MCS27 rate model with S_max = 7.4 bps/Hz (v5 §IV.A)
- The virtual IMU pose model (v5 §III.D)
- The cauchy-bound failure mode and conditional fix (v5 app C)
- The body twin's deployment is already costed in v5 (cadence table)

## What v5 does not include and JSAC2 contributes

- Differentiability of Q in pose (v5 treats pose as observed parameter,
  not decision variable)
- Pose as control variable for capacity (v5 only enforces compliance)
- UE-side gradient computation
- Pose-suggestion UX channel (the BS-to-UE message channel is one-way
  in v5: only data and CSI flow)
- Capacity gain in the LOS-un-shadowed scenario (v5's plaza geometry
  is mostly LOS)

---

**One-line recommendation.** v3 is shorter than v2 because the
exposure-trade machinery comes out. Spine becomes "user pose as
differentiable rate-maximizer, with v5 providing the BS-side compliance
in parallel." Five pages of content trimmed. The empirical claim
stands.

---

## Updates after Robin's mid-critique messages

Two clarifications change the spine again, this time toward something
richer.

### U1. "Double paper" framing: live SAR + RIHB capacity

> "I lowkey see it as a double paper: an app that gives you your exact
> SAR at any moment (interesting for dose epi studies where we correlate
> it with bio effects over years and year, and many other applications)
> AND the RIHB gives us better capacity."

This is a one-paper-two-contributions structure, not the trimmed-down
single contribution v3 was heading toward. Both contributions sit on
the same machinery (body twin + path dictionary + per-body Q), but
they answer different questions:

- **Contribution A (Personal SAR receipt).** The body twin runs on
  the user's phone and computes the user's own real-time absorbed
  dose from the received downlink path set. The receipt is displayed
  in an app for transparency, logged for personal use, and (with
  consent) aggregated across users for epidemiology. The framing the
  user opens with is: mmWave deployment is *hinged* on the population
  not being freaked out. A real-time, transparent dose number is the
  trust artifact that lets the conversation continue.
- **Contribution B (RIHB capacity lift).** The same body twin, with
  the differentiability theorem of v2 §4, lets the BS suggest pose
  moves that improve the user's own channel via un-shadowing or
  via favorable backscatter. The body is treated as a slowly
  reconfigurable scatterer in the propagation graph.

The two contributions share: SMPL-X body, Q^(u), path dictionary,
translation phasor, per-slot per-body compute. They differ in what
they output: A outputs a number to display, B outputs a pose move to
suggest.

### U2. Lean into RIS lingo

> "I think we might need to lean into the RIS lingo a bit to sell it
> well."

The right vocabulary is already in `rib.tex`: Reflective Intelligent
Body (RIB) for the body as analytical scatterer, Reflective Intelligent
Human Body (RIHB) when the human's brain is the tuning controller
("RIB + intelligent organ called the brain" -- `NEW_ANGLE.md`). The
RIS analogy is informal but pedagogically strong:

- A real RIS has electronically tunable phase shifters. The body has
  none. But the body's surface phase pattern under a given pose is a
  *fixed* phase mask, and posing the body changes which mask is
  active. The body is a passive, slowly-tunable RIS with gait as the
  knob.
- The RIS literature has the cascaded-channel model
  `h_cascaded = h_BS-to-RIS · Phi · h_RIS-to-UE`. The body's analog
  is `h_cascaded = h_BS-to-body · F_b(theta) · h_body-to-UE`, with
  `F_b(theta)` the bistatic body scattering matrix from `rib.tex`
  Definition 4.1.
- The "tuning" of RIS phase shifters is electronic and at MHz rates;
  the "tuning" of body pose is muscular and at Hz rates. Both buy
  channel rank lift, just at different timescales.

v3 should adopt this vocabulary throughout. The title, intro, and
section headers should use RIB/RIHB explicitly. The body's
contribution to capacity is the "RIS gain"; the closed loop is the
"RIS-and-controller co-design."

### U3. Reframe v3's structure

The single-contribution v3 outlined above (capacity-only, no exposure)
becomes a two-contribution v3 with both Personal SAR (Part 1) and
RIHB Capacity (Part 2). The connecting tissue is the shared body twin.
The introduction frames the population-trust problem; Part 1 addresses
it with a per-user receipt; Part 2 capitalizes on the same machinery
for capacity.

The dose receipt is informational only (per Robin's earlier
correction) but it is foregrounded for trust-building, not for
optimization. The capacity story is the more technically rich half.

The discussion mentions, as a side observation, that re-routing
multipath through the body via RIHB pose moves probably *increases*
the user's own absorbed dose (the body absorbs more when more power
hits it). This is an interesting comment to make, not a constraint
to enforce. The user receives the dose receipt; the user decides.

Length budget under the two-contribution structure: 12-14 pages, not
the 8-10 of the trimmed single-contribution outline. The Part 1
material adds two sections (the on-device compute architecture, the
epidemiology pitch). v3 lands closer to v2's length but at a different
distribution: less optimization machinery, more application framing.
