# Adjacent high-power domains: is military really the best answer?

Agent report, 2026-07-09. Written against `AGENT_BRIEF.md` (read it first). Scope: find every
domain OTHER than defense where a coherent controllable multi-element transmitter deposits power
into a body or lossy dielectric under a hard quadratic exposure limit with a moneyed buyer, and
rank them against the military play. Does not redo the 17 topics in `feasibility_synthesis.md`.

## 1. Verdict

No non-defense domain beats military as a market, and the single most important thing here is not a
market at all: MRI parallel-transmit VOPs are a live, FDA-accepted, commercially-shipping instance of
Robin's exact exposure operator (the incumbent even calls it the "Q-Matrix"), which makes pTx prior
art and a regulatory precedent to borrow, not a market to enter.

## 2. The three things that most changed my view

1. **Sim4Life (ZMT) already ships a "Parallel Transmit Toolbox" that computes, compresses, and
   exports Q-Matrices and VOPs from pTx MRI coil simulations.** The exposure operator is not just
   published prior art (Eichfelder 2011), it is a named feature in a commercial product sold by
   Robin's own first customer, using the same word "Q-Matrix" the AEGIS brief uses for the crown
   jewel. This simultaneously kills pTx as a market for AEGIS and hands Robin the strongest possible
   regulatory-precedent slide plus a warm intro path.
   Source: https://sim4life.swiss/mri-modules

2. **The active mmWave airport-scanner "exposure" angle is dead by four to six orders of magnitude.**
   Measured scan power density is 0.00001 to 0.0006 mW/cm2 (0.0001 to 0.006 W/m2) against a 10 W/m2
   public limit. There is no thin compliance case and no regulatory pressure. Verified against the
   National Academies compliance study and the ICNIRP/IEEE limits. This kills candidate D cleanly.
   Sources: https://nap.nationalacademies.org/read/24936/chapter/5 ; arXiv 1503.05944

3. **The near-term power-beaming money is going to lasers, not RF phased arrays.** DARPA POWER
   (800 W over 8.6 km, 10 kW over ~1 km in 2025) and Aetherflux (kilowatt-class 2026 demo, $50M
   Series A plus DoD OECIF money) both beam with optical/IR lasers and enforce safety by
   beam-interrupt shutoff, not by exposure-constrained array design. The gigawatt microwave
   phased-array space-solar case that would fit AEGIS perfectly is real in the standards literature
   but is a 2035-2040 object with no buyer today. So the one domain with textbook-perfect physics fit
   has no reachable customer, and the domain with the customer uses physics AEGIS does not model.
   Sources: https://www.darpa.mil/research/programs/power ; https://newatlas.com/energy/laser-beamed-space-solar-power-aetherflux-2026-test/

## 3. What I verified, inferred, and could not check

**Verified (primary or near-primary):**
- VOP method and its a-priori overestimation bound (Eichfelder and Gebhardt, MRM 66:1468-1476, 2011,
  the PDF in this directory, read in full).
- VOP SAR supervision is built into clinical 7T pTx scanners (Siemens Magnetom Terra) and runs
  real-time on GPU. Fiedler 2025, MRM 10.1002/mrm.30643; multiple ISMRM proceedings.
- Sim4Life pTx toolbox exports Q-matrices and VOPs commercially (vendor page).
- Generic vs patient-specific SAR overestimation: ~34% average for one-size-fits-all models, safety
  factors up to 2.45 at 10.5T body imaging driven by 141% inter-subject variability. PMC9314883,
  Schmidt 2024 MRM 10.1002/mrm.29866.
- Differentiable / deep-learning pTx pulse design under SAR/VOP constraints is already done: IMPULSE
  (PMC6372346), DL B1+ prediction (Plumley 2022), US Patent 8,653,818, arXiv 2408.11323.
- mmWave scanner power density 4-6 orders below limit (National Academies).
- ITER ICRH is a 20 MW, 40-55 MHz phased strap array coupling into plasma modeled as a
  high-permittivity lossy dielectric (Messiaen PPCF 2011). Differentiable inertial-fusion inverse
  design exists (arXiv 2606.08827, 2206.01637) but I found no differentiable ICRH antenna design.
