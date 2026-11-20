#!/usr/bin/env python3
"""Test rapide du câblage, à lancer directement sur le Pi (via SSH).
Mets la voiture sur un support, roues en l'air !

    python3 test_motors.py
"""
import time
from car import Car

STEPS = [
    ("Moteur GAUCHE seul, avant", (0.6, 0)),
    ("Moteur GAUCHE seul, arrière", (-0.6, 0)),
    ("Moteur DROIT seul, avant", (0, 0.6)),
    ("Moteur DROIT seul, arrière", (0, -0.6)),
    ("Les deux en AVANT", (0.6, 0.6)),
    ("Les deux en ARRIÈRE", (-0.6, -0.6)),
    ("Pivot à GAUCHE", (-0.6, 0.6)),
    ("Pivot à DROITE", (0.6, -0.6)),
]

car = Car()
try:
    for label, (l, r) in STEPS:
        print(f"-> {label}")
        car.drive(l, r)
        time.sleep(1.5)
        car.stop()
        time.sleep(0.7)
    print("\nRampe de vitesse (avant) 0 -> 100 %")
    for i in range(0, 11):
        car.drive(i / 10, i / 10)
        print(f"   {i*10:3d} %")
        time.sleep(0.4)
    print("Terminé. Si une roue tournait à l'envers, mets "
          "LEFT_INVERTED / RIGHT_INVERTED = True dans config.py")
except KeyboardInterrupt:
    pass
finally:
    car.close()
