# Patent landscape search: geometric dosimetry / AEGIS

*Search run 2026-05-23. Method: structured Google Patents / Espacenet / freepatentsonline search across five independent clusters, reading abstracts and independent claims of the closest hits. This is a self-run landscape scan, NOT a professional freedom-to-operate (FTO) opinion. WebSearch is US-biased, legal statuses and dates are approximate, and a real FTO needs a paid database (Derwent / PatSnap / Questel) plus UGent-appointed counsel. Treat everything below as leads to verify, not conclusions to rely on.*

This document exists to fill the hole the IDF review flagged: the IDF section "Patents or patent applications of others most closely related to the invention" currently says "No closely related patents were identified," which is thin and, as written, wrong. The honest reading is more nuanced, and it matters for both the patent claims and the USP.

---

## TL;DR verdict

The IDF claim "no other people have done it" is **true for the specific computational method, false for the broad concepts**. Split it:

| Cluster | Is "no one did it" defensible? | Dominant risk |
|---|---|---|
| 1. Device-side SAR/APD control (sense body, back off power, pick safer beam) | **No. Crowded since 2001.** | FTO + novelty |
| 2. Exposure-aware MIMO precoder (the exposure operator Q, QCQP) | **Partly. The object is published/patented, the closed-form-from-Fresnel angle is open.** | Novelty (academic prior art) |
| 3. Fast closed-form surface dosimetry (the core S_ab law, view-factor, Gamma_lm) | **Yes at the patent level. No, against academic publications.** | Novelty (non-patent prior art) |
| 4. Base-station / network EMF compliance + exposure mapping | **The combination survives, the pieces do not.** | Novelty + competitive |
| 5. RF digital-twin ray tracing + differentiable antenna optimisation | **Pieces (A) are prior-arted, the differentiable-dosimetry loop (B) is genuine white space.** | Novelty (pieces), competitive |

Bottom line: the moat is **not the physics insight**. It is the differentiable, calibration-free design loop and the integrated system, exactly as the honest-analysis doc already argued. The patent should be drafted around that, not around "we discovered a constant transmission coefficient."

---

## The patents that actually matter

Twelve references carry almost all the weight. Verify each with counsel.

### Highest priority

1. **US11940477B2 - University of Notre Dame (Hochwald, Ebadi Shahrivar).** Granted 2024, priority 2018, NSF-funded (CCF-1403458, so US government has Bayh-Dole march-in rights). **Full-text read confirms:** the spec defines the local SAR matrix `R_d = (sigma/2rho) E^H(d) E(d)`, a Hermitian PSD matrix of rank <= 3, and local SAR as `tr{R_d R_x}`, which for a rank-one beamformer `R_x = x x^H` is exactly `x^H R_d x`. That is AEGIS's exposure operator `Q`, fully disclosed (and published since Hochwald 2014 / Ying 2015). **So you cannot claim the quadratic-form exposure operator itself as novel.** BUT all three independent claims (1, 13, 18) require physically **transmitting and measuring** exposure with a probe, and there is **no claim to using the matrix to design or optimise a precoder.** Net: **FTO is low** (AEGIS computes `Q` with zero measurement and AEGIS's ECBF precoder is not claimed here), **novelty pressure on Claim 2 is high** (the matrix object is prior art). Your `Q` novelty must rest entirely on: closed-form from Fresnel + surface geometry (no measured E-field, no FDTD), near-field point-source uplink, and differentiability. Bonus: the examiner's reference list is a ready-made bibliography of the exact prior art to distinguish (Hochwald 2013/2014, Ying 2015, Castellanos 2016, Perotos 2012, Li 2014, Colombi 2015, Ebadi-Shahrivar 2017). https://patents.google.com/patent/US11940477B2/en

