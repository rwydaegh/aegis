import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import StudioScene from './scene/StudioScene'
import StudioPanel from './panels/StudioPanel'
import StudioHud from './StudioHud'
import { useStudioManifest } from './useStudioManifest'
import { useStudioPhantom } from './useStudioPhantom'
import { useStudioSlice } from './useStudioSlice'
import { useStudioBodyMap } from './useStudioBodyMap'

// Coherent Exposure Studio: the hero scene, the data-fetch loop, the grouped
// control panel, and the HUD overlay. Layout mirrors exposureLab/LabModule: a
// full-bleed Canvas column with absolute overlays, plus a fixed-width side panel.
export default function StudioModule() {
  // Data-fetch hooks (manifest seeds params -> slice + body map fetch follow).
  useStudioManifest()
  useStudioPhantom()
  useStudioSlice()
  useStudioBodyMap()

  // Bumped by the "snap to BS axis" button; the scene's CameraRig reframes on it.
  const [snapSignal, setSnapSignal] = useState(0)

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0a0a0f', color: '#ddd' }}>
      <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
        <Canvas camera={{ position: [-5, 2.5, 5], fov: 45 }}>
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
