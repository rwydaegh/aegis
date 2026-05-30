 Gemini
About Gemini Opens in a new window
Gemini App Opens in a new window
Subscriptions Opens in a new window
For Business Opens in a new window
Computational RF Dosimetry and EMF Compliance: Strategic Market, Standards, and Academic Landscape Analysis for AEGIS

The transition of wireless communication systems to frequencies above 6 GHz—notably 5G millimeter-wave (mmWave) Frequency Range 2 (FR2), the emerging 6G Frequency Range 3 (FR3), and sub-terahertz bands—fundamentally alters the physics of human electromagnetic field (EMF) exposure. At these higher frequencies, electromagnetic energy absorption is confined to a highly superficial skin layer, shifting the primary dosimetric restriction from the volume-based Specific Absorption Rate (SAR, in W/kg) to the surface-based absorbed power density (Sab​, in W/m2), also referred to as epithelial power density.  

The conventional method for evaluating compliance and biological safety relies on full-wave solvers, such as the Finite-Difference Time-Domain (FDTD) method, which solve Maxwell's equations on discretized grids. However, FDTD simulations require sub-millimeter cell sizes to resolve thin skin layers at high frequencies, which increases computational grid sizes and scales execution times to hours or days per run. This computational bottleneck limits real-time device optimization, base-station compliance planning, and exposure-aware beamforming.  

The AEGIS software platform, spun out of Ghent University and imec, addresses this bottleneck by replacing slow full-wave simulations with fast, closed-form analytical physics. Operating across a range of 100 MHz to 300 GHz, AEGIS evaluates local exposure in milliseconds. It models superficial power absorption using the analytical formulation:  
Sab​(r)=Sinc​⋅T0​⋅ReLU[n^⋅(−k^)]

where Sinc​ represents the incident power density, T0​ is the near-constant Fresnel transmission coefficient into tissue accounting for the pseudo-Brewster effect, n^ is the unit normal vector of the body surface, and k^ is the wave propagation vector.

AEGIS extends this core formulation with a radiating near-field spherical-harmonic expansion, a coherent massive multiple-input multiple-output (massive-MIMO) exposure operator, and an end-to-end differentiable JAX pipeline. This report evaluates the academic, commercial, and regulatory landscapes to position AEGIS strategically for commercialization between 2026 and 2027.  
What Changed My Assumptions

A systematic review of academic literature, corporate filings, standards developments, and industry indicators from 2024 to 2026 reveals critical developments that shift the baseline assumptions of the AEGIS venture.

                                 
                                          |
                                          v
+------------------+     +-------------------------------+     +--------------------+
| Academic Sector  | <-> |  Differentiable JAX Pipeline  | <-> | Industry Standards |
+------------------+     +-------------------------------+     +--------------------+
         |                                |                                      |
  • Split Univ (Autodiff)        • Remilab (rfx FDTD)             • IEC 63195-2:2027
  • GOLIAT (Ghent/IMT)           • TICRA / DTU (JPO arrays)       • ISED RSS-102 Iss 6

1. Automatic Differentiation is Already Active in Dosimetry

The assumption that computational electromagnetics (CEM) dosimetry is an open field for automatic differentiation (AD) is challenged by the work of Ante Lojic Kapetanovic and Dragan Poljak at the University of Split. They have developed AD-based solvers designed to evaluate high-frequency incident power density (IPD) and Sab​ on non-planar geometries, such as spherical heads and realistic ear phantoms.  

Their approach uses boundary element formalism to compute electric (E) and magnetic (H) fields and resolves surface integration via Gaussian quadrature, demonstrating significant improvements in speed and accuracy over traditional finite differences.  
2. General-Purpose Differentiable EM Solvers Have Commercialized

Differentiable electromagnetic simulation is no longer a purely academic concept. Remilab has commercialized rfx (packaged as rfx-fdtd), a 3-D FDTD Maxwell solver built entirely in JAX. It provides native gradient support (jax.grad) for inverse design, S-parameter extraction, Debye dispersive material fitting, and GPU-accelerated execution.  

Additionally, TICRA and the Technical University of Denmark (DTU) have deployed PyTorch-based differentiable far-field simulators to execute joint parameterized optimization (JPO) of large-scale active electronically scanned arrays (AESAs).  
3. The Physical Measurement Ecosystem Has Extended to FR3

