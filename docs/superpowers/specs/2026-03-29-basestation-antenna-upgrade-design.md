# Base station antenna visualization and MIMO integration

**Date**: 2026-03-29
**Status**: Approved
**Scope**: Replace sphere markers with realistic antenna panels, add geocoding for location input, integrate mMIMO beamforming for 5G base stations

## Problem

Base stations in the viewer render as colored spheres on tall poles. The data has rich antenna metadata (gain, beamwidth, azimuth, tilt, frequency, radiation patterns) that goes unused visually. The base station loading UI requires raw lat/lon coordinates instead of accepting location names. And 5G mMIMO antennas are treated identically to legacy 2G sector panels despite having fundamentally different radiation behavior.

## Goals

1. Render base station antennas as oriented panel models with visible element grids, classified by archetype (mMIMO, sector, small cell).
2. Accept free-text location input for base station loading (geocoded via geopy), with a checkbox to auto-load base stations when loading a scene.
3. Compute coherent beamformed dosimetry (MRT) for mMIMO base stations, incoherent fixed-pattern dosimetry for everything else.
4. All classification thresholds and visual parameters live in config JSON, not hardcoded.

## Non-goals

- Full multi-user MIMO (multiple UEs served simultaneously). Single-user MRT toward the body only.
- Cross-polarization modeling. Patterns remain scalar gain.
- Replacing the existing single-antenna MIMO mode. Base station MIMO is a separate path.
- Real-time pattern updates as the user moves. Recompute is on-demand.

---

## Design

### 1. Archetype classification

A classifier function (implemented in both Python and TypeScript) maps antenna metadata to one of three archetypes. Thresholds and element gain are configurable.

**Inputs**: `gain_dbi`, `horizontal_beamwidth_deg`, `vertical_beamwidth_deg`, `freq_mhz`, `technology`

**Classification rules** (evaluated in order):

1. `mmimo`: gain >= `mmimo_gain_threshold` (default 20.0) AND technology contains "5G"
2. `small_cell`: gain < `small_cell_gain_threshold` (default 10.0)
3. `sector`: everything else

When technology is null, empty, or unrecognized, the classifier treats it as non-5G (so mmimo is never assigned). This is conservative: an unknown antenna gets sector treatment rather than being assumed to beamform.

**Element count inference**:

Array gain is estimated as `gain_dbi - element_gain_dbi` (default element gain: 5.0 dBi for a patch). Raw element count: `N_raw = 10^(array_gain / 10)`. This raw value is then snapped to the nearest standard grid from a lookup table:

Standard grids (configurable):
- mMIMO: [4x4, 4x8, 8x8, 8x16] (16, 32, 64, 128 elements)
- sector: [1x2, 1x4, 2x4, 2x8] (2, 4, 8, 16 elements)
- small_cell: [1x1, 2x2] (1, 4 elements)

Grid notation is N_h x N_v (columns x rows). For mMIMO panels, N_v >= N_h because the narrow elevation beam requires vertical stacking while the broad azimuth coverage comes from digital beamforming, not physical array width. For sector panels, N_h is fixed at 1 or 2 (cross-pol columns) with variable vertical stacking.

With the default element_gain_dbi=5.0:
- 24.9 dBi (Brussels 5G 3600 MHz): N_raw=98, snaps to 8x16 (128). With element_gain_dbi=7.0: N_raw=62, snaps to 8x8 (64). The default element gain is tunable per deployment.
- 15.0 dBi (typical sector): N_raw=10, snaps to 2x4 (8) or 2x8 (16) depending on rounding.
- 2.1 dBi: N_raw < 1, snaps to 1x1.

**Panel physical dimensions**:

Panel size is derived from element count and half-wavelength spacing at the antenna's frequency:

```
lambda = c / freq_hz
spacing = lambda / 2
panel_width = (N_h - 1) * spacing + margin
panel_height = (N_v - 1) * spacing + margin
```

When frequency is missing or zero, the config fallback dimensions are used (`default_panel_width`, `default_panel_height` per archetype). Element count inference still runs using a default frequency of 2100 MHz (mid-band).

### 2. Config schema

Added to `configs/default.json` under a new `basestations` key:

```json
{
  "basestations": {
    "classification": {
      "element_gain_dbi": 5.0,
      "mmimo_gain_threshold": 20.0,
      "small_cell_gain_threshold": 10.0,
      "default_freq_mhz": 2100,
      "standard_grids": {
        "mmimo": [[4,4],[4,8],[8,8],[8,16]],
        "sector": [[1,2],[1,4],[2,4],[2,8]],
        "small_cell": [[1,1],[2,2]]
      }
    },
    "panel": {
      "depth": 0.05,
      "pole_radius": 0.04,
      "element_dot_radius": 0.008,
      "show_elements": true,
      "margin": 0.02
    },
    "mmimo": {
      "default_panel_width": 0.7,
      "default_panel_height": 0.4,
      "show_pattern": true,
      "ico_detail": 6,
      "pattern_opacity": 0.85,
      "dynamic_range_db": 36
    },
    "sector": {
      "default_panel_width": 0.3,
      "default_panel_height": 1.0,
      "show_pattern": false
    },
    "small_cell": {
      "default_panel_width": 0.15,
      "default_panel_height": 0.15,
      "show_pattern": false
    },
    "auto_load_with_scene": false,
    "default_radius_m": 500,
    "max_distance_m": 2000,
    "site_vertical_gap": 0.1
  }
}
```

