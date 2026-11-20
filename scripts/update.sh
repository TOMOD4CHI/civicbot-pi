#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - pull the latest code and restart. Your .env files and
#  the database are not touched (they are git-ignored).
#
#     bash scripts/update.sh car       on the Raspberry Pi
#     bash scripts/update.sh server    on the Linux PC
# =============================================================
set -euo pipefail
ROLE="${1:?Usage: bash scripts/update.sh car|server}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "You have local code changes:"; git status --short
  echo "Commit or stash them first (git stash), then re-run."
  exit 1
fi

echo "==> git pull"
git pull --ff-only

case "$ROLE" in
  car)
    grep -v '^ncnn' car/requirements.txt > /tmp/potholepi-req.txt
    car/.venv/bin/pip install --quiet -r /tmp/potholepi-req.txt
    SERVICE=potholepi-car ;;
  server)
    server/.venv/bin/pip install --quiet -r server/requirements.txt
    SERVICE=potholepi-server ;;
  *) echo "Role must be car or server"; exit 1 ;;
esac

if systemctl list-unit-files 2>/dev/null | grep -q "^$SERVICE.service"; then
  echo "==> Restarting $SERVICE"
  sudo systemctl restart "$SERVICE"
  sleep 2
  systemctl --no-pager --lines=5 status "$SERVICE" || true
else
  echo "No $SERVICE service installed: restart it by hand (scripts/run_*.sh)."
fi
echo "Updated to $(git log -1 --format='%h %s')"
