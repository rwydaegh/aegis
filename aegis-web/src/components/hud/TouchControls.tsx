import { useCallback } from 'react'
import { touchKeys } from '@/lib/touchKeys'

interface BtnProps {
  code: string
  label: string
  className?: string
}

function Btn({ code, label, className = '' }: BtnProps) {
  const down = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    touchKeys.add(code)
  }, [code])

  const up = useCallback(() => {
    touchKeys.delete(code)
  }, [code])

  return (
    <button
      onPointerDown={down}
      onPointerUp={up}
      onPointerCancel={up}
      onPointerLeave={up}
      onContextMenu={(e) => e.preventDefault()}
      className={`touch-none select-none flex items-center justify-center
        rounded-xl bg-white/10 border border-white/20 backdrop-blur-sm
        text-white/70 font-bold text-sm active:bg-white/25 active:scale-95
        transition-transform ${className}`}
    >
      {label}
    </button>
  )
}

export default function TouchControls() {
  return (
    <div className="absolute bottom-[calc(16dvh+env(safe-area-inset-bottom,0px))] left-0 right-0 pointer-events-none z-20">
      {/* D-pad: left side */}
      <div className="absolute bottom-0 left-5 pointer-events-auto grid grid-cols-3 gap-1.5 w-[148px]">
        {/* Row 1: _ W _ */}
        <div />
        <Btn code="KeyW" label="W" className="h-11 w-11" />
        <div />
        {/* Row 2: A S D */}
        <Btn code="KeyA" label="A" className="h-11 w-11" />
        <Btn code="KeyS" label="S" className="h-11 w-11" />
        <Btn code="KeyD" label="D" className="h-11 w-11" />
      </div>

      {/* Actions: right side */}
      <div className="absolute bottom-0 right-5 pointer-events-auto flex flex-col items-center gap-2.5">
        {/* Q / E row */}
        <div className="flex gap-2.5">
          <Btn code="KeyQ" label="Q" className="h-12 w-12" />
          <Btn code="KeyE" label="E" className="h-12 w-12" />
        </div>
        {/* Jump */}
        <Btn code="Space" label="JUMP" className="h-11 w-20 text-xs tracking-widest" />
      </div>
    </div>
  )
}
