import { Link } from 'react-router-dom'
import LabScene from './scene/LabScene'
import PosePanel from './panels/PosePanel'
import SourcePanel from './panels/SourcePanel'
import PhysicsPanel from './panels/PhysicsPanel'
import { useLabStore } from './store'
import { useLabCompute } from './useLabCompute'

export default function LabModule() {
  // Drive the debounced re-pose -> dose pipeline while the lab is open.
  useLabCompute()
  const computing = useLabStore((s) => s.computing)

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0a0a0f', color: '#ddd' }}>
      <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
        <LabScene />
        {computing && (
          <div
            style={{
              position: 'absolute',
              top: 16,
              right: 16,
              zIndex: 10,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 12px',
              borderRadius: 6,
              background: 'rgba(13, 13, 18, 0.85)',
              border: '1px solid #1e1e26',
              color: '#9cf',
              fontSize: 13,
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: '#6cf',
                animation: 'labPulse 1s ease-in-out infinite',
              }}
            />
            Computing dose...
            <style>{'@keyframes labPulse{0%,100%{opacity:0.3}50%{opacity:1}}'}</style>
          </div>
        )}
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
      </div>

      {/* Panels (pose / source / physics) mount here in later tasks. */}
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
        <h1 style={{ fontSize: 18, margin: '0 0 8px' }}>Exposure Lab</h1>
        <p style={{ fontSize: 13, color: '#888', margin: 0 }}>
          Click a joint handle in the scene or pick one below, then rotate.
        </p>
        <PosePanel />
        <SourcePanel />
        <PhysicsPanel />
      </aside>
    </div>
  )
}
