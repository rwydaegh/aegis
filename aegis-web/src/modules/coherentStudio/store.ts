import { create } from 'zustand'
import type {
  BodyMapResult,
  PhantomGeometry,
  Provenance,
  SlicePlane,
  SliceResult,
  StudioFieldQuantity,
  StudioFocusMode,
  StudioManifest,
  Vec3,
} from './api'

export type StudioScaleMode = 'auto' | 'fixed' | 'log'
export type StudioUeAntenna = 'dipole'

interface StudioState {
  // --- Parameters (all positions in SERVER / Z-up metres) ---
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
  /** ECBF absorbed-power budget as a fraction of MRT (1 = MRT, lower = safer). */
  ecbfBudgetFrac: number

  // --- Render-only (never trigger a slice/body-map re-fetch) ---
  colormap: string
  scaleMode: StudioScaleMode
  /** Number of arrival rays drawn in the scene (decoration; own fetch). */
  topK: number
  showRays: boolean
  showArrayPattern: boolean
  wireframe: boolean
  /** When true, clicking the body moves the focus to the clicked surface point. */
  pickFocusOnBody: boolean

  // --- Results ---
  sliceResult: SliceResult | null
  bodyMap: BodyMapResult | null
  phantom: PhantomGeometry | null
  manifest: StudioManifest | null
  computing: boolean
  /** True when the last body-map fetch found no precomputed pack for the combo. */
  bodyMapNotPrecomputed: boolean
  /** Provenance of the currently displayed slice / body map (whichever was set last). */
  provenance: Provenance | null

  // --- Parameter actions ---
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
  setColormap: (colormap: string) => void
  setScaleMode: (scaleMode: StudioScaleMode) => void
  setEcbfBudgetFrac: (ecbfBudgetFrac: number) => void
  setTopK: (topK: number) => void
  setShowRays: (showRays: boolean) => void
  setShowArrayPattern: (showArrayPattern: boolean) => void
  setWireframe: (wireframe: boolean) => void
  setPickFocusOnBody: (pickFocusOnBody: boolean) => void

  // --- Result actions ---
  setSliceResult: (sliceResult: SliceResult | null) => void
  setBodyMap: (bodyMap: BodyMapResult | null) => void
  setBodyMapNotPrecomputed: (notPrecomputed: boolean) => void
  setPhantom: (phantom: PhantomGeometry | null) => void
  setManifest: (manifest: StudioManifest | null) => void
  setComputing: (computing: boolean) => void
}

export const useStudioStore = create<StudioState>()((set) => ({
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
  bodyMapQuantity: 'mrt',
  ecbfBudgetFrac: 0.5,

  colormap: 'viridis',
  scaleMode: 'auto',
  topK: 150,
  showRays: true,
  showArrayPattern: true,
  wireframe: false,
  pickFocusOnBody: false,

  sliceResult: null,
  bodyMap: null,
  phantom: null,
  manifest: null,
  computing: false,
  bodyMapNotPrecomputed: false,
  provenance: null,

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
  setColormap: (colormap) => set({ colormap }),
  setScaleMode: (scaleMode) => set({ scaleMode }),
  setEcbfBudgetFrac: (ecbfBudgetFrac) => set({ ecbfBudgetFrac }),
  setTopK: (topK) => set({ topK }),
  setShowRays: (showRays) => set({ showRays }),
  setShowArrayPattern: (showArrayPattern) => set({ showArrayPattern }),
  setWireframe: (wireframe) => set({ wireframe }),
  setPickFocusOnBody: (pickFocusOnBody) => set({ pickFocusOnBody }),

  setSliceResult: (sliceResult) =>
    set({ sliceResult, provenance: sliceResult ? sliceResult.provenance : null }),
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

/** Params requiring a body-map pack swap. */
export type BodyMapKeyState = Pick<
  StudioState,
  'condition' | 'arrayN' | 'beam' | 'bodyMapQuantity' | 'frequencyGhz' | 'seed'
>

export function sliceFetchKey(s: SliceKeyState): string {
  return JSON.stringify([
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
  return JSON.stringify([
    s.condition,
    s.arrayN,
    s.beam,
    s.bodyMapQuantity,
    s.frequencyGhz,
    s.seed,
  ])
}
