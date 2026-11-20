"""
Pothole reports: pick the best location, attach a camera snapshot and send
the detection to the Linux server.

Used today by the app's "Send location" button (trigger="manual") and later
by the detector (trigger="model") - same path, same payload.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from ..config import Settings
from ..hardware.gps import GpsFix

log = logging.getLogger(__name__)


@dataclass
class PhoneLocation:
    lat: float
    lon: float
    accuracy_m: float | None = None


class NoLocationError(Exception):
    """Neither the car GPS nor the phone gave a usable position."""


def choose_location(car: GpsFix, phone: PhoneLocation | None, max_age_s: float) -> dict:
    """Car GPS first (if it has a recent fix), phone GPS as fallback."""
    age = car.age_s()
    if car.fix and car.lat is not None and age is not None and age <= max_age_s:
        return {
            "lat": car.lat, "lon": car.lon, "source": "car_gps",
            # NEO-6M: ~2.5 m CEP; HDOP scales it. Rough but useful for the map.
            "accuracy_m": round(2.5 * car.hdop, 1) if car.hdop else None,
            "hdop": car.hdop, "sats": car.sats, "speed_kmh": car.speed_kmh,
        }
    if phone is not None:
        return {
            "lat": phone.lat, "lon": phone.lon, "source": "phone_gps",
            "accuracy_m": phone.accuracy_m, "hdop": None, "sats": None, "speed_kmh": None,
        }
    raise NoLocationError("no GPS fix on the car and no phone location provided")


class Reporter:
    def __init__(self, settings: Settings, gps, camera):
        self.s = settings
        self.gps = gps
        self.camera = camera

    def build(self, phone: PhoneLocation | None, trigger: str = "manual",
              confidence: float | None = None, bbox: list[float] | None = None,
              include_image: bool = True) -> dict:
        payload = choose_location(self.gps.latest(), phone, self.s.GPS_MAX_AGE_S)
        payload.update({
            "device_id": self.s.DEVICE_ID,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger,
            "confidence": confidence,
            "bbox": bbox,
            "image_b64": None,
        })
        if include_image:
            jpg = self.camera.get_jpeg()
            if jpg:
                payload["image_b64"] = base64.b64encode(jpg).decode()
        return payload

    def send(self, payload: dict) -> dict:
        url = f"{self.s.SERVER_URL}/api/detections"
        r = httpx.post(url, json=payload, timeout=self.s.HTTP_TIMEOUT_S)
        r.raise_for_status()
        result = r.json()
        log.info("report sent: #%s (%s, %s)", result.get("id"), payload["source"], payload["trigger"])
        return result

    def report(self, phone: PhoneLocation | None = None, **kwargs) -> dict:
        payload = self.build(phone, **kwargs)
        result = self.send(payload)
        return {"id": result.get("id"), "source": payload["source"],
                "lat": payload["lat"], "lon": payload["lon"],
                "has_image": payload["image_b64"] is not None}
