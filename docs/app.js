const STATUS_OPTIONS = ["new", "shortlisted", "applied", "interview", "rejected"];
const STATUS_LABELS = {
  new: "New", shortlisted: "Shortlisted", applied: "Applied",
  interview: "Interview", rejected: "Rejected",
};

let allJobs = [];
let statusMap = {};
let activeMarkets = new Set();

const $ = (sel) => document.querySelector(sel);
const jobListEl = $("#job-list");
const searchEl = $("#search");
const statusFilterEl = $("#status-filter");
const minScoreEl = $("#min-score");
const sortByEl = $("#sort-by");
const hideRejectedEl = $("#hide-rejected");
const marketChipsEl = $("#market-chips");
const toastEl = $("#toast");

function showToast(message, isError) {
  toastEl.textContent = message;
  toastEl.className = "toast" + (isError ? " error" : "");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toastEl.classList.add("hidden"), 4000);
}

function apiConfigured() {
  return typeof API_BASE_URL === "string" && API_BASE_URL.trim().length > 0;
}

async function loadData() {
  const [jobsResp, statusResp] = await Promise.all([
    fetch("jobs.json", { cache: "no-store" }),
    fetch("status.json", { cache: "no-store" }).catch(() => null),
  ]);
  const jobsData = await jobsResp.json();
  allJobs = jobsData.jobs || [];
  $("#generated-at").textContent = jobsData.generated_at
    ? "Updated " + new Date(jobsData.generated_at).toLocaleString()
    : "";

  statusMap = {};
  if (statusResp && statusResp.ok) {
    try {
      const statusData = await statusResp.json();
      statusMap = statusData || {};
    } catch (e) { /* status.json may not exist yet */ }
  }

  const markets = [...new Set(allJobs.map((j) => j.market))];
  activeMarkets = new Set(markets);
  marketChipsEl.innerHTML = "";
  markets.forEach((m) => {
    const label = allJobs.find((j) => j.market === m)?.market_label || m;
    const chip = document.createElement("div");
    chip.className = "chip active";
    chip.textContent = label;
    chip.dataset.market = m;
    chip.setAttribute("role", "button");
    chip.setAttribute("tabindex", "0");
    chip.setAttribute("aria-pressed", "true");
    const toggle = () => {
      if (activeMarkets.has(m)) { activeMarkets.delete(m); chip.classList.remove("active"); }
      else { activeMarkets.add(m); chip.classList.add("active"); }
      chip.setAttribute("aria-pressed", String(activeMarkets.has(m)));
      render();
    };
    chip.addEventListener("click", toggle);
    chip.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
    });
    marketChipsEl.appendChild(chip);
  });

  render();
}

function statusOf(jobId) {
  return (statusMap[jobId] && statusMap[jobId].status) || "new";
}

function render() {
  const q = searchEl.value.trim().toLowerCase();
  const minScore = Number(minScoreEl.value) || 0;
  const statusFilter = statusFilterEl.value;
  const hideRejected = hideRejectedEl.checked;
  const sortBy = sortByEl.value;

  let jobs = allJobs.filter((j) => {
    if (!activeMarkets.has(j.market)) return false;
    if (j.score < minScore) return false;
    const st = statusOf(j.id);
    if (statusFilter && st !== statusFilter) return false;
    if (hideRejected && !statusFilter && st === "rejected") return false;
    if (q && !(j.title.toLowerCase().includes(q) || j.company.toLowerCase().includes(q))) return false;
    return true;
  });

  jobs.sort((a, b) => {
    if (sortBy === "score") return b.score - a.score;
    if (sortBy === "distance") {
      const da = a.distance_km ?? Infinity, db = b.distance_km ?? Infinity;
      return da - db;
    }
    if (sortBy === "date") return (b.date_posted || "").localeCompare(a.date_posted || "");
    if (sortBy === "first_seen") return (b.first_seen || "").localeCompare(a.first_seen || "");
    return 0;
  });

  $("#job-count").textContent = `${jobs.length} job${jobs.length === 1 ? "" : "s"}`;

  jobListEl.innerHTML = "";
  if (jobs.length === 0) {
    jobListEl.innerHTML = '<p class="empty">No jobs match these filters.</p>';
    return;
  }
  jobs.forEach((j) => jobListEl.appendChild(renderCard(j)));
}

