import { useSyncExternalStore } from 'react'

// Narrow phone layout (full-width sidebar, compact UI)
const mobileQuery = '(pointer: coarse) and (max-width: 768px)'
// Any touch device up to small laptop size (show on-screen WASD controls)
const touchQuery = '(pointer: coarse) and (max-width: 1024px)'

function subscribeMobile(cb: () => void) {
  const mql = window.matchMedia(mobileQuery)
  mql.addEventListener('change', cb)
  return () => mql.removeEventListener('change', cb)
}

function subscribeTouch(cb: () => void) {
  const mql = window.matchMedia(touchQuery)
  mql.addEventListener('change', cb)
  return () => mql.removeEventListener('change', cb)
}

export function useIsMobile() {
  return useSyncExternalStore(subscribeMobile, () => window.matchMedia(mobileQuery).matches, () => false)
}

export function useIsTouchDevice() {
  return useSyncExternalStore(subscribeTouch, () => window.matchMedia(touchQuery).matches, () => false)
}
