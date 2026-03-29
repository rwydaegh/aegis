# Stochastic channel model

AEGIS includes a 3GPP TR 38.901 cluster-based channel generator that produces multipath propagation paths without a ray tracer. It draws large-scale fading parameters (delay spread, K-factor, angular spreads, shadow fading) from log-normal distributions parameterized by the chosen scenario preset, then expands them into per-cluster and per-subpath arrival directions and powers. The output is a `PropagationPaths` object identical to one produced by DiffeRT or Sionna RT, so any incoherent fidelity level (0-6) can consume it directly.

The model is the default path source in the interactive viewer when ray tracing is disabled.

## When to use it

Use the stochastic channel when you want fast dosimetry estimates across many antenna placements without building or loading a geometric scene. It is appropriate for sensitivity studies, fidelity-level comparisons, and compliance screening where the exact multipath geometry is unknown. Use ray tracing when building geometry is available and you need spatially consistent paths tied to specific reflectors.

The two modes are mutually exclusive in the viewer. Enabling stochastic channel disables ray tracing and vice versa.

## Presets

Presets are QuaDRiGa-format `.conf` files in `data/channel_presets/`. The viewer exposes a curated set of featured presets. The full library contains over 80 entries from 3GPP TR 38.901, WINNER II, mmMAGIC, Berlin measurements, and QuaDRiGa NTN models.

Featured presets (configured in `dosimetry.stochastic.featured_presets`):

| Preset | Scenario | Valid range |
|--------|----------|-------------|
| `Freespace` | Free-space reference (single LOS path) | any |
| `3GPP_38.901_UMi_LOS` | Urban micro, line-of-sight | 0.5-100 GHz, 10-5000 m |
| `3GPP_38.901_UMi_NLOS` | Urban micro, non-line-of-sight | 0.5-100 GHz, 10-5000 m |
| `3GPP_38.901_UMa_LOS` | Urban macro, line-of-sight | 0.5-100 GHz, 10-5000 m |
| `3GPP_38.901_UMa_NLOS` | Urban macro, non-line-of-sight | 0.5-100 GHz, 10-5000 m |
| `3GPP_38.901_Indoor_LOS` | Indoor factory/office, LOS | 0.5-100 GHz, 1-150 m |
| `3GPP_38.901_Indoor_NLOS` | Indoor factory/office, NLOS | 0.5-100 GHz, 1-150 m |
| `3GPP_38.901_InF_LOS` | Indoor factory, LOS | 0.5-100 GHz |
| `3GPP_38.901_RMa_LOS` | Rural macro, LOS | 0.5-7 GHz, 10-10000 m |
| `3GPP_38.901_RMa_NLOS` | Rural macro, NLOS | 0.5-7 GHz, 10-10000 m |

The default preset is `3GPP_38.901_UMi_LOS`. To list all installed presets programmatically:

```python
from aegis.channel import list_presets
from pathlib import Path

names = list_presets(Path("data/channel_presets"))
print(names)  # sorted list of all .conf stems
```

## Key parameters

Each preset defines a set of large-scale parameters sampled once per realization:

- **K-factor** (`KF_mu`, `KF_sigma`): Ricean K-factor in dB. Controls the power ratio of the dominant (LOS) cluster to the diffuse multipath. The UMi LOS preset uses $K = 9 \pm 5$ dB. NLOS presets set `KF_mu = -100` dB (effectively zero LOS component).
- **Delay spread** (`DS_mu`, `DS_gamma`): RMS delay spread in log$_{10}$(s), frequency-scaled as $\mu + \gamma \log_{10}(f/f_0)$.
- **Azimuth spread of arrival** (`AS_A_mu`, `AS_A_gamma`): Log$_{10}$(degrees) at the body. For UMi LOS at 28 GHz, the mean ASA is about $10^{1.56} \approx 36°$.
- **Elevation spread of arrival** (`ES_A_mu`): Elevation equivalent of ASA. Typically smaller than ASA (UMi LOS mean ESA $\approx 7°$ at 28 GHz).
- **NumClusters**: Number of scattering clusters. The UMi preset uses 12 clusters.
- **NumSubPaths**: Sub-paths per NLOS cluster (default 20). Each cluster is expanded using the fixed QuaDRiGa offset table with per-cluster angular spreads `PerClusterAS_A` and `PerClusterES_A`.

Shadow fading (`SF_sigma`) is drawn independently and applied as a multiplicative offset on the total received power.

## Generation procedure

`generate_channel` runs the following steps:

