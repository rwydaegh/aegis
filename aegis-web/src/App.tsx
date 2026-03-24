import LoginGate from '@/components/layout/LoginGate'
import AppInner from '@/components/layout/AppInner'

export default function App() {
  return (
    <LoginGate>
      <AppInner />
    </LoginGate>
  )
}
