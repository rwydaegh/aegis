#!/usr/bin/env bash
# PreToolUse:Bash hook - reminds about release cadence when committing/pushing
set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Only fire on git commit or git push
if [[ "$CMD" == *"git commit"* ]] || [[ "$CMD" == *"git push"* ]]; then
  # Find last tag reachable from HEAD (not orphaned tags from squash-merged branches)
  LAST_TAG=$(git describe --tags --abbrev=0 HEAD 2>/dev/null || echo "")
  # Fallback: if no reachable tag, pick the highest semver tag that IS an ancestor of HEAD
  if [ -z "$LAST_TAG" ]; then
    LAST_TAG=$(git tag --sort=-v:refname | while read -r t; do
      git merge-base --is-ancestor "$t" HEAD 2>/dev/null && echo "$t" && break
    done)
  fi
  if [ -n "$LAST_TAG" ]; then
    COUNT=$(git rev-list --count "${LAST_TAG}..HEAD" 2>/dev/null || echo "0")
    if [ "$COUNT" -gt 10 ]; then
      # Include commit summaries so Claude can judge release type
      COMMITS=$(git log --oneline "${LAST_TAG}..HEAD" 2>/dev/null | head -40 | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|$//')
      # Also grab merged PR numbers for changelog context
      MERGED_PRS=$(git log --format="%s" "${LAST_TAG}..HEAD" 2>/dev/null | grep -oP '\(#\d+\)' | tr -d '()' | sort -u | tr '\n' ',' | sed 's/,$//' || echo "none")
      cat <<ENDJSON
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "RELEASE REMINDER: ${COUNT} commits since ${LAST_TAG}. Use /release to handle this with a proper changelog. Otherwise, review commits and decide: (1) Is a release warranted, or are these just chores/CI/docs? (2) If yes, is it a PATCH (bug fixes, corrections, small improvements) or MINOR (new features, new modules, meaningful new capability)? Merged PRs: ${MERGED_PRS} | Commits since ${LAST_TAG}: ${COMMITS} --- When tagging a release, also run 'bash .claude/hooks/update-release-metadata.sh' to update README.md (bibtex version, test count badge) and CITATION.cff (version, date-released). Commit these metadata updates before or alongside the tag."
  }
}
ENDJSON
      exit 0
    fi
  fi
fi

echo '{}'
