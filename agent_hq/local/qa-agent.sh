#!/usr/bin/env bash
# QA agent - tests the live production viewer with Playwright
set -euo pipefail

REPO_DIR="/home/user/aegis"

# Pick random focus area (same list as .github/workflows/qa-agent.yml)
AREAS=(
    "Antenna placement and positioning"
    "Phantom movement and rotation"
    "Dosimetry HUD and compliance display"
    "Scene loading and environment"
    "Ray tracing integration"
    "Stochastic propagation"
    "MIMO multi-user mode"
    "Parameter controls and frequency bands"
    "Export and analysis panels"
    "Camera controls and viewpoints"
    "Base station panel"
    "Tissue and skin model settings"
    "Quantities and display modes"
    "Layers panel and visibility toggles"
    "Voxel environment and 3D tiles"
)
INDEX=$((RANDOM % ${#AREAS[@]}))
FOCUS="${AREAS[$INDEX]}"

# Recent commits
RECENT=$(cd "$REPO_DIR" && git log --oneline --since="2 days ago" --no-merges -100 2>/dev/null)
if [ -z "$RECENT" ]; then
    RECENT=$(cd "$REPO_DIR" && git log --oneline -20 --no-merges)
fi

# QA agent uses: qa-tester prompt + aegis-overview + not-bugs + focus + commits
EXTRA="$(cat "${REPO_DIR}/agent_hq/context/not-bugs.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="## Your focus area this session"$'\n\n'
EXTRA+="**${FOCUS}**"$'\n\n'
EXTRA+="Start here, but don't limit yourself. Use the app naturally."$'\n\n'
EXTRA+="## Recent changes (prioritize testing these)"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${RECENT}"$'\n'
EXTRA+='```'

exec "${REPO_DIR}/agent_hq/local/run-agent.sh" \
    "qa-agent" \
    "agent_hq/prompts/qa-tester.md" \
    "240" \
    "$EXTRA"
