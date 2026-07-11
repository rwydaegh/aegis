# Shared agent brief: military / high-power RF market fit for AEGIS

Written 2026-07-09 by the orchestrating agent, before fan-out. Every subagent on this study
reads this file first. It is the common ground truth. Do not re-derive it; attack it.

---

## 1. What AEGIS actually is (be precise, the pitch depends on it)

AEGIS computes how much electromagnetic power a **human body** absorbs, given the fields around it.

Core law: `S_ab(r) = S_inc * T0 * ReLU[n_hat(r) . (-k_hat)]`

- The body is a **surface mesh**, not a volume. Absorption is a 2D surface integral, not a 3D
  volumetric solve. This is the speed trick: milliseconds, not hours. Validated within 3-10% of
  FDTD **above ~6 GHz**, where skin depth < 1 mm so the physics genuinely lives on the surface.
- `T0` is a Fresnel transmission coefficient from tissue dielectric properties.
- `ReLU[...]` gates self-shadowing (the lit side absorbs, the dark side does not).
- Nine fidelity levels, 0-8. Levels 0-6 are incoherent (they sum **powers**). Levels 7-8 are
  **coherent** (they sum **complex fields**), and that is where the interesting physics is.
- The whole graph is **differentiable** (JAX). You can take gradients of absorbed power with
  respect to precoder weights, antenna placement, array geometry.

### The crown jewel: the exposure operator Q

For a coherent array with `M` elements and complex excitation vector `x`:

```
G̃(r)            = body-surface field channel, shape (n_triangles, 3, M)
S_ab(triangle t) = Σ_axis | G̃_t . x |²          [local absorbed power density, W/m²]
Q                = Σ_t area_t · G̃_tᴴ G̃_t        [M x M Hermitian PSD matrix]
P_abs            = xᴴ Q x                        [total absorbed power, W]
```

`Q` is built once per scene in milliseconds. Then *every* question about *every* possible beam
is linear algebra on an `M x M` matrix. Consequences that matter commercially:

| Question | Answer | Cost |
|---|---|---|
| Absorbed power for beam `x`? | `xᴴ Q x` | one matvec |
| **Worst case over ALL beams?** | `λ_max(Q)` | one eigendecomposition |
| **Worst-case local APD on skin patch t, over all beams?** | `‖G̃_t‖²₂` (spectral norm of the 3xM block) | trivial |
| Best beam under an exposure cap? | ECBF QCQP, closed form `x* ∝ (λQ + νI)⁻¹ h*` | one solve |
| How exposure-aligned is the serving beam? | `ρ = hᴴQh / (‖h‖² λ_max)` | trivial |

`Q` is extremely low rank in practice: top mode ~60% of trace, top 8 modes ~92.5%.

Code: `src/aegis/coherent/{exposure_operator,ecbf,body_channel,field_channel}.py`.
`eigendecompose_Q` and `λ_max` are already implemented and shipped.

### What AEGIS is NOT

- Not a full-wave solver. First-bounce physical optics (assumption A2). It **cannot certify a
  passive scattering signature** (RCS, radome boresight, deep co-site isolation) because those
  numbers live in edge/tip/creeping-wave diffraction that A2 structurally omits.
- Not valid as a *surface* method below ~6 GHz. Below that, energy penetrates volumetrically.
  The **planner/optimizer transfers** (it only needs field linearity in `x`, which always holds).
  The **millisecond surface speed does not.**
- Not a ship/platform electromagnetics tool. FEKO, HFSS/SBR+, CST, XFdtd model the *platform*
  far better than AEGIS ever will.
- No pulsed / fluence physics. No thermal (bioheat) coupling. No induced-current (sub-30 MHz)
  physics. These are genuine, named gaps.

### The generative rule (earned from 13 prior feasibility studies)

> AEGIS wins where the problem is **design a controllable coherent excitation against quadratic
> power limits**. It loses where the problem is **certify a passive scattering signature**, and it
> is irrelevant where a good-enough tool already ships to a reachable buyer.

---

## 2. The military situation, as currently understood

Read `military_rf_hazard.md` and `gemini_deep_research_answer.md` in this directory. Condensed:

**The gap, independently confirmed:**
1. In ~99% of ship topside projects **the human body is never modeled**. The field is computed in
   empty air ("unperturbed fields") and compared to a threshold. A keep-out zone is painted on the
   deck. The human is a point that must not enter a volume.
