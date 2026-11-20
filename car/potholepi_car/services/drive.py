"""
Drive service: the only place that talks to the motors.

Safety rules (kept from the original TCP server):
  * a watchdog stops the car if no command arrives for WATCHDOG_TIMEOUT s
    (lost Wi-Fi, app closed, phone locked...)
  * the car stops when the controlling client disconnects
"""
from __future__ import annotations

import logging
import threading
import time

from ..hardware.motors import arcade_mix, clamp

log = logging.getLogger(__name__)


class DriveService:
    def __init__(self, car, watchdog_timeout: float):
        self.car = car
        self.timeout = watchdog_timeout
        self.lock = threading.Lock()
        self.last_cmd = time.monotonic()
        self.clients = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watchdog, name="watchdog", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        with self.lock:
            self.car.close()

    # ------------------------------------------------------------ commands
    def drive(self, left: float, right: float) -> None:
        with self.lock:
            self.last_cmd = time.monotonic()
            self.car.drive(clamp(left), clamp(right))

    def arcade(self, throttle: float, steering: float) -> None:
        self.drive(*arcade_mix(throttle, steering))

    def stop(self) -> None:
        with self.lock:
            self.last_cmd = time.monotonic()
            self.car.stop()

    def ping(self) -> None:
        with self.lock:
            self.last_cmd = time.monotonic()

    # ------------------------------------------------------------ clients
    def client_connected(self) -> None:
        with self.lock:
            self.clients += 1

    def client_disconnected(self) -> None:
        with self.lock:
            self.clients = max(0, self.clients - 1)
            self.car.stop()
        log.info("control client disconnected -> STOP")

    def status(self) -> dict:
        with self.lock:
            return {"left": self.car.speed_l, "right": self.car.speed_r,
                    "moving": self.car.moving, "clients": self.clients}

    # ------------------------------------------------------------ watchdog
    def _watchdog(self) -> None:
        while not self._stop.wait(0.1):
            with self.lock:
                if self.car.moving and time.monotonic() - self.last_cmd > self.timeout:
                    self.car.stop()
                    log.warning("watchdog: no command for %.1f s -> STOP", self.timeout)
