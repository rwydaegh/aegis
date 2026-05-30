# Consolidated contact sheet (collaborators + companies)

*Synthesised 2026-05-27 from the Gemini Deep Research pass (`results_gemini.md`) and the Claude-for-Chrome pass (`results_chrome.md`), cross-checked against `collaboration_targets.md` and `company_outreach_and_ndas.md`. Emails marked **[verified]** were read off an official page; **[guess]** follows the institution's standard pattern and must be confirmed. Warm paths come from Robin's own LinkedIn network (high-confidence).*

## Use these warm intros first (highest leverage)
1. **Ericsson — Davide Colombi & Christer Törnevik.** Two-hop: **Wout -> Luc Martens -> both.** Luc is a direct mutual connection on each. One email from Wout/Luc opens the base-station EMF conversation. This is the strongest LOI lead.
2. **Orange — Dinh-Thuy Phan-Huy.** 2nd-degree via **Margot Deruyck** (INTEC-WAVES). Warm door into the RIS/Di Renzo industry side.
3. **ZMT ecosystem — Sven Kühn.** Via Wout's IT'IS/IEC TC 106 ties. Kühn = IT'IS + SPEAG (HW R&D) + ZMT (Product Safety) in one person; the Sim4Life-integration pitch goes to him.
4. **Nokia (no named owner) — via Jafar Keshvari (IEEE ICES Chair).** 2nd-degree via Luc + Mike Wood. Ask him who owns EMF at Nokia.

## Shortlist A — academic collaborators
| Person | Org | Email | Warm path | Status / next action |
|---|---|---|---|---|
| Anja Skrivervik | EPFL | anja.skrivervik@epfl.ch **[verified]** | EuCAP/AP-S community; conference intro | Top prestige x fit. Ready to approach (after patent-draft gate). |
| Marco Di Renzo | CentraleSupélec / Paris-Saclay / CNRS | marco.di-renzo@centralesupelec.fr **[guess]** | via Phan-Huy / Margot Deruyck | Confirm affiliation from a 2025/26 paper (Chrome's "moved?" alarm is likely just a stale dir). |
| Andreas Christ | **was IT'IS — now moved (locate)** | not public | via IT'IS co-authors / Kühn | Still co-publishing 2025 skin-model paper. Find current institution before approaching. |
| Niels Kuster / Esra Neufeld | IT'IS / ETH; Neufeld also ZMT CSO | info@itis.swiss (general) | Wout / IEC TC 106 | Ecosystem owners. Partnership track (coopetition) — handle as in `company_outreach_and_ndas.md`. |
| Thomas Eibert | TU Munich | eibert@tum.de **[guess]** (TUMonline has real one) | EuCAP/AP-S | Near-field rigor co-author. |
| Mats Gustafsson | Lund (EIT/LTH) | mats.gustafsson@eit.lth.se **[verified]** | via Skrivervik (joint 2025 IEEE TAP paper) + ELLIIT | The "provable bounds" angle. Strong, novel. |
| Joe Wiart | Télécom Paris / IP Paris | joe.wiart@telecom-paris.fr **[guess]** | BioEM/COST; Wout likely knows him | Stochastic/ML dosimetry; both in GOLIAT. |
| Emil Björnson | KTH | emilbjo@kth.se **[verified]** | massive-MIMO/EMF overlap | Exposure-aware MIMO operator partner. |
| Romain Fleury | EPFL (LWE) | romain.fleury@epfl.ch **[verified]** | same building as Skrivervik | RIS scattering-physics validation. |
| Akimasa Hirata | Nagoya IT | not public (NITech portal / researchmap) | IEC TC 106 / ICES | Deepest >6 GHz APD-dosimetry fit; mid-prestige uni. |

LinkedIn: most of the above have none (they use Scholar/ResearchGate) — not a problem.

## Shortlist B — companies / labs / regulators
| Target | Person & role | Email | Warm path | Status / next action |
|---|---|---|---|---|
| ZMT / SPEAG / IT'IS | **Sven Kühn** (IT'IS PL + SPEAG HW R&D Dir + ZMT Product Safety) | IT'IS "Send Email" form | Wout / IEC TC 106 | Partner track, not a rushed LOI. The Sim4Life-integration contact. |
| ZMT (Sim4Life) | **Esra Neufeld** (IT'IS Assoc. Dir + ZMT CSO) | info@itis.swiss | as above | The "AEGIS feeds Sim4Life" pitch lands here. |
| Ericsson Research | **Davide Colombi** (Principal Researcher, EMF) | Ericsson page / ResearchGate | **Wout -> Luc -> Colombi (2-hop)** | Strongest LOI lead. LinkedIn: /in/davide-colombi-862509139 |
| Ericsson Research | **Christer Törnevik** (Senior Expert, EMF & Health) | Ericsson page | **Wout -> Luc -> Törnevik (2-hop)** | Same path; senior EMF authority. |
| Nokia | owner **not identified** | — | via **Jafar Keshvari** (ICES Chair, 2nd-deg) | Ask Keshvari who owns EMF at Nokia; or check Nokia's IEC 62232 contributors. |
| Test labs (Eurofins/CETECOM/Verkotan) | leads **not found** | lab contact pages | via Kühn (interfaces with all three) | Manual: Eurofins E&E (DE), CETECOM (Essen), Verkotan (Oulu). |
| BIPT (Belgium) | EMF contact **not identified** (site restructured) | bipt.be / +32 2 226 88 88 | **Wout knows the BIPT EMF engineer** | Ask Wout for the direct name. |

## Gaps -> the unlock is mostly Wout
Test-lab leads, BIPT's named engineer, Nokia's EMF owner, and Christ's current institution are the open gaps. Wout is the fastest route for most (BIPT, Nokia-via-Keshvari, IT'IS); Kühn for the test labs. Resolve these, then refresh the contact table in `company_outreach_brief.tex` in one pass.

