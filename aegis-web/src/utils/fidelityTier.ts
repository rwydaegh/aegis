export type FidelityTier = 'full' | 'spatial' | 'geometric' | 'bound' | 'location_only'

export const TIER_COLORS: Record<FidelityTier, string> = {
  full: '#e0e7ff',        // blue-white
  spatial: '#60a5fa',     // blue-400
  geometric: '#2dd4bf',   // teal-400
  bound: '#fbbf24',       // amber-400
  location_only: '#6b7280', // gray-500
}

export const TIER_LABELS: Record<FidelityTier, string> = {
  full: 'Full fidelity (Level 6+)',
  spatial: 'Spatial ready (Level 3-5)',
  geometric: 'Geometric ready (Level 2)',
  bound: 'Bound only (Level 0-1)',
  location_only: 'Location only',
}

export const TIER_DESCRIPTIONS: Record<FidelityTier, string> = {
  full: 'All fields verified, real antenna pattern available',
  spatial: 'Core RF parameters verified, tilt estimated',
  geometric: 'Power, frequency, azimuth, height verified',
  bound: 'Power and frequency available, geometry estimated',
  location_only: 'Only coordinates known',
}

// Fields needed at each tier with minimum acceptable provenance
// A field is "confident" if its _source column value starts with "gov:" or "ocid"
// A field is "estimated" if source is "est:"
// A field is "missing" if source is "missing" or the value is NaN

export function computeFidelityTier(provenance: Record<string, string> | null): FidelityTier {
  if (!provenance) return 'location_only'

  const isConfident = (field: string): boolean => {
    const src = provenance[field]
    return !!src && src !== 'missing' && !src.startsWith('est:')
  }

  const isAvailable = (field: string): boolean => {
    const src = provenance[field]
    return !!src && src !== 'missing'
  }

  // Full: all fields confident + has real pattern
  if (isConfident('Power') && isConfident('Frequency') && isConfident('Azimuth') &&
      isConfident('CenterHeight') && isConfident('Gain') &&
      isAvailable('Electrical_Tilt') && isAvailable('Mechanical_Tilt') &&
      isAvailable('Horizontal_Beamwidth') && isAvailable('Vertical_Beamwidth') &&
      provenance['Pattern'] && provenance['Pattern'] !== '' &&
      provenance['Pattern'] !== 'synthetic:gaussian') {
    return 'full'
  }

  // Spatial: core RF params confident, tilt at least estimated
  if (isConfident('Power') && isConfident('Frequency') && isConfident('Azimuth') &&
      isConfident('CenterHeight') && isConfident('Gain') &&
      isAvailable('Electrical_Tilt') && isAvailable('Mechanical_Tilt')) {
    return 'spatial'
  }

  // Geometric: power, freq, azimuth, height confident
  if (isConfident('Power') && isConfident('Frequency') && isConfident('Azimuth') &&
      isConfident('CenterHeight')) {
    return 'geometric'
  }

  // Bound: power and frequency at least available
  if (isAvailable('Power') && isAvailable('Frequency')) {
    return 'bound'
  }

  return 'location_only'
}

// Compute what fields are missing/estimated to reach the next tier
export function computeUpgradePath(provenance: Record<string, string> | null): string[] {
  if (!provenance) return ['All RF parameters missing']

  const issues: string[] = []
  const src = (f: string) => provenance[f] || 'missing'

  // Only flag issues that actually block a higher tier. For tilts and
  // beamwidths, computeFidelityTier uses isAvailable (est is fine), so an
  // estimated value is not a blocker — only missing ones are.
  if (src('Power') === 'missing') issues.push('Need Power (EIRP)')
  else if (src('Power').startsWith('est:')) issues.push('EIRP is estimated')
  if (src('Frequency') === 'missing') issues.push('Need Frequency')
  if (src('Azimuth') === 'missing') issues.push('Need Azimuth')
  else if (src('Azimuth').startsWith('est:')) issues.push('Azimuth is estimated')
  if (src('CenterHeight') === 'missing') issues.push('Need antenna height')
  else if (src('CenterHeight').startsWith('est:')) issues.push('Height is estimated')
  if (src('Gain') === 'missing') issues.push('Need antenna gain')
  else if (src('Gain').startsWith('est:')) issues.push('Gain is estimated')
  if (src('Electrical_Tilt') === 'missing') issues.push('Need electrical tilt')
  if (src('Mechanical_Tilt') === 'missing') issues.push('Need mechanical tilt')
  if (src('Horizontal_Beamwidth') === 'missing') issues.push('Need horizontal beamwidth')
  if (src('Vertical_Beamwidth') === 'missing') issues.push('Need vertical beamwidth')

  const patternSrc = provenance['Pattern'] || ''
  if (!patternSrc || patternSrc === 'synthetic:gaussian') {
    issues.push('Need real antenna pattern file')
  }

  return issues
}

