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
- Bamba et al. (2012, 2015) [same research group, UGent INTEC-WAVES] measured absorption efficiency η ~ 0.5 in reverberation chambers, but did not identify the physical origin of this near-constant value.

*Difference:* all these works observed empirically that a nearly constant coefficient works, but none identified the physical mechanism (pseudo-Brewster compensation), derived the coefficient from Fresnel theory, extended the result to spatial maps on 3D bodies, handled polarisation-dependent dosimetry, or built an exposure operator for coherent MIMO beamforming.

SAR matrix for MIMO (Hochwald 2014, Ying 2015-2017). The SAR matrix formulation S (where P_abs = x^H S x) and the QCQP precoder solution were introduced for uplink (handset) SAR at sub-6 GHz. In all works, the SAR matrix entries are calibrated by FDTD simulation with no closed-form content. *Difference:* the exposure operator Q disclosed here has closed-form entries derived from Fresnel theory and body geometry, requires no FDTD calibration, and works for the downlink base-station geometry.

Commercial tools (Sim4Life by ZMT, CST Studio by Dassault, ANSYS HFSS). These tools all implement FDTD or FEM, are not real-time, and are not differentiable. They are desktop-only with expensive module-based licensing: Sim4Life is priced per module (solver, phantom libraries, sub-gridding, each a separate seat), and a typical research or industrial configuration runs into the tens of thousands of dollars per year once a useful mix is combined. Dedicated measurement hardware (SPEAG DASY8 class) is a separate six-figure capital investment. None of these tools integrate real base station data or 3D environment reconstruction. *Difference:* the platform disclosed here runs in a web browser, computes in milliseconds, integrates real antenna data from government databases, and supports gradient-based optimization.

Summary comparison with closest prior art:

| Capability | Kodera (2024) | Li (2019) | Bamba (2012-15) | Ying (2015-17) | Sim4Life / CST | This invention |
|---|---|---|---|---|---|---|
| T_avg ~ T_0 (angular constancy) | Empirical | Empirical | Empirical | -- | N/A | Derived from Fresnel theory |
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

4. Differentiable end-to-end. The entire computation graph (surface geometry, Fresnel coefficients, absorption map, spatial averaging, compliance evaluation) supports automatic differentiation via JAX. This enables gradient-based antenna placement optimization, tilt/power optimization under ICNIRP constraints, and MIMO precoder design. To the inventor's knowledge, no published dosimetry framework offers end-to-end differentiability.

5. Interactive platform. A deployed web application where a user types a city name, sees real antenna installations from government databases, clicks to place a human body, and gets an ICNIRP compliance assessment in under one second. Multi-user MIMO with multiple body models. Three optimization algorithms. No commercial or open-source compliance tool known to the inventor offers this workflow.

6. Real-world data integration. The platform ingests real base station data from 14 government databases across the EU and beyond (~293K antennas), classifies antenna types (mMIMO, sector, small cell), assigns radiation patterns from a library of 1,200+ real patterns, reconstructs 3D urban environments from OpenStreetMap and Google 3D Tiles, and feeds all of this into the dosimetry engine. The inventor is not aware of another tool that connects laboratory dosimetry to operational network compliance at this data scale.

7. Full frequency range. Valid from 100 MHz to 100 GHz via the T_0/T_bar mechanism. Existing closed-form results were limited to single frequencies or narrow bands.

8. Stochastic channel integration. Full 3GPP TR 38.901 channel generator (91 scenario presets) feeds directly into the dosimetry engine, enabling statistical exposure assessment without deterministic ray tracing.

9. Nine fidelity levels. A composable fidelity ladder from O(1) bounds (level 0) through aggregate directivity (level 1) and incoherent spatial maps (levels 2-6) to coherent MIMO (level 7) and exposure-constrained beamforming (level 8). Each level adds one physics correction. Users select the accuracy-speed trade-off appropriate to their use case.

10. Conservative for compliance. Below 40 GHz, the T_0 approximation underestimates absorbed power. The method never certifies a non-compliant deployment as compliant.

11. Solid-angle view-factor whole-body absorption (near-field result). For a point source at d > 3*λ, the total absorbed power reduces to P_abs = P_t * T_0 * Ω_body(r_s) / (4*π), where Ω_body(r_s) is the solid angle subtended by the visible front-facing body surface as seen from the source. For a directive antenna the integral carries the gain pattern as a weight. This is structurally identical to the emissive view-factor formula of radiative heat transfer, with T_0 replacing emissivity. Whole-body compliance becomes a pure geometric integral on a triangle mesh, for which efficient algorithms already exist in the radiometry and computer-graphics literature.

