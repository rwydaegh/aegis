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

# Focus areas - weighted toward app quality over physics (physics has golden tests)
AREAS=(
    "React components: state management, error boundaries, stale closures, missing cleanup"
    "viewer feature completeness: trace user flows end-to-end, find dead code paths and unfinished features"
    "frontend data flow: Zustand store updates, API response handling, loading/error states"
    "viewer backend routes and API edge cases"
    "integration bridges (DiffeRT, Sionna) and ray tracing pipeline"
    "error handling and input validation at system boundaries"
    "physics kernels and compliance (all levels, ECBF, spatial averaging, ICNIRP limits)"
    "base station pipeline: scrapers, adapters, merge, coverage computation"
    "3D scene: Three.js resource lifecycle, geometry disposal, camera state, rendering"
    "type safety and API contracts across frontend and backend"
)

# Avoid repeating the same area back-to-back using a state file
STATE_FILE="${REPO_DIR}/agent_hq/local/.last_reviewed.json"
LAST_FOCUS=""
if [ -f "$STATE_FILE" ]; then
    LAST_FOCUS=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('last_focus',''))" 2>/dev/null || echo "")
fi

# Pick random focus, but skip if it matches last session
for attempt in 1 2 3; do
    INDEX=$((RANDOM % ${#AREAS[@]}))
    FOCUS="${AREAS[$INDEX]}"
    [ "$FOCUS" != "$LAST_FOCUS" ] && break
done

# Save current focus for next run
python3 -c "import json; json.dump({'last_focus': '''$FOCUS'''}, open('$STATE_FILE','w'))" 2>/dev/null || true

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
