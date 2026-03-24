# Frontend refactor progress

## What was done (2 commits on `refactor/frontend-foundation`)

### Commit 1: Foundation (Phases 1 + 2)

**Phase 1a: Typed ViewerConfig**
- 7 new sub-interfaces in `aegis-web/src/api/types.ts`: `AntennaConfig`, `LightingConfig`, `RadiationPatternConfig`, `VoxelConfig`, `DistanceVizConfig`, `UIConfig`, `SystemInfo`
- Added `body_name` and typed `scenes` to `Capabilities` interface
- Eliminated all 13 `as any` casts across 11 files

**Phase 1b: Nested RT config**
- 13 flat `rt*` fields in `aegis-web/src/stores/scene.ts` consolidated into `RtStoreConfig` object
- Single `setRtConfig(partial)` setter replaces 13 individual `setState` calls
- Updated `RayTracingPanel.tsx` and `useDosimetry.ts`

**Phase 1c: Simplified useDosimetry**
- `useShallow` from `zustand/react/shallow` reduces 30+ individual selectors to 2 shallow objects (`sim`, `scene`)
- Dependency arrays shrunk from 32 items to 3 (`sim`, `scene`, `exposureScenario`)

**Phase 2a: Notification system**
- New `aegis-web/src/stores/notifications.ts` store
- New `aegis-web/src/components/hud/NotificationToast.tsx` component (stacked toasts, auto-dismiss)
- Wired into `HudOverlay.tsx`
- Replaced silent `.catch(() => {})` and `console.error` in: `useDosimetry`, `useBodyLoader`, `useVoxelLoader`, `StochasticPanel`, `ScenePanel`

**Phase 2b: Stack overflow fix**
- New `arrayMax`/`arrayMin` in `aegis-web/src/lib/colormap.ts` (loop-based, safe for 100K+ elements)
- Replaced `Math.max(...Array.from(dataArray))` in `BodyMesh.tsx` and `ColorLegend.tsx`

**Phase 2c: Texture leak fix**
- `aegis-web/src/components/scene/DistanceLine.tsx` now disposes previous texture on re-create and on unmount

**Phase 2d: Soft reload**
- `ScenePanel.tsx` no longer calls `window.location.reload()` after location load
- Instead re-fetches capabilities via `fetchCapabilities()`

**Phase 2e: Housekeeping**
- Playwright moved from `dependencies` to `devDependencies` in `package.json`
- Removed unused `fetchHealth` and `fetchHullMesh` from `client.ts`

### Commit 2: Analysis features (Phase 3)

**Backend routes** (`src/aegis/viewer/routes/analysis.py`):
- `GET /api/compliance/limits?freq_hz=28e9&scenario=general_public`
- `GET /api/compliance/summary?tx_power_dbm=60`
- `GET /api/tissue/spectrum?tissue=Skin&f_min=1e9&f_max=100e9&n=100`

**Frontend features**:
- Max compliant power in `CompliancePanel.tsx` (client-side calc, clickable to set power)
- `TissuePanel.tsx` with SVG sparklines (eps_r, sigma, T0 vs freq)
- `ExportPanel.tsx` with screenshot/CSV/JSON/report download buttons
- API client functions: `fetchComplianceLimits`, `fetchComplianceSummary`, `fetchTissueSpectrum`
- Both panels wired into `Sidebar.tsx` accordion

## What needs to be checked (QA checklist)

### Core functionality (must not be broken)
- [x] Body mesh loads and displays correctly
- [x] Antenna placement works (click to place)
- [x] Dosimetry compute triggers on parameter change (578ms)
- [x] Heatmap colors update on body mesh
- [x] Compliance panel shows PASS/FAIL with progress bars
- [x] Color legend shows correct scale (dB/linear toggle)
- [ ] Ray tracing panel controls -- not tested (needs scene/voxels)
- [ ] Stochastic panel loads presets -- not tested (panel renders)

