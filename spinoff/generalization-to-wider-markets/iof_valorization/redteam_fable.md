# Red-team: valorisation strategy (AEGIS, IOF StarTT, 3 Aug 2026)

Adversarial read of `valorisation_strategy.md` against the primary regulatory texts, the raw discovery
notes, and the two accepted StarTT proposals. I have not softened anything.

Short version: the central argument is wrong, and it is wrong in a way that three people in the
applicant's own network can falsify in under a minute. Everything else in the section is fixable.
This one thing is not fixable by editing, it has to be replaced.

---

## 1. Verdict on the central argument

### WRONG. Not "partly". The load-bearing claim is refuted by the text it cites.

The draft argues:

> Above 6 GHz, ICNIRP 2020 moved the binding limit from incident to absorbed power density, and said
> why: incident power density "is not a direct measure of body exposure since up to 50% of incident
> power density is reflected away from the body". [...] Industry still assesses against incident-field
> reference levels anyway [...] We reclaim margin the limit already grants and that nobody can
> currently afford to compute.

**ICNIRP already granted that margin, in the reference level, explicitly, with an equation.**

ICNIRP 2020, section "Reference Levels From >6 GHz to 300 GHz for Local Exposure", equation (29):

> "The incident power density (Sinc) reference levels above 6 GHz for local exposure can be derived
> from the basic restrictions (i.e., from absorbed power density, Sab):
>
> **Sinc = Sab · T⁻¹  W m⁻²**   (29)
>
> where T is Transmittance, defined as follows:  **Transmittance = 1 − |Γ|²**   (30)"

Source: [ICNIRP RF Guidelines 2020, Health Physics 118(5):483-524, p.513](https://www.icnirp.org/cms/upload/publications/ICNIRPrfgdl2020.pdf)

The reference level *is* the basic restriction divided by the transmittance. The reflected fraction is
already divided out. And the guidelines say so in the next paragraph:

> "In the present guidelines, the basic restrictions and reference levels are derived from
> investigations assuming normal incidence to the multi-layered human model. As this represents
> worst-case modeling for most cases, the results obtained and used in these guidelines will generally
> be conservative."

> "The transmittance asymptotically increases from 0.4 to 0.8 as the frequency increases from 10 GHz
> to 300 GHz (Sasaki et al. 2017)."

> "Considering the frequency characteristics of the transmittance, the reference levels for local
> exposure have been derived as exponential functions of the frequency linking 200 W m⁻² at 6 GHz to
> 100 W m⁻² at 300 GHz (for occupational exposure)."

### The numbers, which settle it

ICNIRP 2020 Table 2 (basic restrictions) and Table 6 (reference levels for local exposure), general
public, >6 to 300 GHz:

- Basic restriction: **Sab ≤ 20 W/m²** (4 cm², 6 min)
- Reference level: **Sinc ≤ 55·f_GHz^−0.177 W/m²** (4 cm², 6 min)

Divide one by the other:

| Frequency | Local reference level Sinc | Basic restriction Sab | RL / BR | Implied transmittance |
|---|---|---|---|---|
| 6 GHz | 40.1 W/m² | 20 W/m² | **2.00** | 0.50 |
| 10 GHz | 36.6 W/m² | 20 W/m² | 1.83 | 0.55 |
| 26 GHz | 30.9 W/m² | 20 W/m² | 1.54 | 0.65 |
| 60 GHz | 26.6 W/m² | 20 W/m² | 1.33 | 0.75 |
| 300 GHz | 20.0 W/m² | 20 W/m² | 1.00 | 1.00 |

The factor of two the draft proposes to "reclaim" is, at 6 GHz, **exactly and precisely** the ratio
already printed in ICNIRP's reference-level table. The implied transmittance curve (0.50 rising to
1.00) is ICNIRP's own conservative rounding of Sasaki's measured 0.4-to-0.8. The occupational tables
give the identical ratio (275·f^−0.177 over 100 W/m²).

So the sentence "industry still assesses against incident-field reference levels anyway, for one
reason: computing what a body absorbs needs a full-wave simulation" inverts the actual situation.
Industry assesses against reference levels because **that is what reference levels are for**. ICNIRP
built them by dividing out the transmittance so that nobody would have to compute absorption. There is
no market failure here. There is a regulatory architecture, working as designed.

### The quote is real but it is misused, and that is worse

I could not find "up to 50%" or "not a direct measure" anywhere in the ICNIRP 2020 guidelines PDF. The
sentence is from ICNIRP's ["Differences between the ICNIRP (2020) and previous
guidelines"](https://www.icnirp.org/en/differences.html) web page, where its job is to explain **why
the dosimetric quantity for the basic restriction changed** from Sinc to Sab. It is not a statement
about unclaimed compliance margin. The same page adds:

