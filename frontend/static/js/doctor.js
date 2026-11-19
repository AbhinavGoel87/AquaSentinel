const doctorNode = document.getElementById("doctor");
const errorNode = document.getElementById("error");
let busy = false;

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
        <p class="status" id="doctor-title"></p>
        <p id="doctor-message"></p>
        <p class="note" id="doctor-action"></p>
        <p class="hint" id="doctor-score"></p>
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
  document.getElementById("doctor-score").textContent = `Closest match ${report.match_score}. ${report.honesty || data.note || ""}`;
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
