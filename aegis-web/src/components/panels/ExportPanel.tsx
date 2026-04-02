import * as Sentry from '@sentry/react'
import { useSimulationStore } from '@/stores/simulation'
import { fetchComplianceSummary, fetchDosimetryCsv, fetchDosimetryJson, fetchDosimetryNpz, exportConfig } from '@/api/client'
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
  const compliance = useSimulationStore(s => s.compliance)
  const sabArray = useSimulationStore(s => s.sabArray)

  const btnClass = "w-full px-3 py-1.5 rounded text-xs font-medium bg-muted hover:bg-muted/80 text-foreground disabled:opacity-40"

  const handleExportCsv = async () => {
    if (!sabArray) return
    try {
      const blob = await fetchDosimetryCsv()
      downloadBlob(blob, 'aegis_dosimetry.csv')
    } catch (err) {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', 'Failed to export dosimetry CSV')
    }
  }

  const handleExportJson = async () => {
    if (!sabArray) return
    try {
      const blob = await fetchDosimetryJson()
      downloadBlob(blob, 'aegis_dosimetry.json')
    } catch (err) {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', 'Failed to export dosimetry JSON')
    }
  }

  const handleExportNpz = async () => {
    if (!sabArray) return
    try {
      const blob = await fetchDosimetryNpz()
      downloadBlob(blob, 'aegis_dosimetry.npz')
    } catch (err) {
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', 'Failed to export dosimetry NPZ')
    }
  }

  const handleExportReport = async () => {
    try {
      const powerDbm = useSimulationStore.getState().powerDbm
      const { text } = await fetchComplianceSummary(powerDbm)
      downloadBlob(new Blob([text], { type: 'text/plain' }), 'aegis_compliance_report.txt')
    } catch (err) {
      Sentry.captureException(err)
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
    } catch (err) {
      Sentry.captureException(err)
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
        else useNotificationStore.getState().addNotification('error', 'Screenshot capture returned empty image')
      })
    } catch {
      // Fallback to canvas-only screenshot (captures 3D viewport only)
      // Select the largest canvas to avoid capturing small chart canvases (e.g. compliance heatmap)
      const allCanvases = Array.from(document.querySelectorAll('canvas'))
      const canvas = allCanvases.reduce<HTMLCanvasElement | null>((best, c) => {
        if (!best) return c
        return (c.width * c.height > best.width * best.height) ? c : best
      }, null)
      if (!canvas) {
        useNotificationStore.getState().addNotification('error', 'No canvas element found for screenshot')
        return
      }
      canvas.toBlob(blob => {
        if (blob) downloadBlob(blob, 'aegis_screenshot.png')
        else useNotificationStore.getState().addNotification('error', 'Screenshot capture returned empty image')
      })
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button className={btnClass} onClick={handleScreenshot}>
        Screenshot (PNG)
      </button>
      <button className={btnClass} onClick={handleExportCsv} disabled={!sabArray}>
        Export dosimetry (CSV)
      </button>
      <button className={btnClass} onClick={handleExportJson} disabled={!sabArray}>
        Export dosimetry (JSON)
      </button>
      <button className={btnClass} onClick={handleExportNpz} disabled={!sabArray}>
        Export dosimetry (NPZ)
      </button>
      <button className={btnClass} onClick={handleExportReport} disabled={!stats || !compliance}>
        Compliance report (TXT)
      </button>
      <hr className="border-border" />
      <button className={btnClass} onClick={handleExportConfig}>
        Export configuration (JSON)
      </button>
    </div>
  )
}
