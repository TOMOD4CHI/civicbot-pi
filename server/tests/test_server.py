import base64
import time

import pytest
from fastapi.testclient import TestClient

from potholepi_server.config import Settings
from potholepi_server.db import Database
from potholepi_server.main import create_app
from potholepi_server.repositories.detections import DetectionRepository
from potholepi_server.services.geocoding import GeocodingService, parse_nominatim, parse_photon
from potholepi_server.services.hotspots import distance_m, hotspots
from potholepi_server.services.stats import compute_stats

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100 + b"\xff\xd9"


@pytest.fixture
def settings(tmp_path):
    return Settings(DATA_DIR=str(tmp_path), GEOCODE_ENABLED=False)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


def det(lat, lon, **kw):
    d = {"lat": lat, "lon": lon, "source": "car_gps", "device_id": "test"}
    d.update(kw)
    return d


# ---------------------------------------------------------------- hotspots
def test_distance():
    assert distance_m(37.0, 9.0, 37.0, 9.0) == 0
    assert distance_m(37.0, 9.0, 37.001, 9.0) == pytest.approx(111.2, abs=0.5)


def test_hotspot_levels():
    now = time.time()
    base = [{"id": i, "lat": 37.0 + i * 1e-5, "lon": 9.0, "created_at": now + i,
             "road": "Rue A", "address": None} for i in range(6)]
    far = [{"id": 100 + i, "lat": 37.01, "lon": 9.01 + i * 1e-5, "created_at": now,
            "road": None, "address": None} for i in range(3)]
    lone = [{"id": 200, "lat": 36.5, "lon": 9.5, "created_at": now, "road": None, "address": None}]
    zones = hotspots(base + far + lone, radius_m=30, warning_min=3, critical_min=5)
    assert [z["level"] for z in zones] == ["critical", "warning"]
    assert zones[0]["count"] == 6 and zones[0]["road"] == "Rue A"
    assert zones[1]["count"] == 3


# ---------------------------------------------------------------- API
def test_create_and_list(client, settings):
    r = client.post("/api/detections", json=det(37.27, 9.87, image_b64=base64.b64encode(JPEG).decode()))
    assert r.status_code == 201
    det_id = r.json()["id"]
    d = client.get(f"/api/detections/{det_id}").json()
    assert d["source"] == "car_gps" and d["status"] == "new" and d["trigger"] == "manual"
    assert d["image_url"] == f"/images/{det_id}.jpg"
    assert client.get(d["image_url"]).content == JPEG
    assert len(client.get("/api/detections").json()) == 1
    assert client.get("/api/detections?source=phone_gps").json() == []


def test_validation(client):
    assert client.post("/api/detections", json=det(91, 9)).status_code == 422
    assert client.post("/api/detections", json=det(37, 9, source="wifi")).status_code == 422
    bad_img = det(37, 9, image_b64=base64.b64encode(b"not a jpeg").decode())
    assert client.post("/api/detections", json=bad_img).status_code == 400


def test_status_update_and_delete(client):
    det_id = client.post("/api/detections", json=det(37, 9)).json()["id"]
    assert client.patch(f"/api/detections/{det_id}", json={"status": "fixed"}).json()["status"] == "fixed"
    assert client.patch(f"/api/detections/{det_id}", json={"status": "bogus"}).status_code == 422
    assert client.delete(f"/api/detections/{det_id}").status_code == 204
    assert client.get(f"/api/detections/{det_id}").status_code == 404


def test_hotspots_and_stats_endpoints(client):
    for i in range(5):
        client.post("/api/detections", json=det(37.0 + i * 1e-5, 9.0))
    client.post("/api/detections", json=det(36.0, 9.0, source="phone_gps"))
    zones = client.get("/api/hotspots").json()
    assert len(zones) == 1 and zones[0]["level"] == "critical"
    st = client.get("/api/stats").json()
    assert st["totals"]["total"] == 6 and st["totals"]["today"] == 6
    assert st["totals"]["critical_zones"] == 1
    assert st["by_source"] == {"car_gps": 5, "phone_gps": 1}
    assert len(st["per_day"]) == 30 and st["per_day"][-1]["count"] == 6
    assert sum(st["by_hour"]) == 6


def test_fixed_potholes_leave_hotspots(client):
    ids = [client.post("/api/detections", json=det(37.0, 9.0)).json()["id"] for _ in range(3)]
    assert len(client.get("/api/hotspots").json()) == 1
    client.patch(f"/api/detections/{ids[0]}", json={"status": "fixed"})
    assert client.get("/api/hotspots").json() == []


def test_telemetry(client):
    assert client.get("/api/telemetry/latest").json() == {"online": False}
    client.post("/api/telemetry", json={"fix": True, "lat": 37.0, "lon": 9.0, "sats": 7})
    t = client.get("/api/telemetry/latest").json()
    assert t["online"] and t["lat"] == 37.0


def test_web_pages_served(client):
    assert "leaflet" in client.get("/").text.lower()
    assert "chart" in client.get("/dashboard").text.lower()


def test_stats_empty():
    st = compute_stats([], 30, 3, 5)
    assert st["totals"]["total"] == 0 and st["hotspots"] == []


# ---------------------------------------------------------------- geocoding
def test_parsers():
    n = parse_nominatim({"display_name": "Rue X, Bizerte, Tunisie",
                         "address": {"road": "Rue X", "city": "Bizerte"}})
    assert (n.road, n.city, n.source) == ("Rue X", "Bizerte", "nominatim")
    p = parse_photon({"features": [{"properties": {"street": "Rue Y", "city": "Bizerte",
                                                     "country": "Tunisie"}}]})
    assert p.display == "Rue Y, Bizerte, Tunisie" and p.road == "Rue Y"
    assert parse_nominatim({}) is None and parse_photon({"features": []}) is None


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeClient:
    def __init__(self):
        self.calls = []

    def get(self, url, params):
        self.calls.append(url)
        if "nominatim" in url:
            raise ConnectionError("down")
        return FakeResponse({"features": [{"properties": {"street": "Rue Z", "city": "Bizerte"}}]})


def test_geocoder_fallback_and_cache(settings):
    settings.GEOCODE_MIN_INTERVAL_S = 0
    db = Database(settings.db_path)
    db.init()
    repo = DetectionRepository(db)
    fake = FakeClient()
    geo = GeocodingService(settings, db, repo, client=fake)
    a = geo.lookup(37.27441, 9.87391)
    assert a.source == "photon" and a.road == "Rue Z"
    b = geo.lookup(37.27443, 9.87389)          # same ~11 m cell -> cache, no new call
    assert b.source == "cache" and len(fake.calls) == 2
