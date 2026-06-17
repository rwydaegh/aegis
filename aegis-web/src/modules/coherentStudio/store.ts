import { create } from 'zustand'
import type {
  BodyMapResult,
  ComplianceResult,
  PhantomGeometry,
  PrecoderResult,
  Provenance,
  SceneGeometry,
  SlicePlane,
  SliceResult,
  StudioBodyMapStatistic,
  StudioFieldQuantity,
  StudioFocusMode,
  StudioManifest,
  Vec3,
  VolumeResult,
} from './api'

import type { Range, StudioScaleScope } from './scene/colorScale'

export type StudioScaleMode = 'auto' | 'fixed' | 'log'
/** Scene backdrop: the dark app look, a pure-white scientific-figure look, or
 * a transparent buffer for figure export. Render-only. */
export type StudioBackground = 'dark' | 'white' | 'transparent'
/** Camera view: free orbit, or locked looking down the BS -> focus beam axis. */
export type StudioCameraView = 'orbit' | 'bs-axis'
/** UE receive antenna pattern C_R(k); shapes the matched filter, hence the
 * precoder and the live (deposited / slice / volume) maps. */
export type StudioUeAntenna = 'isotropic' | 'vertical' | 'dipole' | 'patch'
/** How the arrival rays are tinted: by per-path power on the active colormap, or
 * a single neutral colour (so the rays read as geometry, not as a second field). */
export type StudioRayColorMode = 'power' | 'mono'
/** Fixed framing of the scene canvas for figure export. 'free' fills the column;
 * the others letterbox the canvas to a fixed aspect so the captured PNG has
 * predictable, reproducible dimensions (and the camera reacts to the new aspect). */
export type StudioAspect = 'free' | '1:1' | '4:5' | '3:2' | '16:9'
/** A reproducible camera viewpoint. position drives the orbit vantage; the target
 * normally follows the focus, but is stored so a preset can pin it. fov in degrees. */
export interface StudioCameraPose {
  position: Vec3
  target: Vec3
  fov: number
}
/** A named, reproducible Figure panel: a full settings patch (beam, budget,
 * colormap, fixed scale, visible surfaces, background, export framing) plus an
 * optional camera. Applying one reproduces exactly one panel of a paper figure. */
export interface FigurePreset {
  name: string
  label: string
  description: string
  settings: Partial<StudioSettings>
  camera?: StudioCameraPose
}

interface StudioState {
  // --- Parameters (all positions in SERVER / Z-up metres) ---
  /** Phantom mesh (thelonious, duke, eartha, ella). Selects all per-body packs. */
  mesh: string
  condition: string
  arrayN: number
  seed: number
  /** Corridor standing position of the person (UE index 0..8). The body moves
   * down the corridor and the deposited map + phantom geometry follow. */
  ueIdx: number
  ueAntenna: StudioUeAntenna
  beam: string
  focusMode: StudioFocusMode
  focusXyz: Vec3
  frequencyGhz: number
  plane: SlicePlane
  fieldQuantity: StudioFieldQuantity
  bodyMapQuantity: string
  /**
   * Sticky preference for the live "deposited" map. When set, the quantity
   * picker auto-promotes back to 'deposited' the moment its channel pack
   * becomes available again (after an automatic fall-back to 'mrt' on a combo
   * that lacks one). Cleared only when the user explicitly picks a non-live
   * quantity. Render-only meta-state: never part of any fetch key.
   */
  preferDeposited: boolean
  /** Body-map realisation: single, or mean / p95 over the LOS seed ensemble. */
  bodyMapStatistic: StudioBodyMapStatistic
  /** ECBF absorbed-power budget as a fraction of MRT (1 = MRT, lower = safer). */
  ecbfBudgetFrac: number

