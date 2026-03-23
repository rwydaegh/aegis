# Stochastic channel model for AEGIS viewer

**Date:** 2026-03-23
**Status:** Draft

## Goal

Replace the crude synthetic path generator (N plane waves with Gaussian jitter) with a proper geometry-based stochastic channel model (GSCM) following 3GPP TR 38.901. The model generates physically realistic multipath clusters with arrival angles, per-cluster power, and K-factor splitting, all parameterized by standardized scenario presets (UMi, UMa, Indoor, InF, RMa, etc.).

Only the **spatial** subset of 3GPP is implemented. Everything temporal (delay spread as a physical quantity, Doppler, drifting, time evolution, spatial consistency, decorrelation distances) is irrelevant for static CW dosimetry and is dropped. However, synthetic delays are still generated internally as the basis for the exponential power delay profile that determines cluster power ratios.

## What changes

- New Python module `src/aegis/channel/` with preset parser and channel generator
- New frontend accordion panel "Stochastic" (below Ray Tracing) with scenario dropdown, editable parameters, mutual exclusion with RT
- Updated `compute.py` to route through the channel generator when stochastic mode is enabled
- 91 QuaDRiGa `.conf` files copied to `data/channel_presets/` as the raw preset source
- Existing `n_paths` / synthetic path code remains for backward compatibility (used when stochastic is off)
- Documentation update

## Architecture

### New module: `src/aegis/channel/`

```
src/aegis/channel/
    __init__.py          # public API: generate_paths(preset, freq_ghz, antenna_pos, body_center, ...) -> PropagationPaths
    presets.py           # parse .conf files, load/list presets, frequency-dependent scaling
    generator.py         # the 3GPP channel generation algorithm (dosimetry subset)
    path_loss.py         # logdist, dual_slope, nlos path loss models
```

### Data flow

```
User selects scenario "3GPP_38.901_UMi_LOS" in frontend
    |
    v
Frontend sends {stochastic: true, preset: "3GPP_38.901_UMi_LOS", overrides: {KF_mu: 12}, seed: 42}
    |
    v
routes/compute.py validates, passes to compute.py
    |
    v
compute.py derives distance from antenna_pos and body_center, then calls:
    channel.generate_paths(preset, freq_ghz, antenna_pos, body_center, power_dbm, seed, overrides)
    |
    v
channel/generator.py:
    1. Load preset, apply frequency-dependent scaling (mu, sigma with omega/gamma/delta)
    2. Draw large-scale params (K, SF, ASA, ESA)
    3. Generate synthetic delays from exponential distribution
    4. Generate cluster powers from delay-based exponential PDP + K-factor splitting
    5. Generate cluster arrival angles (scaled to ASA/ESA, rotated to LOS)
    6. Generate 20 sub-paths per NLOS cluster (offset table)
    7. Apply path loss and shadow fading to total power
    8. Convert (azimuth, elevation, power) to (k_hat, power)
    |
    v
Returns PropagationPaths (same interface as before)
    |
    v
DosimetryEngine.compute(body, paths, ...) proceeds as normal
```

### Frontend panel: StochasticPanel.tsx

New accordion item in Sidebar.tsx, positioned after Ray Tracing.

**Layout:**
- Enable checkbox at top (mutually exclusive with RT enable)
- Scenario dropdown (populated from backend `/api/channel-presets`)
- Editable parameter group (shown below dropdown):
  - K-factor (dB): number input, default from preset
  - Azimuth spread (deg): number input, displayed in linear degrees. Stored internally as log10(deg) but converted for display. Validation: must be > 0.
  - Elevation spread (deg): same
  - Clusters: integer input
  - Sub-paths per cluster: integer input (default 20)
- Seed: integer input
- "Reset to preset" button (restores all overrides to preset defaults)

When the user changes the scenario dropdown, all parameter fields update to that preset's defaults (with freq-dep scaling applied at the current frequency). When the user edits a parameter, it becomes an override. The "Reset" button clears overrides.

### Propagation source model

