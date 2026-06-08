import { create } from 'zustand'
import type { DosimetryStats } from '@/api/types'
import type { LabRig } from './api'

export type LabGender = 'neutral' | 'male' | 'female'
export type LabSourceMode = 'near' | 'far'
export type LabDiffractionModel = 'none' | 'gelu' | 'fock'

export interface LabPhysicsState {
  diffractionModel: LabDiffractionModel
  selfShadow: boolean
  curvature: boolean
  fresnel: boolean
  polarisation: boolean
}

interface LabState {
  // Pose / shape
  gender: LabGender
  betas: number[]
  pose: number[]
  selectedJoint: number | null
  preset: string | null

  // Source
  sourceMode: LabSourceMode
  // near
  patternId: string
  phonePos: [number, number, number]
  yaw: number
  pitch: number
  roll: number
  powerW: number
  // far
  thetaInc: number
  phiInc: number
  polAngle: number

  // Physics
  diffractionModel: LabDiffractionModel
  selfShadow: boolean
  curvature: boolean
  fresnel: boolean
  polarisation: boolean
  freqMhz: number

  // Results
  sab: Float32Array | null
  stats: DosimetryStats | null
  arrays: Record<string, Float32Array>
  vertexHash: number | null

  // Rig / posed mesh
  rig: LabRig | null
  posedVertices: Float32Array | null
  posedNormals: Float32Array | null

  // UI
  baking: boolean
  computing: boolean

  // Actions
  setGender: (gender: LabGender) => void
  setBetas: (betas: number[]) => void
  setPose: (pose: number[]) => void
  setSelectedJoint: (joint: number | null) => void
  setPreset: (preset: string | null) => void
  setSourceMode: (mode: LabSourceMode) => void
  setPatternId: (id: string) => void
  setPhonePos: (pos: [number, number, number]) => void
  setYaw: (yaw: number) => void
  setPitch: (pitch: number) => void
  setRoll: (roll: number) => void
  setPowerW: (powerW: number) => void
  setThetaInc: (thetaInc: number) => void
  setPhiInc: (phiInc: number) => void
  setPolAngle: (polAngle: number) => void
  setPhysics: (patch: Partial<LabPhysicsState>) => void
  setFreqMhz: (freqMhz: number) => void
  setResults: (
    sab: Float32Array,
    stats: DosimetryStats,
    arrays: Record<string, Float32Array>,
  ) => void
  clearResults: () => void
  setRig: (rig: LabRig | null) => void
  setPosedMesh: (vertices: Float32Array | null, normals: Float32Array | null, vertexHash?: number | null) => void
  setBaking: (baking: boolean) => void
  setComputing: (computing: boolean) => void
}

export const useLabStore = create<LabState>()((set) => ({
  gender: 'neutral',
  betas: new Array(10).fill(0),
  pose: new Array(66).fill(0),
  selectedJoint: null,
  preset: null,

  sourceMode: 'near',
  patternId: 'dipole',
  phonePos: [0.2, 0, 0.3],
  yaw: 0,
  pitch: 0,
  roll: 0,
  powerW: 1,
  thetaInc: 1.2,
  phiInc: 0,
  polAngle: 0,

  diffractionModel: 'fock',
  selfShadow: true,
  curvature: false,
  fresnel: true,
  polarisation: false,
  freqMhz: 3500,

  sab: null,
  stats: null,
  arrays: {},
  vertexHash: null,

  rig: null,
  posedVertices: null,
  posedNormals: null,

  baking: false,
  computing: false,

  setGender: (gender) => set({ gender }),
  setBetas: (betas) => set({ betas }),
  setPose: (pose) => set({ pose }),
  setSelectedJoint: (selectedJoint) => set({ selectedJoint }),
  setPreset: (preset) => set({ preset }),
  setSourceMode: (sourceMode) => set({ sourceMode }),
  setPatternId: (patternId) => set({ patternId }),
  setPhonePos: (phonePos) => set({ phonePos }),
  setYaw: (yaw) => set({ yaw }),
  setPitch: (pitch) => set({ pitch }),
  setRoll: (roll) => set({ roll }),
  setPowerW: (powerW) => set({ powerW }),
  setThetaInc: (thetaInc) => set({ thetaInc }),
  setPhiInc: (phiInc) => set({ phiInc }),
  setPolAngle: (polAngle) => set({ polAngle }),
  setPhysics: (patch) => set(patch),
  setFreqMhz: (freqMhz) => set({ freqMhz }),
  setResults: (sab, stats, arrays) => set({ sab, stats, arrays }),
  clearResults: () => set({ sab: null, stats: null, arrays: {} }),
  setRig: (rig) => set({ rig }),
  setPosedMesh: (posedVertices, posedNormals, vertexHash) =>
    set(vertexHash !== undefined ? { posedVertices, posedNormals, vertexHash } : { posedVertices, posedNormals }),
  setBaking: (baking) => set({ baking }),
  setComputing: (computing) => set({ computing }),
}))
