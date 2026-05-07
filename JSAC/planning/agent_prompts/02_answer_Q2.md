# Q2 — BR-based audit in regulatory practice

## 1. IEC/IEEE 62232:2022 — body-centric BR assessment

The full standard is paywalled, but a substantive 40-page CENELEC preview (covering Foreword, Introduction, Scope, Normative references, and full table of contents) is publicly accessible via VDE-Verlag and iTeh Standards. From these, the following is verified primary-source language.

**Scope (Clause 1):** "This document provides methods for the determination of RF field strength, power density and specific absorption rate (SAR) in the vicinity of base stations (BS) for the purpose of evaluating human exposure." Sub-clause 1(e) further states the document "describes several RF field strength, power density, and SAR measurement and computation methodologies with guidance on their applicability to address both the in-situ evaluation of installed BS and laboratory-based evaluations." (IEC 62232:2022 ED3, p. 19, Clause 1).

**Foreword:** This third edition introduces "h) compatibility with ICNIRP-2020 exposure limits." (IEC 62232:2022 ED3, p. 17).

**Annex B (normative) — Evaluation methods.** The TOC enumerates body-centric numerical methods explicitly:
- B.5 SAR measurements (B.5.1 Overview, B.5.2 Requirements, B.5.3 Description, B.5.4 Uncertainty)
- B.6.3 "Basic whole-body SAR and peak spatial-average SAR evaluation"
- B.7.3 "Full wave RF exposure computation" (p. 171)
- B.7.4 "Full wave SAR computation" (p. 180)
- Table B.29 "Validation reference SAR results for computation method" (p. 185)

**Normative references include the IEC/IEEE 62704 family** (Parts 1–4), each titled "Determining the peak spatial-average specific absorption rate (SAR) in the human body … using the finite difference time-domain (FDTD) method" or FEM. These are the body-centric numerical-dosimetry standards — pulled in normatively, not informatively.

**Annex E.9** (TOC): "Establishing compliance boundaries using numerical simulations of MIMO" with sub-clauses on densely packed MIMO and large MIMO arrays (pp. 270+).

Verdict for sub-question 1: IEC/IEEE 62232:2022 explicitly permits "RF exposure assessment" via SAR computation, and normatively imports FDTD/FEM-based SAR-in-body computation standards. Whether full clauses (B.7.4, E.9) say "digital twin" verbatim cannot be confirmed from the preview — the specific clause text beyond the TOC is paywalled.

## 2. ITU-T K.122 — body-centric BR assessment

ITU-T K.122 (12/2016), full PDF retrieved from itu.int.

**Scope (Clause 1):** "In this Recommendation the level of electric field strength is simulated in the vicinity of transmitting antennas of the: FM high-power antenna … UHF TV … mobile communication dual-band 900/1 800 MHz antenna panel … micro-cell ceiling-mounted antenna … fixed point-to-point 22.4 GHz antenna … fixed point-to-point 75 GHz antenna." (Rec. ITU-T K.122, p. 1).

**Methods (Introduction):** "The results presented in this Recommendation have been obtained using the following calculation methods: method of moments (MoM) or hybrid methods multilevel fast multipole method (MLFMM) and physical optics with MoM (PO/MoM). All these methods are full-wave methods so they allow for calculations even in the reactive part of the near-field region." (Rec. ITU-T K.122, p. iv).

**Body assessment:** K.122 references "basic restrictions" only via the standard ITU-T K.70 definition (Clause 3.1.4: "specific absorption rate (SAR) and power density (S)") and consistently outputs E-field in V/m versus distance. It does not specify a body-centric SAR computation procedure. For SAR/numerical dosimetry, K.122 defers: "It is also recommended, if the exposure level is close to the limit, to confirm results by measurements using the procedures defined in [ITU-T K.61] and [IEC 62232]" (Clause 1, NOTE, p. 1).

Verdict for sub-question 2: K.122 is an antenna-near-field reference-level catalogue. It does not authorise or describe body-centric BR assessment. The BR-language pathway sits in IEC 62232 and the IEC/IEEE 62704 family, which K.122 cross-references.

## 3. Jurisdictions where RL and BR are legally alternative

**United States — 47 CFR §1.1310 (current eCFR text):**
Paragraph (a): "Specific absorption rate (SAR) shall be used to evaluate the environmental impact of human exposure to RF radiation as specified in §1.1307(b) … with the limits …"
Paragraph (d)(2): "For operations within the frequency range of 300 kHz and 6 GHz (inclusive), the limits for maximum permissible exposure (MPE), derived from whole-body SAR limits and listed in Table 1 in paragraph (e)(1) of this section, may be used instead of whole-body SAR limits as set forth in paragraphs (a) through (c) of this section to evaluate the environmental impact of human exposure to RF radiation as specified in §1.1307(b) of this part, except for portable devices as defined in §2.1093 of this chapter as these evaluations shall be performed according to the SAR provisions in §2.1093." (47 CFR 1.1310, Cornell LII / eCFR).

So for fixed/base stations 300 kHz–6 GHz, MPE (RL) is the *option*; SAR (BR) is the default and remains legal. FCC 19-126 (Dec. 2019) further "allow[s] the use of any valid computational method to determine potential RF exposure levels." No FCC base-station permit known to have used SAR in lieu of MPE in practice — base stations universally use MPE.

## 4. BR audit accepted for a mmWave deployment

