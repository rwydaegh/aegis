# Agent reports — direction 5 planning session

Assembled 2026-04-23. Each section below is the verbatim final message returned by a subagent during the planning conversation for direction 5 / Route B PoC. No editing or synthesis. See `direction_5_ue_hardware_summary.md` for the synthesized finding and `direction_5_ue_hardware_queries.md` for the query set.

---

## Report 1 — Direction 5 Route B spec and surrounding JSAC folder landscape

**Agent:** Explore (Opus)
**Task:** Read `direction_5_math_opus_codex.tex` in full and report what Route B commits to; also survey `/home/user/aegis/JSAC/directions/` and `/home/user/aegis/JSAC/related_works/` for context on UE-side path estimation, DTN, closed-loop SAR/APD, precoding for exposure.

---

Perfect. Now let me report comprehensively on Route B with relevant quotes from the math document I read:

## Route B Specification (from direction_5_math_opus_codex.tex)

**Route B: Minimum Pilot Diversity for Direct ψₙ Recovery** (Sec. 3.2, lines 244–269)

### Scope & Assumptions
Route B is a **hardware-lite recovery path** that reconstructs the exposure operator **Q** using measurement-derived path data instead of ray tracing. It commits to these dependencies:

- **Dual-polarised UE receiver**: "Suppose the UE has a dual-polarised receive front end with two linearly independent patterns C_R^(1)(k̂), C_R^(2)(k̂) ∈ ℂ² (rank-2 port matrix)" (Prop. 5.1, line 248)
- **UE-side AoA estimation**: "per-path arrival direction k̂ₙ is known (e.g. from UE-side AoA estimation on a small array)" (line 250–251)
- **Per-port per-path amplitudes exported**: "protocol extension that exposes per-port per-path amplitudes to the BS" (line 269)
- **Body geometry still required**: "the body geometry is still required to integrate G^H G over Σ" (line 265)

### Success Criteria
**Identifiability achieved.** Proposition 5.1 (lines 246–262) proves that with k̂ₙ known, ψₙ lives in the 2-dimensional plane perpendicular to k̂ₙ in ℂ³. Two scalar port measurements form a 2×2 linear system guaranteed to have a unique solution:

> "the two scalar measurements form a 2×2 linear system in the (θ̂(k̂ₙ), φ̂(k̂ₙ)) basis; linear independence of C_R^(1), C_R^(2) guarantees invertibility." (lines 258–261)

Once ψₙ and k̂ₙ are both known, the path data **P** is fully specified, so Q = π_Q(P, Σ) can be computed analytically.

### Hardware/Protocol Cost
Minimal upgrade (already deployed at FR2):
- Dual-pol UE Rx receiver (standard at FR2)
- UE-side AoA capability (already used for spatial multiplexing)
- Protocol extension: expose per-port per-path channel amplitudes to BS (new)

### Critical Math Skeleton
Route B is a **measurement-based version of Route A**:
- Route A: ray tracer delivers path data → compute Q analytically
- Route B: measurement delivers path data → compute Q analytically

The two differ only in how **P** is obtained. Once obtained, both follow the same integration formula:
$$Q = \int_Σ \tilde{G}(r)^H \tilde{G}(r) \, dA$$

where $\tilde{G}_j(r) = \sum_{n:j(n)=j} F_n(r) ψ_n e^{-ik_0 \hat{k}_n \cdot r}$ (lines 122–124).

---

## Surrounding Landscape

### `/home/user/aegis/JSAC/directions/` Files (10 documents):

1. **direction_4_problem_codex_opus.tex** — APD/SAR constraint analysis; proves APD binds before whole-body SAR at mmWave
2. **direction_4_problem_opus.tex** — Variant; same APD/SAR framing
3. **direction_4_spatial_compliance.md** — Short markdown on spatial compliance constraints
4. **direction_4_report_codex.md** — Report summary of APD tight-binding on phantom bodies
5. **direction_5_Q_from_channel.md** — High-level overview; three routes (A/B/C) sketched informally
6. **direction_5_math_opus_codex.tex** — **This file** — Rigorous theorems; identifiability, perturbation bounds, refresh rules
7. **direction_5_Q_from_channel_report_codex.tex** — Report version; wraps theorems
8. **direction_5_Q_from_channel_math_codex.tex** — Math variant (parallel to opus codex)
9. **direction_5_math_opus.tex** — Earlier draft (check git history for relationship)
10. **direction_4_problem_codex.tex** — Earlier APD/SAR draft

