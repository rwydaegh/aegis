#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 STUDY_ROOT PYTHON [SITE ...]" >&2
  exit 2
fi

study_root=$(realpath "$1")
python=$2
shift 2

if [[ ! -x $python ]]; then
  echo "Python executable is missing or not executable: $python" >&2
  exit 2
fi

if [[ $# -gt 0 ]]; then
  sites=("$@")
else
  sites=(london_trafalgar milan_duomo krakow_rynek toulouse_capitole)
fi

semantics_dir=semantics_sam3_3c879f39826c281e_61id
cd "$study_root"
export PYTHONPATH="$study_root"

material_prior=data/panoramas/korenmarkt/semantics/semantics.json
if [[ ! -f $material_prior ]]; then
  echo "Canonical shared material-prior record is missing: $material_prior" >&2
  exit 2
fi

wait_for_semantics() {
  local site=$1
  local job="outputs/hybrid_batch/${site}.json"
  local status
  while true; do
    if "$python" - "$job" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
document = json.loads(path.read_text()) if path.is_file() else {}
rows = document.get("stations", [])
if any(row.get("status") == "failed" for row in rows):
    raise SystemExit(2)
if len(rows) == 14 and all(row.get("status") in {"completed", "skipped_complete"} for row in rows):
    raise SystemExit(0)
raise SystemExit(1)
PY
    then
      return 0
    else
      status=$?
    fi
    if [[ $status -eq 2 ]]; then
      echo "[prep-failed-upstream] $site" >&2
      return 2
    fi
    sleep 10
  done
}

for site in "${sites[@]}"; do
  wait_for_semantics "$site"
  echo "[prep-start] $site"
  "$python" reregister_site.py \
    --site "$site" \
    --crop-m 250 \
    --workers "${AEGIS_REGISTRATION_WORKERS:-6}" \
    --semantics-dirname "$semantics_dir"
  "$python" build_site_semantics.py \
    --site "$site" \
    --crop-m 250 \
    --workers 4 \
    --semantics-dirname "$semantics_dir"
  "$python" build_surface_atlas.py \
    --site "$site" \
    --crop-m 250 \
    --semantics-dirname "$semantics_dir"
  "$python" - "$site" <<'PY'
import hashlib
import json
import pathlib
import sys

site = sys.argv[1]
root = pathlib.Path("outputs/site_semantics") / site
report = json.loads((root / "walk_semantic_250m.json").read_text())
if report.get("result") != "written" or len(report.get("stations_admitted", [])) < 2:
    raise SystemExit(f"{site}: semantic report is not ready for a production route")
atlas_path = root / "joint_atlas_250m_r8.json"
atlas = json.loads(atlas_path.read_text())
artifact = atlas_path.parent / atlas["artifact"]["path"]
digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
if digest != atlas["artifact"]["sha256"]:
    raise SystemExit(f"{site}: atlas artifact hash does not match its manifest")
if len(atlas.get("camera_ids", [])) < 2:
    raise SystemExit(f"{site}: atlas has fewer than two admitted cameras")
print(f"[prep-validated] {site}: {len(report['stations_admitted'])} admitted cameras")
PY
  echo "[prep-done] $site"
done
