"""Dashboard aggregates (computed in Python, in the server's local time zone)."""
from __future__ import annotations

import time
from collections import Counter
from datetime import date, datetime, timedelta

from .hotspots import hotspots as compute_hotspots


def _day(ts: float) -> date:
    return datetime.fromtimestamp(ts).date()


def compute_stats(detections: list[dict], radius_m: float, warning_min: int,
                  critical_min: int, now: float | None = None, days: int = 30) -> dict:
    now = now or time.time()
    today = _day(now)
    open_dets = [d for d in detections if d["status"] != "fixed"]
    zones = compute_hotspots(open_dets, radius_m, warning_min, critical_min)

    per_day = Counter(_day(d["created_at"]) for d in detections)
    by_hour = Counter(datetime.fromtimestamp(d["created_at"]).hour for d in detections)
    by_weekday = Counter(datetime.fromtimestamp(d["created_at"]).weekday() for d in detections)
    last_30 = [d for d in detections if _day(d["created_at"]) > today - timedelta(days=days)]

    def count_since(n_days: int) -> int:
        return sum(1 for d in detections if _day(d["created_at"]) > today - timedelta(days=n_days))

    total = len(detections)
    return {
        "generated_at": now,
        "totals": {
            "total": total,
            "today": per_day.get(today, 0),
            "last_7_days": count_since(7),
            "last_30_days": len(last_30),
            "open": len(open_dets),
            "confirmed": sum(1 for d in detections if d["status"] == "confirmed"),
            "fixed": sum(1 for d in detections if d["status"] == "fixed"),
            "critical_zones": sum(1 for z in zones if z["level"] == "critical"),
            "warning_zones": sum(1 for z in zones if z["level"] == "warning"),
            "avg_per_day_30d": round(len(last_30) / days, 2),
            "with_image_pct": round(100 * sum(1 for d in detections if d["image_url"]) / total, 1) if total else 0,
            "geocoded_pct": round(100 * sum(1 for d in detections if d["address"]) / total, 1) if total else 0,
            "last_detection_at": max((d["created_at"] for d in detections), default=None),
        },
        "by_source": dict(Counter(d["source"] for d in detections)),
        "by_trigger": dict(Counter(d["trigger"] for d in detections)),
        "by_status": dict(Counter(d["status"] for d in detections)),
        "per_day": [
            {"date": (today - timedelta(days=i)).isoformat(),
             "count": per_day.get(today - timedelta(days=i), 0)}
            for i in range(days - 1, -1, -1)
        ],
        "by_hour": [by_hour.get(h, 0) for h in range(24)],
        "by_weekday": [by_weekday.get(w, 0) for w in range(7)],
        "top_roads": [{"road": r, "count": c} for r, c in
                      Counter(d["road"] for d in detections if d["road"]).most_common(8)],
        "top_cities": [{"city": r, "count": c} for r, c in
                       Counter(d["city"] for d in detections if d["city"]).most_common(5)],
        "hotspots": zones[:10],
        "recent": detections[:20],
    }
