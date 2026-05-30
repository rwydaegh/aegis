# Invention Disclosure Form (IDF)

**CONFIDENTIAL**

---

## DATE

01/04/2026

---

## TITLE of the invention (+ possible acronym)

Geometric Dosimetry: Closed-Form Method and Software for Real-Time Computation of Electromagnetic Absorption on Human Bodies (AEGIS)

---

## IOF/VALORISATION INFORMATION

IOF/Valorisation responsible: *[to be filled in by IOF/valorisation responsible]*

TTRM Project No.: *[to be filled in by IOF/valorisation responsible]*

---

## 1. Description of the invention

### If you would consider your invention as a solution, what technical problem were you trying to solve?

Regulatory bodies worldwide (ICNIRP, IEEE/FCC) require that wireless systems comply with limits on human electromagnetic exposure. Above 6 GHz, the relevant quantity is the absorbed power density (Sab): the power deposited per unit area in the skin layer (skin depth approximately 0.3 to 0.5 mm at millimetre-wave frequencies). Below 6 GHz, whole-body specific absorption rate (SAR) is the governing metric.

Computing Sab by conventional means requires solving Maxwell's equations over the full volume of the human body using numerical methods (FDTD or FEM). At millimetre-wave frequencies, the mesh must resolve the sub-millimetre skin depth across a body spanning roughly one metre. This requires approximately 10^12 mesh cells. A single simulation at one frequency, one source, and one body orientation takes hours to days on a high-performance computing cluster. Evaluating compliance for a realistic multi-source, multi-frequency, multi-orientation environment is computationally intractable.

The problem: there was no closed-form framework for computing absorbed power density on realistic three-dimensional human body geometries. Every compliance assessment required a new brute-force simulation.

### How have others tried to solve this problem? Describe for each solution the functional and/or structural differences with your solution.

**FDTD (Finite-Difference Time Domain).** The regulatory gold standard. Maxwell's equations are discretised on a Cartesian grid and stepped forward in time. Requires ~10^12 cells at mmWave, takes hours to days per single configuration. *Difference:* our method replaces the volumetric simulation with a closed-form surface computation, reducing computation from hours to milliseconds.

**FEM (Finite Element Method).** Unstructured tetrahedral meshes reduce cell count versus FDTD, but the thin absorption layer still demands fine surface meshing. Computation times remain hours to days. *Difference:* same as above.

**Layered analytical models (Christ et al. 2006).** One-dimensional multi-layer models (skin-fat-muscle) compute absorption for a flat surface patch at a single incidence angle. *Difference:* our method handles arbitrary 3D body geometry, self-shadowing, multiple incidence directions, and produces full spatial maps.

**Empirical transmission coefficients.** Several groups observed that a nearly constant transmission coefficient T_tr reproduces FDTD results:
- Kodera et al. (2024) showed SAR_wb = T_tr x A_perp x Sinc / W, reproducing 3D FDTD to within 5% from 10-100 GHz. T_tr was extracted from a 1D slab model; no physical mechanism was identified for its near-constancy.
- Li et al. (2019) showed numerically that transmitted flux is nearly insensitive to incidence angle on a flat skin model from 6 GHz to 1 THz. The unpolarised average was not examined; no 3D geometry was considered.
- Diao et al. (2024) obtained T ~ 0.52 at 28 GHz from anatomical FDTD.
- Bamba et al. (2012, 2014) [same research group, UGent INTEC-WAVES] measured absorption efficiency eta ~ 0.5 in reverberation chambers. No physical origin was identified; the method only works in diffuse fields.

*Difference:* all these works observed empirically that a nearly constant coefficient works, but none identified the physical mechanism (pseudo-Brewster compensation) or derived the coefficient from Fresnel theory. None extended the result to spatial maps on arbitrary 3D bodies, polarisation-dependent dosimetry, or coherent MIMO beamforming.

**Pseudo-Brewster angle (optics).** Azzam (2015) proved that high-index substrates (|n| > 2.5) have nearly angle-independent unpolarised reflectance. *Difference:* this optics result was never applied to biological tissue or dosimetry. Our work makes this connection.

