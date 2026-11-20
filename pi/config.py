# =============================================================
#  Configuration du câblage  Raspberry Pi 4  <->  L298N
#  Numérotation BCM (GPIOxx), PAS le numéro physique de la broche
# =============================================================
#
#  L298N        Raspberry Pi 4 (BCM)     Broche physique
#  -----        --------------------     ---------------
#  ENA   ->     GPIO18                   12
#  IN1   ->     GPIO17                   11
#  IN2   ->     GPIO27                   13
#  IN3   ->     GPIO22                   15
#  IN4   ->     GPIO23                   16
#  ENB   ->     GPIO13                   33
#  GND   ->     GND                      6   (masse COMMUNE obligatoire)
#
#  Alimentation moteurs : batterie 6-12 V sur "12V" et "GND" du L298N.
#  Ne JAMAIS alimenter les moteurs depuis le 5 V du Raspberry.
#
#  Si tu laisses les cavaliers (jumpers) sur ENA / ENB, mets
#  ENA = None et ENB = None : la vitesse sera alors réglée par PWM
#  sur IN1..IN4 (comme dans l'article mataucarre.fr).

# --- Moteur gauche (sortie OUT1/OUT2 du L298N) ---
LEFT_IN1 = 17
LEFT_IN2 = 27
LEFT_EN = 18          # None si cavalier ENA en place

# --- Moteur droit (sortie OUT3/OUT4 du L298N) ---
RIGHT_IN3 = 22
RIGHT_IN4 = 23
RIGHT_EN = 13         # None si cavalier ENB en place

# Inverser le sens d'un moteur si la roue tourne à l'envers
# (évite de devoir dessouder / inverser les fils)
LEFT_INVERTED = False
RIGHT_INVERTED = False

# Correction si la voiture dérive (un moteur plus rapide que l'autre)
# ex: 0.95 ralentit ce moteur de 5 %
LEFT_TRIM = 1.0
RIGHT_TRIM = 1.0

# Vitesse minimale utile : en dessous, beaucoup de moteurs TT ne
# démarrent pas et "grognent". 0 pour désactiver.
MIN_DUTY = 0.25

# Vitesse maximale : les moteurs TT sont prévus pour 3-6 V. Avec ~12 V
# sur le L298N (qui chute ~2 V), 0.6 donne environ 5-6 V aux moteurs.
MAX_DUTY = 0.6

# Réseau (serveur sur le Pi)
HOST = "0.0.0.0"
PORT = 5005

# Sécurité : si aucune commande reçue pendant ce délai (s), on stoppe
WATCHDOG_TIMEOUT = 0.5
