export function formatSab(value: number): string {
  if (value === 0) return `0 W/m\u00b2`
  const abs = Math.abs(value)
  if (abs >= 0.1) return `${value.toFixed(2)} W/m\u00b2`
  if (abs >= 1e-4) return `${(value * 1e3).toFixed(2)} mW/m\u00b2`
  return `${value.toExponential(2)} W/m\u00b2`
}

export function formatPower(mw: number): string {
  if (mw === 0) return '0 mW'
  const abs = Math.abs(mw)
  if (abs >= 0.1) return `${mw.toFixed(2)} mW`
  if (abs >= 1e-4) return `${(mw * 1e3).toFixed(2)} \u00b5W`
  if (abs >= 1e-7) return `${(mw * 1e6).toFixed(2)} nW`
  return `${mw.toExponential(2)} mW`
}

export function formatDistance(m: number): string {
  return `${m.toFixed(1)} m`
}
