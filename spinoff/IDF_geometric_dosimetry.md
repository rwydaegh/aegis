# Invention Disclosure Form (IDF)

CONFIDENTIAL

---

## DATE

01/04/2026 (filed), revised 15/04/2026

---

## TITLE of the invention (+ possible acronym)

Geometric Dosimetry: Closed-Form Method, Differentiable Engine, and Interactive Platform for Real-Time Computation and Optimization of Electromagnetic Absorption on Human Bodies

Software platform: AEGIS (Adaptive Electromagnetic Geometric Illumination & Safety)

---

## IOF/VALORISATION INFORMATION

IOF/Valorisation responsible: *[to be filled in by IOF/valorisation responsible]*

TTRM Project No.: *[to be filled in by IOF/valorisation responsible]*

---

## 1. Description of the invention

### If you would consider your invention as a solution, what technical problem were you trying to solve?

Regulatory bodies worldwide (ICNIRP, IEEE/FCC) require that wireless systems comply with limits on human electromagnetic exposure. Above 6 GHz, the relevant quantity is the absorbed power density (S_ab): the power deposited per unit area in the skin layer. Below 6 GHz, whole-body specific absorption rate (SAR) is the governing metric.

Computing S_ab by conventional means requires solving Maxwell's equations over the full volume of the human body using numerical methods (FDTD or FEM). At millimetre-wave frequencies, the mesh must resolve the sub-millimetre skin depth across a body spanning roughly one metre. This can require up to 10^12 mesh cells at the highest frequencies. A single simulation at one frequency, one source, and one body orientation takes hours to days on a high-performance computing cluster. Evaluating compliance for a realistic multi-source, multi-frequency, multi-orientation environment is computationally intractable.

Three specific problems were unsolved:

1. No closed-form spatial dosimetry. There was no method to compute a per-point absorption map on a realistic 3D human body without volumetric simulation.

2. No exposure-aware beamforming. For MIMO systems, no method existed to design a beamforming vector that accounts for human absorption without re-running FDTD per candidate precoder.

3. No real-time compliance workflow. Network operators deploying 5G/6G had no way to assess body-specific exposure compliance interactively during network planning. The only options were conservative worst-case exclusion zones (unnecessarily restrictive, reducing network capacity) or expensive FDTD campaigns (impractical at network scale).

### How have others tried to solve this problem? Describe for each solution the functional and/or structural differences with your solution.

FDTD (Finite-Difference Time Domain). FDTD is the regulatory gold standard and discretises Maxwell's equations on a Cartesian grid, stepping them forward in time. It can require up to 10^12 cells at high mmWave frequencies and takes hours to days per single configuration. The method is not differentiable and cannot be used for real-time assessment or gradient-based optimization. *Difference:* the present method replaces the volumetric simulation with a closed-form surface computation, reducing computation from hours to milliseconds, and is differentiable end-to-end.

FEM (Finite Element Method). FEM uses unstructured tetrahedral meshes that reduce cell count versus FDTD, but the thin absorption layer still demands fine surface meshing. Computation times remain hours to days, and the same limitations on differentiability and real-time use apply. *Difference:* same as above.

Layered analytical models (Christ et al. 2006). One-dimensional multi-layer models (skin-fat-muscle) compute absorption for a flat surface patch at a single incidence angle. *Difference:* the present method handles arbitrary 3D body geometry, self-shadowing, multiple incidence directions, and produces full spatial maps.

Empirical transmission coefficients. Several groups observed that a nearly constant transmission coefficient T reproduces FDTD results:
- Kodera et al. (2024) showed SAR_wb = T_tr x A_perp x S_inc / W, reproducing 3D FDTD to within 5% from 10-100 GHz. T_tr was extracted from a 1D slab model. No physical mechanism was identified for its near-constancy.
- Li et al. (2019) showed numerically that transmitted flux is nearly insensitive to incidence angle on a flat skin model from 6 GHz to 1 THz, but did not consider 3D geometry.
- Diao et al. (2024) obtained T ~ 0.52 at 28 GHz from anatomical FDTD.
- Bamba et al. (2012, 2015) [same research group, UGent INTEC-WAVES] measured absorption efficiency eta ~ 0.5 in reverberation chambers, but did not identify the physical origin of this near-constant value.

*Difference:* all these works observed empirically that a nearly constant coefficient works, but none identified the physical mechanism (pseudo-Brewster compensation), derived the coefficient from Fresnel theory, extended the result to spatial maps on 3D bodies, handled polarisation-dependent dosimetry, or built an exposure operator for coherent MIMO beamforming.