**SAR matrix for MIMO (Hochwald 2014, Ying 2015-2017).** The SAR matrix formulation S (where P_abs = x^H S x) and the QCQP precoder solution were introduced for uplink (handset) SAR at sub-6 GHz. In all works, the SAR matrix entries are calibrated by FDTD simulation with no closed-form content. *Difference:* our exposure operator Q has closed-form entries derived from Fresnel theory and body geometry, and works for the downlink base-station geometry.

**Castellanos et al. (2020).** Per-element scalar Fresnel coefficient at 28 GHz for MIMO exposure. *Difference:* no surface integral over the body, no depth coupling, no closed-form exposure operator Q.

**Commercial tools (Sim4Life by ZMT, CST Studio by Dassault, ANSYS HFSS).** All implement FDTD or FEM and share the same fundamental computational limitations.

**Summary comparison with closest prior art:**

| Element of framework | Kodera (2024) | Li (2019) | Bamba (2012-14) | Azzam (2015) | Ying (2015-17) | This invention |
|---|---|---|---|---|---|---|
| Tavg ~ T0 (angular constancy) | Empirical | Empirical | Empirical | Derived (optics only) | -- | Derived, applied to dosimetry |
| Local Sab(r) on 3D body | -- | Flat slab only | -- | -- | -- | Closed-form on arbitrary 3D |
| Cauchy formula (A_ab/4) | Empirical | -- | -- | -- | -- | Derived (generalised) |
| Exposure fraction = ambient occlusion | -- | -- | -- | -- | -- | New |
| Compliance formula | -- | -- | -- | -- | Empirical | Derived |
| Exposure operator Q (closed-form) | -- | -- | -- | -- | FDTD-calibrated | Closed-form from Fresnel theory |

### Describe the advantage of your solution over the existing solutions.

1. **Speed.** 10^6 to 10^9 times faster than FDTD. Milliseconds instead of hours. This is not incremental but transformative: it enables real-time exposure monitoring, network-level compliance, and interactive assessment, which are fundamentally impossible with existing methods.

2. **Closed-form.** The framework provides analytical formulas. No mesh generation, no iterative solvers, no convergence issues. A frequency sweep requires only recomputing T0 (a lookup table). A body orientation sweep uses the precomputed directivity D(k_hat).

3. **Coherent MIMO.** The exposure operator Q is the first closed-form tool for computing absorption from beamformed signals. The ECBF precoder is the first closed-form exposure-constrained beamformer. No existing method can handle this without re-running FDTD per precoding vector.

4. **Differentiable.** The computation is a matrix-vector multiply followed by a rectified linear activation. This is compatible with automatic differentiation and gradient-based optimisation, enabling network optimisation with exposure as a constraint.

5. **Full frequency range.** Valid from 100 MHz to 100 GHz via the T0/Tbar mechanism. Existing closed-form results were limited to single frequencies or narrow bands.

6. **Exact polarisation handling.** The absorption Stokes vector provides exact polarisation-dependent dosimetry. No prior dosimetry framework handles arbitrary polarisation analytically.

7. **Conservative for compliance.** Below 40 GHz, the T0 approximation underestimates absorbed power. This means the method never certifies a non-compliant deployment as compliant, which is the safety property regulators require.

| Property | FDTD/FEM | This invention |
|----------|----------|----------------|
| Computation time | Hours to days | Milliseconds |
| Mesh cells | ~10^12 | ~10^4 triangles (surface only) |
| Real-time capable | No | Yes |
| Multi-source | One simulation per source | Matrix-vector multiply |
| Frequency sweep | One simulation per frequency | Recompute T0 (lookup) |
| Coherent MIMO | Per-precoder simulation | Closed-form (exposure operator Q) |
| Differentiable | No | Yes |

