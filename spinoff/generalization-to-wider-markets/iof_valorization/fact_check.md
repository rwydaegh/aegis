# Fact check for the IOF StarTT valorization section

Compiled 2026-07-13. Every claim below was checked against a primary or near-primary source and the URL is given. Where a claim could not be confirmed it is listed at the bottom under "NOT VERIFIED - do not use" rather than softened.

Confidence key:
- **HIGH** = read in the primary document itself (standard text, official register, regulator PDF).
- **MEDIUM** = authoritative secondary source (standards body page, trade press, vendor page) but not the primary document.
- **LOW** = single non-authoritative source, data broker, or blog. Do not put a LOW number in the proposal without hedging.

---

## 1. Standards

### 1.1 IEC/IEEE 63195 series (devices, 6 GHz to 300 GHz)

The series title is "Assessment of power density of human exposure to radio frequency fields from wireless devices in close proximity to the head and body (frequency range of 6 GHz to 300 GHz)". It splits into four parts. **Parts 1 and 2 cover incident power density. Parts 3 and 4 cover absorbed power density and are both still drafts.** This is the single most useful standards fact in the whole check.

| Part | Subject | Quantity | Status | Date |
|---|---|---|---|---|
| 63195-1 | Measurement procedure | Incident/surface power density (PD) | **Published**, Ed. 1.0 | 2022-05-11 (IEC/IEEE); EN version 2023 |
| 63195-2 | Computational procedure | Incident/surface power density (PD) | **Published**, Ed. 1.0 | 2022-05-11 (IEC/IEEE); EN version 2023 |
| 63195-3 | Measurement procedures for **absorbed** power density | APD | **Draft** (active PAR) | PAR approved 2024-09-26 |
| 63195-4 | Computational procedures for **absorbed** power density | APD | **Draft** (active PAR) | PAR approved 2024-09-26 |

Sources:
- 63195-1: https://webstore.iec.ch/en/publication/62755 (Ed. 1.0, 2022-05-11) and https://ieeexplore.ieee.org/document/9770427/
- 63195-2: https://webstore.iec.ch/en/publication/62754 (Ed. 1.0, 2022-05-11) and https://ieeexplore.ieee.org/document/9770556
- 63195-3 (draft PAR): https://standards.ieee.org/ieee/63195-3/11781/
- 63195-4 (draft PAR): https://standards.ieee.org/ieee/63195-4/11782/

Confidence: **HIGH** for parts 1/2 (IEC webstore record read directly). **HIGH** for the existence and draft status of parts 3/4 (IEEE SA project pages read directly). **MEDIUM** for the exact PAR approval date of 2024-09-26 (taken from the IEEE SA project page rendering; if the jury may check, phrase as "PAR approved in late 2024").

**Answer to your specific question:** Yes, there is a part covering computational/simulation determination of absorbed power density above 6 GHz. It is **IEC/IEEE P63195-4, "Part 4: Computational Procedures for Absorbed Power Density"**. It is **not yet published** - it is an active project with a PAR approved 26 September 2024. Its scope covers devices operating at up to 200 mm from the head or body, 6-300 GHz.

**The part of this that is load-bearing for you:** P63195-4 specifies **FDTD and FEM** as the computational procedures ("The computational procedures described are finite-difference time-domain (FDTD) and finite element methods (FEM), which are used to determine electromagnetic quantities by solving Maxwell's equations"). So the standard that will govern computational APD is, right now, being written around exactly the two methods you are trying to displace, and it is still open. That is a defensible "the window is open now" argument. Source: https://standards.ieee.org/ieee/63195-4/11782/ (confidence MEDIUM-HIGH; the same FDTD/FEM wording appears in the published 63195-2, which I confirmed at the IEC webstore).

Caveat to avoid overclaiming: 63195-2 (published, computational) is about **incident** power density, not absorbed. Do not write "IEC/IEEE 63195-2 governs computational absorbed power density" - that is wrong.

### 1.2 IEC 62232 (base stations) and IEC TR 62669 (case studies)

**IEC 62232** - "Determination of RF field strength, power density and SAR in the vicinity of base stations for the purpose of evaluating human exposure".

- Ed. 2.0: 2017.
- Ed. 3.0: **2022** (2022-10). https://webstore.iec.ch/en/publication/64934
- Ed. 4.0: **2025-04-29**, 738 pages. It "cancels and replaces the third edition published in 2022" and "has the same technical content as the third edition" - it is an error-correction/editorial edition only. https://webstore.iec.ch/en/publication/89073

Confidence: **HIGH** (IEC webstore record read directly). Note: your proposal should say "current edition is IEC 62232:2025 (Ed. 4.0), technically identical to Ed. 3.0 (2022)". Saying "an edition 3 is in preparation" would be out of date.

Scope, per the standard: 110 MHz to 300 GHz; specifies both measurement and computation methods; explicitly compatible with ICNIRP 1998, ICNIRP 2020, IEEE C95.1-2019 and Safety Code 6; content includes **product compliance boundaries** and **product installation compliance boundaries (including pre-existing exposure)**, plus the **actual maximum approach**. Source: Christophe Grangeat (Nokia, Convenor of IEC TC106 MT3), "Base stations RF-EMF exposure assessment methods standardization", 13th GSMA EMF Forum, Brussels, 2024-10-01: https://www.gsma.com/solutions-and-impact/connectivity-for-good/public-policy/wp-content/uploads/2024/10/Grangeat_GSMA_EMFForum_2024_IEC-TC106-MT3-62232-TR62669-Tutorial.pdf (confidence **HIGH** - this is the convenor of the maintenance team presenting the standard's own content). "Compliance boundary" is the standard's term; it is what you are calling exclusion zone / compliance distance.

