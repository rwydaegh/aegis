# Compliance overhaul and spatial averaging design

## Problem

The AEGIS compliance module has critical bugs and is missing major features needed
for proper ICNIRP 2020 exposure assessment.

**Bugs:**

- S_ab basic restriction limit is hardcoded as 10 W/m² (this is the S_inc reference
  level from Table 5). The correct S_ab basic restriction from Table 2 is 20 W/m²
  for general public, 100 W/m² for occupational.
- Compliance is checked against raw per-triangle peak S_ab, not spatially averaged
  S_ab. ICNIRP requires spatial averaging over 4 cm².
- Inconsistent comparison operators: `<` in result.py and viewer code, `<=` in
  compliance helpers.
- Spatial averaging is disabled by default and never enabled in the viewer pipeline.
- Comment says "Table 5" but Table 5 is reference levels, not basic restrictions.

**Missing features:**

- No reference level (S_inc) compliance assessment.
- No occupational exposure scenario (only general public).
- No frequency-dependent limits (Table 6 local reference levels depend on frequency).
- No 1 cm² averaging constraint for >30 GHz.
- No S_inc computation pipeline.
- No frequency field in the frontend.
- Single PASS/FAIL badge conflating all compliance checks.
- No compliance margin or power headroom display.
- No compliance ratio visualization.

## Source of truth

ICNIRP 2020 guidelines: `theory/ICNIRPrfgdl2020.pdf` in this repository.

Key tables:

- **Table 2**: basic restrictions (S_ab, SAR) for averaging intervals >= 6 min
- **Table 3**: basic restrictions (U_ab) for brief exposures < 6 min
- **Table 5**: reference levels, whole-body average, >= 6 min
- **Table 6**: reference levels, local, 6 min

## Features

### F1. Compliance module rewrite

Replace the existing flat compliance module with a proper data model.

**Exposure scenarios:**

| Scenario | S_ab 4 cm² | S_ab 1 cm² (>30 GHz) | SAR_wb | S_inc local (Table 6) | S_inc whole-body (Table 5) |
|----------|-----------|----------------------|--------|----------------------|--------------------------|
| General public | 20 W/m² | 40 W/m² | 0.08 W/kg | 55/f_G^0.177 W/m² | 10 W/m² |
| Occupational | 100 W/m² | 200 W/m² | 0.4 W/kg | 275/f_G^0.177 W/m² | 50 W/m² |

Where f_G is frequency in GHz. The 1 cm² limits are 2x the 4 cm² basic restriction
per Table 2 note 5 and only apply above 30 GHz. The Table 6 local S_inc formulas
are valid for >6 GHz to 300 GHz.

**Supported frequency range:** >6 GHz to 300 GHz. Below 6 GHz, different quantities
apply (SAR over 10-g mass rather than S_ab). The compliance module raises
ValueError for frequencies outside this range.

**Data model:**

```
ExposureScenario: enum (GENERAL_PUBLIC, OCCUPATIONAL)

ICNIRPLimits:
    scenario: ExposureScenario
    freq_hz: float
    -> sab_4cm2: float         (Table 2)
    -> sab_1cm2: float | None  (Table 2 note 5, only >30 GHz)
    -> sar_wb: float            (Table 2)
    -> sinc_local: float        (Table 6, frequency-dependent)
    -> sinc_whole_body: float   (Table 5)

ComplianceResult:
    scenario: ExposureScenario
    freq_hz: float
    # Basic restrictions
    sab_4cm2_value: float
    sab_4cm2_limit: float
    sab_4cm2_pass: bool
    sab_1cm2_value: float | None  (only >30 GHz)
    sab_1cm2_limit: float | None
    sab_1cm2_pass: bool | None
    sar_wb_value: float | None
    sar_wb_limit: float
    sar_wb_pass: bool | None
    # Reference levels
    sinc_local_value: float
    sinc_local_limit: float
    sinc_local_pass: bool
    sinc_whole_body_value: float | None
    sinc_whole_body_limit: float
    sinc_whole_body_pass: bool | None
    # Derived
    overall_pass: bool  (all checks pass)
    margin_db: float    (min margin across all checks: 10*log10(limit/value))
    # Power headroom
    tx_power_dbm: float | None  (from engine input or config)
    max_compliant_power_dbm: float | None  (tx_power_dbm + margin_db)
```