  // --- Render-only (never trigger a slice/body-map re-fetch) ---
  colormap: string
  scaleMode: StudioScaleMode
  /** Colour-scale scope: each surface autoscales, or one range shared by all. */
  scaleScope: StudioScaleScope
  /** Dynamic range (dB) of the log / dB colour window below the peak. */
  dynamicRangeDb: number
  /** Robust autoscale: clip the colour range to the p0.5..p99.5 percentiles. */
  robustClip: boolean
  /** User-locked colour range, applied in 'fixed' scale mode (null = not yet set). */
  fixedRange: Range | null
  /** Captured body map to compare the live map against (A in the A/B compare). */
  referenceMap: { values: number[]; label: string } | null
  /** Number of arrival rays drawn in the scene (decoration; own fetch). */
  topK: number
  showRays: boolean
  showArrayPattern: boolean
  showRxPattern: boolean
  /** Max radius (metres) of the Rx pattern lobe. Render-only. */
  rxPatternExtentM: number
  /** Gap (metres) between the focus and the ray arrowheads, so the rays stop
   * short of the hotspot. Independent of the Rx pattern extent. Render-only. */
  rayCutoffM: number
  /** Overall thickness multiplier on the arrival rays. Per-ray width still scales
   * with path power on top of this, so it sets how bold the strong rays read. */
  rayThickness: number
  /** Tint the rays by power (colormap) or with a single neutral colour. */
  rayColorMode: StudioRayColorMode
  /** Draw the real factory blockers (metallic scatterers + NLOS slab). */
  showBlockers: boolean
  /** Draw the dashed BS -> focus beam axis and its range / downtilt label. */
  showBeamAxis: boolean
  /** Scene backdrop (dark / white / transparent). Render-only. */
  background: StudioBackground
  /** Visible radius (metres) of the BS array pattern lobe. The panel is ~14 m
   * from the body, so the true lobe is tiny; this sets a legible display size. */
  arrayPatternSizeM: number
  /** Strip chrome (grid, gizmos, helpers) for a clean figure capture. */
  screenshotMode: boolean
  /** Draw the 4 cm^2 ICNIRP reference square on the slice at the focus. */
  showRefSquare: boolean
  /** Draw the slice TransformControls gizmo (the RGB axis triad on the plane). */
  showGizmo: boolean
  /** Camera view: free orbit, or locked down the BS -> focus beam axis. */
  cameraView: StudioCameraView
  /** When true, clicking the body moves the focus to the clicked surface point. */
  pickFocusOnBody: boolean
  /** Draw the free-space field slice plane. Off makes a clean body-only tile for
   * figure panels where the slice would occlude the deposited map. */
  showSlice: boolean
  /** Render the focal lobe as a 3D field-volume cloud (own fetch). */
  showVolume: boolean
  /** Per-axis sample count of the field-volume box (clamped 8..48 server-side). */
  volumeRes: number
  /** Full side length of the field-volume box, metres. */
  volumeExtentM: number
  /** Voxels below this fraction of the box peak are not drawn (declutter). */
  volumeThreshold: number
  /** Per-voxel cube opacity for the field-volume cloud. */
  volumeOpacity: number
  /** Show the ICNIRP compliance scalars panel (P_abs, SAR_wb, psSAR, eta,
   * signal vs MRT). Opt-in: the first request per phantom builds the 4 cm^2
   * averaging matrix (a few seconds), so it is off by default. Render-only. */
  showCompliance: boolean

  // --- Figure export (render-only; reproducible captures for paper figures) ---
  /** Letterbox the scene canvas to this aspect so captures have fixed dimensions. */
  exportAspect: StudioAspect
  /** Target long-edge resolution (px) the canvas is re-rendered at on capture, so
   * the exported PNG is print-crisp and independent of the on-screen window size. */
  exportLongEdgePx: number
  /** Composite the field (slice / volume) colour bar into the exported PNG. */
  colorbarFieldInExport: boolean
  /** Composite the body (deposited APD) colour bar into the exported PNG. */
  colorbarBodyInExport: boolean
  /** Last saved camera viewpoint (null until the user saves one). */
  savedCamera: StudioCameraPose | null
  /** Bumped to ask the in-canvas bridge to read the live camera into savedCamera. */
  cameraSaveNonce: number
  /** Bumped to ask the in-canvas bridge to apply savedCamera to the live camera. */
  cameraApplyNonce: number

  // --- Results ---
  sliceResult: SliceResult | null
  volumeResult: VolumeResult | null
  bodyMap: BodyMapResult | null
  /** Synthesised precoder x + array geometry for the live Tx radiation lobe. */
  precoder: PrecoderResult | null
  phantom: PhantomGeometry | null
  manifest: StudioManifest | null
  computing: boolean
  /** Real scene geometry (blockers, room, BS). Null until fetched / on miss. */
  scene: SceneGeometry | null
  /** True when the last body-map fetch found no precomputed pack for the combo. */
  bodyMapNotPrecomputed: boolean
  /** ICNIRP compliance scalars for the current beam + focus (null until fetched). */
  compliance: ComplianceResult | null
  /** True when compliance is unavailable for the combo (no channel/Q pack, or a
   * beam with no per-element precoder such as decohered). */
  complianceNotAvailable: boolean
  /** Provenance of the currently displayed slice / body map (whichever was set last). */
  provenance: Provenance | null

