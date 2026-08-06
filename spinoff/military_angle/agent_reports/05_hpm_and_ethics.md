# HPM, non-lethal mmWave, and the ethics fork

Agent report 05. Written 2026-07-09. Reads `AGENT_BRIEF.md` as ground truth and attacks it.

## 1. Verdict

The pulsed/fluence gap is a small integrator, not new physics, but it is almost worthless because the only fielded high-power system that sits in AEGIS's valid band (>6 GHz) is the 95 GHz Active Denial family, which is continuous-wave skin heating with no pulse-fluence problem at all, so in HPM the surface-speed story is dead and only the planner and a possible ADS-class safety-of-effect play survive, both of which are fundable in Flanders and EU defence money only if scoped hard to personnel protection.

## 2. The three things that most changed my view

1. **The brief's Leonidas numbers are wrong, and the error matters.** Epirus Leonidas is a **GaN solid-state, long-pulse** system, not a 450 MW / 20 ns / 50 Hz single-shot emitter. Solid-state GaN amplifiers physically cannot make 450 MW in a 20 ns pulse. That figure describes a **vircator/Marx-generator** class weapon (the "traditional HPM" the sources explicitly contrast Leonidas against). This changes sub-question 1: the flagship counter-drone systems are not even in the extreme-peak-field regime the brief worries about. Sources: [semiconductor-today](https://www.semiconductor-today.com/news_items/2025/sep/epirus-300925.shtml), [New Atlas](https://newatlas.com/military/microwave-beam-anti-drone-weapon/), [TWZ](https://www.twz.com/land/army-puts-50m-bet-on-next-gen-leonidas-high-power-microwave-counter-drone-tech).

2. **Above 6 GHz there is essentially one fielded high-power counter-personnel system, and it is CW.** The 95 GHz Active Denial System (and its Raytheon "Silent Guardian" commercial twin) is the only mmWave directed-energy anti-personnel system that has been fielded/demonstrated, and it is a **continuous-wave gyrotron heater**, roughly 100 kW, not a pulsed HPM. Every pulsed HPM counter-drone weapon (Leonidas, THOR, Mjolnir, Thales ThunderShield, UK RFDEW) sits at **1 to 4 GHz**, where AEGIS's surface method is invalid. So the pulsed-fluence integrator and the surface-speed trick never apply to the same system. Sources: [Wikipedia ADS](https://en.wikipedia.org/wiki/Active_Denial_System), [THOR Wikipedia](https://en.wikipedia.org/wiki/THOR_(weapon)), [Thales ThunderShield](https://www.thalesgroup.com/en/solutions-catalogue/defence/thundershieldtm-high-power-microwave-electromagnetic-neutralisation).

3. **Flanders now has an explicit defence funding line, and the civil/defence funding split is exactly as the brief warned.** VLAIO's Flemish Defence Plan openly funds dual-use civil-and-defence projects, but Eurostars and the classic civil instruments still bar "research with military affinity," and Horizon Europe remains civil-only until at least FP10 (2028). EDF funds defence but not weapons prohibited under international law or lethal autonomous weapons. HPM counter-drone is a legal, non-LAWS weapon, so it is EDF-eligible and now VLAIO-defence-eligible, but not Horizon-eligible. Sources: [VLAIO/Blue Cluster defence call](https://www.bluecluster.be/news/innovation-for-defense-help-build-a-safer-future), [Horizon Europe civil-focus guidance note](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/guidance-note-research-focusing-exclusively-on-civil-applications_he_en.pdf), [Nature on Horizon staying civil](https://www.nature.com/articles/d41586-025-03221-2), [Article36 on EDF weapon limits](https://article36.org/wp-content/uploads/2024/04/european-defence-fund-autonomous-weapons-1.pdf).

## 3. What I verified, inferred, and could not check