12. Spherical-harmonic antenna-body decoupling (near-field result). For any fixed source position r_s, the absorbed power decomposes as P_abs = (T_0 / 4*π) * sum_{lm} g_lm * Γ_lm(r_s), where Γ_lm(r_s) is a precomputed body-response coefficient and g_lm are the spherical-harmonic coefficients of the antenna gain. The lookup table is approximately 50 MB per body at phone-scale resolution (1 cm grid, 50 cm extent, L up to 6). Any candidate antenna design at a fixed position is then evaluated in O(L^2) operations by a dot product. Standard FDTD/FEM workflows re-run per configuration and do not offer this pre-computation.

13. Differentiability in the near field. The point-source absorption law is smooth in the source position r_s, in the antenna gain pattern (through g_lm or directly), and in all coherent-MIMO variables. Ω_body(r_s) and Γ_lm(r_s) are themselves smooth in r_s. Device pre-compliance therefore becomes a gradient-based design problem rather than a worst-case full-wave sweep. To the inventor's knowledge, this differentiability is not available in any published near-field dosimetry framework or in commercial full-wave tools.

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

*Insight 1 (pseudo-Brewster compensation):* For biological tissue (|n| ~ 3-7), the TE and TM Fresnel power transmissions compensate each other. Their unpolarised average is within 5.6% of the normal-incidence value T_0 over 0-75 degrees. This allows replacing angle-dependent transmission with a single scalar T_0 (= 0.54 for skin at 28 GHz).

*Insight 2 (surface confinement):* Above 6 GHz, the skin depth (< 1 mm) confines all absorption to the surface. Only the body's external shape matters.

These yield the geometric absorption law:

    S_ab(r) = S_inc(r) * T_0 * ReLU[n_hat(r) . (-k_hat(r))]

The same equation covers far-field and radiating-near-field illumination. In the far-field limit (base stations, distant transmitters) S_inc and k_hat are constant across the body and the formula reduces to the plane-wave form.

In the radiating near-field at source distance d > 3*λ (3.2 cm at 28 GHz, 1.5 cm at 60 GHz, 0.9 cm at 100 GHz), S_inc(r) = P_t * G(k_hat(r)) / (4*π*d(r)^2) and k_hat(r) = (r - r_s)/d(r) vary over the body surface. The pointwise law, the spatial map, total absorbed power, the exposure operator Q, and the ECBF precoder are all unchanged. This is the regime that governs device pre-compliance under IEC/IEEE 63195-2. Only the reactive near-field (d < λ/(2*π), at most 1.7 mm at 28 GHz) falls outside this framework and requires full-wave simulation.

Two integrated near-field results follow from the pointwise law (derived in full in the monograph, summarised under "Advantages" above). First, a solid-angle view-factor formula P_abs = P_t T_0 Ω_body(r_s)/(4*π) for whole-body absorbed power, structurally identical to radiative-heat-transfer view factors. Second, a spherical-harmonic antenna-body decoupling Γ_lm(r_s) that reduces per-configuration antenna-pattern evaluation to a ~50 MB lookup and an O(L^2) dot product. Both are differentiable in r_s, in antenna-pattern parameters g_lm, and in body-pose variables.

Essential elements:

1. A tissue-dependent transmission coefficient (T_0, or T_avg(θ), or T_bar(f))
2. A human-body surface mesh with triangle normals
3. Incident wave parameters: power density and propagation direction per source (body-constant for far field, derived from r_s and the antenna gain pattern G(u_hat) for near-field point sources)
4. For coherent MIMO: the exposure channel matrix G_tilde and exposure operator Q = integral of G_tilde^H G_tilde dA (the same construction applies in both regimes)
5. For optimization: a differentiable computation graph (JAX) over antenna parameters
6. For fast device evaluation: the precomputed body-response tables Ω_body(r_s) and Γ_lm(r_s)

Elements that can be varied:
- Transmission coefficient variant: T_0, T_avg(θ), or T_bar(f) (accuracy-speed trade-offs)
- Body mesh: simple ellipsoids through high-resolution phantoms (8 phantoms plus SMPL-X parametric generation)
- Fidelity level: O(1) bound, O(N) aggregate, O(M_tri * N) spatial, coherent MIMO
- Propagation environment: synthetic paths, stochastic 3GPP channel models (91 presets), or deterministic ray tracing (DiffeRT on GPU with JAX, Sionna RT with OptiX)
- 3D environment source: OpenStreetMap, Google Photorealistic 3D Tiles, SRTM terrain, GeoJSON, or voxel data
- Base station data: 14 government APIs (7 EU + 7 non-EU), OpenCellID, or user-specified
- Tissue type and frequency: any tissue with known dielectric properties, 100 MHz to 100 GHz
- Source distance: unified treatment of far-field (base stations) and radiating-near-field sources at d > 3*λ (devices at typical body proximity: phones, tablets, laptops, AR headsets). Reactive near-field excluded. Intermediate range λ/(2*π) <= d <= 3*λ, relevant to close wearables, is the subject of ongoing FDTD-matched validation.

