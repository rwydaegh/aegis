# FR2 smartphone UE hardware model for direction 5 (Route B PoC)

Research note assembled 2026-04-23 via Tavily (pro research + advanced search + extract). Purpose: give the JSAC paper's "UE model" section a defensible physical-realism footing, and answer whether Route B's "per-element IQ + UE-side AoA" assumption survives contact with commercial hardware.

---

## TL;DR — the recommended FR2 smartphone UE model

| Parameter | Value | Source / note |
|---|---|---|
| Number of physical mmWave modules (panels) | **2 (typical shipping phone), up to 4 (X50 reference max)** | Qualcomm X50 press release [Q1]; iFixit iPhone 12 teardown shows 2 [IF12]; iFixit Galaxy S23 teardown shows 2 [IF23]; Qualcomm placement whitepaper analyzes the 2-module case as canonical [QWP] |
| Active modules at a time | **1** (module-selection based on per-module SSB-RSRP; alternates tracked as backups) | Qualcomm / Microwave Journal: "X50 modem ... was already monitoring alternatives on the other modules ... beam switching across multiple modules" [5GTW]; 3GPP UL single-panel-at-a-time was baseline through Rel-16, multi-panel UL transmission (STxMP) only introduced as optional in Rel-17/18 [EP4529299, Qcom-R17] |
| Elements per module | **1×5 dual-polarized linear array (10 ports per module), 1×4 also common** | Qualcomm mmWave placement whitepaper: "each antenna module consists of a 5×1 dual-polarized linear antenna array" [QWP]; Microwave Journal on QTM052: "2×2 array" [MWJ-QTM]; academic designs at λ/2 consistently 1×4 [MWJ-Smart] |
| Polarization | **Dual-pol (±45° slant or H/V, depending on vendor)** | Qualcomm QTM052 family "2×2 MIMO with dual polarization" [Q1]; QTM10028 FCC filing: "8×8 dual-pol antenna array ... independent H/V beamforming" [FCC-QTM10028] (note: QTM10028 is small-cell, not handset); dual-pol is universal across QTM series [QEverythingRF] |
| Inter-element spacing | **λ/2 ≈ 5.36 mm at 28 GHz** | Qualcomm whitepaper: "antenna elements are typically placed at λ/2 (≈ 5.36 mm) inter-antenna element spacings" [QWP] |
| Total aperture per module | **~21 mm (1×5) or ~16 mm (1×4)** = ~2λ–1.5λ; Rayleigh beamwidth ≈ 2/N rad ≈ 23°–29° per module | Derived from λ/2 spacing above |
| Beamforming architecture | **Analog / hybrid: phase shifters + PAs in the RFIC; ONE IF chain per polarization per module → 2 ADCs per active module in the baseband** | Qualcomm whitepaper: "size-9 analog beamforming codebook" [QWP]; TechInsights QTM10028 spec: "coax IF interface" and "independent beamforming per layer" [FCC-QTM10028]; X70 modem spec describes "modem-to-antenna" [QX70] |
| Codebook exposed to higher layer | **3GPP Type I / Type II codebook indices, CRI + L1-RSRP per SSB/CSI-RS, PMI/RI/CQI — NOT per-element IQ** | 3GPP TS 38.214 §5.2: reportQuantity is CSI-related or L1-RSRP [TS38214]; no standardized per-element export path [ARXIV-BB] |
| Typical per-carrier BW | **100 MHz most common, up to 400 MHz; SCS = 120 kHz** | 3GPP TS 38.101-2 Table 5.3.5-1: n261 supports {50, 100, 200, 400} MHz with 60/120 kHz SCS [TS38101]; Qualcomm X65 spec "1000 MHz bandwidth (mmWave), 10 carriers" via CA [QX65] |
| 3GPP reference element | GE,max = 3 dBi (TR 38.828 Table 5.2.2.5.4-1); ITU-R M.2412 uses 5 dBi Table 11 | [TR38828], [M2412] |

