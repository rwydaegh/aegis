# Sionna RT integration

AEGIS supports two ray tracing backends. DiffeRT (JAX-based, differentiable) handles small scenes. Sionna RT (Mitsuba 3 / Dr.Jit, GPU-accelerated) handles city-scale scenes with hundreds of thousands of triangles.

Both backends produce the same `PropagationPaths` object. The dosimetry engine does not know which backend generated the paths.

## Requirements

Sionna RT requires Linux with a GPU. It does not work on Windows (DrJit LLVM JIT crash, upstream bug in DrJit 1.2.0).

```bash
pip install aegis[sionna]    # installs sionna-rt >= 1.0
```

The NVIDIA driver must be version 570 or newer. Versions 559-565 are blocked by DrJit due to OptiX miscompilation bugs.

## Usage

### Batch runner

```bash
python -m aegis.run --config my_run.yaml --backend sionna --scene-path scene.xml
```

Or in the YAML config:

```yaml
raytracer:
  backend: sionna
  scene_path: /path/to/sionna/scene.xml
  max_bounces: 3
```

### Python API

```python
import mitsuba as mi
mi.set_variant("cuda_ad_mono_polarized")  # GPU, or llvm_ad_mono_polarized for CPU

import sionna.rt
from aegis.integration.sionna import paths_from_sionna_scene

scene = sionna.rt.load_scene(sionna.rt.scene.munich)

paths = paths_from_sionna_scene(
    scene,
    tx_positions=np.array([[8.5, 21.0, 27.0]]),
    rx_position=np.array([45.0, 90.0, 1.5]),
    freq_hz=28e9,
    max_bounces=3,
    tx_power_dbm=30.0,
)

# Use with any fidelity level
from aegis import DosimetryEngine
from aegis.tissue.dielectric import SKIN_28GHZ

engine = DosimetryEngine(SKIN_28GHZ)
result = engine.compute(body, paths, level=2)
```

### Interactive viewer

The viewer shows a backend dropdown when both DiffeRT and Sionna RT are installed. Each Sionna XML scene appears twice in the dropdown, once per backend. Select "Scene (Sionna RT)" to use Sionna for that scene.

## How the conversion works

Sionna RT computes channel coefficients `a` that are scalar per (TX antenna, RX antenna, path). These are already projected onto receive antenna patterns. AEGIS needs the full 3D E-field vector $\boldsymbol{\psi}$ at the body surface, because each triangle has its own surface normal and Fresnel transmission.

The solution is a dual-polarized isotropic RX probe. Sionna's RX antenna is set to `polarization="cross"` with an isotropic gain pattern. This gives two channel coefficients per path: $a_\theta$ (captured by the theta-polarized element) and $a_\varphi$ (captured by the phi-polarized element).

The conversion to AEGIS's psi vector:

$$\boldsymbol{\psi} = \frac{\sqrt{8\pi Z_0 P_T}}{\lambda} \left( a_\theta \, \hat{e}_\theta + a_\varphi \, \hat{e}_\varphi \right)$$

where $Z_0 = 376.73\;\Omega$ is the vacuum impedance, $P_T$ is the transmit power in watts, and $\lambda = c/f$ is the wavelength.

The $4\pi/\lambda$ scaling factor corrects for the effective area built into Sionna's channel model. Sionna's `a` includes a $\lambda/(4\pi)$ factor from the Friis equation (antenna effective area). The monograph defines $\psi$ as the field at the surface without this factor. Dividing by $\lambda/(4\pi)$ removes it.

Verification: for a single LOS path at distance $d = 10$ m, frequency 28 GHz, TX power 1 W:

- Sionna gives $|a| = \lambda/(4\pi d) = 8.53 \times 10^{-5}$
- Scale factor: $\sqrt{8\pi Z_0}/\lambda = 9087$
- $|\psi| = 9087 \times 8.53 \times 10^{-5} = 0.775$ V/m
- $S_{\mathrm{inc}} = |\psi|^2/(2Z_0) = 7.96 \times 10^{-4}$ W/m$^2$ = $P/(4\pi d^2)$

All three columns agree to float64 precision.

## Mitsuba variant selection

Sionna RT requires a JIT variant of Mitsuba with polarization support. Set the variant before importing `sionna.rt`:

```python
import mitsuba as mi
mi.set_variant("cuda_ad_mono_polarized")   # GPU (OptiX)
# or
mi.set_variant("llvm_ad_mono_polarized")   # CPU (Embree)
```

Do not use `scalar_*` variants (Sionna needs JIT) or `*_rgb` variants (Jones matrix size mismatch with the rgb color representation).

## Platform notes

| Platform | Status | Notes |
|----------|--------|-------|
| Linux + NVIDIA GPU (driver >= 570) | Works | `cuda_ad_mono_polarized` variant, 21x faster than CPU |
| Linux CPU | Works | `llvm_ad_mono_polarized` variant, Embree BVH |
| Windows | Does not work | DrJit LLVM JIT symbol materialization failure |
| macOS | Untested | May work with LLVM variant |

The TensorDock cloud machine (`python tools/cloud.py up`) has an RTX A4000 with driver 570.211 and sionna-rt pre-installed.

## Comparison with DiffeRT

| | DiffeRT | Sionna RT |
|---|---------|-----------|
| Backend | JAX | Dr.Jit / Mitsuba 3 |
| Differentiable | Yes (end-to-end) | Forward only |
| Scene size | Small (O(N^K) path enumeration) | City-scale (BVH acceleration) |
| Polarization tracking | Manual TE/TM in AEGIS code | Built into Sionna |
| GPU | JAX GPU | OptiX (NVIDIA only) |
| Windows | Works | No |
| Install | `pip install aegis[rt]` | `pip install aegis[sionna]` |