SAR matrix for MIMO (Hochwald 2014, Ying 2015-2017). The SAR matrix formulation S (where P_abs = x^H S x) and the QCQP precoder solution were introduced for uplink (handset) SAR at sub-6 GHz. In all works, the SAR matrix entries are calibrated by FDTD simulation with no closed-form content. *Difference:* the exposure operator Q disclosed here has closed-form entries derived from Fresnel theory and body geometry, requires no FDTD calibration, and works for the downlink base-station geometry.

Commercial tools (Sim4Life by ZMT, CST Studio by Dassault, ANSYS HFSS). These tools all implement FDTD or FEM, are not real-time, and are not differentiable. They are desktop-only with expensive licenses (~50-60K/year) and offer no integration with real base station data or 3D environment reconstruction. *Difference:* the platform disclosed here runs in a web browser, computes in milliseconds, integrates real antenna data from government databases, and supports gradient-based optimization.

Summary comparison with closest prior art:

| Capability | Kodera (2024) | Li (2019) | Bamba (2012-15) | Ying (2015-17) | Sim4Life / CST | This invention |
|---|---|---|---|---|---|---|
| Tavg ~ T_0 (angular constancy) | Empirical | Empirical | Empirical | -- | N/A | Derived from Fresnel theory |
| Local S_ab(r) on 3D body | -- | Flat slab only | -- | -- | FDTD (hours) | Closed-form (milliseconds) |
| Exposure operator Q | -- | -- | -- | FDTD-calibrated | FDTD-calibrated | Closed-form from geometry |
| Differentiable | No | No | No | No | No | Yes (JAX end-to-end) |
| Real-time interactive | No | No | No | No | No | Yes (web viewer) |
| Real base station data | No | No | No | No | No | Yes (14 government databases) |
| 3D environment from address | No | No | No | No | No | Yes (OSM, 3D Tiles, terrain) |
| Optimization algorithms | No | No | No | No | Manual | 3 algorithms (placement, tilt/power, precoder) |
| Stochastic channel models | No | No | No | No | No | Yes (3GPP 38.901, 91 presets) |

### Describe the advantage of your solution over the existing solutions.

1. Speed. 10^6 to 10^9 times faster than FDTD. Milliseconds instead of hours. This enables real-time exposure monitoring, network-level compliance, and interactive assessment, none of which are possible with existing methods.

2. Closed-form spatial dosimetry. The first method to produce per-point absorption maps on arbitrary 3D human bodies without numerical simulation. A frequency sweep requires only recomputing T_0 (a lookup table). A body orientation sweep uses the precomputed directivity D(k_hat).

3. Closed-form exposure operator Q. The first exposure operator for MIMO beamforming computed entirely from body geometry and Fresnel theory, without FDTD calibration. Enables exposure-constrained beamformer design (ECBF) with an analytical QCQP solution.

4. Differentiable end-to-end. The entire computation graph (surface geometry, Fresnel coefficients, absorption map, spatial averaging, compliance evaluation) supports automatic differentiation via JAX. This enables gradient-based antenna placement optimization, tilt/power optimization under ICNIRP constraints, and MIMO precoder design. No existing dosimetry method is differentiable.

5. Interactive platform. A deployed web application where a user types a city name, sees real antenna installations from government databases, clicks to place a human body, and gets an ICNIRP compliance assessment in under one second. Multi-user MIMO with multiple body models. Three optimization algorithms. No existing compliance tool offers this workflow.

6. Real-world data integration. The platform ingests real base station data from 14 government databases across the EU and beyond (~293K antennas), classifies antenna types (mMIMO, sector, small cell), assigns radiation patterns from a library of 1,200+ real patterns, reconstructs 3D urban environments from OpenStreetMap and Google 3D Tiles, and feeds all of this into the dosimetry engine. Nothing else connects laboratory dosimetry to operational network compliance.

7. Full frequency range. Valid from 100 MHz to 100 GHz via the T_0/T_bar mechanism. Existing closed-form results were limited to single frequencies or narrow bands.

8. Stochastic channel integration. Full 3GPP TR 38.901 channel generator (91 scenario presets) feeds directly into the dosimetry engine, enabling statistical exposure assessment without deterministic ray tracing.

9. Nine fidelity levels. A composable fidelity ladder from O(1) bounds (level 0) through aggregate directivity (level 1) and incoherent spatial maps (levels 2-6) to coherent MIMO (level 7) and exposure-constrained beamforming (level 8). Each level adds one physics correction. Users select the accuracy-speed trade-off appropriate to their use case.

