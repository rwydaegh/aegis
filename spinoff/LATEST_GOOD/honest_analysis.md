# Honest analysis of AEGIS as a spin-off

*Claude Opus, April 2026. Written after reading the IDF, monograph (including the near-field section), spin-off reports, co-founder analysis, commercial moats, GOLIAT synergy doc, personal advice files, feature inventory, and after targeted web research on ICNIRP 2020, IEC 62232:2025, IEC/IEEE 63195-2, SPEAG DASY8, ZMT/Sim4Life, IXUS, mmWave deployment status, and Ericsson's internal compliance tooling. This is an opinion, not a summary. The questions being asked internally are mostly the wrong questions.*

---

## Framing

Robin's internal docs keep asking "will the spin-off work" and "what's the expected value." Those aren't the questions that decide the outcome. The questions that do are below, with honest answers.

---

## Q1. Who is the actual incumbent, and is AEGIS displacing them?

Robin's pitch frames the competition as Sim4Life/CST (slow expensive FDTD) and IXUS/MVG (zone-based, no body geometry). That framing is wrong and hides the real incumbent. There are in fact two different markets with two different incumbents.

**Base-station compliance market.** The real incumbent is **IXUS (Alphawave/EMSS, South Africa)**. They already have Vodafone, T-Mobile, Telstra, AT&T, TPG, MTN, Vodacom, and Ericsson Australia as customers. One Alphawave MNS customer manages 20,000+ base stations through it. It is the Salesforce of base-station EMF compliance and it already handles ICNIRP 2020 and 5G massive MIMO via "actual maximum" envelope patterns per IEC 62232:2025. On top of that, **Ericsson has an internal MATLAB tool ("MSI compliance analyzer")** that reads MSI antenna pattern files and computes compliance boundaries. Nokia has similar. Sim4Life and CST live in R&D and test labs, not in operator compliance workflows.

Corollary: "replacing Sim4Life in operator workflows" is fiction because Sim4Life was never in operator workflows to begin with. Operators live on IXUS plus Narda measurement gear plus internal spreadsheets from IEC 62232.

**Device pre-compliance market.** The real incumbent stack is **ZMT Sim4Life + SPEAG DASY8 + IT'IS Foundation tissue database + cSAR3D**. This is the "Kuster ecosystem" and it has been built over 20 years. 1000+ DASY systems installed worldwide. Every mmWave-capable phone OEM (Apple, Samsung, Google, Xiaomi, OPPO, Vivo, Huawei, OnePlus, Motorola), every chipset vendor (Qualcomm, MediaTek), and most test labs run some variant of this pipeline for pre-certification. DASY8 covers 3 kHz to 110 GHz, the DASY83D integration combines cSAR3D pre-screening with full DASY8 for gold-standard evaluation.

These are two genuinely different markets and AEGIS's story is very different in each.

---

## Q2. What is AEGIS actually for?

Ordered by tractability, not by pitch-deck prominence:

### (a) mmWave device pre-compliance — the biggest wedge, and the one the internal docs underweight

Every mmWave-capable phone needs APD (absorbed power density) pre-compliance evidence under FCC rules and IEC/IEEE 63195-2. The frequency range is 6 to 300 GHz, typical distances 5 to 200 mm from skin. Every design iteration runs pre-compliance simulations, often thousands of beam-configuration × hand-grip × body-position scenarios per product. FDTD at mmWave is hours per scenario. This is the single largest Sim4Life revenue pool in the dosimetry world.

This is exactly the regime AEGIS covers (see Q3 on near-field). The pitch is not "replace Sim4Life" but "accelerate pre-screening by 100-1000x, then feed the worst-case scenarios into Sim4Life for rigorous validation, then DASY for physical certification." Sim4Life seat count doesn't fall; its value rises because worst cases are found in seconds instead of sampled blindly.

TAM sketch: 10-15 OEMs × 5-50 compliance engineers × 30-60K/yr Sim4Life-equivalent seats = 2-45M/yr in simulation seat equivalents, plus chipset vendors, test labs, academic. 30-100M globally is the right order.

