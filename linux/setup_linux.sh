#!/usr/bin/env bash
# =============================================================
#  Configuration du serveur GPS — à lancer SUR LA MACHINE LINUX
#     bash setup_linux.sh               -> configuration
#     bash setup_linux.sh --service     -> + démarrage auto (systemd)
# =============================================================
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="$(whoami)"

echo "==> Vérification de Python 3"
python3 --version || { echo "Installe python3 (sudo apt install python3)"; exit 1; }

CURRENT=$(grep -oP '^CONTACT_EMAIL = "\K[^"]*' "$DIR/server_config.py" || true)
if [[ -z "$CURRENT" ]]; then
  echo
  echo "Nominatim (OpenStreetMap) demande que chaque application s'identifie."
  echo "Politique : https://operations.osmfoundation.org/policies/nominatim/"
  read -rp "Ton e-mail de contact (mis dans le User-Agent) : " EMAIL
  sed -i "s#^CONTACT_EMAIL = .*#CONTACT_EMAIL = \"$EMAIL\"#" "$DIR/server_config.py"
fi

echo "==> Ouverture du port 8000 dans le pare-feu (si ufw est actif)"
if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow 8000/tcp
else
  echo "   ufw inactif ou absent : rien à faire"
fi

if [[ "$1" == "--service" ]]; then
  echo "==> Création du service systemd robot-gps-server"
  sudo tee /etc/systemd/system/robot-gps-server.service >/dev/null <<EOF
[Unit]
Description=Serveur GPS robot car
After=network-online.target

[Service]
User=$USER_NAME
WorkingDirectory=$DIR
ExecStart=/usr/bin/python3 -u $DIR/gps_server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now robot-gps-server.service
  echo "   Logs : journalctl -u robot-gps-server -f"
fi

IP=$(hostname -I | awk '{print $1}')
echo
echo "Terminé."
echo "  Lancer le serveur : cd $DIR && python3 gps_server.py"
echo "  Carte             : http://localhost:8000"
echo "  IP à donner au Pi : $IP   ->  bash setup_gps_pi.sh $IP"
