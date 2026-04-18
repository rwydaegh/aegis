import { useEffect, useRef, useState } from 'react'
import { useOptimizeStore } from '@/stores/optimize'
import { useSimulationStore } from '@/stores/simulation'
import { toScene, type ServerPos } from '@/api/coordinates'

const STEP_MS = 250

function extractPos(entry: { params?: Record<string, unknown> }): ServerPos | null {
  const raw = entry.params?.antenna_pos
  if (!Array.isArray(raw) || raw.length < 3) return null
  const [x, y, z] = raw as number[]
  if ([x, y, z].some(v => typeof v !== 'number' || !Number.isFinite(v))) return null
  return [x, y, z]
}

export default function HistoryScrubber() {
  const history = useOptimizeStore(s => s.history)
  const playbackIter = useOptimizeStore(s => s.playbackIter)
  const setPlaybackIter = useOptimizeStore(s => s.setPlaybackIter)
  const setAntennaPos = useSimulationStore(s => s.setAntennaPos)

  const [playing, setPlaying] = useState(false)
  const timerRef = useRef<number | null>(null)

  const total = history.length
  const activeIdx = playbackIter ?? total - 1
  const entry = history[activeIdx]
  const objective = entry?.objective ?? null
  const isBest = Boolean(entry?.isBest)

  useEffect(() => {
    if (!playing) {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current)
        timerRef.current = null
      }
      return
    }
    timerRef.current = window.setInterval(() => {
      const store = useOptimizeStore.getState()
      const hist = store.history
      if (hist.length === 0) return
      const current = store.playbackIter ?? hist.length - 1
      const next = current + 1
      if (next >= hist.length) {
        store.setPlaybackIter(hist.length - 1)
        setPlaying(false)
      } else {
        store.setPlaybackIter(next)
      }
    }, STEP_MS)
    return () => {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [playing])

  useEffect(() => {
    if (playbackIter === null) return
    const e = history[playbackIter]
    if (!e) return
    const server = extractPos(e)
    if (!server) return
    setAntennaPos(toScene(server))
  }, [playbackIter, history, setAntennaPos])

  if (total < 2) return null

  const handlePlay = () => {
    const store = useOptimizeStore.getState()
    if (store.playbackIter === null || store.playbackIter >= history.length - 1) {
      store.setPlaybackIter(0)
    }
    setPlaying(true)
  }

  const handlePause = () => setPlaying(false)

  const handleReset = () => {
    setPlaying(false)
    setPlaybackIter(null)
    const bestIdx = history.reduce(
      (acc, h, i) => (h.isBest ? i : acc),
      -1,
    )
    const best = bestIdx >= 0 ? history[bestIdx] : history[history.length - 1]
    const server = best ? extractPos(best) : null
    if (server) setAntennaPos(toScene(server))
  }

  const handleSlider = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPlaying(false)
    const v = parseInt(e.target.value, 10)
    if (!Number.isNaN(v)) setPlaybackIter(v)
  }

  return (
    <div className="space-y-1.5 border-t border-border pt-2">
      <div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
        <span>Replay iterations</span>
        <span>
          {activeIdx + 1} / {total}
          {isBest && <span className="ml-1 text-emerald-400 normal-case tracking-normal">(best)</span>}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={playing ? handlePause : handlePlay}
          className="px-2 py-1 rounded text-xs bg-muted hover:bg-muted/70 text-foreground border border-border"
          title={playing ? 'Pause' : 'Replay animation'}
          aria-label={playing ? 'Pause replay' : 'Play replay'}
        >
          {playing ? '❚❚' : '▶'}
        </button>
        <input
          type="range"
          min={0}
          max={total - 1}
          step={1}
          value={activeIdx}
          onChange={handleSlider}
          className="flex-1 accent-primary"
          aria-label="Iteration position"
        />
        <button
          onClick={handleReset}
          className="px-2 py-1 rounded text-xs bg-muted hover:bg-muted/70 text-muted-foreground border border-border"
          title="Return to best position"
        >
          Best
        </button>
      </div>
      {objective !== null && (
        <p className="text-[11px] text-muted-foreground">
          Peak S<sub>ab</sub> at this position:{' '}
          <span className="text-foreground font-mono">{objective.toExponential(2)}</span> W/m²
        </p>
      )}
    </div>
  )
}
