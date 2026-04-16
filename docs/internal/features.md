# AEGIS feature inventory

*Current as of v0.28.0 (April 2026). Updated on each release when user-facing features are added.*

## Core physics engine

- DosimetryEngine central dispatch with 9 fidelity levels (0-8) and mode-based routing (bound, aggregate, spatial, coherent, ecbf)
- Core absorption law: Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]
- PropagationPaths dataclass for batch storage of N paths with directions, complex polarisation-amplitude vectors (psi), element indices, delays, and LOS flags
- Vectorized per-path incident power density: S_i = |psi_i|^2 / (2 * Z_0)
- Path construction from scalar power and direction via PropagationPaths.from_powers with automatic perpendicular polarisation assignment
- Path generation from spherical coordinates and uniform sphere sampling for Monte Carlo and worst-case analysis
- Path concatenation with optional element index reindexing
- LOS and NLOS path filtering properties
- JSON serialization/deserialization of complex arrays using {"real": [...], "imag": [...]} format with round-trip fidelity
- DosimetryResult frozen dataclass with per-triangle S_ab, p_abs, SAR, fidelity level, and coherent-specific fields (Q, rho, eigenvalues)
- Per-triangle incident power density (sinc) computation for incoherent and coherent modes
- Absorbed power computation: P_abs = sum(S_ab * areas)
- Whole-body SAR computation: P_abs / mass
- Spatial averaging at ICNIRP 4 cm^2 via precomputed sparse averaging matrices (CSR format)
- 1 cm^2 spatial averaging for frequencies above 30 GHz
- Thread-safe LRU cache (max 16 entries) for averaging matrices keyed on geometry hash and target area
- Result scaling by arbitrary power factors for parameter sweeps (linear in transmit power)
- Comparison of multiple dosimetry results across fidelity levels with relative errors, RMSE, and max absolute errors
- Sweep across multiple fidelity levels with convergence analysis and silent skipping of levels with missing parameters
- Peak S_ab extraction with triangle index, mean S_ab, and illuminated triangle count
- Path contribution analysis: per-path contribution ranking, top-k filtering, exposure heatmap (M, N) matrix, importance scoring
- SimulationConfig frozen dataclass aggregating TissueConfig, BodyConfig, AntennaConfig, RayTracerConfig, DosimetryConfig, ChannelConfig, MIMOConfig
- YAML serialization/deserialization and CLI argument parsing with per-parameter overrides
- Power unit conversion (dBm to watts)
- Physical constants: C_0, EPS_0, MU_0, Z_0; defaults: 28 GHz, 43 dBm, level 2, 3 bounces
- JAX array detection and NumPy conversion for cross-framework compatibility
- Lazy module loading via __getattr__ for all public API classes
- Finite value validation for S_ab with NaN/Inf reporting; degenerate mesh triangle detection
- Numerical stability: safe division guards, unit vector validation (1e-5 tolerance), vectorized cross products
- Timing profiling: kernel execution time, averaging matrix build time, matrix-vector product time
- Thread-safe timings lock for concurrent requests

## Fidelity levels (0-8)

- Level 0 (Bound): worst-case absorbed power bound using absorption area A_ab and max directivity D_max; uniform surface distribution
- Level 1 (Aggregate): directivity-weighted absorption via spherical harmonics, LUT nearest-neighbor, or isotropic fallback; uniform surface distribution of aggregated power
- Level 2 (Geometric): ReLU spatial map with cosine-of-incidence via dot product of normals and incident directions; constant Fresnel T0
- Level 3 (Fresnel): angle-dependent Fresnel transmission with TE/TM decomposition; unpolarised average (T_s + T_p) / 2
- Level 4 (Polarisation): polarisation-aware correction via parameter q modifying effective transmission T_eff = T_avg + (q/2) * DeltaT
- Level 5 (Curvature): additive curvature perturbation using twice mean curvature H and wavenumber k; non-negative clamping
- Level 6 (Diffraction): physical GELU activation replacing hard ReLU shadow boundary; sigma from sqrt(lambda * H / (4pi)); diffraction-aware curvature correction
- Level 7 (Coherent MIMO): body-surface channel G_tilde(r) with precoder application; per-triangle S_ab = ||G_tilde @ x||^2; exposure operator Q and eigendecomposition; rho metric
- Level 8 (ECBF): exposure-constrained beamforming via QCQP solver; optimal precoder x* maximizing signal power subject to P_abs and transmit power constraints
- Unified spatial kernel with composable corrections (fresnel, polarisation, curvature, diffraction flags)
- Automatic chunking for large M*N > 50M problems to bound memory
- JAX compatibility detection for automatic dispatch to compiled kernel

