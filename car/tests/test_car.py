import time

import pytest
from fastapi.testclient import TestClient
from gpiozero import Device
from gpiozero.pins.mock import MockFactory, MockPWMPin

from potholepi_car.config import Settings
from potholepi_car.hardware.gps import GpsFix, NmeaParser, checksum_ok, to_decimal
from potholepi_car.hardware.motors import Car, arcade_mix, to_duty
from potholepi_car.services.drive import DriveService
from potholepi_car.services.reporter import NoLocationError, PhoneLocation, choose_location

RMC = "$GPRMC,123519,A,3716.464,N,00952.434,E,022.4,084.4,201126,003.1,W*{cs}"
GGA = "$GPGGA,123519,3716.464,N,00952.434,E,1,08,0.9,545.4,M,46.9,M,,*{cs}"


def with_cs(s: str) -> str:
    body = s[1:s.index("*")]
    cs = 0
    for ch in body:
        cs ^= ord(ch)
    return s.format(cs=f"{cs:02X}")


@pytest.fixture
def mock_pins():
    Device.pin_factory = MockFactory(pin_class=MockPWMPin)
    yield
    Device.pin_factory.reset()


# ---------------------------------------------------------------- GPS
def test_checksum():
    assert checksum_ok(with_cs(RMC))
    assert not checksum_ok(with_cs(RMC).replace("A,37", "V,37"))
    assert not checksum_ok("garbage")


def test_to_decimal():
    assert to_decimal("3716.464", "N") == pytest.approx(37.27440)
    assert to_decimal("00952.434", "W") == pytest.approx(-9.87390)
    assert to_decimal("", "N") is None


def test_parser_rmc_gga():
    p = NmeaParser()
    p.feed(with_cs(RMC))
    p.feed(with_cs(GGA))
    st = p.state
    assert st.fix and st.lat == pytest.approx(37.2744) and st.lon == pytest.approx(9.8739)
    assert st.speed_kmh == pytest.approx(41.5, abs=0.1)
    assert st.sats == 8 and st.hdop == 0.9 and st.alt == 545.4
    assert st.utc.startswith("2026-11-20T12:35:19")
    assert st.age_s() is not None


# ---------------------------------------------------------------- motors
def test_to_duty_range():
    assert to_duty(0, 0.25, 0.6) == 0
    assert to_duty(0.005, 0.25, 0.6) == 0
    assert to_duty(1, 0.25, 0.6) == pytest.approx(0.6)
    assert to_duty(-1, 0.25, 0.6) == pytest.approx(0.6)
    assert to_duty(0.5, 0.25, 0.6) == pytest.approx(0.425)
    assert to_duty(5, 0.25, 0.6) == pytest.approx(0.6)


def test_arcade_mix_normalised():
    assert arcade_mix(1, 0) == (1, 1)
    assert arcade_mix(0, 1) == (1, -1)
    left, right = arcade_mix(1, 1)
    assert (left, right) == (1, 0)


def test_car_applies_cap_and_inversion(mock_pins):
    s = Settings(RIGHT_INVERTED=True)
    car = Car(s)
    car.drive(1, 1)
    assert car.left.value == pytest.approx(0.6)
    assert car.right.value == pytest.approx(-0.6)      # inverted wiring
    car.stop()
    assert car.left.value == 0 and not car.moving
    car.close()


def test_watchdog_stops_car(mock_pins):
    car = Car(Settings())
    drive = DriveService(car, watchdog_timeout=0.2)
    drive.start()
    drive.drive(0.5, 0.5)
    assert car.moving
    time.sleep(0.5)
    assert not car.moving
    drive.close()


# ---------------------------------------------------------------- reporter
def test_choose_location_prefers_fresh_car_fix():
    fix = GpsFix(fix=True, lat=1.0, lon=2.0, hdop=1.2, sats=7, updated=time.monotonic())
    loc = choose_location(fix, PhoneLocation(9, 9, 5), max_age_s=5)
    assert loc["source"] == "car_gps" and loc["lat"] == 1.0 and loc["accuracy_m"] == 3.0


def test_choose_location_falls_back_to_phone():
    stale = GpsFix(fix=True, lat=1.0, lon=2.0, updated=time.monotonic() - 60)
    loc = choose_location(stale, PhoneLocation(9, 8, 5), max_age_s=5)
    assert loc["source"] == "phone_gps" and loc["lat"] == 9 and loc["accuracy_m"] == 5
    with pytest.raises(NoLocationError):
        choose_location(GpsFix(), None, max_age_s=5)


# ---------------------------------------------------------------- API
def test_api_in_simulation():
    from potholepi_car.main import create_app

    s = Settings(SIMULATE=True, SERVER_URL="http://127.0.0.1:9")   # nothing listens there
    with TestClient(create_app(s, start_background=False)) as client:
        st = client.get("/api/status").json()
        assert st["simulate"] and st["gps"]["fix"]

        with client.websocket_connect("/ws/control") as ws:
            ws.send_json({"type": "drive", "left": 0.5, "right": -0.5})
            assert ws.receive_json() == {"type": "ack"}
            assert client.get("/api/status").json()["drive"]["moving"]
            ws.send_json({"type": "nope"})
            assert ws.receive_json()["type"] == "error"
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}
        assert not client.get("/api/status").json()["drive"]["moving"]   # stop on disconnect

        time.sleep(0.3)
        assert client.get("/snapshot.jpg").headers["content-type"] == "image/jpeg"

        r = client.post("/api/report", json={"phone_lat": 37.0, "phone_lon": 9.0})
        assert r.status_code == 502            # server unreachable, reported cleanly
