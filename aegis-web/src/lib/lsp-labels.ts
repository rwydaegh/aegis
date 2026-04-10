/** Pretty labels and LaTeX for LSP parameter keys. */

export interface LSPMeta {
  key: string
  label: string
  latex: string
}

const LSP_META: Record<string, LSPMeta> = {
  SF_dB:   { key: 'SF_dB',   label: 'Shadow fading',                latex: '\\sigma_\\text{SF}\\;(\\text{dB})' },
  KF_dB:   { key: 'KF_dB',   label: 'Rician K-factor',              latex: 'K\\;(\\text{dB})' },
  DS:      { key: 'DS',      label: 'Delay spread',                  latex: '\\tau_\\text{DS}\\;(\\text{s})' },
  ASA_deg: { key: 'ASA_deg', label: 'Azimuth spread (arrival)',      latex: '\\sigma_\\text{ASA}\\;(\\degree)' },
  ASD_deg: { key: 'ASD_deg', label: 'Azimuth spread (departure)',    latex: '\\sigma_\\text{ASD}\\;(\\degree)' },
  ESA_deg: { key: 'ESA_deg', label: 'Elevation spread (arrival)',    latex: '\\sigma_\\text{ESA}\\;(\\degree)' },
  ESD_deg: { key: 'ESD_deg', label: 'Elevation spread (departure)',  latex: '\\sigma_\\text{ESD}\\;(\\degree)' },
  XPR_dB:  { key: 'XPR_dB',  label: 'Cross-polarization ratio',     latex: '\\text{XPR}\\;(\\text{dB})' },
}

export const LSP_KEYS = Object.keys(LSP_META)

export function getLSPMeta(key: string): LSPMeta {
  return LSP_META[key] ?? { key, label: key, latex: `\\text{${key}}` }
}
