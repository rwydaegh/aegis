# Fidelity levels

For a step-by-step convergence analysis, see the [fidelity levels tutorial](../tutorials/fidelity_levels.md).

AEGIS uses a mode + corrections architecture for computing absorbed power density. You pick a computation mode, then toggle independent physics corrections on or off.

The integer `level=` API (0-8) still works and maps to specific mode + correction combinations. See the [quick reference](#quick-reference) below.

The cost column in the tables below ($O(1)$, $O(MN)$, etc.) describes theoretical scaling, not wall-clock time. All nine levels run in milliseconds on typical meshes. Choose based on which physics corrections matter for your scenario, not on computational budget.

## Computation modes

| Mode | Output | Cost | What it does |
|------|--------|------|-------------|
| `bound` | Scalar $P_{\mathrm{abs}}$ upper bound, uniform $S_{\mathrm{ab}}$ | O(1) | Worst-case bound using $A_{\mathrm{ab}}$ and $D_{\mathrm{max}}$. No spatial map. |
| `aggregate` | Scalar $P_{\mathrm{abs}}$ via directivity, uniform $S_{\mathrm{ab}}$ | O(N) | Direction-weighted total power using SH coefficients or a directivity LUT. |
| `spatial` | Per-triangle $S_{\mathrm{ab}}(\mathbf{r})$ map | O(MN) | Full spatial map. Default mode. Supports composable physics corrections. |
| `coherent` | Per-triangle $S_{\mathrm{ab}}$ from MIMO field superposition | O(MN + M $\cdot$ M_ant) | Builds the body-surface channel $\tilde{\mathbf{G}}(\mathbf{r})$ and computes $\|\tilde{\mathbf{G}} \mathbf{x}\|^2$. Requires a `Precoder`. |
| `ecbf` | Per-triangle $S_{\mathrm{ab}}$ with optimal precoder $\mathbf{x}^*$ | O(MN + M $\cdot$ M_ant$^2$ + M_ant$^3$) | Solves the QCQP for max signal subject to absorption and power constraints. Requires channel vector $\mathbf{h}$. |

Where M = number of body triangles, N = number of paths, M_ant = number of antenna elements.

### Bound

$$P_{\mathrm{abs}} \le T_0 \cdot \frac{A_{\mathrm{ab}} \cdot D_{\mathrm{max}}}{4} \cdot \sum_i S_i$$

Returns uniform $S_{\mathrm{ab}} = P_{\mathrm{abs}} / A_{\mathrm{total}}$. Requires precomputed absorption area $A_{\mathrm{ab}}$ and maximum directivity $D_{\mathrm{max}}$. Useful for quick compliance screening when you do not need a spatial map.

### Aggregate

$$P_{\mathrm{abs}} = T_0 \cdot \frac{A_{\mathrm{ab}}}{4} \cdot \sum_i S_i \cdot D(\hat{k}_i)$$

Returns uniform $S_{\mathrm{ab}}$. Uses spherical harmonic coefficients or a directivity look-up table to weight each path by its arrival direction. More accurate than the bound, but still no spatial resolution.

### Spatial

$$S_{\mathrm{ab}}(\mathbf{r}) = T(\mu) \cdot [\hat{n}(\mathbf{r}) \cdot (-\hat{k})]_+ \cdot \mathbf{s}$$

The core formula. Produces a per-triangle absorption map. Physics corrections (Fresnel, polarisation, curvature, diffraction) compose independently on top of this base computation. See [physics corrections](#physics-corrections) below.

### Coherent

$$S_{\mathrm{ab}}(\mathbf{r}) = \|\tilde{\mathbf{G}}(\mathbf{r}) \mathbf{x}\|^2$$

Builds the body-surface channel $\tilde{\mathbf{G}}(\mathbf{r})$ from Fresnel-filtered, depth-coupled path contributions, then computes the squared-norm field at each triangle. Also returns the exposure operator $\mathbf{Q}$, its eigendecomposition, and exposure-signal alignment $\rho$ (when $\mathbf{h}$ is provided).

Uses Approximation 1 (TM direction, error at most 4%) and Approximation 2 (depth coupling, error at most 0.44%).

### ECBF

Solves the exposure-constrained beamforming QCQP:

$$\max_{\mathbf{x}} |\mathbf{h}^H \mathbf{x}|^2 \quad \text{s.t.} \quad \mathbf{x}^H \mathbf{Q} \mathbf{x} \le P_{\mathrm{abs}}^{\mathrm{max}}, \quad \|\mathbf{x}\|^2 \le P$$

Finds the precoder $\mathbf{x}^*$ that maximizes signal power while keeping absorption below a specified limit. Returns the same outputs as coherent mode, plus the optimal precoder.

## Physics corrections

These corrections apply to `spatial` mode only. Each one is an independent boolean flag. You can combine them freely.

### Fresnel

Replaces the constant normal-incidence $T_0$ with angle-dependent $T_{\mathrm{avg}}(\theta)$. Accounts for the pseudo-Brewster compensation where TM transmission peaks near the Brewster angle. On by default (`fresnel=True`).

Error from using constant $T_0$ instead: about 5.6% for skin at 28 GHz (the exact figure depends on tissue and frequency). For most practical scenarios the Fresnel correction matters, so it stays on unless you explicitly disable it.

No additional data required beyond what the engine already has (tissue model).

### Polarisation

Splits $T_{\mathrm{avg}}$ into TE and TM components:

$$T = T_{\mathrm{avg}} + \frac{q}{2} \Delta T$$

where $q \in [-1, 1]$ is the TM excess per path. With $q = 0$ (unpolarized), this reduces to the base Fresnel result. Worst-case polarisation error is 16%, but in typical multipath environments it stays below 2.5%.

Requires per-path TM excess $q$ (scalar or array). Set `polarisation=True` and pass `q=...`.

### Curvature

Adds a first-order Physical Optics correction:

$$S_{\mathrm{ab}}^{\mathrm{curv}} = S_{\mathrm{ab}}^{\mathrm{base}} + T_0 \cdot \frac{H}{k} \cdot g(\mu)^2 \cdot \mathbf{s}$$

where $H$ is the twice-mean curvature per triangle and $k = 2\pi / \lambda$. With $H = 0$ (flat surface), the correction vanishes.

Requires per-triangle curvature data. Set `curvature=True` and pass `curvature_H=H`.

### Diffraction

Replaces the sharp ReLU at shadow boundaries with a GELU:

$$\text{GELU}(\mu, \sigma) = \mu \cdot \tfrac{1}{2}[1 + \text{erf}(\mu / \sigma)]$$

The transition width $\sigma_j = \sqrt{\lambda H_j / (4\pi)}$ depends on local curvature. With $H = 0$, the GELU reduces to ReLU and you recover the base result.

Requires per-triangle curvature data. Set `diffraction=True` and pass `curvature_H=H`. Automatically enables the curvature correction as well.

## Quick reference

Mapping from old integer levels to the mode API:

| Old level | Mode | Corrections | Notes |
|-----------|------|-------------|-------|
| 0 | `bound` | - | Requires $A_{\mathrm{ab}}$, $D_{\mathrm{max}}$ |
| 1 | `aggregate` | - | Requires $A_{\mathrm{ab}}$, directivity data |
| 2 | `spatial` | `fresnel=False` | Constant $T_0$ |
| 3 | `spatial` | (default: `fresnel=True`) | Angle-dependent $T_{\mathrm{avg}}$ |
| 4 | `spatial` | `polarisation=True` | Requires TM excess $q$ |
| 5 | `spatial` | `curvature=True` | Requires curvature $H$ |
| 6 | `spatial` | `curvature=True, diffraction=True` | Requires curvature $H$ |
| 7 | `coherent` | - | Requires `Precoder` |
| 8 | `ecbf` | - | Requires channel $\mathbf{h}$ |

## Code examples

### Mode API (recommended)

```python
from aegis import DosimetryEngine, TissueModel

tissue = TissueModel.from_database("Skin", 28e9)
engine = DosimetryEngine(tissue)

# Basic spatial map with Fresnel (default)
result = engine.compute(body, paths, mode="spatial")

# Add polarisation correction
result = engine.compute(body, paths, mode="spatial",
                        polarisation=True, q=0.3)

# Add curvature and diffraction
result = engine.compute(body, paths, mode="spatial",
                        curvature=True, diffraction=True,
                        curvature_H=H)

# Combine everything
result = engine.compute(body, paths, mode="spatial",
                        polarisation=True, q=q_per_path,
                        curvature=True, diffraction=True,
                        curvature_H=H)

# Coherent MIMO
precoder = aegis.Precoder.mrt(h, P=1.0)
result = engine.compute(body, paths, mode="coherent",
                        precoder=precoder, h=h)
result.Q             # exposure operator
result.eigenvalues   # Q eigenvalues (descending)
result.rho           # exposure-signal alignment

# ECBF
result = engine.compute(body, paths, mode="ecbf",
                        h=h, P_abs_max=0.1)
result.x_star        # optimal precoder
```

### Legacy level API

The integer `level=` parameter still works. It maps to the corresponding mode + corrections internally.

```python
# These two are equivalent
result = engine.compute(body, paths, level=3)
result = engine.compute(body, paths, mode="spatial")

# These two are equivalent
result = engine.compute(body, paths, level=4, q=0.3)
result = engine.compute(body, paths, mode="spatial",
                        polarisation=True, q=0.3)
```

!!! note
    When neither `mode` nor `level` is specified, AEGIS defaults to `level=2` (spatial with constant $T_0$, no Fresnel). To get angle-dependent Fresnel by default, use `mode="spatial"` explicitly.

## Choosing a mode

- For quick compliance screening: `bound` or `spatial` with `fresnel=False`
- For accurate incoherent dosimetry: `spatial` (Fresnel on by default)
- For polarisation-sensitive analysis: `spatial` with `polarisation=True`
- For MIMO beamforming analysis: `coherent`
- For exposure-constrained precoder design: `ecbf`
- For research and validation: compare multiple configurations on the same data