## Tissue and dielectric modeling

- TissueModel frozen dataclass with relative permittivity (eps_r), conductivity (sigma), and frequency
- Complex refractive index n_tilde from permittivity and conductivity
- Normal-incidence power transmission coefficient T0 calculation
- 4-pole Cole-Cole permittivity model (Gabriel 1996) with 14 parameters per tissue
- Per-pole dispersion modeling (delta, tau, alpha) with static conductivity integration
- Debye single-pole permittivity model (Cole-Cole with alpha=0)
- Vectorized frequency array support for spectrum computation
- IT'IS v5.0 tissue database (SQLite, 7 MB) with Gabriel model parameter extraction
- Database lookup by tissue name with caching for performance
- Frequency-dependent complex permittivity, conductivity, extinction coefficient, and transmission coefficient retrieval
- Predefined tissue instances: SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ
- Multiple skin model variants: ITIS, Christ2021 (1.2x scaled), Christ2025, NICT
- Tissue measurement data (measurements-Skin.csv)
- Energy-conserving Fresnel transmission computation for TE (s) and TM (p) polarisations
- Fresnel amplitude reflection and transmission coefficients
- Numerically stable square-root branch selection and grazing incidence handling (mu < 1e-10 floor)
- JIT-safe and array-backend compatible Fresnel computation
- Tissue spectrum plotting with matplotlib integration (permittivity and conductivity dual-axis)

## Body geometry and mesh

- Binary STL file loading with vectorized numpy I/O (~50-100x over struct.unpack)
- BodyMesh frozen dataclass: triangles, normals, centroids, areas, name, content-based geometry hash
- Icosphere mesh generation with configurable subdivision depth; capped cylinder mesh generation
- STL binary format writing; mesh from raw vertex arrays with automatic normal computation
- Bounding box caching, mesh center, height, scale, n_triangles, total_area properties
- Fibonacci sphere sampling for near-uniform S^2 distribution (golden spiral, deterministic, cached up to 32)
- Projected area A_perp computation with cosine-weighted projection and chunked direction processing
- Directivity D = A_perp / mean(A_perp) normalization
- Spherical harmonic fitting (complex coefficients, configurable degree L) with reconstruction error metrics (RMS, max, p99)
- Cauchy surface area formula for convex bodies; mean projected area; self-occlusion metric
- Cosine-weighted ambient occlusion (exposure fraction eta) with BVH acceleration
- BVH construction (median-split, configurable leaf size), ray-AABB and Moller-Trumbore intersection tests
- Numba JIT acceleration with fallback; ThreadPoolExecutor parallelization for >100 triangles
- ICNIRP 4 cm^2 and 1 cm^2 spatial averaging matrix construction (area-weighted, row-stochastic, sparse CSR)
- Numba-accelerated matrix building (~15-30x speedup); KDTree-based neighbor querying
- JAX BCOO sparse array conversion for differentiable averaging
- Device offset estimation: smartphone position from mesh, eye/head detection, face direction, forward distance parameterization
- 8 phantom models: thelonious (cat, 17.4 kg), duke (72.4 kg), eartha (56.0 kg), ella (58.7 kg), adult_male (73 kg), adult_female (60 kg), boy_6y (19 kg), girl_8y (30 kg)
- GLB/FBX animation models with poses: idle, walking, phone_ear_r, phone_ear_l, sitting
- SMPL-X parametric body generation from shape (betas) and pose parameters with batch support; gender selection (neutral, male, female)
- glTF skeleton loading, forward kinematics, linear blend skinning (LBS) with 4 joint influences per vertex
- Joint hierarchy extraction, inverse bind matrices, local/global transform composition, quaternion to rotation matrix conversion
- Posed mesh generation with FK+LBS and normal recomputation after deformation

## Coherent MIMO and beamforming

