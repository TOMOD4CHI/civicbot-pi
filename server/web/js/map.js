// Interactive pothole map: detections, critical zones, live car marker.
const DEFAULT_CENTER = [37.2744, 9.8739];   // Bizerte

const state = { days: 30, firstFit: true, markers: new Map(), focusId: null };

const map = L.map("map", { zoomControl: true }).setView(DEFAULT_CENTER, 14);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

const cluster = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 45 }).addTo(map);
const zonesLayer = L.layerGroup().addTo(map);
let carMarker = null;

// ---------------------------------------------------------------- filters
const $ = (id) => document.getElementById(id);
document.querySelectorAll("#period button").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll("#period button").forEach((x) => x.classList.toggle("active", x === b));
    state.days = Number(b.dataset.days);
    state.firstFit = true;
    refresh();
  }));
["f-car", "f-phone", "f-fixed"].forEach((id) => $(id).addEventListener("change", refresh));
$("l-zones").addEventListener("change", () => toggleLayer(zonesLayer, $("l-zones").checked));
$("l-car").addEventListener("change", () => carMarker && toggleLayer(carMarker, $("l-car").checked));

function updateHalos() {
  document.getElementById("map").classList.toggle("zoomed-in", map.getZoom() >= 17);
}
map.on("zoomend", updateHalos);
updateHalos();

function toggleLayer(layer, on) {
  if (on) layer.addTo(map); else map.removeLayer(layer);
}

function query() {
  const q = {};
  if (state.days) q.since = Date.now() / 1000 - state.days * 86400;
  const car = $("f-car").checked, phone = $("f-phone").checked;
  if (car !== phone) q.source = car ? "car_gps" : "phone_gps";
  return { q, none: !car && !phone };
}

// ---------------------------------------------------------------- popups
function popupHtml(d) {
  const rows = [
    ["Detected", `${fmt.date(d.created_at)} <span style="color:var(--muted)">(${fmt.ago(d.created_at)})</span>`],
    ["Address", esc(d.address) || '<span style="color:var(--muted)">looking up…</span>'],
    ["Position", `${d.lat.toFixed(6)}, ${d.lon.toFixed(6)}`],
    ["Source", fmt.source(d.source) + (d.accuracy_m ? ` · ±${d.accuracy_m} m` : "")],
  ];
  if (d.sats != null) rows.push(["Satellites", `${d.sats}${d.hdop ? ` · HDOP ${d.hdop}` : ""}`]);
  rows.push(["Trigger", d.trigger === "model"
    ? `Model${d.confidence != null ? ` (${Math.round(d.confidence * 100)} %)` : ""}` : "Manual"]);
  rows.push(["Status", `<span class="badge ${d.status}">${d.status}</span>`]);
  const actions = ["new", "confirmed", "fixed"]
    .filter((s) => s !== d.status)
    .map((s) => `<button class="btn${s === "fixed" ? " primary" : ""}" data-id="${d.id}" data-status="${s}">Mark ${s}</button>`)
    .join("");
  return `<div class="pop">
    <h4>Pothole #${d.id}</h4>
    ${d.image_url ? `<a href="${d.image_url}" target="_blank" rel="noopener"><img src="${d.image_url}" alt="pothole #${d.id}"></a>` : ""}
    <table>${rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("")}</table>
    <div class="actions">${actions}</div>
  </div>`;
}

map.on("popupopen", (e) => {
  e.popup.getElement().querySelectorAll("button[data-status]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      await API.setStatus(b.dataset.id, b.dataset.status);
      map.closePopup();
      refresh();
    }));
});

// ---------------------------------------------------------------- data
async function refresh() {
  const { q, none } = query();
  try {
    const [dets, zones] = await Promise.all([
      none ? [] : API.detections(q),
      none ? [] : API.hotspots(q),
    ]);
    const shown = $("f-fixed").checked ? dets : dets.filter((d) => d.status !== "fixed");
    drawDetections(shown);
    drawZones(zones);
    $("s-shown").textContent = fmt.num(shown.length);
    $("s-critical").textContent = fmt.num(zones.filter((z) => z.level === "critical").length);
    if (state.firstFit && shown.length) {
      map.fitBounds(L.latLngBounds(shown.map((d) => [d.lat, d.lon])).pad(0.15), { maxZoom: 16 });
      state.firstFit = false;
    }
    if (state.focusId && state.markers.has(state.focusId)) {
      const m = state.markers.get(state.focusId);
      cluster.zoomToShowLayer(m, () => m.openPopup());
      state.focusId = null;
    }
  } catch (e) {
    console.error(e);
  }
}

