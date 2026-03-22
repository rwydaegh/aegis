# Batch runner

Run dosimetry simulations from the command line without the viewer. Each run saves a resolved YAML config alongside results for full reproducibility.

## Quick start

```bash
py -3.12 -m aegis.run --config runs/my_scenario.yaml
```

Or specify everything inline:

```bash
py -3.12 -m aegis.run \
    --body thelonious \
    --frequency 28e9 \
    --level 2 \
    --antenna-pos "5,0,1" \
    --backend synthetic
```

## Configuration

Simulations are defined by a YAML config file. All fields have defaults, so you only need to specify what differs from the baseline.

```yaml
tissue:
  name: Skin           # IT'IS database name (capitalized)
  frequency_hz: 28.0e+9

body:
  name: thelonious      # STL filename stem in data/
  mass_kg: null         # for whole-body SAR (optional)

antenna:
  positions:
    - [5.0, 0.0, 1.0]  # TX element positions [m]
  power_dbm: 30.0
  polarisation: vertical
  pattern: isotropic

raytracer:
  backend: synthetic    # synthetic (default: differt), differt, or sionna
  max_bounces: 3
  scene_path: null      # required for differt/sionna

dosimetry:
  level: 2              # fidelity level 0-8
  spatial_averaging: false

output_dir: outputs
```

### Backends

Three ray tracer backends are available:

- `synthetic` generates one LOS path per TX element using free-space path loss. No external dependencies, useful for testing and quick estimates.
- `differt` runs DiffeRT ray tracing on a Sionna XML scene. Requires `pip install aegis[rt]`. Tracks TE/TM polarisation through reflections.
- `sionna` runs Sionna RT on a scene file. Requires `pip install aegis[sionna]`. Handles large city-scale scenes with diffraction and scattering.

### CLI overrides

Any config field can be overridden from the command line. CLI flags take precedence over the YAML file.

```bash
py -3.12 -m aegis.run --config base.yaml --level 6 --power-dbm 23
```

Available flags: `--body`, `--frequency`, `--level`, `--power-dbm`, `--antenna-pos`, `--backend`, `--max-bounces`, `--scene-path`, `--output-dir`.

## Output

Each run creates a timestamped directory under `output_dir/`:

```
outputs/20260321_143052/
    config.yaml      # resolved config (exactly what was computed)
    result.npz        # sab array, p_abs
    summary.json      # peak Sab, compliance, timing
```

The `summary.json` looks like:

```json
{
  "peak_sab": 0.0234,
  "p_abs": 0.00012,
  "compliant": true,
  "compliant_note": "conservative (no spatial averaging)",
  "level": 2,
  "n_triangles": 320,
  "elapsed_s": 0.042
}
```

The compliance check compares the raw per-triangle peak against the ICNIRP 2020 limit of 10 W/m$^2$. This is conservative because the standard requires spatial averaging over 4 cm$^2$.

## Relationship to the viewer

The batch runner and the interactive viewer are separate systems. The viewer has its own JSON-based config for real-time interaction (camera, lighting, UI). The batch runner uses `SimulationConfig` YAML for reproducible research runs. They share the same dosimetry engine, tissue database, and body meshes.

## Python API

You can also use `SimulationConfig` directly in scripts:

```python
from aegis.config import SimulationConfig, TissueConfig

cfg = SimulationConfig(
    tissue=TissueConfig(name="Skin", frequency_hz=60e9),
)
cfg.to_yaml("my_run.yaml")

# Later, reload:
cfg2 = SimulationConfig.from_yaml("my_run.yaml")
assert cfg == cfg2
```
