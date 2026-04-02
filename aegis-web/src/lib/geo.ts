import * as THREE from 'three'

/** WGS84 semi-major axis in meters. */
export const WGS84_A = 6378137.0

/** Convert lat/lon (degrees) + altitude (meters) to ECEF position. */
export function latLonToECEF(latDeg: number, lonDeg: number, altitude: number): THREE.Vector3 {
  const latRad = (latDeg * Math.PI) / 180
  const lonRad = (lonDeg * Math.PI) / 180
  const r = WGS84_A + altitude
  const cosLat = Math.cos(latRad)
  return new THREE.Vector3(
    r * cosLat * Math.cos(lonRad),
    r * cosLat * Math.sin(lonRad),
    r * Math.sin(latRad),
  )
}

/** Convert lat/lon (radians) + altitude (meters) to ECEF position. */
export function latLonRadToECEF(latRad: number, lonRad: number, altitude: number): THREE.Vector3 {
  const r = WGS84_A + altitude
  const cosLat = Math.cos(latRad)
  return new THREE.Vector3(
    r * cosLat * Math.cos(lonRad),
    r * cosLat * Math.sin(lonRad),
    r * Math.sin(latRad),
  )
}

/** Extract lat/lon (degrees) from an ECEF position. */
export function ecefToLatLon(pos: THREE.Vector3): { lat: number; lon: number } {
  const lon = Math.atan2(pos.y, pos.x) * (180 / Math.PI)
  const lat = Math.atan2(pos.z, Math.sqrt(pos.x * pos.x + pos.y * pos.y)) * (180 / Math.PI)
  return { lat, lon }
}
