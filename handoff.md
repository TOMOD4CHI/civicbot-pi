# Handoff: Robot car (Raspberry Pi 4 + L298N + GPS + camera)

## 1. Goal & Current Status
**Goal:** a robot car with 2 driven DC motors (differential drive) and 1 unpowered caster wheel.
- Raspberry Pi 4 drives an **L298N** motor board.
- The car is controlled from a **Linux PC** over the network (Pi reached by SSH).
- Extra modules: **GY-NEO6MV2 GPS** (position + street address on a live map), and a camera for still photos.

**Status:**
- **Motors: working, driven from the Pi.** Still to check: the wheel direction (`*_INVERTED`), drift between the two wheels (`*_TRIM`), and remote driving with `server.py` + the desktop app.
- **GPS: the whole chain works.** Pi sender → Linux server, currently **through an SSH reverse tunnel**. The module streams NMEA correctly at 9600 baud, but has **no fix indoors**: at most 1 satellite in view (PRN 14, signal 21 dB). Needs a sky view.
- **Camera: just started.** It captures, but **images are blurry**. Model unknown (CSI ribbon assumed). Diagnosis in progress (protective film, fixed-focus distance, motion blur).
- **Git:** motor code pushed to GitHub **from the Pi**. Pushing the GPS/Linux/desktop files from the PC is pending; it must start with a pull/rebase first.

## 2. Key Decisions & Constraints
**Power**
- Motor supply: **8×AA in series (≈12 V)** into the L298N's 12V terminal.
- **5V-EN jumper ON**: the board makes its own 5 V logic supply. With the jumper on, the **Pi's 5 V must NOT be connected** to the L298N's 5V terminal; only **GND is shared**.
- Pi powered separately by **USB-C**. It flickered earlier (low voltage); check with `vcgencmd get_throttled`.
- The 6 V pack was dropped: too low for the board's regulator.

