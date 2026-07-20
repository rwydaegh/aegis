# Near-field pre-compliance: the concrete money plan

*Claude Fable, July 2026. Builds on `spinoff/LATEST_GOOD/honest_analysis.md` (April 2026), which established the market structure. This doc answers the next question: who literally pays, when, and how the public-FCC-data intuition converts to cash. Regulatory facts below were verified against FCC KDB sources in July 2026.*

---

## 1. The premise correction: the device side pays TODAY

The "standards are years and years away" feeling is true for base stations, 6G, and population exposure. It is false for device near-field compliance:

- FCC has enforced power-density limits (not SAR) above 6 GHz since the 2019 RF exposure R&O. Every FR2 phone, 60 GHz radar, WiGig device, and mmWave CPE certified in the US files PD exposure evidence right now.
- IEC/IEEE 63195-2 (computational APD, 6 to 300 GHz, up to 200 mm from body) was published in 2022. The 2026 revision is in draft. This is not a future standard, it is the current one.
- FCC KDB 447498 says PD simulation for portable devices above 6 GHz "requires a KDB inquiry", meaning FCC accepts computational methods case by case. Whoever accumulates accepted-method precedent builds a moat that is procedural, not physical.
- KDB 388624 (Pre-Approval Guidance): several mmWave device categories cannot be certified by a TCB alone, the TCB must request FCC pre-approval guidance. This adds weeks to months per product. Pain that money already flows around.

So the market is not waiting for standards. It is certifying devices against live rules with tooling (full FDTD + DASY measurement) that is slow and expensive.

## 2. The FCC public data, verified

- The Equipment Authorization System (EAS) is public, has a web API (KDB 953436), and is fully mirrored with test report PDFs by fcc.report and fccid.io.
- A test report PDF contains: measured SAR/APD values per configuration, test distances, antenna locations, device photos, frequencies, power levels, the test lab, the TCB, and dates.
- ISED Canada's REL is similarly public. The EU (RED) has no public database, so the FCC window is effectively the world's window: the same hardware ships globally.
- Module integration guidance (KDB 996369) confirms that host products integrating pre-certified modules still owe an RF exposure evaluation, and misclassification (mobile module in a body-worn host) has caused US import denials.

### Three distinct uses of this data

**Use 1: a free validation corpus.** Thousands of public filings are measured ground truth: geometry photos, antenna positions, frequencies, and measured APD/PD values. Scrape them, rebuild the scenarios in AEGIS, and publish "AEGIS reproduces N measured FCC filings within X dB". This is stronger marketing than a Sim4Life cross-check because it is measured data, and it costs nothing but compute. It also substitutes short-term for the matched Sim4Life validation the April doc called essential.

**Use 2: a lead-generation engine.** The database tells you, per company: do they ship >6 GHz portable devices (do they need us), what margins did they measure (a result at 95 percent of the limit means design pain), how long did their PAG take (grant date minus filing date), did they re-file or do Class II permissive changes (they failed something and paid twice). Rank prospects by pain. All public record.

**Use 3: a sellable product in itself.** Nobody sells the *extracted, structured* exposure dataset: measured values, distances, antenna placements, margins, lab turnaround benchmarks, parsed out of tens of thousands of PDFs. fcc.report only mirrors documents. An "RF exposure intelligence" subscription for compliance teams and test labs (which antenna placements pass, how your margin compares to competitors, which labs are fast) at 5 to 15k EUR/yr is a low-tech product Robin plus Claude can build in weeks. It funds and de-risks the simulation business and every subscriber is a warm lead for it.

## 3. Who actually pays: the beachheads, filtered by physics

AEGIS is valid in the radiating near field, invalid in the reactive near field. That filter, applied to the certification universe:

**Beachhead A: 60 GHz radar.** Reactive boundary 0.8 mm, occupants at centimeters. Perfectly in-regime.
- In-cabin automotive radar for child presence detection (Euro NCAP is pushing CPD, most solutions are 60 GHz radar). Every carmaker and Tier-1 (IEE, Aptiv, Vayyar-based, Acconeer/Infineon-based integrators) is certifying these with humans in the near field.
- Consumer presence/sleep/gesture sensing (Nest-style, sleep trackers, laptop presence sensors).
These teams are radar engineers, not dosimetry experts. High volume of distinct products, low in-house capability.

**Beachhead B: FR2 modules, CPE/FWA, laptops, XR at 60 GHz.** The honest_analysis story. The OEM antenna teams are sophisticated, slower to close, higher value.

