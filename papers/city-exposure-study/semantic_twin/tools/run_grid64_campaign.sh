#!/usr/bin/env bash
set -euo pipefail

study_root=${1:?usage: run_grid64_campaign.sh STUDY_ROOT AEGIS_DATA_DIR [SITE ...]}
aegis_data_dir=${2:?usage: run_grid64_campaign.sh STUDY_ROOT AEGIS_DATA_DIR [SITE ...]}
shift 2
output_root="$study_root/outputs/experiments/ten_city_geometry_screen_64_v1"
cache_root="$output_root/_transport_cache"
progress_log="$output_root/progress.log"

mkdir -p "$output_root" "$cache_root"
cd "$study_root"

if (( $# )); then
    configs=()
    for site in "$@"; do
        configs+=(
            "config/roofline_campaign_${site}_fixed_ground_grid_64_v1_first_material_interaction_v1_geometry_screen_cuda_iid.json"
        )
    done
else
    configs=(config/roofline_campaign_*_fixed_ground_grid_64_v1_first_material_interaction_v1_geometry_screen_cuda_iid.json)
fi

for config in "${configs[@]}"; do
    site=$(sed -n 's/.*"site": "\([^"]*\)".*/\1/p' "$config" | head -1)
    if [[ -z "$site" ]]; then
        echo "could not read site from $config" >&2
        exit 2
    fi
    printf 'START %s %s\n' "$site" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$progress_log"
    AEGIS_DATA_DIR="$aegis_data_dir" /usr/bin/time \
        -f 'WALL_SECONDS=%e\nMAX_RSS_KB=%M' \
        .venv/bin/python -m semantic_twin.cli.roofline_campaign \
        --config "$config" \
        --study-root "$study_root" \
        --persistent-transport-cache "$cache_root" \
        >"$output_root/$site.log" 2>&1
    printf 'DONE %s %s\n' "$site" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$progress_log"
done

printf 'ALL_DONE %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$progress_log"
