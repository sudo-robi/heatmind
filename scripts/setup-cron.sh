#!/usr/bin/env bash
# setup-cron.sh — Install daily HeatMind simulator cron job.
# Runs every morning at 8:00 AM (local time) until August 31, 2026.
#
# Usage:
#   bash scripts/setup-cron.sh          # install cron
#   bash scripts/setup-cron.sh remove   # remove cron
#   bash scripts/setup-cron.sh status   # check if installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SIMULATE="$PROJECT_DIR/scripts/simulate.py"
LOG_DIR="$PROJECT_DIR/logs"
CRON_TAG="# heatmind-simulator"

mkdir -p "$LOG_DIR"

install_cron() {
    local venv_python="$PROJECT_DIR/venv/bin/python"
    if [[ ! -f "$venv_python" ]]; then
        venv_python="python3"
    fi

    local cron_line="0 8 * * * cd $PROJECT_DIR && $venv_python $SIMULATE --sessions 5 >> $LOG_DIR/simulate_\$(date +\\%Y-\\%m-\\%d).log 2>&1 $CRON_TAG"

    # Remove existing entry if present
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" | crontab - 2>/dev/null || true

    # Add new entry
    (crontab -l 2>/dev/null; echo "$cron_line") | crontab -

    echo "Installed cron job:"
    echo "  Schedule: Every day at 8:00 AM"
    echo "  Sessions: 5 per run"
    echo "  Log:      $LOG_DIR/"
    echo "  Until:    August 31, 2026 (manual removal needed)"
    echo ""
    echo "To run manually now:"
    echo "  $venv_python $SIMULATE --sessions 3"
}

remove_cron() {
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" | crontab - 2>/dev/null || true
    echo "Removed heatmind-simulator cron job."
}

show_status() {
    echo "Current heatmind cron entries:"
    crontab -l 2>/dev/null | grep "$CRON_TAG" || echo "  (none installed)"
}

case "${1:-install}" in
    install) install_cron ;;
    remove)  remove_cron ;;
    status)  show_status ;;
    *)       echo "Usage: $0 {install|remove|status}" ;;
esac