- Field channel matrix G(r) computation from multipath propagation with phase propagation exp(-jk0 * k_hat . r)
- Scatter-add accumulation of path contributions by antenna element index
- NumPy and JAX dual-backend implementation
- Fresnel operator F_n(r) with TE/TM basis vector generation and rank-2 projection operator
- Front-facing path filtering (Heaviside gate for mu <= 0); normal incidence fallback for parallel k_hat
- Body-surface channel G_tilde(r) with depth coupling factors sqrt(sigma / (4*alpha_n)) for tissue penetration
- Approximation 2: depth coupling Gamma ~ 1 (< 0.44% error at 28 GHz)
- Factored Fresnel computation: O(N_center) instead of O(N_center * M_elements); 16x+ speedup for 4x4 UPA
- Antenna array with M elements at arbitrary positions; UPA factory (n_h x n_v, d_h x d_v spacing)
- Isotropic and patch element patterns (cos^q(theta), q=1.5 default) with backside suppression
- Steering vector computation with per-element phase advances and pattern gain
- Path expansion from center-of-array to per-element paths via phased array far-field model
- UE channel vector h: steering matrix, half-wave dipole effective length (Balanis formula), UE phase per path
- MIMOScene container: array, users, frequency, power, tissue model
- UserConfig (phantom, position, orientation, device position) and UserState (body, paths, h, G_tilde, Q, result)
- Stacked channel matrix H (K, M_ant) assembly; exposure operator list for multi-user constraint evaluation
- build_user_channels, compute_mimo_scene, compute_mimo_scene_with_bodies orchestration pipelines
- Per-stage timing measurement (channels_ms, precoder_ms, sab_and_engine_ms, total_ms)
- Per-triangle multi-stream S_ab: ||G_tilde[m] @ W||_F^2; total absorbed power: trace(W^H Q W)

## Exposure operator and ECBF

- Exposure operator Q = integral G_tilde^H G_tilde dA; Hermitian PSD by construction
- Total absorbed power: P_abs = x^H Q x
- Eigendecomposition with descending ordering and noise clamping
- Exposure-signal alignment rho = h^T Q h* / (||h||^2 * lambda_max), normalized to [0, 1]
- QCQP solver: max |h^T x|^2 s.t. x^H Q x <= P_abs_max, ||x||^2 <= P
- Eigendecomposition-based transformation to Q eigenbasis
- Null-space detection and concentration as lambda -> infinity
- Power-slack regime handling; per-column budget allocation
- Bisection root-finding for constraint satisfaction; minimum-absorption direction fallback
- Complementary slackness condition enforcement

## Optimization

- Mode-agnostic optimizer dispatcher with cancellation, per-iteration yield, and convergence detection
- MIMO peak S_ab optimizer: projected gradient descent on soft_peak_exposure(coherent_sab(G_tilde, x))
- Log-sum-exp soft peak with temperature parameter; Adam optimizer with bias correction
- Power constraint projection; JAX automatic differentiation with finite-difference fallback
- Convergence: 6-iteration history buffer with 0.1% relative change threshold
- Tilt/power optimizer: joint gradient descent on (tilt_deg, log_power_dbm) for ICNIRP compliance maximization
- Rodrigues formula for boresight tilt rotation; cosine^n radiation pattern gain
- Violation penalty: lambda * (peak_sab - limit)^2; parameter bounds enforcement
- Placement optimizer: grid search over 2D points with constraint axis support
- Per-point evaluation callback; best position tracking; progress ratio reporting
- Differentiable primitives: peak_exposure, total_absorbed_power, soft_peak_exposure, coherent_sab (all JAX-compatible)

## Compliance and regulatory

- ICNIRP 2020 evaluation from 100 kHz to 300 GHz for general public and occupational scenarios
- Peak spatially-averaged S_ab over 4 cm^2 and 1 cm^2 (above 30 GHz) compliance checks
- Whole-body SAR compliance check
- Peak local and whole-body incident power density (S_inc) compliance checks
- Frequency-dependent ICNIRP limit retrieval
- Compliance margin calculation in dB; maximum compliant TX power (watts and dBm)
- Human-readable compliance summary text generation
- RF link budget compliance evaluation (TX power, gain, distance)
- Power sweep compliance across TX power range; frequency sweep across 10 kHz to 300 GHz
- Spatial compliance grid at 3D positions
- 2D compliance heatmap (frequency x power axes) with per-point margin and max power per frequency
- JSON compliance output format
- Thermal relaxation time (T0) computation

## Stochastic channel modeling