## Critical notes (read before trusting the research)
- **Prior art on "differentiable dosimetry" is real (University of Split, since 2021).** Kapetanović & Poljak, *AD for mmWave absorbed power density on non-planar bodies* ([IEEE 2021](https://ieeexplore.ieee.org/document/9566429/)), + follow-ups (spherical head to 100 GHz; realistic ear model with Zhadobov/IETR). Their method is **BEM + autodiff**, not your closed-form physics — so AEGIS's speed is still differentiated, **but differentiability is not the novelty.** Lead the patent and pitch on the **closed-form surface method + millisecond speed**, not "first differentiable dosimetry."
- **General differentiable EM is mature** (Fan/Stanford `ceviche`, Johnson/MIT adjoint Meep, `FDTDX`, `meent`). Different object (full-wave photonics). "Remilab rfx" from the Gemini report **did not verify** — treat as fiction.
- **Gemini's report is prestige-blind and citation-sloppy** (ranked Wout #2, a Croatian group #1; double-attributed the Split paper to Hirata). Trust its *reasoning* (the "critical gaps" / curvature sections are good) more than its *facts*. Verify every precise date/number before use (63195-2 Ed.2 "2027", TR 63572, ITU-T K.160, the grant euros all UNVERIFIED; 63195-2 **Ed.1 2022** is real and is the validation benchmark).
- **Net on prestige collaborators:** the differentiable-EM thread delivered no new prestigious host. The prestige set is unchanged: EPFL/Skrivervik, ETH-IT'IS, Paris-Saclay/Di Renzo, TUM/Eibert, Lund/Gustafsson, KTH/Björnson. The new low/mid-prestige names (Split, CNR IEIIT/EXPOAUTO, Aalborg) earn their place only for specific reasons (Split = neutralise prior art; CNR IEIIT = dosimetry side of the RIS thread).

## Draft note for Alessandro/Filip (patent prior-art flag)
*Now backed by a full read of the 2023 Split PhD thesis — see `prior_art_split_thesis.md`.*
> While mapping the field I found the closest prior art: A. Lojić Kapetanović & D. Poljak (Univ. Split), PhD thesis "Advanced Technique for Assessment of Spatially Averaged Dosimetric Quantities on Nonplanar Surfaces" (2023) + 4 journal papers (incl. one with Zhadobov/IETR Rennes). It is a *numerical post-processor* (Gauss-quadrature surface-averaging of an externally computed BEM/FDTD field), not a closed-form method, and reports no speed figures. Two points for the claims: (1) the transmission relationship `Sab = T·Sinc` with `T = 1-|Γ|²` (Fresnel) is **explicitly in the thesis** (eqs. 3.9-3.10), so we should *not* claim the transmission-coefficient idea itself; and (2) they use JAX autodiff loosely, so we should not lead on "differentiable dosimetry". Our defensible novelty should be framed tightly around: the **closed-form, solver-free, millisecond analytical product**; the **near-constant pseudo-Brewster T0** characterisation that enables it (the thesis only uses normal-incidence T and treats Brewster as an angle effect); the **coherent MIMO exposure operator**; the **spherical-harmonic antenna/body decoupling**; and the **end-to-end differentiable beamforming/antenna-optimisation loop**. Flagging so the draft is framed accordingly.
