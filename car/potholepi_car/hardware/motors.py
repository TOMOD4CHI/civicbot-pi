"""
Differential drive: two driven DC motors on an L298N + one free caster wheel.

No steering servo: the car turns by running the two wheels at different
speeds (or in opposite directions to pivot on the spot).
"""
from __future__ import annotations

from ..config import Settings


def clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def to_duty(value: float, min_duty: float, max_duty: float) -> float:
    """Map a speed magnitude 0..1 to a PWM duty in MIN_DUTY..MAX_DUTY.

    0 stays 0 (motor stopped). Any non-zero speed starts at MIN_DUTY so the
    motor really turns, and full speed is capped at MAX_DUTY to protect the
    3-6 V TT motors on a ~12 V supply.
    """
    mag = abs(value)
    if mag < 0.01:
        return 0.0
    return min_duty + (max_duty - min_duty) * min(mag, 1.0)


def arcade_mix(throttle: float, steering: float) -> tuple[float, float]:
    """throttle/steering in -1..1 -> (left, right) in -1..1."""
    left = throttle + steering
    right = throttle - steering
    m = max(1.0, abs(left), abs(right))
    return left / m, right / m


class Car:
    def __init__(self, settings: Settings):
        from gpiozero import Motor  # imported here so tests can set a pin factory first

        self.s = settings
        self.left = Motor(forward=settings.LEFT_IN1, backward=settings.LEFT_IN2,
                          enable=settings.LEFT_EN, pwm=True)
        self.right = Motor(forward=settings.RIGHT_IN3, backward=settings.RIGHT_IN4,
                           enable=settings.RIGHT_EN, pwm=True)
        self.speed_l = 0.0
        self.speed_r = 0.0

    @property
    def moving(self) -> bool:
        return self.speed_l != 0 or self.speed_r != 0

    def _apply(self, motor, value: float, inverted: bool, trim: float) -> None:
        value = clamp(value) * trim
        if inverted:
            value = -value
        duty = to_duty(value, self.s.MIN_DUTY, self.s.MAX_DUTY)
        if duty == 0:
            motor.stop()
        elif value > 0:
            motor.forward(duty)
        else:
            motor.backward(duty)

    def drive(self, left: float, right: float) -> None:
        """left / right between -1.0 (full reverse) and 1.0 (full forward)."""
        self.speed_l, self.speed_r = clamp(left), clamp(right)
        self._apply(self.left, self.speed_l, self.s.LEFT_INVERTED, self.s.LEFT_TRIM)
        self._apply(self.right, self.speed_r, self.s.RIGHT_INVERTED, self.s.RIGHT_TRIM)

    def arcade(self, throttle: float, steering: float) -> None:
        self.drive(*arcade_mix(throttle, steering))

    def stop(self) -> None:
        self.drive(0, 0)

    def close(self) -> None:
        self.stop()
        self.left.close()
        self.right.close()