**IEC TR 62669** - "Case studies supporting IEC 62232".

- Ed. 2.0: **2019** (published, current). 16 case studies from 8 national committees. https://webstore.iec.ch/en/publication/62014
- Ed. 3.0: **in development, not yet published.** IEC stage 50.60 ("Close of voting. Proof returned by secretariat"), estimated completion 2026-06-19 per the standards register. Grangeat's 2024 GSMA deck said publication was expected 1H-2025 and it slipped. Ed. 3.0 will have 30+ case studies from 13 national committees, adding case studies on the actual maximum approach, extrapolation of 5G massive-MIMO signals, and "emerging laboratory measurement methods related to ICNIRP 2020".
- Register entry: https://genorma.com/en/standards/iec-tr-62669-ed3 (confidence **MEDIUM** for the stage/date - it is a standards reseller mirroring the IEC register, not the IEC register itself). The content of Ed. 3.0 is **HIGH** confidence (Grangeat deck, slide 30).

So: "what is in preparation" = **IEC TR 62669 Ed. 3.0**, not a new edition of 62232.

### 1.3 ICNIRP 2020 - basic restrictions above 6 GHz

All of the following was read directly out of the ICNIRP 2020 guidelines PDF, *Health Physics* 118(5):483-524 (May 2020). DOI 10.1097/HP.0000000000001210. Free PDF: https://www.icnirp.org/cms/upload/publications/ICNIRPrfgdl2020.pdf

**Confirmed.** Above 6 GHz the relevant local basic restriction is **absorbed power density Sab in W/m^2**, averaged over **6 min** and a **square 4 cm^2 surface area of the body**. Table 2, p. 491:

| | 100 kHz - 6 GHz | >6 GHz - 300 GHz |
|---|---|---|
| Occupational, whole-body avg SAR | 0.4 W/kg | 0.4 W/kg |
| Occupational, local head/torso SAR | 10 W/kg | NA |
| Occupational, **local Sab** | NA | **100 W/m^2** |
| General public, whole-body avg SAR | 0.08 W/kg | 0.08 W/kg |
| General public, local head/torso SAR | 2 W/kg | NA |
| General public, **local Sab** | NA | **20 W/m^2** |

Table 2 notes, verbatim: "Local SAR and Sab exposures are to be averaged over 6 min." and "Local Sab is to be averaged over a square 4-cm2 surface area of the body. Above 30 GHz, an additional constraint is imposed, such that exposure averaged over a square 1-cm2 surface area of the body is restricted to two times that of the 4-cm2 restriction."

Whole-body-average SAR is averaged over 30 min (not 6). Do not conflate.

Confidence: **HIGH** (read the table).

### 1.4 The load-bearing legal claim: basic restrictions vs reference levels

This is confirmed, with explicit language, in three places in ICNIRP 2020. Use these quotes.

**(a) Compliance against *either* is sufficient - you do not need both.** ICNIRP 2020, p. 491:

> "To be compliant with the present guidelines, for each exposure quantity (e.g., E-field, H-field, SAR), and temporal and spatial averaging condition, either the basic restriction or corresponding reference level must be adhered to; compliance with both is not required."

And in the Guidelines Summary, p. 485:

> "an exposure is taken to be compliant with the guidelines if it is shown to be below either the relevant basic restrictions or relevant reference levels."

**(b) Reference levels are conservative - they are strictly a worst-case proxy, and in normal cases the actual body absorption is far below the basic restriction.** ICNIRP 2020, p. 485:

> "As a conservative step, reference levels have been derived such that under worst-case exposure conditions (which are highly unlikely to occur in practice) they will result in similar exposures to those specified by the basic restrictions. It follows that in the vast majority of cases, observing the reference levels will result in substantially lower exposures than the corresponding basic restrictions allow."

And p. 494:

> "Reference levels have been derived from a combination of computational and measurement studies to provide a means of demonstrating compliance using quantities that are more-easily assessed than basic restrictions, but that provide an equivalent level of protection to the basic restrictions for worst-case exposure scenarios. However, as the derivations rely on conservative assumptions, in most exposure scenarios the reference levels will be more conservative than the corresponding basic restrictions."

**(c) There is a regime where the reference level is *not even allowed* and you *must* assess the basic restriction.** ICNIRP 2020, p. 495, and repeated as note 6 under the reference-level tables:

> "for exposure within the >2 to 300 GHz range, within the reactive near-field the quantities applied for the reference level values are treated as inadequate to ensure compliance with the basic restrictions. In such cases, compliance with the basic restrictions must be assessed."

Table 6 note, verbatim: "within the reactive near-field zone, reference levels cannot be used to determine compliance, and so basic restrictions must be assessed."

Confidence: **HIGH** on all three. All quotes read from the ICNIRP PDF.