function renderCard(j) {
  const card = document.createElement("div");
  card.className = "card";

  const badges = [`<span class="badge market">${escapeHtml(j.market_label)}</span>`];
  if (j.distance_km != null) badges.push(`<span class="badge distance">📍 ~${Math.round(j.distance_km)}km</span>`);
  if (j.matched_visa) badges.push(`<span class="badge visa">💼 visa/relocation</span>`);
  if (j.date_posted) badges.push(`<span class="badge">${escapeHtml(j.date_posted)}</span>`);

  const skills = (j.matched_skills || []).slice(0, 6).join(", ");

  card.innerHTML = `
    <div class="card-top">
      <div class="card-title"><a href="${escapeAttr(j.url)}" target="_blank" rel="noopener">${escapeHtml(j.title)}</a></div>
      <div class="score-badge">${j.score}</div>
    </div>
    <div class="card-sub">${escapeHtml(j.company)} — ${escapeHtml(j.location || "")}</div>
    <div class="badge-row">${badges.join("")}</div>
    ${skills ? `<div class="skills">Matches: ${escapeHtml(skills)}${j.matched_role ? ", " + escapeHtml(j.matched_role) : ""}</div>` : ""}
    <div class="card-actions">
      <a class="btn" href="${escapeAttr(j.url)}" target="_blank" rel="noopener">View listing</a>
      <button class="btn primary" data-action="generate-cv">Generate CV</button>
      <span class="status-select">
        <select data-action="status">
          ${STATUS_OPTIONS.map((s) => `<option value="${s}" ${s === statusOf(j.id) ? "selected" : ""}>${STATUS_LABELS[s]}</option>`).join("")}
        </select>
      </span>
    </div>
  `;

  card.querySelector('[data-action="status"]').addEventListener("change", (e) => updateStatus(j, e.target.value));
  card.querySelector('[data-action="generate-cv"]').addEventListener("click", (e) => generateCv(j, e.target));

  return card;
}

async function updateStatus(job, newStatus) {
  if (!apiConfigured()) {
    showToast("Backend not configured yet — set API_BASE_URL in config.js", true);
    render();
    return;
  }
  try {
    const resp = await fetch(`${API_BASE_URL}/api/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: job.id, status: newStatus }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    statusMap[job.id] = { status: newStatus, updated_at: new Date().toISOString() };
    showToast(`${job.title} → ${STATUS_LABELS[newStatus]}`);
  } catch (err) {
    showToast("Couldn't update status: " + err.message, true);
  }
}

async function generateCv(job, buttonEl) {
  if (!apiConfigured()) {
    showToast("Backend not configured yet — set API_BASE_URL in config.js", true);
    return;
  }
  const originalText = buttonEl.textContent;
  buttonEl.disabled = true;
  buttonEl.textContent = "Generating…";
  try {
    const resp = await fetch(`${API_BASE_URL}/api/generate_cv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: job.id }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `CV_${(job.company || "job").replace(/[^a-z0-9]+/gi, "_")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showToast("CV downloaded for " + job.title);
  } catch (err) {
    showToast("CV generation failed: " + err.message, true);
  } finally {
    buttonEl.disabled = false;
    buttonEl.textContent = originalText;
  }
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

[searchEl, statusFilterEl, minScoreEl, sortByEl, hideRejectedEl].forEach((el) =>
  el.addEventListener("input", render)
);

loadData().catch((err) => {
  jobListEl.innerHTML = `<p class="empty">Couldn't load jobs.json: ${escapeHtml(err.message)}</p>`;
});
