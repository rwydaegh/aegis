#!/usr/bin/env bash
# QA agent - tests the live production viewer with Playwright.
# The agent picks its own focus by reading docs/internal/features.md
# and agent_hq/coordination/qa-coverage.md; the shell script just
# injects recent-commits context.
set -euo pipefail

REPO_DIR="/home/user/aegis"

# Recent commits for context -- the agent uses these to bias focus
# toward recently changed areas.
RECENT=$(cd "$REPO_DIR" && git log --oneline --since="2 days ago" --no-merges -100 2>/dev/null)
if [ -z "$RECENT" ]; then
    RECENT=$(cd "$REPO_DIR" && git log --oneline -20 --no-merges)
fi

EXTRA="$(cat "${REPO_DIR}/agent_hq/context/not-bugs.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="## Recent commits (bias focus toward these if unsure)"$'\n\n'
EXTRA+='```'$'\n'
EXTRA+="${RECENT}"$'\n'
EXTRA+='```'

exec "${REPO_DIR}/agent_hq/local/run-agent.sh" \
    "qa-agent" \
    "agent_hq/prompts/qa-tester.md" \
    "240" \
    "$EXTRA"
