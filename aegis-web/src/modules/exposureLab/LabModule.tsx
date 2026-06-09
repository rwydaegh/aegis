import { Link } from 'react-router-dom'
import LabScene from './scene/LabScene'
import LabHud from './LabHud'
import PosePanel from './panels/PosePanel'
import SourcePanel from './panels/SourcePanel'
import PhysicsPanel from './panels/PhysicsPanel'
import { useLabCompute } from './useLabCompute'

export default function LabModule() {
  // Drive the debounced re-pose -> dose pipeline while the lab is open.
  useLabCompute()

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0a0a0f', color: '#ddd' }}>
      <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
        <LabScene />
        <LabHud />
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
