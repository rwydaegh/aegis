# De-risking the head-worn / XR RF exposure market

Prepared 2026-07-14. Adversarial review. Every non-obvious claim carries a URL. Unsourced items are quarantined in the NOT VERIFIED section at the end.

## Verdict

**FICTION, as stated.** Every clause of the market hypothesis is false against primary evidence. RF exposure for head-worn devices is not an unsolved problem, there is an established method, there is an established phantom, and the vendors are already quantifying the risk and passing. Meta's own FCC filing for the Ray-Ban Meta AI glasses (FCC ID 2AYOA-4003, Sporton report FA541802A, 17 June 2025) reports both SAR and absorbed power density for a 6 GHz Wi-Fi radio in the temple arm, measured on the SAM head phantom with a SPEAG near-field probe, and passes at 65 % of the FCC power density limit. Worse for us, the one head-worn radio that genuinely sits above 6 GHz today (Wi-Fi 6E/7 at 5925 to 7125 MHz) is compliance-tested at 0 to 2 mm from the head, which is deep inside the reactive near field at those frequencies (lambda/2pi = 7.4 mm at 6.5 GHz). That is the exact regime AEGIS declares out of scope. So the one real above-6-GHz head-worn exposure problem in existence is structurally in AEGIS's blind spot, and the regulator that governs it has stated a preference for measurement over simulation. The coordinator's Wi-Fi 6E APD lead is factually correct and is the biggest finding in this report, but it does not rescue the thesis: it converts "no market" into "a real market that AEGIS cannot serve, in which SPEAG already sells the box."

The honest reframing at the end of this document (`Where the real business is`) points back at FR3 base stations and far-field network exposure, which is where AEGIS already lives.

---

## Part 1: the Wi-Fi 6E / 6 GHz APD lead (verified, and it is the most important section)

### The ISED claim is TRUE, with one correction

ISED Canada did publish **SPR-APD, Issue 1**, "Supplementary Procedure for Assessing Specific Absorption Rate (SAR) and Absorbed Power Density (APD) Compliance of Portable Devices in the 6 GHz Band (5925-7125 MHz)", on **2 June 2022**, as a supplement to RSS-102 and tied to the newly published RSS-248.
Source: https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/spr-apd-supplementary-procedure-assessing-specific-absorption-rate-sar-and-absorbed-power-density
Public consultation record: https://approve-it.net/canada-ised-publishes-rss-248-and-opens-public-consultation-on-rss-102-spr-apd/

**Correction the coordinator needs:** SPR-APD Issue 1 has been **rescinded**. The ISED page now says "This document is now rescinded; its content is now part of: RSS-102.SAR.MEAS". Its content was folded into **RSS-102.SAR.MEAS Issue 2, dated 15 August 2025**, as **Annex F** ("The content of this annex was previously published in Supplementary Procedure SPR-APD").
Source: https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/measurement-procedure-assessing-specific-absorption-rate-sar-compliance-accordance-rss-102

The substantive requirement survives and is still live. So: **yes, APD is already a live certification requirement in a G7 country for Wi-Fi 6E.** That part of the lead is real.

### But here is what actually kills it

**1. In the 6 to 7.125 GHz range, ISED does not compute APD. It derives APD from a measured SAR.**
RSS-102.SAR.MEAS states that within 6 GHz to 7.125 GHz, APD is derived from SAR measurements using the conversion formulas in **IEC PAS 63446**, not from direct power density measurement and not from simulation. IEC PAS 63446:2022 is titled "Conversion method of specific absorption rate to absorbed power density ... Frequency range of 6 GHz to 10 GHz".
Sources: https://webstore.iec.ch/en/publication/75849 and https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/measurement-procedure-assessing-specific-absorption-rate-sar-compliance-accordance-rss-102

The compliance pipeline is therefore: **robot + probe measures SAR in a liquid phantom, software converts to APD.** There is no computational entry point. A simulation engine is not part of this flow at all.

**2. SPEAG already sells the box, and it is the only box.**
SPEAG's DASY8 Module SAR / APD covers SAR from 4 MHz to 10 GHz and APD from 6 GHz to 45 GHz, and explicitly lists IEC PAS 63446 in its supported-standards list.
Source: https://speag.swiss/products/dasy8/m-sar-apd

The independent test house Verkotan, which runs this service commercially, states the position with no ambiguity: "RF Exposure assessment for Wi-Fi 6E devices for sale in Canada now requires both SAR and APD measurements", the APD limit is 10 W/m2, and **"APD is measured rather than simulated"**, using "SAR measurement systems that comply with RSS-102 and IEC/IEEE 62209-1528" with SAR-to-APD conversion algorithms.
Source: https://verkotan.com/2023/advances-in-wi-fi-technology-and-rf-exposure-testing-capabilities/

