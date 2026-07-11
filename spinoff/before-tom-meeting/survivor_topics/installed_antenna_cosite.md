# Installed-antenna performance and co-site coupling: graded feasibility

Pressure-test of the #1 generalization wedge. This is the rigorous, graded companion to
`../antenna_coupling_pitch.md`. That doc makes the optimistic case. This one tries to break it:
where the physics is actually wrong, who already owns the space, whether the moat survives
contact with the incumbents, and what would have to be true to win a first licensing
conversation. I am solo-authoring so this is "I", not "we". I do not cheerlead here.

## Bottom line up front

- **Verdict: CONDITIONAL.** The physics is genuine and the differentiability angle is real, but
  the honest addressable slice is narrow (the mid-range installed-pattern regime, not the deep
  co-site isolation regime that co-site engineers actually buy tools for), and the strongest
  incumbent (Ansys HFSS SBR+ / Savant) already computes antenna-to-antenna coupling *with*
  creeping-wave corrections that AEGIS's first-bounce PO does not have.
- **Strongest sub-case:** high-dimensional *installed-pattern* placement pre-screening on a
  smooth platform (car roof, satellite bus panel) where the objective is gain/coverage in the
  -3 to -15 dB regime and there are many design variables (8+ antennas x position x orientation
  x platform-panel shape). Here reverse-mode gradients beat forward-mode Optimetrics and beat GP
  surrogates, and first-bounce PO is physically in-band.
- **Biggest honest risk:** the buyer's real pain is deep-isolation co-site (receiver desense at
  -60 to -120 dB), and in that regime the coupling is dominated by exactly the physics AEGIS
  drops (creeping waves, surface/traveling waves, near-field reactive coupling). So AEGIS is
  accurate where the customer's requirement is loose and wrong where the requirement is tight.
  If the pitch leads with "co-site S-parameters" it walks straight into the regime it cannot do.

## 1. The physics, made precise and honest

### What AEGIS is physically computing here

Reframe the dosimetry engine onto a metal platform. Antenna `u` radiates, the platform's lit
surface picks up a physical-optics current `J_s = 2 n_hat x H_inc` on the ReLU-gated,
ambient-occluded visible set (the exact dosimetry visibility machinery), that current
re-radiates, and antenna `v`'s receive aperture collects it. The platform-mediated coupling is a
bilinear form `S_vu ~ x_v^H Q^(vu) x_u`, with `Q^(vu)` built from the reflection kernel `Q_re`
defined in `theory/q_complement.tex`. The Kirchhoff-dual proposition in that file
(`prop:kirch`, lines 611-618) is the exact reciprocity statement that lets the same operator act
as a receiver, so the receive leg is not a new construction. The cross-object term is even
flagged as an explicit open object in the same file:
`Q^(u,v)_re` "(user v's reflection hitting user u) is a new object" (lines 727-728). So the
theory names this term but has not built it.

The assumption ladder from the brief maps cleanly:

- **A1 (linear superposition):** holds. The whole Q calculus needs only this. Antennas on a
  passive metal platform superpose linearly. No issue.
- **A2 (first bounce dominates):** this is the load-bearing assumption and it is where the honest
  story lives (below).
- **A3 (surface confinement) / A4 (locally planar Fresnel/PEC):** fine at platform scale. A car
  roof at 6 GHz is ~24 wavelengths across with meter-scale radii of curvature, so locally planar
  PEC reflection is a defensible leading term.
- **A5 (pseudo-Brewster scalar collapse):** does NOT apply. That is a tissue trick. On metal you
  run full angle-dependent PEC/coated reflection. The "million-x" dosimetry speed number does not
  transfer, and the pitch doc already concedes this (lines 128-132). Correctly conceded.

### Where first-bounce PO is physically valid for coupling

First-bounce PO is a good leading term for **installed-pattern distortion** and for the
**line-of-sight-over-a-curved-body** coupling path between antennas that see each other across a
convex lit surface. Two antennas on the same car roof, both on the upper convex surface, couple
partly through a direct grazing path plus a single specular bounce off the roof. That is exactly
what PO captures. In the installed-pattern case the platform-scattered field interfering with the
direct field is a first-order-visible effect and PO is legitimate at leading order.

### Where it is simply wrong

Four regimes where first-bounce PO is not an approximation but a physically absent term:

1. **Creeping / shadow-region coupling.** Two antennas on opposite sides of a fuselage couple
   only through waves that creep around the shadowed surface. PO abruptly truncates surface
   current at the shadow boundary (the Ansys HFSS creeping-wave documentation and the Naishadham
   Radio Science 2010 analysis both state this), so PO returns essentially zero for a path that
   physically is not zero. SBR+ adds an explicit creeping-wave current correction precisely
   because raw PO fails here. AEGIS has no such term.
