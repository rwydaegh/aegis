# Custorix / Valtorix dossier

Compiled 28 July 2026, after an inbound LinkedIn message from Pieter-Paul Smet and a lab invitation
to Wetteren. Everything below is either sourced from a public record or flagged as inference.

---

## 1. One-paragraph summary

Custorix is a three-month-old, two-person Belgian defence startup in Wetteren building a pulsed
high-power microwave (HPM) counter-drone effector. Its co-founders are Pieter-Paul Smet (CEO,
commercial) and Maxime Lebrun (CTO, builder). The technical core is not the pulse generator but a
3D-printed graded-index Luneburg lens, which the same two people also sell as passive radar
reflectors under a second brand, Valtorix. They won the drone track of Belgian Defence's Start2Def
programme in March 2026, were selected for the imec.istart Belgium summer 2026 cohort in July, and
travel to MSPO in Poland in September on a Flanders Investment & Trade delegation. Their commercial
velocity is far ahead of any publicly demonstrated technical substance. They found Robin via Google
Scholar and want electromagnetic modelling capability they do not have.

---

## 2. Corporate structure

### Custorix BV

| Field | Value |
|---|---|
| Enterprise number | BE 1036.734.218 |
| Incorporated | 10 April 2026 |
| Registered seat | Kapellendries 32, 9230 Wetteren |
| Legal form | Besloten Vennootschap |
| VAT activity | NACE 25.300, *vervaardiging van wapens en munitie* (manufacture of weapons and ammunition) |
| First book year | Extended, ends 31 December 2027 |
| Annual accounts | None filed yet |
| Contact | info@custorix.eu, +32 498 08 82 92 |

Six "functiehouders" in KBO, which collapses to two humans acting through their own companies:

- **Shaa VOF** (BE 1017.401.524, Destelbergen, incorporated 15 December 2024). Permanent
  representative Pieter-Paul Smet, co-managed with Dante Willems. Its own VAT codes are guest rooms,
  camping grounds, motorcycle parts retail and engineering consultancy. A personal vehicle, not an
  RF company.
- **Max Prototypes BV** (BE 1033.904.390, incorporated 3 February 2026). Sole director Maxime
  Lebrun. Registered at the *same* Kapellendries 32. VAT codes: plastics manufacturing and
  management consulting.

No institutional shareholder appears in the registry. No "links between entities" recorded.

### Valtorix / MP Systems

Valtorix is described on its own LinkedIn page as "the commercial brand of MP Systems". It sells
"advanced radar signature solutions": Luneburg lenses and radar reflectors for radar calibration,
testing, training, validation and RCS enhancement, to governmental organisations, defence OEMs and
industrial partners. It states it develops exclusively for Belgium, the EU and NATO allied
countries. Two LinkedIn followers, one associated member, 2-10 employees.

**Not resolvable in the registry from here.** "Valtorix" is a brand, not a company name. Max
Prototypes BV still carries that name in the KBO snapshot dated 27 July 2026, so "MP Systems" is
either a rename too recent to appear or a third entity that KBO's name search would reveal (that
endpoint is not reachable from this machine; data.be sits behind Cloudflare and staatsbladmonitor
has this IP blocked).

Pieter-Paul's personal profile describes Valtorix differently — "radar, RF testing and
next-generation wireless applications" serving "aerospace, defence and telecommunications" — and
claims it builds on "more than two years of collaborative technology development and market
validation prior to its official founding in 2026". Treat the company page as the business and the
personal profile as the ambition.

### Consequence that matters

The lens IP sits **outside Custorix**. Anything contributed to lens design accrues to MP Systems /
Valtorix, which is the other founder's side. Any collaboration must name the contracting entity, the
field of use, and who owns improvements. UGent TechTransfer will ask this first, because Robin's own
IDF is UGent-owned.

### Infrastructure

- custorix.eu: no A record, so no website. MX points to Microsoft 365. Nameservers
  ns1.european-server.eu / ns3 / ns4.european-server.com.
- valtorix.eu: identical fingerprint. No website, M365 mail, same nameservers.
- custorix.com: unrelated Namecheap parking page with registrar email forwarding.

Two brands, one operation, neither with a live site.

---

## 3. People

### Pieter-Paul Smet — Co-founder & CEO, Custorix; Co-founder (strategy/BD), Valtorix

