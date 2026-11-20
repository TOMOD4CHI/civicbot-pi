# Voiture Raspberry Pi 4 + L298N (2 moteurs + roue folle)

## Câblage (BCM)
| L298N | Pi 4 (GPIO) | Broche physique |
|-------|-------------|-----------------|
| ENA   | GPIO18      | 12 |
| IN1   | GPIO17      | 11 |
| IN2   | GPIO27      | 13 |
| IN3   | GPIO22      | 15 |
| IN4   | GPIO23      | 16 |
| ENB   | GPIO13      | 33 |
| GND   | GND         | 6  ← masse commune OBLIGATOIRE |

- Batterie moteurs (6–12 V) → bornes `12V` / `GND` du L298N. Ne prends jamais le 5 V du Pi pour les moteurs.
- Enlève les cavaliers ENA/ENB pour brancher ces broches. Si tu les gardes, mets `LEFT_EN = None` et `RIGHT_EN = None` dans `pi/config.py`.

## Installation (depuis la machine Linux)
```bash
bash deploy.sh pi@IP_DU_PI            # copie via SSH + installe
bash deploy.sh pi@IP_DU_PI --service  # + serveur lancé au démarrage
```

## Utilisation
```bash
ssh pi@IP_DU_PI
cd ~/robot-car/pi
python3 test_motors.py   # roues en l'air : vérifie chaque moteur
python3 server.py        # serveur de commande (port 5005)
```
Sur le PC : `python3 desktop/car_control_app.py`, saisis l'IP du Pi, puis **Connecter**.
Clavier : flèches / ZQSD / WASD, **Espace = STOP**.

## Réglages (`pi/config.py`)
- Une roue tourne à l'envers → `LEFT_INVERTED` / `RIGHT_INVERTED = True`
- La voiture dérive → `LEFT_TRIM` / `RIGHT_TRIM` (ex. 0.93)
- Le moteur grogne sans tourner à basse vitesse → augmente `MIN_DUTY`
