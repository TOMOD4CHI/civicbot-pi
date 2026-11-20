"""SQLite storage: one short-lived connection per operation (thread-safe)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS detections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      REAL    NOT NULL,           -- server receive time (unix s)
    captured_at     TEXT,                       -- car/phone capture time (ISO 8601)
    device_id       TEXT,
    lat             REAL    NOT NULL,
    lon             REAL    NOT NULL,
    source          TEXT    NOT NULL,           -- car_gps | phone_gps
    accuracy_m      REAL,
    hdop            REAL,
    sats            INTEGER,
    speed_kmh       REAL,
    trigger         TEXT    NOT NULL DEFAULT 'manual',   -- manual | model
    confidence      REAL,
    bbox            TEXT,                       -- JSON [x1,y1,x2,y2]
    severity        TEXT,
    image_path      TEXT,
    address         TEXT,
    road            TEXT,
    city            TEXT,
    address_source  TEXT,                       -- nominatim | photon | cache
    geocode_tries   INTEGER NOT NULL DEFAULT 0,
    status          TEXT    NOT NULL DEFAULT 'new'       -- new | confirmed | fixed
);
CREATE INDEX IF NOT EXISTS idx_det_created ON detections(created_at);
CREATE INDEX IF NOT EXISTS idx_det_geo ON detections(lat, lon);

CREATE TABLE IF NOT EXISTS geocode_cache (
    lat_key   REAL NOT NULL,
    lon_key   REAL NOT NULL,
    address   TEXT,
    road      TEXT,
    city      TEXT,
    source    TEXT,
    fetched_at REAL,
    PRIMARY KEY (lat_key, lon_key)
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