- 3GPP TR 38.901 cluster-based stochastic channel generator with configurable cluster count and sub-paths per cluster
- 3GPP sub-path offset angles (20 fixed-offset table); exponential PDP with K-factor
- Cluster arrival angles with ASA/ESA-weighted scaling; LOS rotation to antenna-body direction
- Sub-path expansion with angular offsets; path loss integration into incident power density
- Spatial consistency mode via SC_lambda parameter; shadow fading generation
- Logdist, dual-slope, NLOS, and FSPL path loss models
- Large-Scale Fading model with spatially consistent, cross-correlated LSP maps
- 8 large-scale parameters (DS, KF, SF, ASD, ASA, ESD, ESA, XPR) with frequency-dependent mu/sigma scaling
- Per-parameter decorrelation distances; 8x8 inter-parameter correlation matrix with Cholesky factorization
- Sum-of-Sinusoids spatial correlation engine (QuaDRiGa v2.8.1); deterministic seed control
- 2D LSP map generation on horizontal planes with configurable resolution
- QuaDRiGa .conf file parsing for channel presets (116+ parameter types) with LRU cache (max 32)
- Scenario families: 3GPP 38.901 (UMi, UMa, RMa), 37.885 (V2X), 3D; QuaDRiGa, WINNER, mmMAGIC, 5G-ALLSTAR
- Visualization metadata output (cluster angles, powers, delays, departure angles)

## Ray tracing integrations

- DiffeRT ray tracer integration with TE/TM polarization decomposition and multi-bounce support
- Surface normal handling and Fresnel reflection coefficients per bounce
- Polarization tracking through reflections; material refractive index lookup
- Dual-polarization (horizontal/vertical); propagation phase tracking for coherent levels 7-8
- LOS detection; multi-element TX array support with element index assignment
- Variable bounce order with path padding and concatenation
- Sionna RT integration with dual-polarized isotropic RX; cross-polarization (theta/phi)
- JAX array output with gradient tracking; channel impulse response extraction
- Spherical basis vector computation; Sionna CIR to AEGIS psi conversion
- TX patterns: isotropic, half_wave_dipole; RT parameters: max_depth, specular/diffuse reflection, refraction, diffraction
- Modal serverless GPU: DiffeRT on T4 (JAX/CUDA 12), Sionna RT on L4 (OptiX)
- 120-second scaledown; volume-based scene caching; up to 1M rays per trace
- Per-order reflection loss modeling; path visualization data for 3D ray rendering
- Voxel geometry support with dynamic mesh-to-Sionna conversion; dual-tier scene caching
- Gzip+pickle compression for network optimization; automatic PLY mesh writing
- Mitsuba XML scene generation from voxel geometry; 10 predefined material types
- Specular/diffuse reflection, refraction, diffraction, edge diffraction controls
- Synthetic array generation for MIMO; seed control for reproducibility
- CloudRF API client for antenna database, coverage heatmaps (GeoTIFF), point-to-point link budget
- 7 predefined CloudRF templates (5G C-Band, LTE eNodeB, LoRa GW, WiFi AP, PMR446, DMR, Starlink)
- 12 Sionna synthetic scenes (box, floor_wall, street_canyon variants)

## Base station pipeline

- AntennaPattern: 181x360 radiation pattern matrix with elevation/azimuth indexing
- BaseStation dataclass: location, RF parameters, orientation, provenance
- ExposureConfig: duplex mode, TDD downlink ratio, power reduction factor, traffic load factor
- BeamConfig: mMIMO broadcast/traffic beam separation with independent gain, beamwidth, and sweep parameters
- MSI file format parsing (Kathrein, Commscope, Huawei) with nested zip support; H-plane and V-plane attenuation
- Gain unit conversion (dBi, dBd); tilt angle and vertical convention detection (boresight vs zenith)
- Separable approximation reconstruction (3GPP TR 38.901 Sec 7.3) from 1D cuts to 2D patterns
- Gaussian fallback pattern from beamwidth (ITU-R F.1336-5); sidelobe suppression floor
- Pattern library: SQLite index with manufacturer/model/frequency/gain search; auto-decompression
- Three archetype classification: mmimo (>=20 dBi + 5G), sector, small_cell (<10 dBi)
- Element grid inference (n_h, n_v) from array gain with standard grid snapping per archetype
- Physical panel dimensions from element grid and frequency (half-wavelength spacing)
- TDD/FDD mode determination from technology and frequency bands; TDD band definitions (NR n41/n77/n78/mmWave, LTE B38/B40/B42/B43)
- PRF assignment per archetype
- Multi-source extraction: basestationLib (Belgium), OpenCellID, Mastedatabasen (Denmark), ANFR (France), BNetzA (Germany), RTR (Austria), ACMA (Australia), Antenneregister (Netherlands)
- Bounding box, operator, technology, and frequency band filtering; multi-source parallel extraction with timeout
- Spatial deduplication via cKDTree within 50m per operator and frequency band
- Multi-source conflict resolution with priority-based selection; estimation from technology+frequency groupby medians
- Validation: power 0-80 dBm, azimuth 0-360 deg; data coverage reporting with per-field completeness
- Parquet I/O with PyArrow; provenance column tagging; pattern source tracking (gov, synthetic, estimated, missing)
- Confidence score per source type; dosimetric impact weights for aggregate confidence
- WGS84 to ENU conversion and reverse; antenna rotation matrix from azimuth + tilt
- EIRP to TX power conversion; single LOS path generation with distance-based filtering
- Pattern-modulated power density with gain interpolation; isotropic fallback
- Exposure modes: THEORETICAL (full power), ACTUAL_MAX (broadcast/traffic envelope), TYPICAL (summed with load factors)
- TDD downlink ratio and traffic load factor application; in-sweep detection for traffic beams
- Extract/merge/validate/report pipeline stages; YAML region configuration with per-source priority

