import { useSceneStore } from '@/stores/scene'

export function VoxelsStatus() {
  const voxelData = useSceneStore((s) => s.voxelData)

  return (
    <div className="space-y-2 pt-1 border-t border-border">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Voxels
      </p>
      {voxelData ? (
        <p className="text-xs text-muted-foreground">
          Voxels loaded. Use the Layers panel to toggle material visibility.
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">
          No voxels loaded. Go to <span className="font-medium text-foreground">Scene &gt; Location</span> to load a location and generate voxel data.
        </p>
      )}
    </div>
  )
}