10. Conservative for compliance. Below 40 GHz, the T_0 approximation underestimates absorbed power. The method never certifies a non-compliant deployment as compliant.

| Property | FDTD/FEM | This invention |
|----------|----------|----------------|
| Computation time | Hours to days | Milliseconds |
| Mesh cells | Up to ~10^12 | ~10^4 triangles (surface only) |
| Real-time capable | No | Yes |
| Multi-source | One simulation per source | Matrix-vector multiply |
| Frequency sweep | One simulation per frequency | Recompute T_0 (lookup) |
| Coherent MIMO | Per-precoder simulation | Closed-form (exposure operator Q) |
| Differentiable | No | Yes (JAX) |
| Interactive web viewer | No | Yes |
| Real base station data | No | 14 government databases |
| Optimization | Manual | Gradient-based (3 algorithms) |

Further technical effect (EPO G 1/19). The invention produces a further technical effect beyond the implementation of software on a computer: it enables real-time assessment of physical electromagnetic absorption in human tissue against regulatory limits (ICNIRP 2020, IEEE C95.1-2019). The output is a measurable physical quantity (absorbed power density in W/m^2) with direct safety and regulatory significance. The optimization methods produce antenna configurations that satisfy physical safety constraints. The environment reconstruction produces physically accurate 3D scene geometry with measured electromagnetic material properties.

### Give a short description of the invention, preferably including a listing of those elements of the invention that are essential to make the invention work, those elements that can be varied and how they can be varied (max. one page).

The method. Two physical insights reduce volumetric dosimetry to a surface-geometric computation:

*Insight 1 (pseudo-Brewster compensation):* For biological tissue (complex refractive index |n| ~ 3-7), the TE and TM Fresnel power transmissions compensate each other. Their unpolarised average remains within 5.6% of the normal-incidence value T_0 over 0-75 degrees. This allows replacing angle-dependent transmission with a single scalar T_0 (= 0.54 for skin at 28 GHz).

*Insight 2 (surface confinement):* Above 6 GHz, the skin depth (< 1 mm) confines all absorption to the surface. Only the body's external shape matters.

These yield the geometric absorption law:

    S_ab(r) = S_inc * T_0 * ReLU[n_hat(r) . (-k_hat)]

Essential elements:
1. A tissue-dependent electromagnetic transmission coefficient (T_0, or the exact angle-dependent Tavg(theta), or the flux-averaged T_bar(f))
2. A surface mesh of the human body with triangle normals
3. Incident wave parameters: power density and propagation direction per source
4. For coherent MIMO: the exposure channel matrix G_tilde and the exposure operator Q = integral of G_tilde^H G_tilde dA
5. For optimization: a differentiable computation graph (JAX) enabling gradient-based search over antenna parameters

Elements that can be varied:
- The transmission coefficient variant: T_0 (constant, fastest), Tavg(theta) (exact, per-triangle), T_bar(f) (flux-averaged, for sub-6 GHz). Different accuracy-speed trade-offs.
- The body mesh complexity: from simple ellipsoids to high-resolution anatomical phantoms (8 phantoms included, plus SMPL-X parametric generation)
- The number of fidelity levels: O(1) bound, O(N) aggregate, O(M_tri * N) spatial, coherent MIMO
- The propagation environment: synthetic paths, stochastic 3GPP channel models (91 presets), or deterministic ray tracing (DiffeRT on GPU with JAX, Sionna RT with OptiX)
- The 3D environment source: OpenStreetMap buildings, Google Photorealistic 3D Tiles, SRTM terrain, GeoJSON, or voxel data
- The base station data source: 14 government APIs (7 EU + 7 non-EU), OpenCellID, or user-specified
- Tissue type and frequency: any tissue with known dielectric properties, 100 MHz to 100 GHz

Extensions:
- Polarisation: exact handling via absorption Stokes vector (P_abs = m . s_inc)
- Sub-6 GHz: replace T_0 with T_bar for exact direction-averaged results at any frequency above 100 MHz
- Coherent MIMO: S_ab(r) = ||G_tilde(r) x||^2. Exposure operator Q. Closed-form exposure-constrained beamformer (ECBF) via QCQP.
- Optimization: antenna placement grid search, tilt/power gradient descent under ICNIRP constraints, MIMO precoder optimization via Adam with projected gradient descent

