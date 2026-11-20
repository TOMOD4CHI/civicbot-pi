#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - car setup. Run ON THE RASPBERRY PI:
#     bash car/scripts/setup_pi.sh SERVER_IP            install
#     bash car/scripts/setup_pi.sh SERVER_IP --service  + start at boot
#  A reboot is needed the first time (UART for the GPS).
# =============================================================
set -e
SERVER_IP="${1:?Usage: bash setup_pi.sh SERVER_IP [--service]}"
CAR_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(whoami)"

echo "==> System packages (GPIO, camera, serial)"
sudo apt update
sudo apt install -y python3 python3-venv python3-gpiozero python3-lgpio \
  python3-picamera2 python3-serial

echo "==> GPIO + serial access for $USER_NAME"
sudo usermod -aG gpio,dialout,video "$USER_NAME" || true

echo "==> UART for the GPS: serial console OFF, serial hardware ON"
sudo raspi-config nonint do_serial_cons 1
sudo raspi-config nonint do_serial_hw 0

echo "==> Python venv (with system packages for gpiozero/picamera2)"
python3 -m venv --system-site-packages "$CAR_DIR/.venv"
"$CAR_DIR/.venv/bin/pip" install --upgrade pip
# ncnn (model runtime) is optional until the detector is integrated
grep -v '^ncnn' "$CAR_DIR/requirements.txt" > /tmp/potholepi-req.txt
"$CAR_DIR/.venv/bin/pip" install -r /tmp/potholepi-req.txt

if [[ ! -f "$CAR_DIR/.env" ]]; then
  echo "==> Writing $CAR_DIR/.env"
  cp "$CAR_DIR/.env.example" "$CAR_DIR/.env"
fi
sed -i "s#^POTHOLEPI_SERVER_URL=.*#POTHOLEPI_SERVER_URL=http://$SERVER_IP:8000#" "$CAR_DIR/.env"

if [[ "$2" == "--service" ]]; then
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
  echo "   Enabled. Logs: journalctl -u potholepi-car -f"
fi

IP=$(hostname -I | awk '{print $1}')
echo
echo "Done. Reboot once to enable the UART:  sudo reboot"
echo "Then:"
echo "  cd $CAR_DIR && .venv/bin/python scripts/test_motors.py   # wheels in the air"
echo "  cd $CAR_DIR && .venv/bin/python -m potholepi_car          # car service on :8080"
echo "  Mobile app -> Settings -> car IP $IP, port 8080"
