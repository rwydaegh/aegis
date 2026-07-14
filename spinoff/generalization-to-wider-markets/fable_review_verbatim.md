> Verbatim output from the Fable agent run (2026-07-03), prompt: independent
> physicist-strategist review of the AEGIS method's generalization space, business cases,
> method extensions, and a red-team of my shortlist. Reproduced exactly as returned.

---

I have read the operator calculus (`q_complement.tex`), the IDF, and confirmed the Cauchy/view-factor scaffolding in the monograph. Here is the map. I did the physics reasoning directly rather than delegating, since the value is in the synthesis and I had the primary sources.

---

# Where the method goes

## The one insight to lead with: it is two products wearing one coat, and only one of them generalizes

The pitch to an EDA vendor conflates two independent engines that have opposite value propositions. Separating them is the whole game.

**Engine A — the surface collapse (speed).** "Volumetric solve → 2D surface integral in milliseconds." This is a *solver* story, and it is a real one *only for tissue*. It rests on two things: sub-mm skin depth (surface confinement) and the pseudo-Brewster scalar-T0 accident. Neither generalizes cleanly. For metal (RCS, antennas, radome) the incumbents **already** compute the surface in real time — physical optics and shooting-bouncing-rays (Ansys Perceive EM, FEKO PO, HFSS SBR+) are exactly "fast surface methods." So in EDA, Engine A is not a moat. It is table stakes that Ansys shipped years ago.

**Engine B — the Q-operator calculus (design).** `P = x^H Q x`, `Q = ∫_Σ G̃^H G̃ dA`, the `Q_ab + Q_re + Q_mi = I` partition, the eigenmodes, the closed-form QCQP, and end-to-end autodiff. This needs **only** linearity and superposition. It is wave-agnostic, source-agnostic, and functional-agnostic. This is the licensable object, and its sharpest EDA expression is one nobody sells:

> **The eigenvectors of Q are differentiable, closed-form, objective-tied characteristic modes of the scatterer-array system.**

Characteristic Mode Analysis (Theory of Characteristic Modes) is a real, funded EDA subfield — Altair FEKO and Ansys both sell it. Classical CMA diagonalizes the MoM impedance operator in *current* space, structure-only, excitation-blind, and non-differentiable. AEGIS's Q-modes diagonalize a **named power functional** (absorbed / scattered / coupled) in *excitation* space, and they are differentiable in geometry. That is a cleaner object for design than TCM, because the modes are already tied to the design objective instead of being a structure basis you must then project onto. "Differentiable functional characteristic modes" is a defensible, non-obvious, EDA-native framing, and I have not seen it in the literature. (Caveat: Q-modes are functional-and-structure modes, not the structure-only modes of TCM — related, not identical. State it that way and it survives an expert's first question.)

**Strategic consequence:** license Engine B as a *design-optimization layer* that sits above the incumbents' solvers, not as a solver. In dosimetry you sell speed. In EDA you sell "your power objective becomes an eigenproblem or a QCQP, and it is differentiable." Do not let tech-transfer pitch the surface speed to Keysight/Ansys; they will (correctly) say they already have PO. Pitch them the calculus.

---

## Part 1 — What the object is, stripped of human/EM/absorption

It is a **differentiable surface-Gram operator calculus for linear-superposition wave sources**, plus a **first-bounce geometric evaluator** that fills its entries cheaply. The assumption ladder, tiered by which engine each supports:

| # | Assumption | Enables | Where it bites |
|---|---|---|---|
| A1 | Linear medium, linear source superposition | The whole Q calculus (`x^H Q x`, POVM partition, QCQP, eigenmodes) | Essentially never bites for our targets. This is the deep, general layer. |
| A2 | First interaction dominates (geometric optics) | Cheap surface evaluation of Q | Cavities, low-loss multi-bounce, edge/creeping-wave diffraction, resonance. The universal accuracy ceiling. |
| A3 | Surface confinement (interaction on the boundary) | 3D→2D reduction | Needs high loss (skin depth ≪ feature) **or** PEC. Dies for penetrable/low-loss bodies and any deep-penetration use (therapy, imaging). Then Q becomes a **volume** Gram `∫_V g^H g dV` — still PSD, still QCQP, but no ms-miracle. |
| A4 | Locally planar surface (features ≫ λ) | Fresnel/Kirchhoff local reflection | Wavelength-scale curvature, edges, tips. |
| A5 | Scalar transmission collapse (pseudo-Brewster) | O(1) frequency sweeps, one scalar T0 | **Tissue/high-index-lossy only.** Does not transfer to metal, hulls, radomes. But it is *optional* — the machinery runs with full angle-dependent T(θ). |
| A6 | Smooth visibility surrogate (GELU for ReLU) | Differentiability | Always available. |

