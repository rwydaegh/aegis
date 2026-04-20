#!/usr/bin/env bash
# Polish agent - small UX polish, state bugs, half-baked features.
# Runs often, short session. See prompts/polish-agent.md for scope.
set -euo pipefail

export PATH="/home/user/.local/bin:$PATH"
REPO_DIR="/home/user/aegis"

# Recent commits so the agent can bias toward recently changed code.
RECENT=$(cd "$REPO_DIR" && git log --oneline --since="3 days ago" --no-merges -50 2>/dev/null)
if [ -z "$RECENT" ]; then
    RECENT=$(cd "$REPO_DIR" && git log --oneline -20 --no-merges)
fi

# Open issues (rare on this repo, but include for completeness).
ISSUES=$(cd "$REPO_DIR" && gh issue list --state open --limit 10 --json number,title,labels \
    --jq '.[] | "#\(.number) [\(.labels | map(.name) | join(","))] \(.title)"' 2>/dev/null || echo "")

EXTRA="$(cat "${REPO_DIR}/agent_hq/context/environment.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="$(cat "${REPO_DIR}/agent_hq/context/how-to-ship.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="$(cat "${REPO_DIR}/agent_hq/context/not-bugs.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="## Recent commits"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${RECENT}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## Open issues"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${ISSUES}"$'\n'
EXTRA+='```'

exec "${REPO_DIR}/agent_hq/local/run-agent.sh" \
    "polish-agent" \
    "agent_hq/prompts/polish-agent.md" \
    "45" \
    "$EXTRA"