  // --- Parameter actions ---
  setMesh: (mesh: string) => void
  setCondition: (condition: string) => void
  setArrayN: (arrayN: number) => void
  setSeed: (seed: number) => void
  setUeIdx: (ueIdx: number) => void
  setUeAntenna: (ueAntenna: StudioUeAntenna) => void
  setBeam: (beam: string) => void
  setFocusMode: (focusMode: StudioFocusMode) => void
  setFocusXyz: (focusXyz: Vec3) => void
  setFrequencyGhz: (frequencyGhz: number) => void
  setPlane: (patch: Partial<SlicePlane>) => void
  setFieldQuantity: (fieldQuantity: StudioFieldQuantity) => void
  setBodyMapQuantity: (bodyMapQuantity: string) => void
  setPreferDeposited: (preferDeposited: boolean) => void
  setBodyMapStatistic: (bodyMapStatistic: StudioBodyMapStatistic) => void
  setColormap: (colormap: string) => void
  setScaleMode: (scaleMode: StudioScaleMode) => void
  setScaleScope: (scaleScope: StudioScaleScope) => void
  setDynamicRangeDb: (dynamicRangeDb: number) => void
  setRobustClip: (robustClip: boolean) => void
  setFixedRange: (fixedRange: Range | null) => void
  setReferenceMap: (referenceMap: { values: number[]; label: string } | null) => void
  setEcbfBudgetFrac: (ecbfBudgetFrac: number) => void
  setTopK: (topK: number) => void
  setShowRays: (showRays: boolean) => void
  setShowArrayPattern: (showArrayPattern: boolean) => void
  setShowRxPattern: (showRxPattern: boolean) => void
  setRxPatternExtentM: (rxPatternExtentM: number) => void
  setRayCutoffM: (rayCutoffM: number) => void
  setRayThickness: (rayThickness: number) => void
  setRayColorMode: (rayColorMode: StudioRayColorMode) => void
  setShowBlockers: (showBlockers: boolean) => void
  setShowBeamAxis: (showBeamAxis: boolean) => void
  setBackground: (background: StudioBackground) => void
  setArrayPatternSizeM: (arrayPatternSizeM: number) => void
  setScreenshotMode: (screenshotMode: boolean) => void
  setShowRefSquare: (showRefSquare: boolean) => void
  setShowGizmo: (showGizmo: boolean) => void
  setCameraView: (cameraView: StudioCameraView) => void
  setPickFocusOnBody: (pickFocusOnBody: boolean) => void
  setShowSlice: (showSlice: boolean) => void
  setShowVolume: (showVolume: boolean) => void
  setVolumeRes: (volumeRes: number) => void
  setVolumeExtentM: (volumeExtentM: number) => void
  setVolumeThreshold: (volumeThreshold: number) => void
  setVolumeOpacity: (volumeOpacity: number) => void
  setShowCompliance: (showCompliance: boolean) => void
  setExportAspect: (exportAspect: StudioAspect) => void
  setExportLongEdgePx: (exportLongEdgePx: number) => void
  setColorbarFieldInExport: (colorbarFieldInExport: boolean) => void
  setColorbarBodyInExport: (colorbarBodyInExport: boolean) => void
  setSavedCamera: (savedCamera: StudioCameraPose | null) => void
  /** Ask the in-canvas bridge to read the live camera into savedCamera. */
  requestCameraSave: () => void
  /** Ask the in-canvas bridge to apply savedCamera to the live camera. */
  requestCameraApply: () => void
  /** Apply a named Figure preset: a full settings patch + optional camera, in one
   * atomic update, so a panel of the paper figure reproduces exactly. */
  applyFigurePreset: (preset: FigurePreset) => void
  /** Restore every knob to STUDIO_DEFAULTS (results refetch from the new params). */
  resetDefaults: () => void