1. Draw large-scale parameters (DS, KF, SF, ASA, ESA) from their log-normal distributions, applying frequency scaling.
2. Generate cluster powers from an exponential power delay profile scaled by the delay spread ratio `r_DS`. Add per-cluster log-normal shadowing (`LNS_ksi`). Boost cluster 0 power by the K-factor.
3. Draw cluster arrival angles (azimuth and elevation), then scale them to match the drawn ASA/ESA.
4. Rotate all cluster angles so cluster 0 points toward the body center.
5. Expand each NLOS cluster into `NumSubPaths` sub-paths using the fixed offset table. The LOS cluster remains a single ray.
6. Compute path loss from the antenna-to-body distance using the preset's path loss model (`logdist`, `dual_slope`, or `nlos`). Apply the shadow fading offset.
7. Return `PropagationPaths.from_powers(k_hat, power)`.

The LOS cluster points toward the body by construction. The remaining clusters form a diffuse halo whose angular spread matches the drawn ASA/ESA.

## Path loss models

The generator supports three path loss models selected by `PL_model` in the preset:

- `logdist`: $\text{PL} = A \log_{10}(d) + B + C \log_{10}(f)$
- `dual_slope`: two-segment LOS model with a breakpoint distance $d_{\mathrm{BP}} = E(h_{\mathrm{BS}} - h_E)(h_{\mathrm{MS}} - h_E) f$
- `nlos`: $\max(\text{dual\_slope}, A_n \log_{10}(d) + B_n + C_n \log_{10}(f))$

Unknown models fall back to free-space path loss $20 \log_{10}(d) + 20 \log_{10}(f) + 32.45$ dB.

## Python API

### Basic usage

```python
from aegis.channel import generate_channel, load_preset
from aegis import DosimetryEngine
from aegis.tissue.dielectric import SKIN_28GHZ
import numpy as np

preset = load_preset("3GPP_38.901_UMi_LOS", "data/channel_presets")

paths = generate_channel(
    params=preset["params"],
    freq_ghz=28.0,
    antenna_pos=np.array([10.0, 0.0, 1.5]),
    body_center=np.array([0.0, 0.0, 1.0]),
    power_dbm=23.0,
    seed=42,
)

engine = DosimetryEngine(SKIN_28GHZ)
result = engine.compute(body, paths, level=2)
```

### Overriding preset parameters

Pass an `overrides` dict to `generate_channel` to fix specific parameters without editing the `.conf` file:

```python
paths = generate_channel(
    params=preset["params"],
    freq_ghz=28.0,
    antenna_pos=antenna_pos,
    body_center=body_center,
    power_dbm=23.0,
    seed=42,
    overrides={
        "KF_mu": 15,          # stronger LOS component (15 dB)
        "AS_A_mu": 1.0,       # narrower azimuth spread (~10 deg)
    },
)
```

When a parameter key appears in `overrides`, its variance (`sigma`) is set to zero, so the override becomes the deterministic value.

### Loading a custom preset

Any QuaDRiGa-format `.conf` file can be used. Pass a `Path` to the directory containing your file:

```python
from aegis.channel import parse_conf

params = parse_conf("my_scenarios/custom_scenario.conf")
paths = generate_channel(params, freq_ghz=60.0, ...)
```

## Viewer configuration

The stochastic channel is controlled by the `dosimetry.stochastic` block in the viewer config:

```json
{
  "dosimetry": {
    "stochastic": {
      "preset_dir": "data/channel_presets",
      "default_preset": "3GPP_38.901_UMi_LOS",
      "default_seed": 42,
      "featured_presets": [
        "Freespace",
        "3GPP_38.901_UMi_LOS",
        "3GPP_38.901_UMi_NLOS"
      ]
    }
  }
}
```

The `featured_presets` list controls which presets appear in the viewer dropdown. The full preset library is still accessible via the REST endpoint `GET /api/channel-presets`. The viewer UI also exposes K-factor, azimuth/elevation spread, and number of clusters as overridable fields per realization.

## Comparison with ray tracing

| | Stochastic channel | Ray tracing |
|-|-------------------|-------------|
| Scene geometry required | No | Yes |
| Paths per realization | 221 (12 clusters × 20 subpaths - 19 LOS subpaths + 1 LOS) | depends on scene and bounce count |
| Spatial consistency | None (i.i.d. per call) | Yes (paths tied to reflectors) |
| Frequency range | 0.5-100 GHz (preset-dependent) | any |
| Compute time | < 1 ms | 50 ms to seconds |
| Fidelity levels supported | 0-6 (incoherent only) | 0-8 |

Ray tracing supports coherent levels 7-8 because it produces complex path amplitudes $\psi$. The stochastic generator only produces scalar powers and therefore feeds incoherent kernels only.