Extensions:
- Polarisation: exact handling via absorption Stokes vector (P_abs = m . s_inc)
- Sub-6 GHz: T_bar replaces T_0 for exact direction-averaged results from 100 MHz
- Coherent MIMO: S_ab(r) = ||G_tilde(r) x||^2. Closed-form exposure-constrained beamformer (ECBF) via QCQP.
- Optimization: antenna placement grid search, tilt/power gradient descent under ICNIRP constraints, MIMO precoder optimization via Adam with projected gradient descent
- Uplink exposure operator for device MIMO: the same Q-operator construction applies to the handset-side uplink with the point-source Green's function replacing the far-field channel. This gives a closed-form exposure-constrained precoder (ECBF) for handset mmWave MIMO without FDTD recalibration. The inventor is not aware of a prior closed-form uplink ECBF that accounts for near-field body absorption.

### If possible, provide a figure that shows all features of the invention.

The interactive viewer at https://aegis.waves-ugent.be shows all features of the invention in a live, regularly updated deployment. The platform can be explored interactively: place antennas, compute dosimetry heatmaps, run MIMO scenarios, and assess ICNIRP compliance in real time. The deployment is password-protected. Contact the inventor for current credentials.

### Does your invention possess disadvantages or limitations? Indicate how they might be overcome.

1. Reactive near-field exclusion. The pointwise absorption law is not valid for sources inside the reactive-near-field boundary d < λ/(2*π) (1.7 mm at 28 GHz, 0.8 mm at 60 GHz, 14 mm at 3.5 GHz). In this regime evanescent fields and antenna-body impedance coupling require full-wave simulation. The radiating-near-field regime d > 3*λ is covered by the point-source extension with a single unified absorption law. The intermediate range λ/(2*π) <= d <= 3*λ, relevant to wearables and on-body devices, is the subject of ongoing FDTD-matched validation. Extension to that range is a software and validation task rather than a new invention.

2. Surface absorption assumption below 6 GHz. The local spatial map loses physical meaning below ~6 GHz when multi-layer resonances become significant. *Can be overcome:* total-power results remain valid via T_bar. The local map limitation is inherent to the surface-confinement physics.

3. Diffraction. Geometric optics. Diffraction modelling is approximate (GELU smoothing at shadow boundaries). ~10% error on total absorbed power for torso-sized bodies at mmWave. *Can be overcome:* GTD correction layer (partially implemented at fidelity level 6).

4. Tissue property uncertainty. Dielectric properties are uncertain to 10-20%. The framework error (2-6%) is well within this parametric uncertainty. *Inherent to the field.*

5. Ray tracing dependency for realistic environments. Realistic multipath environments need propagation paths from a ray tracer (seconds to minutes), though this is still orders of magnitude faster than FDTD. The stochastic channel mode provides an alternative without ray tracing.

### Describe the development status (concept only, laboratory tested, in vitro/in vivo data, prototype, etc.). Indicate what further development may be necessary.

Status: deployed production software with thorough validation.

The theoretical framework is complete and documented in a monograph (~6,000 lines LaTeX) with all derivations, proofs, and error analysis.

The software (AEGIS v0.28.0) is deployed on a production server at https://aegis.waves-ugent.be (password-protected, regularly updated):
- Core engine: ~33,000 lines Python, 9 fidelity levels (0-8), JAX differentiable backend
- Web platform: ~21,000 lines TypeScript/React, Three.js 3D rendering
- 2,469 automated tests (golden tests against monograph tables, Mie-theory regression, Hypothesis property-based tests, end-to-end pipeline tests)
- Integrations: DiffeRT and Sionna RT ray tracing (GPU via Modal), 14 government base station databases, 1,200+ real antenna patterns, 3GPP TR 38.901 stochastic channel (91 presets), OpenStreetMap, Google 3D Tiles, SRTM terrain
- Infrastructure: Docker deployment, Caddy HTTPS, Sentry error tracking, Umami analytics, CI/CD with GitHub Actions

Validation:
- Mie-theory regression: R_sphere = 0.988 at 28 GHz for lossy spheres
- Golden tests for every table in the monograph
- Property-based tests: S_ab >= 0, energy conservation, ReLU correctness
- Comparison with published empirical data (Bamba, Kodera, Diao, Flintoft, Zhang): framework predictions match independent observations to within 3-8%

Further development needed:
- Journal publication (monograph and summary paper written, not yet submitted)
- Numerical validation against full-wave FDTD on IT'IS anatomical phantoms, prioritising the IEC/IEEE 63195-2 distance range (5-200 mm, 6-300 GHz) and the on-body wearable regime (d < 3*λ)
- Reference software implementation of the near-field point-source mode (Eq. S_ab(r) with spatially varying inputs), the solid-angle/view-factor formula, and the Γ_lm(r_s) fast pre-compliance primitive. Framework is fully specified and derived in the monograph. Code is on the 2026-2027 AEGIS roadmap, aligned with the IEC/IEEE 63195-2 2026 draft cycle.
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
| Manuscript submitted for publication (including internet pre-publishing) | None |
| Manuscript published | None |
| Thesis submitted or defended | Planned: PhD thesis defense before August 2026. Thesis will be publicly available after defense. |
| Report (official or internal) | None |
| News article or feature report | None |
| Information given to a party outside the University WITH NDA/CDA | None |
| Information given to a party outside the University WITHOUT NDA/CDA | None |