**Further technical effect (EPO G 1/19).** The invention produces a further technical effect beyond the implementation of software on a computer: it enables real-time assessment of physical electromagnetic absorption in human tissue against regulatory limits (ICNIRP 2020, IEEE C95.1-2019). The output is a measurable physical quantity (absorbed power density in W/m^2) with direct safety and regulatory significance.

### Give a short description of the invention, preferably including a listing of those elements of the invention that are essential to make the invention work, those elements that can be varied and how they can be varied (max. one page).

**The method.** Two physical insights combine to reduce volumetric dosimetry to a surface-geometric computation:

*Insight 1 (pseudo-Brewster compensation):* For biological tissue (complex refractive index |n| ~ 3-7), the TE and TM Fresnel power transmissions compensate each other. Their unpolarised average remains within 5.6% of the normal-incidence value T0 over 0-75 degrees. This allows replacing angle-dependent transmission with a single scalar T0 (= 0.54 for skin at 28 GHz).

*Insight 2 (surface confinement):* Above 6 GHz, the skin depth (< 1 mm) confines all absorption to the surface. Only the body's external shape matters.

These yield the geometric absorption law:

    Sab(r) = Sinc * T0 * ReLU[n_hat(r) . (-k_hat)]

**Essential elements:**
1. A tissue-dependent electromagnetic transmission coefficient (T0, or the exact angle-dependent Tavg(theta), or the flux-averaged Tbar(f))
2. A surface mesh of the human body with triangle normals
3. Incident wave parameters: power density and propagation direction per source
4. For coherent MIMO: the exposure channel matrix G_tilde and the exposure operator Q

**Elements that can be varied:**
- The transmission coefficient variant: T0 (constant, fastest), Tavg(theta) (exact, per-triangle), Tbar(f) (flux-averaged, for sub-6 GHz). Different accuracy-speed trade-offs.
- The body mesh complexity: from simple ellipsoids to high-resolution anatomical phantoms
- The number of fidelity levels: O(1) bound, O(N) aggregate, O(M_tri * N) spatial, coherent MIMO
- The ray tracing backend: any tool that provides propagation paths
- Tissue type and frequency: any tissue with known dielectric properties, 100 MHz to 100 GHz

**Extensions:**
- Polarisation: exact handling via absorption Stokes vector (P_abs = m . s_inc)
- Sub-6 GHz: replace T0 with Tbar for exact direction-averaged results at any frequency above 100 MHz
- Coherent MIMO: Sab(r) = ||G_tilde(r) x||^2. Exposure operator Q = integral of G_tilde^H G_tilde dA. Closed-form exposure-constrained beamformer via QCQP.

**The software (AEGIS):** Python library + web-based 3D visualisation tool implementing all of the above. Nine fidelity levels (0-8). Real-time 3D viewer (Flask + React + Three.js) with OpenStreetMap, Google 3D Tiles. Ray tracing via Sionna. Real base station data from 8 EU government databases. 1,200+ real antenna patterns from CloudRF. ~28,000 lines Python, ~14,000 lines TypeScript, 2,177 automated tests.

### If possible, provide a figure that shows all features of the invention.

*[To be included: (1) Fresnel curves showing TE/TM compensation at 28 GHz, (2) Sab map on human phantom, (3) AEGIS viewer screenshot, (4) system block diagram: mesh + paths -> geometric law -> Sab map -> compliance check]*

### Does your invention possess disadvantages or limitations? Indicate how they might be overcome.

1. **Far-field assumption.** Requires source-to-body distance > ~3 wavelengths (~3 cm at 28 GHz). Does not apply to devices pressed against the body. *Can be overcome:* near-field extension under development.

2. **Surface absorption assumption below 6 GHz.** The local spatial map loses physical meaning below ~6 GHz when multi-layer resonances become significant. *Can be overcome:* total-power results remain valid via Tbar; the local map limitation is inherent to the surface-confinement physics.

3. **Diffraction.** Geometric optics; no diffraction modelling. ~10% error on total absorbed power for torso-sized bodies at mmWave. *Can be overcome:* GTD correction layer (partially implemented at fidelity level 6).

