# =============================================================
#  Configuration du module GPS GY-NEO6MV2 (côté Raspberry Pi)
# =============================================================
#
#  Câblage GY-NEO6MV2  ->  Raspberry Pi 4
#  ------------------      ---------------------------------
#  VCC                ->   5V   (broche physique 4)  [3.3V broche 1 marche aussi]
#  GND                ->   GND  (broche physique 9)
#  TX                 ->   GPIO15 / RXD (broche physique 10)
#  RX                 ->   GPIO14 / TXD (broche physique 8)   (optionnel)
#
#  TX du GPS va sur RX du Pi, et inversement (croisé).

SERIAL_PORT = "/dev/serial0"   # UART matériel du Pi (activé par setup_gps_pi.sh)
BAUDRATE = 9600                # valeur par défaut du NEO-6M

# Adresse du serveur sur la machine Linux (mets son IP : `hostname -I`)
SERVER_URL = "http://192.168.1.100:8000/api/gps"

DEVICE_ID = "robot-car"        # nom de la voiture affiché sur le serveur
SEND_INTERVAL = 2.0            # secondes entre deux envois
HTTP_TIMEOUT = 3.0
