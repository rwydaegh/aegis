# Prestigious‑University Authors — BioEM & EuCAP

Submissions in which **at least one author lists an affiliation from the blended Top‑50 universities**.
Sources analysed:

| Conference | Years available | Pages | Notes |
|---|---|---|---|
| BioEM | 2022, 2023, 2024, 2025 | 767 / 427 / 282 / 258 | Bioelectromagnetics. 2023 is figure‑heavy but all 219 abstracts have extractable author text. |
| EuCAP | 2024 only | 378 | Antennas & Propagation. "2025" was an app, not a document — **not analysed**. |

Method: `pdftotext` extraction → curated name+abbreviation patterns for each Top‑50 institution → **manual disambiguation** of every hit against the affiliation lines.

---

## ⚠️ Robustness & limitations (read this)

This is a curated‑name search, not a guarantee. What I verified and what can still slip through:

- **Extraction completeness — OK.** EuCAP: 0 image‑only pages (all 378 have text). BioEM 2023: the 158 MB size is embedded figures; the 219 abstracts all extracted.
- **Line‑wrap undercount — FOUND & CORRECTED for EuCAP.** EuCAP's layout wraps long author lists, so a per‑line regex misses names split across lines (e.g. `University of\nManchester`). A whitespace‑collapsed re‑search recovered extra hits: Michigan 4→6, Manchester 12→14, Edinburgh 9→11, **TU Munich 12→15**, NUS 6→7, **Tsinghua 1→2**, control "Politecnico di Torino" 34→41. The **set of institutions is unchanged**, but EuCAP per‑institution paper counts are best read as **lower bounds**, especially for prolific groups whose papers appear in the abstract‑listing section.
- **Allowlist risk.** If an institution is written in a form I didn't anticipate, it's invisible. I covered standard names + abbreviations (MIT, UCL, NYU, NUS, NTU, ANU, TUM, PSL, UCSF/UCSD, Caltech, etc.).
- **Namesake/city collisions — manually filtered.** Documented per‑case below (the big ones: the "Duke" virtual‑human model ≠ Duke University; "Peking Union Medical College" ≠ Peking University; "Melbourne/San Francisco/San Diego/Edinburgh, Australia" the city ≠ the university; "Université Catholique de Louvain (UCL)" ≠ University College London).
- **Affiliation ≠ employment.** Some are co‑/courtesy affiliations (e.g. Ben Mabrouk lists "Al Ain University & Princeton University"; the Kuster/IT'IS group lists ETH Zurich alongside the IT'IS Foundation). Flagged where relevant.

---

## Cross‑check against your screenshot list

| Your name | Found? | Where |
|---|---|---|
| Joel Schwartz | ✅ | BioEM 2024 — Harvard School of Public Health (Project GOLIAT) |
| Prof Nir Grossman | ✅ | BioEM 2023 — Imperial College London (Temporal Interference Stimulation) |
| Rachel B Smith | ✅ | BioEM 2023 — Imperial College London (COSMOS) |
| Mrs Uma Mangalanathan | ✅ | BioEM 2023 — co‑author on the Stanford abstract (OS02‑03) |
| alvaro pascual‑leone | ✅ | BioEM 2022 — Harvard Medical School (miniaturized coils) |
| Syed Osama Kamal | ✅ | EuCAP 2024 — University College London |
| "An L‑Band Receiving Array…" | ✅ | EuCAP 2024 — National University of Singapore |
| Ismail Ben Mabrouk (princeton) | ✅ | EuCAP 2024 — "Al Ain University & **Princeton University**" (co‑affiliation, UAE) |
| **H. Vincent Poor** (Princeton) | ❌ | "Poor" appears **0 times** in any extracted file |
| **Pippa Gleave** | ❌ | "Gleave"/"Pippa" appear **0 times** in any extracted file |

