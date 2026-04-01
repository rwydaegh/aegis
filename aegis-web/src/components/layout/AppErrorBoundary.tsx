import { Component, type ReactNode } from 'react'
import * as Sentry from '@sentry/react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: string | null }

/**
 * Top-level error boundary that catches unhandled errors anywhere in the app
 * (Toolbar, HudOverlay, Sidebar, etc.) and shows a recovery UI instead of
 * a blank white screen.
 */
export class AppErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    Sentry.captureException(error, {
      contexts: {
        react: { componentStack: errorInfo.componentStack ?? '' },
      },
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen w-screen bg-background flex items-center justify-center">
          <div className="text-center max-w-md px-6">
            <p className="text-destructive font-medium mb-2">Something went wrong</p>
            <p className="text-muted-foreground text-sm mb-4">{this.state.error}</p>
            <button
              className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
              onClick={() => {
                this.setState({ hasError: false, error: null })
                window.location.reload()
              }}
            >
              Reload app
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
