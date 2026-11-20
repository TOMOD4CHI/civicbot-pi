"""
Pothole Pi - server (runs on the Linux PC).

    uvicorn potholepi_server.main:create_app --factory --host 0.0.0.0 --port 8000
    python -m potholepi_server

Web:  /            interactive map
      /dashboard   statistics
API:  /api/detections, /api/hotspots, /api/stats, /api/telemetry  (docs: /docs)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import analytics, detections, telemetry
from .config import Settings, settings as default_settings
from .db import Database
from .repositories.detections import DetectionRepository
from .services.geocoding import GeocodingService

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
log = logging.getLogger("potholepi_server")


@dataclass
class Context:
    settings: Settings
    db: Database
    repo: DetectionRepository
    geocoder: GeocodingService


def create_app(s: Settings | None = None, geocoder: GeocodingService | None = None) -> FastAPI:
    s = s or default_settings
    db = Database(s.db_path)
    db.init()
    s.images_dir.mkdir(parents=True, exist_ok=True)
    repo = DetectionRepository(db)
    ctx = Context(s, db, repo, geocoder or GeocodingService(s, db, repo))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ctx.geocoder.start()
        log.info("server ready: http://localhost:%d  (dashboard: /dashboard)", s.PORT)
        yield
        ctx.geocoder.stop()

    app = FastAPI(title="Pothole Pi - server", version="1.0.0", lifespan=lifespan)
    app.state.ctx = ctx
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    for module in (detections, analytics, telemetry):
        app.include_router(module.router)

    @app.get("/dashboard", include_in_schema=False)
    def dashboard():
        return FileResponse(WEB_DIR / "dashboard.html")

    app.mount("/images", StaticFiles(directory=s.images_dir), name="images")
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app



def run() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run(create_app(), host=default_settings.HOST, port=default_settings.PORT)