### `/home/user/aegis/JSAC/related_works/` Scope (8 documents):

**Closed-Loop & Precoding:**
- `Closed-Loop_Precoding_and_Capacity_Analysis_for_Multiple-Antenna_Wireless_Systems_With_User_Radiation_Exposure_Constraints.pdf` — Ying, Love, Hochwald SAR precoding (referenced in direction_4 for phantom calibration)
- `Incorporating_specific_absorption_rate_constraints_into_wireless_signal_design.pdf` — SAR constraint integration in signal design

**Exposure & Signal Modeling:**
- `Signal-Level_Models_of_Pointwise_Electromagnetic_Exposure_for_Millimeter_Wave_Communication.pdf` — mmWave-specific exposure models
- `Determining_Electromagnetic_Exposure_Compliance_of_Multi-Antenna_Devices_in_Linear_Time.pdf` — Compliance checking (likely phantom-based)
- `Sum-Rate_Analysis_for_Multi-User_MIMO_Systems_With_User_Exposure_Constraints.pdf` — Multi-user extensions

**Archival:**
- `2601.19587v1.pdf`, `2601.19587_transcription.pdf`, `2601.19587_transcription.tex` — arXiv deposit (likely a key baseline paper)

### Topic Coverage in Directions

**UE-side path estimation:** Route B (direction_5_math_opus_codex.tex, Prop. 5.1) covers this directly — UE estimates k̂ₙ via "small array" AoA and transmits per-port amplitudes.

**DTN vs DT:** Not explicitly discussed. The document uses "scene model S" (ray-traced version, Route A) and "body-mounted pilot measurement" (Route B) but does not formalize a "Digital Twin Network" distinction.

**Closed-loop SAR/APD control:** Direction_4 quantifies when APD binds before whole-body SAR (APD-dominated regime). Direction_5 frames the ECBF precoder x* = √P (λQ + νI)^{-1} h* as the KKT solution to closed-form compliance (lines 138–142), but does not cover feedback control loops.

**Precoding for exposure:** Core theme across both directions. ECBF (Exposure-Constrained Beamformer) defined at lines 136–149; alignment metric ρ at lines 145–149. Two-timescale refresh architecture (Def. 5.2, Cor. 5.4) decouples h (refresh ~T_c) from Q (refresh ~T_p).

---

## Report 2 — AEGIS MIMO + coherent pipeline map

**Agent:** Explore (Opus)
**Task:** Map the MIMO/coherent pipeline deeply: PropagationPaths, kernels 7–8, Precoder, coherent/, engine dispatch, Sionna/DiffeRT bridges, and viewer backend — to identify where a UE-inferred-paths module plugs in.

---

## Report: AEGIS MIMO/Coherent Pipeline & UE-Inferred Paths PoC Design

### 1. **PropagationPaths Class Structure** (`/home/user/aegis/src/aegis/paths.py`)

```python
@dataclass(frozen=True)
class PropagationPaths:
    k_hat: np.ndarray = field(repr=False)           # (N, 3) unit directions
    psi: np.ndarray = field(repr=False)             # (N, 3) complex polarisation-amplitude vectors
    element_index: np.ndarray = field(repr=False)   # (N,) antenna element index
    delay: np.ndarray = field(repr=False)           # (N,) propagation delay [s]
    is_los: np.ndarray = field(repr=False)          # (N,) boolean LOS flag
```

**Key invariants enforced in `__post_init__`:**
- `k_hat` rows are unit vectors (norm=1.0, atol=1e-5)
- `element_index` are non-negative integers, `max(element_index) < n_elements`
- `psi` is complex, extracted via `power = |psi|^2 / (2*Z_0)` for incoherent levels
- All arrays must have matching first dimension (N paths)

