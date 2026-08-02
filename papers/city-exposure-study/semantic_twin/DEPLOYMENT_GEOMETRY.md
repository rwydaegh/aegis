# Deployment geometry

`MONOSTATIC_SBR.md` section 2.7 models the external network as an angular
illumination density rather than a site list. Two deployment classes are
defined, each by a height band and a horizontal range band, and eight endpoint
numbers carry those two bands:

| Class | Height above head | Horizontal range | Elevation support |
| --- | --- | --- | --- |
| Macro rooftop | 13.5 to 43.5 m | 25 to 250 m | 3.1 to 60.1 deg |
| Street small cell | 2.5 to 6.5 m | 10 to 150 m | 0.95 to 33 deg |

None of the eight had a citation. This document supplies the evidence, states
what the evidence does not cover, and says by how much and in which direction
the evidence moves each number.

Code is `semantic_twin/propagation/directions.py`, constants `ROOFTOP` and
`STREET_SMALL_CELL`.

**Four findings, if you read nothing else.**

**These numbers cannot be cited, because the deployment they describe does not
exist.** Across 3 863 228 European antennas in the AEGIS base station database,
the number of deployed cellular access antennas above 6 GHz is **zero**
(section 4.3). There is no FR3 or mmWave macro network anywhere to calibrate a
15 GHz height band against. That is not a gap in data collection, it is an
absence of the deployment, and no further register work will close it. Every cap
in this document is an assumption argued from site acquisition and radio
mechanism, and the paper must present it as one.

**So the paper needs a sensitivity band, not a citation.** Across the defensible
span of the range cap, 100 to 400 m, the headline susceptibility proxy moves
**7.8 dB**. Across the defensible span of the height band it moves 0.7 to 2.0 dB
(section 7.5). Report `chi` at 150, 250 and 400 m, and stop arguing about the
height band, which is where sections 10 and 11 spent most of their length for
under a decibel of effect.

**The largest correctable defect is not one of the eight numbers, and it may
invalidate a published figure.** `IlluminationModel` evaluates the pure
`1/sin^3(el)` law on a support derived from the height bands, which is a
different distribution from the one the bands describe (section 7.1). At the
study's 250 m crop the correction moves `chi_rooftop` by **+5.3 to +5.7 dB** at
canyon sites and +1.0 dB at the open plaza, and across the five sites measured so
far it **compresses the cross-site spread from 11.75 to 7.43 dB** (section 7.4).
Roughly a third of the reported cross-city spread looks like an artefact of the
elevation law. This is free to fix, it should be fixed first, and the cross-city
spread figure should not be published until the remaining seven sites land.

**Sub-6 heights are still the right prior for the macro class, for a reason that
is not frequency.** Deployed median height is flat against carrier frequency
across a 5x span, 30.0 to 31.8 m in the Netherlands and 26.8 to 27.8 m in
Brussels, because operators co-site every band on the same mast and the binding
constraint is site acquisition rather than radio (section 4.4). This kills any
attempt to extrapolate a height-versus-frequency trend to 15 GHz, and it supplies
a better argument in its place: if FR3 arrives as an overlay on existing macro
sites, the sub-6 macro distribution is right because it is the **same real
estate**. If FR3 instead requires densification, the new sites appear at street
level and the small cell class carries them. Those are the two branches, the
study already has a class for each, and the paper should say so.

## 1. The datum, stated once

The study places the observation point at pedestrian head height, **1.5 m above
local ground** (`semantic_twin/propagation/walk.py`, `head_height_m: float =
1.5`). Every height in the two bands above is a height **above the head**, so a
ground-referenced height converts as

```
Delta_h = h_ground_referenced - 1.5 m
```

The current bands are therefore **15 to 45 m above ground** for macro and **4 to
8 m above ground** for street small cells.

Almost every source below quotes ground-referenced heights, and most of them do
not say so. The datum question is not pedantic here: the small-cell band is only
4 m wide, so a 1.5 m datum slip is nearly 40 % of it, and the small-cell band is
the one the evidence moves most.

**What the sources actually state about their own datum.**

- **3GPP nowhere states in words that `h_BS` is above ground level.** A search
  of TR 38.901 V19.4.0 for "above ground" and "ground level" returns no hit in
  any height context. The ground reference is inferable but not stated: clause
  7.6.8 builds the explicit ground-reflection path from the Tx and Rx heights
  over "a flat surface with its normal pointing into z-direction", the RMa and
  SMa NLOS pathloss uses the ratio `h/h_BS` with `h` the average building height
  under simultaneous ranges `5 m <= h <= 50 m` and `10 m <= h_BS <= 150 m`, and
  UT height is defined per floor as `h_UT = 3(n_fl - 1) + 1.5` with `n_fl = 1`
  outdoors (TR 36.873 Table 6-1). Clause 6.2 of TR 38.901 writes "Rx height
  **with reference to floor height**: 1.5 m", which pins the UT but not the BS.
- **Report ITU-R M.2412-0 (10/2017) Table A1-45** is the one primary sentence
  that states the datum outright: "BS antenna height (m), h_b, **10-150 m:
  (height above the UT ground level)**", and in the same table "Average building
  height (m), <H>, 5-50 m: (height above the UT ground level)". This is the
  below-6-GHz TSP extension module in Attachment 2 to Annex 1, not the primary
  IMT-2020 module, but it uses exactly the 10 to 150 m range that TR 38.901 and
  TR 36.873 carry in their Okumura-Hata-lineage NLOS applicability, so it is a
  legitimate bridge.
- **Recommendation ITU-R P.1411-13 (09/2025)** is explicit both ways. Its cell
  taxonomy (Table 3) and its L1/L2/L3 station levels (clause 3.1) are
  **roof-top-referenced** and carry no metres at all. Its low-height-terminal
  models say "above ground" in words: clause 4.3.1 cites "antenna heights
  between 1.9 and 3.0 m above ground", clause 4.3.2 "between 1.5 and 4.0 m above
  ground".

**Convention adopted here.** All heights are quoted ground-referenced in the
evidence sections, and converted to above-head only in the recommendation
(section 11). Where a source is roof-top-referenced it is flagged inline.

## 2. Standards evidence for the height bands

### 2.1 3GPP

Values below were read from the 3GPP FTP archive originals, TR 38.901 V19.4.0
(2026-06), TR 36.873 V12.7.0 (2017-12), TR 38.802 V14.2.0 (2017-09), TR 38.808
V17.0.0 (2021-03), TR 38.820 V16.1.0 (2021-03), TR 38.913 V19.0.0 (2025-09).

| Value | Where |
| --- | --- |
| UMi-street canyon `h_BS = 10 m`, ISD 200 m, 19 micro sites, 3 sectors | TR 38.901 Table 7.2-1 |
| UMa `h_BS = 25 m`, ISD 500 m, 19 macro sites, 3 sectors | TR 38.901 Table 7.2-1 |
| "UMa scenarios with ISDs between 200-500m can be used for evaluations" | TR 38.901 Table 7.2-1 NOTE 1 |
| UMi pathloss applicability `h_BS = 10 m`, `1.5 m <= h_UT <= 22.5 m` | TR 38.901 Table 7.4.1-1 |
| UMa pathloss applicability `h_BS = 25 m`, `1.5 m <= h_UT <= 22.5 m` | TR 38.901 Table 7.4.1-1 |
| 3D-UMa NLOS applicability `10 m < h_BS < 150 m`, `5 m < h < 50 m` | TR 36.873 Table 7.2-1 |
| Dense urban: `h_BS` "25 m for macro cells and 10 m for micro cells", inter-BS 200 m macro | TR 38.802 Table A.2.1-1 |
| Dense urban micro-TRP minimum spacing 57.9 m (3 per macro TRP), 42.4 m (6), 32 m (9). Option 2 gives 40 / 32 / 25 m | TR 38.802 Table A.2.1-9 |
| Dense urban mmWave, 1 layer: `h_BS = 10 m`, `h_UT = 1.5 m`, **ISD = 150 m**, "FFS: whether ISD needs to be smaller" | TR 38.808 V17.0.0, outdoor scenario A |
| Dense urban mmWave, 2 layer: macro `h_BS = 25 m` at **ISD 100 m**, micro `h_BS = 10 m` randomly dropped, minimum micro-to-micro 10 m | TR 38.808 V17.0.0, outdoor scenario B |
| 7-24 GHz dense urban ISD 200 m, urban macro 500 m, indoor hotspot 20 m. No heights given | TR 38.820 Table 5.6.5-1 |
| Deployment scenario tables carry no BS height row at all | TR 38.913 clause 6.1 |

Two points matter more than the individual numbers.

**3GPP defines the deployment class relative to the roofline, not in metres.**
TR 38.901 clause 6.2 item (1): UMi is the scenario "where the BSs are mounted
**below rooftop levels** of surrounding buildings". Item (2): UMa is "where the
BSs are mounted **above rooftop levels** of surrounding buildings". The metre
values 10 m and 25 m are quoted as bracketed *examples* attached to those
definitions, not as the definition. Recommendation ITU-R P.1411-13 Table 3 does
the same thing: micro-cell is "mounted above average roof-top level", dense urban
micro-cell is "mounted below average roof-top level", pico-cell is "mounted below
roof-top level". Section 5 builds on this.

**3GPP's own name for this study's scenario is UMi open area, not UMa.**
TR 38.901 clause 6.2 item (1), verbatim:

> UMi (Street canyon, open area) with O2O and O2I: This is similar to 3D-UMi
> scenario, where the BSs are mounted below rooftop levels of surrounding
> buildings. **UMi open area is intended to capture real-life scenarios such as a
> city or station square. The width of the typical open area is in the order of
> 50 to 100 m.**

Eleven city squares of 50 to 130 m span is precisely that scenario, and 3GPP
assigns it `h_BS = 10 m` below the roofline. That is 8.5 m above the head, which
falls in the **gap between this study's two bands** (small cell tops out at
6.5 m above head, macro starts at 13.5 m). The single most-cited base station
height for this exact geometry is currently not representable in either class.

There is one caveat on the FR3 relevance. The Release 19 study "Channel
modelling enhancements for 7-24 GHz for NR" (SID RP-234018) was folded into
TR 38.901 rather than given its own TR, and it changed large-scale parameter
values and added the SMa scenario. **It did not introduce band-specific base
station heights.** The 7-24 GHz geometry is the same UMi 10 m / UMa 25 m as
sub-6.

### 2.2 ITU-R

| Value | Where |
| --- | --- |
| Dense Urban-eMBB Config A and B: `h_BS = 25 m`, ISD 200 m. Config C: "25 m for macro sites and **10 m for micro sites**", macro ISD 200 m | Report ITU-R M.2412-0, Table 5 b) |
| Dense urban is two-layer: "**3 micro sites randomly dropped in each macro TRxP area**", no micro ISD specified | Report ITU-R M.2412-0, clause 8.3.2 |
| UMi_x pathloss `h_BS = 10 m`, UMa_x `h_BS = 25 m` | Report ITU-R M.2412-0, Tables A1-3, A1-4 |
| Micro-cell: **cell radius 0.05 to 1 km**, "mounted above average roof-top level, heights of some surrounding buildings may be above base station antenna height" | Rec. ITU-R P.1411-13, Table 3 |
| Dense urban micro-cell: **cell radius 0.05 to 0.5 km**, "mounted below average roof-top level" | Rec. ITU-R P.1411-13, Table 3 |
| Pico-cell: **cell radius up to 50 m**, "mounted below roof-top level" | Rec. ITU-R P.1411-13, Table 3 |
| Over-roof-top multi-screen model, **urban**, valid for "**h1: 4 to 55 m**; h2: 1 to 3 m; f: 800 to 26 000 MHz; **d: 20 to 5 000 m**" | Rec. ITU-R P.1411-13, clause 4.2.2 |
| Over-roof-top multi-screen model, **suburban**, valid for "h1: 1 to 100 m; h2: 4 to 10 m" | Rec. ITU-R P.1411-13, clause 4.2.2 |
| Site-general below-rooftop street canyon: LoS valid 0.45-300 GHz over **5 to 660 m**, NLoS urban high-rise 0.8-159 GHz over **20 to 715 m**, NLoS urban low-rise/suburban 0.45-255 GHz over **10 to 250 m**. Applies "regardless of their antenna heights" | Rec. ITU-R P.1411-13, clause 4.1.1 and Table 4 |
| Site-general above-rooftop: LoS valid 2.2-73 GHz over **55 to 1200 m**, NLoS urban high-rise 2.2-66.5 GHz over **260 to 1200 m** | Rec. ITU-R P.1411-13, clause 4.2.1 and Table 8 |
| Measured `h1` values in the delay-spread tables: 100 m (urban very high-rise, 2.5 GHz), 60 m and 40 m (urban high-rise, 3.7 GHz), 46 m (1.9-2.1 GHz), 20 m, and in Table 12 a cluster at **4.0 to 6.0 m** for 0.78 to 15.75 GHz urban | Rec. ITU-R P.1411-13, Tables 11, 12 |

The `h1: 4 to 55 m` validity range of the urban over-roof-top model is the
closest thing in the standards to an explicit statement of the macro height
band, and it is wider at the bottom and narrower at the top than the current
15 to 45 m.

**ITU-R P.1410 supplies the shape of the height distribution, which no other
standard does.** Recommendation ITU-R P.1410-5 (02/2012) clause 2.1.4 builds
its urban LoS coverage model on three parameters, one of which is the building
height distribution, and equation (17) states it:

```
P(h) = (h / gamma^2) exp(-h^2 / (2 gamma^2))
```

