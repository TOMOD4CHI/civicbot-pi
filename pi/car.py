"""
Pilotage d'une voiture à 2 moteurs (propulsion différentielle) + 1 roue folle
via un driver L298N sur Raspberry Pi 4.

Principe : pas de servo de direction. Pour tourner, on fait tourner les
deux roues motrices à des vitesses différentes (ou en sens opposé pour
pivoter sur place). La roue folle suit librement.
"""
from gpiozero import Motor
import config


def _clamp(v, lo=-1.0, hi=1.0):
    return max(lo, min(hi, v))


class Car:
    def __init__(self):
        self.left = Motor(forward=config.LEFT_IN1, backward=config.LEFT_IN2,
                          enable=config.LEFT_EN, pwm=True)
        self.right = Motor(forward=config.RIGHT_IN3, backward=config.RIGHT_IN4,
                           enable=config.RIGHT_EN, pwm=True)
        self.speed_l = 0.0
        self.speed_r = 0.0

    # ---------- bas niveau ----------
    @staticmethod
    def _apply(motor, value, inverted, trim):
        value = _clamp(value) * trim
        if inverted:
            value = -value
        mag = abs(value)
        if mag < 0.01:
            motor.stop()
            return
        # remap 0..1 -> MIN_DUTY..MAX_DUTY : démarrage franc + tension plafonnée
        mag = config.MIN_DUTY + (config.MAX_DUTY - config.MIN_DUTY) * mag
        if value > 0:
            motor.forward(mag)
        else:
            motor.backward(mag)

    def drive(self, left, right):
        """left / right entre -1.0 (arrière plein) et 1.0 (avant plein)."""
        self.speed_l, self.speed_r = _clamp(left), _clamp(right)
        self._apply(self.left, self.speed_l, config.LEFT_INVERTED, config.LEFT_TRIM)
        self._apply(self.right, self.speed_r, config.RIGHT_INVERTED, config.RIGHT_TRIM)

    # ---------- haut niveau ----------
    def arcade(self, throttle, steering):
        """throttle: -1..1 (avant/arrière), steering: -1..1 (gauche/droite)."""
        left = throttle + steering
        right = throttle - steering
        m = max(1.0, abs(left), abs(right))   # normalisation
        self.drive(left / m, right / m)

    def forward(self, speed=0.6):   self.drive(speed, speed)
    def backward(self, speed=0.6):  self.drive(-speed, -speed)
    def turn_left(self, speed=0.6): self.drive(-speed, speed)    # pivot sur place
    def turn_right(self, speed=0.6): self.drive(speed, -speed)

    def stop(self):
        self.drive(0, 0)

    def close(self):
        self.stop()
        self.left.close()
        self.right.close()
