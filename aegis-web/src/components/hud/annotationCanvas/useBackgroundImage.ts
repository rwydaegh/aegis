import { useEffect, type RefObject } from 'react'

// Paint the screenshot onto the background canvas whenever the URL changes.
export function useBackgroundImage(
  canvasRef: RefObject<HTMLCanvasElement | null>,
  screenshotUrl: string,
  width: number,
  height: number,
): void {
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const img = new Image()
    img.onload = () => {
      ctx.clearRect(0, 0, width, height)
      ctx.drawImage(img, 0, 0, width, height)
    }
    img.src = screenshotUrl
  }, [canvasRef, screenshotUrl, width, height])
}