a Rayleigh distribution, with "the variable gamma equates to the most probable
(mode) building height". Clause 2.1.6 records that "the Rayleigh fit was made to
the cumulative distribution of **rooftop heights** found in a suburban location
in the United Kingdom (Malvern)", giving `alpha = 0.11, beta = 750,
gamma = 7.63`, and clause 2.1.5 warns that "the Rayleigh building height
distribution has been found accurate for some samples of data where a limited
area was considered, e.g. a small town". P.1410-5 also states the parameter
ranges "for suburban to high-rise locations alpha will range from 0.1 to 0.8 and
beta from 750 to 100", and its Figure 6 sweeps transmitter heights of **5, 10,
15, 20, 25 and 30 m** as the urban range of interest.

This is the only primary source found that says anything at all about the
*shape* of the height distribution rather than its endpoints, and what it says
is that the shape is unimodal with a decaying tail. It is not uniform. Section 10
takes this up.

## 3. Measurement campaign evidence

This is the strongest section, because it reports what was actually built rather
than what was assumed. All heights below are above ground level unless flagged.

### 3.1 A correction on the source everybody cites

The multi-institution table of campaign geometries is **not** in Haneda et al.,
"5G 3GPP-like Channel Models for Outdoor Urban Microcellular and Macrocellular
Environments", VTC Spring 2016 (arXiv:1602.07533). That paper carries only
LOS-probability and pathloss model comparisons, and its one geometry sentence is
"there was one AP used in the study which had a height of 25 m. The UE height was
1.5 m." The table lives in

> "5G Channel Model for bands up to 100 GHz, Annex A: Summary of channel
> sounding, simulations and measurement data", revised September 2016, 109 pp.
> Contributors Aalto, AT&T, BUPT, CMCC, Ericsson, Huawei, Intel, KT, Nokia,
> NTT DOCOMO, NYU, Qualcomm, Samsung, Univ. of Bristol, USC.
> `http://www.5gworkshops.com/Annex_230916.pdf`

The companion white paper's campaign tables are status matrices only, party by
band, with no heights.

### 3.2 The one campaign at 15 GHz with an elevated base station in a square

> P. Okvist, H. Asplund, A. Simonsson, B. Halvarsson, J. Medbo, N. Seifi,
> "15 GHz Propagation Properties Assessed with 5G Radio Access Prototype",
> IEEE PIMRC 2015, pp. 2220-2224, doi 10.1109/PIMRC.2015.7343666. Also
> transcribed in 5GCM Annex A clause A.1.3.1.

Verbatim: "The two TPs are **installed on the walls of two office buildings at
heights 8.5 m (TP1) and 12 m (TP2)**, respectively, and with an **inter-distance
of 82 m**." The site is "a **square area located in Kista, an urban area in
Stockholm, Sweden**, with mainly 4-6 floor office buildings". Main test areas
"10-65 m from corresponding antennas", mobile driven "**up to 250 m away**
including NLoS areas", dual-slope fit with a **break point at 120 m** and a
second-slope exponent of 4. Elevation HPBW 8.6 degrees.

This is the closest published analogue to what this study models: the right
frequency, an enclosed European square, an elevated base station, and a
pedestrian-height receiver. Its two antenna heights, **8.5 and 12 m**, are both
**below the current macro band's 15 m floor** and both **above the current small
cell band's 8 m ceiling**. They land in the gap.

Its coverage sentence is the most useful single quote for the range cap: "In the
enclosed square and along adjacent streets within LoS, coverage is quite good
with received signal strength above -65 dBm. **In non-LOS conditions, coverage
disappears** as received signal strength quickly decreases towards the noise
floor with the present configuration of the test system." Corner loss about
20 dB, and "**No indications on significant LOS propagation difference at
15 GHz**" against lower bands.

### 3.3 Per-site heights, pooled across campaigns

| Campaign | Frequency | City | TX or BS heights | Reference |
| --- | --- | --- | --- | --- |
| NYU WIRELESS Manhattan | 28 GHz | New York | **7, 7, 17 m** (COL1, COL2, KAU) | Azar et al., ICC 2013 clause III; MacCartney et al., IEEE Access 3:1573 (2015) Table 1; Rappaport et al., IEEE TCOMM 63(9) Tables II, XI |
| NYU WIRELESS Manhattan | 73 GHz | New York | **7, 7, 7, 7, 17 m** (COL1, COL2, KIM1, KIM2, KAU) | Rappaport et al., IEEE TCOMM 63(9) clause II.D.4 |
| NYU Brooklyn | 28 GHz | New York | **40 m** (Rogers Hall, eight storeys) | Samimi et al., VTC Spring 2013 clause II |
| NYU Brooklyn MetroTech | 73.5 GHz | New York | **4.0 m** | Rappaport et al., IEEE TAP 65(12) 2017, arXiv:1707.07816 |
| UT Austin campus | 38 GHz | Austin | **8, 23, 36, 36 m** (ECJ, WRW-A, ENS-A, ENS-B), antenna on a tripod 1.5 m above each roof | Rappaport et al., IEEE TAP 61(4) 2013 clause II; IEEE Access 2015 Table 2 |
| Ericsson Kista | 15 GHz | Stockholm | **8.5, 12 m** | Okvist et al., PIMRC 2015 |
| Ericsson Kista | 2.44 / 14.8 / 58.68 GHz | Stockholm | **1.5 m** both ends | 5GCM Annex A clause A.1.3.2.2 |
| Ericsson UMa | 28 GHz | Gothenburg | **25 m** (Lindholmen), **36 m** (Molndal) | 5GCM Annex A Table A5.2.1-1 |
| Nokia and Aalborg | 10 / 18 / 28 GHz | Aalborg | **15, 20, 25, 54 m** by boom lift plus a hospital roof, in a district with "building height and street width ... measured at 17 and 20 meter" | 5GCM Annex A clause A.5.4.1, Table A5.4.1-1 |
| Aalto Otaniemi | 15 / 28 / 60 GHz | Espoo | **2.57 m both ends**, pedestrian to pedestrian, not a base station | mmMAGIC D2.1 clause 6.1.1 |
| Aalto Narinkkatori open square | 28 / 86 GHz | Helsinki | **5 m** on a lamp post at a square corner, MS at 1.6 m | mmMAGIC D2.2 Table A.16 |
| Aalto Kamppi open square | 60 GHz | Helsinki | **2 m both ends**, square 80 by 80 m surrounded by six-storey buildings of "average height of 40 m" | 5GCM Annex A clause A.2.1.2 |
| Fraunhofer HHI and R&S, Friedrichstrasse | 10.25 / 28.5 / 41.5 / 82.5 GHz | Berlin | **5.0 m** on a tripod | mmMAGIC D2.1 clause 6.1.2 |
| Rohde & Schwarz, open square | **17 GHz** | Munich | **about 14 m**, outside the 5th floor across the street, tilted down to the square centre. Square 50 by 50 m | mmMAGIC D2.2 clause A.2.7, Table A.24 |
| University of Bristol | 60 GHz | Bristol | **6.45 m** | mmMAGIC D2.2 |
| Orange | 3 / 17 / 60 GHz | Belfort | **2.5 m** on a van roof | mmMAGIC D2.2 |
| Nokia Bell Labs and Columbia | 28 GHz | Manhattan and Valparaiso | **15 to 51 m** roof edge, **8 to 15 m** lamppost | Du, Chizhik, Valenzuela et al., IEEE TAP 69(6):3459, 2021, arXiv:1908.00512 |
| NYU FR3 Brooklyn | 6.75 and **16.95 GHz** | New York | **4 m** at all five TX, "similar to lamppost heights, representing small-cell BS", site is an "open square of around 200 m" | Shakya, Ying, Rappaport et al., ICC 2025, arXiv:2410.17539 |
| FR3 ultra-massive MIMO UMi | **14.875 to 15.125 GHz** | not named in text | **14.7 and 16.5 m**, RX 1.8 m, TX tilt 15 degrees | arXiv:2604.08012 |
| USC | 6 to 14 GHz | Los Angeles | **20.38 m** | arXiv:2412.20755 |
| AT&T | 6.9 / 8.3 / 14.5 GHz | Austin | "a tripod-mounted transmitter is positioned atop rooftops or other structures ... at **heights between 10 and 35 meters above the street level**" | arXiv:2510.00275, GLOBECOM 2025 |
| AT&T, 3GPP contribution | 7 / 8 / **15 GHz** | Austin | **25 and 35 m** | 3GPP R1-2501371 |
| BUPT | 8 and **15 GHz** | Beijing | **27.8 m** | arXiv:2606.11622, arXiv:2604.15680 |
| BUPT cell-free | **14.8 to 15.2 GHz** | Beijing | **27 m** | arXiv:2512.02501 |
| BUPT clutter loss | 10.2 to 14.8 GHz | Beijing | **62.5 m** | arXiv:2504.06727 |
| Live commercial cell | 26 GHz | Copenhagen | **34.9 m**, Ericsson AIR 5322 n258, RX walked at 1.7 m | arXiv:2404.05477, IEEE WCL doi 10.1109/LWC.2024.3434415 |
| Live commercial cell | 26.5 to 29.5 GHz | Oslo | **15 m** rooftop, one sector "towards an **open square**" | Elmokashfi et al., arXiv:2104.06188 |

The AT&T Austin FR3 statement, "**heights between 10 and 35 meters above the
street level**", is an independent measured-deployment statement of almost
exactly the band recommended in section 11.2. That was not the intent when the
band was chosen, and it is the strongest single corroboration in this document.

### 3.4 The height distribution, which is the point

Pooling every stated elevated urban site height above, one entry per site or per
stated value:

```
4.0, 4, 5, 5, 5, 6, 6.45, 7, 7, 7, 7, 7, 8, 8.5, 12, ~14, 14, 14.7, 15, 15, 15,
15, 15, 15, 15, 15, 16.5, 17, 17, 18, 20, 20, 20, 20, 20.38, 22, 23, 25, 25, 27,
27.8, 33, 34, 34.9, 35, 36, 36, 40, 45-50, 50, 54, 56, 62.5
```

This is **bimodal, with a long upper tail, and nothing like uniform**. Three
functional modes:

- **A lamppost and low-facade mode at 4 to 8 m.** NYU's FR3 campaign at 4 m
  explicitly "similar to lamppost heights", Aalto's open-square BS at 5 m on a
  lamp post, Fraunhofer Berlin at 5 m, NYU's six Manhattan sites at 7 m, Nokia's
  lamppost subset at 8 to 15 m.
- **A low-rooftop mode at 14 to 25 m**, which carries most of the mass.
- **A sparse macro tail at 33 to 62 m.**

The single best-resolved per-site list is Nokia's Manhattan streets:

> D. Chizhik, J. Du, R. A. Valenzuela, "Universal Path Gain Laws for Common
> Wireless Communication Environments", IEEE TAP 2021,
> doi 10.1109/TAP.2021.3121173, arXiv:2111.01758, Table 1.

Twelve streets, per-street `h_BS`: **14, 15, 15, 15, 15, 15, 15, 20, 20, 20, 22,
56 m**. Median 15 m, eight of twelve at 14 to 15 m, one outlier at 56 m. That is
a sharply peaked distribution with a thin high tail, which is the shape section
10 argues for and the opposite of uniform. Note the two Nokia papers do not agree
with each other: TAP 2021 states a range of "15 to 51 m" while the companion
table contains 56 m.

Also from that campaign, the roof-edge result, verbatim: "**Offsetting the base
antenna 5 m away from roof edge, as is common in macro cellular deployments,
introduces an additional average loss of 15 dB at 100 m**, but this additional
loss reduces with distance", with the stated motivation that antennas are set
back "to conceal them from street view based on aesthetic considerations". This
matters for `MONOSTATIC_SBR.md` section 9.3's parapet exception, and it means a
rooftop height is an upper bound on the effective illumination height.

⚠️ Read the Nokia geometry carefully before citing: the rotating horn
**receiver** emulates the base station and the transmitter emulates the UE.
Path gains are reciprocal so the models transfer, but the sentence "the
transmitter was at 51 m" would be wrong.

**Two further Nokia results bear on how separate the two classes really are.**
The lamppost subset (422 links, 3 streets, `h_BS` 8 to 15 m) fits
`A = -60.4 dB, n = 2.42, sigma = 5.5 dB` and "suffers about 9 dB more loss than
free space at 200 m", and the paper concludes "**very similar path gain behavior
for roof-edge and lamppost mounted base stations**" in same-street coverage,
with the rooftop fit applied to lamppost data raising RMS only from 5.5 to
6.0 dB. That is an argument that the two deployment classes are less distinct
than a two-band model implies, at least for same-street geometry.

The same paper also reports that standard ray tracing **overpredicted signal by
13 dB at 200 m** in a simple street canyon, attributed to "omission of
difficult-to-model scatter from street objects, such as vehicles, pedestrians
and trees", and that standard 3GPP models were 12 to 17 dB RMS off their data.
Both are caveats the deterministic arm of this study should acknowledge.

### 3.5 Measured range, which settles the range cap better than any standard

| Statement | Value | Source |
| --- | --- | --- |
| Longest 28 GHz Manhattan link that closed | **187 m** NLOS, LOS max 102 m. "We could find no links at distances greater than 200 m for Manhattan with 178 dB PL" | Azar et al., ICC 2013 clause V |
| Longest 73 GHz Manhattan link that closed | **190 m**. 216 m was attempted and gave outage | Rappaport et al., IEEE TCOMM 63(9), footnote |
| NYU's converged conclusion, two frequencies and two cities | "**A 200 m cell radius** means that the distance between base stations is 400 m"; and independently at 38 GHz in Austin, "The coverage radius of 200 m is identical to that measured in New York City" | IEEE TCOMM 63(9) clause VI; IEEE TAP 61(4) 2013 |
| 38 GHz recommendation | "millimeter-wave cellular systems may work best in dense urban environments with microcell deployments with **cell radii less than 200 m**" | Rappaport et al., IEEE TAP 61(4) 2013 clause IV |
| Measured Verizon 39 GHz lamppost spacing, downtown Chicago | "**The average distance between the Verizon mmWave BSs is 140 m**" | Rochman et al., ACM WiNTECH 2021, arXiv:2108.00453 |
| Measured Verizon 28 GHz throughput cliff, downtown Miami | drops at **91 m**, and "having trees ... reduces the coverage range down to **38 m**" | Rochman et al., WiNTECH 2021 |
| Deployed site density, downtown Chicago | 34 and 19 BS in 2.23 km2, that is 15.2 and 8.5 per km2, "often mounted over poles", covering only 35 % of road length | Narayanan et al., INFOCOM 2022 |
| Qualcomm deployment planning | "5G NR mmWave mobile deployments will require dense network topologies with **inter-site distances of about 150-200 meters**" | Qualcomm, "5G NR Millimeter Wave Network Coverage Simulation Studies for Global Cities" |
| Nokia at 13 GHz, the closest band to this study | 75 dBm/100 MHz EIRP "would lead to **outage at the cell edge for urban macro sites with ISD of 500 m**", and "much denser deployments (e.g. **200 m ISD**) will be required" | Nokia, "Coverage evaluation of 7-15 GHz bands from existing sites", 2025 |
| Live 26 GHz cell, Copenhagen | LOS RSRP above -92 dBm "for BS-UE distances **below 140 m**", -125 dBm at **350 m**, and "within a few meters after turning the corner, the signal drops below the sensitivity of the radio scanner" | arXiv:2404.05477 |
| Nokia Aalborg, longest measured link | **1429 m** at 18 GHz from a 54 m rooftop, over a residential district with 17 m buildings | 5GCM Annex A Table A5.4.1-1 |
| NYU FR3, both ends of the spread from the same 4 m antenna | outage at **216 m** NLOS from one TX, **880 m** NLOS closed from another | arXiv:2410.17539 |

