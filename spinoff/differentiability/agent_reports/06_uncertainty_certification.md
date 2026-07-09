# 06. Uncertainty budgets and sensitivity coefficients: the mandated, billable, boring mechanism

Lens: mechanism (c). Certification standards require an uncertainty budget with sensitivity
coefficients c_i = dy/dx_i. Autodiff produces them exactly in one reverse pass. Is that a business,
or is it decorative because AEGIS's forward is already fast enough to finite-difference?

Author: Claude Opus, 2026-07-09. Sibling reports 01 (diff-render), 02 (moat), 03 (RCS) are
concurrent, I stay in my lane.

**Headline verdict, stated up front so the rest can defend it.** For the uncertainty budget that
standards mandate *today* (10 to 30 scalar input quantities), autodiff sensitivity coefficients are
**decorative, not essential**, and the reason is AEGIS's own founding virtue. Finite differences cost
2N forward runs, and when a forward run is milliseconds the whole 30-parameter budget finite-differences
in under a minute. Autodiff saves seconds, not days. The mechanism only becomes *essential* in a regime
no standard mandates yet: **spatially resolved, field-valued sensitivity** (per-triangle material, per-vertex
geometry, 10^3 to 10^5 coefficients), where finite differences are infeasible and only reverse-mode works.
So mechanism (c) is a **trajectory bet on where VVUQ is going**, plus a **gradient-enhanced-surrogate
play with a warm UGent contact**, not a today-invoice for faster GUM tables. That is a weaker answer than
the brief hoped for, and I defend it below rather than inflate it.

---

## NEEDS_CONTEXT

Nothing blocking. Two soft gaps I could not close from open web, flagged so Robin can close them:

1. **Clause-level text of the paywalled standards.** I could verify that IEC 62232, IEC/IEEE 63195-2,
   and IEC/IEEE 62704 exist, their scope, and that each explicitly addresses uncertainty of the
   computational assessment. I could **not** open the normative text to confirm whether a full GUM-style
   per-input sensitivity-coefficient table is *required*, versus a lumped conservative uncertainty
   statement being *permitted*. That distinction is the whole business case. If Robin (or Wout, who sits
   on the joint IEC TC 106 / IEEE ICES working group per `spinoff/LATEST_GOOD/standards_play.md`) can
   pull the uncertainty clause of IEC/IEEE 63195-2:2022 and the 2026 draft, this report's grade moves.
2. A Gemini Deep Research prompt worth running is at the very end.

---

## Diverge: 20 places "exact derivatives of a certified physical quantity w.r.t. every input" could be worth money

One line each, unfiltered, good and bad mixed.

1. EMF base-station compliance dossier: auto-generate the GUM Type B sensitivity table for an installation.
2. mmWave device power-density pre-compliance (63195-2): exact c_i for permittivity, distance, frequency, phase.
3. Field-valued uncertainty *map*: per-triangle "which patch of skin does my uncertainty live on", impossible by FD.
4. Gradient-enhanced surrogate training (Sobolev / gradient-Kriging): AEGIS as the free-gradient data generator for Tom Dhaene's surrogates.
5. Global sensitivity ranking to *reduce* a compliance model to the 3 inputs that matter, retire the other 27.
6. Automatic worst-case-direction discovery: the gradient points straight at the posture/position that maximizes exposure uncertainty.
7. Fisher information and Cramer-Rao bounds for any estimator built on the scattering model (calibration, localization).
8. Lipschitz constant extraction for a certified upper bound over a continuous parameter box (branch-and-bound certificate).
9. Design of experiments: use gradients to place the few expensive FDTD confirmations where they matter.
10. Medical-device (MRI RF coil, hyperthermia, implant heating) submission uncertainty budgets to FDA/notified body.
11. Automotive ISO 26262 / SOTIF ISO 21448: argued uncertainty for a radar or in-cabin RF exposure function.
12. Aviation HIRF / DO-160 certification: sensitivity of induced fields to geometry and material tolerances.
13. Radiation-protection and RF-safety consultancies who currently copy sensitivity coefficients from a 2005 paper.
14. National metrology institutes (PTB, NPL, VSL) who literally sell uncertainty and want a differentiable reference model.
15. Notified bodies and test houses (TÜV, UL, SGS) who need defensible budgets fast and at scale.
16. Insurance and product-liability: a signed, reproducible sensitivity budget is an evidentiary asset.
17. Expert-witness / litigation support: "here is the exact derivative of dose w.r.t. the disputed parameter".
18. Standards committees themselves: donate the exact-c_i method as the reference recipe in the next edition.
19. Antenna-array phase-error budgets: exact d(power density)/d(phase_m) across M elements for a MIMO panel.
20. Digital-twin recertification: when the twin's geometry updates, recompute the whole budget in one pass instead of re-running the sweep.