2. **US8929828B2 - Bertrand Hochwald (individual).** Granted Jan 2015, priority Apr 2012, **active until 2032.** A multi-transmit-chain device that adjusts the phase/amplitude of each chain from a **codebook of code words generated using a parameter that characterizes near-field EM radiation intensity / MPE**, where the codebook satisfies a reception-quality criterion. This is the exposure-aware transmit-weight design (the "SAR codes" idea) as a **granted, active patent**, and it is explicitly near-field and device-side, so it is the closest FTO hit to AEGIS Claim 2a (near-field uplink ECBF). It models exposure as a generic constraint S(v) <= tau, not as an explicit quadratic form/matrix, and it is a runtime-codebook method rather than a closed-form continuous-`x` QCQP. Those are AEGIS's distinctions, but they are narrow and need counsel. NOTE: my cluster-2 agent initially concluded "the SAR-codes precoder was never patented." That was wrong, this patent is it. https://patents.google.com/patent/US8929828B2/en

2b. **Hochwald / Love / Ying "SAR codes" (CISS 2013, IEEE Comms Mag 2014), academic.** Maximises rate subject to a SAR constraint modelled as a quadratic form in the transmit vector, solved by SDP + bisection. Essentially AEGIS's ECBF QCQP minus the closed-form-Fresnel-`Q`, near-field, and differentiable angles. As printed-publication prior art it would **anticipate a broad Claim 2**, and it is the published basis of US8929828B2 above.

3. **US9622187B2 - Qualcomm.** Granted, priority 2015. "Real-time SAR" via 6-minute time-averaging over pre-stored FCC-certification SAR tables, then power back-off. This is **the incumbent meaning of "real-time SAR"** (lookup + time-average), and it is the foil AEGIS must distinguish from. Do not market AEGIS as "real-time SAR estimation" without qualification, that phrase is owned in its common reading. https://patents.google.com/patent/US9622187B2/en

4. **US11729728B2 (with US11184863B2) - Qualcomm.** Granted, priority 2019 / 2018. UE selects an uplink beam by converting EIRP history to power-density/SAR, scaling by per-module proximity, and picking the beam with the most remaining exposure headroom over a time-averaging window. **Biggest FTO risk to AEGIS Claim 3a** (on-device beam selection under a live exposure constraint). A shipped handset beam-picker that uses a running exposure budget reads onto this. https://patents.google.com/patent/US11729728B2/en

5. **US9961647B2 - ETRI (Korea).** Granted 2018, priority 2015. **Full-text read confirms:** terminals in a controlled area measure received power + position, the system bins them onto a 20m grid, sums per frequency band, converts to power density, then **computes body SAR per subarea by scaling a PRE-STORED 3D FDTD SAR distribution** (per band, per age: infants/children/adults), with a 12-plane-wave incident-direction-and-polarisation decomposition (Fig 4/5), and visualises it on a GIS (Claim 6). Closest hit to AEGIS Claim 4. **FTO is low:** Claim 1 requires "collecting a power value received... using terminals" and "mapping the received power value collected from the terminals," which is crowd-sourced measurement. AEGIS forward-simulates from an antenna-installation database, so it does not practise the claimed collection step. **Novelty pressure on Claim 4 is moderate-to-high:** this is the prior "base-station data to body-SAR-over-a-map to compliance to visualise" system. AEGIS's defensible distinctions: forward simulation from antenna databases (not terminal measurement), 3D environment reconstruction + ray tracing / coherent MIMO field synthesis, and the closed-form generative surface law on a body mesh (not a scaled pre-stored FDTD LUT). https://patents.google.com/patent/US9961647B2/en

6. **WO2024197059A1 - DeepSig.** PCT 2023 (national status unclear). A differentiable, learned "RF radiance field" that traces rays and outputs per-position reflectance, **absorption**, and transmittance from learned functions, gradient-trained on RF measurements. Closest single document to AEGIS's differentiable ray-tracing pipeline. "Absorption" here is scene-surface absorption for channel prediction, not human-tissue dosimetry, and there is no compliance objective. Field is being actively staked out. https://patents.google.com/patent/WO2024197059A1/en

### Important context / second tier