All comparison operators use `<=` (value at the limit is compliant). This explicitly
fixes the `<` operators in `result.py` lines 99 and 109, `viewer/routes/compute.py`
line 46, `viewer/compute.py` line 220, and `viz/dashboard.py` lines 110 and 115.

### F2. S_inc computation pipeline

Compute incident power density at each body triangle, without absorption physics.

**Physical definition:** S_inc is the power density of the incident electromagnetic
field at the body surface location, measured as if the body were absent (free-space
quantity). For a single plane wave, S_inc = |E|^2 / (2 * eta_0). It does not depend
on surface orientation, tissue properties, or Fresnel reflection.

**Relation to S_ab:** In the AEGIS equation S_ab = S_inc * T0 * ReLU[n . (-k)],
the per-ray S_inc is the factor before T0 and the geometric projection. To compute
S_inc per triangle, sum the per-ray incident power densities for all rays associated
with that triangle:

```
# Per-ray contribution (already exists in the kernel as the pre-T0 quantity)
sinc_ray = paths.power[i]  # incident power density of ray i [W/m^2]

# Per-triangle S_inc (sum over all rays hitting triangle j)
sinc[j] = sum(sinc_ray for all rays i hitting triangle j)
```

No T0 (Fresnel), no ReLU (cosine projection), no cos(theta). Rays arriving from
behind the surface (cos < 0) still contribute to S_inc because the incident field
exists regardless of surface orientation.

**Coherent levels (7-8):** S_inc uses the same superposition mode as S_ab. For
coherent computation, S_inc = |sum(psi_i)|^2 / eta_0, where psi_i are the complex
field amplitudes. The difference from S_ab is only the absence of T0 and cos(theta)
factors.

**Spatial averaging for reference levels:** ICNIRP Table 6 note 6 specifies that
for >6 GHz, S_inc compliance is evaluated "averaged over a square 4-cm^2 projected
body surface space." So S_inc is spatially averaged using the same matrix G as S_ab.

**Whole-body S_inc:** Area-weighted average over the entire body surface:
sinc_whole_body = sum(sinc[j] * area[j]) / sum(area[j]). Compared against Table 5
limits (10 W/m^2 general public, 50 W/m^2 occupational).

**Local S_inc:** Peak of the spatially-averaged S_inc array (G @ sinc).max().
Compared against Table 6 frequency-dependent limits.

The S_inc array has the same shape as S_ab (M,) and lives on DosimetryResult as a
new field `sinc`. The spatially-averaged version is `sinc_averaged`.

### F3. Precomputed averaging matrix G

Replace the current iterative KD-tree averaging with a precomputed sparse matrix.

```
G = precompute_averaging_matrix(body, target_area_m2=4e-4) -> scipy.sparse.csr_array
```

- G is (M, M), sparse, row-stochastic (rows sum to 1)
- G depends only on mesh geometry (centroids, areas), not on S_ab
- Compute once per body mesh, cache on the DosimetryEngine instance (engine
  persists across compute calls, BodyMesh is frozen). Invalidate when body changes.
- Apply as: sab_averaged = G @ sab (linear, differentiable)
- For JAX: convert to jax.experimental.sparse or densify for small meshes
- Also precompute G_1cm2 for the 1 cm² constraint (target_area_m2=1e-4)
- Engine compute flow: if freq > 30 GHz, compute sab_1cm2_averaged = G_1cm2 @ sab
  and store on DosimetryResult. ComplianceResult.sab_1cm2_value = max(sab_1cm2_averaged).

The current circular neighborhood approximation is used (KD-tree ball query
accumulating area). This is flagged as an approximation in results and docs.
The ICNIRP standard specifies square patches. Strict square patches are a future
enhancement.

### F4. Frequency as an explicit parameter

Add frequency as a first-class parameter throughout the system.

**Backend:**