## 3D environment reconstruction

- WGS-84 to ECEF and ECEF to local ENU coordinate conversions
- Transverse Mercator projection (degrees to local XY meters)
- Three.js Y-up coordinate transformation
- 13+ material types with EM properties: concrete, brick, glass, metal, asphalt, vegetation, water, wood, ground, roof tile, soil, dense vegetation, plaster
- OpenStreetMap import via Overpass API with retry, rate-limit handling, and multiple server mirror fallback
- OSM parsing for buildings (simple ways and multipolygon relations), highways, water bodies, natural features
- Building-with-parts relations (hierarchical); building height from tags with type-based defaults
- 12 roof shapes: flat, gabled, hipped, pyramidal, skillion, half-hipped, gambrel, saltbox, mansard, dome, onion, round
- Per-level wall geometry with recessed window and door openings; glass recess depth
- Building style library: default, house, detached, apartments, office, commercial, industrial, retail, garage
- Polygon triangulation (fan algorithm); wall extrusion from 2D footprint; face normal computation
- Road centerline to quad-strip mesh conversion with highway type classification and width mapping
- Water polygon footprint extraction; forest canopy generation; hedgerow geometry; ground plane generation
- SRTM1 HGT tile download and caching (~30m resolution); elevation grid with bilinear interpolation
- Terrain mesh generation from elevation grid; Z-value projection for arbitrary XY points
- OGC 3D Tiles v1.0/1.1 traversal (Google Photorealistic 3D Tiles) with geometric error filtering
- GLB/B3DM tile content parsing; glTF 2.0 binary format with accessor decompression
- Per-vertex color classification to MaterialType; ECEF to local ENU for tiles
- Google API key authentication and session token support
- GeoJSON FeatureCollection parsing and import; ring projection from lon/lat to local XY
- Scene export: Mitsuba XML for Sionna RT, PLY per material group, DiffeRT TriangleScene with JAX arrays
- Per-material RGB colors; brick/plaster/concrete color palettes; HSV-based material classification
- EnvironmentMesh unified representation with origin and source tracking
- Degenerate geometry filtering; malformed OSM relation recovery; void SRTM handling; fallback on complex roof failure

## Web viewer backend (API)