Key point: **mmWave network deployment slowdown (T-Mobile handing spectrum back, Verizon pivoting to C-band) does NOT hurt this market.** Apple ships mmWave-capable iPhones to every US buyer whether or not the network lights up a cell nearby. Regulatory compliance is required for the capability, not for its use. FCC demands APD compliance above 6 GHz. IEC/IEEE 63195-2 is the standard. This market is driven by regulation and device shipment volume, not network capex.

### (b) ZMT / Sim4Life licensing partnership — the distribution channel

The AEGIS-on-top-of-Sim4Life framing (fast pre-screener, viewer layer, gradient-based antenna design) is commercially much more tractable than displacing FDTD. ZMT already has every customer AEGIS wants to sell to. Revenue share / co-brand / extension SKU is a normal deal structure in simulation. GOLIAT (Robin's 42k-line Sim4Life automation wrapper, Sim4Life competition winner) is the proof that Robin understands and respects their stack and isn't trying to replace them.

Wout has explicitly suggested this path. It's under-explored in the docs. It should probably be the primary commercial path in year 1, not plan B.

### (c) IXUS+dosimetry for base-station compliance teams at Tier-1 operators

Specialist EMF compliance teams (not RF planners — RF planners don't own compliance) at Tier-1 operators. Use case: site fails the reference-level test, operator escalates to basic-restriction analysis (actual S_ab on a body mesh) to defend the site at 80% of rated power instead of 40%. AEGIS does this in a browser. IXUS does not. Price per seat 10-30K/yr. Total compliance specialists globally at Tier-1 operators: 500-1000 people. Small but real.

### (d) Academic / research tier — the community-building play

Every RF-body-interaction PhD student currently chooses between Sim4Life (expensive), openEMS/MEEP/gprMax (free but clunky), or in-house custom FDTD. Offering a free-or-cheap academic tier of AEGIS (Python-native, differentiable, IT'IS-compatible, fast) gets citations, standards-body recognition, and a pipeline: today's grad student is tomorrow's compliance engineer at Apple/Samsung/Qualcomm. This is the Kuster move ZMT pulled via IT'IS tissue data.

### (e) Regulator / national spectrum authority tooling

BIPT, Ofcom, ANFR, BNetzA have weaker in-house tools than the operators they regulate. Lower ceiling per customer (20-50K/yr) but very sticky once adopted and a direct path to being cited in IEC 62232 / IEC 63195. Standards-body leverage.

### (f) Test labs

Eurofins, Verkotan, PCTEST, UL, TUV. Short sales cycle (lab director decides). Plausible short-term first revenue.

None of these wedges is "sell to operators to run dosimetry at every base station." That market doesn't exist today and probably won't exist for 3-5 years.

---

## Q3. What does the theory actually say about near-field, and why does it matter?

The `monograph_v2.tex` sec:near-field defines three regimes:

| Regime | Boundary | AEGIS applicable? |
|---|---|---|
| Reactive near-field | $d < \lambda/(2\pi)$ | **No.** Evanescent and impedance coupling need full-wave. |
| Radiating near-field (locally plane-wave) | $\lambda/(2\pi) < d < 5L$ | **Yes.** Point-source extension with spatially varying $S_\mathrm{inc}$ and $\hat{k}$. Still O(M) per source. |
| Far-field | $d > 5L$ | **Yes.** Original framework. |

Reactive NF boundaries:
- 28 GHz: 1.7 mm
- 60 GHz: 0.8 mm
- 3.5 GHz: 14 mm
- 900 MHz: 53 mm

What this means for device compliance:

- **mmWave handsets (28, 39, 60 GHz, future 6G)** typically sit 5-200 mm from skin. Entirely in AEGIS's valid regime. This is exactly IEC/IEEE 63195-2 territory (6-300 GHz, $\le$ 200 mm).
- **Sub-6 GHz handsets at the ear** are inside the reactive near-field. AEGIS cannot touch sub-6 device SAR. GOLIAT can via Sim4Life automation, but AEGIS alone cannot.
- **Wearables at 60 GHz (smart glasses, AR headsets, hearables)** at 5-30 mm from skin: in-regime, genuinely exciting application.
- **UWB short-range (<10 GHz) on body**: partially outside the regime.
- **Implantable devices** at sub-GHz: deep-body volumetric problem, not surface. Out of scope.

The monograph also gives a **spherical-harmonic decoupling** ($\Gamma_{lm}(\mathbf{r}_s)$, ~50 MB LUT for phone-scale geometry) that separates antenna pattern from body response. Commercially meaningful: "try 10,000 antenna patterns at this phone position" becomes a dot product per pattern. That's exactly the inner loop of an OEM antenna designer.

**The differentiability claim is concretely valuable here.** "Move this array element to minimize APD hot-spot on the face while maximizing beam gain" is a gradient descent problem AEGIS can solve in minutes. Sim4Life would need finite differences at full FDTD cost per step. This is a feature Sim4Life structurally cannot match.

Pseudo-Brewster compensation carries over cleanly because it's a local tissue-interface property. Spherical-wavefront curvature affects $S_\mathrm{inc}(\mathbf{r})$ per point, not $T_0$.

**Honest caveats:**
- Theory says it works. Published validation of AEGIS's point-source extension against Sim4Life on a real phone geometry at 28 GHz does not yet exist. That comparison is essential before pitching Apple or ZMT. Mie-sphere and existing validations are for simpler geometries.
- Numerical stability of gradients across realistic phone geometries with curvature, hand occlusion, and multiple antenna panels is an engineering question, not just a theoretical claim.
- Device compliance buyers are conservative. "We trust this new fast method" takes product cycles to earn. You're shortening the iteration loop of an existing Sim4Life user, not replacing Sim4Life.

---

## Q4. Is the physics insight actually novel?

Less confidently novel than the internal docs claim, and Robin should defend it to a skeptical reviewer before spending 15K EUR on PCT filing.

Pseudo-Brewster for lossy media is established physics (Kim & Vedam 1986). Kodera 2024 empirically observed that a nearly-constant transmission coefficient reproduces 3D FDTD to 5% from 10-100 GHz. Bamba 2012/2015 observed absorption efficiency ~0.5 empirically. Li 2019 observed angle-insensitivity numerically on flat skin.

The claim to novelty is: first to (a) derive T_0's near-constancy from Fresnel theory for biological tissue rather than observe it numerically, (b) extend it to spatial maps on 3D bodies, (c) produce a closed-form exposure operator Q for MIMO, (d) make the whole pipeline differentiable, (e) extend to radiating near-field with the spherical-harmonic decoupling.

Of these, (b), (c), (d), (e) as an integrated method are plausibly novel. (a) is borderline — may be a cleaner theoretical explanation of what Kodera/Li/Bamba already knew numerically. EPO will want more than "I derived what others observed." The system claim (IDF claim 4: base-station pipeline + 3D reconstruction + dosimetry + compliance + viewer) is the strongest patent claim because it bundles novelty with implementation.

Translation: **the moat is execution speed, base-station-database plumbing, viewer, partnership with ZMT, and standards-body recognition — not the physics.** The monograph, once published, lowers the barrier for a well-resourced competitor to re-derive and re-implement in a matter of months using modern AI-assisted development.

---

## Q5. Is Robin the right founder for this company?

Right founder for the first 12 months. Probably not the right founder for years 2-5 alone.

**Year 1 needs:** file a Belgian patent, defend a PhD, write the JSAC / TWC near-field paper, secure VLAIO, submit istart, build the ZMT demo, run matched AEGIS-vs-Sim4Life validation on a standard phone scenario. Robin can do all of that. He has the credentials, the supervisor network, the product, and an unusual technical velocity.

**Years 2-5 need:** cold-email ZMT, sit through 40 product discovery calls with OEM compliance engineers, negotiate OEM extension-SKU terms, price, forecast, hire, fire, manage pipeline churn. There is zero evidence in the documents that Robin has done any of this. The ROADMAP says 20 customer discovery calls this summer. Zero have happened as of April 2026. The personal files explicitly call out analysis paralysis, parallel career exploration of MBB/FAANG/EU/quant, and a prior pattern of researching LETF allocations for 2.5 years without investing a euro.

This doesn't kill the business. It means the real strategic question is not "should Robin do the spin-off?" but "how early and how aggressively does Robin bring in a commercial co-founder?"

Carolina is not that person. She is a PhD neuroscientist on the same supervisor, there to clear the istart 2-founder gate. She is useful for grant writing and BD but not for running an enterprise sales motion against ZMT or device OEMs.

The right structure, in my view:
- Use Carolina as istart co-founder. The 1-year cliff is the correct instrument.
- Use the istart year (Nov 2026 - Oct 2027) to find a commercial co-founder through the istart and ZMT network: ex-Sim4Life product manager, ex-SPEAG applications engineer, ex-Apple compliance lead, ex-Ericsson EMF team. Start with advisor equity (0.5-1%, 1-year cliff). Convert to co-founder (15-25%) only after proven.
- If no such person materializes by month 18, that is itself the kill signal.

---

## Q6. What does the Belgian context actually buy?

Under-appreciated externally, over-sold internally.

**What it genuinely buys:** A 2-year postdoc salary at 0% equity cost via VLAIO Innovation Mandate. A product-friendly IID tax regime (3.75% effective on IP income; better than Ireland 6.25%, Netherlands 9%). A near-zero-downside failure case (~33-60K opportunity cost over 2-4 years). A plausible path to 250-760K in mostly non-dilutive capital via VLAIO + IOF + istart + KBC. The most founder-friendly accelerator terms in Europe (istart 100K for 6% + convertible loan, imec claims no IP).

**What it does not buy:** Customers. A US distribution channel. VC scale. Belgian VCs are well-documented to be late-stage and risk-averse. Seed rounds at 5M pre are small by US standards.

**The honest read:** The Belgian ecosystem is exactly the right shape for a 3-15M EUR exit to a European strategic acquirer (ZMT, Dassault, ATDI, Forsk, an operator innovation arm), not for a 100M+ category winner. Building *for* a 3-15M exit is not glamorous but it is a rational strategy given the TAM (~30-100M global), the founder's current profile, and the acquirer landscape. UGent has a track record of this exact outcome: Feops → Materialise, Gatewing → Trimble, Caliopa → Huawei.

---

## Q7. What's the realistic outcome distribution?

My honest cut, with the near-field / device OEM story properly weighted:

| Outcome | My probability | Robin's internal |
|---|---|---|
| Fail / wind-down within 18 months (analysis paralysis wins) | 20% | 15-20% |
| Lifestyle / zombie (300-600K ARR, no exit) | 20% | 20% |
| Modest exit (3-10M, most likely ZMT, Dassault, or similar) | 35% | 25-30% |
| Good strategic exit (10-25M to Ericsson, Nokia, ZMT, Dassault) | 20% | 20-25% |
| Category winner (25M+) | 5% | 5% |

The thing that specifically lifts probability is a ZMT licensing deal within 12-24 months that evolves into an acquisition within 3-5 years. Very Belgian-deep-tech-shaped, fits the capital efficiency of the plan, and is the natural consequence of leading with device mmWave pre-compliance rather than base-station operator sales.

The thing that doesn't change: Robin still has to actually pick up the phone and call the right people. Apple, ZMT, Samsung, and the IEC TC 106 chair are not going to discover the password-protected viewer on their own.

Expected value is positive because the downside is genuinely 33-60K opportunity cost over 2-4 years, not "lost my house." The EV math actually tracks reality here rather than being Silicon Valley hagiography.

---

## Q8. What should Robin do that he isn't already planning?

**Rebuild the primary pitch around device mmWave APD pre-compliance, not base-station compliance.** The spin-off docs lead with telecom operators. Lead instead with "differentiable APD simulation for mmWave device pre-compliance, 100-1000x faster than FDTD, plugs into Sim4Life + DASY + IT'IS workflow." This is a tighter story for a validator and it maps to a known-paying customer base (Sim4Life's existing OEM customer list).

**Run matched validation against Sim4Life on a standard phone scenario.** Pick a published IEC 63195-2 benchmark (phone at the cheek at 28 GHz, Duke or Ella anatomical model, matched antenna pattern) and produce side-by-side AEGIS-vs-Sim4Life figures. This is the single strongest piece of evidence for any ZMT or Apple conversation. GOLIAT can run the Sim4Life side.

**Write the near-field paper as a standalone contribution.** The near-field section is buried inside a general-framework monograph. Separate paper, probably IEEE TAP or IEEE TMTT, titled around "Closed-form APD on 3D body for mmWave device pre-compliance." This is the calling card for device OEM conversations.

**Target the IEC TC 106 / IEEE ICES 63195-2 2026 revision process.** Wout is in that ecosystem. The window to get AEGIS mentioned as an acceptable computational method in the next edition is closing. The 2026 edition is in draft now. Standards adoption is worth more than any early customer. IEC 62232:2025 (base stations) is already published; target the 2027+ revision there.

**Pursue the ZMT/Sim4Life partnership as the primary commercial path, not as plan B.** Wout has the contact. First ask is not a license deal — it's a matched-validation collaboration ("we ran AEGIS against Sim4Life on Duke at 28 GHz; here are the figures; can we co-present at BioEM 2027?"). The license conversation comes after they trust the physics.

**Stop pitching operators as the first customer.** They're slow, IXUS-locked, and the sale goes through vendor relationships anyway. Test labs and national regulators are the short-cycle entry.

**Drop the "real-time" framing in enterprise pitches.** Operators and OEMs don't need real-time; they need reliable batch processing of 10,000 design variants or site configurations overnight. Same underlying feature, different framing. Real-time is a demo headline, not a buyer's need. Keep it in the viewer for conference demos.

**File the Belgian patent this month, not later.** PhD defense deadline is a hard cutoff per EPO absolute novelty. Every week of TechTransfer delay is risk. The IDF is 80% drafted into claims already. Push the "my defense is before August" timing constraint explicitly in the TechTransfer email.

**Commit to 6 real customer calls by end of May 2026.** Not 20, not to sell, just to listen. Target mix: 1 ZMT applications engineer, 2 device OEM compliance engineers (start with a Samsung or Xiaomi contact through Wout's network, not Apple), 2 test lab leads (Eurofins, Verkotan), 1 national regulator (BIPT is local). If Robin can't do 6 in 4 weeks, the spin-off is already broken. This is the single test that predicts everything downstream.

**Drop `career.txt`.** It's procrastination pretending to be research. Pick one backup path — EU institutions via JRC/ESA is the most credible given the profile — and let the rest go.

---

## Q9. Would a Preuve-style validator give this a green light?

Scoring the way a Preuve AI 6-dimension assessment would probably cut:

- **Problem validation: medium-strong.** ICNIRP 2020, IEC 62232:2025, IEC 63195-2 2026 draft are real regulatory artifacts. 5G massive MIMO at mmWave creates real simulation overestimation that the standards literature complains about openly (Ericsson 2021 white paper, Frontiers 2022, Samsung Research 2020). Device mmWave pre-compliance is a real burning problem at every OEM that ships mmWave.
- **Market demand: medium.** Academic and standards-body demand is clearly there. Device OEM simulation-acceleration demand is real and existing buyers are identifiable. Operator-side demand is weak for body-specific dosimetry today. Test-lab demand is plausible but small.
- **Competitor landscape: misread in the internal docs, but genuinely favourable for the device-pre-compliance framing.** IXUS is the base-station incumbent (not Sim4Life). ZMT Sim4Life + SPEAG DASY is the device incumbent but they are a natural partner rather than a frontal competitor. The Kuster ecosystem is a moat, but it's a moat that can be joined rather than broken.
- **Unit economics: strong gross margins, medium TAM, long sales cycle risk.** Classic deep-tech B2B shape. Payback periods 12-24 months.
- **Timing and defensibility: mixed.** Regulatory tailwinds real (IEC 62232:2025, IEC 63195-2 2026, ICNIRP 2020 adoption). mmWave network slowdown is noise for device compliance, real for operator compliance. Post-LLM replicability of the method post-monograph is a genuine weakness. The defensibility has to come from execution, standards recognition, and ZMT ecosystem integration, not from the math alone.
- **Founder-market fit: technically excellent, commercially unproven, structurally risky.** Supervisor is the biggest commercial asset. Co-founder structure is weak. Founder has no sales track record and self-reports analysis paralysis. Near-zero customer discovery to date.

That's a "proceed with structural changes" rating, not a "greenfield winner" rating. It's also a "do this because the downside is genuinely capped at ~60K, not because the EV math is spectacular" rating.

---

## The thing to sit with

The dominant failure mode for this company is not "the market isn't there" or "the physics was wrong." Both of those produce a clean failure at month 18 that lets Robin land at ETNO or JRC with a good story.

The dominant failure mode is a 300-500K ARR company with 5 test-lab customers and no acquirer interest by year 4, where Robin is 31 with a child, can't interview at Ericsson because they're a customer, and can't take a demanding EU job because the company still pays his salary. That's the zombie scenario. Belgium has 8.8% zombie firm rate, third-highest in OECD. 14% of Belgian companies run at losses for 3+ years.

The hard kill date at 18 months — 1 paying customer or signed LOI or wind down — is the single most important piece of the whole plan. Every other recommendation is downstream of actually enforcing it.

---

## Sources

- [IEC 62232:2025 base station EMF assessment](https://webstore.iec.ch/en/publication/89073)
- [IEEE/IEC 63195-2 computational procedure, 6-300 GHz, draft 2026 edition](https://standards.ieee.org/ieee/63195-2/7717/)
- [SPEAG DASY8 near-field SAR evaluation, 3 kHz-110 GHz](https://speag.swiss/products/dasy8/dasy8-state-of-the-art-wireless-device-compliance-testing)
- [ZMT Sim4Life platform](https://sim4life.swiss/)
- [Ericsson: Accurately assessing EMF exposure from 5G](https://www.ericsson.com/en/reports-and-papers/white-papers/accurately-assessing-exposure-to-radio-frequency-electromagnetic-fields-from-5g-networks)
- [ICNIRP 2020 implications on base station compliance (Frontiers 2022)](https://www.frontiersin.org/journals/communications-and-networks/articles/10.3389/frcmn.2022.744528/full)
- [Samsung Research: Era of 5G and standardization of human exposure to EM fields](https://research.samsung.com/blog/The-Era-of-5G-and-Standardization-of-Human-Exposure-to-Electromagnetic-Fields)
- [T-Mobile relinquishes mmWave spectrum (Light Reading)](https://www.lightreading.com/5g/t-mobile-relinquishes-mmwave-spectrum-not-feasible-to-deploy)
- [IXUS RF safety software, the base-station compliance incumbent](https://ixusapp.com/)
- [Kim & Vedam (1986), analytic pseudo-Brewster angle](https://www.semanticscholar.org/paper/Analytic-solution-of-the-pseudo-Brewster-angle-Kim-Vedam/b04187a59140bb3c6ef5336819d9f92e7d3c181c)
- [5G-PPP Beyond 5G/6G EMF Considerations whitepaper](https://5g-ppp.eu/wp-content/uploads/2023/07/EMF-TF-white-paper_v1.2__.pdf)
- [5G mmWave market 2025-2030 (Mordor Intelligence)](https://www.mordorintelligence.com/industry-reports/5g-mm-wave-market)
- Monograph near-field section: `theory/monograph_v2.tex` sec:near-field
- Feature inventory: `docs/internal/features.md`
- IDF: `spinoff/IDF_geometric_dosimetry.md`