- Multi-antenna synchronized microwave ablation is clinical and growing, in-phase constructive
  interference, FDA-regulated (multiple PMC clinical series).
- Novocure TTFields revenue: $605.2M in 2024, +19% YoY (SEC 8-K). NovoTAL is FDA-cleared planning
  software.
- DARPA POWER and Aetherflux use lasers; safety is beam-interrupt shutoff (DARPA, NRL, pv-magazine).

**Inferred (reasoned, not directly sourced):**
- pTx is unreachable for AEGIS because 298 MHz (7T) is deep volumetric, the body sits inside the coil
  in the reactive near field, there is no propagation environment to ray-trace, and the surface law
  is invalid. The differentiable planner would transfer in principle, but the whole value there is
  patient-specific field prediction, which needs the volumetric FDTD that AEGIS explicitly is not.
- Fusion ICRH design is a coupling-maximization problem (get power into the plasma), not an
  exposure-limit problem, so it fails the generative rule on the constraint even before the tiny
  closed buyer and the dead 55 MHz surface physics.
- Microwave ablation is the hyperthermia case from the prior study wearing a different hat: same
  sub-6 volumetric physics, same thermal-dose-with-sparing objective, same eigenproblem structure,
  same ZMT-adjacent path.

**Could not check:**
- Exact split of the pTx SAR-supervision revenue between scanner OEM bundling and third-party tooling
  (it appears bundled with coil plus scanner; Sim4Life sells the generation side to OEMs and
  researchers).
- Reddit practitioner sentiment: r/mri is dominated by technologists, not pTx physicists, and pTx SAR
  is a research-tier topic, so I judged the Reddit channel low-yield here and did not spend budget on
  it. Flagging rather than pretending I covered it.

## 4. Domain-by-domain

### A. MRI parallel transmit (pTx). Grade: KILL as market, PURSUE as precedent to borrow.

**Physics fit.** The exposure operator survives perfectly as mathematics and is in fact identical:
Eichfelder's `S_v` spatial matrices are Robin's per-triangle `G^H G`, the VOP set `{A_j}` is a
compressed cover such that `max_j U^H A_j U` upper-bounds local SAR for any pulse `U`, and their
eigen-decomposition to build a dominating matrix (their Eq. 6, spectral norm gives the diagonal
`|lambda_min|` solution) is the same spectral machinery AEGIS already ships in `eigendecompose_Q`.
But the surface **speed** trick is dead: 298 MHz means centimetre skin depth, volumetric absorption,
body inside the coil in the near field, no ray-traced environment. The thing that makes AEGIS fast
does not apply, and the thing that makes pTx valuable (patient-specific volumetric E-fields) is
exactly the volumetric FDTD AEGIS is not.

**Buyer and money.** SAR supervision is bundled: the coil plus scanner ships with a
fully-characterized RF safety assessment and the VOPs baked into the online supervisor. Siemens Terra
runs it in real time on GPU. The generation side is sold by Sim4Life (ZMT) via its Parallel Transmit
Toolbox and by in-house OEM teams. There is no separately-addressable "sell a better VOP engine"
line for an outside spin-off.

**Incumbent.** Sim4Life / ZMT on generation, the scanner OEMs (Siemens, Philips, GE) on the online
supervisor. Robin already knows ZMT.

**Prior art.** Dense and directly on point. Eichfelder 2011 is the quadratic-form exposure
certificate with an a-priori overestimation bound. Differentiable and deep-learning pTx pulse design
under VOP constraints is a solved, published, patented (US 8,653,818) research area. The unmet need
that does exist (generic-model overestimation ~34%, safety factors up to 2.45, patient-specific SAR
from a single T1 scan) is being chased by the MRI groups themselves and needs volumetric field
prediction AEGIS cannot provide.

**Why it still matters more than any market here.** This is the certification instrument the military
study needs, already blessed by the FDA in clinical use. The transferable lessons, extracted below,
are the highest-value output of this whole report.

#### What to borrow from 15 years of pTx SAR practice

