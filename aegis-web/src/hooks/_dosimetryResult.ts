import * as Sentry from '@sentry/react'
import type { ComputeResult } from '@/api/client'
import { isNetworkError } from '@/api/client'
import { useSimulationStore } from '@/stores/simulation'
import { useNotificationStore } from '@/stores/notifications'

/**
 * Apply a successful ComputeResult to the simulation store. Shared by every
 * hook that drives a compute pipeline whose backend returns the standard
 * {sab, stats, arrays} shape and writes into useSimulationStore.
 */
export function applyDosimetryResult(result: ComputeResult): void {
  const { sab, stats, arrays } = result
  useNotificationStore.getState().dismissByLevel('error')
  useSimulationStore.getState().setResults(sab, stats, {
    sabAveraged: arrays['sab_4cm2'],
    sinc: arrays['sinc_local'],
    sincAveraged: arrays['sinc_wb'],
    sab1cm2Averaged: arrays['sab_1cm2'],
  })
}

export interface DosimetryErrorContext {
  /** Abort controller whose signal.reason is inspected for timeout. */
  controller: AbortController
  /** Timeout in ms, surfaced in the timeout message. */
  timeoutMs: number
  /** Human label used in error notifications (e.g. 'MIMO', 'Base station'). */
  label: string
  /** Label used in the network-error sentence (lowercased variant of label by default). */
  networkLabel?: string
  /** Optional hint appended to the timeout notification after a single space. */
  timeoutHint?: string
}

/**
 * Handle an error thrown by a compute pipeline. Centralises the AbortError /
 * isNetworkError / Sentry.captureException ladder that used to live in every
 * dosimetry hook (single-user, MIMO, base stations).
 */
export function handleDosimetryError(
  err: unknown,
  ctx: DosimetryErrorContext,
): void {
  const error = err as Error
  if (error?.name === 'AbortError') {
    if (ctx.controller.signal.reason === 'timeout') {
      const hint = ctx.timeoutHint ? ` ${ctx.timeoutHint}` : ''
      useNotificationStore.getState().addNotification(
        'warning',
        `${ctx.label} compute timed out after ${ctx.timeoutMs / 1000}s.${hint}`,
      )
    }
    return
  }
  if (isNetworkError(err)) {
    const netLabel = ctx.networkLabel ?? ctx.label.toLowerCase()
    useNotificationStore.getState().addNotification(
      'warning',
      `Network error during ${netLabel} compute. Check your connection and try again.`,
    )
    return
  }
  Sentry.captureException(err)
  useNotificationStore.getState().addNotification(
    'error',
    `${ctx.label} compute failed: ${error?.message ?? err}`,
    'This error has been reported and will be fixed automatically using AI. Most issues are fixed in less than 30 minutes.',
  )
}
