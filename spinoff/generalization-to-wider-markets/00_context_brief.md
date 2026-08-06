# Context brief: the "can we generalize the patent" question

Captured 2026-07-03. This is the situation dump behind `generalization_map.md`.

## Where we are

- IOF StarTT application in prep with Wout. Initially scoped purely to RF-EMF dosimetry
  of humans. Filip (business dev, TechTransfer) ran the intake, said I may submit.
- Two problems flagged at intake: (1) too many customer types, not enough focus, and
  (2) the dosimetry monopoly (ZMT) is only ~$2.3M ARR, so the niche is small. The
  near-field pre-compliance SOM on the intake slides is $0.3-2M. That is too small to
  hang a company or a broad patent on.
- Bigger pools sit adjacent: operators and RAN vendors (Ericsson, Nokia) are an
  order of magnitude bigger to grow into. Governments discouraged (unpredictable).
  Near-field device pre-compliance pays most but is riskiest (you must land in the
  standard).
- Second meeting with Filip, the real one: he pushed "can't you generalize the method?"
  Radar, maybe microchips. His point was that the moat is the *method* (fast +
  differentiable), and a method-level moat can address a much bigger market than
  dosimetry.
- Decision taken: patent on hold for 1 week. I assess technical feasibility of
  generalizing, then we choose: generalize the patent (aim at big EDA licensees,
  submit to the Sept call / Oct 9, ask LoIs from EDA players once a broadened patent
  is filed) or keep the dosimetry scope and submit against the 24 July deadline.

## The market frame (intake slides)

- EM simulation market: $1.66B (2026) -> $2.7B (2031), growing with 5G/6G.
- ZMT (Sim4Life, FDTD) quasi-monopoly of the *dosimetry* slice, ~$2.3M ARR.
- The generalization play is about reaching the $1.66B EM-simulation market (and the
  larger multiphysics/EDA world behind it), not the ~$2M dosimetry niche.

## The moat, stated precisely

USP on the slides: "3D to 2D, >1,000,000x faster, real-time, within 10% of dielectric
uncertainty." Differentiability at TRL 4. But the *durable* moat is narrower and
sharper than "fast":

The incumbents already have fast high-frequency solvers. Ansys Perceive EM is
physical-optics shooting-and-bouncing-rays, real-time on one GPU, millions of facets.
FEKO has PO/MLFMM. HFSS has SBR+. What none of them have is **differentiability** and a
**closed-form quadratic-operator calculus for inverse design**. That is the moat. See
the Ansys license note: Perceive EM is explicitly *not* differentiable, which is why it
can never be our pipeline backend and why our design loop is defensible against it.

## The meeting: Tom Dhaene (SUMO lab, UGent/imec IDLab)

Filip's recommendation, in-house prof, startup-minded, expert in exactly this
generalization question. Profile that matters:

- Runs the **Surrogate Modeling (SUMO) lab**. His field is building fast, cheap
  approximations (surrogates / metamodels) of expensive simulations, plus
  design-space exploration, adaptive sampling, and uncertainty quantification.
- Industry roots: Alphabit (imec spin-off), HP, and **Agilent -> Keysight**. He has
  lived inside the EDA / RF-measurement world we want to license into.
- 500+ papers, SUMO toolbox used in industry.

Implication for the pitch: AEGIS is a **physics-based analytical surrogate** for the
full-wave solve. That is Tom's native language. Frame it as complementary to his
data-driven surrogates, not competing: a closed-form differentiable surrogate that also
gives you exact gradients (which data-driven surrogates struggle to give cleanly), that
his surrogate-assisted-optimization paradigm can wrap. He is the ideal person to
pressure-test whether the generalization is real and to co-author the valorisation
story that lands with Keysight/Ansys people.

## The method, stripped to its core (for the generalization)

Fix nothing about dosimetry and ask what the engine actually is:

A differentiable, closed-form, real-time **physical-optics surface engine**. It takes an
electrically-large, smooth scatterer as a surface mesh and, per surface element, applies
a local plane-wave interaction law (Fresnel), gates visibility with a ReLU cosine plus
ambient occlusion (no ray tracing needed for the first bounce), and integrates over the
surface. On top of that sits a calculus of closed-form Hermitian operators:

- `Q_ab` absorbed power (dosimetry, heating, dose)
- `Q_re` scattered power (RCS, target strength, backscatter) -- already built in
  `q_complement.tex`
- `Q_in` incident/captured power (antenna capture, harvesting, delivered power)
- `Q_mi` missed radiation (spillover, stray)
- identity `Q_ab + Q_re + Q_mi = I`, plus the transparency subspace `ker Q_in` and the
  Kirchhoff/thermal-reciprocal dual (`Q_ab` is also a passive receive/imaging operator).

Everything is differentiable end to end, and the operators turn power/energy functionals
into quadratic forms, so constrained design becomes a QCQP or an eigenproblem in closed
form. That is the generalizable object. The dosimetry application just froze three
choices: the wave (EM), the functional (absorbed power), and the body (human). Relax
each independently -> `generalization_map.md`.

## Files that matter

- `spinoff/patent/IDF/IDF_geometric_dosimetry.md` -- the method + near-field results
- `spinoff/patent/32471_claims_and_advantages_v1.md` -- Alessandro's claims draft (converted)
- `theory/q_complement.tex` -- the complement operators (radar/sensing latent here)
- `theory/monograph_v2.tex` -- Cauchy integral-geometry, view-factor = radiative transfer
- `papers/TAP_paper/paper.tex`, `papers/coherent-exposure-operator/` -- the two papers
- `spinoff/webinar_ansys/ansys_license_decision.md` -- competitive landscape