2. **Surface / traveling waves along edges and seams.** A real co-site contributor along
   fuselage stringers, roof channels, and antenna ground-plane edges. Not a first-bounce specular
   scatter. Absent from A2.
3. **Cavity and resonance effects near the feed.** Radomes, shark-fin housings, wheel-well and
   under-panel cavities. Multiple internal bounces and resonances. Absent.
4. **Near-field reactive coupling between closely spaced antennas.** This is the important honesty
   point and it is a category error to model it with PO at all. When two antennas are within a
   fraction of a wavelength, they couple through evanescent reactive near fields, not through a
   far-field scatter off the platform. There is no platform in the path. PO does not model it
   even in principle. So for tightly packed modules (a shark-fin with GNSS + LTE + V2X inside
   ~10 cm) the dominant antenna-to-antenna coupling term is one AEGIS structurally cannot see.

**The honest addressable boundary:** AEGIS is physically valid for *electrically-separated
antennas coupling via the convex-lit platform body in the mid/far field*, and for installed-
pattern distortion. It is wrong for *tightly-spaced antennas dominated by near-field reactive
coupling* and for *deep shadow-region coupling dominated by creeping/surface waves*. That
boundary is not a footnote. It decides the market slice.

## 2. Light calculations

All numbers from the inline script (c = 3e8, standard creeping-wave attenuation approximations).

### Electrical size

| Case | Frequency | Wavelength | Platform in wl | Antenna separation |
|---|---|---|---|---|
| Car roof V2X | 2.4 GHz | 125 mm | roof 1.2 m = 9.6 wl | 0.3 m = 2.4 wl |
| Car roof V2X | 5.9 GHz | 51 mm | roof 1.2 m = 23.6 wl | 0.3 m = 5.9 wl |
| Fuselage blade | 300 MHz | 100 cm | dia 4 m = 4.0 wl | 5 m = 5.0 wl |
| Fuselage blade | 1.0 GHz | 30 cm | dia 4 m = 13.3 wl | 5 m = 16.7 wl |
| Fuselage blade | 1.5 GHz | 20 cm | dia 4 m = 20.0 wl | 5 m = 25.0 wl |

At these sizes A2/A3/A4 are in the right asymptotic regime at the platform scale. Good. The car
roof at 5.9 GHz is 24 wl, comfortably in the PO/asymptotic domain, and antenna separations of
2 to 6 wl are large enough that a far-field-mediated scatter picture is not absurd, but small
enough that a direct near/intermediate-field term coexists.

### Which coupling regime, and the dynamic range that decides adequacy

The deciding question is not "is the platform electrically large" (it is) but "at what `|S_uv|`
level does the customer's requirement sit, and is that level above or below the floor set by the
physics PO misses."

Take the fuselage at 1 GHz, radius a = 2 m, so ka = 41.9. The leading creeping-wave mode
attenuates at roughly `0.68 * (ka)^(1/3)` nepers per radian ≈ 21 dB per radian, so a path that
creeps halfway around (pi radians, antennas on opposite sides) is attenuated by roughly
**64 dB** just in the creeping propagation, on top of launch and spreading loss. Two consequences,
and they cut in opposite directions:

- If the isolation *requirement* is loose (say -20 to -30 dB, typical for avoiding gross
  desensitization on a strong nearby transmitter), then the -64-dB creeping contribution is
  negligible and the coupling budget is dominated by the direct + first-bounce paths that PO
  *does* capture. **PO is adequate here.**
