# AEGIS — Adaptive Electromagnetic Geometric Illumination & Safety

## An Open-Source Real-Time Dosimetry Engine for 5G/6G

> *"The framework transforms a 10¹²-cell volumetric simulation into O(M) surface operations: a reduction of six orders of magnitude that preserves the essential physics."*  
> — Geometric Dosimetry monograph

---

## 1. Executive Summary

**AEGIS** (Adaptive Electromagnetic Geometric Illumination & Safety) is an open-source, GPU-accelerated dosimetry engine that brings every mathematical result from the Geometric Dosimetry monograph into a single, unified software stack. The system computes absorbed power density on articulated human bodies moving through realistic wireless environments — in real time, with tunable fidelity, and with full differentiability for exposure-constrained network optimisation.

The core insight that makes this feasible is the monograph's own discovery: for biological tissue, dosimetry *is* geometry. The pseudo-Brewster compensation collapses the material factor to a scalar, the ReLU cosine gate makes absorption a piecewise-linear function of surface normals, and the entire chain — from ray-traced paths through Fresnel transmission to the exposure operator Q — is differentiable. AEGIS operationalises all of this.

### What it looks like in practice

A user sees a 3D scene: a city block, an office floor, a stadium. Articulated human avatars walk through the space. Base station antennas radiate. Coloured heat maps on each body show absorbed power density in real time. A sidebar displays whole-body SAR, peak spatially-averaged $S_{ab}$, and compliance status. The user drags an antenna, changes a precoder, switches a body pose — and the dosimetry updates live.

Under the hood, AEGIS is doing something remarkable: it runs the *full physics pipeline* of the monograph at interactive framerates. The exposed surface of a walking human is a moving mesh of ~10⁴ triangles. The Fresnel coefficients, the TE/TM decomposition, the occlusion rays, the depth-coupling integrals — all computed per frame on the GPU. When the user selects "coherent MIMO mode," the engine builds the exposure operator **Q**, computes its eigendecomposition, and solves the exposure-constrained beamforming QCQP in under 100 ms.

### Why it matters

1.  **Regulatory impact.** ICNIRP and IEEE compliance assessment today requires either FDTD simulation (days per scenario) or gross approximations (a sphere). AEGIS makes per-scenario compliance checking instantaneous.
2.  **Network design.** 5G/6G deployment planning can incorporate exposure constraints as first-class citizens in the optimisation loop, not as after-the-fact checks.
3.  **Research tool.** Every formula in the monograph becomes a callable function. Researchers can reproduce, extend, and challenge the theory with real data.
4.  **Demonstration.** The visual spectacle of watching a walking human avatar accumulate absorbed power in real time — with the mathematics visibly correct — is the most compelling argument for the monograph's results.

---

## 2. Scientific Foundation: What the Monograph Gives Us

The monograph develops three progressively richer frameworks. AEGIS implements all three as selectable "fidelity levels," plus the higher-order corrections. Every boxed equation becomes executable code.

### 2.1 Part I: The Geometric Absorption Law (Incoherent, Unpolarised)

| Concept | Equation | What AEGIS computes |
|---------|----------|---------------------|
| Exact absorption law | $S_{ab}(\mathbf{r}) = S_{inc} \cdot T_{eff}(\mathbf{r}) \cdot \text{ReLU}[\hat{n}(\mathbf{r}) \cdot (-\hat{k})]$ | Per-triangle $S_{ab}$ with full angle-dependent Fresnel |
| Geometric absorption law | $S_{ab}(\mathbf{r}) \approx S_{inc} \cdot T_0 \cdot \text{ReLU}[\hat{n}(\mathbf{r}) \cdot (-\hat{k})]$ | Per-triangle $S_{ab}$ with constant $T_0$ (fast path) |
| Projected area / Cauchy | $P_{abs}(\hat{k}) = S_{inc} \cdot T_0 \cdot A_\perp(\hat{k})$ | Total absorbed power via precomputed shadow-area LUT |
| Generalised Cauchy | $\langle P_{abs} \rangle = S_{inc} \cdot T_0 \cdot A_{ab}/4$ | Direction-averaged power via absorption area |
| Absorption directivity | $D(\hat{k}) = 4 A_\perp(\hat{k}) / A_{ab}$ | SH-compressed directional response ($L \leq 6$) |
| Exposure fraction (AO) | $\eta(\mathbf{r}) = \frac{1}{\pi}\int \text{ReLU}[\hat{n} \cdot (-\hat{k})] \cdot O(\mathbf{r}, \hat{k})\, d\Omega$ | GPU ambient-occlusion pass, identical to CG |
| Multi-source ReLU net | $S_{ab}(\mathbf{r}) = \mathbf{a}^\top \text{ReLU}(\mathbf{W}\hat{n}(\mathbf{r}))$ | Vectorised matrix-ReLU per frame |
| Curvature correction | $+\frac{H_j}{k} \text{ReLU}(\mu)^2$ per source | Optional ReLU² term using mean curvature |
| Diffraction smoothing | $\text{ReLU} \to \text{GELU}_{\sigma_j}$ | Physical GELU with $\sigma_j = \sqrt{\lambda/(2\pi R_j)}$ |

