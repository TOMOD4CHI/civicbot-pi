#!/usr/bin/env python3
"""
Serveur GPS à lancer sur la machine Linux.
  - reçoit les positions envoyées par le Pi   (POST /api/gps)
  - trouve l'adresse (Nominatim, secours Photon) avec cache et limite de débit
  - enregistre le trajet dans SQLite
  - affiche une carte en direct sur http://localhost:8000

Aucune dépendance externe : uniquement la bibliothèque standard Python.
    python3 gps_server.py
"""
import json
import math
import os
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import server_config as cfg

HERE = os.path.dirname(os.path.abspath(__file__))
lock = threading.Lock()
latest = {}            # dernière position reçue (+ adresse)
geo_cache = {}         # (lat arrondie, lon arrondie) -> adresse


# ---------------------------------------------------------------- base
def db():
    conn = sqlite3.connect(os.path.join(HERE, cfg.DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY, received REAL, device TEXT, lat REAL, lon REAL,
        alt REAL, speed_kmh REAL, course REAL, sats INTEGER, hdop REAL,
        utc TEXT, address TEXT)""")
    return conn


def save(p):
    with db() as c:
        c.execute("""INSERT INTO positions (received, device, lat, lon, alt, speed_kmh,
                     course, sats, hdop, utc, address) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (time.time(), p.get("device"), p["lat"], p["lon"], p.get("alt"),
                   p.get("speed_kmh"), p.get("course"), p.get("sats"), p.get("hdop"),
                   p.get("utc"), p.get("address")))


def track(limit=500):
    with db() as c:
        rows = c.execute("SELECT lat, lon FROM positions ORDER BY id DESC LIMIT ?",
                         (limit,)).fetchall()
    return [[r[0], r[1]] for r in reversed(rows)]


# ---------------------------------------------------------------- géocodage
def distance_m(a, b):
    R = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def http_json(url, params):
    ua = cfg.USER_AGENT.format(email=cfg.CONTACT_EMAIL or "not-set")
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)


def nominatim(lat, lon):
    d = http_json(cfg.NOMINATIM_URL, {"lat": lat, "lon": lon, "format": "jsonv2",
                                      "accept-language": cfg.LANGUAGE, "zoom": 18})
    return d.get("display_name")


def photon(lat, lon):
    d = http_json(cfg.PHOTON_URL, {"lat": lat, "lon": lon, "lang": cfg.LANGUAGE})
    if not d.get("features"):
        return None
    p = d["features"][0]["properties"]
    street = " ".join(x for x in (p.get("housenumber"), p.get("street")) if x)
    parts = [p.get("name"), street, p.get("district"), p.get("city"),
             p.get("postcode"), p.get("country")]
    seen, out = set(), []
    for x in parts:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return ", ".join(out)


def reverse_geocode(lat, lon):
    key = (round(lat, 4), round(lon, 4))          # ~11 m : cache
    if key in geo_cache:
        return geo_cache[key], "cache"
    for name, fn in (("nominatim", nominatim), ("photon", photon)):
        try:
            addr = fn(lat, lon)
            if addr:
                geo_cache[key] = addr
                return addr, name
        except Exception as e:
            print(f"[geo] {name} indisponible : {e}")
        time.sleep(1.1)                            # jamais plus d'1 req/s
    return None, None


def geocoder_loop():
    last_point, last_time = None, 0.0
    while True:
        time.sleep(1)
        with lock:
            p = dict(latest)
        if not p.get("fix") or p.get("lat") is None:
            continue
        here = (p["lat"], p["lon"])
        moved = last_point is None or distance_m(here, last_point) >= cfg.GEOCODE_MIN_DISTANCE_M
        if not moved or time.time() - last_time < cfg.GEOCODE_MIN_INTERVAL_S:
            continue
        last_time = time.time()
        addr, src = reverse_geocode(*here)
        if addr:
            last_point = here
            with lock:
                latest["address"] = addr
                latest["address_source"] = src
            print(f"[geo] {addr}  ({src})")


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/api/gps":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            p = json.loads(self.rfile.read(n))
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "json invalide"})
        p["received"] = time.time()
        p["client"] = self.client_address[0]
        with lock:
            addr = latest.get("address") if p.get("fix") else None
            latest.clear()
            latest.update(p)
            if addr:
                latest["address"] = addr
            snapshot = dict(latest)
        if p.get("fix") and p.get("lat") is not None:
            save(snapshot)
        self._send(200, {"ok": True})

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            with open(os.path.join(HERE, "map.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path == "/api/latest":
            with lock:
                p = dict(latest)
            if p:
                p["age_s"] = round(time.time() - p["received"], 1)
            return self._send(200, p)
        if path == "/api/track":
            return self._send(200, track())
        self._send(404, {"error": "not found"})

    def log_message(self, *args):        # silence les logs HTTP
        pass


def main():
    if not cfg.CONTACT_EMAIL:
        print("[!] CONTACT_EMAIL vide dans server_config.py : Nominatim demande un "
              "User-Agent qui identifie l'application. Lance setup_linux.sh.")
    db().close()
    threading.Thread(target=geocoder_loop, daemon=True).start()
    srv = ThreadingHTTPServer((cfg.HOST, cfg.PORT), Handler)
    print(f"Serveur GPS prêt : http://localhost:{cfg.PORT}   (Ctrl+C pour quitter)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")


if __name__ == "__main__":
    main()
