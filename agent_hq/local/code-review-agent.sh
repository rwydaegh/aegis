#!/usr/bin/env bash
# Code review agent - reviews recent changes for bugs
set -euo pipefail

export PATH="/home/user/.local/bin:$PATH"
REPO_DIR="/home/user/aegis"

# Recent commits
RECENT=$(cd "$REPO_DIR" && git log --oneline --since="12 hours ago" --no-merges -50 2>/dev/null)
if [ -z "$RECENT" ]; then
    RECENT=$(cd "$REPO_DIR" && git log --oneline -10 --no-merges)
fi

# Diff stats for recently changed files
SINCE_SHA=$(cd "$REPO_DIR" && git log --since="12 hours ago" --no-merges --format="%H" | tail -1)
if [ -n "$SINCE_SHA" ]; then
    DIFF=$(cd "$REPO_DIR" && git diff --stat "$SINCE_SHA"..HEAD 2>/dev/null || echo "")
else
    DIFF=$(cd "$REPO_DIR" && git diff --stat HEAD~10..HEAD 2>/dev/null || echo "")
fi

# Pick random review focus (same list as .github/workflows/code-review-agent.yml)
AREAS=(
    "kernels and physics correctness"
    "viewer backend routes and API"
    "geometry and mesh operations"
    "tissue properties and Fresnel"
    "coherent MIMO and ECBF"
    "compliance checks and limits"
    "integration bridges (DiffeRT, Sionna)"
    "test coverage gaps and edge cases"
    "error handling and input validation"
    "type safety and API contracts"
)
INDEX=$((RANDOM % ${#AREAS[@]}))
FOCUS="${AREAS[$INDEX]}"

# Code review agent uses all four context files
EXTRA="$(cat "${REPO_DIR}/agent_hq/context/environment.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="$(cat "${REPO_DIR}/agent_hq/context/how-to-ship.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="$(cat "${REPO_DIR}/agent_hq/context/not-bugs.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="## Your focus this session"$'\n\n'
EXTRA+="**${FOCUS}**"$'\n\n'
EXTRA+="## Recent changes"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${RECENT}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="Changed files:"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${DIFF}"$'\n'
EXTRA+='```'

exec "${REPO_DIR}/agent_hq/local/run-agent.sh" \
    "code-review-agent" \
    "agent_hq/prompts/code-reviewer.md" \
    "30" \
    "$EXTRA"
