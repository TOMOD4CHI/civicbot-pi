#!/usr/bin/env bash
# =============================================================
#  À lancer depuis la MACHINE LINUX : copie le projet sur le Pi
#  via SSH, lance la configuration et prépare l'appli desktop.
#
#     bash deploy.sh pi@192.168.1.50            (installe)
#     bash deploy.sh pi@192.168.1.50 --service  (+ démarrage auto)
# =============================================================
set -e
TARGET="${1:?Usage: bash deploy.sh utilisateur@ip_du_pi [--service]}"
EXTRA="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "==> Dépendance de l'appli desktop (Tkinter) sur ce PC"
command -v apt >/dev/null && sudo apt install -y python3-tk || \
  echo "   (installe python3-tk avec ton gestionnaire de paquets)"

echo "==> Copie des fichiers vers $TARGET:~/robot-car"
ssh "$TARGET" "mkdir -p ~/robot-car"
scp -r "$HERE/pi" "$HERE/setup_pi.sh" "$HERE/setup_gps_pi.sh" "$TARGET:~/robot-car/"

echo "==> Configuration du Pi"
ssh -t "$TARGET" "cd ~/robot-car && bash setup_pi.sh $EXTRA"

echo
echo "Prochaines étapes :"
echo "  ssh $TARGET 'cd ~/robot-car/pi && python3 test_motors.py'"
echo "  ssh $TARGET 'cd ~/robot-car/pi && python3 server.py'"
echo "  python3 $HERE/desktop/car_control_app.py"