Instead of two booleans (`stochasticEnabled` + `rtEnabled`) that need cross-store synchronization, use a single enum in the scene store:

```typescript
pathSource: 'synthetic' | 'stochastic' | 'rt'   // default 'synthetic'
```

- `synthetic`: existing single-plane-wave code (current `n_paths` behavior, kept for backward compat)
- `stochastic`: 3GPP channel generator
- `rt`: ray tracing (DiffeRT/Sionna/voxel)

The RT panel's checkbox becomes: `pathSource === 'rt'`, toggling between `'rt'` and the previous non-RT source. The Stochastic panel's checkbox becomes: `pathSource === 'stochastic'`, toggling between `'stochastic'` and `'synthetic'`. This keeps mutual exclusion in a single store field with no cross-store coupling.

### Store changes

Add to scene store (`stores/scene.ts`), replacing `rtEnabled`:
```typescript
pathSource: 'synthetic' | 'stochastic' | 'rt'  // default 'synthetic'
```

Add to simulation store (`stores/simulation.ts`):
```typescript
stochasticPreset: string                         // default "3GPP_38.901_UMi_LOS"
stochasticOverrides: Record<string, number>      // user edits, e.g. {KF_mu: 12}
stochasticSeed: number                           // default 42
```

Keep `nPaths` as-is for the synthetic path source. It remains functional when `pathSource === 'synthetic'`.

### Backend API changes

**New endpoint:** `GET /api/channel-presets`
Returns list of available presets with their parameters (name, display name, category, default params at reference frequency).

**Updated endpoint:** `POST /api/compute`
New optional fields in request body:
```json
{
  "stochastic": true,
  "stochastic_preset": "3GPP_38.901_UMi_LOS",
  "stochastic_overrides": {"KF_mu": 12},
  "stochastic_seed": 42
}
```

When `stochastic: true`, the backend calls `channel.generate_paths()` instead of the old synthetic path code. When `stochastic: false` (or absent), the existing `n_paths`-based behavior is unchanged. This is fully backward compatible.

### Config changes

Add `dosimetry.stochastic` to config.py DEFAULTS (alongside existing `synthetic_paths` and `path_options`, which are kept):
```python
"stochastic": {
    "preset_dir": "data/channel_presets",
    "default_preset": "3GPP_38.901_UMi_LOS",
    "default_seed": 42,
    "featured_presets": [
        "Freespace",
        "3GPP_38.901_UMi_LOS",
        "3GPP_38.901_UMi_NLOS",
        "3GPP_38.901_UMa_LOS",
        "3GPP_38.901_UMa_NLOS",
        "3GPP_38.901_Indoor_LOS",
        "3GPP_38.901_Indoor_NLOS",
        "3GPP_38.901_InF_LOS",
        "3GPP_38.901_RMa_LOS",
        "3GPP_38.901_RMa_NLOS",
    ],
},
```

`featured_presets` controls which presets appear in the frontend dropdown. All 91 are loadable via API, but only these 10 are shown by default. Freespace is included as a baseline (NumClusters=1, produces single LOS path equivalent to the old n_paths=1).

## Channel generation algorithm

Reference: 3GPP TR 38.901 v16.1.0, Table 7.5-6 for scenario parameters. QuaDRiGa v2.8.1 documentation Section 3.3 for the generation procedure (eqs 51-80). Where QuaDRiGa extends 3GPP (e.g. the angular scaling in eqs 66-69), we follow QuaDRiGa.

### Step 1: Load preset and scale parameters

Given frequency $f$ (GHz) and preset params with optional frequency-dependent terms:

$$\mu(f) = \mu_0 + \gamma \cdot \log_{10}(\omega + f)$$
$$\sigma(f) = \sigma_0 + \delta \cdot \log_{10}(\omega + f)$$

where $\omega$ = `*_omega` (reference frequency offset, typically 1 GHz), $\gamma$ = `*_gamma`, $\delta$ = `*_delta`. Not all presets have all terms. Missing `omega` defaults to 1, missing `gamma`/`delta` defaults to 0.

