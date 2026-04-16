#!/usr/bin/env bash
# Common agent runner - called by per-agent wrapper scripts
# Usage: run-agent.sh <agent-name> <prompt-file> <timeout-minutes> [extra-context]
set -euo pipefail

# Cron has minimal PATH - ensure user-installed binaries are available
export PATH="/home/user/.local/bin:/home/user/.cargo/bin:/usr/local/bin:$PATH"

AGENT_NAME="${1:?Usage: run-agent.sh <agent-name> <prompt-file> <timeout-min> [extra-context]}"
PROMPT_FILE="${2:?Missing prompt file}"
TIMEOUT_MIN="${3:-30}"
EXTRA_CONTEXT="${4:-}"

REPO_DIR="/home/user/aegis"
LOG_DIR="${REPO_DIR}/agent_hq/local/logs"
LOCK_FILE="/tmp/aegis-agent-${AGENT_NAME}.lock"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M)
LOG_FILE="${LOG_DIR}/${AGENT_NAME}_${TIMESTAMP}.log"
WORKTREE_DIR="/tmp/aegis-agent-${AGENT_NAME}-$$"

mkdir -p "$LOG_DIR"

# Per-agent lock - only prevents the same agent from running twice
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[${TIMESTAMP}] ${AGENT_NAME}: same agent already running, skipping" >> "${LOG_DIR}/skipped.log"
    exit 0
fi

# Clean up worktree on exit
cleanup() {
    if [ -d "$WORKTREE_DIR" ]; then
        echo "[$(date +%Y-%m-%d_%H-%M)] Removing worktree ${WORKTREE_DIR}" >> "$LOG_FILE"
        cd "$REPO_DIR"
        git worktree remove --force "$WORKTREE_DIR" 2>/dev/null || rm -rf "$WORKTREE_DIR"
        git branch -D "agent/${AGENT_NAME}-$$" 2>/dev/null || true
    fi
    rm -f "$PROMPT_TMPFILE" 2>/dev/null || true
}
trap cleanup EXIT

echo "[${TIMESTAMP}] Starting ${AGENT_NAME}" | tee "$LOG_FILE"

cd "$REPO_DIR"

# Pull latest on main repo (fail gracefully if network issues)
git pull --rebase origin master >> "$LOG_FILE" 2>&1 || echo "Warning: git pull failed, continuing with current state" >> "$LOG_FILE"

# Auto-truncate bulletin board to last 20 entries, archive the rest
BULLETIN="${REPO_DIR}/agent_hq/coordination/bulletin.md"
ARCHIVE="${REPO_DIR}/agent_hq/coordination/bulletin-archive.md"
if [ -f "$BULLETIN" ]; then
    LINE_COUNT=$(wc -l < "$BULLETIN")
    if [ "$LINE_COUNT" -gt 40 ]; then
        HEADER=$(head -5 "$BULLETIN")
        MIDDLE_END=$((LINE_COUNT - 20))
        if [ "$MIDDLE_END" -gt 5 ]; then
            sed -n "6,${MIDDLE_END}p" "$BULLETIN" >> "$ARCHIVE"
            {
                echo "$HEADER"
                echo ""
                tail -20 "$BULLETIN"
            } > "${BULLETIN}.tmp"
            mv "${BULLETIN}.tmp" "$BULLETIN"
            cd "$REPO_DIR" && git add "$BULLETIN" "$ARCHIVE" && \
                git commit -m "Auto-truncate bulletin board (archived $(( MIDDLE_END - 5 )) lines)" --no-verify 2>/dev/null || true
        fi
    fi
fi

# Create isolated worktree so agents don't conflict with Robin's working directory
git worktree add "$WORKTREE_DIR" -b "agent/${AGENT_NAME}-$$" HEAD >> "$LOG_FILE" 2>&1
echo "[${TIMESTAMP}] Created worktree at ${WORKTREE_DIR}" >> "$LOG_FILE"

cd "$WORKTREE_DIR"

# Assemble prompt from agent-specific file + context files
PROMPT=""
PROMPT+="$(cat "${REPO_DIR}/${PROMPT_FILE}")"
PROMPT+=$'\n\n---\n\n'
PROMPT+="$(cat "${REPO_DIR}/agent_hq/context/aegis-overview.md")"

# Add extra context (assembled by the per-agent wrapper)
if [ -n "$EXTRA_CONTEXT" ]; then
    PROMPT+=$'\n\n---\n\n'
    PROMPT+="${EXTRA_CONTEXT}"
fi

# Write prompt to temp file to avoid shell argument length/quoting issues
PROMPT_TMPFILE=$(mktemp /tmp/aegis-agent-prompt.XXXXXX)
echo "$PROMPT" > "$PROMPT_TMPFILE"

# Run Claude in print mode with timeout
EXIT_CODE=0
timeout $((TIMEOUT_MIN * 60)) claude -p \
    --model claude-opus-4-7 \
    --allowedTools "Edit,Read,Write,Glob,Grep,Bash(*),WebSearch,WebFetch,Agent" \
    --dangerously-skip-permissions \
    < "$PROMPT_TMPFILE" \
    >> "$LOG_FILE" 2>&1 || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 124 ]; then
    echo "[$(date +%Y-%m-%d_%H-%M)] ${AGENT_NAME} TIMED OUT after ${TIMEOUT_MIN}m" | tee -a "$LOG_FILE"
else
    echo "[$(date +%Y-%m-%d_%H-%M)] ${AGENT_NAME} finished (exit=${EXIT_CODE})" | tee -a "$LOG_FILE"
fi

# Prune logs older than 7 days
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
