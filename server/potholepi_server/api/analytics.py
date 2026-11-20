"""Critical zones and dashboard statistics."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..schemas import Hotspot
from ..services.hotspots import hotspots
from ..services.stats import compute_stats

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/hotspots", response_model=list[Hotspot])
def get_hotspots(request: Request, since: float | None = None, until: float | None = None,
                 source: str | None = None,
                 include_fixed: bool = Query(False, description="count fixed potholes too")):
    ctx = request.app.state.ctx
    s = ctx.settings
    dets = ctx.repo.list(since, until, source)
    if not include_fixed:
        dets = [d for d in dets if d["status"] != "fixed"]
    return hotspots(dets, s.HOTSPOT_RADIUS_M, s.WARNING_MIN, s.CRITICAL_MIN)


@router.get("/stats")
def get_stats(request: Request, days: int = Query(30, ge=7, le=365)):
    ctx = request.app.state.ctx
    s = ctx.settings
    data = compute_stats(ctx.repo.list(), s.HOTSPOT_RADIUS_M, s.WARNING_MIN, s.CRITICAL_MIN, days=days)
    data["config"] = {"hotspot_radius_m": s.HOTSPOT_RADIUS_M, "warning_min": s.WARNING_MIN,
                      "critical_min": s.CRITICAL_MIN}
    return data
