/* site/app.js — vanilla JS, no build step (build-plan E4).

Data contract:
  GET /api/jobs            → { jobs: [...records...], generated_at }
  POST /api/jobs/user-state → { job_id, status?, notes?, starred? }
Staleness banner reads the latest run report's finished_at (§6.7).
Never renders full ad copy — headline fields + link out only (privacy).
*/
"use strict";

const $ = (sel) => document.querySelector(sel);
let JOBS = [];
let USER_STATE = { starred: new Set(), status: {}, notes: {} };

async function postUserState(jobId, patch) {
  await fetch("/api/jobs/user-state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId, ...patch }),
  });
}

async function loadData() {
  const res = await fetch("/api/jobs");
  if (!res.ok) { $("#banner").hidden = false; $("#banner").textContent = "data unavailable"; return; }
  const data = await res.json();
  JOBS = data.jobs || [];
  for (const j of JOBS) {
    if (j.starred) USER_STATE.starred.add(j.job_id);
    if (j.status) USER_STATE.status[j.job_id] = j.status;
    if (j.notes) USER_STATE.notes[j.job_id] = j.notes;
  }
  renderBanner(data);
  render();
}

function renderBanner(data) {
  const gen = data.generated_at || (data.jobs || [])[0]?.last_seen_at;
  const days = gen ? Math.floor((Date.now() - new Date(gen)) / 864e5) : null;
  const b = $("#banner");
  if (days !== null && days >= 1) {
    b.hidden = false;
    b.textContent = `data is stale — last successful run ${days} day(s) ago (see runbook)`;
  } else if (days !== null) {
    b.hidden = true;
  }
}

function tierOrder(j) {
  return { A: 0, B: 1, C: 2 }[j.tier] ?? 3;
}
function scoreOrder(j) { return -(j.match_score ?? 0); }
function newness(j) { return -new Date(j.posted_date || j.last_seen_at || 0).getTime(); }

function jobRow(j) {
  const row = document.createElement("div");
  row.className = "job";

  const starred = USER_STATE.starred.has(j.job_id);
  const status = USER_STATE.status[j.job_id] || "";
  const notes = USER_STATE.notes[j.job_id] || "";

  row.innerHTML = `
    <div class="head">
      <a href="${j.url || "#"}" target="_blank" rel="noopener noreferrer">${esc(j.title)}</a>
      <span class="tier-badge tier-${j.tier || "C"}">${esc(j.tier || "-")}</span>
    </div>
    <div class="meta">
      ${["company", "salary_raw", "districts", "posted_date"].map(f => fmtField(j[f])).join(" · ")}
      ${j.match_score != null ? ` · score ${j.match_score}` : ""}
    </div>
    ${j.match_reasons && j.match_reasons.length ?
      `<div class="reasons">${esc(j.match_reasons.join(" · "))}</div>` : ""}
    <div class="actions">
      <button class="star ${starred ? "on" : ""}" title="star">★</button>
      <button class="st-int ${status === "interested" ? "on" : ""}">interested</button>
      <button class="st-app ${status === "applied" ? "on" : ""}">applied</button>
      <button class="st-irr ${status === "irrelevant" ? "on" : ""}">irrelevant</button>
      <input type="text" placeholder="notes…" value="${esc(notes)}">
    </div>`;

  row.querySelector(".star").onclick = (e) => {
    const next = !USER_STATE.starred.has(j.job_id);
    if (next) USER_STATE.starred.add(j.job_id); else USER_STATE.starred.delete(j.job_id);
    e.target.classList.toggle("on", next);
    postUserState(j.job_id, { starred: next });
  };
  for (const [cls, value] of [["st-int", "interested"], ["st-app", "applied"], ["st-irr", "irrelevant"]]) {
    row.querySelector("." + cls).onclick = (e) => {
      USER_STATE.status[j.job_id] = value;   // doubles as a label (G2)
      for (const c of ["st-int", "st-app", "st-irr"]) {
        row.querySelector("." + c).classList.toggle("on", c === cls);
      }
      postUserState(j.job_id, { status: value });
    };
  }
  let notesTimer;
  row.querySelector("input").oninput = (e) => {
    clearTimeout(notesTimer);
    notesTimer = setTimeout(() => {
      USER_STATE.notes[j.job_id] = e.target.value;
      postUserState(j.job_id, { notes: e.target.value });
    }, 500);
  };
  return row;
}

function fmtField(v) {
  if (v == null || v === "") return "";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function render() {
  if (!JOBS.length) { $("#list").innerHTML = "<p>No jobs yet — run the pipeline.</p>"; return; }

  const min = parseInt($("#minScore").value || "0", 10);
  const sort = $("#sortBy").value;
  let view = JOBS.filter(j => (j.match_score ?? 0) >= min
    && (j.deleted_record !== true));
  if (sort === "tier") {
    view = view.slice().sort((a, b) =>
      tierOrder(a) - tierOrder(b) || scoreOrder(a) - scoreOrder(b) ||
      a.title.localeCompare(b.title));
  } else if (sort === "score_new") {
    view = view.slice().sort((a, b) => scoreOrder(a) - scoreOrder(b) || newness(b) - newness(a));
  } else {
    view = view.slice().sort((a, b) => newness(a) - newness(b));
  }

  const list = $("#list");
  list.innerHTML = "";
  if (sort === "tier") {
    const groups = { A: [], B: [], C: [] };
    for (const j of view) (groups[j.tier] || groups.C).push(j);
    for (const t of ["A", "B", "C"]) {
      if (!groups[t].length) continue;
      const h = document.createElement("div");
      h.className = "tier-h";
      h.textContent = `Tier ${t} (${groups[t].length})`;
      list.appendChild(h);
      for (const j of groups[t]) list.appendChild(jobRow(j));
    }
  } else {
    for (const j of view) list.appendChild(jobRow(j));
  }
}

$("#minScore").oninput = render;
$("#sortBy").onchange = render;
loadData();