- Flask server with session-based password authentication, CORS, and security headers (CSP, X-Frame-Options, HSTS)
- Multi-threaded request handling with binary data streaming and chunked responses
- POST /api/compute: mode-based dosimetry with per-correction toggles, multi-antenna support, stochastic channel, inline mesh upload, body offset/rotation, tissue model and exposure scenario selection
- POST /api/compute/rt: DiffeRT ray tracing (local CPU or Modal GPU fallback) with voxel hull, environment mesh, and scene support
- POST /api/compute/sionna-rt, /api/compute/voxel-rt, /api/compute/sionna-env-rt: Sionna RT endpoints with scene caching and material assignment
- GET /api/body: body mesh binary with X-Meta header; GET /api/voxels: voxel data binary; GET /api/tiles: GLB tile listing and serving
- GET /api/phantom/<name>.glb: GLB phantom serving with path traversal protection
- POST /api/scene/load: Sionna scene geometry extraction; POST /api/parametric-body: SMPL-X/Anny generation
- POST /api/environment/osm, /3dtiles, /from-voxels, /combine, /geojson: environment mesh construction endpoints
- POST /api/terrain/elevation: SRTM elevation mesh generation with flat terrain fallback
- POST /api/environment/export-scene: DiffeRT and Sionna XML export
- GET /api/environment/materials: material catalog with EM properties
- POST /api/basestations/load: multi-source loading with geocoding, bbox/radius filtering, operator/technology filtering, region mapping
- POST /api/basestations/compute: multi-station dosimetry with archetype-aware exposure modes
- POST /api/basestations/compute_mimo: mMIMO dosimetry with element grid inference and ENU transform
- GET /api/basestations/coverage: global overview with binary packing (12 bytes/site)
- GET /api/patterns/search, /manufacturers, /<source>/<path>: pattern library search and binary pattern loading
- POST /api/patterns/build-index: MSI zip scanning and SQLite index rebuild
- POST /api/mimo/compute: coherent MIMO scene with UPA, multi-user phantoms, precoder selection; GET /api/mimo/result/<user_id>, /api/mimo/summary
- GET /api/compliance/limits, /summary, /power-sweep, /heatmap, /frequency-sweep: ICNIRP evaluation endpoints
- POST /api/compliance/spatial: gridded compliance with free-space path loss
- GET /api/tissue/spectrum: frequency-vectorized dielectric spectrum with skin model variants
- POST /api/validate/sinc: CloudRF SINC validation with great-circle path loss
- POST /api/optimize: SSE streaming optimization (mimo_peak, tilt_power, placement) with cancellation
- GET /api/export/dosimetry-csv, -json, -npz: per-triangle export in multiple formats
- GET /api/config, /api/viewer-config, /api/levels, /api/body/info, /api/health, /api/system: system metadata endpoints
- POST /api/export-config: merged config with camelCase mapping and fidelity level inference
- GET /api/location/load: SSE pipeline streaming with voxelEarth integration; POST /api/location/cancel
- GET /api/geocode: Google Geocoding wrapper
- POST /api/bug-report: screenshot capture, GitHub issue creation; POST /api/sentry-webhook: HMAC-verified Sentry integration with rich issue generation
- Configuration system: server, scene, camera, renderer, lighting, body material, voxels, antenna, physics, interaction, dosimetry, MIMO, colormap, distance viz, RT paths, base station, UI styling, named scenarios

## Web viewer frontend (UI/UX)

- Three.js canvas rendering with React Three Fiber and Zustand state management
- Orbit, follow, and globe camera modes with presets (front, side, top, focus, reset) and FOV adjustment
- Real-time SAB heatmap on 3D body model with dynamic range control, colormap selection, dB scale toggle, and peak indicator
- Multi-mode dosimetry: Bound, Aggregate, Spatial with per-correction toggles (Fresnel, Polarisation, Curvature, Diffraction)
- Interactive antenna placement via click-to-place; multiple antenna management with per-antenna power, enable/disable, and element pattern selection
- Antenna array configuration (horizontal/vertical elements, element spacing); 3D radiation pattern visualization with gain interpolation
- Pattern browser: search across local and CloudRF databases, polar plot preview, pattern loading/caching
- MIMO mode: multi-user management, phantom assignment, orientation control, precoder selection (MRT, ZF, MMSE, ZF+Exposure)
- Automatic precoder fallback (M < K); per-user SAB results and compliance; show-all-heatmaps toggle; precoder weight display
- Multiple phantom selection (8 STL + animated GLB with pose controls); body rotation and offset positioning
- Environment sources: None, Voxels, OSM, 3D Tiles, Cesium; geocoding search with radius control
- OSM loading with building height config; 3D Tiles with geometric error LOD; GeoJSON upload; environment reload centered on antenna
- Ray tracing backend selection (Sionna, DiffeRT) with method, reflection, diffraction, and seed controls
- Ray path visualization with order-based coloring (LOS white, 1st orange, 2nd+ red)
- Stochastic channel mode with preset selection, parameter overrides, LSP heatmap, and cluster/subpath visualization
- Base station loading by location with operator/technology/frequency filtering and color coding
- Base station markers, detail viewing, dosimetry computation, antenna pattern visualization
- Global coverage map with zoom-level transitions, site density, operator coloring, and one-click setup to local scene
- ICNIRP compliance indicators (pass/warn/fail); frequency-dependent quantity switching at 30 GHz
- Power sweep and frequency sweep analysis charts (Recharts); compliance heatmap visualization
- Optimization controls: placement grid search, tilt+power sweep, MIMO peak optimizer with iteration display and convergence tracking
- Configuration export (JSON/YAML); shareable state links with URL encoding; dosimetry export (CSV, JSON, NPZ)
- Responsive sidebar (hidden/rail/expanded) with grouped sections (World, Source, Exposure, Analysis)
- Keyboard shortcuts with help overlay; status bar with timing and GPU info; notification toasts
- Welcome overlay, guided tour (9 steps), and tour completion tracking
- Touch controls for mobile; orientation-aware layout; camera widget for manual positioning
- Voxel field visualization with per-material toggles; environment display modes (cubes, hull, tiles)
- Distance line visualization; compliance ring with directivity-aware boundary; optimize grid preview
- Lazy asset loading; binary protocol for data transfer; streaming responses; request abort/cancel
- Sentry error tracking integration; local storage persistence with schema versioning
- Error boundary protection at app and scene level

