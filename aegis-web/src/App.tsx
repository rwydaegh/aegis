import LoginGate from '@/components/layout/LoginGate'
import AppInner from '@/components/layout/AppInner'
import { AppErrorBoundary } from '@/components/layout/AppErrorBoundary'

export default function App() {
  return (
    <AppErrorBoundary>
      <LoginGate>
        <AppInner />
      </LoginGate>
    </AppErrorBoundary>
  )
}
