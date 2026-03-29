import { Component, type ReactNode } from 'react'
import * as Sentry from '@sentry/react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error: string | null }

export class SceneErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // WebGL context failures are environmental, not bugs -- skip Sentry
    if (error.message?.includes('WebGL')) return
    Sentry.captureException(error, { contexts: { react: { componentStack: errorInfo.componentStack ?? '' } } })
  }

  render() {
    if (this.state.hasError) {
      const isWebGL = this.state.error?.includes('WebGL')
      return this.props.fallback || (
        <div className="absolute inset-0 flex items-center justify-center bg-background">
          <div className="text-center max-w-md px-6">
            <p className="text-destructive font-medium mb-2">
              {isWebGL ? 'WebGL is not available' : '3D rendering failed'}
            </p>
            <p className="text-muted-foreground text-sm">
              {isWebGL
                ? 'Your browser or device does not support WebGL, which is required for the 3D viewer. Try using a different browser, enabling hardware acceleration, or updating your graphics drivers.'
                : this.state.error}
            </p>
            {!isWebGL && <p className="text-muted-foreground text-xs mt-2">Try refreshing the page</p>}
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