- KU Leuven, Master Industrial Engineering Sciences, 2016-2018, cum laude. Erasmus exchange at
  University of Split (FESB), 2017-2018.
- World trip June 2022 - May 2024: converted a 1981 fire truck into a camper, 45,000 km through 23
  countries with his partner and two dogs.
- Rocco Mundo, self-employed e-commerce venture, June 2023 - February 2025.
- VDP Automation, sales & application consultant (freelance), August 2024 - April 2026. VDP is a
  motion-control integrator; he worked with Stöber Antriebstechnik, R+W Antriebselemente and
  Heidrive. His farewell post drew 97 reactions, indicating a real industrial network.
- Ghent metropolitan area. 827 followers. LinkedIn interests include Gary Vaynerchuk and Tim
  Ferriss.
- Self-description: "I bridge technology, strategy and partnerships." He explicitly assigns
  "advanced RF engineering" to the other founder and "strategic business development" to himself.

He is the commercial half and says so. He is not the person to ask physics questions.

### Maxime Lebrun — CTO, Custorix; founder, Max Prototypes

- Founder of Max Prototypes (maxprototypes.com), a B2B prototyping shop offering consulting, design,
  3D printing, machining, automation and electronics. Shopify site, no products, no prices, no
  machine list, no defence content.
- Self-taught trajectory by his own About page: RC planes, electric karts, CNC machines, turbojet
  engines, woodworking, resin casting. No degree, publications or certifications claimed anywhere.
- Holder of the Start2Def award plaque in the BEDEX photographs.

Formidable maker. No visible computational electromagnetics background. Anyone who builds a working
turbojet in a workshop should be taken seriously as a builder and should not be assumed to have
modelled anything.

### Unresolved

Pieter-Paul refers to Valtorix's "engineering co-founder". That is presumably Maxime, but it could
be a third person with actual RF credentials who has not surfaced publicly. Worth asking directly —
if such a person exists, the technical assessment below changes materially.

---

## 4. Timeline

| Date | Event |
|---|---|
| ~2023-2024 | Luneburg lens work begins ("more than two years" of development prior to founding) |
| Dec 2024 | Shaa VOF incorporated (Pieter-Paul's vehicle) |
| Aug 2024 | Pieter-Paul goes freelance at VDP Automation |
| Oct 2025 | Start2Def opens; 33 applications; 10 startups selected |
| 3 Feb 2026 | Max Prototypes BV incorporated |
| ~Mar 2026 | BEDEX Brussels: Max Prototypes wins the drone track, award from Defence Minister Theo Francken. ATOMNIA wins cyber. |
| 10 Apr 2026 | Custorix BV incorporated |
| ~Apr 2026 | Valtorix founded (per LinkedIn; no registry trace) |
| 16 Apr 2026 | "New chapter" launch post (timestamp decoded from the LinkedIn activity ID) |
| ~May 2026 | CAP4LAND launch at the Royal Military Academy, Brussels |
| ~Jun 2026 | Eurosatory, Paris |
| 11 Jul 2026 | FIT publishes the Poland defence mission page |
| 27 Jul 2026 | imec.istart Belgium summer 2026 cohort announced: 9 selected from 140 |
| 28 Jul 2026, 00:21 | Inbound LinkedIn message to Robin, same night as the cohort post |
| 7-9 Sep 2026 | FIT defence & security mission, Warsaw and Kielce (MSPO runs 8-11 Sep) |
| 29 Sep 2026 | EDF-2026-LS-DIS-NT call deadline |

Five months of relentless, well-sequenced ecosystem execution. In that entire public run there is not
one technical number: no band, no peak field, no pulse width, no rep rate, no range, no measured
effect, no TRL, no test partner, no patent.

---

## 5. Programmes, money and validation

### Start2Def

Run by the Royal Higher Institute for Defence with imec.istart and IGNITY, with Belgian Defence. Two
themes in the first edition: "Drone Swarms & Counter Drone Swarms" and "Cybersecurity for Critical
Infrastructure". 33 applications in October 2025, 10 selected, 2 winners. The prize is described
publicly as a package of service vouchers plus coaching; no cash amount or follow-on contract is
published. **Ask what they actually received.**

The challenge page is worth reading in full because it is Defence stating the requirement in its own
words. Relevant points:

- The programme's stated purpose is to "bridge research, SMEs and Defence" — research is a named leg,
  so a university partner is structurally expected rather than odd.
- Enabling technologies explicitly include "counter-swarm systems (kinetic effectors,
  **directed-energy/HPM testing**, drone-dogfighting)". Defence is asking for HPM *testing*, i.e.
  evidence, not just a prototype.
