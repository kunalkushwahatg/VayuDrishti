#!/usr/bin/env bash
# Rebuilds the India-wide AQI heatmap grid. Run periodically via cron.
#
# Example crontab (refresh every hour, on the hour):
#   0 * * * * /home/subhrajit/Desktop/VayuDrishti/backend/scripts/refresh_heatmap.sh >> /tmp/vayudrishti_heatmap.log 2>&1
#
# Edit crontab with:  crontab -e
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BACKEND_DIR"

# Activate venv if present
if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

export PYTHONPATH="$BACKEND_DIR"
echo "[$(date -u +%FT%TZ)] Refreshing heatmap..."
python src/ingestion/heatmap.py
echo "[$(date -u +%FT%TZ)] Done."