### 2.2 Part II: Generalisations (Polarisation, Sub-6 GHz)

| Concept | Equation | What AEGIS computes |
|---------|----------|---------------------|
| Absorption Stokes vector | $P_{abs} = \mathbf{m}(\hat{k}) \cdot \mathbf{s}_{inc}$ | 4-component dot product per path |
| TM excess $q$ | $q(\mathbf{r}) = -\cos(2\chi)\cos(2\alpha(\mathbf{r}) - 2\psi_0)$ | Per-triangle polarisation correction |
| Polarisation directivity $D_B$ | $D_B(\hat{k}) = |\tilde{B}(\hat{k})| / (2\tilde{A}_\perp(\hat{k}))$ | Precomputed Mollweide map |
| Exact averaged transmission | $\bar{T}(f) = 2\int_0^1 T_{avg}(\mu, f)\mu\, d\mu$ | Quadrature over Fresnel, per frequency |
| Multipath pol. convergence | $\sigma[\Delta P_{pol}]/P_{unpol} = D_B/\sqrt{2N}$ | Runtime diagnostic |

### 2.3 Part III: Coherent MIMO Illumination

| Concept | Equation | What AEGIS computes |
|---------|----------|---------------------|
| Field channel matrix | $\mathbf{E}(\mathbf{r}) = \mathbf{G}(\mathbf{r})\mathbf{x}$ | $3 \times M$ complex matrix at every body-surface point |
| Fresnel transmission operator | $\mathbf{F}_n(\mathbf{r}) = t_{s,n}\hat{e}_s\hat{e}_s^T + t_{p,n}\hat{e}_p\hat{e}_p^T$ | Rank-2 operator per path per triangle |
| Coherent absorption law | $S_{ab}(\mathbf{r}) = \|\tilde{\mathbf{G}}(\mathbf{r})\mathbf{x}\|^2$ | Squared-norm per triangle, GPU-parallel |
| Exposure operator | $\mathbf{Q} = \int_\Sigma \tilde{\mathbf{G}}^H \tilde{\mathbf{G}}\, dA$ | $M \times M$ Hermitian PSD matrix |
| Exposure-signal alignment | $\rho = \mathbf{h}^T\mathbf{Q}\mathbf{h}^* / (\|\mathbf{h}\|^2 \lambda_{max}(\mathbf{Q}))$ | Scalar diagnostic per user |
| Exposure-constrained BF | $\mathbf{x}^\star = \sqrt{P}(\lambda\mathbf{Q} + \nu\mathbf{I})^{-1}\mathbf{h}^* / \|\cdot\|$ | Closed-form QCQP solution |
| MU-MIMO exposure | $P_{abs}^{(u)} = \sum_k \mathbf{w}_k^H \mathbf{Q}^{(u)} \mathbf{w}_k$ | Per-person quadratic form |

### 2.4 Approximation Hierarchy

The monograph identifies a clean hierarchy of approximations. AEGIS exposes every level as a user-selectable option:

```
Level 0: Bound-only           O(1)      T₀ · Aab · Dmax / 4 · ΣSᵢ
Level 1: Aggregate (SH)       O(N)      T₀ · Aab/4 · Σ Sᵢ D(k̂ᵢ)
Level 2: Geometric ReLU map   O(MN)     T₀ · ReLU(N·Kᵀ) · s
Level 3: + Fresnel(θ)         O(MN)     Tavg(θ) · ReLU(μ) per path
Level 4: + Polarisation       O(MN)     + q·ΔT/2 correction
Level 5: + Curvature          O(MN)     + H/k · ReLU²
Level 6: + Diffraction        O(MN)     ReLU → GELU
Level 7: Coherent MIMO        O(M·N·M)  ||G̃(r)x||²
Level 8: + ECBF optimiser     O(M³)     Solve QCQP for x*
```

The user slides one slider and the engine transparently switches between these. At Level 2, the engine runs at thousands of FPS. At Level 7, it runs at 30+ FPS for $M=64$ antennas, $N=100$ paths, $M_{tri}=10^4$ triangles (≈ 4×10⁷ operations per frame — microseconds on a modern GPU, as the monograph itself notes).

---

## 3. Architecture

### 3.1 Design Principles

1.  **Physics-first.** Every computation maps to a boxed equation in the monograph. No ad-hoc heuristics.
2.  **GPU-native.** The bottleneck is the $M_{tri} \times N$ matrix-ReLU product. This is an embarrassingly parallel operation — ideal for GPU.
3.  **Differentiable.** The entire chain from scene parameters to $S_{ab}$ and $P_{abs}$ is differentiable. Gradients flow back through ReLU, Fresnel, and Sionna's ray tracer via standard backpropagation.
4.  **Tiered fidelity.** From $O(1)$ bounds to $O(M_{tri} \cdot M^2)$ coherent exposure, all from the same code path.
5.  **Sionna-native.** Sionna RT already provides differentiable GPU ray tracing. AEGIS plugs into its path output.