Not found. ITU-T K Suppl. 16 (10/2022) and IEC TR 62669 case studies for 5G base stations all use the actual-maximum-power approach combined with field-level (V/m, W/m²) compliance boundaries, not in-body SAR. Several academic dosimetry papers (Thors et al., MDPI 2020; Frontiers in Comm 2022) compute body absorption for mmWave panels but as research, not regulator-accepted compliance dossiers.

## 5. Regulator-facing mmWave exposure tools

**Ericsson EMF Estimator** (the most widely cited operator tool, used at ITU compliance workshops): per the ITU document "Use of EMF estimator for Base Station authorization in a multi-operator environment" (ITU-T workshop, Botswana 2011), it computes electric field strength E [V/m] vs. distance, plotted against measurement traces — i.e. RL-based, not body-SAR. Confirmed by Ericsson's own white paper "Accurately assessing exposure … from 5G networks": "The RF EMF limits applicable for base stations are typically expressed in terms of power density (unit W/m²) or electric field strength (unit V/m) levels," and the methodology referenced is IEC 62232 with PD/E-field outputs.

Other tools (Wavecontrol EME-SPY, Narda SRM-3006) are measurement instruments and report E/H/S; none compute body SAR. No regulator-facing production tool that computes body SAR for compliance was located.

## 6. Belgium — BR-based assessment for Brussels

Not found. Brussels Environment ("environnement.brussels") describes its limit exclusively in V/m at publicly accessible points (e.g., 14.57 V/m exterior, 9.19 V/m indoor), with per-operator quotas (Proximus 29.5 %, Orange 26.5 %, …) on the *field* contribution; the page references Recommandation 1999/519/CE, not ICNIRP 2020 BR pathway. No BIPT/IBPT decision, environnement.brussels permit, or Belgian Federal Public Service Economy filing was located in which a body-centric SAR assessment was substituted for the V/m measurement to demonstrate compliance.

## Bottom-line assessment

IEC/IEEE 62232:2022 does explicitly accommodate body-centric numerical SAR assessment as one of several valid evaluation methods (Clause 1(e); Annex B.5, B.6.3, B.7.4, E.9; normative references to IEC/IEEE 62704 FDTD/FEM SAR standards). The paper can therefore claim that "numerical SAR computation in human body models for compliance assessment of base-station installations is an evaluation pathway specified by IEC/IEEE 62232:2022." The paper should *not* claim that any regulator (FCC, BIPT, Brussels Environment, Ofcom, Japan MIC) has accepted a body-centric digital-twin BR audit in practice for a deployed base station — all known regulator-facing tools and accepted dossiers compute E/PD against RL. The honest framing is therefore: the BR pathway is permitted by the standards (62232, 62704, ICNIRP 2020), used in academic dosimetry, but operationalised in regulator workflows essentially nowhere; the digital twin would be a *proposed* audit protocol that fits inside an existing standards-permitted slot rather than a *proven* regulatory practice.

## Sources consulted

- IEC/IEEE 62232:2022, ED3 preview: https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec62232%7Bed3.0%7Db.pdf and https://cdn.standards.iteh.ai/samples/103182/820f0ec8e2134e06b0e7463afc08fd72/IEC-62232-2022.pdf (40-page and 15-page TOC + scope previews, used for verbatim quotes and clause/annex names)
- IEC webstore page: https://webstore.iec.ch/en/publication/64934
- ITU-T K.122 (12/2016) full PDF: https://www.itu.int/rec/T-REC-K.122-201612-I (downloaded and parsed)
- ITU-T K Suppl. 16 (10/2022): https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-K.Sup16-202210-I!!PDF-E&type=items
- ITU-T K Suppl. 32 (06/2024) abstract: https://www.itu.int/epublications/publication/itu-t-k-suppl-32-2024-06-case-studies-of-radio-frequency-electromagnetic-field-rf-emf-assessment
- 47 CFR §1.1310 (Cornell LII): https://www.law.cornell.edu/cfr/text/47/1.1310
- FCC 19-126 Report and Order: https://docs.fcc.gov/public/attachments/fcc-19-126a1.pdf
- Nokia C2M webinar on IEC 62232 ED3 (April 2022): https://chairec2m.wp.imt.fr/files/2022/04/C2M_Webinar-26042022_Nokia-Introduction-IEC62232ED3.pdf
- Ericsson white paper on 5G EMF: https://www.ericsson.com/en/reports-and-papers/white-papers/accurately-assessing-exposure-to-radio-frequency-electromagnetic-fields-from-5g-networks
- ITU EMF Estimator workshop paper (2011): https://www.itu.int/dms_pub/itu-t/oth/06/4f/t064f0000030051pdfe.pdf
- Brussels Environment legal-norms page: https://environnement.brussels/citoyen/reglementation-et-inspection/textes-de-loi/quelles-sont-les-normes-legales-dexposition-aux-ondes-electromagnetiques
- ICNIRP base-station page: https://www.icnirp.org/en/applications/base-stations/index.html

## Not verified from primary source / paywalled gaps

- Verbatim text of IEC/IEEE 62232:2022 Clauses 6.2.8, 7, 8.3, 8.4, B.7.4 and Annex E.9 (paywalled; clause titles confirmed from preview, but the language inside those clauses cannot be quoted from public material here).
- Whether IEC/IEEE 62232:2022 uses the phrase "digital twin" anywhere (preview does not).

> NEEDS_CONTEXT: To strengthen the §VII claim with verbatim text from Annex B.7.4 ("Full wave SAR computation") or Annex E.9 ("Establishing compliance boundaries using numerical simulations of MIMO"), Robin may need to provide the IEC PDF or point to a specific quoted excerpt in a 62232 co-author's slide deck/paper.