---

## Converge

### The mandate, as precisely as I could establish it

What standards actually govern this, and what each requires. Every clause-level "requires a sensitivity
table" statement below is marked because I could not open the normative text.

| Standard | Scope | Uncertainty status | Marking |
|---|---|---|---|
| ISO/IEC Guide 98-3 (GUM) | The umbrella. Defines u(x_i), c_i = dy/dx_i, combined u_c(y) = sqrt(sum (c_i u_i)^2) | Sensitivity coefficients are *the* GUM object | verified (GUM is the standard framework, universally cited) |
| IEC 62232:2025 (4th ed) | Base-station RF field/PD/SAR, 110 MHz to 300 GHz, incl. beam-steering MIMO | Requires uncertainty budget; measurement side has a 4 dB target expanded uncertainty | verified (scope + 4 dB); could-not-check (whether numerical assessment needs a per-input c_i table) |
| IEC/IEEE 63195-1:2022 | Power density *measurement*, 6 to 300 GHz | Uncertainty budget required (measurement) | verified scope |
| IEC/IEEE 63195-2:2022 | Power density *computational*, 6 to 300 GHz. **2026 edition in draft now** | Computational report must include uncertainty statement / validation evidence | verified (report requires uncertainty statement); could-not-check (per-input c_i table) |
| IEC/IEEE 62704-1/-2/-3:2017 | FDTD SAR, 30 MHz to 6 GHz. Part 1 general, 2 vehicle, 3 phones | Explicitly "assess its uncertainty when used in SAR simulations", defines validation + uncertainty of the numerical model | verified (uncertainty of computation is normative) |
| IEEE 1528-2013 | Peak spatial SAR *measurement*, head | Provides means for estimating overall uncertainty | verified |
| IEEE C95.3-2021 | Measurements *and computations*, 0 Hz to 300 GHz (US sister to 62232/63195) | Blessed computational practices, uncertainty addressed | verified scope (via `standards_play.md`) |

**The load-bearing finding.** Computational dosimetry is **not** exempt from uncertainty. The FDTD-SAR
standard (62704) and the computational power-density standard (63195-2) both make the *uncertainty of the
computation itself* a normative deliverable. `verified`. This kills the naive objection that "sensitivity
budgets are only for measurements". They are required for simulations too.

**But** the honest counter-nuance, which is where the business case bleeds out. The FDTD computational
uncertainty budget is dominated by *numerical-method* contributions that are **not differentiable inputs**:
staircasing / grid discretization, ABC boundary reflection, convergence / truncation, source-model
mismatch, feed-point modeling. Autodiff cannot produce c_i for "staircasing error", because staircasing
is not a smooth function of a continuous input, it is a property of the solver. Autodiff only helps the
*physical-input* rows of the budget: dielectric permittivity and conductivity, phantom geometry and
posture, separation distance, frequency, antenna position, array phase. `inferred` from the structure of
published FDTD SAR uncertainty budgets (e.g. the 62704 validation framework and the Aalto thesis
"Uncertainty in computational RF dosimetry", which I could not open, HTTP 403). So even in the regime where
autodiff *works*, it addresses maybe a third to a half of the budget rows, and the numerical rows still
need convergence studies and benchmark validation. Mechanism (c) is not a whole-budget replacement, it is
a partial-budget accelerator.

### Quantify the pain, with real numbers from the repo

I timed reverse-mode gradient vs finite-difference full-gradient cost through a real AEGIS kernel
(`level3_fresnel`, JAX backend, x64, this machine). Script archived in scratchpad. `verified`, in-repo.

| Parameter count N | 1 forward | reverse-mode grad (all N) | grad / forward | FD full budget (2N forwards) | autodiff speedup vs FD |
|---|---|---|---|---|---|
| 100 | 9.7 us | 9.9 us | 1.0x | 1.9 ms | ~200x |
| 1 000 | 59 us | 9.8 us | 0.16x | 119 ms | ~12 000x |
| 10 000 | 73 us | 13 us | 0.18x | 1.45 s | ~110 000x |
| 100 000 | 189 us | 92 us | 0.49x | 38 s | ~410 000x |

Two facts the table proves. (1) Reverse-mode cost is roughly one forward evaluation and is **independent
of N** (the textbook property, confirmed empirically here). (2) FD cost scales as 2N forwards and blows up.