The convergence is unusually good. NYU at 28 and 73 GHz in New York and 38 GHz
in Austin, Qualcomm's deployment planning, Nokia at 13 GHz and Verizon's actual
deployed spacing all land between 140 and 200 m of cell radius or inter-site
distance in a dense core. The current 150 m small-cell cap sits inside that
cluster. The 250 m macro cap sits above it, which is correct for an exposure sum
that must include non-serving sites, and section 8 quantifies the price.

The last row is the honest counterweight and deserves to be in the paper: the
same 4 m antenna gave outage at 216 m at one site and closed 880 m at another.
In a dense core, site geometry dominates any nominal range, which is the argument
for the deterministic arm of this study in the first place.

### 3.6 An internal inconsistency this section exposes

`report.tex` line 102 states that the deterministic arm places "Sites ... on
interior points of real rooftops inside an **8 to 45 m height band** with 10
degree downtilt", and figure captions state a **150 m range**. The stochastic
arm documented in `MONOSTATIC_SBR.md` section 2.7 uses **15 to 45 m above ground**
and **250 m**. The two arms of the same paper disagree on the height floor by
7 m and on the range by 100 m. That should be reconciled before submission, and
the campaign evidence above says the lower floor is the better one.

### 3.7 Discrepancies between primary sources, flag these if citing

1. UT Austin WRW-A is **23 m** in IEEE TAP 2013, IEEE Access 2015 Table 2, RWS
   2012 and IEEE Access 2013 clause IV.A, but **18 m** in IEEE TCOMM 2015
   Table X and IEEE Access 2013 clause IV.B. ICC 2012 describes the same
   building as "a 5 story building (~60 feet)", about 18.3 m, which favours
   18 m. Unresolved in the literature.
2. Aalto Otaniemi antenna height is **2.57 m** (mmMAGIC D2.1), **2.6 m**
   (mmMAGIC D2.2) and **2.77 m** (5GCM Annex A). Cite D2.1, the campaign owner's
   own deliverable. Maximum distance likewise 121 m against "about 124 m".
3. Nokia Manhattan BS heights are "15 to 51 m" in TAP 2021 but the companion
   per-street table contains 56 m.
4. NYU 28 GHz minimum T-R separation appears as 19, 20, 30 or 31 m and maximum
   as 425 or 500 m, while the per-link table maxes at 419 m.
5. NYU's 2013 outage percentages were explicitly declared incorrect by the same
   authors in IEEE TCOMM 2015 clause VI. Use TCOMM Table XI.

### 3.8 What could not be reached

Reported as NEEDS_CONTEXT rather than substituted.

1. **H. Miao, J. Zhang, P. Tang, L. Tian, X. Zhao, B. Guo, G. Liu, "Sub-6 GHz
   to mmWave for 5G-Advanced and Beyond", IEEE JSAC 41(6):1945-1960, 2023,
   doi 10.1109/JSAC.2023.3274175.** The 3.3 / 6.5 / **15** / 28 GHz UMi campaign,
   probably the most cited 15 GHz urban microcell dataset. Not on arXiv, closed
   in Semantic Scholar. NYU's ICC 2025 paper describes it secondhand as having "a
   rooftop TX at 12.5 m height and human height RX". **Do not cite 12.5 m without
   the primary.**
2. **Naderpour, Vehmas, Nguyen, Jarvelainen, Haneda, "Spatio-temporal channel
   sounding in a street canyon at 15, 28 and 60 GHz", IEEE PIMRC 2016,
   doi 10.1109/PIMRC.2016.7794730.** Would settle the Aalto height discrepancy.
   research.aalto.fi returns 403.
3. **Okvist, Seifi, Halvarsson, Simonsson, Thurfjell, Asplund, Medbo, "15 GHz
   Street-Level Blocking Characteristics Assessed with 5G Radio Access
   Prototype", VTC Spring 2016, doi 10.1109/VTCSpring.2016.7503969.** Street-level
   15 GHz blocking geometry, directly relevant to pedestrian exposure.
4. **Saba, Mela, Sheikh, Ruttik (Aalto), "Measurements at 5G Commercial 26 GHz
   Frequency with Above and on Rooftop Level Antenna Masts in Urban
   Environment", VTC 2021-Spring,
   doi 10.1109/VTC2021-Spring51267.2021.9448983.** The title promises exactly the
   above-rooftop against on-rooftop mast contrast this document needs.
5. **METIS D1.2 and D1.4.** metis2020.com is parked, Wayback has no usable
   snapshot, CORDIS 404s. Only on ResearchGate behind a login.
6. **Masui, Kobayashi, Akaike, "Microwave path-loss modeling in urban
   line-of-sight environments", IEEE JSAC 20(8):1151-1155, 2002,
   doi 10.1109/JSAC.2002.801215.** Measured in metropolitan Tokyo at 3.35, 8.45
   and **15.75 GHz**, so within 5 % of this study's frequency. Du et al.
   (arXiv:1908.00512) describe it **secondhand** as a "base station at 4 m and a
   terminal at 1.6 and 2.7 m" on a single Tokyo street. **Secondhand only. Do not
   cite the 4 m without the primary.** Paywalled at
   `https://ieeexplore.ieee.org/document/1021907`.
7. NTT DOCOMO Tokyo and Odaiba site heights, doi 10.1109/CCNC.2019.8651808,
   doi 10.1109/VTCFall.2019.8891237, doi 10.1587/transcom.2018TTP0008. A web
   snippet claimed about 25 m and 30 degrees downtilt for the Odaiba site. **That
   is unverified against any PDF and is not cited here.**

## 4. Regulatory and register evidence

Sections 2 and 3 give what standards assume and what researchers built. This
section gives what regulators permit and what operators have actually installed.

**Read 4.3 before using anything in this section.** The registers contain no
deployed FR3 or mmWave cellular base station anywhere in the world, so nothing
here calibrates a 15 GHz height band directly. What the registers do establish is
where the *sites* are, and 4.4 gives the reason that is the relevant fact anyway.

All register numbers below come from the AEGIS base station database at
`data/basestations/merged/*.parquet`, 5 252 041 antennas across 15 regions,
configured in `data/basestations/regions.yaml`. Nothing here was re-scraped.

### 4.1 What the rules permit

Regulatory ceilings bound the height band from above but they bound it loosely.
Every number below is a permitted maximum, not a deployment claim, and the
deployed distributions in 4.2 sit well inside all of them.

| Jurisdiction | Instrument | Height limit | Datum, as written |
| --- | --- | --- | --- |
| US, federal | 47 CFR 1.6002(l)(1)(i) | 50 ft, 15.24 m | Structure height **including antennas**. No reference plane stated anywhere in the rule |
| US, federal | 47 CFR 1.6100(b)(7)(i) | +10 % or +3.048 m (10 ft), whichever greater | **Increment above the original support structure**. No absolute ceiling |
| US, states | Ohio RC 4939.0319, Texas LGC 284 | 12.2 to 16.8 m | Above grade, as written in the statutes |
| UK | GPDO 2015 Sch. 2 Pt. 16 A.1(1)(c) | 30 m unprotected, 25 m art. 2(3) land | Above ground level, **excluding any antenna** |
| UK | GPDO A.1(2)(b) | +6, +8 or +10 m by building tier | **Above the highest part of the building** |
| EU | Reg. 2020/1070, EECC art. 57 | No height limit at all | Volume 30 L, and a 2.2 m walkway clearance in recital (8) |
| France | ANFR, no national cap | None | n/a |

Three things in that table matter for modelling and are easy to get wrong.

**The FCC never states a reference plane.** The rule says facilities "are
mounted on structures 50 feet or less in height including their antennas". It is
a total support-structure height inclusive of the antenna, not an
antenna-above-structure figure and not a centreline. Reading it as above-grade is
natural but it is an inference, so do not attribute "AGL" to the FCC. The
definition also does not live in a numbered paragraph: it is footnote 9 to
paragraph 11 of FCC 18-133, and cite it that way.

**The UK order uses three different datums in a single sub-paragraph.**
A.1(2)(a)'s 15 m and 10 m are the apparatus's own vertical extent, taken by
itself. A.1(2)(b)'s 6, 8 and 10 m are measured above the highest part of the
building, so a parapet or a plant room raises the datum. Only A.1(2)(e) says
"measured from ground level", and it says so expressly because it is the one
place the Order means it. A building of exactly 15.0 m falls in the 6 m tier,
because the 8 m tier requires "more than 15 metres".

**The UK mast limit excludes the antenna.** A permitted-development 30 m mast
carries its radiating aperture above 30 m AGL by an amount the Order does not
regulate. Any use of 30 m as a modelling ceiling understates the aperture height.

One correction to a claim in circulation: S.I. 2022/278 art. 3(2) reads "in
sub-paragraph (i), for '25' substitute '30'; in sub-paragraph (ii), for '20'
substitute '25'". It raised **ground mast** heights only. The building-mounted
15/10 m and 10/8/6 m figures are unchanged since S.I. 2016/1040. The 2022 order
is often described as having raised rooftop limits and it did not.

Small cells are exempt from prior planning permission in both the EU (EECC art.
57(1)) and the UK, so the regulatory ceiling is not what caps street-level
heights. Something else does, and 4.5 shows what.

### 4.2 What is actually deployed

The database carries usable heights for **four of the eleven study sites**.
Restricting to `CenterHeight` in (0, 100] m:

| Study site | Region | Radius | n | p5 | p25 | median | p75 | p95 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Place du Capitole | france | 250 m | 137 | 17.9 | 20.8 | **21.3** | 25.1 | 32.1 | 32.4 |
| Place du Capitole | france | 500 m | 636 | 17.6 | 20.2 | **21.1** | 26.2 | 31.6 | 33.8 |
| Korenmarkt | flanders | 250 m | 418 | 18.8 | 26.2 | **27.6** | 42.5 | 42.5 | 42.5 |
| Korenmarkt | flanders | 500 m | 1164 | 18.8 | 22.4 | **25.8** | 28.0 | 42.5 | 42.5 |
| Grand Place | brussels | 250 m | 94 | 6.5 | 32.5 | **33.5** | 34.1 | 35.3 | 35.3 |
| Grand Place | brussels | 500 m | 360 | 7.9 | 29.7 | **32.5** | 34.7 | 51.6 | 54.2 |
| Rynek Glowny | poland | 250 m | 73 | 14.8 | 25.0 | **38.0** | 42.0 | 42.0 | 42.0 |
| Rynek Glowny | poland | 500 m | 224 | 12.0 | 25.0 | **28.0** | 35.0 | 42.0 | 42.0 |

Two of these, Brussels and Krakow, were listed as blocked in an earlier draft of
this document. They were not blocked, they were already extracted.

**The four medians run from 21.1 to 32.5 m at 500 m radius.** That is an 11 m
spread across four European historic squares, and it is the most direct evidence
in this document for the section 9 argument that a single global height band
cannot represent all eleven sites. Toulouse and Krakow differ by more than the
width of any band either of them would justify alone.

Spain has 178 207 antennas with 100 % frequency coverage and **0 % height
coverage**, so Madrid and Barcelona remain without deployed heights. That is a
property of the source, not a scraping failure.

**The datum trap survives normalisation, and gets worse.** The merged schema
calls the column `CenterHeight` for every region, but the underlying registers do
not all report a centre. Verified: the France rows reproduce the ANFR
`AER_NB_ALT_BAS` distribution exactly, median 21.1 m at 500 m in both, and that
field is the antenna **base**.

| Register | Source field | Datum, verbatim | Actually marks |
| --- | --- | --- | --- |
| France, ANFR | `AER_NB_ALT_BAS` | "La hauteur de l'antenne sur son support par rapport au sol" | Antenna **base** |
| Flanders, conformiteitsattest | `Hoogte midden (m)` | "H1 is de hoogte vanaf het grondniveau (referentiepunt) tot aan het midden van de antenne" | Antenna **centre** |
| Netherlands, Antenneregister | `Hoogte` | "de hoogte in meters waarop de antennepanelen zijn geplaatst, vanaf de grond gemeten" | Panel **mounting point** |

All three are ground-referenced, which is what matters most. Base to centre is
roughly half a panel length, about 1 m at macro sizes, so the French figures run
about 1 m low against the Belgian ones. Not corrected. The column name asserts a
uniformity the sources do not have, and this is recorded again in section 14.

The superseded direct-harvest tables that an earlier draft of this section
carried are dropped. They are reproduced by the database to within a metre at
Toulouse and Ghent, and where they are not reproduced, section 4.5 explains why
the database should be preferred.

### 4.3 No register anywhere contains a deployed FR3 or mmWave cellular antenna

This is the finding that governs everything else in the section, and it is a
negative result.

Auditing `Frequency` across all 15 regions, of **3 863 228 European antennas the
number of cellular access antennas above 6 GHz is zero**. Not sparse. Zero.
France, Netherlands, Spain, Poland and Brussels each return exactly zero, and
their maxima are 2600, 3700, 3755, 3500 and 3750 MHz respectively.

Two apparent counter-examples both dissolve on inspection.

**UK, 15 140 rows above 6 GHz.** Every one has `Technology` = `FH`, and the
median frequency is 22 036 MHz. These are fixed point-to-point microwave links,
which is backhaul infrastructure and not cellular access. The entire UK region
is `FH`, 15 141 of 15 141 rows, so it contains no access antennas at all.

**Australia, an apparent 137 897 rows above 6 GHz, which is every row.** This is
a units artefact. Australia stores `Frequency` in **Hz** while the European
registers store **MHz**, so a naive `Frequency > 6000` filter passes every
Australian row at 6 kHz and above. Australia's actual maximum is
854 000 000 Hz, that is **854 MHz**. It is the lowest-frequency region in the
database, not the highest.

