# Configuration centralization and export

**Date**: 2026-03-27
**Status**: Approved
**Scope**: Backend defaults refactor, SimulationConfig expansion, viewer config export, share URL compression

## Problem

AEGIS has two config systems (SimulationConfig for batch, viewer JSON for interactive) and neither is complete. Hardcoded defaults are scattered across 30+ files. The viewer can share state via URL but cannot export a full reproducible config file. Share URLs use uncompressed base64.

## Goals

1. No hardcoded default values in code. All defaults live in named constants or config files.
2. SimulationConfig captures enough state for reproducible batch runs.
3. The viewer can export a complete JSON config that relaunches the exact same scene.
4. Share URLs are shorter via deflate compression.
5. No behavior changes. Current defaults are preserved exactly.

## Non-goals

- Unifying the two config systems into one (viewer needs display params that batch does not).
- Making physics constants (c, eps_0) or ICNIRP regulatory limits configurable.
- Making internal numerical safety floors (1e-30) configurable.
- Embedding binary scene data (STL, voxels) in exported configs. Configs reference paths.

---

## Design

### 1. Centralize scattered defaults

**New file: `src/aegis/defaults.py`**

```python
"""Project-wide default values. Single source of truth for all defaults
that appear in function signatures, dataclass fields, and config dicts."""

DEFAULT_FREQ_HZ: float = 28e9
DEFAULT_POWER_DBM: float = 60.0
DEFAULT_P_ABS_MAX: float = 0.1         # absorbed power limit [W]
DEFAULT_NOISE_POWER: float = 0.01      # MMSE noise power
DEFAULT_FIDELITY_LEVEL: int = 2
DEFAULT_MAX_BOUNCES: int = 3
DEFAULT_SEED: int = 42

NUMERICAL_FLOOR: float = 1e-30         # safe-division guard

CONCRETE_EPS_R: float = 5.31           # material fallback
CONCRETE_SIGMA: float = 0.0326
```

**Files to update** (import from `defaults.py` instead of inline literals):

| Constant | Files affected |
|----------|---------------|
| `DEFAULT_FREQ_HZ` | `config.py`, `viewer/config.py`, `viewer/compute.py`, `viewer/raytracer.py`, `viewer/modal_proxy.py`, `viewer/routes/compute.py`, `viewer/routes/mimo.py`, `compliance/__init__.py`, `mimo/scene.py`, `mimo/compute.py`, `viz/dashboard.py`, `channel/presets.py`, `integration/differt.py`, `modal_rt/differt_tracer.py`, `modal_rt/sionna_tracer.py` |
| `DEFAULT_POWER_DBM` | `config.py`, `viewer/config.py`, `viewer/raytracer.py`, `viewer/compute.py`, `viewer/modal_proxy.py` (3x), `viewer/routes/compute.py` (3x), `integration/differt.py` (2x), `integration/sionna.py`, `modal_rt/differt_tracer.py`, `modal_rt/sionna_tracer.py` |
| `DEFAULT_P_ABS_MAX` | `engine.py` (3x), `kernels/level8_ecbf.py`, `mimo/compute.py` (2x) |
| `DEFAULT_NOISE_POWER` | `mimo/precoders.py`, `mimo/compute.py` |
| `DEFAULT_SEED` | `channel/generator.py`, `integration/sionna.py` |
| `NUMERICAL_FLOOR` | `coherent/ecbf.py` (3x), `coherent/exposure_operator.py` (2x), `coherent/body_channel.py`, `precoder.py`, `mimo/precoders.py` (3x), `geometry/occlusion.py`, `result.py`, `kernels/_base.py`, `channel/generator.py` (2x), `viz/dashboard.py` |
| `CONCRETE_EPS_R/SIGMA` | `integration/differt.py` (3x) |

Pure refactor. Every call site gets the same numeric value it had before.

**Phantom masses: `data/phantoms.yaml`**

