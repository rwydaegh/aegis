import { useEffect, useRef } from 'react'
import { useNotificationStore, type Notification } from '@/stores/notifications'
import { cn } from '@/lib/utils'

function ToastItem({ notification }: { notification: Notification }) {
  const dismiss = useNotificationStore(s => s.dismiss)
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => {
    // Auto-dismiss info and warning after 8 seconds, errors persist
    if (notification.level !== 'error') {
      timerRef.current = setTimeout(() => dismiss(notification.id), 8000)
    }
    return () => clearTimeout(timerRef.current)
  }, [notification.id, notification.level, dismiss])

  return (
    <div
      className={cn(
        'rounded-md border px-3 py-2 text-xs font-mono shadow-lg backdrop-blur-sm cursor-pointer',
        'animate-in slide-in-from-right-2 fade-in duration-200',
        notification.level === 'error' && 'bg-destructive/20 border-destructive/40 text-destructive',
        notification.level === 'warning' && 'bg-amber-500/15 border-amber-500/30 text-amber-400',
        notification.level === 'info' && 'bg-primary/15 border-primary/30 text-primary',
      )}
      onClick={() => dismiss(notification.id)}
    >
      <div>{notification.message}</div>
      {notification.detail && (
        <div className="mt-1 text-[10px] opacity-70 font-sans leading-tight">{notification.detail}</div>
      )}
    </div>
  )
}

export default function NotificationToast() {
  const notifications = useNotificationStore(s => s.notifications)

  if (notifications.length === 0) return null

  return (
    <div className="absolute bottom-14 right-14 flex flex-col gap-2 max-w-xs z-50 pointer-events-auto">
      {notifications.slice(-3).map(n => (
        <ToastItem key={n.id} notification={n} />
      ))}
    </div>
  )
}
