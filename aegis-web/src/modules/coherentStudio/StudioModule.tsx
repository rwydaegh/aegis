import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import StudioScene from './scene/StudioScene'
import StudioPanel from './panels/StudioPanel'
import StudioHud from './StudioHud'
import StudioCaptureBridge, { type StudioCaptureFn } from './StudioCaptureBridge'
import { useStudioManifest } from './useStudioManifest'
import { useStudioPhantom } from './useStudioPhantom'
import { useStudioSlice } from './useStudioSlice'
import { useStudioVolume } from './useStudioVolume'
import { useStudioBodyMap } from './useStudioBodyMap'
import { useStudioCompliance } from './useStudioCompliance'
import { useStudioScales } from './useStudioScales'
import { useStudioStore, type StudioAspect } from './store'
import { findFigurePreset } from './figurePresets'
import type { ColorbarSpec } from './figureExport'

// Aspect-ratio (width:height) for each letterbox option; 'free' fills the column.
const ASPECT_WH: Record<Exclude<StudioAspect, 'free'>, [number, number]> = {
  '1:1': [1, 1],
  '4:5': [4, 5],
  '3:2': [3, 2],
  '16:9': [16, 9],
}

// Coherent Exposure Studio: the hero scene, the data-fetch loop, the grouped
// control panel, and the HUD overlay. The scene canvas can be letterboxed to a
// fixed aspect for figure capture; the capture re-renders at a target resolution
// and optionally composites the colour bars.
export default function StudioModule() {
  // Data-fetch hooks (manifest seeds params -> slice + body map fetch follow).
  useStudioManifest()
  useStudioPhantom()
  useStudioSlice()
  useStudioVolume()
  useStudioBodyMap()
  useStudioCompliance()

  const sceneRef = useRef<HTMLDivElement>(null)
  const captureRef = useRef<StudioCaptureFn | null>(null)

  const exportAspect = useStudioStore((s) => s.exportAspect)
  const exportLongEdgePx = useStudioStore((s) => s.exportLongEdgePx)
  const colorbarFieldInExport = useStudioStore((s) => s.colorbarFieldInExport)
  const colorbarBodyInExport = useStudioStore((s) => s.colorbarBodyInExport)
  const beam = useStudioStore((s) => s.beam)
  const sliceResult = useStudioStore((s) => s.sliceResult)
  const bodyMap = useStudioStore((s) => s.bodyMap)
  const showSlice = useStudioStore((s) => s.showSlice)
  const applyFigurePreset = useStudioStore((s) => s.applyFigurePreset)
  const scales = useStudioScales()

  // Open at /studio?preset=<name> to land straight on a figure panel (the URL is
  // the reproducer). Runs once on mount. Also exposes the store handle so a
  // headless driver (and power users) can script captures and camera poses.
  useEffect(() => {
    ;(window as unknown as { __studioStore?: typeof useStudioStore }).__studioStore = useStudioStore
    const name = new URLSearchParams(window.location.search).get('preset')
    if (!name) return
    const preset = findFigurePreset(name)
    if (preset) applyFigurePreset(preset)
  }, [applyFigurePreset])

  // Letterbox box size: largest rectangle of the chosen aspect that fits the scene
  // column. Recomputed on column resize and aspect change, so the scene reacts.
  const [box, setBox] = useState<{ w: number; h: number } | null>(null)
  useLayoutEffect(() => {
    const el = sceneRef.current
    if (!el) return
    const measure = () => {
      if (exportAspect === 'free') {
        setBox(null)
        return
      }
      const cw = el.clientWidth
      const ch = el.clientHeight
      const [aw, ah] = ASPECT_WH[exportAspect]
      const ar = aw / ah
      let w = cw
      let h = cw / ar
      if (h > ch) {
        h = ch
        w = ch * ar
      }
      setBox({ w: Math.round(w), h: Math.round(h) })
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [exportAspect])

  const capturePng = useCallback(() => {
    const bars: ColorbarSpec[] = []
    if (colorbarFieldInExport && showSlice && sliceResult) {
      bars.push({
        title: 'field',
        unit: scales.slice.logMode ? 'dB' : 'S',
        vmin: scales.slice.vmin,
        vmax: scales.slice.vmax,
        colormap: scales.slice.colormap,
        logMode: scales.slice.logMode,
        dynamicRangeDb: scales.slice.dynamicRangeDb,
      })
    }
    if (colorbarBodyInExport && bodyMap) {
      bars.push({
        title: 'S_ab',
        unit: scales.body.logMode ? 'dB' : 'abs.',
        vmin: scales.body.vmin,
        vmax: scales.body.vmax,
        colormap: scales.body.colormap,
        logMode: scales.body.logMode,
        dynamicRangeDb: scales.body.dynamicRangeDb,
      })
    }
    void captureRef.current?.({
      longEdgePx: exportLongEdgePx,
      bars,
      filename: `studio_${beam}.png`,
    })
  }, [colorbarFieldInExport, colorbarBodyInExport, showSlice, sliceResult, bodyMap, scales, exportLongEdgePx, beam])

  const innerStyle = box
    ? { width: box.w, height: box.h, position: 'relative' as const }
    : { width: '100%', height: '100%', position: 'relative' as const }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0a0a0f', color: '#ddd' }}>
      <div
        ref={sceneRef}
        style={{
          position: 'relative',
          flex: 1,
          minWidth: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        <div style={innerStyle}>
          <Canvas camera={{ position: [-5, 2.5, 5], fov: 45 }} gl={{ preserveDrawingBuffer: true, alpha: true }}>
            <StudioScene />
            <StudioCaptureBridge captureRef={captureRef} />
          </Canvas>
        </div>

        <StudioHud />

        <Link
          to="/"
          style={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 10,
            color: '#6cf',
            textDecoration: 'none',
            fontSize: 14,
          }}
        >
          &larr; Back to viewer
        </Link>

        <button
          type="button"
          onClick={capturePng}
          title="Save the current 3D view as a PNG, re-rendered at the export resolution"
          style={{
            position: 'absolute',
            top: 44,
            left: 16,
            zIndex: 10,
            padding: '6px 12px',
            fontSize: 13,
            color: '#ddd',
            background: '#1a1a22',
            border: '1px solid #2a2a36',
            borderRadius: 6,
            cursor: 'pointer',
          }}
        >
          Capture PNG
        </button>
      </div>

      <aside
        style={{
          width: 320,
          flexShrink: 0,
          height: '100%',
          overflowY: 'auto',
          borderLeft: '1px solid #1e1e26',
          background: '#0d0d12',
          padding: 16,
          boxSizing: 'border-box',
        }}
      >
        <h1 style={{ fontSize: 18, margin: '0 0 4px' }}>Coherent Exposure Studio</h1>
        <p style={{ fontSize: 13, color: '#888', margin: 0 }}>
          A coherent MIMO beam onto a phantom. Drag the slice gizmo in the scene, or steer the design
          space below.
        </p>
        <StudioPanel />
      </aside>
    </div>
  )
}
