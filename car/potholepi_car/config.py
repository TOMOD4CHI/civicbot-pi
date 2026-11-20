"""
Pothole Pi car settings.

Every value has a default here and can be overridden with an environment
variable of the same name prefixed with ``POTHOLEPI_`` (e.g.
``POTHOLEPI_SERVER_URL=http://192.168.1.20:8000``). The systemd unit loads
them from ``car/.env``.

Pin numbers are BCM (GPIOxx), not physical pin numbers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
CAR_DIR = PACKAGE_DIR.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines) so no extra dependency is needed."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _optional_int(value: str) -> int | None:
    return None if value.strip().lower() in ("", "none", "null") else int(value)


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    # --- Simulation: run without any hardware (mock GPIO, fake GPS, test camera)
    SIMULATE: bool = False

    # --- L298N wiring -------------------------------------------------------
    # ENA/ENB jumpers ON  -> LEFT_EN = RIGHT_EN = None (PWM on the IN pins).
    # Never wire a GPIO to ENA/ENB while its jumper is on (5 V on a 3.3 V pin).
    LEFT_IN1: int = 17
    LEFT_IN2: int = 27
    LEFT_EN: int | None = None
    RIGHT_IN3: int = 22
    RIGHT_IN4: int = 23
    RIGHT_EN: int | None = None

    # --- Motor calibration ----------------------------------------------------
    LEFT_INVERTED: bool = False
    RIGHT_INVERTED: bool = False
    LEFT_TRIM: float = 1.0           # e.g. 0.95 slows this motor by 5 %
    RIGHT_TRIM: float = 1.0
    MIN_DUTY: float = 0.25           # below this TT motors hum without turning
    MAX_DUTY: float = 0.6            # TT motors are 3-6 V; pack is ~12 V

    # --- Safety -----------------------------------------------------------------
    WATCHDOG_TIMEOUT: float = 0.5    # seconds without a command -> stop

    # --- HTTP API (this service) -----------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # --- GPS (GY-NEO6MV2 on the UART) ---------------------------------------------
    GPS_ENABLED: bool = True
    GPS_SERIAL_PORT: str = "/dev/serial0"
    GPS_BAUDRATE: int = 9600
    GPS_MAX_AGE_S: float = 5.0       # a car fix older than this is not used

    # --- Camera -------------------------------------------------------------------
    CAMERA_ENABLED: bool = True
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480
    CAMERA_FPS: int = 15
    CAMERA_JPEG_QUALITY: int = 80
    CAMERA_USB_INDEX: int = 0        # used only if Picamera2 is unavailable

    # --- Linux server -------------------------------------------------------------------
    SERVER_URL: str = "http://192.168.1.100:8000"
    DEVICE_ID: str = "pothole-pi"
    TELEMETRY_INTERVAL_S: float = 2.0
    HTTP_TIMEOUT_S: float = 5.0

    # --- Pothole detection (model not integrated yet) ------------------------------
    DETECTION_ENABLED: bool = False
    DETECTION_MODEL_PATH: str = str(CAR_DIR / "models" / "pothole.pt")
    DETECTION_MIN_CONFIDENCE: float = 0.5
    DETECTION_COOLDOWN_S: float = 3.0   # min time between two automatic reports

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv(CAR_DIR / ".env")
        s = cls()
        for f in fields(cls):
            raw = os.environ.get(f"POTHOLEPI_{f.name}")
            if raw is None:
                continue
            current = getattr(s, f.name)
            if f.name in ("LEFT_EN", "RIGHT_EN"):
                value = _optional_int(raw)
            elif isinstance(current, bool):
                value = _bool(raw)
            elif isinstance(current, int):
                value = int(raw)
            elif isinstance(current, float):
                value = float(raw)
            else:
                value = raw
            setattr(s, f.name, value)
        s.SERVER_URL = s.SERVER_URL.rstrip("/")
        return s


settings = Settings.from_env()