The software (AEGIS): Python library + web-based interactive 3D platform implementing all of the above. Nine fidelity levels (0-8). Real-time 3D viewer (Flask + React + Three.js) with interactive antenna placement, multi-user MIMO, ICNIRP compliance dashboard, and three optimization algorithms. OpenStreetMap and Google 3D Tiles environment reconstruction. GPU ray tracing via Modal serverless (DiffeRT on T4, Sionna RT on L4). Real base station data from 14 government databases. 1,200+ real antenna patterns. 3GPP TR 38.901 stochastic channel generator with 91 presets. ~33,000 lines Python, ~21,000 lines TypeScript, 2,469 automated tests.

### If possible, provide a figure that shows all features of the invention.

See attached figures from the AEGIS documentation: (1) S_ab heatmap on human phantom (sab_3d_front.png), (2) Fresnel TE/TM compensation curves at 28 GHz (fresnel_curves.png), (3) Mie-theory validation curve (mie_validation.png), (4) Framework error budget (error_budget.png). Additional figures and screenshots of the interactive viewer are available at the project documentation site.

### Does your invention possess disadvantages or limitations? Indicate how they might be overcome.

1. Far-field assumption. Requires source-to-body distance > ~3 wavelengths (~3 cm at 28 GHz). Does not apply to devices pressed against the body. *Can be overcome:* near-field extension under development.

2. Surface absorption assumption below 6 GHz. The local spatial map loses physical meaning below ~6 GHz when multi-layer resonances become significant. *Can be overcome:* total-power results remain valid via T_bar; the local map limitation is inherent to the surface-confinement physics.

3. Diffraction. Geometric optics; diffraction modelling is approximate (GELU smoothing at shadow boundaries). ~10% error on total absorbed power for torso-sized bodies at mmWave. *Can be overcome:* GTD correction layer (partially implemented at fidelity level 6).

4. Tissue property uncertainty. Dielectric properties are uncertain to 10-20%. The framework error (2-6%) is well within this parametric uncertainty. *Inherent to the field.*

5. Ray tracing dependency for realistic environments. Realistic multipath environments need propagation paths from a ray tracer (seconds to minutes), though this is still orders of magnitude faster than FDTD. The stochastic channel mode provides an alternative without ray tracing.

### Describe the development status (concept only, laboratory tested, in vitro/in vivo data, prototype, etc.). Indicate what further development may be necessary.

Status: deployed production software with thorough validation.

The theoretical framework is complete and documented in a monograph (~6,000 lines LaTeX) with all derivations, proofs, and error analysis.

The software (AEGIS v0.28.0) is deployed on a production server:
- Core engine: ~33,000 lines Python, 9 fidelity levels (0-8), JAX differentiable backend
- Web platform: ~21,000 lines TypeScript/React, Three.js 3D rendering
- 2,469 automated tests (golden tests against monograph tables, Mie-theory regression, Hypothesis property-based tests, end-to-end pipeline tests)
- Integrations: DiffeRT and Sionna RT ray tracing (GPU via Modal), 14 government base station databases, 1,200+ antenna patterns (CloudRF), 3GPP TR 38.901 stochastic channel (91 presets), OpenStreetMap, Google 3D Tiles, SRTM terrain
- Infrastructure: Docker deployment, Caddy HTTPS, Sentry error tracking, Umami analytics, CI/CD with GitHub Actions

Validation:
- Mie-theory regression: R_sphere = 0.988 at 28 GHz for lossy spheres
- Golden tests for every table in the monograph
- Property-based tests: S_ab >= 0, energy conservation, ReLU correctness
- Comparison with published empirical data (Bamba, Kodera, Diao, Flintoft, Zhang): framework predictions match independent observations to within 3-8%

Further development needed:
- Journal publication (monograph and summary paper written, not yet submitted)
- Numerical validation against full-wave FDTD on IT'IS anatomical phantoms
- Near-field extension
- Dynamic pose tracking
- Formal IEC/IEEE certification pathway
- Multi-site batch processing for network-scale deployment

---

## 2. Invention disclosure record

### List all past and near-future disclosures of the invention (or parts of it).

| Type | Date and reference |
|------|-------------------|
| Oral presentation(s) at meetings, conferences, companies | None |
| Abstract, poster, proceeding posted, printed, or web-published | None |
| Manuscript submitted for publication (including internet pre-publishing) | Planned: JSAC SI 'Digital Twins for Wireless Networks' (submission deadline May 1, 2026) |
| Manuscript published | None |
| Thesis submitted or defended | Planned: PhD thesis defense before August 2026. Thesis will be publicly available after defense. |
| Report (official or internal) | None |
| News article or feature report | None |
| Information given to a party outside the University WITH NDA/CDA | None |
| Information given to a party outside the University WITHOUT NDA/CDA | None |

