# Fidelity levels

AEGIS provides nine fidelity levels (0-8) for computing absorbed power density. Each level adds a physical correction, trading accuracy for computational cost.

## Incoherent levels (0-6)

These levels use scalar power per path. They compute `S_ab = T(theta) * ReLU(n_hat . (-k_hat)) @ power` with increasing physical detail.

### Level 0: worst-case bound

$$P_{abs} \le T_0 \cdot \frac{A_{ab} \cdot D_{max}}{4} \cdot \sum_i S_i$$

Cost: O(1). Requires precomputed A_ab and D_max. Returns uniform S_ab = P_abs / A_total.

Use when: you need a quick upper bound without computing the spatial map.

### Level 1: aggregate via directivity

$$P_{abs} = T_0 \cdot \frac{A_{ab}}{4} \cdot \sum_i S_i \cdot D(\hat{k}_i)$$

Cost: O(N). Uses SH coefficients or a directivity LUT. Returns uniform S_ab.

Use when: you have precomputed directivity and need per-direction power without the spatial map.

### Level 2: geometric ReLU map (default)

$$S_{ab}(\mathbf{r}) = T_0 \cdot \text{ReLU}[\hat{n}(\mathbf{r}) \cdot (-\hat{k})]^T \mathbf{s}$$

Cost: O(MN). The core formula. Uses constant T_0 for all angles.

Use when: you need the spatial map and can tolerate ~0.35% total power error.

### Level 3: exact Fresnel

$$S_{ab}(\mathbf{r}) = T_{avg}(\mu) \cdot \text{ReLU}(\mu) @ \mathbf{s}$$

Cost: O(MN). Replaces constant T_0 with angle-dependent T_avg(theta). Matches Level 2 at normal incidence.

Use when: you need accurate angular dependence of absorption.

### Level 4: polarisation correction

$$S_{ab} = [T_{avg} + \frac{q}{2} \Delta T] \cdot \text{ReLU}(\mu) @ \mathbf{s}$$

Cost: O(MN). Adds TM excess q per path. With q=0 (unpolarised), equals Level 3 exactly.

Use when: you know the polarisation state of each path and it matters (TM-dominant scenarios).

### Level 5: curvature correction

$$S_{ab} = S_{ab}^{(3)} + T_0 \cdot \frac{H}{k} \cdot \text{ReLU}(\mu)^2 @ \mathbf{s}$$

Cost: O(MN). Adds physical optics curvature correction using twice mean curvature H per triangle. With H=0, equals Level 3.

Use when: the body has regions of high curvature (nose, chin, fingers) and you need the correction.

### Level 6: diffraction smoothing

Same as Level 5 but replaces ReLU with a physical GELU at shadow boundaries. The GELU width sigma_j depends on the local radius of curvature.

Cost: O(MN). Provides smooth transition at shadow boundaries instead of the sharp ReLU cutoff.

Use when: you need physically accurate shadow-boundary diffraction effects.

## Coherent levels (7-8)

These levels use the full complex polarisation-amplitude vectors psi and antenna element structure. They require a `Precoder` object.

### Level 7: coherent MIMO map

$$S_{ab}(\mathbf{r}) = \|\tilde{\mathbf{G}}(\mathbf{r}) \mathbf{x}\|^2$$

Cost: O(M_tri * N + M_tri * M_ant). Builds the body-surface channel G_tilde(r) from Fresnel-filtered, depth-coupled path contributions, then computes the squared-norm field at each triangle.

Also computes the exposure operator Q, its eigendecomposition, and the exposure-signal alignment rho (if h is provided).

Uses Approximation 1 (TM direction, error <= 4%) and Approximation 2 (depth coupling, error <= 0.44%).

```python
precoder = aegis.Precoder.mrt(h, P=1.0)
result = engine.compute(body, paths, level=7, precoder=precoder, h=h)
result.sab           # per-triangle S_ab
result.Q             # exposure operator
result.eigenvalues   # Q eigenvalues (descending)
result.rho           # exposure-signal alignment
```

Use when: you have coherent MIMO paths and want to see the absorption pattern for a specific precoder.

### Level 8: exposure-constrained beamforming

Solves the QCQP:

$$\max_{\mathbf{x}} |\mathbf{h}^T \mathbf{x}|^2 \quad \text{s.t.} \quad \mathbf{x}^H \mathbf{Q} \mathbf{x} \le P_{abs}^{max}, \quad \|\mathbf{x}\|^2 \le P$$

Cost: O(M_tri * N + M_tri * M_ant^2 + M_ant^3). Computes Q, solves for the optimal precoder x* via bisection in the Q eigenbasis, then computes S_ab with x*.

```python
result = engine.compute(body, paths, level=8, h=h, P_abs_max=0.1)
result.sab           # S_ab with optimal precoder
result.p_abs         # <= P_abs_max
result.rho           # how aligned signal and exposure are
```

Use when: you want to find the precoder that maximises signal while keeping absorption below a limit.

## Level comparison summary

| Level | Cost | Key addition | Error vs full Fresnel |
|-------|------|--------------|-----------------------|
| 0 | O(1) | Upper bound only | Conservative bound |
| 1 | O(N) | Directivity weighting | Direction-averaged |
| 2 | O(MN) | Spatial map, constant T_0 | ~0.35% total power |
| 3 | O(MN) | Angle-dependent T_avg | Reference |
| 4 | O(MN) | Polarisation q | Level 3 + pol. correction |
| 5 | O(MN) | Curvature H/k | Level 3 + PO correction |
| 6 | O(MN) | GELU diffraction | Level 3 + shadow smoothing |
| 7 | O(MN_ant) | Coherent phases | Approx 1+2: ~5% combined |
| 8 | O(M_ant^3) | ECBF solver | Same as Level 7 |

## Choosing a level

- For quick compliance checks: Level 0 or Level 2
- For accurate incoherent dosimetry: Level 3
- For MIMO beamforming analysis: Level 7
- For exposure-constrained precoder design: Level 8
- For research/validation: compare multiple levels on the same data