**What follows.** A height distribution taken from these registers describes
where GSM, UMTS, LTE and sub-6 NR antennas sit. Presenting it as a bound on where
a 15 GHz radio would sit is the same category error this document already caught
once in section 11.2, where 3GPP's UMi value of 10 m was imported into the
above-roofline class, one level up. The registers are not a calibration set for
this study's frequency. **No such calibration set exists**, because the
deployment does not exist.

That is not a gap in the data collection. It is an absence of the deployment
being modelled, and no amount of further register work will close it. Every
height and range cap in this document is therefore an **assumption argued from
site acquisition economics and radio mechanism**, not a calibrated fact. Section
7.5 replaces the citation the caps cannot have with the sensitivity analysis they
require instead.

### 4.4 Height does not vary with frequency, which is why sub-6 heights are still the right prior

The obvious repair would be to find a height-versus-frequency slope in the sub-6
data and project it to 15 GHz. That repair is not available, and the reason it is
not available is more useful than the repair would have been.

Median `CenterHeight` by carrier frequency, within region:

| Region | 0.7 to 1.0 GHz | 1.8 to 2.1 GHz | 2.6 GHz | 3.5 GHz n78 |
| --- | --- | --- | --- | --- |
| Netherlands | 30.0 m | 29.6 m | 30.2 m | **31.8 m** |
| Brussels | 26.8 m | 26.7 m | 27.1 m | **27.8 m** |
| France | 28.0 m | 27.0 m | 26.2 m | no n78 in snapshot |
| Poland | 40.0 m | 40.0 m | 40.0 m | no n78 in snapshot |

The trend is flat, and where it moves at all it moves **up** with frequency. Over
a 5x frequency range the Dutch median shifts by 1.8 m and the Brussels median by
1.0 m, both upward.

Operators are not siting higher bands lower. They are co-siting every band on the
same mast, because the binding constraint is **site acquisition**, not radio.
Getting a roof lease, power and backhaul is the expensive step, and once it is
paid for every band goes on the same steel.

The one region that is not flat does not rescue the extrapolation either. Canada
gives 42.7 m at 0.7 to 1.0 GHz against 36.0 m at 3.5 GHz, but its highest band is
its *lowest* antennas only in the sense that its low band sits on tall rural
coverage towers. The gradient runs the wrong way for anyone wanting to argue that
higher frequencies get sited lower.

**This cuts two ways and both matter.**

It falsifies extrapolation. There is no height-versus-frequency slope to project
out to 15 GHz, at least up to 3.5 GHz, so nobody can infer FR3 heights from sub-6
heights by trend fitting. Any attempt to do so in the paper would be inventing a
gradient the data denies.

It supplies a better reason to use sub-6 macro heights anyway. If FR3 arrives as
an **overlay on existing macro sites**, which flat co-siting across five octaves
is direct evidence for, then the sub-6 macro height distribution is the correct
prior for the macro class. Not because it is the same band, but because it is the
same real estate. That is a much stronger argument than any frequency-matched
citation would have been, and it is available now.

**Its failure mode is clear and should be stated in the paper.** If FR3 needs
densification rather than overlay, the new sites do not appear on the existing
roofs. They appear at street level, on lampposts and facades, and the small cell
class carries them. This is exactly why the study keeps two classes, and it means
the two classes are not merely a modelling convenience: they are the two branches
of the one open question about how FR3 gets deployed. The paper should say so.

The section 3 campaigns sit inside that open question rather than resolving it.
NYU Manhattan at 7 m, Ericsson Kista at 8.5 and 12 m, Nokia Manhattan lampposts
at 8 to 15 m and NYU Brooklyn FR3 at 4 m are research deployments prototyping the
densification branch. They are evidence that the branch is buildable. They are
not evidence that it is what will be built.

One empirical check survives all of this. Section 5 measures a roof p50 of 17.1 m
at Toulouse. Adding the 3 to 5 m mast of section 11.1 gives 20.1 to 21.1 m,
against a database median of 21.1 m within 500 m. The mast convention, which
section 13 lists as uncited, survives its one available test to within a metre.

### 4.5 The two modes are real, the gap between them is not as empty as an earlier draft claimed

An earlier draft of this document reported a sharply bimodal height distribution
with an "exactly zero" 8 to 10 m bin, based on a direct harvest of three city
centres. The larger database does not support the strong form of that claim, and
the correction is worth recording because the weak form still carries the
argument.

Pooled over the six European regions with height coverage, n = 3 459 777:

```
  0 to  4 m    0.34 %          18 to 20 m    5.56 %
  4 to  6 m    0.63 %          20 to 25 m   18.11 %
  6 to  8 m    0.45 %          25 to 30 m   22.78 %
  8 to 10 m    0.68 %          30 to 35 m   17.44 %
 10 to 12 m    1.72 %          35 to 40 m   10.59 %
 12 to 14 m    1.92 %          40 to 50 m    9.30 %
 14 to 16 m    2.77 %          50 m and up   3.13 %
 16 to 18 m    4.57 %

 below 6 m 1.0 %      6 to 18 m 12.1 %      above 18 m 86.9 %
```

The 8 to 10 m bin is 0.68 %, not zero, and the 6 to 18 m band holds 12.1 %
nationally rather than the 2 to 10 % the three-city sample suggested. Per region
the 6 to 18 m share runs 3.8 % (Poland) to 14.6 % (France).

Two extraction paths also disagree on the fractions. At Rotterdam within 2 km the
direct harvest returned n = 4224 with 10.4 % in the 6 to 18 m band, while the
database returns n = 546 with 27.8 %. The row counts differ by a factor of eight,
which means the two are counting different units: the harvest counts one row per
antenna-frequency entry and therefore over-weights sites carrying many bands,
which by 4.4 is most of them. **The database is the correct unit and the harvest
percentages should not be quoted.**

What survives, and is enough:

- A dominant rooftop mode from 18 to 40 m, peaking at 25 to 30 m, holding 87 % of
  European antennas. This is robust across every region and both extraction paths.
- A thin street-level mode below 6 m, 1 % nationally but 3 to 8 % inside dense
  cores, which is where this study's pedestrians are.
- A monotonically thin middle. The 6 to 18 m region is not empty but it is
  sparsely populated relative to its width, and nothing in it looks like a mode.

The two-class structure the study already uses is therefore still supported, and
the reason is a site-acquisition fact rather than a radio one: an operator leases
a roof or it leases a lamppost, and there is not much building stock offering
anything in between in a historic core. That fact does carry across bands, which
is what makes it usable here at all when 4.3 says almost nothing else does.

### 4.6 Morphology, confirmed on deployed data

Section 9 argues that a single global height band is wrong because morphology
varies. Section 4.2 tests that on deployed antennas rather than on rooftops, and
it holds: the four study-site medians run 21.1, 25.8, 28.0 and 32.5 m at 500 m
radius. An 11 m spread across four European historic squares is larger than
either of the two height changes section 12 recommends, which means the choice of
*which city* currently matters more to the source height than any endpoint
argument in this document.

The radius matters too, and it must always be quoted. Krakow's median is 38.0 m
within 250 m and 28.0 m within 500 m, because the immediate centre carries a few
tall sites and the wider grid regresses toward the regional norm. No register
number in the paper should appear without its radius.

### 4.7 What is genuinely missing, which is less than an earlier draft claimed

Four of the eleven sites now have deployed heights (section 4.2). The earlier
draft listed Brussels and Krakow as blocked and they were not: both are in the
database. The remaining gaps, and their status:

1. **Madrid and Barcelona.** Spain is in the database with full frequency
   coverage and zero height coverage. This is a property of the Spanish source,
   not a fetch failure, and no further scraping will fix it.
2. **Milan, Prague, London, New York, Mexico City, Tokyo.** No region covering
   them carries usable access-antenna heights. The UK region is entirely fixed
   links (4.3) and so does not help London.
3. **Every site, at 15 GHz.** This is the gap that matters and section 4.3 shows
   it cannot be closed from registers at all.

The right response to gaps 1 and 2 is not more collection. It is section 9's
per-site conditioning driven by the measured DSMs of section 5, which exist for
all eleven sites, anchored to the four sites where a deployed distribution can
check the DSM-plus-mast construction. The right response to gap 3 is section 7.5.

## 5. Measured rooftop heights at the eleven sites

The study already owns the evidence that matters most here, because the twin
meshes are photogrammetric reconstructions of the eleven sites and a top-down
raycast recovers a digital surface model directly.

Method: for each site's largest double-precision crop (130 m radius for ten
sites, 200 m for Milan), sample a 300 by 300 grid inside the crop disc, cast one
ray straight down from above the bounding box, and take the first hit height
minus the crop-centre ground datum. Statistics are over the built-up part only,
defined as return height above 3 m, which removes the plaza floor.

| Site | Built fraction | Roof p10 | Roof p50 | Roof p90 | Max | Rayleigh gamma | KS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Krakow Rynek Glowny | 0.09 | 3.3 | 4.6 | 8.1 | 50.7 | 5.5 | 0.27 |
| Korenmarkt, Ghent | 0.58 | 6.0 | 13.4 | 17.9 | 63.2 | 10.0 | 0.13 |
| Brussels Grand-Place | 0.76 | 5.9 | 15.4 | 24.6 | 89.5 | 12.0 | 0.07 |
| Madrid Plaza Mayor | 0.69 | 6.7 | 15.5 | 23.0 | 58.6 | 11.7 | 0.11 |
| Toulouse Place du Capitole | 0.73 | 6.9 | 17.1 | 22.2 | 35.1 | 12.0 | 0.18 |
| Prague Staromestske | 0.68 | 8.2 | 18.6 | 25.1 | 71.6 | 13.5 | 0.18 |
| London Trafalgar Square | 0.73 | 5.0 | 19.2 | 30.3 | 74.7 | 14.6 | 0.09 |
| Tokyo Hachiko | 0.72 | 4.9 | 20.0 | 46.8 | 230.1 | 34.4 | 0.38 |
| Mexico City Zocalo | 0.59 | 7.7 | 21.4 | 27.2 | 62.5 | 14.6 | 0.17 |
| Milan Piazza del Duomo | 0.58 | 13.4 | 26.7 | 34.7 | 108.9 | 19.6 | 0.19 |
| New York Times Square | 0.60 | 14.0 | 39.8 | 178.0 | 222.8 | 72.1 | 0.38 |

All heights in metres above local ground. `gamma` is the maximum-likelihood
Rayleigh parameter under P.1410-5 eq. (17), `KS` the Kolmogorov-Smirnov distance
of the measured CDF from that Rayleigh.

Read this as follows.

- **The median roofline of the eight European and Latin American historic cores
  spans 13.4 to 26.7 m.** Add a rooftop mast and the antenna sits somewhere near
  17 to 31 m above ground. The current macro band's floor of 15 m is at the very
  bottom of that and its ceiling of 45 m is above every one of those eight
  sites' roof p90.
- **Times Square and Hachiko are a different population, not a tail of the same
  one.** Times Square's roof p90 is 178 m, six times Milan's. Any single global
  band that contains Times Square is grossly wrong for Ghent and vice versa.
- **The Rayleigh form of P.1410-5 fits the historic cores and fails the
  high-rise sites.** KS runs 0.07 to 0.19 for the eight mid-rise sites and 0.38
  for both Times Square and Hachiko, where the true distribution is bimodal
  (low podium plus towers). Krakow at KS 0.27 fails for a third reason: at 0.09
  built fraction the 130 m crop is almost entirely open plaza and the sample is
  small and unrepresentative.

Caveats, and they are real. The DSM is a photogrammetric mesh, so trees and
awnings are counted as roof. The crop is 130 m and the macro band reaches to
250 m, so this measures the near field of the morphology rather than the whole
source region. The ground datum is a single crop-centre value, so sloping sites
bias the tails. And a rooftop being present is not the same as a rooftop being
used, which no measurement in this repository can settle.

## 6. Where the illumination weight can actually be used

A separate raycast measures, at head height, the fraction of azimuth that is
open sky as a function of elevation. This is `f_open(el)` in the sense of
`MONOSTATIC_SBR.md` section 9.3, computed at the crop centre with 720 azimuths
per elevation.

| Site | 1 deg | 3 deg | 5 deg | 10 deg | 15 deg | 20 deg | 30 deg | 45 deg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Brussels Grand-Place | 0.00 | 0.00 | 0.00 | 0.00 | 0.05 | 0.25 | 0.62 | 0.93 |
| Korenmarkt | 0.04 | 0.03 | 0.03 | 0.06 | 0.12 | 0.23 | 0.49 | 0.78 |
| Krakow Rynek | 0.17 | 0.60 | 0.73 | 0.86 | 0.93 | 0.96 | 0.99 | 1.00 |
| London Trafalgar | 0.00 | 0.00 | 0.00 | 0.10 | 0.58 | 0.92 | 0.98 | 0.98 |
| Madrid Plaza Mayor | 0.00 | 0.00 | 0.00 | 0.00 | 0.07 | 0.66 | 0.85 | 1.00 |
| Mexico Zocalo | 0.00 | 0.00 | 0.00 | 0.22 | 0.57 | 0.85 | 0.99 | 0.99 |
| Milan Duomo | 0.02 | 0.04 | 0.04 | 0.15 | 0.32 | 0.53 | 0.84 | 0.95 |
| New York Times Square | 0.12 | 0.16 | 0.17 | 0.20 | 0.21 | 0.22 | 0.26 | 0.44 |
| Prague Staromestske | 0.00 | 0.00 | 0.00 | 0.14 | 0.34 | 0.63 | 0.90 | 1.00 |
| Tokyo Hachiko | 0.00 | 0.00 | 0.00 | 0.04 | 0.18 | 0.23 | 0.48 | 1.00 |
| Toulouse Capitole | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

A run over 21 to 25 head positions spread on rings at 0, 15, 30 and 45 m gives
the same picture (below 10 degrees, open fraction under 0.15 everywhere except
Krakow), with the caveat that some ring positions land inside building
footprints and bias the mean down.

The point of the table is not the tracer, which handles blockage correctly
without help. The point is that **the low-elevation region where the
`1/sin^3(el)` weight concentrates its mass is the region where these scenes have
almost no sky**. Any change to the elevation law that moves mass across the
5 to 20 degree range is a first-order change to the published `chi_rooftop`,
because that is exactly where `f_open` goes from 0.00 to 0.6. Section 7.3
measures how large that is.