4. **Tissue property uncertainty.** Dielectric properties are uncertain to 10-20%. The framework error (2-6%) is well within this parametric uncertainty. *Inherent to the field.*

5. **Static body pose.** Computes dosimetry for a fixed pose. *Can be overcome:* real-time pose tracking integration.

6. **Ray tracing dependency.** Realistic environments need propagation paths from a ray tracer (seconds to minutes). Still orders of magnitude faster than FDTD.

### Describe the development status (concept only, laboratory tested, in vitro/in vivo data, prototype, etc.). Indicate what further development may be necessary.

**Status: working deployed software with comprehensive validation.**

The theoretical framework is complete and documented in a monograph (~6,000 lines LaTeX) with all derivations, proofs, and error analysis.

The software (AEGIS v0.11.0) is deployed on a password-protected production server:
- Core engine: 28,000 lines Python, 9 fidelity levels (0-8)
- Web viewer: 14,000 lines TypeScript/React
- 2,177 automated tests (golden tests, property-based tests, Mie-theory regression, end-to-end)
- Integrations: Sionna ray tracing, 8 EU base station databases, 1,200+ antenna patterns

**Validation:**
- Mie-theory regression: < 10% error for body-sized objects at mmWave
- Golden tests for every table in the monograph
- Property-based tests: Sab >= 0, energy conservation, ReLU correctness
- Comparison with published empirical data (Bamba, Kodera, Diao, Flintoft, Zhang): framework predictions match independent observations to within 3-8%

**Further development needed:**
- Journal publication (monograph and summary paper written, not yet submitted)
- Clinical validation against FDTD on IT'IS anatomical phantoms
- Near-field extension
- Dynamic pose tracking
- Formal IEC/IEEE certification

---

## 2. Invention disclosure record

### List all past and near-future disclosures of the invention (or parts of it).

| Type | Date and reference |
|------|-------------------|
| Oral presentation(s) at meetings, conferences, companies | None |
| Abstract, poster, proceeding posted, printed, or web-published | None |
| Manuscript submitted for publication (including internet pre-publishing) | None |
| Manuscript published | None |
| Thesis submitted or defended | None |
| Report (official or internal) | None |
| News article or feature report | None |
| Information given to a party outside the University WITH NDA/CDA | None |
| Information given to a party outside the University WITHOUT NDA/CDA | None |

The AEGIS software is deployed on a password-protected server accessible only to the inventor. No external parties have been given access. No public demonstrations have been conducted.

The novelty is fully preserved. No anticipated disclosure date has been set. The inventor will coordinate with TechTransfer before any publication or public disclosure.

### Prior art: publications by the inventors most closely related to the invention

None. No publications by the inventor describe any aspect of this invention.

### Prior art: publications by others most closely related to the invention

3. Y. Kodera, T. Hikage, and T. Nagaoka, "Whole-body average SAR estimation using surface area and a transmission coefficient at frequencies above 6 GHz," Phys. Med. Biol., vol. 69, 2024.
4. K. Li, K. Sasaki, and S. Watanabe, "Relationship between power density and temperature elevation in human tissue," IEEE Access, vol. 7, 2019.
5. A. Bamba et al., "Experimental assessment of specific absorption rate using room electromagnetics," IEEE Trans. EMC, vol. 54, no. 4, 2012.
6. A. Bamba et al., "Assessing whole-body absorption cross section for diffuse exposure from reverberation chamber measurements," IEEE Trans. EMC, vol. 57, no. 1, 2015.
7. R. M. A. Azzam, "High-index dielectric substrates with nearly constant reflectance," J. Mod. Opt., vol. 62, no. 18, 2015.
8. Z. Ying, D. J. Love, and B. M. Hochwald, "Closed-form capacity-SAR tradeoff for MIMO beamforming," IEEE Trans. Wireless Commun., vol. 14, no. 1, 2015.
9. M. R. Castellanos et al., "Closed-form Fresnel-based approach for 5G mmWave human body exposure assessment," IEEE Access, vol. 8, 2020.
10. I. D. Flintoft et al., "Average absorption cross-section of the human body measured at 1-12 GHz in a reverberant environment," IEEE Trans. AP, vol. 62, no. 5, 2014.