// Source URL mapping for data cards
export const SOURCE_URLS: Record<string, { label: string; url: string }> = {
  'gov:brussels': { label: 'BIPT Open Data', url: 'https://data.bipt.be/' },
  'gov:flanders': { label: 'BIPT Open Data', url: 'https://data.bipt.be/' },
  'gov:anfr': { label: 'ANFR (data.gouv.fr)', url: 'https://data.gouv.fr/' },
  'gov:antenneregister': { label: 'Antenneregister', url: 'https://antenneregister.nl/' },
  'gov:bnetza': { label: 'BNetzA EMF Database', url: 'https://www.bundesnetzagentur.de/' },
  'gov:mastedatabasen': { label: 'Mastedatabasen', url: 'https://mastedatabasen.dk/' },
  'gov:rtr': { label: 'RTR Senderkataster', url: 'https://www.senderkataster.at/' },
  'gov:acma': { label: 'ACMA RRL', url: 'https://www.acma.gov.au/' },
  'gov:uke': { label: 'UKE / BTSearch', url: 'https://btsearch.pl/' },
  'gov:vctel': { label: 'SETSI (Spain)', url: 'https://geoportal.minetur.gob.es/' },
  'gov:bakom': { label: 'BAKOM Funksender', url: 'https://www.bakom.admin.ch/' },
  'gov:ised': { label: 'ISED Canada', url: 'https://www.ic.gc.ca/' },
  'gov:ofcom_wtr': { label: 'Ofcom WTR', url: 'https://www.ofcom.org.uk/' },
  'gov:anatel_smp': { label: 'ANATEL (Brazil)', url: 'https://www.anatel.gov.br/' },
  'gov:cadastre_gsm': { label: 'ILR Cadastre (Luxembourg)', url: 'https://data.public.lu/' },
  'ocid': { label: 'OpenCellID', url: 'https://opencellid.org/' },
}

// Dosimetric impact weights (1-5) for display
export const FIELD_IMPACT: Record<string, number> = {
  Power: 5,
  Azimuth: 4,
  CenterHeight: 3,
  Frequency: 3,
  Gain: 2,
  Electrical_Tilt: 1,
  Mechanical_Tilt: 1,
  Horizontal_Beamwidth: 1,
  Vertical_Beamwidth: 1,
}

// Human-readable field labels
export const FIELD_LABELS: Record<string, string> = {
  Power: 'EIRP',
  Azimuth: 'Azimuth',
  CenterHeight: 'Height',
  Frequency: 'Frequency',
  FrequencyBand: 'Band',
  Gain: 'Gain',
  Electrical_Tilt: 'E-Tilt',
  Mechanical_Tilt: 'M-Tilt',
  Horizontal_Beamwidth: 'H-BW',
  Vertical_Beamwidth: 'V-BW',
}

// Field units
export const FIELD_UNITS: Record<string, string> = {
  Power: 'dBm',
  Azimuth: 'deg',
  CenterHeight: 'm',
  Frequency: 'MHz',
  Gain: 'dBi',
  Electrical_Tilt: 'deg',
  Mechanical_Tilt: 'deg',
  Horizontal_Beamwidth: 'deg',
  Vertical_Beamwidth: 'deg',
}
