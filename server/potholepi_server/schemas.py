"""API data models."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Source = Literal["car_gps", "phone_gps"]
Trigger = Literal["manual", "model"]
Status = Literal["new", "confirmed", "fixed"]


class DetectionIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    source: Source
    device_id: str | None = None
    captured_at: str | None = None
    accuracy_m: float | None = None
    hdop: float | None = None
    sats: int | None = None
    speed_kmh: float | None = None
    trigger: Trigger = "manual"
    confidence: float | None = Field(None, ge=0, le=1)
    bbox: list[float] | None = None
    severity: str | None = None
    image_b64: str | None = None


class DetectionOut(BaseModel):
    id: int
    created_at: float
    captured_at: str | None
    device_id: str | None
    lat: float
    lon: float
    source: str
    accuracy_m: float | None
    hdop: float | None
    sats: int | None
    speed_kmh: float | None
    trigger: str
    confidence: float | None
    bbox: list[float] | None
    severity: str | None
    image_url: str | None
    address: str | None
    road: str | None
    city: str | None
    address_source: str | None
    status: str


class StatusUpdate(BaseModel):
    status: Status


class Hotspot(BaseModel):
    lat: float
    lon: float
    count: int
    level: Literal["warning", "critical"]
    radius_m: float
    first_at: float
    last_at: float
    road: str | None
    address: str | None
    detection_ids: list[int]


class TelemetryIn(BaseModel):
    device_id: str | None = None
    fix: bool = False
    lat: float | None = None
    lon: float | None = None
    alt: float | None = None
    speed_kmh: float | None = None
    course: float | None = None
    sats: int | None = None
    hdop: float | None = None
    utc: str | None = None
    moving: bool | None = None