> "the value of the basic restriction for EMFs >6 GHz [...] has been set to provide equivalent maximum
> exposures in the body above and below 6 GHz"

and notes that the net effect of ICNIRP 2020 above 6 GHz is *more* restrictive in practice, because of
the reduced 4 cm² averaging area.

The draft attributes the quote to "ICNIRP 2020" and to "the standard itself", which is loose, and then
uses it to support a conclusion that ICNIRP's equation (29) directly contradicts. A grant section that
quotes a regulator against itself is not a small blemish. It is the kind of thing that makes a reviewer
stop trusting every other number in the document.

### Who catches this

- **Wout Joseph**, the promotor, is the Belgian representative to CENELEC TC106X and IEC TC106. He knows Table 6.
- **Christophe Grangeat** (Nokia, IEC TC106 MT3) sits on the maintenance team for the standard.
- **Marta Parazzini** works on high-frequency exposure limits for a living.

All three are named in, or attached to, this application. This claim cannot survive contact with any of
them. It must come out.

### The other four leaks, in order

**(a) The frequency splice.** The regulatory argument is >6 GHz only. Every economic fact used to
monetise it is sub-6 GHz. "2 to 8 m in front of a 40 W macro cell", "beyond 15 m at 250 W", and the
Brussels story are all sub-6 GHz macro numbers. Above 6 GHz, base stations are low-power: the Frontiers
analysis of ICNIRP 2020 mmWave compliance boundaries is conducted for base stations **below 1 W**, and
the reported compliance distances for 5G radios run "less than a few centimeters for low-power indoor
products [...] and up to about 20 m for macro products", where the 20 m macros are sub-6.
([Frontiers in Communications and Networks, 2022](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2022.744528/full))
The money and the physics are in different frequency bands, and the draft staples them together without
noticing. This is the second-most-damaging structural error after the ICNIRP claim.

**(b) The wrong restriction binds at a base-station compliance boundary.** Above 6 GHz, general public,
the whole-body reference level is Sinc ≤ 10 W/m² (Table 5), while the local reference level is ~31 W/m²
at 26 GHz (Table 6). The whole-body one is three times lower, so it binds first. Its basic restriction
is whole-body SAR ≤ 0.08 W/kg, **not** local Sab. The Frontiers paper confirms it: the whole-body SAR
limit governs at the compliance boundary above 6 GHz at higher powers. The draft's Fresnel argument is
aimed at the local Sab restriction, which is not the one setting the boundary. It is shooting at the
wrong target with a gun that is already empty.

**(c) The reactive near-field sentence is a self-own.** The draft writes: "Above 2 GHz in the reactive
near field, ICNIRP 2020 rules that reference levels *cannot* be used at all, so body-based assessment
there is not merely cheaper, it is mandatory." The regulatory fact is correct (Table 6, note 5c, and
the >2-300 GHz text: "reference levels cannot be used to determine compliance, and so basic
restrictions must be assessed"). But per the project's own theory (`honest_analysis.md` Q3, and the
monograph's near-field section), **AEGIS cannot compute the reactive near field**. That regime needs
full-wave. The reactive near-field boundary is λ/2π: 1.7 mm at 28 GHz, 14 mm at 3.5 GHz. So the draft's
one "mandatory demand" argument points at precisely the regime the method does not serve. Delete the
sentence. If a reviewer who knows the method reads it, it is worse than saying nothing.

