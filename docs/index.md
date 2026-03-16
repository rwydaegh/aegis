# AEGIS

**Adaptive Electromagnetic Geometric Illumination & Safety**

AEGIS computes absorbed power density on human bodies in wireless environments. It replaces volumetric EM simulation (10^12 cells) with O(M*N) surface operations by exploiting the geometric nature of dosimetry.

The core equation:

$$S_{ab}(\mathbf{r}) = S_{inc} \cdot \mathcal{T}_0 \cdot [\hat{n}(\mathbf{r}) \cdot (-\hat{k})]_+$$

## Quick start

```python
from aegis import DosimetryEngine, BodyMesh, TissueModel, PropagationPaths

skin = TissueModel.from_database("Skin")
body = BodyMesh.load("thelonious.stl")
paths = PropagationPaths.from_powers(k_hat=[[0, 0, -1]], power=[1.0])

engine = DosimetryEngine(skin, frequency=28e9)
result = engine.compute(body, paths, level=2)

result.plot()
```

## Fidelity levels

| Level | Name | What it adds | Complexity |
|-------|------|-------------|------------|
| 0 | Bound | Worst-case P_abs | O(1) |
| 1 | Aggregate | SH-compressed directivity | O(L^2) |
| 2 | Geometric | ReLU kernel on mesh | O(M*N) |
| 3 | Fresnel | Exact angle-dependent T(mu) | O(M*N) |
| 4 | Polarisation | TE/TM decomposition | O(M*N) |
| 5 | Curvature | Local curvature correction | O(M*N) |
| 6 | Diffraction | GELU shadow smoothing | O(M*N) |
| 7 | Coherent | Complex field summation | O(M*N*K) |
| 8 | ECBF | Exposure-constrained beamforming | O(K^3) |