While AEGIS positions itself as a fast pre-screen to physical measurement bottlenecks, SPEAG (the hardware incumbent) has expanded its physical validation tools into upcoming 6G bands. SPEAG launched DASY8 Module APD V1.0 in 2024 to emulate skin absorption between 24 and 30 GHz.  

In March 2026, SPEAG released Module APD V2.0, extending physical measurement capability down to 10 GHz. This directly targets upcoming 6G Frequency Range 3 (FR3) compliance and features dedicated phantoms (such as the PHA10-18G) and skin-simulating liquids (SSL). This development shortens the physical testing cycle for devices, altering the baseline efficiency margins required for AEGIS to compete.  
4. Regulatory Mandates for APD Have Crystalized

The regulatory transition from incident power density (Sinc​) to absorbed power density (Sab​) has accelerated. Innovation, Science and Economic Development (ISED) Canada finalized its transition to RSS-102 Issue 6. This regulation mandates that all wireless devices operating above 6 GHz must undergo explicit APD evaluations.  

Furthermore, the Federal Communications Commission (FCC) expanded unlicensed Very Low Power (VLP) device operations across the entire 6 GHz band. This has generated immediate compliance demand for WiFi 6E/7 and emerging 5G/6G wearable architectures.  
5. Detailed Active RIS Dosimetry Models Have Emerged

Rather than relying on simplified propagation assumptions, the European Union's EXPOAUTO project has produced detailed 3D numerical dosimetry datasets modeling the impact of active Reconfigurable Intelligent Surfaces (RIS) on pedestrian exposure.  

Led by Martina Benini and Gabriella Tognola at CNR IEIIT in Milan, this research evaluates whole-body SAR and Sab​ at 28 GHz in realistic urban vehicle-to-vehicle (V2V) environments. This provides concrete, multi-physics baselines for the RIS optimization algorithms that AEGIS seeks to enable.  
Academic Collaborators

To establish scientific authority and accelerate collaborative R&D, AEGIS must align with leading research groups in computational RF dosimetry, differentiable electromagnetics, and exposure-aware beamforming. The table below lists and ranks prominent global groups based on institutional prestige, research output, and alignment with AEGIS's core technology.
Rank	PI & Research Group	University / Country	Key Outputs (2022-2026)	Recent Grants / Projects	Strategic Fit Rationale
1	

Dragan Poljak & Ante Lojic Kapetanovic

Computational Electromagnetics Group
	University of Split, Croatia	

