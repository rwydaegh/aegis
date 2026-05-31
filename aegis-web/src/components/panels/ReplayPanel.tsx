import { useRef } from 'react'
import { useReplayStore } from '@/stores/replay'
import { validateArtifact, type ReplayArtifact, type ReplayFrame } from '@/api/replayTypes'

const INPUT_CLASS = 'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground'
const LABEL_CLASS = 'text-xs text-muted-foreground block mb-1'
const BTN_CLASS = 'px-2 py-1.5 text-sm rounded border border-border bg-background hover:bg-muted text-foreground'

function uniq<T>(xs: T[]): T[] {
  return [...new Set(xs)]
}

/** Find the index of the first frame matching all given constraints. */
function findFrame(frames: ReplayFrame[], want: Partial<Pick<ReplayFrame, 'ue_index' | 'condition' | 'precoder'>>): number {
  const i = frames.findIndex(
    (f) =>
      (want.ue_index === undefined || f.ue_index === want.ue_index) &&
      (want.condition === undefined || f.condition === want.condition) &&
      (want.precoder === undefined || f.precoder === want.precoder),
  )
  return i >= 0 ? i : -1
}

function Loader() {
  const fileRef = useRef<HTMLInputElement>(null)
  const loadArtifact = useReplayStore((s) => s.loadArtifact)
  const setError = useReplayStore((s) => s.setError)
  const error = useReplayStore((s) => s.error)

  function ingest(text: string) {
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch (e) {
      setError(`JSON parse error: ${(e as Error).message}`)
      return
    }
    const err = validateArtifact(parsed)
    if (err) {
      setError(err)
      return
    }
    loadArtifact(parsed as ReplayArtifact)
  }

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

  function jump(want: Partial<Pick<ReplayFrame, 'ue_index' | 'condition' | 'precoder'>>) {
    const i = findFrame(frames, want)
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