The AEGIS software is deployed on a password-protected server accessible only to the inventor. No external parties have been given access. No public demonstrations have been conducted.

The novelty is fully preserved. No anticipated disclosure date has been set. The inventor will coordinate with UGent TechTransfer before any public disclosure.

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

No closely related patents were identified. The existing patent landscape addresses device-level SAR control (e.g. power backoff, beam selection at the handset) rather than base-station-side spatial dosimetry on body surfaces. A formal freedom-to-operate search has not yet been conducted. It is expected to be carried out by UGent-appointed patent counsel prior to national-phase entry, covering at minimum device-OEM (Qualcomm, Apple, Samsung, Nokia, Ericsson) and simulation-vendor (ZMT, Dassault, ANSYS) portfolios.

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

No. Open-source software tools (Sionna, DiffeRT, NumPy, React, Three.js) are used as dependencies but do not form part of the invention. Base station data is from public government APIs.

---

## 5. FUNDING

### Past and current funding that led to the invention

| Agency or Sponsor | Grant/Contract (Type & Ref. Nr.) | Term |
|---|---|---|
| None | N/A | N/A |

This invention arose spontaneously and was not funded by any specific research project, grant, or contract. The inventor's PhD position at UGent/IMEC is the only relevant employment relationship. Standard UGent IP regulations apply.

### Future funding that will further develop/improve the invention

No external funding sources have been identified. The invention is sufficiently complete for commercialisation without additional research funding. Further development (near-field software implementation, FDTD validation across the IEC/IEEE 63195-2 distance range, certification) can be pursued within the current PhD or a spin-off context.

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

Fully functional end-user system. It implements the incoherent and coherent MIMO framework (fidelity levels 0-8) under far-field and locally-plane-wave illumination: O(1) compliance bounds through full spatial dosimetry maps, exposure-constrained MIMO beamforming, and antenna placement optimization. The production-quality web-based 3D interface, real base-station data pipeline (14 government databases), and GPU-accelerated ray tracing are all deployed. 2,469 automated tests pass. The near-field point-source mode, the solid-angle/view-factor formula, and the spherical-harmonic antenna-body decoupling Γ_lm(r_s) are specified and derived in the monograph and form part of the disclosed invention. Reference software implementation is on the 2026-2027 AEGIS roadmap, aligned with the IEC/IEEE 63195-2 2026 draft cycle. The disclosure is enabling: a skilled person can implement each near-field primitive from the monograph derivations.

### Is the software a derivative or improvement of any existing source code?

No. The software was written from scratch by the inventor based on the theoretical framework described in this disclosure. Standard open-source libraries are used as infrastructure dependencies (NumPy, SciPy, JAX, React, Three.js, Flask) under their respective open-source licences.

---

## 8. COMMERCIALIZATION POTENTIAL

### In your opinion, what kind of commercial applications could be derived from your invention and how easy/feasible would it be to bring a product to the market?

1. Millimetre-wave device pre-compliance (primary market). Every 5G/6G-capable phone, laptop, tablet, AR headset, and wearable must demonstrate compliance with absorbed power density limits above 6 GHz under IEC/IEEE 63195-2 and equivalent national rules. Measurement at mmWave requires robotic near-field scanning (SPEAG DASY8 class), so the pre-compliance iteration loop is driven by simulation. Current practice runs FDTD on each design candidate. Each FDTD run takes hours, so only a small number of device, beam, and pose configurations can be evaluated per product cycle.

The geometric dosimetry engine replaces the FDTD step for radiating-near-field scenarios (d > 3*λ) with a closed-form computation in milliseconds, backed by the solid-angle view-factor formula for whole-body absorbed power and the Γ_lm(r_s) precomputed body-response table for fast antenna-design sweeps at fixed source position. Gradient-based antenna design, not available in any full-wave tool, lets a designer move an array element to minimise peak APD while preserving beam gain.

The engine targets the full IEC/IEEE 63195-2 range (6 GHz to 300 GHz). Its present-day locally-plane-wave validity threshold d > 3*λ covers the majority of the standard's 5-200 mm device-to-body distance range at mmWave frequencies (d > 32 mm at 28 GHz, d > 15 mm at 60 GHz, d > 9 mm at 100 GHz) and the upper end at sub-mmWave (d > 150 mm at 6 GHz). Closer-range coverage (the band λ/(2*π) < d < 3*λ) is the subject of ongoing FDTD-matched validation, with a monograph-derived theoretical extension already in place.

Near-field differentiability enables several design workflows that full-wave tools cannot offer:

