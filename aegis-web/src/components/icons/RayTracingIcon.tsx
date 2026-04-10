/** Custom icon for Ray Tracing section. Matches lucide style: 24x24, 2px stroke, round caps/joins. */
export function RayTracingIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="4" y1="4" x2="12" y2="12" />
      <line x1="12" y1="12" x2="20" y2="4" />
      <line x1="6" y1="16" x2="18" y2="16" />
    </svg>
  )
}
