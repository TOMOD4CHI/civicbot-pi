#!/usr/bin/env python3
"""
Wiring / calibration test, run directly on the Pi (over SSH).
Put the car on a stand, wheels in the air! Stop the car service first
(it holds the GPIO pins):  sudo systemctl stop potholepi-car

    cd ~/civicbot-pi/car && .venv/bin/python scripts/test_motors.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from potholepi_car.config import settings  # noqa: E402
from potholepi_car.hardware.motors import Car  # noqa: E402

STEPS = [
    ("LEFT motor only, forward", (0.6, 0)),
    ("LEFT motor only, backward", (-0.6, 0)),
    ("RIGHT motor only, forward", (0, 0.6)),
    ("RIGHT motor only, backward", (0, -0.6)),
    ("Both FORWARD", (0.6, 0.6)),
    ("Both BACKWARD", (-0.6, -0.6)),
    ("Pivot LEFT", (-0.6, 0.6)),
    ("Pivot RIGHT", (0.6, -0.6)),
]

car = Car(settings)
print(f"MIN_DUTY={settings.MIN_DUTY}  MAX_DUTY={settings.MAX_DUTY}  "
      f"LEFT_EN={settings.LEFT_EN}  RIGHT_EN={settings.RIGHT_EN}")
try:
    for label, (left, right) in STEPS:
        print(f"-> {label}")
        car.drive(left, right)
        time.sleep(1.5)
        car.stop()
        time.sleep(0.7)
    print("\nSpeed ramp (forward) 0 -> 100 %")
    for i in range(0, 11):
        car.drive(i / 10, i / 10)
        print(f"   {i * 10:3d} %")
        time.sleep(0.4)
    print("Done. If a wheel turned the wrong way set POTHOLEPI_LEFT_INVERTED / "
          "POTHOLEPI_RIGHT_INVERTED=true in car/.env")
except KeyboardInterrupt:
    pass
finally:
    car.close()