**In prose.** A US-market flagship 5G mmWave smartphone (iPhone 12–15 Pro US, Galaxy S20–S23 Ultra US) carries **2–3 physically separated mmWave antenna modules** bonded to the chassis frame or logic-board back, where each module is an integrated SiP: one small phased array (the industry-standard implementation is 4 or 5 dual-polarized patch/dipole elements on λ/2 pitch), the PA/LNA chain per pol, and an up/down-conversion stage. Only ONE module is RF-active for a given UL/DL direction at any given time; the modem runs a fast beam-sweep across SSB/CSI-RS beams on each module and switches to the module with best L1-RSRP when the current one is blocked (hand, body, building). The post-combining output of the active module is a pair of IQ streams (one per polarization), and this is the first thing the baseband / application layer can see. Everything upstream of that — the per-element phase-shifted analog sums — is locked inside the RFIC.

## Query 5 answer: can a commercial FR2 smartphone support Route B's UE-side AoA estimation?

**Not with stock commercial hardware/software, in the strong sense of "per-element complex baseband IQ → classical AoA algorithms (MUSIC / ESPRIT / ML)."**

Evidence, in order of strength:

1. **Architectural: analog/hybrid beamforming at the module.** Qualcomm's own published mmWave placement study describes smartphone modules as "5×1 dual-polarized linear antenna array" combined via a "size-9 analog beamforming codebook" [QWP]. The Qualcomm QTM10028 FCC filing (small-cell but family-representative) documents an IF-interface coax link to baseband and independent H/V beamforming per layer — a single IF pair per module, not per element [FCC-QTM10028]. A small-footprint phone modem cannot afford per-element ADCs (16 × 2 GS/s complex ADCs per module would blow the power budget). So the baseband physically never sees per-element IQ; the combining is done by RFIC phase shifters before digitization.

2. **Standards: 3GPP TS 38.214 reporting is codebook-based, not per-element.** TS 38.214 §5.2 defines `reportQuantity` as either a CSI-related quantity (PMI/RI/CQI over Type I or Type II codebooks) or L1-RSRP per CSI-RS resource (beam index). Type II codebooks compress spatial signatures into DFT beam amplitudes + quantized phases, omitting the strongest beam's amplitude/phase. Nothing in 38.214 asks for per-element h-vector export [TS38214]. The FR2 UE is explicitly modelled as multi-panel with analog beamforming — Rel-17 added "UL beam selection for multi-panel devices" and Rel-18 is still working on "simultaneous multi-panel UL transmission (STxMP)" as a new work item, confirming that multi-panel coherent aggregation is not yet baseline even in 2026 [Qcom-R17, ATIS-R18].

3. **Software/diagnostics: no published exposure path.** Qualcomm's Android HAL / RIL / QMI / DIAG interfaces and community tools (QCSuper, qcrilhook, BaseMirror on Samsung Exynos) can dump baseband memory and issue vendor AT commands, but the academic and community corpus contains no documented example of per-element FR2 IQ being exfiltrated from a commercial phone [ARXIV-BB, P1SEC-QCSUPER]. BaseMirror (arXiv 2024) reverse-engineered Samsung Exynos RIL extensively and found diagnostic commands, but not per-element mmWave IQ [ARXIV-BB].

### What does this mean for Route B?

Route B as originally framed ("UE-side AoA estimation from a small phone array") **needs to be reformulated** to survive peer review. The hardware does not expose the mathematical object (per-element h) that classical AoA requires. The paper should instead frame the UE-side spatial estimation problem as:

