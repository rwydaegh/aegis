import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import StudioScene from './scene/StudioScene'
import { useStudioManifest } from './useStudioManifest'
import { useStudioPhantom } from './useStudioPhantom'
import { useStudioSlice } from './useStudioSlice'
import { useStudioBodyMap } from './useStudioBodyMap'
import { useStudioStore } from './store'

// Phase-1-minimal Coherent Exposure Studio: the hero scene + the data-fetch loop.
// The full HUD and parameter panels arrive in the next task.
export default function StudioModule() {
  // Data-fetch hooks (manifest seeds params -> slice + body map fetch follow).
  useStudioManifest()
  useStudioPhantom()
  useStudioSlice()
  useStudioBodyMap()

  const computing = useStudioStore((s) => s.computing)
  const [snapSignal, setSnapSignal] = useState(0)

  return (
    <div style={{ position: 'relative', height: '100vh', background: '#0a0a0f', color: '#ddd' }}>
      <Canvas camera={{ position: [-5, 2.5, 5], fov: 45 }}>
        <StudioScene snapSignal={snapSignal} />
      </Canvas>

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
          top: 16,
          right: 16,
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

      {computing && (
        <div
          style={{
            position: 'absolute',
            bottom: 16,
            left: 16,
            zIndex: 10,
            padding: '4px 12px',
            fontSize: 12,
            color: '#9fe',
            background: 'rgba(10,10,15,0.8)',
            border: '1px solid #2a2a36',
            borderRadius: 999,
          }}
        >
          Computing slice...
        </div>
      )}
    </div>
  )
}