**Verified from primary or strong secondary sources:**
- ICNIRP 2020 and IEEE C95.1-2019 both add per-pulse **fluence limits** above 6 GHz, on the order of **200 to 400 kJ/m²** for single pulses over a **1 cm²** area (30 to 300 GHz), on top of the 6 minute, 4 cm² CW power-density limit ([PMC8300848](https://pmc.ncbi.nlm.nih.gov/articles/PMC8300848/)).
- ICNIRP 2020 short-interval (<6 min) local restriction above 6 GHz is expressed as **absorbed energy density Uab**, with the operational adverse-effect threshold for 30 to 300 GHz over 1 cm² given as **Uab = 144[0.025 + 0.975(t/360)^0.5] kJ/m²** (t in seconds), reduced by a factor of 10 for the occupational basic restriction ([Health Physics / McGarr et al.](https://www.researchgate.net/publication/360864834), [ICNIRP differences page](https://www.icnirp.org/en/differences.html)).
- IEEE C95.1-2005 sets a **maximum instantaneous peak E-field of 100 kV/m** ([Interference Technology overview](https://interferencetechnology.com/overview-c95-1-2005-ieee-standard-safety-levels-respect-human-exposure-radio-frequency-electromagnetic-fields-3-khz-300-ghz/)).
- Microwave-auditory (Frey) perception threshold is roughly **0.4 to 2 mJ/cm² per pulse** (≈4 to 20 J/m²) for low-GHz pulses ([Frontiers, PMC8733248](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8733248/)).
- ADS safety case: **~10,000 volunteer exposures**, independent **Penn State Human Effects Advisory Panel**, second-degree blistering in **<0.1%** of exposures ([HandWiki ADS](https://handwiki.org/wiki/Engineering:Active_Denial_System), [W&M PIPS report](https://www.wm.edu/offices/global-research/_documents/pips/ADS.Report.Final.6.28.2013.Printer.pdf)).
- Belgian dual-use export licensing is a **Flemish regional competence**, run by the **Strategic Goods Control Unit** of the Flanders Chancellery and Foreign Office (FDFA), under EU Reg 2021/821 plus a Flemish decree ([FDFA Strategic Goods Control](https://www.fdfa.be/en/peace-security/strategic-goods-control), [FDFA on the Flemish Defence Plan](https://www.fdfa.be/en/strategic-goods-control-in-the-flemish-defence-plan-accelerate-where-possible-protect-if-necessary)).
- UGent has a formal **Dual-use Contact Point**; any project involving defence funding, the military, or export of controlled dual-use tech must be reported to it and pass ethics review ([UGent research framework](https://www.ugent.be/en/research/framework)).

**Inferred (reasoned, not directly sourced):**
- Leonidas's real per-pulse energy is far below the vircator numbers in the brief, so its peak fields never approach breakdown at human standoff (calculation in section 4.1).
- IOF StarTT money is UGent valorization funding with no explicit defence bar found, but its civil-innovation framing makes a defence-labelled application a poor fit. Treat as civil-only in practice until UGent TechTransfer confirms otherwise.

**Could not check:**
- The specific **~100 ms reference-window** clause the brief attributes to C95.1-2345. I confirmed the per-pulse fluence limit and the 100 kV/m peak-E limit, but I could not verify a named 100 ms averaging window. **Marked unverified.** The full C95.1-2345-2014 and C95.1-2019 normative text sits behind the IEEE/ANSI paywall.
- **Reddit practitioner sentiment.** The reddit MCP returned HTTP 403 on every call this session. Not retrieved. `NEEDS_CONTEXT:` if practitioner opinion on defence-funded academia is wanted, the reddit tool needs auth fixed.
- Exact THOR/Leonidas operating frequencies are not public. The 1 to 4 GHz band placement is from secondary defence reporting, not a spec sheet.

## 4. Body

### 4.1 The pulsed / fluence gap: an integrator, plus a bioheat model, plus a band you cannot use

**What the standards actually require.** Two limits stack above 6 GHz:
- A time-averaged power-density / absorbed-power-density limit over 4 cm² and 6 minutes (the CW limit AEGIS already computes).
- A **per-pulse fluence limit**: energy density in any single pulse, group, or subgroup must not exceed roughly 200 to 400 kJ/m² incident (over 1 cm², 30 to 300 GHz), and for exposures shorter than 6 minutes ICNIRP caps absorbed energy density Uab by the 144[0.025 + 0.975(t/360)^0.5] kJ/m² curve. There is also the C95.1 instantaneous-peak-E ceiling of 100 kV/m.

**Which of these is "AEGIS plus an integrator"?** All three of the *field-level* ones:
- Per-pulse fluence is just S_ab integrated over the pulse. Because S_ab is homogeneous of degree 1 in incident power and linear per triangle, energy-per-pulse = S_ab_peak x pulse-width, and windowed energy = S_ab_peak x (pulses in window x pulse-width). AEGIS already has time-averaged APD, so a sliding-window energy accumulator plus a second limit table is a **small module**, not new physics.
- Peak incident E-field is already sitting in the coherent field channel (|E| per triangle). Comparing it to 100 kV/m is trivial.
- Absorbed energy density Uab over 1 cm² is the same surface integral against a different averaging area.

So at the **field and fluence** level, the pulsed regime is a genuine but shallow gap: an integrator and a limits table. This is the honest good news.

**Where AEGIS genuinely cannot go without new physics:**
- **Temperature, not energy.** The ICNIRP thresholds are anchored to tissue reaching 41 C, and the ADS safety margin is a *temperature-versus-time* story. Energy density does not give temperature without a **Pennes bioheat solve** (conduction, perfusion, the thermal time constant). AEGIS has no bioheat layer. This is a real, named gap and it is the one that actually matters for effect.
- **Microwave hearing (Frey effect).** Threshold ~0.4 mJ/cm² per pulse looks like a fluence quantity AEGIS could feed, but the mechanism is **thermoelastic**: rapid heating launches a pressure wave that reaches the cochlea. It needs a thermoelastic-acoustic model inside the head, not a surface APD, and it is a head-interior effect. Off the surface method entirely.
- **Membrane electroporation / nsPEF.** Only relevant at extreme peak fields, and here is the physics point the brief asked for: **at 1 GHz the classic electroporation mechanism is inaccessible.** A cell membrane is a low-pass filter with a charging time of order microseconds. At GHz the field reverses long before transmembrane potential can build, so the membrane is capacitively shorted and no poration occurs. The only pathway left is heating. So even at very high peak power, the sub-6-GHz HPM weapons do their biological work thermally, which loops back to bioheat.

**Does the field break down linear dielectrics at 450 MW?** I computed it. Take the brief's notional vircator: 450 MW peak, L-band 1.1 GHz (λ = 0.27 m), a ~1 m² aperture (effective area ~0.5 m², gain ~84, ~19 dBi), peak EIRP ≈ 3.8 x 10^10 W. Free-space peak power density S = EIRP/(4πR²), peak field E = sqrt(2 η0 S) with η0 = 377 Ω:

| Range | Peak S (W/m²) | Peak E (kV/m) | vs limits |
|---|---|---|---|
| At aperture (~P/A) | 4.5 x 10^8 | ~580 | 0.19x air breakdown, 8x the 100 kV/m MPE |
| 10 m (near field) | 3.0 x 10^7 | ~150 | 1.5x the 100 kV/m MPE |
| 25 m | 4.8 x 10^6 | ~60 | below the MPE |
| 100 m | 3.0 x 10^5 | ~15 | well below |

Reference thresholds: **air dielectric breakdown ~3 MV/m** (30 kV/cm at sea level), **nanosecond-pulse tissue electroporation ~1 to 10 MV/m**, **C95.1 instantaneous peak MPE 0.1 MV/m**.

Reading: even at the aperture face of a full vircator-class emitter, the peak field (~0.58 MV/m) is about **one fifth of air breakdown** and **roughly a tenth of the nsPEF regime**, and at any human-relevant standoff (>10 m) it is an order of magnitude below both. **Linear tissue dielectrics and the Fresnel description hold everywhere a person could plausibly stand.** The field only flirts with breakdown at the emitter face, which is not an exposure geometry and is exactly where the plane-wave-per-triangle assumption also fails, so it is doubly outside AEGIS. The brief's worry about non-linear breakdown is, on the numbers, **not triggered**. The binding constraints in the pulsed regime are the *regulatory* peak-E and fluence limits, both linear, both integrator-friendly.

**The catch that kills the value.** Every number above is only computable by AEGIS's surface method **above 6 GHz**. The pulsed HPM weapons are at 1 to 4 GHz. There AEGIS's surface APD is invalid, so the integrator has nothing valid to integrate. The one place the integrator is valid (>6 GHz, ADS-class) is CW, where there is no pulse-fluence problem. **The gap is easy to fill and the fill has almost no valid market.** That is the finding, and it is worse for the thesis than the brief implies.

### 4.2 The band problem: above 6 GHz, the shelf is nearly empty

Systematic pass over fielded and emerging high-power systems:

| System | Band | Regime | AEGIS surface valid? |
|---|---|---|---|
| Epirus Leonidas | ~1 to 4 GHz (multi-band, long-pulse) | Volumetric | No |
| AFRL THOR / Mjolnir | low GHz (~S-band reported, unconfirmed) | Volumetric | No |
| Thales ThunderShield, UK RFDEW | low GHz | Volumetric | No |
| Boeing CHAMP | L/S band (classified) | Volumetric | No |
| Russian UIMC microwave gun | "super-high-frequency" (unspecified) | Likely volumetric | Unknown |
| X-band fire-control / nav radar | ~10 GHz | Skin regime returning | Yes (but not weapons, and average power modest) |
| Ka-band / W-band EW jammers, seekers | 30 to 95 GHz | Skin | Yes, but low power, not anti-personnel |
| **95 GHz Active Denial System / Silent Guardian** | 95 GHz | **Skin, CW** | **Yes** |

The honest conclusion: **the only fielded high-power anti-personnel system in AEGIS's valid band is the ADS family, and it is CW.** X-band radars are in-band but they are sensors, not weapons, and platform tools like FEKO already own that RADHAZ zone. Ka/W-band EW hardware is in-band but not high enough power to be a personnel-injury weapon. So AEGIS's millisecond surface speed, in the directed-energy weapon world, has a market of essentially one system class (ADS and successors) plus the general **exposure-constrained planner**, which transfers to any band because it only needs field linearity in the excitation. **Say it plainly to Robin: in HPM, the surface-speed pitch is dead, and only the planner and a narrow ADS-class safety-of-effect role survive.**

### 4.3 Safety-of-effect for the Active Denial System: real, owned by others, and ethically double-edged

**How ADS safety is actually certified.** Not by simulation. By roughly 10,000 human volunteer exposures at Kirtland/Brooks, bioeffects work by AFRL's Human Effectiveness Directorate (now 711th Human Performance Wing), and independent review by a Penn State Human Effects Advisory Panel. The safety case is behavioural: the escape reflex (nociceptor firing at ~44 to 54 C in the top 0.4 mm of skin) fires seconds before a burn threshold, and the beam intensity and dwell are capped so the burn is not reached. Second-degree blistering occurred in <0.1% of exposures. The physics that sets that pain-versus-burn margin is exactly what AEGIS models: incident angle (Fresnel), skin curvature and orientation (the ReLU projection), and dwell. What AEGIS is *missing* is the temperature layer that turns absorbed surface power into a 44 C-versus-burn timeline. That is bioheat again.

**Would a validated fast surface model plus a bioheat layer reduce human testing?** In principle yes: the exposed variables (skin thickness, sweat, clothing, angle, curvature, duration) are precisely the ones a fast surface-plus-bioheat model spans, so it could **replace much of the parametric human-subject sweep** and reduce the count and severity of live exposures. This is a genuinely attractive, ethically defensible framing.

**Who owns the problem, and would they pay.** ADS safety is owned by the **US DoD Joint Non-Lethal Weapons Directorate (JNLWD)** with AFRL bioeffects. That is a US government customer, unreachable for a Belgian spin-off with no clearance and no US partner. The buyers you could actually reach are (a) EU non-lethal / counter-personnel programs if any mature, and (b) the manufacturers of ADS-class hardware (Raytheon/RTX for Silent Guardian). Neither is in reach today. So the ADS safety-of-effect play is real physics-market fit but **customer-inaccessible from where Robin sits**, which is a harder wall than the brief credits.

**The double reading, unresolved as required.** Reading one: a validated model that reduces human-subject exposure testing is ethically defensible and is squarely personnel-protection. Reading two: the identical model, by tightening the pain-versus-burn margin, makes the weapon **usable at higher duty cycle and shorter standoff** because the operator can prove the burn threshold is not reached. That is effectiveness engineering wearing a safety badge. **I am not resolving this for Robin.** I am flagging that the same deliverable reads as both, and that the scoping language ("never effectiveness or targeting") does not by itself prevent the second reading, because a tighter safety envelope is mechanically a wider operating envelope. This is the sharpest ethics point in the study and section 4.4 takes it up.

### 4.4 The ethics fork, stated properly

**The constraints, verified.**
- **Belgian export control is Flemish, not federal.** Confirmed. Dual-use and military export licensing for a Ghent-based entity runs through the Flemish **Strategic Goods Control Unit** (FDFA), under EU Reg 2021/821 plus the Flemish decree of Dec 2025. Federal government does not license this. So Robin's control counterpart is Brussels-Flemish, and Flanders actively rejects licences over diversion risk (7 rejected in 2024). Practically: any AEGIS build that becomes a controlled dual-use item needs a Flemish export licence, and Wout/TechTransfer would route it through the Flemish unit.
- **EU Reg 2021/821** controls export/brokering/technical-assistance of dual-use items and adds a catch-all for non-listed items where the exporter suspects military or WMD end-use. A dosimetry solver is plausibly EAR99-equivalent / uncontrolled as software, but *coupling it to a weapon-effectiveness deliverable* raises the catch-all risk.
- **Horizon Europe is civil-only** (guidance note requires exclusive focus on civil applications) until the FP10 dual-use opening proposed for 2028. **EDF explicitly funds defence** but excludes weapons prohibited under international law and lethal autonomous weapons. HPM counter-drone is neither, so it is EDF-eligible.
- **VLAIO** now has a Flemish Defence Plan funding dual-use civil-and-defence projects, but the civil instruments and **Eurostars still bar "research with military affinity."** So money exists on both sides of the wall, but you cannot mix a defence deliverable into a civil grant.
- **IOF StarTT** is UGent valorization money. No explicit defence bar found, but it is civil-innovation framed. Treat any defence-labelled scope as out of bounds for IOF until TechTransfer says otherwise. **Unverified, inferred.**
- **UGent** requires everything defence- or dual-use-touching to go through its Dual-use Contact Point and ethics review. This is a gate, not a bar.

**The narrowest fundable-and-defensible scope.** Candidate from the brief: *"personnel protection and hazard characterisation only, never effectiveness or targeting."* My read:
- It **survives IOF/VLAIO-civil and Horizon** only if there is genuinely no defence deliverable, i.e. the work is framed as RF-EMF compliance and 5G/6G base-station and industrial exposure, with the military relevance left implicit. This is the honest civilian core and it is real (base-station pipeline, ICNIRP compliance module).
- It **does not survive contact with a real EDF call**, because EDF calls require demonstrated **defence relevance and dual-use uplift**. An EDF reviewer wants to see the capability improve a defence system. "Personnel protection only, never effectiveness" is exactly the framing EDF is designed to look through. You would be funded for the dual-use uplift, which is the thing the scope promises never to touch. So the scope is coherent for civil money and self-contradictory for EDF money. **You cannot have both the pure scope and the EDF cheque.**
- The one framing that threads it: **certification and standards, not systems.** Finding A's certifiable exposure envelope and Finding C(a)'s "agile array is compliant on paper, non-compliant in reality" are *standards* findings. They protect bystanders and they are Wout's world (RF-EMF standards bodies). They do not optimise a weapon. They are publishable, non-controlled, and fundable as civil RF-EMF compliance science. That is the defensible narrow scope, and it deliberately **excludes the ADS safety-of-effect play**, because that one cannot escape the higher-duty-cycle reading.

**The unresolved tension, surfaced not hidden.** Making a microwave system legally operable closer to humans protects bystanders and raises its permitted duty cycle. This is not a framing problem you can write away. The only clean side of it is the standards/certification work, where the deliverable is a *limit* or a *bound* (a keep-out certificate, a compliance method), not a *controller* or an *effect model*. The moment the deliverable is "how hot does this make skin," you are on the weapon's side of the line whatever the cover page says. Robin should decide on that boundary: **deliverables that are bounds and limits are defensible, deliverables that are effect models are not**, regardless of stated intent.

## 5. What would kill this, as a one-week falsifiable test

Two independent kill tests:

1. **The band kill.** Someone spends a day building the definitive table of every fielded or funded high-power (>10 kW average or >10 MW peak) directed-energy anti-personnel or counter-drone system, with sourced operating frequency. If the count of systems above 6 GHz is still one (ADS family) and it is still CW, the pulsed-fluence integrator has zero valid pulsed market and the surface-speed HPM pitch is confirmed dead. I expect this table confirms the kill.

2. **The EDF-scope kill.** Take one real, open EDF or EDA call text and try to write a half-page concept for AEGIS that (a) satisfies the call's defence-relevance requirement and (b) never produces an effect/effectiveness deliverable. If it cannot be done without either failing the relevance test or crossing into effect modelling, then "personnel protection only" is not EDF-fundable and Robin must choose civil-only money or accept the dual-use reading. One week, one call, one honest attempt.

## 6. The single highest-value next action, and who

**Action:** Wout Joseph tables Finding C(a) as a *standards contribution* at one of the RF-EMF committees he sits on: "an agile coherent array can be compliant against the 4 cm² / 6 min / unperturbed-field averaging while producing a steerable λ-sized hotspot that the averaging hides." That is the one output here that is simultaneously true, novel, publishable, non-controlled, defensible on any ethics reading, and fundable as civil compliance science, and it needs no defence customer, no clearance, and no classified geometry to exist. It also seeds the certifiable-envelope product (Finding A) as the answer to the problem it raises.

**Who:** Wout, using his standing committee seat. It costs nothing and it is the fastest route to the only version of this thesis that fully clears section 4's ethics boundary.

---

### Note back to the orchestrator

Two corrections to the brief itself:
- The Leonidas "450 MW / 20 ns / 50 Hz" line describes a vircator-class weapon, not the actual GaN long-pulse Leonidas. Any downstream agent using those numbers as Leonidas specs is wrong.
- The "~100 ms reference window" attributed to C95.1-2345 could not be verified. The verified pulsed constraints are the per-pulse fluence limit (~200 to 400 kJ/m² over 1 cm², >30 GHz) and the 100 kV/m instantaneous peak-E ceiling. If a downstream claim rests on the 100 ms window, source it from the paywalled standard first.