  // --- Result actions ---
  setSliceResult: (sliceResult: SliceResult | null) => void
  setVolumeResult: (volumeResult: VolumeResult | null) => void
  setBodyMap: (bodyMap: BodyMapResult | null) => void
  setBodyMapNotPrecomputed: (notPrecomputed: boolean) => void
  setPrecoder: (precoder: PrecoderResult | null) => void
  setPhantom: (phantom: PhantomGeometry | null) => void
  setManifest: (manifest: StudioManifest | null) => void
  setComputing: (computing: boolean) => void
  setScene: (scene: SceneGeometry | null) => void
  setCompliance: (compliance: ComplianceResult | null) => void
  setComplianceNotAvailable: (complianceNotAvailable: boolean) => void
}

/** The user-settable knobs (parameters + render-only state), minus results,
 * fetched geometry, and actions. This is exactly what `resetDefaults` restores. */
export type StudioSettings = Pick<
  StudioState,
  | 'mesh'
  | 'condition'
  | 'arrayN'
  | 'seed'
  | 'ueIdx'
  | 'ueAntenna'
  | 'beam'
  | 'focusMode'
  | 'focusXyz'
  | 'frequencyGhz'
  | 'plane'
  | 'fieldQuantity'
  | 'bodyMapQuantity'
  | 'preferDeposited'
  | 'bodyMapStatistic'
  | 'ecbfBudgetFrac'
  | 'colormap'
  | 'scaleMode'
  | 'scaleScope'
  | 'dynamicRangeDb'
  | 'robustClip'
  | 'fixedRange'
  | 'referenceMap'
  | 'topK'
  | 'showRays'
  | 'showArrayPattern'
  | 'showRxPattern'
  | 'rxPatternExtentM'
  | 'rayCutoffM'
  | 'rayThickness'
  | 'rayColorMode'
  | 'showBlockers'
  | 'showBeamAxis'
  | 'background'
  | 'arrayPatternSizeM'
  | 'screenshotMode'
  | 'showRefSquare'
  | 'showGizmo'
  | 'cameraView'
  | 'pickFocusOnBody'
  | 'showSlice'
  | 'showVolume'
  | 'volumeRes'
  | 'volumeExtentM'
  | 'volumeThreshold'
  | 'volumeOpacity'
  | 'showCompliance'
  | 'exportAspect'
  | 'exportLongEdgePx'
  | 'colorbarFieldInExport'
  | 'colorbarBodyInExport'
>

// Default values for every user-settable knob (parameters + render-only state).
// The store initialises from this, and `resetDefaults` restores it, so the two
// can never drift. Results / fetched geometry (slice, body map, manifest, scene)
// are NOT here: they refetch from the restored parameters.
export const STUDIO_DEFAULTS: StudioSettings = {
  mesh: 'thelonious',
  condition: '',
  arrayN: 16,
  seed: 0,
  // Mid-corridor UE (14 m), the default standing position whose packs keep the
  // original unsuffixed names. The manifest's default_ue_idx confirms this.
  ueIdx: 4,
  ueAntenna: 'dipole',
  beam: 'ecbf',
  focusMode: 'free-space',
  focusXyz: [0.923, -0.005, 0.734],
  frequencyGhz: 10,
  plane: { orientation: 'free', normalXyz: [0, 1, 0], extentM: 0.8, res: 160 },
  fieldQuantity: 'S',
  // Open on the live, focus-tracking deposited map so the headline interaction
  // (move the focus, watch the body recolour) works out of the box. Static
  // packs (mrt / floor / worstcase / amp) are frozen at a reference focus and
  // would read as "the body map is not responding". The quantity picker falls
  // back to 'mrt' if the default scene has no field-channel pack.
  bodyMapQuantity: 'deposited',
  // Default scene opens on 'deposited', so the preference starts on: any combo
  // without a channel pack falls back to 'mrt', and stepping back onto a packed
  // combo restores the live map without the user re-selecting it.
  preferDeposited: true,
  bodyMapStatistic: 'single',
  ecbfBudgetFrac: 0.5,

  colormap: 'jet',
  scaleMode: 'auto',
  scaleScope: 'surface',
  dynamicRangeDb: 30,
  robustClip: false,
  fixedRange: null,
  referenceMap: null,
  topK: 150,
  showRays: true,
  showArrayPattern: true,
  showRxPattern: true,
  rxPatternExtentM: 0.3,
  rayCutoffM: 0.5,
  rayThickness: 1,
  rayColorMode: 'power',
  showBlockers: true,
  showBeamAxis: true,
  background: 'white',
  arrayPatternSizeM: 1.8,
  screenshotMode: false,
  showRefSquare: true,
  showGizmo: true,
  cameraView: 'orbit',
  pickFocusOnBody: false,
  showSlice: true,
  showVolume: false,
  volumeRes: 24,
  volumeExtentM: 0.16,
  volumeThreshold: 0.25,
  volumeOpacity: 0.45,
  // Opt-in: the first compliance request per phantom builds the 4 cm^2 averaging
  // matrix (a few seconds), so the panel stays off until the user asks for it.
  showCompliance: false,

  // Figure export defaults: fill the column (working view), and capture at a
  // print-crisp long edge. Both colour bars off so a plain capture is just the
  // scene (the figure presets turn the relevant bar on).
  exportAspect: 'free',
  exportLongEdgePx: 2000,
  colorbarFieldInExport: false,
  colorbarBodyInExport: false,
}