- `DosimetryEngine.compute()` accepts `freq_hz: float` parameter
- If not provided, fall back to `tissue.freq_hz` (current implicit behavior)
- Frequency is stored on `DosimetryResult`
- Compliance limits are computed from the frequency

**Frontend:**

- Frequency input field in the parameters panel (in GHz, with common presets:
  3.5, 28, 39, 60)
- When tissue is selected, frequency auto-fills from tissue preset but can be
  overridden
- Frequency is sent with compute requests and displayed in the HUD

**Config:**

- Default frequency in config JSON (default: 28.0 GHz)

### F5. Five heatmap display modes

Add a display mode selector for body mesh coloring.

| Mode | Quantity | Unit | Use case |
|------|----------|------|----------|
| Raw S_ab | per-triangle absorbed power density | W/m² | Fine spatial detail |
| Averaged S_ab | spatially averaged over 4 cm² | W/m² | Regulatory basic restriction |
| S_inc | incident power density | W/m² | Reference level assessment |
| Compliance ratio (S_ab) | S_ab_avg / S_ab_limit | dimensionless | Intuitive compliance view |
| Compliance ratio (S_inc) | S_inc_avg / S_inc_limit | dimensionless | Reference level proximity |

For compliance ratio modes, the color scale is fixed and universal:
- Green: 0 to 0.5 (plenty of margin)
- Yellow: 0.5 to 0.8 (moderate margin)
- Orange: 0.8 to 1.0 (close to limit)
- Red: > 1.0 (exceeding limit)

The existing linear/dB toggle applies to modes 1-3. Compliance ratio modes always
use a linear 0-2 scale (since they are already normalized).

**Frontend state:**

```
displayMode: 'raw_sab' | 'avg_sab' | 'sinc' | 'ratio_sab' | 'ratio_sinc'
```

**Backend API:**

The compute response returns all arrays needed:
- `sab_bytes`: raw S_ab (exists)
- `sab_averaged_bytes`: spatially averaged S_ab (new)
- `sinc_bytes`: incident power density (new)

Compliance ratios are computed client-side (divide by limit from compliance result).

### F6. Compliance panel in HUD

Replace the single PASS/FAIL badge with a structured compliance panel.

**Layout:**

```
COMPLIANCE (ICNIRP 2020)            [General Public ▾]

BASIC RESTRICTIONS
  S_ab (4 cm²)     12.3 / 20 W/m²      PASS  [====----]
  S_ab (1 cm²)     n/a (< 30 GHz)
  SAR_wb            0.012 / 0.08 W/kg   PASS  [=-------]

REFERENCE LEVELS
  S_inc (local)     25.8 / 31.0 W/m²    WARN  [=======-]
  S_inc (whole)     4.2 / 10 W/m²       PASS  [===-----]

Margin             +2.1 dB
Max compliant P    25.1 dBm  (at 23 dBm TX)
Frequency          28.0 GHz
```

States: PASS (green, value <= limit), WARN (yellow, value > 80% of limit but
<= limit), FAIL (red, value > limit). WARN is purely visual, not a compliance
category. ICNIRP only defines compliant/non-compliant.

The scenario selector (General Public / Occupational) updates all limits and
re-evaluates compliance immediately.

Power headroom = minimum margin across all checks, in dB.
Max compliant P = current P_tx + power headroom.

### F7. Peak location indicator

Show where on the body the peak spatially-averaged S_ab occurs.

- A small glowing marker (sphere or ring) placed at the centroid of the triangle
  with the highest spatially-averaged S_ab
- Always visible regardless of heatmap mode
- Togglable (on by default)
- Updates when computation results change

### F8. Compliance report export

Generate a structured compliance report.

**JSON format** returned from a new API endpoint `/api/compliance/report`:

