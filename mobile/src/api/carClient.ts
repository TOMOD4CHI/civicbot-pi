// HTTP + WebSocket client for the car service running on the Raspberry Pi.

export type CarStatus = {
  device_id: string;
  simulate: boolean;
  drive: { left: number; right: number; moving: boolean; clients: number };
  gps: {
    fix: boolean;
    lat: number | null;
    lon: number | null;
    sats: number;
    hdop: number | null;
    speed_kmh: number | null;
    age_s: number | null;
    connected: boolean;
    error: string | null;
  };
  camera: { source: string; ok: boolean; error: string | null };
  server: { url: string; reachable: boolean | null };
  detector: { name: string; active: boolean; reports: number };
};

export type ReportResult = {
  id: number;
  source: "car_gps" | "phone_gps";
  lat: number;
  lon: number;
  has_image: boolean;
};

export type PhoneFix = { lat: number; lon: number; accuracy: number | null };

export const carUrls = (host: string, port: number) => {
  const base = `http://${host}:${port}`;
  return {
    base,
    ws: `ws://${host}:${port}/ws/control`,
    viewer: `${base}/viewer`,
    status: `${base}/api/status`,
    report: `${base}/api/report`,
  };
};

async function fetchWithTimeout(url: string, init: RequestInit = {}, ms = 4000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(t);
  }
}

export async function getStatus(host: string, port: number): Promise<CarStatus> {
  const r = await fetchWithTimeout(carUrls(host, port).status);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function sendReport(host: string, port: number, phone: PhoneFix | null): Promise<ReportResult> {
  const body = phone
    ? { phone_lat: phone.lat, phone_lon: phone.lon, phone_accuracy: phone.accuracy }
    : {};
  const r = await fetchWithTimeout(
    carUrls(host, port).report,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    15000,
  );
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data?.detail ?? `HTTP ${r.status}`);
  return data as ReportResult;
}

export type DriveMessage =
  | { type: "drive"; left: number; right: number }
  | { type: "stop" }
  | { type: "ping" };

/** Arcade mixing: throttle/steering (-1..1) -> left/right wheel speeds (-1..1). */
export function arcadeMix(throttle: number, steering: number): { left: number; right: number } {
  const left = throttle + steering;
  const right = throttle - steering;
  const m = Math.max(1, Math.abs(left), Math.abs(right));
  return { left: left / m, right: right / m };
}
