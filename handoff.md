# Handoff: Pothole Pi (Raspberry Pi 4 car + Linux server + mobile app)

## 1. Goal & Current Status
**Goal:** a robot car that detects potholes and puts them on a map.
- A fine-tuned YOLO model will run on the Pi; for now it is an empty placeholder.
- Each detection's GPS position goes to the Linux PC server, which shows it on a map and a dashboard.
- A mobile app drives the car and shows the live camera.

**Hardware**
- Raspberry Pi 4 driving an L298N board: 2 driven DC motors and 1 caster wheel.
- GY-NEO6MV2 GPS on the UART.
- CSI camera, model still unknown.

**Status (branch `feature/clean-architecture`)**
- **Code rewritten as three modules:** `car/`, `server/`, `mobile/`. The old `pi/`, `linux/` and `desktop/` folders were removed; their logic now lives in the new modules.
- **Verified on the Windows dev PC, in simulation mode:**
  - car and server tests pass (10 + 12)
  - WebSocket drive, the watchdog stop, the MJPEG stream and snapshots work
  - report → detection with photo → map
  - map and dashboard checked in Chrome
- **Not yet verified on real hardware:** the Pi camera (Picamera2), the GPS reader in the new service, and the motors in the new service.
- **Motors:** worked from the Pi with the old code. Still to do: `INVERTED`/`TRIM` calibration.
- **GPS:** worked end to end before the rewrite (through an SSH tunnel), but has no fix indoors and needs a sky view.
- **Camera:** captured images, but they were blurry. Diagnosis is pending (lens film, focus, shutter time).

## 2. Key Decisions & Constraints
**Power and wiring**
- Motors: 8×AA (about 12 V) into the L298N's 12V terminal, with the 5V-EN jumper **on**.
- **Never** connect the Pi's 5 V to the L298N; only GND is shared.
- ENA/ENB jumpers are **on**, so `LEFT_EN = RIGHT_EN = None` and speed is set by PWM on the IN pins. **Never** wire a GPIO to ENA/ENB while its jumper is on.
- `MIN_DUTY=0.25` and `MAX_DUTY=0.6`: the TT motors are 3–6 V, and the L298N drops about 2 V.
- Pins use BCM numbering: IN1=17, IN2=27, IN3=22, IN4=23. GPIO14/15 are the GPS UART.

**Software choices (made with the user)**
- **Car and server:** FastAPI on both.
  - Car service on port **8080**: WebSocket control, MJPEG video, report and status endpoints.
  - Server on port **8000**: SQLite, Leaflet map, Chart.js dashboard; plain HTML/JS with no build step.
- **Mobile:** Expo SDK 58 + Expo Router + TypeScript.
  - Video is shown through a WebView of the car's `/viewer` page, because React Native's Image can't play MJPEG on Android.
  - Settings (car IP and port) are stored in AsyncStorage.
- **Report GPS:** the car's GPS if its fix is ≤ 5 s old, otherwise the phone's GPS. The source is stored with each detection.
- **Network:** all devices on the same LAN.
- **Config:** a `Settings` dataclass in each module, overridable with `POTHOLEPI_*` env vars or a `.env` file (`car/.env`, `server/.env`). The old `deploy.sh` problem of overwriting `config.py` is gone: the local calibration lives in the untracked `.env`.
- **Safety:** watchdog stop after 0.5 s without commands, a stop on WebSocket disconnect, and the app sends a single `stop` when the stick is released.
- **Geocoding (OSM policy):**
  - Nominatim first, Photon as fallback.
  - One worker thread, ≥ 1.1 s between requests.
  - User-Agent with a contact email (`POTHOLEPI_CONTACT_EMAIL`).
  - Persistent cache keyed on coordinates rounded to 4 decimals.
  - Lookups happen **once per detection**, never per GPS update. **Don't make lookups more aggressive.**
- **Critical zones:** greedy clustering within 30 m. ≥ 3 detections = warning, ≥ 5 = critical. Fixed potholes are excluded.
- **Project name:** "Pothole Pi", changed from CivicBot at the user's request. The GitHub repo name `civicbot-pi` is unchanged.

## 3. Relevant Files
- `car/potholepi_car/`
  - `config.py`
  - `hardware/`: `motors.py`, `gps.py`, `camera.py`
  - `services/`: `drive.py`, `reporter.py`, `telemetry.py`, `detection.py` (the YOLO hook)
  - `api/`: `control.py`, `camera.py`, `report.py`, `status.py`
  - `main.py`
- `car/scripts/`: `setup_pi.sh <PC_IP> [--service]` (systemd unit `potholepi-car`) and `test_motors.py`.
- `server/potholepi_server/`
  - `config.py`, `db.py`, `schemas.py`
  - `repositories/detections.py`
  - `services/`: `geocoding.py`, `hotspots.py`, `stats.py`
  - `api/`, `main.py` (app factory)
- `server/web/`: `index.html` + `js/map.js` (map), `dashboard.html` + `js/dashboard.js`.
- `server/scripts/`: `setup_server.sh [--service]` (systemd unit `potholepi-server`) and `seed_demo.py`.
- `mobile/src/`
  - `app/`: `index.tsx` (drive screen), `settings.tsx`, `_layout.tsx`
  - `components/`, `hooks/`, `api/carClient.ts`
- `docs/architecture.md`, `docs/api.md`, `README.md`.

## 4. Immediate Next Steps
1. **Review and merge** `feature/clean-architecture` into `main`. The teammate also pushes to `main`, so pull first.
2. **On the Pi:**
   - Run `git pull`, then `bash car/scripts/setup_pi.sh <PC_IP> --service`, then reboot.
   - Run `test_motors.py`.
   - Calibrate in `car/.env`.
   - Check that `/api/status` shows `camera.source = picamera2`.
3. **On the Linux PC:** `bash server/scripts/setup_server.sh --service`. Set a real contact email.
4. **Phone:**
   - Run `cd mobile && npx expo start` and open the app in Expo Go.
   - Enter the Pi's IP and port 8080.
   - Drive, then press Send location outdoors.
5. **Camera blur:** check the model with `rpicam-hello --list-cameras`, remove the lens film, and adjust focus.
6. **YOLO:** implement `YoloPotholeDetector` in `car/potholepi_car/services/detection.py` and set `POTHOLEPI_DETECTION_ENABLED=1`.

## 5. Open Questions / Edge Cases
- **Picamera2 path:** untested on the real Pi. `RGB888` frames are BGR in memory and are flipped for the model.
- **Release (non-Expo Go) builds:** these need `usesCleartextTraffic` for `http://` and `ws://` on the LAN, which is already set through `expo-build-properties` in `app.json`.
- **Pi power:** the earlier power-LED flicker was never explained. Check `vcgencmd get_throttled`, especially with the motors and camera running.
- **Pi 4 UART:** `/dev/serial0` is the mini UART while Bluetooth is on. `dtoverlay=disable-bt` is an option if the data gets corrupted.
- **Direct link:** a direct Pi → PC connection failed earlier (errno 113, possibly Wi-Fi client isolation). The phone also needs to reach the Pi directly.