This applies to: AS_A (mu, sigma), ES_A (mu, sigma), DS (mu, sigma, but DS only used for power generation). KF and XPR have no frequency dependence in most 3GPP 38.901 scenarios.

### Step 2: Draw large-scale parameters

For a single realization (single TX-RX link):
- $K = \text{KF\_mu} + \text{KF\_sigma} \cdot \mathcal{N}(0,1)$ (dB)
- $\text{SF} = \text{SF\_sigma} \cdot \mathcal{N}(0,1)$ (dB)
- $\text{ASA} = 10^{\mu_{ASA}(f) + \sigma_{ASA}(f) \cdot \mathcal{N}(0,1)}$ (degrees)
- $\text{ESA} = 10^{\mu_{ESA}(f) + \sigma_{ESA}(f) \cdot \mathcal{N}(0,1)}$ (degrees)
- $\text{DS} = 10^{\mu_{DS}(f) + \sigma_{DS}(f) \cdot \mathcal{N}(0,1)}$ (seconds, used only for power generation)

When the user overrides a parameter (e.g. sets KF_mu = 12), we use the override as the deterministic value (sigma = 0 for that parameter). This gives the user direct control.

### Step 3: Generate cluster delays and powers

$L$ = `num_clusters`. Generate initial delays from a single-sided exponential distribution with unit mean and unit STD (eq 51, QuaDRiGa):

$$\tilde{\tau}_l = -\ln\{X_l^\tau\}$$

where $X_l^\tau \sim \mathcal{U}(0,1)$. The LOS delay ($l=1$) is set to 0.

Generate initial cluster powers using the standard exponential PDP (3GPP TR 38.901, Step 5):

$$\tilde{P}_l = \exp\left\{-\tilde{\tau}_l \cdot \frac{r_\tau - 1}{r_\tau \cdot \text{DS}}\right\} \cdot 10^{-Z_l/10}$$

where $r_\tau$ = `r_DS` (delay scaling factor from preset) and $Z_l \sim \mathcal{N}(0, \xi)$ with $\xi$ = `LNS_ksi` (per-cluster shadowing). DS is the drawn delay spread from Step 2. The delays themselves are not used after this step (we only need the power ratios).

Apply K-factor (eq 61): set the LOS cluster power to $K_\text{linear}$ times the sum of all NLOS cluster powers:

$$\tilde{P}_{1} = K_\text{linear} \cdot \sum_{l=2}^{L} \tilde{P}_{l}, \quad K_\text{linear} = 10^{K_\text{dB}/10}$$

Normalize (eq 62): $P_l = \tilde{P}_l / \sum_{l=1}^{L} \tilde{P}_l$

For NLOS-only scenarios (KF_mu = -100 dB, e.g. UMa_NLOS), $K_\text{linear} \approx 0$ and the LOS cluster gets negligible power. All clusters are effectively NLOS.

### Step 4: Generate cluster arrival angles

Initial angles drawn uniformly on $[-\pi/2, \pi/2]$ (eq 54). The LOS path initial angles are set to 0.

Scale to match target ASA/ESA using the QuaDRiGa scaling procedure (eqs 66-69):

1. Compute power-weighted mean angle offset $\Delta_\phi$ (eq 66)
2. Shift angles: $\hat{\phi}_l = \arg\exp\{j(\tilde{\phi}_l - \Delta_\phi)\}$ (eq 67)
3. Compute achieved AS: $\widetilde{\text{AS}}$ (eq 68)
4. Compute scaling coefficient: $s = \text{AS}_\text{target} / \widetilde{\text{AS}}$, clamped to 3.0 for azimuth and 1.5 for elevation (eq 69)
5. Apply scaling: $\phi_l = \arg\exp(j \cdot \tilde{\phi}_l \cdot s)$

Same procedure for elevation angles with ES_A target.

### Step 5: LOS rotation

Compute LOS azimuth and elevation from antenna_pos to body_center:
- $\phi_1^a = \arctan_2(y_r - y_t, x_r - x_t)$ (eq 70-71)
- $\theta_1^a = \arctan_2(z_r - z_t, d_{2d})$ (eq 72-73)

