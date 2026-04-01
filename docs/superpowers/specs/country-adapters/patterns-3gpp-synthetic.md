# 3GPP TR 38.901 synthetic pattern spec

## Source
- **Name:** 3GPP TR 38.901 parametric antenna model
- **URL:** https://www.3gpp.org/ftp/Specs/archive/38_series/38.901/
- **Type:** Mathematical formula (no download)
- **Auth:** N/A
- **License:** FRAND (3GPP standards are freely readable; no data redistribution concern)

## What it provides

A parametric single-element radiation pattern for 5G NR base station antennas, defined in 3GPP TR 38.901 Section 7.3. This is a synthetic model, not measured data. It captures the main lobe shape but does not reproduce realistic sidelobes or manufacturing variation.

Use this model when no measured pattern is available from CommScope BSAPatternsWeb or wireless-planning.com.

## Model definition

Single-element 3D pattern (dB, relative to boresight):

```
A_E,V(theta') = -min[12 * (theta' / theta_3dB)^2, SLA_V]   [vertical cut, dB]
A_E,H(phi)   = -min[12 * (phi   / phi_3dB)^2,   A_m   ]   [horizontal cut, dB]
A_E(theta', phi) = -min[-(A_E,V(theta') + A_E,H(phi)), A_m]
```

Where `theta'` is the zenith angle measured from the downward boresight direction (0 = boresight, 90 = horizon), and `phi` is the azimuth angle from the main lobe direction.

Default parameters:
| Parameter | Value | Description |
|---|---|---|
| theta_3dB | 65 deg | Vertical 3 dB beamwidth |
| phi_3dB | 65 deg | Horizontal 3 dB beamwidth |
| SLA_V | 30 dB | Vertical sidelobe attenuation limit |
| A_m | 30 dB | Maximum attenuation (front-to-back ratio) |
| G_max | 8 dBi | Maximum element gain |

Absolute gain: `G_E(theta', phi) = G_max + A_E(theta', phi)` (add because A_E is in dB and negative).

## Python implementation

```python
import numpy as np

def pattern_3gpp_38901(
    theta_deg,       # elevation angles, 0 = boresight (array)
    phi_deg,         # azimuth angles, 0 = main lobe (array)
    theta_3dB=65.0,
    phi_3dB=65.0,
    SLA_V=30.0,
    A_m=30.0,
    G_max_dBi=8.0,
):
    """3GPP TR 38.901 single-element pattern. Returns gain in dBi."""
    theta = np.asarray(theta_deg, dtype=float)
    phi   = np.asarray(phi_deg,   dtype=float)

    A_V = -np.minimum(12.0 * (theta / theta_3dB) ** 2, SLA_V)
    A_H = -np.minimum(12.0 * (phi   / phi_3dB  ) ** 2, A_m )
    A_E = -np.minimum(-(A_V + A_H), A_m)
    return G_max_dBi + A_E
```

Angles outside [-180, 180] should be wrapped before calling.

## Limitations

This model is intentionally idealised:

1. No realistic sidelobes. Real antennas have sidelobe levels 15-25 dB below the main lobe. The 3GPP model has zero sidelobes (pure Gaussian roll-off, clamped at `SLA_V`/`A_m`). For a population-average dosimetry model this overpredicts exposure in back-lobe directions by the front-to-back ratio.
2. Frequency-independent. The pattern does not change with frequency. Real antennas narrow at higher frequencies.
3. Single element only. For massive MIMO arrays, the array pattern is the single-element pattern multiplied by the array factor, which depends on the precoding vector. This spec covers only the single-element baseline.
4. The Gaussian shape is symmetric. Real antennas have asymmetric patterns due to feed network design and radome effects.

For AEGIS dosimetry, the impact of using 3GPP synthetic vs measured MSI is largest in high-elevation-angle directions (above the horizon for a tilted antenna), where the model underestimates the back-radiation. In the forward hemisphere the error is small.

## When to use

Apply the 3GPP model in this priority order:

1. Measured pattern from Brussels 181x360 matrix (best)
2. Measured MSI from CommScope BSAPatternsWeb or wireless-planning.com
3. 3GPP TR 38.901 synthetic (this spec)

The 3GPP model is appropriate for:
- Countries where no pattern library match is found
- Rapid prototyping and scenario sweeps
- Situations where the antenna model number is unknown

Do not use the 3GPP model when a measured pattern is available. The difference in peak power density near the antenna can reach 25-35 dB in back-lobe directions.

## AEGIS integration

```python
from aegis.geometry.directivity import pattern_3gpp_38901

# Generate a 181x360 matrix for AEGIS (same shape as Brussels format)
theta = np.linspace(0, 180, 181)  # elevation from boresight
phi   = np.linspace(0, 359, 360)  # azimuth
THETA, PHI = np.meshgrid(theta, phi, indexing="ij")
gain_dBi = pattern_3gpp_38901(THETA, PHI)  # shape (181, 360)
```

This produces a matrix compatible with the Brussels-format pattern arrays already used in AEGIS. Store at `data/antenna_patterns/synthetic_3gpp_38901.npy`.

## Parameter overrides by band

When frequency band is known but no measured pattern is available, the beamwidth defaults can be adjusted:

| Band | theta_3dB | phi_3dB | Notes |
|---|---|---|---|
| 700-900 MHz | 65 deg | 65 deg | 3GPP default |
| 1800-2100 MHz | 65 deg | 65 deg | 3GPP default |
| 2600 MHz | 65 deg | 65 deg | 3GPP default |
| 3500 MHz (5G sub-6) | 65 deg | 65 deg | 3GPP default; massive MIMO arrays vary widely |
| 26/28 GHz (mmWave) | 10-15 deg | 10-15 deg | Much narrower; consult 3GPP TR 38.802 |

## Status
No dedicated implementation. The formula is simple enough to inline. A shared utility function in `aegis/geometry/directivity.py` is sufficient.
