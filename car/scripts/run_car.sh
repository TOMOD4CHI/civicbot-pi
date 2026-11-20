#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - run the car service on the Pi (foreground, Ctrl+C).
#     bash car/scripts/run_car.sh                 car service on :8080
#     bash car/scripts/run_car.sh --test-motors   wiring/calibration test
#     bash car/scripts/run_car.sh --simulate      no hardware (any Linux PC)
#  The systemd service (if installed) holds the GPIO pins, so it is
#  stopped first; restart it with: sudo systemctl start potholepi-car
# =============================================================
set -euo pipefail
CAR_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$CAR_DIR/.venv/bin/python"
[[ -x "$PY" ]] || { echo "Run setup first: bash $CAR_DIR/scripts/setup_pi.sh SERVER_IP"; exit 1; }

if systemctl is-active --quiet potholepi-car 2>/dev/null; then
  echo "==> Stopping the potholepi-car service (it holds the GPIO pins)"
  sudo systemctl stop potholepi-car
fi

cd "$CAR_DIR"
case "${1:-}" in
  --test-motors)
    echo "Put the car on a stand: the wheels will turn!"
    read -rp "Press Enter to start (Ctrl+C to cancel)..." _
    exec "$PY" scripts/test_motors.py ;;
  --simulate)
    export POTHOLEPI_SIMULATE=1
    exec "$PY" -m potholepi_car ;;
  "")
    exec "$PY" -m potholepi_car ;;
  *)
    echo "Unknown option: $1"; exit 1 ;;
esac