**3. The EU has not adopted it.** Verkotan (same source) states that in the EU, SAR remains the metric up to 10 GHz, and APD will only replace SAR above 6 GHz "as and when the 2020 version of ICNIRP guidelines ... becomes recommended by the European Union." As of this review I found no EU harmonised standard under the RED requiring APD for 6 GHz Wi-Fi. So the Canadian requirement is, today, a single-country requirement.

**4. The FCC does not use APD at all here, and has no published procedure.**
This is the crux for the largest market. FCC KDB Publication 987594 (U-NII 6 GHz devices, 5.925-7.125 GHz) says, verbatim:

> "For U-NII 6-7 GHz band portable devices (subject to MPE power density limits, not SAR limits), until the FCC publishes specific additional exposure evaluation guidance, applicants and test labs may submit a KDB inquiry for review of the RF exposure evaluation plan before completing testing and submitting to a TCB, consistent with KDB Pub. 388624 PAG requirements by a TCB under PAG OVER6G."

Source (public draft, 4 April 2024): http://hctinsight.com/webzine/webzine/202407/file/fcc/fcc1.pdf
KDB index entry: https://apps.fcc.gov/oetcf/kdb/forms/FTSSearchResultPage.cfm?id=277034&switch=P

Three things follow. First, at the FCC the regulated quantity above 6 GHz is **incident** MPE power density (1 mW/cm2 = 10 W/m2, from 47 CFR 1.1310), **not** absorbed power density. Second, there is genuinely **no published FCC method** and every applicant must file a pre-approval (PAG OVER6G) KDB inquiry. Third, that friction is real and it is exactly what Meta hits, as the next section shows. But the FCC's answer to that gap is to write a measurement procedure, not to accept a solver.

**5. The FCC has explicitly said it prefers measurement to simulation in this band.** SPEAG's report of the IEC TC106 meeting records the FCC position that measurements are preferred over numerical simulations for above-6-GHz exposure evaluation, "particularly due to difficulties in validating the numerical model against the physical device", with simulation relegated to helping identify worst-case phase combinations.
Source: https://speag.swiss/news-events/news/measurement/iec-tc106-meeting-update/
Confidence: high on the substance, medium on currency (that meeting report is from 2017 and the position may have softened, see NOT VERIFIED).

### Is 6 GHz exposure binding, or trivially met? Real numbers from real filings

This was the crux question and the answer is **it is binding, but not for us.**

**Ray-Ban Meta, gen 1** (models RW4006 / RW4008 / RW4009 / RW4009F / RW4010 / RW4006M, FCC ID 2AYOA-4003, Sporton report FA272102-03, issued 30 January 2024). Sub-6 SAR summary:

| Condition | Band | Reported 1 g SAR (W/kg) | Limit | % of limit |
|---|---|---|---|---|
| Face-worn, 0 mm | 5 GHz WLAN | 0.85 | 1.6 | 53 % |
| Rest-on-shirt, 0 mm | 2.4 GHz WLAN | 1.02 | 1.6 | 64 % |
| Highest simultaneous Tx | BT + WLAN | **1.33** | 1.6 | **83 %** |

Source: https://fcc.report/FCC-ID/2AYOA-4003/7103737.pdf

83 % of the limit on a pair of sunglasses. That is not "5 % of the limit and no pain". It is a device that has to be actively managed. Confirming that: the same filing declares four **power states (A/B/C/D)** keyed to exposure conditions (Face-Worn, Rest-on-Head, Rest-on-Shirt, Pocketing, Free Space) driven by a "Sensor Fusion Algorithm and Power State Decision Logic Flow", the details of which were negotiated in a **KDB inquiry with the FCC**. Meta built wear-detection hardware and a power-backoff state machine because exposure is a binding constraint.

**Ray-Ban Meta, gen 2 "AI Glasses"** (models RW4012 / RW4013 / RW4013F / RW4014, same FCC ID 2AYOA-4003, Sporton report **FA541802A**, issued **17 June 2025**). This is the WLAN 6 GHz report, covering **5925 to 7125 MHz**:

| Quantity | Face-worn 0 mm | Rest-on-head 0 mm | Rest-on-shirt 0 mm | Pocket in case 5 mm | Handheld in case 0 mm | Limit |
|---|---|---|---|---|---|---|
| Reported 1 g SAR (W/kg) | 0.27 | 0.13 | 0.25 | 0.43 | 0.21 (10 g) | 1.6 / 4.0 |
| Measured APD (W/m2) | 1.20 | 0.51 | 0.92 | 2.71 | 3.56 | (reference only) |
| Max scaled total psPD (W/m2) | | | | | **6.46** | **10** |

Source (fetched from fccid.io mirror of exhibit 2AYOA-4003_TestRpt_SAR_WLAN_6GHz): https://fccid.io/2AYOA-4003/RF-Exposure-Info/2AYOA-4003-TestRpt-SAR-WLAN-6GHz-8440744