Read it as: **Q-calculus needs only A1. The fast surface evaluator needs A2+A3+A4. The scalar cheapness needs A5.** The further you move from tissue, the more you keep A1 (and usually A2/A4) and lose A3, and you *always* lose A5. Every honest generalization claim below is really a claim about A1 travelling, not A5.

One more honesty flag that matters for every EDA pitch: "**closed-form Q**" is closed-form *given the paths*. In free space or single-bounce it is genuinely closed-form. In clutter, a cavity, or an urban scene, you still need a ray tracer to get G̃, so Q inherits the tracer's cost. Do not oversell "closed-form" to a solver vendor.

---

## Part 2 — The generalization map, ranked

Ranked by a blend of physical soundness, market reality, and closeness to what is built. New ideas (not in your shortlist) flagged **[NEW]**.

### Tier A — strong, physically honest, buyer identifiable

**1. Differentiable installed-antenna performance + co-site EMC on platforms.**
Physics: PEC surface confinement (A3) is *cleaner* than for tissue — all current is on the boundary, skin depth ~0. Q_in becomes the antenna-to-structure coupling / installed-gain operator; the cross-body term `Q^(u,v)` becomes the **antenna-to-antenna coupling matrix** (co-site interference). Breaks: A5 is gone (metal reflects); A2 is the ceiling (misses creeping waves along fuselage, cavity coupling). Transfers exactly: A1 + autodiff. Sell it as a *differentiable PO surrogate* that produces installed-pattern and coupling gradients for placement, feeding SBR+/FEKO for verification. **[NEW: the co-site EMC angle]** — antenna placement on cars/aircraft/satellites to minimize inter-antenna coupling is a large, less export-controlled market than stealth, and "differentiable coupling matrix" is novel. Who pays: antenna-integration teams at every automotive/aero/satellite OEM, via Altair/Ansys. Novelty: differentiable SBR exists in research; the operator-QCQP framing does not. **Rank: highest strategic fit.**

**2. RCS / target strength shaping — but as an early-stage explorer, not a certifier.**
Q_re is already derived; it *is* a monostatic-RCS operator. Physics: same as (1). The killer caveat, state it plainly: low-observable design lives and dies on edge diffraction, traveling waves, and tip scattering at exactly the nose-on angles that matter — precisely what first-bounce PO (A2) misses. AEGIS gives fast first-order shape gradients, it cannot certify a stealth shape. Plus ITAR/export and glacial defense procurement are business killers independent of physics. Keep as a fast design-space *explorer*; verification stays with the primes' full-wave. **Rank: keep, sober.**

**3. Acoustic target strength / sonar (scalar wave = the most faithful transfer).**
Pressure is a scalar field, so there is no polarization, no TE/TM, no pseudo-Brewster needed — the Q-machinery is *cleaner* here than in its home domain. The Kirchhoff approximation for target strength is standard acoustics. Differentiable hull-shape-for-target-strength is genuinely underdeveloped. Breaks: A2 (multi-bounce off superstructure), and market is defense-gated/slow. **Rank: high physical soundness, medium market. This is the best pedagogical proof that Engine B is wave-agnostic.**