- Device antenna placement: minimise peak spatially-averaged APD jointly over element positions and per-element weights across typical user poses. Gradient descent replaces the "move an element, re-run FDTD" iteration loop.
- Array design co-optimization: solve for antenna-gain spherical-harmonic coefficients g_lm that maximise beam gain subject to a peak-APD constraint at a grid of source positions, via a QCQP-like coupled antenna-body formulation.
- On-device beam selection: pick the beam that maximises link quality subject to a live APD constraint given current estimated body proximity r_s. The gradient of P_abs with respect to the precoding vector gives the ECBF update rule.
- Pose-robust compliance: optimise a design to minimise worst-case APD over a distribution of plausible user poses (phone-to-ear, phone-to-hand, tablet-on-lap), differentiating through r_s and body-mesh parameters (SMPL-X shape coefficients β).
- On-body wearables (once validated for d < 3*λ): the same gradient machinery extends to smartwatches, earbuds, and AR-headset temples, where r_s is fixed by the product form factor but array layout is a design variable.
- Uplink MIMO ECBF: a handset MIMO transmitter precoded in closed form via the near-field exposure operator Q(r_s). Analogous to the downlink-MIMO ECBF but for device-to-base-station uplink, the regime where mmWave handset APD regulation is most acute.

The commercial asymmetry between device pre-compliance (uplink, near-field) and base-station compliance (downlink, far-field) is structural. Device OEMs face a per-product regulatory gate at every launch, with shipment volumes in the millions and recertification budgets that for major OEMs are plausibly in the seven-figure range per program (exact figures are not public). Operators, by contrast, rely on conservative worst-case exclusion zones and in-situ measurement and have limited present incentive for body-specific modelling. The patent's near-field claims therefore sit on the side of the value chain that pays for computational pre-compliance today. The IEC/IEEE 63195-2 2026 edition (currently at draft stage) is the immediate standards window through which geometric near-field methods can be named as an accepted fast computational procedure alongside FDTD and FEM.

2. Integration with the Sim4Life and DASY ecosystem. The engine is a pre-screening layer above full-wave FDTD (ZMT Sim4Life, Dassault CST Studio) and above measurement hardware (SPEAG DASY8, cSAR3D). A compliance engineer runs 10,000 geometric evaluations in an hour. The worst 20 configurations are then passed to Sim4Life for full-wave validation. The final design is measured on DASY. Each Sim4Life seat gains value rather than being replaced. The engine reads the IT'IS Foundation v5.0 Gabriel tissue database and outputs compliance quantities in the formats Sim4Life uses.

3. Standards alignment. IEC/IEEE 63195-2 (computational procedure for device APD, 6 GHz to 300 GHz) has its 2026 edition currently in draft. The 2022 edition permits FDTD and FEM. The geometric method satisfies the standard's conservatism requirement (T_0 underestimates absorbed power below 40 GHz) and its validation requirement (matched within 3-8% against published reference data). Inclusion in the 2026 edition as an accepted fast method is an explicit target. IEC 62232:2025 (base stations, 110 MHz to 300 GHz, 4th edition, September 2025) permits computational methods including ray tracing. IEEE C95.3-2021 is the US parallel. ITU-R Report SM.2452-1 (July 2022) is the globally referenced 5G measurement methodology. Wout Joseph (INTEC-WAVES, UGent) is an active participant in these standards committees. This participation is an academic role rather than a formal AEGIS asset and any contribution of the geometric method to standard text would follow the standard route of technical merit, committee review, and consensus vote. It is noted here because the route from a new computational procedure to named acceptance in an IEC/IEEE document normally requires a sponsor already inside the committee, which is in place.

4. Base-station and network compliance. Telecom operators deploying 5G/6G must demonstrate ICNIRP 2020 and IEC 62232:2025 compliance per site. Current practice uses zone-based calculators (IXUS, MVG EMF Visual) or field measurement (Narda SRM-3006). The engine produces body-specific compliance reports for sites that fail conservative zone checks, allowing operators to recover transmit power that would otherwise be lost to over-conservative exclusion zones. Real base station data from 14 government databases is already ingested.

5. Antenna placement and tilt optimization. The differentiable engine enables gradient-based optimization: "place this antenna such that nobody exceeds ICNIRP limits" solved by gradient descent. Three optimization algorithms are implemented and operational.

6. Exposure-aware beamforming for MIMO. The exposure operator Q enables beamforming designs that account for human absorption without FDTD recalibration. The closed-form ECBF precoder maximises signal quality while guaranteeing compliance. Relevant for dense urban deployments and indoor small cells. Multi-user MIMO with multiple body models is operational.

7. Statistical exposure assessment. The 3GPP TR 38.901 stochastic channel integration feeds directly into the dosimetry engine, enabling Monte Carlo compliance ("what is the 95th percentile exposure in this scenario class?") without deterministic ray tracing.