- "Simulation & training tools" is a listed enabling technology, so modelling is in scope for the
  challenge's own taxonomy.
- The word "dual-use" is Defence's own. That is the framing that keeps this survivable for an IOF
  file that will not fund military work.
- The illustrative scenario is a forward operating base under coordinated FPV attack with decoys and
  jamming — a military field problem, not an airport.

### imec.istart

Selected for the Belgium summer 2026 cohort, 9 of 140. The Belgium deal is €100,000 pre-seed as a
convertible loan with no upfront equity, plus coaching, imec R&D access, community and office space,
investor days, and follow-on potential. Portfolio-wide: 341 companies since 2011, 14 exits (3 IPOs,
11 acquisitions), 1 unicorn (Deliverect), over €1 billion cumulative follow-on funding.

Caveat on those numbers: the marquee outcomes are all software (Deliverect, DataCamp, UgenTec at a
€90M exit, FibriCheck). The portfolio's track record is a software track record. Hardware, and
especially certification-gated defence hardware, has a longer and thinner curve. €100k buys a
software team a year; it buys an HPM team some capacitors, an antenna and a little test range time.

### Flanders Investment & Trade

Registered for the FIT "Defense and security mission to Poland", 7-9 September 2026, Warsaw and
Kielce, sectors aeronautics / electronics / security, with Agoria as stakeholder and FIT Warsaw's
Kris Put as contact. Nineteen participants, and Custorix is the smallest by an order of magnitude:
VITO, Sirris, Agoria, Materialise, Septentrio, Luciad, Cegeka, Senhive, Sioen, Seyntex, Intersoft
Electronics, XO Advanced Systems, Smulders, GEO.XYZ, Fergus Engineering, A.C.B., BPrepared, Sol1.

(The public FIT page renders as an empty Angular shell; the participant data was read from the
underlying promotieplatform API.)

---

## 6. The technology

### What they say

The BEDEX roll-up banner states the architecture in six words:

> **DIRECTED ENERGY COUNTER-UAS — pulse generator with focussing lens**

The FIT profile expands it: compact directed-energy effector modules; portable high-power
electromagnetic pulse technology to neutralise hostile drones and drone swarms; custom effector
modules for integration into existing platforms; co-development with OEMs and system integrators;
dual-use for military, critical infrastructure, airport and public security; expertise in high-power
pulse electronics, RF systems and "advanced electromagnetic energy delivery"; licensing
opportunities and long-term support for integration partners.

Note the scoping: they are a **component supplier**, not a system integrator. No radar, no tracking,
no C2, no mount. That is the right call for two people, but the corollary is that everything they
kept — prime power, pulse generation, aperture — is the hard physics.

### What is visible in the photographs

- A clear acrylic enclosure roughly 1.2 m long containing hardware (metalwork and a red component
  are visible; reflections defeat the rest). A fire extinguisher sits under the table. They fire this
  thing.
- Two smooth matte-white spheres on stands, roughly 20 cm and 15 cm diameter.
- A row of about eight small spheres, some apparently sectioned — consistent with print trials at
  different infill densities.
- Poster art: a soldier in helmet and camo shouldering a chunky squared-off device, firing a wide
  cone into a formation of six to eight drones.

### The lens

Confirmed, not inferred: Valtorix sells "Luneburg lenses and radar reflectors". A Luneburg lens is a
spherically symmetric graded-index lens; the standard modern fabrication route is 3D printing with
varying lattice infill to grade the effective permittivity. The size series of test spheres is
exactly what developing that looks like.

**Why a Luneburg is a clever choice for counter-swarm.** Every point on the surface of an ideal
Luneburg sphere focuses to a plane wave in the opposite direction. So multiple feeds around one
sphere give multiple simultaneous beams in multiple directions, with no phase shifters, no gimbal
and no beam-steering electronics. For a two-person company that cannot build a phased array, that is
a genuinely elegant answer to "how do you engage several drones". It also explains "compact":
aperture gain without a reflector dish or a long horn.

### The structure of the business, now that the lens is known

One manufacturing competence, two businesses:

- **Valtorix / MP Systems** — passive radar reflectors, RCS augmentation, calibration and training
  targets. Established market, real customers, simple physics, sellable now, cash-generating.