Construct the 3D rotation matrix from LOS angles (eq 76) and apply to all cluster direction vectors. Convert back to spherical (eqs 77-78).

### Step 6: Sub-paths

**LOS cluster ($l = 1$):** 1 specular path (no sub-paths) carrying the full LOS cluster power.

**NLOS clusters ($l > 1$):** each split into 20 sub-paths using the fixed offset table from 3GPP (Table 26 in QuaDRiGa docs):

$$\phi_{l,m} = \phi_l + \frac{\pi \cdot c_\phi \cdot \hat{\phi}_m}{180^\circ}$$

where $c_\phi$ = `per_cluster_AS_A` and $\hat{\phi}_m$ are the 20 standard sub-path offsets ($\pm 0.0447, \pm 0.1413, \pm 0.2492, \ldots, \pm 2.1551$ degrees). Same for elevation with `per_cluster_ES_A`. Each sub-path within a cluster carries equal power ($P_l / 20$).

**Total path count:** $1 + (L-1) \times 20$ for LOS scenarios. For pure NLOS scenarios (K $\approx$ 0), all L clusters get 20 sub-paths: $L \times 20$ total paths.

### Step 7: Convert to PropagationPaths

Spherical to Cartesian: $\hat{k} = (\cos\theta\cos\phi, \cos\theta\sin\phi, \sin\theta)$ (eq 75).

Negate (arrival direction to propagation direction): $\hat{k} \to -\hat{k}$.

Compute total incident power density at the body surface:
- Distance $d$ derived from antenna_pos and body_center
- Path loss: $\text{PL}(d, f)$ from the preset's path loss model
- Shadow fading: $\text{SF}$ from Step 2
- $S_\text{inc} = \frac{P_\text{tx}}{4\pi d^2} \cdot 10^{-\text{PL}(d,f)/10} \cdot 10^{\text{SF}/10}$

Wait, that double-counts. The path loss model already accounts for distance. So:

- $P_\text{rx} = P_\text{tx} \cdot 10^{-\text{PL}(d,f)/10} \cdot 10^{\text{SF}/10}$ (received power in watts)
- $S_\text{inc} = P_\text{rx} / A_\text{eff}$ or simply use $P_\text{rx} / (4\pi d^2)$ as the power density

Actually, for dosimetry we need incident power density $S_\text{inc}$ (W/m^2). The 3GPP path loss gives received power for isotropic antennas. The correct conversion:

$$S_\text{inc} = \frac{P_\text{tx}}{4\pi d^2} \cdot 10^{\text{SF}/10}$$

We use free-space path loss for the power density (same as current code), with the 3GPP shadow fading applied on top. The 3GPP path loss models (which include waveguide effects, NLOS excess loss, etc.) would replace the $1/4\pi d^2$ term, but they output received power, not power density. For consistency with how AEGIS defines $S_\text{inc}$, we use FSPL for the power density and let the channel model control the angular/power distribution across clusters.

Assign per-path power: $P_l \cdot S_\text{inc}$ for each cluster/sub-path (sub-paths share cluster power equally).

Build and return `PropagationPaths.from_powers(k_hat=k_hats, power=powers)`.

**XPR note:** Cross-polarization ratio has no effect when using `from_powers()` for incoherent dosimetry (levels 0-6), because power is a scalar. XPR support is deferred to when coherent levels (7-8) are wired to the viewer. The XPR parameter is parsed and stored in the preset but not applied in the initial implementation.

### Path loss models

The preset `.conf` files reference several path loss model types. Supported models for the featured presets:

| Model | Formula | Used by |
|-------|---------|---------|
| `logdist` | $\text{PL} = A\log_{10}(d) + B + C\log_{10}(f)$ | Freespace, Indoor, InF |
| `dual_slope` | $\text{PL}_1$ before breakpoint, $\text{PL}_2$ after | UMi LOS, UMa LOS, RMa LOS |
| `nlos` | $\max(\text{PL}_\text{LOS}, \text{PL}_n)$ with height terms | UMa NLOS, UMi NLOS, RMa NLOS |