**Beachhead C: UWB (6.5 to 9 GHz).** Above the 6 GHz transition so APD applies, but reactive boundary is ~6 mm, so body-contact wearables are borderline. Case by case.

**Explicitly NOT a target: sub-6 GHz body-worn SAR** (BLE, LTE-M wearables). Reactive near field, out of regime. Refer these to a partner test lab or a GOLIAT-style Sim4Life service. Saying "we don't do that" early builds trust and avoids the credibility-killing failure.

## 4. The revenue ladder (in order of arrival)

1. **Fixed-price pre-compliance reports, 3 to 8k EUR, 1 week turnaround.** "Send CAD + antenna model, we return: worst-case exposure map, pass/fail margin prediction, recommended antenna placement, and a simulation annex formatted the way FCC filings expect." Consulting on purpose: it is immediate cash and it is how you learn what the product is.
2. **Test lab channel.** Labs do not do simulation. Offer white-label pre-screening so their customers pass on the first measurement cycle. Lab director decides fast, and each lab brings a stream of Tier A customers.
3. **The intelligence database subscription** (Use 3 above), sold to the same people.
4. **Seats/retainers for OEM antenna teams** (Beachhead B), enabled by the validation corpus and later the ZMT relationship.
5. **The procedural moat**: accumulate KDB inquiries where FCC accepts AEGIS-based computational annexes, and push AEGIS into the 63195-2 2026 revision (Wout's ecosystem). After a few accepted filings, "the method FCC has already accepted N times" is the sales pitch and the acquisition rationale.

## 5. The 90-day plan

**Days 1 to 10: scrape and structure.**
- Pull EAS grants via the API, filter equipment classes and frequency >6 GHz, portable/mobile exposure categories.
- Download test report PDFs from fcc.report mirrors. LLM-extract: measured values, distances, configs, lab, dates, margins.
- Outputs: (a) prospect list ranked by pain, (b) validation target list of 20 well-documented filings, (c) first cut of the intelligence DB schema.

**Days 10 to 40: the validation artifact.**
- Rebuild 10 to 20 filings in AEGIS (device position, antenna model from photos/patterns, frequency). Compare predicted vs measured.
- Produce a 2-page "AEGIS vs measured FCC certification data" note. This is the calling card, the paper seed, and the ZMT conversation opener all at once.

**Days 30 to 60: ten discovery contacts, each carrying a gift.**
- The email is not cold: "We rebuilt your public FCC filing for [product] and predicted your measured APD within X percent. We think we can pre-screen your next design in a day instead of a lab cycle. 20 minutes?"
- Target mix: 3 automotive in-cabin radar (Tier-1s and radar chipset FAEs), 2 consumer 60 GHz radar, 2 test labs (Eurofins, Verkotan, or a US lab visible in the scraped data as high-volume), 1 module maker FAE (Quectel/Telit/u-blox), 1 TCB, 1 ZMT applications engineer.
- Titles to search: "regulatory compliance engineer", "RF exposure", "certification engineer", "EMC/RF test lab manager".

**Days 60 to 90: first paid work.**
- Close 1 to 2 fixed-price reports. Even one at 5k EUR converts the company from thesis to business.
- Pitch 2 labs on a referral/white-label arrangement.
- File the first KDB inquiry alongside a customer filing to start the procedural track record.

**Parallel, ongoing:** the 63195-2 2026 revision window via Wout, and the near-field validation paper (TAP/TMTT) built directly on the FCC corpus results.

## 6. Contact mechanics

- The certification world's watering hole is the **TCB Council workshops** (twice a year), not BioEM. Every lab, TCB, and OEM compliance lead attends. One trip buys the network.
- LinkedIn works in this niche because the titles are exact and the community is small. The scraped database gives the company names, the filing PDFs literally name the responsible engineers sometimes.
- Test labs are the multiplier: they cannot ethically design their customers' antennas, so a referral partner who makes their customers pass faster is a gift to them, not a competitor.

## 7. Honest caveats

- The validation corpus play assumes filings contain enough geometry to rebuild scenarios. Some do (photos, dimensioned drawings), some don't. Expect a 30 to 50 percent usable rate, which is fine at this volume.
- Antenna patterns are rarely in filings. Rebuilds will need pattern assumptions or vendor datasheets. Report accuracy honestly with that caveat, buyers know their own antennas.
- FCC confidentiality requests hide some reports (short-term confidentiality on photos/schematics is common). The long tail of smaller applicants hides less.
- The dream near-field module does not exist yet. Everything above except the paid reports can start before it is finished, and the FCC corpus itself tells you which capabilities to build first.
- The intelligence DB has thin defensibility (public data). Treat it as cashflow and lead-gen, not the company.

## 7b. Update after reading actual reports (July 14, 2026)

Three example filings downloaded and read in full (PDFs in `example_reports/`). They resolve the "step 3 ????" question. The three archetypes:

**Archetype 1: FR2 phone, measured PD** (Motorola razr 5G, IHDT56ZP1, Sporton lab). Measured free-space PD at 2 mm from each surface, per beam ID, per antenna module, 4 cm^2 averaged, SPEAG cDASY6 + field reconstruction. The decisive detail: **simulation is already load-bearing inside the certification.** The measured campaign only samples worst cases that a mandatory prior simulation identified ("beam IDs with highest simulated PD were selected for testing"), surface-to-surface and distance-to-distance worst-case ratios must come from a "validated model/simulation", and a separate Part 0 simulation report derives the input power limit. So every FR2 filing sits on top of a full-codebook simulation sweep that the OEM must run and validate. That sweep, not the measurement, is the AEGIS-shaped hole.

**Archetype 2: WiFi 6E/7 module in a laptop/tablet, SAR + PD + APD** (Dell tablet, Qualcomm QCNFA765, Bureau Veritas). Reports **APD explicitly** (8.61 W/m^2) alongside PD for the 6 to 7.125 GHz band, tested at 0 mm body contact. APD compliance is routine filing practice today, not a future standard. And the report *contains the antenna data*: part numbers, types (monopoles), peak gain per band. Simple antennas, huge volume (every WiFi 6E/7 laptop, tablet, AP), geometry partially in the filing. Caveat: 0 mm at 6.5 GHz is inside the reactive boundary (~7 mm), so AEGIS validity needs the hotspot/proximity distances, not the contact case.

**Archetype 3: fixed 60 GHz device, MPE calculation** (Google Nest Hub Soli, Bureau Veritas). Six pages, Friis formula at 20 cm, "Mobile Device" classification. No simulation market where a device can claim 20 cm separation. This softens the 60 GHz radar beachhead: it is real only for *portable-classified* 60 GHz products (laptop presence radar, wearables, handhelds), not for fixed smart displays, and in-cabin automotive needs case-by-case checking on classification.

**What "rebuild a report" honestly means.** Blindly reproducing Archetype 1 measured values needs the beam codebook, which is not public. Three honest substitutes: (a) model known Qualcomm antenna modules from datasheets/teardowns and check the predicted worst-case PD *envelope* against many filings statistically, (b) reproduce the *simulation reports* inside filings where public, which is apples-to-apples, (c) for Archetype 2 the filing gives antenna type + gain + power + distance, so direct prediction of the reported PD/APD is actually feasible. The product pitch is not "we reproduce your filing", it is "we do the mandatory codebook-times-surfaces-times-distances sweep 100-1000x faster, and it is the sweep FCC already requires you to validate".

**Extraction feasibility:** the reports are versioned lab templates (Sporton, Bureau Veritas format 6.x), highly regular, ideal for LLM extraction at scale. Also every report names its lab and engineers, which feeds the contact list.

**A low-physics quick win spotted in Archetype 1:** the simultaneous-transmission TER bookkeeping (SAR/1.6 + PD/10 summation matrices across antenna pairs, exposure positions, modules) is tabular drudgery labs assemble by hand today. A tool that automates TER analysis from extracted filing data is sellable to labs without any dosimetry engine at all.

## 9. Post-Gemini revision (July 14, 2026)

Gemini Deep Research results in `gemini-response.md`. Caution: it returned **zero source URLs** despite the prompt demanding them, so treat every number as a lead. I independently verified the two strategically load-bearing claims: ISED's codified simulation procedures (RSS-102.SAR.SIM, RSS-102.IPD.SIM; Issue 6 released Dec 2023, SPR-002 rescinded Aug 2025) are real, and SPEAG's Maximum Exposure Optimizer with user-defined codebooks is real and has existed since SEMCAD V19.2, February 2021. Its grant-volume table is a projection with round numbers, its specific FCC ID examples are unverified, and its "Akamai bot manager makes scraping hard" claim is overstated: our own curl pulls fcc.report PDFs with zero friction.

### Revised beachhead ranking

1. **WiFi 6E/7 devices (laptops, tablets, APs, modules).** The volume segment by an order of magnitude (Gemini estimates ~1,200-1,500 grants/yr vs ~150-180 FR2). APD is the reported quantity, antennas are simple, campaign cost 10-30k USD, and the channel is concentrated in three labs (Eurofins Hsinchu, Sporton, Bureau Veritas). This is the beachhead.
2. **XR / smart glasses at 60 GHz + FR2 wearables.** Highest pain per device: portable classification, antennas millimeters from eyes/head, far-field MPE prohibited, 0 mm APD evaluation mandatory. Small filing volume but extreme willingness to pay, and it is exactly the regime where the free-space-PD-vs-APD physics debate lives. Actors: Meta, Apple, HTC.
3. **FR2 phones.** Real money (50-120k USD per campaign) but incumbent-locked: HFSS for Part 0, Qualcomm Smart Transmit workflows, entrenched lab relationships. Enter later via the labs, not the OEMs.
4. **60 GHz radar: demoted to near-zero.** In-cabin automotive CPD is classified mobile (roof-mounted, >20 cm, Friis calc only, per the DA 21-407 waiver cohort). Laptop presence radar is portable but usually test-excluded at its power levels. No simulation market in either.

### New angles the Gemini pass surfaced

- **The EU is the soft entry.** RED compliance is manufacturer self-declaration: if harmonised standards (EN IEC 62311, EN IEC/IEEE 63195-1:2023) are applied, no notified body reviews the file. A simulation report in the technical file is already legally sufficient evidence above 6 GHz. A Belgian company selling "simulation annex for your RED technical file" has no regulatory gatekeeper at all. Use FCC public data for lead-gen (same hardware ships globally), sell the RED+FCC bundle.
- **Canada is the codified-precedent play.** RSS-102.IPD.SIM and RSS-102.SAR.SIM are published regulator-issued *simulation* procedures with uncertainty requirements. Making AEGIS conformant to a named regulator document is cheaper than accumulating FCC KDB case law, and "conforms to RSS-102.IPD.SIM Issue 1" is a checkbox a lab can accept.
- **The APD transition is home turf.** Kuster's own TCB-workshop argument (free-space incident PD is a poor proxy, dielectric loading matters, sPDn+ vs sPDtot+, IT'IS skin model adopted as 63195-3/4 reference) is the industry conceding that the compliance quantity should be absorbed power, which is literally AEGIS's core equation (Sinc -> T0 -> Sab). Tools that natively compute APD fast are scarce; SEMCAD added draft IEC PAS 63446 APD support only in V20.2.
- **First-pass failure economics for the pitch deck:** ~50% first-pass failure (consultant-sourced, verify), 5-30k USD re-test, 4-12 weeks slip, lab queues 2 weeks stretching to 6+ in post-CES and pre-holiday seasons. Also real: FCC stripped accreditation from several foreign-linked labs in 2024-25, contracting cheap capacity and lengthening queues.
- **Pricing confirmed:** the market rate for a pre-compliance simulation sweep is 3-8k USD, exactly the fixed-price report tier in section 4.

