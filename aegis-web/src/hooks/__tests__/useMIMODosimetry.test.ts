import { describe, it, expect, beforeEach } from 'vitest'
// Break the antenna<->simulation module init cycle (see useScenario.test.ts).
import '../../stores/simulation'
import { applyMIMOSummary } from '../useMIMODosimetry'
import { useMIMOStore } from '../../stores/mimo'
import { useNotificationStore } from '../../stores/notifications'
import type { MIMOComputeResponse, MIMOSummary } from '@/api/types'

function emptyResponse(): MIMOComputeResponse {
  return { user_ids: [], timings: {}, precoder_type: 'mrt' }
}

function emptySummary(): MIMOSummary {
  return { users: [], precoder: 'mrt', timings: {} }
}

describe('applyMIMOSummary ECBF warning propagation', () => {
  beforeEach(() => {
    useMIMOStore.getState().reset()
    useNotificationStore.getState().dismissByLevel('warning')
    useNotificationStore.getState().dismissByLevel('error')
    useNotificationStore.getState().dismissByLevel('info')
  })

  it('copies ecbf_warnings from response onto summary and commits to store', () => {
    const summary = emptySummary()
    const response: MIMOComputeResponse = {
      ...emptyResponse(),
      ecbf_warnings: [
        'ECBF constraint infeasible: minimum achievable P_abs (1.5 W) exceeds 0.5 W',
      ],
    }
    applyMIMOSummary(summary, response)
    const stored = useMIMOStore.getState().summaryStats
    expect(stored?.ecbf_warnings).toEqual(response.ecbf_warnings)
  })

  it('summary-level ecbf_warnings wins over response copy', () => {
    const summary: MIMOSummary = {
      ...emptySummary(),
      ecbf_warnings: ['summary-side warning'],
    }
    const response: MIMOComputeResponse = {
      ...emptyResponse(),
      ecbf_warnings: ['response-side warning'],
    }
    applyMIMOSummary(summary, response)
    expect(useMIMOStore.getState().summaryStats?.ecbf_warnings).toEqual(['summary-side warning'])
  })

  it('adds a user-visible notification when ecbf_warnings are present', () => {
    const summary = emptySummary()
    const response: MIMOComputeResponse = {
      ...emptyResponse(),
      ecbf_warnings: ['ECBF bisection failed to converge'],
    }
    applyMIMOSummary(summary, response)
    const notifs = useNotificationStore.getState().notifications ?? []
    const hit = notifs.find(n => /ECBF/i.test(n.message) || /ECBF/i.test(n.detail ?? ''))
    expect(hit).toBeTruthy()
  })

  it('does not set ecbf_warnings when neither source has any', () => {
    const summary = emptySummary()
    const response = emptyResponse()
    applyMIMOSummary(summary, response)
    const stored = useMIMOStore.getState().summaryStats
    expect(stored?.ecbf_warnings).toBeUndefined()
  })
})
