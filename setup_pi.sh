#!/usr/bin/env bash
# =============================================================
#  Script de configuration — à lancer SUR LE RASPBERRY PI
#     bash setup_pi.sh            -> installe les dépendances
#     bash setup_pi.sh --service  -> + démarrage auto au boot
# =============================================================
set -e
DIR="$(cd "$(dirname "$0")" && pwd)/pi"
USER_NAME="$(whoami)"

echo "==> Mise à jour des paquets et installation des dépendances"
sudo apt update
sudo apt install -y python3 python3-gpiozero python3-lgpio python3-rpi.gpio

echo "==> Ajout de l'utilisateur $USER_NAME au groupe gpio"
sudo usermod -aG gpio "$USER_NAME" || true

echo "==> Vérification de l'accès GPIO"
python3 - <<'EOF'
from gpiozero import Device
from gpiozero import LED
l = LED(17); l.close()
print("   GPIO OK, pin factory :", Device.pin_factory.__class__.__name__)
EOF

IP=$(hostname -I | awk '{print $1}')

if [[ "$1" == "--service" ]]; then
  echo "==> Création du service systemd robot-car"
  sudo tee /etc/systemd/system/robot-car.service >/dev/null <<EOF
[Unit]
Description=Serveur de commande voiture L298N
After=network-online.target
Wants=network-online.target

[Service]
User=$USER_NAME
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 $DIR/server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now robot-car.service
  echo "   Service actif. Logs : journalctl -u robot-car -f"
fi

echo
echo "Installation terminée."
echo "  1) Test câblage  : cd $DIR && python3 test_motors.py"
echo "  2) Serveur       : cd $DIR && python3 server.py"
echo "  3) Sur le PC     : python3 desktop/car_control_app.py   (IP du Pi : $IP)"
