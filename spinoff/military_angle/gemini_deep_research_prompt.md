# Gemini Deep Research prompt: military RF exposure (HERP) landscape

Paste everything below the line into Gemini Deep Research.

---

I am researching the commercial and technical landscape for **protecting humans from high-power
military radio-frequency emitters**: shipboard radars, electronic-warfare jammers, ground-based
air-defense radars, and the new class of high-power microwave (HPM) counter-drone weapons. I want a
rigorous, sourced landscape report, not a summary of what RF exposure is. Assume I am an
electromagnetics PhD. Be specific, name names, cite documents, and give numbers where they exist.
Where something is genuinely unknown or classified, say so explicitly rather than guessing.

Please cover the following, in this order.

**1. The regulatory and standards skeleton.**
- Map the governing documents for military RF exposure to personnel: MIL-STD-464 (which revision is
  current, and what does section 5.9 EMRADHAZ actually require), NAVSEA OP 3565 / NAVAIR 16-1-529,
  DoDI 6055.11, IEEE C95.1 (which edition the DoD adopts), and NATO STANAG 2345.
- How do the military limits (IEEE C95.1) differ numerically from the civilian ICNIRP 2020 limits,
  in the 300 MHz to 100 GHz range? Give the actual permissible exposure values for controlled and
  uncontrolled environments and explain where and why they diverge.
- What is the European and NATO equivalent of the US framework? Which standard binds a Belgian,
  Dutch, French or German navy vessel? Is STANAG 2345 actually implemented nationally, and how?
- Clarify the distinction between HERP (personnel), HERO (ordnance) and HERF (fuel), including who
  owns each in the US Navy, and whether HERO is a bigger budget line than HERP.

**2. How the hazard assessment is actually performed today.**
- Concretely, what is the workflow for computing a radiation hazard (RADHAZ) zone around a warship,
  a ground radar, or an aircraft? Is it measurement survey, closed-form worst-case formula, full-wave
  simulation, or ray tracing? Cite doctrine or papers.
- Which commercial computational-electromagnetics tools are actually used for shipboard "topside
  design" and RADHAZ analysis? I specifically want to know the real capabilities of Altair FEKO,
  Ansys HFSS SBR+ / Savant / Perceive EM, Dassault CST, and Remcom in this application, plus any
  government or defense-lab in-house codes (for example anything from NSWC Dahlgren, NRL, or NATO
  bodies). Do any of them ship a dedicated RADHAZ or HERP module?
- How is the human body represented in these tools, if at all? Is it a simple power-density
  threshold at a point in space, a whole-body SAR calculation, an anatomical phantom, or nothing?
  This is the crux: I want to know whether anyone actually models the person, or whether they only
  model the field and compare it to a limit.
- Are keep-out zones computed conservatively, and what is the operational cost of that conservatism
  (for example, emission-control doctrine, restrictions on flight-deck operations, personnel
  scheduling)? Find any documented case where conservative RADHAZ zones limited operational tempo.

**3. Phased arrays and the optimization question (the most important section).**
- Modern shipboard radars (AN/SPY-6, AN/SPY-1, Thales SeaMaster / SMART-L, EW arrays) and HPM weapons
  are electronically steered phased arrays with software control of the excitation weights.
- Is there ANY published work, product, patent, or program that performs **exposure-constrained
  beamforming or beam scheduling**, meaning: choosing the array excitation or the scan schedule so
  as to maximize mission performance subject to a constraint that human exposure at specified
  locations (a ship's deck, a friendly troop position) stays under the permissible limit?
- Search adjacent literature deliberately: SAR-constrained beamforming and SAR-aware MIMO precoding
  in 5G handsets and base stations, exposure-aware beam management in cellular networks, and
  "safe beamforming" or "human-aware beamforming." Then tell me whether that literature has ever
  been carried into the military RADHAZ domain.
- Do any RADHAZ tools expose gradients, adjoint sensitivities, or any optimization loop at all, or is
  the entire discipline forward-analysis-only?

**4. High-power microwave counter-drone systems and their human-safety story.**
- Profile the fielded and near-fielded HPM counter-UAS systems: Epirus Leonidas (and its VehicleKit
  and Expeditionary variants), the AFRL THOR and Mjolnir programs, Raytheon CHIMERA / PHASER, and any
  European equivalents.
- For each, what is publicly stated about human safety, standoff distance, and "safe zones"? Epirus
  publicly describes "software-controlled safe zones" and "highly directional phased array antennas."
  I want to know: is there any published methodology, certification path, or regulatory approval
  behind such claims, or is it presently an engineering assertion?
- What agency certifies that a directed-energy weapon is safe to operate near friendly personnel and
  civilians, and by what analysis? Is there an emerging standard?
- What frequencies do these systems operate at? This determines whether human exposure is a surface
  (skin) absorption problem or a whole-body volumetric one.

**5. The buyer, the money, and the barriers.**
- Who actually purchases RADHAZ / E3 (electromagnetic environmental effects) analysis and software?
  Prime contractors, shipyards, navies, test ranges, or safety authorities? Name the offices.
- Estimate the size of the market for E3 / EMC / RADHAZ engineering services and software in defense.
  Separate software licences from consulting and test services.
- What are the export-control realities? Is RADHAZ analysis software ITAR-controlled, EAR-controlled,
  or unclassified? Contrast this explicitly with radar-cross-section and stealth-signature tooling,
  which I understand to be far more restricted. I want to know whether a *safety* discipline is
  genuinely more open than a *signature* discipline.
- What is the realistic path for a **European (Belgian, university spin-off)** company to sell into
  this space? Cover NATO bodies, the European Defence Fund and EDA, national navies, and European
  primes (Thales, Naval Group, Damen, Leonardo, Saab, Hensoldt). What are current open calls or
  programmes in 2026 related to electromagnetic environmental effects, directed energy safety, or
  counter-UAS?

**6. The scientific gaps.**
- Where does current RADHAZ practice acknowledge that it is inaccurate or over-conservative? Look for
  discussion of multipath and reflection off ship superstructure, near-field versus far-field
  assessment, cumulative exposure from multiple simultaneous emitters, time-averaging over rotating
  or scanning beams, and the difference between incident power density and actual absorbed power in
  a human body.
- Above 6 GHz, international limits shifted from whole-body SAR to absorbed power density on the
  skin (ICNIRP 2020, IEEE C95.1-2019). Has the military RADHAZ community adopted that shift, and does
  it change anything for X-band and millimetre-wave emitters?
- Is anyone doing anatomically-realistic human-body dosimetry in a military RF environment, as
  opposed to comparing a field value to a threshold?

**7. Synthesis.**
- Give me a clear verdict on where the genuine unmet need is, if any, and who feels the pain most
  acutely.
- Identify the three most credible entry points for a new technical entrant, and the three strongest
  reasons this market resists new entrants.
- Flag anything that surprised you.

Format the answer with clear headings matching the sections above. Prefer primary sources
(standards documents, DoD instructions, program offices, peer-reviewed papers, vendor technical
documentation) over trade-press summaries, and mark clearly when you are relying on marketing
material. Include a short list of the highest-value documents I should read myself.
