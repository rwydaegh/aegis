import { Component, type ReactNode } from 'react'
import * as Sentry from '@sentry/react'

interface Props { children: ReactNode; name: string }
interface State { hasError: boolean; error: string | null }

export class PanelErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    Sentry.captureException(error, {
      contexts: {
        react: { componentStack: errorInfo.componentStack ?? '' },
        panel: { name: this.props.name },
      },
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="py-3 px-2 text-center">
          <p className="text-destructive text-xs font-medium mb-1">
            {this.props.name} panel crashed
          </p>
          <p className="text-muted-foreground text-xs mb-2 break-words">
            {this.state.error}
          </p>
          <button
            className="text-xs text-primary hover:underline"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Retry
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