2. **No fielded military system does exposure-constrained beamforming.** It is an on/off lookup
   table: if the beam would sweep a walkway, blank the sector or drop power.
3. The conservatism has a **documented operational cost**: during flight-deck ops, warships must
   put high-power tracking radars into standby or blank sectors, which "degrades the ship's
   hemispherical air defense capabilities, leaving the platform vulnerable to low-altitude threats
   during flight operations."

**The vocabulary:** RADHAZ (radiation hazard, umbrella). HERP = hazard to **personnel**.
HERO = to **ordnance**. HERF = to **fuel**. MIL-STD-464D §5.9 mandates all three. DoDI 6055.11 +
IEEE C95.1-2345-2014 set US military limits; STANAG 2345 is the NATO transposition that binds a
Belgian/Dutch/German ship. EU Directive 2013/35/EU Art. 3(9) is the military derogation.

**A correction the orchestrator already made to the Gemini output:** the military "controlled" tier
is numerically identical to the ICNIRP **occupational** tier (0.4 W/kg whole-body, 10 W/kg local
head/torso 10g, 20 W/kg limbs, 100 W/m² APD over 4 cm²/6 min). Gemini compared military-controlled
against civilian-*public* and wrongly concluded a military-specific 5x. There is no such factor.
**AEGIS's existing occupational limit set already IS the military limit set.**

**What is genuinely military-specific:** the **pulsed regime**. Epirus Leonidas: ~450 MW peak,
20 ns pulse, 50 Hz PRF. IEEE C95.1-2345 adds **fluence** (energy-per-pulse) rules over a 100 ms
window that civilian guidance lacks. AEGIS has none of this.

**Band map (decides whether the speed trick survives):**

| Band | Example | Regime |
|---|---|---|
| 2-30 MHz | ship HF comms | **Not AEGIS physics.** Induced body currents, contact burns. Exclude. |
| 1-4 GHz | Epirus Leonidas (L), AFRL THOR (S), air-search radar | Volumetric. Planner transfers, speed does not. |
| ~10 GHz (X) | fire-control, nav radar | Skin regime returning |
| 30 GHz+ (Ka, mmW) | seekers, jammers, 95 GHz Active Denial | **Home turf.** Sub-mm skin depth. |

**The walls, honestly:**
- HERP (personnel) is a **small budget line**. HERO (ordnance) commands far more money, because a
  missile cooking off destroys a carrier while overexposing a sailor is an administrative matter
  managed with paint and signage.
- **Safety boards structurally prefer the dumb static method** because it cannot crash. They resist
  dynamic, sensor-driven, software-defined nulling.
- **Classified geometry.** The solver is unclassified dual-use (EAR99-ish). The ship CAD, antenna
  phase centres, and waveform tables you need to run a *real* simulation are Secret/NOFORN.
- **Small software slice.** Military E3/EMC/RADHAZ is ~$1.5-2B/yr, but only ~$300-400M is software
  licensing. The rest is physical test and engineering services.
- **The name.** AEGIS is the US Navy's flagship combat system (Lockheed Martin, SPY-1 radar).
  Needs a different product name in this market.

Current verdict in `military_rf_hazard.md`: **CONDITIONAL, near the top of the band.**

---

## 3. Two orchestrator findings that reframe the study. Test them, do not assume them.

### Finding A: the certifiable exposure envelope (the likely product)

The memo treats safety-board conservatism as a structural wall against AEGIS. **It may be the
opposite.** Because `P_abs = xᴴQx`, the supremum over *all* unit-norm excitations is `λ_max(Q)`,
and the worst-case local APD on skin patch `t` over all beams is `‖G̃_t‖²₂`. Both are closed form,
already in the code, and computed **with a real human body in the scene**.

That yields a **static, deterministic, provably-valid-for-any-beam keep-out certificate**. No
runtime software sits in the safety loop. No sensor can drop out. It is a bound, not a controller.
It is therefore exactly the kind of artifact NOSSA / the Navy LSRB / AFNIRSB can accept — while
being *tighter* than today's unperturbed-field zone, because today's method (a) ignores the body's
own absorption and shadowing, and (b) implicitly assumes main-beam gain in every direction at once.