- **Custorix** — the same printed sphere used as a focusing lens on a pulsed HPM emitter. Hard,
  speculative, large prize.

The boring product funds the moonshot and both come off the same printer. That is a coherent
deep-tech strategy, and it retroactively explains the "IP-driven licensing" language, the two
entities, the two years of prior development, and how a prototyping shop won a defence prize four
weeks after incorporating. They did not invent a weapon in a month. They had a lens and found a war.

---

## 7. Technical assessment

### The single largest unknown: wideband or narrowband

"Pulsed HPM" covers two very different machines.

- **Wideband / damped sinusoid.** Marx generator or pulse-forming line into an impulse-radiating
  antenna. Sub-nanosecond rise, broad spectrum, back-door coupling through cabling and seams. Diehl's
  DS110/DS120 class.
- **Narrowband.** Magnetron or vircator into a horn. Single frequency, front-door coupling, much
  harder demands on prime power and thermal management.

Everything points wideband: "compact, energy-efficient, portable, scalable" is the marketing of a
solid-state switched Marx, and it is the only one of the two a maker with a prototyping shop and
€100k can realistically build. This determines which of Robin's capabilities transfers, so it is
question one and it can be answered by *looking* — capacitor bank plus spark gaps or SiC switches
plus a TEM horn or IRA is wideband; magnetron plus waveguide plus horn is narrowband.

### Risk 1: partial discharge in the printed lattice

Every hour of their lens experience is passive, narrowband, low-power radar. Now they push
megawatt-class sub-nanosecond pulses through the same printed object. A 3D-printed lattice is full
of voids, layer-line gaps and trapped air. Field enhancement inside those voids means discharge can
initiate at macroscopic field levels well below what bulk material properties suggest, and once a
dielectric starts tracking internally it degrades and then fails. A radar reflector never sees
anything close to these levels, so nothing in their prior experience would have flagged it.

If the lens flashes over at operational power, there is no product. This is a modelling question
before it is a hardware question, and it is the sharpest near-term risk to their core asset.

### Risk 2: dispersion smearing the pulse

A graded printed lattice is effectively a metamaterial with a frequency-dependent effective index.
Irrelevant for a narrowband radar reflector — which is precisely why they would not have looked. For
a sub-nanosecond broadband pulse it smears the waveform. If the effect on the target depends on rise
time and peak field, and the aperture stretches the pulse, they lose the thing they were optimising
for. This is full-wave time-domain work.

### Risk 3: band chosen by lens physics rather than target physics

A lens only focuses if it is electrically large. A 20 cm sphere is about two-thirds of a wavelength
at 1 GHz, two wavelengths at 3 GHz, and only around seven wavelengths at 10 GHz where it begins to
behave like a proper lens. So the hardware implies operating well up in the microwave band. But
back-door coupling into a drone works best *low*, in the hundreds of MHz to low GHz, where cable runs
and seams are resonant. Go high and the airframe is electrically large, coupling happens through
small apertures, effects get erratic and atmospheric loss climbs.

**The question to ask, in these words: are you at that band because the drone physics wants it, or
because that is where your lens works?**

### Risk 4: the man-portable form factor is ahead of the entire fielded state of the art

Nobody has fielded shoulder-fired HPM. Everything real is containerised or vehicle-mounted: AFRL's
THOR is a shipping container, IFPC-HPM is a trailer, the Marines' ExDECS is a ground installation,
Leonidas AR is bolted to a ten-tonne tracked UGV. The trade consensus is that HPM is bulky and needs
a crew. Read the poster as concept art expressing ambition. Their honest object is the 1.2 m bench
box.

The physics squeeze also tightens under that form factor: small energy store, small aperture, and a
wide beam (as depicted) all at once gives tens of metres of useful range, not hundreds. Which may be
fine for close-in point defence and is nowhere near what "protecting an airport" implies.

### Risk 5: counter-swarm fights compact and energy-efficient

Wide beam covers many drones but drops the field on each, collapsing range. Narrow beam gets range
but engages one at a time and demands tracking, fast re-pointing and high pulse repetition rate — and
rep rate is thermal and prime-power limited, which is where "compact and energy-efficient" dies.
Their pitch claims all four properties simultaneously. There is a real design surface here (aperture
and beamwidth against range against number of targets against energy per engagement) and it is
computable rather than intuitable.