So the peak spatially averaged power density is **6.46 W/m2 against a 10 W/m2 limit, i.e. 65 % of limit**, with a tune-up power of only 6.5 to 13.5 dBm. There is pain here. There is not much headroom. A vendor that wanted to raise Wi-Fi 6E transmit power in these glasses would run into the wall.

**But read what the filing says the method is.** From the same report:

- Limit basis: "Peak Spatially Averaged Power Density was evaluated over a square area of 4 cm2 per **interim FCC Guidance for near-field power density evaluations per October 2018 TCB Workshop notes**".
- Phantom: "The device was mounted on the **SAM Head-Stand Phantom** as it is intended to be worn, the detailed please refer to **KDB inquiry with the FCC**."
- Method: "evaluate incident PD using the **mmw near-field probe and total-field/power-density reconstruction method (2 mm closest meas. plane)**".
- Status of APD: "also report estimated absorbed (epithelial) power density (**for reference purposes only, not specifically for compliance**) and estimated incident PD, derived from measured SAR."
- Metrology gap admitted: "SPEAG has not yet developed the specific phantom SAR system check target values for the 7 GHz band."

Read that list again. There **is** a method. There **is** a phantom (SAM). It is a measurement method. APD is explicitly **not the compliance quantity** at the FCC, it is a reference number. And the residual uncertainty is a **metrology** gap (missing 7 GHz system-check targets), not a **modelling** gap.

### The structural killer: reactive near field

AEGIS's own hard limit is that it cannot compute inside roughly lambda/(2*pi) of the antenna.

| Frequency | lambda | lambda/2pi |
|---|---|---|
| 6.0 GHz | 50.0 mm | 7.96 mm |
| 6.5 GHz | 46.2 mm | **7.35 mm** |
| 7.125 GHz | 42.1 mm | 6.70 mm |
| 28 GHz | 10.7 mm | 1.71 mm |
| 60 GHz | 5.0 mm | 0.80 mm |

The Ray-Ban Meta 6 GHz filing tests **face-worn at 0 mm separation**, and the worst-case body position is "Left Temple Arm Outer Edge Touching Phantom, gap 2 mm". The antenna-to-tissue distance is on the order of **2 mm at 6.0 to 7.1 GHz**, which is **a quarter of the reactive near-field radius**. AEGIS is, by its own stated scope, invalid there.

This is not a detail that can be engineered around. It is the defining geometry of the entire device class: eyewear puts the antenna in contact with the head. Any tool that requires the radiating near field cannot serve eyewear at 6 to 7 GHz. Ironically, AEGIS would be *more* valid at 28 or 60 GHz (lambda/2pi of 1.7 mm and 0.8 mm) than at the frequency band that head-worn devices actually use.

**And one more:** the Wi-Fi 6E band is 5925 to 7125 MHz. The slice from 5925 to 6000 MHz is **below** 6 GHz and requires volumetric 10 g / 1 g SAR, which AEGIS cannot compute at all. So even in a world where the near-field problem vanished, AEGIS could only address part of a single band and the customer would still need a second tool and a second phantom for the rest of it. It is not a complete answer to any regulatory question that exists.

---

## Part 2: the radio inventory (the load-bearing table)

Confidence key: **[V]** verified from a primary FCC filing or manufacturer page I read. **[S]** secondary press or spec sheet. **[?]** unverified, see NOT VERIFIED.

