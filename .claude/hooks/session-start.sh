#!/usr/bin/env bash
# SessionStart hook: injects the using-superpowers skill into every conversation.
# Portable across Windows (Git Bash) and Linux.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_CLAUDE="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILL_FILE="${PROJECT_CLAUDE}/skills/using-superpowers/SKILL.md"

if [ ! -f "$SKILL_FILE" ]; then
  echo '{}' && exit 0
fi

using_superpowers_content=$(cat "$SKILL_FILE")

escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

escaped=$(escape_for_json "$using_superpowers_content")
context="You have superpowers skills installed at project level.\n\n**Below is the full content of your 'using-superpowers' skill - your introduction to using skills. For all other skills, use the 'Skill' tool:**\n\n${escaped}"

printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$context"
exit 0
