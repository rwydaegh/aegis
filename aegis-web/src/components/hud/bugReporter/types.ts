export interface BugReportResponse {
  issueNumber: number
  issueUrl: string
}

export type Phase = 'idle' | 'capturing' | 'open' | 'submitting' | 'success' | 'error'

export interface ScreenshotDimensions {
  width: number
  height: number
}
