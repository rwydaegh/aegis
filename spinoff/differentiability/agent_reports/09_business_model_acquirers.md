# Who pays, how, and who buys the company

Agent 09. Lens: business model, revenue mechanics, and the acquirer thesis. Written 2026-07-09 for the
differentiability study. My job is to test Robin's stated ambition, verbatim: *"hoping this is a
bigger market (if we can spinoff-to-acquire into the big EDA players like Dassault would be cool, or
license to them)."*

I read the BRIEF, `military_angle/SYNTHESIS.md`, and Robin's own `LATEST_GOOD/honest_analysis.md` and
`funding_stack.md` first, so this does not restate his prior work. Where I confirm something he
already wrote, I say "Robin already has this" and move on.

Every deal figure below is marked `verified` (I found the number and the source), `inferred`, or
`could-not-check`. No invented numbers. The last study caught a model fabricating deal codes, so I
have erred toward "could-not-check."

---

## NEEDS_CONTEXT

None blocking. Reddit MCP was not needed for this lens (M&A facts are in press releases and SEC
filings, which WebFetch and WebSearch reach fine). Two numbers I would upgrade from inferred to
verified if Robin wants them: ZMT's actual revenue and headcount (a getlatka scrape says ~$2.3M / 15
people, which is an unreliable source), and whether Ansys HFSS specifically ships a full-wave EM
adjoint (I verified Fluent's CFD adjoint and Lumerical's photonic adjoint, not HFSS). Neither changes
the conclusion.

---

## 1. Diverge: 25 ways this becomes money, one line each

Unfiltered, including bad and unglamorous ones. Ranked later.