export const useStudioStore = create<StudioState>()((set) => ({
  ...STUDIO_DEFAULTS,

  sliceResult: null,
  volumeResult: null,
  bodyMap: null,
  precoder: null,
  phantom: null,
  manifest: null,
  computing: false,
  scene: null,
  bodyMapNotPrecomputed: false,
  compliance: null,
  complianceNotAvailable: false,
  provenance: null,
  savedCamera: null,
  cameraSaveNonce: 0,
  cameraApplyNonce: 0,

  setMesh: (mesh) => set({ mesh }),
  setCondition: (condition) => set({ condition }),
  setArrayN: (arrayN) => set({ arrayN }),
  setSeed: (seed) => set({ seed }),
  setUeIdx: (ueIdx) =>
    set((s) => {
      // Move the steering focus with the body. The corridor relocates the body
      // (and hence its natural focus) by ue_positions[new] - ue_positions[old],
      // a pure x translation in the e11 frame. Shifting focusXyz by the same
      // vector keeps the beam tracking the same spot on the body as the slider
      // moves, so the rays / slice / volume / Rx marker / gizmo all follow it
      // instead of staying pinned at the previous standing position.
      const ue = s.scene?.ue_positions
      if (!ue || ueIdx === s.ueIdx || !ue[ueIdx] || !ue[s.ueIdx]) return { ueIdx }
      const [ox, oy, oz] = ue[s.ueIdx]
      const [nx, ny, nz] = ue[ueIdx]
      const [fx, fy, fz] = s.focusXyz
      return { ueIdx, focusXyz: [fx + (nx - ox), fy + (ny - oy), fz + (nz - oz)] as Vec3 }
    }),
  setUeAntenna: (ueAntenna) => set({ ueAntenna }),
  setBeam: (beam) => set({ beam }),
  setFocusMode: (focusMode) => set({ focusMode }),
  setFocusXyz: (focusXyz) => set({ focusXyz }),
  setFrequencyGhz: (frequencyGhz) => set({ frequencyGhz }),
  setPlane: (patch) => set((s) => ({ plane: { ...s.plane, ...patch } })),
  setFieldQuantity: (fieldQuantity) => set({ fieldQuantity }),
  setBodyMapQuantity: (bodyMapQuantity) => set({ bodyMapQuantity }),
  setPreferDeposited: (preferDeposited) => set({ preferDeposited }),
  setBodyMapStatistic: (bodyMapStatistic) => set({ bodyMapStatistic }),
  setColormap: (colormap) => set({ colormap }),
  setScaleMode: (scaleMode) => set({ scaleMode }),
  setScaleScope: (scaleScope) => set({ scaleScope }),
  setDynamicRangeDb: (dynamicRangeDb) => set({ dynamicRangeDb }),
  setRobustClip: (robustClip) => set({ robustClip }),
  setFixedRange: (fixedRange) => set({ fixedRange }),
  setReferenceMap: (referenceMap) => set({ referenceMap }),
  setEcbfBudgetFrac: (ecbfBudgetFrac) => set({ ecbfBudgetFrac }),
  setTopK: (topK) => set({ topK }),
  setShowRays: (showRays) => set({ showRays }),
  setShowArrayPattern: (showArrayPattern) => set({ showArrayPattern }),
  setShowRxPattern: (showRxPattern) => set({ showRxPattern }),
  setRxPatternExtentM: (rxPatternExtentM) => set({ rxPatternExtentM }),
  setRayCutoffM: (rayCutoffM) => set({ rayCutoffM }),
  setRayThickness: (rayThickness) => set({ rayThickness }),
  setRayColorMode: (rayColorMode) => set({ rayColorMode }),
  setShowBlockers: (showBlockers) => set({ showBlockers }),
  setShowBeamAxis: (showBeamAxis) => set({ showBeamAxis }),
  setBackground: (background) => set({ background }),
  setArrayPatternSizeM: (arrayPatternSizeM) => set({ arrayPatternSizeM }),
  setScreenshotMode: (screenshotMode) => set({ screenshotMode }),
  setShowRefSquare: (showRefSquare) => set({ showRefSquare }),
  setShowGizmo: (showGizmo) => set({ showGizmo }),
  setCameraView: (cameraView) => set({ cameraView }),
  setPickFocusOnBody: (pickFocusOnBody) => set({ pickFocusOnBody }),
  setShowSlice: (showSlice) => set({ showSlice }),
  setShowVolume: (showVolume) => set({ showVolume }),
  setVolumeRes: (volumeRes) => set({ volumeRes }),
  setVolumeExtentM: (volumeExtentM) => set({ volumeExtentM }),
  setVolumeThreshold: (volumeThreshold) => set({ volumeThreshold }),
  setVolumeOpacity: (volumeOpacity) => set({ volumeOpacity }),
  setShowCompliance: (showCompliance) => set({ showCompliance }),
  setExportAspect: (exportAspect) => set({ exportAspect }),
  setExportLongEdgePx: (exportLongEdgePx) => set({ exportLongEdgePx }),
  setColorbarFieldInExport: (colorbarFieldInExport) => set({ colorbarFieldInExport }),
  setColorbarBodyInExport: (colorbarBodyInExport) => set({ colorbarBodyInExport }),
  setSavedCamera: (savedCamera) => set({ savedCamera }),
  requestCameraSave: () => set((s) => ({ cameraSaveNonce: s.cameraSaveNonce + 1 })),
  requestCameraApply: () => set((s) => ({ cameraApplyNonce: s.cameraApplyNonce + 1 })),
  applyFigurePreset: (preset) =>
    set((s) => ({
      ...preset.settings,
      // Pin the camera and bump the apply nonce in the same update so the bridge
      // re-frames the scene the instant the preset's params land.
      savedCamera: preset.camera ?? s.savedCamera,
      cameraApplyNonce: preset.camera ? s.cameraApplyNonce + 1 : s.cameraApplyNonce,
    })),
  resetDefaults: () => set({ ...STUDIO_DEFAULTS }),

  setSliceResult: (sliceResult) =>
    set({ sliceResult, provenance: sliceResult ? sliceResult.provenance : null }),
  setVolumeResult: (volumeResult) => set({ volumeResult }),
  setBodyMap: (bodyMap) =>
    set({ bodyMap, provenance: bodyMap ? bodyMap.provenance : null }),
  setBodyMapNotPrecomputed: (bodyMapNotPrecomputed) => set({ bodyMapNotPrecomputed }),
  setPrecoder: (precoder) => set({ precoder }),
  setPhantom: (phantom) => set({ phantom }),
  setManifest: (manifest) => set({ manifest }),
  setComputing: (computing) => set({ computing }),
  setScene: (scene) => set({ scene }),
  setCompliance: (compliance) => set({ compliance }),
  setComplianceNotAvailable: (complianceNotAvailable) => set({ complianceNotAvailable }),
}))

