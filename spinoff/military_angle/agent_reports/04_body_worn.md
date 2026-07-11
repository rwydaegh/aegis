# Body-worn military RF exposure as an AEGIS beachhead

Agent report, 2026-07-09. Answers the orchestrator's body-worn hypothesis against the shared brief.

## 1. Verdict

Dead on the sub-6 GHz physics: every body-worn military emitter category sits at or below 6 GHz, which is exactly the band where AEGIS's surface method is invalid and its millisecond speed disappears, so the one thing AEGIS uniquely sells does not apply, and the problem is already assessed by the US Army as low hazard and already served by full-wave FDTD that is the correct tool for this volumetric regime.

## 2. The three things that most changed my view

1. **The whole category ceilings out at ~6 GHz, and that is a hard wall, not a soft one.** Manpack radios are 30 MHz to 2 GHz (AN/PRC-117G) or 30-512 plus 762-870 MHz (AN/PRC-152). Body-worn and handheld counter-drone jammers run 200 MHz to 6 GHz, topping out at the 5.8 GHz WiFi/FPV band (DroneBuster, MyDefence Pitbull). Ukrainian EW backpacks (Kvertus) sit at 720-1050 MHz. CREW counter-RCIED jammers are broadband but target cellular/VHF/UHF/L/S triggers, all sub-6. There is no common body-worn-against-the-body emitter above 6 GHz. AEGIS's surface law is validated **above** ~6 GHz. The bands do not touch. Sources: [AN/PRC-152 Wikipedia](https://en.wikipedia.org/wiki/AN/PRC-152), [AN/PRC-117 Wikipedia](https://en.wikipedia.org/wiki/AN/PRC-117), [DroneBuster / unmannedsystemstechnology](https://www.unmannedsystemstechnology.com/expo/drone-rf-jammers/), [MyDefence Pitbull](https://mydefence.com/products/pitbull-drone-jammer/), [Euromaidan Kvertus backpack](https://euromaidanpress.com/2024/05/17/the-ew-backpack-revolution-how-ukrainian-portable-tech-jams-russian-drones/).

