import { useMIMOStore } from '@/stores/mimo'
import { AntennaList } from './AntennaList'
import { AddAntennaButton } from './AddAntennaButton'
import { AntennaEditor } from './AntennaEditor'

export default function AntennasPanel() {
  const mimoEnabled = useMIMOStore(s => s.enabled)

  if (mimoEnabled) {
    return (
      <p className="text-xs text-muted-foreground">
        MIMO mode active. Antenna config is managed in the MIMO and Antenna tabs.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <AntennaList />
      <AddAntennaButton />
      <AntennaEditor />
    </div>
  )
}