**Key methods:**
- `from_powers(k_hat, power)`: Constructor for incoherent-only use; builds arbitrary perpendicular polarisation and assigns each path a virtual element
- `from_spherical(theta, phi, power)`: Construct from spherical angles (θ∈[0,π], φ∈[0,2π])
- `subset(indices)`, `los_paths`, `nlos_paths`: Filtering
- `n_elements` property: `max(element_index) + 1` if N>0 else 0
- `total_power` property: Sum of per-path incident power densities
- `concatenate()`: Join multiple path batches with optional element reindexing
- `to_dict() / from_dict()`: Serialization (psi stored as {real, imag})

**Critical for MIMO:** `psi` stores per-antenna complex phasors. Each path n originates from antenna element `element_index[n]`, and `psi[n]` is the (3,) complex field amplitude vector arriving at the body. This is the interface between ray tracing and coherent kernels.

---

### 2. **Coherent Pipeline (Levels 7-8)**

#### Level 7: Fixed precoder coherent MIMO
**File:** `/home/user/aegis/src/aegis/kernels/level7_coherent.py` (lines 26-96)

```python
def level7_coherent(
    normals, centroids, areas,
    k_hat, psi, element_index,  # paths
    x,                            # precoding vector (M_ant,)
    n_tilde, sigma, freq_hz, n_elements,
    h=None
) -> (sab, Q, eigenvalues, rho)
```

Flow:
1. **Body channel:** `G_tilde = compute_body_channel(...)` → (M_tri, 3, M_ant) complex matrix
   - Each triangle m has a (3, M_ant) matrix mapping precoder x to field at that point
   - Built by accumulating per-path Fresnel-filtered contributions (line 69-79)
2. **Absorption:** `sab = |G_tilde @ x|^2` (element-wise over M triangles)
3. **Exposure operator:** `Q = compute_exposure_operator(G_tilde, areas)` → (M_ant, M_ant)
   - `Q = Σ_m area_m * G_tilde_m^H @ G_tilde_m` (Hermitian PSD by construction)
   - Represents worst-case absorbed power: `P_abs_worst = x^H @ Q @ x`
4. **Eigendecompose Q:** Sort eigenvalues descending, clamp negatives to 0
5. **Alignment metric:** `rho = h^H @ Q @ h / (||h||^2 * λ_max)` if h provided
   - Ratio of MRT absorption to worst-case (monograph eq:rho-def, line 86-131 of exposure_operator.py)

#### Level 8: Exposure-constrained beamforming (ECBF)
**File:** `/home/user/aegis/src/aegis/kernels/level8_ecbf.py` (lines 26-100)

Solves QCQP:
```
max_x |h^H x|^2
s.t.  x^H Q x ≤ P_abs_max
      ||x||^2 ≤ P
```

**Optimal solution:** `x* = sqrt(P) * (λ*Q + ν*I)^{-1} h* / ||(λ*Q + ν*I)^{-1} h*||`
- λ, ν found via bisection on complementary slackness (ecbf.py lines 99-189)
- Power constraint always active at optimum (||x*||^2 = P unless underconstrained)
- Returns: `(sab, Q, eigenvalues, x_star, rho)`

**Key:** Level 8 requires UE channel vector `h ∈ C^{M_ant}`. This is the downlink channel estimate (from body to TX).

---

### 3. **Body Channel Construction** (`/home/user/aegis/src/aegis/coherent/body_channel.py:29-106`)

Per-triangle centroid, the channel is:

```python
G_tilde[m, :, j] = Σ_{n: element_index[n]=j}
    sqrt(σ/(4α_n)) * F_n[m] @ psi_n * exp(-i*k₀ * k_hat_n · r_m)
```

Where:
- **F_n[m]:** Fresnel operator (TE/TM decomposition + transmission coefficients)
- **psi_n:** Complex polarisation-amplitude vector from PropagationPaths (3,)
- **α_n:** Amplitude decay rate in tissue (Im part of k₀ * ξ, where ξ depends on angle)
- **Phase:** exp(-i*k₀ * k_hat · r) accounts for position-dependent phase
- **Accumulation:** Sum over all paths of element j, then expand to (M_ant,) precoder dimension