2. **The US Army already assessed this and said there is no hazard, and the establishment is already modeling it with the right tool.** The Army Public Health Center fact sheet on RF from electronic countermeasures states that for portable jammers carried by dismounted soldiers, "RFR overexposure is a rare occurrence as these systems have reliable safety procedures to prevent overexposure," that "when maintaining a stand-off distance while the system is on, there is no health hazard," and that "there is no expectation of adverse health effects to users of these systems." Independently, an Italian Army (CEPOLISPE) plus Sapienza group published a 2025 Sim4Life FDTD study of body-proximity military antennas on the Duke phantom **with helmet and headset**, at 16-351 MHz, 20-50 W, and found whole-body SAR 0.06 W/kg and peak head SAR 0.99 W/kg, both far under limits. The problem is real, documented, and already handled by full-wave FDTD, which is the physically correct method below 6 GHz. Sources: [APHC electronic countermeasures fact sheet](https://ph.health.mil/resources/exposure_to_rf_radiation_from_electronic_countermeasures.pdf) (fetched via search snippet, see caveats), [Colella et al., Frontiers Public Health 2025](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2025.1620240/full).

3. **The civilian mirror does not transfer, because the two cases are in different bands and therefore different physics regimes.** Robin's funded civilian beachhead is IEC/IEEE 63195-2, whose scope is defined as **6 GHz to 300 GHz**, and the keystone validation is a near-field mmWave device against Sim4Life. Body-worn military is all sub-6. A 28 GHz phone validation says nothing about a 900 MHz manpack radio, because at 900 MHz energy penetrates volumetrically and the surface law is simply the wrong model. So the attractive "one experiment de-risks both the civilian beachhead and a military entry" claim is false for the body-worn case. Source: [IEC/IEEE 63195-2 scope](https://ieeexplore.ieee.org/document/9770556).

## 3. What I verified, inferred, could not check

**Verified (primary or datasheet):**
- Manpack radio bands and powers (Wikipedia + L3Harris datasheets): PRC-152 30-512 + 762-870 MHz, 5 W line of sight, 10 W SATCOM; PRC-117G 30-2000 MHz.
- Body-worn counter-drone jammer bands: DroneBuster 200 MHz-6 GHz; MyDefence soldier kit (Wingman + Pitbull) ~2.5 kg vest-worn; Kvertus Ukrainian backpack 720-1050 MHz protecting an 8-10 soldier unit off one operator for ~2 h continuous.
- Frontiers 2025 vehicular-antenna study: full authorship (Sapienza + Italian Army CEPOLISPE + Larimart), Sim4Life FDTD, Duke phantom with PPE, HF/VHF/UHF 16-351 MHz, 20-50 W, SAR values above.
- MDPI 2022 review (PMC8776107): covers body-worn "radio station placed on the backpack of the soldier, rod antenna," reports SAR1g of 0.0252 W/kg at 1.575 GHz and 0.175 W/kg at 915 MHz at 1 W, concludes "only occasional situations of overexposure," and names an explicit gap: "a real need to increase EMF exposure assessment studies in military working conditions," with "particular deficiencies regarding jammer exposure and future 5G technologies."
- SBIR DHA211-005 "Wearable RF Weapon Exposure Detector" is a **hardware indicator** (MOLLE-mounted, M4-magazine-sized, UHF through Ka) for incoming directed-energy weapons, funded by the Defense Health Agency. Not a modeling tool and not for self-exposure.
- Army body-wearable antenna SBIR requires compliance shown by "actual SAR measurements, in each of the six radio frequency bands," under FCC/OSHA occupational limits: measurement, not software.
- IEC/IEEE 63195-2 computational near-field power-density scope is 6-300 GHz.
- Ka-band manpack SATCOM terminals exist (Get SAT, Requtech PICO75) at ~20-30 GHz, ~3.4 kg, man-carried.

**Inferred:**
- CREW jammer (Duke, CVRJ, Thor III, Guardian) exact bands are not public, but the RCIED threat set (cellular, ISM, VHF/UHF remote controls) is entirely sub-6, so the emitters are sub-6. Reasonable but not certified by a datasheet.
- Ka manpack SATCOM antennas point at the satellite (skyward, away from the body) and are deployed on the ground while transmitting, so they are not a near-field-against-the-spine geometry. Inferred from how these terminals operate, not from an exposure study.

**Could not check:**
- Full text of the APHC electronic-countermeasures fact sheet. The ph.health.mil PDF failed on a TLS certificate error and the phc.amedd mirror timed out. The quoted conclusions are from the search engine's extract of that exact PDF, so treat them as high-confidence but not personally page-verified. NEEDS_CONTEXT if an exact citation is required for a proposal.
- Reddit practitioner sentiment. The Reddit MCP returned HTTP 403 on every call this session and site-scoped web search surfaced no threads. I could not confirm whether EW operators worry about self-exposure in their own words. Weakly suggestive of low salience, not conclusive.

## 4. Body

### 4.1 The band question kills the speed trick (item 2, attacked first per the brief)

The brief's own band map says the surface method's millisecond speed survives only where skin depth is sub-millimetre, roughly above 6 GHz. Below that the planner transfers but the speed does not. Every body-worn category I could find lives entirely below 6 GHz:

| Category | Example | Band | Power | Regime |
|---|---|---|---|---|
| Manpack tactical radio | PRC-117G, PRC-152 | 30 MHz-2 GHz | 5-20 W | Volumetric, sub-6 |
| CREW counter-RCIED jammer | Duke, CVRJ, Thor III | VHF/UHF/L/S (sub-6) | tens to hundreds W (unverified) | Volumetric, sub-6 |
| Body-worn counter-drone | Pitbull, DroneBuster | 200 MHz-6 GHz | tens W | Volumetric, sub-6 |
| Ukrainian EW backpack | Kvertus | 720-1050 MHz | ~2 h continuous | Volumetric, sub-6 |

At 900 MHz the free-space wavelength is 33 cm and the tissue skin depth is centimetres. Absorption is a 3D volumetric process, not a surface phenomenon. AEGIS's `S_ab = S_inc T0 ReLU[...]` surface integral is not merely slower here, it is the wrong equation, and the brief already concedes this. The physically correct tool is exactly what the incumbents already use: FDTD in Sim4Life, which the Italian Army group ran on Duke to close this precise question in 2025.

There is one technically-above-6 body-worn candidate: Ka-band manpack SATCOM terminals (~20-30 GHz). It fails on geometry, not band. The dish points at the satellite, away from the operator, and transmits when set down, not while strapped to a spine. It is not the near-field-against-the-body regime the hypothesis needs. I found no exposure study treating it as one.

### 4.2 The single-antenna problem kills the coherent value (independent of band)

Even if a body-worn emitter were above 6 GHz, AEGIS's crown jewel is the exposure operator `Q` for an `M`-element coherent array, where `xᴴQx` and `λ_max(Q)` answer worst-case-over-all-beams questions. A body-worn radio or jammer is a **single antenna**. There is no excitation vector `x` to optimize, no beam to bound, no `Q` worth eigendecomposing. Findings A and B in the brief (the certifiable envelope, the VOP precedent) are both about bounding a controllable array. They have nothing to grip on a one-element emitter. So the coherent machinery, which is the actual differentiator, is inert here. What remains is a scalar near-field absorption calc that Sim4Life already does, more correctly, below 6 GHz.

### 4.3 Is the problem real and documented? Yes, and that cuts against us

The evidence that the problem is real is strong, and it is the same evidence that shows it is already owned:

- APHC has a standing Health Hazard Assessment process and a published fact sheet specifically on dismounted-soldier jammers, concluding low hazard with standoff.
- The MDPI 2022 review documents body-worn backpack radios explicitly and finds mostly-compliant SAR, while flagging jammers and 5G as understudied.
- The Frontiers 2025 study is a live, funded, military-academic effort doing body-proximity dosimetry with FDTD.
- The 2025 Military Medicine narrative review on RF thermal effects in military contexts exists but discusses no body-worn systems at all, treating the topic at the level of general radar and HPM bands.

"Understudied" in the MDPI review is real, but it is a call for **more FDTD studies of the volumetric internal field**, not for a fast surface tool. AEGIS answers a question (surface APD at mmWave) that this literature is not asking.

### 4.4 Who pays? A buyer exists, but not for this deliverable

There is documented willingness to spend on soldier RF exposure, and it points away from AEGIS every time:
- DHA SBIR DHA211-005 buys a **hardware** wearable detector for incoming RF weapons, not a self-exposure model.
- Army body-wearable antenna SBIRs mandate compliance by **physical SAR measurement** in each band, not simulation.
- HERP verification under MIL-STD-464D is a small budget line even at platform scale (the brief's own finding), and for a single body-worn emitter it is discharged by the APHC standoff-distance assessment and signage, which is cheap and already exists.

No procurement notice, SBIR topic, or program office I found is asking for fast software surface dosimetry of a body-worn emitter. The closest real money (detectors, measurement) is for things AEGIS does not build.

### 4.5 Body armour and kit: harder than AEGIS can do, not easier (item 5)

The plate carrier, helmet, rifle, and the radio body itself are conductive and dielectric scatterers. In the reactive near-field (10-20 cm) of a sub-6 GHz antenna, the plate is sub-wavelength and resonant, and the coupling is dominated by reactive fields and multiple bounces. AEGIS's multi-body occlusion (claim 12) is a far-field visibility/shadow gate. It answers "does surface patch A see the source past body B," not "how does a resonant conductive plate reshape the reactive near-field standing wave." First-bounce physical optics (assumption A2) structurally omits exactly the multi-bounce and edge/creeping-wave terms that dominate here. So body armour makes the problem a full-wave problem, which is the incumbents' turf, not AEGIS's. This is the honest answer even setting the band issue aside.

Note on claim 8 (the near-field point-source extension): it fixes the **incident-field geometry** (a proper solid-angle view factor instead of a plane-wave assumption) but leaves the **absorption law** a surface/skin-depth model that is still only valid above 6 GHz. Claim 8 addresses the wrong half of the body-worn problem. The half that breaks is the volumetric absorption, which no incident-field improvement can rescue below 6 GHz.

### 4.6 Ethics and scope

Clean. This is personnel-protection and compliance for already-fielded, mostly-defensive systems (counter-IED, counter-drone, comms). No targeting or lethality work is implied. The dual-use tension the brief names (making an emitter legally operable closer to humans also raises its permitted duty cycle) is present in principle but muted here, since the finding is that AEGIS adds nothing over the existing standoff-distance method for these single-antenna sub-6 emitters.

## 5. What would kill this (falsifiable, one week)

The verdict is already the kill. To try to **revive** it, someone would have to find, within a week, a real fielded or funded body-worn military emitter that is (a) above 6 GHz, (b) a multi-element phased array, and (c) transmitting with its main beam toward or across the wearer's body, such that a coherent `Q` bound with a real human in the near field is the deliverable a program office wants. Search the SBIR/STTR topic database, EDF and EDA CapTech calls, and Ka/mmWave body-worn data-link and 5G-tactical-node programs. If no such emitter exists (my strong expectation, since body-worn mmWave arrays pointed at the wearer are close to a contradiction in terms), the beachhead stays dead. A single counter-example flips it back to conditional.

## 6. Single highest-value next action

Drop body-worn as a standalone beachhead and fold its one genuinely transferable asset into the civilian mmWave plan. The only near-field, above-6-GHz, multi-antenna geometry with a real buyer is a Ka-band or mmWave **platform-mounted** array with crew in open hatches (the ship/vehicle SATCOM-on-the-move case), which is the ship study's territory, not a soldier's. The action for Robin: when scoping the IEC 63195-2 near-field validation against Sim4Life for the civilian device play, run it once at a Ka-band SATCOM frequency (~20-30 GHz) as well, so the same de-risking experiment also covers the above-6 platform-crew military case. That reuses the funded experiment for a military-adjacent entry without touching classified geometry or the dead sub-6 body-worn category. Owner: Robin, inside the existing IOF de-risking task, no new partner or clearance required.

---

### Sources

- AN/PRC-152, AN/PRC-117 specs: https://en.wikipedia.org/wiki/AN/PRC-152 , https://en.wikipedia.org/wiki/AN/PRC-117
- CREW Duke / CVRJ: https://www.l3harris.com/all-capabilities/crew-vehicle-receiver-jammer-cvrj , https://www.srcinc.com/products/ew-spectrum-operations/crew-duke.html
- Body-worn counter-drone: https://www.unmannedsystemstechnology.com/expo/drone-rf-jammers/ , https://mydefence.com/products/pitbull-drone-jammer/
- Ukraine EW backpack: https://euromaidanpress.com/2024/05/17/the-ew-backpack-revolution-how-ukrainian-portable-tech-jams-russian-drones/ , https://www.forbes.com/sites/vikrammittal/2025/07/29/russia-is-developing-a-new-soldier-worn-counter-drone-jammer/
- APHC electronic countermeasures fact sheet: https://ph.health.mil/resources/exposure_to_rf_radiation_from_electronic_countermeasures.pdf
- Frontiers 2025 vehicular antenna FDTD study (Sapienza + CEPOLISPE): https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2025.1620240/full
- MDPI 2022 military occupational RF review: https://pmc.ncbi.nlm.nih.gov/articles/PMC8776107/
- Military Medicine 2025 RF thermal review: https://academic.oup.com/milmed/advance-article/doi/10.1093/milmed/usaf613/8404557
- SBIR DHA211-005 wearable RF weapon detector: https://www.highergov.com/contract-opportunity/wearable-radio-frequency-weapon-exposure-detector-dha211-005-sbir-e13d0/
- Army body-wearable antenna SBIR (SAR measurement requirement): https://legacy.www.sbir.gov/node/870603
- IEC/IEEE 63195-2 (6-300 GHz near-field PD): https://ieeexplore.ieee.org/document/9770556
- Body-worn SAR near-field study (30-5800 MHz): https://pubmed.ncbi.nlm.nih.gov/17652110/
- Ka manpack SATCOM terminals: https://www.getsat.com/satcom-solutions-for-any-mission/manpack/ , https://requtech.com/satcom-terminals/manpack-satcom-terminals/
