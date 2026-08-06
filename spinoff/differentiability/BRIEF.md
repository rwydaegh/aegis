# Shared brief: can differentiability carry a business?

Ground truth for every agent in this study. Written by the orchestrator, 2026-07-09, after reading
the code, the tests, `papers/jsac_archeology.md`, and the eleven-agent military study
(`spinoff/military_angle/SYNTHESIS.md`). Read all of section 1 to 6 before you start. Do not
re-derive what is here; disagree with it if the evidence makes you, and say so loudly.

---

## 1. The question

Robin's words: *"all sorts of weapons, defensive or offensive, or more generally when one wants to
optimize wrt some human body... we can even generalize away from human body to 'electrically large
smoothish object'. And yes the crudest version of AEGIS is a first-order reflection physical optics
on each triangle of said object, with possible extensions. Assume for now those hurdles are
overcomable. The real question: can differentiability enable a really good business case?"*

Two jobs, in order. **Diverge first**: generate a lot of candidate answers, including bad ones,
including ones outside your lens. **Then converge**: rank them and defend the top few with evidence.
A report with three ideas has failed even if all three are good. The previous study was criticised,
correctly, for not fanning out far enough before selecting.

---

## 2. What AEGIS actually is, with the dosimetry stripped off

Forget "absorbed power on humans." Structurally, AEGIS is:

> A differentiable, mesh-native, first-order physical-optics **surface operator** for electrically
> large scatterers, with exact gradients from any input parameter to any output parameter.

Given a triangulated object and `M` coherent sources it builds a surface field channel
`G̃(r)` of shape `(n_triangles, 3, M)` (rank ≤ 3 per triangle), and from it the quadratic form

```
Q = Σ_t  area_t · G̃_tᴴ G̃_t          P_abs = xᴴ Q x          λ_max(Q) = sup over all excitations x
```

`x` is the precoder / excitation vector. `λ_max(Q)` is a closed-form supremum over the entire
excitation continuum. Per-triangle worst-case local density is `‖G̃_t‖²₂`.

Nine fidelity levels: 0-6 incoherent (sum powers), 7-8 coherent (sum fields). Level 6 is the
diffraction / soft-shadow level. Level 8 is the closed-form eigen-beamformer.

**Speed is the founding observation.** Robin, in the first message of the JSAC2 archive: *"the main
thing I realized was you can make this matrix really quickly and compute it very fast, much faster
than FDTD, and that's really the enabler."* `Q = Jᵀ M J` in milliseconds, not FDTD-hours. The
archeology (`papers/jsac_archeology.md`) concludes that across eleven paper versions and two
complete pivots, the operator is the only thing that survived every rewrite. Every spine built on
top of it died.

### 2.1 What is actually differentiable, verified in this repo

Do not repeat the orchestrator's earlier mistake of counting `jax.grad` calls inside `src/`. A
differentiable library has zero, because the *caller* differentiates. `engine.py:753`
(`compute_sab()`) returns raw JAX arrays for exactly this purpose, and its docstring says so.

Verified working, finite-difference validated:

| Gradient w.r.t. | Where | Tolerance |
|---|---|---|
| per-path power, through **every** level 0-6 | `tests/test_jax_grad.py:27,51,98,120,143,166` | `rtol=1e-4` |
| complex precoder `x` (coherent) | `tests/test_jax_grad.py:186,210` | FD-checked |
| transmitter / antenna position, end to end through a trace | `tests/test_jax_grad.py:242,267` | `rtol=1e-3` |
| carrier frequency, and the Fock gate parameter `ξ` | `tests/test_fock_diffraction.py:290,301` | < 2% |

Also present: `src/aegis/optim/mimo_peak.py` softens the peak `S_ab` with LogSumExp and calls
`jax.grad(loss_fn)(x_j)`; `src/aegis/coherent/multibody_ecbf_jax.py` builds a `vmap`ped Jacobian.
`grep -ril differentiab spinoff/` returns 20+ files and 542 matches, including the patent IDF.