7. **US12369129B2 - Samsung.** Granted 2025, priority 2022. Estimates past RF exposure from radar-detected distance + transmit history, predicts future exposure, sets max power. Reinforces that "estimate exposure from proximity, then cap power" is fenced. (Novelty pressure on Claim 4b, FTO-adjacent to 3a.)

8. **Ericsson average-EIRP family: US11956727B2, US12342294B2, US12108347B2, US12003294B2, EP3427337B1.** Granted, priority 2016-2019. Coordinated time-averaged EIRP / beam-width / multi-transmitter control to **shrink the exclusion zone and recover transmit power**. This is competitive (it targets one of AEGIS's stated value props) but via live power-control loops, not body-mesh dosimetry. US12003294 weights a precoder via a control parameter for compliance, the nearest neighbour to AEGIS's precoder optimisation, but as a runtime feedback loop, not a design-time gradient solve.

9. **US10652833B2 / US9237531B2 - Qualcomm.** Granted. Store lab-measured SAR / power-density **maps** for a body model and scale them by transmit power for real-time compliance. Terminology ("surface scans," "PD maps") overlaps AEGIS, but these are stored measured device-emission maps, not a generative surface law from body geometry. Distinguishable, cite to differentiate.

10. **US6317599B1 - Wireless Valley / Extreme Networks (expired).** 1999. Automated antenna-placement optimisation in a 3D environment database with per-surface EM material properties (attenuation, reflectivity) and ray tracing. Foundational prior art that "material-tagged 3D scene + ray trace + optimise placement" is old. Expired (FTO-clear) but bad for the novelty of that generic combination (AEGIS Claims 4b / 15).

11. **US20190102493A1 - Ordnance Survey (granted) and the Cisco family US11785477B2 / US11742965B2.** RF simulation over 3D models reconstructed from survey / LIDAR / building data, with per-material signal degradation. Anticipate the "reconstruct scene from geodata, ray trace through materials" pieces of Claims 4b / 15. None tie to human-body absorption.

12. **NVIDIA Sionna RT (arXiv 2303.11103, Apache-2.0).** Differentiable ray tracing for radio, **published and open-sourced, no located patent**. This is FTO-positive twice over: it likely bars others from patenting generic differentiable-RT-for-radio, and it means AEGIS using DiffeRT / Sionna as a component is probably safe. Confirm no later NVIDIA filing via an Espacenet assignee sweep before relying on it.

---

## Two distinct risk buckets

These get conflated and should not be. FTO (will AEGIS infringe a live patent?) and novelty (can AEGIS get a patent, or does prior art block it?) are different questions with different evidence.

### FTO risks (AEGIS as a product might infringe)

- **Claim 2a near-field uplink ECBF** is pressured by **Hochwald US8929828B2** (active until 2032), which patents device-side near-field exposure-aware transmit-weight codebook design. AEGIS's closed-form continuous-`x` QCQP with an explicit `Q` matrix is distinguishable from a runtime codebook keyed to "a parameter characterizing near-field intensity," but the gap is narrow. This is the most important single FTO/novelty item for the precoder claims and must go to counsel.
- **Claim 3a device beam-picker** reads onto **Qualcomm US11729728 / US11184863** (exposure-budgeted uplink beam selection). Highest collision risk. Either license, carve the claim to the closed-form/gradient computation only, or do not ship a runtime exposure-budget beam-picker.
- **"Real-time SAR" framing** collides conceptually with **Qualcomm US9622187**. This is a marketing/claim-language risk more than a mechanism risk. Reframe as "closed-form computed APD field," never "real-time SAR estimate."
- **Device SAR-budget allocation** (Apple US11689234, Broadcom US8825102) and **proximity-triggered backoff** (the whole Apple/Qualcomm/Huawei/Siemens line back to US7146139, 2001, now expired). AEGIS does not currently do live device power control, so collision is low **unless** the product grows a device-side control feature. Keep AEGIS on the computation/design side and FTO stays clean here.
- Base-station live power control (Ericsson EIRP family): low collision, AEGIS does not run transmitter control loops.

### Novelty risks (prior art that could block or narrow AEGIS claims)

The dangerous prior art is mostly **non-patent**:

- **Kodera 2024, Li 2019, Bamba 2012/2015** remain the real threat to core Claim 1 / Claims 6-9 (empirical near-constant transmission coefficient).
- **THE CASTELLANOS CITATION IN THE IDF IS WRONG (likely fabricated).** The IDF cites "M. R. Castellanos et al., 'Closed-form Fresnel-based approach for 5G mmWave human body exposure assessment,' IEEE Access vol. 8, 2020." That paper could not be located by multiple searches. The US11940477 examiner cites the **real** Castellanos paper: "M. R. Castellanos et al., 'Hybrid precoding for millimeter wave systems with a constraint on user electromagnetic radiation exposure,' 2016 50th Asilomar Conference on Signals, Systems and Computers, pp. 296-300." This is a **precoder-design-under-exposure-constraint** paper (with Love), so it is prior art for **Claim 2**, not the dosimetry. Fix the citation before any UGent TTO reviewer or examiner checks it. A fabricated reference in an IDF is a credibility landmine, and the real paper is actually more relevant (to the precoder claim) than the fake one would have been. Closed-form Fresnel + incidence-angle absorption above 6 GHz is published. AEGIS's distinguishers (arbitrary-mesh per-point map at scale, the pseudo-Brewster-compensation justification of near-constant `T0`, the ReLU-projected-area whole-body form, the view-factor and `Gamma_lm` results) are what carry novelty. The IDF already cites most of these, good, but it must frame them as the closest prior art and articulate the specific delta.
- **Hochwald "SAR codes"** (above) for Claim 2.
- **Projected-area / view-factor for the human body** exists, but in **thermal radiative heat transfer**, not RF. The RF transposition (Claim 1b, `P_abs = P_t T0 Omega_body / 4pi`) appears novel.
- **ML surrogates of FDTD SAR** (CNN/cGAN local SAR, deep-learning head absorption, a CNN over ~7000 phone models ~2000x faster than full-wave). All journal papers, **no granted ML-SAR-on-body patent found**. Good for patentability, but they anticipate the generic "fast approximate body SAR" idea, so claim the specific physics, not "fast SAR."

---

## What this means for the patent claims

1. **Do not file a broad Claim 2** that merely recites "maximise signal quality subject to `x^H (SAR matrix) x <= limit`, solved by SDP/bisection." That is anticipated by Hochwald SAR codes and shadowed by US11940477. Anchor every `Q` claim to: closed-form entries from Fresnel transmission + body geometry, **no FDTD/probe calibration**, near-field point-source uplink form, and differentiability. The "no calibration" limitation is the strongest non-obvious distinction over US11940477 (inherently measurement-based) and over the Hochwald academic precoders (empirically-derived matrix).
2. **Lead the core method claim with the integrated surface law** (`S_ab = S_inc * T0 * ReLU[n_hat . (-k_hat)]` on an arbitrary mesh) plus the view-factor and `Gamma_lm` results, and explicitly distinguish Castellanos-2020 and the thermal view-factor literature in the background. Do not rest novelty on "constant transmission coefficient" alone, that is Kodera/Li/Bamba territory.
3. **Claim 4 (the system)** likely survives as a combination but is vulnerable to an examiner combining ETRI US9961647 (body-SAR over a grid) with US8131312 / US6317599 (3D geo reconstruction + antenna DB + ray trace). Foreground the **forward physics path** (ray-traced / MIMO-coherent field synthesis onto explicit body meshes) and the body-resolved interactive output as the novelty, not "ray tracing," "exclusion zone," or "3D map," all anticipated.
4. **Claims 3 / 3a / 13 (differentiable optimisation under an exposure constraint)** are stronger than the IDF assumes. No patent performs end-to-end gradient descent through a differentiable absorption/compliance operator. Closest is Ericsson US12003294 (runtime precoder weighting) and the deep-RL paper arXiv 2601.02385 (RL, not differentiable). Claim precisely around the differentiable graph (geometry to Fresnel to APD to spatial averaging to compliance) and the gradient over placement/tilt/power/precoder/array-geometry. Cite the RL paper defensively.
5. **Drop the bare "no closely related patents were identified" sentence** from the IDF. Replace with a short paragraph: what was searched (keywords, CPC classes, Qualcomm/Apple/Samsung/Ericsson/Notre Dame/ZMT portfolios), the closest references found (US11940477, US9961647, US9622187, US11729728, Castellanos 2020), and the specific distinctions. The IDF review already requested exactly this. It makes the disclosure credible to UGent TTO and counsel.

---

## What this means for the USP / business plan

The search confirms and sharpens the honest-analysis conclusion: **the defensible differentiator is the differentiable, calibration-free design loop and the integrated system, not the physics discovery.** Reframe the pitch accordingly.

- **Stop selling "we invented physics nobody has."** A skeptical reviewer (or competitor's counsel) will point to Castellanos, Kodera, Li, Bamba, and Hochwald within an hour. The near-constant-`T0` insight is a cleaner derivation of something several groups already observed.
- **Start selling the capability gap.** Every incumbent treats body exposure as one of: a stored scalar SAR value (Qualcomm lookup tables), a proximity-scaled estimate (Apple/Samsung radar backoff), a measured matrix (Hochwald US11940477), a runtime power-control loop (Ericsson EIRP family), or a full-wave FDTD run (Sim4Life/CST). **None of them can hand you a gradient.** AEGIS's "move this array element / pick this beam to minimise peak APD while preserving gain, by differentiating through the absorption operator" is a workflow the entire incumbent stack structurally cannot offer. That is the USP, and the patent search found zero patents on it.
- **The white space is real and narrow:** closed-form surface APD on a mesh (Claim 1), the view-factor whole-body formula (1b), the `Gamma_lm` body-response lookup (16/16a), the calibration-free near-field exposure operator (2a), and differentiable device/network design under an exposure constraint (3a / 3). Build the moat there plus execution (base-station-DB plumbing, viewer, ZMT integration, standards recognition), which no patent touches.
- **The device-OEM market the honest-analysis favours is also the most patent-dense (Cluster 1).** This cuts both ways: it validates that the problem is real and OEMs pay to solve it, and it means any device-side **product** feature needs an FTO check against Qualcomm/Apple before shipping. The **pre-screening-feeds-FDTD** positioning (Claim 17, rank configs then validate in Sim4Life) is the FTO-safest device wedge because it is a design-time computational tool, not a runtime control loop, and it does not read onto the beam-picker patents.

---

## Recommended next steps

1. **Rewrite the IDF prior-art-patents paragraph** with the references above (this closes the credibility gap UGent TTO will probe).
2. **Commission a real FTO** through UGent-appointed counsel before national-phase entry, focused on: Qualcomm + Apple device-SAR portfolios (Cluster 1), Notre Dame/Hochwald US11940477 (Cluster 2), and an Espacenet assignee sweep of NVIDIA / Ericsson / DeepSig 2024-2026 filings (the field is actively being staked, several relevant docs are very recent).
3. **File before any public disclosure** (JSAC submission, preprint, thesis defense). EPO absolute novelty. The academic prior art above does not block AEGIS's specific claims, but AEGIS's own publications would.
4. If a deeper, structured search is wanted, run it through SerpAPI Google Patents API or a paid database to get full claim trees, family/legal-status accuracy, and CPC-class coverage that WebSearch cannot match.

---

## Appendix: full cluster findings

The five-cluster raw findings (every patent located, with status, assignee, claim summary, and per-patent relevance tag) are available in the search session and can be expanded into this appendix on request. Clusters: (1) device SAR/APD control, (2) exposure-aware MIMO precoding, (3) fast/closed-form body dosimetry, (4) base-station/network EMF compliance, (5) RF digital-twin + differentiable optimisation.
