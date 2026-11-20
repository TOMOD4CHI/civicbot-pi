"""
Critical zones: group nearby detections and rank them.

Greedy clustering: each detection joins the nearest cluster whose centroid is
within ``radius_m``, otherwise it starts a new one. Clusters with at least
``warning_min`` detections are "warning" zones, at least ``critical_min``
"critical". Fixed potholes are excluded by the caller.
"""
from __future__ import annotations

import math
from collections import Counter


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def cluster(detections: list[dict], radius_m: float) -> list[list[dict]]:
    clusters: list[dict] = []        # {"lat", "lon", "items"}
    for d in sorted(detections, key=lambda x: x["created_at"]):
        best, best_dist = None, radius_m
        for c in clusters:
            dist = distance_m(d["lat"], d["lon"], c["lat"], c["lon"])
            if dist <= best_dist:
                best, best_dist = c, dist
        if best is None:
            clusters.append({"lat": d["lat"], "lon": d["lon"], "items": [d]})
        else:
            best["items"].append(d)
            n = len(best["items"])
            best["lat"] += (d["lat"] - best["lat"]) / n
            best["lon"] += (d["lon"] - best["lon"]) / n
    return [c["items"] for c in clusters]


def hotspots(detections: list[dict], radius_m: float, warning_min: int,
             critical_min: int) -> list[dict]:
    out = []
    for items in cluster(detections, radius_m):
        n = len(items)
        if n < warning_min:
            continue
        lat = sum(i["lat"] for i in items) / n
        lon = sum(i["lon"] for i in items) / n
        spread = max(distance_m(lat, lon, i["lat"], i["lon"]) for i in items)
        roads = Counter(i["road"] for i in items if i.get("road"))
        with_addr = [i for i in items if i.get("address")]
        out.append({
            "lat": lat, "lon": lon, "count": n,
            "level": "critical" if n >= critical_min else "warning",
            "radius_m": round(max(spread + 10, 15), 1),
            "first_at": min(i["created_at"] for i in items),
            "last_at": max(i["created_at"] for i in items),
            "road": roads.most_common(1)[0][0] if roads else None,
            "address": with_addr[-1]["address"] if with_addr else None,
            "detection_ids": [i["id"] for i in items],
        })
    out.sort(key=lambda h: (h["count"], h["last_at"]), reverse=True)
    return out