The AEGIS software is deployed on a password-protected server accessible only to the inventor. No external parties have been given access. No public demonstrations have been conducted.

The novelty is fully preserved. No anticipated disclosure date has been set. The inventor will coordinate with UGent TechTransfer before any public disclosure. Journal submission is confidential peer review and does not constitute public disclosure.

### Prior art: publications by the inventors most closely related to the invention

1. R. Wydaeghe, S. Shikhantsov, E. Tanghe, G. Vermeeren, L. Martens, W. Joseph, "Hybrid ray-tracing-QuaDRiGa/FDTD method for realistic 28 GHz exposure with 6G CF-MaMIMO in 3D outdoor environments," npj Wireless Technology, vol. 2, no. 13, 2026.
2. R. Wydaeghe, S. Shikhantsov, E. Tanghe, G. Vermeeren, L. Martens, P. Demeester, W. Joseph, "Realistic human exposure at 3.5 GHz and 28 GHz for distributed and collocated MaMIMO in indoor environments using hybrid ray-tracing and FDTD," IEEE Access, vol. 10, pp. 130996-131004, 2022.
3. M. Leeman, R. Wydaeghe et al., "City-scale spatio-temporal modeling of 5G downlink exposure of users and non-users by ray-tracing in a real urban environment," IEEE Access, vol. 13, pp. 30894-30906, 2025.

These publications describe the hybrid ray-tracing/FDTD pipeline that preceded the present invention. The geometric dosimetry method disclosed here replaces the FDTD step with a closed-form surface computation, representing a fundamentally different approach.

### Prior art: publications by others most closely related to the invention

1. Y. Kodera, T. Hikage, and T. Nagaoka, "Whole-body average SAR estimation using surface area and a transmission coefficient at frequencies above 6 GHz," Phys. Med. Biol., vol. 69, 2024.
2. K. Li, K. Sasaki, and S. Watanabe, "Relationship between power density and temperature elevation in human tissue," IEEE Access, vol. 7, 2019.
3. A. Bamba et al., "Experimental assessment of specific absorption rate using room electromagnetics," IEEE Trans. EMC, vol. 54, no. 4, 2012.
4. A. Bamba et al., "Assessing whole-body absorption cross section for diffuse exposure from reverberation chamber measurements," IEEE Trans. EMC, vol. 57, no. 1, 2015.
5. R. M. A. Azzam, "High-index dielectric substrates with nearly constant reflectance," J. Mod. Opt., vol. 62, no. 18, 2015.
6. Z. Ying, D. J. Love, and B. M. Hochwald, "Closed-form capacity-SAR tradeoff for MIMO beamforming," IEEE Trans. Wireless Commun., vol. 14, no. 1, 2015.
7. M. R. Castellanos et al., "Closed-form Fresnel-based approach for 5G mmWave human body exposure assessment," IEEE Access, vol. 8, 2020.
8. I. D. Flintoft et al., "Average absorption cross-section of the human body measured at 1-12 GHz in a reverberant environment," IEEE Trans. AP, vol. 62, no. 5, 2014.
9. S. Shikhantsov et al., "Hybrid ray-tracing/FDTD method for human exposure evaluation of a massive MIMO technology in an industrial indoor environment," IEEE Access, vol. 7, pp. 21020-21031, 2019.

### Is literature screened on a regular basis?

YES

### Keywords:

Absorbed power density, electromagnetic dosimetry, Fresnel transmission, pseudo-Brewster angle, geometric optics, projected area, ambient occlusion, ICNIRP 2020, millimetre-wave, 5G, 6G, MIMO beamforming, exposure operator, SAR, compliance, real-time computation, human phantom, ray tracing, exposure-constrained precoding, differentiable dosimetry, antenna placement optimization, 3GPP channel model, base station database, 3D environment reconstruction, OpenStreetMap, interactive viewer, web platform

### Patents or patent applications of others most closely related to the invention

