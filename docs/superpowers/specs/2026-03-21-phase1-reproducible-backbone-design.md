# Phase 1: Reproducible research backbone

*Design spec for ROADMAP.md Phase 1: dataclass configs, CLI batch runner, Sionna RT integration.*

## Context

Phases 0-4 are complete. The dosimetry engine works: 9 fidelity levels, 200+ tests, Mie-validated physics, Flask+Three.js viewer, DiffeRT ray tracing. Phase 1 of the new roadmap adds the infrastructure for reproducible paper results and large-scene ray tracing.

Three sub-phases, largely independent:
- **1a.** Dataclass config system (replaces the roadmap's Hydra proposal)
- **1b.** CLI batch runner (`python -m aegis.run`)
- **1c.** Sionna RT integration (`paths_from_sionna_scene()`)

## Decision: no Hydra

The roadmap proposed hydra-zen for config management. Hydra's value is sweeps (`--multirun`) and SLURM submission, which are Phase 4 concerns. For reproducibility, all that is needed is: dataclass configs, a CLI runner, and the resolved config saved alongside results. The dataclasses are future-proof for Hydra if needed later.

## 1a. Simulation config (dataclass hierarchy)

New file: `src/aegis/config.py`

Frozen dataclasses that fully describe a simulation run:

```python
@dataclass(frozen=True)
class TissueConfig:
    name: str = "skin"          # tissue name for database lookup
    frequency_hz: float = 28e9

@dataclass(frozen=True)
class BodyConfig:
    name: str = "thelonious"    # STL stem in data/
    mass_kg: float | None = None

@dataclass(frozen=True)
class AntennaConfig:
    positions: list[list[float]]  # (M_ant, 3) TX element positions [m]
    power_dbm: float = 30.0
    polarisation: str = "vertical"  # also used as tx_pattern for Sionna backend
    pattern: str = "isotropic"      # TX antenna pattern ("isotropic", "dipole", etc.)

@dataclass(frozen=True)
class RayTracerConfig:
    backend: str = "differt"    # "differt" or "sionna"
    max_bounces: int = 3
    scene_path: str | None = None  # Sionna XML scene path, or None for voxels

@dataclass(frozen=True)
class DosimetryConfig:
    level: int = 2              # fidelity level 0-8
    spatial_averaging: bool = False

@dataclass(frozen=True)
class SimulationConfig:
    tissue: TissueConfig
    body: BodyConfig
    antenna: AntennaConfig
    raytracer: RayTracerConfig
    dosimetry: DosimetryConfig
    output_dir: str = "outputs"
```

Serialization: `to_yaml()` / `from_yaml()` methods using PyYAML. Serialization uses `dataclasses.asdict()`. Deserialization uses a `_from_dict()` helper that reconstructs nested dataclasses from the YAML-loaded dict (no extra dependencies like dacite). Each run auto-saves the resolved config as `config.yaml` alongside results.

Validation: each sub-config uses `__post_init__` to enforce constraints (level in 0-8, backend in {"differt", "sionna"}, frequency_hz > 0, etc.). Frozen dataclasses allow `__post_init__` for validation but not mutation.

The viewer config system (`viewer/config.py`, `configs/`) is untouched. This config is for simulation runs only.

## 1b. CLI batch runner

New file: `src/aegis/run.py` (also registered as `aegis-run` console script in pyproject.toml).

### Flow

1. Parse CLI args or load YAML config file
2. Resolve `SimulationConfig` (CLI overrides > YAML > defaults)
3. Load body mesh via `BodyMesh.load()`
4. Load tissue via `TissueModel.from_database()`
5. Generate propagation paths:
   - `backend=differt`: call existing `paths_from_differt_scene()`
   - `backend=sionna`: call new `paths_from_sionna_scene()`
6. Run `DosimetryEngine.compute(body, paths, level)`
7. Save results to `outputs/{timestamp}/`:
   - `config.yaml` (resolved config)
   - `result.npz` (sab array, p_abs, sar_wb, metadata)
   - `summary.json` (peak sab, compliance, timing)

### CLI usage

```bash
# From YAML config
py -3.12 -m aegis.run --config runs/my_scenario.yaml

# Override fields
py -3.12 -m aegis.run --config runs/base.yaml --level 6 --power-dbm 23

# All from CLI (no YAML)
py -3.12 -m aegis.run --body duke --frequency 28e9 --level 2 \
    --antenna-pos "5,0,1" --backend differt
```

No Hydra, no sweeps. Argparse + dataclass + YAML.

## 1c. Sionna RT integration

New file: `src/aegis/integration/sionna.py`

### The physics problem

Sionna RT's path coefficient `a` is a scalar per (rx_ant, tx_ant, path), already projected onto receive antenna patterns:

```
a_n = (lambda / 4pi) * C_R^H * T_i * C_T
```

AEGIS needs `psi`: a 3D complex vector preserving the full E-field polarisation state at the body surface. The body IS the receiver. Each triangle has its own normal, its own Fresnel transmission.

### Solution: dual-polarized isotropic RX probe

Set Sionna's receive antenna to a dual-polarized isotropic pattern:
- pol 0 captures the theta-component of the arriving field
- pol 1 captures the phi-component

Then `a[rx=0, pol=0, ...]` = a_theta and `a[rx=0, pol=1, ...]` = a_phi.

### Unit conversion (critical)

Sionna's `a` is a dimensionless channel coefficient (voltage ratio). AEGIS's `psi` is the E-field vector in V/m (with TX power included, matching the existing DiffeRT integration convention).

The conversion bridges Sionna's "received power at an antenna" convention (which includes the antenna's effective area lambda^2/(4pi)) to AEGIS's "E-field illuminating the body surface" (area-independent).

