import { AlignCenter, AlignJustify, LayoutGrid, Focus, Video, Globe } from 'lucide-react'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { useUIStore } from '@/stores/ui'
import type { CameraPreset } from '@/stores/ui'
import { cn } from '@/lib/utils'

const CAMERA_PRESETS: Array<{ preset: CameraPreset & string; label: string; icon: React.ReactNode }> = [
  { preset: 'front', label: 'Front view', icon: <AlignCenter className="size-4" /> },
  { preset: 'side', label: 'Side view', icon: <AlignJustify className="size-4" /> },
  { preset: 'top', label: 'Top view', icon: <LayoutGrid className="size-4" /> },
  { preset: 'focus', label: 'Focus body', icon: <Focus className="size-4" /> },
]

export default function CameraWidget() {
  const cameraMode = useUIStore(s => s.cameraMode)
  const setCameraPreset = useUIStore(s => s.setCameraPreset)
  const setCameraMode = useUIStore(s => s.setCameraMode)

  function handleCameraPreset(preset: CameraPreset & string) {
    setCameraMode('orbit')
    setCameraPreset(preset)
    // Clear after a tick so the controller fires on every click (even the same preset)
    setTimeout(() => setCameraPreset(null), 50)
  }

  return (
    <div data-tour="camera-widget" className="flex flex-col pointer-events-auto
      bg-card/80 backdrop-blur-md rounded-lg border border-border p-1">
      {CAMERA_PRESETS.map(({ preset, label, icon }) => (
        <Tooltip key={preset}>
          <TooltipTrigger
            onClick={() => handleCameraPreset(preset)}
            className={cn(
              'inline-flex items-center justify-center size-7 rounded transition-colors',
              'hover:bg-muted text-muted-foreground hover:text-foreground',
            )}
            aria-label={label}
          >
            {icon}
          </TooltipTrigger>
          <TooltipContent side="left">{label}</TooltipContent>
        </Tooltip>
      ))}

      <div className="h-px bg-border/60 my-0.5" />

      <Tooltip>
        <TooltipTrigger
          onClick={() => setCameraMode(cameraMode === 'orbit' ? 'follow' : 'orbit')}
          className={cn(
            'inline-flex items-center justify-center size-7 rounded transition-colors',
            cameraMode === 'follow'
              ? 'bg-primary/15 text-primary'
              : 'hover:bg-muted text-muted-foreground hover:text-foreground',
          )}
          aria-label="Toggle follow camera"
        >
          <Video className="size-4" />
        </TooltipTrigger>
        <TooltipContent side="left">{cameraMode === 'follow' ? 'Free camera' : 'Follow camera'}</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger
          onClick={() => setCameraMode(cameraMode === 'globe' ? 'orbit' : 'globe')}
          className={cn(
            'inline-flex items-center justify-center size-7 rounded transition-colors',
            cameraMode === 'globe'
              ? 'bg-primary/15 text-primary'
              : 'hover:bg-muted text-muted-foreground hover:text-foreground',
          )}
          aria-label="Toggle globe camera"
        >
          <Globe className="size-4" />
        </TooltipTrigger>
        <TooltipContent side="left">{cameraMode === 'globe' ? 'Free camera' : 'Globe camera'}</TooltipContent>
      </Tooltip>
    </div>
  )
}
