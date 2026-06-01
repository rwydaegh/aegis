import { useRef, useState } from 'react'
import { useReplayStore } from '@/stores/replay'
import {
  validateArtifact,
  findFrameIndex,
  type ReplayArtifact,
  type FrameQuery,
} from '@/api/replayTypes'

const INPUT_CLASS = 'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground'
const LABEL_CLASS = 'text-xs text-muted-foreground block mb-1'
const BTN_CLASS = 'px-2 py-1.5 text-sm rounded border border-border bg-background hover:bg-muted text-foreground'

function uniq<T>(xs: T[]): T[] {
  return [...new Set(xs)]
}

function Loader() {
  const fileRef = useRef<HTMLInputElement>(null)
  const loadArtifact = useReplayStore((s) => s.loadArtifact)
  const setError = useReplayStore((s) => s.setError)
  const error = useReplayStore((s) => s.error)
  const [url, setUrl] = useState('')

  function ingest(text: string): ReplayArtifact | null {
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch (e) {
      setError(`JSON parse error: ${(e as Error).message}`)
      return null
    }
    const err = validateArtifact(parsed)
    if (err) {
      setError(err)
      return null
    }
    const a = parsed as ReplayArtifact
    loadArtifact(a)
    return a
  }

  function loadFromUrl(u: string) {
    if (!u) return
    fetch(u)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.text()
      })
      .then(ingest)
      .catch((e) => setError(`fetch ${u}: ${(e as Error).message}`))
  }
  // Note: autoload from ?artifact=<url> (and deep-link frame params) is handled
  // globally in AppInner so it works regardless of which panel is open.

  return (
    <div>
      <label className={LABEL_CLASS}>Load replay artifact (.json)</label>
      <input
        ref={fileRef}
        type="file"
        accept="application/json,.json"
        className={INPUT_CLASS}
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (!file) return
          file.text().then(ingest)
        }}
      />
      <div className="flex gap-1 mt-1.5">
        <input
          type="text"
          placeholder="or fetch a served URL, e.g. /factory.json"
          className={INPUT_CLASS}
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') loadFromUrl(url)
          }}
        />
        <button className={BTN_CLASS} onClick={() => loadFromUrl(url)}>
          Load
        </button>
      </div>
      {error && <p className="text-xs text-destructive mt-2">{error}</p>}
      <p className="text-xs text-muted-foreground mt-2">
        Produced by a headless run, e.g. <code>build_replay_artifact.py</code>.
      </p>
    </div>
  )
}

function Controls() {
  const artifact = useReplayStore((s) => s.artifact)!
  const frameIndex = useReplayStore((s) => s.frameIndex)
  const setFrameIndex = useReplayStore((s) => s.setFrameIndex)
  const clear = useReplayStore((s) => s.clear)
  const frames = artifact.frames
  const frame = frames[frameIndex]

  const conditions = uniq(frames.map((f) => f.condition))
  const precoders = uniq(frames.map((f) => f.precoder))
  const ueIndices = uniq(frames.map((f) => f.ue_index)).sort((a, b) => a - b)
  const realizations = uniq(frames.map((f) => f.realization ?? 0)).sort((a, b) => a - b)

  // Keep the current realization fixed when changing any other dimension.
  function jump(want: FrameQuery) {
    const i = findFrameIndex(frames, { realization: frame.realization, ...want })
    if (i >= 0) setFrameIndex(i)
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">
          {(artifact.meta?.title as string) ?? 'Replay'}
        </span>
        <button className={BTN_CLASS} onClick={() => clear()}>
          Exit
        </button>
      </div>

      {realizations.length > 1 && (
        <div>
          <label className={LABEL_CLASS}>Realization (scatterer layout)</label>
          <select
            className={INPUT_CLASS}
            value={frame.realization ?? 0}
            onChange={(e) => jump({ realization: Number(e.target.value) })}
          >
            {realizations.map((r) => (
              <option key={r} value={r}>Realization {r}</option>
            ))}
          </select>
        </div>
      )}

      {conditions.length > 1 && (
        <div>
          <label className={LABEL_CLASS}>Condition</label>
          <select
            className={INPUT_CLASS}
            value={frame.condition}
            onChange={(e) => jump({ condition: e.target.value, precoder: frame.precoder, ue_index: frame.ue_index })}
          >
            {conditions.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      )}

      {precoders.length > 1 && (
        <div>
          <label className={LABEL_CLASS}>Precoder</label>
          <select
            className={INPUT_CLASS}
            value={frame.precoder}
            onChange={(e) => jump({ precoder: e.target.value, condition: frame.condition, ue_index: frame.ue_index })}
          >
            {precoders.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
      )}

      {ueIndices.length > 1 && (
        <div>
          <label className={LABEL_CLASS}>Served UE</label>
          <select
            className={INPUT_CLASS}
            value={frame.ue_index}
            onChange={(e) => jump({ ue_index: Number(e.target.value), condition: frame.condition, precoder: frame.precoder })}
          >
            {ueIndices.map((u) => (
              <option key={u} value={u}>UE {u}</option>
            ))}
          </select>
        </div>
      )}

      <div>
        <label className={LABEL_CLASS}>
          Frame {frameIndex + 1} / {frames.length}
        </label>
        <input
          type="range"
          min={0}
          max={frames.length - 1}
          value={frameIndex}
          className="w-full"
          onChange={(e) => setFrameIndex(Number(e.target.value))}
        />
        <div className="flex gap-2 mt-1">
          <button className={BTN_CLASS} onClick={() => setFrameIndex(frameIndex - 1)}>
            Prev
          </button>
          <button className={BTN_CLASS} onClick={() => setFrameIndex(frameIndex + 1)}>
            Next
          </button>
        </div>
      </div>

      {frame.scalars && Object.keys(frame.scalars).length > 0 && (
        <div>
          <label className={LABEL_CLASS}>Readouts</label>
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(frame.scalars).map(([k, v]) => (
                <tr key={k}>
                  <td className="text-muted-foreground pr-2">{k}</td>
                  <td className="text-foreground text-right font-mono">
                    {typeof v === 'number' ? formatNum(v) : String(v)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function formatNum(v: number): string {
  if (v === 0) return '0'
  const abs = Math.abs(v)
  if (abs < 1e-3 || abs >= 1e5) return v.toExponential(2)
  return v.toPrecision(4)
}

export default function ReplayPanel() {
  const artifact = useReplayStore((s) => s.artifact)
  return (
    <div className="flex flex-col gap-4 p-1">
      <Loader />
      {artifact && <Controls />}
    </div>
  )
}
