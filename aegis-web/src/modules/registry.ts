import { lazy, type LazyExoticComponent, type ComponentType } from 'react'

export interface ModuleEntry {
  id: string
  label: string
  path: string
  component: LazyExoticComponent<ComponentType>
}

export const MODULES: ModuleEntry[] = [
  {
    id: 'lab',
    label: 'Exposure Lab',
    path: '/lab',
    component: lazy(() => import('./exposureLab/LabModule')),
  },
  {
    id: 'studio',
    label: 'Coherent Exposure Studio',
    path: '/studio',
    component: lazy(() => import('./coherentStudio/StudioModule')),
  },
]
