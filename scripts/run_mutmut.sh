#!/usr/bin/env bash
# Local mutation-testing driver. Not wired to PR CI (see
# docs/internal/testing_roadmap.md Phase 4). The minor-release job in
# .github/workflows/release.yml invokes the same binary with its own config.
#
# Usage:
#   scripts/run_mutmut.sh                  # runs fresnel.py (pyproject default)
#   scripts/run_mutmut.sh parsing          # runs viewer compute/_parsing.py
#   scripts/run_mutmut.sh kernels          # runs src/aegis/kernels/*.py
#   scripts/run_mutmut.sh compliance       # runs src/aegis/compliance/*.py
#   scripts/run_mutmut.sh tissue           # runs src/aegis/tissue/*.py
#
# Results land in mutants/ and are queryable via:
#   uv run mutmut results
#   uv run mutmut show <mutant_id>
#   uv run mutmut browse       # TUI
set -euo pipefail

cd "$(dirname "$0")/.."

# The IT'IS tissue DB lives under data/ which is too big to copy into mutants/.
# Export the env var so viewer routes can resolve it from the mutants cwd.
export AEGIS_DATA_DIR="${AEGIS_DATA_DIR:-$PWD/data}"

target="${1:-fresnel}"

case "$target" in
    fresnel)
        paths='["src/aegis/tissue/fresnel.py"]'
        tests='["tests/test_fresnel.py"]'
        ;;
    parsing)
        paths='["src/aegis/viewer/routes/compute/_parsing.py"]'
        tests='["tests/test_compute_route_helpers.py", "tests/viewer/test_compute_routes.py", "tests/test_viewer_schemathesis_repro_antenna_pos_overflow.py"]'
        ;;
    kernels)
        paths='["src/aegis/kernels"]'
        tests='["tests/"]'
        ;;
    compliance)
        paths='["src/aegis/compliance"]'
        tests='["tests/test_compliance.py"]'
        ;;
    tissue)
        paths='["src/aegis/tissue"]'
        tests='["tests/test_fresnel.py", "tests/test_dielectric.py", "tests/test_tissue_database.py"]'
        ;;
    *)
        echo "Unknown target: $target" >&2
        echo "Usage: $0 [fresnel|parsing|kernels|compliance|tissue]" >&2
        exit 1
        ;;
esac

# mutmut v3 is pyproject-driven; patch [tool.mutmut].paths_to_mutate/tests_dir
# in place for this run, then restore. Avoids a separate config file.
python - <<PYEOF
import re
from pathlib import Path

p = Path("pyproject.toml")
src = p.read_text()
src2 = re.sub(
    r"(paths_to_mutate\s*=\s*)\[[^\]]*\]",
    r"\g<1>${paths}",
    src,
    count=1,
)
src2 = re.sub(
    r"(tests_dir\s*=\s*)\[[^\]]*\]",
    r"\g<1>${tests}",
    src2,
    count=1,
)
p.write_text(src2)
PYEOF

trap 'git checkout -- pyproject.toml' EXIT

# Wipe the mutants/ cache so paths_to_mutate/tests_dir changes take effect.
rm -rf mutants

uv run mutmut run --max-children 4 "$@"
uv run mutmut results | tee "mutmut_results_${target}.txt"

echo ""
echo "Results written to mutmut_results_${target}.txt"
echo "Use 'uv run mutmut show <id>' to inspect a survivor."