**4. HIFU / focused-ultrasound treatment planning (the ECBF swap).**
This is the highest-value single transfer of the *crown jewel*, and it teaches the A1-vs-A3 split. A phased HIFU array wants to *maximize* deposited dose at a focus subject to sparing skin and ribs — literally `max focal intensity s.t. x^H Q_skin x ≤ L1, x^H Q_rib x ≤ L2`, a multi-constraint QCQP, exactly ECBF with EM→acoustic. Rib-sparing HIFU is a real, currently-heuristic problem. **The honest catch:** ultrasound penetrates deep, so surface confinement (A3) is *gone* — Q becomes a **volume** integral needing an acoustic field model (angular spectrum / Green's function). You lose the ms-speed miracle; you keep the differentiable closed-form QCQP planning layer, which is what HIFU planning actually lacks. Who pays: Insightec, Profound Medical, HIFU/hyperthermia planning. Novelty: high. **Rank: high — but position it as "the operator survives; the surface trick does not."**

**5. WPT safety-efficiency co-design (underrated in your shortlist).**
WPT is the *inverse* of dosimetry: maximize delivered power, bound human exposure. That is `max x^H Q_deliver x s.t. x^H Q_ab x ≤ L` — one QCQP, and AEGIS already owns *both* operators (the delivery target and the tissue-absorption safety side) from the same physics. Real buyers exist now (near-field industrial/automotive WPT, RF-harvesting, consortia). **Rank: higher than your Tier-2 placement implies; it uses the tissue physics you already have, not a swap.**

**6. mmWave/THz body imaging + automotive in-cabin radar.** **[NEW: in-cabin]**
The Kirchhoff dual (passive) and Q_re (active) apply, and *the target is the human body* — AEGIS's home turf, no domain transfer at all. Two concrete buyers: (a) **airport mmWave body scanners** (Rohde & Schwarz QPS, Smiths) — a differentiable forward model plus the shape-from-scattering inverse below improves reconstruction/automatic threat recognition, and R&S is in your backyard; (b) **automotive in-cabin child-presence detection**, which is Euro-NCAP-mandated — "what waveform/array best senses this occupant" is Q_re maximization over a body model you already have. **Rank: high — real regulatory drivers, zero physics transfer risk.**

**7. RIS / reflectarray system-level synthesis (reshaped).**
A RIS *is* a programmable Q_re — you design the scattered field. Native fit for the calculus, and differentiable RIS phase-profile optimization is hot. Reshape: AEGIS is the *macro/system-level* phase-profile optimizer given a unit-cell library, **not** the periodic-Floquet unit-cell designer (that stays full-wave). **Rank: keep, reshaped to system level.**

**8. Radome / radar-transparent parts (niche, but A5 partially revives).**
A thin panel has an angle-dependent transmission you want flat — the one non-tissue place where "carry T(θ), differentiate it" fits, and the pseudo-Brewster *style* of reasoning half-returns. AEGIS handles installed pattern-through-radome distortion cheaply and differentiably; the panel/FSS itself stays full-wave. Modest market, genuine fit. **Rank: keep, niche.**

### Tier B — kill or heavily discount, with the reason

- **Differentiable radiative-thermal / view factors.** The `P = P_t T0 Ω/4π` result *is* radiative heat transfer with T0 = emissivity — which means AEGIS brings nothing *new* to a commoditized, ancient computation, and **differentiable rendering already exists** (Mitsuba 3, nvdiffrast do differentiable radiative transport). You would be reinventing a mature field. Keep only as a free identity you already have. **Discount.**
- **Freeform illumination optics.** Differentiable rendering owns this outright. AEGIS is behind, not ahead. **Kill.**
- **Seismic AVO / elastic.** Full-Waveform Inversion is a mature, huge differentiable-adjoint industry; AEGIS is *behind* the state of the art, not ahead. Elastic mode conversion (P↔S) also breaks the clean 2-polarization structure. **Kill.**
- **Room acoustics.** Low-frequency, modal, diffuse — both A2 (single-bounce) and A3 (surface) fail; it is already a ray+radiosity+wave hybrid. The only real hook (diffuse-field absorption cross-section, Sabine/Bamba) is a solved incoherent problem with no operator advantage. **Kill-ish.**
- **Deep-tissue volumetric heating / RF hyperthermia.** Same structure as HIFU: jewel survives as a volume QCQP, surface trick dies. Fold into (4) as an adjunct, not a separate line.

---

## Part 3 — Extending the method itself (new physics/math latent in the calculus)

Ordered solid → speculative.

**a) The dispersion operator Q(ω) and broadband modes (solid, easy).** Everything is monochromatic. Stack Q(ω) over a band; eigenvectors stable across ω are broadband exposure/scattering modes. Gives wideband ECBF (OFDM compliance) and broadband RCS shaping for free. Low-hanging.

**b) The operator shape-derivative dQ/d(geometry) + eigenvalue perturbation (solid, monetizable).** You differentiate the *scalar* P today. But `dλ₁ = v₁^H (dQ) v₁` gives a **closed-form shape gradient of the worst-case mode** — worst-case-robust design (robust stealth, robust compliance) in closed form. This connects the calculus to shape/topology-optimization adjoint theory and is the natural bridge into EDA design loops.

**c) Shape-from-scattering: Q_in encodes the body's surface-area measure (solid theorem, novel application).** The whole-body scalar is Cauchy's mean projected area (a Minkowski intrinsic volume). The direction-resolved capture cross-section Ω_body(direction) *is* the body's **brightness function**, and by **Aleksandrov's projection theorem** the brightness function uniquely determines an origin-symmetric convex body. So: *the convex hull of a scatterer is determined by its direction-resolved capture/RCS spectrum* — a shape-from-exposure/shape-from-RCS inverse problem with a classical uniqueness backbone. The coherent Q-lift (phased area measure) is the novel part. This is the mathematical engine under idea #6 (body scanners) and the kind of result a domain expert finds non-obvious but immediately verifiable. Flag: the convex-hull recovery is classical-solid; the coherent lift is a conjecture with a real theorem underneath.