**Key insight for your PoC:** The `psi` vectors encode both magnitude and phase per-element. If you infer paths from UE measurements, you must populate `psi` with per-antenna complex field samples (not just power), **preserving relative phase between elements** for coherent beamforming to work.

---

### 4. **Precoder Dataclass** (`/home/user/aegis/src/aegis/precoder.py:15-87`)

```python
@dataclass(frozen=True)
class Precoder:
    x: np.ndarray  # (M_ant,) complex precoding vector, ||x||^2 = P_tx
```

**Constructors:**
- `mrt(h, P)`: Maximum ratio transmission = `sqrt(P) * h* / ||h||` (lines 39-57)
- `ecbf(h, Q, P_abs_max, P)`: Solves QCQP via `solve_ecbf()` (lines 59-83)

**Entry point to coherent kernel:** The precoder x is passed directly to level7/8. No UE model beyond the channel vector h.

---

### 5. **Engine Flow for MIMO** (`/home/user/aegis/src/aegis/engine.py:269-823`)

**High-level compute() dispatch:**

```python
if level >= 7:
    return self._compute_coherent(body, paths, level, precoder, h, P_abs_max, ...)
```

**_compute_coherent() (lines 724-823):**
1. Routes to `level7_coherent()` or `level8_ecbf()` based on level
2. Calls kernel with `paths.k_hat`, `paths.psi`, `paths.element_index`, `paths.n_elements`
3. Kernel returns `(sab, Q, eigenvalues, rho)` or `(sab, Q, eigenvalues, x_star, rho)`
4. Computes **coherent incident power density** via `coherent_sinc()` (lines 799-806):
   ```python
   sinc = coherent_sinc(centroids, k_hat, psi, element_index, x_for_sinc, freq_hz)
   ```
   This does: for each triangle, `sinc[m] = |Σ_n (phase[m,n] * psi[n] * x[element_index[n]])|^2 / (2*Z_0)`
5. Wraps in DosimetryResult with sab, Q, eigenvalues, x_star, and spatial averaging

**Critical:** `compute_sab()` (lines 433-583) is the JAX-compatible path for differentiable optimization.

---

### 6. **Sionna RT Integration** (`/home/user/aegis/src/aegis/integration/sionna.py:249-456`)

**paths_from_sionna_scene():** Runs Sionna PathSolver, converts CIR to PropagationPaths.

**Key for MIMO:**
- **synthetic_array=True (default):** All elements see the same arrival angles (θ_r, φ_r), but each element gets a per-antenna CIR coefficient `a[rx_idx, pol, tx_idx, elem, path]`
- **Per-element psi:** For each element, `psi[n] = scale * (a_θ[elem] * e_θ + a_φ[elem] * e_φ)` where e_θ, e_φ are spherical basis vectors (lines 74-105)
- **Element indexing:** Paths are tiled: if 4 paths and 4 elements → 16 total path rows, with `element_index = [0,0,0,0, 1,1,1,1, 2,2,2,2, 3,3,3,3]`
- **Differentiable path:** `differentiable=True` returns JAX arrays with gradient tracking via `paths.cir(out_type="jax")`, using masked zeros for invalid paths (static shapes, lines 164-246)

**Current limitation:** Sionna only populates `psi` per-antenna correctly; DiffeRT integration exists but is less optimized.

---

### 7. **DiffeRT Integration** (`/home/user/aegis/src/aegis/integration/differt.py:233-390`)

**paths_from_differt():** Manual path geometry + Fresnel tracking.

**Polarisation handling:**
- If `object_indices` and `material_n_tilde` provided: tracks TE/TM decomposition through reflections (`_track_polarisation()`, lines 157-230)
- Otherwise: arbitrary perpendicular (sufficient for incoherent, but **breaks coherent if used**—phase information lost)

**Current state:** DiffeRT + coherent MIMO is **not tested/validated**. Sionna is the only fully coherent-qualified ray tracer.

---

