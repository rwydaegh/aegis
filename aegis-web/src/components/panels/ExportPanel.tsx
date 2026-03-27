import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { fetchComplianceSummary, exportConfig } from '@/api/client'
import { useNotificationStore } from '@/stores/notifications'
import { collectState } from '@/lib/shareLink'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function ExportPanel() {
  const stats = useSimulationStore(s => s.stats)
  const sabArray = useSimulationStore(s => s.sabArray)

  const btnClass = "w-full px-3 py-1.5 rounded text-xs font-medium bg-muted hover:bg-muted/80 text-foreground disabled:opacity-40"

  const handleExportCsv = () => {
    if (!sabArray) return
    const geometry = useSceneStore.getState().bodyGeometry
    const pos = geometry?.getAttribute('position')
    const lines = ['x,y,z,sab_w_m2']

    for (let i = 0; i < sabArray.length; i++) {
      if (pos) {
        const v0 = i * 3
        const cx = (pos.getX(v0) + pos.getX(v0 + 1) + pos.getX(v0 + 2)) / 3
        const cy = (pos.getY(v0) + pos.getY(v0 + 1) + pos.getY(v0 + 2)) / 3
        const cz = (pos.getZ(v0) + pos.getZ(v0 + 1) + pos.getZ(v0 + 2)) / 3
        lines.push(`${cx.toFixed(6)},${cy.toFixed(6)},${cz.toFixed(6)},${sabArray[i]}`)
      } else {
        lines.push(`,,,${sabArray[i]}`)
      }
    }

    downloadBlob(new Blob([lines.join('\n')], { type: 'text/csv' }), 'aegis_sab.csv')
  }

  const handleExportJson = () => {
    if (!stats) return
    downloadBlob(
      new Blob([JSON.stringify(stats, null, 2)], { type: 'application/json' }),
      'aegis_stats.json',
    )
  }

  const handleExportReport = async () => {
    try {
      const powerDbm = useSimulationStore.getState().powerDbm
      const { text } = await fetchComplianceSummary(powerDbm)
      downloadBlob(new Blob([text], { type: 'text/plain' }), 'aegis_compliance_report.txt')
    } catch {
      useNotificationStore.getState().addNotification('error', 'Failed to fetch compliance report')
    }
  }

  const handleExportConfig = async () => {
    try {
      const state = collectState()
      const config = await exportConfig(state)
      const json = JSON.stringify(config, null, 2)
      const blob = new Blob([json], { type: 'application/json' })
      downloadBlob(blob, `aegis-config-${new Date().toISOString().slice(0, 10)}.json`)
    } catch {
      useNotificationStore.getState().addNotification('error', 'Failed to export configuration')
    }
  }

  const handleScreenshot = async () => {
    try {
      const html2canvas = (await import('html2canvas')).default
      const canvas = await html2canvas(document.body, {
        useCORS: true,
        scale: window.devicePixelRatio || 1,
        backgroundColor: null,
      })
      canvas.toBlob(blob => {
        if (blob) downloadBlob(blob, 'aegis_screenshot.png')
      })
    } catch {
      // Fallback to canvas-only screenshot
      const canvas = document.querySelector('canvas')
      if (!canvas) return
      canvas.toBlob(blob => {
        if (blob) downloadBlob(blob, 'aegis_screenshot.png')
      })
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button className={btnClass} onClick={handleScreenshot}>
        Screenshot (PNG)
      </button>
      <button className={btnClass} onClick={handleExportCsv} disabled={!sabArray}>
        Export Sab (CSV)
      </button>
      <button className={btnClass} onClick={handleExportJson} disabled={!stats}>
        Export stats (JSON)
      </button>
      <button className={btnClass} onClick={handleExportReport} disabled={!stats}>
        Compliance report (TXT)
      </button>
      <hr className="border-border" />
      <button className={btnClass} onClick={handleExportConfig}>
        Export configuration (JSON)
      </button>
    </div>
  )
}