**How to phrase this in the proposal so it survives a jury:** ICNIRP 2020 permits compliance to be demonstrated against *either* the basic restriction or the reference level; the reference level is a conservative proxy that in most real scenarios over-predicts body absorption; and above 2 GHz in the reactive near field the reference level is not permitted at all, so the basic restriction (i.e. absorbed power density in the body) *must* be computed. IEC 62232 is the standard that operationalises this for base stations, and it explicitly contains both computation methods and compliance-boundary determination.

Do **not** write "ICNIRP says you can exceed the reference level". It does not say that. What it says is that the reference level is one of two alternative routes to compliance, and the basic restriction is the other, more permissive-in-practice one. That is enough for your argument and it is exactly true.

---

## 2. The economic constraint

### 2.1 The strongest single citation: ITU-T K Supplement 14

**ITU-T K Suppl. 14 (09/2019), "The impact of RF-EMF exposure limits stricter than the ICNIRP or IEEE guidelines on 4G and 5G mobile network deployment."** Approved 2019-09-20 (Ed. 2.0; Ed. 1.0 was 2018-05-25). Free PDF: https://www.itu.int/rec/T-REC-K.Sup14-201909-I/en

Verbatim findings (I read the PDF):

- Scope of the problem: "a small group of countries, regions or even cities within the same country, especially in Europe (e.g., Poland, Russia, Italy, Switzerland, the city of Paris and regions of Belgium), use limits that are 10 to 100 times lower" than ICNIRP.
- **Poland simulation, site count:** "operators would have to have 3.5-fold the number of sites in urban areas by 2025 and almost sevenfold the number of sites in dense urban areas by 2025".
- **Poland simulation, unserved demand:** "in 2020, it is projected that 22% of available total mobile data traffic demand cannot be served (of which 31% of urban traffic demand and 63% of dense urban traffic demand remain unserved). In 2025, this number would increase to 41% and in 2030 to up to 56%."
- **Conclusion, verbatim:** "Investigation shows that in the next 3 years up to 63% of mobile data traffic demands will not be served in countries, regions and even specific cities where RF-EMF limits are significantly stricter than the [ICNIRP 1998] or [IEEE C95.1] guidelines."
- Poland's limit at the time: **7 V/m** across 10 MHz - 10 GHz, vs ICNIRP's 28-61 V/m (Table 1).

Confidence: **HIGH**. This is an ITU-T deliverable with contributions from Poland, Ericsson, Nokia, GSMA, Vodafone, Huawei and others - a jury will accept it. Caveat: it is a 2019 document based on ICNIRP 1998 and the Polish limits have since changed (see below), so cite it as evidence that *strict limits constrain deployment*, not as a current description of Poland.

### 2.2 Belgium / Brussels-Capital Region - verified, and it is a strong story

**The 6 V/m limit.** Brussels-Capital Region had a cumulative limit of **6 V/m** (at 900 MHz reference), in force from 3 April 2014, under the ordinance of 1 March 2007. It was the strictest such limit in Europe.

**The regulator said, in writing, that it made 5G impossible.** BIPT (Belgian Institute for Postal Services and Telecommunications), "Study of 12 September 2018 on the impact of the radiation standards in Brussels on the deployment of mobile networks":
https://www.bipt.be/file/cc73d96153bbd5448a56f19d925d05b1379c7f21/b789103a289430580cabea768599885ac43bf796/Study_impact_radiation_standards_Brussels_deployment_mobile_networks.pdf

Verbatim from the conclusions (p. 19):

> "The 6 V/m standard does not allow to deal with the expected increase in mobile data traffic, regardless of the technology used to transport this data."

> "The 6 V/m standard does not allow to deploy 5G in Brussels."

> "BIPT strongly advises against a cumulative limit under 14.5 V/m at a frequency of 900 MHz."

> "Therefore, BIPT proposes to adopt the standard above 14.5V/m and up to 41.5V/m."

The study was commissioned by two ministers (Alexander De Croo, telecoms; Céline Fremault, environment). De Croo's letter, quoted in the study: "In Brussels particularly, the imposed standard (6 Volts per metre on a cumulative basis for all operators) makes it impossible to invest in 5G and an increasing number of congestion problems will arise for 4G."

Confidence: **HIGH** (read the BIPT PDF). This is a national regulator saying in an official study that the limit blocked 5G. It is the best single citation you have for the economic-constraint argument, and it is Belgian, which is ideal for a Flemish jury.

**What happened next - the limit was raised.** The 1 March 2007 ordinance was amended on **2 March 2023**. Current limits in Brussels-Capital Region, at the 900 MHz reference frequency:
- **Outdoors: 14.57 V/m** (0.5635 W/m^2)
- **Indoors: 9.19 V/m** (0.2243 W/m^2)

Source: Bruxelles Environnement / Leefmilieu Brussel, "Wat zijn de wettelijke normen voor blootstelling aan elektromagnetische golven?": https://leefmilieu.brussels/burgers/wetgeving/wetteksten/wat-zijn-de-wettelijke-normen-voor-blootstelling-aan-elektromagnetische-golven
Implementing decree: Besluit van de Brusselse Hoofdstedelijke Regering van 08/06/2023: https://etaamb.openjustice.be/nl/besluit-van-de-brusselse-hoofdstedelijke-regering-van-_n2023042811.html

