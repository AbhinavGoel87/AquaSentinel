const fieldNode = document.getElementById("field");
const zonesNode = document.getElementById("zones");
const sensorsNode = document.getElementById("sensors");
const alertsNode = document.getElementById("alerts");
const bannerNode = document.getElementById("banner");
const identityNode = document.getElementById("identity");
const legendNode = document.getElementById("legend");
const errorNode = document.getElementById("error");
const controlsNode = document.getElementById("controls");
const doctorNode = document.getElementById("doctor");

let busy = false;

function esc(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[ch]));
}

function formatTime(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function zoneById(data, zoneId) {
  return data.zones.find((zone) => zone.id === zoneId);
}

function readingClass(zone) {
  if (zone.status === "insufficient") return "bad";
  if (zone.status === "uneven") return "warn";
  if (zone.average == null) return "bad";
  if (zone.average < zone.low_threshold) return "dry";
  if (zone.average >= zone.target_moisture) return "high";
  return "ok";
}

function readingLabel(zone) {
  if (zone.status === "insufficient") return "Needs more sensors";
  if (zone.status === "uneven") return "Uneven bed";
  if (zone.average == null) return "No average";
  if (zone.average < zone.low_threshold) return "Below setpoint";
  if (zone.average >= zone.target_moisture) return "Above target";
  return "In range";
}

function zoneFill(zone) {
  if (zone.status === "insufficient" || zone.average == null) return "#3c4742";
  if (zone.average < zone.low_threshold) return "#6d4a2e";
  if (zone.average >= zone.target_moisture) return "#2f5963";
  return "#2f5a3c";
}

function sensorFill(sensor, zone) {
  if (sensor.quality === "missing" || sensor.quality === "invalid") return "#8a403c";
  if (sensor.quality === "suspect") return "#a7843a";
  if (sensor.moisture == null || !zone) return "#8a403c";
  if (sensor.moisture < zone.low_threshold) return "#d08a5a";
  if (sensor.moisture >= zone.target_moisture) return "#8eb8c4";
  return "#b7d7a8";
}

function qualityLabel(quality) {
  if (quality === "ok") return "Usable";
  if (quality === "suspect") return "Left out";
  if (quality === "missing") return "No reading";
  return "Rejected";
}

function showError(message) {
  if (!message) {
    errorNode.hidden = true;
    errorNode.textContent = "";
    return;
  }
  errorNode.hidden = false;
  errorNode.textContent = message;
}

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "The controller refused that request.");
  }
  return data;
}

function render(data) {
  const scale = Number(data.time_scale);
  bannerNode.innerHTML = `<strong>Simulated data.</strong> ${esc(data.disclaimer)} Field time runs at ${esc(scale)}×. ${esc(data.model_note)} ${esc(data.water_note)}`;

  if (!document.getElementById("clock-wall")) {
    identityNode.innerHTML = `
      <div class="clocks">
        <div><span>Computer time</span><strong id="clock-wall"></strong></div>
        <div><span>Simulated field time</span><strong id="clock-sim"></strong></div>
      </div>
      <div class="actions">
        <button type="button" class="btn btn-stop" data-action="estop">Emergency stop</button>
        <button type="button" class="btn btn-quiet" id="estop-reset" data-action="estop-reset">Reset stop</button>
      </div>
    `;
  }
  document.getElementById("clock-wall").textContent = formatTime(data.wall_time);
  document.getElementById("clock-sim").textContent = formatTime(data.sim_time);
  document.getElementById("estop-reset").disabled = !data.emergency_stop;

  renderField(data);
  renderLegend(data);
  renderZones(data);
  renderSensors(data);
  renderAlerts(data.alerts || []);
  renderDoctor(data);
  ensureControls(data);
}

