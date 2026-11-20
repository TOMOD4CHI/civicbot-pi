"""
Pothole Pi server settings. Defaults below; override any field with an
environment variable prefixed ``POTHOLEPI_`` or in ``server/.env``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


@dataclass
class Settings:
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATA_DIR: str = str(SERVER_DIR / "data")
    DB_FILE: str = "potholepi.db"
    MAX_IMAGE_BYTES: int = 3_000_000

    # --- Reverse geocoding (OpenStreetMap) ------------------------------------
    # Nominatim usage policy: identify the app with a real contact e-mail,
    # max 1 request/s, cache results. https://operations.osmfoundation.org/policies/nominatim/
    GEOCODE_ENABLED: bool = True
    CONTACT_EMAIL: str = ""
    USER_AGENT: str = "PotholePi/1.0 (student project; contact: {email})"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/reverse"
    PHOTON_URL: str = "https://photon.komoot.io/reverse"
    LANGUAGE: str = "fr"
    GEOCODE_MIN_INTERVAL_S: float = 1.1

    # --- Critical zones -----------------------------------------------------------
    HOTSPOT_RADIUS_M: float = 30.0
    WARNING_MIN: int = 3
    CRITICAL_MIN: int = 5

    # --- Live car marker --------------------------------------------------------
    TELEMETRY_STALE_S: float = 15.0

    @property
    def db_path(self) -> Path:
        return Path(self.DATA_DIR) / self.DB_FILE

    @property
    def images_dir(self) -> Path:
        return Path(self.DATA_DIR) / "images"

    @property
    def user_agent(self) -> str:
        return self.USER_AGENT.format(email=self.CONTACT_EMAIL or "not-set")

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv(SERVER_DIR / ".env")
        s = cls()
        for f in fields(cls):
            raw = os.environ.get(f"POTHOLEPI_{f.name}")
            if raw is None:
                continue
            cur = getattr(s, f.name)
            if isinstance(cur, bool):
                val = raw.strip().lower() in ("1", "true", "yes", "on")
            elif isinstance(cur, int):
                val = int(raw)
            elif isinstance(cur, float):
                val = float(raw)
            else:
                val = raw
            setattr(s, f.name, val)
        return s


settings = Settings.from_env()
