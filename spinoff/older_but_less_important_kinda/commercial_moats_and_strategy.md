# AEGIS commercial moats and product strategy

April 2026. Working document for IDF revision and spin-off positioning.

---

## What we actually built vs. what the IDF says we built

The IDF (April 1, 2026) frames AEGIS as a closed-form dosimetry method. That is accurate but incomplete. The IDF reads like a physics paper with a software mention at the end. The actual platform has capabilities that no competitor has, and the IDF barely touches them.

This document identifies what matters commercially, why, and where the SaaS should focus.

---

## The seven moats

### 1. Real base station data pipeline

AEGIS ingests real antenna installations from 14 government databases (Belgium, France, Germany, Denmark, Netherlands, Austria, Luxembourg, Poland, Spain, Switzerland, UK, Canada, Brazil, Australia, New Zealand, plus OpenCellID). ~293K antennas. Each station gets classified (mMIMO, sector, small cell), assigned a radiation pattern (1200+ from CloudRF or Gaussian fallback), and annotated with confidence scores per field.

Why this matters: No compliance tool starts from real deployments. They all start from hypothetical scenarios. An operator's RF planning team can type a city name and immediately see their own antennas with real patterns and real power levels. That is the demo that sells.

Why it's a moat: Government APIs are messy, undocumented, and change without notice. The extraction, normalization, spatial deduplication, and provenance tracking took weeks of engineering. A competitor would need to replicate this per country. We already cover the largest EU markets.

IDF gap: One throwaway line mentions base station databases. Should be a dedicated section.

### 2. 3D environment reconstruction

AEGIS builds ray-traceable 3D scenes from multiple sources: OpenStreetMap (buildings with 12 roof types, roads, water, vegetation), Google Photorealistic 3D Tiles, SRTM terrain elevation, GeoJSON uploads, and voxel data. Each source produces triangle meshes with per-face material classification and EM properties (permittivity, conductivity). Scenes export to both DiffeRT and Sionna RT formats.

Why this matters: Ray tracing needs geometry. Today's workflow is: manually model a building in CST, spend a day setting materials, run one simulation. AEGIS generates a complete urban scene from a geocoded address in seconds. That turns ray tracing from a research exercise into an operational tool.

Why it's a moat: The OSM-to-mesh pipeline with proper facade decomposition, material classification, and RT-compatible export is not trivial. Google 3D Tiles ingestion with material inference from vertex colors is novel. Nobody else connects "type a city name" to "run a ray trace."

IDF gap: Not mentioned at all.

### 3. Interactive real-time viewer

A deployed web application (React + Three.js + Flask) where you click to place an antenna, and the dosimetry heatmap updates in real time on a 3D human body. MIMO multi-user mode with multiple phantoms. Compliance indicators. Power sweep and frequency sweep charts. Optimization controls. Coverage map with global base station overview.

Why this matters: This is the product surface. Every other dosimetry tool is either a CLI script, a MATLAB function, or an expensive desktop application (Sim4Life at ~60K/year). A web-based tool with no install, no license server, and sub-second feedback is a different category. It is also the demo that gets an istart pitch past the first slide.

Why it's a moat: 21K lines of TypeScript with tight backend integration. Camera modes, binary protocols for mesh transfer, Zustand state management, responsive layout, guided tour. This is not a weekend project. It is a production frontend.

IDF gap: Mentioned as "web-based 3D visualisation tool" in one sentence. Should describe the interactive compliance workflow.

### 4. Differentiable engine (JAX backend)

All kernels (levels 0-6) support JAX automatic differentiation. The spatial kernel, the Fresnel coefficients, the averaging matrices, and the optimization primitives all flow gradients. Three optimization algorithms use this: MIMO precoder optimization, antenna placement grid search, and tilt/power sweep.