Toulouse Place du Capitole returns 0.00 open at every elevation up to 45 degrees
and a whole-sphere sky fraction of 0.069. That site's crop centre appears to sit
under cover. It is excluded from the ratio statistics below and should be looked
at independently.

## 7. What the numbers do to the answer

### 7.1 The elevation law as coded is not the mixture the bands describe

`MONOSTATIC_SBR.md` section 2.7 already records that the height band and the
elevation law are two different models and that the code evaluates the law.
Expressed as a CDF over elevation, the gap is large. Under the honest mixture,
with `Delta_h` drawn from a band and `d` uniform by area on a **fixed** range
annulus, the elevation density is

```
N(el) proportional to  cos(el)/sin^3(el) * [ G(d_max tan el) - G(d_min tan el) ]
G(x) = integral from 0 to x of f(h) h^2 dh
```

which recovers the pure `cos/sin^3` law exactly on
`[atan(h_max/d_max), atan(h_min/d_min)]` and rolls off outside it to the stated
support `[atan(h_min/d_max), atan(h_max/d_min)]`. For the macro numbers the pure
law holds only between 9.9 and 28.4 degrees, and the roll-off covers 3.1 to 9.9
and 28.4 to 60.1 degrees. Under the pure law almost two thirds of the weight
sits below 5 degrees, which is inside the lower roll-off, so the roll-off is not
a correction at the edges. It is where nearly all of the mass is.

| Macro model | below 5 deg | below 10 deg | below 20 deg | median | p90 |
| --- | --- | --- | --- | --- | --- |
| Pure law on [3.1, 60.1] deg, as coded | 0.620 | 0.907 | 0.979 | 4.36 deg | 9.65 deg |
| Honest mixture, `f` uniform on [13.5, 43.5] | 0.094 | 0.549 | 0.902 | 9.50 deg | 19.84 deg |
| Honest mixture, `f` lognormal median 18 m, sigma 0.35 | 0.228 | 0.764 | 0.952 | 6.80 deg | 14.77 deg |

| Small cell model | below 3 deg | below 5 deg | below 10 deg | median | p90 |
| --- | --- | --- | --- | --- | --- |
| Pure law on [0.95, 33] deg, as coded | 0.899 | 0.964 | 0.992 | 1.35 deg | 3.01 deg |
| Honest mixture, `f` uniform on [2.5, 6.5] | 0.654 | 0.879 | 0.973 | 2.50 deg | 5.49 deg |

The coded law puts the median arrival 5.1 degrees lower than the band it is
documented with, for macro, and 1.2 degrees lower for small cells.

### 7.2 Both bands are more sensitive to the range cap than the height cap

Holding the other band fixed and sweeping, under the honest mixture:

| Macro range cap `d` | below 5 deg | below 10 deg | median |
| --- | --- | --- | --- |
| 25 to 150 m | 0.000 | 0.182 | 15.43 deg |
| 25 to 250 m | 0.094 | 0.549 | 9.50 deg |
| 25 to 400 m | 0.351 | 0.825 | 5.99 deg |
| 25 to 800 m | 0.820 | 0.956 | 3.01 deg |

| Macro height band `Delta_h` | below 5 deg | below 10 deg | median |
| --- | --- | --- | --- |
| 8.5 to 18.5 m | 0.608 | 0.911 | 4.44 deg |
| 10.5 to 28.5 m | 0.274 | 0.798 | 6.48 deg |
| 13.5 to 43.5 m | 0.094 | 0.549 | 9.50 deg |
| 13.5 to 100 m | 0.033 | 0.190 | 18.63 deg |

Changing `d_min` from 25 to 50 m or 10 m barely moves anything (median 9.34 and
9.54 degrees against 9.50). Only `d_max` matters. The range cap, which is the
number with the weakest evidence, is at least as influential as the height band,
which is the number with the strongest. That ordering is uncomfortable and is
the main reason section 8 derives the cap rather than asserting it.

### 7.3 How much of this reaches the published number

Combining the measured `f_open(el)` of section 6 with the elevation laws gives a
zero-bounce susceptibility proxy `K0 = integral of f_open(el) Q(el) dOmega`,
which bounds the direct-path part of `chi`. Over the ten sites excluding
Toulouse:

| Comparison | min | median | max | median in dB |
| --- | --- | --- | --- | --- |
| Macro: honest mixture over pure law as coded | 1.15 | 4.47 | 4.82 | +6.5 dB |
| Small cell: honest mixture over pure law as coded | 0.94 | 2.58 | 3.15 | +4.1 dB |
| Macro: band [8.5, 33.5] over band [13.5, 43.5], both mixed | 0.51 | 0.56 | 0.94 | -2.5 dB |
| Small cell: band [3, 10] over band [2.5, 6.5], both mixed | 1.07 | 2.44 | 3.21 | +3.9 dB |

Put that next to the result the study reports. In the 250 m run, the site-median
`chi_rooftop` runs from 0.0251 (Brussels) to 0.7052 (Krakow), a 14.5 dB spread,
but Krakow is an open-plaza outlier and the other ten sites span 0.0251 to 0.0981,
which is **5.9 dB**. A 6.5 dB median shift from changing the elevation law is
therefore **larger than the entire cross-city spread among ten of the eleven
sites**. The illumination model is not a boundary condition on the headline
result, it is comparable in size to the result.

Two things keep this from being a verdict.

The proxy covers the zero-bounce term only. The full `chi` includes multipath,
which is far less elevation-selective, and the evidence that multipath carries
most of `chi` here is in the table itself: Toulouse has an `f_open` of 0.00 below
45 degrees and still reports `chi_rooftop` = 0.0981, the second highest of the
eleven. So the true sensitivity is smaller than 6.5 dB, probably by a lot.

Bounding it properly needs a re-weighting run against the stored `K_S`, which the
current `*_spectra.npz` files cannot support: they store `rho_rooftop` with the
illumination already folded in, for three locations.

### 7.4 The re-weighting run, measured

That run has since been done, so 7.3's proxy can be replaced with the real
number. The corrected band mixture of 11.4 was implemented and the study re-run
at Korenmarkt over 120 walk locations on the 130 m crop, holding the geometry
and the tracer fixed so that only the illumination weight changes.

| Quantity | Old law | Corrected mixture | Median change | Spread p95/p05 |
| --- | --- | --- | --- | --- |
| `chi_rooftop` | 0.1472 | 0.2355 | **+2.04 dB** | 12.45 to **8.44 dB** |
| `chi_rooftop_direct` | 0.0975 | 0.1616 | +2.19 dB | 13.52 to **9.06 dB** |
| `chi_street_small_cell` | 0.0675 | 0.0983 | +1.64 dB | 18.48 to 16.62 dB |
| `multipath_gain_rooftop` | 1.487 | 1.500 | +0.04 dB | 2.75 to 2.22 dB |
| `chi_isotropic` | 0.3360 | 0.3360 | +0.00 dB | 3.85 to 3.85 dB |

`sky_fraction`, `mean_bounces`, `escaped_fraction`, `mean_excess_delay_ns` and
`chi_isotropic` are bit-identical across the pair, which is the control: the
isotropic model has no elevation weighting to correct, so anything that moved in
its column would have been a harness artefact. Nothing moved.

**Two corrections to 7.3 follow, and the first is against this document's own
argument.** The zero-bounce proxy said 6.5 dB. The measured full effect on
`chi_rooftop` is **2.04 dB**, so the proxy overstates it by about 4.5 dB, in the
direction 7.3 predicted but by more than 7.3 allowed for. The mechanism is
visible in the table: `multipath_gain_rooftop` barely moves at 0.04 dB, so the
correction acts almost entirely on the direct term, and the multipath term
dilutes it. The claim in 7.3 that the illumination model is "comparable in size
to the result" is therefore **too strong**. At 2.04 dB against a 5.9 dB
cross-city spread it is a third of the spread, which is a serious systematic and
not a rival to the result.

The second correction is more interesting, and it was not predicted at all.
**The correction narrows the location-to-location spread by 4 dB**, from 12.45
to 8.44 dB across the 120 walk locations. The old law was not merely biased low,
it was differentially wrong across locations, hardest at the ones where the
sky is most restricted. Section 9 argues that a wrong `Q_S` distorts spread as
well as level and could only assert the sign. This measures it, at one site, and
the sign holds.

Caveat on scope: one site, 120 locations, 130 m crop.

**Update, cross-city, partial.** The cross-city version is running and five of
eleven sites have landed, at the study's actual **250 m crop** with 80 locations
and 200 000 rays. Old and new law are evaluated on the same rays at each site, so
the level difference carries no Monte Carlo noise.

| Site | `chi_rooftop` old | new | Rooftop law shift | Small cell |
| --- | --- | --- | --- | --- |
| Ghent Korenmarkt | 0.0478 | 0.1621 | **+5.30 dB** | +4.36 dB |
| London Trafalgar | 0.0774 | 0.2871 | **+5.69 dB** | +3.59 dB |
| Mexico Zocalo | 0.0825 | 0.2985 | **+5.59 dB** | +4.09 dB |
| Milan Duomo | 0.0785 | 0.2465 | **+4.97 dB** | not yet read |
| Krakow Rynek | 0.7159 | 0.8978 | **+0.98 dB** | +2.48 dB |

Three things, all of which matter more than anything in sections 9 to 11.

**The 130 m figure understated it.** At the 250 m crop the Korenmarkt shift is
+5.30 dB against +2.04 dB at 130 m. The correction grows with the crop because a
larger crop admits more low-elevation geometry, which is exactly where the two
laws differ most. **The headline configuration is the 250 m one**, so +5.3 dB is
the number that applies to the published result, not +2.0 dB.

**The shift is strongly site-dependent, and in the direction section 9
predicted.** Krakow, the open plaza with 0.09 built fraction, moves +0.98 dB. The
four canyon sites move +4.97 to +5.69 dB. The law error is small where the sky is
open and large where it is not, which is the same morphology dependence section
7.5 finds for the range cap.

**It compresses the cross-site spread by 4.3 dB.** Across these five sites the
spread of `chi_rooftop` falls from **11.75 dB to 7.43 dB** when the law is
corrected. Section 13 item 9 lists "a fixed global `Q_S` compresses the measured
cross-city spread" as an argument whose sign was sound but whose magnitude was
unmeasured. It is now measured on four sites and the magnitude is large: roughly
a third of the reported spread is an artefact of the elevation law. If this holds
over the remaining seven sites, **the paper's cross-city spread figure has to be
recomputed before it is published**, and that is the single most consequential
finding in this document.

Treat these five numbers as provisional until all eleven land. The run was still
adding sites when this document was written, and every site added so far has
fallen inside the pattern above.

### 7.5 The sensitivity analysis that replaces the citation the caps cannot have

Section 4.3 establishes that no deployed FR3 cellular base station exists in any
register, so the range cap and the height band cannot be cited. They can only be
assumed. An assumption that cannot be cited has to be reported as a sensitivity
instead, and this subsection is that report. **It should be the centrepiece of
how the paper handles deployment geometry.**

The statistic is the zero-bounce susceptibility proxy
`K0 = integral of f_open(el) Q(el) dOmega` of section 7.3, evaluated per site on
the measured `f_open(el)` of section 6, with the macro band mixture. It is a
proxy rather than `chi`, and section 7.4 shows proxies overstate, so read the
columns as relative leverage rather than as predicted `chi` shifts.

**Range cap, across its defensible span.** `d_min` = 25 m throughout.

| Site | 100 m | 150 m | 250 m | 400 m | span |
| --- | --- | --- | --- | --- | --- |
| Brussels Grand Place | 0.3042 | 0.1817 | 0.0753 | 0.0302 | 10.0 dB |
| Madrid Plaza Mayor | 0.5877 | 0.3716 | 0.1498 | 0.0583 | 10.0 dB |
| Tokyo Hachiko | 0.2635 | 0.1677 | 0.0840 | 0.0398 | 8.2 dB |
| Toulouse Capitole | 0.2813 | 0.2128 | 0.1093 | 0.0450 | 8.0 dB |
| Prague Staromestske | 0.6073 | 0.4359 | 0.2271 | 0.0993 | 7.9 dB |
| London Trafalgar | 0.7767 | 0.5907 | 0.3051 | 0.1333 | 7.7 dB |
| Mexico Zocalo | 0.4198 | 0.3315 | 0.1794 | 0.0751 | 7.5 dB |
| Milan Duomo | 0.6187 | 0.4465 | 0.2368 | 0.1122 | 7.4 dB |
| Ghent Korenmarkt | 0.1463 | 0.0928 | 0.0524 | 0.0332 | 6.4 dB |
| New York Times Square | 0.1571 | 0.1345 | 0.1171 | 0.1065 | 1.7 dB |
| Krakow Rynek | 0.9511 | 0.9233 | 0.8818 | 0.8276 | 0.6 dB |

Relative to the 250 m default, median over the eleven sites: **+4.2 dB at 100 m,
+2.8 dB at 150 m, -3.6 dB at 400 m.** The defensible span of the cap is therefore
worth about **7.8 dB** on the headline susceptibility.

**Height band, at a fixed 250 m cap**, ratio to the current [13.5, 43.5]:

| Band, above head | Median ratio | Range over sites |
| --- | --- | --- |
| [16.5, 38.5], section 11.2 recommendation | 0.85x, **-0.7 dB** | 0.81 to 0.99 |
| [8.5, 33.5], the superseded earlier draft | 0.63x, -2.0 dB | 0.56 to 0.97 |
| All mass at the floor, not defensible | 0.17x, -7.8 dB | 0.11 to 0.85 |
| All mass at the ceiling, not defensible | 1.50x, +1.8 dB | 1.03 to 1.66 |

**The comparison is the point.** Moving the range cap across its defensible span
is worth 7.8 dB. Moving the height band across its defensible span is worth 0.7
to 2.0 dB. The height band would need to be collapsed to a delta function, which
no one proposes, before it reached the leverage the range cap has by default.
This is the same ordering section 10.1 found in degrees of arrival elevation,
18.2 against under 1, now expressed in the quantity the paper actually reports.

So the paper should:

1. Report `chi` at 150, 250 and 400 m as a published sensitivity band, not pick
   250 m and cite nothing. The cap is an assumption and this is what an honest
   assumption looks like in a results table.
2. State the height band as low leverage and stop arguing about it. Sections 10
   and 11 argue the shape question at length and the answer is that it is worth
   under a decibel.
