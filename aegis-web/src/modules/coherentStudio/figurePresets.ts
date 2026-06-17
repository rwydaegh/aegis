import type { FigurePreset, StudioSettings } from './store'

// Reproducible "gimme this part of Figure 1" presets. Each entry is a full
// settings patch (and, once captured, a camera) that reproduces exactly one panel
// of the paper's lead figure. Apply from the panel dropdown, or open the studio
// at /studio?preset=<name> to land straight on a panel (the URL is the reproducer).
//
// Figure 1 tells the on-body story the paper actually proves: turning the ECBF
// exposure budget down cools the body's absorbed power S_ab = ||G~(r) x||^2 while
// the delivered signal follows the trade-off. The free-space field slice is
// deliberately omitted here (it is a different quantity, air not tissue, and would
// invite the "the air spot is the body hotspot" misread); it lives in the
// hotspot-tomography figure instead.
//
// Honesty is pinned in the data: every body panel shares ONE fixed colour scale
// (vmax locked to the MRT body peak) so the cooling between panels is real, not a
// per-panel autoscale artifact. Provenance for the locked range and config is in
// figures/configuration_fig1/PROVENANCE.md.

// The paper's headline demonstration: thelonious / NLOS (a partition removes the
// direct path, so the body is reached only by multipath) / 8x8 = 64-element URA /
// 28 GHz / seed 0 / dipole UE, focus at the served position. MRT deposited-map
// peak ~1.54e-3, p99.9 ~1.29e-3 (W m^-2 per W tx); lock the shared scale a touch
// above p99.9 so a single hot facet does not set it.
const FIXED_SAB_VMAX = 0.0013

// Settings common to every Figure 1 panel: the scene config, a clean transparent
// figure backdrop with all chrome stripped, and the locked S_ab colour scale.
const FIG1_BASE: Partial<StudioSettings> = {
  mesh: 'thelonious',
  condition: 'nlos',
  arrayN: 8,
  seed: 0,
  ueIdx: 4,
  ueAntenna: 'dipole',
  frequencyGhz: 28,
  focusMode: 'free-space',
  focusXyz: [0.923, -0.005, 0.734],
  bodyMapQuantity: 'deposited',
  fieldQuantity: 'S',
  colormap: 'inferno',
  scaleMode: 'fixed',
  scaleScope: 'surface',
  robustClip: false,
  fixedRange: { vmin: 0, vmax: FIXED_SAB_VMAX },
  background: 'transparent',
  screenshotMode: false,
  showGizmo: false,
  showRefSquare: false,
  showBeamAxis: false,
  cameraView: 'orbit',
  pickFocusOnBody: false,
  exportLongEdgePx: 2200,
  colorbarFieldInExport: false,
  colorbarBodyInExport: false,
}

// A bare body tile: no rays / array / blockers / slice, just the phantom wearing
// its deposited map on the locked scale. The three of these are the knob filmstrip.
const BODY_TILE: Partial<StudioSettings> = {
  ...FIG1_BASE,
  showRays: false,
  showArrayPattern: false,
  showRxPattern: false,
  showBlockers: false,
  showSlice: false,
  showVolume: false,
  exportAspect: '4:5',
  exportLongEdgePx: 1800,
  colorbarBodyInExport: false, // one shared bar is drawn once in the composition
}

// Shared camera for the three knob body tiles: a 3/4 front view from the
// array-facing side, so the lit deposition reads and the framing is identical
// across the sweep (the cooling is the only thing that changes).
const TILE_CAMERA = { position: [-2.0, 0.98, 1.7] as [number, number, number], target: [0.92, 0.82, 0.0] as [number, number, number], fov: 23 }

export const FIGURE_PRESETS: FigurePreset[] = [
  {
    name: 'fig1-hero',
    label: 'Fig 1 - hero (scene)',
    description:
      'Establishing scene: array, coherent arrival rays, phantom wearing S_ab. The conventional matched-filter (MRT) beam. No field slice (avoids the air-vs-tissue conflation).',
    settings: {
      ...FIG1_BASE,
      beam: 'mrt',
      showRays: true,
      topK: 150,
      rayColorMode: 'power',
      showArrayPattern: true,
      showRxPattern: false,
      showBlockers: true,
      showSlice: false,
      showVolume: false,
      exportAspect: '3:2',
      exportLongEdgePx: 2400,
      // No baked bar: the figure draws ONE shared S_ab colour bar in LaTeX (serif
      // type, beside the knob filmstrip where the cooling is read).
      colorbarBodyInExport: false,
    },
    camera: { position: [-3.0, 3.2, 6.5], target: [0.2, 1.1, 0.0], fov: 40 },
  },
  {
    name: 'fig1-mrt',
    label: 'Fig 1 - knob: MRT (100% dose)',
    description: 'Body tile, matched-filter beam. Reference point: P_abs 100%, signal 100%.',
    settings: { ...BODY_TILE, beam: 'mrt' },
    camera: TILE_CAMERA,
  },
  {
    name: 'fig1-ecbf50',
    label: 'Fig 1 - knob: ECBF 50%',
    description: 'Body tile, ECBF at 50% of the MRT absorption budget. Measured: signal ~81%.',
    settings: { ...BODY_TILE, beam: 'ecbf', ecbfBudgetFrac: 0.5 },
    camera: TILE_CAMERA,
  },
  {
    name: 'fig1-ecbf15',
    label: 'Fig 1 - knob: ECBF 15%',
    description: 'Body tile, ECBF at 15% of the MRT absorption budget. Measured: signal ~44%.',
    settings: { ...BODY_TILE, beam: 'ecbf', ecbfBudgetFrac: 0.15 },
    camera: TILE_CAMERA,
  },
]

export function findFigurePreset(name: string): FigurePreset | undefined {
  return FIGURE_PRESETS.find((p) => p.name === name)
}