```json
{
  "icnirp_version": "2020",
  "scenario": "general_public",
  "freq_hz": 28e9,
  "spatial_averaging": {
    "method": "circular_neighborhood_kdtree",
    "target_area_m2": 4e-4,
    "note": "Circular approximation. ICNIRP specifies square 4 cm^2 patches."
  },
  "basic_restrictions": {
    "sab_4cm2": {"value": 12.3, "limit": 20.0, "unit": "W/m^2", "pass": true},
    "sab_1cm2": null,
    "sar_wb": {"value": 0.012, "limit": 0.08, "unit": "W/kg", "pass": true}
  },
  "reference_levels": {
    "sinc_local": {"value": 25.8, "limit": 31.0, "unit": "W/m^2", "pass": true},
    "sinc_whole_body": {"value": 4.2, "limit": 10.0, "unit": "W/m^2", "pass": true}
  },
  "overall_pass": true,
  "margin_db": 2.1,
  "peak_location": [0.12, 0.45, 1.23],
  "tx_power_dbm": 23.0,
  "max_compliant_power_dbm": 25.1
}
```

**Human-readable text** via `compliance.summary_text()` (existing function, extended).

### F9. Differentiable optimization target

With G precomputed, the ECBF solver and any optimization can target the actual
regulatory metric:

```python
# Before (optimizes raw peak, not regulatory quantity)
loss = jnp.max(sab)

# After (optimizes against spatially-averaged peak)
sab_avg = G_jax @ sab
loss = jnp.max(sab_avg)
```

This requires F3 (precomputed G matrix) and a JAX-compatible sparse or dense
representation. The gradient of G @ sab with respect to sab is G^T, which is
trivially computed.

This is an enhancement to the existing coherent module, not a new module.

## Out of scope

- **Multi-frequency exposure quotient** (ICNIRP eqn 2): requires multi-frequency
  propagation paths infrastructure. Future work.
- **Strict square patches**: circular approximation is flagged. Square patches are
  a future enhancement.
- **Temporal averaging**: AEGIS computes steady-state. 6-minute averaging is
  inherently satisfied for continuous exposure.
- **Brief exposure limits** (Table 3, U_ab): requires time-domain simulation
  capability not currently in AEGIS.
- **Compliance contour lines**: visualization enhancement, can be added after
  the compliance ratio heatmap is in place.

## Affected files

**Rewrite:**
- `src/aegis/compliance/__init__.py` - full rewrite with new data model

**Modify:**
- `src/aegis/result.py` - add sinc, sinc_averaged, sab_1cm2_averaged fields, freq_hz, fix `<` to `<=` in compliance properties, update compliance to use new ComplianceResult
- `src/aegis/engine.py` - add freq_hz param, S_inc computation, always-on averaging
- `src/aegis/geometry/averaging.py` - add precompute_averaging_matrix(), keep apply_spatial_averaging() as convenience wrapper
- `src/aegis/geometry/__init__.py` - export new function
- `src/aegis/viewer/compute.py` - enable averaging, pass freq_hz, return new arrays
- `src/aegis/viewer/routes/compute.py` - return compliance result, new arrays, new endpoint
- `src/aegis/viewer/config.py` - add frequency, scenario, display_mode defaults
- `src/aegis/viewer/server.py` - register new routes
- `src/aegis/viz/dashboard.py` - update compliance display
- `src/aegis/coherent/ecbf.py` - optional: optimize against G @ sab
- `aegis-web/src/stores/simulation.ts` - add sinc, sab_averaged, compliance result
- `aegis-web/src/stores/ui.ts` - add displayMode, exposureScenario
- `aegis-web/src/components/panels/ParametersPanel.tsx` - add frequency input, scenario toggle, display mode selector
- `aegis-web/src/components/layout/HudOverlay.tsx` - compliance panel
- `aegis-web/src/components/scene/BodyMesh.tsx` - multi-mode heatmap, peak marker
- `aegis-web/src/api/types.ts` - updated DosimetryStats type

**New:**
- `tests/test_compliance_icnirp2020.py` - comprehensive compliance tests against actual ICNIRP values
- `tests/test_sinc_pipeline.py` - S_inc computation tests
- `tests/test_averaging_matrix.py` - G matrix properties (row-stochastic, sparse, shape)

**Tests to update:**
- `tests/test_compliance.py` - update for new API
- `tests/test_engine.py` - update for new fields
