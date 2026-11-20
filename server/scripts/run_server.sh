#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - run the server in the foreground (Ctrl+C to stop).
#     bash server/scripts/run_server.sh
#     bash server/scripts/run_server.sh --no-geocode   (offline / testing)
#  If the systemd service is installed, use instead:
#     sudo systemctl start|stop|restart potholepi-server
# =============================================================
set -euo pipefail
SERVER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$SERVER_DIR/.venv/bin/python"

[[ -x "$PY" ]] || { echo "Run setup first: bash $SERVER_DIR/scripts/setup_server.sh"; exit 1; }
[[ "${1:-}" == "--no-geocode" ]] && export POTHOLEPI_GEOCODE_ENABLED=0

if systemctl is-active --quiet potholepi-server 2>/dev/null; then
  echo "The potholepi-server service is already running (port 8000)."
  echo "Stop it first: sudo systemctl stop potholepi-server"
  exit 1
fi

cd "$SERVER_DIR"
exec "$PY" -m potholepi_server