### The strategic tell

In March the poster sold a soldier's ray gun. By July the FIT profile sells effector modules for
integration by OEMs, with licensing. Those are different companies with different constraints. In
four months the story has already moved once, which is the correct commercial evolution and smells
like accelerator coaching. **Ask which one is the roadmap**, because Robin's value differs: the
man-portable case makes operator exposure existential, the OEM-module case makes aperture and pulse
fidelity the priority.

---

## 8. Where Robin fits

### Genuinely useful

**Near-field operator and bystander exposure.** A shoulder-fired emitter puts a human permanently in
the reactive near field of a pulsed high-peak-field aperture — head, hands and torso within
centimetres to tens of centimetres, plus generator leakage against the chest. Far-field reference
levels do not apply, time-averaged SAR does not capture it, and there is no measurement standard.
This needs body-coupled near-field dosimetry of a pulsed source, which is exactly Robin's field,
including the near-field-device-against-a-body work and the focal-hotspot machinery from paper C.

There is a legal hook that turns this from curiosity into business problem. EU Directive 2013/35 on
workers' exposure to electromagnetic fields lets member states substitute an equivalent or more
specific protection system for the armed forces — NATO standards, for example — but only on condition
that adverse health effects are actually prevented. Defence gets flexibility on the *method*, not a
pass on the *obligation*. And the dual-use civil market they are targeting (airport security staff,
police, critical-infrastructure operators) are ordinary workers with **no derogation at all**. Their
stated route to a bigger market runs straight through a compliance problem they have not started.

Note that their own bio says "to protect people & critical infrastructure" and nothing in any public
material addresses exposure.

**Field prediction in a real environment.** Their range budget depends on the field arriving at the
drone, which in the field is not clean 1/r from an ideal aperture. Ground reflection alone can double
or nearly null the field depending on geometry, and airports and infrastructure sites add fences,
buildings and hangars. This is what hybrid ray tracing with full-wave exists for, and it is the work
they found him through. A servet-level free-space estimate is the likely status quo.

**Lens and feed design as a parametric optimisation.** Infill-to-permittivity mapping, index profile,
feed placement, beam quality, sidelobes, how many feeds before beams overlap. Not "simulate my
antenna" but "the tradeoff you are navigating by intuition is computable, and if you can compute it
you can design against it instead of building three prototypes to find out". That framing is the
differentiable-design-loop USP without disclosing the method.

**Pulse fidelity and breakdown.** Risks 1 and 2 above. Hardest, most valuable, most likely to be
completely unexamined.

### Not useful, and worth saying plainly

- Coupling *into* the target. What a pulse does to a specific drone's wiring, ESCs and flight
  controller is back-door coupling: cable-coupling and statistical EM, closer to reverberation
  chamber work. Not his field.
- Pulsed power hardware, switching, high-voltage engineering.
- Probability of effect per pulse. That is measured, not simulated.

### One honest caveat

If they are wideband, Robin's *older* work transfers better than his newest. The coherent exposure
operator, Q-matrix and precoding work is narrowband and phase-sensitive; a damped sinusoid lives in
the time domain. The hybrid RT/FDTD lineage is the relevant one — which is, ironically, exactly what
Pieter-Paul found on Scholar. **Open question: is that FDTD side a true transient solver, or
frequency-domain stitching?** The answer decides which card is strongest.

---

## 9. Risks to Robin

- **IP.** The IDF is filed and UGent-owned, with zero prior disclosures. Everything said in the lab
  must be traceable to a published paper. No slides, no repo, no demo, not even on request. The
  existence of a patent is not a disclosure; its contents are.
- **Structural incentive.** A company whose stated model is licensing IP it does not yet own, under
  time pressure (MSPO in six weeks), is a company with a strong incentive to acquire technical
  substance quickly. Not sinister, just worth being clear-eyed about.
- **Entity confusion.** Lens contributions accrue to MP Systems / Valtorix, not to Custorix. Get the
  corporate relationship on the record before anything is written down.
- **Export control.** Valtorix states BE/EU/NATO-only development. Belgian dual-use export control
  and UGent's own review would touch any contribution.
- **IOF framing.** Memory says IOF will not fund military. "Dual-use" is Defence's own word and is
  the framing that survives. Do not wave a defence LOI at the IOF file.
