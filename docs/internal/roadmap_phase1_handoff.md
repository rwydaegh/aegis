# Roadmap Phase 1 hand-off: reproducible research backbone

Phase 1 of the revised roadmap (ROADMAP.md) added the infrastructure for reproducible batch simulations and a second ray tracing backend (Sionna RT). The viewer gained a backend dropdown so users can choose DiffeRT or Sionna RT per scene.

## What was built

### Source modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `config.py` | 130 | Frozen dataclass hierarchy: TissueConfig, BodyConfig, AntennaConfig, RayTracerConfig, DosimetryConfig, SimulationConfig. YAML round-trip via `to_yaml()` / `from_yaml()`. Validation in `__post_init__`. |
| `run.py` | 220 | CLI batch runner. Loads config, body, tissue, paths. Runs dosimetry. Saves resolved config + result.npz + summary.json to timestamped output dir. |
| `integration/sionna.py` | 220 | Sionna RT v2 to PropagationPaths. Dual-pol isotropic RX probe captures full E-field. Scales to V/m via `psi = sqrt(8*pi*Z_0*P_T)/lambda * (a_theta*e_theta + a_phi*e_phi)`. |
| `viewer/routes/compute.py` (extended) | +80 | `/api/compute/sionna-rt` endpoint. |
| `viewer/routes/data.py` (extended) | +10 | `has_sionna` detection via `importlib.util.find_spec`. |
| `viewer/templates/index.html` (extended) | +50 | Backend dropdown: scenes listed as "Scene (DiffeRT)" and "Scene (Sionna RT)". Routes to separate endpoints. |

### Configuration

| File | Purpose |
|------|---------|
| `configs/batch_example.yaml` | Ready-to-use example for the CLI runner |
| `pyproject.toml` | `aegis-run` console script, `pyyaml` core dep, `[sionna]` optional dep group |

### Tests

| File | Tests | What it validates |
|------|-------|-------------------|
| `test_config.py` | 8 | YAML round-trip, defaults, validation, from_dict, CLI override merging |
| `test_run.py` | 4 | CLI smoke test (synthetic backend), output file structure, summary.json content |
| `test_sionna.py` | 3 | Unit conversion (LOS physics canary), empty paths, spherical basis vectors. Marked `@pytest.mark.slow`, skipped if sionna-rt not installed. |

242 fast tests total (all passing). Lint clean.

### Documentation

| File | Content |
|------|---------|
| `docs/user_guide/batch_runner.md` | Full user guide: YAML format, CLI overrides, backends, output structure |
| `docs/user_guide/sionna_integration.md` | Physics of the conversion, platform requirements, usage |
| `ROADMAP.md` | Updated: Phase 1 marked done, Hydra deferred, sequencing revised |

## Key decisions

### No Hydra (deferred to Phase 4)

The roadmap proposed hydra-zen for config management. Hydra's main value is sweeps (`--multirun`) and SLURM job submission, which are Phase 4 concerns. For reproducibility, frozen dataclass configs with YAML serialization are sufficient. The dataclasses are shaped correctly for hydra-zen if needed later.

### Psi unit convention

The monograph defines psi in V/m/sqrt(W). Both integrations bake sqrt(P_T) into psi so that the `power` property `|psi|^2 / (2*Z_0)` returns absolute W/m^2 directly. The Sionna conversion formula:

$$\boldsymbol{\psi} = \frac{\sqrt{8\pi Z_0 P_T}}{\lambda} \left( a_\theta \hat{e}_\theta + a_\varphi \hat{e}_\varphi \right)$$

The $4\pi/\lambda$ factor bridges Sionna's effective-area convention (channel coefficient includes $\lambda/(4\pi)$ from Friis) to the field-at-surface convention. Verified numerically: LOS at 10m, 28 GHz, 1W gives $S_\text{inc} = 7.96 \times 10^{-4}$ W/m$^2$ = $P/(4\pi d^2)$.

### Dual-pol isotropic RX probe

Sionna's `a` coefficient is projected onto receive antenna patterns. The body is the receiver in AEGIS, so we need the unprojected E-field. Setting Sionna's RX to a dual-pol isotropic antenna (`polarization="cross"`) captures the theta and phi components separately, allowing reconstruction of the full 3D psi vector.

### Viewer backend separation

The viewer and batch runner have separate config systems by design. The viewer uses JSON/argparse for real-time interaction. The batch runner uses SimulationConfig YAML for reproducible research. They share the same dosimetry engine, tissue database, and body meshes.

## Sionna RT v2 gotchas

These were discovered during integration with sionna-rt 2.0.0:

1. **TX/RX API changed.** Use `scene.add(Transmitter("tx", position=[...]))`, not `scene.add_transmitter()`.

2. **CIR shape changed.** v2 returns `a` with shape `(num_rx, num_rx_ant, num_tx, num_tx_ant, num_paths, num_time_steps)`. With cross-pol RX, `num_rx_ant=2` (index 0=theta, 1=phi). Drop the time_steps dim with `a[..., 0]`.

3. **Antenna pattern names.** v2 uses `"iso"` not `"isotropic"`. The integration maps common names: `{"isotropic": "iso", "half_wave_dipole": "hw_dipole"}`.

4. **Mitsuba variant.** Must use a polarized JIT variant. `llvm_ad_rgb` crashes on scene loading (Jones matrix size mismatch with Color3f). Use `cuda_ad_mono_polarized` (GPU) or `llvm_ad_mono_polarized` (CPU).

5. **Windows.** DrJit 1.2.0 LLVM JIT crashes on Windows when loading scenes (symbol materialization failure). Sionna RT is Linux/cloud only.

6. **GPU driver.** DrJit blocks OptiX on NVIDIA driver versions 559-565. The cloud machine was upgraded from 565.57 to 570.211 to fix this. GPU ray tracing is 21x faster than CPU (0.14s vs 2.94s for Munich scene).

7. **PyYAML scientific notation.** `yaml.safe_load` treats `28.0e9` as a string. Must write `28.0e+9` (explicit plus sign) for YAML 1.1 compatibility.

## Platform support

| Platform | DiffeRT | Sionna RT | Notes |
|----------|---------|-----------|-------|
| Windows (local) | Works | No | DrJit LLVM JIT crash on scene loading |
| Linux CPU (cloud) | Works | Works | `llvm_ad_mono_polarized` variant |
| Linux GPU (cloud) | Works | Works (fast) | `cuda_ad_mono_polarized`, driver >= 570 |

## Performance (cloud, RTX A4000)

Munich scene, 28 GHz, 3 bounces, level 2, thelonious body:

| Stage | GPU | CPU |
|-------|-----|-----|
| Sionna RT ray tracing | 0.14s | 2.94s |
| Dosimetry (level 2) | 0.87s | 0.87s |
| Total | 1.23s | 3.81s |

## What comes next

Phase 2 (JAX migration) and Phase 3 (React frontend) can proceed in parallel. The batch runner and Sionna integration are ready for paper-producing simulations. Hydra adds value only when sweeps or SLURM submission are needed (Phase 4).
