import { useState, useCallback } from 'react'
import * as Sentry from '@sentry/react'
import { useSimulationStore } from '@/stores/simulation'
import { fetchComplianceSummary, fetchDosimetryCsv, fetchDosimetryJson, fetchDosimetryNpz, exportConfig, isNetworkError } from '@/api/client'
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

function handleExportError(err: unknown, label: string) {
  if (isNetworkError(err)) {
    useNotificationStore.getState().addNotification('warning', `Network error during ${label}. Check your connection and try again.`)
    return
  }
  Sentry.captureException(err)
  useNotificationStore.getState().addNotification('error', `Failed to ${label}`)
}

type ExportKey = 'csv' | 'json' | 'npz' | 'report' | 'config' | 'screenshot'

// ---------------------------------------------------------------------------
// Per-format export helpers (module scope so they do not re-create each render)
// ---------------------------------------------------------------------------

async function exportDosimetryCsv() {
  try {
    const blob = await fetchDosimetryCsv()
    downloadBlob(blob, 'aegis_dosimetry.csv')
  } catch (err) {
    handleExportError(err, 'export dosimetry CSV')
  }
}

async function exportDosimetryJson() {
  try {
    const blob = await fetchDosimetryJson()
    downloadBlob(blob, 'aegis_dosimetry.json')
  } catch (err) {
    handleExportError(err, 'export dosimetry JSON')
  }
}

async function exportDosimetryNpz() {
  try {
    const blob = await fetchDosimetryNpz()
    downloadBlob(blob, 'aegis_dosimetry.npz')
  } catch (err) {
    handleExportError(err, 'export dosimetry NPZ')
  }
}

async function exportComplianceReport() {
  try {
    const powerDbm = useSimulationStore.getState().powerDbm
    const { text } = await fetchComplianceSummary(powerDbm)
    downloadBlob(new Blob([text], { type: 'text/plain' }), 'aegis_compliance_report.txt')
  } catch (err) {
    handleExportError(err, 'fetch compliance report')
  }
}

async function exportConfiguration() {
  try {
    const state = collectState()
    const config = await exportConfig(state)
    const json = JSON.stringify(config, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    downloadBlob(blob, `aegis-config-${new Date().toISOString().slice(0, 10)}.json`)
  } catch (err) {
    handleExportError(err, 'export configuration')
  }
}

/** Pick the largest canvas on the page (fallback when html2canvas fails). */
function pickLargestCanvas(): HTMLCanvasElement | null {
  const allCanvases = Array.from(document.querySelectorAll('canvas'))
  return allCanvases.reduce<HTMLCanvasElement | null>((best, c) => {
    if (!best) return c
    return (c.width * c.height > best.width * best.height) ? c : best
  }, null)
}

function saveCanvasScreenshot(canvas: HTMLCanvasElement) {
  canvas.toBlob(blob => {
    if (blob) downloadBlob(blob, 'aegis_screenshot.png')
    else useNotificationStore.getState().addNotification('error', 'Screenshot capture returned empty image')
  })
}

async function captureScreenshot() {
  try {
    const html2canvas = (await import('html2canvas')).default
    const canvas = await html2canvas(document.body, {
      useCORS: true,
      scale: window.devicePixelRatio || 1,
      backgroundColor: null,
    })
    saveCanvasScreenshot(canvas)
  } catch {
    // Fallback to canvas-only screenshot (captures 3D viewport only)
    // Select the largest canvas to avoid capturing small chart canvases (e.g. compliance heatmap)
    const canvas = pickLargestCanvas()
    if (!canvas) {
      useNotificationStore.getState().addNotification('error', 'No canvas element found for screenshot')
      return
    }
    saveCanvasScreenshot(canvas)
  }
}

export default function ExportPanel() {
  const stats = useSimulationStore(s => s.stats)
  const compliance = useSimulationStore(s => s.compliance)
  const sabArray = useSimulationStore(s => s.sabArray)
  const [busy, setBusy] = useState<Set<ExportKey>>(new Set())

  const withBusy = useCallback((key: ExportKey, fn: () => Promise<void>) => {
    return async () => {
      if (busy.has(key)) return
      setBusy(prev => new Set(prev).add(key))
      try {
        await fn()
      } finally {
        setBusy(prev => {
          const next = new Set(prev)
          next.delete(key)
          return next
        })
      }
    }
  }, [busy])

  const guardSab = useCallback(
    (fn: () => Promise<void>) => async () => { if (sabArray) await fn() },
    [sabArray],
  )

  const handleExportCsv = withBusy('csv', guardSab(exportDosimetryCsv))
  const handleExportJson = withBusy('json', guardSab(exportDosimetryJson))
  const handleExportNpz = withBusy('npz', guardSab(exportDosimetryNpz))
  const handleExportReport = withBusy('report', exportComplianceReport)
  const handleExportConfig = withBusy('config', exportConfiguration)
  const handleScreenshot = withBusy('screenshot', captureScreenshot)

  const btnClass = "w-full px-3 py-1.5 rounded text-xs font-medium bg-muted hover:bg-muted/80 text-foreground disabled:opacity-40"

  return (
    <div className="flex flex-col gap-2">
      <button className={btnClass} onClick={handleScreenshot} disabled={busy.has('screenshot')}>
        {busy.has('screenshot') ? 'Capturing...' : 'Screenshot (PNG)'}
      </button>
      <button className={btnClass} onClick={handleExportCsv} disabled={!sabArray || busy.has('csv')}>
        {busy.has('csv') ? 'Exporting...' : 'Export dosimetry (CSV)'}
      </button>
      <button className={btnClass} onClick={handleExportJson} disabled={!sabArray || busy.has('json')}>
        {busy.has('json') ? 'Exporting...' : 'Export dosimetry (JSON)'}
      </button>
      <button className={btnClass} onClick={handleExportNpz} disabled={!sabArray || busy.has('npz')}>
        {busy.has('npz') ? 'Exporting...' : 'Export dosimetry (NPZ)'}
      </button>
      <button className={btnClass} onClick={handleExportReport} disabled={!stats || !compliance || busy.has('report')}>
        {busy.has('report') ? 'Generating...' : 'Compliance report (TXT)'}
      </button>
      <hr className="border-border" />
      <button className={btnClass} onClick={handleExportConfig} disabled={busy.has('config')}>
        {busy.has('config') ? 'Exporting...' : 'Export configuration (JSON)'}
      </button>
    </div>
  )
}
