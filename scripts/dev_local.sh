#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - run the WHOLE system on one Linux PC without hardware:
#  server (:8000) + simulated car (:8080: mock motors, fake GPS around
#  Bizerte, test-pattern camera). Point the mobile app at this PC.
#
#     bash scripts/dev_local.sh            start both (Ctrl+C stops both)
#     bash scripts/dev_local.sh --seed     + fill the DB with demo potholes
#     bash scripts/dev_local.sh --test     run the Python test suites only
# =============================================================
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv-dev"
PY="$VENV/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "==> Creating dev venv $VENV"
  python3 -m venv "$VENV"
  "$PY" -m pip install --quiet --upgrade pip
  grep -v '^ncnn' "$ROOT/car/requirements.txt" > /tmp/potholepi-car-req.txt
  "$PY" -m pip install --quiet -r /tmp/potholepi-car-req.txt \
    -r "$ROOT/server/requirements-dev.txt" gpiozero numpy
fi

if [[ "${1:-}" == "--test" ]]; then
  (cd "$ROOT/car" && "$PY" -m pytest -q)
  (cd "$ROOT/server" && "$PY" -m pytest -q)
  exit 0
fi

if [[ "${1:-}" == "--seed" ]]; then
  (cd "$ROOT/server" && "$PY" scripts/seed_demo.py)
fi

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "==> Server on :8000 (geocoding off in dev)"
(cd "$ROOT/server" && POTHOLEPI_GEOCODE_ENABLED=0 "$PY" -m potholepi_server) &

echo "==> Simulated car on :8080"
(cd "$ROOT/car" && POTHOLEPI_SIMULATE=1 POTHOLEPI_SERVER_URL=http://127.0.0.1:8000 \
  "$PY" -m potholepi_car) &

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
sleep 3
echo
echo "  Map:        http://localhost:8000"
echo "  Dashboard:  http://localhost:8000/dashboard"
echo "  Car video:  http://localhost:8080/viewer"
echo "  Mobile app: Settings -> car IP ${IP:-<IP of this PC>}, port 8080"
echo "  Ctrl+C to stop everything."
wait
