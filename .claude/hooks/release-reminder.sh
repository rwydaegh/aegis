#!/usr/bin/env bash
# PreToolUse:Bash hook - reminds about release cadence when committing/pushing
set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Only fire on git commit or git push
if [[ "$CMD" == *"git commit"* ]] || [[ "$CMD" == *"git push"* ]]; then
  # Count commits since last tag
  LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
  if [ -n "$LAST_TAG" ]; then
    COUNT=$(git rev-list --count "${LAST_TAG}..HEAD" 2>/dev/null || echo "0")
    if [ "$COUNT" -gt 10 ]; then
      cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "RELEASE REMINDER: ${COUNT} commits since ${LAST_TAG}. Consider suggesting a patch release to the user. Patch releases (e.g. v0.7.1) should happen after bug fixes, small features, or meaningful corrections. Do not let commits pile up. IMPORTANT: When tagging a release, also run 'bash .claude/hooks/update-release-metadata.sh' to update README.md (bibtex version, test count badge) and CITATION.cff (version, date-released). Commit these metadata updates before or alongside the tag."
  }
}
ENDJSON
      exit 0
    fi
  fi
fi

echo '{}'
