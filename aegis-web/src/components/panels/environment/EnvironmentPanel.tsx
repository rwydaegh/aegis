import { useEnvironmentStore } from '@/stores/environment'
import { EnvironmentEmptyState } from '../EnvironmentEmptyState'
import { SourceSelector } from './SourceSelector'
import { VoxelsStatus } from './VoxelsStatus'
import { LocationSearch } from './LocationSearch'
import { RadiusControl } from './RadiusControl'
import { ReloadButton } from './ReloadButton'
import { OSMOptions } from './OSMOptions'
import { GeoJsonUpload } from './GeoJsonUpload'
import { CoverageStatus } from './CoverageStatus'
import { LoadingIndicator } from './LoadingIndicator'
import { ExportButton } from './ExportButton'
import { ErrorMessage } from './ErrorMessage'
import { TerrainSection } from './TerrainSection'

export default function EnvironmentPanel() {
  const source = useEnvironmentStore((s) => s.source)
  const location = useEnvironmentStore((s) => s.location)

  const showLocationAndRadius = source === 'osm' || source === '3dtiles'

  return (
    <div className="space-y-3 text-sm">
      <SourceSelector />
      <EnvironmentEmptyState />

      {source === 'voxels' && <VoxelsStatus />}

      {showLocationAndRadius && <LocationSearch />}
      {showLocationAndRadius && <RadiusControl />}

      {source === 'osm' && location && <ReloadButton />}

      {source === 'osm' && <OSMOptions />}
      {source === 'osm' && <GeoJsonUpload />}

      {/* 3D Tiles options - geometric error only affects backend RT mesh, hidden from globe view */}

      {source === 'coverage' && <CoverageStatus />}

      <LoadingIndicator />

      {showLocationAndRadius && location && <ExportButton />}

      <ErrorMessage />

      <TerrainSection />
    </div>
  )
}