### 8. **Viewer Backend** (`/home/user/aegis/src/aegis/viewer/`)

**Compute endpoint:** `viewer/compute.py` wraps DosimetryEngine
- Accepts config with `level`, `precoder`, `h`, `P_abs_max`
- Returns DosimetryResult including `result.Q`, `result.eigenvalues`, `result.x_star`, `result.rho`

**Ray tracer:** `viewer/raytracer.py` bridges DiffeRT/Sionna
- `paths_from_sionna_scene()` called directly from router
- Paths cached in viewer session

**Visualization:** No existing "true vs estimated paths" endpoint. Paths are internal to compute; only sab/sar/sinc are exposed. **Opportunity: add `/api/paths/compare` route for your PoC.**

---

### 9. **What MIMO + RT Currently Can/Cannot Do**

**✓ WORKS:**
- **Sionna + Level 7:** Fixed precoder `x`, arbitrary MIMO array (1×N, M×N UPA), full coherent dosimetry
- **Sionna + Level 8:** ECBF optimization, UE channel h, arbitrary MIMO, exposure-constrained absorption map
- **DiffeRT + Level 7:** If polarisation is manually tracked (object_indices + materials provided)
- **Differentiable gradient:** `engine.compute_sab()` supports JAX with `differentiable=True` in Sionna

**✗ BROKEN/UNTESTED:**
- DiffeRT + Level 8 (ECBF): No test coverage; polarisation tracking may not be compatible with ECBF solver
- DiffeRT + coherent multi-element arrays: Per-antenna channel extraction not implemented (only scalar per-path)
- Synthetic path generation (from_powers, from_spherical) + Level 7/8: Works for unit-element case, but multi-element array expansion requires careful element_index management

---

### 10. **Where UE-Inferred Paths Module Plugs In**

**Architecture recommendation:**

```
aegis/inferred/
  ├── __init__.py
  ├── from_ue_measurements.py    # Main entry: UE pilot samples → PropagationPaths
  ├── channel_estimation.py       # LS, MMSE, subspace methods
  ├── path_clustering.py          # Detect distinct multipaths from temporal/spatial samples
  └── validation.py               # Compare inferred vs ground-truth (RT or LOS)
```

**Integration points:**

1. **Input:** Raw pilot measurements from UE (channel snapshots, SRS, CSI-RS feedback)
   - Dimension: (M_rx, K) multi-antenna RX, K time/frequency snapshots
   - Optionally: (M_rx, M_tx) full-duplex reciprocal downlink channel

2. **Estimation stage (channel_estimation.py):**
   - Convert raw CSI → (M_ant,) complex channel vector h
   - Extract principal eigenvector/subspace for multi-path detection

3. **Path inference (from_ue_measurements.py):**
   - **Angle extraction:** Use MUSIC, ESPRIT, or beamforming grid-search on h to estimate AoA θ, φ
   - **Amplitude inference:** Pilot power level or Fresnel-inverted amplitude
   - **Per-element psi:** Reconstruct from h and array geometry
     ```python
     psi[m] = h[m] * exp(-i*k₀ * pos[m] · k_hat)  # steering removed
     ```
   - **Delay:** From timing advance or estimated path length
   - **Validation:** Compare inferred k_hat against known antenna pointing; check |psi| against free-space path loss

4. **Output:** `PropagationPaths(k_hat, psi, element_index, delay, is_los)`
   - Use standard constructors where applicable (e.g., `from_spherical()` for single-path AoA)
   - For multi-path, populate N rows with per-element psi

5. **Hook into engine:**
   ```python
   paths_inferred = infer_from_ue_measurements(h_measured, array_pos, freq_hz)
   result_7 = engine.compute(body, paths_inferred, level=7, precoder=x)
   result_8 = engine.compute(body, paths_inferred, level=8, h=h_measured, P_abs_max=...)
   ```

6. **Viewer integration (optional MVP):**
   - Add Flask route `/api/infer-paths` accepting JSON with h and array geometry
   - Return PropagationPaths.to_dict()
   - Extend compute endpoint to accept `inferred_paths` param
   - Comparison visualization: overlay inferred vs RT paths on 3D scene