// ---------------------------------------------------------------------------
// Derived fetch keys
//
// These are stable serialised strings of ONLY the params that require a network
// re-fetch. They drive the debounced compute hooks (later tasks), so they must
// be minimal: render-only state (colormap, scaleMode, camera) must NOT appear.
// ---------------------------------------------------------------------------

/** Params requiring a slice re-fetch. */
export type SliceKeyState = Pick<
  StudioState,
  | 'mesh'
  | 'condition'
  | 'arrayN'
  | 'seed'
  | 'beam'
  | 'focusMode'
  | 'focusXyz'
  | 'frequencyGhz'
  | 'plane'
  | 'fieldQuantity'
  | 'ecbfBudgetFrac'
  | 'ueAntenna'
  | 'ueIdx'
>

/** Params requiring a body-map pack swap (or a live recompute for 'deposited'). */
export type BodyMapKeyState = Pick<
  StudioState,
  | 'mesh'
  | 'condition'
  | 'arrayN'
  | 'beam'
  | 'bodyMapQuantity'
  | 'bodyMapStatistic'
  | 'frequencyGhz'
  | 'seed'
  | 'ueIdx'
  | 'focusMode'
  | 'focusXyz'
  | 'ecbfBudgetFrac'
  | 'ueAntenna'
>