8. Academic licensing. The nine-level fidelity ladder, the differentiable backend, and the 100 MHz to 100 GHz coverage make the framework a candidate reference implementation for research groups in dosimetry, antenna design, and 6G systems. A free or low-cost academic tier generates the citations and standards-body recognition that underwrite commercial adoption.

Bringing the product to market is feasible. The software is already deployed, production-quality, and functional with 2,469 automated tests. It can be commercialised as a pre-compliance SaaS for device OEMs, as a licensing integration with Sim4Life, as a per-seat subscription for base-station compliance teams, as an API into network planning suites, and as a free academic tier.

### Which companies could be interested in your invention?

Device OEMs: Apple (US), Samsung (KR), Xiaomi (CN), OPPO (CN), Vivo (CN), Huawei (CN), Google (US), OnePlus (CN), Motorola / Lenovo (US/CN), Nothing (UK) -- mmWave and future 6G device pre-compliance
Simulation vendors: ZMT / Sim4Life (CH), Dassault / CST (FR), ANSYS HFSS (US), Remcom (US) -- integration and licensing partners for fast pre-compliance above full-wave FDTD
Chipset vendors: Qualcomm (US), MediaTek (TW) -- reference design pre-compliance and exposure-aware beamforming at chipset level
Test labs: SPEAG (CH), Eurofins E&E, UL (US), TUV (DE), PCTEST (US), Verkotan (FI), CETECOM (DE/US) -- pre-compliance service lines and DASY-adjacent workflows
Standards bodies: IEC TC 106, IEEE ICES, ITU-R WP 5A/5C, 3GPP RAN 4 -- reference method recognition
Infrastructure vendors: Ericsson (SE), Nokia (FI), Huawei (CN), Samsung Networks (KR) -- network planning, beamforming design, integration with MSI compliance workflows
Network planning software: ATDI (FR), Forsk / Atoll (FR), iBwave (CA), InfoVista (FR/US) -- integration into planning tools
Operators: Proximus (BE), KPN (NL), Orange (FR), Deutsche Telekom (DE), Vodafone (UK), Telefonica (ES), Telenet (BE) -- deployment compliance
Regulators: BIPT (BE), BNetzA (DE), ARCEP (FR), Ofcom (UK), ANFR (FR), Agentschap Telecom (NL), FCC (US) -- independent verification

---

## 9. SUGGESTED PATENT CLAIMS

*[This section is not part of the standard IDF template but is included to assist the patent attorney in drafting claims.]*

### Independent claims

Claim 1 (Core spatial dosimetry method). A computer-implemented method for determining absorbed power density on a body surface, comprising:
(a) obtaining a surface mesh of at least a portion of a human body, the surface mesh comprising a plurality of surface elements each having an outward-facing surface normal;
(b) obtaining a tissue-dependent electromagnetic transmission coefficient for a frequency of interest;
(c) for each of one or more incident electromagnetic waves, each wave characterised by a propagation direction and a power density: computing, for each surface element, an incidence factor from the dot product of the surface normal with the negated propagation direction; applying a rectified linear activation to the incidence factor;
(d) for each surface element, multiplying the activated incidence factor by the transmission coefficient and the power density to obtain the absorbed power density at that surface element, wherein the power density and propagation direction may be constant across the body (far-field plane-wave illumination) or spatially varying (radiating-near-field point-source illumination).

Claim 1a (Near-field point-source dosimetry method). A computer-implemented method for determining absorbed power density on a body surface illuminated by a point source in the radiating-near-field regime at a source position r_s at distance d > 3*λ from the body, comprising:
(a) obtaining a surface mesh of at least a portion of a human body with outward-facing surface normals per element;
(b) obtaining a tissue-dependent electromagnetic transmission coefficient at a frequency of interest;
(c) obtaining the source position r_s and an antenna gain pattern G(u_hat) at said frequency;
(d) for each surface element at position r, computing the source-to-surface distance d(r) = ||r - r_s||, the propagation direction k_hat(r) = (r - r_s) / d(r), and the incident power density S_inc(r) = P_t * G(k_hat(r)) / (4 * π * d(r)^2), where P_t is the total radiated power;
(e) computing an incidence factor μ(r) = n_hat(r) . (-k_hat(r)) and applying a rectified linear activation;
(f) multiplying, for each surface element, the activated incidence factor by the transmission coefficient and the spatially-varying incident power density to obtain the absorbed power density at that element.

Claim 1b (Solid-angle view-factor absorption method). A computer-implemented method for determining total absorbed power on a human body illuminated by a point source at distance d > 3*λ, comprising:
(a) obtaining a surface mesh of the body with per-element outward normals and per-element area;
(b) obtaining a tissue-dependent transmission coefficient T_0 and a source position r_s;
(c) computing a view-factor Ω_body(r_s) as the sum over front-facing, non-occluded surface elements of μ(r) * dA(r) / d(r)^2, where μ(r) = n_hat(r) . (-k_hat(r)), d(r) = ||r - r_s||, and occlusion is determined by ambient-occlusion or ray-casting from r_s;
(d) computing total absorbed power as P_abs = P_t * T_0 * Ω_body(r_s) / (4 * π) for an isotropic source, or as the gain-weighted generalisation P_abs = (P_t * T_0 / (4 * π)) * integral over Ω_body of G(u_hat) dOmega_s for a directive source.