**d) POVM structure → radar information theory and Helstrom detection (defensible, semi-speculative).** `Q_ab + Q_re + Q_mi = I` is a genuine POVM on precoder Hilbert space. Two live consequences: (i) mutual information between precoder and outcome → optimal *sensing* waveforms (radar information theory); (ii) the transparency subspace = kernel of an effect operator = "undetectable states," which invites a **Helstrom-bound** treatment of "can a radar discriminate body-pose A from B under an exposure cap." Novel bridge, correct in structure, needs one careful paper to firm up.

**e) Low-rank Q_in = compressed exposure sensing (solid conjecture, testable in an afternoon).** The note already conjectures rank(Q_in) ≪ M. If true it means (i) the body-array channel is estimable from few pilots (compressed exposure sensing), and (ii) the body's scattering is low-rank → efficient RIS and RCS synthesis. Links to effective-rank / random-matrix theory. The note itself says this is a one-afternoon measurement — do it; it underwrites several ideas above.

**f) Reciprocal self-calibration: an array that measures its own Q by listening (novel hardware IP).** From the Kirchhoff dual (loose thread #5): estimate the exposure operator in situ from received thermal/backscatter statistics, no phantom, no FDTD. That turns compliance into something a base station self-verifies. This is a firmware/hardware invention with a concrete buyer (base-station OEM self-compliance), distinct from the software. Flag: needs validation that the SNR supports it.

---

## Part 4 — Red-team of your shortlist

**Tier 1**
- *Installed-antenna:* **Keep, top of list.** Add co-site EMC coupling — bigger and less export-gated than stealth. Moat = autodiff + Q, not speed.
- *RCS/stealth:* **Keep, sober.** PO misses the edge/tip/traveling-wave physics that dominates low-observable nulls; it explores, it cannot certify. ITAR + procurement friction are real. Do not lead with this.
- *RIS/metasurface:* **Keep, reshape** to system-level phase synthesis (macro), not unit-cell design (stays full-wave).
- *Radome:* **Keep, niche.** The one place T(θ) reasoning half-revives.
- *Surrogate + pre-screen layer:* **Keep — make it the product wrapper for all of Tier 1.** It is the safest, most immediately sellable framing, it is non-threatening to incumbents (it feeds their solvers rather than replacing them), and it is exactly how a differentiable layer enters an established solver market.

**Tier 2**
- *HIFU:* **Keep, high value.** Be explicit that surface→volume: the ECBF/QCQP jewel transfers, the ms-speed does not.
- *Sonar:* **Keep.** Cleanest physical transfer (scalar wave), slowest market.
- *Radiative-thermal:* **Discount.** Commoditized + differentiable rendering already exists.
- *WPT:* **Promote.** Inverse dosimetry, uses your existing tissue physics on the safety side, real buyers now.
- *mmWave/THz + in-cabin radar:* **Keep, promote.** Home turf, hard regulatory drivers (child-presence, airport screening).

**Tier 3:** agree — kill seismic (FWI is ahead of you), kill optics (differentiable rendering owns it), kill room acoustics (both A2 and A3 fail), fold deep-tissue heating into HIFU.

**Where you may be fooling yourself (the five):**
1. **Speed is not the EDA moat.** PO/SBR are already fast. Only differentiability + the operator-QCQP is defensible there. You half-say this; say it fully and stop selling speed to solver vendors.
2. **Surface collapse does not travel to penetrable/therapeutic/imaging use.** There Q goes volumetric — fine mathematically, but no ms-miracle. Keep the two claims separate per market.
3. **IP novelty of "differentiable surface/PO" is weaker than your dosimetry claim.** Differentiable ray tracing (Sionna RT) and differentiable rendering (Mitsuba) are prior art for the *general* differentiable-surface idea. Your strong, clean patent is the **pseudo-Brewster scalar-collapse dosimetry method** (tissue-specific, genuinely novel). The general Q-calculus needs a careful FTO pass before you lean the licensing story on it — the eigenmode/CMA framing and the POVM/inverse-geometry results are your best shot at defensible general-method novelty.
4. **"Closed-form Q" is closed-form given the paths.** In clutter it inherits the ray tracer's cost. Do not oversell to solver vendors who will probe exactly this.
5. **Stealth's blockers are business, not physics** (ITAR, procurement) — do not let a clean Q_re derivation lure you into a market that will not transact.

**Net:** the licensable core is Engine B — the differentiable Q-operator calculus — sold as a *design-and-optimization layer above* incumbent solvers, with "differentiable functional characteristic modes" as the EDA-native handle. Highest-fit new destinations not already on your list: **co-site/installed-antenna coupling**, **automotive in-cabin + airport-scanner body sensing** (your home turf, hard regulation), **WPT co-design**, and, as a research-to-IP spine, the **shape-from-scattering (Aleksandrov brightness) inverse** and the **reciprocal self-calibrating compliance array**.
