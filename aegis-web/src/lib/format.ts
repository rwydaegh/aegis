export function formatSab(value: number): string {
  if (value === 0) return `0 W/m\u00b2`
  if (Math.abs(value) < 0.01) return `${value.toExponential(1)} W/m\u00b2`
  return `${value.toFixed(2)} W/m\u00b2`
}

export function formatPower(mw: number): string {
  if (Math.abs(mw) < 0.01) return `${mw.toExponential(1)} mW`
  return `${mw.toFixed(2)} mW`
}

export function formatDistance(m: number): string {
  return `${m.toFixed(1)} m`
}