**Testing strategy:**
- Synthetic test: Generate paths with known `k_hat, psi` → compute DosimetryResult → infer back → compare
- Metamorphic: `result(inferred_paths_1) vs result(inferred_paths_2)` for same final k_hat but different intermediate estimates
- Oracle: Compare against Sionna RT on same scene (if RT data available)

---

### Summary: Key Code Paths & Entry Points

| Task | File | Lines | Key Function |
|------|------|-------|--------------|
| PropagationPaths spec | `paths.py` | 18–335 | Class definition, invariants |
| Level 7 coherent | `kernels/level7_coherent.py` | 26–96 | `level7_coherent()` |
| Level 8 ECBF | `kernels/level8_ecbf.py` | 26–100 | `level8_ecbf()` |
| Body channel (coherent) | `coherent/body_channel.py` | 29–106 | `compute_body_channel()` |
| Exposure operator | `coherent/exposure_operator.py` | 19–131 | `compute_exposure_operator()`, `compute_rho()` |
| ECBF solver | `coherent/ecbf.py` | 27–189 | `solve_ecbf()` |
| Sionna bridge | `integration/sionna.py` | 249–456 | `paths_from_sionna_scene()` |
| Engine dispatch | `engine.py` | 377–390, 724–823 | `_compute_coherent()` |
| Precoder | `precoder.py` | 39–83 | `Precoder.mrt()`, `.ecbf()` |

**Your PoC should populate the gap:** infer paths → construct PropagationPaths → call `engine.compute(body, paths, level=7/8, ...)`. Validate against RT or LOS ground truth.

---

## Report 3 — Sionna integration, canonical scene access, JSAC folder tour

**Agent:** Explore (Opus)
**Task:** (1) How is Sionna used in AEGIS — canonical scene access, GPU (Modal) routing, RT → PropagationPaths. (2) Full JSAC folder inventory and look for channel-estimation / AoA / OMP / SBL / MUSIC, plus FR1 vs FR2 / smartphone antenna assumptions.

---

## Summary Report

### 1. Sionna Integration in AEGIS

**Usage:** Sionna is deeply integrated for GPU-accelerated ray tracing. Key files:
- `/home/user/aegis/src/aegis/integration/sionna.py` — Core conversion module that transforms Sionna RT channel coefficients to AEGIS PropagationPaths objects
- `/home/user/aegis/src/aegis/modal_rt/sionna_tracer.py` — Modal L4 GPU wrapper for bundled and voxel scenes
- Tests in `/home/user/aegis/tests/test_sionna.py`

**Canonical Scenes:** The code loads scenes via `sionna.rt.load_scene(getattr(sionna.rt.scene, scene_name))`, accepting scene names as parameters. The `trace_bundled()` method shows scenes are loaded dynamically (cached in memory), but the codebase doesn't hardcode references to specific canonical scenes (street_canyon, munich, simple_street_canyon). These *could* be accessible if Sionna v1.0+ has them in its public registry, but they are not explicitly called out or documented in AEGIS.

**Ray Trace → PropagationPaths:** Yes, fully implemented. The `paths_from_sionna_scene()` function:
- Takes Sionna Scene, TX positions, RX position, frequency, max_bounces
- Configures dual-polarized isotropic RX (cross-pol to capture theta/phi components)
- Runs PathSolver to get channel coefficients a_theta, a_phi and angles theta_r, phi_r
- Converts coefficients to E-field psi vectors (V/m) using scale factor `sqrt(8*pi*Z_0*P_T) / lambda`
- Computes k_hat (direction of arrival), delay, and LOS tagging
- Returns PropagationPaths with full multipath structure

**GPU/Modal:** Yes, GPU on Modal L4. `SionnaTracer` is a Modal class (`@app.cls`) decorated with `gpu="L4"`. It caches scenes in container memory and uses Modal Volumes for persistent storage. Scene loading is cached; ray tracing happens on-GPU; results (paths dict + viz) are serialized back. Runs on default CPU locally but deploys to Modal L4 GPU at execution.

---

### 2. JSAC Folder Structure