function renderField(data) {
  const parts = [];
  parts.push(`<svg viewBox="0 0 100 100" role="img" aria-label="Simulated field with two irrigation zones, a center road, and a docking station">`);
  parts.push(`<rect class="soil" x="0" y="0" width="100" height="100"></rect>`);
  if (data.road) {
    const road = data.road;
    parts.push(`<rect class="road" x="${road.x}" y="${road.y}" width="${road.w}" height="${road.h}"></rect>`);
  }
  for (const route of data.routes) {
    if (!route.dock) continue;
    const dock = route.dock;
    parts.push(`<rect class="dock" x="${dock.x - 5}" y="${dock.y - 3}" width="10" height="8"></rect>`);
    parts.push(`<text class="dock-label" x="${dock.x}" y="${dock.y + 6.2}">Dock</text>`);
  }
  for (const pipe of data.pipes) {
    parts.push(`<line class="pipe" x1="${pipe.x1}" y1="${pipe.y1}" x2="${pipe.x2}" y2="${pipe.y2}"></line>`);
  }
  for (const route of data.routes) {
    const path = route.points.map((point, index) => `${index ? "L" : "M"}${point[0]} ${point[1]}`).join(" ");
    parts.push(`<path class="route" d="${path}"></path>`);
    for (const checkpoint of route.checkpoints) {
      parts.push(`<rect class="checkpoint" x="${checkpoint.x - 0.7}" y="${checkpoint.y - 0.7}" width="1.4" height="1.4"><title>${esc(checkpoint.name)}</title></rect>`);
    }
  }
  for (const zone of data.zones) {
    const box = zone.bounds;
    const stroke = zone.valve_open ? "#d7b56d" : "#31483d";
    parts.push(`<rect class="zone" x="${box.x}" y="${box.y}" width="${box.w}" height="${box.h}" fill="${zoneFill(zone)}" stroke="${stroke}"></rect>`);
    parts.push(`<text class="zone-name" x="${box.x + 1.2}" y="${box.y + 4}">${esc(zone.name)}</text>`);
    parts.push(`<text class="zone-meta" x="${box.x + 1.2}" y="${box.y + 7}">${zone.valve_open ? "Sprinkler on" : "Sprinkler off"}</text>`);
  }
  for (const sensor of data.sensors) {
    const zone = zoneById(data, sensor.zone_id);
    const text = sensor.moisture == null ? "n/a" : Math.round(sensor.moisture);
    parts.push(`<g><title>${esc(sensor.zone_id)} ${esc(sensor.label)}: ${esc(text)}. ${esc(sensor.reason)}</title>`);
    parts.push(`<circle cx="${sensor.x}" cy="${sensor.y}" r="1.7" fill="${sensorFill(sensor, zone)}"></circle>`);
    parts.push(`<text class="sensor-read" x="${sensor.x + 2.4}" y="${sensor.y + 0.7}">${esc(text)}</text></g>`);
  }
  for (const rover of data.rovers) {
    const short = "Dr";
    parts.push(`<g class="rover"><title>${esc(rover.name)}. ${esc(rover.status_label)}</title>`);
    parts.push(`<rect x="${rover.x - 3.1}" y="${rover.y - 2.2}" width="6.2" height="4.4" rx="0.5"></rect>`);
    parts.push(`<text x="${rover.x}" y="${rover.y + 0.8}">${short}</text></g>`);
  }
  parts.push(`</svg>`);
  fieldNode.innerHTML = parts.join("");
}

function renderLegend(data) {
  const rovers = data.rovers.map((rover) => `${esc(rover.name)}: ${esc(rover.status_label)}.`).join(" ");
  legendNode.innerHTML = `
    <span><i class="swatch" style="background:#d08a5a"></i>Below setpoint</span>
    <span><i class="swatch" style="background:#b7d7a8"></i>In range</span>
    <span><i class="swatch" style="background:#8eb8c4"></i>Above target</span>
    <span><i class="swatch" style="background:#a7843a"></i>Left out of average</span>
    <span><i class="swatch" style="background:#8a403c"></i>No reading</span>
    <span>${rovers}</span>
  `;
}

function sparkline(history) {
  const values = (history || []).map((point) => point.average).filter((value) => value != null);
  if (values.length < 2) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);
  const width = 120;
  const height = 32;
  const path = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - min) / span) * (height - 4) - 2;
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return `<svg class="spark" viewBox="0 0 ${width} ${height}" aria-hidden="true"><path d="${path}"></path></svg>`;
}