```yaml
thelonious:
  mass_kg: 17.4
duke:
  mass_kg: 72.4
eartha:
  mass_kg: 56.0
ella:
  mass_kg: 58.7
```

`viewer/compute.py` loads this file (cached) instead of hardcoding `PHANTOM_MASS_KG`.

### 2. Fix config drift

Sync `viewer/config.py` DEFAULTS to match the values that result from deep-merging `default.json` on top. Since all current users run with `default.json`, the merged output is the true default. Aligning DEFAULTS means running without a JSON file produces the same values.

| Key | DEFAULTS now | JSON now | Fix DEFAULTS to |
|-----|-------------|----------|-----------------|
| `voxels.size_scale` | 0.99 | 0.95 | 0.95 |
| `dosimetry.power_input.min` | -30 | 0 | 0 |
| `dosimetry.power_input.max` | 80 | 60 | 60 |
| `dosimetry.convex_body_area_factor` | 1.0 | 0.25 | 0.25 |

Also add keys that exist in `default.json` but not in DEFAULTS:
- `dosimetry.compliance_threshold` (10.0)
- `dosimetry.max_order_options` (the 3-entry array)

After this fix, `load_config(None)` and `load_config("configs/default.json")` produce identical output.

### 3. Expand SimulationConfig

Add fields to capture everything a researcher would vary between experiments. All default values import from `defaults.py`.

```python
@dataclass(frozen=True)
class TissueConfig:
    name: str = "Skin"
    frequency_hz: float = DEFAULT_FREQ_HZ

@dataclass(frozen=True)
class BodyConfig:
    name: str = "thelonious"
    mass_kg: float | None = None    # loaded from phantoms.yaml if None

@dataclass(frozen=True)
class AntennaConfig:
    positions: list[list[float]] = field(default_factory=lambda: [[5.0, 0.0, 1.0]])
    power_dbm: float = DEFAULT_POWER_DBM
    polarisation: str = "vertical"
    pattern: str = "isotropic"

@dataclass(frozen=True)
class RayTracerConfig:
    backend: str = "differt"
    max_bounces: int = DEFAULT_MAX_BOUNCES
    scene_path: str | None = None

@dataclass(frozen=True)
class DosimetryConfig:
    level: int = DEFAULT_FIDELITY_LEVEL
    spatial_averaging: bool = False
    n_paths: int = 1
    max_order: int = 0
    p_abs_max: float = DEFAULT_P_ABS_MAX

@dataclass(frozen=True)
class ChannelConfig:
    preset: str = "3GPP_38.901_UMi_LOS"
    seed: int = DEFAULT_SEED
    overrides: dict = field(default_factory=dict)

@dataclass(frozen=True)
class MIMOConfig:
    precoder: str = "mrt"
    noise_power: float = DEFAULT_NOISE_POWER
    n_rows: int = 4
    n_cols: int = 4

@dataclass(frozen=True)
class SimulationConfig:
    tissue: TissueConfig = field(default_factory=TissueConfig)
    body: BodyConfig = field(default_factory=BodyConfig)
    antenna: AntennaConfig = field(default_factory=AntennaConfig)
    raytracer: RayTracerConfig = field(default_factory=RayTracerConfig)
    dosimetry: DosimetryConfig = field(default_factory=DosimetryConfig)
    channel: ChannelConfig = field(default_factory=ChannelConfig)      # NEW
    mimo: MIMOConfig = field(default_factory=MIMOConfig)               # NEW
    output_dir: str = "outputs"
```

All sub-configs use `field(default_factory=...)` so existing YAML files without `channel` or `mimo` sections load without errors.

The `_CONFIG_CLASSES` dict must be updated to include `"channel": ChannelConfig` and `"mimo": MIMOConfig` so `from_dict()` correctly reconstructs nested dicts instead of passing raw dicts as keyword arguments.

### 4. Viewer config export

