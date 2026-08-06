# Project: "The state of >6 GHz RF exposure compliance" — an FCC filings data study

You are an autonomous AI engineer-analyst with shell access, ample compute and time, and permission to be ambitious. The amount of work is not a constraint. The quality and honesty of the output is.

## Who this is for and why

Robin is spinning off AEGIS, a fast physics engine that computes absorbed power density on human bodies, out of Ghent University. The commercial beachhead is pre-compliance simulation for wireless devices above 6 GHz, where FCC (and ICNIRP/IEC) rules require power density (PD) or absorbed power density (APD) evaluation instead of SAR. An IOF (university valorisation fund) application is being drafted NOW and needs hard market numbers. Beyond the grant, the same dataset is the company's prospect list, its validation corpus, and later a publishable industry note.

Every number in circulation today (analyst reports, a Gemini Deep Research pass, markready.io guides) is an uncited estimate. The FCC Equipment Authorization System is public and contains the ground truth: every certified device, its test reports with measured exposure values, its lab, its dates. Nobody — no consultancy, no incumbent, no data startup — has extracted and analyzed this at scale for the >6 GHz exposure segment. You will build that dataset and mine it.

## What is known for sure (verified by hand on 2026-07-14)

Facts below were verified by actually downloading and reading filings. Trust them.

**Data access:**
- `https://fcc.report/FCC-ID/<FCCID>` returns an HTML index of a filing's documents (titles + links). Document PDFs are at `https://fcc.report/FCC-ID/<FCCID>/<docid>.pdf`. **Plain `curl` works, no bot protection.** fccid.io is an alternative mirror.
- The official FCC EAS has a web API ("EAS Web API Services", FCC KDB publication 953436, includes getFCCIDList and related endpoints) and an advanced search UI at `apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm`. One unverified report claims apps.fcc.gov sits behind Akamai bot management; the mirrors do not. Discover the best bulk-metadata route yourself (candidates: official API, EAS search exports, mirror crawling, archive.org copies). Grant metadata includes applicant, grant date, frequency ranges, equipment class, and links to documents.
- One grant = many documents (test reports, appendices in separate PDFs, photos, cover letters, grant notes). Confidentiality requests hide some documents (usually schematics/photos, short-term), but exposure test reports are usually public.

**Report anatomy (from three real filings read in full):**
- Reports are versioned lab templates (e.g., Sporton "Form version: 180516", Bureau Veritas "Report Format Version 6.0.0") — highly regular, ideal for programmatic extraction. The same ~10 labs write most of them.
- Archetype 1, FR2 phone (example: FCC ID IHDT56ZP1, Motorola razr 5G, Sporton): measured free-space PD at 2 mm per surface per beam ID per antenna module, 4 cm² averaged, in W/m² (measured) and mW/cm² (reported). CRITICAL SUBTLETY: the "Reported PD" used for compliance is a construct (PD design target + device uncertainty, e.g. 3.8 W/m² + 2.1 dB = 6.16 W/m²), NOT the measured maximum. Extract both, never conflate them. Beam selection for measurement comes from a prior simulation ("Part 0" report, sometimes public in the same filing).
- Archetype 2, WiFi 6E/7 device (example: FCC ID E2K-QCNFA765, Qualcomm module in Dell tablet, Bureau Veritas): SAR for sub-6 bands plus PD AND APD for 5925-7125 MHz (this one: APD 8.61 W/m², PD 9.85 W/m² vs 10 W/m² limit — a 1.5% margin). Antenna part numbers, types, and per-band peak gains are IN the report. Result tables often live in separate appendix PDFs.
- Archetype 3, fixed/mobile >20 cm device (example: FCC ID A4RGUIK2, Google Nest Hub with 60 GHz Soli): 6-page MPE calculation, Friis formula at 20 cm. No measurement, no simulation. These filings are cheap paperwork — classify and count them, but they are not the pain market.