function renderZones(data) {
  if (zonesNode.dataset.ready !== "1") {
    zonesNode.innerHTML = data.zones.map((zone) => `
      <article class="zone-card" id="card-${esc(zone.id)}">
        <header>
          <div>
            <h3>${esc(zone.name)}</h3>
            <p class="crop">${esc(zone.crop_label)} · simulated</p>
          </div>
          <div class="spark-slot"></div>
        </header>
        <p class="average"><span class="avg-value"></span><small> %</small></p>
        <p class="status"></p>
        <p class="note setpoint"></p>
        <p class="note valve-line"></p>
        <div class="card-row">
          <button type="button" class="btn" data-action="valve" data-zone="${esc(zone.id)}" data-open="true">Open sprinkler</button>
          <button type="button" class="btn btn-quiet" data-action="valve" data-zone="${esc(zone.id)}" data-open="false">Close sprinkler</button>
        </div>
      </article>
    `).join("");
    zonesNode.dataset.ready = "1";
  }
  for (const zone of data.zones) {
    const card = document.getElementById(`card-${zone.id}`);
    card.querySelector(".spark-slot").innerHTML = sparkline(zone.history);
    card.querySelector(".avg-value").textContent = zone.average == null ? "n/a" : Number(zone.average).toFixed(1);
    const status = card.querySelector(".status");
    status.textContent = readingLabel(zone);
    status.className = `status ${readingClass(zone)}`;
    card.querySelector(".setpoint").textContent = `${zone.summary} Setpoint ${zone.low_threshold}% to ${zone.target_moisture}%. A dry zone with two agreeing sensors opens its sprinkler.`;
    card.querySelector(".valve-line").textContent = zone.valve_open
      ? `Sprinkler on for ${zone.seconds_open}s. Safety limit ${Math.round(zone.max_duration_sec / 60)} min.`
      : `Sprinkler off. Safety limit ${Math.round(zone.max_duration_sec / 60)} min.`;
    card.querySelector('[data-open="true"]').disabled = Boolean(data.emergency_stop || zone.valve_open);
    card.querySelector('[data-open="false"]').disabled = !zone.valve_open;
  }
}