3. Fix the law-versus-band inconsistency first regardless, since section 7.4
   measures it at +2.04 dB and 4 dB of spread, which is real and is free to
   correct.

**One structural observation, which is new.** The per-site spans run from 0.6 dB
at Krakow to 10.0 dB at Brussels and Madrid. The range cap barely matters in an
open plaza, where the sky is visible at every elevation and moving the sources
around changes little, and it matters enormously in a deep canyon, where the
source elevation determines whether anything is visible at all. **The
illumination assumption is not a uniform uncertainty across the study, it is
concentrated in exactly the deep-canyon sites.** Since deep canyons are also
where the study reports its lowest `chi`, the sites carrying the most
interpretive weight are the ones whose illumination model is least constrained.
That belongs in the paper's limitations, and it is a stronger statement than any
of the endpoint arguments this document spent its length on.

## 8. Deriving the range cap instead of asserting it

The range cap is the number the task called weakest, and it is. No source
anywhere states "sources beyond 250 m do not matter". What can be derived is
the fraction of the incident power that a cap at `D` discards.

For a uniform areal density of sites, the incoherent sum over a ring at range
`r` weights as `2 pi r P_rx(r)`, so the tail fraction beyond `D` is

```
tail(D) = integral from D to infinity of r P_rx(r) dr
        / integral from d_min to infinity of r P_rx(r) dr
```

Evaluating `P_rx` with the 3GPP TR 38.901 UMi-street canyon pathloss (Table
7.4.1-1) and LOS probability (Table 7.4.2-1) at 15 GHz, `h_UT = 1.5 m`:

| `D` | LOS/NLOS mix | LOS only | NLOS only |
| --- | --- | --- | --- |
| 100 m | 0.184 | 0.624 | 0.130 |
| 130 m (the crop radius) | 0.129 | 0.556 | 0.087 |
| 150 m | 0.107 | 0.520 | 0.070 |
| 250 m (the current cap) | 0.055 | 0.394 | 0.032 |
| 400 m | 0.029 | 0.284 | 0.016 |
| 800 m | 0.008 | 0.131 | 0.005 |

with `h_BS = 25 m` and `d_min = 25 m`. For the small cell case, `h_BS = 6 m` and
`d_min = 10 m`:

| `D` | LOS/NLOS mix |
| --- | --- |
| 75 m | 0.128 |
| 100 m | 0.085 |
| 150 m (the current cap) | 0.048 |
| 200 m | 0.031 |
| 300 m | 0.017 |

Three readings.

**The two current caps are consistent with each other.** 250 m for macro
truncates 5.5 % of the mixed-statistics power and 150 m for small cells
truncates 4.8 %. Whoever picked them picked a common 5 % criterion, whether or
not that was the intent. Stating the criterion converts two arbitrary numbers
into one stated choice, which is a real improvement even though the numbers do
not change.

**Under LOS-dominated statistics the cap is not innocuous.** If the far field
is line of sight rather than 3GPP-mixed, a 250 m cap discards 39 % of the power,
because the LOS exponent of about 2.1 makes the ring integral only marginally
convergent. Under free space it does not converge at all. The mixed number
relies on the UMi LOS probability `18/d + exp(-d/36)(1 - 18/d)` falling as
roughly `1/d`, and that probability is calibrated for `h_BS = 10 m` below the
roofline. A macro above the roofline in an open square sees more LOS than UMi
predicts, so **5.5 % is a lower bound on the truncation and 39 % is the upper
bound**. This should be stated in the paper rather than smoothed over.

**The 130 m crop is a worse truncation than the 250 m cap.** At `D = 130` m the
mixed tail is 12.9 %. `MONOSTATIC_SBR.md` section 9.4 already calls the crop
radius the largest hole in the design, and this is the same statement in power
rather than in measure: the scene is truncated harder than the source model is.

The same computation with ITU-R P.1411-13's own measured distance exponents,
which are independent of 3GPP, gives the same picture with a wider spread. Using
a pure power law `r^-alpha` so the tail beyond `D` is `(D/d_min)^-(alpha-2)`:

| P.1411-13 case | alpha | Tail beyond the relevant cap |
| --- | --- | --- |
| Above-rooftop LoS, Table 8 | 2.29 | 0.513 at `D` = 250 m |
| Above-rooftop NLoS urban high-rise, Table 8 | 4.39 | 0.004 at `D` = 250 m |
| Below-rooftop LoS, Table 4 | 2.07 | 0.827 at `D` = 150 m |
| Below-rooftop NLoS urban high-rise, Table 4 | 3.73 | 0.009 at `D` = 150 m |
| Below-rooftop NLoS urban low-rise, Table 4 | 4.52 | 0.001 at `D` = 150 m |

So the LOS-versus-NLOS split, not the cap, is what decides whether the cap
matters. Both bounds are wider than the 3GPP ones because P.1411's measured NLoS
exponents (3.73 to 4.52) are steeper than 3GPP UMi NLOS (3.53) while its LoS
exponents (2.07 to 2.29) are shallower.

Independent support for the two caps as deployment statements rather than
propagation ones:

- ITU-R P.1411-13 Table 3 gives micro-cell (above roof-top) a **cell radius of
  0.05 to 1 km** and dense urban micro-cell (below roof-top) **0.05 to 0.5 km**.
  Both current caps sit inside their respective ranges, macro at 250 m in
  [50, 1000] and small cell at 150 m in [50, 500].
- ITU-R P.1411-13 Table 4 gives the site-general below-rooftop NLoS urban
  low-rise model a measured validity of **10 to 250 m**, which brackets the small
  cell band exactly and the macro band's far edge.
- The dense urban macro-layer ISD is 200 m in TR 38.802 Table A.2.1-1, TR 38.820
  Table 5.6.5-1 and M.2412-0 Table 5 b), and TR 38.901 Table 7.2-1 gives the same
  200 m for UMi, with TR 38.808 using 150 m and 100 m for the mmWave dense urban
  cases. A 200 m ISD
  hexagonal layout has a cell outer radius of 200/sqrt(3) = 115 m, so a 250 m cap
  reaches roughly the second tier of sites, which is the right scale for an
  exposure sum that must include non-serving sites.
- 3GPP dense urban micro spacing is 25 to 58 m (TR 38.802 Table A.2.1-9),
  so a 150 m small-cell cap reaches two to six tiers of micro sites.

## 9. Opinion: one global band, or condition on morphology

**Condition on morphology.** Three independent lines say so and they agree.

**The standards themselves do.** TR 38.901 clause 6.2 and ITU-R P.1411-13
Table 3 both define the deployment class by position relative to the average
roofline, and hang metre values off that definition as examples. A single global
metre band inverts the standards' own logic: it fixes the derived quantity and
lets the defining one float. The right primitive is `h_site = h_roof + m` for
above-roofline sites and `h_site` capped below `h_roof` for below-roofline ones,
with `h_roof` taken from the site's own measured distribution. Section 5 already
provides that distribution for all eleven sites at no extra cost.

**The measured spread is too large for one band.** Median roofline runs 13.4 m
(Korenmarkt) to 39.8 m (Times Square), and roof p90 runs 8.1 m to 178 m. Feeding
each site's own measured rooftop DSM plus a 4 m mast into the fixed 25 to 250 m
annulus gives:

| Site | Roof p50 | below 5 deg | below 10 deg | median elevation | p90 |
| --- | --- | --- | --- | --- | --- |
| Krakow Rynek | 4.6 m | 0.836 | 0.960 | 2.53 deg | 6.54 deg |
| Korenmarkt | 13.4 m | 0.479 | 0.871 | 5.12 deg | 11.23 deg |
| Brussels Grand-Place | 15.4 m | 0.372 | 0.818 | 5.94 deg | 13.11 deg |
| Madrid Plaza Mayor | 15.5 m | 0.355 | 0.825 | 5.96 deg | 12.91 deg |
| Toulouse Capitole | 17.1 m | 0.302 | 0.817 | 6.15 deg | 13.15 deg |
| Prague Staromestske | 18.6 m | 0.232 | 0.772 | 6.78 deg | 14.60 deg |
| London Trafalgar | 19.2 m | 0.295 | 0.740 | 6.97 deg | 15.53 deg |
| Mexico Zocalo | 21.4 m | 0.234 | 0.738 | 7.24 deg | 15.54 deg |
| Tokyo Hachiko | 20.0 m | 0.300 | 0.608 | 8.23 deg | 24.73 deg |
| Milan Duomo | 26.7 m | 0.098 | 0.564 | 9.30 deg | 20.02 deg |
| New York Times Square | 39.8 m | 0.099 | 0.335 | 15.96 deg | 51.80 deg |
| Global band [13.5, 43.5] uniform | n/a | 0.094 | 0.549 | 9.50 deg | 19.84 deg |

The median arrival elevation spans 2.5 to 16.0 degrees across sites, a factor of
6.3, against a single global value of 9.5 degrees. Ten of the eleven sites come
out **below** the global band's median, Times Square being the only exception,
because the global band's ceiling of 43.5 m is above the roofline of every
historic core in the set. The global band
is not a compromise between the sites, it is close to the worst of them and
biased high for most.

That last point deserves emphasis because it is the paper's own quantity. The
`MONOSTATIC_SBR.md` argument is that essentially all the cross-city exposure
spread has to live in `K_S`, since the body-side coupling `F` moves only 18 %.
But if `Q_S` is held global while the true `Q_S` varies by a factor of 6 in
median elevation and that variation is **correlated with the morphology that
drives `K_S`**, then a fixed `Q_S` does not merely add noise. It systematically
compresses the spread it is trying to measure. Tall-building sites get a
too-low illumination elevation, low-building sites get a too-high one, and both
errors push `chi` toward the middle.

**Is the height cap radio or regulatory?** The task asks and the honest answer
is: mostly radio, and the radio mechanism shapes the distribution rather than
just clipping it.

The regulatory ceiling is not binding at these heights. Nothing stops an
operator from mounting on a tall building, and section 4 records what the rules
actually cap. What binds is a set of radio and engineering costs that all grow
with height:

1. **The vertical span a sector must cover grows with height.** Serving
   `d` in [25, 250] m needs an elevation range of `atan(h/25) - atan(h/250)`:
   19.5 degrees at `h = 10` m, 34.1 at 20 m, 50.2 at 43.5 m, 54.2 at 100 m. A
   mmWave or FR3 panel has limited elevation scan and loses gain toward the scan
   edges, so a high site either accepts a large scan loss or gives up the near
   part of its own footprint.
2. **The cell-edge depression grows with height, and in a dense core the
   depressed footprint is roofs.** At `h = 43.5` m and a 250 m cell edge, the
   edge sits at 9.9 degrees below horizontal. At `h = 100` m it is 21.8 degrees.
   A sector antenna downtilted to 22 degrees in a core with 0.6 to 0.76 built
   plan fraction (section 5) puts most of its main lobe on roofs, not on
   pedestrians. The built fraction is measured here and is the reason the
   mechanism bites in these particular scenes.
3. **Overshoot into neighbouring cells grows with height,** because the
   horizon-grazing upper edge of the main lobe travels further before it meets a
   roofline. This is standard cellular engineering rather than anything specific
   to this study, and no citation was found that puts a number on it at FR3, so
   it is listed as reasoning in section 13.

**What that implies for the shape, not just the endpoints.** All three
mechanisms are continuous and monotone in height rather than being a wall at
some metre value. So the correct statement is not "the band ends at `h_max`", it
is that **the deployment weight decays above the local roofline** rather than
being cut off there. That argues for a distribution with a mode near
`h_roof + mast` and a decaying upper tail, which is exactly the Rayleigh shape
P.1410-5 fits to rooftop heights, and against a uniform band with a hard ceiling.
The endpoint is the wrong object to argue about.

## 10. Opinion: is a uniform height distribution defensible

**As a description of reality, no.** Four arguments, in decreasing strength.
**As an input to this integral it turns out to be adequate**, which is not what
the four arguments predict, so read 10.1 before acting on them.

**The measured deployed height distribution is bimodal with a long tail.**
Section 3.4 pools every stated elevated site height from the campaign
literature and finds a lamppost and low-facade mode at 4 to 8 m, a low-rooftop
mode at 14 to 25 m carrying most of the mass, and a sparse tail from 33 to 62 m.
The best-resolved single list, Nokia's twelve Manhattan streets (Chizhik, Du,
Valenzuela, IEEE TAP 2021, arXiv:2111.01758 Table 1), is **14, 15, 15, 15, 15,
15, 15, 20, 20, 20, 22, 56 m**: seven of twelve inside a 1 m window, four in a
second cluster at 20 to 22 m, one outlier at 56 m. A uniform draw over any band
wide enough to contain that list would be flatter than reality by a very large
factor. This is measurement, not modelling, and it is the strongest evidence in
the document on the shape question.

**The one primary source that speaks to the shape agrees.**
ITU-R P.1410-5 eq. (17) models rooftop height as Rayleigh, fitted to measured
rooftop CDFs. A Rayleigh has a mode and a decaying tail. Nothing in any standard
proposes a uniform building or antenna height distribution.

**The measured rooftop distributions at the study's own sites are not
uniform, and are Rayleigh-compatible where the morphology is homogeneous.**
Section 5: KS distance from the ML Rayleigh runs 0.07 to 0.19 across the eight
mid-rise sites, and 0.38 at both high-rise sites where the distribution is
bimodal. So the recommendation is Rayleigh for mid-rise cores and an explicitly
two-component form, or a per-site empirical DSM, for high-rise ones.

**Uniform-in-`h` is not neutral, it is tall-weighted.** The number of sites seen
at a given elevation carries a `Delta_h^2` factor (`MONOSTATIC_SBR.md` section
2.7). Under a fixed range annulus the *total* site count per height is
independent of `Delta_h`, because the `Delta_h^2` cancels against the shrinking
elevation support, but at any elevation where the whole band is in support the
`Delta_h^2` is uncancelled and sites in the top third of the band by height
contribute 56 % of the weight. That is the middle window of section 7.1, 9.9 to
28.4 degrees. A uniform band on [13.5, 43.5] has a mean of 28.5 m but
an RMS of 29.8 m and an `h^2`-weighted mean height of 33.3 m, well above every
measured roofline in the European set. If the true `f(h)` decreases above the
roofline, which sections 5 and 9 both say it does, then uniform is wrong in the
direction of over-weighting tall sites, and the `h^2` factor amplifies that
error rather than cancelling it.

