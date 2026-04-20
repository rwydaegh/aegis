#!/usr/bin/env bash
# Feature agent - ambitious product work, longer session.
# See prompts/feature-agent.md for the altitude spec.
set -euo pipefail

export PATH="/home/user/.local/bin:$PATH"
REPO_DIR="/home/user/aegis"

# Recent commits - bias against repeating very recent work.
RECENT=$(cd "$REPO_DIR" && git log --oneline --since="7 days ago" --no-merges -80 2>/dev/null)
if [ -z "$RECENT" ]; then
    RECENT=$(cd "$REPO_DIR" && git log --oneline -30 --no-merges)
fi

# Spinoff materials - business POV, reveals what Robin cares about.
# We ship the filenames so the agent can open the ones that look relevant
# rather than inlining thousands of lines of markdown into the prompt.
# spinoff/personal/ is excluded - career notes, not product signal.
SPINOFF_INDEX=$(cd "$REPO_DIR" && ls -1 spinoff/*.md spinoff/LATEST_GOOD/*.md 2>/dev/null | grep -v '/personal/' | head -40)

# Internal docs index (features.md and friends).
DOCS_INDEX=$(cd "$REPO_DIR" && ls -1 docs/internal/*.md 2>/dev/null | head -60)

EXTRA="$(cat "${REPO_DIR}/agent_hq/context/environment.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="$(cat "${REPO_DIR}/agent_hq/context/how-to-ship.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="$(cat "${REPO_DIR}/agent_hq/context/not-bugs.md")"
EXTRA+=$'\n\n---\n\n'
EXTRA+="## Recent commits (last 7 days, for de-duplication)"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${RECENT}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## spinoff/ contents (business POV — open what looks relevant)"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${SPINOFF_INDEX}"$'\n'
EXTRA+='```'$'\n\n'
EXTRA+="## docs/internal/ contents"$'\n'
EXTRA+='```'$'\n'
EXTRA+="${DOCS_INDEX}"$'\n'
EXTRA+='```'

# Longer timeout: ambitious work needs thinking + reading + building.
exec "${REPO_DIR}/agent_hq/local/run-agent.sh" \
    "feature-agent" \
    "agent_hq/prompts/feature-agent.md" \
    "120" \
    "$EXTRA"
