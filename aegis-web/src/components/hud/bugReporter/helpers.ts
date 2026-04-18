import html2canvas from 'html2canvas-pro'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useSceneStore } from '@/stores/scene'
import type { BugReportResponse, ScreenshotDimensions } from './types'

const FALLBACK_BUG_REPORTER = {
  max_width_ratio: 0.85,
  max_height_ratio: 0.55,
}

/** Collect a lightweight snapshot of the current app state for the issue body. */
export function collectState(): Record<string, unknown> {
  const sim = useSimulationStore.getState()
  const ui = useUIStore.getState()
  return {
    mode: sim.mode,
    freqGhz: sim.freqGhz,
    powerDbm: sim.powerDbm,
    fresnel: sim.fresnel,
    polarisation: sim.polarisation,
    curvature: sim.curvature,
    diffraction: sim.diffraction,
    skinModel: sim.skinModel,
    antennaPos: sim.antennaPos ? sim.antennaPos.join(', ') : null,
    cameraMode: ui.cameraMode,
    sidebarMode: ui.sidebarMode,
    legendScale: ui.legendScale,
  }
}

/** Full-page screenshot. html2canvas-pro supports oklch colors and
 *  captures WebGL canvases natively. One call, everything included. */
export async function captureFullPage(): Promise<string> {
  const canvas = await html2canvas(document.body, {
    useCORS: true,
    scale: Math.max(2, window.devicePixelRatio || 2),
    logging: false,
  })
  return canvas.toDataURL('image/png')
}

export async function postBugReport(payload: {
  screenshot: string
  description: string
  state: Record<string, unknown>
}): Promise<BugReportResponse> {
  const res = await fetch('/api/bug-report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`
    try {
      const data = await res.json()
      if (data?.error) msg = data.error
    } catch {
      // ignore parse errors
    }
    throw new Error(msg)
  }
  return res.json() as Promise<BugReportResponse>
}

/** Compute the display size for the annotation canvas so it fits the modal. */
export function computeScreenshotDimensions(img: HTMLImageElement): ScreenshotDimensions {
  const cfg = useSceneStore.getState().viewerConfig?.ui?.bug_reporter ?? FALLBACK_BUG_REPORTER
  let w = img.width
  let h = img.height
  const maxW = Math.round(window.innerWidth * cfg.max_width_ratio)
  const maxH = Math.round(window.innerHeight * cfg.max_height_ratio)
  if (w > maxW) { h = Math.round(h * (maxW / w)); w = maxW }
  if (h > maxH) { w = Math.round(w * (maxH / h)); h = maxH }
  return { width: w, height: h }
}

/** Convert a Blob to a data URL via FileReader. */
export function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}