1. Consulting and paid studies for OEM compliance teams (cash in year one, zero leverage).
2. Node-locked / SaaS software license, sold as an mmWave APD pre-screener (Robin's accepted wedge).
3. OEM component: license the gradient engine into ZMT Sim4Life as a fast pre-solver SKU.
4. OEM component into a *ray-tracing* vendor (Remcom, Sionna) as the body-surface scattering block.
5. Certification / uncertainty-budget service: sell the exact sensitivity coefficients IEC 62232 and
   ISO GUM legally require, as a billable deliverable.
6. IP-licensing shell: granted patent + a willing infringer, royalty on the differentiable field-channel.
7. Precomputed scattering-library data product (the R2 studio grid, sold as content, not software).
8. Sell to test houses (Eurofins, Verkotan, PCTEST) as an overnight batch pre-screen.
9. Sell to notified bodies / national regulators (BIPT, ANFR, Ofcom) as reference tooling.
10. Sell to insurers underwriting RF-exposure or product-liability risk (dose transparency).
11. A Blender / Unreal plugin: physically-correct RF-body scattering for content and game/AR pipelines.
12. Automotive scenario-validation physics backend (radar/RCS of pedestrians for AV sensor sim).
13. Open-core: free differentiable forward model, paid worst-case-certificate / solver / support.
14. Standards-body reference implementation: get cited in IEC 63195-2 as the accepted fast method.
15. Acquired by NVIDIA into Sionna as the differentiable surface-scattering / body-twin layer.
16. Acquired by a phantom vendor (ZMT/SPEAG, Robin's own first customer) as their fast digital twin.
17. Merge with a differentiable-rendering startup (the Fock-gate soft-rasterizer as the joint asset).
18. License to a radar-simulation vendor (the discarded reflected-half = RCS, agent-06 territory).
19. Sell gradients as an API: POST a mesh + sources, GET back Q, lambda_max, and d(output)/d(input).
20. Training-data generator for a Physics-AI surrogate company (PhysicsX / Neural Concept feedstock).
21. Tuck-in acquisition by Keysight/Cadence/Synopsys-Ansys as an EM-portfolio gap-filler (Lumerical shape).
22. Research group + IOF project + UGent licensing arm, no company at all (the anti-spinoff path).
23. Antenna-design co-optimization tool sold to handset RF teams (minimize APD, maximize gain, one loop).
24. RIS / metasurface phase-optimization tool (10^3-10^4 element design vector, gradient-native).
25. Coating / material inverse-design service for "electrically large smoothish objects" (signature).

The lens of this report is 2, 3, 5, 15, 16, 20, 21, 22. The physics of 12/18/25 belongs to other
agents; I only price the *money* of them.

---

## 2. The EDA / simulation consolidation, factually

I checked every deal the brief named. Real numbers, real dates, real theses.

| Deal | Value | Announced / closed | Stated thesis (their words) | Does "differentiable" appear? |
|---|---|---|---|---|
| Synopsys - Ansys | **$35B** (cash+stock) | announced 16 Jan 2024, **closed 17 Jul 2025** | "Silicon to Systems": chip performance analyzed in the context of the whole system; AI-driven design-space exploration; 3DIC / chiplet multiphysics | No. AI and system-level, not gradients |
| Siemens - Altair | **~$10.6B equity / ~$10B EV** | announced 30 Oct 2024, **closed 26 Mar 2025** | "Most complete AI-powered portfolio of industrial software": simulation + HPC + data science + AI | No. "AI-powered industrial software" |
| Renesas - Altium | **$5.9B USD** (A$9.1B) | announced 15 Feb 2024, **completed ~1 Aug 2024** | Unified electronics system-design + lifecycle-management *data platform* | No. It is a data/PLM-cloud thesis |
| Cadence - BETA CAE | **$1.24B** (~$90M rev, ~13.8x) | **closed 30 May 2024** | Enter structural analysis; multiphysics *system* analysis; automotive vertical | No. Multiphysics + vertical TAM |
| Ansys - Lumerical | **~$107.5M cash** | **closed 1 Apr 2020** | Add photonics to the multiphysics portfolio for 5G / optical / autonomous | The adjoint (lumopt) shipped before the deal but was **not** the stated reason |

All five rows `verified` (Synopsys/Ansys news + RCR Wireless + Forbes; Altair investor release +
Bloomberg + Siemens press; Renesas + Altium press; Cadence press + pulse2; Ansys 8-K / MarketScreener
+ optics.org). Sources at the end.

**The thesis driving the mega-deals, plainly.** It is "silicon to systems" and "AI-powered industrial
software" and "system-design data platform." Every one of them is about linking chip design to
system-level outcomes, folding an ML/AI layer over an existing solver portfolio, and buying a
*vertical* (automotive structural analysis, electronics PLM, photonics for optical networks). The
unit they pay for is a **market position plus a customer base plus a solver franchise**, priced at
low-double-digit multiples of revenue when there is revenue (BETA CAE 13.8x), and paid in the low
hundreds of millions when it is a technology tuck-in with a small book (Lumerical $107.5M).

**Where does a differentiable RF body-scattering engine fit into that thesis? It does not.** `inferred,
high confidence.` "Differentiable" is not a word in any of these deal narratives. The acquirers are
buying AI *layers* (learned surrogates over their own solvers) and *verticals* (a named industry with
named marquee customers). AEGIS is neither a vertical they are missing nor an AI layer over their
stack. To a Synopsys or a Siemens, a two-person tool that computes absorbed power on human bodies is
invisible: it is not silicon, not a system-design data platform, and its TAM (Robin's own estimate
30-100M global) is a rounding error against a $35B deal. **The direct "spinoff-to-acquire into
Dassault/Synopsys via differentiability" ambition is, in the form Robin states it, a fantasy.** I will
qualify that hard in section 6, because there is a real and smaller version of it.

One factual correction to the brief's framing: Dassault is named as the dream acquirer, but Dassault
(SIMULIA/CST) was *not* an acquirer in this consolidation wave. The buyers were Synopsys, Siemens,
Cadence, Renesas, Keysight. Dassault has been comparatively quiet on M&A here. `verified` (absence
across all the deal coverage I read). If Robin fixates on Dassault specifically, he is aiming at the
one big player that is not currently in acquisition mode for EM simulation.

---

## 3. Comparables: what a *differentiable* or AI-physics simulator actually got paid

This is the most important section for the money question. I separated two categories that the hype
blurs together, because they price completely differently.

### 3a. The category that is raising huge money: ML surrogates, not differentiable solvers

| Company | Money | What it is | Is *differentiability* the reason? |
|---|---|---|---|
| **PhysicsX** | $135M Series B (Jun 2025, ~$1B), **$300M Series C Jun 2026 at ~$2.4B valuation** | "Large Geometry Models" trained on tens of thousands of FEM/CFD sims | No. It is a **learned surrogate**. The value is the trained model, not exact gradients |
| **Neural Concept** | $27M Series B, then **$100M (Dec 2025)** | "Neural Concept Shape": GNN surrogate learned from past FEM/CAD | No. Learned surrogate over an existing solver |
| **Luminary Cloud** | $72M Series B (Sep 2025), **$187M total** | GPU-native CFD + "Physics AI" via NVIDIA PhysicsNeMo | Partly (GPU solver) but the pitch is AI surrogate + speed |

All `verified` (physicsx.ai newsroom + techfundingnews + pulse2; pulse2 + siliconangle; siliconangle +
luminary.ai + space-startups tracker).

The single most important finding of this report: **the venture money labelled "differentiable /
AI physics" is going to learned surrogates trained on the accurate solver's output, not to
first-principles differentiable solvers.** A 2025 market write-up I read frames it as a two-tier
structure: a small cohort of "AI-native pure-play" surrogate vendors, and the incumbents bolting AI
onto their solver portfolios. AEGIS is in neither tier. It is a *third* thing: a physically-grounded,
first-order-analytic forward model that happens to be differentiable and needs no training data.

That third position cuts both ways, and Robin should hold both edges at once:

- **Against him:** no VC is currently writing $135M checks for "we have exact analytic gradients." The
  checks are for "we have a trained model that replaces your solver." Robin's differentiability is not
  the thing the hot money is priced on. `inferred, high confidence.`
- **For him:** every one of those surrogate companies has a data problem. A GNN surrogate is only as
  good as the FEM sims it was trained on, and mmWave-on-body FDTD sims are hours each. **A fast,
  physically-correct, differentiable forward model is a training-data factory** (diverge idea 20). This
  is a real and non-obvious way AEGIS is worth money to PhysicsX/Neural Concept/Luminary: not as a
  competitor, as feedstock and as a physics prior. `inferred.` No comparable transaction found to price
  it, so `could-not-check` on the number.

I searched specifically for an M&A *exit* of a differentiable-physics startup in 2024-2025 and found
**none**. `verified` (explicit null result across the differentiable-simulation and deep-tech-VC
coverage). The exits in this space are the surrogate fundings above, and the incumbent tuck-ins below.
There is no established "differentiable solver gets acquired for its gradients" precedent to point at.

### 3b. The category that matches AEGIS's shape: the Lumerical template

The Lumerical case is the one Robin should study, because it is the only clean precedent for "niche,
adjoint-capable EM/physics tool acquired by a big simulation incumbent," and it is his realistic ceiling.

- Ansys bought Lumerical for **~$107.5M cash** in 2020. `verified` (MarketScreener citing Ansys Q1
  2020 results; Ansys 8-K).
- Lumerical shipped **adjoint inverse design** (the `lumopt` Python module, continuous adjoint over
  FDTD) *before* the acquisition. `verified` (Ansys developer portal docs).
- Ansys's stated reason was **photonics market coverage** for 5G / optical / autonomous, folding
  best-in-class photonics into the multiphysics portfolio. The adjoint/differentiability was a feature
  they inherited, not the headline rationale. `verified` (Ansys press release; the adjoint is absent
  from the deal narrative).

The lesson for Robin, stated bluntly: **the differentiability did not set the price. The market did.**
Ansys paid nine figures for a *category* (photonics EDA) with real OEM customers and a standards
footprint, and got the adjoint for free. If AEGIS wants a Lumerical-shaped exit, the thing that must
be true is not "our gradients are exact." It is "we own the fast mmWave-body-APD pre-compliance
category, with OEM logos and an IEC citation." The gradients are the moat that lets him *own* the
category faster, not the line item an acquirer underwrites. That is exactly Robin's own
honest_analysis conclusion ("the moat is execution speed, plumbing, viewer, ZMT partnership, and
standards recognition, not the physics"), now confirmed against a real transaction.

### 3c. Adjacencies that matter for the acquirer map

- **Remcom** (XFdtd + Wireless InSite) shipped, Dec 2024, a "Huygens Antennas" capability that
  integrates on-body near-field and far-field EM modeling in *dynamic* scenarios (moving people,
  wearables, 5G/6G). `verified` (globenewswire + everythingrf). This is the closest existing product
  to AEGIS's "human digital twin in a wireless environment," it uses an equivalence-principle *surface*
  (conceptually adjacent to AEGIS's surface operator), and Remcom is privately held. That makes Remcom
  simultaneously the most direct competitor and one of the more plausible small acquirers. Robin does
  not name them in his docs. He should.
- **NVIDIA Sionna** is a differentiable RT engine for 6G, NVIDIA-owned and open-source. `verified`
  (NVIDIA developer + Sionna docs). Sionna has hard-visibility ray tracing; the BRIEF's Fock-gate
  claim (differentiable soft shadow with physically-correct gradients) is precisely the thing Sionna
  lacks. "Acquired by NVIDIA into Sionna" (diverge idea 15) is aspirational but not absurd. It is also
  the one path where "our gradients are structurally better than yours" is a *technical* argument an
  acquirer would actually care about, because Sionna's whole reason to exist is differentiability.
- **ZMT / SPEAG / IT'IS** are the "Zurich43" alliance, foundation-anchored, not private-equity-owned.
  `verified` (zmt.swiss/about; Zurich43). A foundation-linked group is an unusual *acquirer* (they buy
  little, they build) but a natural *licensor/partner* and a very natural first customer, which is
  Robin's own read. Treat ZMT as a channel and a validation stamp, not as the exit. `inferred.`

---

## 4. The uncomfortable question: does anyone pay for a deliberately approximate model?

The BRIEF's sharpest challenge: AEGIS is fast because it is approximate, but EDA sells *accuracy*, so
is there any market for a deliberately-approximate-but-differentiable model, and did anyone pay for it?

**Yes, and it is exactly the PhysicsX/Neural Concept/Luminary money in section 3a.** Those companies
sell deliberately approximate models (learned surrogates, wrong by a few percent) and raised, between
them, well over half a billion dollars. `verified.` So the abstract objection "nobody pays for
approximate" is empirically false. The market for approximate-but-fast is large and hot right now.

But follow the logic where the BRIEF points it, because the conclusion is precise and it prices the
company. The approximate model is never sold as the *answer*. It is sold as the **screening front-end
that feeds the accurate solver**:

- PhysicsX/Neural Concept surrogates screen thousands of designs, then the survivors go to FEM/CFD.
- Flexcompute Tidy3D's adjoint inverse design proposes a photonic device, then full FDTD validates it.
- Robin's own honest_analysis already frames AEGIS this way: "accelerate pre-screening 100-1000x, then
  feed the worst-case scenarios into Sim4Life for rigorous validation, then DASY for certification."

If AEGIS's honest business is to be **the front end of somebody else's accurate solver, then the
natural acquirer is the owner of that solver.** That is the whole answer to the BRIEF's question 4,
and it is unforgiving: the owner of the accurate mmWave-body solver is **ZMT (Sim4Life)**. The owner
of the accurate photonic/RF adjoint stack is **Ansys (Synopsys)**. The owner of the differentiable RT
front end for 6G is **NVIDIA (Sionna)**. AEGIS's acquirer is one of those three, and the price is a
front-end tuck-in price (Lumerical shape, tens to low-hundreds of millions), not a category-winner
price.

There is one important asymmetry in AEGIS's favour that the surrogate front-ends do not have.
**AEGIS's approximation is physically grounded, not learned, so it produces exact analytic gradients
with no training-data dependency and it extrapolates outside any training set.** A learned surrogate's
gradient is the gradient of a fit, trustworthy only where it was trained. AEGIS's gradient is the
gradient of a physics model, trustworthy wherever the physics holds. For the *inversion and
sensitivity-coefficient* uses (BRIEF mechanisms b and c), that difference is the entire value, because
a certification deliverable that legally must report c_i = dy/dx_i cannot rest on a surrogate's
possibly-biased gradient. This is the one place where "differentiable" is load-bearing and not
decorative, and it is boring, mandated, and billable. Robin's own docs underweight it. `inferred, and
it is the strongest money-to-gradient link I found.`

**Does the rewrite-moat claim survive?** The BRIEF asks whether "gradients are what an incumbent's
non-differentiable stack cannot retrofit without a rewrite," and whether a rewrite is actually hard
for Ansys. **The claim does not survive for the tier-1 acquirers.** Ansys ships an adjoint solver in
Fluent (a free CFD add-on for gradient-based shape optimization) and has shipped adjoint photonics via
Lumerical's `lumopt` since 2020. `verified` (Ansys Fluent adjoint docs; Ansys developer portal). They
have deep adjoint expertise across two solver families already. The "they cannot retrofit gradients
without a rewrite" premise is false against exactly the acquirers Robin dreams of. Where the claim has
*some* teeth is narrower: nobody has retrofitted a differentiable, *measurement-free, Fresnel-surface,
mesh-native body-field-channel* into a ray-traced environment, because that specific construction is
what the redrawn patent has to protect (agent-01 and the SYNTHESIS already carry this). The moat is
the *specific differentiable construction plus the domain plus the standards footprint*, never
"gradients" as a generic capability. `inferred, high confidence.`

---

## 5. Revenue mechanics: rank the vehicles for a two-person EU firm

Ranked by year-one cash-realism for two people in Ghent, with the differentiability-dependence graded.

1. **Consulting and paid studies.** Immediate cash, zero leverage, funds the runway while the product
   hardens. This is how Robin eats in year one regardless of everything else. Differentiability:
   decorative (a client pays for the answer, not the gradient). Doable now. Robin already knows this.
2. **Certification / uncertainty-budget service (sensitivity coefficients).** Recurring, credentialed,
   billable, *mandated* by IEC 62232 / ISO GUM. Slow to accredit but sticky once in. Differentiability:
   **essential** (exact c_i in one pass vs 2N sims). This is the boring strong link. Under-exploited in
   Robin's docs.
3. **Software license (node-locked / SaaS) as the mmWave APD pre-screener.** Robin's accepted wedge; I
   will not re-argue it. ACV for a niche EM tool: his own estimate 30-60k EUR/seat is the right order,
   cross-checked against Sim4Life-equivalent seat pricing. Differentiability: partly essential (the
   antenna/pose co-optimization loop), partly decorative (batch pre-screen would work with sweeps).
4. **OEM component into ZMT / Sionna / Remcom.** Lower control, revenue-share, but it is the on-ramp to
   the acquisition (section 6). Differentiability: essential *if and only if* the component sold is the
   gradient/inversion block; decorative if it is just "fast forward model." Sell the gradients, not the
   speed.
5. **Data / precomputed-library product (the R2 grid).** Passive, low-margin-of-attention, a nice
   add-on, not a company. Differentiability: irrelevant. Cheap to try.
6. **IP-licensing shell.** Needs a granted patent (years away) and a willing infringer (needs the
   market to exist first). Not a year-one or year-two vehicle. Differentiability: this is where a
   *certified-supremum-over-configuration* patent (BRIEF section 5) would live, and it depends on
   differentiability essentially, but it is the slowest path to cash.

The BRIEF's specific claim to test: "an OEM component that computes gradients is *more* valuable to an
acquirer than a standalone tool, because gradients are what an incumbent's stack cannot retrofit." My
verdict: **half true, and the true half is not the half Robin thinks.** Gradients are more valuable to
an acquirer *whose product is itself differentiable and lacks a physics-correct body/surface layer*
(NVIDIA/Sionna), and to an acquirer who wants the training-data-free sensitivity deliverable
(ZMT for certification). Gradients are *not* a retrofit moat against Ansys/Synopsys, who already ship
adjoint. So "sell the gradient component" is the right strategy pointed at the right acquirer (Sionna,
ZMT), and the wrong strategy pointed at the dream acquirer (Synopsys-Ansys). Point it correctly.

---

## 6. Converge: the acquirer thesis, graded, and Robin's ambition scored

**Grade each surviving path against: real problem, can Robin fill it, patentable, doable in 2 yr by 2,
market size, and differentiability-essential-or-decorative.**

### Path A. Lifestyle-to-modest-exit into ZMT (license -> acquire). Grade: A-.
- Problem: real (mmWave APD pre-compliance, Robin's wedge). Fill: yes, he built GOLIAT on their stack.
- Patentable: the field-channel construction, yes (agent-01). 2yr/2people: yes. Market: 30-100M global.
- Differentiability: essential for the certification-sensitivity and co-optimization value, decorative
  for the batch pre-screen. Acquirer: ZMT, but they are foundation-anchored and build more than they
  buy, so weight this as **license-first, acquisition-maybe**. This is Robin's own base case and the
  evidence supports it. Realistic exit 3-15M EUR (his number), Lumerical says the ceiling is ~$100M+
  only if he first *owns the category*.

### Path B. Front-end-of-Sionna into NVIDIA. Grade: B+ on fit, C on reachability.
- Problem: Sionna has hard-visibility gradients; AEGIS's Fock-gate soft-shadow gradients are the thing
  it lacks. This is the one acquirer for whom "our gradients are structurally better" is a real
  technical argument, not a feature bullet. Fill: yes, technically. Patentable: the soft-rasterizer
  correctness claim (BRIEF 2.2b), if it survives the gradient-fidelity test (BRIEF 2.3). 2yr/2people:
  the integration yes, the relationship no. Market: 6G research today, huge later. Differentiability:
  **essential** (Sionna's entire reason to exist). Reachability for a two-person EU firm with no NVIDIA
  relationship: low, and NVIDIA open-sources rather than acquires small tools, so more likely they
  reimplement the idea than buy it. Publish the Fock-gradient result loudly to make ignoring it costly.

### Path C. Training-data + physics-prior feedstock for a Physics-AI surrogate co. Grade: B.
- Problem: real (PhysicsX/Neural Concept/Luminary are starved for physically-correct, cheap training
  data, especially at mmWave-on-body where FDTD is hours). Fill: yes, AEGIS is a data factory. Market:
  the hottest-funded category in the space ($2.4B, $100M, $187M rounds). Differentiability: partly
  essential (physics-prior gradients regularize a surrogate), partly not (they mostly want fast forward
  samples). Reachability: medium, these are approachable VC-backed firms, not $35B primes. Downside: it
  makes AEGIS a supplier to someone else's platform, capped value, and it competes with them the moment
  they generate their own data. A partnership, probably not an exit.

### Path D. Tuck-in into Keysight / Cadence / Synopsys-Ansys. Grade: C.
- Problem: they have EM portfolios (HFSS, EMPro/RFPro, Clarity) but body-dosimetry is not a gap they
  are shopping for. Fill: technically yes. Reachability: they buy verticals and revenue, not two-person
  pre-revenue tools, and AEGIS's TAM is beneath their deal threshold. This is the literal "spinoff into
  big EDA" dream and it is the weakest-graded path until AEGIS has category ownership and a customer
  book that makes it a Lumerical-shaped tuck-in. Not in reach at spinoff. Reachable only after Path A
  succeeds first.

### Path E. No company at all: research group + IOF + UGent licensing arm. Grade: B for risk-adjusted EV.
- The honest alternative the BRIEF asks me to consider. If the realistic exit is 3-15M and the dominant
  failure mode is Robin's own diagnosed "zombie at month 18" (honest_analysis Q7), then a UGent-hosted
  research-and-licensing vehicle captures much of the upside (IOF salary for a hire, licensing revenue
  to ZMT, standards citations, papers) with a fraction of the downside (no payroll trap, no
  can't-interview-at-a-customer problem). Differentiability: irrelevant to the vehicle choice. This is
  not defeatist; given the graded acquirer map, it may be the highest risk-adjusted EV, and Robin
  should price it honestly against the BV before he incorporates. `inferred, and I am flagging it as a
  genuine option, not a throwaway.`

### Scoring Robin's ambition, verbatim.

*"spinoff-to-acquire into the big EDA players like Dassault would be cool, or license to them."*

- **"Acquire into Dassault / big EDA via differentiability"**: **fantasy in that literal form.** The
  mega-deals ($35B, $10.6B, $5.9B, $1.24B) are silicon-to-systems, AI-industrial-software, and PLM-data
  theses into which a differentiable RF body-scattering engine does not fit, at a TAM beneath their deal
  floor. Dassault specifically is not even in the current acquisition wave. `verified thesis + inferred
  fit.`
- **"Or license to them"**: **the real version of the ambition, and it is reachable.** Licensing the
  gradient/sensitivity component into ZMT (certification), into Sionna (differentiable body layer), or
  as feedstock into a Physics-AI firm is a live path, and the Lumerical precedent shows the license/OEM
  relationship is exactly how a niche EM tool eventually gets acquired for nine figures *after* it owns
  its category. So the acquisition is the *second* act, and it is a $50-150M tuck-in at best (Lumerical
  shape), not a seat at the $35B table.

The one-sentence verdict: **Robin should stop aiming the acquisition story at Dassault/Synopsys and
aim it at ZMT, Sionna, and the Physics-AI surrogate cohort, sell the gradients and the mandated
sensitivity deliverable rather than the speed, and treat the big-EDA exit as a Lumerical-shaped
tuck-in that can only happen after he owns the mmWave-body pre-compliance category, not as the
opening move.**

---

## 7. Reality-constraint grading (two people, EU, no clearance, IOF 3 Aug)

| Path | Reachable for 2-person EU firm? | Note |
|---|---|---|
| A. ZMT license -> acquire | **Yes** | Robin's warm path; GOLIAT is the credibility; Wout has the contact |
| Certification/sensitivity service | **Yes** | Slow accreditation, but no clearance/US-chain needed; Wout's IEC world |
| C. Physics-AI feedstock | **Yes, medium** | Approachable VC-backed firms; risk of being commoditized |
| B. Sionna/NVIDIA | **Partly** | Technically reachable, relationship not; publish to force the issue |
| D. Big-EDA tuck-in | **No, not at spinoff** | Below deal threshold; reachable only post category-ownership |
| Radar/RCS, AV sensor sim (idea 12/18) | **Grade elsewhere** | Money is real but it is agent-06's physics; US-defense variants unreachable per SYNTHESIS |
| E. UGent research + licensing arm | **Yes** | Lowest downside; honest EV competitor to the BV |

Unreachable, stated plainly: any path requiring a US prime, a security clearance, or a >1M EUR capex
(own chamber, own fab). Any big-EDA *acquisition* before category ownership. Any Dassault-specific
plan (they are not buying).

---

## Sources

- Synopsys-Ansys $35B: [Synopsys completes acquisition 17 Jul 2025](https://news.synopsys.com/2025-07-17-Synopsys-Completes-Acquisition-of-Ansys), [RCR Wireless](https://www.rcrwireless.com/20250717/test-and-measurement/ansys-acquisition), [Synopsys silicon-to-systems announcement 16 Jan 2024](https://news.synopsys.com/2024-01-16-Synopsys-to-Acquire-Ansys,-Creating-a-Leader-in-Silicon-to-Systems-Design-Solutions), [Futurum on the thesis](https://futurumgroup.com/insights/synopsys-wraps-up-ansys-acquisition-targeting-integrated-design-solutions/)
- Siemens-Altair ~$10.6B: [Altair investor release](https://investor.altair.com/news-releases/news-release-details/altair-signs-definitive-agreement-siemens-be-acquired-106), [Siemens press](https://press.siemens.com/global/en/pressrelease/siemens-acquires-altair-create-most-complete-ai-powered-portfolio-industrial-software), [Bloomberg $10B](https://www.bloomberg.com/news/articles/2024-10-30/siemens-agrees-to-buy-software-group-altair-in-10-billion-deal)
- Renesas-Altium $5.9B: [Renesas completes acquisition](https://www.renesas.com/en/about/newsroom/renesas-completes-acquisition-altium), [TechPowerUp](https://www.techpowerup.com/325134/renesas-completes-acquisition-of-altium-for-usd-5-9bn)
- Cadence-BETA CAE $1.24B: [Cadence completes acquisition 30 May 2024](https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr/2024/cadence-completes-acquisition-of-beta-cae.html), [Cadence to acquire + $90M rev](https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr/2024/cadence-to-acquire-beta-cae-expanding-into-structural-analysis.html), [pulse2 $1.24B](https://pulse2.com/why-cadence-is-buying-beta-cae-for-about-1-24-billion/)
- Ansys-Lumerical ~$107.5M: [MarketScreener citing Ansys Q1 2020](https://www.marketscreener.com/quote/stock/ANSYS-40311135/news/ANSYS-Inc-completed-the-acquisition-of-Lumerical-Inc-for-approximately-120-million-33925617/), [Ansys press 5 Mar 2020](https://www.ansys.com/news-center/press-releases/03-05-20-ansys-photonic-simulation-leader-lumerical-sign-definitive-acquisition-agreement), [lumopt adjoint docs](https://developer.ansys.com/docs/lumerical/python-lumopt)
- PhysicsX: [$135M Series B](https://www.physicsx.ai/newsroom/physicsx-raises-135m-series-b-to-usher-in-a-new-era-of-ai-native-engineering-and-manufacturing), [Series B extension / NVentures ~$1B](https://pulse2.com/physicsx-series-b-extended/), [$300M Series C at $2.4B (Tracxn/coverage)](https://tracxn.com/d/companies/physicsx/__hok5fdWTydefwCO1e175XVPJRWdbtq9y2OjcJDzTacs)
- Neural Concept: [$27M Series B](https://pulse2.com/neural-concept-engineering-ai-platform-company-closes-27-million-in-funding/), [$100M Dec 2025](https://siliconangle.com/2025/12/18/ai-aided-design-software-startup-neural-concept-raises-100m-accelerate-product-engineering/)
- Luminary Cloud: [$72M Series B, $187M total](https://siliconangle.com/2025/09/15/luminary-cloud-raises-72m-advance-ai-driven-physical-product-design/), [Luminary on Physics AI](https://luminary.ai/resources/luminary-cloud-secures-72m-series-b-to-lead-the-physics-ai-era/)
- Flexcompute Tidy3D adjoint: [inverse design / TidyGrad](https://www.flexcompute.com/tidy3d/inverse-design/)
- NVIDIA Sionna differentiable RT: [NVIDIA developer](https://developer.nvidia.com/sionna), [Sionna docs](https://nvlabs.github.io/sionna/index.html)
- Remcom on-body Huygens: [globenewswire 10 Dec 2024](https://www.globenewswire.com/news-release/2024/12/10/2994253/0/en/Remcom-Announces-Huygens-Antennas-to-Integrate-On-body-Near-field-and-Far-field-Electromagnetic-Modeling-in-Dynamic-Scenarios.html), [everythingrf](https://www.everythingrf.com/news/details/19386-remcom-announces-integration-of-xfdtd-and-wireless-insite-for-on-body-near-field-and-far-field-em-modeling)
- Ansys Fluent adjoint (retrofit-moat test): [Ansys Fluent adjoint webinar](https://www.ansys.com/resource-center/webinar/ansys-fluent-adjoint-solver-based-optimization), [PADT on Fluent gradient-based optimizer](https://www.padtinc.com/2021/10/05/using-ansys-fluents-gradient-based-optimization/)
- Cadence Millennium (AI/CFD thesis): [Cadence Millennium platform](https://www.cadence.com/en_US/home/company/newsroom/press-releases/pr/2024/cadence-unveils-millennium-platformindustrys-first-accelerated.html), [NextPlatform](https://www.nextplatform.com/2024/02/01/cadence-sells-custom-gpu-supercomputers-to-run-new-cfd-code/)
- ZMT / Zurich43 structure: [zmt.swiss about](https://zmt.swiss/about/about-zmt/zmt), [Z43](https://www.z43.swiss/)
