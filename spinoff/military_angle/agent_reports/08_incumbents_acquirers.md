# Incumbents and acquirers: does the military angle make AEGIS more or less acquirable

Agent report, 2026-07-09. Reads `AGENT_BRIEF.md`, `../before-tom-meeting/00_context_brief.md`,
and `feasibility_synthesis.md` as ground truth, then attacks the acquisition question directly.

## 1. Verdict

The military angle makes AEGIS **less** acquirable by the "big EDA" buyers Robin actually named
(Dassault, Synopsys/Ansys, Siemens/Altair, Keysight, Cadence), because it wraps clean dual-use IP in
ITAR/export-control and CFIUS diligence that those buyers pay a discount to avoid, and only marginally
more attractive to European defense primes who do not run the kind of exit Robin wants, so the
acquirable asset is the differentiable exposure-operator IP sold as a clean dual-use EDA module, not a
defense-contracted company.

## 2. The three things that most changed my view

1. **The entire independent EM-solver industry has already been bought, and every deal was a solver
   with real revenue and customers, never a pre-revenue academic spinoff.** CST went to Dassault for
   about EUR 220M on about EUR 47M of 2015 revenue (roughly 4.7x revenue). FEKO's owner EMSS went to
   Altair in 2014, and Altair itself went to Siemens for about USD 10.6B in a deal that closed 26 March
   2025. HFSS (via Ansoft) went to Ansys, and Ansys went to Synopsys for about USD 35B, closing 17 July
   2025. There is no precedent in this space for buying a zero-customer engine. AEGIS today is a
   technology-and-team acquisition, and those price in the single-digit millions if they happen at all.
   [Dassault-CST](https://schnitgercorp.com/2016/07/21/quickie-ds-acquire-cst-e220-million/),
   [Siemens-Altair](https://press.siemens.com/global/en/pressrelease/siemens-acquires-altair-create-most-complete-ai-powered-portfolio-industrial-software),
   [Synopsys-Ansys](https://www.rcrwireless.com/20250717/test-and-measurement/ansys-acquisition).

2. **The Duke phantom is not a CST exclusive, and that quietly kills the "nobody brought a body" moat
   as stated.** IT'IS Foundation itself says the Virtual Population V2.0 CAD models (Ella, Duke, Billie,
   Thelonious) are "optimized for finite-element modeling in third-party commercial platforms such as
   ANSYS and CST." So Ansys HFSS imports the same phantoms CST does. The body is already on the shelf at
   both incumbents, licensed from IT'IS. What AEGIS uniquely brings is not the body, it is the
   millisecond differentiable all-beams envelope, which is a much narrower claim than the brief's
   "nobody brought a body."
   [IT'IS ViP overview](https://itis.swiss/virtual-population/virtual-population/overview).

3. **Ansys Perceive EM is the same physical-optics family as AEGIS, already real-time on one GPU, and
   could bolt on a phantom mesh in a quarter, so raw speed is not a durable moat.** Perceive EM is
   PO-based shooting-and-bouncing-rays, GPU-parallel, marketed at "up to 1,000,000x faster" than CPU
   solvers over large scenes with motion. SBR already handles arbitrary meshes, so adding a body mesh
   is trivial for them. The only thing AEGIS has that Perceive EM structurally does not is
   differentiability and the closed-form Q calculus, which the repo's own Ansys note confirms Perceive
   EM lacks. This is the single most important finding for the acquisition question: the acquirable
   differentiator is the differentiable operator, not the speed.
   [Perceive EM](https://www.ansys.com/products/electronics/ansys-perceive-em).

## 3. What I verified, inferred, could not check

**Verified (primary or strong secondary):**
- Dassault to acquire CST announced 20-21 July 2016, about EUR 220M, completed 3 Oct 2016, CST 2015
  revenue about EUR 47M, cash.
- Altair acquired EMSS (FEKO) in June 2014.
- Siemens to acquire Altair announced 30 Oct 2024 at USD 113.00/share, about USD 10.6B equity, closed
  26 March 2025. FEKO now sits in Siemens Simcenter.
- Synopsys acquired Ansys, about USD 35B, closed 17 July 2025, TAM stated about USD 31B.
- As a regulatory condition of that deal, Synopsys divested its Optical Solutions Group and Ansys's
  PowerArtist to **Keysight**, final approval 10 Oct 2025. A forced divestiture literally created a
  buyer in this space in the last quarter.
- Ansys acquired Optis (optical, autonomous-vehicle simulation) announced 22 March 2018, completed 2
  May 2018, price undisclosed.
- Keysight acquired ESI Group at EUR 155.00/share, valuing ESI at about EUR 913M fully diluted,
  controlling block closed 3 Nov 2023, aerospace and defense virtual prototyping.
- Cadence acquired Integrand (EMX method-of-moments solver) 13 Feb 2020, terms undisclosed.
- IT'IS Virtual Population phantoms are provided as CAD optimized for Ansys and CST. IT'IS (non-profit,
  phantoms + tissue database) and ZMT Zurich MedTech (commercial, Sim4Life solver) are sister
  organizations. This is why both suites ship Duke.
- FEKO lineage: 1991 research (Jakobus, Stuttgart), EMSS founded 1994, FEKO commercialized 1997. CST
  and Ansoft/HFSS are likewise university-origin solvers that built businesses before being bought.

**Inferred (reasoned, not directly sourced):**
- CST full-wave FDTD/FEM SAR on a body is minutes to hours per single beam per single frequency, versus
  AEGIS milliseconds, and neither incumbent runs a full-wave whole-ship-plus-body solve because it is
  electrically intractable. The real incumbent workflow is PO for the ship with no body.
- A US EDA acquirer would treat EU defense contracts as diligence hair (export control, EDF
  results-ownership rules, security classification) and discount for it.
- Building differentiable PO into Perceive EM (adjoint or autodiff over SBR) is a known technique, so
  the "hole Ansys would rather build than buy" risk is live.

**Could not check in the time available:**
- Ansys-Ansoft 2008 price (widely reported around USD 832M, marked unverified here).
- Cadence-AWR price (AWR moved NI to Cadence in 2020, figure not confirmed).
- Whether any EDF/national defense contract AEGIS might sign would actually trigger a specific
  export-control classification. That is a lawyer question, not a web-search question.

## 4. Body

### 4.1 The incumbent map, precisely

The market has consolidated hard. Since 2014 essentially every independent high-frequency EM solver
has been absorbed into one of five giants:

| Solver / origin | Bought by | When | Price | Now inside |
|---|---|---|---|---|
| CST (TU Darmstadt lineage, Weiland) | Dassault Systemes | 2016 | EUR 220M (~4.7x rev) | SIMULIA / 3DEXPERIENCE |
| FEKO / EMSS (Stuttgart+Stellenbosch) | Altair 2014, then Siemens | 2014 / 2025 | Altair whole = USD 10.6B | Siemens Simcenter |
| HFSS / Ansoft (CMU, Cendes) | Ansys, then Synopsys | 2008 / 2025 | Ansys whole = USD 35B | Synopsys |
| Optis (optical) | Ansys, then partly Keysight | 2018 / 2025 | undisclosed / divested | Synopsys + Keysight |
| ESI Group (EM + virtual prototyping) | Keysight | 2023 | EUR 913M | Keysight |
| Integrand EMX (MoM) | Cadence | 2020 | undisclosed | Cadence AWR / Clarity |

**What each sells into military E3 / RADHAZ today:**

- **Siemens / Altair FEKO** is the classic shipboard topside and RADHAZ workhorse. PO and MLFMM for
  electrically enormous platforms, installed-antenna placement, co-site coupling, and hazard-zone
  fields. This is the tool most directly in AEGIS's lane, and it is now inside Siemens.
- **Ansys (Synopsys) HFSS + SBR+ + Savant + EMIT** covers full-wave antennas, SBR installed-antenna
  patterns on platforms (Savant), and RF co-site/interference (EMIT). Perceive EM is the new real-time
  PO/SBR channel-and-radar layer. Broadest defense EM stack of anyone.
- **Dassault CST** does full-wave FDTD/FEM including the IT'IS phantoms and a bioheat solver, so it is
  the one that most literally "can do body dosimetry" today.
- **Remcom** sells Wireless InSite (ray-tracing propagation, outputs radiation-hazard quantities) and
  XFdtd. Strong in RF propagation and co-site, present in defense.
- **Keysight / Cadence / Synopsys** on the pure-EDA side are chip-package-board EM (EMX, Clarity, ADS,
  EMPro). Keysight is the defense outlier here: it holds a US Air Force electromagnetic-spectrum
  threat-simulator contract and bought ESI's aerospace/defense virtual prototyping, so it has real
  defense revenue and appetite.

**Which of them ships human dosimetry, and how good.** CST and HFSS both import the IT'IS Virtual
Population phantoms (Duke included) and compute SAR by full-wave solve plus a bioheat post-step. That
is physically rigorous and FDA-recognized for MRI coil SAR. It is also volumetric, slow, and one beam
per solve. Sim4Life (ZMT, the IT'IS sister company) is the dedicated dosimetry incumbent and the
approximately USD 2.3M ARR monopoly the intake already flagged.

**So what exactly can CST not do that AEGIS can?** Pressure-testing the brief's honest answer ("CST can
do body dosimetry, it is just not fast, not differentiable, not the operational workflow"):

- The "not the operational workflow" part is the strongest true claim. Topside RADHAZ is run as PO
  unperturbed fields with no body. That is a workflow gap, not a solver gap, and CST/HFSS/FEKO could
  all close it by dropping in the phantom they already license. Nobody bothers because HERP is a small
  budget line. **The differentiator here is workflow and incentive, not capability.**
- The "not fast" part is real but narrow. On a shipboard problem nobody runs full-wave ship-plus-body
  regardless, because it is electrically intractable at X-band. The realistic comparison is a local
  body sub-problem in a known incident field: CST full-wave is minutes to hours per beam per frequency,
  AEGIS is milliseconds and gives worst-case over all beams in one eigendecomposition of Q. Speed only
  decisively matters when you need the all-beams sweep or a design loop, which is exactly the
  differentiable-Q use case, not generic SAR.
- The "not differentiable" part is the only durable moat, and it is the same conclusion
  `feasibility_synthesis.md` already reached.

**Would Perceive EM adding a phantom evaporate the speed advantage overnight, and how hard is it?**
Yes to the first, and not very hard to the second. Perceive EM is PO-based SBR, the same family as
AEGIS's first-bounce assumption, already GPU-real-time over million-facet scenes with motion. SBR
consumes arbitrary triangle meshes, so a body mesh is just another target. Adding calibrated dosimetric
absorption (a tissue Fresnel/transmission law on the facets) is a few weeks of a competent team's time,
because IT'IS already sells the dielectric data and the phantoms. What Perceive EM cannot do without an
architectural change is differentiability and the closed-form Q eigenstructure, which the repo's own
Ansys license note confirms it lacks. **Conclusion: AEGIS's raw-speed pitch is defeatable by an
incumbent in a quarter. The differentiable-operator pitch is not. Everything downstream should lead
with the latter.**

### 4.2 The acquisition logic

What these companies buy, ranked by what they actually pay premiums for:

- **(c) A standards or platform position** and **(b) an installed customer base with ARR** are what
  earn revenue multiples. Dassault paid ~4.7x revenue for CST's book of aerospace/defense/electronics
  EM customers and its position as the full-wave standard. Keysight paid EUR 913M for ESI's aerospace
  and defense customer relationships and virtual-prototyping standard-of-record status.
- **(a) Technology** and **(d) team** are what get paid for when there is no ARR yet, and those are
  acqui-hire-scale deals, low single-digit to low-tens of millions, usually only when the acquirer has
  a named product hole and a bidding tension.

Brutal scorecard for AEGIS against those four:

| What buyers pay for | Does AEGIS have it? |
|---|---|
| (a) Technology plugging a named hole | Yes, the differentiable Q calculus, which Perceive EM lacks |
| (b) Customers / ARR | No. Zero customers, one polite Hirata email |
| (c) Standards / platform position | Only indirectly, through Wout's committee seats, not owned by the company |
| (d) Team | Small. Robin plus Carolina plus a promotor |

That is a technology-plus-team profile with no revenue and no owned standards position. Priced as such,
it is a single-digit-million outcome at best, and only if a specific buyer decides building
differentiable PO is harder than buying it. **2,469 tests and a beautiful monograph do not change the
category. Buyers in this space have never paid a real number for a zero-customer engine.** The
comparators all built businesses first: CST ran 1998 to 2016, EMSS 1994 to 2014, Ansoft 1984 to 2008.
None sold pre-revenue.

### 4.3 Does defense help or hurt acquirability

Two theses, and the evidence points clearly to one.

**Thesis (i), defense makes you more acquirable** (sticky contracts, accreditation moat, every EDA
player wants defense revenue): partly true at the level of the giants. Keysight visibly wants defense
and grew it through ESI and organic contract wins. But those are large US or US-friendly entities
buying either commercial dual-use IP or already-accredited businesses.

**Thesis (ii), defense makes you less acquirable for a small EU spinoff**: this is the one the evidence
supports. Reasons, with the real comparanda:

- **The natural buyers want clean global dual-use IP.** The one time a US EDA vendor bought a small
  foreign EM SME, it was Altair buying EMSS/FEKO, and FEKO was explicitly commercial dual-use EM with
  defense merely as a customer vertical. Altair did not buy a defense-contracted company, it bought a
  solver it could sell worldwide. That is the template, and it argues for keeping AEGIS's core clean.
- **Export control and CFIUS add diligence cost.** A US acquirer inheriting EU defense contracts takes
  on export-control classification, EDF results-ownership and control-change rules, and potential
  national security review. CFIUS has blocked only about 11 deals ever, so an outright block is
  unlikely, but the diligence burden and the risk of forced carve-outs are a real discount, and 2025
  saw fresh forced divestitures and China-deal blocks that keep this front-of-mind for boards.
- **The revenue is lumpy, services-heavy, and small.** See 4.6.
- **An EU defense-adjacent software SME typically gets bought by a European prime or stays small.** The
  realistic non-EDA acquirers are Thales, Leonardo, Saab, Hensoldt, Naval Group, and those buy
  accredited defense capability, not pre-revenue spinoffs, and they are not the "big EDA" exit Robin
  wants.

Net: defense revenue would move AEGIS away from the buyer set Robin named, not toward it. It is useful
as non-dilutive R&D funding (EDF, national lines) and as a source of reference problems, but it should
not become the company's identity if an EDA exit is the goal.

### 4.4 License instead of sell

The blunt fact: in this market, incumbents **acquire** solvers, they do not **license** them in. CST,
FEKO, Optis, ESI, Integrand were all bought outright, because a solver is core IP and no suite wants a
roadmap dependency on an outside engine. Ansys/Dassault/Altair partner programs exist (ACT extensions,
3DEXPERIENCE marketplace, Python scripting), but those license **apps and workflows on top of** the
solver, not the solver itself, and they carry modest revenue-share terms, not acquisition economics.
There is essentially no precedent for a university spinoff licensing a native solver into HFSS or CST.

The Perceive-EM-is-not-differentiable note cuts both ways, as the brief says. It means AEGIS is
genuinely complementary. It also means Ansys has a named hole it can fill by building, and building
differentiable PO (adjoint/autodiff over their existing SBR) is a known technique they would likely
prefer over taking a dependency on an EU academic's JAX code. So "license my differentiable layer into
Perceive EM" is a plausible conversation to open, but the base rate says it converts to either an
acquisition or a build-it-ourselves, not a durable license.

### 4.5 Complement vs compete: the body module

Is "the body module for someone else's solver" a better business than a standalone tool? For topside
RADHAZ the pitch is seductive: be the phantom-and-dosimetry layer that plugs into FEKO/HFSS/CST. But
two facts hollow it out:

- **The phantom is already commoditized.** IT'IS licenses the Virtual Population (Duke included)
  directly to both Ansys and CST as ready CAD. The body you would "bring" is on their shelf.
- **The dosimetry solver incumbent already exists and is a sister of the phantom vendor.** ZMT's
  Sim4Life is the dedicated body-dosimetry engine, and ZMT and IT'IS are related organizations. So
  "the body dosimetry module" is a space ZMT/IT'IS is closer to owning than AEGIS, and it is the same
  ~$2.3M ARR niche the intake already judged too small to hang a company on.

Understanding the IT'IS/ZMT relationship is the key that explains all of this. IT'IS Foundation
(non-profit) makes the phantoms and tissue database. ZMT Zurich MedTech (commercial) makes and sells
Sim4Life, the solver that uses them. The incumbents ship Duke because they license the phantom from
IT'IS. So if you sell "the body," you are reselling an IT'IS input and competing with ZMT's solver, and
a large buyer could just license the phantom from IT'IS and add fast dosimetry itself.

The only defensible wedge in this section is not the phantom and not generic SAR. It is the closed-form
**exposure-envelope certificate** (Finding A), the worst-case-over-all-beams keep-out bound that nobody
ships and that IT'IS/ZMT do not compute. That is the thing worth licensing or selling, and it is again
the differentiable-operator asset, not the body.

### 4.6 The services trap

The E3/RADHAZ market is roughly USD 1.5 to 2B/yr, but only about USD 300 to 400M is software licensing.
The rest is physical test and engineering services (Amentum, CACI, NTS, and specialist shops like
RADHAZ Team LLC, which ran on the order of USD 1M of field-survey and compliance volume in 2024). A
spinoff that follows the money ends up a consultancy.

Is that fatal to the venture thesis? It depends which thesis:

- **For an EDA-scale acquisition exit, yes, it is fatal.** Services revenue carries low multiples,
  does not scale, and does not produce the ARR or standards position an EDA giant pays a premium for.
  The EM consultancies (WEMEC, Emag Associates, RADHAZ Team, and dozens like them) have stayed
  consultancies for decades. The rare escapees, EMSS to FEKO and Integrand, did it by productizing a
  solver early and selling licenses, which is the opposite of leaning into services.
- **For a grant-funded EU SME building runway, it is arguably the right bootstrap.** Non-dilutive
  IOF/VLAIO/EDF plus high-margin services can fund the software, the software is the wedge that wins
  the services, and defense services are one of the few ways to get near the classified geometry and
  reference customers you otherwise cannot reach. The tension to name out loud: services keeps you
  alive but small and unacquirable by the EDA set, and only a productized dual-use dosimetry-plus-design
  tool with real ARR ever gets the EDA multiple. You cannot optimize for both at once.

## 5. What would kill this, as a one-week test

Give a competent RF engineer one week and Ansys Perceive EM (or a GPU SBR stack) plus a licensed IT'IS
Duke phantom. Ask them to compute absorbed power density on the phantom surface in a representative
shipboard incident field, and to do it across a beam sweep. If they get within engineering tolerance of
AEGIS on a laptop-hours budget, then AEGIS's speed pitch is dead and only the differentiable Q and the
closed-form all-beams envelope survive as sellable IP. If, separately, an adjoint-over-SBR prototype
gives usable gradients of absorbed power with respect to precoder weights inside that same week, then
even the differentiability moat is on a clock and the acquisition window is "now, small" rather than
"later, larger." Either result reframes the entire exit story, so run this before pitching any acquirer.

## 6. The single highest-value next action, and who does it

**Stop pitching speed and defense, and get an independent read on whether the differentiable
closed-form exposure operator is genuinely un-buildable-in-a-quarter by Ansys, from someone who has
lived inside that world.** That person is Tom Dhaene (Keysight/Agilent roots, SUMO lab), and it is the
meeting already on the calendar. The specific ask to put to him is not "is my method fast" but "if you
were still at Keysight, would you build differentiable PO or buy it, and what would you pay." His answer
sets the ceiling on every acquisition and licensing path in this report. Robin has to run that meeting,
framed on the operator, not on the body and not on the navy.
