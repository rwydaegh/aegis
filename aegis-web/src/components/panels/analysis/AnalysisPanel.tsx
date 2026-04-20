import { useState } from 'react'
import { AnalysisEmptyState } from '../AnalysisEmptyState'
import { Section } from './Section'
import { ExposureDistributionSection } from './ExposureDistributionSection'
import { SabHistogramSection } from './SabHistogramSection'
import { PowerSweepSection } from './PowerSweepSection'
import { FrequencySweepSection } from './FrequencySweepSection'
import { DistanceSweepSection } from './DistanceSweepSection'
import { ComplianceHeatmapSection } from './ComplianceHeatmapSection'
import { PathInsightsSection } from './PathInsightsSection'

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function AnalysisPanel() {
  const [openSection, setOpenSection] = useState<string | null>('distribution')

  function toggle(key: string) {
    setOpenSection((prev) => (prev === key ? null : key))
  }

  return (
    <div>
      <AnalysisEmptyState />
      <Section
        title="Exposure distribution"
        open={openSection === 'distribution'}
        onToggle={() => toggle('distribution')}
      >
        <ExposureDistributionSection />
      </Section>
      <Section
        title="SAB histogram"
        open={openSection === 'histogram'}
        onToggle={() => toggle('histogram')}
      >
        <SabHistogramSection />
      </Section>
      <Section
        title="Path insights"
        open={openSection === 'paths'}
        onToggle={() => toggle('paths')}
      >
        <PathInsightsSection />
      </Section>
      <Section
        title="Power sweep"
        open={openSection === 'power'}
        onToggle={() => toggle('power')}
      >
        <PowerSweepSection />
      </Section>
      <Section
        title="Frequency sweep"
        open={openSection === 'freq'}
        onToggle={() => toggle('freq')}
      >
        <FrequencySweepSection />
      </Section>
      <Section
        title="Distance sweep"
        open={openSection === 'distance'}
        onToggle={() => toggle('distance')}
      >
        <DistanceSweepSection />
      </Section>
      <Section
        title="Compliance heatmap"
        open={openSection === 'heatmap'}
        onToggle={() => toggle('heatmap')}
      >
        <ComplianceHeatmapSection />
      </Section>
    </div>
  )
}