**Backend endpoint: `POST /api/export-config`**

Request body: current interactive state from the frontend (same shape as share state).

Response: complete viewer JSON config with interactive overrides applied.

Implementation in `routes/data.py` (must acquire `cache_lock` before deep-copying):

```python
@app.route("/api/export-config", methods=["POST"])
def api_export_config():
    """Return the full viewer config with interactive state overlaid."""
    with cache_lock:
        base = copy.deepcopy(cache["config"])
    interactive = request.get_json(silent=True) or {}
    # Map interactive state to config paths
    if "freqGhz" in interactive:
        base["dosimetry"]["freq_hz"] = interactive["freqGhz"] * 1e9
    if "powerDbm" in interactive:
        base["dosimetry"]["default_power_dbm"] = interactive["powerDbm"]
    if "mode" in interactive:
        base["dosimetry"]["default_level"] = _mode_to_level(interactive)
    if "nPaths" in interactive:
        base["dosimetry"]["default_n_paths"] = interactive["nPaths"]
    if "bodyName" in interactive:
        base["body"]["default_name"] = interactive["bodyName"]
    if "antennaPos" in interactive and interactive["antennaPos"]:
        base["antenna"]["default_position"] = interactive["antennaPos"]
    if "skinModel" in interactive:
        base["dosimetry"]["skin_model"] = interactive["skinModel"]
    if "bodyOffset" in interactive:
        base["body"]["default_offset"] = interactive["bodyOffset"]
    if "bodyRotationY" in interactive:
        base["body"]["default_rotation_y"] = interactive["bodyRotationY"]
    # RT config
    if "rtSource" in interactive:
        base["raytracer"]["default_source"] = interactive["rtSource"]
    if "rtMaxOrder" in interactive:
        base["dosimetry"]["default_max_order"] = interactive["rtMaxOrder"]
    if "rtConfig" in interactive:
        base["raytracer"].update(interactive["rtConfig"])
    # Stochastic channel
    if "stochasticPreset" in interactive:
        base["dosimetry"]["stochastic"]["default_preset"] = interactive["stochasticPreset"]
    if "stochasticSeed" in interactive:
        base["dosimetry"]["stochastic"]["default_seed"] = interactive["stochasticSeed"]
    # Display
    if "exposureScenario" in interactive:
        base["dosimetry"]["exposure_scenario"] = interactive["exposureScenario"]
    if "legendScale" in interactive:
        base["dosimetry"]["display_mode"] = interactive["legendScale"]
    if "dynamicRangeDb" in interactive:
        base["dosimetry"]["dynamic_range_db"] = interactive["dynamicRangeDb"]
    if "wireframe" in interactive:
        base["body"]["wireframe"] = interactive["wireframe"]
    return jsonify(base)
```

**Frontend: ExportPanel addition**

New button "Export Configuration" in `ExportPanel.tsx`. On click:

1. `collectState()` from `shareLink.ts` (reuse existing function)
2. POST to `/api/export-config` with that state
3. Download the response JSON as `aegis-config-<timestamp>.json`

The downloaded file is a valid `--config` argument: `python -m aegis.viewer --config aegis-config-2026-03-27.json`.

**New DEFAULTS keys required for round-trip**

The export endpoint writes interactive state into config paths. For the exported JSON to actually reproduce the scene on reload, these keys must exist in DEFAULTS (so they survive deep-merge) and `useConfig.ts` must read them at startup:

| Config path | Default value | Read in useConfig.ts |
|-------------|---------------|---------------------|
| `antenna.default_position` | `null` | Sets `antennaPos` if present |
| `dosimetry.skin_model` | `"itis"` | Sets `skinModel` |
| `dosimetry.dynamic_range_db` | `30` | Sets `dynamicRangeDb` |
| `dosimetry.max_order` | `0` | Sets `rtMaxOrder` via scene store |
| `body.default_offset` | `[0, 0, 0]` | Sets `bodyOffset` |
| `body.default_rotation_y` | `0` | Sets `bodyRotationY` |
| `body.wireframe` | `false` | Sets `wireframe` |
| `raytracer.default_source` | `"differt"` | Sets `rtSource` |

