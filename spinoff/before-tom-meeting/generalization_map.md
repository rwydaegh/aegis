# Generalizing AEGIS: where the method goes when you drop "dosimetry"

A physics-first map of what the method can become, ranked by business case, honest about
what transfers cleanly and what does not. Written for the Tom Dhaene meeting and the
patent go/no-go. Companion to `00_context_brief.md`.

---

## 1. The one idea to hold onto

The method is not about human bodies, and it is not about safety. Those were the first
customer. Underneath, AEGIS is a **differentiable physical-optics surface engine plus a
closed-form quadratic-operator calculus for inverse design**.

Three choices got frozen when I aimed it at dosimetry:

1. the **wave** is electromagnetic,
2. the **quantity** is absorbed power,
3. the **object** is a human body.

Each of those is an independent knob. Turn them and the same engine, the same code
architecture, the same differentiable graph, computes something a different industry
pays for. The generalization is not "find new applications of a dosimetry tool." It is
"the dosimetry tool was one setting of a general machine."

The reason this matters commercially: the incumbents (Ansys Perceive EM, Altair FEKO,
HFSS SBR+, Remcom) already have fast physical-optics solvers. Speed alone is not a moat
against them. What none of them ship is **differentiability wired to a design objective**
plus the **closed-form operator algebra** that turns "optimize this power quantity under
that constraint" into a QCQP or an eigenproblem you solve in closed form. That is the
thing to patent broadly and license. Everything below is a place that thing is worth
money.

---

## 2. The generative engine: three knobs

### Knob A -- the wave equation (swap the impedance)

The tangent-plane / Kirchhoff / physical-optics machinery is not electromagnetic. It is
what any linear wave does at an interface between two media when the scatterer is large
and smooth compared to the wavelength. Change what "impedance" means and the same surface
integral holds:

| Wave | Interface law | "Refractive index" analog | Status of transfer |
|---|---|---|---|
| Electromagnetic | Fresnel (TE/TM) | complex `n` | current home, exact |
| Acoustic / ultrasound | acoustic Fresnel | impedance `Z = rho c` | clean, textbook Kirchhoff scattering |
| Elastic / seismic | Zoeppritz | P and S impedances | clean but adds P-S mode conversion |
| Thermal radiation | Kirchhoff's law | emissivity | the view-factor result is *already* this |