## Visualization and analysis

- Plotly interactive 3D mesh heatmap with per-triangle hover text, configurable colormap, and HTML/PNG export
- Matplotlib static 2D projection heatmap with painter's algorithm depth sorting
- Side-by-side S_ab comparison across multiple fidelity levels (Matplotlib 2D and Plotly 3D subplots)
- Multi-panel compliance assessment figure: S_ab histogram with ICNIRP limit line, pass/fail status bar, margin in dB
- Q eigenvalue spectrum bar chart (coherent results) with color-coded scaling
- Rho (exposure-signal alignment) semicircular gauge with green/orange/red gradient
- Peak S_ab versus frequency sweep plot with logarithmic scaling and ICNIRP reference line
- Tissue material spectrum visualization (Cole-Cole permittivity) with dual-axis plots
- Scene load and ray trace timing metrics
- Dark theme support; lighting simulation parameters (ambient, diffuse, specular, roughness)

## Data, infrastructure, and deployment

- JAX-based differentiable kernels with NumPy fallback via AEGIS_ARRAY_BACKEND env var; JAX 64-bit precision
- Numba JIT optional fast backend for ambient occlusion and averaging matrix construction
- Git LFS for large files (STL meshes, databases); Parquet for base station datasets
- AEGIS_DATA_DIR and SIONNA_SCENES_DIR environment variables
- Hatchling build backend with hatch-vcs (version from git tags); Python >= 3.11
- Core deps: numpy, scipy, pyyaml; optional: JAX, matplotlib, plotly, Flask, DiffeRT, Sionna, Modal, smplx, torch, pygltflib
- aegis-run CLI entry point for batch processing with YAML configuration
- 2443 test cases across 143 test files; pytest with pytest-xdist (2 workers) and Hypothesis property testing
- CodSpeed benchmarking integration
- Ruff linting (120 char, rules E F W I UP B SIM); pre-commit hooks with codespell
- GitHub Actions CI with Ubicloud runners; lint job + test matrix (Windows + Linux x 3.11/3.12/3.13)
- Codecov integration
- Docker buildx multi-platform images (ghcr.io, tagged by SHA and latest); Debian Slim Python 3.12 containers
- Hetzner cloud deployment via SSH; docker-compose: Caddy + Flask (Gunicorn gthread, 2 workers, 4 threads) + Umami + PostgreSQL
- Caddy reverse proxy with HTTPS, HSTS (63072000s), JSON logging
- 3GB memory limit; 600s Gunicorn timeout
- Sentry error tracking with release tracking, auto-commit association, and deploy notification
- Umami web analytics (PostgreSQL 15 backend)
- Claude Code GitHub Action for QA swarm (manager + 5 testers) and code review agent
- Playwright for E2E browser automation; feature agent, labeler, issue-labeler workflows
- Modal GPU offload (T4 for DiffeRT, L4 for Sionna RT); TensorDock cloud GPU support
- Google API key for geocoding and 3D Tiles; CloudRF API key for antenna patterns and coverage
- MkDocs Material documentation with Jupytext integration; Getting Started, 6 tutorials, 8 concepts, 11 guides, developer guide
- LicenseRef-Proprietary license
- Config-driven scenario launcher with named scenarios (open_ground, mmwave_close, urban_ghent, indoor_office)
- Regional power configs: indoor_office (23 dBm), mmwave_close (10 dBm), outdoor_urban (43 dBm)
