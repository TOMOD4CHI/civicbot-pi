# API reference

Interactive docs: `http://<pi>:8080/docs` (car) and `http://<pc>:8000/docs` (server).

## Car (Raspberry Pi, port 8080)

### `WS /ws/control`
Client → car, one JSON message at a time. The app sends 10 per second while the stick is held.

| Message | Effect |
|---------|--------|
| `{"type":"drive","left":0.5,"right":0.5}` | Wheel speeds in −1..1 |
| `{"type":"arcade","throttle":1,"steering":-0.3}` | Throttle/steering, mixed on the car |
| `{"type":"stop"}` | Stop now |
| `{"type":"ping"}` | Keeps the watchdog fed; the car answers `{"type":"pong"}` |

Replies: `{"type":"ack"}`, or `{"type":"error","message":...}` for a bad message. The car stops after 0.5 s without a message, and when the socket closes.

### `POST /api/report`
```json
{ "phone_lat": 37.27, "phone_lon": 9.87, "phone_accuracy": 8, "include_image": true }
```
All fields are optional. The car's GPS is used if it has a fix less than 5 s old; otherwise the phone's position is used.

| Result | Response |
|--------|----------|
| Success | `200 {"id": 81, "source": "car_gps", "lat": ..., "lon": ..., "has_image": true}` |
| No position from either GPS | `422` |
| Server unreachable | `502` |

### Other endpoints
- `GET /api/status`: drive state, GPS fix, camera, server reachability, detector.
- `GET /stream.mjpg`: MJPEG stream.
- `GET /snapshot.jpg`: the latest frame.
- `GET /viewer`: a full-screen stream page, used by the app's WebView.
- `GET /health`

## Server (Linux PC, port 8000)

### `POST /api/detections` (sent by the car)
```json
{
  "lat": 37.2744, "lon": 9.8739, "source": "car_gps",
  "device_id": "pothole-pi", "captured_at": "2026-11-20T16:40:09+00:00",
  "accuracy_m": 2.5, "hdop": 1.0, "sats": 8, "speed_kmh": 4.0,
  "trigger": "manual", "confidence": null, "bbox": null,
  "image_b64": "<JPEG base64>"
}
```
- Returns `201 {"id": 81}`.
- The address is filled in asynchronously by the geocoding worker.

### Detections
- `GET /api/detections`: list detections, newest first. Optional filters: `since`, `until` (unix seconds), `source`, `status`, `limit`.
- `GET /api/detections/{id}`: one detection.
- `PATCH /api/detections/{id}`: change the status. Body: `{"status": "new" | "confirmed" | "fixed"}`.
- `DELETE /api/detections/{id}`: delete a detection.

### Zones, statistics and live position
- `GET /api/hotspots?since=&until=&source=&include_fixed=false`: ranked zones. Each has:
  - `level` (`warning` / `critical`)
  - `count`, center, `radius_m`
  - `first_at`, `last_at`
  - main `road`
  - `detection_ids`
- `GET /api/stats`: data for the dashboard:
  - KPIs
  - per day, per hour and per weekday counts
  - top roads and cities
  - source, trigger and status splits
  - top zones, and the 20 most recent detections
- `POST /api/telemetry`, `GET /api/telemetry/latest`: the car's live position.

### Images and pages
- `GET /images/{id}.jpg`: photo of the detection.
- `GET /`: map page. `GET /dashboard`: dashboard page.
