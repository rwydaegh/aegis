import { useCoverageStore } from '@/stores/coverage'

export function CoverageTooltip() {
  const hoveredIndex = useCoverageStore(s => s.hoveredSiteIndex)
  const coords = useCoverageStore(s => s.hoveredScreenCoords)
  const siteLats = useCoverageStore(s => s.siteLats)
  const siteLons = useCoverageStore(s => s.siteLons)
  const siteOpIndices = useCoverageStore(s => s.siteOpIndices)
  const siteTechIndices = useCoverageStore(s => s.siteTechIndices)
  const siteAntennaCounts = useCoverageStore(s => s.siteAntennaCounts)
  const operatorNames = useCoverageStore(s => s.operatorNames)
  const technologyNames = useCoverageStore(s => s.technologyNames)

  if (hoveredIndex == null || !coords || !siteLats || !siteLons || !siteOpIndices || !siteAntennaCounts) return null

  const lat = siteLats[hoveredIndex]
  const lon = siteLons![hoveredIndex]
  const operator = operatorNames[siteOpIndices[hoveredIndex]] ?? 'Unknown'
  const technology = siteTechIndices ? (technologyNames[siteTechIndices[hoveredIndex]] ?? '') : ''
  const antennaCount = siteAntennaCounts[hoveredIndex] || 1

  return (
    <div
      className="pointer-events-none fixed z-50 rounded-lg bg-zinc-900/95 border border-zinc-700 px-3 py-2 text-xs text-white shadow-xl"
      style={{ left: coords.x + 12, top: coords.y - 20 }}
    >
      <div className="font-medium">{operator}</div>
      {technology && <div className="text-blue-400">{technology}</div>}
      <div className="text-zinc-400">
        {antennaCount} antenna{antennaCount !== 1 ? 's' : ''}
      </div>
      <div className="text-zinc-500 tabular-nums">
        {lat.toFixed(4)}, {lon.toFixed(4)}
      </div>
    </div>
  )
}
