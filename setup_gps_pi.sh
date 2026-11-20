#!/usr/bin/env bash
# =============================================================
#  Configuration du GPS — à lancer SUR LE RASPBERRY PI
#     bash setup_gps_pi.sh 192.168.1.100            (IP de la machine Linux)
#     bash setup_gps_pi.sh 192.168.1.100 --service  (+ envoi auto au démarrage)
# =============================================================
set -e
SERVER_IP="${1:?Usage: bash setup_gps_pi.sh IP_MACHINE_LINUX [--service]}"
DIR="$(cd "$(dirname "$0")" && pwd)/pi"
USER_NAME="$(whoami)"

echo "==> Activation de l'UART matériel, désactivation de la console série"
sudo raspi-config nonint do_serial_cons 1    # 1 = console série OFF
sudo raspi-config nonint do_serial_hw 0      # 0 = port série ON

echo "==> Installation de pyserial"
sudo apt update
sudo apt install -y python3-serial

echo "==> Ajout de $USER_NAME au groupe dialout (accès au port série)"
sudo usermod -aG dialout "$USER_NAME"

echo "==> Adresse du serveur : http://$SERVER_IP:8000/api/gps"
sed -i "s#^SERVER_URL = .*#SERVER_URL = \"http://$SERVER_IP:8000/api/gps\"#" "$DIR/gps_config.py"

if [[ "$2" == "--service" ]]; then
  echo "==> Création du service systemd robot-gps"
  sudo tee /etc/systemd/system/robot-gps.service >/dev/null <<EOF
[Unit]
Description=Envoi de la position GPS au serveur Linux
After=network-online.target
Wants=network-online.target

[Service]
User=$USER_NAME
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 -u $DIR/gps_sender.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable robot-gps.service
  echo "   Service activé (démarre après le redémarrage). Logs : journalctl -u robot-gps -f"
fi

echo
echo "Terminé. REDÉMARRE le Pi pour activer l'UART :  sudo reboot"
echo "Ensuite :"
echo "  cd $DIR && python3 gps_sender.py --raw    # doit afficher des lignes \$GPRMC, \$GPGGA..."
echo "  cd $DIR && python3 gps_sender.py          # envoi réel"
echo "  cd $DIR && python3 gps_sender.py --fake   # test sans fix GPS"
