#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - server setup. Run ON THE LINUX PC:
#     bash server/scripts/setup_server.sh             install
#     bash server/scripts/setup_server.sh --service   + start at boot
# =============================================================
set -e
SERVER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(whoami)"

python3 -m venv "$SERVER_DIR/.venv"
"$SERVER_DIR/.venv/bin/pip" install --upgrade pip
"$SERVER_DIR/.venv/bin/pip" install -r "$SERVER_DIR/requirements.txt"

if [[ ! -f "$SERVER_DIR/.env" ]]; then
  cp "$SERVER_DIR/.env.example" "$SERVER_DIR/.env"
fi
if ! grep -q '^POTHOLEPI_CONTACT_EMAIL=.\+' "$SERVER_DIR/.env"; then
  echo
  echo "Nominatim (OpenStreetMap) requires every app to identify itself."
  echo "Policy: https://operations.osmfoundation.org/policies/nominatim/"
  read -rp "Contact e-mail (put in the User-Agent): " EMAIL
  sed -i "s#^POTHOLEPI_CONTACT_EMAIL=.*#POTHOLEPI_CONTACT_EMAIL=$EMAIL#" "$SERVER_DIR/.env"
fi

echo "==> Opening port 8000 (if ufw is active)"
if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow 8000/tcp
fi

if [[ "$1" == "--service" ]]; then
  sudo tee /etc/systemd/system/potholepi-server.service >/dev/null <<EOF
[Unit]
Description=Pothole Pi server (map, dashboard, API)
After=network-online.target

[Service]
User=$USER_NAME
WorkingDirectory=$SERVER_DIR
ExecStart=$SERVER_DIR/.venv/bin/python -m potholepi_server
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now potholepi-server.service
  echo "   Running. Logs: journalctl -u potholepi-server -f"
fi

IP=$(hostname -I | awk '{print $1}')
echo
echo "Run:  cd $SERVER_DIR && .venv/bin/python -m potholepi_server"
echo "Map:  http://$IP:8000      Dashboard: http://$IP:8000/dashboard"
echo "Demo data: .venv/bin/python scripts/seed_demo.py"