**Frontend: loading exported configs**

No new mechanism needed. The existing `--config` flag and deep-merge handle it. The viewer reads config values at startup in `useConfig.ts` and sets store values accordingly. The new keys listed above need corresponding reads in `useConfig.ts`.

### 5. Share URL compression

**Replace** `btoa(JSON.stringify(diff))` with `base64url(deflateRaw(JSON.stringify(diff)))`.

**New dependency**: `pako` in `aegis-web/package.json`.

**Encoding** (`shareLink.ts`):

```typescript
import pako from 'pako'

function toBase64Url(bytes: Uint8Array): string {
  let binary = ''
  for (const b of bytes) binary += String.fromCharCode(b)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function serializeShareableState(): string {
  const current = collectState()
  const diff = diffState(current)
  const json = JSON.stringify(diff)
  const compressed = pako.deflateRaw(new TextEncoder().encode(json))
  return toBase64Url(compressed)
}
```

**Decoding** (`shareLink.ts`):

```typescript
function fromBase64Url(str: string): Uint8Array {
  const padded = str.replace(/-/g, '+').replace(/_/g, '/') +
    '='.repeat((4 - str.length % 4) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

export function deserializeShareLink(encoded: string): Partial<ShareState> {
  try {
    let json: string
    try {
      // New format: deflated + base64url
      const bytes = fromBase64Url(encoded)
      json = new TextDecoder().decode(pako.inflateRaw(bytes))
    } catch {
      // Backwards compat: old plain base64 format
      json = atob(encoded)
    }
    const parsed = JSON.parse(json) as Record<string, unknown>
    const result: Record<string, unknown> = {}
    for (const key of Object.keys(SHARE_DEFAULTS)) {
      if (key in parsed) result[key] = parsed[key]
    }
    return result as Partial<ShareState>
  } catch {
    console.warn('Failed to parse share link')
    return {}
  }
}
```

Old-format URLs (`#s=<plain-base64>`) continue to work via the fallback path.

### 6. Expand share state vocabulary

Add these fields to `SHARE_DEFAULTS` so they participate in diffing (but cost zero URL bytes when unchanged):

```typescript
// New additions to SHARE_DEFAULTS
colormapName: 'inferno',           // from viewer config
sunIntensity: 1.2,                 // lighting.sun.intensity
ambientIntensity: 0.6,             // lighting.ambient.intensity
cameraFov: 55,                     // camera.fov
```

Corresponding `applyShareState` entries update the scene store when these are present. The viewer config hook needs to expose setters for these display properties.

Keep this expansion conservative. Only add fields that a colleague might meaningfully want to share. Full theme/UI customization stays export-only.

---

## Files changed

### New files
| File | Purpose |
|------|---------|
| `src/aegis/defaults.py` | Named constants for all project defaults |
| `data/phantoms.yaml` | Phantom body masses |