function renderSensors(data) {
  const rows = data.sensors.map((sensor) => {
    const zone = zoneById(data, sensor.zone_id);
    const moisture = sensor.moisture == null ? "n/a" : Number(sensor.moisture).toFixed(1);
    return `<tr>
      <td>${esc(sensor.label)}<div class="hint">${esc(sensor.id)}</div></td>
      <td>${esc(zone ? zone.name : sensor.zone_id)}</td>
      <td class="num">${esc(moisture)}</td>
      <td class="pill">${esc(qualityLabel(sensor.quality))}</td>
      <td>${esc(sensor.reason)} <span class="hint">Simulated.</span></td>
    </tr>`;
  }).join("");
  sensorsNode.innerHTML = `<table>
    <thead><tr><th>Sensor</th><th>Zone</th><th>Reading</th><th>Health</th><th>Note</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function renderAlerts(alerts) {
  if (!alerts.length) {
    alertsNode.innerHTML = `<p class="empty">No active alerts.</p>`;
    return;
  }
  alertsNode.innerHTML = alerts.map((alert) => `
    <div class="alert ${esc(alert.severity)}">
      <strong>${esc(alert.severity)}</strong>
      <div>${esc(alert.message)}</div>
    </div>
  `).join("");
}

function renderDoctor(data) {
  if (doctorNode.dataset.ready !== "1") {
    doctorNode.innerHTML = `
      <p class="empty" id="doctor-empty"></p>
      <div class="doctor-result" id="doctor-result" hidden>
        <img id="doctor-photo" alt="Latest plant photo">
        <div>
          <p class="status" id="doctor-title"></p>
          <p id="doctor-message"></p>
          <p class="note" id="doctor-action"></p>
          <p class="hint" id="doctor-score"></p>
          <p class="note" id="doctor-treatment"></p>
          <div class="card-row">
            <button type="button" class="btn" data-action="confirm-treatment" id="doctor-confirm">Add to irrigation tank</button>
            <button type="button" class="btn btn-quiet" data-action="stop-treatment" id="doctor-stop">Stop treatment</button>
          </div>
        </div>
      </div>
    `;
    doctorNode.dataset.ready = "1";
  }
  const doctor = data.doctor || {};
  const report = doctor.report;
  const treatment = data.treatment || { active: false, note: "" };
  const empty = document.getElementById("doctor-empty");
  const result = document.getElementById("doctor-result");
  if (!report) {
    empty.hidden = false;
    empty.textContent = doctor.note || "Waiting for a photo.";
    result.hidden = true;
    return;
  }
  empty.hidden = true;
  result.hidden = false;
  const photo = document.getElementById("doctor-photo");
  if (photo.getAttribute("src") !== report.image_url) photo.src = report.image_url;
  document.getElementById("doctor-title").textContent = report.title;
  document.getElementById("doctor-message").textContent = report.farmer_message;
  document.getElementById("doctor-action").textContent = report.recommended_action;
  document.getElementById("doctor-score").textContent = `Closest match ${report.match_score}. ${report.honesty || doctor.note || ""}`;
  document.getElementById("doctor-treatment").textContent = treatment.active
    ? `${treatment.title || treatment.treatment_id} · ${treatment.seconds_remaining}s left. ${treatment.note}`
    : treatment.note;
  const confirm = document.getElementById("doctor-confirm");
  confirm.dataset.report = String(report.report_id);
  confirm.disabled = !report.can_treat || treatment.active || data.emergency_stop;
  document.getElementById("doctor-stop").disabled = !treatment.active;
}

function ensureControls(data) {
  if (controlsNode.dataset.ready === "1") return;
  const options = data.sensors.map((sensor) => (
    `<option value="${esc(sensor.id)}">${esc(sensor.id)} · ${esc(sensor.label)}</option>`
  )).join("");
  controlsNode.innerHTML = `
    <div class="controls">
      <label>Sensor<select id="fault-sensor">${options}</select></label>
      <button type="button" class="btn" data-action="fault-on">Drop readings</button>
      <button type="button" class="btn btn-quiet" data-action="fault-off">Restore readings</button>
    </div>
  `;
  controlsNode.dataset.ready = "1";
}

async function refresh() {
  try {
    const response = await fetch("/api/field");
    if (!response.ok) throw new Error("The controller did not answer.");
    render(await response.json());
    showError("");
  } catch (error) {
    showError(error.message);
  }
}

document.body.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button || button.disabled || busy) return;
  const action = button.dataset.action;
  try {
    busy = true;
    if (action === "estop") {
      if (!window.confirm("Turn off every sprinkler and stop any treatment?")) return;
      render(await post("/api/emergency-stop"));
    } else if (action === "estop-reset") {
      render(await post("/api/emergency-stop/reset"));
    } else if (action === "valve") {
      render(await post(`/api/zones/${encodeURIComponent(button.dataset.zone)}/valve`, {
        open: button.dataset.open === "true",
      }));
    } else if (action === "confirm-treatment") {
      render(await post("/api/treatments/confirm", { report_id: Number(button.dataset.report) }));
    } else if (action === "stop-treatment") {
      render(await post("/api/treatments/stop"));
    } else if (action === "fault-on" || action === "fault-off") {
      const sensorId = document.getElementById("fault-sensor").value;
      render(await post(`/api/simulation/sensors/${encodeURIComponent(sensorId)}/fault`, {
        failed: action === "fault-on",
      }));
    }
    showError("");
  } catch (error) {
    showError(error.message);
  } finally {
    busy = false;
  }
});

document.getElementById("photo-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  const file = document.getElementById("photo-file").files[0];
  if (!file) return;
  const body = new FormData();
  body.append("image", file);
  body.append("source", "simulated");
  body.append("rover_id", "rover1");
  try {
    busy = true;
    const response = await fetch("/api/inspections", { method: "POST", body });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The photo could not be checked.");
    await refresh();
    showError("");
  } catch (error) {
    showError(error.message);
  } finally {
    busy = false;
  }
});

const tabButtons = [...document.querySelectorAll("[role='tab']")];

function showTab(tabId) {
  for (const button of tabButtons) {
    const selected = button.dataset.tab === tabId;
    button.setAttribute("aria-selected", selected ? "true" : "false");
    button.tabIndex = selected ? 0 : -1;
    document.getElementById(button.getAttribute("aria-controls")).hidden = !selected;
  }
  try { sessionStorage.setItem("kshetra-tab", tabId); } catch (error) { /* private mode can block storage */ }
}

document.querySelector("[role='tablist']").addEventListener("click", (event) => {
  const button = event.target.closest("[role='tab']");
  if (!button) return;
  showTab(button.dataset.tab);
  button.focus();
});

document.querySelector("[role='tablist']").addEventListener("keydown", (event) => {
  const current = tabButtons.findIndex((button) => button.getAttribute("aria-selected") === "true");
  if (current < 0) return;
  let next = current;
  if (event.key === "ArrowRight") next = (current + 1) % tabButtons.length;
  else if (event.key === "ArrowLeft") next = (current - 1 + tabButtons.length) % tabButtons.length;
  else return;
  event.preventDefault();
  showTab(tabButtons[next].dataset.tab);
  tabButtons[next].focus();
});

try {
  const saved = sessionStorage.getItem("kshetra-tab");
  if (saved && tabButtons.some((button) => button.dataset.tab === saved)) showTab(saved);
} catch (error) { /* keep the Field tab */ }

refresh();
setInterval(refresh, 2000);