- **Opportunity cost.** Robin is finishing a PhD and is a founder in his own venture. The employee
  path here is bad arithmetic (see below). The non-employee paths are all fine.

### Arithmetic on the "is this lucrative" question

Employee case, €20M exit: a well-negotiated early technical hire gets 0.5-2%. Hardware defence needs
several million in capital, so three rounds of dilution at 15-25% each takes 2% to roughly 1%. With
€8-10M raised, a 1x liquidation preference takes that off the top, leaving ~€10M for common. 1% of
that is ~€100k gross, over six to eight years, against a salary €15-25k/year below market. Worse than
industry plus an index fund.

Founder case, same exit: 15-20% at incorporation diluting to 8-10% is €800k-1M+, and Belgium's new
capital gains regime (10% above a €10k annual threshold from 1 January 2026, with a softer graduated
scheme reportedly applying to substantial holdings of 20%+) is comparatively kind. Verify with an
accountant.

Same company, same exit, same physics — a 10x swing decided purely by which side of the cap table.
So: engage, but not as staff.

---

## 10. Questions for the lab visit

Ask Maxime, not Pieter-Paul. Note that the one substantive question already asked ("EMF exposure or
digital twins?") went unanswered in the reply.

**Architecture**
1. Wideband damped sinusoid or narrowband? (Often answerable by looking.)
2. What band, and *why* that band — drone physics or lens physics?
3. Is the lens a Luneburg, and printed in-house?
4. Have you seen partial discharge or tracking in a lens at power?
5. What happens to the pulse shape through the lens?

**Evidence**
6. What has been measured versus simulated? Scope bandwidth, D-dot/B-dot probes, calibration?
7. Has a real drone been brought down? At what range, and is there footage?
8. Do you have test-range or anechoic access?

**Business**
9. How are Custorix and Valtorix related, corporate-wise? Who is Valtorix's engineering co-founder?
10. Man-portable or fixed-site OEM module — which is the roadmap?
11. What did the Start2Def prize actually consist of? Any follow-on Defence contract?
12. What is the imec.istart €100k earmarked for?
13. Are you assembling an EDF-2026 consortium before the 29 September deadline?

**The one to save for when airports come up**
14. How do you plan to demonstrate safe standoff for an operator and for bystanders, for a system
    fielded at a civilian airport?

---

## 11. Options, ranked

1. **Paid co-development contract** on a bounded question (breakdown, dispersion, or range
   prediction). Cleanest. Keeps IP position, defines scope, tests whether they pay.
2. **EDF-2026 work package** with UGent as beneficiary. The programme explicitly wants research-SME-
   Defence bridging; they have the RHID and Defensie doors; deadline 29 September.
3. **Joint paper** on near-field operator exposure for pulsed directed-energy systems. Nobody has
   done it, it is publishable, it is dual-use framed, and it strengthens the standards play.
4. **Advisory stake** for a defined time commitment. Only with the entity question resolved.
5. **Nothing beyond a warm contact.** Perfectly acceptable outcome. The intel is already worth the
   hour.

Employment is not on this list on purpose.

---

## 12. What is still unknown

- Valtorix / MP Systems legal identity and its relationship to Max Prototypes BV.
- Whether a third technical co-founder exists.
- Wideband or narrowband; operating band; peak field; pulse width; rep rate; range.
- Whether any drone has actually been downed, and with what evidence.
- What Start2Def actually awarded, and whether any Defence contract followed.
- Whether the "two years of collaborative technology development" involved a university partner
  already.

---

## Sources

Public registry: KBO Public Search entries for 1036.734.218 (Custorix), 1033.904.390 (Max
Prototypes), 1017.401.524 (Shaa). Flanders Investment & Trade promotieplatform API (event
1f1638a0-1132-460a-8211-595e9500ccf1). start2def.be programme pages. imecistart.com Belgium
programme and portfolio pages. francken.belgium.be press release on the first Start2Def prizes (via
search summary; the page itself blocks automated access). maxprototypes.com. LinkedIn profile and
company pages for Pieter-Paul Smet, Custorix and Valtorix, supplied by Robin. DNS and WHOIS for
custorix.eu, valtorix.eu, custorix.com. Photographs from the BEDEX award, supplied by Robin.
EU Directive 2013/35 as summarised by EU-OSHA and secondary legal commentary. Trade reporting on
THOR, IFPC-HPM, ExDECS and Leonidas for the state-of-the-art comparison.