function drawDetections(dets) {
  const open = map._popup && map._popup.isOpen && map._popup.isOpen();
  if (open) return;   // don't yank a popup away while the user reads it
  cluster.clearLayers();
  state.markers.clear();
  for (const d of dets) {
    const icon = L.divIcon({ className: "", html: `<div class="pin ${d.status}"></div>`, iconSize: [16, 16] });
    const m = L.marker([d.lat, d.lon], { icon, title: `Pothole #${d.id}` }).bindPopup(popupHtml(d));
    state.markers.set(d.id, m);
    cluster.addLayer(m);
  }
}

function drawZones(zones) {
  zonesLayer.clearLayers();
  const list = $("zones");
  if (!zones.length) {
    list.innerHTML = '<div class="empty">No zone yet.</div>';
    return;
  }
  list.innerHTML = "";
  zones.forEach((z, i) => {
    const color = z.level === "critical" ? cssVar("--critical") : cssVar("--warning");
    const tip = `<b>${z.level === "critical" ? "Critical" : "Warning"} zone</b><br>
        ${z.count} potholes${z.road ? ` · ${esc(z.road)}` : ""}<br>
        ${fmt.date(z.first_at)} → ${fmt.date(z.last_at)}`;
    // Real-size circle when zoomed in, fixed-size halo when zoomed out (so zones stay visible).
    L.circle([z.lat, z.lon], {
      radius: z.radius_m, color, weight: 3, fillColor: color, fillOpacity: 0.15,
    }).bindTooltip(tip, { sticky: true }).addTo(zonesLayer);
    L.circleMarker([z.lat, z.lon], {
      radius: Math.min(16 + z.count * 1.5, 34), color, weight: 3, fillColor: color, fillOpacity: 0.12,
      className: "zone-halo", interactive: true,
    }).bindTooltip(tip, { sticky: true }).addTo(zonesLayer);

    const item = document.createElement("div");
    item.className = "zone-item";
    item.innerHTML = `<div class="count" style="background:${color}">${z.count}</div>
      <div><div>${esc(z.road || `Zone ${i + 1}`)}</div>
      <div class="meta">${z.level} · last ${fmt.ago(z.last_at)}</div></div>`;
    item.addEventListener("click", () => map.setView([z.lat, z.lon], 18));
    list.appendChild(item);
  });
}

// ---------------------------------------------------------------- live car
async function refreshCar() {
  try {
    const t = await API.telemetry();
    const online = !!t.online;
    $("car-dot").classList.toggle("on", online);
    $("car-label").textContent = !online ? "Car offline"
      : t.fix ? `Car online · ${t.sats ?? 0} sats` : "Car online · no GPS fix";
    if (t.lat == null) return;
    const icon = L.divIcon({ className: "", html: `<div class="car-icon${online ? "" : " offline"}">🚗</div>`, iconSize: [34, 34] });
    if (!carMarker) {
      carMarker = L.marker([t.lat, t.lon], { icon, zIndexOffset: 1000 });
      if ($("l-car").checked) carMarker.addTo(map);
    } else {
      carMarker.setLatLng([t.lat, t.lon]).setIcon(icon);
    }
    carMarker.bindTooltip(`Pothole Pi car · ${t.speed_kmh ?? 0} km/h · updated ${t.age_s}s ago`);
  } catch (e) {
    console.error(e);
  }
}

// ---------------------------------------------------------------- start
(async () => {
  try {
    const st = await API.stats();
    $("legend-critical").textContent = `Critical zone (≥ ${st.config.critical_min} within ${st.config.hotspot_radius_m} m)`;
    $("legend-warning").textContent = `Warning zone (≥ ${st.config.warning_min})`;
  } catch (e) { /* legend keeps its default text */ }
  const focus = new URLSearchParams(location.search).get("focus");
  if (focus) { state.focusId = Number(focus); state.days = 0; document.querySelector('#period [data-days="0"]').click(); }
  else refresh();
  refreshCar();
  setInterval(refresh, 10000);
  setInterval(refreshCar, 2000);
})();