### 3. Visual components

**New: `PanelAntenna.tsx`**

Shared component rendering a rectangular antenna panel:

Props:
- `nH`, `nV`: element grid dimensions
- `panelWidth`, `panelHeight`: physical size in meters
- `depth`: panel thickness
- `azimuthDeg`, `tiltDeg`: orientation (compass bearing, downtilt)
- `position`: [x, y, z] in scene coordinates
- `color`: panel face color (operator-based)
- `showElements`: render element dots on panel face
- `showPattern`: render radiation pattern mesh
- `patternData`: optional array factor weights or radiation pattern for the mesh
- `config`: panel config from viewer config

Rendering:
- Box geometry for the panel body, oriented by azimuth (Y-rotation) and tilt (local X-rotation)
- Element dots as instanced small circles on the front face, positioned in the N_h x N_v grid
- Support pole (cylinder) from ground to panel bottom
- Optional radiation pattern mesh (icosahedron with vertex coloring, same technique as AntennaArray)

**Modified: `BaseStationMarkers.tsx`**

Complete rewrite. Instead of two InstancedMesh objects (poles + spheres):

- Groups base stations by `site_code`
- Within each site, sorts antennas by azimuth then frequency
- Renders one shared pole per site (height = max antenna height at that site)
- Renders a `PanelAntenna` per antenna, vertically stacked within each azimuth group
- Vertical offset: `site_vertical_gap` from config between stacked panels
- Operator coloring applied to panel face color (same color map as current)
- Click handler on each panel for selection (mMIMO beam computation)

Performance: sector and small_cell panels with identical dimensions share geometry across the full scene via a geometry cache keyed by (N_h, N_v, panel_width, panel_height). With ~540 sector antennas each having 2x4=8 element dots, the geometry cache avoids creating 4320 individual circle meshes. mMIMO panels (~80) are individual meshes since they need per-antenna interaction and pattern rendering.

**Co-located operators**: Different operators sharing a physical site have different `site_code` values at nearly identical coordinates. The current design renders separate poles. This is a known limitation. A future improvement could spatially cluster poles within a configurable radius, but for now the visual overlap at shared sites is acceptable since poles are thin.

**Modified: `AntennaArray.tsx`**

Extracts its backplane + element rendering into PanelAntenna. The array factor computation, precoder weight application, and beam pattern visualization stay in AntennaArray but delegate the physical panel rendering to PanelAntenna.

### 4. Geocoding and loading

**Backend: geopy integration**

New function in `src/aegis/viewer/routes/basestations.py`:

```python
def geocode_location(location: str) -> tuple[float, float]:
    # Try parsing as "lat, lon" first (regex for two floats separated by comma)
    # Fall back to geopy Nominatim geocoder (user_agent="aegis-viewer")
    # Return (latitude, longitude)
    # Raises ValueError with descriptive message on failure
```

The `/api/basestations/load` endpoint gains a `location` parameter. Priority order: `bbox` > `lat/lon` > `location` (geocoded). When geocoding fails (no results, network error, rate limit), the endpoint returns HTTP 400 with an error message. The frontend shows this in the base station panel status area.

Request format with location:
```json
{
  "location": "Brussels, Belgium",
  "radius_m": 500,
  "operator": "Proximus",
  "technology": "5G"
}
```

Existing `bbox` and `lat/lon` parameters continue to work as direct overrides. If both `location` and `bbox` are provided, `bbox` wins.

**Dependency**: `geopy` added to `[viewer]` extra in `pyproject.toml`.

**Frontend: ScenePanel.tsx**

The scene loading section gets a checkbox "Also load base stations" (default from `basestations.auto_load_with_scene` config). When checked and a scene loads successfully, triggers base station loading for the same location string with `basestations.default_radius_m`.

**Frontend: BaseStationPanel.tsx**

The lat/lon coordinate inputs are replaced with a single text input accepting any location string. A radius input remains. Pre-filled from the scene location when one exists.

### 5. Archetype response format

The `/api/basestations/load` response gains per-antenna classification data:

