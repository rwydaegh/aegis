import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense } from 'react'
import LoginGate from '@/components/layout/LoginGate'
import AppInner from '@/components/layout/AppInner'
import { AppErrorBoundary } from '@/components/layout/AppErrorBoundary'
import { MODULES } from '@/modules/registry'

export default function App() {
  return (
    <AppErrorBoundary>
      <LoginGate>
        <BrowserRouter>
          <Suspense fallback={null}>
            <Routes>
              <Route path="/" element={<AppInner />} />
              {MODULES.map((m) => (
                <Route key={m.id} path={m.path} element={<m.component />} />
              ))}
            </Routes>
          </Suspense>
        </BrowserRouter>
      </LoginGate>
    </AppErrorBoundary>
  )
}