**Beam-index RSRP sweep + codebook inversion.** What the UE actually has is a vector of L1-RSRP values, one per beam in the analog codebook (size ~9 per module per Qualcomm's reference [QWP]; plus per-SSB / per-CSI-RS resource reports on the gNB side via CRI). Given knowledge of the codebook beam shapes (which can be either standardized — DFT over az/el — or measured once per device model in an anechoic chamber), the AoA estimation problem becomes a **coarse deconvolution of the beam pattern ⊛ AoA distribution** at resolution set by the ~23°–29° per-module beamwidth. This is beam-level AoA, not element-level, and it is the most that a standards-compliant, commercially deployed UE can deliver in 2026.

**Three concrete path-forward options**, in order of PoC feasibility:

- **(A) Standards-compliant reformulation (recommended).** Replace "per-element h + MUSIC" with "L1-RSRP-per-beam + codebook-inversion AoA," report resolution honestly (≈ beamwidth ≈ 10° for a testbed / ≈ 25° for phone modules [Samsung-mmW, QWP]). This is what Samsung's own testbed paper does for mobile stations [Samsung-mmW].
- **(B) Operator-cooperative beam sweep, UE-side demodulation of per-beam measurements.** Use the P1/P2/P3 beam-management framework in TS 38.214: gNB sweeps CSI-RS; UE reports L1-RSRP per CRI; with known transmit-beam directions at the gNB (achievable in a controlled trial / lab setup), AoA is recoverable at beam resolution. No raw IQ needed.
- **(C) SDR replacement / rooted engineering firmware.** For ground-truth validation, pair a commercial phone's baseband with an SDR (USRP, NI PXI, or a dedicated channel sounder like NYU WIRELESS's FR2 rigs [NYU]) to capture per-element IQ on the same RF link. Cite this as method validation, not product proposal.

**Not recommended**: claiming per-element IQ access "via rooting" without evidence. The literature does not support that claim for FR2 on any commercial modem family.

---

## Recommended UE model — per-query detail

### Query 1 — module count and placement

- iPhone 12 / 12 Pro (US): **2 mmWave modules** — one embedded in the right side frame (USI-packaged, part `339M00104 S30U7FH`, labeled by iFixit), one on the back of the logic board [IF12, MWJ-iPhone12]. iPhone 12 Pro Max: also 2–3 depending on report; UnitedLex identified "the two 5G mmWave antenna modules ... at the back of the PCB stack and at the side" [UL-iPhone12].
- iPhone 15 Pro (US): modular 5G/mmWave antenna module persists; tekdep/iFixit teardowns describe removing it as a discrete step, suggesting unchanged 2-module architecture. TechInsights reports are paywalled; we could not confirm an exact count from free sources.
- Samsung Galaxy S20 Ultra (US): mmWave antennas "embedded into the frame" (iFixit X-ray) [IF-S20]; US variant uses Qualcomm QTM525 [UL-iPhone12 comparison].
- Galaxy S21 Ultra (US): teardowns and replacement parts ship in **2-module sets** [IF-S21, deviceparts]; Snapdragon 888 US variant typically uses QTM535 (3rd-gen) [wccftech-S21].
- Galaxy S23 / S23 Ultra (US): iFixit service manual explicitly documents "There are two (2) mmWave Antenna modules attached to the bracket" [IF23].

Qualcomm's X50 press release said modules are sized "suitable for integrating **up to four modules** in a smartphone" [Q1], but commercial phones have mostly settled on 2 modules (2021+) for thermal / board-area reasons.

Placement pattern per Qualcomm's own whitepaper: "one of the modules on the middle of the top edge ... and another module on the middle strip of the back face or in the middle portion of one of the long edges" [QWP].

### Query 2 — elements per module

- Qualcomm QTM052 / QTM525 public literature: dual-polarized phased array, "2×2 array" discussion in Microwave Journal [MWJ-QTM]. 5G Technology World: "X50 supports up to four of the modules — one for each side of the phone — but most device makers will opt for three" [5GTW].
- Qualcomm whitepaper on placement (the definitive free reference): **"each antenna module consists of a 5×1 dual-polarized linear antenna array"** with **λ/2 spacing** and a **size-9 analog beamforming codebook** [QWP]. Elements per module = 4 or 5; ports (= element × polarization) = 8 or 10.
- Academic Samsung mesh-grid prototype: "16-element mesh-grid patch antenna array ... gain = 11 dBi at boresight ... 12° 3-dB beamwidth" — Samsung's research prototype was 1×16 but not representative of shipping modules [MWJ-Smart].
- For FR2 the 1×4 dual-pol configuration (4 patches on λ/2 pitch + dual-pol feed = 8 ports) is the most cited practical shipping geometry; QTM525/535 uses essentially this geometry.

### Query 3 — active module selection vs simultaneous combining