```json
{
  "basestations": [
    {
      "site_code": "SITE(02OMM)",
      "antenna_label": "ANT(BROMM21D351P)",
      "operator": "Proximus",
      "technology": "5G",
      "latitude": 50.853,
      "longitude": 4.359,
      "height_m": 29.67,
      "eirp_dbm": 36.8,
      "gain_dbi": 24.8,
      "freq_mhz": 3750.0,
      "azimuth_deg": 150,
      "total_tilt_deg": -6,
      "horizontal_beamwidth_deg": 126,
      "vertical_beamwidth_deg": 34,
      "has_pattern": true,
      "archetype": "mmimo",
      "inferred_n_h": 8,
      "inferred_n_v": 8,
      "panel_width_m": 0.32,
      "panel_height_m": 0.32
    }
  ]
}
```

The classification runs in the Python adapter during loading. The frontend receives pre-classified data and renders accordingly.

### 6. MIMO computation for base stations

**New route: `/api/basestations/compute_mimo` [POST]**

For mMIMO-classified base stations:

```json
{
  "index": 42,
  "body_offset": [0, 0, 0],
  "body_rotation_y": 0,
  "use_beamforming": true
}
```

Flow:
1. Look up the base station by index
2. Build ArrayConfig from inferred N_h, N_v, half-wavelength spacing at the antenna's frequency
3. Position the array at the base station's scene coordinates, oriented by azimuth and tilt
4. Compute MRT precoder weights steered toward body center
5. Run coherent dosimetry (level 7) with the precoder
6. Return SAB array + stats (same format as `/api/dosimetry`)

For sector/small_cell antennas, the existing `/api/basestations/compute` path handles computation with fixed patterns and incoherent levels. The `use_beamforming` parameter accepts `true`, `false`, or `"auto"` (default). In auto mode, beamforming activates only for mmimo-classified antennas. The `max_distance_m` parameter (default from config) filters out base stations too far from the body, same as the existing compute route.

**Measured patterns and mMIMO**: When a mMIMO antenna has a measured radiation pattern from the .mat file, the measured pattern represents the passive antenna element pattern (before digital beamforming). The MIMO compute route uses it as the element pattern in the array factor calculation, replacing the default patch model. For antennas without measured patterns, the synthetic patch element (5 dBi, cos^1.5 rolloff) is used.

**Frontend: selected antenna interaction**

Clicking a base station panel in the 3D scene selects it. For mMIMO panels:
- Renders array factor beam pattern mesh on the panel
- Triggers dosimetry computation via the MIMO route
- Shows beam direction indicator (arrow from panel toward body)

For sector/small_cell:
- Highlights the selected panel
- Triggers standard dosimetry computation
- No beam pattern mesh

### 7. Store changes

**`useBaseStationsStore` additions**:
- `selectedIndex: number | null` -- currently selected base station
- `archetypes: Map<number, ArchetypeInfo>` -- classification results (redundant with response data, but convenient for rendering)
- `selectAntenna(index)` / `deselectAntenna()` actions
- `computeForSelected()` -- dispatches to correct compute endpoint based on archetype

### 8. File change summary

| File | Change |
|---|---|
| `aegis-web/src/components/scene/PanelAntenna.tsx` | New shared panel component |
| `aegis-web/src/components/scene/BaseStationMarkers.tsx` | Rewrite with PanelAntenna, site grouping |
| `aegis-web/src/components/scene/AntennaArray.tsx` | Extract panel rendering to PanelAntenna |
| `aegis-web/src/utils/classifyAntenna.ts` | New archetype classifier |
| `aegis-web/src/api/types.ts` | Add archetype fields to BaseStationData |
| `aegis-web/src/components/panels/ScenePanel.tsx` | Add "Also load base stations" checkbox |
| `aegis-web/src/components/panels/BaseStationPanel.tsx` | Replace lat/lon inputs with text location input |
| `aegis-web/src/stores/basestations.ts` | Add archetype, selection, compute dispatch |
| `src/aegis/basestation/classify.py` | New Python archetype classifier |
| `src/aegis/basestation/adapter.py` | Integrate classification into loading, add archetype fields to serialization |
| `src/aegis/viewer/routes/basestations.py` | Geocoding, archetype fields in `_bs_summary()`, MIMO compute route |
| `configs/default.json` | Add basestations config block |
| `pyproject.toml` | Add geopy to [viewer] extra |
| `tests/test_classify_antenna.py` | Unit tests for classifier |

### 9. Testing

- **Unit tests for classifier**: verify archetype assignment and element count inference for known Brussels data points (the 24.9 dBi 3600 MHz antenna should classify as mmimo 8x8, the 15 dBi 900 MHz as sector 2x4, the 2.1 dBi as small_cell 1x1).
- **Geocoding tests**: mock geopy, verify "Brussels" resolves, verify "50.85, 4.35" parses as raw coordinates.
- **Integration test**: load Brussels CSV, classify all 626 antennas, verify ~80 mmimo + ~540 sector + ~6 small_cell (based on data analysis).
- **Visual regression**: manual check in the viewer that panels render at correct orientations and stack properly on multi-antenna sites.
