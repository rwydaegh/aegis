#!/usr/bin/env bash
# Manager agent - daily supervisor. Watches across worker runs.
# See prompts/manager.md for tier definitions and what it can act on.
set -euo pipefail

export PATH="/home/user/.local/bin:$PATH"
REPO_DIR="/home/user/aegis"

# Last 48h of merged PRs and closed issues - the manager's primary signal.
MERGED_PRS=$(cd "$REPO_DIR" && gh pr list --state merged --limit 50 \
    --json number,title,mergedAt,headRefName,additions,deletions,changedFiles \
    --jq "[.[] | select(.mergedAt > \"$(date -u -d '48 hours ago' +%Y-%m-%dT%H:%M:%SZ)\")]" \
    2>/dev/null || echo "[]")

CLOSED_UNMERGED=$(cd "$REPO_DIR" && gh pr list --state closed --limit 30 \
    --json number,title,mergedAt,headRefName,closedAt \
    --jq "[.[] | select(.mergedAt == null and .closedAt > \"$(date -u -d '48 hours ago' +%Y-%m-%dT%H:%M:%SZ)\")]" \
    2>/dev/null || echo "[]")

CLOSED_ISSUES=$(cd "$REPO_DIR" && gh issue list --state closed --limit 30 \
    --json number,title,labels,closedAt \
    --jq "[.[] | select(.closedAt > \"$(date -u -d '48 hours ago' +%Y-%m-%dT%H:%M:%SZ)\")]" \
    2>/dev/null || echo "[]")

OPEN_ISSUES=$(cd "$REPO_DIR" && gh issue list --state open --limit 20 \
    --json number,title,labels,createdAt 2>/dev/null || echo "[]")

# Current cron schedule - so the manager can see its own fleet layout.
CRON=$(crontab -l 2>/dev/null | grep "aegis-agent" || echo "(no aegis-agent cron entries)")

# Current worker prompts - so the manager can evaluate them against output.
PROMPT_FILES=$(cd "$REPO_DIR" && ls -1 agent_hq/prompts/*.md)

# Manager's own prior log - inject the tail so the agent sees its previous
# decisions directly in its prompt. The "read log first, respect prior
# decisions, don't thrash" rule depends on this being visible.
MANAGER_LOG_FILE="${REPO_DIR}/agent_hq/coordination/manager-log.md"
if [ -f "$MANAGER_LOG_FILE" ]; then
    # Last ~400 lines covers roughly the last week of entries.
    PRIOR_LOG=$(tail -400 "$MANAGER_LOG_FILE")
else
    PRIOR_LOG="(manager-log.md does not exist yet — this is the first run)"
fi

# Recent prompt edits (for the 24h cooldown check).
RECENT_PROMPT_EDITS=$(cd "$REPO_DIR" && git log --since="48 hours ago" \
    --pretty=format:"%h %ar %s" -- agent_hq/prompts/ 2>/dev/null \
    || echo "(no recent prompt edits)")

EXTRA="$(cat "${REPO_DIR}/agent_hq/context/environment.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="$(cat "${REPO_DIR}/agent_hq/context/how-to-ship.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="## Last 48h merged PRs"$'\n'
EXTRA+='```json'$'\n'
EXTRA+="${MERGED_PRS}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## Last 48h closed-unmerged PRs (collision signal)"$'\n'
EXTRA+='```json'$'\n'
EXTRA+="${CLOSED_UNMERGED}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## Last 48h closed issues"$'\n'
EXTRA+='```json'$'\n'
EXTRA+="${CLOSED_ISSUES}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## Currently open issues"$'\n'
EXTRA+='```json'$'\n'
EXTRA+="${OPEN_ISSUES}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## Current cron schedule"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${CRON}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## Worker prompt files (read any that look relevant)"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${PROMPT_FILES}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## Prompt edits in the last 48h (for the 24h-cooldown check)"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${RECENT_PROMPT_EDITS}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## Your prior manager-log.md (READ THIS FIRST — your memory across runs)"$'\n'
EXTRA+='```markdown'$'\n'
EXTRA+="${PRIOR_LOG}"$'\n'
EXTRA+='```'

# Manager mostly reads + makes small prompt/bulletin edits; 30m is plenty.
exec "${REPO_DIR}/agent_hq/local/run-agent.sh" \
    "manager" \
    "agent_hq/prompts/manager.md" \
    "30" \
    "$EXTRA"