- Commercial smartphones (X50/X55/X65/X70 modem families) perform **module selection, not coherent combining** across modules [5GTW, Q1]. The modem continuously monitors candidate modules and switches when a better beam is available on a different module.
- 3GPP: in Rel-15/16, "only one beam and panel are used for UL transmission at one timing" [EP4529299]. Multi-panel UL was introduced as an optional feature only in Rel-17 under the umbrella term STxMP (Simultaneous Transmission with Multi-Panel) [EP4529299, Qcom-R17], and Rel-18 is still working on it [ATIS-R18, Ericsson-R18].
- So for PoC purposes, assume **1 active module → 8 ports (1×4 dual-pol) or 10 ports (1×5 dual-pol)**. Do not claim simultaneous 16–24-port coherent UE. That's a future 3GPP feature.

### Query 4 — element spacing and aperture

- λ₂₈GHz = c / 28 GHz ≈ **10.71 mm**. λ/2 ≈ **5.36 mm** [QWP].
- For a 1×5 dual-pol array, aperture = 4 × 5.36 ≈ **21.4 mm ≈ 2λ**. For 1×4, aperture = 3 × 5.36 ≈ **16 mm ≈ 1.5λ**.
- Rayleigh angular resolution Δθ ≈ 2/N rad ≈ **28.6° for N=4, 22.9° for N=5** (in the plane containing the array). Per-pol, per-module. With 2 modules at orthogonal orientations, coverage improves spherically but each module is still beam-limited.
- Samsung testbed at 28 GHz reports: "4×1 Linear ... 20° (H), 60° (V)" half-power beamwidth for the mobile station [Samsung-mmW].

### Query 5 — analog vs digital beamforming architecture

See the main TL;DR and "Query 5 answer" block above. The evidence chain: Qualcomm's own product-brief language (modem-to-antenna, modules, beam steering [QX65, QX70, QX75]), the FCC QTM10028 spec confirming coax IF interface and independent H/V beamforming with "amplitude and phase control of each element" done in the module [FCC-QTM10028], and the absence of any published per-element IQ access path in the community reverse-engineering literature [ARXIV-BB, P1SEC-QCSUPER].

### Query 6 — typical deployed FR2 bandwidth

- 3GPP TS 38.101-2 Table 5.3.5-1 allows {50, 100, 200, 400} MHz per carrier for n257/n260/n261 at 60/120 kHz SCS [TS38101].
- 120 kHz SCS is the practical FR2 default (allows Doppler tracking at mmWave) [ShareTechnote-BW, TechPlayon-Numerology].
- Commercial US deployments (Verizon, AT&T on n260 / n261): **100-MHz blocks aggregated via carrier aggregation**, up to ~800 MHz effective [PhoneArena-5G-bands].
- Snapdragon X65 spec: "1000 MHz bandwidth (mmWave), 10 carriers, 2×2 MIMO" [QX65]. Realistic paper assumption: **one 100-MHz carrier, 120-kHz SCS, 2-layer MIMO**; CSI-RS/SRS typically allocated across full BW.

### Query 7 — teardowns and measurement papers (bibliography)

- **Apple iPhone 12 teardown** — iFixit Guide ID 137669 (Oct 2020). Documents USI-packaged mmWave module, part `339M00104 S30U7FH` [IF12].
- **Galaxy S20 Ultra teardown** — iFixit Feb 2020, "mmwave antennas embedded into the frame" [IF-S20].
- **Galaxy S21 Ultra teardown** — iFixit 2021 [IF-S21].
- **Galaxy S23 Series service manual** — iFixit / Samsung, 2023. Documents "two (2) mmWave Antenna modules attached to the bracket" [IF23].
- **Qualcomm mmWave antenna module placement whitepaper** — definitive free reference on geometry, codebook, placement strategy [QWP].
- **Mo, Ng et al. "Beam Codebook Design for 5G mmWave Terminals"** — Samsung Research, IEEE Access 2019, arXiv:1908.01004. Defines data-driven beam codebooks for mmWave phones, explicitly addresses hand-grip effects [arXiv-1908].
- **Samsung Research "Analysis of mmWave Performance"** white paper — 28 GHz / 800 MHz TDD testbed, BS 8×6 planar / 21 dBi, MS 4×1 linear / 7 dBi [Samsung-mmW].
- **NYU WIRELESS Rappaport group publications** — 28 GHz channel sounding, statistical models [NYU]. Their rigs use horn antennas on mechanical rotators, not smartphone hardware; they characterize the CHANNEL not the UE.
- **Yole Group "Qualcomm's First 5G mmWave Chipset: SDX50M and QTM052"** — paid teardown report with dual-polarized aperture-coupled patch analysis [Yole-QTM].