| Device | Radios | Frequencies | Above 6 GHz? | Power / notes | Source |
|---|---|---|---|---|---|
| **Ray-Ban Meta gen 1** (RW4006-RW4010) | BT BR/EDR/LE, WLAN 2.4, WLAN 5, **WLAN 6 GHz U-NII-5/6/7/8** | 2402-2480, 2412-2472, 5180-5825, **5955-7095 MHz** | **YES (partial)** | Max sim-Tx 1 g SAR **1.33 / 1.6 W/kg (83 %)**. Antenna in temple arm. Power-state machine with wear detection. | [V] https://fcc.report/FCC-ID/2AYOA-4003/7103737.pdf |
| **Ray-Ban Meta gen 2 "AI Glasses"** (RW4012-RW4014) | as above | **WLAN 6 GHz 5925-7125 MHz** | **YES (partial)** | Tune-up 6.5-13.5 dBm. **psPD 6.46 / 10 W/m2 (65 %)**. APD 1.20 W/m2 face-worn. Left temple arm, 2 mm gap. | [V] https://fccid.io/2AYOA-4003/RF-Exposure-Info/2AYOA-4003-TestRpt-SAR-WLAN-6GHz-8440744 |
| **Meta Ray-Ban Display** | BT, Wi-Fi 6E (6 GHz), plus the sEMG "Neural Band" wristband link | incl. 6 GHz | **YES (partial)** | Meta states Wi-Fi 6E. I did not locate its distinct FCC exhibit. | [S] https://www.meta.com/blog/meta-ray-ban-display-ai-glasses-connect-2025/ |
| **Meta Quest 3 / 3S** | BT, **Wi-Fi 6E (6 GHz)** | 2.4 / 5 / 6 GHz | **YES (partial)** | FCC filing confirmed 6 GHz. Antennas in the front shell and strap, not in skin contact. | [S] https://www.uploadvr.com/meta-quest-3-fcc-6ghz-wi-fi/ |
| **Meta Orion** (prototype) | wireless link to a compute "puck" | undisclosed | **[?]** | Not a shipping product. No FCC grant. | [?] |
| **Apple Vision Pro** (FCC ID BCG-A2117) | BT, **Wi-Fi 6 only** | 2.4 / 5 GHz | **NO** | **No 6 GHz. No UWB. No mmWave.** Entirely sub-6, i.e. entirely outside AEGIS's regime. | [S] https://fccid.io/BCGA2117 and https://9to5mac.com/2024/01/16/apple-vision-pro-uwb-wifi-6e-7/ |
| **Apple smart glasses** | rumoured, unannounced | n/a | **[?]** | No product, no filing, no radios to inventory. | [?] |
| **Samsung Galaxy XR** (Project Moohan) | BT 5.4, **Wi-Fi 7** | incl. 6 GHz | **YES (partial)** | Wi-Fi 7 includes the 6 GHz band. Snapdragon XR2+ Gen 2. Headset, not eyewear. | [S] https://en.wikipedia.org/wiki/Samsung_Galaxy_XR |
| **Snap Spectacles (5th gen)** | BT, Wi-Fi | **[?]** | **[?]** | Not verified. | [?] |
| **Xreal / Rokid / Viture** display glasses | mostly USB-C tethered, BT | 2.4 / 5 GHz | **NO (probable)** | These are display terminals driven over a cable. Minimal radio. | [?] |
| **Vuzix, Even Realities** | BT LE, Wi-Fi | 2.4 / 5 GHz | **NO (probable)** | [?] | [?] |
| **HTC Vive Wireless Adapter** | **WiGig 802.11ad, 60 GHz** (Intel) | 57-64 GHz | **YES, fully** | The only genuinely, fully above-6-GHz head-mounted radio I found. Receiver clips to the headset. **Discontinued, niche volume.** | [S] https://www.vive.com/us/accessory/wireless-adapter-full-pack/ |
| **Qualcomm Snapdragon AR/XR reference** | Wi-Fi 7 (incl 6 GHz), BT | incl. 6 GHz | **YES (partial)** | Reference platform, not a certified end product. | [?] |

### The three conclusions from this table

1. **Nothing head-worn ships with FR2 5G mmWave or FR3.** Not one device. Not Meta, not Apple, not Samsung, not Snap.
2. **Apple Vision Pro, the flagship of the category, is 100 % sub-6.** No 6 GHz, no UWB. If the pitch is "Apple faces a launch risk they cannot quantify", the answer is that Apple's headset does not even have a radio in the regime.
3. **The only above-6-GHz head-worn radios that exist are Wi-Fi 6E/7 at 5925-7125 MHz**, and as shown in Part 1, that band is (a) tested in the reactive near field where AEGIS is invalid, (b) partially below 6 GHz where AEGIS cannot compute SAR at all, and (c) already served by a measurement pipeline.

The 60 GHz WiGig headset link is the one genuinely AEGIS-shaped case. It is a discontinued accessory for a headset line with negligible volume.

---

## Part 3: the secondary questions

### Q1. Is exposure actually binding, or trivially met?

**Binding, in the sense that matters to the vendor. Not binding in a way that creates demand for a solver.**

The Ray-Ban numbers above (83 % of the SAR limit sub-6, 65 % of the power density limit above 6) show real pressure. Meta responded with hardware (wear-detection sensor fusion) and a negotiated power-state architecture, not with better simulation. The company also has a dedicated headcount for this: a Meta Reality Labs job posting for **"Wireless Design Validation Engineer (RF Exposure SAR/PD)"** requires "3+ years hands on experience on wireless SAR/PD testing/evaluation **using DASY system**, and experience **filing FCC KDB inquiries and ISED General Inquiries**", for products spanning 5G NR, Wi-Fi 6/6E and Bluetooth.
Source: https://www.jointaro.com/jobs/meta/wireless-design-validation-engineer-rf-exposure-sarpd/

That job description is the single most useful piece of competitive intelligence in this whole document. **Meta's exposure budget is spent on a robot and a regulatory-affairs process, not on a solver.** The skills they buy are DASY operation and KDB inquiry drafting. A faster APD engine solves neither.

