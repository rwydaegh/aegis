import { create } from 'zustand'
import type {
  BodyMapResult,
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
  /** Draw the real factory blockers (metallic scatterers + NLOS slab). */
  showBlockers: boolean
  /** Draw the room as a lineart wireframe (the factory outline). */
  showRoomOutline: boolean
  /** Scene backdrop (dark / white / transparent). Render-only. */
  background: StudioBackground
  /** Multiplier on the BS array pattern lobe so it reads from the Rx vantage. */
  arrayPatternScale: number
  /** Strip chrome (grid, gizmos, helpers) for a clean figure capture. */
  screenshotMode: boolean
  /** Draw the 4 cm^2 ICNIRP reference square on the slice at the focus. */
  showRefSquare: boolean
  /** Camera view: free orbit, or locked down the BS -> focus beam axis. */
  cameraView: StudioCameraView
  wireframe: boolean
  /** When true, clicking the body moves the focus to the clicked surface point. */
  pickFocusOnBody: boolean
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
  setShowBlockers: (showBlockers: boolean) => void
  setShowRoomOutline: (showRoomOutline: boolean) => void
  setBackground: (background: StudioBackground) => void
  setArrayPatternScale: (arrayPatternScale: number) => void
  setScreenshotMode: (screenshotMode: boolean) => void
  setShowRefSquare: (showRefSquare: boolean) => void
  setCameraView: (cameraView: StudioCameraView) => void
  setWireframe: (wireframe: boolean) => void
  setPickFocusOnBody: (pickFocusOnBody: boolean) => void
  setShowVolume: (showVolume: boolean) => void
  setVolumeRes: (volumeRes: number) => void
  setVolumeExtentM: (volumeExtentM: number) => void
  setVolumeThreshold: (volumeThreshold: number) => void
  setVolumeOpacity: (volumeOpacity: number) => void

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
}

export const useStudioStore = create<StudioState>()((set) => ({
  mesh: 'thelonious',
  condition: '',
  arrayN: 16,
  seed: 0,
  // Mid-corridor UE (14 m), the default standing position whose packs keep the
  // original unsuffixed names. The manifest's default_ue_idx confirms this.
  ueIdx: 4,
  ueAntenna: 'dipole',
  beam: '',
  focusMode: 'free-space',
  focusXyz: [0.923, -0.005, 0.734],
  frequencyGhz: 10,
  plane: { orientation: 'free', normalXyz: [0, 1, 0], extentM: 0.4, res: 160 },
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
  rxPatternExtentM: 0.5,
  rayCutoffM: 0.5,
  showBlockers: true,
  showRoomOutline: true,
  background: 'dark',
  arrayPatternScale: 1,
  screenshotMode: false,
  showRefSquare: true,
  cameraView: 'orbit',
  wireframe: false,
  pickFocusOnBody: false,
  showVolume: false,
  volumeRes: 24,
  volumeExtentM: 0.16,
  volumeThreshold: 0.25,
  volumeOpacity: 0.45,

  sliceResult: null,
  volumeResult: null,
  bodyMap: null,
  precoder: null,
  phantom: null,
  manifest: null,
  computing: false,
  scene: null,
  bodyMapNotPrecomputed: false,
  provenance: null,

  setMesh: (mesh) => set({ mesh }),
  setCondition: (condition) => set({ condition }),
  setArrayN: (arrayN) => set({ arrayN }),
  setSeed: (seed) => set({ seed }),
  setUeIdx: (ueIdx) => set({ ueIdx }),
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
  setShowBlockers: (showBlockers) => set({ showBlockers }),
  setShowRoomOutline: (showRoomOutline) => set({ showRoomOutline }),
  setBackground: (background) => set({ background }),
  setArrayPatternScale: (arrayPatternScale) => set({ arrayPatternScale }),
  setScreenshotMode: (screenshotMode) => set({ screenshotMode }),
  setShowRefSquare: (showRefSquare) => set({ showRefSquare }),
  setCameraView: (cameraView) => set({ cameraView }),
  setWireframe: (wireframe) => set({ wireframe }),
  setPickFocusOnBody: (pickFocusOnBody) => set({ pickFocusOnBody }),
  setShowVolume: (showVolume) => set({ showVolume }),
  setVolumeRes: (volumeRes) => set({ volumeRes }),
  setVolumeExtentM: (volumeExtentM) => set({ volumeExtentM }),
  setVolumeThreshold: (volumeThreshold) => set({ volumeThreshold }),
  setVolumeOpacity: (volumeOpacity) => set({ volumeOpacity }),

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
  ])
}