Claim 2 (Exposure operator method). A computer-implemented method for exposure-constrained MIMO precoding, comprising:
(a) for each propagation path from a plurality of antenna elements to a body surface, constructing an exposure channel matrix entry incorporating a Fresnel transmission coefficient, a depth-decay weighting factor, and a phase propagation term;
(b) computing an exposure operator as a surface integral of the Hermitian outer product of the exposure channel matrix, yielding a Hermitian positive-semidefinite matrix;
(c) solving a quadratically constrained optimisation to determine a precoding vector that maximises signal quality subject to an absorption constraint derived from the exposure operator.

Claim 2a (Near-field uplink exposure-constrained precoder for device MIMO). A computer-implemented method for exposure-constrained MIMO precoding of a wireless device operating in the radiating near-field of a human body, comprising:
(a) for each antenna element j of the device at position r_j, constructing a near-field exposure channel entry at each body-surface point r using a point-source Green's function evaluated at distance d_j(r) = ||r - r_j|| and incorporating the tissue Fresnel transmission coefficient;
(b) assembling a near-field exposure operator Q_NF as a surface integral of the Hermitian outer product of the near-field exposure channel over the visible body surface, yielding a Hermitian positive-semidefinite matrix dependent on device geometry and body surface;
(c) solving a quadratically constrained optimisation to determine a device-side precoding vector x that maximises uplink signal quality subject to x^H Q_NF x <= P_lim, where P_lim is derived from a regulatory absorbed-power-density limit under IEC/IEEE 63195-2 or an equivalent standard.

Claim 3 (Differentiable dosimetry optimization method). A computer-implemented method for optimising antenna deployment parameters to satisfy electromagnetic exposure constraints, comprising:
(a) computing absorbed power density on a body surface using the method of claim 1 via a differentiable computation graph;
(b) computing a gradient of a loss function incorporating a regulatory exposure limit with respect to one or more antenna parameters;
(c) iteratively updating the antenna parameters using the computed gradient to minimise peak exposure or maximise compliance margin.

Claim 3a (Near-field differentiable device design method). A computer-implemented method for optimising the design of a wireless device with respect to electromagnetic exposure on a human body, comprising:
(a) computing absorbed power density on the body surface using the near-field point-source method of claim 1a via a differentiable computation graph;
(b) computing a gradient of a loss function incorporating a regulatory exposure limit (IEC/IEEE 63195-2 or equivalent) with respect to one or more of: the source position r_s, the positions r_j of individual antenna elements within a device-embedded array, spherical-harmonic coefficients g_lm of the antenna gain pattern, a precoding vector x, and body-pose parameters (such as SMPL-X shape coefficients) representing uncertainty in user posture;
(c) iteratively updating said parameters by gradient descent to minimise a peak spatially-averaged APD over one or more averaging regions (4 cm^2 and 1 cm^2 per IEC/IEEE 63195-2) while preserving one or more communication objectives such as beam gain, spectral efficiency, or coverage.

Claim 4 (Integrated base-station compliance assessment system). A dosimetry computation system comprising:
(a) a base station data ingestion module that retrieves antenna installation parameters from one or more government databases;
(b) a 3D environment reconstruction module that generates a ray-traceable scene mesh from geographic data sources;
(c) a propagation path computation module that generates multipath propagation data via ray tracing or stochastic channel models;
(d) a dosimetry computation engine implementing the method of claim 1;
(e) a compliance evaluation module that assesses the computed absorption against regulatory limits;
(f) an interactive web-based interface presenting the results in real-time on a 3D visualisation.

Claim 4b (Device pre-compliance assessment system). A dosimetry computation system for wireless device pre-compliance, comprising:
(a) a device antenna module accepting antenna element positions and per-element radiation patterns at frequencies between 6 GHz and 300 GHz;
(b) a body phantom module providing a triangular surface mesh of at least a head or body portion with associated tissue dielectric properties;
(c) a source-placement module positioning the device antenna at a specified distance from the body phantom, said distance lying in the radiating-near-field regime d > 3*λ, equivalently at a distance at which the incident field is locally plane-wave over a wavelength-scale surface patch;
(d) a dosimetry computation engine implementing the method of claim 1 with spatially varying incident power density S_inc(r) = P_t * G(k_hat(r)) / (4*π*d(r)^2) and spatially varying propagation direction k_hat(r) = (r - r_s)/d(r) derived from point-source geometry;
(e) a compliance evaluation module computing spatially averaged absorbed power density over 4 cm^2 and 1 cm^2 regions and comparing the result against IEC/IEEE 63195-2 and equivalent regulatory limits;
(f) a pre-screening output that ranks candidate configurations and selects a subset for subsequent validation by full-wave numerical simulation.

