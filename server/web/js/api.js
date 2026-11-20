// Shared helpers for the map and the dashboard.
const API = {
  async get(path) {
    const r = await fetch(path, { cache: "no-store" });
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.json();
  },
  async patch(path, body) {
    const r = await fetch(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.json();
  },
  detections: (q = {}) => API.get("/api/detections?" + new URLSearchParams(clean(q))),
  hotspots: (q = {}) => API.get("/api/hotspots?" + new URLSearchParams(clean(q))),
  stats: () => API.get("/api/stats"),
  telemetry: () => API.get("/api/telemetry/latest"),
  setStatus: (id, status) => API.patch(`/api/detections/${id}`, { status }),
};

function clean(obj) {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== null && v !== undefined && v !== ""));
}

const fmt = {
  date(ts) {
    return ts ? new Date(ts * 1000).toLocaleString(undefined, {
      day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    }) : "–";
  },
  ago(ts) {
    if (!ts) return "–";
    const s = Math.max(0, Date.now() / 1000 - ts);
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.floor(s / 60)} min ago`;
    if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
    return `${Math.floor(s / 86400)} d ago`;
  },
  source: (s) => ({ car_gps: "Car GPS", phone_gps: "Phone GPS" }[s] || s),
  num: (n) => (n ?? 0).toLocaleString(),
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
