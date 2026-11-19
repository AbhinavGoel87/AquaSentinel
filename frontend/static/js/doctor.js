const doctorNode = document.getElementById("doctor");
const errorNode = document.getElementById("error");
let busy = false;

function entryLabel(id) {
  if (id === "healthy") return "Healthy";
  if (id === "multiple") return "Mixed";
  const word = String(id || "");
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function percentColor(sureness, entryId) {
  let amount = Math.max(0, Math.min(100, Number(sureness) || 0)) / 100;
  if (entryId === "healthy") amount = 1 - amount;
  amount *= amount;
  const green = [31, 110, 58];
  const red = [141, 36, 36];
  const mix = green.map((channel, index) => Math.round(channel + (red[index] - channel) * amount));
  return `rgb(${mix.join(", ")})`;
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
        <img id="doctor-photo" alt="Latest plant photo">
        <div class="result-copy">
          <p class="status" id="doctor-title"></p>
          <ol class="matches" id="doctor-matches"></ol>
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
    return;
  }
  empty.hidden = true;
  result.hidden = false;
  const photo = document.getElementById("doctor-photo");
  if (photo.getAttribute("src") !== report.image_url) photo.src = report.image_url;
  document.getElementById("doctor-title").textContent = report.title;
  document.getElementById("doctor-message").textContent = report.farmer_message;
  document.getElementById("doctor-action").textContent = report.recommended_action;
  const matches = document.getElementById("doctor-matches");
  matches.innerHTML = (report.matches || []).map((item) => `
    <li>
      <span class="match-name">${esc(entryLabel(item.entry_id))}</span>
      <span class="match-percent" style="color:${percentColor(item.sureness, item.entry_id)}">${esc(item.sureness)}%</span>
    </li>
  `).join("");
  document.getElementById("doctor-score").textContent = report.honesty || data.note || "";
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

document.getElementById("photo-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  const file = document.getElementById("photo-file").files[0];
  if (!file) return;
  const body = new FormData();
  body.append("image", file);
  body.append("source", "hardware");
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