Claim 5 (Medium). A non-transitory computer-readable medium storing instructions for performing the method of any of claims 1, 1a, 1b, 2, 2a, 3, 3a, or 16a.

### Dependent claims

Claim 6. The method of claim 1, wherein the transmission coefficient is the normal-incidence Fresnel power-absorption coefficient T_0 derived from the pseudo-Brewster compensation property of biological tissue.

Claim 7. The method of claim 1, wherein the transmission coefficient is the exact angle-dependent T_avg(θ), computed per surface element from TE and TM Fresnel equations.

Claim 8. The method of claim 1, further comprising computing an exposure fraction per surface element using ambient-occlusion computation to account for self-shadowing.

Claim 9. The method of claim 1, further comprising computing an absorption Stokes vector for exact polarisation-dependent dosimetry.

Claim 10. The method of claim 1, wherein the rectified linear activation is replaced by a smooth approximation (GELU) incorporating a surface curvature-dependent width parameter to model diffraction at shadow boundaries.

Claim 11. The method of claim 1, further comprising evaluating the absorbed power density against a frequency-dependent ICNIRP 2020 regulatory limit and generating a compliance assessment with margin in decibels.

Claim 12. The method of claim 3, wherein the antenna parameters comprise at least one of: antenna position, antenna tilt angle, transmit power, or MIMO precoding vector.

Claim 13. The method of claim 3, wherein the loss function comprises a penalty term that is quadratic in the excess of peak spatially-averaged absorbed power density over a regulatory limit.

Claim 14. The system of claim 4, wherein the propagation path computation module comprises a stochastic channel generator implementing 3GPP TR 38.901 cluster-based multipath with configurable scenario presets.

Claim 15. The system of claim 4, wherein the 3D environment reconstruction module generates scene geometry from OpenStreetMap building data, terrain elevation data, or photogrammetric 3D tile data, with per-surface electromagnetic material properties.

Claim 16 (Spherical-harmonic antenna-pattern decoupling). The method of claim 1, further comprising precomputing a set of body-response coefficients Γ_lm(r_s) for each source position r_s, said coefficients being surface integrals of the body's geometric absorption factor weighted by spherical harmonics Y_lm of the incidence direction, such that the absorbed power for an arbitrary antenna gain pattern at source position r_s is obtained as a dot product between the spherical-harmonic expansion of the antenna gain and the precomputed body-response coefficients.

Claim 16a (Body-response spherical-harmonic pre-computation, independent). A computer-implemented method for rapid exposure evaluation of candidate antenna gain patterns at fixed source positions, comprising:
(a) obtaining a body surface mesh and a set of source positions {r_s};
(b) for each r_s, precomputing body-response coefficients Γ_lm(r_s) = integral over Σ_plus of μ(r) * Y_lm(k_hat(r)) / d(r)^2 * O(r, k_hat) dA, where Y_lm are spherical harmonics up to degree L, μ(r) = n_hat(r) . (-k_hat(r)) is the cosine-of-incidence factor, d(r) = ||r - r_s|| is the source-to-surface distance, and O(r, k_hat) is a visibility or ambient-occlusion factor;
(c) storing the coefficients Γ_lm(r_s) in a look-up table indexed by source position;
(d) for a candidate antenna gain pattern G(u_hat) at source position r_s, expanding G in spherical harmonics as G(u_hat) = sum_{lm} g_lm * Y_lm(u_hat);
(e) evaluating total absorbed power as P_abs = (T_0 / (4 * π)) * sum_{lm} g_lm * Γ_lm(r_s) in O(L^2) operations per candidate, where T_0 is a tissue-dependent transmission coefficient.

Claim 17 (Fast pre-screening for full-wave validation). A method for pre-screening candidate configurations of a wireless device relative to a human body before validation by full-wave electromagnetic simulation, comprising:
(a) for each configuration in a set of candidate configurations differing in one or more of antenna position, antenna orientation, beam direction, transmit power, or body pose, computing absorbed power density using the method of claim 1;
(b) ranking the configurations by peak spatially averaged absorbed power density over a specified averaging area;
(c) selecting a subset of highest-ranked configurations for validation by a finite-difference time-domain or finite element method simulation.

Claim 18. The system of claim 4b, wherein the pre-screening output is ingested by a finite-difference time-domain solver implementing IEC/IEEE 63195-2 reference procedures, such that the geometric engine accelerates the iteration loop of a full-wave compliance workflow without replacing the full-wave validation step.

---

## SIGNATURES

Signing this document indicates that (a) the Invention Disclosure Form is complete and accurate, and (b) the inventor recognises that commercialisation of research results is a legal obligation (Codex Hoger Onderwijs, Art. II.285) and will cooperate with UGent TechTransfer.

______________________          _________________          __________
Inventor's name                 Signature                   Date

Robin Wydaeghe                  _________________          __/__/2026