Why this matters commercially: "Where should I put this antenna so nobody exceeds ICNIRP limits?" is the question telecom operators pay to answer. Today they do it by trial and error. With differentiable dosimetry, you solve it by gradient descent. This is the killer use case the IDF's "exposure-aware network design" vision describes but undersells.

Why it's a moat: Making a physics engine differentiable end-to-end requires careful attention to numerical stability, smooth activations (GELU instead of ReLU for diffraction), and sparse matrix handling. We did it. Competitors have FDTD, which is inherently non-differentiable. This cannot be retrofitted.

IDF gap: One bullet point under "Advantages." Should be a primary claim.

### 5. Coherent MIMO with exposure operator Q

The exposure operator Q is a Hermitian PSD matrix that captures how any precoding vector maps to absorbed power on the body. P_abs = x^H Q x. The ECBF solver finds the precoder that maximizes signal quality subject to an absorption constraint, analytically. Multi-user scenes with ZF, MMSE, and exposure-scaled precoders are operational.

Why this matters: 5G mMIMO beamforming is where compliance gets hard. You cannot simulate every possible beam. You need a mathematical object (Q) that summarizes the body's response to any beam, then optimize against it. Nobody else has Q in closed form. Hochwald/Ying's SAR matrix requires FDTD calibration per scenario. Ours is computed from geometry and Fresnel theory.

Why it's a moat: The theory is novel (IDF covers this well). But the implementation is also a moat: multi-user scene orchestration, factored Fresnel computation (16x speedup for 4x4 UPA), per-user compliance evaluation, precoder weight visualization.

IDF gap: Covered, but framed as math. Should also emphasize operational capability.

### 6. Stochastic channel modeling

Full 3GPP TR 38.901 cluster-based channel generator with 91 QuaDRiGa presets. Spatially consistent large-scale parameters with cross-correlated LSP maps. This feeds directly into the dosimetry engine. No other dosimetry tool has this.

Why this matters: In reality, you rarely know exact propagation paths. You know the environment type (urban macro, indoor office) and the statistics. The stochastic channel lets you compute expected exposure distributions without a ray tracer. It also enables Monte Carlo compliance: "what is the 95th percentile exposure in this scenario class?"

Why it's a moat: The QuaDRiGa parameter database alone is a significant asset. Connecting it to dosimetry is novel. Nobody has published "3GPP channel to body absorption" before.

IDF gap: Not mentioned.

### 7. GPU ray tracing as a service

Modal serverless deployment with DiffeRT on T4 (JAX/CUDA) and Sionna RT on L4 (OptiX). Scene caching, compression, automatic scaling. Two independent ray tracers for different use cases.

Why this matters: Scalable SaaS needs serverless compute. You cannot run ray tracing on the customer's laptop. Modal gives elastic GPU without managing infrastructure. The dual-backend means we are not locked into one RT vendor.

Why it's a moat: Integration effort. Both tracers have different APIs, coordinate systems, and output formats. The Modal deployment with scene caching and cold start handling is operational, not experimental.

IDF gap: Not mentioned.

---

## What the SaaS should be

The ROADMAP_12_months.md (written April 2, 2026) said: "The product is a research tool today. It needs to become a commercial product." It recommended: API layer, multi-site batch processing, report generation.

Those recommendations stand. But the feature inventory reveals that the platform is much closer to commercial than the roadmap assumed. Specifically:

The REST API already exists. 40+ endpoints. Authentication. Binary protocols. Streaming responses. It needs documentation, rate limiting, and API keys. It does not need to be built from scratch.

Multi-site is partially there. The base station pipeline loads thousands of sites. The batch runner exists. What is missing is parallel computation across sites with result aggregation.

The viewer IS the product for early customers. The roadmap said "customers don't buy viewers, they buy compliance reports." That was written before the viewer had MIMO, optimization, base station integration, and coverage maps. The viewer is now the fastest way to demonstrate value. Sell access to it. Report generation can come later.

### Recommended pivot

Instead of "compliance API for RF planning integration" (the ATDI/Forsk competitive play), start with:

"Interactive EMF compliance platform for telecom operators."

The demo: open the viewer, search for "Gent," see real Proximus/Orange/Telenet antennas, click one, see the dosimetry heatmap on a body, see ICNIRP compliance status. Then show MIMO mode, show the optimizer finding the best tilt. All in the browser, all real-time.

This is not a feature of someone else's tool. It is its own product. Nobody else can do this.

Pricing model: Per-seat SaaS subscription. Free tier with synthetic scenarios only. Paid tier with real base station data and GPU ray tracing. Enterprise tier with API access and batch processing.

---

## What is "first" that should go in the IDF

1. First closed-form spatial absorption map on arbitrary 3D human body geometry
2. First closed-form exposure operator Q for MIMO beamforming (no FDTD calibration)
3. First exposure-constrained beamformer with analytical solution (ECBF via QCQP)
4. First differentiable electromagnetic dosimetry engine (JAX, gradients through all kernels)
5. First interactive real-time dosimetry viewer with live ICNIRP compliance feedback
6. First platform combining real base station databases + ray tracing + body dosimetry
7. First stochastic-channel-aware dosimetry (3GPP 38.901 models feeding absorption computation)
8. First nine-level fidelity ladder from O(1) bounds to full coherent MIMO in one framework
9. First ambient-occlusion-based exposure fraction for self-shadowing on human bodies
10. First application of pseudo-Brewster compensation to biological tissue dosimetry

Items 1, 2, 3, and 10 are in the current IDF. Items 4-9 are not.

---

## IDF update recommendations

1. Shift the emphasis from T0 derivation to platform capabilities. The pseudo-Brewster insight is the theoretical foundation, but T0 alone is not a product. The platform that computes, visualizes, and optimizes based on T0 is the product.

2. Add the environment reconstruction, base station pipeline, and viewer as essential elements. These are not "further development." They exist and are deployed.

3. Expand the differentiability claim. The current IDF says "compatible with automatic differentiation." It should say: "The engine is differentiable end-to-end via JAX, enabling gradient-based antenna placement optimization, tilt/power optimization under ICNIRP constraints, and MIMO precoder design. Three optimization algorithms are implemented and operational."

4. Add the stochastic channel as a dependent claim. Claim: a method for computing statistical exposure distributions from 3GPP channel model parameters without deterministic ray tracing.

5. Update the development status. ~~The IDF says "v0.11.0."~~ (Corrected: the IDF already says v0.28.0.) The current version is v0.28+. The line count, test count, and feature set are significantly larger.

6. Add the "firsts" list. A dedicated section listing what AEGIS does that nobody has done before, with citations showing the gap.

7. De-emphasize the bounds (level 0-1). These are mathematically elegant but commercially marginal. The IDF spends significant space on Cauchy's formula and the Brewster compensation proof. These should be in the monograph, not leading the IDF. Lead with the spatial map (level 2+), MIMO (7-8), and optimization instead.

---

## Competitive landscape (for IDF section 8)

| Capability | Sim4Life (ZMT) | CST Studio (Dassault) | AEGIS |
|---|---|---|---|
| Method | FDTD | FEM/FDTD | Closed-form |
| Speed per scenario | Hours | Hours | Milliseconds |
| Real-time capable | No | No | Yes |
| Interactive viewer | Desktop only | Desktop only | Web browser |
| Real base station data | No | No | 14 government databases |
| 3D environment from OSM | No | No | Yes |
| MIMO exposure operator | No (re-run per precoder) | No | Closed-form Q |
| Differentiable | No | No | JAX end-to-end |
| 3GPP channel integration | No | No | 91 presets |
| GPU ray tracing | No | No | Modal T4/L4 |
| Optimization | Manual | Manual | 3 algorithms |
| Price | ~60K/year | ~50K/year | TBD (SaaS) |
| Install | Desktop + license server | Desktop + license server | Browser |

---

*Last updated: April 15, 2026*