Quantified in section 7.1: swapping uniform on [13.5, 43.5] for a lognormal of
median 18 m moves the median arrival elevation from 9.50 to 6.80 degrees and
raises the mass below 5 degrees from 0.094 to 0.228.

### 10.1 A correction to the four arguments above, from measured data

The four arguments are about whether uniform *describes* deployment. They are
right, and section 4.5 settles the descriptive question on 3.46 million deployed
antennas rather than fifty campaign entries. But the question that matters for
this paper is different: does the shape of `f(h)` change the answer? The
lognormal comparison above was a hypothetical. Section 4 supplies the real
`f(h)`, so the comparison can be done properly, and it gives a different verdict
from the one the `h^2` argument suggests.

Drawing `d` with uniform areal density on [25, 250] m and weighting by `h^2`,
with `f(h)` taken from the 3 007 343 database antennas at or above 18 m:

| `f(h)`, above head | Median arrival elevation |
| --- | --- |
| Uniform on [13.5, 43.5], current | 10.88 deg |
| **Pooled database macro, measured (section 4.5)** | **11.30 deg** |
| Uniform on [16.5, 38.5], proposed in 11.2 | 9.85 deg |

**The current uniform band reproduces the measured elevation distribution to
within 0.42 degrees.** The reason is visible in the moments: the pooled database
macro population has an `h^2`-weighted mean of 35.3 m above head against 33.3 m
for the current uniform band, and `E[h^2]` differs by 0.29 dB. The measured
distribution is peaked near where the uniform band's `h^2` centroid already sits,
so the `h^2` factor that makes shape look dangerous also makes these two
particular distributions nearly equivalent.

An earlier draft ran this comparison on the direct harvest instead and got
10.24 degrees, that is 0.64 degrees on the other side of the uniform band. The
two extraction paths therefore **bracket** the current band, one 0.64 degrees
below and one 0.42 degrees above. That disagreement is itself the strongest
statement available here: the shape question cannot even be resolved to the
precision at which it would start to matter, and it does not matter at that
precision either.

Shape has leverage in principle. Concentrating all mass at the band floor gives a
median elevation of 4.35 degrees and all mass at the ceiling gives 13.76, a span
of 9.4 degrees. But between *defensible* shapes the span is under 1 degree. The
range cap, over its own defensible span, moves the same statistic much further:

| `d_max`, macro | Median arrival elevation |
| --- | --- |
| 100 m | 25.10 deg |
| 150 m | 17.62 deg |
| 250 m, current | 10.89 deg |
| 400 m | 6.87 deg |

The same holds for the small cell class, where `d_max` from 50 to 250 m moves the
median from 8.15 to 1.67 degrees while the whole height band from floor to
ceiling moves it only from 1.35 to 3.50.

**So the honest answer to "is uniform defensible" is split.** As a description of
deployment, no, and section 4.5 is the evidence. As an input to this particular
integral, yes, and the cost of keeping it is under 1 degree of median elevation
and about 0.5 dB in `E[h^2]`. The premise that the `h^2` weighting makes `f(h)`
consequential is correct in the abstract and does not survive contact with the
measured distribution, because `h` spans a factor of 3.2 across the band while
`d` spans a factor of 10, and the range spread dominates.

The practical consequence is a reordering. The shape of `f(h)` is a second-order
correction worth making for realism. The range cap and the law-versus-band
inconsistency of section 7.1, worth 6.5 dB, are where the uncertainty actually
lives, and they should be fixed first.

## 11. Recommendation

### 11.1 Primary recommendation: define the classes against the local roofline

Replace the two global metre bands with a roofline-relative definition, which is
what both 3GPP and ITU-R actually use, and let the metres fall out of each site's
measured DSM.

**Above-roofline class (currently "macro rooftop").**

```
h_site = h_roof + m,   h_roof ~ site's own measured rooftop DSM (section 5)
                       m      = rooftop mast, 3 to 5 m
Delta_h = h_site - 1.5 m
```

**Below-roofline class (currently "street small cell").**

```
h_site in [4, 8] m above ground, truncated above at min(h_roof)
Delta_h = h_site - 1.5 m
```

The truncation matters: "below rooftop" is the defining property, so at a site
whose lowest buildings are 6 m the class cannot reach 8 m.

Where a register covers the site, prefer it to the DSM-plus-mast construction
for the above-roofline class. Section 4.2 gives measured antenna heights at four
of the eleven sites, and section 11.3 notes that at Toulouse the two constructions
agree to within 1 m while the pooled register median sits 9 m above the generic
DSM-plus-mast estimate. The register measures antennas. The DSM infers them.

Each site then reports its own elevation support and its own `Q_S`, and the
cross-city comparison becomes a comparison of `K_S` under a `Q_S` that is
correct for each city rather than a comparison contaminated by a `Q_S` that is
wrong for all of them in a morphology-correlated direction (section 9).

### 11.2 Fallback: a single global band, if one is required

If the paper needs one band for all sites, these are the defensible numbers.

| Class | Recommended, above head | Recommended, above ground | Current, above head | Shape |
| --- | --- | --- | --- | --- |
| Above-roofline macro | 16.5 to 38.5 m | 18 to 40 m | 13.5 to 43.5 m | Peaked near 26 m above ground, see 11.3 |
| Below-roofline small cell | 2.5 to 6.5 m | 4 to 8 m | 2.5 to 6.5 m | **Unchanged.** Peaked at the floor |

In `directions.py` terms, with the range bands unchanged, that makes the macro
elevation support `atan(16.5/250)` to `atan(38.5/25)`, which is 3.78 to 57.00
degrees against the coded 3.1 and 60.1. The small cell support is
`atan(2.5/150)` to `atan(6.5/10)`, which is 0.95 to 33.02 degrees and matches
the coded values exactly, as it must, since that band does not move.

Citation for every number.

**These bands are assumptions, not calibrated values, and section 4.3 is why.**
No register contains a deployed FR3 cellular antenna, so no band here can be
justified by pointing at a frequency-matched deployment. What follows is the
argument for each, stated as an argument. Section 7.5 gives the sensitivity that
has to accompany them, and it shows the whole height question is worth under a
decibel, so do not over-invest in these endpoints.

**Macro band, 18 to 40 m above ground, derived from co-siting rather than from
percentiles.** An earlier draft derived a floor of 18 m by pointing at deployed
p5 values, which was a bad derivation: those p5 values are sub-6 antennas, and
reading them as a bound on FR3 siting is the category error section 4.3 warns
about. The argument that does work runs through site acquisition.

Section 4.4 measures deployed median height as flat against carrier frequency
across a 5x span, 30.0 to 31.8 m in the Netherlands and 26.8 to 27.8 m in
Brussels, rising slightly rather than falling. Operators co-site every band on
one mast because leasing the roof, powering it and backhauling it is the
expensive step and the radio is not. If FR3 is deployed the same way, as an
overlay on sites that already exist, then **the macro class inherits the existing
macro site population** and the right band is the one that spans it. Not because
15 GHz behaves like 900 MHz, but because it would be bolted to the same parapet.

Spanning the four study sites that have deployed heights (section 4.2), the
central mass at 500 m radius runs from a median of 21.1 m at Toulouse to 32.5 m
at Brussels, with p25 values of 20.2 to 29.7 m and p95 values of 31.6 to 51.6 m.
A band of 18 to 40 m covers the interquartile range of all four and the p95 of
three. That is the derivation, and its premise is the overlay branch of 4.4.

**If the densification branch is right instead, this band is wrong**, and wrong
in a knowable direction: new FR3 sites would appear below the existing grid, in
the 6 to 18 m region and at street level, and the macro floor would belong nearer
10 m. That is the sensitivity to run, and section 4.4 explains why it is a real
branch rather than a hedge: the section 3 campaigns, NYU Manhattan at 7 m,
Ericsson Kista at 8.5 and 12 m, Nokia lampposts at 8 to 15 m, are prototypes of
exactly that branch.

Two independent supports for the ceiling, both frequency-matched, which is rare
enough here to be worth stating. AT&T's 6.9, 8.3 and 14.5 GHz Austin campaign
placed transmitters "atop rooftops or other structures, such as parking garages,
at **heights between 10 and 35 meters above the street level**"
(arXiv:2510.00275, GLOBECOM 2025), and AT&T's 3GPP contribution at 7, 8 and
15 GHz used **25 and 35 m** (R1-2501371). Both sit inside 18 to 40 m. Around
them, ITU-R P.1411-13 clause 4.2.2 puts the urban over-roof-top model's validity
ceiling at `h1 = 55 m`, an applicability limit rather than a deployment claim,
and 3GPP UMa is 25 m in three agreeing tables (TR 38.901 Table 7.2-1, TR 38.802
Table A.2.1-1, M.2412-0 Table 5 b).

**Small cell band, 4 to 8 m above ground. Unchanged, and the earlier draft's
proposal to raise it to 12 m is withdrawn.** The 3GPP UMi value of 10 m, which
that proposal leaned on, appears in five tables and is a modelling convention in
every one of them. Section 4.5 finds no mode anywhere in the 6 to 18 m region in
3.46 million deployed antennas, so raising the ceiling would have added weight
where the deployed street layer is not. The floor is the better-supported end and
it is frequency-matched: NYU's FR3 Brooklyn campaign at 6.75 and **16.95 GHz**
put all five transmitters at "**4 m above ground (similar to lamppost heights,
representing small-cell BS)**" (arXiv:2410.17539), and ITU-R P.1411-13 Table 12
records measured `h1` of 4.0 m at 3.35 to 15.75 GHz urban.

This band is the one that carries the densification branch of section 4.4, so it
matters more than its width suggests. If FR3 densifies, this class holds the new
sites and the paper's small-cell results become the headline rather than the
supporting case.

The remaining paragraphs in this subsection are the superseded justifications,
retained because they are correctly cited and because they remain the argument
for the FR3 densification sensitivity described in section 4.4. Where a heading
says "superseded", the band it argues for is not the recommendation.

**Superseded, macro floor of 10 m above ground.** Four lines converge on it.
ITU-R P.1411-13
clause 4.2.2 gives the urban over-roof-top model a validity floor of `h1 = 4 m`.
TR 36.873 Table 7.2-1 and TR 38.901 Table 7.4.1-1 give the 3D-UMa and RMa NLOS
applicability floor as `h_BS > 10 m`, and Report ITU-R M.2412-0 Table A1-45 gives
`h_b` = 10 to 150 m above UT ground level. Section 5 measures roof p10 of 4.9 to
14.0 m across the ten non-Krakow sites. And the measured deployments of section
3.3 put real base stations well below 15 m in exactly this geometry: Ericsson's
15 GHz Kista square at **8.5 and 12 m**, Nokia's Manhattan lamppost subset at
**8 to 15 m**, NYU's six Manhattan sites at **7 m**. A 10 m floor admits the
3GPP UMi and micro value of exactly 10 m, which the current 15 m floor excludes,
and it is where the paper's own deterministic arm already sits (`report.tex`
uses 8 to 45 m).

**Superseded, macro ceiling of 35 m above ground.** The decisive citation is a measured
deployment statement at almost exactly this study's frequency: AT&T's 6.9, 8.3
and 14.5 GHz Austin campaign placed transmitters "atop rooftops or other
structures, such as parking garages, at **heights between 10 and 35 meters above
the street level**" (arXiv:2510.00275, GLOBECOM 2025), and AT&T's own 3GPP
contribution at 7, 8 and 15 GHz used **25 and 35 m** (R1-2501371). That is the
recommended band, stated independently by an operator, in the right band. Around
it: ITU-R P.1411-13 clause 4.2.2 puts the urban over-roof-top model's validity
ceiling at `h1 = 55 m`, which is an applicability limit rather than a deployment
claim. 3GPP UMa is 25 m in three agreeing tables (TR 38.901 Table 7.2-1,
TR 38.802 Table A.2.1-1, M.2412-0 Table 5 b). ITU-R P.1410-5 Figure 6 sweeps
5 to 30 m as its urban transmitter range. Section 5 measures roof p90 of 8.1 to
34.7 m across the nine mid-rise sites. Section 3.4's pooled campaign
distribution has only six of about fifty entries above 40 m. 35 m is 10 m below
the current 45 m.

**Small cell floor, 4 m above ground. Still current.** Well supported.
NYU's FR3 Brooklyn campaign at 6.75 and **16.95 GHz** put all five transmitters
at "**4 m above ground (similar to lamppost heights, representing small-cell
BS)**" (arXiv:2410.17539), in an "open square of around 200 m". ITU-R P.1411-13
Table 12 records measured `h1` of 4.0 m at 3.35 to 15.75 GHz urban and 2.5 m at
28.5 GHz residential, and clause 4.3.2 gives a validated range of 1.5 to 4.0 m
above ground for low-height terminals. 4 m is the bottom of the deployed range
and the most-used value in the FR3 literature.

**Superseded, small cell ceiling of 12 m above ground.** Read with section 4.3,
which measures the 8 to 12 m region as nearly empty in deployment. The standards
case below is real but it is a modelling convention, not an observation.
3GPP puts UMi and every dense-urban micro layer at
`h_BS = 10 m` in five independent tables (TR 38.901 Table 7.2-1, TR 38.802
Table A.2.1-1, TR 38.808 outdoor scenarios A and B, M.2412-0 Table 5 b), which
the current 8 m ceiling excludes outright. The measured campaigns agree that the
below-rooftop population reaches past 8 m: Nokia's lamppost subset spans **8 to
15 m**, Ericsson's Kista square deployment is at **8.5 and 12 m**. 12 m is 10 m
plus headroom and it keeps the class below the measured roofline (section 5 roof
p50 of 13.4 m at the lowest non-Krakow site).

But do not draw uniformly inside it. The measured mode of the below-rooftop
population is at the **bottom** of the band, 4 to 8 m (NYU's six Manhattan sites
at 7 m, NYU FR3 at 4 m, Aalto's open-square lamp post at 5 m, Fraunhofer Berlin
at 5 m, Bristol at 6.45 m), with a thinner shoulder from 8 to 15 m. Widening the
band to 12 m and keeping a uniform draw would move the class mean upward by more
than the evidence supports.

**Macro range cap, 25 to 250 m. Unchanged.** Section 8 derives that 250 m
truncates 5.5 % of the 3GPP-weighted incident power at 15 GHz and shows the same
cap sits inside the ITU-R P.1411-13 Table 3 micro-cell radius range of 0.05 to
1 km. The number does not change but it acquires a stated criterion.