➡️ **Gleave and Poor are not in the documents I have.** Most likely they're from **EuCAP 2025** (the app, which isn't a file here) or other browsing. Worth confirming against that source separately.

---

## Prestigious universities MISSING from your Top‑50 (but present in the data)

You guessed EPFL — correct, and it's the clearest miss.

| Institution | Why it arguably belongs | Present in |
|---|---|---|
| **EPFL** (École Polytechnique Fédérale de Lausanne) | QS ~#14, THE ~#11–20 — **unambiguously Top‑50 by any blend**. A genuine omission. | **Both.** BioEM 2023 *Temporal Interference Stimulation* (EPFL Geneva — Wessel, Beanato, Hummel) & 2025 OS11‑05 (EPFL Lausanne — Skrivervik); EuCAP 2024 (~14 mentions, several papers) |
| **TU Delft** (Delft University of Technology) | QS ~#47–57; elite in engineering. Strongest borderline case. | EuCAP (very heavy — ~50 mentions, e.g. *Chessboard Focal Plane Array…*); not in BioEM |
| **KU Leuven** | THE ~#42–45 / QS ~#61 — right on the Top‑50 boundary. | EuCAP (~9); not in BioEM |

**Defensible to omit** (world‑class but generally *outside* a Top‑50 overall blend, even if field‑leading): KTH Royal Institute of Technology, Georgia Tech, Chalmers, TU Eindhoven, City University of Hong Kong (the #1 antennas school but ~#60–70 overall), University of Surrey / 5GIC, Queen Mary University of London, Heriot‑Watt, UESTC, Southeast University, Politecnico di Torino.

> Caveat on "prestige": your blend ranks **overall** reputation. For *these specific fields*, the most influential institutions aren't always the highest‑ranked ones — in antennas, places like CityU Hong Kong, Surrey, Delft, KU Leuven and UESTC outweigh several of your Top‑50; in bioelectromagnetics/dosimetry the field is dominated by the IT'IS/ETH and Gustave‑Roussy/Paris‑Saclay groups. If the goal is "prestigious *in this field*", the list would look different.

---

# BioEM (2022–2025)

### Filtered‑out false positives (NOT matches)
- **#24 Duke → 0:** all 24 "Duke" hits are the **IT'IS "Duke" virtual human body model**, not the university.
- **#26 Peking → 0:** all hits are **Peking Union Medical College** (≠ Peking University).
- **#29 Melbourne → 0:** all 69 are the *city* (Swinburne, Monash, RMIT, ARPANSA, Telstra).
- **#4 Oxford → 0:** "Oxford University Press", "Oxford Nanopore", BioEM2020 venue.
- **#17 UCLA / #36 UCSF → 0:** "Los Angeles" was USC; "San Francisco" was a city anecdote.

### Matches

**#2 Harvard** — 2022 *A numerical study on miniaturized coils for focal nerve magnetic stimulation* (Pascual‑Leone, Harvard Medical School); 2024 *Project GOLIAT…* (Schwartz, Harvard School of Public Health). [2025 plenary bio of M. Levin notes "associate faculty, Harvard Wyss" — primary affiliation Tufts.]

**#3 Stanford** — 2023 OS02‑03 *Identification of the ion channels participating in nsPEF‑induced pore formation* (co‑author at Stanford; this is your **Uma Mangalanathan** paper).

**#6 Caltech** — 2022 S04‑6 *Thermoacoustic tomography of the human abdomen: Safety assessment* (Lihong V. Wang group).

**#12 University of Pennsylvania** — 2022 W2‑1 *Workshop Introduction* (Kenneth Foster); 2022 S08‑1 *…the SPARC Data Resource Center* (J. Wagenaar).

**#13 Johns Hopkins** (JHU Applied Physics Laboratory, Carlos Martino) — 2024 OS03‑01 *Quantum Biology of ROS Production in ETF and CRY*; 2025 OS15‑02 & OS15‑03 (*Engineering Magnetic Field Waveforms…* Parts I & II).

**#14 Imperial College London** — 2023 OS01‑01 *Non‑Invasive Transcranial Stimulation… Temporal Interference Stimulation* (Nir Grossman); 2023 OS13‑02 *Headache in the COSMOS study…* (Smith, Elliott, Toledano).

**#15 University College London** — 2025 OS14‑06 *Frequency‑SAR dependency of Mouse Cortical Cell Proliferation…* (Huiliang Li).

**#16 ETH Zurich** — the largest group, via the **IT'IS Foundation / Niels Kuster** team (ETH listed as co‑affiliation), ~28 submissions:
- 2022 — *EM exposure risks for persons with implants: A neglected population?* (P1‑1, plenary); *Tabletop exposure system for assessment of RF compatibility of medical implants with MR examination* (S01‑2); *Coverage factors for efficient assessment of human exposure in the close near field of low‑frequency magnetic field sources* (S03‑3); *A handheld system for in‑situ exposure assessment of WPT systems with basic restrictions* (S05‑3); *Advantages and limitations in applying AC and DC‑coupled four‑electrode probe for low‑frequency dielectric spectroscopy of biological samples* (S05‑4); *Importance of diverse anatomy in virtual population for risk assessment of MR examination* (S06‑4); *Collaborative, sustainable, and FAIR neurosciences in bioelectronic medicine: the SPARC Data Resource Center* (S08‑1); *Fully automatized personalized head exposure modeling… in a brain‑stimulation treatment modeling platform* (S10‑2); *Towards a non‑invasive craniospinal compliance biomarker* (S10‑6); *Electromagnetic field strength measurements in outdoor environments, public indoor places and public transport in Switzerland in 2021* (S11‑2); *Capacitive coupling of local electromagnetic sources with biological bodies* (S14‑3); *Measurement of the absorbed power density of 5G millimeter‑wave mobile devices* (FA‑10/PA‑30); *Analysis of uncertainty in the modeling of treatment performance and safety for non‑invasive brain stimulation techniques* (PB‑6)
- 2023 — *Traceable Absorbed Power Density Assessment System in the 28 GHz Band* (OS01‑03); *Calibrated Induced E‑field Measurement System for Frequencies from 20 Hz to 100 kHz* (OS01‑04); *Development of Morbidly Obese Anatomical Phantoms for MR Safety Applications* (OS03‑03); *Dielectric Properties of Rat Tissues at <10 MHz Measured with an Advanced Instrumentation* (OS10‑06); *Derivation of Calibration Functions for an Open‑Access Smartphone Application for RF‑EMF Exposure Assessment* (B56/FB06); *Stimulus‑evoked responses and modulation of the cerebral cortex with magnetoelectric nanoparticles* (WS05, S. Pané)
- 2024 — *Comparison of the Electromagnetic Energy Absorbed in Human Tissue and in the Standardized Test Phantom when Transmitters are Operated in Closest Proximity to the Skin* (102B); *Robust Validation Methods for Systems Determining the Absorbed Power Density* (113A/FA19); *Methods of Reducing the Uncertainty of Dielectric Tissue Properties at Low Frequencies and Its Impact on Dosimetry* (124B/FB15)
- 2025 — *Robust Assessment of the Incident Field at the Surface of Wireless Power Transfer Devices* (OS01‑04); *Link Budget Assessment for Ingestible RF Devices Navigating Through the Digestive Tract* (PA‑18); *Personalized TMS Planning Tool Based on Electrophysiological Response and Brain Network Dynamics Predictions* (PA‑52); *General Circuit Model for Electrode Contact Impedance for Transcranial and Other Electrical Stimulations* (OS05‑04); *Analytical Modeling of Implantable Antennas: From Spherical Body Model to Planar Body Model* (OS11‑05); *Calibration and Validation Methods for a sub‑THz Near‑Field Test System* (OS13‑06)

**#23 New York University** — 2024 106B/FB11 *Analytical model for rf propagation in layered spheres…*; 2025 OS05‑03 *MRI of the brain: impact of heterogenous head model…* (Riccardo Lattanzi, NYU Grossman School of Medicine).

**#27 UC San Diego** — 2022 S08‑1 *…SPARC Data Resource Center* (Maryann Martone, UCSD).

**#28 University of Edinburgh** — 2024 031A/FA04 *On Electromagnetic Stimulation in Biomanufacturing…* (Alistair Elfick).

**#30 National University of Singapore** — 2025 *Young Scientist Award Plenary: Andy Tay — Adding a mechanical angle to bioelectromagnetism*.

**#32 University of Tokyo** (Sekino / Ueno groups) —
- 2022 — *Evaluation of neuronal network activity in high‑intensity power‑frequency magnetic fields* (W1‑1); *Recent advances in biomedical applications in bioelectromagnetics* (W2‑5); *Magnetic‑resonance‑based specific absorption rate estimation via electrical properties tomography at 7T* (S09‑4); *Real‑time calculation of induced electric field for arbitrary Transcranial Magnetic Stimulation coils* (PA‑4)
- 2023 — *Modeling the Induced Fields in the Head Model with Titanium Skull Plate Using Round TMS Coil* (OS12‑04); *Transcranial Magnetic Stimulation: Past, Present and Future* (WS01, S. Ueno)
- 2024 — *Prediction of therapeutic effect of TMS therapy for treatment‑resistant depression using a combination of electric‑field simulation and functional‑connectivity analysis* (120B/FB13)

**#33 University of Sydney** — 2022 PB‑48; 2023 A32 (Sandhya Clement).

**#35 University of Wisconsin–Madison** — 2022 PB‑59 *Effects of near null magnetic field and PEMF on plants…* (R. Barker; book says only "University of Wisconsin").

**#38 UIUC** — 2025 PB‑14 *Reliable Numerical Characterization of Rodent Exposure Imbalances…* (K. Sanderson).

**#41 Sorbonne University** (GeePs lab, *Sorbonne Université*) —
- 2023 — *Immunity of active implantable medical devices to industrial magnetic field environments: impact of the field direction* (OS07‑06)
- 2024 — *Electromagnetic compatibility assessment of pacemakers in occupational environments: parameters affecting their functioning* (OS09‑01)
- [2025 "Sorbonne" hits were "Sorbonne Paris Nord", a different institution — excluded.]

**#43 Karolinska Institute** (Maria Feychting) —
- 2023 — *Headache in the international Cohort Study of Mobile Phone Use and Health (COSMOS) in the Netherlands and the United Kingdom* (OS13‑02); *Time trends in glioma incidence among males in the Nordic countries 1979–2016 and mobile phone risk* (A58); *Reviewing for the WHO RF EMF Health Risk Assessment: …Epidemiological studies* (WS03)
- 2025 — *Childhood leukemia and ELF‑MF: an epidemiological perspective* (WS1‑2); *Three decades of the WHO EMF project: …ELF‑magnetic fields and childhood leukemia* (WS1‑6); *Effects of recall bias on modeling cancer risk from mobile phone use: …the Interphone case–control study* (OS03‑03)

**#45 Technical University of Munich** — 2023 *Spatial Selectivity of Wireless Neuronal Stimulation via Injectable Nanoelectrodes* (WS05, Kozielski group).

**#47 PSL University** (EPHE‑PSL; Lagroye/Orlacchio) —
- 2022 — *Study of the effects of 5G technology on the mitochondrial stress response* (FB‑14/PB‑50)
- 2023 — *Can we observe brain activity changes during exposure to radiofrequency? A proof‑of‑concept study* (OS04‑02)
- 2024 — *Macroscopic and microscopic temperature measurements during exposure of multicellular spheroid tumors to nanosecond pulsed electric fields (nsPEF)* (WS3)
- 2025 — *Generational effects of a chronic exposure to 26 GHz RF‑EMF on insects: insights from Drosophila melanogaster* (OS02‑04); *Challenges in enhancing pulsed electric fields (PEF) electroporation using conductive nanoparticles: from theory to practice* (PB‑16)

**#50 Paris‑Saclay University** — 2nd‑largest, mainly the **Lluis Mir / Gustave Roussy "METSY"** electroporation team + GeePs + one epidemiology cohort, ~22 submissions:
- 2022 — *Transient changes in membrane hydration of liposome exposed to nanosecond electric pulses detected by wide‑field CARS microspectroscopy* (P3‑1, Plenary 3); *Using subnanosecond pulsed electric fields to electroporate bacteria and eukaryotic cells* (S02‑6); *Advanced microdosimetric investigations through a realistic modelling of cells and intracellular organelles* (PA‑18)
- 2023 — *Realistic model of cell and its internal organelles: 3D model realization procedure and microdosimetric analysis of microsecond pulse exposure of a mixture of cells* (OS01‑06); *A modelling study on the effect of a pulsed electric field on a realistic‑shaped cell comparing facing versus coplanar electrodes* (A21/FA04); *Microsecond Pulse Electric Field enhanced MSCs proliferation* (OS02‑06); *Immunity of active implantable medical devices to industrial magnetic field environments* (OS07‑06); *Cells electropermeabilization with subnanosecond pulsed electric fields* (OS14‑02); *New strategies of electrical stimulation of stem cells for neural tissue regeneration* (WS02); *Microsecond electric pulses effects on mesenchymal and induced neural stem cells for spinal cord injuries application* (WS02); *RISEUP: Regeneration of Injured Spinal cord by Electro‑pUlsed bio‑hybrid implant, focus on the in vivo evaluation* (WS02)
- 2024 — *Effects of microsecond electrical pulses on cells of the immune system* (018B); *In‑vitro imaging and molecular characterization of Ca²⁺ flux modulation by nanosecond pulsed electric fields* (027B); *Electromanipulation of calcium oscillations in mesenchymal stem cells in proliferation and differentiation* (028B); *Cosmos‑France, a cohort nested in the Constances cohort: first descriptive analysis* (049A); *Impact of repeated head‑exposures to a 5G‑3.5 GHz signal on behaviors and intracerebral gene expression in adult male mice* (OS05‑04); *Electromagnetic compatibility assessment of pacemakers in occupational environments* (OS09‑01); *3D Virtual Cell Model in Microdosimetry Assessment* (WS3); *Microdosimetry of µsPEFs on advanced stem‑cell 3D models in microfibrils' electrified scaffolds* (OS01‑06)
- 2025 — *Detection of cell membrane hydration changes induced by pulsed electric fields using wide‑field CARS microspectroscopy* (PB‑17); *EMF interactions with cells: different mechanisms leading to different applications* (WS3‑3)

**EPFL** *(off‑list — not in your Top‑50, but Top‑50‑caliber; QS ~#14)* —
- 2023 — *Non‑Invasive Transcranial Stimulation of Deep Brain Structures in Humans… Temporal Interference Stimulation* (OS01‑01; EPFL Geneva — Wessel, Beanato, Hummel; same paper as the Imperial/Grossman entry)
- 2025 — *Analytical Modeling of Implantable Antennas: From Spherical Body Model to Planar Body Model* (OS11‑05; EPFL Lausanne — Anja Skrivervik; same paper as the ETH/Kuster entry)

### BioEM — zero presence (28/50)
MIT, Oxford, Cambridge, Princeton, UC Berkeley, Columbia, Yale, U Chicago, UCLA, Cornell, Michigan, Toronto, Tsinghua, Northwestern, Duke, U Washington‑Seattle, Peking, British Columbia, LMU Munich, UCSF, UT Austin, Manchester, McGill, ANU, Heidelberg, Kyoto, WashU St. Louis, Nanyang/NTU.

---

# EuCAP 2024

EuCAP is far larger and engineering‑focused, so many more Top‑50 institutions appear. **Paper counts are lower bounds** (see wrap caveat). Disambiguation notes inline.

### Filtered‑out false positives
- **#15 UCL:** "Université Catholique de Louvain (UCL)" (Belgium) ≠ University College London.
- **#28 Edinburgh:** "DST Group Edinburgh, **Australia**" (city), "Edinburgh **Napier** University" (different), and a sponsor blurb — excluded.
- **#1 MIT:** only "MIT **Lincoln Laboratory**" (a defence‑radar workshop presenter), no academic‑MIT papers.
- **#27 UCSD:** only the Rebeiz **keynote** (KY3), not a paper.
- **#6 Caltech:** mostly **NASA‑JPL/Caltech** (JPL is Caltech‑operated) vs. one academic‑Caltech paper.

### Matches

**#3 Stanford (3)** — *The Hydrogen Intensity Real‑Time Analysis eXperiment (HIRAX)*; *Reconfiguration of Electromagnetic Metasurfaces Using Tunable Shape‑Morphing Structures*; *Multistable Structures for Deployable and Reconfigurable Antennas* (M. Sakovsky).

**#4 Oxford (2)** — *Superconducting Space‑Time Modulation: Theoretical Implications and Mixing‑Beamsplitting Functionality*; *Nonreciprocal Phase‑Shifting in Linear Magnet‑Free Reconfigurable Temporal Loops* (Taravati/Bakr, Southampton & Oxford).

**#5 Cambridge (2)** — *Mitigating Zenith Blindness from Mutual Coupling in a Sunflower Phased Array*; *Modal Analysis of Thermal Noise from Lossy Dielectric Medium* (de Lera Acedo).

**#6 Caltech** — academic: *Analyzing the Performance of Phased Array Geometries with Aperture Projection Analysis* (Ali Hajimiri). JPL/Caltech: *Dual‑Frequency Metasurface Antenna for Earth Science Remote Sensing*; *Chessboard Focal Plane Array…*; *Uncertainty Quantification of the Gain Budget for INCUS*; *Feed Assembly Development for INCUS*.

**#7 Princeton (≈3)** — via Ismail Ben Mabrouk ("Al Ain University & Princeton University"): *Dual‑Band 3‑D MIMO Antenna for Deep Tissue Devices*; *Design of an UWB Conformal Antenna for Wireless Capsule*; *Miniaturized Implantable Antenna… for Leadless Pacemakers*.

**#12 University of Pennsylvania (1)** — *Assessing Performance of Transparent Conductive Films for Microwave…* (D. Tzarouchis).

**#14 Imperial College London (3)** — *Electromagnetic Detection and Identification of Perturbed Wire…* (Syms); *Single‑Branch Hybrid Resistance Compression Technique…*; *Optimal Morphing Metasurface Lens for Next‑Generation RF Sensing…*

**#15 University College London (1)** — *Design and Measurement of a 2×2 Array of Coaxial Periodic Leaky‑Wave Antennas* (Syed Osama Kamal, Lai Bun Lok). ← your list.

**#16 ETH Zurich (2)** — *HIRAX* (Crichton, Refregier); *Plug‑In Plug‑Out Multibeam Dielectric Rod Antenna…*

**#18 Cornell (1)** — *Single‑Branch Hybrid Resistance Compression Technique…* (Jichao Yang).

**#19 University of Michigan, Ann Arbor (2 + invited)** — *Increasing the Efficiency‑Bandwidth Product… via Parametric Space‑Time Variation*; *All‑Metal Perfectly‑Matched Metamaterials*; invited talk IN10 (Anthony Grbic).

**#20 University of Toronto (1)** — *3D Method‑of‑Moment Design of Huygens' Metasurfaces* (Eleftheriades).

**#21 Tsinghua (≥1)** — *Recent Advances in Multiscale‑Multiphysics Inverse Scattering* (Maokun Li).

**#23 New York University (2)** — *Empirical Path Loss Model… in 6 and 37 GHz Shared Bands*; *Frequency Domain Channel Characteristics in an Outdoor‑To‑Indoor Environment at 6 and 37 GHz* (Gebremedhin).

**#28 University of Edinburgh (≈6, Podilchak group)** — *Dual‑Polarized SIW Antenna with High Isolation for Polarimetric Radar*; *Mechanically Re‑Configurable Leaky‑Wave Antenna…*; *A Reconfigurable Phase Gradient Metasurface Rasorber…*; *Electromagnetic Beerline Cleaning Using RF Signals*; *Analysis and Design of a Wideband Jaumann‑Like Radar Absorber…*; *Beamforming Orthogonality in Coupled Directional Modulation Arrays*; (+ gprMax software course).

**#30 National University of Singapore (6, Zhi Ning Chen / Mouthaan)** — (Peiqin Liu/Yan/Chen paper); *X‑Band Receiving Phased Array with Digital Beamforming Using RFSoC*; *Technology for Radiation Pattern Manipulation of Wi‑Fi Antennas*; *An L‑Band Receiving Array with Full Digital Simultaneous Quad‑Polarization Beamforming* (← your list); *Optimization of Contiguously Clustered Multibeam Scanning Planar Array for 5G/6G*; *Impact of Deformations on Beamforming Performance of Uniform Rectangular Arrays*.

**#31 University of British Columbia (1)** — *A WiFi‑Based System for Ice Monitoring in Harsh Environment Using 2.7 GHz Microwave Sensor* (Zarifi, UBC Okanagan).

**#33 University of Sydney (1)** — *RIS Performance in a Comprehensive Fading Environment* (Yonghui Li).

**#35 University of Wisconsin–Madison (1)** — *A Class‑E, Switched‑Mode, Non‑LTI Electrically‑Small Transmit Antenna Design…* (Behdad).

**#38 UIUC (2, Zhen Peng)** — *Quantum Optimisation of Reconfigurable Surfaces in Complex Propagation Environments*; *Platform‑Aware Optimization of Conformal Antenna Array via Simulated Bifurcation*.

**#39 University of Manchester (≈8, Zhirun Hu / Anthony Brown)** — *Non‑Volatile RF Frequency Reconfigurable Antenna for Wireless Communication*; *Achievable Rate Approximation of Large Intelligent Surface Based on Deep Learning*; *A High‑Gain Spoof Surface Plasmon Polaritons (SSPP) Antenna…*; *Enhancing Signal Transmission in Energy‑Saving Glass Through Tri‑Bandpass FSS Design*; *MIMO Array Decoupling with SSR Structure…*; *Frequency Reconfigurable Flexible Printed Antenna… for Wearable Applications*; *Mitigating Zenith Blindness…* (Brown); *An Overview of Gigascale Antenna Arrays… for Space‑Based Solar Power* (Brown).

**#40 McGill (1)** — *HIRAX* (Chiang, Gerodias).

**#41 Sorbonne University (≈5, Valerio/Sarrazin)** — *Modal Analysis in Woodpile Dielectric Structures*; *Direction‑of‑Arrival Ambiguities Mitigation in Multibeam Leaky‑Wave Antennas*; *Efficient Numerical Computation of Dispersion Diagrams for Glide‑Symmetric Periodic Structures…*; *Glide‑Symmetric Reconfigurable Substrate‑Integrated Holey Waveguide*; *All‑Metal Glide‑Symmetric Slotted Planar Antennas: Modal Analysis*.

**#45 Technical University of Munich (≈7, Eibert)** — *Inverse Source Solutions with Spectral Filtering*; *Front‑End Mismatching, Mutual Coupling, Bandwidth, Transmission‑Line Noise, and SNR*; *Geometry Reconstruction from Entries of Impedance Matrices*; *In‑Flight Calibration… for UAV‑Based Near‑Field Antenna Measurements*; *Inverse Source‑Based Three‑Antenna Methods in the Near Field*; *Optimized Design Parameters for a Flux‑Driven SNAIL‑Based Traveling‑Wave Parametric Amplifier*; *A Loop‑Star Decomposition for the B‑Spline Based Discretization of the EFIE*.

**#46 Kyoto University (3, Shinohara — wireless power transfer)** — *Optimum Structured Phased Array with Novel Beam‑Forming Circuits…*; *Large and Simple Phased Array System at 28 GHz…*; *Far‑Field Beam Wireless Power Transfer with Combination of Beam Forming and Optical Target Detection*.

**#47 PSL University (2, ESPCI/Institut Langevin)** — *Compact Metamaterial Antenna for Three‑Dimensional Angular Localization of Multiple RF Sources*; *An Electromagnetic‑Compliant Scattering Model for Reconfigurable Intelligent Surfaces*.

**#49 Nanyang Technological University (1)** — *AI‑Assisted Design and Experimental Testing of a Compact UWB Antenna for the Inspection of Food and Beverage Products*.

**#50 Paris‑Saclay University (≈6, Marco Di Renzo group)** — *Exploring RIS Coverage Enhancement in Factories…*; *Analysis and Optimization of RIS Based on S‑Parameters Multiport Network Theory*; *Transmissive‑Type Metagratings with Few Meta‑Atoms for Beam Splitting*; *Impedance‑Based RIS Channel Model and Optimization in Fast‑Fading Environments*; *Direction‑of‑Arrival Estimation by a Programmable Metasurface*; *Empirical Validation of the Impedance‑Based RIS Channel Model in an Indoor Scattering Environment*.

**EPFL** *(off‑list — not in your Top‑50; QS ~#14)* — ~8 papers, the Skrivervik & Fleury labs:
- *Link Budget Estimation for Implantable Antennas: From In‑Body Coupling to Free‑Space Radiation* (Gao, Skrivervik)
- *Tunable Segmented Loop Antenna Reader for Miniaturized Chipless Tag Detection* (Fernández Carnicero, Skrivervik)
- *Series‑Fed Loop Antenna Array Deployable by a Scissors Mechanism* (Ramirez Arroyave, Skrivervik; & Universidad Nacional de Colombia)
- *Reducing Antenna Mutual Coupling Using Current Optimization* (Bartle, Skrivervik; & ClearSpace SA)
- *Plug‑In Plug‑Out Multibeam Dielectric Rod Antenna for Target‑Dedicated mm‑Wave RF‑WPT Applications* (Ahmadi Najafabadi, Skrivervik; joint with ETH Zurich)
- *Characterization of a Metamaterial‑Enabled Waveguide Diplexer for Ka‑Band Satellite Communication Systems* (Bonny; Fleury)
- *SIW Slot Leaky‑Wave Antenna Using Low‑Index Metamaterial* (Jafargholi, Fleury)
- *GPS Interference Cancellation Using Magneto‑Dielectric Metamaterials* (Jafargholi, Fleury)

### EuCAP — zero presence (19/50)
Harvard, UC Berkeley, Columbia, Yale, U Chicago, Johns Hopkins, UCLA, Northwestern, Duke, U Washington‑Seattle, Peking, University of Tokyo, LMU Munich, UCSF, UT Austin, ANU, Karolinska, Heidelberg, WashU St. Louis.
(MIT and UCSD appear only as a Lincoln‑Lab workshop presenter and a keynote, respectively.)

---

## Supporting files (in the conference folders)
- `BioEM/uni_hits.txt`, `EuCAP/uni_hits_eucap.txt` — every raw hit with surrounding context.
- Extracted `*.txt` per year (derived from the PDFs).
