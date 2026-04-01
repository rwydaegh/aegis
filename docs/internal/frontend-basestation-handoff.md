# Frontend base station handoff

Context for a future "beautiful frontend" redesign session. Written after Task 11 of the base station master dataset plan (provenance tracking + minimal frontend wiring).

---

## 1. Current state

The following was implemented in this session:

**Provenance-colored 3D antenna icons.** `BaseStationMarkers.tsx` colors each `PanelAntenna` by its `confidence` score when the field is present and non-zero. The four tiers are: green (>0.7), yellow (>0.4), orange (>0.2), red (<=0.2). If `confidence` is absent or zero (CSV-backed data), the marker falls back to operator color.

**Frequency band filter.** The Zustand store now carries `frequencyBands: string[]`, `enabledFrequencyBands: Set<string>`, and `toggleFrequencyBand(band)`. `BaseStationsPanel` renders a checkbox list for each band. The filter logic is consistent with the existing operator/technology filters: a band-less antenna is never excluded, only antennas that have a `frequency_band` field that is not in the enabled set get hidden.

**Antenna detail panel.** `AntennaDetailPanel.tsx` appears below the filters whenever an antenna is selected (click on a 3D marker). It shows a grid of key fields (EIRP, azimuth, height, frequency, gain, beamwidths, tilts), each with a `ProvenanceDot` beside it when per-field provenance is available. It also shows the `pattern_source` string and an overall confidence percentage.

**ProvenanceDot component.** `ProvenanceDot.tsx` is a tiny inline colored circle with a `title` tooltip. The `confidenceColor` helper is exported so other components can use the same color scale.

**Confidence legend.** A four-dot inline legend (Gov / Mixed / Est. / Low) is rendered inside `BaseStationsPanel` below the frequency band filter section.

**What did not change.** The `PanelAntenna.tsx` 3D shape itself was unchanged - it already existed. The `computeExposure` button, the CloudRF coverage toggle, load/clear controls, and the operator/technology filters all predate this session.

---

## 2. API contract

Both `/api/basestations/load` (POST) and `/api/basestations/list` (GET) return the same shape:

```json
{
  "count": 47,
  "basestations": [
    {
      "site_code": "BEL-PRX-ANT-00123",
      "antenna_label": "ANT-00123-A",
      "operator": "Proximus",
      "technology": "NR",
      "latitude": 50.8503,
      "longitude": 4.3517,
      "height_m": 30.0,
      "eirp_dbm": 65.2,
      "gain_dbi": 18.0,
      "freq_mhz": 3500.0,
      "azimuth_deg": 120.0,
      "total_tilt_deg": 4.0,
      "has_pattern": true,
      "horizontal_beamwidth_deg": 65.0,
      "vertical_beamwidth_deg": 6.5,
      "frequency_band": "n78",
      "pattern_source": "gov:bipt:2024",
      "confidence": 0.82,
      "provenance": {
        "eirp_dbm": { "origin": "gov:bipt", "confidence": 0.9 },
        "azimuth_deg": { "origin": "gov:bipt", "confidence": 0.85 },
        "height_m": { "origin": "gov:bipt", "confidence": 0.95 },
        "gain_dbi": { "origin": "estimated:typical", "confidence": 0.5 },
        "electrical_tilt_deg": { "origin": "estimated:typical", "confidence": 0.4 },
        "mechanical_tilt_deg": { "origin": "gov:bipt", "confidence": 0.8 },
        "horizontal_beamwidth_deg": { "origin": "estimated:pattern_fit", "confidence": 0.6 },
        "vertical_beamwidth_deg": { "origin": "estimated:pattern_fit", "confidence": 0.6 }
      },
      "archetype": "mmimo",
      "n_h": 8,
      "n_v": 8,
      "panel_width_m": 0.34,
      "panel_height_m": 0.34,
      "duplex_mode": "tdd",
      "tdd_dl_ratio": 0.75,
      "power_reduction_factor": 0.32,
      "traffic_load_factor": 0.5
    }
  ]
}
```

Notes on optionality:
- `frequency_band`, `pattern_source`, `confidence`, `provenance` are all absent (not null) for CSV-backed records that have no provenance tracking.
- `provenance` keys match the field names used in `FIELD_LABELS` in `AntennaDetailPanel.tsx`. The detail panel iterates that fixed list; provenance keys outside it are silently ignored.
- `archetype` is one of `"mmimo"`, `"sector"`, or `"small_cell"`.
- The `duplex_mode`, `tdd_dl_ratio`, `power_reduction_factor`, `traffic_load_factor` fields come from classification and are serialized in `_bs_summary()`. They are present in the JSON but the frontend currently ignores them.

Source: `src/aegis/viewer/routes/basestations.py`, function `_bs_summary()`.

---

## 3. Zustand store shape

File: `aegis-web/src/stores/basestations.ts`

```ts
interface BaseStationsState {
  // Raw data
  basestations: BaseStationData[]
  origin: { lat: number; lon: number } | null

  // Loading state
  isLoading: boolean
  isComputing: boolean

  // Filter options (derived from basestations on load)
  operators: string[]
  technologies: string[]
  frequencyBands: string[]            // only non-null frequency_band values

  // Filter state (all-enabled on load)
  enabledOperators: Set<string>
  enabledTechnologies: Set<string>
  enabledFrequencyBands: Set<string>
  activeCount: number                 // recomputed on every toggle

  // Selection
  selectedIndex: number | null
  selectAntenna: (index: number | null) => void

  // Coverage overlay (CloudRF)
  showCoverage: boolean
  coverageUrl: string | null          // blob URL created from /api/environment/coverage
  setShowCoverage: (show: boolean) => void
  setCoverageUrl: (url: string | null) => void

  // Actions
  setBasestations: (bs: BaseStationData[], origin: { lat: number; lon: number }) => void
  toggleOperator: (op: string) => void
  toggleTechnology: (tech: string) => void
  toggleFrequencyBand: (band: string) => void
  setLoading: (v: boolean) => void
  setComputing: (v: boolean) => void
  clear: () => void

  // Derived
  activeIndices: () => number[]       // indices passing all three filters
}
```