### 3.2 System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        AEGIS Engine                             │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────────┐  │
│  │ Scene Graph   │   │ Sionna RT    │   │ Body Module         │  │
│  │              │──▶│ (GPU ray     │   │ ┌─────────────────┐ │  │
│  │ • 3D env     │   │  tracing)    │   │ │ Mesh + Armature │ │  │
│  │ • Antennas   │   │              │   │ │ (GLTF/FBX)      │ │  │
│  │ • Materials  │   │ Output:      │   │ └────────┬────────┘ │  │
│  │ • Bodies     │   │ • N paths    │   │          │          │  │
│  └──────────────┘   │ • k̂ᵢ, Sᵢ   │   │ ┌────────▼────────┐ │  │
│                     │ • ψₙ, Tₙ    │   │ │ Precompute      │ │  │
│                     │ • phases     │   │ │ • Normals N     │ │  │
│                     └──────┬───────┘   │ │ • Areas a       │ │  │
│                            │           │ │ • η (AO)        │ │  │
│                            │           │ │ • D(k̂) SH      │ │  │
│                            │           │ │ • Aab           │ │  │
│                            │           │ │ • m(k̂) Stokes  │ │  │
│                            │           │ │ • Curvature H   │ │  │
│                            │           │ └────────┬────────┘ │  │
│                            │           └──────────┤          │  │
│                            │                      │          │  │
│                     ┌──────▼──────────────────────▼──────┐    │
│                     │     Dosimetry Kernel (GPU/CUDA)    │    │
│                     │                                    │    │
│                     │  Level select ◄── User slider      │    │
│                     │                                    │    │
│                     │  INCOHERENT PATH:                  │    │
│                     │   μ₊ = ReLU(N·Kᵀ)       [O(MN)]   │    │
│                     │   Sab = T₀·(μ₊⊙O)·s     [O(MN)]   │    │
│                     │                                    │    │
│                     │  COHERENT PATH:                    │    │
│                     │   F_n per path            [O(MN)]  │    │
│                     │   G̃(r) per triangle       [O(MN)]  │    │
│                     │   Sab = ||G̃·x||²          [O(M·M)] │    │
│                     │   Q = Σ G̃ᴴG̃ ΔA           [O(M²·M)]│    │
│                     │   x* = solve QCQP         [O(M³)] │    │
│                     │                                    │    │
│                     │  CORRECTIONS:                      │    │
│                     │   + Tavg(θ)  per path              │    │
│                     │   + q·ΔT/2   polarisation          │    │
│                     │   + H/k·ReLU² curvature            │    │
│                     │   + GELU      diffraction          │    │
│                     └────────────────┬───────────────────┘    │
│                                      │                        │
│                     ┌────────────────▼───────────────────┐    │
│                     │        Output / Viz Layer          │    │
│                     │  • Per-triangle Sab → colour map   │    │
│                     │  • Pabs, SARwb, compliance flag    │    │
│                     │  • Q eigenspectrum                 │    │
│                     │  • ρ alignment metric              │    │
│                     │  • Gradient tape for optimisation  │    │
│                     └───────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Ray tracer** | Sionna RT (TensorFlow/JAX) | Differentiable, GPU-native, outputs all needed path data ($\hat{k}_n$, $\psi_n$, $T_n$, delays). Already has 3D scene import. |
| **Dosimetry kernel** | Custom CUDA / JAX kernels | The core ReLU-matrix ops + Fresnel per-path are embarrassingly parallel. TensorFlow/JAX's `jit` + `vmap` handle the outer loops. The monograph's formulas are natively expressible as `jnp` operations. |
| **Body model** | SMPL/SMPL-X + custom armature | Industry-standard parametric body model. Articulated skeleton drives mesh deformation. Exports normals, areas, curvature per triangle. |
| **Visualisation** | Open3D / PyVista / custom WebGPU | Real-time 3D heatmap rendering on the body mesh. Alternatively: Blender Python API for offline high-quality renders. |
| **Optimisation** | JAX autodiff + CVXPY | Differentiable through entire chain for gradient-based design. CVXPY for the QCQP when needed. |
| **Language** | Python (API) + JAX/CUDA (compute) | Python for accessibility and Sionna compatibility. Critical kernels in JAX XLA or raw CUDA. No C++/Rust needed — JAX's JIT compilation handles performance. |

#### Why not C++ / Rust?

The monograph's computations are dense linear algebra (matrix-vector products, outer products, eigendecompositions). These are precisely what JAX/XLA compiles to optimal GPU code. Writing custom CUDA kernels might gain 2-3× over JAX for specific operations (fused ReLU-Fresnel-sum), but at the cost of:
- Breaking Sionna integration (Sionna is TensorFlow/JAX)
- Losing automatic differentiation
- Massively increasing maintenance burden

The bottleneck is never the dosimetry math — it's the ray tracing, and Sionna already handles that on GPU. AEGIS's contribution is the dosimetry *layer* on top of Sionna's path output.

#### Why not a game engine?