- US 8,630,596 B2 (Samsung, 2014): "Apparatus and method for controlling specific absorption rate." Device-level SAR control using return-loss sensing. *Distinguished:* device level, empirical sensing, no body-surface geometry computation, no exposure operator.
- US 2022/0377799 A1 (2022): "RF exposure mitigation and beam selection." Heuristic beam selection and power backoff. *Distinguished:* no closed-form dosimetry, no spatial absorption maps, no mathematically optimal precoder.
- WO 2016/195892 A1 (2016): "SAR distribution management for multi-antenna devices." Device-level power control. *Distinguished:* no geometric absorption framework, no Fresnel analysis, no exposure operator.

A formal freedom-to-operate (FTO) search has not yet been conducted.

### Who are the main academic or industrial research groups active in the field?

Industrial:
ZMT Zurich MedTech / Sim4Life (CH), Dassault Systemes / CST (FR), ANSYS / HFSS (US), Ericsson (SE), Nokia (FI), Huawei (CN), Qualcomm (US), SPEAG (CH), Rohde & Schwarz (DE)

Academic:
IT'IS Foundation / ETH Zurich (CH), Chalmers University Bioelectromagnetics Lab (SE), INTEC-WAVES / Ghent University / IMEC (BE), KTH Royal Institute of Technology (SE), University of Lille / TELICE (FR), Telecom Paris / WHIST Lab (FR)

---

## 3. Inventors

Name only those who contributed intellectually to the inventive concept of the invention. Inventorship is not the same as authorship.

### INVENTOR 1 -- CONTACT PERSON for UGent TechTransfer

Name: Robin Wydaeghe
Institution / Dept.: Ghent University -- IMEC / INTEC-WAVES
Address -- work: Technologiepark-Zwijnaarde 126, 9052 Gent
E-mail: robin.wydaeghe@hotmail.com / robin.wydaeghe@ugent.be
TEL.: +32 483 06 90 27
Address -- Home: Fritz de Beulestraat 24, 9000 Ghent, Belgium
Citizenship: Belgian
Contribution to the invention: 100% -- Sole inventor of the theoretical framework (all physical insights, mathematical derivations, proofs, and error analysis) and sole developer of the software platform (AEGIS, ~54,000 lines of code, 2,469 tests, deployed production system)
UGent payroll: YES

*Note on sole inventorship:* The inventor's PhD supervisor, Prof. Wout Joseph, provided general academic guidance but did not contribute to the inventive concepts. The pseudo-Brewster compensation insight, the geometric reduction to surface dosimetry, the connections to integral geometry and computer graphics, the absorption Stokes vector, the exposure operator construction, the differentiable engine architecture, the optimization algorithms, and all mathematical derivations were developed independently by the sole inventor.

---

## 4. Records / Material

### Are lab records available? Are these lab records dated and signed?

The monograph (~6,000 lines LaTeX) serves as the primary technical record with all derivations, proofs, and validation. Git version control history provides timestamped records of all software development (1,150+ commits). Records are not signed in the traditional lab notebook sense, but all changes are tracked with cryptographic hashes in Git.

### At what site(s) was the research conducted that led to the invention?

Technologiepark-Zwijnaarde 126, 9052 Gent (UGent/IMEC iGent tower).

### Does the invention incorporate any material obtained from companies or institutions outside the University?

No. Open-source software tools (Sionna, DiffeRT, NumPy, React, Three.js) are used as dependencies but do not form part of the invention. Base station data is from public government APIs. Antenna patterns are from CloudRF under standard commercial terms.

---

## 5. FUNDING

### Past and current funding that led to the invention

| Agency or Sponsor | Grant/Contract (Type & Ref. Nr.) | Term |
|---|---|---|
| None | N/A | N/A |

This invention arose spontaneously and was not funded by any specific research project, grant, or contract. The inventor's PhD position at UGent/IMEC is the only relevant employment relationship. Standard UGent IP regulations apply.

### Future funding that will further develop/improve the invention

No external funding sources have been identified. The invention is sufficiently complete for commercialisation without additional research funding. Further development (near-field extension, numerical validation, certification) can be pursued within the current PhD or a spin-off context.

---

## 6. COLLABORATION

### Is the invention the result of a collaborative project involving another party?

No. The geometric dosimetry method, the exposure operator, and the AEGIS platform were developed independently by the sole inventor. The inventor's prior work on hybrid ray-tracing/FDTD methods (with S. Shikhantsov and others at INTEC-WAVES) provided motivation for seeking a faster alternative to FDTD, but the inventive concepts disclosed here are entirely new and were not part of any collaborative project.

### Is there a contract/agreement? If yes, please provide contract number:

No. No collaborations, subcontracts, or material transfer agreements are in place. No external party has access to unpublished details of the framework or the software.

---

