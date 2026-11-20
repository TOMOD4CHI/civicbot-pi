#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - server setup. Run ON THE LINUX PC (once, and after
#  changing requirements). Safe to re-run.
#
#     bash server/scripts/setup_server.sh                      install
#     bash server/scripts/setup_server.sh --service            + start at boot (systemd)
#     bash server/scripts/setup_server.sh --email me@mail.com  non-interactive
# =============================================================
set -euo pipefail
SERVER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(whoami)"
SERVICE=0
EMAIL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --service) SERVICE=1 ;;
    --email) EMAIL="${2:?--email needs a value}"; shift ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

echo "==> Checking Python"
if ! command -v python3 >/dev/null; then
  echo "python3 is missing: sudo apt install python3 python3-venv"; exit 1
fi
if ! python3 -c "import venv, ensurepip" 2>/dev/null; then
  echo "   installing python3-venv"
  sudo apt update && sudo apt install -y python3-venv
fi
python3 - <<'EOF'
import sys
if sys.version_info < (3, 10):
    sys.exit(f"Python >= 3.10 required, found {sys.version.split()[0]}")
EOF

echo "==> Python virtual environment: $SERVER_DIR/.venv"
python3 -m venv "$SERVER_DIR/.venv"
"$SERVER_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$SERVER_DIR/.venv/bin/pip" install --quiet -r "$SERVER_DIR/requirements.txt"

echo "==> Configuration: $SERVER_DIR/.env"
[[ -f "$SERVER_DIR/.env" ]] || cp "$SERVER_DIR/.env.example" "$SERVER_DIR/.env"
if [[ -n "$EMAIL" ]]; then
  sed -i "s#^POTHOLEPI_CONTACT_EMAIL=.*#POTHOLEPI_CONTACT_EMAIL=$EMAIL#" "$SERVER_DIR/.env"
elif ! grep -q '^POTHOLEPI_CONTACT_EMAIL=.\+' "$SERVER_DIR/.env"; then
  echo
  echo "   Nominatim (OpenStreetMap) requires every app to identify itself."
  echo "   Policy: https://operations.osmfoundation.org/policies/nominatim/"
  read -rp "   Contact e-mail (sent in the User-Agent): " EMAIL
  sed -i "s#^POTHOLEPI_CONTACT_EMAIL=.*#POTHOLEPI_CONTACT_EMAIL=$EMAIL#" "$SERVER_DIR/.env"
fi
mkdir -p "$SERVER_DIR/data/images"

echo "==> Firewall: allow TCP 8000 (only if ufw is active)"
if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow 8000/tcp
else
  echo "   ufw not active: nothing to do"
fi

if [[ $SERVICE -eq 1 ]]; then
  echo "==> systemd service potholepi-server"
  sudo tee /etc/systemd/system/potholepi-server.service >/dev/null <<EOF
[Unit]
Description=Pothole Pi server (map, dashboard, API)
After=network-online.target
Wants=network-online.target

[Service]
User=$USER_NAME
WorkingDirectory=$SERVER_DIR
ExecStart=$SERVER_DIR/.venv/bin/python -m potholepi_server
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable potholepi-server.service
  sudo systemctl restart potholepi-server.service
  echo "   Running. Logs: journalctl -u potholepi-server -f"
fi

IP=$(hostname -I | awk '{print $1}')
echo
echo "Server ready."
echo "  Start (foreground): bash $SERVER_DIR/scripts/run_server.sh"
echo "  Map:                http://$IP:8000"
echo "  Dashboard:          http://$IP:8000/dashboard"
echo "  Car setting:        POTHOLEPI_SERVER_URL=http://$IP:8000   (car/.env on the Pi)"