Non-featured presets with unsupported PL models (e.g. `satellite`, `TwoRayGR`) fall back to free-space path loss with a warning logged. The preset is still usable for its angular/cluster structure.

## Files changed

| File | Change | Lines |
|------|--------|-------|
| `src/aegis/channel/__init__.py` | New: public API | ~20 |
| `src/aegis/channel/presets.py` | New: .conf parser, preset loader, freq scaling with omega/gamma/delta | ~140 |
| `src/aegis/channel/generator.py` | New: generation algorithm (steps 2-7) | ~300 |
| `src/aegis/channel/path_loss.py` | New: 3 path loss models + fallback | ~60 |
| `src/aegis/viewer/config.py` | Add stochastic config block (keep existing synthetic_paths) | ~20 |
| `src/aegis/viewer/compute.py` | Add stochastic branch (keep existing n_paths code) | ~30 |
| `src/aegis/viewer/routes/compute.py` | Accept stochastic params, new /api/channel-presets endpoint | ~50 |
| `configs/default.json` | Add stochastic section to dosimetry | ~15 |
| `aegis-web/src/components/panels/StochasticPanel.tsx` | New: full panel component | ~150 |
| `aegis-web/src/components/panels/RayTracingPanel.tsx` | Use pathSource enum instead of rtEnabled | ~15 |
| `aegis-web/src/components/panels/ParametersPanel.tsx` | Hide stochastic propagation dropdown when stochastic mode active | ~5 |
| `aegis-web/src/components/layout/Sidebar.tsx` | Add Stochastic accordion item | ~10 |
| `aegis-web/src/stores/scene.ts` | Replace rtEnabled with pathSource enum | ~15 |
| `aegis-web/src/stores/simulation.ts` | Add stochastic state (keep nPaths) | ~20 |
| `aegis-web/src/hooks/useDosimetry.ts` | Branch on pathSource, send stochastic params | ~20 |
| `tests/test_channel.py` | New: unit tests for generator | ~100 |
| `tests/test_channel_presets.py` | New: preset parsing tests | ~50 |
| `docs/user_guide/viewer.md` | Update with stochastic channel section | ~40 |
| `data/channel_presets/*.conf` | Already copied (91 files) | 0 |

**Total: ~1060 lines across 19 files** (6 new Python, 1 new TSX, 12 modified).

## Testing strategy

- **Preset parser**: parse all 91 .conf files, verify required fields present, no exceptions
- **Frequency scaling**: check AS_A_mu at 28 GHz vs 2 GHz for UMi_LOS, verify omega/gamma/delta applied correctly
- **Power normalization**: $\sum P_l = 1$ for any preset/seed combo
- **K-factor**: generate 1000 realizations for UMi_LOS, verify mean $P_1 / \sum_{l>1} P_l$ matches $10^{9/10}$ within 1 dB
- **Angular spread**: generate 1000 realizations, check mean ASA/ESA matches preset target within 15%
- **LOS direction**: verify cluster 1 direction vector points from antenna to body center
- **Sub-path count**: $1 + (L-1) \times 20$ for LOS presets, $L \times 20$ for NLOS presets
- **Path loss**: check logdist and dual_slope against hand-computed values
- **PropagationPaths integration**: verify output feeds into DosimetryEngine without errors, S_ab >= 0
- **Regression**: golden test with fixed seed + UMi_LOS preset, check exact k_hats and powers match snapshot
- **Backward compat**: verify existing n_paths=1 compute still works when stochastic is off

## What is NOT included

- Delay spread as a physical output (delays are generated internally for power weighting only)
- Doppler, mobility, drifting
- Inter-parameter correlations (single drop, not needed)
- Departure angles (TX is isotropic/dipole in viewer)
- Spatial consistency / decorrelation distances
- O2I (outdoor-to-indoor) penetration loss
- Ground reflection model (QuaDRiGa Section 3.9)
- Multi-frequency joint generation
- XPR polarization (deferred to coherent level support)