**Regulatory constants for interpretation:**
- 6 GHz is the transition: below it SAR (FCC limit 1.6 W/kg / 1 g), above it power density, FCC general-population limit 1.0 mW/cm² = 10 W/m², spatially averaged over 4 cm² (per FCC "interim guidance" / TCB workshop positions; the averaging rules are guidance, not codified rules).
- Portable (<20 cm from body) triggers measured/simulated evaluation; mobile (>=20 cm) gets an MPE calculation. Classification, not physics, determines compliance cost.
- Relevant FCC KDB publications you will see cited inside reports: 447498 (general RF exposure), 865664 (SAR measurement), 616217 (laptops/tablets), 248227 (Wi-Fi SAR), 996369 (modules), 388624 (Pre-Approval Guidance list — mmWave PD devices require FCC pre-approval before the TCB may grant, adding weeks to months).
- Units mix freely (mW/cm² vs W/m², factor 10). Scaling factors appear (tune-up tolerance, duty cycle, design-target constructs). Normalize carefully and keep provenance.

**Segment vocabulary** (for classification): 5G FR2 = bands n257-n261, 24-48 GHz. WiFi 6E/7 = 5925-7125 MHz (U-NII-5 to 8). 60 GHz = 57-71 GHz (WiGig 802.11ad/ay, FMCW radar, Soli). UWB = 6-9 GHz (802.15.4z). Watch for XR/wearables across all of these.

## The mission

Build the dataset, then mine it. Staged, so value exists at every checkpoint:

**Stage 0 — pilot (do this first, before any scaling decision).** End-to-end on ~200 filings spanning the segments and years: metadata -> document download -> extraction -> analysis row. Measure per-filing cost/time, extraction accuracy (hand-audit at least 30 extractions against the PDFs yourself), and the fraction of filings whose reports are public and parseable. Report the pilot numbers before scaling. If extraction accuracy is below ~90% on the money fields (reported value, measured value, limit, distance), fix the pipeline before scaling.

**Stage 1 — the corpus.** All FCC grants since 2019 (the year FR2 phones and the PD regime arrived) that plausibly involve >6 GHz RF exposure evaluation. Expect a few thousand to low tens of thousands of filings and a few hundred GB ceiling of PDFs; cache raw documents keyed by URL hash, be resumable, be polite to the mirrors (rate-limit, identify yourself in the user agent, back off on errors). Store extraction output in parquet with full provenance per field (source doc URL + page number).
Suggested core schema (adapt as reality dictates): fccid, applicant, grantee_code, grant_date, filing/report dates, equipment class, frequency ranges, segment classification, exposure classification (portable/mobile/fixed), evaluation type (measured PD / measured APD / SAR / MPE calc / simulation), lab name + site, TCB, report template + version, per-band and per-configuration reported and measured values with units and limits, separation distances, antenna info when present (type, gain, part numbers), KDB citations, simulation tool mentions, PAG indicators, Class II permissive changes and re-filing lineage.

**Stage 2 — the analyses.** A menu, ranked by value to Robin. You are free to reorder, drop, and add — do what the data supports, not what this list forces. Flag which of these actually worked.

