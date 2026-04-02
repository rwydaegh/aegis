#!/usr/bin/env bash
# Updates README.md and CITATION.cff with current version and test count.
# Run before tagging a release or whenever metadata drifts.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# --- Version from latest git tag ---
VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//')
if [ -z "$VERSION" ]; then
  echo "ERROR: No git tags found. Tag a release first." >&2
  exit 1
fi

# --- Test count ---
# Use the venv python if available, otherwise fall back to system python
PYTHON="${CLAUDE_PROJECT_DIR:-.}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python"
fi

TEST_COUNT=$("$PYTHON" -m pytest tests/ --collect-only -q 2>/dev/null | tail -1 | grep -oP '^\d+')
if [ -z "$TEST_COUNT" ]; then
  echo "WARNING: Could not count tests. Skipping test badge update." >&2
  TEST_COUNT=""
fi

# --- Today's date ---
TODAY=$(date +%Y-%m-%d)

# --- Update README.md ---
echo "Updating README.md..."

# Update bibtex version
sed -i "s/version = {[^}]*}/version = {${VERSION}}/" README.md

# Update test badge (tests-XXXX%20cases)
if [ -n "$TEST_COUNT" ]; then
  sed -i "s/tests-[0-9]*%20cases/tests-${TEST_COUNT}%20cases/" README.md
fi

# --- Update CITATION.cff ---
echo "Updating CITATION.cff..."
sed -i "s/^version: .*/version: ${VERSION}/" CITATION.cff
sed -i "s/^date-released: .*/date-released: ${TODAY}/" CITATION.cff

echo "Done. Version=${VERSION}, Tests=${TEST_COUNT:-skipped}, Date=${TODAY}"