**Derivation.** The monograph (Eq. 99) defines psi per-sqrt-W:

```
psi_n = sqrt(Z_0 / (2pi)) * (lambda / (4pi)) * [e_theta, e_phi] * T_n * C_T
```

where T_n is the monograph's transfer matrix. Sionna's transfer matrix T_i differs by a factor of (4pi/lambda): T_n_monograph = (4pi/lambda) * T_i_sionna. This is because the monograph's T_n absorbs the geometric spreading differently (for LOS: T_n = 4pi/(lambda*d), while Sionna's T_i = 1/d).

With dual-pol isotropic RX, Sionna gives a(2D) = (lambda/(4pi)) * T_i * C_T. Substituting T_i = (lambda/(4pi)) * T_n:

```
psi = sqrt(Z_0 / (2pi)) * (4pi / lambda) * [e_theta, e_phi] * a(2D)
```

Including TX power (to match differt.py convention where psi carries P_T):

```
psi = sqrt(P_T * Z_0 / (2pi)) * (4pi / lambda) * (a_theta * e_theta + a_phi * e_phi)
```

Or equivalently:

```
psi = sqrt(8pi * Z_0 * P_T) / lambda * (a_theta * e_theta + a_phi * e_phi)
```

**Numerical verification (LOS, isotropic TX, P_T=1W, d=10m, f=28GHz, lambda=0.01071m):**

| Quantity | Sionna | Conversion | DiffeRT (reference) |
|----------|--------|------------|---------------------|
| \|a\| | lambda/(4pi*d) = 8.53e-5 | -- | -- |
| scale factor | -- | sqrt(8pi*Z_0*1)/lambda = 9087 | -- |
| \|psi\| | -- | 9087 * 8.53e-5 = 0.775 | sqrt(2*Z_0/(4pi))/d = 0.775 |
| S_inc | -- | 0.775^2/(2*Z_0) = 7.96e-4 | P/(4pi*d^2) = 7.96e-4 |

All three columns agree to float64 precision.

### Conversion code

```python
lambda_ = C_0 / freq_hz
scale = np.sqrt(8 * np.pi * Z_0 * tx_power_w) / lambda_

# Spherical basis vectors at direction of arrival
e_theta, e_phi = spherical_basis(theta_r, phi_r)  # each (N, 3)

# 3D psi from Sionna's 2D channel coefficients
psi = scale * (a_theta[:, np.newaxis] * e_theta
             + a_phi[:, np.newaxis] * e_phi)
```

### Remaining PropagationPaths fields

From Sionna's Paths object:

| AEGIS field | Sionna source | Notes |
|-------------|---------------|-------|
| `k_hat` | `theta_r`, `phi_r` | Convert spherical to Cartesian unit vector |
| `psi` | `a[:, 0:2, ...]` | Dual-pol isotropic RX, scale as above |
| `element_index` | TX antenna dimension | `a[0, :, 0, tx_ant, path]` -> element = tx_ant |
| `delay` | `tau` | Directly from Sionna |
| `is_los` | `interactions` | Check if path has zero interactions |

### Function signature

```python
def paths_from_sionna_scene(
    scene,                        # sionna.rt Scene (loaded externally)
    tx_positions: np.ndarray,     # (M_ant, 3)
    rx_position: np.ndarray,      # (3,) body centroid (single point)
    freq_hz: float,
    max_bounces: int = 5,         # named max_bounces for consistency with DiffeRT
    tx_power_dbm: float = 30.0,
    tx_pattern: str = "isotropic",
) -> PropagationPaths:
```

Returns a standard PropagationPaths. The dosimetry engine does not know or care that paths came from Sionna. If Sionna finds zero valid paths, returns an empty PropagationPaths (matching the DiffeRT fallback at differt.py line 509).

The `rx_position` is a single body centroid. Sionna traces paths to this point. The spatial distribution across the body mesh is handled by the dosimetry kernel's cos(theta) projection, same as DiffeRT. No per-triangle ray tracing is needed.

