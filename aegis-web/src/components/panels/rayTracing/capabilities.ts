export type Backend = 'sionna' | 'differt'

/** Whether a parameter is configurable, fixed to a value, or not available. */
export type ParamCap =
  | { kind: 'configurable' }
  | { kind: 'configurable-when'; when: string; reason: string }
  | { kind: 'fixed'; value: string; reason: string }
  | { kind: 'na'; reason: string }

interface CapExtra {
  method: string
  diffraction: boolean
}

type CapFn = (b: Backend, extra: CapExtra) => ParamCap

const onlyDiffert = (reason: string): CapFn =>
  (b) => b === 'differt' ? { kind: 'configurable' } : { kind: 'na', reason }

const onlySionna = (reason: string): CapFn =>
  (b) => b === 'sionna' ? { kind: 'configurable' } : { kind: 'na', reason }

const requiresDiffraction: CapFn = (b, { diffraction }) => {
  if (b !== 'sionna') return { kind: 'na', reason: 'not available with DiffeRT' }
  if (!diffraction) return { kind: 'configurable-when', when: 'diffraction', reason: 'requires diffraction' }
  return { kind: 'configurable' }
}

const PARAM_CAPS: Record<string, CapFn> = {
  method: (b) =>
    b === 'differt' ? { kind: 'configurable' } : { kind: 'fixed', value: 'SBR', reason: 'fixed for Sionna RT' },

  raysPerSource: (b, { method }) => {
    if (b === 'differt' && method === 'exhaustive')
      return { kind: 'configurable-when', when: 'sbr', reason: 'exhaustive does not use rays' }
    return { kind: 'configurable' }
  },

  maxPathsPerSource: onlySionna('not available with DiffeRT'),

  los: (b) =>
    b === 'sionna' ? { kind: 'configurable' } : { kind: 'fixed', value: 'on', reason: 'always on' },

  specularReflection: (b) =>
    b === 'sionna' ? { kind: 'configurable' } : { kind: 'fixed', value: 'on', reason: 'always on' },

  diffuseReflection: onlySionna('not available with DiffeRT'),
  refraction: onlySionna('not available with DiffeRT'),
  diffraction: onlySionna('not available with DiffeRT'),
  edgeDiffraction: requiresDiffraction,
  diffractionLitRegion: requiresDiffraction,
  reflectionLoss: onlyDiffert('physics-based in Sionna RT'),
  syntheticArray: onlySionna('not available with DiffeRT'),

  chunkSize: (b, { method }) => {
    if (b !== 'differt') return { kind: 'na', reason: 'not available with Sionna' }
    if (method === 'sbr')
      return { kind: 'configurable-when', when: 'exhaustive/hybrid', reason: 'SBR does not use chunks' }
    return { kind: 'configurable' }
  },

  seed: onlySionna('not available with DiffeRT'),
}

export function capFor(
  backend: Backend,
  param: string,
  extra: { method?: string; diffraction?: boolean } = {},
): ParamCap {
  const fn = PARAM_CAPS[param]
  if (!fn) return { kind: 'configurable' }
  return fn(backend, {
    method: extra.method ?? 'exhaustive',
    diffraction: extra.diffraction ?? false,
  })
}

export function isDisabled(cap: ParamCap): boolean {
  return cap.kind !== 'configurable'
}

export function disabledText(cap: ParamCap): string | null {
  if (cap.kind === 'fixed' || cap.kind === 'na' || cap.kind === 'configurable-when')
    return `(${cap.reason})`
  return null
}
