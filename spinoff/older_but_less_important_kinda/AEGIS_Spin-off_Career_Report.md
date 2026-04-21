# AEGIS spin-off feasibility and career strategy report

**Prepared for:** Robin Wydaeghe, Ghent University / IMEC INTEC-WAVES
**Date:** April 2026
**Status:** Pre-decision analysis

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [The technology and IP position](#2-the-technology-and-ip-position)
3. [Belgian startup survival: what "62%" really means](#3-belgian-startup-survival-what-62-really-means)
4. [The funding ladder: VLAIO, istart, and beyond](#4-the-funding-ladder-vlaio-istart-and-beyond)
5. [Market analysis: who buys dosimetry software?](#5-market-analysis-who-buys-dosimetry-software)
6. [Financial projections: how lucrative can this be?](#6-financial-projections-how-lucrative-can-this-be)
7. [Founder equity and dilution mechanics](#7-founder-equity-and-dilution-mechanics)
8. [Belgian tax treatment of startup proceeds](#8-belgian-tax-treatment-of-startup-proceeds)
9. [What founders actually take home: worked examples](#9-what-founders-actually-take-home-worked-examples)
10. [Career impact of founding a startup](#10-career-impact-of-founding-a-startup)
11. [The EU policy and lobbying path](#11-the-eu-policy-and-lobbying-path)
12. [Acquisition by a large telecom vendor](#12-acquisition-by-a-large-telecom-vendor)
13. [Founder mental health and opportunity cost](#13-founder-mental-health-and-opportunity-cost)
14. [The Belgian bureaucracy reality check](#14-the-belgian-bureaucracy-reality-check)
15. [The Delaware question: jurisdiction strategy](#15-the-delaware-question-jurisdiction-strategy)
16. [Long-term scenario modeling](#16-long-term-scenario-modeling)
17. [Work intensity and time allocation](#17-work-intensity-and-time-allocation)
18. [Recommendations](#18-recommendations)
19. [Sources](#19-sources)

---

## 1. Executive summary

This report examines whether spinning off AEGIS (geometric dosimetry software) from a PhD at UGent/IMEC is a good career and financial decision. It draws on Eurostat data, academic research on founder career outcomes, Belgian funding program details, market analysis of the RF/telecom software space, and community input from Belgian entrepreneurs.

**Key findings:**

- The Belgian institutional support system (VLAIO Innovation Mandate, imec.istart) makes the downside of attempting a spin-off close to zero. You get paid a full salary for 2 years to try.
- Median niche B2B software exits in Europe are in the 3-10M range. After dilution and tax, a founder with 50-70% equity takes home 1.5-6M.
- The short-term career penalty for ex-founders (43% fewer callbacks) is real but temporary. The long-term premium (positions ~3 years more senior) dominates.
- The path from deep-tech telecom founder to EU policy/Brussels is not only possible but well-trodden. Your specific niche (EMF compliance) is in high demand.
- The biggest risk is not failure but zombification: a company that survives but never scales. Belgium has the third-highest zombie company rate in the OECD (8.8%).

**Bottom line:** Attempt the spin-off using the VLAIO/istart path. The expected value is strongly positive across all scenarios, including failure.

---

## 2. The technology and IP position

### What AEGIS does

AEGIS computes absorbed power density on human bodies in wireless environments using a closed-form surface computation. The core equation is:

```
Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]
```

This replaces volumetric FDTD/FEM simulations (hours to days per scenario) with millisecond evaluation. The claimed speedup is 10^6 to 10^9 times.

### IP status (from the IDF)

- **Sole inventor**: Robin Wydaeghe (100% contribution)
- **Zero prior disclosures**: No publications, presentations, or external access
- **Novelty fully preserved**: No patent bars exist
- **Filed**: Invention Disclosure Form submitted to UGent TechTransfer, April 2026
- **No external funding**: Independent work during PhD, simplifying IP negotiations

### Technical differentiators

| Feature | AEGIS | FDTD/FEM (Sim4Life, CST) | Zone-based (IXUS, MVG) |
|---|---|---|---|
| Speed | Milliseconds | Hours to days | Seconds |
| Body geometry | Full 3D mesh | Full 3D mesh | None (exclusion zones) |
| Tissue properties | Cole-Cole model | Full dispersive | None |
| Polarization | Exact TE/TM | Exact | None |
| Frequency range | 100 MHz - 100 GHz | Depends on mesh | Varies |
| Differentiable | Yes (GPU-ready) | No | No |
| Validation | 3-8% vs published data | Ground truth | Conservative bounds |

### Software maturity

- 28,000 lines Python, 14,000 lines TypeScript
- 2,177 automated tests
- 9 fidelity levels (0-8)
- Real-time 3D web viewer (Flask + React + Three.js)
- Real base station data from 8 EU government databases
- 1,200+ real antenna patterns from CloudRF
- Monograph with complete derivations (~6,000 lines LaTeX)

### Assessment

The technology is real, validated, and substantially more mature than a typical pre-seed deep-tech project. Most spin-offs at this stage have a proof-of-concept. AEGIS has a deployed product with comprehensive testing. This is a significant advantage.

---

## 3. Belgian startup survival: what "62%" really means

### The headline number

The often-cited "62% five-year survival rate" for Belgian businesses comes from **Eurostat business demography data**, confirmed by Statbel (Belgian Federal Statistical Office). It refers to the 2014 cohort of VAT-registered enterprises tracked to 2019.

**This is for ALL businesses, not startups or tech companies.** It includes sole proprietorships, restaurants, consultancies, shops.

### Updated cohorts

| Cohort year | 5-year survival | Source |
|---|---|---|
| 2014 (survived to 2019) | 62.0% | Eurostat |
| 2016 (survived to 2021) | 67.1% | Statbel |
| 2019 (survived to 2024) | 63.5% | Statbel |

The 2016 cohort's higher rate likely reflects COVID-era government support keeping businesses alive.

### Year-by-year attrition (2019 cohort)

| Year | Survival rate | Annual drop |
|---|---|---|
| 1-year | 89.3% | -10.7% |
| 2-year | 81.5% | ~8% |
| 3-year | ~74% | ~7% |
| 4-year | ~67% | ~7% |
| 5-year | 63.5% | ~3.5% |

The biggest danger is year 1 (10.7% failure). Attrition slows every subsequent year.

### Regional breakdown (2019 cohort, 5-year)

| Region | 5-year survival |
|---|---|
| Wallonia | 65.7% |
| Brussels | 62.8% |
| Flanders | 62.7% |

Counter-intuitively, Wallonia has the highest survival. This likely reflects fewer high-risk ventures and more traditional small businesses.

### European comparison (2014 cohort)

| Country | 5-year survival |
|---|---|
| **Belgium** | **62%** (joint highest) |
| **Sweden** | **62%** (joint highest) |
| Netherlands | 59% |
| **EU average** | **45%** |
| Lithuania | 29% (lowest) |

Belgium and Sweden lead Europe by a wide margin. The EU average is only 45%.

### University spin-off survival (much higher)

University spin-offs dramatically outperform general businesses:

| Population | 5-year survival | Source |
|---|---|---|
| All Belgian businesses | 63.5% | Statbel |
| Flanders spin-offs | 67.8% | Statbel/VLAIO |
| KU Leuven spin-offs | 78% | LRD (published) |
| IMEC recent ventures (post-2017) | 96% (26/27) | IMEC |
| UK university spin-offs | 81% | Academic research |

KU Leuven's 78% is the only Belgian university-specific figure publicly available. UGent TechTransfer does not publish a survival rate for their 150+ spin-offs.

### The zombie company problem

"Survival" means the enterprise retains its VAT registration. It does **not** mean profitable or growing. Belgium has a serious zombie company problem:

- **8.8% of Belgian firms** meet the strict zombie definition (negative equity or persistent losses)
- **14% of companies** (~55,000 firms) have been loss-making for three consecutive years
- Belgium ranks **third globally** for zombie company prevalence (behind Spain and Italy, per OECD)

If ~9% of surviving businesses are zombies, the "real" survival rate (genuinely viable businesses) is closer to **57%**.

### What this means for AEGIS

The raw survival odds are strongly in your favor, especially with university/IMEC backing. The real risk is not dying but becoming a zombie: a company that sort of works, has a few clients, makes enough to survive, but never scales.

---

## 4. The funding ladder: VLAIO, istart, and beyond

Belgium, and Flanders specifically, has a well-structured funding ladder for university spin-offs. Each rung is designed to feed into the next.

### Rung 1: VLAIO Innovation Mandate (spin-off track)

- **What**: Postdoctoral mandate to transfer research into a spin-off
- **Funding**: 100% funded by VLAIO for up to 2 years
- **Salary**: Full postdoc salary (~45-55K gross/year)
- **Ends when**: The spin-off company is incorporated
- **Calls**: 2 per year (March and September deadlines)
- **Requirements**: Cooperation with an industrial mentor (can include VC funds, consultancies)
- **Key advantage**: This is essentially a free option. You get paid to try, and if it fails, you have a postdoc on your CV.

The mandate covers preparatory activities for the spin-off, though the majority of time must be reserved for research activities. In practice, this means you can develop the product while building the business case.

### Rung 2: imec.istart

- **What**: Belgium's #1-ranked university accelerator (UBI Global #1 worldwide)
- **Pre-seed investment**: 50K-250K for 3-6% equity
- **Acceptance rate**: ~20% (1 in 5 applications)
- **Duration**: 12 months of coaching and support
- **Track record**: 341+ startups since 2011, 84% continuation rate
- **Follow-on funding multiplier**: For every euro invested by istart, companies attract 17x in follow-on financing
- **Portfolio has exceeded 1 billion in cumulative follow-on funding**

Notable istart alumni:
- **Deliverect** (Ghent): Foodtech unicorn, 550 employees, three strategic acquisitions
- **UgenTec** (Limburg): 90M exit
- **Waylay**: Acquired by Vertiv in August 2025
- 13 total exits through acquisition/MBO as of 2025

### Rung 3: VLAIO R&D / Development grants

- **Research Project**: 25-60% of costs, max 3M per project
- **Development Project**: 25-50% of costs, min 25K support
- **Cap**: Max 8M allocated per company per calendar year
- **Bonus**: +10% with SME cooperation

These are non-dilutive. You keep all equity.

### Rung 4: Seed round

Key Belgian/Benelux seed investors:

| Investor | Fund size | Typical check | Notes |
|---|---|---|---|
| imec.xpand | 300M (Fund II, 2024) | Series A/B | Deep tech focus |
| PMV / Flanders Future Tech Fund | 75M | 0.5-5M | Government VC |
| Qbic | ~200M AUM (3 funds) | Seed to Series A | Active in deep tech |
| imec.istart Future Fund | Undisclosed | Follow-on for alumni | Bridge between istart and VC |

Benelux seed round median: **1.8M** (up 38.5% from 1.3M in 2024). Median valuation at seed: **5.0M**.

### Rung 5: Series A and beyond

Belgium deployed **650M across 220 deals in 2024**. H1 2025 saw 76 rounds totaling $378M, with nearly a 50% increase in seed rounds vs H1 2024.

### The Belgian VC problem

From both research and community feedback (Reddit Belgium2 thread, March 2026):

> "European VCs are OVERFLOWING with money... The problem is that they are very risk averse. They all want to find companies that don't really need investor money." (u/DDNB, 18 upvotes)

This is confirmed by data: Belgian/European VCs invest at later stages and at lower amounts than US counterparts. The practical implication: **bootstrap as long as possible using grants and istart, and only approach VCs when you have revenue traction.**

### Optimal funding path for AEGIS

| Year | Stage | Funding source | Amount | Equity given up |
|---|---|---|---|---|
| 2026-2028 | Innovation Mandate | VLAIO | Full salary, 2 years | 0% |
| 2028-2029 | Pre-seed | imec.istart | 50-250K | 3-6% |
| 2028-2030 | R&D grant | VLAIO Research Project | Up to 500K | 0% |
| 2030-2031 | Seed | PMV/Qbic/angels | 1-2M | 15-25% |
| 2032+ | Series A (if needed) | imec.xpand/international | 5-15M | 15-25% |

**Cumulative dilution through seed: ~20-30%.** You retain 70-80% through the critical early years. If you can reach profitability without Series A, you retain even more.

---

## 5. Market analysis: who buys dosimetry software?

### The market AEGIS sits in

AEGIS straddles two markets:

1. **RF Planning and Optimization Software**: Valued at **$2.1B in 2024**, forecasted to reach **$6.4B by 2033** (CAGR 13.2%)
2. **EMF Compliance**: No standalone market size figure exists, but it is a fast-growing segment driven by 5G rollout and stricter ICNIRP enforcement

### Competitive landscape

#### Direct competitors (EMF compliance)

| Company | Focus | Differentiation from AEGIS |
|---|---|---|
| IXUS (Alphawave/EMSS) | Cloud-based EMF compliance simulation | Zone-based, no body geometry |
| MVG (Microwave Vision Group) | EMF Visual Software | Public RF safety visualization, no dosimetry |
| Narda Safety Test Solutions | EMF measurement hardware + software | Hardware-focused |

#### Adjacent competitors (RF planning)

| Company | Focus | Status |
|---|---|---|
| Ekahau | WiFi planning and survey | Acquired by Ookla (Ziff Davis). $22M total funding. |
| iBwave Solutions | Indoor wireless network design | PE-backed (BPEA Private Equity) |
| Ranplan Wireless | Indoor/outdoor wireless planning | Nasdaq First North listed |
| ATDI | Radio planning (ICS Telecom) | Long-established, used by regulators and military |
| Forsk | Atoll radio planning | French, major tool for macro network planning |

#### Research tools (different price point)

| Company | Focus | Status |
|---|---|---|
| ZMT Zurich / Sim4Life | Full-wave FDTD simulation | Expensive academic platform |
| Dassault / CST Studio | Electromagnetic simulation | Enterprise simulation suite |

### The gap AEGIS fills

Nobody does real-time computational human dosimetry on 3D body geometries with tissue-specific properties. The market breaks down as:

- **RF coverage tools** (Atoll, iBwave, Ekahau): predict signal strength, not body absorption
- **EMF compliance tools** (IXUS, MVG): calculate exclusion zones, not body-specific exposure
- **Research simulation** (Sim4Life, CST): accurate but slow (hours), expensive ($50K+/license), academic-oriented

AEGIS occupies the unclaimed intersection: **fast enough for real-time deployment, accurate enough for compliance, specific enough for body-level dosimetry.**

### Regulatory tailwinds

The market opportunity is driven by regulatory pressure:

- **ICNIRP 2020 guidelines** introduced new requirements specifically for frequencies above 6 GHz, where AEGIS is strongest
- Many countries are updating regulations from ICNIRP 1998 to ICNIRP 2020, creating compliance upgrade demand
- The EU Digital Strategy explicitly addresses "5G and electromagnetic fields" as a policy priority
- **5G-PPP** (EU research body) has published whitepapers on "Beyond 5G/6G EMF Considerations," signaling regulatory investment
- Ericsson has published whitepapers on "accurately assessing EMF exposure from 5G" acknowledging the compliance burden

### Market risk

The critical question: **will operators pay for body-specific dosimetry, or will conservative zone-based methods remain "good enough"?**

Arguments for adoption:
- ICNIRP 2020 specifically adds absorbed power density requirements above 6 GHz
- As mmWave (5G FR2) and 6G deployments grow, zone-based methods become overly conservative, wasting deployable spectrum
- Differentiable dosimetry enables exposure-aware beamforming, which increases network capacity
- Public health concerns about 5G create liability pressure for operators

Arguments against adoption:
- Operators are conservative and slow-moving
- Zone-based methods are simple, cheap, and legally defensible
- Sales cycles for enterprise telecom software: 6-18 months
- Regulatory mandates for body-specific dosimetry do not yet exist

### Potential customers and partners

**Tier 1: Infrastructure vendors** (most likely acquirers)
- Ericsson, Nokia, Huawei, Samsung Networks
- Integration into network planning suites

**Tier 2: Telecom operators**
- Proximus, KPN, Orange, Deutsche Telekom, Vodafone
- Compliance tool for 5G/6G rollout

**Tier 3: Network planning software vendors**
- ATDI, Mentum/InfoVista, Forsk
- OEM integration or acquisition

**Tier 4: Regulatory bodies**
- National regulators (BIPT, BNetzA, Ofcom, ARCEP)
- BEREC, EU Commission
- Standards bodies

**Tier 5: Device manufacturers**
- Qualcomm, MediaTek
- Exposure-aware beamforming at chip level

---

## 6. Financial projections: how lucrative can this be?

### SaaS valuation fundamentals

For B2B SaaS companies at exit:

| Metric | Median | Average | Source |
|---|---|---|---|
| Revenue multiple at sale | 2.6x | 6.4x | SaaS M&A Report 2025 |
| EBITDA multiple at sale | 10.2x | 16.3x | SaaS M&A Report 2025 |
| Revenue at sale | $5.9M | $101.7M | SaaS M&A Report 2025 |
| European SaaS NTM revenue multiple | 3.0x | - | Translink Q2 2025 |

High-retention niche B2B (NRR >120%): up to **11.7x revenue**. This is where compliance software tends to land, as customers rarely churn off regulatory tools.

### AEGIS-specific revenue model

Assuming a SaaS/API pricing model:

| Revenue source | Price point | Addressable base | Penetration | Annual revenue |
|---|---|---|---|---|
| Operator API licenses | 50-200K/year | ~100 major operators in EU | 5-20% | 250K-4M |
| Vendor OEM integration | 200-500K/year | ~5 major vendors | 1-3 | 200K-1.5M |
| Regulator/government | 20-50K/year | ~30 national regulators | 10-30% | 60-450K |
| Academic/research | 5-10K/year | ~200 research groups | 10-20% | 100-400K |
| Consulting/custom work | Variable | As needed | - | 100-500K |

**Conservative scenario (year 5)**: 500K-1M ARR
**Base scenario (year 5)**: 1-3M ARR
**Optimistic scenario (year 5)**: 3-5M ARR

### Exit valuation scenarios

| Scenario | ARR | Multiple | Exit value | Probability |
|---|---|---|---|---|
| Acqui-hire / soft landing | <500K | 2-3x | 1-1.5M | 15% |
| Modest niche exit | 500K-1M | 3-5x | 1.5-5M | 30% |
| Median B2B SaaS exit | 1-3M | 4-6x | 4-18M | 25% |
| Strong niche exit | 3-5M | 5-8x | 15-40M | 10% |
| Home run | 5M+ | 8-12x | 40-120M | 5% |
| Failure / wind-down | - | - | 0 | 15% |

**Expected value (probability-weighted):** ~6-8M exit value.

### Comparable exits

| Company | Space | Exit value | Acquirer |
|---|---|---|---|
| Ekahau | WiFi planning | Not disclosed (est. $30-50M) | Ookla (Ziff Davis) |
| UgenTec | Lab software (istart alumni) | 90M | Undisclosed |
| Feops | Cardio simulation (UGent spin-off) | Not disclosed | Materialise |
| Gatewing | Drone mapping (UGent spin-off) | Not disclosed | Trimble |
| Caliopa | Silicon photonics (UGent spin-off) | Not disclosed | Huawei |
| Deliverect | Food-tech (istart alumni) | Unicorn status | Still operating |

UGent spin-offs have been acquired by Materialise, Trimble, Huawei, Jensen Hughes, Sweco, and CellCarta. The pattern is clear: Belgian deep-tech spin-offs get acquired by large international companies seeking specialized technical capabilities.

---

## 7. Founder equity and dilution mechanics

### Typical founder ownership by round

Data from Carta (2025 Founder Ownership Report):

| Stage | Median founding team ownership |
|---|---|
| Pre-seed | ~75% |
| Post-seed | 56.2% |
| Post-Series A | 36.1% |
| Post-Series B | 23% |
| Post-Series C | 15-25% |

### Solo founder considerations

Solo founders face additional headwinds:
- 35% of incorporated companies are solo-founded, but only 17% of funded ones
- VCs strongly prefer teams (2-3 founders is optimal)
- The solution: either find a co-founder (commercial/sales DNA) or bootstrap to reduce VC dependence

### AEGIS-specific dilution model

Using the recommended VLAIO/istart path with minimal VC:

| Event | Equity given up | Cumulative founder ownership |
|---|---|---|
| Start | 0% | 100% |
| UGent IP license | 2-5% (typical university take) | 95-98% |
| imec.istart | 3-6% | 89-95% |
| Employee option pool | 10% | 79-85% |
| Seed round (1.5M at 5M pre-money) | 23% | 61-65% |
| **At exit (no Series A)** | - | **61-65%** |

If you skip the seed round entirely and bootstrap with grants:

| Event | Equity given up | Cumulative founder ownership |
|---|---|---|
| Start | 0% | 100% |
| UGent IP license | 2-5% | 95-98% |
| imec.istart | 3-6% | 89-95% |
| Employee option pool | 5-10% | 79-90% |
| **At exit (bootstrapped)** | - | **79-90%** |

### Key insight

The VLAIO/grant path lets you retain dramatically more equity than the VC-funded path. Even with a seed round, you keep 60-65%. Bootstrapped, you keep 80-90%. This is the single biggest financial advantage of the Belgian system.

---

## 8. Belgian tax treatment of startup proceeds

### Current regime (pre-2026)

Until January 1, 2026, capital gains on shares held by individuals in "normal management of private patrimony" are **tax-free** in Belgium. This has been one of Belgium's most founder-friendly features.

### New regime (from January 1, 2026)

Belgium introduced a capital gains tax on financial assets starting January 2026:

- **First 1M of capital gains**: **Exempt** (for substantial shareholdings, defined as 20%+ ownership)
- **Gains above 1M**: Taxed at graduated rates from **1.25% to 10%**
- The exact rate depends on holding period and gain amount
- **Exit tax**: If you move abroad, gains may be taxed if assets are disposed within 2 years

### Innovation Income Deduction (IID)

For ongoing revenue (not exit), Belgium offers one of Europe's best IP tax regimes:

- **85% deduction** of qualifying net IP income
- Effective maximum tax rate on IP income: **3.75%**
- Qualifying IP: patents, copyrighted computer software, plant breeders' rights
- AEGIS software would qualify as copyrighted computer software
- New 2025 rules: unused IID can be carried forward as a non-refundable tax credit

### VVPRbis dividend regime

For distributing ongoing profits from a BV:

- After 3 completed accounting years
- Dividends taxed at: 20% vennootschapsbelasting + 15% VVPRbis withholding = **~32% effective**
- Below the 40% vennootschapsbelasting threshold, the rate is even lower

### Practical tax structure (from Reddit Belgium2 community)

A knowledgeable commenter (u/Crypto-Raven) broke down the optimal structure:

1. Pay yourself wages up to the 40% marginal rate bracket (~2,275 gross/month), actual tax ~15%
2. Use benefits: car, meal vouchers, expense allowances, laptop, phone, home office
3. After year 3, distribute remaining profit via VVPRbis: 20% corporate tax + 15% withholding = 32% effective
4. **Result: on 100K profit, effective total tax is under 30%**

Combined with IID on IP income (3.75% effective), the Belgian tax structure for software companies is actually quite competitive.

---

## 9. What founders actually take home: worked examples

### Example A: Modest exit (5M acquisition, bootstrapped)

| Item | Amount |
|---|---|
| Exit value | 5,000,000 |
| Your equity (85%) | 4,250,000 |
| Capital gains tax (new 2026 regime, ~5-8% effective on gains above 1M) | ~200,000 |
| Advisor/legal fees (3-5%) | ~175,000 |
| **Net take-home** | **~3,875,000** |

### Example B: Median exit (10M acquisition, after seed round)

| Item | Amount |
|---|---|
| Exit value | 10,000,000 |
| Your equity (63%) | 6,300,000 |
| Capital gains tax (~7% effective on gains above 1M) | ~370,000 |
| Advisor/legal fees (3%) | ~190,000 |
| **Net take-home** | **~5,740,000** |

### Example C: Strong exit (25M acquisition, after seed round)

| Item | Amount |
|---|---|
| Exit value | 25,000,000 |
| Your equity (63%) | 15,750,000 |
| Capital gains tax (~9% effective on gains above 1M) | ~1,330,000 |
| Advisor/legal fees (2%) | ~315,000 |
| **Net take-home** | **~14,105,000** |

### Example D: Failure after 4 years

| Item | Amount |
|---|---|
| Exit value | 0 |
| Salary earned during Innovation Mandate (2 years) | ~100,000 |
| Salary earned during istart/startup (2 years, ~50K/year) | ~100,000 |
| Industry salary you would have earned (4 years, ~65K/year) | ~260,000 |
| **Opportunity cost** | **~60,000** |
| **Career capital gained** | PhD + postdoc + founder experience |

The opportunity cost of failure is roughly 60K in lost earnings over 4 years (difference between startup salary and industry salary). This is remarkably low, especially considering the career capital gained.

---

## 10. Career impact of founding a startup

### The founding penalty (short-term)

**Study: Kacperczyk & Younkin (2022), Organization Science**

Methodology: Resume-based audit study. Applications sent to employers varying founding experience.

Key findings:
- **~40% fewer callbacks** for ex-founders compared to non-founders
- Employers perceive founders as **less competent and worse cultural fits** (not less skilled, but less controllable)
- **Successful founders penalized more** than failed founders (employers fear they will leave)
- The penalty is strongest at **large, established firms**
- **Gender effect**: Male founders face the full penalty. Female founders face no comparable penalty.

**Study: Ding (2023), Strategic Entrepreneurship Journal**

Confirmed the penalty exists but varies by employer type:
- Traditional corporate employers: strong penalty
- Entrepreneurial firms: no penalty or slight premium

### The founder premium (long-term)

**Study: Gompers, Kovner, Lerner, Scharfstein (2010), Journal of Financial Economics**

Sample: 9,790 ventures by 8,753 entrepreneurs (1975-2000).

Key findings:
- Previously successful entrepreneurs: **34% success rate** in next venture
- Previously failed entrepreneurs: **23% success rate** (vs 22% for first-timers)
- Failure teaches surprisingly little about future startup success
- But the experience is highly valued by employers

**HBS Working Knowledge (Gompers et al.)**

- After exiting startups, entrepreneurs obtain jobs approximately **3 years more senior** than peers
- This holds even for **failed founders**
- The market values the breadth of general management experience (product, sales, operations, finance, hiring) that founders accumulate

### Serial entrepreneurship

- **34% of previously successful founders** succeed again (vs 22% baseline)
- The persistence is driven by market timing skill, not luck
- Founders who time one market well tend to time the next one well too

### Net career impact by time horizon

| Period | Impact | Evidence |
|---|---|---|
| 0-6 months post-exit | **Negative**: 40% fewer callbacks | Kacperczyk & Younkin 2022 |
| 1-3 years post-exit | **Neutral to positive**: seniority premium kicks in | Gompers et al. |
| 5+ years post-exit | **Strongly positive**: higher career peaks | Gompers et al. |
| 10+ years | **Dominant positive**: founder experience compounds | Career trajectory data |

### PhD + founder combination

- PhD founders are increasingly rare: only ~20% of STEM PhDs in the private sector start companies (down from 30%+ in the late 1990s)
- PhD founders delay entrepreneurship longer than before: average 14% more post-PhD work experience in 2017 vs 1997
- The rarity makes the combination more valuable, especially in deep-tech niches where the hiring penalty research (conducted on generic software engineering roles) is less applicable
- A PhD in electromagnetic dosimetry + a startup building compliance software = you are essentially unhireable by anyone other than the companies that desperately need exactly this person

---

## 11. The EU policy and lobbying path

### Why this path exists for you

The "startup founder who understands EMF compliance at a technical level, has built commercial products, and has a PhD in the field" profile is extremely rare. The EU policy world in Brussels runs on technical credibility, and most policy people lack it. You would be filling a genuine expertise gap.

### Concrete entry points

#### Industry associations (highest probability path)

| Organization | Role type | Relevance | Entry difficulty |
|---|---|---|---|
| **ETNO** (European Telecom Network Operators) | Policy advisor on EMF/spectrum | Direct match | Medium |
| **GSMA Europe** | Technical policy specialist | Direct match | Medium |
| **ConnectEurope** | Connectivity policy | Close match | Medium |
| **DigitalEurope** | Digital industry advocacy | Adjacent | Medium |

Example career path: Alessandro Gropelli went Vodafone (EU affairs) -> Telecom Italia (Brussels team) -> European Parliament (PR officer) -> ETNO (Deputy Director General). This is a well-established revolving door.

#### EU institutions

| Institution | Role | Entry mechanism | Difficulty |
|---|---|---|---|
| **DG CONNECT** (EU Commission) | Policy officer, digital policy | EPSO concours or Seconded National Expert | High (concours), Medium (SNE) |
| **BEREC** | Technical advisor, telecom regulation | Direct application | Medium |
| **ENISA** | Less relevant (cybersecurity) | - | Low relevance |
| **European Parliament** | Advisor to MEP (ITRE committee) | Political networks | Medium-high |

DG CONNECT shapes Europe's digital future. They specifically work on 5G/EMF policy. BEREC implements EU telecom rules and needs technical expertise.

#### National regulators

| Regulator | Country | Relevance |
|---|---|---|
| BIPT | Belgium | Direct (regulates EMF exposure) |
| BNetzA | Germany | High |
| Ofcom | UK | High |
| ARCEP | France | High |

BIPT (Belgian Institute for Postal Services and Telecommunications) literally regulates RF exposure limits. They would be a natural employer for someone with your expertise.

#### Brussels lobbying firms

Firms like FTI Consulting, Kreab, Burson, and Fleishman-Hillard constantly hire technical specialists to advise telecom clients on EU regulation. The typical profile: law or political science + industry experience. A PhD + startup founder in telecom is a premium hire.

### The optimal sequence

The most credible path to Brussels policy is **not** going there directly after the PhD. The sequence that maximizes both financial return and policy credibility:

1. **PhD** (2026) - technical credibility
2. **Startup** (2026-2031) - industry credibility + commercial understanding
3. **Acquisition or exit** (2031-2032) - financial independence + vendor experience
4. **2 years at acquirer** (2032-2034) - large company credibility
5. **Brussels policy role** (2034+) - you're 34, with PhD + startup + industry at a major vendor

At step 5, you are one of perhaps a dozen people in Europe with this combination. ETNO, GSMA, or DG CONNECT would be fighting over you.

---

## 12. Acquisition by a large telecom vendor

### How acquisitions work for small deep-tech companies

Ericsson has made **40 acquisitions** across telecom infrastructure, OSS/BSS, and AI. Nokia has made **41+ acquisitions** since 1997. Both actively acquire capabilities they lack internally.

### What happens to founders post-acquisition

Data from WinSavvy retention study:

| Metric | Value |
|---|---|
| Founders gone within 2 years | 52% |
| Founders gone within 3 years | 75%+ |
| Founders who stay voluntarily (no lock-in) | 8% |
| Typical retention vesting period | 2-4 years |
| Founders staying past 2 years who get promoted | 3x more likely |

### Typical deal structure

- **Cash + stock**: Most common. Some immediate cash, some acquirer stock vesting over 2-4 years.
- **Earn-out**: Additional payments tied to hitting performance targets post-acquisition (revenue, integration milestones).
- **Golden handcuffs**: A portion of the purchase price (often 20-40%) vests over the retention period. If you leave early, you forfeit it.
- **Rollover equity**: 10-20% of proceeds reinvested in the combined entity.

### What the role looks like

If Nokia or Ericsson acquires AEGIS, you would likely become:
- "Head of EMF Dosimetry Solutions" or "VP, Exposure Compliance"
- Report to a VP or SVP in their network planning or radio access division
- Salary: 120-180K (including acquirer stock grants)
- Team: 5-15 people (your existing team + some from the acquirer)

The honest reality: Inc. Magazine titled an article "Congratulations on Selling Your Startup. Get Ready for a Demotion and an Identity Crisis." You go from running everything to running a small team inside a 100K-employee organization. Most founders describe the first year as deeply frustrating.

However, **founders who push past the 2-year mark are 3x more likely to be promoted.** If you can tolerate the corporate environment, the career trajectory inside a large telecom vendor is strong.

### The "soft landing" acquisition

For a company like AEGIS with <1M ARR, the most likely acquisition type is a **soft landing / acqui-hire**:

- Valuation: 1-5M (often based on team quality and IP, not revenue multiples)
- The acquirer wants: your technology, your expertise, and you
- Deal structure: mostly earn-out and retention bonuses
- Typical acqui-hire value: <10M
- The acquirer integrates your tech into their existing platform

This is less lucrative than a revenue-based exit but provides a guaranteed salary, career path, and the "big company on your CV" credential that opens the Brussels policy door.

---

## 13. Founder mental health and opportunity cost

### Mental health data (Freeman, UCSF)

Dr. Michael Freeman's research at UCSF (sample: 242 entrepreneurs vs 93 comparison participants):

| Condition | Entrepreneurs | General population |
|---|---|---|
| Any mental health condition | 72% (direct or family) | Lower baseline |
| Depression | 30% | ~7% |
| ADHD | 29% | ~4-5% |
| Substance use | 12% | ~8% |
| Bipolar disorder | 11% | ~2.6% |
| Two or more conditions | 32% | Much lower |
| Three or more conditions | 18% | Much lower |

This is not because entrepreneurs are inherently less stable. The causation runs both ways: certain traits (high energy, risk tolerance, hyperfocus) predispose to both entrepreneurship and certain conditions, and the startup lifestyle (isolation, uncertainty, financial stress, identity fusion with the company) exacerbates existing vulnerabilities.

### Founder salary during startup years

European data (Sifted/Creandum surveys):

| Stage | Median founder salary (Europe) |
|---|---|
| Bootstrapped | ~28K (CEE/Baltics) to ~50K (Western Europe) |
| Pre-seed | ~50K |
| Seed | ~85K |
| Series A | ~100K+ |
| Series B | ~140K |

### Opportunity cost calculation

A PhD in RF/telecom engineering going to industry in Belgium:

| Year | Industry salary (est.) | Startup salary (est.) | Difference |
|---|---|---|---|
| Year 1 (Innovation Mandate) | 55K | 50K (postdoc) | -5K |
| Year 2 (Innovation Mandate) | 58K | 50K (postdoc) | -8K |
| Year 3 (istart/early startup) | 62K | 45K | -17K |
| Year 4 (post-seed) | 66K | 60K | -6K |
| Year 5 (growing) | 72K | 75K | +3K |
| **Total opportunity cost** | | | **~33K** |

With the VLAIO mandate covering the first 2 years at near-industry salary, the total opportunity cost over 5 years is only about 33K. This is trivially small compared to even the failure scenario's career capital gains.

### What the opportunity cost does NOT include

- **Equity value**: Even in the failure case, you learned how to build and run a company. This is worth more than 33K in future earnings.
- **Network**: The istart/VLAIO/UGent ecosystem connections persist after the company ends.
- **Seniority premium**: Per Gompers et al., ex-founders land positions ~3 years more senior, which compounds over a career. A 3-year seniority advantage at age 32 translates to roughly 100-200K in cumulative additional earnings over the next 20 years.

---

## 14. The Belgian bureaucracy reality check

### What the Reddit thread reveals

A March 2026 Reddit post on r/Belgium2 ("Building a SaaS in Belgium. Genuinely losing my mind.") with 161 upvotes and 130 comments provides a useful reality check on Belgian startup bureaucracy.

**The OP's complaints:**
- Slow BV incorporation (notary appointment delays)
- Confusing address/domicile rules
- Social contributions on zero income
- GDPR compliance complexity
- Difficulty hiring cross-border (German employee)
- Risk-averse Belgian VCs

**What the experienced commenters pushed back on:**

1. **BV setup is actually straightforward**: "Get an accountant, costs 1,500, done in a week" (u/kinv4ris). The notary process can be done in 8 days. A BV has no minimum capital (can start with 1 euro).

2. **Social contributions are manageable**: You can request an exemption for the first 3 years (link to Acerta). Minimum contributions are ~300/month, which is much cheaper than US private insurance for equivalent coverage.

3. **Tax structure is actually competitive**: u/Crypto-Raven provided a detailed breakdown showing effective tax under 30% on 100K profit using wages (15% effective) + benefits + VVPRbis (32% after year 3) + IID (3.75% on IP income).

4. **The real problem is VC risk aversion**: The most-upvoted substantive comment (u/DDNB, 18 points): "European VCs are OVERFLOWING with money... very risk averse... all want to find companies that don't really need investor money."

5. **The address/domicile issue is a non-issue**: Multiple commenters confirmed you can register a BV at your home address with no problems.

### What this means for AEGIS specifically

You will not have most of these problems because:

1. **UGent TechTransfer handles IP**: They have done 150+ spin-offs. The process is standardized.
2. **VLAIO Innovation Mandate handles early funding**: Full salary, no need for personal capital.
3. **imec.istart handles company setup**: Part of their coaching program.
4. **You are not hiring cross-border from day one**: The mandate period is just you doing research.
5. **GDPR for a B2B API product** is simpler than for a consumer SaaS.
6. **The IID (Innovation Income Deduction)** makes your software IP income taxed at effectively 3.75%.

The OP on Reddit was a solo developer trying to do everything from scratch without institutional support. You have institutional rails. The bureaucracy is real but managed.

### The 28th Regime (EU Inc.)

Multiple commenters mentioned the proposed "28th regime" or EU Inc., which would create a unified European company type. This could eliminate cross-border hiring and compliance friction. It is not yet law but has political momentum from the European Commission. If it passes during your startup years, it would remove several of the friction points Belgian entrepreneurs face.

---

## 15. The Delaware question: jurisdiction strategy

### The standard move for ambitious European founders

The "Delaware Flip" is not exotic. It is the standard corporate restructuring used by European startups that want access to US investors. Y Combinator requires it (they only accept US, Cayman Islands, or Singapore entities). Sapphire Ventures, a major US VC, published a full guide for European founders on this topic.

### How the flip structure works

```
Delaware C-Corp (parent / TopCo)
  └── Belgian BV (subsidiary, operational entity)
```

The shareholders of the Belgian BV do a share-for-share exchange into the new Delaware entity. The Belgian BV becomes a wholly-owned subsidiary. IP, team, VLAIO grants, and operations all stay in Belgium. The Delaware parent is the entity US investors put money into.

### The critical finding: you can have both

A Belgian subsidiary of a US parent CAN still receive VLAIO grants, provided the operational headquarters and economic activity are in Flanders. Precedent: IPA's subsidiary BioStrand (owned by a US-listed parent) received a 460K VLAIO research grant. VLAIO's eligibility criteria focus on where the work happens, not where the parent is incorporated.

### Why US VCs require Delaware

- Delaware law allows multiple classes of stock (common, preferred, convertible preferred), which is how VC deals are structured
- The Delaware Court of Chancery has 200+ years of corporate case law, making outcomes predictable
- Term sheets and stock purchase agreements are drafted assuming Delaware law
- Directors and officers do not need to reside in Delaware
- It is the "lingua franca of the investment community"

### Why this matters for AEGIS

- **US acquirer friendliness**: If Ericsson (major US operations), Qualcomm, or any US company wants to acquire AEGIS, a Delaware entity is dramatically simpler for their legal team
- **Y Combinator eligibility**: YC has funded niche B2B compliance tools before. A Delaware entity is a prerequisite.
- **US VC access**: Most US VCs at pre-seed/seed either require or strongly prefer Delaware C-Corps
- **US hiring**: If you hire US-based salespeople (necessary for selling to US telcos), a C-Corp makes equity compensation straightforward

### Costs and risks

| Item | Cost/Risk |
|---|---|
| Incorporation (with legal counsel) | ~$10,000 |
| Delaware franchise tax | ~$400/year minimum |
| Registered agent | ~$100/year |
| US tax preparation | $3-5K/year |
| IRS compliance risk | $25,000 penalty per missed filing |
| Belgian tax event on flip | Potential capital gains on share exchange (needs specialist structuring) |

The Belgium-US double taxation treaty (signed 2006) provides relief from double taxation, with foreign tax credits available in both directions. However, the interaction between Belgium's new capital gains tax (2026+) and the US entity structure requires specialist advice.

### When NOT to flip

- **Pre-revenue, pre-seed**: No US investors, no US customers. Adding US complexity costs money and attention for zero benefit.
- **During VLAIO Innovation Mandate**: You are a postdoc researcher, not a company. No entity to flip.
- **Before imec.istart**: The istart investment goes into the Belgian BV. Keep it clean.

### When TO flip

- **At seed round**: A US VC or accelerator requires it. You have revenue, customers, and a real business. The cost ($10K + ongoing compliance) is justified by the capital access it unlocks.
- **Before a US acquisition**: If a US vendor wants to acquire you, having a Delaware parent simplifies the deal enormously.

### The recommended timeline

| Year | Structure | Rationale |
|---|---|---|
| 2026-2028 | No company (Innovation Mandate) | Postdoc status. No legal entity needed yet. |
| 2028-2029 | Belgian BV only | imec.istart investment. VLAIO grants. Keep it simple. |
| 2029-2030 | Belgian BV + first revenue | Build traction. Price in USD for international customers. |
| 2030-2031 | **Delaware flip** at seed round | US VC wants in, or preparing for US accelerator. Belgian BV becomes subsidiary. |
| 2031+ | Delaware C-Corp (parent) + Belgian BV (ops) | US investor access + Belgian tax incentives (IID at 3.75%) + VLAIO grants on subsidiary |

### The Stripe Atlas trap (what to avoid)

Stripe Atlas ($500/year) makes it trivially easy to set up a Delaware C-Corp from anywhere. This is actively harmful for European founders at pre-seed:

- You are immediately subject to US corporate tax (21%) on worldwide income
- You must file US tax returns annually, even with zero US revenue
- Missing IRS deadlines triggers $25,000 penalties per filing
- You lose eligibility for VLAIO/istart if Belgium is seen as a shell rather than the operational center
- You gain nothing, because you have no US investors and no US customers yet

The right tool is not Stripe Atlas on day one. The right tool is a Belgian BV on day one, with a Delaware flip engineered by a US-Belgium cross-border tax attorney when the seed round demands it.

### Comparison: Belgium-only vs. flip structure

| Factor | Belgian BV only | Delaware flip (at seed) |
|---|---|---|
| VLAIO grants | Eligible | Eligible (if Belgian ops are real) |
| imec.istart | Eligible | Eligible |
| IID (3.75% IP tax) | Yes | Yes (on Belgian subsidiary) |
| US VC access | Limited (some will invest, most won't) | Full access |
| Y Combinator | Not eligible | Eligible |
| US acquisition | Possible but complex | Straightforward |
| Annual compliance cost | ~1.5K (Belgian accountant) | ~5-8K (Belgian + US) |
| Capital gains at exit | Belgian regime (0-10%) | Depends on structure (needs planning) |
| Complexity | Low | Medium-high |

### Alternative jurisdictions considered and rejected

#### Estonia (e-Residency)

Estonian e-residency is marketed as a way to run a company with 0% tax on reinvested profits. However, for a Belgian tax resident:

- Belgian tax authorities will assert **Permanent Establishment** status if you manage the company from Belgium, subjecting the Estonian entity to Belgian corporate income tax regardless
- [Taxpatria.be explicitly warns](https://www.taxpatria.be/is-an-estonian-company-the-right-solution-if-you-live-in-belgium/): "If you effectively manage your company from Belgium, the Belgian tax authorities could argue that this triggers a Permanent Establishment in Belgium"
- You lose all Belgian institutional support (VLAIO, istart, UGent TechTransfer, IID)
- Estonian e-residency is designed for digital nomads without fixed tax residence, not for university researchers building on institutional IP

**Verdict: actively harmful for this profile.**

#### Portugal (IFICI / NHR 2.0)

Portugal replaced NHR with IFICI in January 2025, offering 20% flat tax on qualifying income for 10 years. However:

- Requires physical relocation to Portugal
- 20% flat rate is **worse** than Belgium's IID (3.75% on software IP income)
- Loses all Belgian institutional support
- Deep-tech startup ecosystem in Lisbon/Porto is weaker than Ghent/Leuven for RF/telecom
- Customer base (Northern European telcos) is not in Portugal

**Verdict: wrong profile. Good for remote SaaS founders, not for deep-tech university spin-offs.**

#### Netherlands

The closest real alternative:

- Innovation Box: 9% on qualifying IP income (vs Belgium's 3.75% IID)
- WBSO: 50% R&D tax credit on first 380K for startups (generous)
- Proposed unrealized capital gains tax creating uncertainty
- Would require rebuilding network from scratch (TU Delft/Eindhoven instead of UGent/IMEC)

**Verdict: marginally viable but strictly worse for this specific founder.** The 5.25% IP tax disadvantage (9% vs 3.75%) compounds over years of revenue. The loss of VLAIO/istart access and UGent network is not recoverable.

### Bottom line

The architecture should be in your head from day one, but the execution should wait until there is a compelling reason (US investor, US accelerator, US acquisition). Starting as a Belgian BV and flipping at seed is the standard playbook for ambitious European deep-tech founders. It is not a compromise. It is how Deliverect, UgenTec, and hundreds of other European success stories did it.

Jurisdiction shopping makes sense for bootstrapped SaaS developers selling B2C from a laptop. It does not make sense for a deep-tech founder building on university IP with access to one of Europe's best institutional support systems. The ambitious move is: take Belgium's money, build the product, flip to Delaware when US VCs come knocking, and sell to the world.

### EU Inc. (28th Regime): the wildcard

The European Commission published its formal legislative proposal for EU Inc. on **18 March 2026** ([COM(2026) 321](https://commission.europa.eu/document/download/3e9822aa-8cef-40a1-904e-a53fc68e7265_en)). The European Council endorsed it as a **priority measure for 2026** the very next day. This is unusually strong political backing for EU legislation.

#### What EU Inc. would offer

- Register a pan-European company in **48 hours, for under 100 euros, no minimum capital**
- One legal entity operating across all 27 EU member states
- Unified governance rules (no per-country company law headaches)
- Single submission to an EU-level business register connecting national registers
- Designed specifically for startups and innovative companies, but available to any founder

#### Legislative timeline

| Date | Milestone | Status |
|---|---|---|
| Jan 2025 | Commission's Competitiveness Compass announces 28th regime | Done |
| Jan 2026 | European Parliament adopts resolution with recommendations | Done |
| 18 March 2026 | Commission publishes formal legislative proposal | Done |
| 19 March 2026 | European Council endorses as priority for 2026 | Done |
| 2026 | Parliament + Council negotiate and adopt | In progress |
| **Q1 2027** | **First EU Inc. registrations (target)** | Optimistic |
| 2028 | Full "one Europe, one market" goal | Aspirational |

#### Realistic availability

- **Best case**: Available to founders by mid-2027
- **Likely case**: Available by late 2027 or early 2028
- **Worst case**: Watered down or delayed to 2029+ (member states may fight over details, especially tax and labor law implications)

#### What EU Inc. does NOT do

EU Inc. harmonizes company law but does **not** harmonize tax. Each member state will still apply its own corporate tax rules. The Belgian IID (3.75% on IP income) would remain a Belgian advantage regardless of whether the entity is a Belgian BV or an EU Inc. registered in Belgium.

#### Relevance to AEGIS timeline

The Innovation Mandate runs 2026-2028. Incorporation of the spin-off happens at the end (~2028). By then, EU Inc. may be available. Options at incorporation time:

1. **Incorporate as an EU Inc.** (if available) for seamless cross-border operation from day one, registered in Belgium to keep IID and VLAIO eligibility
2. **Incorporate as a Belgian BV** (safe choice) and convert later if EU Inc. proves useful
3. **Belgian BV + Delaware flip** at seed round (the proven playbook, independent of whether EU Inc. exists)

The Innovation Mandate period buys time. There is no need to decide now. By 2028, the EU Inc. picture will be much clearer.

---

## 16. Long-term scenario modeling

### Scenario 1: Things go OK (probability: ~45%)

| Year | Age | What happens |
|---|---|---|
| 2026 | 26-27 | PhD defended. Apply for VLAIO Innovation Mandate. |
| 2026-2028 | 27-29 | Innovation Mandate. Product development, first pilot conversations. Paid full postdoc salary. |
| 2028 | 29 | Enter imec.istart. Incorporate the BV. Get 50-250K pre-seed. |
| 2028-2030 | 29-31 | Build product, get 2-5 pilot customers. Maybe VLAIO R&D grant. |
| 2030-2031 | 31-32 | Revenue reaches 500K-1M ARR. Small seed round or stay bootstrapped. |
| 2031-2033 | 32-34 | Acquired by a network planning vendor or telco for 3-10M. |
| 2033-2035 | 34-36 | Retention period at acquirer. VP-level role. |
| 2035+ | 36+ | **Choice point**: stay at acquirer, go to Brussels policy, or start something new. |

**Financial outcome**: 1.5-6M net after tax and dilution.
**Career position**: PhD + startup founder + VP at major telco vendor. This is an elite profile for Brussels policy roles.

### Scenario 2: Things go well (probability: ~20%)

| Year | Age | What happens |
|---|---|---|
| 2026-2028 | 27-29 | Same as Scenario 1. |
| 2028-2031 | 29-32 | Product takes off. Regulatory tailwind from ICNIRP 2020 enforcement. |
| 2031-2032 | 32-33 | ARR hits 3-5M. Series A from imec.xpand or international VC. |
| 2032-2035 | 33-36 | Grow to 15-40M valuation. Acquired by Ericsson/Nokia or continue growing. |
| 2035+ | 36+ | Financially independent. Full freedom to choose next move. |

**Financial outcome**: 5-20M net.
**Career position**: Can do literally anything. Brussels policy, angel investing, another startup, academic appointment, early retirement.

### Scenario 3: Modest outcome / lifestyle business (probability: ~15%)

| Year | Age | What happens |
|---|---|---|
| 2026-2030 | 27-31 | Same start. Product works but market adoption is slow. |
| 2030-2035 | 31-36 | Company stabilizes at 200-500K ARR. 2-4 employees. Profitable but not scaling. |
| 2035+ | 36+ | **Decision point**: Keep running as lifestyle business (~100-150K/year income) or wind down. |

**Financial outcome**: Comfortable living but no big exit.
**Career position**: Solid but less dramatic. You have a running company and can transition to industry at any time.
**Risk**: This is the zombie trap. Set a kill criterion to avoid drifting here unintentionally.

### Scenario 4: Failure (probability: ~20%)

| Year | Age | What happens |
|---|---|---|
| 2026-2028 | 27-29 | Innovation Mandate. Product development. |
| 2028-2030 | 29-31 | Enter istart. Build product. Operators show interest but don't buy. |
| 2030-2031 | 31-32 | Market doesn't materialize. Zone-based methods remain "good enough." Wind down. |
| 2031-2032 | 32-33 | 6-month job search (40% callback penalty). Land at Ericsson/Nokia/Proximus. |
| 2032+ | 33+ | Industry career, ~3 years more senior than if you'd gone straight to industry. |

**Financial outcome**: ~33K opportunity cost over 5 years. Negligible.
**Career position**: PhD + postdoc + founder experience. Per Gompers et al., you land a position ~3 years more senior than peers. You're a 32-year-old at the seniority level of a 35-year-old. This compounds over a career.

### Expected value across all scenarios

| Scenario | Probability | Financial outcome (midpoint) | Weighted value |
|---|---|---|---|
| OK exit | 45% | 3.75M | 1.69M |
| Strong exit | 20% | 12.5M | 2.50M |
| Lifestyle business | 15% | 0 (ongoing income) | 0 |
| Failure | 20% | -33K | -6.6K |
| **Expected value** | | | **~4.2M** |

The expected value is strongly positive. Even being very conservative on probabilities, the combination of low downside (VLAIO-funded) and meaningful upside makes this a rational bet.

---

## 17. Work intensity and time allocation

### How many hours per week?

The "grind 80 hours" narrative comes from VC-backed founders in San Francisco burning through runway with 18 months until death. That is not this situation. The VLAIO Innovation Mandate provides 2 years of guaranteed salary. The incentive structure rewards outcomes, not performance theater.

**Target: 20-25 focused hours per week.** Not 40. Not 60.

| Activity | Hours/week | When it matters most |
|---|---|---|
| Customer discovery | 5 | Months 1-12 (non-negotiable) |
| Product development | 10-15 | Months 6-24 |
| Applications/admin | 2-3 | Bursty around deadlines |
| Networking/mentor | 2-3 | Ongoing |
| Learning | 2 | Months 1-6 |
| **Total** | **~25** | |

### Why not more?

The bottleneck is not development speed. With AI-assisted development (Claude Code agents in parallel), product development that would take a team of 3 engineers 6 months can be done by one person in weeks. The bottleneck is:

- **Customer conversations**: One human talking to another human, 45 minutes each. Cannot be parallelized.
- **Relationship building**: Mentors, TechTransfer, VLAIO contacts. Runs at human speed.
- **Enterprise sales cycles**: 6-18 months regardless of product readiness.
- **Institutional timelines**: VLAIO panel decisions take 6 months. Nothing changes this.

### VLAIO mandate obligations

The mandate pays a full postdoc salary. The formal requirement is that "the majority of time must be reserved for research activities." In practice:

- No timesheets. Nobody clocks hours.
- Progress is evaluated at 6-month reviews.
- The deliverable is: did you make progress toward the spin-off?
- If the spin-off is progressing, you are fine. If it is not, no amount of hours saves you.

### Who cares and who does not

**Who might care:**
- The academic supervisor (Wout Joseph): Keep him in the loop with monthly updates. That is enough.
- VLAIO panel: They see progress at the 6-month review. They care about customer conversations, product milestones, and a clear story. Not your calendar.
- imec.istart: They care about results at demo day.

**Who does not care:**
- Customers (they care if the product works)
- Future investors (they care about traction)
- Future acquirers (they care about revenue)

Nobody in the Belgian startup ecosystem will ask how many hours you worked.

### Side activities during the mandate

**Low risk:**
- Consulting/freelancing in EMF/RF domain. Actually helps the spin-off by building relationships and market knowledge.
- Open source contributions to adjacent projects. Builds reputation.
- Teaching, guest lectures. Builds credibility.
- Writing/content creation about EMF/5G. Good marketing for AEGIS.

**Medium risk:**
- Unrelated freelance software development. Takes time but nobody checks.

**High risk:**
- Starting a second company during the Innovation Mandate. UGent employment contract may restrict this.
- Working for a competitor. Obvious conflict.
- Anything publicly visible that makes it look like you are not focused on the spin-off while VLAIO is paying you.

**Practical note:** The Innovation Mandate is a postdoc contract under UGent regulations. Check the rules on "bijberoep" (secondary occupation). Most Belgian university contracts allow it with notification, but some require approval. Know the rule before testing it.

### The pattern of successful mandate founders

Founders who succeed with VLAIO mandates tend to:
- Work intensely but not constantly: 25-30 focused hours/week on the spin-off
- Spend disproportionate time on customer discovery early (months 1-6)
- Shift to product development mid-mandate (months 6-18)
- Shift to sales and fundraising late-mandate (months 18-24)
- Use the remaining flexibility to think clearly rather than thrash

The ones who fail tend to either: (a) treat it like a relaxed postdoc and never talk to customers, or (b) build obsessively for 2 years and launch a product nobody wants.

---

## 18. Recommendations

### Do it. But do it the smart way.

1. **Finish the PhD.** The credential matters for technical credibility in deep-tech and for EU policy roles later. You are almost done. Do not abandon it.

2. **Apply for the VLAIO Innovation Mandate (spin-off track)** in the September 2026 call. This is the single most important action item. It gives you 2 years of funded runway with zero equity dilution.

3. **Apply to imec.istart** during or right after the mandate. 20% acceptance rate is reasonable for your profile (sole inventor, working product, 2,177 tests, validated against published data).

4. **Find a co-founder with commercial DNA.** This is the biggest gap in your profile. You have the technology and the development speed. You need someone who can sell to telecom companies, navigate enterprise procurement, and handle the business side. VCs will ask about this. istart mentors can help here.

5. **Bootstrap as long as possible.** Use VLAIO grants (non-dilutive) instead of VC money whenever possible. Every euro of grant money is a euro of equity you keep. The IID makes your IP income taxed at 3.75%.

6. **Set a kill criterion.** If after 3 years post-istart you do not have 500K ARR or a clear path to it, make a deliberate decision: pivot hard, seek acquisition, or wind down. Do not drift into zombie territory.

7. **Keep the Brussels path in mind.** Every decision you make (which conferences to attend, which regulators to talk to, which standards bodies to engage with) should build toward policy credibility. Attend BEREC workshops. Participate in 5G-PPP EMF consultations. Write position papers. This builds the network that gets you to Brussels at age 34-36.

8. **Do not over-optimize on tax.** Belgium's tax structure for software companies is actually competitive (IID + VVPRbis + low capital gains). The Reddit complaints about Belgian taxes are mostly about employee taxation, not founder/IP taxation. Get a good accountant and focus on building the product.

9. **Do not move abroad to save on taxes.** The institutional support (VLAIO, istart, UGent network, IMEC ecosystem) is worth far more than the tax savings from Estonia or Portugal. The Belgian deep-tech ecosystem is one of the best in Europe.

10. **Protect your mental health.** 72% of entrepreneurs experience mental health conditions. This is not weakness, it is statistics. Build in support structures from the start: co-founder, mentor, regular exercise, non-startup social connections. The Innovation Mandate period (structured, salaried, low-pressure) is a good time to establish these habits.

---

## 19. Sources

### Academic papers

- Kacperczyk, A. & Younkin, P. (2022). [A Founding Penalty: Evidence from an Audit Study on Gender, Entrepreneurship, and Future Employment](https://pubsonline.informs.org/doi/10.1287/orsc.2021.1456). Organization Science, 33(2), 716-745.
- Ding, W. (2023). [Are entrepreneurs penalized during job searches? It depends on who is hiring](https://sms.onlinelibrary.wiley.com/doi/full/10.1002/sej.1479). Strategic Entrepreneurship Journal.
- Gompers, P., Kovner, A., Lerner, J., & Scharfstein, D. (2010). [Performance persistence in entrepreneurship](https://www.sciencedirect.com/science/article/abs/pii/S0304405X09002311). Journal of Financial Economics, 96(1), 18-32.
- Freeman, M.A. et al. (2018). [The prevalence and co-occurrence of psychiatric conditions among entrepreneurs and their families](https://link.springer.com/article/10.1007/s11187-018-0059-8). Small Business Economics, 53, 323-342.

### Government and institutional sources

- [Eurostat - Key Figures on European Business 2022: Business Dynamics](https://ec.europa.eu/eurostat/cache/htmlpub/key-figures-on-european-business-2022/business_dynamics.html)
- [Statbel - Survivals of VAT-registered enterprises](https://statbel.fgov.be/en/themes/enterprises/vat-registered-businesses/survivals-vat-registered-enterprises)
- [Statbel - 67% of enterprises created in 2016 were still active in 2021](https://statbel.fgov.be/en/news/67-enterprises-created-2016-were-still-active-2021)
- [VLAIO - Innovation Mandates](https://www.vlaio.be/en/subsidies/innovation-mandates)
- [VLAIO - Innovation Mandate amounts](https://www.vlaio.be/en/subsidies/innovation-mandates/amount-innovation-mandate)
- [VLAIO - Baekeland Mandates](https://www.vlaio.be/en/subsidies/baekeland-mandates)
- [VLAIO - Research Project grants](https://www.vlaio.be/en/subsidies/research-project/what-amount-could-you-be-awarded-through-research-project-grant)
- [VLAIO - Development Project](https://www.vlaio.be/en/subsidies/development-project/amount-development-project-subsidy)
- [KU Leuven LRD - Spin-off Policy](https://lrd.kuleuven.be/en/spinoff/lrds-spin-off-policy)
- [UGent TechTransfer - Spin-offs](https://techtransfer.ugent.be/en/spin-offs)
- [UGent TechTransfer - Spin-off overview](https://techtransfer.ugent.be/en/overview-spin-companies-ghent-university-association)
- [UGent TechTransfer - Fast Lane scheme](https://techtransfer.ugent.be/en/news/fast-lane-scheme-approved-ugent-speeds-spin-creation-new-standard-pathway)

### IMEC and ecosystem

- [imec.istart program](https://www.imecistart.com/en)
- [imec.istart reaches 1 billion in follow-up funding](https://www.imecistart.com/en/news/imec-istart-reaches-milestone-of-1-billion-in-follow-up-funding)
- [imec.istart - Significant growth and international recognition](https://www.imec-int.com/en/articles/imec-istart-secures-significant-growth-international-recognition)
- [imec.xpand 300M fund](https://www.techzine.eu/news/infrastructure/119454/tech-fund-imec-xpand-raises-300-million-euros-for-deep-tech-startups/)
- [IMEC Spin-offs](https://www.imec-int.com/en/spin-offs)

### Market and valuation data

- [SaaS Valuation Multiples 2015-2025 - Aventis Advisors](https://aventis-advisors.com/saas-valuation-multiples/)
- [2025 Private SaaS Company Valuations - SaaS Capital](https://www.saas-capital.com/blog-posts/private-saas-company-valuations-multiples/)
- [SaaS Valuation Index Q2 2025 - Translink](https://translinkcf.com/2025/09/11/saas-valuation-index-q2-2025-reveals-four-trends-shaping-saas-ma/)
- [The SaaS M&A Report 2025 - SaasRise](https://www.saasrise.com/blog/the-saas-m-a-report-2025)
- [Founder Ownership Report 2025 - Carta](https://carta.com/data/founder-ownership/)
- [Founder Ownership by Round - EquityList](https://www.equitylist.co/blog-post/founder-ownership-by-round)
- [Startup Founder Salary 2026 - OpenVC](https://www.openvc.app/blog/startup-founder-salary)
- [Founder salaries Europe - Sifted](https://sifted.eu/articles/founder-salaries-2023)
- [Founder Compensation 2.0 - Creandum](https://creandum.com/stories/founder-compensation-2024/)

### Deep tech and exits

- [2025 European Deep Tech Report - Dealroom](https://content.dealroom.co/uploaded/2024/11/2025-European-Deep-Tech-Report.pdf)
- [M&A in European tech 2024 - Sifted](https://sifted.eu/articles/exits-startups-europe-2024-data)
- [Deep tech exits: Not just science fiction anymore - TechCrunch](https://techcrunch.com/2023/12/06/deep-tech-exits-not-just-science-fiction-anymore/)
- [76 European deep-tech spinouts hit unicorn/centaur status - TechCrunch](https://techcrunch.com/2025/12/30/76-european-deep-tech-university-spinouts-reached-unicorn-or-centaur-status/)
- [Belgian tech funding 2025 - Agoria](https://www.agoria.be/en/themes/industry-clusters/software-products-saas/belgian-tech-funding-in-2025-fewer-euros-stronger-conviction)
- [Belgium's VC deep dive - SeedBlink](https://seedblink.com/blog/2024-03-05-belgiums-vc-deep-dive-the-rise-of-the-flanders)

### Belgian tax and legal

- [Belgium modernizes investment deduction and IP regime - EY](https://www.ey.com/en_gl/technical/tax-alerts/belgium-modernizes-investment-deduction-regime-and-enhances-ip-regime)
- [Innovation Income Deduction: New BELSPO guidelines - Deloitte](https://www.deloitte.com/be/en/services/tax/blogs/innovation-income-deduction-for-copyrighted-software-new-belspo-guidelines.html)
- [Belgium Corporate Tax Credits and Incentives - PwC](https://taxsummaries.pwc.com/belgium/corporate/tax-credits-and-incentives)
- [Belgium committed to strong tax incentives for innovation - Osborne Clarke](https://www.osborneclarke.com/insights/belgium-committed-strong-tax-incentives-innovation-and-rd)
- [Belgium's capital gains tax changes 2026 - PwC](https://news.pwc.be/belgiums-comprehensive-capital-gains-tax-changes-key-updates-and-implications-starting-january-2026/)
- [New Belgian Capital Gains Tax - EY](https://www.ey.com/en_be/technical/tax/tax-alerts/2025/new-belgian-capital-gains-tax-implications-for-expatriates)
- [Innovation income deduction - ICT Legal Guide](https://www.ictrechtswijzer.be/en/innovation-deduction/)

### Founder retention and career

- [How Often Founders Stay Post-Acquisition - WinSavvy](https://www.winsavvy.com/how-often-founders-stay-post-acquisition-retention-stat-study/)
- [After Selling Your Startup: Demotion and Identity Crisis - Inc.](https://www.inc.com/magazine/201906/thomas-goetz/exit-acquisition-merger-after-sale.html)
- [HBS: Why a Failed Startup Might Be Good for Your Career](https://www.library.hbs.edu/working-knowledge/the-success-of-persistent-entrepreneurs)
- [PhDs Aren't Starting Companies Like They Used To](https://whoisnnamdi.com/phd-founders/)

### EU policy and telecom

- [DG CONNECT - EU Commission](https://commission.europa.eu/about/departments-and-executive-agencies/communications-networks-content-and-technology_en)
- [BEREC](https://www.berec.europa.eu/en)
- [Career Opportunities in EU Advocacy and Lobbying - EuroBrussels](https://www.eurobrussels.com/article/841/career-opportunities-in-eu-advocacy-and-lobbying)
- [How to Get a Job in Digital Policy - EUJobs.co](https://www.eujobs.co/career-guides/digital-policy-career-guide)
- [5G and electromagnetic fields - EU Digital Strategy](https://digital-strategy.ec.europa.eu/en/policies/5g-and-electromagnetic-fields)
- [ETNO-GSMA policy positions](https://etno.eu/news/all-news/769-telecom-sector-joins-forces-in-call-for-new-policies-to-drive-eu-connectivity-leadership.html)
- [Ericsson - Accurately assessing EMF exposure from 5G](https://www.ericsson.com/en/reports-and-papers/white-papers/accurately-assessing-exposure-to-radio-frequency-electromagnetic-fields-from-5g-networks)
- [5G-PPP - Beyond 5G/6G EMF Considerations whitepaper](https://5g-ppp.eu/wp-content/uploads/2023/07/EMF-TF-white-paper_v1.2__.pdf)

### Competitors and market

- [IXUS Software](https://ixusapp.com/)
- [CloudRF](https://cloudrf.com/)
- [Ranplan Wireless - Tracxn](https://tracxn.com/d/companies/ranplan-wireless/__9ogV-C3YP1At99zf-NXj9Nz5xLkpNuZLw2aYSzwfkn8)
- [RF Planning and Optimization Software Market](https://marketintelo.com/report/rf-planning-and-optimization-software-market/amp)

### EU Inc. and 28th Regime

- [EU Inc.: A new harmonised corporate legal regime - European Commission](https://commission.europa.eu/topics/business-and-industry/doing-business-eu/company-law-and-corporate-governance/eu-inc-new-harmonised-corporate-legal-regime_en)
- [Commission presents proposal for EU Inc. - Press release](https://ec.europa.eu/commission/presscorner/detail/en/ip_26_614)
- [EU Inc. proposal full text - COM(2026) 321](https://commission.europa.eu/document/download/3e9822aa-8cef-40a1-904e-a53fc68e7265_en)
- [28th Regime Timeline and Progress Tracker](https://the28thregime.eu/progress)
- [European Parliament Legislative Train - 28th Regime](https://www.europarl.europa.eu/legislative-train/theme-a-new-plan-for-europe-s-sustainable-prosperity-and-competitiveness/file-28th-regime-for-innovative-companies)
- [What is EU Inc.? Complete Guide - eu.inc](https://eu.inc/what-is-eu-inc)
- [EU Inc. marks major win for startups - Tech.eu](https://tech.eu/2026/03/18/eu-inc-marks-major-win-for-startups-as-commission-unveils-28th-regime-proposal/)
- [What is EU-INC and its plan to make European businesses borderless - Euronews](https://www.euronews.com/my-europe/2026/02/03/what-is-eu-inc-and-its-plan-to-make-european-businesses-borderless)

### Jurisdiction comparison

- [Is an Estonian Company the right solution if you live in Belgium? - Taxpatria](https://www.taxpatria.be/is-an-estonian-company-the-right-solution-if-you-live-in-belgium/)
- [Estonian e-Residency: cross-border taxes](https://www.e-resident.gov.ee/understanding-cross-border-taxes/)
- [Estonia e-Residency: legal limits and hidden compliance costs - Key2Law](https://key2law.com/en/news/using-estonias-e-residency-to-form-companies-legal-limits-and-hidden-compliance-costs)
- [Portugal NHR 2.0 (IFICI) Tax Regime Guide](https://www.globalcitizensolutions.com/new-nhr/)
- [Portugal IFICI Regime - Expert Guide](https://immigrantinvest.com/blog/portugal-ifici-regime/)
- [Netherlands Innovation Box - Business.gov.nl](https://business.gov.nl/subsidies-and-schemes/innovation-box/)
- [Netherlands WBSO R&D Tax Scheme](https://newtone.nl/wp-content/uploads/2025/01/Programmatuur-Fiscale-subsidie-WBSO-en-innovatiebox-ENG.pdf)
- [Netherlands Corporate Tax 2025 - PwC](https://taxsummaries.pwc.com/netherlands/corporate/taxes-on-corporate-income)

### Delaware flip and US incorporation

- [Sapphire Ventures: What European Founders Need to Know about Flipping](https://sapphireventures.com/blog/what-european-founders-need-to-know-about-flipping-to-a-u-s-company-structure/)
- [The Delaware Flip: What Startups Should Know - SPZ Legal](https://spzlegal.com/blog/the-delaware-flip)
- [Delaware Flip: Get Ready for US Investment - SeedLegals](https://seedlegals.com/grow/delaware-flip/)
- [What Is a Delaware Flip? - Caribou](https://www.usecaribou.com/post/how-to-do-a-delaware-flip)
- [For foreign startups, incorporating in Delaware is the path to scale - Rest of World](https://restofworld.org/2021/all-roads-lead-to-delaware/)
- [Why Stripe Atlas is Bad for Foreigners - Flag Theory](https://flagtheory.com/stripe-atlas/)
- [Stripe Atlas Review: Starting a US Company as non-US residents - Rapidr](https://rapidr.io/blog/stripe-atlas/)
- [Why VCs Prefer Delaware C-Corps - Harvard Business Services](https://www.delawareinc.com/blog/why-venture-capitalists-prefer-delaware-c-corps/)
- [IPA subsidiary BioStrand receives VLAIO grant](https://www.businesswire.com/news/home/20220509005550/en/IPA%E2%80%99s-Subsidiary-BioStrand-Secures-Second-VLAIO-Research-Grant)
- [US-Belgium Income Tax Treaty - IRS](https://www.irs.gov/pub/irs-trty/belgiumtt06.pdf)
- [US VC Trends for 2026: What European Founders Need to Know](https://www.usxp.co/resources/us-vc-trends-for-2026-what-european-founders-need-to-know/)

### Community input

- [Reddit r/Belgium2: Building a SaaS in Belgium. Genuinely losing my mind.](https://reddit.com/r/Belgium2/comments/1rr8l5l/building_a_saas_in_belgium_genuinely_losing_my/) (March 2026, 161 upvotes, 130 comments)

### Zombie companies

- [VRT NWS: Too many zombie businesses in Belgium](https://www.vrt.be/vrtnws/en/2017/04/13/_too_many_zombiebusinessesinbelgium-1-2950043)
- [EU JRC/OECD: Fear the Walking Dead - zombie firms study](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC111915/jrc111915_jrc111915_jrc-oecd_fear_the_walking_dead_-_withpubsynumbers.pdf)

---

*This report synthesizes publicly available data, academic research, government program documentation, and community input. Financial projections are estimates based on market comparables, not guarantees. Tax information reflects the regime as of April 2026 and should be verified with a qualified Belgian tax advisor before making decisions.*
