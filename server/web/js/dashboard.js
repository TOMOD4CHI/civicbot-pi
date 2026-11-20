// Statistics dashboard (auto-refresh every 15 s).
const charts = {};
const $ = (id) => document.getElementById(id);

function palette() {
  return {
    text: cssVar("--muted"), grid: cssVar("--border"), accent: cssVar("--accent"),
    critical: cssVar("--critical"), warning: cssVar("--warning"), ok: cssVar("--ok"), info: cssVar("--info"),
  };
}

function baseOptions(p, extra = {}) {
  return {
    responsive: true, maintainAspectRatio: false, animation: { duration: 300 },
    plugins: { legend: { display: false }, tooltip: { intersect: false, mode: "index" } },
    scales: {
      x: { ticks: { color: p.text, maxRotation: 0, autoSkipPadding: 12 }, grid: { display: false } },
      y: { beginAtZero: true, ticks: { color: p.text, precision: 0 }, grid: { color: p.grid } },
    },
    ...extra,
  };
}

function upsert(id, config) {
  if (charts[id]) {
    charts[id].data = config.data;
    charts[id].update();
  } else {
    charts[id] = new Chart($(id), config);
  }
}

function kpi(label, value, sub = "", cls = "") {
  return `<div class="card kpi ${cls}"><div class="label">${label}</div>
    <div class="value">${value}</div><div class="sub">${sub}</div></div>`;
}

function render(st) {
  const t = st.totals, p = palette();
  const carPct = t.total ? Math.round(100 * (st.by_source.car_gps || 0) / t.total) : 0;
  $("kpis").innerHTML = [
    kpi("Total potholes", fmt.num(t.total), `${fmt.num(t.open)} still open`),
    kpi("Today", fmt.num(t.today), `${fmt.num(t.last_7_days)} in the last 7 days`),
    kpi("Daily average", t.avg_per_day_30d, "over the last 30 days"),
    kpi("Critical zones", fmt.num(t.critical_zones), `${fmt.num(t.warning_zones)} warning zones`, t.critical_zones ? "alert" : ""),
    kpi("Fixed", fmt.num(t.fixed), `${fmt.num(t.confirmed)} confirmed`),
    kpi("Car GPS share", `${carPct} %`, `${t.with_image_pct} % with photo`),
  ].join("");
  $("updated").textContent = `Last detection ${fmt.ago(t.last_detection_at)} · updated ${new Date().toLocaleTimeString()}`;
  $("zones-rule").textContent =
    `≥ ${st.config.critical_min} potholes within ${st.config.hotspot_radius_m} m = critical, ≥ ${st.config.warning_min} = warning`;

  upsert("c-days", {
    type: "line",
    data: {
      labels: st.per_day.map((d) => new Date(d.date).toLocaleDateString(undefined, { day: "2-digit", month: "short" })),
      datasets: [{
        data: st.per_day.map((d) => d.count), borderColor: p.accent, backgroundColor: p.accent + "33",
        fill: true, cubicInterpolationMode: "monotone", pointRadius: 2, borderWidth: 2,
      }],
    },
    options: baseOptions(p),
  });

  const statusKeys = ["new", "confirmed", "fixed"];
  upsert("c-status", {
    type: "doughnut",
    data: {
      labels: ["New", "Confirmed", "Fixed"],
      datasets: [{ data: statusKeys.map((k) => st.by_status[k] || 0),
        backgroundColor: [p.critical, p.warning, p.ok], borderWidth: 0 }],
    },
    options: { responsive: true, maintainAspectRatio: false, cutout: "65%",
      plugins: { legend: { position: "bottom", labels: { color: p.text, boxWidth: 12 } } } },
  });

  upsert("c-roads", {
    type: "bar",
    data: {
      labels: st.top_roads.map((r) => r.road.length > 28 ? r.road.slice(0, 27) + "…" : r.road),
      datasets: [{ data: st.top_roads.map((r) => r.count), backgroundColor: p.critical, borderRadius: 4 }],
    },
    options: baseOptions(p, {
      indexAxis: "y",
      scales: {
        x: { beginAtZero: true, ticks: { color: p.text, precision: 0 }, grid: { color: p.grid } },
        y: { ticks: { color: p.text }, grid: { display: false } },
      },
    }),
  });

  upsert("c-hours", {
    type: "bar",
    data: {
      labels: st.by_hour.map((_, h) => `${String(h).padStart(2, "0")}h`),
      datasets: [{ data: st.by_hour, backgroundColor: p.info, borderRadius: 3 }],
    },
    options: baseOptions(p),
  });

  upsert("c-source", {
    type: "doughnut",
    data: {
      labels: ["Car GPS", "Phone GPS"],
      datasets: [{ data: [st.by_source.car_gps || 0, st.by_source.phone_gps || 0],
        backgroundColor: [p.accent, p.info], borderWidth: 0 }],
    },
    options: { responsive: true, maintainAspectRatio: false, cutout: "65%",
      plugins: { legend: { position: "bottom", labels: { color: p.text, boxWidth: 12 } } } },
  });

  $("t-zones").innerHTML = st.hotspots.length
    ? `<tr><th>#</th><th>Level</th><th>Road</th><th class="num">Potholes</th><th>First</th><th>Latest</th><th></th></tr>` +
      st.hotspots.map((z, i) => `<tr>
        <td>${i + 1}</td>
        <td><span class="badge ${z.level}">${z.level}</span></td>
        <td>${esc(z.road || "Unknown road")}</td>
        <td class="num">${z.count}</td>
        <td>${fmt.date(z.first_at)}</td>
        <td>${fmt.ago(z.last_at)}</td>
        <td><a href="/?focus=${z.detection_ids[z.detection_ids.length - 1]}">Map →</a></td></tr>`).join("")
    : `<tr><td class="empty">No critical zone yet.</td></tr>`;

  $("t-recent").innerHTML = st.recent.length
    ? `<tr><th></th><th>#</th><th>When</th><th>Address</th><th>Source</th><th>Trigger</th><th>Status</th><th></th></tr>` +
      st.recent.map((d) => `<tr>
        <td>${d.image_url ? `<img class="thumb" src="${d.image_url}" alt="" loading="lazy">` : '<div class="thumb"></div>'}</td>
        <td>${d.id}</td>
        <td title="${fmt.date(d.created_at)}">${fmt.ago(d.created_at)}</td>
        <td>${esc(d.address || `${d.lat.toFixed(5)}, ${d.lon.toFixed(5)}`)}</td>
        <td>${fmt.source(d.source)}${d.accuracy_m ? ` · ±${d.accuracy_m} m` : ""}</td>
        <td>${d.trigger === "model" ? "Model" : "Manual"}</td>
        <td><span class="badge ${d.status}">${d.status}</span></td>
        <td><a href="/?focus=${d.id}">Map →</a></td></tr>`).join("")
    : `<tr><td class="empty">No detection yet. Press “Send location” in the app.</td></tr>`;
}

async function refresh() {
  try {
    render(await API.stats());
  } catch (e) {
    $("updated").textContent = `Cannot reach the server: ${e.message}`;
  }
}

async function refreshCar() {
  try {
    const t = await API.telemetry();
    $("car-dot").classList.toggle("on", !!t.online);
    $("car-label").textContent = !t.online ? "Car offline" : t.fix ? `Car online · ${t.sats ?? 0} sats` : "Car online · no GPS fix";
  } catch (e) { /* ignore */ }
}

refresh();
refreshCar();
setInterval(refresh, 15000);
setInterval(refreshCar, 5000);
