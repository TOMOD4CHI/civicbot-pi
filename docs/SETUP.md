# Pothole Pi: setup and run guide

This guide covers everything needed to install and run the system from now on.

| Machine | What runs there | Port | Started by |
|---------|-----------------|------|------------|
| **Linux PC** | Server: database, map, dashboard, API | 8000 | `potholepi-server` service |
| **Raspberry Pi 4** | Car service: motors, camera, GPS, reports | 8080 | `potholepi-car` service |
| **Phone** | Mobile app (Expo Go) | – | `npx expo start` on a dev PC |

**All three must be on the same Wi-Fi network.** The phone talks directly to the Pi, and the Pi talks directly to the Linux PC.

---

## 0. Before you start

### Find the IP addresses
| Machine | Command |
|---------|---------|
| Linux PC | `hostname -I` (first address, e.g. `192.168.1.100`) |
| Pi | `hostname -I` (e.g. `192.168.1.50`) |

The steps below call these `PC_IP` and `PI_IP`.

> **Tip:** reserve both addresses in your router (a "DHCP reservation") so they never change. Otherwise you'll have to update `car/.env` and the app settings each time they do.

### Get the code
The code is on GitHub: `https://github.com/TOMOD4CHI/civicbot-pi`, branch `main`. If the new architecture is still on `feature/clean-architecture`, merge it into `main` or `git checkout` that branch first.

Clone it on **both** the Linux PC and the Pi:
```bash
cd ~
git clone https://github.com/TOMOD4CHI/civicbot-pi.git
cd civicbot-pi
```

### Scripts overview
| Script | Where | What it does |
|--------|-------|--------------|
| `server/scripts/setup_server.sh [--service] [--email X]` | Linux PC | Creates the venv, asks for the contact email, opens port 8000, installs the systemd service |
| `server/scripts/run_server.sh [--no-geocode]` | Linux PC | Runs the server in the foreground |
| `server/scripts/seed_demo.py [--reset]` | Linux PC | Adds demo potholes around Bizerte |
| `server/scripts/backup_db.sh [DIR]` | Linux PC | Backs up the database and photos to a `.tar.gz` |
| `car/scripts/setup_pi.sh PC_IP [--service]` | Pi | Installs apt packages and the venv, enables the UART, writes `car/.env`, installs the systemd service |
| `car/scripts/run_car.sh [--test-motors \| --simulate]` | Pi | Runs the car service or the motor test in the foreground |
| `scripts/check_network.sh --car PI_IP --server PC_IP` | anywhere | Checks what can reach what |
| `scripts/update.sh car\|server` | Pi / Linux PC | `git pull`, reinstalls the requirements, restarts the service |
| `scripts/dev_local.sh [--seed \| --test]` | any Linux PC | Runs the server and a simulated car together, with no hardware |

---

## 1. Linux server (do this first)

### 1.1 Requirements
- Ubuntu, Debian, Mint or similar, with **Python ≥ 3.10**. Check with `python3 --version`.
- Internet access, for the map tiles and the address lookup.

### 1.2 Install (once)
```bash
cd ~/civicbot-pi
bash server/scripts/setup_server.sh --service
```
The script:
- creates `server/.venv` and installs FastAPI and the other dependencies
- creates `server/.env` and **asks for a contact email**
- opens TCP 8000 if `ufw` is active
- installs and starts the **`potholepi-server`** systemd service, which also starts at every boot

The email is **required by OpenStreetMap's Nominatim policy**. It is only sent in the User-Agent of address lookups.

Without `--service`, nothing starts automatically; use `run_server.sh` instead.

