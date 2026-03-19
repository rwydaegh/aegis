# Tissue and Fresnel transmission

AEGIS models the electromagnetic properties of human tissue to compute how much incident power is absorbed at the body surface. The tissue module provides dielectric models, Fresnel transmission coefficients, and a database of tissue properties from the IT'IS foundation.

## Dielectric properties

At mmWave frequencies, tissue behaves as a lossy dielectric characterized by two parameters: relative permittivity $\varepsilon_r$ and conductivity $\sigma$. These combine into a complex refractive index:

$$\tilde{n} = \sqrt{\varepsilon_r - j\frac{\sigma}{\omega \varepsilon_0}}$$

For skin at 28 GHz: $\varepsilon_r = 17.0$, $\sigma = 25.0$ S/m, giving $|\tilde{n}| \approx 5.5$.

```python
from aegis.tissue.fresnel import n_complex

n = n_complex(eps_r=17.0, sigma=25.0, freq_hz=28e9)
print(f"|n| = {abs(n):.2f}")  # 5.49
```

## TissueModel

The `TissueModel` dataclass wraps dielectric parameters and provides derived quantities:

```python
from aegis.tissue import TissueModel

# From explicit parameters
skin = TissueModel.from_params("Skin 28 GHz", eps_r=17.0, sigma=25.0, freq_hz=28e9)
print(skin.T0)         # 0.539
print(skin.n_complex)  # complex refractive index
```

### Predefined tissues

Four tissue types are hardcoded from published literature:

| Tissue | Frequency | $\varepsilon_r$ | $\sigma$ (S/m) | $\mathcal{T}_0$ |
|--------|-----------|-----------------|-----------------|------------------|
| `SKIN_28GHZ` | 28 GHz | 17.0 | 25.0 | 0.539 |
| `SKIN_60GHZ` | 60 GHz | 7.9 | 36.4 | 0.548 |
| `MUSCLE_28GHZ` | 28 GHz | 25.0 | 30.0 | 0.483 |
| `FAT_28GHZ` | 28 GHz | 4.0 | 2.0 | 0.822 |

```python
from aegis.tissue import SKIN_28GHZ
print(SKIN_28GHZ.T0)  # 0.539
```

### IT'IS database

For arbitrary tissue types and frequencies, AEGIS uses the IT'IS v5.0 database with a 4-pole Cole-Cole model (Gabriel 1996):

```python
skin_db = TissueModel.from_database("Skin", 28e9)
print(f"T_0 = {skin_db.T0:.3f}")
```

The database file (`itis_v5.db`) must be in the data directory. Set `AEGIS_DATA_DIR` or use the default location `../../data/`.

The Cole-Cole model computes complex permittivity from 14 parameters (4 poles with relaxation times spanning picoseconds to milliseconds). This gives accurate dielectric properties across 10 Hz to 100 GHz.

## Fresnel transmission

The fraction of incident power that enters the tissue depends on the angle of incidence $\theta_i$. AEGIS computes Fresnel power transmission coefficients for both TE and TM polarizations.

### Normal incidence

At normal incidence ($\theta_i = 0$), the transmission coefficient simplifies to:

$$\mathcal{T}_0 = \frac{4 \, \text{Re}(\tilde{n})}{|1 + \tilde{n}|^2}$$

This is the single most important tissue parameter. For skin at 28 GHz, $\mathcal{T}_0 = 0.539$, meaning 53.9% of incident power is absorbed.

### Angle-dependent transmission

For oblique incidence, TE and TM polarizations transmit different fractions:

```python
import numpy as np
from aegis.tissue.fresnel import fresnel_transmission, n_complex

n = n_complex(eps_r=17.0, sigma=25.0, freq_hz=28e9)
mu = np.cos(np.radians(45))  # cos(theta_i)

T_s, T_p = fresnel_transmission(mu, n)
print(f"TE: {T_s:.3f}, TM: {T_p:.3f}")  # TE: 0.422, TM: 0.666
```

TM polarization always transmits more than TE at oblique angles. This matters at Level 4 and above, where polarization corrections are applied.

The unpolarized (average) transmission is:

$$\mathcal{T}_{avg}(\theta) = \frac{\mathcal{T}_s(\theta) + \mathcal{T}_p(\theta)}{2}$$

### Amplitude coefficients

Coherent dosimetry (Levels 7-8) needs complex amplitude transmission coefficients, not power:

```python
from aegis.tissue.fresnel import fresnel_amplitude

t_s, t_p = fresnel_amplitude(mu, n)
print(f"t_s = {t_s:.3f}, t_p = {t_p:.3f}")  # complex values
```

The power coefficient relates to the amplitude as $\mathcal{T} = \text{Re}(\xi) / \mu \cdot |t|^2$ where $\xi$ is the normal wave-vector component in tissue.

## How fidelity levels use tissue

| Level | Tissue parameter | Notes |
|-------|-----------------|-------|
| 0-2 | $\mathcal{T}_0$ (scalar) | Same transmission for all angles |
| 3 | $\mathcal{T}_{avg}(\theta)$ | Angle-dependent, unpolarized |
| 4 | $\mathcal{T}_s, \mathcal{T}_p$ separately | Polarization-resolved |
| 5-6 | $\mathcal{T}_{avg}(\theta)$ + curvature | Physical optics correction |
| 7-8 | $t_s, t_p$ (complex amplitudes) | Full coherent Fresnel operator |

The transition from Level 2 to Level 3 (replacing constant $\mathcal{T}_0$ with angle-dependent $\mathcal{T}_{avg}$) changes total absorbed power by about 0.35% on typical body meshes. The correction matters more for geometries with many grazing-incidence triangles.
