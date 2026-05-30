# AEGIS startup briefing for Preuve AI

Context document for external startup validation. Written as a factual briefing, not a pitch. The reader is expected to form an independent opinion on viability, positioning, competition, unit economics, timing, defensibility, and founder-market fit.

---

## 1. One-paragraph summary

AEGIS is a deployed software platform that computes per-point electromagnetic (EM) absorbed power density on 3D human body surfaces in milliseconds, using a closed-form method derived from a specific physics insight (pseudo-Brewster compensation in biological tissue at mmWave). This replaces full-wave FDTD/FEM simulations that currently take hours to days. The primary applications are ICNIRP 2020 regulatory compliance for 5G/6G base stations, exposure-aware MIMO beamforming, and antenna placement/tilt optimization under safety constraints. The platform covers 100 MHz to 100 GHz, integrates real antenna data from 14 government databases (~293k antennas), reconstructs 3D urban scenes from OpenStreetMap and Google Photorealistic 3D Tiles, and exposes a web-based 3D viewer plus REST API. Roughly 33k lines of Python, 21k lines of TypeScript, 2,469 automated tests. Currently pre-revenue, pre-incorporation, with an Invention Disclosure Form filed at UGent TechTransfer (April 2026) and zero prior public disclosures.

---

## 2. Founder profile

### 2.1 Principal founder: Robin Wydaeghe

- Age 27, Belgian citizen.
- Final-year PhD at Ghent University / IMEC, INTEC-WAVES group (Prof. Wout Joseph). Defense targeted before August 2026.
- Thesis topic is EM exposure from massive MIMO at 5G/6G frequencies using hybrid ray-tracing + FDTD. First-author peer-reviewed publications in IEEE Access (2022), npj Wireless Technology (2026). Third author on related work in IEEE Access (2025).
- Awards: two BioEM prizes, TEDx talk, competition placement using Sim4Life (the dominant commercial FDTD platform).
- Built AEGIS alone as a side effort to his PhD using heavy AI-assisted development (parallel Claude Code agents, Max plan). Approximately 54k lines of code, 2,469 tests, ~1,150 commits in a few months.
- Sole inventor of the geometric dosimetry framework. Zero prior disclosures.
- Background: RF dosimetry, computational EM, Bachelor's in physics (Burgerlijk ingenieur natuurkunde), IMEC environment.
- Communication style described in personal notes: casual, direct, prone to broad exploration of career alternatives (consulting, EU institutions, quant, FAANG) in parallel to the spin-off decision. Self-identified pattern of analysis paralysis.

### 2.2 Potential co-founder: Carolina Camacho Cadena

