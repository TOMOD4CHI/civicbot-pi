#!/usr/bin/env python3
"""
Lit le GPS GY-NEO6MV2 (NMEA sur l'UART du Pi) et envoie la position
au serveur de la machine Linux en HTTP (JSON).

    python3 gps_sender.py            # mode normal
    python3 gps_sender.py --raw      # affiche les trames NMEA brutes (diagnostic)
    python3 gps_sender.py --fake     # position simulée (tester sans GPS / sans fix)
    python3 gps_sender.py --server http://192.168.1.20:8000/api/gps
"""
import argparse
import json
import math
import sys
import time
import urllib.request
from datetime import datetime, timezone

import gps_config as cfg


# ---------------------------------------------------------------- NMEA
def checksum_ok(sentence):
    if "*" not in sentence:
        return False
    body, cs = sentence[1:].split("*", 1)
    calc = 0
    for ch in body:
        calc ^= ord(ch)
    try:
        return calc == int(cs[:2], 16)
    except ValueError:
        return False


def to_decimal(value, hemi):
    """ddmm.mmmm / dddmm.mmmm -> degrés décimaux"""
    if not value:
        return None
    dot = value.index(".")
    deg = float(value[:dot - 2])
    minutes = float(value[dot - 2:])
    dec = deg + minutes / 60
    return -dec if hemi in ("S", "W") else dec


class GpsState:
    def __init__(self):
        self.fix = False
        self.lat = self.lon = None
        self.alt = None
        self.speed_kmh = None
        self.course = None
        self.sats = 0
        self.hdop = None
        self.utc = None

    def feed(self, line):
        if not line.startswith("$") or not checksum_ok(line):
            return
        f = line.split("*")[0].split(",")
        kind = f[0][3:]                  # GPRMC / GNRMC -> RMC
        if kind == "RMC" and len(f) >= 10:
            self.fix = f[2] == "A"
            if self.fix:
                self.lat = to_decimal(f[3], f[4])
                self.lon = to_decimal(f[5], f[6])
                self.speed_kmh = round(float(f[7] or 0) * 1.852, 1)
                self.course = float(f[8]) if f[8] else None
                if f[1] and f[9]:
                    self.utc = datetime.strptime(f[9] + f[1][:6], "%d%m%y%H%M%S") \
                        .replace(tzinfo=timezone.utc).isoformat()
        elif kind == "GGA" and len(f) >= 10:
            self.sats = int(f[7] or 0)
            self.hdop = float(f[8]) if f[8] else None
            self.alt = float(f[9]) if f[9] else None

    def as_dict(self):
        return {
            "device": cfg.DEVICE_ID, "fix": self.fix,
            "lat": self.lat, "lon": self.lon, "alt": self.alt,
            "speed_kmh": self.speed_kmh, "course": self.course,
            "sats": self.sats, "hdop": self.hdop, "utc": self.utc,
        }


# ---------------------------------------------------------------- envoi
def send(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=cfg.HTTP_TIMEOUT) as r:
        return r.status


class Sender:
    def __init__(self, url):
        self.url = url
        self.online = None
        self.last = 0.0

    def maybe_send(self, data):
        now = time.monotonic()
        if now - self.last < cfg.SEND_INTERVAL:
            return
        self.last = now
        try:
            send(self.url, data)
            if self.online is not True:
                print(f"[ok] serveur joignable : {self.url}")
            self.online = True
        except Exception as e:
            if self.online is not False:
                print(f"[!] serveur injoignable ({e}) — nouvel essai en continu")
            self.online = False
        status = (f"FIX {data['lat']:.6f}, {data['lon']:.6f}  sats={data['sats']}"
                  if data["fix"] else f"pas de fix (sats={data['sats']})")
        print(f"\r{status}        ", end="", flush=True)


# ---------------------------------------------------------------- modes
def run_fake(sender):
    """Petit cercle autour du centre de Bizerte, pour tester toute la chaîne."""
    lat0, lon0, t = 37.2744, 9.8739, 0
    while True:
        lat = lat0 + 0.0015 * math.sin(t / 20)
        lon = lon0 + 0.0015 * math.cos(t / 20)
        sender.maybe_send({
            "device": cfg.DEVICE_ID, "fix": True, "lat": lat, "lon": lon,
            "alt": 5.0, "speed_kmh": 4.0, "course": (t * 3) % 360, "sats": 8,
            "hdop": 1.0, "utc": datetime.now(timezone.utc).isoformat(), "simulated": True,
        })
        t += 1
        time.sleep(1)


def run_serial(sender, raw):
    import serial  # python3-serial
    try:
        ser = serial.Serial(cfg.SERIAL_PORT, cfg.BAUDRATE, timeout=1)
    except serial.SerialException as e:
        sys.exit(f"Impossible d'ouvrir {cfg.SERIAL_PORT} : {e}\n"
                 "-> as-tu lancé setup_gps_pi.sh puis redémarré ?")
    print(f"Lecture GPS sur {cfg.SERIAL_PORT} @ {cfg.BAUDRATE} bauds")
    state = GpsState()
    got_data = time.monotonic()
    while True:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if not line:
            if time.monotonic() - got_data > 5:
                print("\n[!] aucune donnée du GPS : vérifie TX GPS -> broche 10 (RXD)")
                got_data = time.monotonic()
            continue
        got_data = time.monotonic()
        if raw:
            print(line)
            continue
        state.feed(line)
        sender.maybe_send(state.as_dict())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=cfg.SERVER_URL)
    ap.add_argument("--fake", action="store_true", help="position simulée")
    ap.add_argument("--raw", action="store_true", help="affiche les trames NMEA")
    a = ap.parse_args()
    sender = Sender(a.server)
    try:
        run_fake(sender) if a.fake else run_serial(sender, a.raw)
    except KeyboardInterrupt:
        print("\nArrêt.")


if __name__ == "__main__":
    main()
