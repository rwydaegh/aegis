# Prompt for Gemini Deep Research

*Paste everything below the line into Gemini Deep Research. It is self-contained. This tool is for broad, autonomous public-web synthesis (market, landscape, who-works-on-what). It should NOT try to find private emails or log into LinkedIn — a separate browser tool does that.*

---

You are doing deep research to support a university spin-off. Spend your full research budget reading the public web (academic and lab pages, Google Scholar, conference programmes, company sites, analyst notes, standards bodies, EU project pages). Produce one structured, heavily-sourced markdown report. Every non-obvious claim needs an inline source URL. Flag uncertainty. Do not fabricate names, papers, or numbers.

## The venture (AEGIS)
AEGIS is a software platform spun out of Ghent University (founder Robin Wydaeghe, finishing his PhD, becoming a postdoc). It computes the **absorbed power density (Sab, W/m^2) and SAR** that wireless signals deposit on/in **3D human-body models, in milliseconds**, using fast closed-form/analytical physics instead of slow full-wave FDTD. Core idea: above ~6 GHz, RF absorption is confined to a thin skin layer, so `Sab(r) = Sinc * T0 * ReLU[n_hat . (-k_hat)]`, with `T0` a near-constant Fresnel transmission into tissue (a pseudo-Brewster effect). It covers ~100 MHz to 300 GHz, is validated against the analytical lossy-dielectric-sphere (Mie) solution, and adds: a **near-field extension** (radiating near-field, point sources, spherical-harmonic separation of antenna pattern vs body response), a **coherent massive-MIMO exposure operator** for beamforming, and a fully **differentiable (JAX) pipeline** enabling gradient-based exposure-aware antenna/beam optimization. Target applications: **5G/6G mmWave device pre-compliance** (a fast pre-screen feeding tools like Sim4Life), **base-station EMF compliance** (ICNIRP 2020, IEC 62232:2025, IEC/IEEE 63195-2), and **exposure-aware beamforming / reconfigurable intelligent surfaces (RIS)**.

## What I already believe — your job is to AUGMENT, CHALLENGE, and UPDATE this, not repeat it
- Likely academic-collaborator leads: EPFL (Anja Skrivervik, Romain Fleury), ETH Zürich / IT'IS (Niels Kuster, Andreas Christ, Esra Neufeld), Paris-Saclay / CentraleSupélec (Marco Di Renzo, exposure-aware RIS), TU Munich (Thomas Eibert), Lund (Mats Gustafsson, physical bounds), Télécom Paris / IP Paris (Joe Wiart), KTH (Emil Björnson), Nagoya IT (Akimasa Hirata).
- Market belief: the tractable wedge is mmWave device pre-compliance (vs Sim4Life FDTD); base-station compliance incumbent is IXUS (Alphawave/EMSS); the dosimetry ecosystem is ZMT Sim4Life + SPEAG DASY + IT'IS tissue data ("Kuster ecosystem"); test labs and regulators are short-cycle entry points.
- Standards: IEC 62232:2025 (base stations) published; IEC/IEEE 63195-2 (devices, 6-300 GHz) 2026 edition in draft.

**Tell me explicitly what I missed, what is wrong, and what is new (2024-2026).**

## Research questions (one section each, with ranked tables + inline source URLs)

1. **Academic collaborators.** Leading research groups/PIs at prestigious universities (TOP EUROPEAN first: ETH, EPFL, Oxford, Cambridge, Imperial, TUM, TU Delft, KU Leuven, KTH, Aalto, Politecnico Milano, Sorbonne/Paris-Saclay/IP Paris, DTU, Chalmers; then US and global) working on: fast/differentiable computational RF dosimetry, mmWave absorbed power density on bodies, antennas in/near lossy tissue and near-field body modelling, exposure-aware massive-MIMO/RIS beamforming, ML/stochastic dosimetry. For each: PI, group, university, country, 1-2 specific 2022-2026 outputs (with URL), recent grants, and a one-line fit rationale. Rank by prestige x fit. Surface names beyond my list above.

2. **Customers & market.** Map the buyers and the size, bottom-up: device OEM mmWave pre-compliance (Apple/Samsung/Qualcomm/MediaTek etc. — who does APD pre-compliance and with what), base-station compliance (operators + RAN vendors), test labs (Eurofins, CETECOM, Verkotan, SGS, TÜV, PCTEST, UL), national regulators. Recent market signals: 5G FR2 (mmWave) deployment status 2025-2026, 6G timelines, the regulatory drivers (FCC APD rules, ICNIRP 2020 adoption). Any public pricing for the relevant tools. Which segments are actually growing.

3. **Competitors / incumbents.** Deep dive on ZMT/Sim4Life, SPEAG/DASY, IT'IS Foundation, IXUS (Alphawave/EMSS), CST (Dassault), ANSYS HFSS, MVG/EMF Visual, plus **any emerging fast-dosimetry, ML-dosimetry, or differentiable-EM startups/tools** (this last one matters most — find anyone doing what AEGIS does). For each: what it does, frequency range, speed, pricing if public, recent moves (2024-2026).

4. **Standards & EU 6G-EMF actors.** Current status and key people of IEC TC 106 and IEEE ICES 63195-2 (2026 edition); EU 6G-EMF projects (RISE-6G and its SNS JU successors, 6G-IA EMF task force, Horizon Europe SNS) and who participates. Where are the openings for a new computational method to be recognised.

5. **Exposure-aware RIS / MIMO sub-literature & gaps.** Who is active (Di Renzo, Phan-Huy/Orange, Alouini & Elzanaty, Chiaraviglio, Björnson, others), what is published 2021-2026, **how they model "exposure"** (e.g. free-space incident power vs a limit circle, vs body-level absorbed power), and where the open gaps are that a fast differentiable body-level operator would fill.

## What NOT to do
- Do not try to find private/personal email addresses or log into LinkedIn or any account — a separate browser-based tool handles per-person contact details. Public info only.
- Do not invent. Every claim needs a source URL; mark anything uncertain.

## Output
A single markdown report I can paste back into another tool. Use ranked tables, inline links, an explicit **"What changed my assumptions"** section, and end with a **consolidated shortlist** of the 10-15 highest-value targets (collaborators + customers) across all questions, sorted by prestige x fit, each with the single best source link.