Confidence: **HIGH** for the values and the 2023 amendment (regional environment agency's own legal page). Note that 14.57 V/m is still roughly a factor 3 below the ICNIRP general-public reference level at 900 MHz (~41 V/m), i.e. **Brussels is still ~8x stricter in power density than ICNIRP.** The constraint is relaxed, not gone. That is the honest framing: the pressure that produced the 2023 change is still there, and BIPT itself said 14.5 V/m "is a threshold that will have to be rapidly revised upwards".

BIPT also documents the intra-Belgian asymmetry: after the change, "standards in Brussels will be 7 times more stringent than the Flemish standards and more than 2 times more stringent than the Walloon standards" (BIPT 2018, section 4.1).

### 2.3 Italy - verified

- Old limit: **6 V/m** attention value / quality objective (with a 20 V/m general limit); the restrictive limits apply to homes, schools, and buildings for prolonged human occupancy, i.e. most of the urban territory.
- **Raised to 15 V/m.** Legal instrument: **Law 214/2023 of 30 December 2023**, amending the Electronic Communications Code (D.Lgs. 259/2003). **Entered into force 29 April 2024.** New values: E = 15 V/m, H = 0.039 A/m, S = 0.59 W/m^2.
- Source (Italian Ministry of Enterprise and Made in Italy, MIMIT): https://www.mimit.gov.it/it/notizie-stampa/adeguamento-dei-limiti-dei-campi-elettromagnetici and the MIMIT slide deck https://www.mimit.gov.it/images/stories/documenti/slide_innalzamneto_campi_elettromagnetici_v6.pdf
- Confidence: **HIGH** for 15 V/m / Law 214/2023 / 29 April 2024 (ministry's own page). **MEDIUM** for the exact characterisation of the pre-2024 6 V/m regime (see academic source below, which is where I'd cite it from).

**Academic evidence that the Italian limits actually saturated the network:** A. S. Cacciapuoti, L. Chiaraviglio, G. Di Martino, M. Fiore, "5G Planning under EMF Constraints", 5G Italy White eBook (2018/2019): https://www.5gitaly.eu/2018/wp-content/uploads/2019/01/5G-Italy-White-eBook-5G-planning-under-EMF-constraints.pdf

Verbatim: "two distinct classes of limits are introduced by the italian law: (i) general limits that are in most cases around 30% lower than the ICNIRP ones, and (ii) restrictive limits that are 10 times lower than the ICNIRP ones. The restrictive limits apply in fact to a vast portion of the national territory". And: "Results clearly show that a saturation of EMF levels, preventing the installation of 5G BS sites, is already reached in currently deployed networks." Their measured case studies find EMF levels above 20 V/m in a real Italian deployment at 100% input power.

Confidence: **HIGH** (read the PDF). This is peer-reviewed-adjacent academic work by named academics (Chiaraviglio, Tor Vergata) and it is exactly the "EMF saturation blocks 5G sites" claim you want.

### 2.4 Poland - verified (limit has since been relaxed)

- Old limit: **7 V/m** (all bands 10 MHz - 10 GHz), vs ICNIRP 28-61 V/m. Confirmed in ITU-T K.Suppl.14 Table 1: https://www.itu.int/rec/T-REC-K.Sup14-201909-I/en
- Poland moved to ICNIRP-based limits around 2019/2020. Confidence: **MEDIUM**. See NOT VERIFIED below - I could not confirm the exact regulation number and date from a primary Polish source. Cite the change only as "Poland aligned with ICNIRP around 2020" and cite GSMA/Telia (see 2.6), or omit the date.

### 2.5 Switzerland - verified in structure, MEDIUM on exact numbers

Switzerland's NISV/ORNI (Ordinance on Protection against Non-Ionising Radiation) applies two tiers: ICNIRP-equivalent **immission limit values** (36-61 V/m depending on frequency), plus far stricter precautionary **installation limit values (Anlagegrenzwerte, ~4-6 V/m)** at "places of sensitive use" (dwellings, workplaces, schools, playgrounds, hospitals) - roughly a factor 10 below the immission limits in field strength (i.e. ~100x in power density).

Sources: Swiss Federal Office for the Environment (BAFU), https://www.bafu.admin.ch/en/state-electrosmog ; ITU "5G Country Profile Switzerland" (Oct 2020), https://www.itu.int/en/ITU-D/Regional-Presence/Europe/Documents/Events/2020/5G_EUR_CIS/5G_Swtizerland-final.pdf

Confidence: **MEDIUM**. The two-tier structure and the ~10x factor are solid; the exact 4/5/6 V/m band-by-band values I did not read out of the ordinance text itself. If you need the exact numbers, read SR 814.710 Annex 1 directly before citing.

### 2.6 Lithuania

Claim in circulation: before Lithuania relaxed its limits, "only 10% of shared sites would be available for 5G deployment and up to three times more base stations would be required", and Lithuania moved "from 1% of ICNIRP to the international guidelines" (attributed to Niclas Löwendahl, Telia, at a GSMA EMF Forum). Both Poland and Lithuania adopted ICNIRP-based limits in 2020.

Source: GSMA public-policy write-up of the EMF Forum: https://www.gsma.com/solutions-and-impact/connectivity-for-good/public-policy/ (EMF Forum key-takeaways pages)

Confidence: **LOW-MEDIUM**. This is an industry-association paraphrase of a conference talk, not a study. It is a *quote*, not a *finding*. If you use it, attribute it explicitly ("Telia's spectrum lead told the GSMA EMF Forum that...") rather than stating it as fact. I could not find the underlying Lithuanian study. See NOT VERIFIED.

### 2.7 The "77% of Italian urban sites unavailable" number

**Do not use.** See NOT VERIFIED.

---

## 3. Market

### 3.1 Electromagnetic simulation software market size - YOUR NUMBER IS CORRECT

Mordor Intelligence, "Electromagnetic Simulation Software Market": **USD 1.66 billion in 2026**, reaching **USD 2.70 billion by 2031**, **CAGR 10.22% (2026-2031)**.
https://www.mordorintelligence.com/industry-reports/electromagnetic-simulation-software-market

Confidence: **HIGH** that this is what the source says (I fetched the page and it states exactly these three figures). **Note the obvious caveat**: Mordor is a market-research vendor, not an audited source, and a jury may know that. Cite it as "Mordor Intelligence estimates..." rather than as fact. Nothing wrong with that in a grant.

Useful extra detail from the same page, which strengthens your positioning:
- Top five vendors (Ansys, Dassault Systemes, Keysight, Cadence, Altair) hold "roughly 60% of 2025 revenue".
- Telecommunications is the largest end-use segment at **27% revenue share (2025)**.
- Antenna design is the largest application at **26% of 2025 revenue**.
- On-premise deployment = **58% of 2025 revenue** (i.e. the market has barely moved to cloud/SaaS - a wedge for you).
- Finite element method leads solver type at **28% revenue share**.

An older snapshot of the same report gave USD 1.51 bn (2025) to USD 2.45 bn (2030) at 10.14% CAGR, which is consistent - the report simply rolled forward a year.

### 3.2 EMF compliance / exposure-assessment segment sizing

**NOT VERIFIED.** See bottom section. I found no credible sizing of the EMF-compliance software-and-services segment specifically. The only reports that come up ("electromagnetic field monitoring market", dataintelo etc.) are low-quality report-mill outputs with figures that do not reconcile with each other, and they size hardware *monitors*, not compliance software. Do not put a number here. If you need a market frame, build it bottom-up (number of base station sites in the EU x compliance assessments per site, or number of RF device SKUs certified per year) and label it as your own estimate.

### 3.3 Zurich MedTech AG (ZMT / Sim4Life)

**FDA MDDT qualification - VERIFIED, and it is exactly as you described.**

- MDDT name: **"IMAnalytics with MRIxViP1.5T/3.0T and BCLib"**
- Submission number: **Q181884**
- Submitter: **ZMT Zurich MedTech AG**, Zeughausstrasse 43, 8004 Zurich (contact: Michael Oberle, CEO)
- Date of submission: 2019-02-04
- **Qualification announced 12 December 2019.**
- Qualified Context of Use, verbatim: "The IMAnalytics with MRIxViP1.5T/3.0T and BCLib Toolset may be used in the premarket submissions of active implantable medical devices (AIMDs) to obtain the statistical distribution of the in vivo deposited power and/or induced terminal voltage to support the MR Conditional labeling of these medical devices for 1.5 T or 3 T MR scanners, according to the Tier 3 approach defined in ISO/TS 10974:2018."
- FDA's own conclusion, verbatim: "The qualification of IMAnalytics, MRIxViP, and BClib as an MDDT reduces the burden on sponsors preparing MRI RF safety test results for their AIMDs by defining a verified GUI-based toolset that generates statistical data based on various clinically relevant scenarios."

Sources: FDA MDDT Qualification Decision Summary (Q181884), https://fda.report/media/133458/SEBQ_Q181884_.pdf (I read the full PDF); MedTech Dive, 13 Dec 2019, https://www.medtechdive.com/news/fda-qualifies-tool-for-assessing-safety-of-implanted-devices/569030/ ; ZMT announcement of a later extension to IMAnalytics V3.0 / MRIxViP V2.1, https://zmt.swiss/news-and-events/news/sim4life/fda-extends-mddt-qualification-to-imanalytics-v3-0-and-mrixvip-v2-1

Confidence: **HIGH** on all of the above. Your "regulatory-qualification-as-moat" argument is fully supported: a small Swiss simulation company got a computational tool written into an FDA regulatory pathway, and that qualification then got *extended* to later versions - a compounding moat.

**Two precision points so you do not overclaim:**
1. The qualified context of use is **MRI RF safety of active implantable medical devices under ISO/TS 10974**. It is **not** RF exposure compliance of phones or base stations. Say "in an adjacent regulatory domain (MRI implant safety)" - the moat argument still lands and is more credible for being precise.
2. ZMT and IT'IS describe it as "the first computational Medical Device Development Tool (MDDT) qualified by the FDA". That is the **company's own claim**. MedTech Dive notes it was the third MDDT qualified in 2019 and that earlier MDDTs were questionnaires, which is consistent with it being the first *computational-model* MDDT, but I could not verify "first" against an FDA list. If you use "first", attribute it: "which ZMT describes as the first computational MDDT qualified by the FDA".

**ARR ~USD 2.3M and headcount ~15 - LOW CONFIDENCE.**
- getLatka lists ZMT Zurich MedTech AG at **USD 2.3M revenue with a 15-person team**: https://getlatka.com/companies/zmt.swiss
- RocketReach and other brokers give different figures (one gives ~USD 4M and 18 employees): https://rocketreach.co/zmt-zurich-medtech-ag-profile_b5f7aa2ff42d2aa3
- Confidence: **LOW**. These are data brokers scraping/estimating, not filings. ZMT is a private Swiss AG and does not publish accounts. **Recommendation: either drop the ARR figure, or write "estimated at roughly USD 2-4M with a team of order 15-20 (third-party estimates; ZMT is private and does not publish accounts)".** A jury member who works in the field may know the real number, and being caught with a broker-scraped figure stated as fact is worse than not giving one.

### 3.4 Typical annual licence price per seat (HFSS / CST / FEKO / Sim4Life)

**Effectively NOT VERIFIED - no vendor publishes prices.** All four vendors quote privately.

The only concrete figures I found, with their provenance stated honestly:

| Tool | Initial single-user licence | Annual maintenance/support |
|---|---|---|
| Ansys HFSS | ~USD 90,000 | ~USD 18,000 |
| Dassault CST | ~USD 60,000 | ~USD 12,000 |
| Altair FEKO | ~USD 50,000 | ~USD 10,000 |

Source: https://www.epsilonforge.com/post/commercial-electromagnetic-software/ - but the authors explicitly say: "we have gathered pricing information based on anonymous forum posts on platforms like Reddit, EDABoard, and PhysicsStudents, and added some of our own industry experience" and "none of these companies publicly disclose any pricing information."

Confidence: **LOW.** Do not put these in the proposal as facts. Other estimators (itqlick, vendr, Ozen Engineering) give ranges of USD 10k-50k for an Ansys licence depending on package, and ~18-20% of licence cost per year for maintenance - which is a normal CAE industry convention and is the one thing here I would be comfortable stating ("annual maintenance in CAE is conventionally 18-20% of licence cost").

Altair specifically does **not** sell per-seat: it sells pooled "Altair Units" drawn down by whichever application is running, so a per-seat price for FEKO is not even well-defined. https://help.altair.com/ALM/License%20Management%20System%20Guide.pdf

Sim4Life: ZMT publishes no commercial price. It offers **Sim4Life for Science free of charge** to academic/non-profit research (1-year renewable) and **Sim4Life.lite free** for students, which tells you they use academic seeding as a funnel - a relevant competitive observation you *can* make without a price. https://zmt.swiss/sim4life/configurations/license-options/ and https://sim4life.swiss/students

**Recommendation:** replace "annual licence price per seat" with a claim you can actually defend, e.g. "the incumbent 3D EM solvers are sold on private enterprise quotes, typically five figures per seat per year with maintenance conventionally at 18-20% of licence value; none of the four major vendors publish list prices." That is true, checkable, and makes the same point.

---

## 4. Competition

### 4.1 IXUS

- **Vendor:** Alphawave Mobile Network Products (Pty) Ltd (South Africa). Alphawave is the successor to **EM Software & Systems (EMSS)** - the same lineage as FEKO. Active in network-safety services since 2005.
  https://ixusapp.com/ixus-software/ and https://www.emssixus.com/ixus-software/
- **What it does:** RF-safety / EMF compliance management for rooftops, towers, small cells and DAS, 4G and 5G. It computes **incident field / power density** and **EMF non-compliance zones**, with a "lobe imprint" widget to identify accessible compliance boundaries at a given height.
- **Does it model a human body?** **No.** It computes fields and compliance zones and compares them against **reference levels**. From the product page: it will "identify all accessible areas where reference levels will be exceeded". There is no tissue model, no SAR, no absorbed power density.
- **Standards implemented:** ICNIRP 2020, IEC 62232, IEEE C95.3, CENELEC EN 50383, FCC OET-65, Safety Code 6.
- Confidence: **HIGH** (vendor product page read directly).

**This is your differentiator, stated exactly:** IXUS answers "where is the incident field above the reference level", which is the conservative proxy. It cannot answer "what does the body actually absorb", which is the basic restriction and the more permissive route to compliance that ICNIRP explicitly allows. That gap is precisely the thing your method fills.

### 4.2 EMF Visual

- **Vendor:** MVG (Microwave Vision Group). Originally developed by **France Telecom R&D and Oktal SE**.
  https://www.mvg-world.com/en/products/rf-safety/public-rf-safety/emf-visual-software
- **What it does:** simulates and visualises the EM field in a 3D environment (near-field and far-field), multiple emitters, interaction with buildings, GIS/SketchUp import, GPU-accelerated for large areas, beam-steering for 5G MIMO. Produces "RF exposure results as part of the assessment report for EN 62232".
- **Does it model a human body?** **No evidence that it does.** Everything on the vendor's page is field visualisation and exposure-zone assessment. The page does not mention SAR, tissue, absorbed power density, or a phantom.
- Confidence: **MEDIUM-HIGH** on "field-only". I am confident from the vendor materials, but I am inferring absence rather than reading an explicit "we do not model the body". Phrase as "EMF Visual, per its vendor documentation, computes and visualises incident fields and exposure zones; it does not document any tissue-absorption model." That is safe.

### 4.3 Does any incumbent offer *differentiable* simulation / gradient-based design optimization for exposure?

**No evidence found that any incumbent offers differentiable exposure/dosimetry.** But the answer is more nuanced than "no", and if you write a flat "nobody has gradients" a knowledgeable jury member will push back. Here is the precise state of play:

- **Dassault CST Studio Suite** *does* have a **sensitivity analysis** feature: "Derivatives of S-parameters can be calculated with respect to geometric and material parameters" from a **single** full-wave run (introduced in CST MWS 2010), and these sensitivities feed yield analysis and "more efficient optimization". https://www.3ds.com/products/simulia/cst-studio-suite/automatic-optimization and https://www.microwavejournal.com/articles/8568-efficient-sensitivity-analysis-methods-introduced-in-cst-microwave-studio-2010
  **But:** the differentiated output is **S-parameters**, i.e. a device port quantity. It is not SAR, not absorbed power density, and there is no human body in the loop.
- **Ansys HFSS** has Optimetrics / optiSLang for parametric sweeps and optimization, largely derivative-free or finite-difference-based. No published adjoint/AD path to an exposure metric.
- **Sim4Life** documents SAR-constrained optimisation in the MRI context (enforcing whole-body/partial-body/head SAR limits during pulse or coil design) and an "MRI gradient coil designer and optimization engine". **Careful:** "gradient coil" is MRI hardware terminology and has nothing to do with gradient-based optimization - do not misread that as differentiability. https://sim4life.swiss/mri-modules
- Adjoint-variable methods in computational EM exist in the academic literature (Nikolova et al. and successors) and adjoint/AD-based inverse design is standard in photonics, so "differentiable EM" as a *concept* is not novel. What appears absent is **differentiable EM dosimetry against a human body model, exposed as a product**.

Confidence: **MEDIUM.** This is a negative claim established by searching vendor feature pages, and negatives are hard. **Recommended phrasing, which is defensible:** "No commercial exposure-assessment tool we are aware of exposes analytic gradients of a body-absorption metric with respect to design or deployment parameters. CST offers S-parameter sensitivities with respect to geometry and material, but the differentiated quantity is a device port parameter, not tissue absorption; no incumbent differentiates through a human body model." If the proposal turns on this, it is worth a formal FTO/landscape confirmation rather than my search.

---

## 5. Prior-art check: Lojić Kapetanović & Poljak

**The work exists. Confirmed. Do not claim novelty on "differentiable dosimetry" as a bare concept.**

**Primary hit:**
- A. Lojić Kapetanović and D. Poljak, **"Application of Automatic Differentiation in Electromagnetic Dosimetry - Assessment of the Absorbed Power Density in the mmWave Frequency Spectrum"**, *2021 6th International Conference on Smart and Sustainable Technologies (SpliTech)*, 2021, pp. 1-6.
- DOI: **10.23919/SpliTech52315.2021.9566429** - https://doi.org/10.23919/SpliTech52315.2021.9566429
- Abstract, verbatim (via Semantic Scholar API, https://api.semanticscholar.org/graph/v1/paper/DOI:10.23919/SpliTech52315.2021.9566429): "This paper introduces the concept of automatic differentiation in the evaluation of the absorbed power density in the mmWave frequency spectrum for the new generation of mobile telecommunication technology. Automatic differentiation has been shown to be far superior over numerical differentiation by means of speed and accuracy. To demonstrate the full capacity of the proposed method, a comprehensive analysis of computing the absorbed power density on the surface of irradiated human skin in various configurations is presented."

Confidence: **HIGH** (title, authors, venue, DOI and abstract all confirmed).

**What they actually did, and the distinction that protects you:**

Their code is open (`dosipy`, in https://github.com/akapet00/EMF-exposure-analysis), and the AD (implemented in JAX) is used to compute **spatial derivatives of the analytic free-space field of a half-wave dipole** - i.e. AD replaces *numerical* differentiation inside the evaluation of the fields and hence the Poynting vector, so that APD on the skin surface can be computed accurately and fast. The comparison they draw is **AD vs finite differences for accuracy and speed of evaluating the forward quantity**. It is not gradient-based *design*: they are not backpropagating dSab/d(antenna parameters) or dSab/d(precoder) to optimise anything.

Confidence: **MEDIUM-HIGH** on this characterisation. It follows directly from the abstract ("Automatic differentiation has been shown to be far superior over numerical differentiation by means of speed and accuracy") and from the repo's own description. But **read the 6-page paper before you write the novelty paragraph** - if there is an optimisation experiment in there that I did not see, your claim needs to change. This is the single item in this report where I would not want you to rely on my summary alone.

**Their broader programme (Split + IETR Rennes) is directly adjacent to yours and you should cite it, not ignore it:**
- Area-averaged transmitted and absorbed power density on a **realistic ear model** - IEEE Trans. (2022), https://ieeexplore.ieee.org/document/9993744/
- Assessment of absorbed power density and temperature rise for a **non-planar body model** above 6 GHz - arXiv:2007.02604, https://arxiv.org/pdf/2007.02604
- Spatial averaging of APD on **anatomically-accurate non-planar** models (with G. Sacco and M. Zhadobov, IETR)
- Machine-learning-assisted antenna modelling for incident power density on non-planar surfaces above 6 GHz - *Radiation Protection Dosimetry* 199(8-9):826, 2023, https://academic.oup.com/rpd/article-abstract/199/8-9/826/7177465
- Impact of anthropomorphic shape and skin stratification on APD in mmWave exposure - *Sensors* 25(14):4461, 2025, https://doi.org/10.3390/s25144461
- Author's publication list: https://antekapetanovic.com/publications/

**Recommended novelty framing (safe):** Automatic differentiation has been applied to mmWave dosimetry before (Lojić Kapetanović & Poljak, SpliTech 2021), where it was used to evaluate the forward quantity - the absorbed power density on skin - more accurately and faster than finite differences. What has not been done is to *close the loop*: to make the body-absorption operator itself cheap enough and differentiable end-to-end so that gradients flow back to design and deployment variables (precoder, array geometry, tilt, siting), turning compliance from a check into a design constraint. That is a claim about the **loop**, not about **AD**, and it survives contact with this prior art. (It is also consistent with the position already recorded in your patent-landscape work: the USP is the differentiable design loop, not the physics.)

---

## NOT VERIFIED - do not use

Each of these was actively searched for and could not be confirmed. Some may well be true. None should go in the proposal as stated.

1. **"77% of sites in urban areas in Italy are potentially not available for new antennas due to the Italian EMF restrictions."** This number circulates in GSMA-adjacent summaries and is attributed to "an independent analysis in 2017", but I could not find the underlying study, and the GSMA pages that would cite it (gsma.com/.../european-emf-and-antenna-siting-policy/ and the Italy/Poland economic-impact report page) return HTTP 403 and could not be fetched. **Do not use the 77% figure.** Use the ITU-T K.Suppl.14 numbers (verified, above) and the Cacciapuoti/Chiaraviglio saturation evidence instead - they make the same point and they are readable.

2. **GSMA, "Economic Impact of stricter EMF limits on the Roll-Out of Mobile Broadband Networks - Calculations from Italy and Poland" (Nov 2018).** The report exists (it is listed on GSMA Europe's site) but both GSMA URLs 403'd and I could not read a single number out of it. If you want its figures, ask GSMA directly or find a mirror. Do not cite figures from it that you have not read.

3. **Lithuania: "only 10% of shared sites would be available for 5G" and "up to three times more base stations would be required", and "Lithuania moved from 1% of ICNIRP".** Traceable only to a GSMA write-up paraphrasing a conference talk by Telia's Niclas Löwendahl. No underlying study located. Attribute as a quote if used at all; do not state as a finding.

4. **Poland's exact regulatory change to ICNIRP limits.** That Poland relaxed to ICNIRP-based limits around 2019/2020 is repeatedly asserted by GSMA/ITU-adjacent sources, but I could not verify the instrument (I suspected a Regulation of the Minister of Health of 17 December 2019) or its exact entry-into-force date from a primary Polish source. The *old* 7 V/m limit is verified (ITU-T K.Suppl.14 Table 1). The change is not.

5. **Switzerland's exact installation-limit values (4 / 5 / 6 V/m by frequency band).** The two-tier structure (ICNIRP immission limits ~36-61 V/m, precautionary installation limits ~10x stricter at sensitive-use locations) is verified. The exact per-band numbers were not read from SR 814.710 Annex 1 itself.

6. **Any sizing of the EMF compliance / exposure-assessment segment (software and/or services).** No credible source found. The "electromagnetic field monitoring market" reports that surface (dataintelo and similar) are report-mill output, size hardware monitors rather than compliance software, and give figures that do not reconcile. **Do not state a number for this segment.** Build a bottom-up estimate and label it as yours.

7. **Per-seat annual licence prices for HFSS / CST / FEKO / Sim4Life.** No vendor publishes prices. The only figures available (HFSS ~USD 90k, CST ~USD 60k, FEKO ~USD 50k initial; 18/12/10k annual maintenance) come from a blog that openly states it assembled them from anonymous Reddit/EDABoard forum posts. LOW confidence, do not state as fact. The one defensible price-adjacent claim is that CAE annual maintenance is conventionally 18-20% of licence value.

8. **ZMT ARR of ~USD 2.3M and headcount of ~15.** Only sourced to data brokers (getLatka: USD 2.3M / 15 people; RocketReach: ~USD 4M / 18 people). ZMT is a private Swiss AG that publishes no accounts. Hedge or drop.

9. **"ZMT/IT'IS was the first computational MDDT qualified by the FDA."** This is ZMT's and IT'IS's own claim. It is plausible (MedTech Dive notes earlier MDDTs were questionnaires) but I could not verify "first" against an FDA list of qualified MDDTs - the FDA's qualified-MDDT index page 404'd. Attribute the claim to ZMT if you use it.

10. **"No incumbent offers differentiable simulation or gradient-based design optimization for exposure."** I found no evidence that any does, but this is a negative established by searching vendor feature pages, and CST's S-parameter sensitivity analysis is close enough that a flat denial is risky. Use the hedged phrasing given in section 4.3.

11. **Exact PAR approval date (2024-09-26) for IEC/IEEE P63195-3 and P63195-4.** Taken from the IEEE SA project pages. The *existence* and *draft status* of both parts is HIGH confidence; if the exact date matters, confirm on the IEEE SA project page before submission.

12. **Whether the Lojić Kapetanović & Poljak SpliTech 2021 paper contains any gradient-based *optimisation* (as opposed to AD for forward evaluation).** I read the abstract and the repository description, not the 6-page paper. Read it before writing your novelty paragraph. This is the highest-stakes unread document in this report.
