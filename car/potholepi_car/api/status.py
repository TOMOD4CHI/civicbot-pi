"""GET /api/status - everything the app's status bar needs."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/status")
def status(request: Request):
    rt = request.app.state.rt
    return {
        "device_id": rt.settings.DEVICE_ID,
        "simulate": rt.settings.SIMULATE,
        "drive": rt.drive.status(),
        "gps": {**rt.gps.latest().to_dict(), "connected": rt.gps.connected, "error": rt.gps.error},
        "camera": {"source": rt.camera.name, "ok": rt.camera.ok, "error": rt.camera.error},
        "server": {"url": rt.settings.SERVER_URL, "reachable": rt.telemetry.server_ok},
        "detector": {"name": rt.detector.name, "active": rt.detection.active,
                     "reports": rt.detection.reports},
    }


@router.get("/health")
def health():
    return {"ok": True}