Now the two cost regimes that decide the whole case.

**Regime A, the mandated GUM budget (small N).** A base-station or device budget has 10 to 30 physical
input quantities. In AEGIS a forward is milliseconds. So the *entire* FD budget is 20 to 60 forwards,
call it well under a minute of wall-clock, embarrassingly parallel, trivially robust. Autodiff replaces
"under a minute" with "milliseconds". **The absolute saving is seconds. Nobody buys that.** `inferred`,
directly from the timing table.

**Regime A', the same budget in an FDTD shop (small N, slow forward).** Here a forward is FDTD-hours.
FD of 30 inputs is 60 runs is days to a week of cluster time, per input quantity, per frequency, per
posture. *That* is real pain. `inferred`, standard FDTD run times. **But AEGIS's autodiff does not relieve
that pain**, because you cannot autodiff Sim4Life or a commercial FDTD kernel. The only way AEGIS's
gradient helps the FDTD shop is if AEGIS *replaces* the FDTD forward, and then you are selling the fast
forward, not the gradient. The gradient rides along for free but is not what closed the sale.

**Regime B, field-valued sensitivity (huge N).** Per-triangle material uncertainty (10^4 to 10^5 triangles),
per-vertex geometry (10^5). Here FD is 2 x 10^4 forwards, which the table shows is ~1.5 s to 38 s even at
AEGIS's ms forward, and at FDTD speed it is flatly impossible (weeks to years). Reverse-mode gets the whole
field in ~1 forward. **This is the only regime where mechanism (c) is load-bearing.** `verified` by the timing.

### The kill test, confronted directly

The brief's kill test: "if a coefficient costs 2 forward runs and you have 30 of them, that is 60 runs, and
if a forward is milliseconds then autodiff saves nothing and mechanism (c) is decorative." **The kill test
lands.** For the budget standards mandate today, it is correct. AEGIS's speed is what disarms FD, and AEGIS's
speed is a *property AEGIS advertises anyway*, so the gradient adds nothing on the cost axis for small N.

The mechanism survives only by moving off the cost axis onto one of three other axes:

- **The dimension axis.** Go to field-valued uncertainty (Regime B) that FD cannot reach. Real, but no
  standard requires it yet, so this is thought leadership, not an invoice.
- **The correctness / traceability axis.** Autodiff c_i are *exact* and *reproducible*, whereas today's
  budgets often *assume* c_i, copy them from an old paper, or estimate them with a coarse two-point FD that
  is itself uncertain. A signed, exact, reproducible budget is an audit and liability asset. Real, but it
  is a quality claim, and quality claims are slow to monetize.
- **The surrogate axis.** Gradients make gradient-enhanced surrogates converge with far fewer samples.
  This has a named buyer at UGent. Best of the three.

I will not pretend the cost axis is alive. It is not, for the mandated budget. Say it plainly.

### The incumbent, named

For computational-dosimetry uncertainty **today**, the incumbent method is **not** finite differences and
it is **not** assumed coefficients. It is **stochastic dosimetry**: build a polynomial-chaos-expansion or
Kriging *surrogate* of the FDTD output over the uncertain inputs, then read variance and Sobol sensitivity
indices off the surrogate. This is the Chiaramello / Parazzini / Fiocchi (IEEE, Politecnico di Milano) and
Sudret-school line of work. `verified` (multiple papers: "Stochastic dosimetry to manage uncertainty in
numerical EMF exposure assessment"; sparse-PCE indoor down-link exposure surrogates; Kriging+PCE for
computational dosimetry). The incumbent exists **precisely because the FDTD forward is too slow to Monte
Carlo directly**, so they interpose a surrogate.

This matters two ways. First, it means the market already accepts a *derived* sensitivity artifact, so
selling one is not a cold-start. Second, and sharper: **AEGIS's fast forward partly obviates the incumbent's
whole reason to exist.** If the forward is milliseconds you can Monte-Carlo it directly, no surrogate needed,
and get the full distribution and the Sobol indices without either FD *or* autodiff. So again AEGIS's *speed*
is the disruptor and the *gradient* is a passenger. The one thing the gradient adds that neither direct
Monte Carlo nor the PCE surrogate gives is the **exact local GUM coefficient c_i = dy/dx_i at the operating
point**, which is a *different object* from the variance-based Sobol index. GUM wants the local partial.
Sobol wants the variance share. Autodiff is the natural, exact source of the local partial. That is a
genuine, narrow, defensible niche. `inferred`, and I am fairly confident in it.

### Widen mechanism (c) beyond compliance (brief point 3): which spin-off has a buyer