1. **Real volumes.** Grants/year by segment (FR2, WiFi 6E/7, 60 GHz, UWB, other) and by evaluation type, 2019-2026. This replaces circulating guesses (one estimate says ~1,200-1,500 WiFi 6E/7 vs ~150-180 FR2 grants/yr — check it). Include the portable-vs-mobile split per segment: it is the compliance-cost split.
2. **The margin distribution and the censoring analysis (the intellectually ambitious one).** For every filing with a numeric reported value and limit, compute margin = reported/limit. The compliance limit acts as a hard cut-off on an underlying design distribution: designs that would have exceeded it were power-backed-off, redesigned, or re-filed until they passed, so the observed distribution should show bunching just below 1.0 relative to any smooth latent distribution. Fit a censored/truncated model (and consider bunching estimators from the public-economics literature — the McCrary/Chetty style density-discontinuity toolkit applies) to estimate the latent mass above the limit: that mass is the fraction of designs that needed intervention to pass, i.e. THE quantified demand for pre-compliance tooling. Do this per segment, per year, per lab. Also check for heaping at round values (0.9, 0.95 of limit) which indicates design-to-target behavior, and test whether margin distributions differ by lab (a lab whose reported margins bunch implausibly tight at the limit is itself a finding — handle with statistical care and no defamatory framing). Be honest about identification limits: reported-value constructs (design target + uncertainty) partially decouple the reported number from physics, so run the analysis on measured values separately where extractable.
3. **PAG latency, measured.** Report-issue date and filing date vs grant date distributions, mmWave/PAG-listed devices vs others. The gap IS the pain the industry complains about; nobody has published its actual distribution.
4. **Lab market structure.** Share by segment, year, geography; concentration (HHI); specialization map (which labs own FR2 vs WiFi laptops vs XR); turnaround-time league table where dates permit. Note any effects of the FCC's 2024-25 accreditation removals of certain foreign labs.
5. **Failure and churn proxies.** Re-filing lineage (same product, multiple filings), Class II permissive changes touching RF exposure, dismissed applications if visible. Companies that paid twice are prospects.
6. **The simulation census.** Grep report text for simulation tool mentions (HFSS/Ansys, CST, FEKO, Sim4Life/SEMCAD, XFdtd, openEMS, "in-house"). Which OEMs file simulation reports, with what tools, since when. This dataset exists nowhere.
7. **The prospect table.** Score applicants on: margin tightness, re-filings, PAG exposure, filing volume, segment. Output a ranked CSV of ~100 organizations with the evidence per row (this is a sales asset — every row must survive being read back to the named company).
8. **The validation-target shortlist.** Filings with enough public geometry to rebuild in a simulation tool: antenna type + gain + power + distance present (WiFi 6E/7 style), or known Qualcomm mmWave modules with visible placement photos. ~30 candidates, ranked by rebuildability.
9. **Anything you find.** Seasonality, Smart-Transmit/time-averaging adoption curves, APD-vs-PD reporting adoption over time, the 0mm-testing trend, XR filings census. Surprises are welcome; label exploratory findings as such.

**Stage 3 — deliverables.**
- `data/` — raw cache + parquet (documented schema).
- `analysis/` — reproducible code (scripts or notebooks) for every figure and number.
- `REPORT.md` — the full findings, every claim traceable to data, uncertainty stated, negative results included.
- `IOF_NUMBERS.md` — one page: the 10-15 hardest numbers for a grant valorisation section, each with a one-line derivation. This has a real deadline (days, not weeks) — produce a preliminary version from the Stage 0 pilot immediately, then update.
- `prospects.csv` and `validation_targets.csv`.
- Publication-quality figures for the eventual public note (clean, honest axes, no chartjunk).

## Rules

- Work in a fresh directory OUTSIDE the aegis repo (e.g. `~/fcc6ghz/`), own git repo, bulk data gitignored. Do not commit data into the aegis repository.
- LLM extraction is fine and encouraged, but never single-pass-trusted: validate with a second pass or regex cross-checks on the money fields, and keep per-field provenance so any number can be audited in 30 seconds.
- This is public data used for market analysis — fine. Do not publish anything externally, do not contact anyone, do not present the prospect list as anything but public-record analysis.
- Honesty over impressiveness: if the censoring analysis is underpowered or the PAG dates aren't extractable, say so plainly and move on. A smaller true result beats a large fragile one.
- If you hit a real blocker (mirror bans you, official API needs a key, data is materially more hidden than described), STOP and report NEEDS_CONTEXT with what you tried, rather than silently degrading the project. Robin can provide keys, browser access, or hosting.
- Checkpoint reports at: pilot done, corpus done, each analysis done. Preliminary IOF numbers as early as possible.
