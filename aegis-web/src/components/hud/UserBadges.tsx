import { useMIMOStore } from '@/stores/mimo'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'

export default function UserBadges() {
  const users = useMIMOStore(s => s.users)
  const userList = [...users.values()]
  if (userList.length === 0) return null

  const computed = userList.filter(u => u.compliant !== null)
  const compliant = computed.filter(u => u.compliant === true)
  const allComputed = computed.length === userList.length && userList.length > 0

  if (!allComputed) {
    return (
      <Badge variant="outline" className="text-muted-foreground border-muted-foreground/30 font-mono text-xs">
        {userList.length} users
      </Badge>
    )
  }

  const allPass = compliant.length === computed.length
  return (
    <Tooltip>
      <TooltipTrigger>
        <div className="flex items-center gap-1.5">
          <Badge
            className={
              allPass
                ? 'bg-success/20 text-success border-success/30 font-mono text-xs'
                : 'bg-destructive/20 text-destructive border-destructive/30 font-mono text-xs'
            }
          >
            {compliant.length}/{computed.length}
          </Badge>
          <div className="flex gap-0.5">
            {userList.map(u => (
              <span
                key={u.userId}
                className="size-1.5 rounded-full"
                style={{
                  backgroundColor:
                    u.compliant === null ? '#666' : u.compliant ? '#4ade80' : '#f87171',
                }}
              />
            ))}
          </div>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        {compliant.length} of {computed.length} users compliant
      </TooltipContent>
    </Tooltip>
  )
}
