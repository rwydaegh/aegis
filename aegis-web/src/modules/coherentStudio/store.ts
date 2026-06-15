import { create } from 'zustand'
import type {
  BodyMapResult,
  PhantomGeometry,
  Provenance,
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
export type StudioUeAntenna = 'dipole'

interface StudioState {
  // --- Parameters (all positions in SERVER / Z-up metres) ---
  /** Phantom mesh (thelonious, duke, eartha, ella). Selects all per-body packs. */
  mesh: string
  condition: string
  arrayN: number
  seed: number
  ueAntenna: StudioUeAntenna
  beam: string
  focusMode: StudioFocusMode
  focusXyz: Vec3
  frequencyGhz: number
  plane: SlicePlane
  fieldQuantity: StudioFieldQuantity
  bodyMapQuantity: string
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
  phantom: PhantomGeometry | null
  manifest: StudioManifest | null
  computing: boolean
  /** True when the last body-map fetch found no precomputed pack for the combo. */
  bodyMapNotPrecomputed: boolean
  /** Provenance of the currently displayed slice / body map (whichever was set last). */
  provenance: Provenance | null

  // --- Parameter actions ---
  setMesh: (mesh: string) => void
  setCondition: (condition: string) => void
  setArrayN: (arrayN: number) => void
  setSeed: (seed: number) => void
  setUeAntenna: (ueAntenna: StudioUeAntenna) => void
  setBeam: (beam: string) => void
  setFocusMode: (focusMode: StudioFocusMode) => void
  setFocusXyz: (focusXyz: Vec3) => void
  setFrequencyGhz: (frequencyGhz: number) => void
  setPlane: (patch: Partial<SlicePlane>) => void
  setFieldQuantity: (fieldQuantity: StudioFieldQuantity) => void
  setBodyMapQuantity: (bodyMapQuantity: string) => void
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
  setPhantom: (phantom: PhantomGeometry | null) => void
  setManifest: (manifest: StudioManifest | null) => void
  setComputing: (computing: boolean) => void
}

export const useStudioStore = create<StudioState>()((set) => ({
  mesh: 'thelonious',
  condition: '',
  arrayN: 16,
  seed: 0,
  ueAntenna: 'dipole',
  beam: '',
  focusMode: 'at-skin',
  focusXyz: [0.923, -0.005, 0.734],
  frequencyGhz: 10,
  plane: { orientation: 'transverse', normalXyz: null, extentM: 0.08, res: 160 },
  fieldQuantity: 'S',
  // Open on the live, focus-tracking deposited map so the headline interaction
  // (move the focus, watch the body recolour) works out of the box. Static
  // packs (mrt / floor / worstcase / amp) are frozen at a reference focus and
  // would read as "the body map is not responding". The quantity picker falls
  // back to 'mrt' if the default scene has no field-channel pack.
  bodyMapQuantity: 'deposited',
  bodyMapStatistic: 'single',
  ecbfBudgetFrac: 0.5,

  colormap: 'viridis',
  scaleMode: 'auto',
  scaleScope: 'surface',
  dynamicRangeDb: 30,
  robustClip: false,
  fixedRange: null,
  referenceMap: null,
  topK: 150,
  showRays: true,
  showArrayPattern: true,
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
  phantom: null,
  manifest: null,
  computing: false,
  bodyMapNotPrecomputed: false,
  provenance: null,

  setMesh: (mesh) => set({ mesh }),
  setCondition: (condition) => set({ condition }),
  setArrayN: (arrayN) => set({ arrayN }),
  setSeed: (seed) => set({ seed }),
  setUeAntenna: (ueAntenna) => set({ ueAntenna }),
  setBeam: (beam) => set({ beam }),
  setFocusMode: (focusMode) => set({ focusMode }),
  setFocusXyz: (focusXyz) => set({ focusXyz }),
  setFrequencyGhz: (frequencyGhz) => set({ frequencyGhz }),
  setPlane: (patch) => set((s) => ({ plane: { ...s.plane, ...patch } })),
  setFieldQuantity: (fieldQuantity) => set({ fieldQuantity }),
  setBodyMapQuantity: (bodyMapQuantity) => set({ bodyMapQuantity }),
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
  setPhantom: (phantom) => set({ phantom }),
  setManifest: (manifest) => set({ manifest }),
  setComputing: (computing) => set({ computing }),
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
  | 'focusMode'
  | 'focusXyz'
  | 'ecbfBudgetFrac'
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
      s.beam,
      s.focusMode,
      s.focusXyz,
      s.frequencyGhz,
      s.beam === 'ecbf' ? s.ecbfBudgetFrac : null,
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
  ])
}
