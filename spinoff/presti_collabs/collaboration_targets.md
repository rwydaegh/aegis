# Where AEGIS can land a prestigious collaboration: conclusions

*Claude Opus, May 2026. Synthesized from five parallel web-research sweeps (~25 searches, ~50 candidates) across: RF/EMF dosimetry, exposure-aware comms/RIS, antennas/near-field/metasurface physics, differentiable EM / inverse design, and MRI-SAR. Goal: identify the most prestigious universities where a soon-to-be-postdoc founder of AEGIS could land a genuine research collaboration (the "international mobility" line in a VLAIO/IOF/FWO proposal). Prestige is the primary sort the user asked for; fit is the gate (a prestigious host with no real hook is useless). Sources were gathered by automated agents and the named people/affiliations check out against domain knowledge, but **spot-check the exact paper URLs before citing any in a proposal.***

---

## The one-paragraph conclusion

The single best **prestige × fit** combination is **EPFL — Anja Skrivervik**: a top-3 European technical university and a near-bullseye scientific match (her 2025 work decomposes in-body antenna radiation into reactive near-field + propagating absorption + Fresnel reflection using spherical harmonics, which is essentially AEGIS's own decomposition). Tied at the top on prestige, with a bullseye on dosimetry but a coopetition asterisk, is **ETH Zurich / IT'IS (Kuster, Christ, Neufeld)** — the global gold standard, and the same people as the ZMT/Sim4Life relationship. The two cleanest "bold new direction" hosts are **Paris-Saclay — Marco Di Renzo** (exposure-aware RIS, ETSI RIS chair) and **Lund — Mats Gustafsson** (turn AEGIS's empirical validation into *provable physical error bounds* — a genuinely novel hook). The absolute-prestige names (**MIT — Steven Johnson, Stanford — Shanhui Fan**) are reachable only as *method-credibility* collaborations (you'd import their differentiable-EM machinery into your domain), not as meeting-in-the-middle partnerships. Honest note: **Oxford, Cambridge, and Imperial surfaced no genuine RF-dosimetry/exposure hook** — don't force a fit there just for the name.

---

## Master shortlist (ranked by prestige × fit)

| # | Person | University | Prestige | Fit | The collaboration in one line |
|---|--------|-----------|----------|-----|-------------------------------|
| 1 | **Anja Skrivervik** | EPFL (CH) | Top-3 EU tech | **Bullseye** | Ground-truth the AEGIS near-field/curved-body extension with her spherical-harmonic in-body-antenna analytics |
| 2 | **Niels Kuster / Andreas Christ / Esra Neufeld** | ETH Zürich + IT'IS (CH) | Top-7 global | **Bullseye** (coopetition) | Validate AEGIS's closed-form mmWave APD against the IEC/IEEE 63195 reference + Virtual Population phantoms |
| 3 | **Marco Di Renzo** | Paris-Saclay / CentraleSupélec / CNRS (FR) | Top French, ETSI RIS chair | **Bullseye (new direction)** | Replace his free-space "limit circle" exposure proxy with AEGIS's differentiable body-level operator Q -> physically-rigorous exposure-aware RIS |
| 4 | **Thomas Eibert** | TU Munich (DE) | Top-3 DE | High | Feed AEGIS a probe-corrected, spherical-mode-resolved antenna near-field instead of a power approximation |
| 5 | **Mats Gustafsson** | Lund (SE) | Top SE, world authority on EM bounds | High (novel) | Derive *provable* worst-case SAR error bounds for the planar-on-curved approximation (empirical -> guaranteed) |
| 6 | **Joe Wiart** | Télécom Paris / IP Paris (FR) | Top FR engineering | **High (most genuine application fit)** | AEGIS as the fast differentiable forward model inside his stochastic/ML population-dosimetry pipeline |
| 7 | **Emil Björnson** | KTH (SE) | Top Scandinavia, massive-MIMO superstar | Medium-high | Body-level exposure operator for cell-free / massive-MIMO beamforming (his emerging EMF-trade-off line) |
| 8 | **Steven G. Johnson** (MIT) / **Shanhui Fan** (Stanford) | MIT / Stanford (US) | Top-3 global | Method-genuine, application-aspirational | Import adjoint/differentiable-Maxwell rigor; co-author on the method, not the application |

---

## By prestige tier (fuller list, fit-gated)

### Tier S — absolute top global / top European, with a *real* hook
- **EPFL** — **Anja Skrivervik** (antennas in lossy tissue, implantable, spherical-harmonic near-field decomposition; her 2025 *Cell Reports Phys. Sci.* paper mirrors AEGIS's Fresnel + near-field + propagating decomposition). Also **Romain Fleury** (wave physics / RIS scattering models — the physics-side RIS hook). *EPFL is the standout: max prestige, bullseye fit, no incumbent baggage.*
- **ETH Zürich / IT'IS** — **Andreas Christ** (mmWave skin models 15-110 GHz, IEC/IEEE 63195 co-convener — the most direct technical match), **Esra Neufeld** (Sim4Life technical lead, UQ), **Niels Kuster** (emeritus, the ecosystem). *Bullseye, but this is the ZMT/Sim4Life incumbent — collaboration here is also coopetition. Highest credentialing value.*
- **MIT** — **Steven G. Johnson** (adjoint methods, Meep, NLopt; documented RF phased-array use, not just photonics). Method-direct, application-thematic.
- **Stanford** — **Shanhui Fan** (founded differentiable Maxwell, `ceviche`), **Jelena Vučković** (inverse-design photonics). Method-genuine, application one step removed.
- *Skip-list (no fit found): Oxford, Cambridge, Imperial — no RF-dosimetry/exposure lead surfaced. Princeton (Rodriguez) and Caltech are inverse-design-theory only.*

### Tier A — top European / top global, genuine fit
- **TU Munich** — **Thomas Eibert** (inverse-source, near-field-to-far-field, spherical multipole; 2024 IEEE TAP King Award). Direct near-field-math bridge.
- **Paris-Saclay / CentraleSupélec** — **Marco Di Renzo** (exposure-aware RIS, 5+ papers, ETSI RIS chair, EU-project leverage via RISE-6G successors).
- **KTH** — **Emil Björnson** (massive MIMO / cell-free, emerging EMF trade-offs). High name recognition.
- **NUS** — **Zhi Ning Chen** (implantable/wearable + near-field antennas; AEGIS as millisecond SAR feedback in his design loop). Geographically distant.
- **Toronto** — **George Eleftheriades** (Huygens metasurfaces, superoscillation); **Michigan** — **Anthony Grbic** (Huygens surfaces, near-field plates). Source-physics side; US/Canada geography.
- **TU Delft** — **Nuria Llombart** (mmWave/THz lens field-sensors -> measurement validation of AEGIS above 30 GHz). No dosimetry lead at Delft, but a concrete mmWave validation hook.
- **NYU** — **Riccardo Lattanzi** + **Christopher Collins** (MRI SAR / electrical-property tomography; AEGIS as fast differentiable forward model in their inverse loop); **Ted Rappaport** (NYUSIM mmWave channels feeding AEGIS).

### Tier B — strong / field-leading, slightly below top-rank
- **Télécom Paris / IP Paris** — **Joe Wiart** (Chair C2M; the single most *genuine* application partner: stochastic + AI dosimetry meets AEGIS's differentiable forward model). IP Paris prestige is high.
- **Lund** — **Mats Gustafsson** (physical bounds; the "provable error bound" hook — novel and standalone-publishable).
- **Aalto** — **Sergei Tretyakov** (metasurface/RIS physics, Physical-Optics-validity audit), **Katsuyuki Haneda** (28-140 GHz channel + body phantoms), **Riku Jäntti** (EMF-aware RIS). Strong Nordic 6G ecosystem.
- **KU Leuven** — **Christophe Caloz** (metasurface GSTC physics; *50 km from Ghent*, FWO-fundable, geographically ideal). Also Guy Vandenbosch (WaveCoRE antennas/CEM).
- **KCL** — **Shaihan Malik** (real-time pTx MRI SAR control); **DKFZ Heidelberg** — **Mark Ladd** (real-time 32-ch pTx SAR supervision, 14T push); **UMC Utrecht** — **Cornelis van den Berg** (MRI/hyperthermia SAR, fast methods); **TU Eindhoven + Erasmus MC** — **Maarten Paulides** (SAR optimization for RF antenna arrays driving tissue heating — independently the *same problem formulation* as AEGIS, at 434 MHz). These five are the **MRI/hyperthermia adjacent market** — a second, well-funded application domain on the same SAR physics.
- **Sorbonne** — **Guido Valerio** (near-field focusing / leaky-wave sources); **QMUL** — **Yang Hao** (body-centric antennas, 2024 EurAAP award); **Surrey 5G/6GIC** — **Ahmed Elzanaty** (closest direct EMF-aware-RIS technical hit, joint paper feasible in ~6 months).

### Field-leaders at lower-rank schools (worth it for fit, not for the name)
- **Akimasa Hirata** (Nagoya IT, JP) — *the* world authority on >6 GHz APD dosimetry and ICNIRP 2020 limit derivation. The deepest pure-science match anywhere; mid-rank university.
- **Marta Parazzini** (CNR-IEIIT / PoliMi, IT) — 3D-beamforming + APD + stochastic dosimetry, directly overlapping program.
- **Luca Chiaraviglio** (Tor Vergata, IT) — network-scale 5G/6G EMF compliance (matches the base-station product line).
- **Theodoros Samaras** (Thessaloniki, GR) — stratified-skin thermal dosimetry 6-100 GHz (pairs with AEGIS surface-Sab as thermal input).
- **Stefano Maci** (Siena, IT) — top antenna group, holographic metasurface sources.
- **Claude Oestges + Jérôme Eertmans** (UCLouvain, BE) — **DiffeRT**, the JAX differentiable ray tracer AEGIS consumes. Cleanest *stack* match, Benelux-local. (Eertmans is a finishing PhD; Oestges is the durable PI.)

### Industry (not mobility hosts, but top technical co-authors)
- **NVIDIA Research — Jakob Hoydis / Faycal Ait Aoudia** (Sionna RT, the canonical differentiable ray tracer feeding AEGIS).
- **Ericsson Research — Davide Colombi / Christer Törnevik** (actual-maximum massive-MIMO base-station exposure; Colombi is the same Ericsson contact in `honest_analysis.md`; Törnevik is adjunct at KTH = an academic foothold). Validation + commercialization channel.

---

## By the "story" the proposal could tell

A mobility line reads differently depending on the narrative. Pick one (or pair a prestige anchor with a direction):

1. **"I went to the center of my field."** -> **EPFL (Skrivervik)** or **ETH/IT'IS (Christ)**. Highest credentialing; grounds AEGIS's least-validated piece (near-field) or its compliance physics. EPFL is the cleaner of the two (no incumbent conflict).
2. **"I opened a bold new direction."** -> **Paris-Saclay (Di Renzo)**, exposure-aware RIS. Hot 6G topic, EU-funding leverage, and you bring the missing rigorous-physics layer. (See the dedicated RIS analysis — their exposure model is a free-space proxy you upgrade.)
3. **"I made the method provably correct."** -> **Lund (Gustafsson)**. Convert AEGIS from "validated empirically" to "guaranteed within X% by physical bounds." Genuinely novel, surprising, and standalone-publishable. Underrated pick.
4. **"I brought differentiable physics to dosimetry."** -> **MIT (Johnson)** or **Stanford (Fan)**. Max prestige, but be upfront it's a method-import collaboration, not a 50/50 partnership.
5. **"I entered an adjacent billion-euro market."** -> the **MRI/hyperthermia cluster** (Utrecht / TU-e+Erasmus / KCL / DKFZ / NYU). Same SAR physics, different (sub-GHz) frequency regime, well-funded clinical money. Best fit there is **Paulides (TU/e)** — he literally built the same SAR-array-optimization problem.

---

## Honest caveats (don't skip)

- **Coopetition at ETH/IT'IS.** They are Sim4Life/DASY — simultaneously the dosimetry gold standard *and* the commercial incumbent AEGIS "complements." A collaboration is maximally credentialing but politically the same delicate dance as the whole ZMT relationship. EPFL/Skrivervik gives you near-equivalent prestige with far less conflict.
- **Frequency mismatch for the MRI/hyperthermia cluster.** AEGIS is mmWave (6-300 GHz, surface absorption, plane-wave). MRI is 64-450 MHz (near-field coil coupling, electrically smaller body). The layered-sphere/Fresnel math rhymes, but you'd need a coil/near-field front-end or scope the contribution to the tissue-SAR layer. Hyperthermia (434 MHz, far-field antenna arrays) is the smaller gap — Paulides is the easiest entry.
- **Differentiable-photonics crowd is method-genuine, application-aspirational.** Fan/Johnson/Vučković/Rodriguez invented the autodiff-on-Maxwell machinery AEGIS rests on, but their domain is chips/optics. Frame as "import the method," not "we both do exposure."
- **Geography vs the Carolina-in-Belgium constraint.** For a *proposal mobility line*, short stays (weeks-months) are the norm, so even ETH/EPFL (CH), MIT/Stanford/NYU (US) are feasible. But the path of least friction is EU-proximal: **Paris-Saclay, Télécom Paris, TU Munich, Lund, Aalto, TU Delft, and especially KU Leuven (50 km) / UCLouvain (in-country).**
- **Prestige is not the same as fit.** The QS-top names with no hook (Oxbridge, Imperial) aren't worth forcing. The honest "most prestigious *and* genuine" frontier is EPFL > ETH > TUM > Paris-Saclay > KTH.

---

## Recommended next actions

1. **Approach via warm intros where they exist.** Wout sits in IEC TC 106 / IEEE ICES and almost certainly knows **Kuster, Christ, Hirata, Wiart, Samaras**, and the Ericsson pair (**Colombi/Törnevik**). Use him. The RIS/comms names (**Di Renzo, Björnson, Elzanaty**) come through the EuCNC / IEEE ComSoc world; **Skrivervik/Eibert/Maci** through EuCAP / IEEE AP-S.
2. **Lead with EPFL/Skrivervik for the "center of field" story and Di Renzo for the "new direction" story.** Naming both in a proposal (a rigorous host + an ambitious direction) reads as someone who knows where their field lives and where it is going.
3. **Keep Gustafsson (Lund) in your back pocket** — the "provable error bounds" angle is the most novel and the most likely to impress a physics-literate reviewer.
4. **Treat the MRI/hyperthermia cluster as optional market-expansion**, not the headline (frequency mismatch). Paulides (TU/e) is the cleanest entry if you go there.
5. **Verify every link before it goes in a proposal.** These were machine-gathered; the people and affiliations are sound, but confirm the exact papers/titles yourself.

---

## Appendix: full sourced rosters
The five raw scouting reports (with per-candidate URLs) are preserved in the conversation that generated this file. Key anchor sources:
- Skrivervik 2025 in-body decomposition: cell.com/cell-reports-physical-science (S2666-3864(25)00226-7)
- Di Renzo EMF-aware RIS: arxiv.org/abs/2104.06283, arxiv.org/pdf/2110.10311
- Christ mmWave skin model 15-110 GHz: onlinelibrary.wiley.com/doi/10.1002/bem.70025
- Eibert near-field transforms: ee.cit.tum.de/en/hft (King Award 2024)
- Gustafsson EM bounds: arxiv.org/pdf/2405.11499
- Wiart Chair C2M: telecom-paris.fr/joe-wiart
- Björnson cell-free + EMF: arxiv.org/pdf/2207.05990
- Hirata >6 GHz dosimetry review: arxiv.org/abs/2011.10699
- Paulides constrained-SAR hyperthermia: research.tue.nl (constrained SAR focusing)
- DiffeRT (UCLouvain): github.com/jeertmans/DiffeRT
