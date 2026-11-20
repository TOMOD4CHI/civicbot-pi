"""Live car position (kept in memory only; drives the car marker on the map)."""
from __future__ import annotations

import threading
import time

from fastapi import APIRouter, Request

from ..schemas import TelemetryIn

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])
_lock = threading.Lock()
_latest: dict = {}


@router.post("")
def post_telemetry(body: TelemetryIn, request: Request):
    with _lock:
        _latest.clear()
        _latest.update(body.model_dump())
        _latest["received"] = time.time()
        _latest["client"] = request.client.host if request.client else None
    return {"ok": True}


@router.get("/latest")
def latest(request: Request):
    with _lock:
        p = dict(_latest)
    if not p:
        return {"online": False}
    age = time.time() - p["received"]
    p["age_s"] = round(age, 1)
    p["online"] = age < request.app.state.ctx.settings.TELEMETRY_STALE_S
    return p