**Top-level files:**
- `JSAC_SI_digital_twins.md` — Call-for-papers metadata; submission deadline 1 May 2026; scope is DT-driven wireless, closed-loop optimization, semantic awareness
- `answer.md` — The paper concept in five sections: SAR matrix definition, prior art review (Hochwald 2014 → Zhou 2026), CVaR-risk framework, sensor modeling (Dirichlet confusion matrix, ~30 lines numpy), and paper abstract pitching twin-in-loop ECBF with body-DT gesture inference
- `conversation.md` — Early brainstorm notes
- `old_idea_dont_Read.txt` — Archived material
- `thinking_no_ai.txt` — Handwritten scoping notes

**Subdirectories:**

- `directions/` — Five numbered research directions, each with PDFs and simulation code:
  - **Direction 4** (ICNIRP spatial compliance, worst-case 4 cm² hotspot): Defines `Q_local(r₀, A)` to enforce absorbed power density limits spatially. Key simulation code in `direction_4_sim_opus/hotspot_scaling.py` and `direction_4_sim_codex_opus/real_phantom_near_field_codex_opus.py`. These compute peak APD on 4 cm² patches as a function of N antennas, aperture, and target region (chest/head/shoulder/thigh). Both use AEGIS `compute_body_channel()` and `compute_exposure_operator()` on real phantoms (thelonious, 23k triangles). **No channel estimation code.**
  - **Direction 5** (Estimating Q from channel feedback): Documents the gap — `Q` cannot be algebraically inverted from channel `h` alone because the antenna pattern discards polarization. Sketches three routes: A (ray tracing, already in AEGIS; question: Q-staleness tolerance), B (body-mounted pilot tx), C (phantom calibration one-time). **No code; theoretical gap analysis only.**

- `related_works/` — PDFs of 8 exposure-constrained MIMO papers (Hochwald 2014, Ying 2015/2017, Castellanos 2020, Zhou 2026, etc.) and recent DT-networking papers. Also contains a transcribed arxiv paper on closed-loop precoding (2601.19587).

- `representative_papers/` — Curated bibliography of 10 DT and digital-twin-enabled optimization papers.

- `author_guidelines/` — IEEE JSAC submission templates and guidelines.

**Channel Estimation, AoA, MUSIC/OMP/SBL, UE-side Inversion:** None found. The paper concept (answer.md) is about SAR-constrained beamforming via CVaR-risk ECBF, not channel estimation. It assumes `h` is estimated via "standard uplink pilot sounding" (external; not implemented in AEGIS). Direction 5 explicitly states Q-recovery from h is impossible by algebraic means. No MUSIC, OMP, or SBL algorithms appear.

**FR1 vs FR2 / Sub-6 vs mmWave / Smartphone Antennas:** Simulations are hardcoded to **28 GHz** (mmWave, FR2). No sub-6 or FR1 variants. Direction 4 code sweeps N ∈ {1, 4, 16, 64} antennas and apertures {5–100 cm}, simulating phased-array-like configs on body phantoms — not explicit smartphone form factors. The paper sketch mentions "twin-in-the-loop mmWave" and "closed-loop UL-first (matching the deployed regime the iPhone-12/ANFR saga lives in)," but actual antenna specs (MIMO order on a smartphone) are not detailed in the code or direction files.

---

## Key Snippets

**Sionna conversion (polarisation + power):**
```python
psi = scale * (a_theta[:, None] * e_theta + a_phi[:, None] * e_phi)
# scale = sqrt(8*pi*Z_0*tx_power_w) / lambda
# Result: complex 3D polarisation-amplitude vectors in V/m
```

**Modal GPU dispatch:**
```python
@app.cls(image=sionna_image, gpu="L4", volumes={"/scenes": scene_volume})
class SionnaTracer:
    @modal.method()
    def trace_bundled(self, scene_name: str, ...):
        scene = sionna.rt.load_scene(getattr(sionna.rt.scene, scene_name))
```