1. **Compressed, provably one-sided certificate.** VOPs replace ~300,000 per-voxel SAR matrices with
   a few hundred `A_j` that never underestimate local SAR for any excitation. The military "keep-out
   envelope" (Finding A) is the same move: replace the per-triangle worst-case field bound with a
   small dominating set that a safety board can audit. The precedent is not analogy, it is the same
   theorem.

2. **The a-priori overestimation bound is the whole trick.** Eichfelder's Eq. 7 gives
   `SAR(A) - SAR(B*) <= ||Z*|| * integral |U|^2 dt`, i.e. the certificate's looseness is a knob set
   before you see any pulse, tunable as a percentage of worst-case. This directly answers the brief's
   open sub-question on Finding A ("is lambda_max too loose?"): the pTx field solved exactly this by
   making the overestimation a controlled design parameter rather than an accident of the bound. Robin
   should present the envelope with an explicit, tunable overestimation factor, not as a raw
   `lambda_max`.

3. **Non-dominated observation points = the eigenstructure argument.** Their clustering keeps only
   matrices not dominated by any other in the PSD order. That is a principled way to say which skin
   patches or which array modes actually bind the certificate, which is exactly the low-rank story in
   the brief (top mode ~60% of trace). Reuse the language.

4. **Regulator acceptance is the load-bearing precedent.** The single strongest objection to the
   military thesis ("safety boards will never accept a software-computed envelope") is answered by
   "the FDA already does, for every 7T pTx exam, via this exact quadratic-form certificate." Put it on
   slide one, as the brief's Finding B already argues. My contribution is to confirm it is not merely
   published but commercially shipping (Sim4Life Q-Matrix export) and running online on fielded
   clinical scanners.

**One honest threat this sharpens.** Because Sim4Life sells a "Q-Matrix / VOP" toolbox by that name,
the AEGIS patent's "closed-form exposure operator" claim language is more exposed than the brief
already feared. Novelty must sit in the fast surface construction of Q in an arbitrary ray-traced
propagation environment at mmWave, not in the quadratic form, the eigendecomposition, or the
compressed certificate, all of which are 2011-and-earlier art in MRI.

### B. Fusion and plasma RF heating (ICRH/ECRH). Grade: KILL.

**Physics fit.** Half-right, which is worse than clearly wrong. ITER ICRH is genuinely a phased strap
array (24 straps, 8 triplets, 40-55 MHz, 20 MW CW) coupling into a medium that the field literally
models as a high-permittivity lossy dielectric with a surface. So the "coherent array into lossy
dielectric" half fits. But two things break it. First, 55 MHz is deep volumetric, inside a vacuum
vessel, in the reactive near field: the surface speed is dead and there is no propagation environment.
Second and fatal, the design objective is **coupling maximization** (get megawatts into the plasma
against load-tolerance and voltage limits), not an exposure cap. There is no hard quadratic
exposure/safety limit driving the antenna design. Fusion personnel safety is dominated by neutrons,
tritium, and magnetic fields; stray RF is managed by shielding and access interlocks, and my safety
search returned nothing framing it as an antenna-design constraint.

**Buyer, money, incumbent.** A closed handful of public labs (ITER, JET, W7-X, DTT, EAST, WEST) plus
a few private companies (Commonwealth, Tokamak Energy, Proxima). Antenna design is done in-house with
FEKO/CST/HFSS-class tools and bespoke coupling codes (TOPICA, RAPLICASOL). No open software-license
market. No differentiable ICRH antenna design found, but the buyer is too small and too closed and
the constraint is wrong, so the gap is not worth filling.

**Prior art.** Messiaen PPCF 2011 (plasma as lossy dielectric), decades of ICRH coupling codes.
Differentiable fusion exists but for implosion/kinetic inverse design, not antenna exposure.

### C. Particle accelerator and high-power RF infrastructure. Grade: KILL. (killed as instructed)

Klystron galleries and RF cavities do leak non-ionizing RF, but personnel protection is handled by
Personnel Safety Interlock Subsystems, access control, and shielding, not by any array-design or
exposure-optimization software. Cavity/klystron design uses SUPERFISH, HFSS, CST, AJDISK, DEMIRCI.
There is no coherent-array-into-a-body problem and no exposure-constrained beamforming. Boring as
predicted, killed quickly.