Counterpoint, honestly stated: the 60-to-83 % headroom means that when Meta wants to raise Wi-Fi 6E power, or add a radio, or move an antenna, someone has to predict whether the change busts the budget before committing to a build. That is a pre-compliance design question and it is genuinely worth money. But it is not a new market, it is the existing Sim4Life / XFdtd / HFSS market, and the customer already owns those seats.

### Q2. The eye specifically

**No carve-out, no gap, and the academic space is crowded.**

ICNIRP 2020 does not create a special eye limit above 6 GHz. It classifies the **cornea, anterior chamber and iris as Type-1 tissue** (5 degC threshold) alongside limbs and the pinna, while the rest of the eye and head are **Type-2** (2 degC). That is a *less* restrictive classification for the front of the eye, not a more restrictive one.
Source: https://www.icnirp.org/en/differences.html and https://journals.lww.com/health-physics/fulltext/2022/09000/analysis_of_icnirp_2020_basic_restrictions_for.1.aspx

There is no eye-specific compliance phantom in the certification chain. The chain uses **SAM**, and Meta's filing confirms glasses are tested on the SAM Head-Stand phantom.

Academically the space is well populated. Hirata's group (Nagoya Institute of Technology) authored the definitive review of above-6-GHz computational dosimetry (https://iopscience.iop.org/article/10.1088/1361-6560/abf1b7, preprint https://arxiv.org/pdf/2011.10699), the APD-and-temperature-rise study for non-planar body models (https://arxiv.org/pdf/2007.02604), and the time-temperature threshold work underpinning the limits (https://pmc.ncbi.nlm.nih.gov/articles/PMC8300848/). Ocular mmWave dosimetry has its own literature, down to the level of **modelling the effect of eyelashes on corneal APD** (Foroughimehr et al., Bioelectromagnetics 2024, https://onlinelibrary.wiley.com/doi/abs/10.1002/bem.22526) and localized ocular exposure systems (Sasaki and Sakai).

**Our differentiator here would be speed, not novelty, and nobody in this field is bottlenecked on speed.** A dosimetry paper computes one exposure scenario and publishes it. The FDTD run taking four hours is not the reason the paper took a year.

### Q3. Is the standards gap real?

**No. It was real in 2019. It is closed or closing, and the closure explicitly excludes our method.**

Published:
- **IEC/IEEE 63195-1:2022** Measurement procedure, power density, 6 to 300 GHz, devices in close proximity to head and body. https://webstore.iec.ch/en/publication/62755
- **IEC/IEEE 63195-2:2022** Computational procedure, power density, 6 to 300 GHz. https://webstore.iec.ch/en/publication/62754 Already implemented in Remcom XFdtd: https://support.remcom.com/xfdtd/standards/iec-ieee-63195-2.html
- **IEC PAS 63446:2022** SAR-to-APD conversion, 6 to 10 GHz. https://webstore.iec.ch/en/publication/75849
- **IEC/IEEE 62209-1528:2020** SAR measurement, 4 MHz to 10 GHz (used for the 5925-6000 MHz slice). https://ieeexplore.ieee.org/document/9231298/

In development under IEEE ICES / IEC TC106, both with **PAR approved 2024-09-26**:
- **IEEE/IEC P63195-3**: Measurement procedures for **absorbed power density**.
- **IEEE/IEC P63195-4**: Computational procedures for **absorbed power density**. Working group chair **John Roman**, sponsor BOG/ICES. https://standards.ieee.org/ieee/63195-4/11782/

Read the P63195-4 scope verbatim:

> "This document specifies computational procedures for conservative and reproducible computations of the absorbed power density (APD) or epithelial power density ... **The computational procedures described are finite-difference time-domain (FDTD) and finite element methods (FEM)** ... The methods apply to devices with single or multiple transmitters or antennas that operate with their radiating structure(s) at distances up to 200 mm from the human head or body."

The standard that will govern computational APD **names FDTD and FEM as the methods**. AEGIS is neither. A closed-form ray-optics surface method is not an accepted computational procedure under the standard being written right now, and it would take a multi-year standards campaign to make it one. Meanwhile the incumbents (Sim4Life, XFdtd, CST) are FDTD/FEM and are already compliant by construction.

Also note that ISED has flagged a coming **RSS-102.APD.MEAS** for devices above 7125 MHz, with "general test methods ... for compliance assessment of time-averaged absorbed power density (TA-APD)". Again: a **measurement** procedure.

The honest summary: **there is no method gap. There is a metrology gap** (SPEAG lacks 7 GHz system-check targets), and that gap is SPEAG's to close, not ours.

### Q4. Evidence of commercial pain

Genuine pain exists, and it is worth naming precisely because it is not the pain we can treat.