Both AEGIS and Sionna use z-up right-handed coordinates. No coordinate transform is required.

### Configuring the dual-pol isotropic RX in Sionna

```python
from sionna.rt import PlanarArray

# Dual-polarized isotropic RX: captures both theta and phi field components
scene.rx_array = PlanarArray(
    num_rows=1, num_cols=1,
    pattern="iso",          # isotropic gain pattern
    polarization="cross",   # dual-pol: two orthogonal polarizations
)
```

With this config, `paths.a` has shape `(1, 2, num_tx, num_tx_ant, num_paths)` where dimension 1 indexes the two RX polarizations (theta, phi).

### Helper: `spherical_basis()`

New utility function (in `sionna.py` as private helper):

```python
def _spherical_basis(theta, phi):
    """Spherical basis vectors e_theta, e_phi at given angles."""
    ct, st = np.cos(theta), np.sin(theta)
    cp, sp = np.cos(phi), np.sin(phi)
    e_theta = np.column_stack([ct * cp, ct * sp, -st])
    e_phi = np.column_stack([-sp, cp, np.zeros_like(theta)])
    return e_theta, e_phi
```

### Scene loading

The CLI runner handles scene loading per backend:
- DiffeRT: `scene_path` is passed directly to `paths_from_differt_scene()`
- Sionna: `scene = sionna.rt.load_scene(scene_path)`, then the loaded scene object is passed to `paths_from_sionna_scene()`

This asymmetry (file path vs. loaded object) is intentional. Sionna scene setup (TX/RX arrays, materials) requires the scene object before path computation.

### What we trust Sionna for

We do NOT recompute Fresnel from path geometry (that is what the DiffeRT integration does). We trust Sionna's EM computation: reflections, diffractions, refractions, and scattering are all preserved in the `a` coefficients. We only convert the output format.

### Target version

Pin `sionna-rt>=1.0,<2.0` in pyproject.toml. The v1-to-v2 rewrite was breaking. Isolate all Sionna imports in `sionna.py` with a lazy import check (matching the DiffeRT pattern in `differt.py`).

## File layout

**New files:**
```
src/aegis/config.py              # SimulationConfig dataclass hierarchy
src/aegis/run.py                 # CLI batch runner
src/aegis/integration/sionna.py  # Sionna RT -> PropagationPaths
tests/test_config.py             # Config round-trip tests
tests/test_run.py                # CLI smoke tests
tests/test_sionna.py             # Sionna integration tests (slow, optional)
```

**Modified files:**
- `pyproject.toml` - add `aegis-run` console script, add `sionna` optional dep group, add `pyyaml` core dep
- `src/aegis/integration/__init__.py` - expose new module

**Untouched:**
- Viewer config system (`viewer/config.py`, `configs/`)
- Existing DiffeRT integration
- Existing kernels, engine, tissue, geometry
- Existing tests

## Dependencies

| Package | Type | Purpose |
|---------|------|---------|
| `pyyaml` | core | Config serialization |
| `sionna-rt` | optional (`[sionna]`) | Sionna ray tracer, pinned version |

## Testing strategy

1. **Config round-trip:** Create SimulationConfig, save to YAML, load back, assert equality.
2. **CLI smoke test:** Run `python -m aegis.run` with minimal config (synthetic paths), check output files exist.
3. **Sionna unit conversion (physics canary):** LOS at known distance. Verify `power = |psi|^2 / (2*Z_0) = P_T / (4*pi*d^2)` within float64 tolerance.
4. **Sionna-DiffeRT cross-validation:** Same simple geometry (one reflector), compare psi from both backends. Should agree within Fresnel coefficient differences (Sionna uses slab model, DiffeRT uses half-space).
5. **Integration test:** Full pipeline with Sionna backend, verify DosimetryResult fields are populated and sab >= 0.
6. **Sionna tests** marked `@pytest.mark.slow` and skipped if `sionna-rt` is not installed.

## Prerequisite fix: psi docstring in paths.py

The `PropagationPaths` docstring at `src/aegis/paths.py` line 25 says psi has units `V/m / sqrt(W)`. This is the monograph's per-sqrt(W) convention. The code actually stores the absolute E-field with P_T included (units: V/m). The `power` property confirms this: `S = |psi|^2 / (2*Z_0)` gives W/m^2 directly.

Fix the docstring to say `V/m` during implementation. The monograph's per-sqrt(W) convention is for the theoretical development. The code convention is different and valid, but documentation must match reality.

For coherent levels (7-8), the field channel `G(r) @ x` uses psi directly. If psi already includes P_T, the precoder x must account for this. This is an existing convention, not something introduced by this spec.

## Open questions resolved

- **Hydra:** Deferred. Dataclass configs are future-proof for it.
- **Which ray tracer:** Both. DiffeRT for small/differentiable, Sionna for large scenes.
- **psi convention:** Code stores absolute E-field (P_T included), matching existing DiffeRT integration.
