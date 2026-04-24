# Perplexity queries: FR2 smartphone UE hardware model

Purpose: gather citable facts for the "UE model" section of the direction 5 / Route B PoC paper, so we can defend our array geometry, polarization, beamforming architecture, and bandwidth assumptions with real smartphone references rather than fantasy antennas.

Run via `mcp__perplexity__perplexity_research` for depth (bullets 1, 5, 8) and `mcp__perplexity__perplexity_search` for datasheets/URLs (bullets 2, 4, 6, 7). Use `reasoning_effort: "high"` on research calls where noted.

---

## Query 1 — mmWave module count and placement in flagship phones

**Tool:** `perplexity_research`, `reasoning_effort: "high"`

```
How many 28 GHz (FR2) mmWave antenna modules are physically inside modern flagship smartphones, and where are they located in the chassis?

Please give me specific numbers and placements for:
- Apple iPhone 12 Pro, 13 Pro, 14 Pro, 15 Pro (US mmWave-enabled variants)
- Samsung Galaxy S20 Ultra, S21 Ultra, S22 Ultra, S23 Ultra
- Any representative Android flagship with mmWave (Pixel, OnePlus, Xiaomi)

For each, report: number of modules, module placement (top edge, bottom edge, left side, right side, back), and the Qualcomm QTM part number used (QTM052, QTM525, QTM535, QTM545, or successor).

Cite iFixit teardowns, TechInsights reports, Qualcomm press releases, or academic measurement papers with URLs. Give direct quotes where possible. Year of each source.
```

---

## Query 2 — Radiating elements per module (array size + polarization)

**Tool:** `perplexity_search`, 10 results

```
Qualcomm QTM052 QTM525 QTM535 QTM545 antenna module radiating elements per module dual polarization datasheet specifications
```

Follow-up with `perplexity_research`:

```
How many radiating antenna elements are inside a single Qualcomm QTM052 / QTM525 / QTM535 / QTM545 mmWave module, and are they dual-polarized?

I need to know:
- Element count per module (is it 1x4, 2x4, 4x4?)
- Polarization: dual-pol (±45 slant, or H/V) or single-pol?
- So "ports per module" = elements × polarizations = ?
- Is there a patch antenna plus dipole pair combined in each module (hybrid sub-array)?

Cite Qualcomm datasheets, FCC filings, IEEE measurement papers (e.g., Samsung or NIST mmWave UE characterization papers), or iFixit / TechInsights dissection reports.
```

---

## Query 3 — Active module selection vs simultaneous use

**Tool:** `perplexity_research`, `reasoning_effort: "high"`

```
When a 5G mmWave smartphone (iPhone 12 Pro, Galaxy S21 Ultra, etc.) communicates with a base station at 28 GHz, does the modem:

(a) activate only ONE mmWave antenna module at a time via module selection (spatial diversity selection based on SSB-RSRP per module), or
(b) combine signals from multiple modules simultaneously (panel combining / multi-panel transmission)?

This is critical for my channel-estimation problem: if only one module is active, the UE effectively has ~8 ports (4 elements × 2 pol). If multiple modules are combined coherently, it has 16-24+ ports.

Please cite:
- 3GPP TS 38.214 Multi-Panel UE behavior
- 3GPP Rel-17 / Rel-18 multi-panel transmission (mTRP, multi-TRP, mPUE)
- Qualcomm Snapdragon X55/X65/X70 modem documentation
- Academic measurement papers characterizing module selection in commercial phones

Quote the source passages.
```

---

## Query 4 — Element spacing and aperture of one module

**Tool:** `perplexity_search`

```
smartphone mmWave 28 GHz antenna module element spacing half wavelength aperture QTM iPhone Samsung measured
```

Follow-up with `perplexity_ask`:

```
At 28 GHz, free-space wavelength is about 10.7 mm. For a typical smartphone mmWave antenna module (Qualcomm QTM-series or Samsung in-house), what is:

- The inter-element spacing in mm (is it λ/2 ≈ 5.35 mm, or tighter for bandwidth or larger for grating-lobe trade-off)?
- The total aperture of one module in wavelengths (so, for a 1x4 module at λ/2: 1.5λ ≈ 16 mm)?
- The physical footprint of the module on the PCB?

Give me the Rayleigh beamwidth for the expected array size (Δθ ≈ 2/N radians for an N-element ULA at λ/2). I want to reason about angular resolution for direction-of-arrival estimation.

Cite datasheets and measurement papers.
```

---

## Query 5 — Analog vs digital beamforming architecture (CRITICAL)

**Tool:** `perplexity_research`, `reasoning_effort: "high"`