(https://www.researchgate.net/publication/355634634_Application_of_Automatic_Differentiation_in_Electromagnetic_Dosimetry_-_Assessment_of_the_Absorbed_Power_Density_in_the_mmWave_Frequency_Spectrum) 

(https://data.fesb.unist.hr/documents/public/news/Doktorski%20rad-za%20objavu%20-Ante.pdf) 
	

Croatian Science Foundation EM Safety & Dosimetry 
	

Exact technical alignment. Pioneered JAX-based automatic differentiation for mmWave Sab​ and Gaussian quadrature for non-planar body models.
2	

Wout Joseph

WAVES Research Group
	Ghent University / imec, Belgium	

MaMIMO Exposure at 28 GHz (2022) 

(https://www.robinwydaeghe.com/publications) 
	

Horizon Europe GOLIAT (€9.3M) 

SHAPE (Methusalem) 
	

Direct academic origin. Unrivaled expertise in hybrid Ray-Tracing/FDTD simulations and realistic base-station exposure mapping.
3	

Joe Wiart

Chaire C2M
	Télécom Paris / IP Paris, France	

(https://files01.core.ac.uk/download/610615499.pdf) 

Far-Field Absorption in Phantoms (2025) 
	

Horizon Europe GOLIAT (€9.3M) 
	

Global authority on statistical and stochastic dosimetry. Critical for scaling AEGIS's fast operators to population-level exposure studies.
4	

Gabriella Tognola & Silvia Gallucci

Electromagnetic Fields in Biology & Medicine
	CNR IEIIT / Politecnico di Milano, Italy	

(https://ieeexplore.ieee.org/document/10715541/) 

(https://sciprofiles.com/profile/1916224) 
	

ANSES EXPOAUTO Project (Automotive & Connected Objects EMF) 
	

Leading group on modeling active/passive RIS and vehicle-to-human EMF dosimetry using advanced machine learning and numerical phantoms.
5	

Allan Peter Engsig-Karup

Scientific Computing Section
	Technical University of Denmark (DTU), Denmark	

(https://openreview.net/forum?id=bjyUK5NX0a) 
	

Industry-academic joint venture with TICRA 
	

Experts in PyTorch-based end-to-end differentiable EM solvers and joint parameterized optimization of large antenna arrays.
6	

Akimasa Hirata

Electromagnetic Compatibility Laboratory
	Nagoya Institute of Technology, Japan	

(https://www.researchgate.net/publication/361758590_Assessment_of_Incident_Power_Density_on_Spherical_Head_Model_up_to_100_GHz) 

(https://www.researchgate.net/publication/355634634_Application_of_Automatic_Differentiation_in_Electromagnetic_Dosimetry_-_Assessment_of_the_Absorbed_Power_Density_in_the_mmWave_Frequency_Spectrum) 
	

Japanese National Regulatory Research Grants 
	

Major contributor to ICNIRP/IEEE standards. Focuses on the causal link between spatially averaged Sab​ and steady-state skin temperature rise.
7	

Marco Di Renzo

Laboratory of Signals and Systems
	CentraleSupélec / Université Paris-Saclay, France	

(https://arxiv.org/abs/2206.06870) 

(https://arxiv.org/pdf/2104.06283) 
	

Horizon Europe RISE-6G  and SNS JU Successors 
	

Preeminent authority on RIS. His beamforming optimization algorithms require the fast differentiable exposure operators AEGIS provides.
8	

Shuai Zhang & Gert F. Pedersen

Antenna & Propagation Group
	Aalborg University, Denmark	

(https://ieeexplore.ieee.org/document/10715541/) 

(https://vbn.aau.dk/en/publications/prediction-of-electromagnetic-field-exposure-at-20100-ghz-for-clo/) 
	

Danish Strategic Research Council 
	

Developers of the RAWA-NN deep learning framework, achieving a four-orders-of-magnitude speedup in APD and skin heating prediction.
 

The academic research vector has shifted from verifying basic far-field compliance to addressing complex near-field and multi-source environments. Under the Horizon Europe GOLIAT project, which coordinates €9.3 million in funding to study 5G/6G health implications, researchers are focusing on personal micro-environment mapping.  

This transition has highlighted the limitations of classical FDTD when modeling large, dynamic environments, such as smart offices or outdoor urban streets populated by moving pedestrians. Consequently, groups like the one at CNR IEIIT have turned to hybrid propagation modeling, combining geometric ray-tracing for environmental propagation with localized FDTD for phantom dosimetry.  

By positioning its fast closed-form analytical operators as a standardized interface between ray-tracers and body models, AEGIS can access collaborative European funding through these established networks.
Customers & Market Map

To build a sustainable commercial model, AEGIS must address clear, bottom-up customer segments defined by distinct regulatory drivers and technical requirements.

                     
                                   |
    +------------------------------+------------------------------+
    |                                                             |
    v                                                             v
                       
  • Target: Apple, Samsung, MediaTek                 • Target: Orange, Ericsson, Nokia
  • Pain: Slow physical SAR/APD tests                • Pain: Exclusion zone compliance
  • Volume: High (Pre-compliance)                    • Volume: Medium (Continuous site audits)
    |                                                             |
    +------------------------------+------------------------------+
                                   |
                                   v
                        
                           • Target: SGS, Eurofins, UL
                           • Pain: Test bottlenecks
                           • Volume: Moderate

1. Device OEMs (mmWave/6G Pre-compliance)

The core target customers in this segment include global handset brands and silicon chip developers, such as Apple, Samsung, Qualcomm, MediaTek, and Intel. The primary commercial driver is the ongoing expansion of the 6 GHz spectrum and the deployment of WiFi 6E/7 and 5G/6G mmWave radios. Under regulatory frameworks like ISED Canada RSS-102 Issue 6 and the FCC’s unlicensed Very Low Power (VLP) rules, hardware designers must demonstrate that device emissions close to the body comply with APD limits.  

Currently, designers are caught in a slow iteration loop: they must run full-wave simulations in Sim4Life or ANSYS HFSS, or wait for physical lab time on robotic test benches like SPEAG's cSAR3D or DASY8 systems. By integrating AEGIS's millisecond-level solver into their automated EDA (Electronic Design Automation) pipelines, OEMs can run thousands of antenna placement sweeps and beamforming codebook validations daily, reserving physical testing for final certification.  
2. Telecom Operators and RAN Vendors

This segment consists of Mobile Network Operators (MNOs) like Orange, Vodafone, and Deutsche Telekom, as well as Radio Access Network (RAN) vendors like Ericsson, Nokia, and Huawei. Under standards such as IEC 62232:2025, base stations must be evaluated to map public and occupational exclusion zones.  

The introduction of massive-MIMO and cell-free spatial beamforming means that exposure hotspots are highly dynamic and environment-dependent, rendering static, conservative safety boundaries obsolete. AEGIS offers these customers the ability to simulate and optimize coherent multi-user beamforming patterns in real time, enabling exposure-aware scheduling that maximizes throughput while strictly maintaining compliance.  
3. Commercial Test Labs

Independent testing and certification laboratories, such as Eurofins, CETECOM, Verkotan, SGS, TÜV SÜD, and UL, experience operational bottlenecks due to the physical setup time required for high-frequency measurements.  

Under RSS-102 Issue 6, labs must perform tedious, fine-grained spatial scans over non-planar surfaces using specialized liquid-filled phantoms. AEGIS serves as an accelerated computational pre-screen, allowing labs to quickly model devices and pinpoint worst-case exposure hot spots before setting up robotic measurement probes.  
4. National Regulators and Market Surveillance

Regulatory bodies, including the FCC, ISED, and European national agencies like the Lithuanian Regulatory Laboratory, require independent tools to audit and verify manufacturer compliance filings. AEGIS provides regulators with a fast, standardized computational engine to audit device codebooks and base-station site designs under realistic multi-source conditions.  
Sizing the Total Addressable Market (TAM)

The table below outlines a bottom-up estimation of the addressable market for EMF compliance software, based on active commercial entities and standard enterprise licensing models.
Customer Segment	Active Global Target Base	Est. Annual Spend per Entity (USD)	Total Segment Value (USD)	Primary Drivers & Growth Catalysts
Device OEMs	~60 major consumer electronics brands and RF chipmakers	$150,000 – $250,000 (Multi-seat design & optimization licenses)	$12.0M – $15.0M	

Mandatory APD regulations (RSS-102 Issue 6) ; commercialization of 6G FR3 and sub-terahertz wearables.
Operators & Vendors	~800 active MNOs + 5 dominant global RAN vendors	$25,000 – $60,000 (Site planning and exposure-aware planning modules)	$20.1M – $48.3M	

Denser base-station layouts required for cell-free massive-MIMO ; compliance with IEC 62232:2025.
Commercial Test Labs	~150 tier-1 and tier-2 compliance labs	$30,000 – $75,000 (Testing acceleration software suites)	$4.5M – $11.25M	

Demands for shorter certification cycles; increasing testing complexity from multi-transmitter (TER) mandates.
National Regulators	~100 national spectrum and safety regulators	$15,000 – $30,000 (Verification and market surveillance tools)	$1.5M – $3.0M	

Rapid auditing of consumer device filings; public safety verification of dynamic beamforming arrays.
Total Addressable Market			$38.1M – $77.55M	An extremely high-margin, specialized engineering software market.
 
Competitors & Incumbents

The computational and physical EMF dosimetry market is structured around a small group of highly integrated incumbents, alongside emerging open-source and specialized differentiable solvers.
Competitor / Tool	Primary Technical Offering	Frequency Range	Computational Speed	Pricing Structure	Key Moves & Developments (2024-2026)

ZMT Zurich MedTech AG

(Sim4Life)
	

Industry-standard multi-physics CEM platform. Houses detailed Virtual Population anatomical voxel phantoms.
	

DC to 110 GHz+ 
	

Slow to moderate. High-resolution FDTD requires GPU clusters for mmWave models.
	

High enterprise subscription ($30k–$80k/seat). Pay-per-use on AWS; free Sim4Life.lite for students.
	

Released V5.2 with Total Exposure Ratio (TER) evaluator and a flat-surface APD averaging algorithm in line with current standards.

SPEAG

(DASY8 / cSAR3D)
	

Robotic and array-based physical compliance testing systems.
	

4 MHz to 10 GHz (SAR); extended to 45 GHz (APD) 
	

Fast physical scans; bottlenecked by physical setup and calibration.
	

High capital expenditure ($150k–$400k+ per system), plus annual maintenance.
	

Launched Module APD V2.0 in March 2026, offering full FR3 band coverage down to 10 GHz.

IXUS

(Alphawave / EMSS)
	

Specialized base-station safety and compliance suite with a library of 5,000+ antenna models.
	

Sub-6 GHz to standard 5G mmWave bands 
	

Fast. Relies on simplified analytical field-point calculators and ray-tracers.
	

Enterprise lease or perpetual licensing; bulk discounts available.
	

Integrated with standard field measurement tools (e.g., Narda SRM) and updated to support spatial averaging under IEC 62232.
ANSYS HFSS & CST Studio	General-purpose high-frequency full-wave solvers (FEM, FDTD, FIT).	DC to THz	

Slow for biological phantoms at high frequencies due to meshing limitations.
	$40k–$100k+ annual enterprise licenses.	Enhanced cloud-computing integration; refined voxel meshing algorithms for basic human models.

Remilab

(rfx)
	

3D FDTD EM simulator built entirely in JAX for native gradient-based optimization.
	High-frequency RF and microwave	

Accelerated JAX JIT execution on GPUs.
	

Commercial SaaS Python package subscription.
	

Expanded rfx-fdtd with automated grid configuration, Debye material fitting, and SBP-SAT subgridding.
TICRA / DTU Solver	

PyTorch-based batchable and differentiable antenna array simulator for JPO.
	Far-field array frequencies	

Fast. Uses tensor products to optimize gain masks and beamforming.
	Proprietary research software.	

Demonstrated joint parameterized optimization of large active electronically scanned arrays at NeurIPS 2025.
 
Competitive Positioning and Market Gaps

The incumbent market is polarized between full-wave physical accuracy and fast, simplified analytical planning tools. ZMT’s Sim4Life and SPEAG's DASY8 represent the gold standard for final compliance verification, but they are too slow and computationally expensive to be integrated directly into iterative hardware design or dynamic real-time RAN beamforming loops.  

Conversely, base-station planning tools like IXUS rely on highly simplified free-space propagation models and standard "limit circles" that do not account for the complex electromagnetic interactions and curvatures of actual human bodies.  

Emerging differentiable CEM tools, such as Remilab’s rfx, offer gradient-based optimization, but they are built as general-purpose microwave solvers. They lack the specialized biological phantoms, spatial-averaging algorithms, and tissue database integrations required for regulatory human dosimetry.  

AEGIS occupies a unique market niche: it provides the physical accuracy of non-planar biological skin models in a millisecond-level solver, natively integrated into a differentiable JAX pipeline. This allows AEGIS to act as a bridge between the physical rigor of the Kuster ecosystem and the automated design demands of modern chipmakers and telecom operators.  
Standards & EU 6G-EMF Actors

Establishing AEGIS as a recognized tool in the regulatory compliance landscape requires alignment with international standards organizations and participation in major European research consortia.

                   
                                 |
        +------------------------+------------------------+
        |                                                 |
        v                                                 v
                        
  • IEC 62232:2025 (Published)                      • ISED Canada RSS-102 Issue 6
  • IEC/IEEE 63195-2:2027 (Draft)                     (APD mandatory since Dec 2024)
  • IEC TR 63572:2026 (Published)                   • FCC 6 GHz VLP Expansion

1. Active International Standards and Committees

    IEC TC 106 (Methods for Assessment of Electric, Magnetic, and EM Fields): This is the central international committee governing human exposure standards. AEGIS must track and contribute to the upcoming IEC/IEEE 63195-2 Edition 2.0, which is currently in the Active Committee Draft (ACD) stage, with a forecasted publication date of April 3, 2027. This standard specifies computational procedures (such as FDTD and FEM) for conservative evaluations of incident power density and absorbed power density close to the human body.  

    IEC/IEEE TR 63572:2026: Published in early 2026, this Technical Report explicitly outlines "Evaluation of Absorbed Power Density related to human exposure to radio frequency fields from wireless communication devices operating between 6 GHz and 300 GHz". SPEAG's research under the EURAMET-funded Metrology for Emerging Wireless Standards (MEWS) project (completed October 1, 2025) directly influenced this report, establishing traceable calibration for APD probes and validated near-field reference sources. AEGIS can leverage these public calibration metrics to validate its fast closed-form analytical solvers against identical physical benchmarks.  

    ITU-T Recommendation K.160 (Approved December 2025): Titled "Assessment of human exposure to radiofrequency electromagnetic fields from wireless communication devices operating close to the human body," this standard establishes guidelines for combining SAR, Sab​, and incident power density (Sinc​) measurements using international standards as reference.  

2. Major European 6G Consortia and Actors

The European Union's 6G research roadmap is funded through the Smart Networks and Services Joint Undertaking (SNS JU) under Horizon Europe, succeeding the earlier RISE-6G initiative.  

    The GOLIAT Consortium (Grant 101057262, 2022-2027): This €9.3 million project is the primary European initiative studying 5G/6G EMF exposure and health impacts. Led by Monica Guxens (ISGlobal), it brings together leading academic nodes, including Wout Joseph’s group at Ghent University (€1.07 million in funding) and Joe Wiart’s group at Mines-Télécom (€290,937 in funding). GOLIAT is actively developing next-generation exposure assessment methods to estimate aggregated whole-body and organ doses in young populations. AEGIS can leverage its Ghent University spin-off origin to position its fast computational solver as a standardized tool within GOLIAT for large-scale exposure modeling.  

    6G-GOALS (SNS JU Stream B): This project focuses on semantic and goal-oriented communication networks. It explicitly targets a reduction in transmitted data bits, leading to a "reduction of EMF exposure".  

    OPTI-6G (SNS JU Stream B, 2024-2026): Coordinated by Eurescom, this project integrates cell-free sub-THz and optical wireless communication (OWC) architectures. By replacing standard RF access points with optical beam steering in indoor environments, it aims to eliminate uplink RF interference, resulting in "90% energy savings and a tenfold reduction in EMF radiation levels" compared to sub-6 GHz systems.  

    6G-DISAC (SNS JU, 2024-2026): Focuses on Distributed Intelligent Sensing and Communication (ISAC), optimizing resources across extremely large MIMO arrays and distributed RIS configurations.  

Regulatory Recognition Strategies

For AEGIS to be accepted as a valid pre-compliance or compliance verification tool, the venture should:

    Validate against IEC/IEEE 63195-2 Benchmarks: Publish validation studies comparing AEGIS's millisecond-level outputs against the canonical lossy-dielectric-sphere (Mie) solution and the standardized flat/spherical phantoms defined in 63195-2.  

    Contribute to Technical Reports: Join IEC TC 106 working groups to position fast boundary-approximation methods as acceptable computational procedures for accelerated screening in future editions of standard technical reports.  

    Establish Open-Source Reference Datasets: In collaboration with the University of Split, publish open-source, high-fidelity numerical dosimetry datasets of non-planar exposures. This will lower the barrier to entry for other researchers and establish AEGIS’s physical models as a benchmark in the academic literature.  

Exposure-Aware RIS / MIMO Sub-literature & Gaps

The academic and industrial literature on exposure-aware wireless systems has grown rapidly between 2021 and 2026, driven by public concerns over network densification and the deployment of directional high-frequency beamforming.  
Current Exposure Modeling Paradigms (2021-2026)

    Free-Space Incident Power and "Limit Circles": The most common paradigm in communication theory, championed by Marco Di Renzo (CentraleSupélec) and Dinh-Thuy Phan-Huy (Orange Innovation), treats electromagnetic exposure as a boundary-exclusion problem in free space. To prevent a base station from exceeding regulatory thresholds beyond a specific "limit circle" during long scheduling periods, they optimize transmit phase-shifts using Truncated Beamforming (nulling the MRT beam pattern along angles that breach the limit) or Equalized Beamforming (equalizing path gains across a virtual propagation channel to keep emissions exactly tangent to the limit boundary). While computationally tractable, these models assume free-space propagation and completely disregard the physical presence, posture, and tissue characteristics of human bodies within the environment.  

    Static Uplink SAR Coefficient Matrices: In the uplink (UL) domain, where the user equipment (UE) radiates close to the body, researchers like Chiaraviglio and Emil Björnson model exposure using static Specific Absorption Rate (SAR) matrices. They represent the multi-body SAR constraint as a time-averaged quadratic form:
     
    SARUL​=tr(BQ)


    where B is a diagonal matrix of pre-computed, static SAR coefficients and Q is the transmit signal covariance matrix. While this allows for optimization of transmit power and resource allocation, the coefficients in B are static and cannot adjust to real-time changes in device orientation, near-field coupling, or hand-gripping configurations.  

    Multi-Point Environmental Incident Power Density: To address third-party exposure in multi-user downlink scenarios, optimization frameworks define a set of coordinate points (Q) representing non-users. The base station then minimizes average incident power density (Pavg​, in W/m2) across Q subject to a minimum spectral efficiency (SE) constraint for the target user. This approach relies on a discrete Fourier transform (DFT) codebook to steer nulls toward the non-user coordinates, but it models the human targets as simple point receivers in space.  

Critical Gaps in the Literature

A systematic review of these paradigms reveals two major gaps that prevent exposure-aware beamforming from being deployed in commercial networks.
1. The Disconnect Between Incident Fields and Spatially Averaged Skin Absorption

In the mmWave and sub-THz bands, the human body is highly reflective, and the local curvature of anatomical features (such as the head, limbs, and ears) significantly alters the actual absorbed power density (Sab​). Comparative studies demonstrate that spatially averaged incident power density on a spherical head model is up to 12% to 15% larger than on equivalent planar models due to curvature and near-field coupling.  

Because communication theorists cannot model these complex non-planar boundaries in real time, they must rely on conservative free-space "limit circle" approximations. This conservatism leads to unnecessary reductions in base station transmit power (χ), degrading network coverage and quality of service (QoS).  

AEGIS resolves this gap by providing a fast, closed-form boundary operator that translates incident fields into true, non-planar tissue absorption (Sab​) in milliseconds, allowing operators to safely reclaim transmit power margins.  
2. The Lack of Differentiable Tissue Coupling in Closed-Loop Beamforming

In emerging 6G architectures utilizing active RIS and extremely large MIMO, phase shifts (Φ) must be optimized dynamically to balance communication quality with localized human exposure. However, because existing EM solvers are not differentiable, the optimization of Φ is completely decoupled from the biological tissue response.  

AEGIS's fully differentiable JAX pipeline bridges this gap. By enabling the backpropagation of gradients directly from the skin surface through the electromagnetic boundary, designers can compute the exact derivative of absorbed power with respect to the antenna phase shifts:
∂Φ∂Sab​​

This allows standard gradient descent algorithms (such as Adam) to optimize RIS configurations and beamforming vectors in a single, unified computational pass, enabling real-time, biologically compliant closed-loop beamforming.  
Consolidated Strategic Shortlist

Based on institutional prestige, technological alignment, and commercial fit, the following 12 targets represent the highest-value academic collaborators, industrial partners, and customer accounts for the AEGIS spin-off.
1. University of Split (Computational Electromagnetics Group)

    Type: Academic Collaborator

    Key Figures: Dr. Ante Lojic Kapetanovic / Dr. Dragan Poljak

    Fit Rationale: The premier research group applying automatic differentiation to high-frequency computational dosimetry and non-planar skin modeling. A partnership would combine their boundary element autodiff expertise with AEGIS's fast closed-form analytical operators.  

    Primary Source:(https://data.fesb.unist.hr/documents/public/news/Doktorski%20rad-za%20objavu%20-Ante.pdf)  

2. imec / Ghent University (WAVES Group)

    Type: Academic Collaborator / Parent Institution

    Key Figures: Dr. Wout Joseph

    Fit Rationale: The original academic group of the AEGIS founder, providing access to robotic measurement systems, extensive ray-tracing databases, and direct funding routes through the Horizon Europe GOLIAT and Methusalem SHAPE projects.  

    Primary Source:(https://research.ugent.be/web/person/robin-wydaeghe-0/en)  

3. Orange Innovation

    Type: Target Customer / Industrial Partner

    Key Figures: Dr. Dinh-Thuy Phan-Huy

    Fit Rationale: Orange is actively patenting and publishing on exposure-aware RIS, truncated beamforming, and green networks. They are an ideal industrial partner to validate AEGIS's JAX pipeline inside real-world carrier networks.  

    Primary Source:(https://hellofuture.orange.com/wp-content/uploads/sites/56/2022/03/White-Paper-%E2%80%93-Oranges-vision-for-6G-%E2%80%93-March-2022.pdf)  

4. SPEAG (Schmid & Partner Engineering AG)

    Type: Distribution Partner / Potential Acquirer

    Key Figures: Dr. Niels Kuster

    Fit Rationale: The global incumbent for physical compliance testing. As they expand DASY8 Module APD V2.0 for 6G FR3 compliance, they require a fast computational pre-screening tool to offer device manufacturers.  

    Primary Source:(https://speag.swiss/news-events/news/measurement/2026/dasy8-module-apd-v2-0-full-fr3-coverage-for-apd-compliance-testing)  

5. Technical University of Denmark (DTU) & TICRA

    Type: Academic & Computational Partner

    Key Figures: Dr. Allan Peter Engsig-Karup / Frederik Faye

    Fit Rationale: Developed batchable, differentiable PyTorch simulators for the joint parameterized optimization of active antenna arrays. Integrating AEGIS's differentiable biological dosimetry operator into their far-field solvers represents an immediate win-win.  

    Primary Source:(https://openreview.net/forum?id=bjyUK5NX0a)  

6. Mines-Télécom / Télécom Paris

    Type: Academic Collaborator

    Key Figures: Dr. Joe Wiart

    Fit Rationale: Leader of stochastic dosimetry work packages inside the Horizon Europe GOLIAT consortium. He is critical for backing AEGIS's fast analytical models with robust statistical uncertainty frameworks.  

    Primary Source:(https://projectgoliat.eu/about/)  

7. CNR IEIIT Milan

    Type: Academic Collaborator

    Key Figures: Dr. Gabriella Tognola / Dr. Martina Benini

    Fit Rationale: Leading the dosimetry of active RIS in urban environments under the EXPOAUTO project. Their research group needs fast, non-planar human absorption models to evaluate pedestrian exposure in real-time vehicle-to-everything (V2X) setups.  

    Primary Source:(https://ieeexplore.ieee.org/document/10715541/)  

8. Aalborg University (Antenna & Propagation Group)

    Type: Academic Collaborator

    Key Figures: Dr. Shuai Zhang / Dr. Gert F. Pedersen

    Fit Rationale: Developed the RAWA-NN deep learning proxy models for fast APD and temperature rise computation. A partnership would allow AEGIS to combine physics-informed differentiable models with pure data-driven neural network proxies.  

    Primary Source: Aalborg University Publications  

9. Remilab.ai

    Type: Technology Partner / Competitor

    Key Figures: Core Developers of rfx

    Fit Rationale: Developers of the JAX-based rfx 3D FDTD simulator. Partnering would allow AEGIS to build a unified workflow where its fast analytical skin-layer operator acts as a pre-screen, seamlessly passing complex cases to rfx for full-wave FDTD verification.  

    Primary Source:(https://remilab.ai/rfx/)  

10. ZMT Zurich MedTech AG

    Type: Target Customer / Computational Incumbent

    Key Figures: Sim4Life Business Product Leads

    Fit Rationale: The industry-standard computational life-sciences platform. By licensing AEGIS's fast analytical dosimetry engine, ZMT can integrate a fast, real-time pre-screening module into their Sim4Life cloud platform to address their pay-per-use business market.  

    Primary Source:(https://sim4life.swiss/business)  

11. Alphawave Mobile Network Products (IXUS)

    Type: Potential Partner / Acquirer

    Key Figures: Dirk Ludick

    Fit Rationale: Developers of the IXUS software suite, the dominant tool for base station EMF compliance among major carriers. Adding AEGIS's millisecond-level dynamic beamforming exposure operator would modernize their static 3D CAD modeller for cell-free 6G networks.  

    Primary Source:(https://www.emssixus.com/ixus-software/)  

12. Eurescom GmbH

    Type: Research Consortium Coordinator

    Key Figures: Project Directors for SNS JU

    Fit Rationale: Coordinates major 6G-EMF transition projects, including the newly funded OPTI-6G consortium. Partnering with Eurescom ensures AEGIS can be written into the next round of Horizon Europe SNS JU Stream B/C/D proposals.  

    Primary Source:(https://opti-6g.sns-ju.eu/)  

Report unsafe content Opens in a new window