**CVaR-ECBF formulation (paper concept):**
```
maximize log|I + (1/σ²)HFF^H H^H|  subject to  CVaR_α[tr(R(θ)FF^H)] ≤ Q_0
```
CVaR interpolates worst-case (Hochwald α→0) to expected-value (α→1); with posterior p_t over gesture states.

**Direction 4 metrics** (real_phantom_near_field):
- `peak_apd_w_m2`: worst 4 cm² patch across body
- `track = apd_at_target / peak_apd`: 1.0 if hotspot tracks MRT focus, <1 if geometric artifact
- Sweeps: 4 body regions × {5,10,30,100} cm distance × {1,4,16,64} antenna elements

---

**Bottom line:** Sionna is production-ready in AEGIS (GPU + differentiable JAX path). JSAC is a body-DT SAR-precoding paper (May 2026 deadline), focusing on CVaR-robust ECBF with pose inference and spatial ICNIRP compliance. Direction 5 is an open question (Q recovery from h). No channel-estimation or UE-side algorithms in flight; the UL CSI is assumed estimated externally (standard 3GPP practice).

---

## Report 4 — FR2 smartphone UE hardware research (executive summary returned by Tavily subagent)

**Agent:** general-purpose (Opus), using Tavily MCP
**Task:** Run the 8 queries from `direction_5_ue_hardware_queries.md` and write the consolidated summary at `direction_5_ue_hardware_summary.md`. Return an executive summary.

Note: the full synthesized summary lives in `direction_5_ue_hardware_summary.md` (45+ citations, UE-model table, caveats, Route B feasibility paragraph). This report below is only the agent's executive-summary return value. The verbatim per-query raw Tavily responses were NOT preserved in the main conversation — that would require re-running the queries with a raw-dump instruction.

---

## Executive summary (~300 words)

**The paper-breaking answer (Query 5): Route B's "per-element IQ + UE-side AoA" assumption does NOT survive contact with commercial FR2 hardware.** Qualcomm's own mmWave antenna module placement whitepaper is explicit: each smartphone module is a "5×1 dual-polarized linear antenna array" with a "size-9 analog beamforming codebook" — i.e., the per-element phase combining happens in the RFIC analog front-end, and only one post-combining IQ pair per polarization reaches the baseband. 3GPP TS 38.214 §5.2 confirms that CSI reporting at FR2 is codebook/beam-index based (Type I/II + L1-RSRP per CRI), never per-element h-vectors. No published reverse-engineering effort (QCSuper, BaseMirror on Exynos) has extracted per-element FR2 IQ from a commercial phone. Route B needs reframing as "L1-RSRP-per-beam + codebook inversion" at ~beam-width resolution.

**Recommended UE model** (full table in summary):

| Param | Value |
|---|---|
| Modules | 2 (shipping) / up to 4 (max per X50) |
| Active at once | 1 (module selection by SSB-RSRP; STxMP still "under study" in Rel-18) |
| Elements per module | 1×5 or 1×4 dual-pol (Qualcomm reference: 1×5) |
| Spacing | λ/2 ≈ 5.36 mm |
| Beamforming | Analog/hybrid in RFIC, not digital per-element |
| Exposable to app | PMI/RI/CQI/CRI/L1-RSRP; no per-element IQ |
| BW | 100 MHz typical, 400 MHz max per carrier, 120 kHz SCS |

**Three surprise findings that could change the paper's framing:**
1. **"3 panels at 120°" is folklore, not 3GPP.** TR 38.828 only documents a 2-panel 180° variant. Reviewers will flag this.
2. **iPhones do NOT use Qualcomm QTM modules** — Apple uses USI-packaged custom antennas with Qualcomm SMR526 IF IC. Papers citing "QTM525 in iPhone" are wrong.
3. **STxMP (simultaneous multi-panel) is still in Rel-18 WI in early 2026**, so coherent multi-module aggregation at the UE is a future feature, not current commercial.

**Deliverable**: `/home/user/aegis/JSAC/directions/direction_5_ue_hardware_summary.md` with 35 cited URLs, caveats section, explicit Route B feasibility paragraph, and three path-forward options (standards-compliant reformulation, operator-cooperative beam sweep, SDR replacement).