### Is literature screened on a regular basis?

YES

### Keywords:

Absorbed power density, electromagnetic dosimetry, Fresnel transmission, pseudo-Brewster angle, geometric optics, projected area, Cauchy's formula, ambient occlusion, ICNIRP 2020, millimetre-wave, 5G, 6G, MIMO beamforming, exposure operator, SAR, compliance, real-time computation, human phantom, ray tracing, exposure-constrained precoding

### Patents or patent applications of others most closely related to the invention

- US 8,630,596 B2 (Samsung, 2014): "Apparatus and method for controlling specific absorption rate." Device-level SAR control using return-loss sensing. *Distinguished:* device level, empirical sensing, no body-surface geometry computation, no exposure operator.
- US 2022/0377799 A1 (2022): "RF exposure mitigation and beam selection." Heuristic beam selection and power backoff. *Distinguished:* no closed-form dosimetry, no spatial absorption maps, no mathematically optimal precoder.
- WO 2016/195892 A1 (2016): "SAR distribution management for multi-antenna devices." Device-level power control. *Distinguished:* no geometric absorption framework, no Fresnel analysis, no exposure operator.

A formal freedom-to-operate (FTO) search has not yet been conducted.

### Who are the main academic or industrial research groups active in the field?

**Industrial:**
ZMT Zurich MedTech / Sim4Life (CH), Dassault Systemes / CST (FR), ANSYS / HFSS (US), Ericsson (SE), Nokia (FI), Huawei (CN), Qualcomm (US), SPEAG (CH), Rohde & Schwarz (DE)

**Academic:**
IT'IS Foundation / ETH Zurich (CH) -- anatomical phantoms, tissue properties, Sim4Life
Chalmers University Bioelectromagnetics Lab (SE) -- mmWave dosimetry
INTEC-WAVES / Ghent University / IMEC (BE) -- RF exposure, room electromagnetics
KTH Royal Institute of Technology (SE) -- exposure-aware beamforming
University of Lille / TELICE (FR) -- room electromagnetics, reverberation
Telecom Paris / WHIST Lab (FR) -- EMF exposure assessment

---

## 3. Inventors

Name only those who contributed intellectually to the inventive concept of the invention. Inventorship is not the same as authorship.

### INVENTOR 1 -- CONTACT PERSON for UGent TechTransfer

**Name:** Robin Wydaeghe
**Institution / Dept.:** Ghent University -- IMEC / INTEC-WAVES
**Address -- work:** Technologiepark-Zwijnaarde 126, 9052 Gent
**E-mail:** robin.wydaeghe@hotmail.com / robin.wydaeghe@ugent.be
**TEL.:** +32 483 06 90 27
**Address -- Home:** Fritz de Beulestraat 24, 9000 Ghent, Belgium
**Citizenship:** Belgian
**Contribution to the invention:** 100% -- Sole inventor of the theoretical framework (all physical insights, mathematical derivations, proofs, and error analysis) and sole developer of the software (AEGIS, ~42,000 lines of code, 2,177 tests)
**UGent payroll:** YES

*Note on sole inventorship:* The inventor's PhD supervisor, Prof. Wout Joseph, provided general academic guidance but did not contribute to the inventive concepts. The pseudo-Brewster compensation insight, the geometric reduction to surface dosimetry, the connections to integral geometry and computer graphics, the absorption Stokes vector, the exposure operator construction, and all mathematical derivations were developed independently by the sole inventor.

---

## 4. Records / Material

### Are lab records available? Are these lab records dated and signed?

The monograph (~6,000 lines LaTeX) serves as the primary technical record with all derivations, proofs, and validation. Git version control history provides timestamped records of all software development. Records are not signed in the traditional lab notebook sense, but all changes are tracked with cryptographic hashes in Git.