One honest caveat up front, because it is the kind of thing a reviewer or Tom will catch
in five seconds: the **pseudo-Brewster scalar collapse** (the "one constant `T0` works
at all angles" trick, which is 40% of the dosimetry magic) is a coincidence of high-water
biological tissue. It does *not* transfer to steel, to a submarine hull, to a radome. So
be precise about what generalizes. The scalar shortcut is EM-tissue-specific. The
**geometric surface integral, the ReLU visibility gating, the differentiability, and the
Q-operator calculus are wave-agnostic**. That distinction is the whole credibility of the
pitch, so lead with it rather than hide it.

### Knob B -- the functional (same forward model, different output)

From the incident field on the surface you can read off many quantities, and I have
already built the operators for most of them in `q_complement.tex`:

- absorbed power `Q_ab` -> dose, heating, hyperthermia, HIFU
- scattered power `Q_re` -> RCS, sonar target strength, backscatter, LiDAR return
- captured/incident power `Q_in` -> antenna capture, energy harvesting, delivered power
- missed power `Q_mi` -> spillover, stray light, interference
- reciprocal coupling (the Kirchhoff dual) -> antenna-to-antenna coupling, passive imaging
- the full forward map -> an imaging system's forward model (mmWave/THz scanners, SAR)

The scattering operator is the key unlock. `Q_re` is literally a **monostatic-radar RCS
operator**. I already proved it shares eigenvectors with `Q_ab` under pseudo-Brewster
("the worst beam for the bystander is the best beam for a radar"). Radar is not a new
research direction I have to invent. It is the complement of the operator I already have.

### Knob C -- the design loop (the moat)

Differentiability plus the closed-form quadratic forms means every one of the above
becomes an *inverse* problem you can solve fast:

- gradient descent on shape, material, source, or excitation,
- QCQP in closed form when the constraint is a quadratic form (exposure-constrained,
  RCS-constrained, coupling-constrained beamforming),
- eigenanalysis of `Q` for the worst-case or optimal mode,
- a differentiable surrogate that sits inside an outer optimization loop and calls the
  full-wave solver only to validate. This last one is Tom Dhaene's exact paradigm.

---

## 3. Business cases, ranked

Three tiers. Tier 1 is EDA-native, biggest addressable market, cleanest licensing story,
and the strongest argument for broadening the patent. Tier 2 is adjacent wave equations,
market expansion, and the surprising ones. Tier 3 is honest long-shots.

### Tier 1 -- EDA-native (broaden the patent toward these)

**1.1 Differentiable installed-antenna performance.**
How does an antenna actually radiate once you bolt it onto a car roof, an aircraft
fuselage, a ship mast, a satellite bus, or the frame of a phone? This "installed
performance" / "antenna-on-platform" problem is a physical-optics problem on an
electrically-large body, and Ansys, Altair FEKO, and Keysight all sell tools for it. What
they do not do is make it *differentiable*, so placement and platform shaping are today a
manual "move it, re-solve, look" loop. My `Q_in`/`Q_mi` operators already frame it
(captured vs radiated-away power), and differentiability turns it into gradient-based
placement optimization. This is the single best wedge: existing multi-hundred-million EDA
market, direct extension of my algebra, and the customers are exactly the LoI targets
(aerospace, automotive, defense, mobile).

**1.2 Differentiable RCS and low-observable shaping.**
`Q_re` is an RCS operator. Full-wave RCS optimization is brutal because every candidate
shape is a fresh solve, so stealth design is largely expert intuition plus expensive
verification. A differentiable PO-RCS gives you the gradient of signature with respect to
the shape, so you can descend it. Obvious market: defense primes (aircraft, drones,
ships). Less obvious and possibly bigger: **automotive radar**, where you want to control
the RCS of the car itself, of guardrails and road furniture, and to suppress "ghost
targets" and multipath. Every 77 GHz automotive radar program fights this.

**1.3 RIS / reflectarray / metasurface synthesis.**
A reconfigurable intelligent surface (the 6G darling) or a reflectarray (satcom antenna
panels) is a surface whose per-element phase/amplitude you tune to shape a *scattered*
beam. That is exactly the `Q_re` eigen/QCQP problem: find the surface excitation that
maximizes scattered power toward a target subject to constraints, in closed form, and
differentiate it. Fast RIS/reflectarray design is something Keysight, Ansys, and CST are
all chasing right now with slow full-wave loops.

**1.4 Radome and radar-transparent-part design.**
This is the transmission side of the same coin (`Q_in` and the Fresnel `T`). How does a
dielectric cover distort the beam behind it: an automotive radar fascia behind painted
bumper plastic, an aircraft nose radome, a phone back cover? Differentiable transmission
through a layered surface lets you inverse-design the cover. Automotive 77 GHz radomes
behind paint are a real, unglamorous, well-funded pain point with direct Tier-1 supplier
customers.

**1.5 The differentiable surrogate / pre-screen layer over full-wave.**
The cleanest licensing narrative, and Tom's language. The IDF already describes the
pattern for dosimetry: run 10,000 fast geometric evaluations, gradient-step the design,
pass the worst/best handful to FDTD for validation. Generalize it: AEGIS is the fast
differentiable layer that does design-space exploration and gradient steps and calls
HFSS / FEKO / Perceive EM only to certify the final candidate. This is "surrogate-assisted
optimization," which is Tom Dhaene's entire field. The pitch to an EDA vendor is not
"replace your solver," it is "the differentiable optimization layer that makes your solver
into a design tool." Every EDA vendor wants that and none has a physics-based
(non-data-hungry) version of it.

### Tier 2 -- adjacent wave equations (market expansion, the surprising ones)

**2.1 Focused-ultrasound (HIFU) treatment planning.** *(strongest surprise)*
Swap EM impedance for acoustic impedance and the *entire exposure-constrained beamforming
machine transplants to medicine*. HIFU ablates tumors with a phased-array transducer. The
planning problem is: focus acoustic energy on the tumor while sparing ribs, skin, and
nerves. That is my ECBF verbatim, with an acoustic `Q` on healthy tissue as the constraint
and a `Q` on the target as the objective, differentiable, in closed form. Focused
ultrasound for tumor ablation and for neuromodulation (through-skull to the brain) is a
real device market (Insightec, Profound Medical, EDAP), and the simulation tools there
(k-Wave, and Ansys via OnScale acoustics) do the forward solve numerically without a
closed-form differentiable constrained-focusing layer. ZMT itself has an acoustics module,
so this even extends the *same* first customer. Physically clean, and it moves the method
from "safety compliance" (a cost center nobody loves paying) to "therapy planning" (a
value center hospitals pay for).

**2.2 Sonar / underwater target strength.**
`Q_re` for acoustics is sonar target strength, the underwater RCS. Differentiable -> design
quiet hulls (submarine stealth) and optimize sonar arrays. Naval defense market, its own
specialized tools, high value per seat.

**2.3 Differentiable radiative heat transfer / thermal design.** *(the "it is not even EM anymore" surprise)*
The view-factor result in my monograph *is* radiative heat transfer, with `T0` playing
the role of emissivity, and the Kirchhoff dual (absorptivity = emissivity) is literally
Kirchhoff's law of thermal radiation. So the same view-factor engine, made differentiable,
optimizes: spacecraft thermal layout (radiator placement, multi-layer insulation),
building facade solar-gain and inter-building shading, furnace and receiver design,
concentrated-solar heliostat fields, and bifacial-PV yield (module-to-ground view factors).
Differentiable view factors is a genuine gap. Thermal simulation is a large Ansys market
(Icepak, mechanical thermal), and "we can optimize radiative thermal designs by gradient
descent" is a sentence that surprises people because they file heat and radio in different
mental drawers, when the geometry is identical.

**2.4 Wireless power transfer co-design.**
Beamed RF power to devices, drones, IoT nodes. You must maximize power delivered to the
rectenna (`Q_in` on the device) while keeping human exposure compliant (`Q_ab` on nearby
people). That is a two-operator constrained optimization, and closed-form joint
safety-plus-efficiency is exactly my dual-operator setup, which nobody else has because
nobody else built both operators. Emerging market (Ossia, Powercast, Emrod, Reach,
Wi-Charge). The safety operator is the AEGIS home turf, so this one is a natural bridge:
same physics, same regulator, new revenue quantity.

**2.5 mmWave / THz imaging and in-cabin radar.**
The forward model of an active mmWave body scanner (airport security, e.g. R&S QPS) or a
THz NDT/imaging system is surface reflection off the target, a `Q_re` problem, and the
Kirchhoff dual gives the passive-imaging version. Differentiable forward model ->
learned reconstruction, optimal illuminator/sensor placement, resolution optimization.
Adjacent and hot: automotive in-cabin radar (occupant and child-presence detection,
gesture sensing), where the "target" is again a human body I already model well.

### Tier 3 -- honest long-shots (name them, do not bet on them)

- **Seismic AVO/AVA.** Zoeppritz is elastic Fresnel, so differentiable surface
  reflectivity for amplitude-versus-offset inversion is real physics. But seismic is a
  huge, closed, specialized software world (SLB/Petrel and friends). Hard entry, wrong
  buyer. Interesting for a paper, not for the BV.
- **Freeform illumination optics** (headlamps, LiDAR optics). Geometric optics with
  refraction and Fresnel loss, partial fit, but imaging performance needs more than a
  single-bounce PO surface model. Weak.
- **Room acoustics.** Too diffuse and too low-frequency for the smooth-large-scatterer
  regime. The assumptions break. Do not claim it.
- **Deep-tissue volumetric heating** (microwave ablation, industrial RF/microwave
  heating). Surface confinement is exactly what fails below 6 GHz, so the spatial map
  does not transfer. The total-power `T_bar` result partially survives, but this is not a
  strength. Be honest that the surface trick is a high-frequency thing.

---

## 4. What this means for the patent

Two problems in Alessandro's draft, and the generalization fixes both at once, which is
the rare win-win worth walking into the decision with.

**Problem one, the structural error.** Independent claim 1 characterizes the novelty as
"performing a surface integration over the surface of the body to reduce the
dimensionality of the computation." That is a textbook description of the Method of
Moments, the Boundary Element Method, and Physical Optics, all of which are decades old
and all of which reduce a 3D volume problem to a 2D surface integral. As written, claim 1
reads onto the entire history of surface-based computational electromagnetics and is
anticipated on its face. The *actual* inventive step (the local-plane-wave scalar surface
law, the ReLU visibility gating that avoids ray tracing, the end-to-end differentiability,
and the closed-form `Q`-operator) is demoted into dependent claims 2, 3, 4, and 9. The
point of novelty has to live in the independent claim, not below it.

**Problem two, the scope is backwards.** Claim 1 says "a body" generically, but the
advantages and dependents (claims 3-7) hardwire "biological tissue" and "human body."
So the patent is simultaneously too broad where it is worthless (claim 1 = all of PO) and
too narrow where the money is (dependents = biology only). The biology lock is exactly
what forecloses radar, antennas, and thermal.

**The fix, which is also the generalization.** Rewrite the independent claim around the
true novel combination applied to a *generic wave field on a generic electrically-large
smooth scatterer*: (i) a per-element local-interaction surface law, (ii) visibility-gated
by a rectified projection without volumetric ray tracing, (iii) computed as an end-to-end
differentiable graph, (iv) yielding a closed-form Hermitian operator whose quadratic form
gives absorbed / reflected / captured power and whose eigen/QCQP solution is the optimal
excitation or geometry. Keep dosimetry as a dependent embodiment (biological tissue,
`T0`, ICNIRP). Add embodiments for scattered power (RCS/RIS), transmitted power (radome),
captured power (installed antenna / harvesting), and the acoustic-impedance analog (HIFU,
sonar). That claim is *broader* (bigger market) *and* more defensible (it recites the
actual inventive combination, not plain PO). That is the argument for generalizing rather
than narrowing.

One caution to voice honestly in the room: broadening invites more prior art (differentiable
rendering, differentiable ray tracers like Sionna, Ansys Perceive EM's PO core). The moat
survives because none of those combine *closed-form quadratic operators for power
functionals* with *QCQP/eigen inverse design* the way the `Q`-calculus does. But the FTO
search gets bigger, and that is a real cost to weigh against the bigger market.

---

## 5. What this means for the Tom meeting

Pitch AEGIS to Tom in *his* vocabulary. He is a surrogate-modeling person out of Keysight,
not a dosimetrist.

- Frame it as a **physics-based analytical surrogate** for the full-wave solve:
  closed-form, real-time, and, unlike a data-driven surrogate, it hands you *exact*
  gradients for free rather than fitting them. That is a property his community wants and
  rarely gets cleanly.
- Position it as **complementary** to his data-driven surrogates and his
  surrogate-assisted optimization, not competing. AEGIS is the analytic inner loop, his
  adaptive-sampling and UQ machinery is the outer loop that wraps it and handles the
  regimes where the PO assumptions break.
- Bring the honest limits (section 2, Knob A caveat, and Tier 3). He will trust the pitch
  more if I open with what does *not* transfer. Given the feedback in my notes about
  engaging honestly with divergences, this is the right register with him anyway.
- Ask him the two questions that decide the go/no-go: (1) of the Tier 1 wedges, which is
  the most credible to a Keysight/Ansys licensing conversation, and (2) is the
  differentiable-surrogate-over-full-wave framing (1.5) strong enough to carry LoIs, or do
  we need a named vertical (installed antenna, or automotive radar/radome) as the tip of
  the spear.

## 6. My recommendation, if you want one

Bet the patent broadening on **Tier 1**, and lead the spear with **installed-antenna
performance (1.1)** plus the **surrogate-over-full-wave framing (1.5)**, because those two
are (a) the least physically speculative, (b) the closest to my existing `Q_in`/`Q_mi`
algebra, and (c) the easiest for an EDA vendor to see revenue in. Keep **RCS/RIS (1.2/1.3)**
as the "and it also does the radar things Filip asked about" proof of breadth. Carry
**HIFU (2.1)** and **differentiable radiative thermal (2.3)** as the two "this is a general
machine, not a one-trick tool" surprises that make the breadth argument land and widen the
patent's embodiment list. Name Tier 3 honestly and drop it.

The single sentence to walk into both the Tom meeting and the patent decision with:

> AEGIS is a differentiable physical-optics surface engine with a closed-form operator
> calculus for inverse design. Dosimetry was the first setting of the machine. The same
> machine does installed-antenna design, RCS and RIS synthesis, radome design, focused-
> ultrasound planning, and radiative-thermal optimization, and the moat against every fast
> incumbent solver is that ours is differentiable and theirs is not.

---

## 7. Second pass (Fable review): what changed

I ran an independent physicist-strategist over the same primary sources (`q_complement.tex`,
IDF, monograph). It sharpened four things and corrected two. Where it disagrees with my
first pass, it is usually right, so the deltas below override the section above.

**7.1 Separate the two engines. Sell only one to EDA.**
The pitch conflates two products with opposite value:

- **Engine A, the surface collapse (speed).** "3D volume to 2D surface in ms." Real, but it
  rests on surface confinement + the pseudo-Brewster scalar. Against EDA it is *not* a moat,
  because PO/SBR (Perceive EM, FEKO, HFSS SBR+) are *already* fast surface methods. Do not
  pitch speed to solver vendors. They shipped it years ago.
- **Engine B, the Q-operator calculus (design).** `x^H Q x`, the `Q_ab+Q_re+Q_mi=I`
  partition, eigenmodes, closed-form QCQP, autodiff. This needs *only linearity and
  superposition*, so it is wave/source/functional-agnostic. This is the licensable object.

Consequence: license Engine B as a **differentiable design-optimization layer that sits
above** the incumbents' solvers, not as a solver. In dosimetry you sell speed. In EDA you
sell "your power objective becomes an eigenproblem or a QCQP, and it is differentiable."

**7.2 The single best new EDA handle: "differentiable functional characteristic modes."**
Characteristic Mode Analysis (Theory of Characteristic Modes) is a real, funded EDA subfield
that FEKO and Ansys already sell. Classical TCM diagonalizes the MoM impedance operator in
*current* space: structure-only, excitation-blind, non-differentiable. The eigenvectors of
`Q` diagonalize a *named power functional* (absorbed / scattered / coupled) in *excitation*
space, and they are differentiable in geometry. That is a cleaner design object than TCM and,
as far as either of us can find, nobody sells it. Honest caveat to state up front: Q-modes
are functional-and-structure modes, not TCM's structure-only modes. Related, not identical.

**7.3 The assumption ladder (use this instead of my "three knobs" when talking to Tom).**
A1 linear superposition -> the whole Q calculus. A2 first-bounce dominates -> cheap surface
eval (the universal accuracy ceiling: misses edges, tips, creeping/traveling waves,
cavities, resonance). A3 surface confinement -> the 3D->2D reduction (needs high loss or
PEC; dies for penetrable/low-loss bodies, where Q becomes a *volume* Gram, still PSD, still
QCQP, but no ms miracle). A4 locally planar -> Fresnel/Kirchhoff. A5 scalar collapse ->
tissue only, and optional. So: **Q-calculus travels on A1 alone; the fast evaluator needs
A2+A3+A4; the cheapness needs A5.** Every honest generalization is a claim about A1
travelling, never A5.

**7.4 Ranking corrections.**
- **Radiative-thermal: discount/kill.** Differentiable rendering (Mitsuba 3, nvdiffrast)
  already does differentiable radiative transport, and view factors are ancient and
  commoditized. AEGIS brings nothing *new* there. Keep it only as a free identity, not a
  product line. (I was too enthusiastic in 2.3.)
- **WPT: promote.** It is *inverse dosimetry* (maximize delivered power s.t. exposure bound),
  a single QCQP where AEGIS already owns *both* operators from the tissue physics it already
  has. Real buyers now. Higher than my Tier-2 placement.
- **In-cabin automotive radar: promote, and it is [NEW].** Child-presence detection is
  Euro-NCAP mandated, the "target" is a human body I already model, zero physics transfer
  risk. Pair with airport mmWave scanners (R&S QPS, in our backyard).
- **Co-site EMC / antenna-to-antenna coupling on platforms: [NEW], add to Tier 1.** The
  cross-body term `Q^(u,v)` is literally the inter-antenna coupling matrix. Bigger and far
  less export-gated than stealth. "Differentiable coupling matrix" is novel.
- **RCS/stealth: keep but demote to explorer, not certifier.** Low-observable nulls are
  dominated by edge/tip/traveling-wave physics that first-bounce PO (A2) misses, so AEGIS
  can gradient-explore shapes but cannot certify one. And the blockers are *business* (ITAR,
  glacial procurement), not physics. Do not lead with it.
- **Seismic, optics, room acoustics: kill** (confirmed). FWI adjoint methods are *ahead* of
  us in seismic, differentiable rendering owns optics, and both A2 and A3 fail in rooms.

**7.5 New method-level IP spine (this is where defensible general novelty actually lives).**
Beyond applications, the calculus has latent theorems worth a paper and a claim each:
- **Shape-from-scattering via Aleksandrov's projection theorem.** The direction-resolved
  capture cross-section `Omega_body(direction)` is the body's *brightness function*, which
  (classical result) uniquely determines an origin-symmetric convex body. So a scatterer's
  convex hull is determined by its capture/RCS spectrum. The coherent Q-lift of this is the
  novel part. This is the math engine under body-scanner reconstruction. Solid backbone,
  conjectural lift.
- **Operator shape-derivative.** `d lambda_1 = v_1^H (dQ) v_1` gives a closed-form shape
  gradient of the *worst-case mode* -> worst-case-robust design (robust compliance, robust
  RCS) in closed form. The clean bridge into topology/adjoint design loops.
- **POVM structure -> radar information theory + Helstrom detection** (the transparency
  subspace = undetectable states). Novel bridge, needs one careful paper.
- **Low-rank `Q_in` = compressed exposure sensing.** If rank(Q_in) << M (a one-afternoon
  measurement), the body-array channel is estimable from few pilots. Do this test; it
  underwrites several ideas.
- **Reciprocal self-calibrating compliance array.** From the Kirchhoff dual: an array that
  measures its own `Q` in situ by listening to body thermal/backscatter, no phantom. That is
  hardware/firmware IP with a concrete buyer (base-station self-compliance), distinct from
  the software.

**7.6 The IP tension I have to flag honestly (this partially pushes back on section 4).**
Section 4 argued for broadening the independent claim to a generic wave/scatterer. Fable's
warning, which I think is correct and important: **the general "differentiable surface/PO"
idea is weaker IP than the tissue-specific dosimetry claim**, because differentiable ray
tracing (Sionna RT) and differentiable rendering (Mitsuba) are prior art for the *general*
differentiable-surface concept. My genuinely strong, clean patent is the pseudo-Brewster
scalar-collapse tissue-dosimetry method. So the strategic fork is real:

- keep the narrow tissue claim -> strong IP, small market, and you foreclose the licensing
  play, or
- broaden -> bigger market but the general claim is more exposed and needs a serious FTO
  pass before you lean the licensing story on it.

The reconciliation: broaden, but do *not* anchor the general claim on "differentiable PO" (it
will not hold). Anchor it on the parts that are actually novel as a combination: the
**functional-characteristic-mode eigenstructure of `Q`**, the **POVM partition**, and the
**inverse-geometry (brightness/Aleksandrov) results**. Those are the defensible general-method
novelty, and they are exactly the pieces no incumbent ships. Keep the tissue dosimetry method
as the strong, clean, separately-defensible embodiment underneath.

**7.7 Two more "am I fooling myself" checks worth internalizing.**
- "Closed-form `Q`" is closed-form *given the paths*. In clutter, a cavity, or an urban
  scene you still need a ray tracer to fill `G_tilde`, so `Q` inherits the tracer's cost. Do
  not oversell "closed-form" to a solver vendor who will probe exactly this.
- For HIFU / imaging / any penetrable target, be explicit that surface confinement is gone:
  the ECBF/QCQP *planning* jewel transfers, the ms-speed *does not*. Keep the two claims per
  market separate.

**Net after two passes.** The licensable core is Engine B, the differentiable Q-operator
calculus, sold as a design-and-optimization layer above incumbent solvers, with
"differentiable functional characteristic modes" as the EDA-native handle. Highest-fit
destinations: installed-antenna + **co-site coupling**, **automotive in-cabin + airport body
sensing** (home turf, hard regulation), **WPT co-design**, and, as a research-to-IP spine,
the **shape-from-scattering (Aleksandrov)** inverse and the **self-calibrating compliance
array**. Lead the Tom conversation with the two-engine split and the CMA framing, not speed.