- **Gradient-enhanced surrogates (Sobolev training).** Buyer: **Tom Dhaene, UGent**, surrogate-modeling
  authority and a warm contact per the brief. Gradient-enhanced Kriging and Sobolev-trained neural
  surrogates need far fewer samples for the same accuracy, and AEGIS hands over exact gradients for free.
  Pitch: AEGIS is the ideal *training-data generator* for a certified fast dosimetry surrogate. **Caveat that
  I must state:** because AEGIS's forward is already cheap, the sample-efficiency win matters most when the
  surrogate must generalize over expensive *external* inputs (a Sionna-RT scene, an FDTD confirmation),
  not over AEGIS's own cheap parameters. So the honest framing is a *hybrid* surrogate, AEGIS-gradient-enhanced
  where AEGIS is the physics and something expensive is the environment. This is the most fundable of the
  widenings and it lands on a named professor one hour away. `inferred`.
- **Fisher information / Cramer-Rao.** Buyer: anyone doing model-based *estimation* on scattering (array
  self-calibration, RF localization, material ID). Real math, thin near-term buyer for a two-person EU firm.
- **Lipschitz / certified suprema over a continuum.** This is mechanism (d), covered by the brief's
  "where the patent has to move" and better argued in a sibling report. It uses the gradient *essentially*.
  Flagging the overlap, not claiming it here.
- **Global sensitivity ranking for model reduction.** Buyer: standards committees and consultancies who
  want to justify ignoring 27 of 30 inputs. Nice, but this is a service, not a product.
- **Worst-case direction / DoE.** Feature of the above, not a standalone business.

---

## Grade the survivors

Grading criteria per brief: problem exists / Robin can fill it / patentable / doable in 2 years by 2 people /
market size / **differentiability essential or decorative** / named incumbent.

### Survivor 1: field-valued (spatially resolved) uncertainty maps

- Problem exists: **weakly today, strongly on trajectory.** No standard asks "which triangle carries the
  uncertainty" yet. VVUQ push (IEEE/ICES, ASME VVUQ, the 63195-2 2026 redraft) is heading toward richer
  uncertainty reporting. `inferred`.
- Robin can fill it reliably: **yes.** This is literally what reverse-mode over the per-triangle field does,
  and the repo already differentiates through the levels. `verified` (tests, timing).
- Patentable: **maybe, narrowly.** "Spatially resolved sensitivity of a certified exposure quantity via
  reverse-mode AD over a surface-field operator" is not obviously prior-arted, but I did not do an FTO scan
  and the sibling patent report should own that. `could-not-check`.
- Doable in 2 years by 2 people: **yes.**
- Market size: **small today, unknown-but-possibly-large on trajectory.** Depends entirely on standards
  adopting field-valued UQ.
- Differentiability: **essential.** FD cannot do 10^5 coefficients. This is the one survivor where the
  mechanism is not decorative. `verified` by the timing table.
- Incumbent: **none, that is both the opportunity and the warning** (no incumbent can mean no market).

### Survivor 2: gradient-enhanced certified surrogate, with Tom Dhaene

- Problem exists: **yes.** Certified fast surrogates for dosimetry are an active field (stochastic dosimetry
  incumbent). `verified`.
- Robin can fill it: **yes, and has the warm contact.** `verified` (brief).
- Patentable: **weak.** Gradient-enhanced surrogate modeling is a mature published technique. The novelty
  would be the *physics that supplies the gradient*, not the surrogate method. `inferred`.
- Doable in 2 years: **yes**, and it doubles as a paper with a UGent co-author.
- Market size: **medium**, tracks the surrogate-modeling / EDA world Robin is already courting (Tom Dhaene,
  the generalization-EDA thread in memory).
- Differentiability: **essential-ish, but honestly hedged.** Gradient-enhanced surrogates *need* gradients
  by definition, so within that method differentiability is essential. But the method itself is optional:
  because AEGIS's forward is cheap you could train a plain surrogate on forwards alone. So the mechanism is
  essential *conditional on choosing the gradient-enhanced method*, and that choice is only clearly worth it
  when the surrogate spans an expensive external input. Downgrade accordingly. `inferred`.
- Incumbent: **Chiaramello/Parazzini stochastic-dosimetry PCE, and UQLab (Sudret, ETH)** as the tooling.

### Survivor 3: standards-embedding of the exact-c_i recipe

- Problem exists: **yes, structurally.** Per `standards_play.md`, getting a method named in IEC/IEEE 63195-2
  (2026 edition, in draft *now*) is worth more than any single customer, and Wout is on the working group.
