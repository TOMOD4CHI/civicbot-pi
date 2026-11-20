# Pothole Pi

A robot car that finds potholes and puts them on a map.

- **Car (Raspberry Pi 4).** The car drives two DC motors through an L298N board, streams its camera, and reads a GY-NEO6MV2 GPS. It reports potholes to the server.
- **Server (Linux PC).** The server stores every report in SQLite and looks up the street address with OpenStreetMap. It shows the reports on an **interactive map** with **critical zones**, plus a **statistics dashboard**.
- **Mobile app (Expo / React Native).** The app drives the car with a joystick and shows the live video. Its **Send location** button reports a pothole by hand. The YOLO detector will use the same path later.

```
 ┌──────────── phone (Expo app) ────────────┐
 │ joystick ─ WS /ws/control ──────┐        │
 │ video   ◀─ GET /viewer (MJPEG) ─┤        │
 │ Send location ─ POST /api/report┤        │
 └─────────────────────────────────┼────────┘
                                   ▼
 ┌──────────── car: Raspberry Pi (:8080) ───────────┐
 │ motors (L298N)  camera (Picamera2)  GPS (UART)   │
 │ detector (YOLO, placeholder) ──┐                 │
 │ reporter: car GPS → phone GPS fallback + photo   │
 └────────────────────────────────┼─────────────────┘
          POST /api/detections    │   POST /api/telemetry (every 2 s)
                                  ▼
 ┌──────────── server: Linux PC (:8000) ────────────┐
 │ SQLite · geocoding (Nominatim → Photon, ≤1 req/s)│
 │ /  map (Leaflet)   /dashboard (Chart.js)  /docs  │
 └──────────────────────────────────────────────────┘
```

## Repository layout

| Path | What it is |
|------|------------|
| `car/potholepi_car/` | Car service (FastAPI). It is split into `hardware/` (motors, GPS, camera), `services/` (drive and watchdog, reporter, telemetry, detection) and `api/` (HTTP and WebSocket routes). |
| `car/models/` | Folder for the YOLO weights. It is git-ignored and empty for now. |
| `server/potholepi_server/` | Server (FastAPI). It is split into `repositories/` (SQL), `services/` (geocoding, hotspots, stats) and `api/`. |
| `server/web/` | The map and dashboard pages: plain HTML, CSS and JS, with no build step. |
| `mobile/` | Expo app. Screens are in `src/app/`; components, hooks and the API client are in `src/`. |
| `docs/` | `architecture.md` and `api.md`. |

## Quick start

> **Full step-by-step guide (Linux server, Pi, phone, troubleshooting): [docs/SETUP.md](docs/SETUP.md).**

### 1. Server (Linux PC)
```bash
bash server/scripts/setup_server.sh          # venv + asks for the Nominatim contact e-mail
cd server && .venv/bin/python -m potholepi_server
# http://<pc-ip>:8000  (map)    http://<pc-ip>:8000/dashboard
.venv/bin/python scripts/seed_demo.py        # optional demo data around Bizerte
```

### 2. Car (Raspberry Pi)
```bash
git clone https://github.com/TOMOD4CHI/civicbot-pi && cd civicbot-pi
bash car/scripts/setup_pi.sh <PC_IP> --service   # then: sudo reboot
cd car && .venv/bin/python scripts/test_motors.py   # wheels in the air (stop the service first)
```
The service listens on port **8080**. Settings go in `car/.env`; see `car/.env.example` and `car/potholepi_car/config.py`.

### 3. Mobile app
```bash
cd mobile && npm install && npx expo start
```
1. Open the app in **Expo Go** on a phone on the same Wi-Fi.
2. Tap ⚙ and enter the Pi's IP (port 8080).
3. Tap **Test connection**, then **Save**.

### Without the hardware
`POTHOLEPI_SIMULATE=1` runs the car service on any computer with:
- a mock GPIO
- a fake GPS circling Bizerte
- a test-pattern camera

```bash
cd car && POTHOLEPI_SIMULATE=1 POTHOLEPI_SERVER_URL=http://127.0.0.1:8000 python -m potholepi_car
```

## Wiring (BCM numbering)

| L298N | Pi 4 GPIO | Physical pin |
|-------|-----------|--------------|
| IN1 | GPIO17 | 11 |
| IN2 | GPIO27 | 13 |
| IN3 | GPIO22 | 15 |
| IN4 | GPIO23 | 16 |
| ENA / ENB | jumpers **on** → `LEFT_EN = RIGHT_EN = None` (jumpers off: GPIO18 / GPIO13, pins 12 / 33) | |
| GND | GND | 6 (shared ground is **required**) |

| GPS GY-NEO6MV2 | Pi pin |
|----------------|--------|
| VCC | 4 (5 V) |
| GND | 9 |
| TX | 10 (RXD) |
| RX | 8 (TXD) |

**Power**
- The motors run from 8×AA (about 12 V) on the L298N's `12V` input. The 5V-EN jumper stays **on**.
- **Never** connect the Pi's 5 V to the L298N; only GND is shared.
- **Never** wire a GPIO to ENA/ENB while its jumper is on.
- `MAX_DUTY = 0.6` keeps the 3–6 V TT motors at about 5 V.

## Calibration (`car/.env`)
- A wheel turns the wrong way: set `POTHOLEPI_LEFT_INVERTED=true` (or `RIGHT`).
- The car drifts to one side: lower the faster wheel's trim, e.g. `POTHOLEPI_LEFT_TRIM=0.95`.
- The motors hum at low speed without turning: raise `POTHOLEPI_MIN_DUTY`. For top speed versus motor heat, adjust `POTHOLEPI_MAX_DUTY`.

## Tests
```bash
pip install -r car/requirements-dev.txt -r server/requirements-dev.txt
(cd car && pytest) && (cd server && pytest)
cd mobile && npx tsc --noEmit
```
