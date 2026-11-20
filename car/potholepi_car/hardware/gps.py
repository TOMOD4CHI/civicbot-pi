"""
GY-NEO6MV2 GPS: NMEA parsing (RMC + GGA, checksum verified) and a
background reader thread that keeps the latest fix.

Note: ``sats`` comes from GGA, i.e. satellites *used* in the fix, so it is 0
until the module has a fix.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- NMEA
def checksum_ok(sentence: str) -> bool:
    if not sentence.startswith("$") or "*" not in sentence:
        return False
    body, cs = sentence[1:].split("*", 1)
    calc = 0
    for ch in body:
        calc ^= ord(ch)
    try:
        return calc == int(cs[:2], 16)
    except ValueError:
        return False


def to_decimal(value: str, hemi: str) -> float | None:
    """ddmm.mmmm / dddmm.mmmm -> decimal degrees."""
    if not value:
        return None
    dot = value.index(".")
    deg = float(value[:dot - 2])
    minutes = float(value[dot - 2:])
    dec = deg + minutes / 60
    return -dec if hemi in ("S", "W") else dec


@dataclass
class GpsFix:
    fix: bool = False
    lat: float | None = None
    lon: float | None = None
    alt: float | None = None
    speed_kmh: float | None = None
    course: float | None = None
    sats: int = 0
    hdop: float | None = None
    utc: str | None = None
    updated: float = 0.0          # time.monotonic() of the last valid fix

    def age_s(self) -> float | None:
        return None if not self.updated else time.monotonic() - self.updated

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("updated")
        age = self.age_s()
        d["age_s"] = None if age is None else round(age, 1)
        return d


class NmeaParser:
    def __init__(self):
        self.state = GpsFix()

    def feed(self, line: str) -> None:
        if not checksum_ok(line):
            return
        f = line.split("*")[0].split(",")
        kind = f[0][3:]                   # GPRMC / GNRMC -> RMC
        st = self.state
        if kind == "RMC" and len(f) >= 10:
            st.fix = f[2] == "A"
            if st.fix:
                st.lat = to_decimal(f[3], f[4])
                st.lon = to_decimal(f[5], f[6])
                st.speed_kmh = round(float(f[7] or 0) * 1.852, 1)
                st.course = float(f[8]) if f[8] else None
                if f[1] and f[9]:
                    st.utc = datetime.strptime(f[9] + f[1][:6], "%d%m%y%H%M%S") \
                        .replace(tzinfo=timezone.utc).isoformat()
                st.updated = time.monotonic()
        elif kind == "GGA" and len(f) >= 10:
            st.sats = int(f[7] or 0)
            st.hdop = float(f[8]) if f[8] else None
            st.alt = float(f[9]) if f[9] else None


# ---------------------------------------------------------------- readers
class GpsReader:
    """Reads NMEA from the serial port in a daemon thread."""

    def __init__(self, port: str, baudrate: int):
        self.port, self.baudrate = port, baudrate
        self.parser = NmeaParser()
        self.lock = threading.Lock()
        self.connected = False
        self.error: str | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="gps", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def latest(self) -> GpsFix:
        with self.lock:
            return GpsFix(**asdict(self.parser.state))

    def _run(self) -> None:
        try:
            import serial  # pyserial
        except ImportError:
            self.error = "pyserial not installed"
            log.error(self.error)
            return
        while not self._stop.is_set():
            try:
                with serial.Serial(self.port, self.baudrate, timeout=1) as ser:
                    self.connected, self.error = True, None
                    log.info("GPS reading on %s @ %d baud", self.port, self.baudrate)
                    while not self._stop.is_set():
                        line = ser.readline().decode("ascii", errors="ignore").strip()
                        if line:
                            with self.lock:
                                self.parser.feed(line)
            except Exception as e:  # serial errors: retry, never crash the service
                self.connected, self.error = False, str(e)
                log.warning("GPS unavailable (%s), retrying in 5 s", e)
                self._stop.wait(5)


class FakeGps:
    """Simulated fix: a small circle around Bizerte centre."""

    connected = True
    error = None

    def __init__(self, lat0: float = 37.2744, lon0: float = 9.8739):
        self.lat0, self.lon0 = lat0, lon0
        self.t0 = time.monotonic()

    def start(self) -> None: ...
    def stop(self) -> None: ...

    def latest(self) -> GpsFix:
        t = time.monotonic() - self.t0
        return GpsFix(
            fix=True,
            lat=self.lat0 + 0.0015 * math.sin(t / 20),
            lon=self.lon0 + 0.0015 * math.cos(t / 20),
            alt=5.0, speed_kmh=4.0, course=(t * 3) % 360, sats=8, hdop=1.0,
            utc=datetime.now(timezone.utc).isoformat(),
            updated=time.monotonic(),
        )


class NoGps:
    """Used when the GPS is disabled."""

    connected = False
    error = "disabled"

    def start(self) -> None: ...
    def stop(self) -> None: ...

    def latest(self) -> GpsFix:
        return GpsFix()