### Query 8 — 3GPP reference UE model

- **3GPP TR 38.828 Table 5.2.2.5.4-1**: GE,max = 3 dBi for UE element (5 dBi directivity − 2 dB loss). Simulation variant: "two UE panels with 180° horizontal shift, UE azimuth uniformly distributed in [-180°, +180°]"; 90° element beamwidth assumed; indoor case modelled as omni 0 dBi [TR38828].
- **3GPP TR 38.901**: defines element pattern (Table 7.3-1: 0 dB boresight to -30 dB at 90° elevation), supports P=1 or P=2 polarization, defines dH / dV as free parameters — no mandated UE array geometry [TR38901].
- **3GPP does NOT mandate "3 panels at 120°" for UE.** That is a frequent folk claim but not in any of the referenced TRs. The only explicit simulation variant in TR 38.828 is **two panels at 180°** spacing (front/back of phone).
- **ITU-R M.2412 Table 11**: UE element GE,max = 5 dBi at 30 GHz; up to 32 Tx/Rx elements evaluation upper bound [M2412]. Note the 2 dB disagreement with TR 38.828's 3 dBi.
- Literature practice (IEEE TWC / JSAC / T-AP 2024–2026): we could not extract a definitive summary from free sources in the time budget. Anecdotally, the TR 38.901 element pattern + a 2-panel 180° UE with 1×4 dual-pol per panel is the most commonly cited configuration; but papers vary widely.

---

## Caveats and counter-evidence

1. **"3 panels at 120°" is folklore, not a 3GPP spec.** Route B papers that claim this as the "3GPP reference" UE will not stand up to reviewer scrutiny. Use "2 panels at ~180° per TR 38.828 simulation variant" or justify a custom geometry explicitly.
2. **Apple does not use Qualcomm QTM modules.** iPhone 12 teardown revealed USI-packaged mmWave antennas; Apple explicitly rejected QTM525 due to z-height [9to5Mac-custom-antenna, Semianalysis-Qcom-lost]. Papers referring to "Qualcomm QTM525 inside iPhone" are incorrect; iPhones use Apple/USI custom designs with the Qualcomm SMR526 IF IC on the main PCB.
3. **Galaxy S21 Ultra Exynos international variant had no mmWave** [wccftech-S21]. The US Snapdragon variant does. Always specify the regional variant.
4. **Counter-possibility: STxMP (Rel-17/18) simultaneous multi-panel.** This is the only 3GPP mechanism that could deliver coherent multi-module aggregation. As of early 2026 it is still "under study" in RAN1 [ATIS-R18] and not deployed. A JSAC paper could reasonably project it as "near-future" but not "current commercial."
5. **Qualcomm X75 adds "sensor-modem-RF solution for mmWave beam management"** [QX75]. This uses gyroscope + accelerometer + AI to predict beam switching; it doesn't change the fundamental analog-beamforming architecture but does add a new data stream the UE uses for beam decisions. Worth acknowledging as 2023+ state-of-the-art.
6. **QTM10028 is a small-cell, not a handset module.** Its 8×8 dual-pol array [FCC-QTM10028] is NOT what's inside a phone; that spec is often confused in online writeups.
7. **Literature on per-element IQ access is genuinely thin.** Absence of evidence is not proof of absence; a rooted phone with engineering firmware from a vendor MAY have access to something equivalent. The summary above reflects the *published and peer-reviewable* state of knowledge as of April 2026. If Robin has a vendor NDA contact at Qualcomm, the answer could change.

---

## References (URLs + year)