Filter semantics: `activeIndices()` excludes an antenna if:
1. Its `operator` is not in `enabledOperators`, or
2. Its `technology` is not in `enabledTechnologies`, or
3. It has a `frequency_band` AND `enabledFrequencyBands.size > 0` AND the band is not enabled.

Antennas without a `frequency_band` are never excluded by the band filter.

---

## 4. Component tree

```
BaseStationsPanel          aegis-web/src/components/panels/BaseStationsPanel.tsx
  AntennaDetailPanel       aegis-web/src/components/panels/AntennaDetailPanel.tsx
    ProvenanceDot          aegis-web/src/components/panels/ProvenanceDot.tsx

BaseStationMarkers         aegis-web/src/components/scene/BaseStationMarkers.tsx
  PanelAntenna             aegis-web/src/components/scene/PanelAntenna.tsx

useBaseStationsStore       aegis-web/src/stores/basestations.ts
BaseStationData            aegis-web/src/api/basestations.ts
```

How they connect:

- `BaseStationsPanel` lives in the sidebar. It owns the load/clear controls, filter checkboxes, and the "Compute exposure" button. It renders `AntennaDetailPanel` at the bottom (which self-hides when nothing is selected).
- `BaseStationMarkers` is mounted inside the R3F `<Canvas>` scene. It reads the same store and renders one `PanelAntenna` per visible antenna, colored by confidence or operator.
- Clicking a `PanelAntenna` calls `selectAntenna(index)` on the store. `AntennaDetailPanel` reads `selectedIndex` and renders accordingly.
- `ProvenanceDot` is a pure display component with no store access. It receives `confidence` and optional `title` as props.
- The `confidenceColor` function is defined in both `ProvenanceDot.tsx` (exported) and duplicated inline in `BaseStationMarkers.tsx`. This should be consolidated in the beautiful session.

---

## 5. What is missing (deferred to the beautiful session)

The items below were explicitly scoped out. The data is available in the API; the work is purely frontend.

**Data source legend/attribution panel.** The `origin` strings in `provenance` (e.g. `"gov:bipt"`, `"estimated:typical"`, `"estimated:pattern_fit"`) need a human-readable legend explaining what each source is and how much to trust it. Currently only the four confidence tiers are labeled.

**Coverage overlay showing which source covers which area.** The store has `showCoverage`/`coverageUrl` plumbing. The CloudRF overlay is hooked up but only shows a circle for the first loaded antenna. A proper overlay would show per-source coverage footprints on a map.

**Per-source confidence histogram or summary.** Aggregate statistics about data quality across the loaded dataset: how many antennas are fully government-sourced vs. partially estimated vs. low-confidence.

**Antenna comparison view.** Ability to select two antennas and see their key parameters side by side. Useful when multiple antennas share a site.

**Map-level data quality heatmap.** Overlay the 3D scene with a color field representing average confidence in each area, so spatial gaps in data quality are visible at a glance.

**Interactive estimation explanation.** When hovering or clicking a ProvenanceDot, explain in plain language why the value was estimated (e.g. "Gain not in government data; estimated from antenna archetype (mMIMO) and frequency band").

**Radiation pattern 3D visualization.** The `has_pattern` flag and `pattern_source` field are already in the API. When `has_pattern` is true, the 3D viewer could render the antenna's beam pattern as a translucent 3D lobe around the PanelAntenna marker.

**Better mobile responsiveness.** The base station panel is wide-card style and was designed for desktop. The filter lists stack awkwardly on small screens.

**Animated transitions when switching between antennas.** The detail panel snaps on/off. A slide or fade transition when `selectedIndex` changes would feel more polished.

**Use the unused classification fields.** `duplex_mode`, `tdd_dl_ratio`, `power_reduction_factor`, `traffic_load_factor` are present in every API response but nothing in the frontend displays them. The detail panel could show effective load factor or TDD split.

**Consolidate `confidenceColor`.** The function is defined twice (ProvenanceDot.tsx and BaseStationMarkers.tsx). Move to a shared util.

---

## 6. Design constraints

The existing tech stack to follow:

- **React + TypeScript** throughout. No class components.
- **Zustand** for all shared state. No React context or prop drilling for global state.
- **R3F (React Three Fiber)** for the 3D scene. `PanelAntenna` and `BaseStationMarkers` must remain R3F components.
- **Tailwind CSS** for all styling. No inline style objects except where Three.js/canvas requires it. Use design tokens (`text-foreground`, `bg-muted`, `border-border`, `text-primary`) for dark-mode compatibility - never hardcode colors in Tailwind classes.
- **Color conventions.** The existing confidence color scale (green/yellow/orange/red at 0.7/0.4/0.2 breakpoints) should be preserved and extended, not replaced.
- **No new state management libraries.** Zustand is the only store layer. If a component needs derived state, compute it inside `create()` or with `useMemo` in the component.
- **API shape is fixed.** Backend changes require a separate backend session. The frontend must work within the contract in section 2.
- **Existing panel layout.** The sidebar panel structure is managed by the parent shell. `BaseStationsPanel` renders its content as a plain `<div>` with no fixed height or scroll. Adding tall components (histograms, legends) may require adding a scroll container.
- **Three.js coordinate system.** Y-up, north is -Z. See `bsToScenePos` in `BaseStationMarkers.tsx` for the lat/lon to scene-position conversion. Any new 3D overlays must use the same origin and projection.