```
This is the most important question for my research paper on UE-side channel estimation for 5G mmWave smartphones.

Does a commercial 5G FR2 smartphone modem (Snapdragon X55, X65, X70; Samsung Exynos 5G) expose per-element complex baseband IQ samples to higher layers, or does the modem hardware only expose post-beamforming scalars (one IQ stream per polarization per selected beam)?

Specifically:
- Is the FR2 RF front end analog / hybrid (one RF chain and ADC per polarization per module, with beam steering done via phase shifters in the RFIC before digitization)? If so, per-element CSI is NOT recoverable at PHY or higher layers.
- Or is it digital per-element (one ADC per element)? This would expose per-element IQ but is prohibitive in power for a phone.
- Does the Android HAL / RIL / modem AT interface expose any raw per-element channel-estimate output, or only post-combining RSRP / CSI / CQI / RI / PMI?
- What do UEs actually report as "CSI" at FR2 — 3GPP Type I / Type II codebooks over beam indices, not per-element h vectors — correct?

Cite:
- Qualcomm Snapdragon FR2 modem whitepapers
- IEEE measurement papers that characterize commercial UE CSI access (e.g., NYU WIRELESS, Bell Labs, Samsung, Nokia Bell Labs characterization)
- 3GPP TS 38.214 Section 5 (CSI reporting)
- Reddit / forum discussions from modem developers (r/Qualcomm, r/mmwave, r/Android, XDA) about whether raw per-element IQ can be obtained on rooted phones

Quote the sources.

FOLLOW-UP: If per-element IQ is NOT exposed, what substitutes are available? e.g., beam-index RSRP sweeps (SSB, CSI-RS) across the codebook — this gives indirect angular information through a "fan of beams" rather than direct spatial samples. Does the 3GPP L1 measurement framework (L1-RSRP per beam index, P1/P2/P3 beam management) provide sufficient data for UE-side angle-of-arrival estimation?
```

---

## Query 6 — Typical deployed FR2 bandwidth

**Tool:** `perplexity_search`

```
5G NR FR2 28 GHz smartphone typical channel bandwidth deployment Verizon AT&T T-Mobile 100 MHz 400 MHz 800 MHz SCS numerology
```

Follow-up with `perplexity_ask`:

```
What channel bandwidth and subcarrier spacing are typically used for 5G NR FR2 (28 GHz) in commercial deployments, as of 2024-2026?

I need:
- Typical contiguous channel BW per carrier (100 MHz, 400 MHz, 800 MHz?)
- Subcarrier spacing (60, 120 kHz?)
- CSI-RS / SRS allocation bandwidth (is it the full channel BW or a narrower subset?)
- Carrier aggregation across multiple 100-MHz blocks — do phones CA up to 800 MHz for effective BW?

Cite Verizon, AT&T, T-Mobile technical briefs, 3GPP TS 38.104 Table 5.3.5-1, FCC filings.
```

---

## Query 7 — Teardowns and measurement papers

**Tool:** `perplexity_search`

```
iFixit TechInsights teardown iPhone 15 Pro Samsung Galaxy S23 Ultra mmWave antenna module photos placement 28 GHz
```

```
academic measurement paper smartphone FR2 mmWave antenna pattern radiation pattern characterization NYU Samsung NIST 2023 2024 2025
```

Follow-up with `perplexity_research`:

```
I need a short bibliography of academic papers and industry teardowns that measure or expose the 28 GHz mmWave antenna pattern, panel count, or beam codebook of commercial 5G smartphones. Specifically:

- NYU WIRELESS characterizations (Ted Rappaport group)
- Samsung Research Korea / Samsung Electronics AE papers on S21/S22/S23 antenna
- NIST or Keysight measurement reports
- Nokia Bell Labs or Ericsson field measurements
- Any paper that publishes the actual radiation patterns C^(1)(theta,phi) and C^(2)(theta,phi) for the two polarization ports

Give me titles, authors, venue, year, and URL if possible. I want to cite 3-5 of these in the "UE model" section of a JSAC 2026 paper.
```

---

## Query 8 — 3GPP FR2 reference UE model

**Tool:** `perplexity_research`, `reasoning_effort: "high"`

```
What is the standard 3GPP reference UE antenna model for FR2 (28 GHz) system-level simulations, as used in TR 38.803, TR 38.817-01, TR 38.901, and related technical reports?

Specifically:
- The reference assumes how many panels per UE? (I recall 3 panels at 120° azimuth spacing, but verify.)
- How many elements per panel? (4+4 dual-pol? 2+2 dual-pol?)
- What is the assumed element pattern? (cosine-squared? 3GPP 38.901 patch?)
- What is the polarization model? (±45 slant dual-pol?)
- What is the beam codebook used in SLS? (DFT codebook over azimuth and elevation?)

Cite exact table numbers and section references in 3GPP documents. I want to defend my PoC's UE model by saying "matches 3GPP TR XX.XXX Table Y.Y reference UE for FR2."

Also, is there a difference between the 3GPP reference UE model and the ITU IMT-2020 evaluation guidelines (M.2412) UE model for mmWave? Which do papers in IEEE TWC, IEEE JSAC, IEEE T-AP commonly use in 2024-2026?
```

---

## Consolidated deliverable

After running queries 1-8, write a 1-page markdown summary at `/home/user/aegis/JSAC/directions/direction_5_ue_hardware_summary.md` with:

- A single recommended "FR2 smartphone UE model" for the PoC (N panels, elements per panel, polarization, spacing, active panel count, exposable CSI interface, assumed BW).
- 3-5 citable sources per claim.
- A "caveats and counter-evidence" subsection flagging where the literature disagrees or where commercial phones may exceed / fall short of the 3GPP reference model.
- One paragraph answering: "Can a commercial FR2 smartphone actually run Route B's UE-side AoA estimation, given the hardware exposes only post-beamforming scalars per beam index? If not, what is the path forward (rooted phone, SDR replacement, operator-cooperative beam sweep, or reformulation)?"

This file becomes the physical-realism footing for the PoC plan.