The honest sub-questions: is `λ_max` over *all* unit-norm `x` too loose to be useful, given a real
array has per-element power limits, scan-sector limits, and amplitude tapers? The constrained
supremum over a realistic excitation set is the real object. Does it still beat the incumbent zone?
**Someone must actually compute this.**

### Finding B: MRI parallel-transmit VOPs are prior art AND regulatory precedent

Nowhere in this repo. **Virtual Observation Points** (Eichfelder & Gebhardt, MRM 2011) are a
compressed set of matrices `Q_i` such that `max_i xᴴQ_i x` upper-bounds local SAR anywhere in the
body for *any* parallel-transmit RF pulse `x`. This is the same mathematical object as `Q`, in 7T
MRI, published 2011, and it is the basis of the online SAR supervisor in every clinical pTx system.

Both edges cut:
- **Threat.** "Bound exposure over all excitations with a quadratic form" is not novel per se. The
  patent's claim-9 language ("closed-form exposure operator") is exposed. Novelty must be relocated
  to the **fast surface construction of `Q` in an arbitrary propagation environment** (RT + Fresnel
  surface law + differentiability at mmWave), not to the existence of the quadratic form.
- **Gift.** The single strongest objection to the whole military thesis is "safety boards will never
  accept a software-computed envelope." **The FDA already does, for 7T pTx MRI, via VOPs.** That is
  a live, clinical, regulator-blessed precedent for precisely this instrument. It should be the
  first slide.

### Finding C: correcting the "death ray" premise before anyone builds on it

Robin's framing is that AEGIS shows a MaMIMO array concentrating a wavelength-sized hotspot on skin
and "essentially frying that little area." Read `papers/coherent-exposure-operator/exposure_datamining/FINDINGS.md`,
including its own correction notice at the top. The measured facts:

- Hotspot footprint collapses to **0.9 cm²** at 1% ECBF budget (≈1.07 cm diameter ≈ λ at 28 GHz —
  genuinely diffraction-limited). It is **steerable**: across the whole 56-config grid the peak lands
  on the clicked triangle, co-location 0.0 cm, 100% of configs. Thin distal limbs (ankle, shin) are
  the worst foci.
- Peak-to-mean `η` up to **57**. But the matched-illumination **decohered** baseline already gives
  `η_dec ≈ 4` (Rayleigh speckle). So coherent engineering buys **~10-13x** in peak-to-mean, and
  **~11-39x** local buildup at the aimed patch. An earlier "~100x vs incoherent" claim was
  **retracted**: that was just array gain `~M`, which any EIRP check already counts.
- **Crucially: the grid is calibrated at 25 dBm total (0.316 W).** At that power, at 14 m, **neither
  limit is breached at all.** Nothing is fried. `P_abs` is homogeneous of degree 1 in total power.

So: **at base-station power there is no death ray.** And at military power you do not need coherent
cleverness to hurt someone — a 50 kW array with a pencil beam does that trivially. The novelty is
therefore **not** "we can fry a spot." It is the pair:

- **(a) The hazard is sub-resolution to the regulation.** A steerable λ-sized coherent hotspot is
  invisible to *three independent* averaging operations in the standard: the 4 cm² spatial window
  (a 0.9 cm² spot is diluted ~4x), the 6-minute time window (a scanning beam dwells for ms), and the
  unperturbed-field assumption (no body, so no coherent buildup on tissue at all). An agile array can
  be **compliant on paper and non-compliant in reality.** This is the fundable problem statement, and
  it is a *standards* finding — which is Wout's world.
- **(b) The envelope is certifiable.** Finding A bounds exactly the thing (a) says is unbounded.

(a) is the problem. (b) is the product. Both are safety-side. Build the study on this pair.

---

## 4. Ethics and scope. This is a hard boundary, not a preference.

This study covers: **hazard characterization, personnel protection, compliance and certification,
and safety-of-effect for already-fielded systems** (i.e., proving a deployed non-lethal system does
not cause permanent injury to bystanders and friendly forces).

This study does **not** cover, and no subagent should produce: optimization of a system to maximize
injury to targeted people, targeting or lethality engineering, or any design whose deliverable is
better harm to a human. If your line of inquiry drifts there, **stop and say so in your report.**

This is also correct strategy, not only correct ethics. An EU university spin-off running on IOF /
VLAIO / EDF money, with a UGent TechTransfer IDF and a university ethics committee, cannot touch
offensive weapon design without destroying its funding path. Note also Horizon Europe excludes
lethal-weapon work while EDF explicitly funds defense; these have different rules and a subagent
touching funding must get that distinction right.