### Sharpened threat assessment

SPEAG/ZMT have been attacking the codebook-sweep problem inside SEMCAD since 2021 (MEO, 100x speedup of the PD evaluator in V19.0, phase-uncertainty search). The differentiator is therefore NOT "we can sweep a codebook", it is: 100-1000x cheaper surrogate physics for the *pre-design* loop (placement iteration before CAD freeze, gradients for placement optimization), Python-native automation, and price points a WiFi-6E laptop team or XR startup will pay, versus a 40-100k USD/yr FDTD suite operated by dosimetry specialists. This is consistent with the partnership framing in `honest_analysis.md`: AEGIS upstream of SEMCAD/DASY, not instead of it.

### Immediate actions changed by this

- Scraper filter v1: WiFi 6E/7 portable devices first (equipment class + 5925-7125 MHz), FR2 second, radar dropped.
- Validation corpus v1: predict reported PD/APD for WiFi 6E/7 filings from in-filing antenna data (archetype 2), not FR2 phones.
- Discovery call mix rebalanced: 3 laptop/tablet OEM compliance teams (Lenovo, ASUS, Getac tier), 2 XR (start with HTC, not Meta/Apple), 2 Taiwan labs (Eurofins Hsinchu, Sporton), 1 module maker, 1 consultancy (Eleos or Compatible Electronics as referral channel), 1 ZMT.
- Add ISED RSS-102.SIM conformance to the near-field module spec as an explicit target, it is the cheapest named-standard credential available.