### At what site(s) was the research conducted that led to the invention?

Technologiepark-Zwijnaarde 126, 9052 Gent (UGent/IMEC iGent tower).

### Does the invention incorporate any material obtained from companies or institutions outside the University?

No. Open-source software tools (Sionna, DiffeRT, NumPy, React) are used as dependencies but do not form part of the invention. Base station data is from public government APIs. Antenna patterns are from CloudRF under standard commercial terms.

---

## 5. FUNDING

### Past and current funding that led to the invention

| Agency or Sponsor | Grant/Contract (Type & Ref. Nr.) | Term |
|---|---|---|
| None | N/A | N/A |

This invention arose spontaneously and was not funded by any specific research project, grant, or contract. The inventor's PhD position at UGent/IMEC is the only relevant employment relationship. Standard UGent IP regulations apply.

### Future funding that will further develop/improve the invention

No external funding sources have been identified. The invention is sufficiently complete for commercialisation without additional research funding. Further development (near-field extension, clinical validation, certification) can be pursued within the current PhD or a spin-off context.

---

## 6. COLLABORATION

### Is the invention the result of a collaborative project involving another party?

No.

### Is there a contract/agreement? If yes, please provide contract number:

No. No collaborations, subcontracts, or material transfer agreements are in place. No external party has access to unpublished details of the framework or the software.

---

## 7. AUTHORSHIP / COPYRIGHT

### Is there any expression of this invention through software?

Yes. AEGIS: approximately 42,000 lines of Python and TypeScript implementing all aspects of the invention (core computation engine, nine fidelity levels, coherent MIMO beamforming, real-time 3D visualisation, regulatory compliance checking).

### What is the purpose of the software?

Fully functional end-user system. It implements the complete invention from O(1) compliance bounds through full spatial dosimetry maps to exposure-constrained MIMO beamforming, with a production-quality web-based 3D visualisation interface. Deployed on a production server.

### Is the software a derivative or improvement of any existing source code?

No. The software was written from scratch by the inventor based on the theoretical framework described in this disclosure. Standard open-source libraries are used as infrastructure dependencies (NumPy, SciPy, React, Three.js) under their respective open-source licences.

---

## 8. COMMERCIALIZATION POTENTIAL

### In your opinion, what kind of commercial applications could be derived from your invention and how easy/feasible would it be to bring a product to the market?

**1. Network planning and compliance (primary market).** Telecom operators deploying 5G/6G must demonstrate regulatory compliance. Current practice uses either conservative worst-case calculations (unnecessarily restrictive exclusion zones, reduced network capacity) or expensive FDTD simulations (impractical at network scale). This invention enables real-time compliance during network planning. The result: denser, more efficient networks with smaller exclusion zones. The invention can be added as a computation layer in existing network planning tools, requiring no new regulatory burden.

**2. Exposure-aware beamforming.** The exposure operator Q enables the first beamforming designs that account for human absorption. The closed-form ECBF precoder maximises signal quality while guaranteeing compliance. Relevant for dense urban deployments and indoor small cells.

**3. Real-time exposure monitoring / smart city infrastructure.** Millisecond computation enables continuous real-time monitoring. Combined with real base station data and ray tracing, this creates a digital twin of the electromagnetic environment.

**4. Device compliance testing.** Rapid screening during device design, reducing expensive measurement campaigns.

**5. Standards and academic licensing.** Foundation for a new generation of exposure assessment standards.

Bringing the product to market is feasible. The software is already deployed and functional. It can be licensed to network planning vendors, offered as a SaaS API, contributed to standards bodies, or commercialised via a spin-off company.

### Which companies could be interested in your invention?

