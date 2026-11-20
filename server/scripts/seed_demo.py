#!/usr/bin/env python3
"""
Fill the database with demo detections around Bizerte so the map and the
dashboard can be checked without the car. Writes straight to the database
and never calls the geocoding APIs (demo addresses are made up locally).

    python scripts/seed_demo.py            # 80 detections over 30 days
    python scripts/seed_demo.py --count 200 --reset
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from potholepi_server.config import settings  # noqa: E402
from potholepi_server.db import Database  # noqa: E402
from potholepi_server.repositories.detections import DetectionRepository  # noqa: E402

# (lat, lon, road, weight): a few "bad" streets get most of the potholes
SPOTS = [
    (37.27440, 9.87390, "Avenue Habib Bourguiba", 6),
    (37.27120, 9.86810, "Rue de Belgique", 4),
    (37.27890, 9.86450, "Boulevard Hassen Nouri", 3),
    (37.26760, 9.87920, "Route de Tunis", 3),
    (37.28310, 9.87150, "Rue Ibn Khaldoun", 1),
    (37.26200, 9.85600, "Avenue de la République", 1),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=80)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--reset", action="store_true", help="delete existing detections first")
    a = ap.parse_args()

    db = Database(settings.db_path)
    db.init()
    repo = DetectionRepository(db)
    if a.reset:
        with db.connect() as c:
            c.execute("DELETE FROM detections")

    rng = random.Random(42)
    now = time.time()
    weights = [s[3] for s in SPOTS]
    for _ in range(a.count):
        lat0, lon0, road, _w = rng.choices(SPOTS, weights)[0]
        spread = 0.00015 if rng.random() < 0.7 else 0.002
        lat = lat0 + rng.gauss(0, spread)
        lon = lon0 + rng.gauss(0, spread)
        ts = now - rng.random() ** 1.5 * a.days * 86400      # more recent = more frequent
        hour = rng.choices(range(24), [1] * 6 + [4] * 4 + [3] * 6 + [5] * 4 + [2] * 4)[0]
        ts = datetime.fromtimestamp(ts).replace(hour=hour, minute=rng.randint(0, 59)).timestamp()
        ts = min(ts, now)
        car = rng.random() < 0.75
        det_id = repo.insert({
            "lat": lat, "lon": lon, "device_id": "pothole-pi",
            "source": "car_gps" if car else "phone_gps",
            "captured_at": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
            "accuracy_m": round(rng.uniform(2, 6), 1) if car else round(rng.uniform(4, 20), 1),
            "hdop": round(rng.uniform(0.8, 2.4), 1) if car else None,
            "sats": rng.randint(5, 11) if car else None,
            "speed_kmh": round(rng.uniform(0, 8), 1) if car else None,
            "trigger": "manual",
        }, created_at=ts)
        repo.set_address(det_id, f"{road}, Bizerte, Tunisie (demo)", road, "Bizerte", "demo")
        status = rng.choices(["new", "confirmed", "fixed"], [6, 3, 1])[0]
        repo.set_status(det_id, status)
    print(f"{a.count} demo detections written to {settings.db_path}")


if __name__ == "__main__":
    main()
