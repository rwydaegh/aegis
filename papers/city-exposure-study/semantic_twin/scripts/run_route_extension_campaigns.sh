#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 STUDY_ROOT PYTHON PERSISTENT_TRANSPORT_CACHE" >&2
  exit 2
fi

study_root=$(realpath "$1")
python=$2
transport_cache=$(realpath -m "$3")
sites=(brussels_grandplace london_trafalgar milan_duomo krakow_rynek toulouse_capitole)

cd "$study_root"
export PYTHONPATH="$study_root"
staged_aegis_data=$(dirname "$study_root")/aegis/data
if [[ -z ${AEGIS_DATA_DIR:-} && -f $staged_aegis_data/phantoms.yaml ]]; then
  export AEGIS_DATA_DIR=$staged_aegis_data
fi
if [[ ! -f outputs/city_screening/screening.json ]]; then
  echo "Provider link graph is missing: outputs/city_screening/screening.json" >&2
  exit 2
fi
if [[ -z ${AEGIS_DATA_DIR:-} || ! -f ${AEGIS_DATA_DIR:-}/phantoms.yaml ]]; then
  echo "AEGIS_DATA_DIR does not contain the required phantom registry" >&2
  exit 2
fi
if [[ ! -x $python ]]; then
  echo "Python executable is missing or not executable: $python" >&2
  exit 2
fi
mkdir -p "$transport_cache" outputs/experiments/ten_city_route_extension64_v1/logs

for site in "${sites[@]}"; do
  config="config/roofline_campaign_${site}_provider_corridor_v1_first_material_interaction_v1_extension64_cuda_iid.json"
  log="outputs/experiments/ten_city_route_extension64_v1/logs/${site}.log"
  echo "[campaign-preflight] $site" | tee -a "$log"
  "$python" -m semantic_twin.cli.roofline_campaign \
    --config "$config" \
    --dry-run \
    --persistent-transport-cache "$transport_cache" | tee -a "$log"
  echo "[campaign-run] $site" | tee -a "$log"
  "$python" -m semantic_twin.cli.roofline_campaign \
    --config "$config" \
    --persistent-transport-cache "$transport_cache" | tee -a "$log"
  echo "[campaign-done] $site" | tee -a "$log"
done
