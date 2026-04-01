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
LOCK_FILE="/tmp/aegis-agent.lock"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M)
LOG_FILE="${LOG_DIR}/${AGENT_NAME}_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

# Mutual exclusion - only one agent at a time
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[${TIMESTAMP}] ${AGENT_NAME}: another agent is running, skipping" >> "${LOG_DIR}/skipped.log"
    exit 0
fi

# Clean up dirty working directory on exit (timeout kills can leave uncommitted edits)
cleanup() {
    cd "$REPO_DIR"
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        echo "[$(date +%Y-%m-%d_%H-%M)] Cleaning dirty working directory" >> "$LOG_FILE"
        git checkout -- . 2>/dev/null || true
        git clean -fd 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "[${TIMESTAMP}] Starting ${AGENT_NAME}" | tee "$LOG_FILE"

cd "$REPO_DIR"

# Clean any leftover dirty state from a previous killed run
cleanup

# Pull latest (fail gracefully if network issues)
git pull --rebase origin master >> "$LOG_FILE" 2>&1 || echo "Warning: git pull failed, continuing with current state" >> "$LOG_FILE"

# Assemble prompt from agent-specific file + context files
PROMPT_FILE_PATH="${REPO_DIR}/${PROMPT_FILE}"
PROMPT=""
PROMPT+="$(cat "$PROMPT_FILE_PATH")"
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
# Pipe prompt via stdin to avoid shell injection from git log messages
EXIT_CODE=0
timeout $((TIMEOUT_MIN * 60)) claude -p \
    --model claude-opus-4-6 \
    --allowedTools "Edit,Read,Write,Glob,Grep,Bash(*),WebSearch,WebFetch,Agent" \
    --dangerously-skip-permissions \
    --max-budget-usd 5 \
    < "$PROMPT_TMPFILE" \
    >> "$LOG_FILE" 2>&1 || EXIT_CODE=$?

rm -f "$PROMPT_TMPFILE"

if [ "$EXIT_CODE" -eq 124 ]; then
    echo "[$(date +%Y-%m-%d_%H-%M)] ${AGENT_NAME} TIMED OUT after ${TIMEOUT_MIN}m" | tee -a "$LOG_FILE"
else
    echo "[$(date +%Y-%m-%d_%H-%M)] ${AGENT_NAME} finished (exit=${EXIT_CODE})" | tee -a "$LOG_FILE"
fi

# Prune logs older than 7 days
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