## 7. AUTHORSHIP / COPYRIGHT

### Is there any expression of this invention through software?

Yes. AEGIS: approximately 54,000 lines of Python and TypeScript implementing all aspects of the invention. This includes: the core computation engine with nine fidelity levels and JAX differentiable backend, the coherent MIMO exposure operator and ECBF solver, three optimization algorithms, 3GPP stochastic channel generator, base station data pipeline for 14 countries, 3D environment reconstruction from OpenStreetMap and Google 3D Tiles, GPU ray tracing integration, and a production web-based interactive 3D platform with real-time compliance assessment.

### What is the purpose of the software?

Fully functional end-user system. It implements the complete invention from O(1) compliance bounds through full spatial dosimetry maps to exposure-constrained MIMO beamforming and antenna placement optimization, with a production-quality web-based 3D interface, real base station data, and GPU-accelerated ray tracing. Deployed on a production server with 2,469 automated tests.

### Is the software a derivative or improvement of any existing source code?

No. The software was written from scratch by the inventor based on the theoretical framework described in this disclosure. Standard open-source libraries are used as infrastructure dependencies (NumPy, SciPy, JAX, React, Three.js, Flask) under their respective open-source licences.

---

## 8. COMMERCIALIZATION POTENTIAL

### In your opinion, what kind of commercial applications could be derived from your invention and how easy/feasible would it be to bring a product to the market?

1. Interactive EMF compliance platform (primary market). Telecom operators deploying 5G/6G must demonstrate regulatory compliance. Current practice uses either conservative worst-case calculations (unnecessarily restrictive exclusion zones, reduced network capacity) or expensive FDTD simulations (impractical at network scale). This invention enables a web-based platform where an engineer types a location, sees real antenna installations, places human bodies, and gets ICNIRP compliance results in under one second. The platform already exists and is deployed.

2. Antenna placement and tilt optimization. The differentiable engine enables gradient-based optimization: "place this antenna such that nobody exceeds ICNIRP limits" solved by gradient descent. Telecom operators placing 5G small cells need exactly this. Three optimization algorithms are implemented and operational.

3. Exposure-aware beamforming for MIMO. The exposure operator Q enables the first beamforming designs that account for human absorption. The closed-form ECBF precoder maximises signal quality while guaranteeing compliance. Relevant for dense urban deployments and indoor small cells. Multi-user MIMO with multiple body models is operational.

4. Real-time exposure monitoring / digital twin. Millisecond computation enables continuous real-time monitoring. Combined with real base station data and 3D environment reconstruction from OpenStreetMap, this creates a digital twin of the electromagnetic environment for any city.

5. Statistical exposure assessment. The 3GPP stochastic channel integration enables Monte Carlo compliance: "what is the 95th percentile exposure in this scenario class?" without deterministic ray tracing. This addresses the regulatory question of typical vs. worst-case exposure.

6. Standards and academic licensing. The nine-level fidelity ladder and the conservative compliance property (T_0 underestimates below 40 GHz) make the framework a candidate for adoption in exposure assessment standards (IEC 63195, IEEE C95.1).

Bringing the product to market is feasible. The software is already deployed, production-quality, and functional with 2,469 automated tests. It can be offered as a SaaS platform (per-seat subscription), licensed as an API to network planning vendors, or commercialised via a spin-off company.

### Which companies could be interested in your invention?

Infrastructure vendors: Ericsson (SE), Nokia (FI), Huawei (CN) -- network planning, beamforming design
Operators: Proximus (BE), KPN (NL), Orange (FR), Deutsche Telekom (DE), Vodafone (UK) -- deployment compliance
Network planning software: ATDI (FR), Forsk (FR), iBwave (CA) -- integration into planning tools
Chipset vendors: Qualcomm (US), MediaTek (TW) -- exposure-aware beamforming at chipset level
Simulation vendors: ZMT / Sim4Life (CH), Dassault / CST (FR) -- complementary real-time module
Device OEMs: Samsung, Apple, Xiaomi -- device compliance screening
Test houses: SPEAG (CH), UL, TUV -- measurement and compliance
Regulators: BIPT (BE), Agentschap Telecom (NL), ANFR (FR), BNetzA (DE) -- real-time monitoring

---

## 9. SUGGESTED PATENT CLAIMS

*[This section is not part of the standard IDF template but is included to assist the patent attorney in drafting claims.]*

### Independent claims

