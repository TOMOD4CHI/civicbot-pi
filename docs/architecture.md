# Architecture

The system has three deployable modules. Each one has the same internal layering: **routes → services → hardware/repositories**. Routes only translate HTTP to calls, services hold the logic, and the bottom layer touches the hardware or the database.

## Car: `car/potholepi_car`

| Layer | Module | Responsibility |
|-------|--------|----------------|
| config | `config.py` | One `Settings` dataclass. Every field can be overridden with `POTHOLEPI_<NAME>` (env or `car/.env`). |
| hardware | `hardware/motors.py` | `Car`: L298N differential drive. Speed in −1..1 is mapped to a PWM duty in `MIN_DUTY..MAX_DUTY`, with trim and inversion. |
| | `hardware/gps.py` | `NmeaParser` (RMC/GGA with checksum check), `GpsReader` (serial thread with auto-retry), `FakeGps`, `NoGps`. |
| | `hardware/camera.py` | `PiCamera` (Picamera2 hardware MJPEG), `UsbCamera` (OpenCV), `TestPattern`. All share a `FrameBuffer` with the latest JPEG. |
| services | `services/drive.py` | `DriveService`: the only code that drives the motors. It has a 0.5 s watchdog and stops on disconnect. |
| | `services/reporter.py` | `choose_location()` picks the car GPS if its fix is ≤ 5 s old, otherwise the phone GPS. `Reporter` adds a snapshot and POSTs to the server. |
| | `services/telemetry.py` | Posts the live position to the server every 2 s, and records whether the server is reachable. |
| | `services/detection.py` | `PotholeDetector` protocol, `NullDetector`, the **empty** `YoloPotholeDetector`, and `DetectionWorker` (frames → detector → reporter, with a cooldown). |
| api | `api/control.py` | `WS /ws/control` for drive commands. |
| | `api/camera.py` | `GET /stream.mjpg`, `/snapshot.jpg`, `/viewer`. |
| | `api/report.py` | `POST /api/report`. |
| | `api/status.py` | `GET /api/status`, `/health`. |
| app | `main.py` | `build_runtime()` wires everything together (dependency injection by hand). `create_app()` builds FastAPI with a lifespan. |

### Report flow (manual today, automatic later)
```
App "Send location" ──► POST car/api/report {phone_lat, phone_lon, phone_accuracy}
                          │
DetectionWorker ─────────►├─ choose_location(car fix, phone fix)
  (trigger = "model")     ├─ + camera JPEG (base64)
                          └─► POST server/api/detections
                                 ├─ save row + image
                                 └─ queue reverse geocoding
```

### Plugging in the YOLO model
1. Put the weights in `car/models/`.
2. Implement `YoloPotholeDetector.load()` and `.detect(frame) -> list[Detection]` in `services/detection.py`. `frame` is an RGB numpy array from `camera.get_frame()`.
3. Set `POTHOLEPI_DETECTION_ENABLED=1`. Tune `DETECTION_MIN_CONFIDENCE` and `DETECTION_COOLDOWN_S` as needed.

Nothing else changes: reports from the model reach the server with `trigger="model"`, along with `confidence` and `bbox`.

## Server: `server/potholepi_server`

| Layer | Module | Responsibility |
|-------|--------|----------------|
| storage | `db.py` | SQLite schema (`detections`, `geocode_cache`). One connection per operation, WAL mode. |
| | `repositories/detections.py` | All SQL for detections. |
| services | `services/geocoding.py` | Nominatim with Photon as fallback. One worker thread, ≥ 1.1 s between requests, contact-email User-Agent, and a persistent cache keyed on 4-decimal coordinates. |
| | `services/hotspots.py` | Greedy haversine clustering. ≥ `WARNING_MIN` → warning, ≥ `CRITICAL_MIN` → critical. Fixed potholes are excluded. |
| | `services/stats.py` | Aggregates for the dashboard. |
| api | `api/detections.py`, `api/analytics.py`, `api/telemetry.py` | REST endpoints (see `api.md`). |
| web | `web/` | `index.html` (Leaflet map) and `dashboard.html` (Chart.js). They only call the JSON API. |

## Mobile: `mobile/src`

| Folder | Content |
|--------|---------|
| `app/` | Expo Router screens: `index.tsx` (drive), `settings.tsx`, `_layout.tsx`. |
| `api/carClient.ts` | Typed HTTP calls, URLs, arcade mixing. |
| `hooks/` | `useCarControl` (WebSocket, 10 Hz send loop, reconnect), `useCarStatus` (2 s polling), `usePhoneLocation`. |
| `components/` | `Joystick`, `CameraFeed` (MJPEG in a WebView), `CarStatusBar`, `SpeedSelector`, `StopButton`, `SendLocationButton`, `Toast`. |
| `settings/` | `SettingsProvider`: car IP and port plus options, persisted in AsyncStorage. |

## Safety
- The car stops if no command arrives for 0.5 s (watchdog) and when the controlling WebSocket closes.
- The app sends commands only while the stick is held, then sends a single `stop`. The STOP button fires on press-in.
- `MAX_DUTY` caps the motor voltage. Never connect a GPIO to ENA/ENB while their jumpers are on.
