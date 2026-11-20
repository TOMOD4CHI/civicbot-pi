"""All SQL for the detections table lives here."""
from __future__ import annotations

import json
import time

from ..db import Database

COLUMNS = ("captured_at", "device_id", "lat", "lon", "source", "accuracy_m", "hdop",
           "sats", "speed_kmh", "trigger", "confidence", "bbox", "severity")


def row_to_dict(row) -> dict:
    d = dict(row)
    d["bbox"] = json.loads(d["bbox"]) if d.get("bbox") else None
    d["image_url"] = f"/images/{d['image_path']}" if d.get("image_path") else None
    d.pop("image_path", None)
    d.pop("geocode_tries", None)
    return d


class DetectionRepository:
    def __init__(self, db: Database):
        self.db = db

    def insert(self, data: dict, created_at: float | None = None) -> int:
        values = {k: data.get(k) for k in COLUMNS}
        if values["bbox"] is not None:
            values["bbox"] = json.dumps(values["bbox"])
        cols = ", ".join(("created_at",) + COLUMNS)
        marks = ", ".join("?" * (len(COLUMNS) + 1))
        with self.db.connect() as c:
            cur = c.execute(f"INSERT INTO detections ({cols}) VALUES ({marks})",
                            (created_at or time.time(), *values.values()))
            return cur.lastrowid

    def set_image(self, det_id: int, image_path: str) -> None:
        with self.db.connect() as c:
            c.execute("UPDATE detections SET image_path=? WHERE id=?", (image_path, det_id))

    def get(self, det_id: int) -> dict | None:
        with self.db.connect() as c:
            row = c.execute("SELECT * FROM detections WHERE id=?", (det_id,)).fetchone()
        return row_to_dict(row) if row else None

    def list(self, since: float | None = None, until: float | None = None,
             source: str | None = None, status: str | None = None,
             limit: int = 5000) -> list[dict]:
        where, args = [], []
        if since is not None:
            where.append("created_at >= ?"); args.append(since)
        if until is not None:
            where.append("created_at <= ?"); args.append(until)
        if source:
            where.append("source = ?"); args.append(source)
        if status:
            where.append("status = ?"); args.append(status)
        sql = "SELECT * FROM detections"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT ?"
        with self.db.connect() as c:
            rows = c.execute(sql, (*args, limit)).fetchall()
        return [row_to_dict(r) for r in rows]

    def set_status(self, det_id: int, status: str) -> bool:
        with self.db.connect() as c:
            return c.execute("UPDATE detections SET status=? WHERE id=?",
                             (status, det_id)).rowcount > 0

    def delete(self, det_id: int) -> dict | None:
        det = self.get(det_id)
        if det:
            with self.db.connect() as c:
                c.execute("DELETE FROM detections WHERE id=?", (det_id,))
        return det

    # ------------------------------------------------------------ geocoding
    def needing_address(self, max_tries: int = 3) -> list[tuple[int, float, float]]:
        with self.db.connect() as c:
            rows = c.execute("SELECT id, lat, lon FROM detections WHERE address IS NULL "
                             "AND geocode_tries < ? ORDER BY id", (max_tries,)).fetchall()
        return [(r["id"], r["lat"], r["lon"]) for r in rows]

    def set_address(self, det_id: int, address: str | None, road: str | None,
                    city: str | None, source: str | None) -> None:
        with self.db.connect() as c:
            c.execute("UPDATE detections SET address=?, road=?, city=?, address_source=?, "
                      "geocode_tries = geocode_tries + 1 WHERE id=?",
                      (address, road, city, source, det_id))