- **FCC has no published procedure for 6 GHz portable RF exposure** and routes every applicant through a pre-approval inquiry under PAG code OVER6G. That is a real, repeated, per-SKU cost in calendar time and consulting fees. (KDB 987594, cited above.)
- **Meta had to negotiate its glasses test setup with the FCC by KDB inquiry**, twice, including the SAM head-stand mounting and the power-state logic. (Both Ray-Ban filings say "please refer to KDB inquiry with the FCC".)
- **Meta staffs a dedicated RF exposure SAR/PD validation engineer** in Reality Labs. A team is a budget. But the budget line is measurement and regulatory affairs.
- **SPEAG's own metrology is behind the band**: no 7 GHz phantom system-check targets as of June 2025.
- **Patent activity exists** on exposure management in this device class, e.g. "Eyewear with RF shielding having grounding springs" (US 12,342,516) and "Configurable radio frequency exposure compliance based on region" (US 11,871,359, US 12,273,825). I did not verify the assignees. See NOT VERIFIED.

The pattern in all of it: the money flows to **robots, phantoms, labs and lawyers**. Not to solvers.

### Q5. The FR3 / 6G timing thesis

3GPP has set the Release 21 (6G) timeline: functional freeze **December 2028**, code freeze **March 2029**, with first commercial systems targeted for **2030**.
Sources: https://www.3gpp.org/news-events/3gpp-news/rel21-timeline and https://www.lightreading.com/6g/it-s-official-6g-specs-are-set-for-early-2029

The upper mid-band (roughly 6.4 to 7.125 GHz) and cmWave (7 to 15 GHz) are the headline 6G bands.

**Head-worn FR3 is not on any roadmap I could find.** No vendor has announced an FR3 or FR2 radio in a headset or in glasses. XR devices are Wi-Fi-tethered by design because a cellular modem is a thermal and battery problem in a 50 g frame. Meta's Quest FCC filings have shown 5G test appendices, but no shipping XR product has a cellular modem.

So the honest timing answer for **head-worn FR3** is: **not 2029-2031, but unknown and probably never in the form imagined.** The device physics argue against it. That is worse than "late". "Late" is fundable. "Speculative and possibly never" is not.

Note that **FR3 for the network side (base stations, CPE) is a completely different story and is real**. That is the AEGIS thesis that already exists, and this study does not undermine it.

### Q6. Sizing

