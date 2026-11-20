"""
Pothole Pi - car service (runs on the Raspberry Pi).

    python -m potholepi_car                     # real hardware
    POTHOLEPI_SIMULATE=1 python -m potholepi_car  # no hardware (any PC)

Endpoints: WS /ws/control, GET /stream.mjpg, GET /snapshot.jpg, GET /viewer,
POST /api/report, GET /api/status, GET /health.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import camera as camera_api
from .api import control, report, status
from .config import Settings, settings as default_settings
from .hardware.camera import BaseCamera, create_camera
from .hardware.gps import FakeGps, GpsReader, NoGps
from .hardware.motors import Car
from .services.detection import DetectionWorker, create_detector
from .services.drive import DriveService
from .services.reporter import Reporter
from .services.telemetry import TelemetryService

log = logging.getLogger("potholepi_car")


@dataclass
class Runtime:
    settings: Settings
    drive: DriveService
    gps: object
    camera: BaseCamera
    reporter: Reporter
    telemetry: TelemetryService
    detector: object
    detection: DetectionWorker

    def stop(self) -> None:
        for svc in (self.detection, self.telemetry, self.gps, self.camera):
            try:
                svc.stop()
            except Exception:
                log.exception("error while stopping %s", svc)
        self.drive.close()


def build_runtime(s: Settings) -> Runtime:
    if s.SIMULATE:
        from gpiozero import Device
        from gpiozero.pins.mock import MockFactory, MockPWMPin

        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        log.warning("SIMULATION MODE: mock GPIO, fake GPS, test-pattern camera")

    drive = DriveService(Car(s), s.WATCHDOG_TIMEOUT)
    if s.SIMULATE:
        gps = FakeGps()
    elif s.GPS_ENABLED:
        gps = GpsReader(s.GPS_SERIAL_PORT, s.GPS_BAUDRATE)
    else:
        gps = NoGps()
    camera = create_camera(s)
    reporter = Reporter(s, gps, camera)
    telemetry = TelemetryService(s, gps, drive)
    detector = create_detector(s)
    detection = DetectionWorker(s, detector, camera, reporter)
    return Runtime(s, drive, gps, camera, reporter, telemetry, detector, detection)


def create_app(s: Settings | None = None, start_background: bool = True) -> FastAPI:
    s = s or default_settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        rt = build_runtime(s)
        app.state.rt = rt
        rt.drive.start()
        rt.gps.start()
        if start_background:
            rt.telemetry.start()
            rt.detection.start()
        log.info("car service ready on port %d (camera: %s, detector: %s)",
                 s.PORT, rt.camera.name, rt.detector.name)
        try:
            yield
        finally:
            rt.stop()

    app = FastAPI(title="Pothole Pi - car", version="1.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    for module in (control, camera_api, report, status):
        app.include_router(module.router)
    return app


def run() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run(create_app(), host=default_settings.HOST, port=default_settings.PORT, log_level="info")
