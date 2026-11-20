const doctorNode = document.getElementById("doctor");
const errorNode = document.getElementById("error");
let busy = false;

function entryLabel(id) {
  if (id === "healthy") return "Healthy";
  if (id === "multiple") return "Mixed";
  const word = String(id || "");
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function showError(message) {
  errorNode.hidden = !message;
  errorNode.textContent = message || "";
}

function render(data) {
  const report = data.report;
  if (doctorNode.dataset.ready !== "1") {
    doctorNode.innerHTML = `
      <p class="empty" id="doctor-empty"></p>
      <div class="doctor-result" id="doctor-result" hidden>
        <div class="result-copy">
          <p class="status" id="doctor-title"></p>
          <ol class="matches" id="doctor-matches"></ol>
          <button type="button" class="btn" id="doctor-add">Add to irrigation</button>
          <p class="note" id="doctor-treatment"></p>
          <p id="doctor-message"></p>
          <p class="note" id="doctor-action"></p>
          <p class="hint" id="doctor-score"></p>
        </div>
      </div>
    `;
    doctorNode.dataset.ready = "1";
  }
  const empty = document.getElementById("doctor-empty");
  const result = document.getElementById("doctor-result");
  if (!report) {
    empty.hidden = false;
    empty.textContent = data.note || "Waiting for a photo.";
    result.hidden = true;
    document.getElementById("doctor-photo").hidden = true;
    return;
  }
  empty.hidden = true;
  result.hidden = false;
  const photo = document.getElementById("doctor-photo");
  photo.hidden = false;
  if (photo.getAttribute("src") !== report.image_url) photo.src = report.image_url;
  document.getElementById("doctor-title").textContent = report.title;
  document.getElementById("doctor-message").textContent = report.farmer_message;
  document.getElementById("doctor-action").textContent = report.recommended_action;
  const matches = document.getElementById("doctor-matches");
  const signature = (report.matches || []).map((item) => `${item.entry_id}:${item.sureness}`).join("|");
  if (matches.dataset.signature !== signature) {
    matches.dataset.signature = signature;
    matches.innerHTML = (report.matches || []).map((item) => `
    <li>
      <span class="match-name">${esc(entryLabel(item.entry_id))}</span>
      <span class="match-bar"><span style="width:${Math.max(0, Math.min(100, Number(item.sureness) || 0))}%"></span></span>
      <span class="match-percent">${esc(item.sureness)}%</span>
    </li>
  `).join("");
  }
  document.getElementById("doctor-score").textContent = report.honesty || data.note || "";
  const treatment = data.treatment || { active: false, note: "" };
  const add = document.getElementById("doctor-add");
  add.dataset.report = String(report.report_id);
  add.disabled = !report.can_treat || treatment.active;
  document.getElementById("doctor-treatment").textContent = treatment.active
    ? `${treatment.treatment_id} · ${treatment.seconds_remaining}s left. ${treatment.note}`
    : "";
}

async function refresh() {
  try {
    const response = await fetch("/api/doctor");
    if (!response.ok) throw new Error("The controller did not answer.");
    render(await response.json());
    showError("");
  } catch (error) {
    showError(error.message);
  }
}

document.getElementById("doctor").addEventListener("click", async (event) => {
  const button = event.target.closest("#doctor-add");
  if (!button || button.disabled || busy) return;
  try {
    busy = true;
    button.disabled = true;
    const response = await fetch("/api/treatments/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report_id: Number(button.dataset.report) }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The treatment could not be added.");
    render(payload);
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

refresh();
setInterval(refresh, 2000);