### 1.3 Check it
- On the PC, open **http://localhost:8000** for the map and **http://localhost:8000/dashboard** for the dashboard.
- From another device, open `http://PC_IP:8000`. If that fails, see the [Troubleshooting](#5-troubleshooting) section.
- API docs: `http://PC_IP:8000/docs`.

Optional demo data, to see the map and dashboard filled in:
```bash
cd ~/civicbot-pi/server && .venv/bin/python scripts/seed_demo.py
# remove it later:  .venv/bin/python scripts/seed_demo.py --reset --count 0
```

### 1.4 Day-to-day commands
| Task | Command |
|------|---------|
| Status | `systemctl status potholepi-server` |
| Live logs | `journalctl -u potholepi-server -f` |
| Restart (after editing `server/.env`) | `sudo systemctl restart potholepi-server` |
| Stop / start | `sudo systemctl stop potholepi-server` / `start` |
| Run in the foreground instead | `sudo systemctl stop potholepi-server && bash server/scripts/run_server.sh` |
| Back up the data | `bash server/scripts/backup_db.sh` |
| Update the code | `bash scripts/update.sh server` |

### 1.5 Server settings (`server/.env`)
| Variable | Default | Meaning |
|----------|---------|---------|
| `POTHOLEPI_CONTACT_EMAIL` | – | Contact email for Nominatim (required for address lookup) |
| `POTHOLEPI_PORT` | 8000 | HTTP port |
| `POTHOLEPI_HOTSPOT_RADIUS_M` | 30 | Potholes within this distance are grouped into one zone |
| `POTHOLEPI_WARNING_MIN` | 3 | Number of potholes for a zone to count as a **warning** |
| `POTHOLEPI_CRITICAL_MIN` | 5 | Number of potholes for a zone to count as **critical** |
| `POTHOLEPI_LANGUAGE` | fr | Language of the street addresses |
| `POTHOLEPI_GEOCODE_ENABLED` | true | Set to `false` to work offline |

The data lives in `server/data/`: `potholepi.db` and `images/`. It is git-ignored, so back it up with `backup_db.sh`.

---

## 2. Raspberry Pi car

### 2.1 Requirements
- Raspberry Pi OS **Bookworm** (64-bit recommended), with SSH enabled.
- Wiring as in the [README](../README.md#wiring-bcm-numbering). Keep the L298N jumpers on: 5V-EN, ENA and ENB.
- **Power:** the Pi runs on its own USB-C supply, and the motors run on the 8×AA pack. **Only GND is shared.**

### 2.2 Install (once)
```bash
ssh <user>@PI_IP
cd ~/civicbot-pi
bash car/scripts/setup_pi.sh PC_IP --service
sudo reboot
```
The script:
- installs `gpiozero`, `lgpio`, `picamera2` and `pyserial`
- adds you to the `gpio`, `dialout` and `video` groups
- turns the serial console off and the UART on, for the GPS
- creates `car/.venv` and `car/.env`, with `POTHOLEPI_SERVER_URL=http://PC_IP:8000`
- installs the **`potholepi-car`** service, which starts at boot

**The reboot is needed the first time** for the UART and the new groups.

### 2.3 First test: motors (wheels in the air)
```bash
cd ~/civicbot-pi
bash car/scripts/run_car.sh --test-motors
```
`run_car.sh` stops the service first, because the service holds the GPIO pins. Watch each step:

| What you see | Fix in `car/.env` |
|--------------|-------------------|
| A wheel turns the wrong way | `POTHOLEPI_LEFT_INVERTED=true` (or `RIGHT`) |
| The car drifts to one side on the floor | Lower the faster wheel's trim: `POTHOLEPI_LEFT_TRIM=0.93` |
| The motors hum but don't turn at low speed | Raise `POTHOLEPI_MIN_DUTY` (e.g. `0.3`) |
| Too slow, or the motors get hot | Adjust `POTHOLEPI_MAX_DUTY` (default 0.6; don't exceed about 0.7 at 12 V) |

Then start the service again:
```bash
sudo systemctl start potholepi-car
```

### 2.4 Check it
```bash
curl http://localhost:8080/api/status        # on the Pi
```
In the output, check:
- `camera.source` is `picamera2`
- `gps.connected` is `true`
- `server.reachable` is `true`

In a browser, `http://PI_IP:8080/viewer` shows the live camera.

From the Linux PC:
```bash
bash scripts/check_network.sh --car PI_IP --server PC_IP
```

### 2.5 Day-to-day commands
| Task | Command |
|------|---------|
| Status / logs | `systemctl status potholepi-car` / `journalctl -u potholepi-car -f` |
| Restart (after editing `car/.env`) | `sudo systemctl restart potholepi-car` |
| Run in the foreground | `bash car/scripts/run_car.sh` |
| Update the code | `bash scripts/update.sh car` |
| Power check (expect `throttled=0x0`) | `vcgencmd get_throttled` |
| Detect the camera | `rpicam-hello --list-cameras` |
| Raw GPS output (NMEA) | `sudo systemctl stop potholepi-car && car/.venv/bin/python -m serial.tools.miniterm /dev/serial0 9600` |

### 2.6 Car settings (`car/.env`)
Every field in `car/potholepi_car/config.py` can be set as `POTHOLEPI_<NAME>=value`. The ones you will use:

| Variable | Default | Meaning |
|----------|---------|---------|
| `POTHOLEPI_SERVER_URL` | set by the setup script | The Linux server |
| `POTHOLEPI_PORT` | 8080 | Car service port |
| `POTHOLEPI_LEFT_INVERTED`, `POTHOLEPI_RIGHT_INVERTED`, `POTHOLEPI_LEFT_TRIM`, `POTHOLEPI_RIGHT_TRIM` | false, false, 1.0, 1.0 | Wheel direction and drift calibration |
| `POTHOLEPI_MIN_DUTY`, `POTHOLEPI_MAX_DUTY` | 0.25, 0.6 | Motor PWM range |
| `POTHOLEPI_CAMERA_WIDTH`, `POTHOLEPI_CAMERA_HEIGHT`, `POTHOLEPI_CAMERA_FPS` | 640, 480, 15 | Video resolution and frame rate (lower them if the video lags) |
| `POTHOLEPI_GPS_ENABLED`, `POTHOLEPI_CAMERA_ENABLED` | true | Turn a module off |
| `POTHOLEPI_DETECTION_ENABLED` | false | Turn this on once the YOLO model is integrated |

> `car/.env` is git-ignored, so pulling updates never overwrites your calibration.

---

## 3. Mobile app

### 3.1 Requirements
- A dev PC (Windows, Linux or macOS) with **Node.js 20 or later**. Check with `node --version`.
- On the phone, the **Expo Go** app from the Play Store or App Store.
- The dev PC and the phone on the same Wi-Fi.

### 3.2 Start it
```bash
cd civicbot-pi/mobile
npm install          # first time, and after pulling changes to package.json
npx expo start
```
Scan the QR code with Expo Go (Android), or with the Camera app (iOS).

If the phone can't load the app, the network probably blocks it. Use `npx expo start --tunnel`.

### 3.3 Connect to the car
1. In the app, tap **⚙** (top right).
2. Enter the **car IP** (`PI_IP`) and **port** `8080`.
3. Tap **Test connection**. It should show the camera source, the GPS state and "server OK".
4. Tap **Save**.

### 3.4 Use it
- **Joystick:** hold and drag to drive; let go to stop. If no command arrives for 0.5 s (for example, the Wi-Fi drops), the car stops by itself.
- **STOP:** stops immediately.
- **Slow / Normal / Fast:** speed limit for the joystick.
- **Send location:** saves a pothole at the car's position, with a photo.
  - It uses the car's GPS when it has a fix, otherwise the phone's GPS.
  - Allow location access the first time.
  - The result appears on the map within 10 s.

---

## 4. Everyday startup checklist

1. **Linux PC on.** The server starts by itself. Check `http://PC_IP:8000`.
2. **Car power:**
   - Pi on USB-C, then the motor battery switch on.
   - Wait about 30 s for the Pi to boot. The service starts by itself.
3. **Phone:**
   - Run `npx expo start` on the dev PC, then open the app.
   - Check that the status chips show **Car connected**, **GPS fix** and **Server OK**.
4. **Drive outdoors:**
   - The GPS needs open sky. The first fix can take 1–5 minutes; watch the "sats" counter.
5. **Afterwards:**
   - Motor battery off first, then shut down the Pi with `sudo poweroff`.

**Without any hardware** (to demo or develop on a Linux PC):
```bash
bash scripts/dev_local.sh --seed
```
This runs the server and a simulated car together. Point the app at this PC's IP, port 8080.

---

## 5. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| The app says **Car offline** | Wrong IP in the app settings, the service is stopped (`systemctl status potholepi-car`), or the phone is on another network. |
| **Server unreachable** in the app or `check_network.sh` | `POTHOLEPI_SERVER_URL` is wrong in `car/.env`, or a firewall is blocking it. On the PC, run `sudo ufw allow 8000/tcp`. |
| `errno 113` / "No route to host" between devices | The router has **Wi-Fi client isolation** (often on guest or campus networks). Turn it off, or use a phone hotspot or a home router. |
| Black video, but driving works | Check `camera.error` in `/api/status` and run `rpicam-hello --list-cameras`. The ribbon may be reversed or loose. |
| Blurry photos | Remove the lens film. On v1/v2 cameras, turn the focus ring. Stop the car before capturing. |
| **No GPS fix** | Normal indoors. Outdoors, wait a few minutes. If `gps.connected` is false, check TX→pin 10 and that the UART is enabled (re-run the setup script and reboot). |
| The motors don't move | The motor battery is off, or the jumpers or wiring are wrong. Run `run_car.sh --test-motors` and check `LEFT_EN/RIGHT_EN = None` with the jumpers on. |
| The car stops by itself while driving | The watchdog stops it after 0.5 s without commands, which usually means weak Wi-Fi. Move closer to the router. |
| The Pi reboots or flickers when the motors start | Power problem. Check `vcgencmd get_throttled`. Use a proper 5 V / 3 A supply, and **never** power the Pi from the L298N. |
| Addresses stay "looking up…" | `POTHOLEPI_CONTACT_EMAIL` is empty, or the PC has no internet. See `journalctl -u potholepi-server`. |
| `run_server.sh` says the port is in use | The service is already running. Use `systemctl` or stop the service first. |
| The app shows a red error screen after `git pull` | Run `npm install` in `mobile/` again, then `npx expo start --clear`. |
