import { useMemo } from 'react'
import { useStudioStore } from './store'
import { isSignedQuantity } from './scene/studioHelpers'
import { rangeOf, resolveScale, unionRange, type Range, type ResolvedScale } from './scene/colorScale'

export interface StudioScales {
  slice: ResolvedScale
  body: ResolvedScale
  volume: ResolvedScale
  /** The shared union range (null when no surface has data); for the legend. */
  sharedRange: Range | null
  /** What the slice scale would be in auto mode: the snapshot for "lock to current". */
  autoRange: Range
}

/**
 * Resolve the colour scale for all three surfaces (slice, body map, field volume)
 * from one place, so 'shared' scope can union their data ranges and the slice,
 * body, volume, and legend all agree. Data ranges are recomputed only when a
 * result object or the robust-clip flag changes (percentileRange sorts, so it
 * must not run per frame); the cheap resolveScale step re-runs on any scale knob.
 */
export function useStudioScales(): StudioScales {
  const sliceResult = useStudioStore((s) => s.sliceResult)
  const bodyMap = useStudioStore((s) => s.bodyMap)
  const volumeResult = useStudioStore((s) => s.volumeResult)
  const fieldQuantity = useStudioStore((s) => s.fieldQuantity)
  const colormap = useStudioStore((s) => s.colormap)
  const scaleMode = useStudioStore((s) => s.scaleMode)
  const scaleScope = useStudioStore((s) => s.scaleScope)
  const dynamicRangeDb = useStudioStore((s) => s.dynamicRangeDb)
  const robustClip = useStudioStore((s) => s.robustClip)
  const fixedRange = useStudioStore((s) => s.fixedRange)

  const sliceRange = useMemo(() => rangeOf(sliceResult?.scalar, robustClip), [sliceResult, robustClip])
  const bodyRange = useMemo(() => rangeOf(bodyMap?.values, robustClip), [bodyMap, robustClip])
  const volumeRange = useMemo(() => rangeOf(volumeResult?.scalar, robustClip), [volumeResult, robustClip])

  // The shared range unions the non-negative surfaces. A signed slice keeps its
  // own symmetric scale, so it is excluded (its negative half would not share a
  // scale with the non-negative body / volume anyway).
  const sliceSigned = isSignedQuantity(fieldQuantity)
  const sharedRange = useMemo(
    () => unionRange([sliceSigned ? null : sliceRange, bodyRange, volumeRange]),
    [sliceSigned, sliceRange, bodyRange, volumeRange],
  )

  return useMemo(() => {
    const common = { scope: scaleScope, colormap, dynamicRangeDb, fixedRange, sharedRange }
    const auto = resolveScale({ ...common, mode: 'auto', quantity: fieldQuantity, surfaceRange: sliceRange })
    return {
      slice: resolveScale({ ...common, mode: scaleMode, quantity: fieldQuantity, surfaceRange: sliceRange }),
      body: resolveScale({ ...common, mode: scaleMode, quantity: 'sab', surfaceRange: bodyRange }),
      volume: resolveScale({ ...common, mode: scaleMode, quantity: 'S', surfaceRange: volumeRange }),
      sharedRange,
      autoRange: { vmin: auto.vmin, vmax: auto.vmax },
    }
  }, [scaleMode, scaleScope, colormap, dynamicRangeDb, fixedRange, sharedRange, fieldQuantity, sliceRange, bodyRange, volumeRange])
}