### New features to verify
- [x] Max compliant power row appears in CompliancePanel footer (62.6 dBm)
- [ ] Clicking max power value sets TX power -- not tested interactively
- [x] Tissue panel shows sparklines when opened (eps_r, sigma, T0)
- [x] Current frequency vertical line shows at 28 GHz position
- [ ] Export panel: screenshot -- renders button, not tested download
- [ ] Export panel: CSV download -- renders button
- [x] Export panel: JSON download works (aegis_stats.json confirmed)
- [x] Export panel: compliance report -- API returns correct text
- [ ] Notification toasts -- not triggered during QA (no errors occurred)

### Regression checks
- [x] No `as any` TypeScript errors in build (tsc --noEmit clean)
- [x] RT config changes -- RayTracingPanel renders with nested config
- [ ] Location loading -- not tested (no API key available)
- [x] Camera presets work (focus preset tested and confirmed)
- [ ] Follow camera mode -- not tested
- [x] Wireframe toggle works
- [x] Sidebar opens/closes smoothly

### API routes verified
- [x] GET /api/compliance/limits (28 GHz, 60 GHz occupational)
- [x] GET /api/compliance/summary (returns formatted text)
- [x] GET /api/tissue/spectrum (returns eps_r, sigma, T0 arrays)
- [x] Bad freq_hz returns 400 error correctly
- [x] No console errors during normal operation

## Files changed (for reference)

### New files
- `aegis-web/src/stores/notifications.ts`
- `aegis-web/src/components/hud/NotificationToast.tsx`
- `aegis-web/src/components/panels/TissuePanel.tsx`
- `aegis-web/src/components/panels/ExportPanel.tsx`
- `src/aegis/viewer/routes/analysis.py`

### Modified files (25 total)
- `aegis-web/src/api/types.ts` (major: new interfaces)
- `aegis-web/src/api/client.ts` (new fetch functions, removed unused)
- `aegis-web/src/stores/scene.ts` (RtStoreConfig nesting)
- `aegis-web/src/hooks/useDosimetry.ts` (rewritten with useShallow)
- `aegis-web/src/hooks/useConfig.ts` (removed as any)
- `aegis-web/src/hooks/useKeyboard.ts` (removed as any)
- `aegis-web/src/hooks/usePhysics.ts` (removed as any)
- `aegis-web/src/hooks/useBodyLoader.ts` (notification)
- `aegis-web/src/hooks/useVoxelLoader.ts` (notification)
- `aegis-web/src/components/scene/SceneRoot.tsx` (typed lighting)
- `aegis-web/src/components/scene/Antenna.tsx` (typed antenna config)
- `aegis-web/src/components/scene/DistanceLine.tsx` (texture disposal)
- `aegis-web/src/components/scene/VoxelField.tsx` (typed voxel config)
- `aegis-web/src/components/scene/BodyMesh.tsx` (arrayMax fix)
- `aegis-web/src/components/hud/ColorLegend.tsx` (arrayMax fix)
- `aegis-web/src/components/hud/ServerInfoBadge.tsx` (typed SystemInfo)
- `aegis-web/src/components/hud/CompliancePanel.tsx` (max power widget)
- `aegis-web/src/components/layout/HudOverlay.tsx` (notification toast)
- `aegis-web/src/components/layout/Toolbar.tsx` (active_scenario)
- `aegis-web/src/components/layout/Sidebar.tsx` (tissue + export panels)
- `aegis-web/src/components/panels/RayTracingPanel.tsx` (nested rtConfig)
- `aegis-web/src/components/panels/ScenePanel.tsx` (soft reload, notifications)
- `aegis-web/src/components/panels/StochasticPanel.tsx` (notification)
- `aegis-web/src/lib/colormap.ts` (arrayMax/arrayMin)
- `aegis-web/package.json` (playwright to devDeps)
- `src/aegis/viewer/server.py` (register analysis routes)
