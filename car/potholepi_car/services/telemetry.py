"""Posts the live car position/status to the server (live car marker on the map)."""
from __future__ import annotations

import logging
import threading

import httpx

from ..config import Settings

log = logging.getLogger(__name__)


class TelemetryService:
    def __init__(self, settings: Settings, gps, drive):
        self.s = settings
        self.gps = gps
        self.drive = drive
        self.server_ok: bool | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="telemetry", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        url = f"{self.s.SERVER_URL}/api/telemetry"
        with httpx.Client(timeout=self.s.HTTP_TIMEOUT_S) as client:
            while not self._stop.wait(self.s.TELEMETRY_INTERVAL_S):
                data = self.gps.latest().to_dict()
                data["device_id"] = self.s.DEVICE_ID
                data["moving"] = self.drive.status()["moving"]
                try:
                    client.post(url, json=data).raise_for_status()
                    if self.server_ok is not True:
                        log.info("server reachable: %s", self.s.SERVER_URL)
                    self.server_ok = True
                except Exception as e:
                    if self.server_ok is not False:
                        log.warning("server unreachable (%s), will keep retrying", e)
                    self.server_ok = False