export function sliceFetchKey(s: SliceKeyState): string {
  return JSON.stringify([
    s.mesh,
    s.condition,
    s.arrayN,
    s.seed,
    s.beam,
    s.focusMode,
    s.focusXyz,
    s.frequencyGhz,
    s.plane.orientation,
    s.plane.normalXyz,
    s.plane.extentM,
    s.plane.res,
    s.fieldQuantity,
    s.beam === 'ecbf' ? s.ecbfBudgetFrac : null,
    s.ueAntenna,
    s.ueIdx,
  ])
}

export function bodyMapFetchKey(s: BodyMapKeyState): string {
  // The live "deposited" map is a function of the precoder, so it keys on the
  // beam + focus axes (like the slice) rather than a static pack identity.
  if (s.bodyMapQuantity === 'deposited') {
    return JSON.stringify([
      'live',
      s.mesh,
      s.condition,
      s.arrayN,
      s.seed,
      s.ueIdx,
      s.beam,
      s.focusMode,
      s.focusXyz,
      s.frequencyGhz,
      s.beam === 'ecbf' ? s.ecbfBudgetFrac : null,
      s.ueAntenna,
    ])
  }
  return JSON.stringify([
    s.mesh,
    s.condition,
    s.arrayN,
    s.beam,
    s.bodyMapQuantity,
    s.bodyMapStatistic,
    s.frequencyGhz,
    s.seed,
    s.ueIdx,
  ])
}

// The Tx radiation lobe is a function of the synthesised precoder, so it keys on
// the same beam + focus axes as the live deposited map.
export function precoderFetchKey(s: BodyMapKeyState): string {
  return JSON.stringify([
    'precoder',
    s.mesh,
    s.condition,
    s.arrayN,
    s.seed,
    s.ueIdx,
    s.beam,
    s.focusMode,
    s.focusXyz,
    s.frequencyGhz,
    s.beam === 'ecbf' ? s.ecbfBudgetFrac : null,
    s.ueAntenna,
  ])
}

// The compliance scalars are a function of the synthesised precoder + body
// channel, so they key on the same beam + focus axes as the live deposited map,
// plus the showCompliance gate (so toggling the panel on triggers the fetch).
export type ComplianceKeyState = BodyMapKeyState & Pick<StudioState, 'showCompliance'>

export function complianceFetchKey(s: ComplianceKeyState): string {
  return JSON.stringify([
    'compliance',
    s.showCompliance,
    s.mesh,
    s.condition,
    s.arrayN,
    s.seed,
    s.ueIdx,
    s.beam,
    s.focusMode,
    s.focusXyz,
    s.frequencyGhz,
    s.beam === 'ecbf' ? s.ecbfBudgetFrac : null,
    s.ueAntenna,
  ])
}

/** Params requiring a field-volume re-fetch (only when showVolume is on). */
export type VolumeKeyState = Pick<
  StudioState,
  | 'showVolume'
  | 'mesh'
  | 'condition'
  | 'arrayN'
  | 'seed'
  | 'beam'
  | 'focusMode'
  | 'focusXyz'
  | 'frequencyGhz'
  | 'volumeRes'
  | 'volumeExtentM'
  | 'ecbfBudgetFrac'
  | 'ueAntenna'
  | 'ueIdx'
>

export function volumeFetchKey(s: VolumeKeyState): string {
  return JSON.stringify([
    s.showVolume,
    s.mesh,
    s.condition,
    s.arrayN,
    s.seed,
    s.beam,
    s.focusMode,
    s.focusXyz,
    s.frequencyGhz,
    s.volumeRes,
    s.volumeExtentM,
    s.beam === 'ecbf' ? s.ecbfBudgetFrac : null,
    s.ueAntenna,
    s.ueIdx,
  ])
}