Claim 1 (Core spatial dosimetry method). A computer-implemented method for determining absorbed power density on a body surface, comprising:
(a) obtaining a surface mesh of at least a portion of a human body, the surface mesh comprising a plurality of surface elements each having an outward-facing surface normal;
(b) obtaining a tissue-dependent electromagnetic transmission coefficient for a frequency of interest;
(c) for each of one or more incident electromagnetic waves, each wave characterised by a propagation direction and a power density: computing, for each surface element, an incidence factor from the dot product of the surface normal with the negated propagation direction; applying a rectified linear activation to the incidence factor;
(d) for each surface element, multiplying the activated incidence factor by the transmission coefficient and the power density to obtain the absorbed power density at that surface element.

Claim 2 (Exposure operator method). A computer-implemented method for exposure-constrained MIMO precoding, comprising:
(a) for each propagation path from a plurality of antenna elements to a body surface, constructing an exposure channel matrix entry incorporating a Fresnel transmission coefficient, a depth-decay weighting factor, and a phase propagation term;
(b) computing an exposure operator as a surface integral of the Hermitian outer product of the exposure channel matrix, yielding a Hermitian positive-semidefinite matrix;
(c) solving a quadratically constrained optimisation to determine a precoding vector that maximises signal quality subject to an absorption constraint derived from the exposure operator.

Claim 3 (Differentiable dosimetry optimization method). A computer-implemented method for optimising antenna deployment parameters to satisfy electromagnetic exposure constraints, comprising:
(a) computing absorbed power density on a body surface using the method of claim 1 via a differentiable computation graph;
(b) computing a gradient of a loss function incorporating a regulatory exposure limit with respect to one or more antenna parameters;
(c) iteratively updating the antenna parameters using the computed gradient to minimise peak exposure or maximise compliance margin.

Claim 4 (Integrated compliance assessment system). A dosimetry computation system comprising:
(a) a base station data ingestion module that retrieves antenna installation parameters from one or more government databases;
(b) a 3D environment reconstruction module that generates a ray-traceable scene mesh from geographic data sources;
(c) a propagation path computation module that generates multipath propagation data via ray tracing or stochastic channel models;
(d) a dosimetry computation engine implementing the method of claim 1;
(e) a compliance evaluation module that assesses the computed absorption against regulatory limits;
(f) an interactive web-based interface presenting the results in real-time on a 3D visualisation.

Claim 5 (Medium). A non-transitory computer-readable medium storing instructions for performing the method of any of claims 1-3.

### Dependent claims

Claim 6. The method of claim 1, wherein the transmission coefficient is the normal-incidence Fresnel power-absorption coefficient T_0 derived from the pseudo-Brewster compensation property of biological tissue.

Claim 7. The method of claim 1, wherein the transmission coefficient is the exact angle-dependent Tavg(theta), computed per surface element from TE and TM Fresnel equations.

Claim 8. The method of claim 1, further comprising computing an exposure fraction per surface element using ambient-occlusion computation to account for self-shadowing.

Claim 9. The method of claim 1, further comprising computing an absorption Stokes vector for exact polarisation-dependent dosimetry.

Claim 10. The method of claim 1, wherein the rectified linear activation is replaced by a smooth approximation (GELU) incorporating a surface curvature-dependent width parameter to model diffraction at shadow boundaries.

Claim 11. The method of claim 1, further comprising evaluating the absorbed power density against a frequency-dependent ICNIRP 2020 regulatory limit and generating a compliance assessment with margin in decibels.

Claim 12. The method of claim 3, wherein the antenna parameters comprise at least one of: antenna position, antenna tilt angle, transmit power, or MIMO precoding vector.

Claim 13. The method of claim 3, wherein the loss function comprises a penalty term that is quadratic in the excess of peak spatially-averaged absorbed power density over a regulatory limit.

Claim 14. The system of claim 4, wherein the propagation path computation module comprises a stochastic channel generator implementing 3GPP TR 38.901 cluster-based multipath with configurable scenario presets.

Claim 15. The system of claim 4, wherein the 3D environment reconstruction module generates scene geometry from OpenStreetMap building data, terrain elevation data, or photogrammetric 3D tile data, with per-surface electromagnetic material properties.

---

## SIGNATURES

Signing this document indicates that (a) the Invention Disclosure Form is complete and accurate, and (b) the inventor recognises that commercialisation of research results is a legal obligation (Codex Hoger Onderwijs, Art. II.285) and will cooperate with UGent TechTransfer.

______________________          _________________          __________
Inventor's name                 Signature                   Date

Robin Wydaeghe                  _________________          __/__/2026