## 8b (renumbered footnote): sub-6 GHz body-worn SAR remains out of scope, and the Gemini data reinforces it: that segment's simulation pathway (RSS-102.SAR.SIM, SAM phantom, FDTD validation burden) is exactly where full-wave incumbents are strongest.

## 10. Competitor sighting: markready.io (July 14, 2026)

MarkReady is building the "Use 3" intelligence layer on public FCC data: FCC database search, lab finder (591 labs), requirements checker, permissive-change analyzer, SAR/MPE *classifier* (does my device need testing), cost estimator, multi-market mapper. Tagline: "Hardware certification shouldn't require a $500/hr consultant." Status as of today: every tool is "Coming Soon", no pricing, no named team, no funding trail, SEO content dated April-May 2026. Reads as a recently launched, likely AI-built, audience-first solo effort. They have ingested EAS metadata (50,153 grantees, ~50 new filings/day tracked) but show no sign of parsing report PDFs for measured values, and nothing physics-shaped is on the roadmap: their classifier answers "do you need testing", not "will you pass".

Implications: (a) independent validation that the public-FCC-data wedge is real and the window is now; (b) the generic compliance-navigation product is confirmed low-moat, do not build it as the company; (c) the measured-values extraction layer and everything physics-side is still open; (d) their future audience is our lead pool, a referral/partner motion ("classifier says you need PD evaluation -> get a simulated pre-screen") is plausible later; (e) for the IOF valorisation section this is a gift: a competitor map with MarkReady in the navigation corner, SPEAG/ZMT in the expensive-full-wave corner, and an empty "fast physics prediction" quadrant is exactly the story a jury understands.