- PhD researcher, same lab (UGent INTEC-WAVES), same supervisor (Wout Joseph).
- PhD topic: EM effects on neurons (low-frequency EM, biological tissue interaction). Different frequency regime than AEGIS core.
- BSc Mathematics (Queen's University, Canada), MSc Neural Systems and Computation (joint ETH Zurich / University of Zurich).
- Entrepreneurial track record: two founded ventures (Spotlight for a Forgotten Light, Move and Restore), multiple hackathon wins, national competition nominee, Queen's Innovation Center bootcamp alumna.
- Skills: data science, ML, MATLAB, Python, R, statistics. English fluent, native Spanish.
- Would join as co-founder primarily to meet the imec.istart 2-founder requirement. Proposed 20% equity, 4-year vest, 1-year cliff. Role: BD, customer discovery, grant writing, pitching.
- Personal context: Robin and Carolina are a couple (same household). This is a known governance risk and is disclosed honestly in internal documents.

### 2.3 Supervisor and institutional backing

- Prof. Wout Joseph heads the EMF exposure assessment group at INTEC-WAVES and participates in ICNIRP/IEC/IEEE standards bodies. Active in the field for two decades.
- Prof. Luc Martens (co-PI of the group) is pursuing a commercial contact at Ericsson (NDA stage as of April 2026).
- UGent TechTransfer has a Fast Lane scheme (approved March 2025) for standardized IP licensing to spin-offs.
- IMEC recent spin-offs have 96% continuation (26/27 post-2017). KU Leuven spin-offs at 78% five-year survival (LRD data).

---

## 3. The problem

### 3.1 What the product solves

Wireless operators, equipment vendors, and regulators must demonstrate compliance with EM exposure limits (ICNIRP 2020 internationally, IEEE C95.1-2019 in the US). Above 6 GHz the governing metric is absorbed power density (S_ab, W/m^2) averaged over 1 cm^2 or 4 cm^2 of skin. Below 6 GHz it is whole-body or 10 g local SAR (specific absorption rate).

Today the compliance toolchain splits into two worlds:

1. Simple exclusion-zone calculators (IXUS, MVG EMF Visual, various national spreadsheet-based tools). Cheap, conservative, ignore body geometry. Accepted by most national regulators for basic siting. Overestimate exposure, which reduces allowable transmit power or creates larger mandatory "safety zones." This shrinks network capacity.
2. Full-wave solvers on anatomical phantoms (ZMT Sim4Life, Dassault CST Studio Suite, ANSYS HFSS). Accurate, differentiable-free, slow (hours to days per scenario), desktop software with expensive licenses (~50-60K EUR/year per seat per reports). Dominant in test labs, device certification, research, and ICNIRP/IEC standards work.

There is no middle tier. You either overestimate with simple math or run an FDTD campaign per configuration. A frequency sweep, a power sweep, an antenna tilt sweep, or a multi-beam MIMO sweep is computationally infeasible with full-wave tools at network scale. This is an inefficiency everyone in the field acknowledges.

### 3.2 Why now

- ICNIRP revised exposure guidelines in 2020. Above 6 GHz, absorbed power density is now a basic restriction (not just a derived quantity). Countries are progressively adopting 2020 terms (rollout is uneven).
- 5G FR2 (mmWave) deployments are live in the US, Japan, Korea, and parts of Europe. Sub-6 GHz remains the majority but mmWave is growing.
- 6G research has started in 3GPP and EU H2020/Horizon Europe programs. Frequencies proposed go up to 300 GHz.
- Network densification (small cells, urban MIMO) means antennas are closer to people than before.
- Public concern about 5G EMF is a recurring story. Operators and regulators have reputational incentive to have better tooling.

### 3.3 Why now is also ambiguous

- US mmWave deployment has slowed. T-Mobile returned some spectrum. Verizon pivoted investment toward C-band (mid-band).
- In the EU most 5G is at 3.5 GHz and below, where classical SAR applies and existing tools are considered adequate.
- There is no regulatory mandate forcing operators to do body-mesh dosimetry per site. Exclusion zones still meet the legal bar in virtually all EU countries.
- Adoption therefore depends on either (a) operators voluntarily buying better tooling to recover capacity from over-conservative exclusion zones, (b) vendors (Ericsson/Nokia) buying or integrating such tooling into planning suites, (c) regulators tightening rules, or (d) test labs absorbing the tool into their workflow.
- "Nobody does real-time body-specific dosimetry" is true. The honest counter-hypothesis is: nobody does it because nobody needs to. The market exists if (a)-(d) materialize, not before.

---

## 4. The technology

### 4.1 Physics insight

Two claims reduce a 3D volumetric EM problem to a surface computation:

1. Pseudo-Brewster compensation. For biological tissue (complex refractive index |n| ~ 3-7), the TE and TM Fresnel power transmissions are not individually flat with angle, but their unpolarised average stays within ~5.6% of the normal-incidence value T_0 between 0 and 75 degrees. This lets you use a single scalar T_0 instead of an angle-dependent transmission for many use cases. T_0 ~ 0.54 for skin at 28 GHz.
2. Surface confinement. Above ~6 GHz the skin depth is below 1 mm. Absorption is confined to a thin surface layer. The relevant quantity per point on the body is determined by the outward surface normal and the incident wave direction.

Combined:

```
S_ab(r) = S_inc * T_0 * ReLU[n_hat(r) . (-k_hat)]
```

That is, the absorbed power density at surface point r equals incident power density, times transmission coefficient, times the rectified cosine of incidence. For a multi-path/multi-antenna source this sums (incoherent) or coherently combines (via an exposure channel matrix G_tilde and an exposure operator Q = integral over body of G_tilde^H G_tilde dA).

Validation against independent literature (Bamba 2012/2015, Kodera 2024, Diao 2024, Flintoft 2014, Zhang) is reported at 3-8% error on absorbed power quantities. Mie regression against analytical lossy spheres at 28 GHz: R = 0.988.

### 4.2 Existing work the inventor cites as closest

- Kodera et al. 2024 (Phys. Med. Biol.): empirically extracted transmission coefficient SAR_wb = T_tr * A_perp * S_inc / W, within 5% of 3D FDTD from 10-100 GHz. No physical mechanism proposed, no spatial map, no 3D body extension.
- Li et al. 2019 (IEEE Access): numerical observation that transmitted flux is nearly insensitive to incidence angle on flat skin from 6 GHz to 1 THz. Flat slab only.
- Bamba et al. 2012/2015 (IEEE EMC): measured ~0.5 absorption efficiency in reverberation chambers. Empirical, no mechanism.
- Hochwald 2014, Ying 2015-2017 (IEEE TWC): SAR matrix formulation with QCQP precoder for uplink handset SAR. Matrix entries are FDTD-calibrated, not closed-form.
- Sim4Life, CST: full-wave numerical, not real-time, not differentiable, desktop licenses.

The AEGIS claim is to be the first to (a) derive T_0's near-constancy from Fresnel theory, (b) extend it to spatial maps on 3D bodies, (c) produce a closed-form exposure operator Q for MIMO, (d) make the whole computation graph differentiable, and (e) integrate all this into a real-time web platform.

### 4.3 Software state

Versioned v0.28.x at time of writing.

- Engine: 9 fidelity levels (0 = O(1) absorbed-power bound, ..., 8 = exposure-constrained MIMO precoder via analytical QCQP). Python + JAX. NumPy fallback.
- Frontend: React + Three.js + Zustand. Production 3D viewer with interactive antenna placement, multi-user MIMO, ICNIRP compliance dashboard, power/frequency sweeps, 3 optimization algorithms, guided tour, bug reporting.
- Backend: Flask REST API, 40+ endpoints, session auth, binary protocols for mesh transfer, SSE streaming for long jobs, Sentry error tracking, Umami analytics.
- Environment reconstruction: OpenStreetMap via Overpass (buildings with 12 roof types, roads, water, vegetation), Google Photorealistic 3D Tiles with material inference, SRTM terrain, GeoJSON, voxel import.
- Base station pipeline: 14 government APIs (Belgium, France, Germany, Denmark, Netherlands, Austria, Luxembourg, Poland, Spain, Switzerland, UK, Canada, Brazil, Australia, New Zealand) + OpenCellID. ~293k antennas. Pattern library of 1,200+ real antenna patterns via CloudRF. MSI file parsing for manufacturer radiation patterns (Kathrein, Commscope, Huawei).
- GPU ray tracing: Modal serverless deployment of DiffeRT (JAX, T4 GPU) and Sionna RT (OptiX, L4 GPU), with scene caching and compression.
- Stochastic channel: full 3GPP TR 38.901 cluster-based generator with 91 QuaDRiGa presets, spatially consistent large-scale parameters.
- Body models: 8 anatomical phantoms (Duke, Ella, Thelonious, Eartha, adult male/female, children), plus SMPL-X parametric body generation with poses.
- Compliance module: ICNIRP 2020 from 100 kHz to 300 GHz, spatially averaged S_ab at 1 cm^2 and 4 cm^2, whole-body SAR, margin in dB, maximum compliant TX power.
- Deployment: Docker multi-platform images, Hetzner cloud, Caddy reverse proxy with HTTPS, docker-compose stack with Gunicorn (2 workers, 4 threads), PostgreSQL for analytics. Live at aegis.waves-ugent.be (password-protected, inventor-only at present).
- Testing: 2,469 automated tests (143 files), pytest-xdist, Hypothesis property tests, CodSpeed benchmarking, golden tests against every monograph table. CI on GitHub Actions (Windows + Linux x Python 3.11/3.12/3.13).
- Theory reference: monograph_v2.tex, ~6,000 lines of LaTeX, all derivations, proofs, error analysis.

### 4.4 Limitations the inventor flags

- Far-field only (source > ~3 wavelengths = ~3 cm at 28 GHz). Does not apply to devices pressed against the body. Near-field extension in progress.
- Below ~6 GHz the local surface map loses physical meaning because multi-layer resonances become significant. Total-power results remain valid via flux-averaged T_bar. Sub-6 GHz spatial dosimetry remains in FDTD territory.
- Diffraction is approximate (GELU smoothing at shadow boundaries). ~10% error on total absorbed power for torso-sized bodies at mmWave.
- Dielectric tissue properties are uncertain at 10-20% in the literature. Framework error (2-6%) is smaller than this parametric uncertainty. Inherent field limitation.
- Tested and validated against published data, but not yet against full-wave FDTD on high-resolution anatomical phantoms in a formal comparison campaign.

### 4.5 Complementary asset: GOLIAT

The founder has a second codebase, GOLIAT, which is a 42k-line Python automation wrapper for Sim4Life FDTD. It produces volumetric SAR (whole-body, psSAR10g per tissue group) via the full Sim4Life pipeline (near-field phone-to-head, far-field plane waves, MaMIMO). Won a Sim4Life competition. Not public. Requires a Sim4Life license to run.

GOLIAT would give the startup sub-6 GHz coverage that AEGIS alone cannot provide geometrically. It also creates a validation path for AEGIS (compare matched scenarios in 2-6 GHz overlap). The licensing question is open (keep Sim4Life backend, replace with open-source FDTD like gprMax/openEMS/MEEP, or build minimal JAX FDTD from scratch).

---

## 5. Market

### 5.1 Market sizing

The analyst report the founder has seen sizes the "RF Planning and Optimization Software" market at ~$2.1B in 2024 growing to ~$6.4B by 2033 (13.2% CAGR). This is the broad market (Atoll, iBwave, Ekahau, Ranplan, ATDI class tools). AEGIS is not directly in this market. It is in a sub-slice focused on human EMF exposure.

There is no standalone "computational body-specific dosimetry" market size figure in public reports. Estimated bottom-up total addressable is 10-50M USD globally today, based on:

- ~100-150 major cellular operators worldwide.
- ~5 Tier-1 RAN vendors (Ericsson, Nokia, Samsung Networks, Huawei, ZTE).
- ~20-30 national regulators in markets where 5G deployment is active.
- ~50-100 test labs (Eurofins, Verkotan, PCTEST, SPEAG, UL, TUV, CETECOM).
- ~200 academic/research groups.
- ~10 device OEMs (Apple, Samsung, Xiaomi, Qualcomm, etc.) who already budget for compliance.

Assumed willingness to pay:

- Operators: 50-200K/yr for a tool that shows demonstrable capacity savings.
- Vendors: 200-500K/yr as OEM integration into planning suites.
- Test labs: 10-50K/yr as a computational dosimetry service line.
- Regulators: 20-50K/yr if they run their own audits.
- Academic: 5-10K/yr at most.

If you assume 10-20% penetration across these in a mature state, that lands in the 5-20M ARR range. Comparable exits in niche telecom SaaS tend to be 3-10x revenue (see section 7).

### 5.2 Customer segments (Tiers)

Tier 1. Infrastructure vendors. Ericsson (SE), Nokia (FI), Samsung Networks (KR), Huawei (CN), ZTE (CN), Qualcomm (US), MediaTek (TW). Integrate into network planning or chipset beamforming. Long sales cycles (12-18 months), strategic, highest-ticket.

Tier 2. Operators. Proximus (BE), KPN (NL), Orange (FR), Deutsche Telekom (DE), Vodafone (UK), Telefonica (ES), British Telecom, Telenor, TIM. Compliance during rollout. Very conservative buyers. Usually buy planning tools via the vendor relationship, not directly.

Tier 3. Network planning software vendors. ATDI (FR), Forsk (FR) with Atoll, InfoVista (FR/US), iBwave (CA), Ranplan (UK). Two paths: AEGIS as an embedded module inside their tool, or AEGIS displacing their tool for compliance-specific use cases. Integration path is more likely.

Tier 4. Simulation vendors. ZMT / Sim4Life (CH), Dassault / CST (FR), ANSYS (US), Remcom (US). Could license AEGIS as a fast pre-screening layer on top of their FDTD. Wout Joseph has explicitly suggested the Sim4Life path. ZMT is tightly coupled with SPEAG and IT'IS Foundation, which is the dominant EM dosimetry ecosystem in the world (Kuster playbook).

Tier 5. Test labs. Eurofins, Verkotan, PCTEST, SPEAG, UL, TUV, CETECOM. Short sales cycle (lab director decides). Highest-probability first customers per internal analysis.

Tier 6. Regulators. BIPT (BE), BNetzA (DE), ARCEP (FR), Ofcom (UK), FCC (US), ANFR (FR). They set rules but usually don't buy simulation tools. They might pay for audits or for their own internal reference.

Tier 7. Device OEMs. Apple, Samsung, Xiaomi. Pre-screening before certification.

Tier 8. Consultancies / EM-health NGOs / lobbies. Smaller but short sales cycles.

### 5.3 Current sales pipeline (as of April 2026)

- Zero paying customers. Zero signed LOIs. Zero pilot agreements.
- One active introduction through Prof. Luc Martens to an Ericsson contact, NDA-stage. No commitment beyond that.
- Prof. Wout Joseph has suggested pursuing ZMT / Sim4Life as a licensing partner and Nokia as a follow-on. Not initiated.
- No customer discovery calls have been conducted yet. Target is 20 calls across Tiers 1-5 before September 2026. Current count: 0.
- The founder's internal feedback (see personal/claude_career_advice_2.md) flags this as the single biggest risk: "the spin-off lives or dies on whether you can force yourself to do the uncomfortable work: cold-email a test lab, get on a call, show the demo, hear 'interesting but we don't need this,' and do it again."

---

## 6. Competition

### 6.1 Competitive map

| Capability                   | Sim4Life (ZMT) | CST (Dassault) | IXUS (Alphawave/EMSS) | MVG EMF Visual | ATDI / Forsk | AEGIS |
|---|---|---|---|---|---|---|
| Method                       | FDTD            | FEM/FDTD        | Zone-based             | Zone-based      | Propagation only | Closed-form surface + GPU RT |
| Speed per scenario           | Hours           | Hours           | Seconds               | Seconds         | Seconds      | Milliseconds |
| Body geometry                | Full 3D         | Full 3D         | None (zone)           | None (zone)     | None         | Full 3D mesh |
| Polarization                 | Exact           | Exact           | None                  | None            | None         | Exact TE/TM |
| Frequency range              | 0 Hz - 1 THz    | 0 Hz - 1 THz    | Limited               | Limited         | Limited      | 100 MHz - 100 GHz |
| Differentiable               | No              | No              | No                    | No              | No           | Yes (JAX end-to-end) |
| Real base station data       | No              | No              | Limited               | No              | Partial      | 14 gov databases |
| 3D environment from address  | No              | No              | No                    | No              | No           | OSM + 3D Tiles + SRTM |
| MIMO exposure operator       | No (per-beam)   | No              | No                    | No              | No           | Closed-form Q + ECBF |
| Interactive web viewer       | Desktop only    | Desktop only    | Web (2D zones)        | Web (2D zones)  | Desktop      | Web 3D |
| Reported license price       | ~50-60K/yr      | ~50K/yr         | mid-5-figures          | mid-5-figures   | 5-figures    | Not yet set |
| Typical user                 | Researchers, test labs | Researchers | Operators (zone-only) | Operators (zone-only) | Operators / vendors | N/A |

### 6.2 Adjacent plays

- Ekahau (WiFi planning) acquired by Ookla / Ziff Davis. Total raised $22M. Exit undisclosed, estimated $30-50M.
- UgenTec (lab software, istart alumni) exited at 90M EUR.
- Feops (cardio simulation, UGent spin-off) acquired by Materialise.
- Gatewing (drone mapping, UGent spin-off) acquired by Trimble.
- Caliopa (silicon photonics, UGent spin-off) acquired by Huawei.

### 6.3 Standards ecosystem (adjacent to competition)

- IT'IS Foundation (ETH Zurich) maintains the tissue database that almost every dosimetry tool uses. Spun out SPEAG (hardware) and ZMT (software). Dominant player in the field's ecosystem over ~20 years. Kuster playbook: publish -> standards -> hardware -> software -> database.
- IEC TC 106, IEEE ICES: where exposure assessment methods are standardized. Wout Joseph is active in these bodies.
- ICNIRP issues the guidelines (non-binding, but adopted by most EU states).
- IEC 63195-1 / 63195-2 / IEEE C95.1-2019 / IEEE C95.3-202x: computational and measurement procedures for incident/absorbed power density.

### 6.4 The "IT'IS is the moat" observation

Most dosimetry tools depend on IT'IS for tissue properties (Gabriel 1996 Cole-Cole parameters, anatomical phantoms, tissue segmentation). ZMT is owned/tied to IT'IS. Displacing ZMT as the dominant commercial dosimetry vendor requires either (a) building on top of IT'IS without threatening it, (b) partnering with IT'IS/ZMT (the licensing path Wout suggested), or (c) operating in a niche adjacent to but not colliding with them. AEGIS uses the IT'IS v5.0 SQLite dataset as input. Approach (b) is currently the explicitly favoured option.

---

## 7. Business model options

No business model has been committed to. The following are under consideration.

### 7.1 Option A: direct SaaS / API

Per-seat subscription to the web viewer + API access. Tiers:

- Free: synthetic scenarios only, throttled.
- Professional: 5-15K/yr per seat, real base station data, basic API.
- Enterprise: 30-100K/yr per organization, batch API, PDF compliance reports, SLA, private deployment option.

Revenue path: test labs and consultancies first (short cycle), operators second, vendors later.

Unit economics (assumed):

- Cost per tenant per year: under 1K EUR (Hetzner hosting + GPU bursts via Modal).
- Gross margin: 85-92% once past breakeven.
- CAC (telecom B2B enterprise): high. Field sales, travel to trade shows, 6-18 month cycles. Internal estimate: 20-50K per enterprise win. Unknown for test labs (probably lower).
- Payback: 12-24 months for enterprise.

### 7.2 Option B: OEM licensing into Sim4Life / CST / ATDI

License AEGIS as a fast pre-screening module inside an existing tool. Revenue share or fixed license. Advantages: leverages partner sales channel, short time-to-revenue once signed, validates the technology. Disadvantages: ceiling on margin, dependence on the partner's roadmap, possible delayed adoption internally.

### 7.3 Option C: Consulting / service

AEGIS as an expert service. Founder runs compliance analyses for clients at 200-500 EUR/hour. Advantages: immediate revenue, market intelligence, short cycle. Disadvantages: does not scale, locks the founder into delivery work rather than product.

### 7.4 Option D: Open core

Open-source the incoherent spatial kernel (levels 0-6) and sell the advanced features (coherent MIMO at 7-8, viewer, batch processing, enterprise). Advantages: adoption by researchers, citations, becoming the reference implementation, standards leverage. Disadvantages: levels 0-6 cover ~95% of practical compliance cases today, so open-sourcing them means open-sourcing the near-term revenue. Competitor with the open code and public monograph could commercialize faster than in a pre-LLM world.

Current posture: proprietary (LicenseRef-Proprietary on the code), but no public decision made.

### 7.5 Option E: acquisition target

Treat the company as an 18-36 month build-to-acquire. Target acquirers: Ericsson (40+ acquisitions historically), Nokia (41+ acquisitions), ZMT, Dassault. Acquire-hire range 2-10M EUR, niche strategic acquisition 10-30M, strong strategic fit 25-60M.

---

## 8. Unit economics and financial projections

### 8.1 Operating cost structure

AEGIS is a software-only company. Current non-salary burn:

- Cloud hosting (Hetzner + Modal + misc): 3-6K/yr.
- Domain, SaaS tools, analytics, email: 1-1.5K/yr.
- Travel (2-3 conferences/yr): 3-5K/yr.
- Legal/IP (one-time + ongoing): 5-10K + ~2K/yr maintenance.
- Accounting: 1.5K/yr.
- Patent filing Belgian national + PCT (if pursued): 5-15K one-time, maintenance fees thereafter.

Founder salaries:

- Robin: planned to be paid by VLAIO Innovation Mandate for 2 years (~45-55K gross/yr postdoc scale). Mandate 100% funded by the government, 0% equity cost.
- Carolina: remains on PhD salary through PhD completion, then would need salary coverage.
- No other hires planned in year 1.

Total burn excluding Robin's VLAIO-covered salary: 15-30K/yr. Total including founder salaries: 60-90K/yr.

### 8.2 Revenue scenarios at year 5

Internally estimated ranges:

- Conservative (zombie lane): 100-500K ARR. 3-10 small test-lab and consultancy customers. Survival but no exit.
- Base: 1-3M ARR. ~10-30 enterprise customers across tiers 1-5. Median niche B2B SaaS trajectory.
- Optimistic: 3-5M ARR. 1-2 Tier-1 vendor integrations. Position for Series A or strategic acquisition.
- Home run: 5-10M+ ARR. Standard-body reference status, Tier-1 OEM integration, 6G tailwind. Requires execution across all 4 of (a)-(d) in section 3.3.

### 8.3 Exit scenarios (from internal analyst reports)

| Scenario | Probability (internal estimate) | Exit value | Founder take-home (after dilution + Belgian cap gains tax, 2026+ regime) |
|---|---|---|---|
| Failure / wind-down | 15-20% | 0 | ~60K opportunity cost over 2-4 yrs |
| Lifestyle / zombie | 20% | Ongoing 100-150K/yr | Ongoing founder salary, no exit event |
| Modest exit | 25-30% | 3-10M | 1.5-6M net |
| Good exit | 20-25% | 10-25M | 5-14M net |
| Strong exit | 5% | 25M+ | 14M+ |

The founder's earlier external review (personal/claude_career_advice_1.md) explicitly flagged this scenario distribution as optimistic: "for a niche scientific software product without a regulatory mandate driving adoption, I'd flip those: 40-50% chance it becomes a modest lifestyle business or fizzles, 15-20% chance of a meaningful exit." Read this honestly.

### 8.4 Belgian tax treatment

- Capital gains tax regime effective Jan 1, 2026: first 1M EUR exempt for substantial shareholders (>=20%), above that graduated 1.25-10%.
- Innovation Income Deduction (IID): 85% deduction on qualifying IP income (copyrighted software qualifies). Effective max rate on IP income 3.75%. Competitive with Ireland (6.25%), Netherlands (9%).
- VVPRbis dividend regime for BVs: 20% CIT + 15% withholding = ~32% combined after 3 fiscal years.

### 8.5 Dilution model

Bootstrapped via Belgian grants path:

| Event | Equity given | Cumulative founder ownership |
|---|---|---|
| Start | 0 | 100% |
| UGent IP license (typical) | 2-5% | 95-98% |
| imec.istart base (100K) | 6% | 89-92% |
| Employee option pool | 5-10% | 79-87% |
| Optional seed (1.5M at 5M pre) | 23% | 56-64% |
| Optional Series A | 15-25% | 40-55% |

The Belgian grant ladder lets a founder retain 80-90% through the pre-revenue phase, significantly higher than the US default. This is a unique feature of the jurisdiction.

---

## 9. Funding path (Belgian-specific context)

This is the most unusual structural feature of the opportunity. Belgium has a staircase of non-dilutive and low-dilutive funding designed specifically for university spin-offs. The founder plans to use it.

### 9.1 VLAIO Innovation Mandate (spin-off track)

- Funded postdoc mandate for up to 2 years, full salary (~100-110K gross total), 0% equity cost, 100% government funded.
- Requires PhD diploma, academic supervisor sign-off, industrial mentor commitment, cooperation agreement within 4 weeks of submission.
- Deadlines twice a year (March / September). Results ~6 months later. Founder is targeting the September 2026 call.
- Can include side activities. 20-25 weekly hours nominally on spin-off, majority on "research activities" (permissive interpretation in practice).

### 9.2 IOF (Industrial Research Fund, UGent)

- Fast Lane IP licensing scheme (approved March 2025): predefined conditions, no lengthy IP negotiation.
- StarTT / ConcepTT: 50-125K for 1-2 years of technical milestone funding. Non-dilutive.
- Stepstone: up to 400K over 3 years for spin-off acceleration. Non-dilutive. Larger than needed for this business.
- Mandatory intake meeting before submission.
- Deadlines: 21 April 2026 (too tight), 3 August 2026 (feasible), 19 October 2026.

### 9.3 imec.istart

- UBI Global ranking: #1 worldwide in 2019 and 2023, #4 worldwide in 2025 (#1 in Europe).
- 341+ startups since 2011, 84% continuation, ~1B EUR cumulative follow-on funding, 17-20x leverage on investment, 13+ exits, 1 unicorn (Deliverect).
- Pre-seed terms (current, April 2026): 100K EUR = 50K for 6% equity + 50K as convertible loan. Up to 150K additional during the program.
- 12-month program. Dedicated business coach 6-18 months. Expert-in-Residence embedded 1-2 days/week for 3 months.
- Requires minimum 2 founders for the main program. Solo founders go to the lesser Launch Program.
- Application deadlines: 1 Feb, 1 Jun, 1 Oct per year. Founder is targeting 1 Oct 2026.
- IP policy: imec claims no IP on istart projects. Founder-friendly.
- Telecom/Media/Entertainment vertical. Telenet (Belgian operator) is a partner. Potential direct path to an operator pilot.

### 9.4 KBC Start it (parallel, zero-equity accelerator)

- 12 months, zero equity, zero cost. Can be combined with imec.istart.
- Start it Fund (Dec 2025): EUR 100M committed. Top ~5 startups per cohort get EUR 300-450K convertible loan at end of program. Follow-on up to EUR 5M via KBC Securities.
- 73% 5-year survival rate for alumni (vs 51% international benchmark).
- Fall 2026 applications are the target.

### 9.5 Aggregated funding envelope

Theoretical ceiling (stacking everything non-dilutive + istart base): ~760K EUR for roughly 6% equity dilution. Realistic target for the business (which has ~15-30K/yr non-salary burn): 260-335K, specifically:

- VLAIO mandate: ~110K (salary, fixed)
- istart base: 100K
- IOF StarTT or ConcepTT: 50-125K for a specific technical milestone

The key feature for a validator to weigh: the downside scenario here is "2 years on a postdoc salary working on your own IP in a university environment." Failure opportunity cost is roughly 33-60K over 2-4 years, far below the US bootstrap-or-burn default.

---

## 10. IP position

### 10.1 Current status

- Invention Disclosure Form (IDF) filed at UGent TechTransfer on April 1, 2026, revised April 15, 2026.
- Sole inventor: Robin Wydaeghe. 100% contribution. Zero prior disclosures (no oral presentations, posters, publications, NDAs, demos).
- AEGIS viewer deployed on a password-protected server accessible only to the inventor.
- No prior funding tied to the invention (no grants, contracts, material transfer agreements).
- UGent IP regulations (Codex Hoger Onderwijs Art. II.285) give UGent first right to commercialize.
- Fast Lane scheme available for standardized IP licensing.

### 10.2 Patent strategy

- An IDF is not a patent application. It does not establish a legal priority date.
- EPO enforces absolute novelty (no grace period for inventor's own disclosures, unlike US).
- PhD thesis (public on repository after defense) will constitute a disclosure. Defense planned before August 2026.
- Therefore: a patent application (at minimum Belgian national, ~1,500 EUR) must be filed before the PhD defense. Timeline is tight (5-12 weeks realistic from TechTransfer engagement to filing).
- Wout Joseph is cautious about patentability (methods/algorithms). Luc Martens is more optimistic. The suggested claims cover (a) core spatial dosimetry method, (b) exposure operator + QCQP precoder, (c) differentiable optimization method, (d) integrated compliance system, (e) medium claims.
- Three referenced prior-art patents from Samsung and others cover device-level SAR control. AEGIS is distinguished as infrastructure-level body-surface computation, not device sensing.
- Freedom-to-operate (FTO) search not yet conducted.

### 10.3 Publication plan

- Monograph (~6000 lines LaTeX) drafted, not submitted.
- JSAC Special Issue on Digital Twins for Wireless Networks, submission deadline 1 May 2026 is a candidate (confidential peer review does not constitute disclosure; paper becomes prior art only on publication ~Sep 2026).
- PMB or IEEE TEMC for core theory (post patent filing).
- Standards body participation (IEC TC 106, IEEE ICES) is the long-term credibility play. Wout's existing relationships provide a path.

### 10.4 Trade-secret component

The mathematical method will be public (thesis + monograph + journal papers). Trade secret protection applies to the implementation: optimization heuristics, viewer UX, integration pipelines, enterprise features, operational tricks. The method is not defensible post-thesis; implementation and execution speed are.

---

## 11. Timeline

Approximate schedule as of April 2026:

- **Now (Apr 2026):** IDF filed, patent path being initiated with UGent TechTransfer. Customer discovery not yet started. No paying customers. No LOIs.
- **May-June 2026:** Schedule IOF intake meeting. Attend Gentrepreneur Research Track (2-3 or 2-17 June). Engage patent attorney. Begin customer discovery calls. Potentially submit JSAC paper (1 May) under confidential review.
- **July-August 2026:** PhD defense (hard deadline to remain eligible for September VLAIO call). Patent application filed before defense. Industrial mentor confirmed for VLAIO. IOF application (3 August deadline) submitted if aligned.
- **September 2026:** VLAIO Innovation Mandate application submitted.
- **October 2026:** imec.istart Autumn call submitted (1 October). KBC Start it Fall cohort application.
- **Nov-Dec 2026:** istart pitch / jury. VLAIO panel.
- **Jan-Mar 2027:** VLAIO results (March). If both accepted, 2 years of postdoc salary + 100K istart + coaching with <6% dilution.
- **Mid-2027 milestone:** First paying customer or signed LOI. If neither, kill or pivot.
- **End of 2027:** BV incorporation (triggers end of VLAIO mandate).
- **2028-2029:** Pre-seed / seed conversations, Tier-1 enterprise pilots, potential OEM integration.

Internal advisory documents flag an 18-month hard kill date: if by mid-2027 there is no paying customer or LOI, founder should pivot or wind down rather than zombie-drift. Belgium has 8.8% zombie firm rate (third-highest in OECD). 14% of Belgian companies are loss-making for 3+ years.

---

## 12. Explicit risks and internal counterpoints

The internal strategic documents include unusually blunt self-criticism. Faithfully represented here:

### 12.1 Market risk

- No regulatory mandate requires body-mesh dosimetry today. Exclusion zones are legally sufficient in virtually all EU countries. If operators are the target customer, adoption requires them to voluntarily buy a tool that reduces unnecessarily conservative exclusion zones. Voluntary, niche, enterprise sales are slow.
- The $2.1B RF planning market cited in the pitch deck is not AEGIS's market. The actual addressable market is probably 10-50M globally today, generously.
- US mmWave slowdown is real. Verizon pivoted to C-band. 6G is still early research.
- "Nobody does body-specific real-time dosimetry" may be because nobody needs to yet.

### 12.2 Founder risk

- Founder self-identifies as prone to analysis paralysis. Has not yet conducted a single customer discovery call as of April 2026. The path depends on converting to outbound sales mode, which is not the founder's current strength or habit.
- Heavy parallel interest in alternative careers (MBB consulting, FAANG Belgium, EU institutions, quant finance). Internal advisory flags this as procrastination dressed as research. External document suggests setting a hard 18-month kill date.
- "20-25 focused hours per week" on the spin-off is explicitly stated. Whether this suffices for enterprise B2B sales cycles with a market of perhaps 200 potential customers worldwide is open.

### 12.3 Co-founder risk

- Carolina is (a) the founder's partner, (b) employed to meet the istart 2-founder gate, (c) technically from a different subfield (low-frequency EM on neurons vs above-6-GHz geometric dosimetry).
- Internal critique: "Investors at istart aren't stupid. The vesting cliff protects you financially, but the governance risk of a couple co-founding is real, and the 'equity stays in household' framing will not reassure external investors at seed stage."
- Counter-argument: she has real entrepreneurial experience (2 founded ventures, hackathon wins, national competition), speaks Spanish (Latin American telco angle), brings BD/grant-writing capacity. Shared promotor may smooth operational alignment.

### 12.4 Competitive risk

- Sim4Life / ZMT ecosystem has ~20 years of accumulated standards and hardware moat. Partnering is the sensible path. Displacing them head-on is unrealistic.
- With AI-assisted development widely available, a competitor with the open monograph and any open-sourced kernel could replicate commercial features faster than pre-LLM dynamics suggest.
- Large vendors (Ericsson, Nokia) may buy in-house rather than integrate a third-party tool.

### 12.5 Customer sales cycle risk

- Tier 1 vendor sales cycles: 12-18 months. "Luc is pursuing an NDA" is step 0.5 of a 50-step process.
- Standards body adoption (IEC / IEEE) takes years. Worth pursuing but not a short-term revenue driver.
- Operators buy via vendor relationships, not directly from startups.

### 12.6 Zombie risk

- Internal analysis considers this the dominant failure mode. 4-5 years of prime career years locked into a small company with 3-5 non-growing customers and no acquirer interest. "Survival" in official statistics is not the same as "thriving."
- The founder's prior behavior pattern (investing research without investing money in LETFs for 2.5 years) is cited internally as a precedent for this failure mode at an emotional level: thorough analysis, delayed commitment.

### 12.7 Offsetting factors (also from internal documents)

- Belgian institutional safety net: VLAIO salary for 2 years at 0% equity is a genuine near-zero-downside option. Opportunity cost in failure scenario estimated 33-60K.
- Technology maturity: 54k lines of code, 2,469 tests, deployed production viewer is an atypical head start for a pre-seed deep tech.
- Clear IP position: sole inventor, no prior disclosures, no co-funders, no collaborators claiming invention.
- Supervisor access to Tier-1 vendor (Ericsson NDA path) and Tier-4 partner (ZMT licensing path), plus direct standards bodies.
- Credible EU career fallback if the business fails (ex-founder + PhD + industry exposure = ETNO, GSMA, BEREC, DG CONNECT attractive profile).

---

## 13. What the founder wants the validator to weigh

The founder has already read extensive internal analysis and several rounds of external advice. The following are the open questions where an independent view would help most.

1. Is the core market thesis (operator adoption of body-specific dosimetry) likely to materialize within the 3-5 year window, or is it permanently stuck behind conservative exclusion-zone regulation?
2. If the market does not materialize on the operator side, which of (test labs, simulation vendors, chipset vendors, standards bodies, regulators) is the most realistic first-revenue path, and at what price?
3. Given AI-era development speed, does the closed-form method + monograph + any open-source kernel create a durable moat, or does the method inevitably become a commodity once published?
4. Is the co-founder structure (20/80 to the founder's partner, to meet a program gate) a tolerable governance arrangement for an external investor, or should the founder restructure (solo Launch track, different co-founder, advisor-only) before pitching?
5. Is the Belgian institutional path (VLAIO + IOF + istart + KBC) sufficient to reach first revenue without external VC, and does that materially change the optimal commercial positioning (licensing vs SaaS vs acquire-hire target)?
6. Given the founder's self-reported analysis paralysis pattern and the absence of customer discovery to date, is this founder-market fit sound, or should the founder preferentially seek a commercial co-founder with enterprise B2B sales experience before attempting a VLAIO / istart application?
7. Is an 18-month kill date (if no paying customer or signed LOI by mid-2027, wind down) a reasonable checkpoint for this market's sales cycle?
8. What comparable European deep-tech spin-offs should be benchmarked for realistic financial projections (UgenTec, Feops, Caliopa, Deliverect) and how do they map to AEGIS's specific sub-niche?

---

## 14. Key primary-source references

- Invention Disclosure Form: `spinoff/IDF_geometric_dosimetry.md`
- Feature inventory (product surface area): `docs/internal/features.md` and `spinoff/AEGIS_feature_inventory.md`
- Theory (full monograph): `theory/monograph_v2.tex`, `theory/summary_paper.tex`
- Spin-off feasibility and career report: `spinoff/AEGIS_Spin-off_Career_Report.md`
- Co-founder and istart analysis: `spinoff/AEGIS_Report_CoFounder_and_iStart.md`
- Commercial moats + strategy: `spinoff/commercial_moats_and_strategy.md`
- GOLIAT + AEGIS synergy (sub-6 GHz story): `spinoff/GOLIAT_AEGIS_synergies.md`
- Publication and IP strategy: `spinoff/publication_and_opensource_strategy.md`
- 12-month roadmap: `spinoff/ROADMAP_12_months.md`
- Events and accelerator research: `spinoff/events_and_kbc_startit_research.md`
- Internal external-advisor letters with blunt critique: `spinoff/personal/claude_career_advice_1.md`, `claude_career_advice_2.md`
- Live deployed viewer: `aegis.waves-ugent.be` (password-protected).
- Repo: ~33k Python + ~21k TypeScript, 2,469 tests, 1,150+ commits.

---

*End of briefing.*