Known gap, and it is a bridge not an absence: SMPL-X pose → vertices runs in PyTorch
(`src/aegis/geometry/parametric.py`), so the pose → exposure chain is not yet one autodiff graph.
Also `compute_sab()`'s docstring notes the single specular recapture is a ray-cast pass and is
excluded from the autodiff path.

### 2.2 Two structural observations the orchestrator made, which you should attack

**(a) AEGIS is half an engine.** Fresnel splits incident power into absorbed `T0` and reflected
`1 - T0`. AEGIS keeps `T0` and discards the rest. Grep confirms there is no electromagnetic
scattering anywhere in `src/` (every "scatter" is `scatter-add`, the einsum accumulation). But the
*same* `G̃_t` gives the scattered far field: swap transmittance for reflectance and evaluate the PO
radiation integral toward an observer instead of at the surface. `T0` at skin: 0.485 (8 GHz), 0.539
(28 GHz), 0.623 (60 GHz) — so a human reflects roughly 38-51% of incident mmWave power and is a
strong radar target. **The discarded half is RCS, radar, sensing, and imaging.** Those markets are
much larger than dosimetry and they are exactly "optimize w.r.t. an electrically large smoothish
object."

**(b) The Fock gate is a physically-derived soft rasterizer.** In differentiable rendering the
central obstruction is that visibility is a discontinuous function of geometry, so silhouette
gradients are biased or undefined. The field solved this with heuristic softening (SoftRas) or
expensive edge sampling (Li et al., redner). AEGIS's `geometry/fock_gate.py` and
`kernels/level6_diffraction.py` replace the hard shadow boundary with the Fock transition function,
which is what Maxwell says the field actually does there, and `tests/test_fock_diffraction.py`
differentiates through it. Hypothesis: **hard-visibility differentiable ray tracers (Sionna RT,
DiffeRT, Mitsuba-based stacks) have biased shape gradients; AEGIS's are correct because the physics
picked the smoothing kernel.** This is a moat claim. Verify or destroy it. It may be the single most
defensible technical statement in the company.