Units (IDC, via https://www.idc.com/resource-center/blog/smart-glasses-surge-the-xr-market-is-rewriting-its-own-rules/ and https://my.idc.com/getdoc.jsp?containerId=prUS54033425):
- Display-less smart glasses: **~13.6 M units in 2026**, **27.3 M by 2030** (18.9 % CAGR).
- Mixed reality headsets: **3.2 M (2026)** to **10.4 M (2030)**.
- Optical see-through display glasses: **3.0 M (2026)** to **12.2 M (2030)**.
- Total XR 2025: 14.5 M units, up 41.6 %.

**But units are the wrong denominator. SKUs are the denominator, and SKUs are tiny.** The Ray-Ban Meta gen 1 filing covers **six model numbers under one FCC ID and one test campaign**, because the variants differ only in "color of frames, lenses, and sizes". Meta certifies on the order of **a handful of RF-distinct platforms per year**. Apple certifies one headset. Samsung one.

Certification cost per SKU (secondary sources, treat as order-of-magnitude, confidence LOW):
- Basic SAR test: **USD 3,000 to 5,000**. https://compliancetesting.com/sar-testing-cost/
- Wi-Fi-integrated device with 5/6 GHz scanning: **USD 6,500 to 12,000**. https://markready.io/learn/fcc-certification-cost
- Complex multi-band body-worn: up to **USD 30,000** in SAR alone.

**Honest addressable-spend estimate for head-worn RF exposure certification, globally: low single-digit millions of USD per year in lab fees, essentially all of it going to test houses and to SPEAG's hardware.** Confidence: LOW to MEDIUM, derived from (a few RF-distinct head-worn platforms per year, across maybe 10 vendors) times (USD 10k-30k per campaign) plus regulatory-affairs headcount. There is no plausible arithmetic that gets a design-tool licence business to a meaningful number from this segment alone.

The simulation-tool spend at Meta and Apple (HFSS, CST, Sim4Life seats and the antenna teams that use them) is much larger, but it is an **antenna design** budget, not an **exposure** budget, and displacing ANSYS/Dassault/ZMT inside those teams is a different and much harder company to build.

### Q7. Who would we actually email?

The people are findable but the pitch has nowhere to land. Named and semi-named:

- **John Roman** (US), working group chair, IEEE/IEC **P63195-4** (computational APD), sponsor BOG/ICES. https://standards.ieee.org/ieee/63195-4/11782/ He is also named as a co-convener of the IEC/IEEE 62704-2 joint work. https://www.ices-emfsafety.org/publication-iecieee-62704-2-dual-logo-standard-providing-protocol-compliance-assessment-vehicle-mounted-antennas/
- **Teruo Onishi** (Japan), **Kai Niskala** (Finland), **Andreas Christ** (Switzerland), co-conveners on the same joint IEC/IEEE work. Same source.
- **Akimasa Hirata**, Nagoya Institute of Technology. Author of the above-6-GHz computational dosimetry review and the APD/temperature work that the ICNIRP 2020 limits rest on. Already known to Robin (see the military-angle study, which recommended a standards paper with Hirata).
- **Jafar Keshvari**, active in the joint IEC TC106 / IEEE ICES meetings. https://www.linkedin.com/posts/jafar-keshvari-3233201_iectc106-ieeetc34-emfsafety-activity-7331401869803573251-SKgg
- **IEEE ICES TC34 subcommittee roster**: https://ices-emfsafety.org/committees/tc34-subcommittees (I did not enumerate individual members, see NOT VERIFIED).
- **Meta Reality Labs**: the RF exposure SAR/PD validation team. The hiring manager for the "Wireless Design Validation Engineer (RF Exposure SAR/PD)" role is the right door, but the requirement list tells you they want a DASY operator, not a solver vendor.
- **SPEAG (Schmid and Partner Engineering AG)** and **ZMT / IT'IS Foundation**, Zurich. If there is any commercial relationship to be had in this space, it is a **partnership or acquisition conversation with SPEAG/ZMT**, not a competitive one. They own the measurement chain, they sit on TC106, and they sell Sim4Life. Confidence: high that they are the gatekeeper, unknown whether they would want anything from us.

I did not find named RF exposure compliance leads at Apple, Google, Snap or Qualcomm. See NOT VERIFIED.

### Q8. Nearby markets, ranked

Ranked by (is there a real above-6-GHz exposure constraint) x (is AEGIS's regime valid) x (is there money).

**1. FR3 / upper-mid-band network-side exposure (base stations, CPE, fixed wireless).** Far field, beamforming, above 6 GHz, exposure genuinely binding for EIRP-limited deployments, and AEGIS's exposure-constrained beamforming solver is directly relevant. This is not a "nearby market", it is the existing AEGIS thesis, and this study strengthens the case for staying there.

**2. FR2 5G mmWave handsets (24-47 GHz).** The single largest genuine above-6-GHz body-worn exposure problem in the world. psPD limited, binding, huge SKU volume. lambda/2pi = 1.7 mm at 28 GHz, so antenna-to-skin distances of 5 to 20 mm are in AEGIS's regime. **But** the compliance route is measurement (SPEAG DASY with the 5G phantom), the standard is IEC/IEEE 63195-1/-2, and the incumbents are entrenched. Worth understanding, not obviously winnable.

**3. 60 GHz WiGig / 802.11ay links (including head-mounted receivers).** Fully in regime. Vanishing volume.

**4. 60 GHz in-cabin automotive radar and vital-sign radar. DEAD.** The FCC waivers that enable this class cap power at **13 dBm EIRP with a 10 % duty cycle**, i.e. **20 mW peak, 2 mW average**. Source: https://www.federalregister.gov/documents/2021/08/19/2021-16637/fcc-seeks-to-enable-state-of-the-art-radar-sensors-in-60-ghz-band and https://www.wiley.law/alert-FCC-Issues-Waiver-for-In-Cabin-Vehicle-Radar-in-60-GHz-Band. At those powers, exposure at an occupant is orders of magnitude below any limit. There is no pain and therefore no business.

**5. UWB in watches and hearables (6.5 to 9 GHz). DEAD, and this is a trap worth naming.** UWB is nominally above 6 GHz, which makes it look like a hook. But the FCC EIRP limit is **-41.3 dBm/MHz**, which over a 500 MHz channel is **-14.3 dBm total, i.e. 0.037 mW**. That is about 500 times weaker than the Ray-Ban's 6 GHz Wi-Fi radio. Exposure is trivially met by a factor of thousands. Anyone pitching UWB exposure as a market has not done the arithmetic.

**6. Wireless power transfer.** Mostly sub-6 and mostly reactive near field. Both of AEGIS's hard limits. Dead.

---

## NOT VERIFIED

Explicit list of everything I could not source. None of these are used to support the verdict.

1. **Meta Quest 3 / 3S actual reported SAR and power density values.** I confirmed Wi-Fi 6E via secondary press (UploadVR) but could not locate Meta's Quest FCC grantee code or the RF exposure exhibit on fccid.io or fcc.report. The verdict does not depend on it. If wanted, this needs a manual fccid.io lookup.
2. **Meta Ray-Ban Display's own FCC exhibit.** I have Meta's marketing claim of Wi-Fi 6E but not the filing.
3. **Snap Spectacles, Xreal, Rokid, Vuzix, Even Realities radio inventories.** I did not pull their FCC filings. My "probably sub-6" annotations are inference from product category, not evidence.
4. **Meta Orion radios.** Prototype, no filing exists to check.
5. **Assignees of US 12,342,516 ("Eyewear with RF shielding having grounding springs"), US 11,871,359 and US 12,273,825 ("Configurable radio frequency exposure compliance based on region").** patents.google.com returned 404 or empty for my queries. These could be Meta, Apple, Snap or a supplier. Patent density was requested as a proxy for spend and I have not delivered it. See NEEDS_CONTEXT.
6. **The FCC's current (2025/2026) position on numerical simulation for above-6-GHz portable RF exposure.** My source for "FCC prefers measurement" is SPEAG's report of an IEC TC106 meeting that I believe dates from 2017. I attempted to fetch FCC KDB 447498 D01 v06 and D04 and the October 2023 TCB workshop slides directly and **www.fcc.gov and apps.fcc.gov/kdb/GetAttachment are blocked or timing out from this environment**. The claim is consistent with the Ray-Ban filing being measurement-only, but I have not read the current FCC text. See NEEDS_CONTEXT.
7. **Whether the EU has any draft harmonised standard requiring APD above 6 GHz.** My source is Verkotan's 2023 article. I did not check the current OJEU list of harmonised standards under the RED.
8. **Japan (MIC), Korea and China positions on APD above 6 GHz.** Searches returned only general statements about their base-station limits. I have nothing specific on 6 GHz portable APD in those jurisdictions.
9. **Named RF exposure / EMF compliance leads at Apple, Google, Snap and Qualcomm.** Not found. Only Meta's role posting surfaced.
10. **Certification cost figures (USD 3k-30k per campaign).** These come from test-lab marketing pages, not from a quote or a contract. Confidence LOW. Treat as order-of-magnitude only.
11. **The addressable-spend estimate (low single-digit USD millions/year).** This is my arithmetic on top of item 10 and a SKU-count guess. Confidence LOW.
12. **The exact percentage of Meta's Sim4Life/HFSS/CST seat spend attributable to exposure rather than antenna design.** Not knowable from outside.

---

## What would change the verdict

Three specific facts. If any of the first two turns out to be true, this goes from fiction to real. I do not believe any of them are true today.

**1. A shipping head-worn device with an FR2 (24-47 GHz) or 60 GHz radio, with the antenna 5 mm or more from tissue.**
This is the single fact that would flip everything. At 28 GHz the reactive near field ends at 1.7 mm, so an antenna behind 5 mm of frame is in AEGIS's regime. At 60 GHz it ends at 0.8 mm. Such a device would have a genuine, binding, above-6-GHz exposure problem in exactly AEGIS's regime, with no reactive-near-field escape and no sub-6 SAR component. **Falsifier:** find an FCC filing for any head-worn product with a band above 24 GHz. I found none. The closest is the discontinued HTC Vive 60 GHz WiGig adapter, whose receiver sits on the outside of a headset shell. If Meta, Apple or Samsung announces a 60 GHz headset-to-puck or headset-to-PC link (which is a real engineering direction for wireless VR, because Wi-Fi 6E cannot carry the bitrate), **this market becomes real overnight and should be re-examined immediately.** That is the one watch item.

**2. A regulator or standards body accepting a non-FDTD/FEM computational route for APD or psPD compliance.**
Today IEEE/IEC P63195-4 names FDTD and FEM, ISED derives APD from measured SAR, and the FCC routes 6 GHz portable devices through a measurement-based PAG inquiry. If P63195-4 ballots with a clause admitting validated reduced-order or analytic methods with a defined uncertainty budget, a compliance-adjacent product becomes conceivable. **Falsifier:** read the P63195-4 draft. That requires an IEEE SA membership or a purchased draft. See NEEDS_CONTEXT.

**3. A vendor paying for pre-compliance design exploration rather than certification.**
The 65-83 % of limit numbers mean Meta has to predict, before building, whether an antenna move or a power increase busts the exposure budget. If a Meta or Google antenna team would pay for a millisecond-per-scenario exposure oracle to sweep temple-arm antenna placements, there is a small design-tool business. **But** it must survive two objections: the customer already owns Sim4Life, and the 6 to 7 GHz contact geometry is in AEGIS's invalid regime. To make this real, AEGIS would need a reactive-near-field extension, which is a research programme, not a feature.

## Where the real business is

Nothing in this study weakens the network-side FR3 case. It strengthens it by elimination. Above 6 GHz, in the radiating near field and far field, with beamforming, with exposure as a genuine binding constraint on deployment: that is base stations and fixed wireless in the 7 to 24 GHz band, not glasses. The exposure-constrained beamforming solver is the asset. Head-worn devices put the antenna against the skin, and against the skin is where AEGIS stops.

If this market is to be pursued at all, the correct move is **not** a Meta pitch. It is a conversation with **SPEAG / ZMT**, who own the measurement chain, sit on IEC TC106, and would be the ones to tell you whether a fast forward model has any role in the pipeline they control.