- [Q1] Qualcomm press, "Qualcomm Announces the Latest and Smallest Additions in its Family of 5G NR mmWave Modules," Oct 2018. https://www.qualcomm.com/news/releases/2018/10/qualcomm-announces-latest-and-smallest-additions-its-family-5g-nr-mmwave
- [QWP] Qualcomm, "Millimeter wave antenna module placement" whitepaper (n.d., ~2020). https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/5G-Whitepaper-mmWave_Antenna_Module_Placement-Qualcomm.pdf
- [QEverythingRF] EverythingRF product page, QTM545, 2021. https://www.everythingrf.com/products/front-end-modules/qualcomm/529-914-qtm545
- [QX65] Qualcomm Snapdragon X65 Product Brief, 2021. https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/prod_brief_qcom_x65.pdf
- [QX70] Qualcomm Snapdragon X70 Product Brief, 2022. https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/snapdragon-x70-modem-rf-system-product-brief.pdf
- [QX75] Qualcomm Snapdragon X75 Product Brief, 2023. https://docs.qualcomm.com/doc/87-27161-1/87-27161-1_REV_C_Snapdragon_X75_5G_Modem-RF_System_Product_Brief.pdf
- [Qcom-R17] Qualcomm, "3GPP Release 17: Completing the first phase of the 5G evolution," 2022. https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/powerpoint_messaging_-_3gpp_release_17_completing_the_first_phase_of_5g_evolution.pdf
- [ATIS-R18] ATIS, "3GPP Release 18 Overview," Feb 2023. https://atis.org/wp-content/uploads/2023/02/Feb-23-Webinar-PPT-slides-collated-1.pdf
- [Ericsson-R18] Ericsson Technology Review, "Toward 5G Advanced: overview of 3GPP releases 17 & 18," 2022. https://www.ericsson.com/en/reports-and-papers/ericsson-technology-review/articles/5g-evolution-toward-5g-advanced
- [IF12] iFixit, "iPhone 12 and 12 Pro Teardown" Guide 137669, Oct 2020. https://documents.cdn.ifixit.com/pdf/ifixit/guide_137669_en.pdf
- [IF-S20] iFixit, "Samsung Galaxy S20 Ultra Teardown," 2020. https://www.ifixit.com/Teardown/Samsung+Galaxy+S20+Ultra+Teardown/131607
- [IF-S21] iFixit, "Samsung Galaxy S21 Ultra Teardown," 2021. https://www.ifixit.com/Teardown/Samsung+Galaxy+S21+Ultra+Teardown/141188
- [IF23] iFixit / Samsung, "Galaxy S23 Series service manual," 2023. https://documents.cdn.ifixit.com/6mWOqWwWPVj1OUHN.pdf
- [MWJ-iPhone12] Microwave Journal, "iPhone 12/12 Pro Teardown for RF," Nov 2020. https://www.microwavejournal.com/blogs/9-pat-hindle-mwj-editor/post/34907-iphone-1212-pro-teardown-for-rf
- [UL-iPhone12] UnitedLex, "Apple iPhone 12 Pro Max Teardown Report," 2020. https://unitedlex.com/insights/apple-iphone-12-pro-max-teardown-report/
- [MWJ-QTM] Microwave Journal, "First 5G mmWave Antenna Module for Smartphones," Dec 2018. https://www.microwavejournal.com/articles/31448-first-5g-mmwave-antenna-module-for-smartphones
- [5GTW] 5G Technology World, "Qualcomm Introduces Miniaturized mmWave Antenna Modules for 5G Smartphones," Jul 2018. https://www.5gtechnologyworld.com/qualcomm-introduces-miniaturized-mmwave-antenna-modules-for-5g-smartphones/
- [MWJ-Smart] Microwave Journal, "Compact Antenna Designs for Future mmWave 5G Smart Phones," Nov 2020. https://www.microwavejournal.com/articles/34931-compact-antenna-designs-for-future-mmwave-5g-smart-phones
- [FCC-QTM10028] Qualcomm QTM10028 5G-NR Millimeter-Wave Antenna Module Device Specification, FCC filing (small-cell, not handset — reference only), 2020. https://fcc.report/FCC-ID/2AG32BSC7261A249D/7197700.pdf
- [Yole-QTM] Yole Group, "Qualcomm's First 5G mmWave Chipset: SDX50M and QTM052," 2019 (sample). https://medias.yolegroup.com/uploads/2019/09/SP19482-YOLE-Qualcomm-5G-mmWave-Chipset-SDX50M-and-QTM052_Sample.pdf
- [arXiv-1908] Mo, Ng et al. "Beam Codebook Design for 5G mmWave Terminals," IEEE Access 2019, arXiv:1908.01004. https://arxiv.org/abs/1908.01004
- [Samsung-mmW] Samsung, "Analysis of mmWave Performance," 2017 white paper. https://images.samsung.com/is/content/samsung/p5/global/business/networks/home/global-networks-insight-analysis-of-mmwave-performance-0.pdf
- [NYU] Theodore Rappaport publications, NYU WIRELESS. https://wireless.engineering.nyu.edu/tedrappaport-publications/
- [TS38214] 3GPP / ETSI TS 38.214 v15.04.00 / v17.01.00. https://www.etsi.org/deliver/etsi_ts/138200_138299/138214/15.04.00_60/ts_138214v150400p.pdf
- [TS38101] 3GPP / ETSI TS 38.101-2 v16.04.00. https://www.etsi.org/deliver/etsi_ts/138100_138199/13810102/16.04.00_60/ts_13810102v160400p.pdf
- [TR38828] 3GPP TR 38.828 (ATIS mirror), Release 16. https://atisorg.s3.amazonaws.com/archive/3gpp-documents/Rel16/ATIS.3GPP.38.828.V1610.pdf
- [TR38901] 3GPP / ETSI TR 38.901 v15.00.00. https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/15.00.00_60/tr_138901v150000p.pdf
- [M2412] ITU-R Report M.2412, "Guidelines for evaluation of radio interface technologies for IMT-2020," 2017. https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-M.2412-2017-PDF-E.pdf
- [EP4529299] European Patent EP4529299A1 (background discussion of Rel-17 STxMP and Rel-15/16 single-panel baseline), 2025. https://data.epo.org/publication-server/rest/v1.2/publication-dates/2025-03-26/patents/EP4529299NWA1/document.pdf
- [ARXIV-BB] Wen et al. "BaseMirror: Automatic Reverse Engineering of Baseband Commands from Android's Radio Interface Layer," arXiv:2409.00475, 2024. https://arxiv.org/html/2409.00475v1
- [P1SEC-QCSUPER] P1 Security, "Presenting QCSuper: A tool for capturing your 2G/3G/4G air traffic on Qualcomm-based phones," 2019. https://p1sec.com/blog/presenting-qcsuper-a-tool-for-capturing-your-2g-3g-4g-air-traffic-on-qualcomm-based-phones
- [ShareTechnote-BW] ShareTechNote, "5G FR Bandwidth." https://www.sharetechnote.com/html/5G/5G_FR_Bandwidth.html
- [TechPlayon-Numerology] TechPlayon, "5G NR Numerology / Subcarrier Spacing." https://www.techplayon.com/5g-nr-numerology-subcarrier-spcaing-scs/
- [PhoneArena-5G-bands] PhoneArena, "5G bands cheat sheet: Verizon vs AT&T vs T-Mobile vs World." https://www.phonearena.com/news/5G-bands-explained-Verizon-vs-AT-T-vs-Sprint-vs-T-Mobile-vs-World_id116781
- [wccftech-S21] wccftech, "Galaxy S21 Ultra With Exynos 2100 Gets Disassembled," 2021. https://wccftech.com/samsung-galaxy-s21-ultra-teardown/
- [9to5Mac-custom-antenna] 9to5Mac, "iPhone 12 may use custom 5G antenna with Qualcomm modems," Feb 2020. https://9to5mac.com/2020/02/14/iphone-12-custom-5g-antenna/
- [Semianalysis-Qcom-lost] SemiAnalysis, "Qualcomm Lost the iPhone 12 mmWave Antenna Module Contract to a Chinese Company," 2020. https://newsletter.semianalysis.com/p/qualcomm-lost-the-iphone-12-mmwave

---

*Document assembled 2026-04-23. Tavily budget used: ~14 calls (4 pro research, 7 advanced search, 2 extract). Where the literature was thin (NYU/Nokia/Bell-Labs specific FR2 smartphone radiation-pattern measurements; literature practice in 2024–2026 papers), the summary honestly states so rather than fabricating citations.*