> **Correction, added by the orchestrator after reading the code. The claim above is too broad and
> agents must use this narrower version.** The gate is smooth in `mu = n̂·(-k̂)`
> (`level6_diffraction.py:51`), and `n̂` depends on vertex positions, so the *terminator* of a smooth
> convex body genuinely is a differentiable function of geometry, with a width `(kR)^(-1/3)` pinned
> by physics rather than by a tuning knob. But inter-part occlusion (torso shadowing an arm) is a
> different discontinuity and is **not** smoothed: `level6_diffraction.py:87` is
> `g = xp.where(mu > 0.0, g * g_distal, g)`, a hard switch, and `fock.py:565` states that `R_occ` is
> baked so the switch is "constant in pose-grad". `engine.py`'s docstring separately excludes the
> specular-recapture ray cast from the autodiff path.
>
> So AEGIS has a **smooth terminator and a hard inter-part shadow**. The moat, if it exists, is
> exactly: *physically pinned soft self-shadow terminator on a smooth convex body.* Competitors
> confirmed so far: Sionna RT does not handle visibility discontinuity at all ("paths cannot appear
> or disappear"); DiffeRT smooths with a tunable heuristic width, the RF twin of SoftRas. Neither
> has a physical anchor. Claim that, and nothing wider.

### 2.3 The deepest technical risk, and everyone must respect it

**Is `∇(PO)` a good approximation of `∇(truth)`?** First-order PO is 3-10% wrong in *value*. A model
can be a few percent wrong in value and badly wrong in *gradient direction*, especially near
silhouettes and edges, exactly where PO omits edge diffraction (PTD), creeping waves, and
travelling waves. Gradient-based shape optimisation will happily march into the region where the
model is least trustworthy, because that is where the gradient is largest.

Nobody has tested this. It is testable in-house: AEGIS already validated the Fock model against an
exact cylinder solution (see `project_diffraction_fock` memory, `tests/test_fock_diffraction.py`).
Compare `∇` of PO against `∇` of the analytic Mie/cylinder solution w.r.t. radius, frequency, and
incidence angle. If gradient cosine similarity is poor near shadow boundaries, several ideas in this
study die and you must say so.

---

## 3. Why differentiability might be worth money: the four mechanisms

Do not say "gradients are fast." Say *which* mechanism, and check that the market has it.

**(a) High-dimensional design.** Gradients beat sweeps only in high dimension; below ~10 parameters
a sweep or a surrogate wins and gradients are worth nothing. So the design vector must be big.
Candidates that are genuinely big: precoder `x` (M=256 complex = 512 real), SMPL-X pose (63+),
per-triangle coating impedance (10⁴-10⁵), mesh vertices (10⁵), RIS element phases (10³-10⁴).

**(b) Inversion and calibration.** A differentiable forward model turns any measurement into a
gradient-descent fit: recover shape, pose, material, or array calibration from observed scattering.

**(c) Exact sensitivity coefficients.** Certification standards (IEC 62232, IEC 63195, ISO GUM)
*legally require* an uncertainty budget with sensitivity coefficients `c_i = ∂y/∂x_i`. Today those
are obtained by finite differences (2N simulations) or simply assumed. Autodiff gives them exactly,
in one pass. This converts differentiability from a nice property into a mandated, billable
deliverable. It is boring and it may be the strongest link between gradients and revenue.

**(d) Certified suprema over continua.** Gradients bound Lipschitz constants, which turns
branch-and-bound into a *certificate* over a continuous parameter space rather than a sample of it.
See section 5: this is probably where the patent has to move.

---

## 4. Ethics boundary. This persists verbatim from the previous study.

This study covers: hazard characterization, personnel protection, compliance and certification,
safety-of-effect for already-fielded systems, survivability and signature management of *platforms*,
sensing and imaging, and inverse design of *objects*.

This study does **not** cover, and no subagent should produce: optimization of a system to maximize
injury to targeted people, targeting or lethality engineering, or any design whose deliverable is
better harm to a human. If your line of inquiry drifts there, **stop and say so in your report.**

"Optimize with respect to a human body" is in scope when the objective is to protect, to sense, to
communicate, to certify, or to treat. It is out of scope when the objective is to hurt. The
distinction is the sign of the objective and the consent of the person, not the vocabulary.

---

## 5. What is already dead. Do not re-propose these.

From `spinoff/military_angle/SYNTHESIS.md` (eleven agents, 2026-07-09) and
`papers/jsac_archeology.md`:

- **Military RF safety as the company.** Three independent kills: the operational pain is
  misattributed (radar blanking is EMCON/HERO, not personnel/HERP); Epirus Leonidas already holds
  HERP/HERF/HERO certification via physical measurement with no body model; AFRL already funded the
  exact product (RATE-EM, Stellar Science, ~$1.5M, to 2027) inside a US supply chain (ITAR, CMMC L2
  from Nov 2026) a two-person EU firm cannot enter.
- **The closed-form exposure envelope as novel IP.** `λ_max(Q)` is the MRI Virtual Observation Point.
  Eichfelder & Gebhardt MRM 2011; Siemens US8,547,097B2 (priority 2009); and, in AEGIS's own mmWave
  domain, Xu et al. IEEE T-EMC 2018 (DOI 10.1109/TEMC.2018.2832445) published both the eigenvalue
  certificate and the per-element-constrained SDP. ZMT ships it as the "Q-Matrix toolbox."
- **The "57x death ray."** Peak ΔT scales as 1/radius, not 1/area (lateral conduction). It is a
  ~2.6x thermal effect at 28 GHz, and Hashimoto & Hirata (2017) and Neufeld & Kuster (2018)
  published most of it.
- **The body-aware exclusion zone.** Ties the incumbent (361 m vs 369 m at X-band). ICNIRP's
  reference level already bakes in the `T0` coupling factor.
- **Exposure as a binding constraint.** Established three separate times: Direction 4 (worst patch
  is a geometric artefact), JSAC v1 (four orders of magnitude of slack), JSAC2 PoC (user sits at
  0.001× the basic restriction). Exposure is a transparency product, never an optimisation
  constraint. Any idea whose value depends on an exposure limit binding is dead on arrival unless
  you show the regime where it binds.
- **The MCS cap eats channel-quality gains.** Sell SINR or Mbps, never rate-dB.
- **mmWave device pre-compliance.** Robin: *"I already KNOW pre-compliance clients would like our
  stuff. But that's a convo for another day."* It is the presumed civilian beachhead. Do not spend
  your report re-arguing for it.

**Where the patent probably has to move.** Prior art gives the supremum over the *excitation*
continuum (VOP eigenvalue). Nobody gives a certified supremum over the *configuration* continuum
(pose, position, orientation, shape) because nobody had a differentiable geometry→field map. AEGIS
does. Standards bodies today test a handful of postures and hope. A Lipschitz / branch-and-bound
certificate over all postures would be new, would be what a regulator actually needs, and depends
on differentiability *essentially* rather than decoratively. Attack this idea if you can.

---

## 6. What Robin has, and what is in reach

- Ending a PhD at UGent and IMEC (WAVES group, Wout Joseph). Spinning off a BV with a co-founder,
  Carolina. VLAIO and istart funding tracks. An IOF project whose deadline is 3 Aug.
- The code: nine fidelity levels, JAX backend, a Flask + React 3D viewer, a Sionna RT and DiffeRT
  ray-tracing bridge, SMPL-X parametric bodies, four phantoms (duke, ella, eartha, thelonious),
  the IT'IS tissue database, a Cloudflare R2 grid of precomputed studio scenes.
- An IDF filed with UGent TechTransfer, sole inventor, zero public disclosures. Patent attorney
  Alessandro is live and time-sensitive.
- Warm academic reach: Hirata (Nagoya, and a likely reviewer), KU Leuven WaveCoRE 28 GHz array
  (Pollin, Schreurs) one hour from Ghent, Jerome Eertmans (DiffeRT), Tom Dhaene (EDA/surrogates).
  Professor-to-professor introductions are cheap and available.
- Robin's own framing of the freedom you have: *"You can truly be creative, even if you're like,
  bro go partner with someone that builds crazy antennas and go test it on a human."*
- Robin's hint, unprompted: *"pose estimation is just a relatively easy engineering task nowadays,
  so building a good human digital twin is somewhat doable."*

Constraints: two people, EU, no security clearance, no US supply-chain access, no fab, no
measurement chamber of their own. Anything requiring a cleared US prime or a €1M capital
expenditure is not reachable and should be graded accordingly.

---

## 7. Reporting discipline

Write to `spinoff/differentiability/agent_reports/NN_your_slug.md`.

- **Diverge before you converge.** Open with a raw idea list: at least 15, unfiltered, one line
  each. Then rank them and defend the top three to five with real evidence.
- **Mark every claim** as `verified` (you found the source, cite it), `inferred` (you reasoned to
  it, show the reasoning), or `could-not-check`. An unmarked claim will be treated as invented.
- **Grade each surviving idea** on: does a problem exist, can Robin fill it reliably, is it
  patentable, is it doable in two years by two people, how big is the market, and *does the value
  depend on differentiability essentially or decoratively*. The last one is the whole study. If the
  idea would work almost as well with finite differences or a surrogate, say so and downgrade it.
- **Name the incumbent** for every market. If you cannot name who the customer buys from today, you
  have not found a market.
- **NEEDS_CONTEXT protocol.** If you are blocked by a missing API key, a paywall, a site that
  refuses you, or a tool you do not have, write `NEEDS_CONTEXT:` and the exact ask at the top of
  your report. Do **not** silently downgrade to a worse method. Robin can supply keys, run browser
  steps, and fetch papers. He wants the ambitious answer, not the fast one. Known: the Reddit MCP
  returned HTTP 403 for every agent last study, and `WebFetch` cannot read Reddit or Twitter. Robin
  can also run Gemini Deep Research prompts on request, so if a question needs deep web search,
  write the prompt you would want run.
- No invented identifiers. No fabricated patent numbers, contract numbers, DOIs, or call codes. The
  last study caught Gemini hallucinating EDF call codes and confabulating a "practitioner
  consensus" section. If you did not see it, say you did not see it.
- Style: no em dashes, no semicolons, sentence case for headings.