- Robin can fill it: **plausibly**, via Wout and the monograph, but this is committee work not a product.
- Patentable: **N/A / counterproductive** (you donate it to get it cited).
- Doable in 2 years: the *contribution* yes, the *payoff* no (standards move on multi-year cycles).
- Market size: **large and indirect** (the Kuster/IT'IS lock-in playbook).
- Differentiability: **decorative-to-supporting.** The standard would specify *that* you report exact c_i,
  not *how*. AEGIS becomes the reference implementation, but a competitor could FD the small-N budget and
  comply equally. So differentiability is the *marketing edge*, not the *barrier*. `inferred`.
- Incumbent: the committee status quo (assumed or FD coefficients, lumped conservative uncertainty).

---

## The one-paragraph answer to Robin's actual question

Can differentiability carry a business *through mechanism (c)*? **On its own, no.** The mandated uncertainty
budget is small-N, and AEGIS's millisecond forward lets anyone finite-difference it in under a minute, so the
gradient is decorative exactly where the legal mandate lives. Mechanism (c) is essential in only one regime,
field-valued sensitivity over 10^3 to 10^5 inputs, which no standard requires yet, so it is a bet on the
VVUQ trajectory rather than a current invoice. The most fundable near-term expression is not "sell the c_i
table", it is "AEGIS is the exact-gradient physics engine behind a certified surrogate", which puts Tom Dhaene
and the 63195-2 2026 redraft in the same room. Treat mechanism (c) as a **credibility and standards-position
multiplier on top of the fast forward**, not as a standalone revenue line. If the study is ranking the four
mechanisms, (c) should sit *below* (a) high-dimensional design and (d) certified suprema, because both of
those use the gradient essentially while (c), for the mandated budget, does not.

---

## Ethics check

In scope throughout: compliance, certification, metrology, hazard characterization. No drift toward
harm-optimization. Nothing to flag.

---

## Claim ledger

- Reverse-mode ~= 1 forward, N-independent, FD ~= 2N forwards, with the exact us/ms numbers: **verified**, in-repo benchmark, `level3_fresnel`, JAX x64, script in scratchpad.
- IEC 62232:2025 4th ed, base stations, beam-steering, 4 dB measurement target uncertainty: **verified** (IEC blog, genorma listing, review papers, `standards_play.md`).
- IEC/IEEE 63195-1/-2:2022, 6 to 300 GHz, computational report requires uncertainty statement, 2026 edition in draft: **verified** scope; **could-not-check** whether a per-input c_i table is normatively required.
- IEC/IEEE 62704-1/-2/-3:2017 assess uncertainty of the FDTD computation: **verified** (IEEE Xplore scope text).
- IEEE 1528-2013 measurement SAR uncertainty; IEEE C95.3-2021 measurements and computations: **verified** scope.
- GUM = ISO/IEC Guide 98-3, c_i = dy/dx_i the central object: **verified** (universal).
- Stochastic dosimetry (PCE / Kriging surrogate, Sobol indices) is the incumbent computational-UQ method, Chiaramello/Parazzini/Sudret: **verified** (multiple papers).
- FDTD uncertainty budget is dominated by non-differentiable numerical rows (staircasing, ABC, convergence): **inferred** from published FDTD-SAR budget structure; could not open normative text.
- GUM local c_i differs from variance-based Sobol index, autodiff is the natural exact source of the former: **inferred**, confident.
- Complex-step + FDTD field derivatives already exist as prior art for on-the-fly EM sensitivities (arXiv 1901.02315): **verified** existence, not read in full.
- Patentability of the field-valued-sensitivity idea: **could-not-check**, no FTO scan done.

No invented standard numbers, DOIs, or clause codes. Where I did not open the document I said so.

---

## Gemini Deep Research prompt to close the mandate gap

> Pull the normative uncertainty-evaluation clauses of IEC/IEEE 63195-2:2022 and its 2026 draft, and of
> IEC/IEEE 62704-1:2017. For each, state whether a compliant *computational* assessment must tabulate
> individual input quantities with a standard uncertainty and a sensitivity coefficient c_i = dy/dx_i and
> combine them per ISO/IEC Guide 98-3, or whether a single lumped/conservative uncertainty statement is
> permitted. List every input quantity the standard names for the computational budget. Separately, find
> any IEEE ICES or IEC TC 106 working-group document from 2023 to 2026 proposing spatially resolved or
> field-valued uncertainty reporting for computational dosimetry. Give exact clause numbers and quote the
> requirement text. Do not infer, quote or say not found.