### D. mmWave security screening (the exposure angle). Grade: KILL.

The brief asked me to check the exposure angle rather than the imaging angle. The exposure angle is
dead: active mmWave scanners run at 4 to 6 orders of magnitude below the ICNIRP/IEEE public limit
(0.0001-0.006 W/m2 vs 10 W/m2). The National Academies compliance study exists precisely because the
margin is so large that the debate is about privacy and ionizing-vs-nonionizing confusion, not about
a binding power constraint. No regulatory pressure, no quadratic constraint that binds, no buyer for
an exposure tool. (The imaging angle stays where the prior study left it: CONDITIONAL, R&S QPS
incumbent.)

### E. Microwave and RF ablation, multi-antenna. Grade: CONDITIONAL, but as a hyperthermia sibling, not new ground.

**Physics fit.** Multi-antenna synchronized microwave ablation is real, clinical, growing, and
explicitly uses in-phase constructive interference across simultaneously-driven antennas to build a
larger, rounder, hotter zone (three synchronized antennas make a zone ~3x a single antenna's). That
is a controllable coherent array depositing power into tissue. But it runs at 915 MHz / 2.45 GHz:
volumetric, surface speed dead. And the "hard limit" is inverted relative to dosimetry: you WANT to
cook the tumor, and the binding constraint is sparing adjacent critical structure (bowel, vessel,
diaphragm), which is precisely the hyperthermia HTQ ratio-of-quadratic-forms eigenproblem the prior
study already graded CONDITIONAL. So this is deep-hyperthermia's interventional cousin, not a new
domain. The ECBF/QCQP transfers, the surface speed does not.

**Buyer and money.** Real and growing: Ethicon/J&J (NeuWave), Medtronic (Emprint), Varian/Siemens
Healthineers, plus Chinese OEMs. But ablation planning today is largely single-antenna nomograms and
manufacturer charts; multi-antenna synchronized phasing is done by hardware, not by an
exposure/sparing optimizer. A per-region sparing solver is a plausible research-planning aid, same as
HIFU and hyperthermia, and it extends the same ZMT/Sim4Life regulatory relationship.

**Incumbent and prior art.** Sim4Life already does thermal-dose tissue modeling; academic ablation
modeling is mature (COMSOL, Sim4Life). Differentiable multi-antenna phased ablation optimization
under a sparing constraint is thin, so there is a genuine research gap, but it lands squarely inside
the CONDITIONAL hyperthermia bucket rather than beside it.

### F. High-power wireless power: space solar and ground beaming. Grade: KILL for the reachable near-term buyer, CONDITIONAL-2040 for the perfect-fit version.

This is the domain the brief flagged as possibly the single best fit, so I pushed hardest here, and
the honest answer is a split that lands short.

**The perfect-fit version (microwave SPS) has no buyer.** Gigawatt-class solar-power satellites with
enormous-M phased arrays beaming 2.45 GHz to a 5-10 km2 rectenna, with the entire public-acceptance
case resting on keeping periphery power density under 10 W/m2, is a textbook instance of the
generative rule: huge coherent array, hard quadratic exposure limit, safety case currently
hand-waved. But it is a 2035-2040 object. The 2026 reality is Caltech MAPLE (milliwatts), JAXA
OHISAMA, ESA SOLARIS (paper studies), China Bishan (ground demo). No one is buying exposure-envelope
software for a system that does not exist. This is WPT's CONDITIONAL "tech solid, market thin"
verdict pushed out two decades.

**The version with a buyer today uses the wrong physics.** DARPA POWER and Aetherflux, the two places
with real 2025-2026 money (DoD OECIF, $50M Series A, record 800 W over 8.6 km and 10 kW over 1 km),
beam with optical/IR lasers, not RF phased arrays, and enforce safety by mechanical beam-interrupt
shutoff, not by exposure-constrained array design. A single laser aperture with a trip-wire is not
AEGIS physics. So the money is real but AEGIS has nothing to sell it.

**Net:** right physics, no buyer; buyer, wrong physics. This does not beat military.

### G. Others I evaluated and killed

- **Novocure TTFields (tumor-treating fields).** Tempting because it is real money ($605M revenue in
  2024, +19%, FDA-cleared NovoTAL planning software) and it is literally a multi-electrode array
  depositing energy into the body with a dose that is a quadratic form in the drive. But it runs at
  200 kHz, quasi-static capacitive coupling, no wave propagation, electrodes not antennas. AEGIS's
  physical-optics ray-traced engine models none of it. Striking mathematical analog and a nice
  "quadratic dose form is a fundable, regulated object" precedent, but a KILL as a market for AEGIS's
  actual engine.
- **Broadcast/telecom tower-climber RF safety, EV wireless charging, induction heating.** All either
  sub-6 quasi-static (dead surface physics) or a static keep-out/personal-meter problem with no
  coherent-array design loop. Killed without deep dives.

## 5. Ranking against the military play

Ordered by whether they beat military as a place to put the spin-off's next two years.

1. **Military RF safety.** Still the best high-power **market**: reachable EU buyers (RMA, Thales,
   Damen), non-dilutive EDF/DIRS money, the certifiable-envelope product (Finding A), and a genuine
   standards gap (Finding C(a)). Held back exactly as the brief says (ordnance not personnel money,
   static-zone-preferring boards, classified geometry, the AEGIS name clash). Nothing below overtakes
   it.
2. **pTx MRI as a borrowed precedent, not a market.** The highest-value single item in this report,
   but it is an input to the military play (the FDA-blessed VOP certificate), not a competing market.
   Treat it as slide one of the military pitch and as a patent-defensiveness warning.
3. **Microwave ablation.** The best genuinely-commercial new market I found, but it is a
   hyperthermia sibling (CONDITIONAL, sub-6, thermal-dose-with-sparing, ZMT-adjacent), so it belongs
   in the medical-planning basket with HIFU and hyperthermia, not ahead of military.
4. **Space solar / power beaming.** Right physics, no buyer for 15 years, and the near-term money
   moved to lasers. A watch-item, not a bet.
5. **Fusion ICRH, accelerators, mmWave-scanner exposure, TTFields.** Killed.

The most valuable possible outcome (military is not the best high-power market) did not materialize:
no non-defense high-power market beats military on a fair comparison. The second outcome did: military
wins, but its winning slide is borrowed from MRI.

## 6. What would kill this (falsifiable one-week tests)

- **Kills the pTx-as-precedent gift:** find one written safety-board or NOSSA/Navy-LSRB rejection of a
  VOP-style software certificate, or evidence the FDA treats pTx VOPs as device-firmware (not a
  transferable methodology precedent). If the precedent does not travel from FDA to a defense safety
  board, Finding B's first slide collapses. Test: one week of standards and NAVSEA/AFNIRSB document
  search plus one email to Wout, who sits on the RF-EMF bodies.
- **Kills microwave ablation:** confirm that NeuWave/Emprint multi-antenna phasing is fixed hardware
  with no software-addressable phase/amplitude control. If the array is not electronically
  controllable, there is no excitation to optimize and the ECBF has nothing to solve. Test: read the
  two device 510(k) summaries and one vendor engineering contact.
- **Kills the "no non-defense market beats military" conclusion:** find a funded, near-term (pre-2030)
  microwave (not laser) power-beaming program with an exposure-envelope procurement line. If DARPA
  POWER Phase 2 or an SSP program funds RF-phased-array exposure certification before 2030, candidate
  F jumps to CONDITIONAL-now and the ranking changes. Test: read the POWER Phase 2 BAA and the ESA
  SOLARIS phase-2 scope.

## 7. Single highest-value next action, and who

Robin (or Wout) should ask ZMT directly how they position the Sim4Life Parallel Transmit Toolbox
(the Q-Matrix / VOP export) relative to a general exposure-operator claim, in the same conversation
that already exists for the dosimetry relationship. This does three things at once: confirms the
prior-art exposure for the patent (defensive), secures the FDA-VOP-precedent story for the military
pitch (offensive), and does it through a warm existing channel rather than a cold defense
introduction. It costs one email and it de-risks both the IP claim and the military pitch's opening
slide. Wout is the right sender because he carries the standards-body credibility and the ISMRM-world
familiarity that make the ask land as peer-to-peer rather than as a competitor probing.