**Infrastructure vendors:** Ericsson (SE), Nokia (FI), Huawei (CN) -- network planning, beamforming design
**Operators:** Proximus (BE), KPN (NL), Orange (FR), Deutsche Telekom (DE), Vodafone (UK) -- deployment compliance
**Network planning software:** ATDI (FR), Mentum/InfoVista (FR) -- integration into planning tools
**Chipset vendors:** Qualcomm (US), MediaTek (TW) -- exposure-aware beamforming at chipset level
**Simulation vendors:** ZMT / Sim4Life (CH), Dassault / CST (FR) -- complementary real-time module
**Device OEMs:** Samsung, Apple, Xiaomi -- device compliance screening
**Test houses:** SPEAG (CH), UL, TUV -- measurement and compliance
**Regulators:** BIPT (BE), Agentschap Telecom (NL), ANFR (FR), BNetzA (DE) -- real-time monitoring

---

## 9. SUGGESTED PATENT CLAIMS

*[This section is not part of the standard IDF template but is included to assist the patent attorney in drafting claims.]*

### Independent claims

**Claim 1 (Core method).** A computer-implemented method for determining absorbed power density on a body surface, comprising:
(a) obtaining a surface mesh of at least a portion of a human body, the surface mesh comprising a plurality of surface elements each having an outward-facing surface normal;
(b) obtaining a tissue-dependent electromagnetic transmission coefficient for a frequency of interest;
(c) for each of one or more incident electromagnetic waves, each wave characterised by a propagation direction and a power density: computing, for each surface element, an incidence factor from the dot product of the surface normal with the negated propagation direction; applying a rectified linear activation to the incidence factor;
(d) for each surface element, multiplying the activated incidence factor by the transmission coefficient and the power density to obtain the absorbed power density at that surface element.

**Claim 2 (Aggregate method).** A computer-implemented method for determining total absorbed power on a body, comprising:
(a) computing a projected area or absorption area from a surface mesh;
(b) obtaining a tissue-dependent electromagnetic transmission coefficient;
(c) applying a generalised Cauchy formula incorporating the transmission coefficient and the absorption area to obtain direction-averaged total absorbed power.

**Claim 3 (MIMO method).** A computer-implemented method for exposure-constrained MIMO precoding, comprising:
(a) for each propagation path from a plurality of antenna elements to a body surface, constructing an exposure channel matrix entry incorporating a Fresnel transmission coefficient, a depth-decay weighting factor, and a phase propagation term;
(b) computing an exposure operator as a surface integral of the Hermitian outer product of the exposure channel matrix, yielding a Hermitian positive-semidefinite matrix;
(c) solving a quadratically constrained optimisation to determine a precoding vector that maximises signal quality subject to an absorption constraint derived from the exposure operator.

**Claim 4 (System).** A dosimetry computation system comprising a processor and memory storing instructions that, when executed, cause the processor to perform the method of any of claims 1-3.

**Claim 5 (Medium).** A non-transitory computer-readable medium storing instructions for performing the method of any of claims 1-3.

### Dependent claims

**Claim 6.** The method of claim 1, wherein the transmission coefficient is the normal-incidence Fresnel power-absorption coefficient T0.

**Claim 7.** The method of claim 1, wherein the transmission coefficient is the exact angle-dependent Tavg(theta), computed per surface element.

**Claim 8.** The method of claim 2, wherein the transmission coefficient is the flux-averaged Tbar(f).

**Claim 9.** The method of claim 1, further comprising computing an exposure fraction using ambient-occlusion computation to account for self-shadowing.

**Claim 10.** The method of claim 1, further comprising computing an absorption Stokes vector for exact polarisation-dependent dosimetry.

**Claim 11.** The method of claim 1, performed as a matrix-vector multiplication on a GPU.

**Claim 12.** The method of claim 1, further comprising evaluating the absorbed power density against a regulatory exposure limit and generating a compliance assessment.

---

## SIGNATURES

Signing this document indicates that (a) the Invention Disclosure Form is complete and accurate, and (b) the inventor recognises that commercialisation of research results is a legal obligation (Codex Hoger Onderwijs, Art. II.285) and will cooperate with UGent TechTransfer.

______________________          _________________          __________
Inventor's name                 Signature                   Date

Robin Wydaeghe                  _________________          __/__/2026