**(d) Curvature does not rescue the margin.** One might hope that a real curved body absorbs materially
less than ICNIRP's planar normal-incidence model, leaving residual margin for AEGIS to harvest. Diao,
Rashed and Hirata computed exactly this: for curvature radii above ~30 mm and frequencies above
~20 GHz, the differences in heating factor between APD averaging schemes and between TE and TM cases
are **below ~6%**, and the effect of curvature radius on the heating factor is "rather small" (largest
difference between 20 mm and 50 mm radius models ~10%, at 6 GHz).
([arXiv:2007.02604](https://arxiv.org/pdf/2007.02604)) There is no factor of two hiding in the
geometry either. At the hot spot, which is by construction the patch facing the antenna, incidence is
near normal, which is ICNIRP's own assumption.

### What actually survives, and it is not nothing

Three things survive the primary text, and one of them is strong.

**(i) The whole-body reference level above 6 GHz was never re-derived.** ICNIRP carried it over
unchanged from 1998:

> "ICNIRP (1998) set whole-body reference levels within this range (up to 10 GHz) at 50 W m⁻² and
> 10 W m⁻² (for occupational and general public exposure, respectively). As there is no evidence that
> these levels will result in exposures that exceed the whole-body basic restrictions above 6 GHz, or
> that they will cause harm, these guidelines retain the ICNIRP (1998) reference levels for whole-body
> exposure conditions."

That is a statement of *sufficiency*, not of *tightness*. The 10 W/m² figure traces back to whole-body
resonance around 70 MHz, where coupling is maximal. At 26 GHz a standing adult at 10 W/m² absorbs
roughly Sinc × A_projected × T ≈ 10 × 0.6 m² × 0.6 ≈ 3.6 W, giving a whole-body SAR near 0.05 W/kg
against a 0.08 W/kg limit. That is around **1.5x of genuine, unclaimed margin in permitted power,
hence roughly 1.2x in compliance distance** in the far field.

I want to be explicit: **this estimate is mine, and it is NOT VERIFIED.** I did not find a published
number for whole-body SAR at the ICNIRP whole-body reference level above 6 GHz on an anatomical model.
That is precisely why it should be a Phase 1 deliverable rather than a claim in the application. If the
number comes out at 1.0, the applicant needs to know that in month 3, not month 18.

This argument is better than the one in the draft in every respect. It is not contradicted by the
standard. It targets the restriction that actually binds. And because the whole-body reference level of
10 W/m² spans 2 to 300 GHz, **it repairs the frequency splice**: the macro-cell economics and the
physics finally live in the same band.

**(ii) ICNIRP explicitly invites this work.** From the "General Considerations for Reference Levels"
section:

> "information from a technical standards body, designed to specify external exposures for each EMF
> source type to more adequately match the basic restrictions, should be utilized to improve reference
> level assessment procedures."

ICNIRP is asking IEC to build source-specific external-exposure specifications that track the basic
restrictions more closely than the generic reference levels do. That is a written invitation to do
exactly what AEGIS makes cheap. It is a far better quote than the 50% one and it is on the applicant's
side rather than against him.

**(iii) Basic-restriction assessment is legally permitted, and there is no standardised procedure for
it above 6 GHz.** Reference levels are a conservative proxy. Exceeding one does not establish a
violation, and a basic-restriction assessment is the accepted escalation route. IEC 62232:2025 is
explicitly in scope for "RF field strength, power density and specific absorption rate (SAR)"
determination and covers "measurement and computation methodologies", 110 MHz to 300 GHz
([IEC 62232:2025](https://webstore.iec.ch/en/publication/89073)). Meanwhile the Frontiers authors state
plainly that "standardized procedures for the assessment of absorbed power density currently do not
exist" above 6 GHz. That gap is the actual opportunity, and it is a standards opportunity, not a margin
opportunity.

**But note what the buyers said.** Ericsson: "for CD we use reference levels in-house tool." Nokia:
"operators probably prefer on reference level basis." Legally permitted is not the same as
commercially wanted. Both vendors told him, unprompted, that the reference-level route is the one they
want to keep using. The draft does not report this.

---

## 2. Everything else that is wrong or unsupported, ranked by damage

### 2.1 The section leads with the base-station story that Ericsson's own standards expert told him to abandon

From the Ericsson notes:

> "there is this standard 63195, where stanislav was part of it and his reaction was: **go there instead
> of base stations** cuz we just work with compliance distance and thats it. -2: that is IPD
> simulations. **-3 and -4: APD simulations. not published yet**, 1 TR is there"

The single most qualified person in the discovery set, a contributor to the very standard in question,
said: do not go to base stations, go to devices, and by the way parts 3 and 4 (the APD simulation
parts) are not published yet.

The applicant's own `honest_analysis.md` reaches the same conclusion independently ("Rebuild the primary
pitch around device mmWave APD pre-compliance, not base-station compliance" and "Stop pitching operators
as the first customer"). The literature agrees that no standardised APD assessment procedure exists yet.

Three independent sources point at devices. The draft leads with base stations. This is the largest
strategic error in the document after the ICNIRP claim, and it is self-inflicted, because the evidence
is already in the applicant's own files.

The irony is sharp: **above 6 GHz, on devices, absorbed power density genuinely IS the certification
quantity.** It is what IEC/IEEE 63195 exists to compute. That is the market where the APD story does not
need a rhetorical assist, because APD is simply the thing the customer must produce. And it is the
regime AEGIS actually covers (radiating near field, 5 to 200 mm, above 6 GHz), where FDTD is most
expensive, where thousands of beam-by-grip-by-position scenarios must be swept per product cycle, and
where differentiability pays because antenna placement is a design variable. The strong version of the
draft's own argument is sitting one market over, unused.

### 2.2 The ZMT rebuttal is contradicted by the applicant's own letter of support

The draft says:

> "That revenue comes from a neighbouring market, implant and MRI safety [...] The buyers named above
> are largely not ZMT customers"

Parazzini's statement, which the jury will read, says:

> "Zurich MedTech provides some licences for free as part of their University Research Agreement"

The flagship alpha customer is a ZMT customer. So is essentially every device OEM and test lab, which
is the strongest market. The rebuttal is false as written for the best segment and is falsified by an
annex of the same application.

Worse, **the rebuttal does not answer Filip's objection, it evades it.** Filip said the niche is too
small. The draft's reply is "that number does not measure this niche." Fine, but then the draft never
supplies a number that does. It demolishes the only figure on the table and puts nothing in its place.
A business developer reads that as a dodge, and he will be right.

There is also a sourcing problem underneath: the $2.3M ARR / $6.8M valuation figures in
`LARGE-zmt-market-analysis.md` have the smell of scraped estimates rather than audited accounts. Do not
build an argument on either side of a number you cannot source.

The honest and much stronger answer is in section 4.2 below: concede the niche is small, size it
bottom-up, and point out that IOF StarTT is not a venture fund. The accepted Unisens proposal projects
**€780k of turnover in year 5**. That is the bar. It was cleared. A small niche is not a disqualifier
here, and pretending otherwise is what makes the section look defensive.

### 2.3 The traction is over-read, and the notes are cleaner than the spin

Comparing the draft against the raw notes:

| Draft says | Notes say |
|---|---|
| "Called instantaneous whole-body assessment *'great to have'* and AEGIS a plausible *'drop-in replacement'*" | "if you do already the IPD, you need X data, but APD is AS FAST and needs SAME data, then yeah. **for emf visual or ixus. like a drop-in replacement**" |
| "Outcome: an **invitation to present to the full team for a full day** after the summer" | "the invitation is to do it properly now after summer **if patent and whatnot allows**" and "stanislav definitely said many times it looks cool and promising, but obviously **'cool' doesnt buy us much**" |
| Nokia: "A deliberately sceptical read, which produced the most useful instruction we received" | "**he thinks its more a research project than valorization. not in the agenda.**" / "att will not buy nokia instead of ercisson cuz of this. **no new customers. only if operators ask for this themselves**" / "operators probably prefer on reference level basis" / "he doesn't see it generalizing" |

Three specific problems.

**The Ericsson quote is truncated at the point where it stops being flattering and starts being
useful.** Stanislav did not say AEGIS is a drop-in replacement for a full-wave solver. He said it is a
drop-in replacement **inside EMF Visual or IXUS**. He described the shape of the deal: an embedded or
OEM licence into the tool the operator already uses, not a standalone seat. That is the single most
valuable commercial finding in the entire discovery set and the draft deletes the half of the sentence
that contains it. See 3.5.

**The Nokia paragraph launders a No into coaching.** Grangeat said this is a research project, not
valorisation, and that there is no customer pull. That is data, and it is good data: it says the
base-station pull does not exist today. The correct use of that finding is to justify moving the
beachhead to devices. Instead the draft converts it into a helpful lesson about standards and moves on.
An IOF jury may not read the notes. Wout will. Filip might.

**An invitation to demo is not traction.** It is a second meeting, and it is conditional on the patent.
Do not present it in the same register as a signed letter of interest.

### 2.4 The Brussels anecdote cuts both ways

It is factually right (Brussels held a ~6 V/m norm, roughly fifty times stricter than ICNIRP in power
density terms, BIPT concluded new frequencies could not be brought into service, and 5G stalled until
the limit was raised to 14.5 V/m in 2021). But:

- It is a **sub-6 GHz** story, so it does not support a >6 GHz argument.
- It is a **reference-level** story: the binding constraint was a field limit, not an absorption limit.
- It was resolved **politically**, by raising the limit. Nobody solved Brussels with a better solver.

As written, the anecdote quietly argues that when exposure limits bind hard enough to matter, the lever
that moves is regulation, not simulation fidelity. Keep it to one clause as proof that exposure limits
have economic consequences, and do not let it carry weight it cannot bear.

### 2.5 The 17-application screen is dressed up

The draft: "A structured screen of 17 candidate applications, run in mid-2026 with UGent TechTransfer".
The applicant's own notes on that meeting: "HONESTLY it is a BS meeting. just Filip virtue signal Tom
in here [...] AND i dont CARE for answers."

The **selection rule** that came out of it is genuinely good, falsifiable, and worth keeping: value
where the task is to design a controllable coherent excitation against a quadratic power limit, none
where the task is to certify a passive scattering signature. Keep the rule. Drop "structured screen"
and "run with UGent TechTransfer" unless a written screen actually exists that could be produced on
request. If a reviewer asks to see the 17 and there is no document, the credibility loss is out of all
proportion to what the phrase buys.

### 2.6 The gated exploration WP misses the one deadline that would make it bite

This WP is politically well-constructed and it is the right answer to Filip. But it does not connect to
the decision it is supposed to inform.

The patent is due end of July 2026, so priority lands around August 2026, which puts the **PCT deadline
at roughly August 2027**. If the project starts in January 2027, the M6 gate falls around June 2027,
which is **one to two months before the last moment the family's scope can still be widened**.

That alignment is a gift and the draft does not use it. Say it explicitly. It converts a vague "gated
exploration" into a decision synchronised with a hard, dated legal deadline, and it answers Filip in his
own currency. Right now the WP reads like a way of deferring his objection. With the PCT date in it, it
reads like a plan for resolving it.

Also tighten the gate criterion. "Identifies one adjacent application with a named industrial customer"
is not a gate, it is a hope. A gate is: **a signed LOI or a paid pilot from a named company by M6, or
the patent family stays narrow.**

### 2.7 Nobody is named as running the spin-off

Both accepted proposals name the person. EIoT: "we have a clear goal to create a spin-off company
**under the lead of Anniek Eerdekens**." Unisens: "the team (**Kenneth Deprez, Lowie Christiaen**)
together with the promotors and business developer is present."

The AEGIS draft names a promotor and an advisor and no founder. For a jury assessing a spin-off route,
that is a conspicuous hole, and it is free to fill: name the founder, the promotor, the TechTransfer
business developer, and the istart co-founder arrangement. This costs nothing and needs no new hires.

### 2.8 What the accepted proposals actually do that this one does not

I read both valorisation sections looking for the shape of the thing that passes. They are not
arguments. **They are relationship maps.**

Unisens spends its two pages naming roughly thirty organisations with existing ties: VPO-Flanders
(support letter, 7+ tenders), Fluvius (already asked for a prototype), Elia, Sibelga, ORES, Proximus,
Orange, Telenet, CityMesh, Agoria, the Dutch/Swiss/UK/French regulators, GSMA, MMF, EPRI, ARPANSA. Then
a phased contact plan. Then a unit price with a worked example. Neither accepted proposal stakes its
valorisation section on a contested technical claim. Neither one needs to.

EIoT does not even have a revenue table. It has a unit price (€72.50 implant plus subscription), a named
lead, named ambassadors, and named channel partners (Equicty, Pavo, Cavalor) plus an insurance channel.

The AEGIS draft has one letter, one invitation, one sceptic, and a physics argument doing all the
load-bearing work. **Rebalance: less argument, more named channel.** The applicant has more relationship
surface than he is using (WAVES in three of four EU 5G-health projects, Wout in CENELEC TC106X and IEC
TC106, the BioEM board, GOLIAT, SEAWAVE, ETAIN, the Sim4Life competition win). Almost none of it appears
in the section.

---

## 3. Pricing and revenue

### 3.1 The turnover table is a near-clone of the accepted Unisens table

| Year | Unisens (accepted) | AEGIS draft |
|---|---|---|
| 1 | 120 000 | 110 000 |
| 2 | 240 000 | 280 000 |
| 3 | 420 000 | **420 000** |
| 4 | 600 000 | 580 000 |
| 5 | 780 000 | 760 000 |

Year 3 is identical and the rest are within a rounding error. Whatever the intent, this reads as a table
reverse-engineered to a number known to have passed, rather than derived from a customer count. If the
same panel or the same business developer sees both documents, that is a bad moment. Rebuild the table
from the bottom up so the arithmetic is visible and the numbers land where they land.

### 3.2 The research licence at 4 kEUR/yr is both unsupported and strategically backwards

The anchor is Parazzini's 3 kEUR/yr. But the same letter says ZMT gives Sim4Life to her group **free**
under a University Research Agreement. So the offer is: pay 4 kEUR for the challenger, or pay zero for
the incumbent that is already installed, already validated, already in the standards, and already has
the phantoms.

That is not a price, it is a tax on adoption. And it taxes the exact channel that the whole strategy
depends on. Parazzini's own ranked adoption criteria are a usable platform with tutorials (5/5) and a
peer-reviewed validation paper (4/5). `standards_play.md` argues, correctly, that citations and
standards recognition are worth more than any individual customer, and that this is the Kuster playbook.
Charging academics 4 kEUR/yr while running that playbook is self-defeating.

It is also **only about €100k of the €760k year-5 figure**. Give it away. Make the academic tier free or
nominal and say so as a deliberate funnel decision. That converts a weak revenue line into a strong
strategic one, and it is the kind of move a jury recognises.

### 3.3 The industrial tier collides head-on with the Nokia datapoint, and the draft does not mention it

Nokia's EMF team: "**less than 10 kEUR/year**" on software of this class, "FTE <10", "not FDTD. just EMF
Visual for their reports and site analysis on operator request".

One of roughly six infrastructure vendors on the planet has a **total annual budget for this entire
software category that is half of one AEGIS industrial seat**. The draft prices an industrial licence at
20 kEUR/yr and never mentions this. It is in the discovery notes. A reviewer who has the notes, or a
business developer who asks one question, finds it immediately.

There is a good answer, and the draft should give it: **the EMF team's software line is the wrong budget
to target.** The right budget is either (a) the antenna and full-wave budget, which is ten to a hundred
times larger and is where CST, FEKO and HFSS are actually paid for, or (b) not a seat at all, but an OEM
licence into the tool the customer already buys. Which brings us to the finding the draft threw away.

### 3.4 The enterprise tier misuses its own letter of support

The draft justifies 40 kEUR/yr as "against a workflow costing 1 to 2 FTE in waiting". That figure comes
from Parazzini. Read her letter carefully:

- 4 to 5 researchers use FDTD.
- **Two** work above 6 GHz. **Three** work below 6 GHz on biomedical applications.
- The 1.5 FTE of waiting is across the whole group.

AEGIS serves above 6 GHz. It cannot serve the sub-6 biomedical work (reactive near-field, deep-body,
volumetric). So the AEGIS-addressable share of that pain is roughly **0.6 FTE, not "1 to 2 FTE"**.

The draft quotes a number from its own annexed letter in a way the letter does not support, to justify a
price to a customer segment (enterprise) that is not the customer the letter is from (an academic
institute paying 3 kEUR). A reviewer holding both documents catches this. It is a small dishonesty and
it costs more than it earns.

### 3.5 The year-5 customer count is not credible as a seat model, and is credible as a channel model

Twenty-four industrial and enterprise licences by year 5. Count the universe from the applicant's own
files: ~5-6 infrastructure vendors, ~12-15 mmWave device OEMs plus 2-3 chipset vendors, ~20-40 test labs
doing RF exposure, ~10-15 regulators, ~20-40 research institutes. Call it 80 to 110 organisations
worldwide, generously.

Twenty-four paying seats is **20 to 30 percent global penetration, by a one-person Belgian spin-off,
against an incumbent ecosystem twenty years old**, within five years, with no salesforce. It is not
credible and a jury that thinks for thirty seconds will see that.

The same number becomes entirely credible under the model the buyer handed over and the draft deleted:

> "**for emf visual or ixus. like a drop-in replacement.**"

An OEM or embedded licence into the tools the customers already run (IXUS/EMSS, EMF Visual/MVG, ATDI,
Forsk, or Sim4Life itself as a fast pre-screener) reaches the same revenue through **two to four deals
instead of twenty-four**. It matches how simulation software is actually distributed. It matches the
`honest_analysis.md` recommendation to pursue the ZMT partnership as the primary path rather than plan
B. It even partially concedes Filip's licensing thesis while redirecting it from Keysight and Ansys,
who do not sell into this workflow, to the vendors who do.

Restructure the revenue model around three lines: **direct seats for institutes, test labs and device
OEMs, an OEM licence or royalty for the compliance-tool vendors, and contract research.** Then the year-5
number stops depending on a penetration rate nobody would believe.

---

## 4. Concrete replacement text

Prose below is drafted to drop in. No em dashes, no semicolons, sentence case headings.

### 4.1 Replacing "The regulator has already conceded the margin we sell"

Cut the paragraph entirely. It is not repairable. Replace with:

> **Above 6 GHz, absorbed power density is the compliance quantity, and nobody has a fast way to compute
> it.** ICNIRP 2020 made absorbed power density the basic restriction above 6 GHz, and IEC/IEEE 63195
> makes it the certification quantity for devices. The reference levels that stand in for it are generic
> plane-wave proxies, derived on a planar multi-layer model at normal incidence. They are deliberately
> conservative and they are not source-specific. ICNIRP says as much, and asks for better: "information
> from a technical standards body, designed to specify external exposures for each EMF source type to
> more adequately match the basic restrictions, should be utilized to improve reference level assessment
> procedures." No such source-specific procedure exists above 6 GHz. Parts 3 and 4 of IEC/IEEE 63195,
> which cover absorbed-power-density simulation, are not yet published, and the assessment procedures
> they will specify are not yet decided. That is the gap this project addresses, and the window is open
> now.
>
> **The obstacle is cost.** Computing absorbed power density on an anatomical body needs a full-wave
> simulation, at hours per scenario, which is why assessment falls back on the generic proxy. A device
> product cycle needs thousands of scenarios across beam configurations, grips and body positions.
> AEGIS replaces the volume simulation with a closed-form surface integral: milliseconds per scenario,
> and differentiable, so absorbed power becomes a design variable rather than a post-hoc check.

Note what this does. It stops arguing with the regulator, which is a fight the applicant cannot win, and
starts arguing that the standard is incomplete in a specific, dated, checkable way, which is a fight he
can win and which his promotor is positioned to fight.

### 4.2 Replacing the market-size paragraph

Cut "It is not. That revenue comes from a neighbouring market". Replace with:

> **On market size.** This is a specialist market and we will not pretend otherwise. The global
> electromagnetic simulation market is roughly $1.7B, but the slice concerned with human RF exposure is
> a low-single-digit-millions niche, and ZMT's reported revenue is one plausible order-of-magnitude
> marker for it. Bottom-up, the buyers are roughly six infrastructure vendors, twelve to fifteen
> mmWave device makers and their chipset suppliers, twenty to forty test laboratories, ten to fifteen
> regulators, and several dozen research institutes. At the prices below, a serviceable market of a few
> million euros per year is the honest ceiling.
>
> That is the right size for this instrument. We are not proposing a venture-scale company. We are
> proposing a capital-efficient software spin-off on the same model as the two recent StarTT spin-offs
> in this group, targeting seven-figure recurring revenue and a strategic exit to an established
> simulation or compliance-tool vendor. The niche being small is not an argument against the spin-off,
> it is an argument for reaching it through the incumbents' distribution rather than around it, which is
> what the route to market below does.

This is the paragraph that answers Filip. It concedes the true thing, which immediately buys back all
the credibility the current draft spends, and then reframes to the actual funding instrument. Note that
the accepted Unisens proposal projects €780k in year 5 and cleared this jury. The bar is not a unicorn.

### 4.3 Replacing the pricing table

> | Tier | Price | Anchor |
> |---|---|---|
> | Academic and research | Free, with citation requirement | Deliberate funnel. ZMT supplies Sim4Life free to academic groups under a University Research Agreement, so a paid academic tier would not clear. Citations and standards recognition are the asset. |
> | Test lab and institute seat | 12 to 20 kEUR/yr | Below one commercial full-wave seat, against the budget it displaces |
> | Device maker and vendor seat (API, report automation, design loop) | 40 kEUR/yr | Under half an FTE, against a pre-compliance workflow of thousands of scenarios per product cycle |
> | OEM licence into a compliance tool | 60 to 150 kEUR/yr plus royalty | The route Ericsson's EMF team described unprompted: "for EMF Visual or IXUS, like a drop-in replacement" |
> | Contract research | 40 to 60 kEUR/project | Vendor studies, EU projects |

And then, honestly, in the text:

> **Two datapoints constrain this pricing and we state them plainly.** Nokia's EMF team reports spending
> under 10 kEUR per year on software of this class, and CNR-IEIIT pays 3 kEUR per exposure licence.
> Neither supports a seat-based model sold into an EMF team's existing software line. Both are why the
> model above sells design-loop value to the engineering budget that already pays for full-wave tools,
> and sells distribution to the vendors whose compliance products the operators already run.

Stating the awkward numbers yourself is the single highest-leverage move available in this section. It
converts the two facts most likely to sink the section into evidence that the applicant did real
discovery and drew the right conclusion from it. Reviewers reward this. Hiding them and getting caught
is fatal, and Filip already has the notes.

### 4.4 Rewriting the alpha-customer bullets honestly

> - **CNR-IEIIT Milan, Dr. Marta Parazzini, Director of Research.** On the record and signable: two of her
>   researchers work above 6 GHz and she intends to hire more as FR3 arrives. On the workflow, "the
>   bottleneck is always the mesh, it is our nightmare." On price, "if I really find a real improvement
>   with respect to what I have now, I would be able to pay you." She ranked what would make her adopt: a usable platform
>   with tutorials (5/5), a peer-reviewed validation paper (4/5), standards recognition (3/5). Phase 1
>   delivers all three. She is the validation and citation route, not the revenue route, and we price her
>   accordingly.
> - **Ericsson Research, EMF team (6 to 7 people, 1 to 2 FTE on full-body simulation in CST, FEKO, HFSS).**
>   Two findings, one encouraging and one instructive. The team set the target: "if you can reduce the
>   compliance boundary only because you added the human body, that would be a great story." And they
>   described the shape of the deal without being asked: absorbed power density needs the same input data
>   as the incident power density they already compute, so the method is "a drop-in replacement, for EMF
>   Visual or IXUS." That is a distribution instruction, and we have taken it. Outcome: an invitation to
>   demonstrate to the full team after the summer.
> - **Nokia, C. Grangeat (IEC TC106 MT3).** A clear negative on the base-station route and the most useful
>   result we obtained. He reports no operator pull for body-based compliance ("operators probably prefer
>   on reference level basis", "only if operators ask for this themselves") and judged the work closer to
>   research than to valorisation on that route. We take this at face value. It is why the beachhead is
>   device-side absorbed power density under IEC/IEEE 63195, where absorbed power density is already the
>   certification quantity, and why the base-station case is scoped to the escalation use (a site that
>   fails the reference-level test and today loses power or the site) rather than to routine assessment.

Turning Nokia into a documented negative that visibly changed the plan is worth more than any positive
quote in the section. It is the clearest possible evidence that customer discovery actually happened and
actually did something. Right now the draft spins it, which achieves the opposite.

### 4.5 The compliance-boundary claim, if it stays at all

If the base-station story is kept as a secondary case, it must be stated as a hypothesis with a Phase 1
test, not as a fact:

> **The margin at a compliance boundary is a measurable quantity and we will measure it.** Above 6 GHz
> the binding basic restriction at a base-station compliance boundary is whole-body SAR at 0.08 W/kg for
> the general public, and its reference-level proxy of 10 W/m² was carried over unchanged from ICNIRP
> 1998, where it was set by whole-body resonance near 70 MHz. It has not been re-derived for the
> superficial-absorption regime above 6 GHz. Our estimate is that an anatomical assessment recovers
> roughly a factor of 1.5 in permitted power density, hence roughly 1.2 in distance, but this is an
> estimate and no published value exists. Phase 1 computes it, for a named IEC 62232 reference
> configuration at 3.5 GHz and at 26 GHz, and reports the ratio of the reference-level boundary to the
> basic-restriction boundary. If the ratio is 1.0, we will say so and the base-station case is closed at
> month 6 rather than month 18.

This is the move that most improves the section's standing with a technical jury. It replaces an
assertion that a reviewer can falsify with a measurement that a reviewer would want to see, and it puts
a kill date on the weaker half of the business.

### 4.6 Delete outright

- The reactive near-field "mandatory" sentence. AEGIS cannot compute the reactive near field.
- "The standard itself concedes that assessing on the incident field over-states what a body absorbs, by up to a factor of two."
- "We reclaim margin the limit already grants and that nobody can currently afford to compute."
- "That reflected fraction is precisely the Fresnel transmission coefficient" as a compliance argument. Keep it as a statement of what the engine computes, which is true and useful, just not as a margin claim.
- "run in mid-2026 with UGent TechTransfer", unless a written screen exists.
- The Brussels paragraph, cut to one clause.

---

## 5. The one-line summary

The section is built on a factor of two that ICNIRP already handed to industry in 2020, in Table 6, via
equation (29). Remove that argument and what is left is a good company aimed at the wrong beachhead,
priced with a model its own discovery notes contradict, and hiding a distribution insight that the
customer volunteered for free. Fix all four and this is a strong application. Submit it as it stands and
the promotor will find the error before the jury does.

---

## Sources

- [ICNIRP RF Guidelines 2020 (Health Physics 118(5):483-524), full PDF](https://www.icnirp.org/cms/upload/publications/ICNIRPrfgdl2020.pdf) - equations (20), (29), (30); Tables 2, 5, 6; reference-level derivation above 6 GHz; reactive near-field rules
- [ICNIRP, Differences between the ICNIRP (2020) and previous guidelines](https://www.icnirp.org/en/differences.html) - origin of the "up to 50% ... reflected away from the body" sentence
- [Implications of ICNIRP 2020 Exposure Guidelines on the RF EMF Compliance Boundary of Base Stations, Frontiers in Communications and Networks, 2022](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2022.744528/full) - whole-body SAR governs the boundary above 6 GHz; local reference levels ~3.5x higher at 28 GHz under ICNIRP 2020; no standardised APD assessment procedure exists
- [IEC 62232:2025, base station EMF assessment, 110 MHz to 300 GHz](https://webstore.iec.ch/en/publication/89073) - scope covers field strength, power density and SAR, measurement and computation
- [Diao, Rashed, Hirata, Assessment of absorbed power density and temperature rise for nonplanar body model above 6 GHz, arXiv:2007.02604](https://arxiv.org/pdf/2007.02604) - curvature and TE/TM effects on heating factor below ~6 to 10 percent for radii >30 mm above 20 GHz
- Internal: `spinoff/outreach_dossier/Ericsson/resulting_meeting_notes.txt`, `spinoff/outreach_dossier/Nokia/resulting_meeting_notes.txt`, `spinoff/outreach_dossier/letters/parazzini_statement_22jun.tex`, `spinoff/LATEST_GOOD/honest_analysis.md`, `spinoff/LATEST_GOOD/standards_play.md`, `spinoff/IOF/F2024_IOF-StarTT_076 - Unisens-5.pdf`, `spinoff/IOF/F2024_IOF-StarTT_006 - EIoT Chip (1).pdf`