## 11. Price sheet and process facts mined from markready.io guides (July 14, 2026)

Treat MarkReady as a data source, not a competitor (Robin's call, correct). Their guides are uncited but cross-corroborate the Gemini numbers on failure rates, queue seasons, and costs. Key extractions:

**The headline insight: in RF exposure, pre-compliance IS simulation.** For EMC emissions, pre-compliance is a commodity: rent a chamber day for $500-2,000 and measure. For SAR/PD there is no cheap rental equivalent, the measurement rig is a DASY-class robot system only labs own. So the "spend $500-2,000 to avoid $5,000-30,000" pre-compliance economics that MarkReady documents for EMC can only be delivered *by simulation* in the RF exposure domain. AEGIS's price anchor is the chamber-day rate, and the competition at that price point is literally nothing.

**Failure economics (their numbers):** ~50% first-pass failure for teams that skip pre-compliance vs under 10% for those who invest. Re-test $2,000-10,000 fees plus $1,000-15,000 engineering plus 4-12 weeks. Complex products with multiple retests: $10,000-30,000.

**SAR/exposure price sheet:** SAR campaigns $3,000-30,000 (BLE wearable $3-5k, WiFi laptop $5-8k, multi-band phone $10-15k+, cellular IoT wearable $5-10k). Adders: $1-2k per extra band, $2-3k per extra body position. SAR re-test $3-8k. RF exposure exemption *paperwork* (the Nest-Hub-style MPE calc) sells for $500-2,000, that is the floor price for a trivial deliverable. Host-device residual testing with a pre-certified module totals $2,500-5,500, of which RF exposure evaluation is $500-2,000 (KDB 447498).

**Positioning consequence:** the 3-8k EUR fixed-price report targets *escalated* cases (portable classification triggered, antenna moved, margins tight, PD/APD regime), not the $500 paperwork tier. Do not compete for exemption calcs.

**Timeline levers worth selling against:** labs booked 3-6 weeks ahead (6-8 in peak Jan-Mar / Jul-Sep), report prep 1-3 weeks with a +25-50% expedite surcharge, each TCB deficiency cycle adds 3-7 days. Certification single-band typical 8-12 weeks end to end.

**Regime confirmation:** "The original device configuration must have measured SAR data from a physical test", simulation covers variations relative to a measured baseline (cases, accessories, minor changes). Consistent with the hybrid regime from the filings. Also: their SAR guide contains *zero* above-6-GHz / APD content. The best free content source in the space has a hole exactly where AEGIS lives, which both confirms scarce expertise and marks the SEO/authority opening for a "state of >6 GHz compliance" note.

## 8. The problem you didn't formulate

The April analysis identified the real bottleneck: zero discovery calls, analysis paralysis. This plan is shaped to attack that. A cold call is terrifying, but "we reproduced your public filing and predicted your measured value" is not a cold call, it is a gift with a phone number attached. The scrape-then-validate sequence exists to make the first ten conversations easy to start. If the scrape and validation are done and the ten emails still have not gone out by day 60, that is the kill signal the April doc asked for, arriving early and cheap.
