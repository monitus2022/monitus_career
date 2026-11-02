// functions/api/jobs.js — Cloudflare Pages Function (E3)
//
// GET  /api/jobs               → { jobs: [...], generated_at }
//                                  GETs jobs.json (+user_state overlay) from R2.
// POST /api/jobs/user-state    → user-state write-back with field-ownership
//                                  merge (build-plan §6.6).
//
// Field ownership (§6.6): the pipeline owns all source-derived + computed
// fields; this Function (and the site UI) own `status`, `notes`, `starred`
// only. User-state lives in R2 at `state/user_state.json`, keyed by job_id,
// so the daily pipeline rebuild can merge it in and never clobber user data.


// R2 binding: DATA (bucket `monitus-career-data`) — configured in wrangler.toml
const USER_STATE_KEY = "state/user_state.json";
const JOBS_KEY = "jobs.json";

const OWNED_FIELDS = ["status", "notes", "starred"];
const VALID_STATUS = new Set(["interested", "applied", "irrelevant"]);

async function readUserState(env) {
  const obj = await env.DATA.get(USER_STATE_KEY);
  if (!obj) return {};
  try {
    const parsed = JSON.parse(await obj.text());
    return (parsed && typeof parsed === "object") ? parsed : {};
  } catch {
    return {};
  }
}

async function writeUserState(env, state) {
  // never given a custom domain or r2.dev URL — objects are private
  await env.DATA.put(
    USER_STATE_KEY,
    JSON.stringify(state, null, 1),
    { httpMetadata: { contentType: "application/json" } },
  );
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "X-Robots-Tag": "noindex, nofollow",
      "Cache-Control": "no-store",
    },
  });
}

// ------------------------------------------------------------------ GET

export async function onRequestGet({ env }) {
  const [jobsObj, userStateObj] = await Promise.all([
    env.DATA.get(JOBS_KEY),
    readUserState(env),
  ]);
  if (!jobsObj) {
    return json({ jobs: [], generated_at: null }, 200);
  }
  const payload = JSON.parse(await jobsObj.text());
  const jobs = Array.isArray(payload) ? payload : (payload.jobs || []);
  // overlay user state per job_id (function owns these fields)
  for (const j of jobs) {
    const st = userStateObj[j.job_id];
    if (st) {
      for (const f of OWNED_FIELDS) {
        if (st[f] !== undefined) j[f] = st[f];
      }
    }
  }
  return json({ jobs, generated_at: jobsObj.customTime || null });
}

// ------------------------------------------------------------------ POST

export async function onRequestPost({ env, request }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "invalid JSON body" }, 400);
  }
  const jobId = body && String(body.job_id || "").trim();
  if (!jobId) return json({ error: "job_id required" }, 400);
  if (!/^[a-f0-9]{16}$/.test(jobId)) return json({ error: "bad job_id" }, 400);

  const patch = {};
  if (body.status !== undefined) {
    if (!VALID_STATUS.has(body.status)) {
      return json({ error: "status must be interested|applied|irrelevant" }, 400);
    }
    patch.status = body.status;
  }
  if (body.notes !== undefined) {
    if (typeof body.notes !== "string" || body.notes.length > 500) {
      return json({ error: "notes must be a ≤500-char string" }, 400);
    }
    patch.notes = body.notes;
  }
  if (body.starred !== undefined) {
    if (typeof body.starred !== "boolean") {
      return json({ error: "starred must be boolean" }, 400);
    }
    patch.starred = body.starred;
  }
  if (!Object.keys(patch).length) {
    return json({ error: "no user-owned fields (status/notes/starred)" }, 400);
  }

  const state = await readUserState(env);
  const existing = state[jobId] || {};
  // ownership merge: only owned fields accepted from user; pipeline fields
  // can never be smuggled in through this endpoint
  state[jobId] = { ...existing, ...patch };
  await writeUserState(env, state);
  return json({ ok: true, job_id: jobId, state: state[jobId] });
}
