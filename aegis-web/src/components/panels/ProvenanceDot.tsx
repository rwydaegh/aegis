interface ProvenanceDotProps {
  confidence: number
  title?: string
}

function confidenceColor(c: number): string {
  if (c > 0.7) return '#22c55e'
  if (c > 0.4) return '#eab308'
  if (c > 0.2) return '#f97316'
  return '#ef4444'
}

export default function ProvenanceDot({ confidence, title }: ProvenanceDotProps) {
  return (
    <span
      className="inline-block w-2 h-2 rounded-full ml-1"
      style={{ backgroundColor: confidenceColor(confidence) }}
      title={title ?? `Confidence: ${(confidence * 100).toFixed(0)}%`}
    />
  )
}

export { confidenceColor }
