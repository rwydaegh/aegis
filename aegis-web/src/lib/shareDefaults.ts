// Default values for all shareable fields. Must match store defaults exactly.
export const SHARE_DEFAULTS = {
  // simulation store
  antennaPos: null as [number, number, number] | null,
  mode: 'spatial' as string,
  fresnel: true,
  polarisation: false,
  curvature: false,
  diffraction: false,
  powerDbm: 43,
  skinModel: 'itis',
  freqGhz: 28,
  stochasticPreset: '3GPP_38.901_UMi_LOS',
  stochasticSeed: 42,
  stochasticOverrides: {} as Record<string, number>,
  bodyOffset: [0, 0, 0] as [number, number, number],
  bodyRotationY: 0,
  enabledQuantities: ['sab', 'sab_4cm2'] as string[],
  displayQuantity: 'sab' as string,
  // scene store
  bodyName: '' as string,
  pathSource: 'synthetic' as string,
  rtSource: 'sionna' as string,
  rtMaxOrder: 3,
  rtConfig: {
    method: 'exhaustive' as string,
    raysPerSource: 1_000_000,
    maxPathsPerSource: 1_000_000,
    los: true,
    specularReflection: true,
    diffuseReflection: false,
    refraction: true,
    diffraction: false,
    edgeDiffraction: false,
    diffractionLitRegion: true,
    reflectionLoss: 0.5,
    syntheticArray: true,
    seed: 42,
  },
  envDisplayMode: 'cubes' as string,
  // display config from scene store
  colormapName: 'inferno' as string,
  sunIntensity: 1.2,
  ambientIntensity: 0.6,
  cameraFov: 55,
  // scene visibility
  bodyMeshVisible: true,
  groundPlaneVisible: true,
  gridVisible: false,
  sceneGeometryVisible: true,
  // camera (null = use default, not from share link)
  cameraPosition: null as [number, number, number] | null,
  cameraTarget: null as [number, number, number] | null,
  // ui store
  wireframe: false,
  legendScale: 'linear' as string,
  dynamicRangeDb: 30,
  ratioMode: false,
  exposureScenario: 'general_public' as string,
  // antenna store (multi-antenna)
  antennas: [] as Array<{
    id: string
    name: string
    position: [number, number, number]
    height: number
    focusPoint: [number, number, number] | null
    powerDbm: number
    arrayConfig: {
      n_h: number
      n_v: number
      d_h_wavelengths: number
      d_v_wavelengths: number
      broadside: [number, number, number]
      element_pattern: string
    }
    enabled: boolean
  }>,
  selectedAntennaId: null as string | null,
}

export type ShareState = typeof SHARE_DEFAULTS