Dual-use tension worth naming rather than hiding: making a high-power microwave system *legally
operable closer to humans* protects bystanders **and** simultaneously raises the system's permitted
duty cycle. Robin has flagged this himself. Surface it; do not resolve it silently.

---

## 5. What Robin actually has, and what is in reach

**Has:**
- AEGIS: ~28k lines Python, 2,469 tests, deployed 3D web viewer, 9 fidelity levels, JAX
  differentiable backend, 4 anatomical phantoms (thelonious 17 kg child, eartha 56 kg, ella 59 kg,
  duke 72 kg), ICNIRP 2020 + IEEE C95.1 compliance module, DiffeRT/Sionna ray-tracing bridge, a
  base-station pipeline over 15 regions / 5.25M antennas.
- Theory: a ~6000-line monograph, a TAP paper, a TWC paper in prep on the coherent exposure
  operator, `theory/exposure_null_precoding.tex` (already the null-steering form).
- IP: IDF **P2026/040** filed with UGent TechTransfer, **sole inventor, zero public disclosures**.
  Claims cover the surface-integration method, ReLU shadow gating, scalar `T0`, >6 GHz validity,
  the differentiable graph, and the "closed-form exposure operator" for coherent MIMO.
- People: promotor **Wout Joseph** (UGent/IMEC WAVES, sits on the RF-EMF standards bodies that
  matter, has won this exact IOF grant twice). Co-founder Carolina. UGent TechTransfer (Filip,
  business dev; Anniek).
- Money path: IOF StarTT (deadline pressure, ~3 Aug), VLAIO, istart. Mostly non-dilutive.

**Emphatically does not have:** any defense customer, any clearance, any classified geometry, any
LOI, any defense-sector track record. Almost zero commercial traction of any kind — one polite email
from Hirata, no calls held, no signed partners.

**Plausibly in reach (verify, do not assume):**
- Royal Military Academy (RMA/KMS) Brussels — Belgian, academic, defense-credentialed, has an
  EW/comms department. A natural non-classified partner.
- Thales Belgium (Herstal) and Thales Nederland (SMART-L, SeaMaster naval radars). Damen Shipyards.
- Belgian Defence's DIRS strategy funding line. EDF non-thematic SME calls. EDA CapTechs. NATO STO
  panels (HFM = human factors and medicine; SET = sensors).
- Wout's standards-body seats are a free, immediate dissemination channel for Finding C(a).

---

## 6. How to work, and how to report

**Be adversarial, not agreeable.** The prior feasibility study's own conclusion was that "the
optimistic map oversold everything by about one grade." Assume this brief does too. The most
valuable thing you can return is a **specific, sourced fact that kills or sharply narrows an idea
here.** An agent that returns "confirmed, looks great" has probably not worked hard enough.

**Sourcing.** Prefer primary sources: standards documents, program-office pages, patent texts,
budget line items, published papers, procurement notices. Distinguish clearly between what you
**verified**, what you **inferred**, and what you are **guessing**. Never invent grant call codes,
patent numbers, contract vehicles, budget figures, or people's roles. If you cannot verify an
identifier, say "unverified" next to it. Web search and WebFetch are available; Reddit is available
via the reddit MCP (WebFetch cannot reach Reddit or Twitter) and is genuinely useful for practitioner
opinion (r/rfelectronics, r/AskEngineers, defense subreddits).

**NEEDS_CONTEXT protocol.** If you hit a blocker (paywalled source, needed API key, a document you
cannot reach, a browser step) — **stop and report `NEEDS_CONTEXT:` with the precise ask.** Do not
silently downgrade to an inferior approach. Robin can supply keys, run browser steps, download files.
He wants the most ambitious result, not the fastest fallback.

**Return a markdown report**, written for a smart reader who is not a defense person. Plain language.
No em dashes, no semicolons. Sentence case headings. Lead with the answer. Structure:

1. **Verdict** in one sentence.
2. **The three things that most changed my view**, with sources.
3. **What I verified / what I inferred / what I could not check.**
4. Body, organised however the material demands.
5. **What would kill this**, stated as a concrete falsifiable test someone could run in a week.
6. **The single highest-value next action**, and who would have to do it.

Length: as long as the evidence warrants, no longer. Dense over padded.
