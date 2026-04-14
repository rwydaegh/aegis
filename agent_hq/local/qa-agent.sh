#!/usr/bin/env bash
# QA agent - tests the live production viewer with Playwright
set -euo pipefail

REPO_DIR="/home/user/aegis"

# --- Build focus areas: mix of recent changes + stable rotation ---

# 1. Extract focus areas from recent PRs (last 48h)
#    These are the titles of merged PRs, which describe what changed.
RECENT_PRS=$(cd "$REPO_DIR" && gh pr list --state merged --limit 8 \
    --json title,mergedAt,files \
    --jq '[.[] | select(.mergedAt > (now - 48*3600 | strftime("%Y-%m-%dT%H:%M:%SZ")))] | .[:5] | .[].title' 2>/dev/null || true)

# 2. Stable rotation of existing features (reduced from 15 to 10, no overlap)
STABLE_AREAS=(
    "Antenna placement, WASD movement, and phantom rotation"
    "Dosimetry HUD, compliance panel, and quantity toggles"
    "OSM environment loading and terrain"
    "Ray tracing and stochastic propagation"
    "MIMO multi-user mode"
    "Parameter controls, frequency bands, and exposure scenarios"
    "Export, analysis panels, and data quality"
    "Camera controls and viewpoints"
    "Base station panel and coverage maps"
    "Bug reporter (Shift+B), keyboard help (?), and guided tour"
)

# 3. Pick focus: 50% chance recent PR, 50% chance stable rotation
#    If no recent PRs, always pick from stable rotation.
FOCUS=""
if [ -n "$RECENT_PRS" ] && [ $((RANDOM % 2)) -eq 0 ]; then
    # Pick a random recent PR title as the focus
    mapfile -t PR_ARRAY <<< "$RECENT_PRS"
    PR_INDEX=$((RANDOM % ${#PR_ARRAY[@]}))
    FOCUS="Recently shipped: ${PR_ARRAY[$PR_INDEX]}"
else
    INDEX=$((RANDOM % ${#STABLE_AREAS[@]}))
    FOCUS="${STABLE_AREAS[$INDEX]}"
fi

# Recent commits for context
RECENT=$(cd "$REPO_DIR" && git log --oneline --since="2 days ago" --no-merges -100 2>/dev/null)
if [ -z "$RECENT" ]; then
    RECENT=$(cd "$REPO_DIR" && git log --oneline -20 --no-merges)
fi

# Build the extra context block
EXTRA="$(cat "${REPO_DIR}/agent_hq/context/not-bugs.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="## Your focus area this session"$'\n\n'
EXTRA+="**${FOCUS}**"$'\n\n'
EXTRA+="Start with this area, but also spend 2-3 interactions smoke-testing"$'\n'
EXTRA+="other features you encounter along the way. Use the app naturally."$'\n\n'
EXTRA+="## Recent changes (always worth a quick check)"$'\n\n'
EXTRA+="These features shipped in the last 48 hours. Even if they are not your"$'\n'
EXTRA+="focus area, give them a quick poke if you come across them naturally."$'\n\n'
EXTRA+='```'$'\n'
EXTRA+="${RECENT}"$'\n'
EXTRA+='```'

exec "${REPO_DIR}/agent_hq/local/run-agent.sh" \
    "qa-agent" \
    "agent_hq/prompts/qa-tester.md" \
    "240" \
    "$EXTRA"
