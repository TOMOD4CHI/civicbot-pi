"""
Reverse geocoding with OpenStreetMap: Nominatim first, Photon (komoot) as
fallback.

Policy-friendly by design:
  * one background worker -> requests are strictly sequential, >= 1.1 s apart
  * a User-Agent that identifies the app with a contact e-mail
  * a persistent cache keyed on coordinates rounded to 4 decimals (~11 m)
  * lookups happen once per *detection*, never per GPS update
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass

import httpx

from ..config import Settings
from ..db import Database
from ..repositories.detections import DetectionRepository

log = logging.getLogger(__name__)


@dataclass
class Address:
    display: str
    road: str | None
    city: str | None
    source: str


def parse_nominatim(d: dict) -> Address | None:
    if not d.get("display_name"):
        return None
    a = d.get("address", {})
    road = a.get("road") or a.get("pedestrian") or a.get("path") or a.get("suburb")
    city = a.get("city") or a.get("town") or a.get("village") or a.get("municipality")
    return Address(d["display_name"], road, city, "nominatim")


def parse_photon(d: dict) -> Address | None:
    if not d.get("features"):
        return None
    p = d["features"][0]["properties"]
    street = " ".join(x for x in (p.get("housenumber"), p.get("street")) if x)
    parts = [p.get("name"), street, p.get("district"), p.get("city"),
             p.get("postcode"), p.get("country")]
    seen, out = set(), []
    for x in parts:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    if not out:
        return None
    return Address(", ".join(out), p.get("street") or p.get("name"), p.get("city"), "photon")


class GeocodingService:
    def __init__(self, settings: Settings, db: Database, repo: DetectionRepository,
                 client: httpx.Client | None = None):
        self.s = settings
        self.db = db
        self.repo = repo
        self.client = client or httpx.Client(timeout=8, headers={"User-Agent": settings.user_agent})
        self.queue: queue.Queue[int | None] = queue.Queue()
        self._last_request = 0.0
        self._thread = threading.Thread(target=self._run, name="geocoder", daemon=True)

    # ------------------------------------------------------------ public
    def start(self) -> None:
        if not self.s.GEOCODE_ENABLED:
            log.info("geocoding disabled")
            return
        if not self.s.CONTACT_EMAIL:
            log.warning("CONTACT_EMAIL is empty: Nominatim asks for a User-Agent that "
                        "identifies the app. Set POTHOLEPI_CONTACT_EMAIL in server/.env")
        for det_id, _, _ in self.repo.needing_address():
            self.queue.put(det_id)
        self._thread.start()

    def stop(self) -> None:
        self.queue.put(None)

    def enqueue(self, det_id: int) -> None:
        if self.s.GEOCODE_ENABLED:
            self.queue.put(det_id)

    def lookup(self, lat: float, lon: float) -> Address | None:
        key = (round(lat, 4), round(lon, 4))
        cached = self._cache_get(key)
        if cached:
            return cached
        for name, fn in (("nominatim", self._nominatim), ("photon", self._photon)):
            try:
                addr = fn(lat, lon)
                if addr:
                    self._cache_put(key, addr)
                    return addr
            except Exception as e:
                log.warning("%s unavailable: %s", name, e)
        return None

    # ------------------------------------------------------------ worker
    def _run(self) -> None:
        while True:
            det_id = self.queue.get()
            if det_id is None:
                return
            det = self.repo.get(det_id)
            if not det or det["address"]:
                continue
            addr = self.lookup(det["lat"], det["lon"])
            if addr:
                self.repo.set_address(det_id, addr.display, addr.road, addr.city, addr.source)
                log.info("#%d -> %s (%s)", det_id, addr.display, addr.source)
            else:
                self.repo.set_address(det_id, None, None, None, None)   # counts the try

    # ------------------------------------------------------------ providers
    def _get(self, url: str, params: dict) -> dict:
        wait = self.s.GEOCODE_MIN_INTERVAL_S - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            r = self.client.get(url, params=params)
            r.raise_for_status()
            return r.json()
        finally:
            self._last_request = time.monotonic()

    def _nominatim(self, lat: float, lon: float) -> Address | None:
        return parse_nominatim(self._get(self.s.NOMINATIM_URL, {
            "lat": lat, "lon": lon, "format": "jsonv2", "zoom": 18,
            "addressdetails": 1, "accept-language": self.s.LANGUAGE}))

    def _photon(self, lat: float, lon: float) -> Address | None:
        return parse_photon(self._get(self.s.PHOTON_URL, {
            "lat": lat, "lon": lon, "lang": self.s.LANGUAGE}))

    # ------------------------------------------------------------ cache
    def _cache_get(self, key) -> Address | None:
        with self.db.connect() as c:
            row = c.execute("SELECT * FROM geocode_cache WHERE lat_key=? AND lon_key=?", key).fetchone()
        return Address(row["address"], row["road"], row["city"], "cache") if row else None

    def _cache_put(self, key, a: Address) -> None:
        with self.db.connect() as c:
            c.execute("INSERT OR REPLACE INTO geocode_cache VALUES (?,?,?,?,?,?,?)",
                      (*key, a.display, a.road, a.city, a.source, time.time()))