### Modified files (backend)
| File | Change |
|------|--------|
| `src/aegis/config.py` | Add ChannelConfig, MIMOConfig, expand DosimetryConfig, update _CONFIG_CLASSES |
| `src/aegis/viewer/config.py` | Sync DEFAULTS drift, add new round-trip keys |
| `src/aegis/viewer/routes/data.py` | Add `POST /api/export-config` endpoint |
| `src/aegis/engine.py` | Import DEFAULT_P_ABS_MAX (3 sites) |
| `src/aegis/kernels/level8_ecbf.py` | Import DEFAULT_P_ABS_MAX |
| `src/aegis/mimo/compute.py` | Import DEFAULT_P_ABS_MAX, DEFAULT_NOISE_POWER, DEFAULT_FREQ_HZ |
| `src/aegis/mimo/precoders.py` | Import DEFAULT_NOISE_POWER, NUMERICAL_FLOOR |
| `src/aegis/mimo/scene.py` | Import DEFAULT_FREQ_HZ |
| `src/aegis/precoder.py` | Import NUMERICAL_FLOOR |
| `src/aegis/coherent/ecbf.py` | Import NUMERICAL_FLOOR |
| `src/aegis/coherent/exposure_operator.py` | Import NUMERICAL_FLOOR |
| `src/aegis/coherent/body_channel.py` | Import NUMERICAL_FLOOR |
| `src/aegis/compliance/__init__.py` | Import DEFAULT_FREQ_HZ |
| `src/aegis/result.py` | Import NUMERICAL_FLOOR |
| `src/aegis/kernels/_base.py` | Import NUMERICAL_FLOOR |
| `src/aegis/geometry/occlusion.py` | Import NUMERICAL_FLOOR |
| `src/aegis/viewer/compute.py` | Import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM, load phantom masses from YAML |
| `src/aegis/viewer/raytracer.py` | Import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM |
| `src/aegis/viewer/modal_proxy.py` | Import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM |
| `src/aegis/viewer/routes/compute.py` | Import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM |
| `src/aegis/viewer/routes/mimo.py` | Import DEFAULT_FREQ_HZ |
| `src/aegis/integration/differt.py` | Import CONCRETE_EPS_R, CONCRETE_SIGMA, DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM |
| `src/aegis/integration/sionna.py` | Import DEFAULT_SEED, DEFAULT_POWER_DBM |
| `src/aegis/modal_rt/differt_tracer.py` | Import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM |
| `src/aegis/modal_rt/sionna_tracer.py` | Import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM |
| `src/aegis/channel/generator.py` | Import DEFAULT_SEED, NUMERICAL_FLOOR |
| `src/aegis/channel/presets.py` | Import DEFAULT_FREQ_HZ |
| `src/aegis/viz/dashboard.py` | Import DEFAULT_FREQ_HZ, NUMERICAL_FLOOR |

### Modified files (frontend)
| File | Change |
|------|--------|
| `aegis-web/package.json` | Add `pako` dependency |
| `aegis-web/src/lib/shareLink.ts` | deflate + base64url encoding, backwards-compat decoding |
| `aegis-web/src/lib/shareDefaults.ts` | Add colormap/lighting/camera fields |
| `aegis-web/src/components/panels/ExportPanel.tsx` | Add "Export Configuration" button |
| `aegis-web/src/hooks/useConfig.ts` | Read new config keys (body offset, rotation, skin model) |
| `aegis-web/src/api/client.ts` | Add `exportConfig()` API call |

---

## Testing

- **No behavior change**: Run `pytest tests/ -m "not slow" -x` before and after. All results identical.
- **Config roundtrip**: Export config from viewer, relaunch with it, verify identical state.
- **Share URL backwards compat**: Old-format `#s=` links still decode correctly.
- **Share URL compression**: Verify shorter URLs for typical diffs.
- **SimulationConfig compat**: Existing YAML configs load without errors (new fields have defaults).
- **Phantom masses**: Verify `data/phantoms.yaml` values match the old hardcoded dict.

## Risks

- **Import cycles**: `defaults.py` is a leaf module with no imports. Safe.
- **pako bundle size**: ~12KB gzipped. Negligible for this app.
- **Config key naming**: The export endpoint maps interactive state keys (camelCase) to config keys (snake_case/nested). This mapping is explicit, not automatic. New interactive fields require updating the mapping.
- **Forward compatibility**: The current `from_dict` raises `ValueError` for unknown keys. A config saved with new fields (channel, mimo) will fail on older AEGIS versions. Expected for version upgrades.
- **Thread safety**: The export endpoint must acquire `cache_lock` before deep-copying `cache["config"]` to avoid races with concurrent requests that modify the cache.
