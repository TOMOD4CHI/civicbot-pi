#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - car setup. Run ON THE RASPBERRY PI (Raspberry Pi OS
#  Bookworm). Safe to re-run; your car/.env calibration is kept.
#
#     bash car/scripts/setup_pi.sh SERVER_IP            install
#     bash car/scripts/setup_pi.sh SERVER_IP --service  + start at boot
#
#  Reboot once after the first run (enables the GPS UART + groups).
# =============================================================
set -euo pipefail
SERVER_IP="${1:?Usage: bash setup_pi.sh SERVER_IP [--service]}"
SERVICE=0
[[ "${2:-}" == "--service" ]] && SERVICE=1
CAR_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(whoami)"

echo "==> System packages (GPIO, camera, serial)"
sudo apt update
sudo apt install -y python3 python3-venv python3-gpiozero python3-lgpio \
  python3-picamera2 python3-serial rpicam-apps || \
sudo apt install -y python3 python3-venv python3-gpiozero python3-lgpio \
  python3-picamera2 python3-serial

echo "==> Groups for $USER_NAME: gpio, dialout (GPS), video (camera)"
sudo usermod -aG gpio,dialout,video "$USER_NAME" || true

if command -v raspi-config >/dev/null; then
  echo "==> UART for the GPS: serial console OFF, serial hardware ON"
  sudo raspi-config nonint do_serial_cons 1
  sudo raspi-config nonint do_serial_hw 0
else
  echo "   raspi-config not found: enable the UART manually (enable_uart=1)"
fi

echo "==> Python venv (sees the apt gpiozero/picamera2 packages)"
python3 -m venv --system-site-packages "$CAR_DIR/.venv"
"$CAR_DIR/.venv/bin/pip" install --quiet --upgrade pip
# ncnn (model runtime) is skipped until the detector is integrated
grep -v '^ncnn' "$CAR_DIR/requirements.txt" > /tmp/potholepi-req.txt
"$CAR_DIR/.venv/bin/pip" install --quiet -r /tmp/potholepi-req.txt

echo "==> Configuration: $CAR_DIR/.env"
[[ -f "$CAR_DIR/.env" ]] || cp "$CAR_DIR/.env.example" "$CAR_DIR/.env"
if grep -q '^POTHOLEPI_SERVER_URL=' "$CAR_DIR/.env"; then
  sed -i "s#^POTHOLEPI_SERVER_URL=.*#POTHOLEPI_SERVER_URL=http://$SERVER_IP:8000#" "$CAR_DIR/.env"
else
  echo "POTHOLEPI_SERVER_URL=http://$SERVER_IP:8000" >> "$CAR_DIR/.env"
fi
echo "   server = http://$SERVER_IP:8000"

if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  echo "==> Firewall: allow TCP 8080"
  sudo ufw allow 8080/tcp
fi

if [[ $SERVICE -eq 1 ]]; then
  echo "==> systemd service potholepi-car"
  sudo tee /etc/systemd/system/potholepi-car.service >/dev/null <<EOF
[Unit]
Description=Pothole Pi car service (drive, camera, GPS, reports)
After=network-online.target
Wants=network-online.target

[Service]
User=$USER_NAME
WorkingDirectory=$CAR_DIR
ExecStart=$CAR_DIR/.venv/bin/python -m potholepi_car
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable potholepi-car.service
  echo "   Enabled (starts at boot). Logs: journalctl -u potholepi-car -f"
fi

if command -v rpicam-hello >/dev/null; then
  echo "==> Camera detected:"
  rpicam-hello --list-cameras 2>&1 | sed 's/^/   /' | head -5 || true
fi

IP=$(hostname -I | awk '{print $1}')
echo
echo "Done. First time only:  sudo reboot"
echo "Then:"
echo "  bash $CAR_DIR/scripts/run_car.sh --test-motors   # wheels in the air"
echo "  bash $CAR_DIR/scripts/run_car.sh                 # car service on :8080"
echo "  Mobile app -> Settings -> car IP $IP, port 8080"