**Small cell range cap, 10 to 150 m. Unchanged.** Section 8 derives 4.8 %
truncation, matching the macro criterion, and ITU-R P.1411-13 Table 3 gives
dense urban micro-cell a radius of 0.05 to 0.5 km, Table 4 gives the below-rooftop
NLoS urban low-rise model a measured validity of exactly 10 to 250 m.

### 11.3 Shape

**Do this only after 11.4.** Section 10.1 measures the shape correction at under
1 degree of median arrival elevation and about 0.5 dB in `E[h^2]`, against 6.5 dB
for the law-versus-band fix. The ordering is not close.

When it is done, the best available `f(h)` is the register histogram of section
4.3, not a fitted family. It is measured, it is large-sample, it is
ground-referenced, and at two of the eleven sites it is measured at the site
itself. Use Toulouse's ANFR distribution at Toulouse and Ghent's at Ghent, and
the pooled three-city macro distribution elsewhere. Its summary statistics, above
ground: median 26.9 m, mean 28.3 m, `h^2`-weighted mean 33.3 m.

Where a parametric form is needed, Rayleigh per ITU-R P.1410-5 eq. (17) remains
the only shape any primary source proposes, with the mode `gamma` taken from the
site's measured DSM. Section 5 gives `gamma` per site: the measured rooftop
`gamma` of the eight mid-rise sites runs 10.0 to 19.6 m with a median of 12.75 m,
so a rooftop `gamma` of about 13 m plus a 4 m mast puts the antenna-height mode
near 17 m above ground. Note that this is 9 m below the register median of 26 m,
which is the one place the DSM-plus-mast construction and the register disagree
materially, and the register should win because it measures antennas rather than
inferring them.

Do not use the Rayleigh form at Times Square or Hachiko. Section 5 measures KS
of 0.38 at both, where the true distribution is bimodal. Use the empirical DSM
directly, or an explicit two-component mixture.

For the small cell class, do not draw uniformly. The deployed street layer is
peaked at the floor: Ghent p25 5.0 m and median 6.0 m inside a 4 to 8 m band,
and the campaigns agree (NYU FR3 at 4 m, Aalto's open-square lamp post at 5 m,
Fraunhofer Berlin at 5 m, Bristol at 6.45 m, NYU's six Manhattan sites at 7 m).

### 11.4 Also fix the law-versus-band inconsistency

Independently of the numbers, `IlluminationModel` evaluates the pure
`1/sin^3(el)` law on a support derived from the bands, and section 7.1 shows
that is not the same distribution as the bands describe. Section 7.3 puts the
zero-bounce cost of the discrepancy at a median 6.5 dB for macro and 4.1 dB for
small cell. Whichever bands are adopted, the law should be replaced by the
mixture

```
N(el) proportional to cos(el)/sin^3(el) * [G(d_max tan el) - G(d_min tan el)]
```

which is closed-form given `f(h)`, reduces to the current law inside
`[atan(h_max/d_max), atan(h_min/d_min)]`, and needs no sampling.

## 12. What the evidence does to the current numbers

| Number | Current | Recommended | Direction and size | Confidence |
| --- | --- | --- | --- | --- |
| Macro height floor | 13.5 m above head | 16.5 m | **Up 3 m** | Low, and conditional. Derived from the overlay branch of 4.4, not from any FR3 measurement. Under the densification branch it belongs near 8.5 m instead |
| Macro height ceiling | 43.5 m above head | 38.5 m | Down 5 m | Medium. Two frequency-matched AT&T deployments at 7 to 15 GHz sit inside 18 to 40 m, and the four study-site p25 to p75 ranges are covered |
| Macro range floor | 25 m | 25 m | No change | Low sensitivity. Section 7.2 shows `d_min` barely moves the answer |
| Macro range cap | 250 m | **Report 150, 250 and 400 m** | The value does not change, the presentation must | This is the number that matters. Section 7.5 measures a 7.8 dB span across the defensible range, four to ten times the height band's leverage. It cannot be cited, so it has to be a reported sensitivity |
| Small cell height floor | 2.5 m above head | 2.5 m | No change | Medium-high. Frequency-matched: NYU FR3 at 6.75 and 16.95 GHz used exactly 4 m above ground, and ITU-R P.1411-13 Table 12 records 4.0 m at 3.35 to 15.75 GHz |
| Small cell height ceiling | 6.5 m above head | 6.5 m | **No change. An earlier draft said up 4 m and is withdrawn** | Medium. 3.46 M deployed antennas show no mode anywhere in 6 to 18 m, and the 3GPP UMi 10 m that motivated the increase is a modelling convention in all five tables it appears in |
| Small cell range floor | 10 m | 10 m | No change | Low sensitivity |
| Small cell range cap | 150 m | 150 m | No change | Medium. 4.8 % truncation, matches the macro criterion |
| Height distribution shape | Uniform | Register empirical, else Rayleigh | Qualitative change, small numerical effect | High on direction, but section 10.1 measures the effect at under 1 degree of median elevation. Do it after the law fix, not before |
| Elevation law | Pure `1/sin^3(el)` on a band-derived support | The band mixture of 11.4 | **+2.04 dB on median `chi_rooftop`, and 4 dB off the location spread** | High, and now measured rather than proxied (section 7.4). The largest single defect found, and it is not a number at all, it is an inconsistency |

**The table is the least important thing in this document, and saying so is the
main conclusion.** Four points, in decreasing order of what they should change
about the paper.

**None of these numbers can be cited.** Section 4.3 audits 3 863 228 European
antennas and finds zero deployed cellular access above 6 GHz. There is no FR3
macro network to calibrate against, anywhere, and the two apparent exceptions are
a fixed-link dataset and a Hz-versus-MHz units artefact. The caps are assumptions
argued from site acquisition economics and radio mechanism. Presenting them as
anything else would be dishonest, and the paper should say plainly that the
deployment being modelled does not yet exist.

**So the deliverable is a sensitivity band, not a number.** Section 7.5 measures
7.8 dB of leverage across the defensible range-cap span against 0.7 to 2.0 dB
across the defensible height-band span. The paper should report `chi` at 150, 250
and 400 m and treat the height endpoints as settled-enough detail. Sections 9,
10 and 11 of this document argue the height question across roughly 400 lines,
and section 7.5 shows the whole argument is worth under a decibel. That
misallocation is worth recording so the paper does not repeat it.

**The one free fix is the law, not any endpoint.** Section 7.4 measures the
law-versus-band inconsistency at +2.04 dB on median `chi_rooftop` and 4 dB off
the location spread, with a bit-identical isotropic control. It costs nothing to
correct and it is larger than every height endpoint change combined.

**The endpoints themselves barely moved, and two of this document's own earlier
recommendations were withdrawn.** Of the eight, four are unchanged and the two
height changes are 3 and 5 m on bands 30 m wide. The withdrawn pair were both
derived from standards tables read as deployment facts, the small-cell ceiling
from 3GPP UMi's 10 m and the macro floor from the same table, and both were
corrected by looking at what is deployed. The general lesson, which applies to
the surviving numbers too, is that a modelling convention repeated in five
standards tables is still a modelling convention.

## 13. What remains uncited or judgement-based

Listed plainly rather than buried.

**No citation exists for any of these, and none was manufactured.**

1. **The 3 to 5 m rooftop mast height** in section 11.1. This is an engineering
   convention and no standard or register consulted states it. It now has one
   empirical test, in section 4.4: Toulouse's measured roof p50 of 17.1 m plus
   the mast gives 20.1 to 21.1 m against a measured ANFR median of 20.9 m within
   130 m. That is agreement to within 1 m at one site, which is encouraging and
   is not a citation.
2. **Every height and range cap in this document, without exception.** Section
   4.3 establishes that no deployed FR3 cellular antenna exists in any register,
   so nothing here is calibrated at the study's frequency. This is the single
   most important entry in this list and it applies to numbers that other
   sections state with apparent confidence.
3. **Whether FR3 arrives as overlay or as densification**, section 4.4. The two
   branches give macro floors of 18 m and roughly 10 m, and nothing available
   settles which. The recommendation takes the overlay branch because co-siting
   is measured and densification is so far only prototyped, but that is a
   judgement about how an industry will behave, not a measurement. It should be
   run as a sensitivity and reported as one.
4. **The claim that sub-6 site heights transfer to FR3 at all.** This rests
   entirely on the co-siting flatness of section 4.4, which is measured only up
   to 3.5 GHz. Extending a flat trend across a further 4x in frequency, past the
   point where propagation arguably does start to constrain siting, is an
   extrapolation. It is a better-motivated one than trend fitting, and it is
   still an extrapolation.
5. **Treating registers with different datums as one population.** Base, centre
   and panel mounting point differ by roughly a panel half-length, about 1 m at
   macro sizes, and the merged schema hides this behind one column name. Not
   corrected. Small against the spread being measured and not zero.
6. **The bin fractions in section 4.5 are extraction-dependent.** Two paths over
   the same city disagree by a factor of eight in row count and by 17 points in
   the 6 to 18 m share. The qualitative two-mode structure survives that, but
   the percentages should not be quoted as if they were stable.
7. **The 5 % truncation criterion** in section 8. The computation is derived,
   the choice of 5 % is not. It was reverse-engineered from the current numbers,
   which happen to be mutually consistent at that level, and then adopted. Given
   section 7.5, the criterion matters less than reporting the span either way.
8. **The overshoot argument** in section 9, mechanism 3. Standard cellular
   engineering, but no paper was found that quantifies overshoot as a function
   of site height at FR3 or mmWave. It is stated as reasoning and should not be
   cited as a result.
9. **Resolved, and larger than expected.** The claim that a fixed global `Q_S`
   compresses the measured cross-city spread (section 9) is now measured on five
   sites at the 250 m crop: the spread falls from 11.75 to 7.43 dB when the law
   is corrected (section 7.4). No longer a judgement call. Pending the other
   seven sites.

**Judgement calls that are defensible but are calls.**

10. **Four of the eleven sites have a deployed source height**, from the AEGIS
    database: Toulouse, Ghent, Brussels and Krakow. For the other seven,
    including both high-rise sites that drive the morphology argument, the height
    model is a prior. Section 4.7 explains why further collection will not close
    most of them, and none of it closes the 15 GHz gap.
11. **Whether the 130 m crop DSM represents the source region out to 250 m.**
    Section 5 measures rooftops within 130 m and section 8 shows sources out to
    250 m carry the weight. In a homogeneous historic core the extrapolation is
    mild. At Times Square, where the morphology changes over a block, it is not.
12. **Photogrammetric DSM counts vegetation and awnings as roof.** Not corrected.
    Biases roof p10 down and built fraction up.
13. **Excluding Toulouse from the ratio statistics** in sections 6 and 7.3. Its
    crop centre reads 0.00 open below 45 degrees, which makes every ratio
    degenerate. That site needs its own look, since it still reports the second
    highest `chi_rooftop` of the eleven.
14. **Krakow's 0.09 built fraction** makes its rooftop statistics and its
    Rayleigh fit unrepresentative. It is reported but should not drive anything.

**The one measurement that would settle the most, now partly done.**

15. The re-weighting run is **done for one site and running for the rest**.
    Section 7.4 has Korenmarkt at the 130 m crop and four sites at the 250 m
    crop. Six sites are outstanding. Until they land, the cross-site
    compression figure of 11.75 to 7.43 dB rests on five points, four of which
    are canyons and one of which is an open plaza, so the pooled number is
    sensitive to which morphologies the remaining seven add.
16. **The recommended per-site `Q_S` of section 11.1 has not been run at all.**
    Section 7.4 changes only the law, not the bands, and not the
    morphology-conditioned weighting. The section 9 argument remains unmeasured.

## 14. Data quality findings for the AEGIS base station pipeline

**This section is not about this paper.** It records defects found in
`data/basestations/merged/*.parquet` while using it as evidence for section 4.
They are logged here because they will silently corrupt any cross-region query,
not because they affect the city exposure study.

**1. `Frequency` units are not normalised across regions.** Australia stores Hz.
The European registers store MHz. A filter such as `Frequency > 6000`, intended
to select above 6 GHz, returns all 137 897 Australian rows because they are
above 6 kHz, and returns them alongside genuine MHz-denominated rows from other
regions. Confirmed by inspection: Australia's `Frequency` runs from 2.9e4 to
8.54e8, and the European maxima are 2600 (France) to 3755 (Spain).

Anyone filtering by frequency across regions today gets a silently wrong answer.
This one bit me directly and it is the reason section 4.3 needed a second look
before it could state its result.

**2. The Australia extraction looks truncated.** Its maximum is 854 MHz, so it
appears to contain only the low bands. Australia deploys 1800, 2100, 2600 and
3500 MHz, none of which are present. Worth re-checking the ACMA fetch.

**3. `CenterHeight` asserts a datum the sources do not share.** One column name
covers at least three different physical reference points: ANFR's
`AER_NB_ALT_BAS` is the antenna **base**, the Flemish conformiteitsattest
`Hoogte midden` is the antenna **centre**, and the Dutch Antenneregister `Hoogte`
is the panel **mounting point**. Verified for France by reproducing the ANFR
distribution exactly from the parquet. The spread is roughly a panel
half-length, about 1 m at macro sizes, which is small but is a systematic offset
between regions rather than noise.

**4. Coverage is very uneven and there is no completeness flag.** Measured across
the 15 regions:

| Field | Regions at 100 % | Regions at 0 % |
| --- | --- | --- |
| `Frequency` | australia, brussels, canada, france, netherlands, poland, spain, uk | austria, brazil, denmark, flanders, germany, luxembourg, switzerland |
| `CenterHeight` | australia, brussels, canada, flanders, france, netherlands, uk | austria, brazil, denmark, luxembourg, spain, switzerland |
| `Technology` | all except germany | germany |

Spain has 178 207 rows with complete frequency and no height at all. Flanders has
488 221 rows with complete height and no frequency at all. Germany has no
`Technology`. Poland is at 75 % height coverage. A caller cannot currently
distinguish "this region reports no heights" from "these antennas have no
height", which matters for any aggregate computed across regions.

**5. The UK region contains no cellular access antennas.** All 15 141 rows are
`Technology` = `FH`, fixed point-to-point links at a 22 GHz median. This is
correct data but it is a different kind of object from every other region, and
pooling it into an access-antenna statistic is wrong. It should carry a flag, or
the fixed links should live in a separate table.