Game engines (Unreal, Unity) are tempting for visualisation but create massive integration headaches with Sionna and scientific Python. Instead:
- **For interactive use:** A lightweight Python 3D viewer (Open3D or PyVista with GPU support) renders the heatmapped body mesh. The scene geometry comes from Sionna's existing scene loader.
- **For publication-quality renders:** Blender Python API. Blender imports the mesh, AEGIS provides per-vertex $S_{ab}$ as vertex colours, and Blender renders with its Cycles path tracer.
- **For web demos:** A WebGPU/Three.js frontend can receive the dosimetry data via WebSocket and render it in a browser.

The key insight: the "game" is the *physics*, not the graphics. A walking avatar with a scientifically correct $S_{ab}$ heatmap is more impressive than a AAA-rendered avatar with fake dosimetry.

---

## 4. Feasibility: Why This Can Be Fast

### 4.1 The Numbers

The monograph itself does the performance analysis (§6.3, Table 5). Let's make it concrete:

**Incoherent spatial map (Level 2):**
- $M_{tri} = 10{,}000$ triangles (Thelonious-class)
- $N = 100$ paths (typical indoor)
- Core operation: $\mathbf{S}_{ab} = T_0 \cdot (\mu_+ \odot \mathbf{O}) \cdot \mathbf{s}$
- FLOPs: $10^4 \times 10^2 = 10^6$ multiply-adds
- GPU throughput (RTX 4090): ~80 TFLOPS (FP32)
- **Time: ~12 ns** (yes, nanoseconds). Limited by memory, not compute.
- Realistic estimate with memory: **~50 μs**

**Coherent spatial map (Level 7):**
- $M = 64$ antenna elements
- $M_{tri} = 10{,}000$ triangles
- $N = 100$ paths
- Building $\tilde{\mathbf{G}}(r)$: $O(M_{tri} \cdot N) = 10^6$ ops
- $S_{ab}(r) = \|\tilde{\mathbf{G}}(r)\mathbf{x}\|^2$: $O(M_{tri} \cdot M) = 6.4 \times 10^5$ ops
- Building $\mathbf{Q}$: $O(M_{tri} \cdot M^2) = 4 \times 10^7$ ops (dominant)
- QCQP solve: $O(M^3) = 2.6 \times 10^5$ ops
- Total: ~$4 \times 10^7$ ops
- **Time: ~500 μs on GPU** (0.5 ms, i.e., 2000 Hz)

**Ambient occlusion precompute:**
- This is the "expensive" step: $O(M_{tri} \cdot N_{dir} \cdot R)$ where $R$ is rays per direction.
- Standard GPU AO (e.g., OptiX BVH traversal): **~10 ms** for 10K triangles.
- Must recompute per pose. Cached for static poses.

**Body animation update:**
- SMPL forward kinematics + mesh deformation: **~2 ms** on GPU.
- Normal recomputation: **~0.1 ms**.

**Sionna RT ray tracing:**
- Typical: **10-100 ms per frame** for a complex scene.
- This is the *actual* bottleneck. The dosimetry layer adds negligible overhead.

**Total per-frame budget (incoherent):**
| Step | Time |
|------|------|
| Sionna RT (N=100 paths) | ~50 ms |
| Body mesh update | ~2 ms |
| AO update (if pose changed) | ~10 ms |
| Dosimetry kernel (Level 2) | ~0.05 ms |
| Render | ~5 ms |
| **Total** | **~67 ms (15 FPS)** |

**Total per-frame budget (coherent, M=64):**
| Step | Time |
|------|------|
| Sionna RT | ~50 ms |
| Body mesh update | ~2 ms |
| Dosimetry kernel (Level 7) | ~0.5 ms |
| QCQP solve | ~0.3 ms |
| Render | ~5 ms |
| **Total** | **~58 ms (17 FPS)** |

The dosimetry itself is *never* the bottleneck. The ray tracer is. As Sionna's performance improves (and it is improving rapidly with NVIDIA hardware RT acceleration), the whole pipeline gets faster. AEGIS is ready for real-time before the ray tracer is.

### 4.2 What Makes It Work

Three properties of the monograph's mathematics conspire to make GPU execution natural:

1. **Embarrassingly parallel per-triangle.** Every triangle's $S_{ab}$ depends on the same global path list but different local normals. This is a textbook `vmap` pattern.

2. **No inter-triangle coupling** (except for ICNIRP spatial averaging, which is a sparse-matrix multiply). The ReLU cosine, Fresnel coefficients, visibility check — all per-triangle.

3. **Small state per triangle.** Each triangle needs: normal (3 floats), area (1 float), curvature (1 float), $\eta$ (1 float). Total body state: $10^4 \times 6 \times 4 = 240$ KB. Fits in L1 cache.

---

## 5. The Walking Human: Avatar System

### 5.1 Body Representation

AEGIS uses a standard articulated mesh:
- **Mesh:** ~10,000 triangles, generated from SMPL or imported from Blender/MakeHuman.
- **Armature:** 24-joint skeleton (SMPL standard) or custom.
- **Animation:** Walk cycles, standing poses, reaching, crouching — loaded from BVH/FBX motion capture data.
- **Deformation:** Linear blend skinning (LBS) on GPU. Standard, fast, well-supported.

