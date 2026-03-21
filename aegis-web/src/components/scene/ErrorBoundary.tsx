import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error: string | null }

export class SceneErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="absolute inset-0 flex items-center justify-center bg-background">
          <div className="text-center">
            <p className="text-destructive font-medium mb-2">3D rendering failed</p>
            <p className="text-muted-foreground text-sm">{this.state.error}</p>
            <p className="text-muted-foreground text-xs mt-2">Try refreshing the page</p>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
