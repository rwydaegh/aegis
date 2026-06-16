import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import StudioScene from './scene/StudioScene'
import StudioPanel from './panels/StudioPanel'
import StudioHud from './StudioHud'
import { useStudioManifest } from './useStudioManifest'
import { useStudioPhantom } from './useStudioPhantom'
import { useStudioSlice } from './useStudioSlice'
import { useStudioVolume } from './useStudioVolume'
import { useStudioBodyMap } from './useStudioBodyMap'

// Coherent Exposure Studio: the hero scene, the data-fetch loop, the grouped
// control panel, and the HUD overlay. Layout mirrors exposureLab/LabModule: a
// full-bleed Canvas column with absolute overlays, plus a fixed-width side panel.
export default function StudioModule() {
  // Data-fetch hooks (manifest seeds params -> slice + body map fetch follow).
  useStudioManifest()
  useStudioPhantom()
  useStudioSlice()
  useStudioVolume()
  useStudioBodyMap()

  // Bumped by the "snap to BS axis" button; the scene's CameraRig reframes on it.
  const [snapSignal, setSnapSignal] = useState(0)

  // The scene column; we query its <canvas> to grab the rendered pixels.
  const sceneRef = useRef<HTMLDivElement>(null)

  // Capture the WebGL canvas to a PNG and download it. preserveDrawingBuffer on
  // the Canvas keeps the last frame readable; alpha keeps a transparent
  // background transparent in the export. A double rAF ensures the latest frame
  // (e.g. just after toggling screenshot mode) is the one captured.
  const capturePng = useCallback(() => {
    const canvas = sceneRef.current?.querySelector('canvas')
    if (!canvas) return
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        canvas.toBlob((blob) => {
          if (!blob) return
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = 'studio_fig.png'
          a.click()
          URL.revokeObjectURL(url)
        }, 'image/png')
      }),
    )
  }, [])

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0a0a0f', color: '#ddd' }}>
      <div ref={sceneRef} style={{ position: 'relative', flex: 1, minWidth: 0 }}>
        <Canvas camera={{ position: [-5, 2.5, 5], fov: 45 }} gl={{ preserveDrawingBuffer: true, alpha: true }}>
          <StudioScene snapSignal={snapSignal} />
        </Canvas>

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
          onClick={() => setSnapSignal((n) => n + 1)}
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
          Snap to BS axis
        </button>

        <button
          type="button"
          onClick={capturePng}
          title="Save the current 3D view as a PNG (transparent in screenshot mode)"
          style={{
            position: 'absolute',
            top: 80,
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
