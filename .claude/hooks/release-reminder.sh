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
      # Include commit summaries so Claude can judge release type
      COMMITS=$(git log --oneline "${LAST_TAG}..HEAD" 2>/dev/null | head -30 | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')
      cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "RELEASE REMINDER: ${COUNT} commits since ${LAST_TAG}. Review the commits below and decide: (1) Is a release warranted, or are these just chores/CI/docs? (2) If yes, is it a PATCH (bug fixes, corrections, small improvements) or MINOR (new features, new modules, meaningful new capability)? Commits since ${LAST_TAG}: ${COMMITS} --- When tagging a release, also run 'bash .claude/hooks/update-release-metadata.sh' to update README.md (bibtex version, test count badge) and CITATION.cff (version, date-released). Commit these metadata updates before or alongside the tag."
  }
}
ENDJSON
      exit 0
    fi
  fi
fi

echo '{}'