**ENA/ENB**
- Recommended setup: **ENA/ENB jumpers ON**, with `LEFT_EN = None` and `RIGHT_EN = None`, so speed is set by PWM on the IN pins.
- **Never** wire a GPIO to ENA/ENB while its jumper is on (5 V would hit the Pi's 3.3 V pin).
- Alternative: jumpers off, ENA→GPIO18, ENB→GPIO13.

**Motor speed cap**
- TT motors are rated 3–6 V, so at 12 V the PWM is capped with `MAX_DUTY = 0.6`.
- Also `MIN_DUTY = 0.25`, so the motors actually start at low speeds.

**Pin numbering**
- Code uses **BCM numbers**. The GPIO extension board is labelled in BCM (`GPIO17`…).
- Avoid GPIO 0/1/2/3; GPIO14/15 are now the UART used by the GPS.

**Libraries and tools**
- Motors: `gpiozero.Motor` with `pwm=True`.
- Linux GPS server: Python **standard library only** (`http.server`, `sqlite3`, `urllib`).
- Desktop app: Tkinter.
- GPS: `pyserial`, with an NMEA parser written by hand (RMC and GGA sentences, checksum verified).
- Camera: `rpicam-still` (`libcamera-still` on older systems); `fswebcam` if it's a USB webcam.

**Address lookup (reverse geocoding)**
- **Nominatim (OSM)** first, **Photon (komoot)** as fallback.
- Nominatim's policy is mandatory: a User-Agent with a contact email, at most 1 request/s, cached results, no heavy use. Policy: https://operations.osmfoundation.org/policies/nominatim/
- The server only re-geocodes after moving **≥25 m and ≥15 s** since the last lookup, with a cache keyed on coordinates rounded to 4 decimals (~11 m). **Don't make lookups more aggressive.**
- Map page: Leaflet 1.9.4 with OSM tiles (CDN).

**Safety and networking**
- Motor server: TCP **port 5005**, one text command per line. A **watchdog stops the motors after 0.5 s** without commands, and they also stop when the client disconnects.
- GPS server: HTTP **port 8000**. The port was opened in the Linux firewall.

## 3. Relevant Files & Code
Project root: `robot-car/` (on the Pi: `~/robot-car`).

**`pi/`**
- **`config.py`**
  - Pins: `LEFT_IN1=17`, `LEFT_IN2=27`, `LEFT_EN=18`, `RIGHT_IN3=22`, `RIGHT_IN4=23`, `RIGHT_EN=13`
  - Settings: `LEFT/RIGHT_INVERTED`, `LEFT/RIGHT_TRIM`, `MIN_DUTY=0.25`, `PORT=5005`, `WATCHDOG_TIMEOUT=0.5`
  - User should have added `MAX_DUTY=0.6`, and possibly `LEFT_EN/RIGHT_EN=None` for the jumper setup. **The Pi copy (the working one, pushed to the repo) is the source of truth, not the zip.**
- **`car.py`**: class `Car` with:
  - `drive(left, right)`, values −1..1
  - `arcade(throttle, steering)`
  - `forward`, `backward`, `turn_left`, `turn_right` (pivots on the spot)
  - `stop`, `close`

  The helper `_apply()` remaps the speed into the duty range. Required patch for the cap:
  ```python
  mag = config.MIN_DUTY + (config.MAX_DUTY - config.MIN_DUTY) * mag
  ```
- **`test_motors.py`**: runs each motor alone, then both together, both pivots, then a 0→100 % speed ramp.
- **`server.py`**: TCP command server. Protocol: `DRIVE l r`, `ARCADE t s`, `STOP`, `PING`→`PONG`. Includes the watchdog thread.
- **`gps_config.py`**: `SERIAL_PORT=/dev/serial0`, `BAUDRATE=9600`, `SERVER_URL`, `DEVICE_ID="robot-car"`, `SEND_INTERVAL=2.0`.
- **`gps_sender.py`**: `GpsState.feed()` parses RMC/GGA. Sends a JSON POST to `/api/gps` every 2 s. Flags:
  - `--raw`: print the raw NMEA lines
  - `--fake`: circle around Bizerte (37.2744, 9.8739)
  - `--server URL`: override the server address

**`desktop/car_control_app.py`**
- Tkinter app: IP/port fields, press-and-hold buttons, keyboard control (arrows / ZQSD / WASD, Space = STOP), speed slider, pivot-mode checkbox.
- Sends `DRIVE l r` every 100 ms.

**`linux/`**
- **`server_config.py`**: `PORT=8000`, `CONTACT_EMAIL`, `USER_AGENT`, `GEOCODE_MIN_DISTANCE_M=25`, `GEOCODE_MIN_INTERVAL_S=15`, `LANGUAGE="fr"`.
- **`gps_server.py`**:
  - `POST /api/gps` (only fixes with coordinates are saved to SQLite `gps_track.db`)
  - `GET /api/latest`, `GET /api/track`, `GET /` (serves `map.html`)
  - `geocoder_loop()` runs in a background thread.
- **`map.html`**: Leaflet map; polls `/api/latest` every 2 s and `/api/track` every 5 s.
- **`setup_linux.sh`**: asks for the contact email, opens port 8000 if ufw is active, and with `--service` creates the systemd unit `robot-gps-server`.

**Scripts at the root**
- **`setup_pi.sh`**: apt install `python3-gpiozero`, `python3-lgpio`; adds the user to the `gpio` group; `--service` creates the `robot-car` systemd unit.
- **`setup_gps_pi.sh <LINUX_IP> [--service]`**: `raspi-config nonint do_serial_cons 1` and `do_serial_hw 0`; installs `python3-serial`; adds the user to `dialout`; writes `SERVER_URL` with sed; the optional service is `robot-gps`. **Reboot needed** afterwards.
- **`deploy.sh user@pi [--service]`**: copies `pi/` and the setup scripts to the Pi with scp. **It overwrites the Pi's `config.py`**, so don't rerun it blindly.
- **`README.md`**: wiring table and usage.

**Wiring (physical pins)**
- **L298N:** IN1→11, IN2→13, IN3→15, IN4→16, (ENA→12, ENB→33 if jumpers off), GND→6
- **GPS:** VCC→4 (5V), GND→9, TX→10 (RXD), RX→8 (TXD)

**Useful commands**
- SSH tunnel for GPS data: on the PC, `ssh -R 8000:localhost:8000 pi@PI`; then on the Pi, `python3 gps_sender.py --server http://localhost:8000/api/gps`.
- Camera:
  - `rpicam-hello --list-cameras` (detect the camera and its model)
  - `rpicam-still -n -o t.jpg --width W --height H -q 100 --denoise cdn_hq -t 3000` (best-quality still)
  - `scp pi@PI:~/t.jpg .` on the PC (fetch the photo)

## 4. Immediate Next Steps
1. **Camera.**
   - Get the model with `rpicam-hello --list-cameras` (`ov5647`=v1, `imx219`=v2, `imx708`=v3).
   - Remove the lens film; test a subject ~3 m away; test with a short exposure: `rpicam-still -n -o t.jpg --shutter 10000 --gain 6`.
   - v1/v2: adjust the focus ring by hand. v3: use `--autofocus-on-capture`.
   - Capture at full resolution with `-q 95..100 --denoise cdn_hq`, then fetch on the PC with `scp`.
2. **Finish motor calibration.**
   - With `test_motors.py`, set `LEFT/RIGHT_INVERTED` if a wheel turns the wrong way.
   - On the floor, adjust `LEFT/RIGHT_TRIM` until the car drives straight.
   - Tune `MIN_DUTY` (motors hum without turning → raise it) and `MAX_DUTY` (top speed vs motor heating).
3. **Remote driving test:** stop any running `server.py`, start it again, then use `car_control_app.py` on the PC. Check the watchdog stops the car when the app is closed.
4. **GPS outdoors.**
   - With `--raw`, wait until `$GPGSV` shows ≥4 satellites and `$GPRMC` changes `V`→`A`.
   - Then run the normal sender and confirm the address appears on the map.
   - Optionally switch from the tunnel to a direct connection (`curl http://LINUX_IP:8000/api/latest` from the Pi).
5. **Git.**
   - On the Pi: commit the working motor config (`config.py`, the `car.py` patch) if it changed since the last push.
   - On the PC: pull/rebase first, then add `linux/`, `pi/gps_*.py`, `setup_gps_pi.sh`, `desktop/`, `deploy.sh`, `README.md`. **Don't overwrite the Pi's `pi/config.py` or `pi/car.py`.** `.gitignore` already has `__pycache__/`, `*.pyc`, `gps_track.db`.
6. **Possible later work:** camera streaming into the desktop app or map page; showing GPS in `car_control_app.py`; a `deploy.sh` that doesn't overwrite `config.py` (for example a `config_local.py` override).

## 5. Open Questions / Edge Cases
- **Pi power:** the earlier power-LED flicker was never explained. Check `vcgencmd get_throttled` (expect `0x0`), especially with the motors running.
- **L298N losses:** the board drops ~2 V, so at 12 V × 0.6 the motors get roughly 5 V. Watch for motor heating, and for the AA pack sagging under load.
- **Pi 4 UART:** `/dev/serial0` is the mini UART while Bluetooth is enabled. Fine at 9600 baud; `dtoverlay=disable-bt` is an option if the data gets corrupted.
- **Satellite count:** the sender's `sats` comes from GGA (satellites *used*), not satellites *in view*, so it shows 0 until a fix.
- **Firewall:** port 8000 is open on the Linux PC, but a direct Pi→PC connection hasn't been confirmed (errno 113 earlier). Possible Wi-Fi client isolation; the SSH tunnel is the fallback.
- **Geocoding:** never tested against the real APIs (sandbox blocked); only the parsing was tested with sample responses. `CONTACT_EMAIL` must be set (`setup_linux.sh`).
- **Zip vs Pi:** the zip's `pi/config.py` and `pi/car.py` lack the user's working local edits.
- **Pin conflict:** `server.py` (or the `robot-car` service) holds the GPIO pins, so stop it before running `test_motors.py`.
- **Motors and camera together:** motor vibration can blur photos. Stop the motors during captures, or use a short shutter time.