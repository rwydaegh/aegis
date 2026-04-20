#!/usr/bin/env bash
# Toggle agent runners between local cron and GitHub Actions
# Usage: toggle.sh local|remote|status
set -euo pipefail

export PATH="/home/user/.local/bin:$PATH"
REPO_DIR="/home/user/aegis"
CRON_MARKER="# aegis-agent"
REPO="rwydaegh/aegis"

GH_WORKFLOWS=("QA agent" "Feature agent" "Code review agent")

show_status() {
    echo "=== Local cron ==="
    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        echo "ENABLED"
        crontab -l 2>/dev/null | grep "$CRON_MARKER"
    else
        echo "DISABLED"
    fi
    echo ""
    echo "=== GitHub Actions ==="
    for wf in "${GH_WORKFLOWS[@]}"; do
        STATE=$(gh workflow list --repo "$REPO" --all --json name,state \
            --jq ".[] | select(.name == \"${wf}\") | .state" 2>/dev/null || echo "unknown")
        echo "  ${wf}: ${STATE:-not found}"
    done
}

enable_local() {
    echo "Enabling local cron jobs..."
    # Remove existing aegis-agent entries, then add fresh ones.
    # Schedule notes (staggered minutes so agents don't all fire at :00):
    #   qa-agent          - every 2h :00         Playwright against prod, long session
    #   code-review-agent - every 2h :30         correctness review from reading, not UX
    #   polish-agent      - every 3h :45         small UX/state fixes, 45m session
    #   feature-agent     - every 4h :15         ambitious product work, 2h session
    #   manager           - every 6h :20         supervises the fleet, 30m session
    (crontab -l 2>/dev/null | grep -v "$CRON_MARKER" || true; cat <<CRON
0 */2 * * * ${REPO_DIR}/agent_hq/local/qa-agent.sh ${CRON_MARKER}-qa
30 */2 * * * ${REPO_DIR}/agent_hq/local/code-review-agent.sh ${CRON_MARKER}-code-review
45 */3 * * * ${REPO_DIR}/agent_hq/local/polish-agent.sh ${CRON_MARKER}-polish
15 2,6,10,14,18,22 * * * ${REPO_DIR}/agent_hq/local/feature-agent.sh ${CRON_MARKER}-feature
20 0,6,12,18 * * * ${REPO_DIR}/agent_hq/local/manager-agent.sh ${CRON_MARKER}-manager
CRON
    ) | crontab -
    echo "Local cron: ENABLED"
}

disable_local() {
    echo "Disabling local cron jobs..."
    (crontab -l 2>/dev/null | grep -v "$CRON_MARKER" || true) | crontab -
    echo "Local cron: DISABLED"
}

enable_remote() {
    echo "Enabling GitHub Actions workflows..."
    for wf in "${GH_WORKFLOWS[@]}"; do
        gh workflow enable "$wf" --repo "$REPO" 2>/dev/null && echo "  ${wf}: enabled" || echo "  ${wf}: failed to enable"
    done
}

disable_remote() {
    echo "Disabling GitHub Actions workflows..."
    for wf in "${GH_WORKFLOWS[@]}"; do
        gh workflow disable "$wf" --repo "$REPO" 2>/dev/null && echo "  ${wf}: disabled" || echo "  ${wf}: failed to disable"
    done
}

case "${1:-status}" in
    local)
        enable_local
        disable_remote
        echo ""
        echo "Agents now run locally on this machine."
        ;;
    remote)
        disable_local
        enable_remote
        echo ""
        echo "Agents now run on GitHub Actions."
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: toggle.sh local|remote|status"
        exit 1
        ;;
esac
