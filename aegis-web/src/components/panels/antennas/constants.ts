import type { ElementPattern } from '@/api/types'

export const PATTERN_OPTIONS: { value: ElementPattern; label: string }[] = [
  { value: 'short_dipole', label: 'Dipole' },
  { value: 'patch', label: 'Patch' },
  { value: 'isotropic', label: 'Iso' },
]

export const inputClass =
  'w-full bg-muted/50 border border-border rounded px-1.5 py-1 text-[11px] text-foreground font-mono'
export const labelClass = 'text-[10px] text-muted-foreground block mb-0.5'
export const sectionClass =
  'text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1'