At each frame:
1. Advance the animation clock.
2. Forward-kinematics the skeleton.
3. LBS-deform the mesh vertices.
4. Recompute triangle normals and areas.
5. (Optional) Recompute curvature via discrete Laplacian.
6. (Optional) Recompute AO if the pose changed significantly.

Step 6 is the expensive one (~10 ms) but can be amortised: AO changes slowly with pose (the monograph's posture sensitivity study shows $D_{max}$ varies by only 6.5% across a *backflip*). A lazy-recompute strategy (update AO every 10 frames, or only when joint angles exceed a threshold) keeps the cost negligible.

### 5.2 Walking Animation and Real-Time Physics

The monograph already validated the framework against 51 frames of a backflip animation. The posture sensitivity is small. This means:
- A walking cycle can reuse a single AO map (or interpolate between 3-4 keyframe AO maps).
- The directivity $D(\hat{k})$ SH coefficients change by < 1% across the walk cycle. Precompute once, valid for the entire animation.
- Only the per-triangle normals change per frame, and the dosimetry kernel recomputes $S_{ab}$ from the new normals in microseconds.

The visual result: a human avatar walks through a city. The $S_{ab}$ heatmap on the body shifts and flows as the avatar turns, faces different base stations, passes behind buildings. The projected-area shadow visibly rotates. Concavities (armpits, between legs) show lower $\eta$ as blue regions. The whole scene is physically correct.

---

## 6. Feature Set

### 6.1 Core Engine

- **Multi-level dosimetry** (Levels 0–8 as described above)
- **Tissue database** (IT'IS v5.0 integration, Gabriel 4-Cole-Cole model, frequency-dependent $\tilde{n}(f)$, $T_0(f)$, $\bar{T}(f)$)
- **Multi-body support** (arbitrary number of avatars, each with separate $\mathbf{Q}^{(u)}$)
- **Animated bodies** (SMPL/custom, walk cycles, custom poses)
- **Compliance checking** (ICNIRP limits: $S_{ab}$ < 10 W/m², SAR_{wb} < 0.08 W/kg, with 4 cm² spatial averaging)
- **Sionna RT integration** (scene + path import, differentiable backprop)

### 6.2 Coherent MIMO Module

- **Exposure operator Q** computation and eigendecomposition
- **Exposure modes** visualisation (eigenvectors of Q as body heatmaps)
- **ρ alignment** dashboard
- **MRT vs. ECBF comparison** (side-by-side Sab maps)
- **MU-MIMO** support (K users, per-person Q, sum-rate vs. exposure Pareto front)
- **Coherent hotspot analysis** (hotspot size from Fourier uncertainty, $\sigma_q$, $\delta_{coh}$)

### 6.3 Visualisation

- **3D heatmap** on body mesh (colourmap: blue = low $S_{ab}$, through green/yellow, to red = high)
- **Compliance overlay** (triangles exceeding 10 W/m² flash red)
- **Mollweide directivity plot** ($D(\hat{k})$ from SH, live)
- **Eigenspectrum bar chart** (eigenvalues of Q, updated per frame)
- **ρ gauge** (alignment meter, 0 to 1)
- **Animation timeline** (scrub through walk cycle, see dosimetry evolve)
- **Split-screen comparison** (Level 2 vs Level 7, incoherent vs coherent)

### 6.4 Optimisation Tools

- **Antenna placement optimiser** (gradient-based, minimise worst-case $S_{ab}$ over user positions)
- **Beam pattern designer** (exposure-constrained beamforming in real time)
- **RIS phase optimiser** (differentiable through surface reflections)
- **Population statistics** (Monte Carlo sampler: random poses × positions × illumination → exposure CDFs)

---

## 7. Validation Strategy

The monograph provides its own validation targets:

| Test | Monograph result | AEGIS must reproduce |
|------|-----------------|----------------------|
| Fresnel table (Table 1) | $T_{avg}/T_0$ within 5.6% up to 75° | Exact match |
| Sphere ratio $R$ | 0.99 (unpolarised, 28 GHz) | Exact match |
| Thelonious phantom | Total power error 0.35%, local RMS 3.2% | Exact match |
| Mie theory curve | Error vs. size parameter at 28 GHz | Exact match to monograph's Fig. 7 |
| Polarisation (Mollweide) | $D_B^{max} = 16.0\%$ on Thelonious | Exact match |
| Multipath convergence | $\sigma/P = D_B/\sqrt{2N}$ scaling | Monte Carlo reproduction |
| SH compression | RMS error < 1% at $L=4$ for $D(\hat{k})$ | Exact match |
| Backflip posture | $D_{max}$ varies by 6.5% across 51 frames | Exact match |
| Approx 1 error | ≤ 4% on TM-TM cross-terms | Exact match |
| Approx 2 error | ≤ 0.44% on $\Gamma_{nn'}$ | Exact match |

Additionally:
- **Cross-validation with existing scripts.** The ~37 Python scripts already in the `scripts/` directory serve as ground truth.
- **Mie theory regression tests.** Automated CI that runs the Mie comparison at every commit.
- **FDTD spot-checks.** For a few canonical scenarios, compare against published FDTD results.

---

## 8. Project Structure

```
aegis/
├── README.md
├── LICENSE                    # MIT or Apache-2.0
├── pyproject.toml
├── docs/
│   ├── monograph_mapping.md   # Every equation → function mapping
│   ├── api_reference/
│   └── tutorials/
│       ├── 01_quickstart.py
│       ├── 02_incoherent.py
│       ├── 03_coherent_mimo.py
│       ├── 04_ecbf.py
│       └── 05_walking_avatar.py
├── aegis/
│   ├── __init__.py
│   ├── tissue/                # Tissue database
│   │   ├── itis.py            # IT'IS v5.0 loader
│   │   ├── cole_cole.py       # Gabriel 4-Cole-Cole model
│   │   └── fresnel.py         # T₀, T̄, Ts, Tp, ξ, all vectorised
│   ├── geometry/              # Body-geometry computations
│   │   ├── mesh.py            # Triangle mesh operations
│   │   ├── normals.py         # Normal computation, curvature
│   │   ├── projected_area.py  # A⊥(k̂) table, shadow casting
│   │   ├── ambient_occlusion.py  # η(r), GPU-accelerated AO
│   │   ├── directivity.py     # D(k̂), SH fitting, SH eval
│   │   └── cauchy.py          # Aab, generalised Cauchy
│   ├── incoherent/            # Part I + II
│   │   ├── geometric_law.py   # Sab = T₀ · ReLU(n̂·(-k̂))
│   │   ├── exact_law.py       # Sab with Teff(θ, pol)
│   │   ├── multi_source.py    # ReLU neural network form
│   │   ├── matrix_form.py     # S_ab = T₀ · (μ₊⊙O) · s
│   │   ├── corrections.py     # Curvature + GELU diffraction
│   │   └── stokes.py          # Absorption Stokes vector m(k̂)
│   ├── coherent/              # Part III
│   │   ├── field_channel.py   # G(r), g_j(r), ψ_n
│   │   ├── fresnel_operator.py  # F_n(r), Approx 1
│   │   ├── body_channel.py    # G̃(r), depth coupling, Approx 2
│   │   ├── absorption_law.py  # Sab = ||G̃(r)x||²
│   │   ├── exposure_op.py     # Q, eigendecomposition, ρ
│   │   ├── ecbf.py            # QCQP solver for x*
│   │   └── mu_mimo.py         # Multi-user extension
│   ├── compliance/            # Regulatory
│   │   ├── icnirp.py          # Limits, spatial averaging
│   │   ├── sar.py             # SAR_wb computation
│   │   └── anthropometric.py  # Du Bois scaling, body-size tables
│   ├── body/                  # Avatar system
│   │   ├── smpl.py            # SMPL model loader
│   │   ├── armature.py        # FK, LBS deformation
│   │   ├── animation.py       # Walk cycle, BVH import
│   │   └── precompute.py      # AO, SH, curvature per pose
│   ├── integration/           # External tools
│   │   ├── sionna.py          # Sionna RT path import
│   │   ├── blender.py         # Blender export (vertex colours)
│   │   └── open3d_viz.py      # Real-time 3D viewer
│   └── engine/                # Main loop
│       ├── scene.py           # Scene graph, entity management
│       ├── pipeline.py        # Per-frame update orchestration
│       ├── fidelity.py        # Level selector (0-8)
│       └── differentiable.py  # Gradient tape, loss functions
├── tests/
│   ├── test_fresnel.py
│   ├── test_cauchy.py
│   ├── test_mie.py
│   ├── test_stokes.py
│   ├── test_coherent.py
│   ├── test_ecbf.py
│   └── test_compliance.py
├── examples/
│   ├── single_plane_wave.py
│   ├── reverberation_chamber.py
│   ├── urban_canyon.py
│   ├── massive_mimo_exposure.py
│   └── walking_avatar_demo.py
└── assets/
    ├── meshes/                # Body meshes (Thelonious, SMPL)
    ├── animations/            # Walk cycles, poses
    └── scenes/                # Sionna scene files
```

---

## 9. Roadmap

### Phase 1: Foundations (Months 1–3)

**Goal:** Reproduce every table and figure in the monograph from a clean Python package.

- [ ] `aegis.tissue`: Cole-Cole model, Fresnel coefficients, $T_0(f)$, $\bar{T}(f)$
- [ ] `aegis.geometry`: Mesh loader (OBJ/PLY), normal computation, projected area
- [ ] `aegis.incoherent.geometric_law`: Single-source $S_{ab}$ on Thelonious
- [ ] Reproduce Tables 1–3, Figures 1–4 from the monograph
- [ ] Unit tests against existing scripts in `scripts/`
- [ ] CI: Mie theory regression at every commit

**Milestone:** `pip install aegis` produces correct $S_{ab}$ on a static body with a single plane wave.

### Phase 2: Full Incoherent Engine (Months 3–6)

**Goal:** Multi-source, polarisation-aware, all corrections, GPU-accelerated.

- [ ] `aegis.geometry.ambient_occlusion`: GPU AO (OptiX or custom BVH)
- [ ] `aegis.geometry.directivity`: SH fitting ($L \leq 6$), Cauchy formula
- [ ] `aegis.incoherent.multi_source`: ReLU neural network form, matrix formulation
- [ ] `aegis.incoherent.stokes`: Absorption Stokes vector, polarisation directivity
- [ ] `aegis.incoherent.corrections`: Curvature (ReLU²) + diffraction (GELU)
- [ ] `aegis.compliance`: ICNIRP 2020 limits, spatial averaging, SAR
- [ ] Sionna RT integration: import paths, run dosimetry on GPU
- [ ] Reproduce all Part I + II figures

**Milestone:** Full incoherent dosimetry at 60+ FPS on GPU. Publish as v0.1.

### Phase 3: Coherent MIMO (Months 6–9)

**Goal:** Part III fully operational.

- [ ] `aegis.coherent.field_channel`: $\mathbf{G}(\mathbf{r})$ assembly from Sionna paths
- [ ] `aegis.coherent.fresnel_operator`: $\mathbf{F}_n(\mathbf{r})$, Approximation 1
- [ ] `aegis.coherent.body_channel`: $\tilde{\mathbf{G}}(\mathbf{r})$, Approximation 2, depth coupling
- [ ] `aegis.coherent.absorption_law`: $S_{ab} = \|\tilde{\mathbf{G}}\mathbf{x}\|^2$
- [ ] `aegis.coherent.exposure_op`: **Q**, eigendecomposition, exposure modes
- [ ] `aegis.coherent.ecbf`: QCQP solver, $\mathbf{x}^\star$
- [ ] `aegis.coherent.mu_mimo`: Multi-user extension
- [ ] Validate against synthetic scenarios

**Milestone:** Exposure-constrained beamforming with live $S_{ab}$ map. Publish as v0.5.

### Phase 4: Walking Avatar & Visualisation (Months 9–12)

**Goal:** The "wow" demo.

- [ ] `aegis.body`: SMPL integration, FK, LBS, animation
- [ ] `aegis.integration.open3d_viz`: Real-time 3D heatmap viewer
- [ ] `aegis.integration.blender`: Export plugin for publication renders
- [ ] Walk cycle: human avatar walks through a Sionna scene, $S_{ab}$ updates per frame
- [ ] Dashboard: SAR, peak $S_{ab}$, ρ, Q eigenspectrum, compliance status
- [ ] Level slider: user switches fidelity in real time
- [ ] Side-by-side: incoherent vs. coherent, MRT vs. ECBF

**Milestone:** Demo video of a walking avatar in a 5G urban scene with live coherent dosimetry. Publish as v1.0.

### Phase 5: Optimisation & Research Tools (Months 12+)

- [ ] Differentiable pipeline end-to-end (scene → $S_{ab}$ → grad)
- [ ] Antenna placement optimiser
- [ ] Population Monte Carlo (random poses × positions → exposure statistics)
- [ ] RIS integration
- [ ] Web-based demo (WebGPU + FastAPI backend)
- [ ] Paper: "AEGIS: An Open-Source Engine for Real-Time Geometric Dosimetry"

---

## 10. What Makes This Project Unique

### 10.1 It's Not Just Another Dosimetry Tool

Existing tools:
- **Sim4Life / FDTD:** Accurate but slow (hours per scenario). Not differentiable. Not real-time.
- **Sionna:** Fast ray tracing, no dosimetry.
- **SEMCAD:** Commercial, closed-source, expensive.

AEGIS is the only system that:
1. Runs in real time
2. Is differentiable
3. Supports arbitrary body poses
4. Implements the full physics hierarchy from bounds to coherent MIMO
5. Is open source

### 10.2 It Showcases Every Result in the Monograph

The project is structured so that each monograph section maps to a module:

| Monograph Section | AEGIS Module |
|-------------------|--------------|
| §2 Local absorption law | `incoherent.exact_law` |
| §3 Pseudo-Brewster | `tissue.fresnel` |
| §4 Geometric framework | `geometry.*` |
| §5 Compliance | `compliance.*` |
| §6 Computational framework | `incoherent.multi_source`, `incoherent.matrix_form` |
| §7 Higher-order corrections | `incoherent.corrections` |
| §8 Validation (Mie) | `tests/test_mie.py` |
| §9 Applications | `examples/*` |
| §10 Polarisation | `incoherent.stokes` |
| §11 Sub-6 GHz | `tissue.fresnel` ($\bar{T}$ path) |
| §12 Limitations | (documented, not coded around) |
| §14–20 Coherent MIMO | `coherent.*` |

Every table in the monograph has a corresponding unit test. Every figure has a corresponding example script.

### 10.3 The Cross-Disciplinary Flex

The monograph's beauty is in the connections it reveals between fields. AEGIS makes these connections visible:

- **Dosimetry ↔ Computer Graphics:** The AO module is literally the same algorithm used in game engines. AEGIS can import AO bake results from Blender or compute them with the same OptiX BVH traversal that powers real-time global illumination.

- **Dosimetry ↔ Machine Learning:** The multi-source formula *is* a ReLU neural network. AEGIS evaluates it with the same `jax.nn.relu` that trains actual neural networks. The curvature correction is a ReLU² (a known activation function). The diffraction smoothing is a GELU (the same activation in GPT-series transformers).

- **Dosimetry ↔ Integral Geometry:** Cauchy's 1841 formula, stated in a 180-year-old paper about the expected width of a convex body's shadow, turns out to compute whole-body SAR. AEGIS's `cauchy.py` implements a result from pure mathematics.

- **Dosimetry ↔ Mueller Calculus:** The absorption Stokes vector connects dosimetry to classical polarisation optics. A body is an absorber on the Poincaré sphere.

- **Dosimetry ↔ Signal Processing:** The exposure operator Q has the same structure as a spatial covariance matrix. Its eigendecomposition reveals "exposure modes" that are the dosimetric analogue of MIMO spatial modes. ECBF is a regularised MRT — a standard concept in array processing.

---

## 11. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Sionna API changes | High | Medium | Pin Sionna version; abstract behind `integration.sionna` adapter |
| GPU memory for large meshes | Low | Medium | Streaming: process triangles in batches of 10K |
| AO recomputation too slow for fast animation | Medium | Low | Lazy update; pose-change threshold; interpolate AO keyframes |
| SMPL licensing | Medium | Medium | Support generic GLTF/FBX meshes as alternative; MakeHuman (open-source) |
| Accuracy of Approx 1+2 at low $|\tilde{n}|$ (high freq) | Low | Low | Always offer exact path as fallback (Level 3+) |
| Scope creep | High | High | Phase gates; v0.1 = incoherent only; v0.5 = + coherent; v1.0 = + avatar |

---

## 12. Impact and Audience

### Primary users
1. **EMF dosimetry researchers** — validate, reproduce, extend the monograph
2. **Telecom engineers** — exposure-aware 5G/6G design in Sionna
3. **Standards bodies** (ICNIRP, IEEE, IEC) — computational support for limit-setting
4. **Bioelectromagnetics labs** — reverberation chamber dosimetry interpretation

### Secondary users
5. **ML/optimisation researchers** — the ReLU/GELU correspondence is a curiosity; the differentiable pipeline is useful
6. **CG researchers** — ambient occlusion applied to a new domain
7. **Physics educators** — Fresnel, Brewster angle, Snell's law, Mie theory in one interactive demo

### Success metrics
- 100+ GitHub stars in Year 1
- Used in ≥3 published papers by external groups
- Integrated into ≥1 standards body's computational toolkit
- Demo video viewed 10,000+ times

---

## 13. Name and Branding

**AEGIS** — *Adaptive Electromagnetic Geometric Illumination & Safety*

The name connects to:
- The *aegis* of Greek mythology: a shield, here shielding people from harmful exposure
- The *adaptive* nature of the fidelity hierarchy
- The *geometric* core of the framework

Logo concept: a stylised human silhouette with a translucent shield-shaped halo, coloured as an $S_{ab}$ heatmap. The figure is composed of triangles, hinting at the mesh representation.

---

## 14. Conclusion

The Geometric Dosimetry monograph is a rare scientific document: it discovers that a hard computational problem (10¹² mesh cells for mmWave FDTD) has an elegant closed-form solution ($T_0 \cdot \text{ReLU}(\hat{n} \cdot (-\hat{k}))$), and that this solution connects four fields (EM dosimetry, Fresnel optics, integral geometry, and neural networks). The coherent extension in Part III shows that even beamforming — where fields add as amplitudes — collapses to a finite-dimensional matrix problem ($S_{ab} = \|\tilde{\mathbf{G}}\mathbf{x}\|^2$, $P_{abs} = \mathbf{x}^H\mathbf{Q}\mathbf{x}$) with a closed-form exposure-constrained optimum.

AEGIS turns this mathematical framework into software. Every boxed equation becomes a function. Every approximation becomes a slider. Every validation figure becomes a unit test. The walking human avatar — a mesh of 10,000 triangles, animated at 30 FPS, with physically correct absorbed power density updated in real time — is the visual proof that dosimetry really is geometry.

The project is ambitious but feasible because the mathematics itself is fast: the hardest computation (coherent MIMO with 64 antennas) takes 0.5 ms on a modern GPU. The bottleneck is the ray tracer, and Sionna is improving that independently. AEGIS is positioned to be ready for real-time the moment the ray tracer catches up.

The open-source release makes the monograph's results reproducible, extensible, and useful. It transforms a theoretical framework into a practical tool for the engineers, researchers, and regulators who need it.

---

*"I did not expect the geometry to have the structure it does."*  
*— Preface, Geometric Dosimetry monograph*

*AEGIS exists to show people that structure.*
