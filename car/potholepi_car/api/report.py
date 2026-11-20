"""POST /api/report - the app's "Send location" button (later: the detector)."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.reporter import NoLocationError, PhoneLocation

router = APIRouter()


class ReportIn(BaseModel):
    phone_lat: float | None = Field(None, ge=-90, le=90)
    phone_lon: float | None = Field(None, ge=-180, le=180)
    phone_accuracy: float | None = Field(None, ge=0)
    include_image: bool = True


@router.post("/api/report")
def report(body: ReportIn, request: Request):
    rt = request.app.state.rt
    phone = None
    if body.phone_lat is not None and body.phone_lon is not None:
        phone = PhoneLocation(body.phone_lat, body.phone_lon, body.phone_accuracy)
    try:
        return rt.reporter.report(phone, trigger="manual", include_image=body.include_image)
    except NoLocationError as e:
        raise HTTPException(422, str(e))
    except httpx.HTTPError as e:
        raise HTTPException(502, f"server unreachable ({rt.settings.SERVER_URL}): {e}")
