import type { EnvironmentSource } from '@/stores/environment'

export const SOURCE_OPTIONS: { value: EnvironmentSource; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'voxels', label: 'Voxels' },
  { value: 'osm', label: 'OSM' },
  { value: '3dtiles', label: '3D Tiles' },
  { value: 'coverage', label: 'Coverage' },
]

export const labelClass = 'text-xs text-muted-foreground block mb-1'
export const inputClass =
  'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground'