- If the requirement is tight (-60 to -120 dB, which is exactly where receiver desense and
  co-site EMC live, e.g. a transmitter's noise floor into a co-located sensitive receiver), then
  the creeping/surface-wave contribution *is* the coupling, and PO returns roughly nothing where
  the true answer is the number the engineer cares about. **PO is wrong here.**

So the clean statement: **first-bounce PO is adequate in the roughly 0 to -40 dB `|S_uv|`
regime and progressively wrong below about -40 to -50 dB.** Installed-pattern work and gross
coupling screening live in the adequate band. Deep co-site isolation, the higher-value and
harder problem, lives in the wrong band. The pitch doc's own "explorer not certifier" framing
(lines 120-135) is the right instinct, but the calculation sharpens it: the boundary is a dynamic-
range floor around -40 dB, and the co-site niche the pitch leads with is mostly below it.

For the car roof case the separations are 2.4 to 5.9 wl and both antennas typically sit on the
same convex upper surface, so the coupling path is a grazing LOS-plus-one-bounce path, not a
deep creeping path. That is the more PO-friendly geometry, which is one more reason automotive
installed-pattern (not deep co-site) is the honest beachhead.

## 3. Incumbents and the true gap

### Who owns this today

- **Ansys HFSS SBR+ (formerly Delcross Savant).** The stated industry leader for installed-
  antenna performance on platforms "tens to thousands of wavelengths," and it explicitly computes
  "antenna-to-antenna coupling" (Ansys SBR+ application brief). Critically, SBR+ is a
  hybridization of GO and PO that launches rays, paints PO currents, does multiple bounces, *and*
  adds an explicit creeping-wave correction that "paints currents beyond the shadow boundary,
  smoothly blending SBR and CW currents." In other words the market leader already does the exact
  physics AEGIS's A2 drops. This is the single most important competitive fact in this report.
- **Altair FEKO.** MoM + MLFMM + PO/UTD with true solver hybridization, the classic installed-
  antenna and co-site EMC tool. The workflow is documented: element on a canonical ground plane,
  then installed on the CAD body via domain decomposition (full-wave near the feed, asymptotic on
  the electrically-large body), co-site judged on S-parameters / ECC / total efficiency /
  receiver desense. FEKO pairs with HyperStudy for automated parametric and surrogate-driven
  optimization.
- **Ansys EMIT** builds the receiver-desense / RFI model straight from the installed 3D result,
  which is the co-site deliverable customers actually pay for.
- **Dassault CST, Keysight (EMPro/ADS), Remcom (XFdtd/WavesFarer)** round out the field.

### How the placement loop is actually run

Confirmed by the FEKO/HyperStudy and HFSS/optiSLang material: the "move the antenna" step is
largely expert-driven, and when automated it is GA / PSO / Nelder-Mead / trust-region wrapped
with data-driven surrogates (Kriging / GP, Bayesian optimization via optiSLang or DesignXplorer).
Surrogates dominate precisely because a single installed-platform solve is minutes to hours and
there are no cheap gradients through the asymptotic body leg. This is the genuine pain and it is
real.

### Is anything already differentiable? (verifying the moat carefully)

This is where the moat claim has to survive scrutiny, and it half-survives.

- **HFSS Optimetrics / optiSLang analytic derivatives are real.** Ansys computes analytic
  derivatives of S/Y/Z-parameters and far-field quantities with respect to geometry and material
  design variables, and optiSLang uses them to converge in a few design variations. So the flat
  claim "full-wave gives no gradient" is **false** and must not be said to Tom.
- **But they are forward-mode (tangent) derivatives.** Cost scales with the *number* of
  parameters, because forward mode requires re-solving the sensitivity system per parameter (the
  Optimetrics documentation itself notes forward mode "can become prohibitively expensive in cases
  involving multiple parameters"). AEGIS is reverse-mode: all gradients in a small multiple of one
  forward pass, independent of parameter count. So AEGIS wins decisively only in **high parameter
  dimension**, not on a 2-antenna 6-DOF toy where Optimetrics is already fine.
- **And those analytic derivatives live in the full-wave region.** Through the *asymptotic body
  coupling* leg (SBR / PO / UTD), there is no deployed differentiable path. Differentiating
  through discrete ray launching, bouncing, and hard visibility is genuinely nasty (the same
  reason Sionna RT had to build a bespoke differentiable ray tracer, arXiv 2303.11103). AEGIS's
  smoothly-gated analytic PO surface integral is differentiable by construction and does not pay
  the ray-launch discontinuity cost. So the surviving, defensible moat is narrow and precise:

  > AEGIS makes reverse-mode-differentiable the one leg the industry cannot cleanly
  > differentiate, the asymptotic electrically-large body coupling, and it wins over Optimetrics
  > only in high parameter dimension.

That is a real gap, but note how much smaller it is than "they are not differentiable." It is
"they are forward-mode-differentiable in the full-wave region only, and non-differentiable in the
asymptotic region." AEGIS owns the intersection: high-dimensional design variables acting through
the asymptotic body leg.

### The uncomfortable part

SBR+ already computes coupling with creeping-wave physics. So AEGIS is not more accurate than the
incumbent, it is faster and differentiable but *less* physically complete. The value proposition
is therefore strictly "cheap differentiable pre-screen that feeds SBR+/FEKO," never "better
answer." That is a defensible position but it is a layer on top of a $1.5-1.9 B EM-simulation
market owned by two incumbents, not a new market.

## 4. Market and buyer

- **Total EM simulation software market:** roughly USD 1.5 to 1.65 B in 2025, ~10 to 13% CAGR
  (Mordor Intelligence; Global Growth Insights). Antenna design/analysis is ~28% of revenue and
  automotive is ~23% of the end-user split (2024). So the automotive-antenna-adjacent slice is on
  the order of a few hundred million dollars of tool revenue, and the *installed-antenna + co-site*
  sub-slice is a fraction of that, plausibly low tens of millions of addressable license value
  globally. This is a niche inside a niche. Real, but not large.
- **Buyers:** automotive Tier-1s (antenna module suppliers), aerospace/defense primes, phone
  OEMs, satcom platform builders. Deep-co-site EMC is dominated by aerospace/defense and is the
  most export-gated and procurement-heavy, the least reachable for a UGent spin-off. Phone-frame
  near-field coupling is exactly the near-field regime AEGIS cannot do. That leaves **automotive
  installed-pattern / roof-antenna placement** as the most reachable buyer: high volume, low
  export friction, EDA-native, and the geometry (convex roof, mid separations, -3 to -15 dB
  coverage objectives) sits inside PO's valid band.
- **License-a-layer vs sell-a-solver:** the honest and credible go-to-market is "license Engine B
  as a differentiable placement/pre-screening layer that feeds FEKO/HFSS," not "sell a solver a
  startup cannot certify." A startup will not sell a standalone certifying solver into
  aerospace/defense co-site, full stop. The layer story is credible *only* if it plugs into an
  existing solver's certification loop, which means the real customer is arguably the incumbent
  (Ansys/Altair/Keysight) or a Tier-1 that already owns those seats, not a greenfield buyer. That
  is a partnership/OEM motion, slow, and it puts AEGIS in a position where the incumbent could
  reproduce the differentiable pre-screen internally if it mattered enough.

## 5. Proof-of-concept and readiness

### Smallest convincing PoC

Two monopoles on a conducting circular cylinder (the canonical fuselage proxy, and the geometry
with a closed-form / MoM reference):

1. Predict `S_21(separation, angular position)` with the AEGIS reflection operator `Q^(vu)`.
2. Predict the gradient `dS_21/d(position)` by reverse-mode autodiff through the same operator.
3. Reference against a MoM solve (FEKO) or the eigenfunction/creeping-wave series for the PEC
   cylinder.
4. Run a 2-antenna placement descent that minimizes `|S_21|` while holding installed gain.
5. Headline: milliseconds and an exact gradient vs minutes-per-point and forward-mode-only, and
   report the accuracy *as a function of separation* so the PO breakdown at deep isolation is
   shown honestly rather than hidden.

The value of the cylinder is that it exposes the weakness on purpose: as the second antenna moves
into the shadow, AEGIS's error will grow, and plotting that is more credible than hiding it.

### Readiness: what exists vs what is new

- **Exists (shipped code):** `src/aegis/coherent/exposure_operator.py` assembles the Hermitian
  Gram `Q = sum_m area_m G_m^H G_m` and eigendecomposes it. `ecbf.py`, `field_channel.py`,
  `fresnel_operator.py` give the constrained-beamforming and channel machinery. The dosimetry
  visibility (ReLU cosine + ambient occlusion) is production code. So the *diagonal / same-object*
  Q machinery and the differentiable surface eval are done.
- **New (real work, not just theory):**
  1. The **cross-object operator `Q^(vu)`** with two different port sets on two antennas. Today
     `compute_exposure_operator` builds a single `G_tilde` Gram for one radiating configuration
     onto a body surface. The cross term needs one leg carrying `u`'s field to the platform and a
     second, reciprocity-correct leg carrying it to `v`'s *receive* aperture. The Kirchhoff dual
     (`prop:kirch`) says this is legal, but the code assembles neither a receive aperture nor a
     two-antenna bilinear form. Call it a moderate module, not a one-liner: new field-to-aperture
     projection, new bilinear assembly, phase bookkeeping across two elements.
  2. **PEC / coated reflection** replacing the tissue Fresnel `T0`. The `fresnel_operator.py`
     scaffold exists but the pseudo-Brewster scalar collapse must be removed and full
     angle-dependent metal reflection put in.
  3. **Position/orientation as differentiable design variables.** Today the differentiable
     variables are the precoder `x`. Making antenna *position on the platform* a differentiable
     input (so `dS/dp` exists) means the geometry-to-visibility map has to be differentiable in
     placement, which touches the occlusion gating.
  4. **Validation harness against FEKO/MoM.** New, and it is the deliverable that matters.

**Readiness grade: about 40 to 50% of the code exists.** The Q-assembly and differentiable
surface eval are done and that is the hard part conceptually. The cross-object receive-aperture
operator, the PEC reflection swap, and placement-differentiability are each real engineering, on
the order of a few focused weeks to a first validated cylinder result, not a day and not a
quarter.

## 6. Verdict

**Grade: CONDITIONAL.**

Not OVERRATED: the differentiable-asymptotic-body-leg gap is real, verified against the actual
incumbent capabilities, and the code is genuinely half-built. Not SOLID or STRONG-BET: the
addressable regime is narrower than the pitch implies, the flagship co-site-isolation use case
sits mostly below the -40 dB dynamic-range floor where AEGIS's physics is absent, and the market
leader (SBR+) already computes coupling with the creeping-wave physics AEGIS lacks, so AEGIS can
only ever be a faster differentiable *pre-screen*, never a better answer.

- **Single strongest sub-case:** high-dimensional *installed-pattern* placement on a smooth
  convex automotive platform (roof / shark-fin outer surface, 8+ antennas, coverage objectives in
  the -3 to -15 dB band). Here reverse-mode gradients beat forward-mode Optimetrics, beat GP
  surrogates on dimension and on zero-DOE, and first-bounce PO is physically in-band.
- **Biggest honest risk:** the buyer's real money is in deep co-site isolation (-60 to -120 dB
  receiver desense), and there the coupling is dominated by creeping / surface / near-field
  physics AEGIS structurally cannot represent. Leading the pitch with "co-site S-parameters"
  points the demo straight at the one regime it fails.
- **What would have to be true to win the first licensing conversation:**
  1. Scope the claim to **high parameter dimension** (many antennas + orientation + panel shape),
     because in low dimension Optimetrics forward-mode already wins and the moat evaporates.
  2. Sell it as a **differentiable pre-screen feeding FEKO/HFSS**, explicitly not a certifier, and
     show the accuracy-vs-separation curve so the PO limit is disclosed, not buried.
  3. Frame the collaboration as **AEGIS analytic core + a learned residual** (Tom's GP /
     adaptive-sampling / UQ machinery correcting the surface-wave and near-field term). This is
     the only framing that turns AEGIS's physical incompleteness from a weakness into the
     collaborator's research contribution, and it is the one that is both honest and fundable.
  4. Anchor the first PoC on **automotive installed-pattern**, not aerospace deep co-site, to stay
     inside the valid dynamic range and the reachable, low-export-friction buyer.

## Sources

- [Altair FEKO installed antenna / co-site EMC](https://altair.com/feko) and
  [Optimizing antennas installed performance (Altair white paper)](https://altair.com/docs/default-source/resource-library/sim_print_technicaldocument_esd-aerodefense-optantennaperformance_letter.pdf)
- [Ansys HFSS SBR+ installed antenna examples (application brief)](https://www.ansys.com/content/dam/resource-center/application-brief/ansys-sbr-plus.pdf) and
  [Ansys SBR+ shooting and bouncing rays docs](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v251/en/Subsystems/HFSS/Content/HFSS/ShootingAndBouncingRaysSBR.htm)
- [Ansys creeping waves documentation](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/HFSS/Content/HFSS/CreepingWaves.htm) and
  [Naishadham, creeping waves on coated / PEC cylinders, Radio Science 2010](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2009RS004241)
- [Ansys optiSLang + HFSS analytical derivatives webinar](https://www.ansys.com/resource-center/webinar/novel-optimization-approach-using-optislang-and-hfss-analytical-derivatives) and
  [HFSS Optimetrics overview](https://www.microwavejournal.com/articles/2779-parametrics-and-optimization-using-ansoft-hfss)
- [Sionna RT: differentiable ray tracing, arXiv 2303.11103](https://arxiv.org/pdf/2303.11103)
- [Algorithm-driven placement optimization of aircraft VHF antennas for mutual-coupling reduction, Applied Sciences 2026](https://www.mdpi.com/2076-3417/16/6/2718) and
  [Mutual coupling between antennas on a platform via SWE + UTD, ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2211379724003954)
- [Characteristic-mode-assisted antenna placement for isolation, IEEE Xplore](https://ieeexplore.ieee.org/document/8207595/)
- [Electromagnetic simulation software market, Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/electromagnetic-simulation-software-market) and
  [EM simulation technology software market, Global Growth Insights](https://www.globalgrowthinsights.com/market-reports/electromagnetic-simulation-technology-software-market-107811)
- Internal: `theory/q_complement.tex` (Q_re, Kirchhoff dual `prop:kirch`, cross-object `Q^(u,v)_re` open item), `src/aegis/coherent/exposure_operator.py`, `spinoff/before-tom-meeting/antenna_coupling_pitch.md`
