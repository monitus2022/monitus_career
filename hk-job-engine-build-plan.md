# HK Job Engine — Build Plan (agent-executable)

**Status:** ready to build
**Source of truth for *why*:** `hk-job-engine-plan.md` (design doc). This file is
the operational plan an autonomous coding agent executes. The design doc is not
modified during the build; discrepancies are logged, not silently "fixed".
**Human involvement:** 5 checkpoints (H0–H4), all short. Everything else is
agent-decided using the defaults in §7.

---

## 1. Autonomy contract

| The agent MAY, without asking | The agent MUST NOT | The human only does (checkpoint) |
|---|---|---|
| Create/modify files inside the project repo | Touch anything outside the repo dir (except its own caches/logs) | H0 — approve this plan |
| Run local tests, builds, docker commands, probe scripts | Fetch any live site except in tasks marked **LIVE**, within the request caps in §4 | H1 — review sample records after M1 (≈30 min) |
| Choose library versions, file layout details, helper structure | Commit any scraped data, fixture *payloads of real personal relevance*, or `jobs.json` to git | H2 — fill `profile.yaml` (irreducible personal input, template provided) |
| Fix bugs, refactor, extend the district alias table from observed data | Enable any LLM/API key path (fallback stays **off**; drop + count instead) | H3 — create Cloudflare resources & paste tokens (checklist provided, ≈20 min) |
| Mark a task blocked → write `BLOCKERS.md` → skip to the next independent task | Change `job_id` / `content_hash` formulas after fixtures exist (one-time migration procedure only, §6.4) | H4 — post-soak review of metrics (≈30 min) |
| Record every assumption-breaking discovery in `PROGRESS.md` | Fetch LinkedIn by any automated means | |

**Blocked-task rule:** if a task is stuck after ~2 focused attempts, write the
obstacle + options into `BLOCKERS.md`, mark it blocked, and continue with
independent work. Never idle-wait on a human.

**Session protocol (multi-session autonomy):** every session starts by reading
`PROGRESS.md` + `BLOCKERS.md` and resumes the first non-done task in dependency
order; every session ends by updating `PROGRESS.md` (checkboxes, notes,
deviations from the design doc).

---

## 2. Global invariants (checked in CI, violated = fail)

1. **No scraped data in git.** `fixtures/` holds captured HTML/JSON *only as
   local untracked files by default*; committed fixtures must be synthetic or
   redacted. CI greps for salary/company patterns in tracked files as a tripwire
   (see A5).
2. **Tests never touch the network.** All adapter tests run against fixtures.
   Live fetching exists only in `scripts/` entry points and LIVE tasks.
3. **Request budget:** the daily run makes **≤10 HTTP requests per source** and
   ≤40 total, logged per run in the report. A run that would exceed the cap must
   stop that source, not silently exceed it.
4. **No LLM anywhere by default.** The parse-fallback hook exists but is
   disabled unless `LLM_FALLBACK=1` + key are set (human opt-in later).
5. **Rank, never filter.** Every normalized record appears in the output with a
   tier; deal-breakers demote, never hide.
6. **Timezone = Asia/Hong_Kong** for all dates and "day" boundaries.
7. **Idempotence:** running the pipeline twice in a day writes the same
   `jobs.json` (no duplicate records, no reset `first_seen_at`).

---

## 3. Repository layout (created in T1.1)

```
monitus-career/           # private repo ~/Documents/Github/monitus-career; served at career.monitus.org
  PROGRESS.md             # task tracker + deviations log (agent-maintained)
  BLOCKERS.md             # obstacles + options (agent-maintained)
  docs/
    probes/               # outputs of P-series tasks (evidence, committed)
    runbook.md            # failure modes → responses (from §9)
  pipeline/
    schema.py  normalize.py  score.py  embed.py  dedupe.py
    report.py  alert.py  state.py     # state.py = R2 seen-set + merge
    sources/hkgov.py  jobsdb.py  ctgoodjobs.py  recruit.py
    run.py                # orchestrator (entry point)
  scripts/                # LIVE probe + capture + upload helpers
  site/                   # index.html + app.js (vanilla JS, no build step)
  functions/api/jobs.js   # Pages Function (read + user-state write-back)
  fixtures/               # captured samples (untracked) + synthetic/ (tracked)
  tests/                  # contract tests, per adapter + per spec in §6
  profile.yaml            # human-filled at H2 (gitignored: contains preferences)
  profile.yaml.example    # committed template
  .env.example  .env      # secrets (`.env` gitignored)
  Dockerfile  docker-compose.yml  launchd/org.monitus.career.plist
  wrangler.toml           # Pages project config
```

`PROGRESS.md` format: one line per task — `ID | done|blocked|open | notes`.
Plus sections: `## Deviations from design doc`, `## Probe results`.

### Naming convention (fixed)

| Artifact | Name |
|---|---|
| Repo (private) / local path | `monitus-career` / `~/Documents/Github/monitus-career` |
| Production domain | `career.monitus.org` — Pages custom domain; the `monitus.org` zone must be on Cloudflare DNS (E1 verifies, migrates if needed) |
| Pages project | `monitus-career` (default preview: `monitus-career.pages.dev`) |
| R2 bucket | `monitus-career-data` — prefixes `jobs.json`, `state/`, `reports/`, `raw/`; never given a custom domain or `r2.dev` URL |
| Access application | `monitus-career` — allow-list: the owner's email only |
| launchd label / plist | `org.monitus.career.pipeline` / `launchd/org.monitus.career.plist` |
| Docker container | `monitus-career-pipeline` |

Accepted tradeoff: the subdomain *name* is semi-public — guessable via DNS
enumeration and visible in certificate-transparency logs (as is
`monitus-career.pages.dev`). Content stays Access-gated; only existence and
purpose leak. If that ever matters (job-hunting while employed), switch to a
neutral subdomain name and rely on a wildcard cert — the design is unaffected.

---

## 4. Phase 0 — environment probes (before any build task)

Each probe writes evidence to `docs/probes/<id>.md` and its outcome to
`PROGRESS.md`. Probes are LIVE but capped and one-off.

| ID | Probe | Method | Decision rule |
|---|---|---|---|
| P1 | **HK Gov scoped search.** Can keywords/districts be passed via URL params on `joblist`? Inspect the page's search form field names; try param combos; also try the documented hidden `SimpJobSearch` API. | Plain HTTP, ≤20 one-off requests | If scoping works → adapters use scoped URLs. If not: fetch `joblist` pages and filter locally — acceptable iff full sweep ≤10 pages; if deeper, `SimpJobSearch` is mandatory → if it fails too, BLOCKERS + design-doc note |
| P2 | **Playwright image.** Pull `mcr.microsoft.com/playwright/python:<latest stable version tag>` (pin the exact tag), run headless `example.com` load. | docker | Works → record tag in `Dockerfile`. Fails on arm64 → try `--platform`, record |
| P3 | **Unattended daemon start.** Quit Docker Desktop, relaunch its binary headlessly, poll `docker info` ≤120 s. | docker CLI | Success → autostart viable. Also record Docker Desktop version; if ≥4.89 note the boot-prompt caveat for H0/H1 awareness |
| P4 | **launchd wake-catch-up.** Install a harmless test plist with `StartCalendarInterval` 2 min ahead, log a touch-file. | launchd | *Requires the human to sleep/wake the Mac once* — bundle this one-line instruction into H0 confirmation. Missed-run-then-wake fires → keep launchd; else switch scheduler to a wake-server `StartInterval` fallback and record |
| P5 | **Ollama/embeddings.** `ollama list`; if missing, `ollama pull nomic-embed-text` (~274 MB); time an embedding call. | ollama | Available → embeddings recall ON. Absent/unwilling to install → keyword-only recall, graceful degradation flag in report |
| P6 | **JobsDB stability.** Re-fetch the v5 endpoint once, diff against the design doc's finding. | 1 request | Structure changed → BLOCKERS + fixtures update. (Then never probe again outside the daily run.) |

No build task starts until P1–P3 conclude (P4–P6 can run parallel/deferred).

---

## 5. Work breakdown

### Phase A — scaffold + data contracts (design §5)

| ID | Task | Acceptance (machine-checkable) |
|---|---|---|
| A1 | Scaffold repo per §3; init git; `PROGRESS.md` seeded from this plan; `.env.example`, `profile.yaml.example`, `docs/runbook.md` skeleton | `git status` clean tracked tree; layout matches §3 |
| A2 | `schema.py`: canonical record dataclass + validation (§6.1–6.3 specs); `null` semantics enforced (`""`/`0` rejected where null intended) | Unit tests incl. rejection cases pass |
| A3 | Adapter contract test harness: required-fields check, `salary_period ∈ {hour,day,month,year}` iff salary set, coverage report generator | Harness runs on a dummy adapter |
| A4 | Synthetic fixtures for all traps (design §5 Traps 1–7): day-rate salary, "Kln. Peninsula", "Central - United States", anonymous HK Gov row, cross-source duplicate pair | Fixtures committed (synthetic), tests reference them |
| A5 | CI: GitHub Actions — pytest + privacy tripwire (Invariant 1) on push | Green run on GitHub |

### Phase B — the two HTTP adapters (design §3.1–3.2, Gate 1)

| ID | Task | Acceptance |
|---|---|---|
| B1 | **LIVE** capture: 1 real fetch each of HK Gov `joblist` + JobsDB v5 → fixtures (untracked) + redacted/synthetic committed versions | Fixture files exist; `content_hash` stable across 2 parses |
| B2 | `sources/hkgov.py` pure `parse(raw) -> [Job]` incl. salary-period parsing, alias-table district mapping (extend table from real data) | Contract tests green on real + synthetic fixtures; ≥80% salary parse coverage on the real capture |
| B3 | `sources/jobsdb.py` (clean JSON; easiest) | same |
| B4 | Field-coverage/null-rate report per source (the drift canary), wired to `report.py` | Report generated for both sources |
| B5 | Tiered failure policy implemented (§6.5): CI breach = fail build; per-record runtime breach = drop + count (+ optional disabled LLM hook); systemic breach (coverage drop >30 pp vs 7-day baseline, or contract-failure rate >5%) = fail run, write nothing | Unit tests simulate all three paths |
| B6 | `dedupe.py`: `dedupe_key`/`cluster_id` per §6.3 spec; HK Gov anonymous rows excluded from clustering | Cross-source duplicate synthetic fixture clusters; anonymous rows don't |

**M1 checkpoint = H1:** agent presents 20 sample normalized records + coverage
report; human sanity-checks realism.

### Phase C — orchestration, Docker, launchd (design §4)

| ID | Task | Acceptance |
|---|---|---|
| C1 | `run.py`: fetch (retry ×2 backoff, per-source cap) → parse → dedupe → upsert state → report → upload; **write-back merge**: read current `jobs.json` from R2, preserve user-state fields by `job_id` (§6.6) | Dry-run against local dir; double-run idempotent (Invariant 7) |
| C2 | `state.py` + `report.py`: seen-set read/write; run report JSON per §6.7 | Report validates against schema |
| C3 | Dockerfile (pin image tag from P2) + compose; run inside container hits local fixtures store | `docker compose run pipeline` end-to-end on captured fixtures |
| C4 | launchd plist + `run.sh` (poll `docker info` ≤120 s, `caffeinate`, alert on failure) per P3/P4 findings | plist loaded; manual trigger produces a full log + report |
| C5 | **LIVE** first real end-to-end daily run (both sources, real upload) | ≤40 requests total logged; `jobs.json` written |

### Phase D — ranking + recall (design §7) → after **H2** (profile.yaml filled)

| ID | Task | Acceptance |
|---|---|---|
| D1 | `score.py`: deterministic scorer per §6.8 (must/nice/exclude, period-adjusted salary floor, districts, seniority regex; tiers A/B/C; deal-breakers demote) | Unit tests on synthetic profile + adversarial postings; ties reproducible |
| D2 | `embed.py`: local embeddings recall (`nomic-embed-text` via ollama), union into candidates before scoring; OFF if P5 failed | top_k=50; latency logged; graceful-off path tested |
| D3 | Ranked output merged into `jobs.json` (`match_score`, `match_reasons[]`) | Site data now carries tiers |

**M2a = H2** sits before D1: human fills `profile.yaml` from the template
(must_have / nice_to_have / exclude / salary floor / districts / seniority).
Agent offers the adjacent-title list as suggestions (optionally one-off LLM if
the human later opts in — default: agent drafts from observed titles).

### Phase E — serving + write-back (design §4, Gate 2)

| ID | Task | Acceptance |
|---|---|---|
| E1 | Cloud bootstrap checklist script + exact H3 instructions (verify `monitus.org` zone is on Cloudflare DNS — migrate if not; R2 bucket `monitus-career-data`; Pages project `monitus-career` + custom domain `career.monitus.org`; Access app; `r2.dev` **disabled**; API tokens into `.env`) | Human executes in ≈20 min; agent verifies via `wrangler whoami` + list; `career.monitus.org` serves the site behind Access |
| E2 | Upload step → R2 `jobs.json`, `raw/<date>/<source>/` (retention: 90 days, purge in daily run) | Objects listed via wrangler; raw purge works |
| E3 | `functions/api/jobs.js`: GET (R2 binding) + POST user-state (star/status/notes) with field-ownership merge | curl through dev server round-trips state; merge preserves pipeline fields |
| E4 | `site/`: single page, vanilla JS: staleness banner (data age from latest report), tier sections, sort by score, star/status buttons, notes field; `_headers` with `X-Robots-Tag: noindex` on all routes + `robots.txt` disallow-all | Manual + E2E via Playwright test against dev server |
| E5 | Deploy pipeline via Actions (tests → `wrangler pages deploy`), secrets as Actions vars | Deploy green; site loads behind Access |

**M2 checkpoint:** human opens the site (H3 completion), stars a few jobs, next
run must preserve them (write-back verified live).

### Phase F — browser sources (design §3.3–3.4)

| ID | Task | Acceptance |
|---|---|---|
| F1 | **LIVE** Playwright discovery for recruit.com.hk search POST (the unresolved ViewState search): capture search results HTML → fixtures | ≥1 real search captured; otherwise BLOCKERS with the fallback: enter search terms via plain detail-page crawl of `MoreSearchResultsOnline.aspx` endpoints from robots map |
| F2 | `sources/recruit.py`: discovery (browser) + detail enrichment (plain HTTP) as separate steps | Contract tests green |
| F3 | `sources/ctgoodjobs.py`: browser-rendered cards; session-token handling per observed 400 headers | 54-link-class fixture parses; coverage report ≥ cards found |
| F4 | Wire both into `run.py` behind per-source feature flags (CT/recruit default ON only after 2 consecutive green runs) | Full 4-source run green twice |

### Phase G — hardening + evaluation (design §6)

| ID | Task | Acceptance |
|---|---|---|
| G1 | Alerting: failure → macOS notification (`osascript`) + `alerts.log` + report flag; trigger on 2 consecutive day-level source failures or systemic breach | Simulated failure fires exactly once (not per retry) |
| G2 | Labeling via the site: `status` values `interested | applied | irrelevant` double as labels; after ≥50 labels, compute precision@20 into the weekly report | Precision@20 report generated |
| G3 | Drift canary baselines (coverage per field per source, 7-day rolling) | Baseline + drop detection tested on synthetic history |
| G4 | `docs/runbook.md` finalized from §9; stale-banner end-to-end test (freeze uploads → banner shows N days) | Banner flips at ≥2 days |

---

## 6. Exact specs (the agent implements these verbatim)

### 6.1 Identity & hashing
- `job_id = sha256(f"{source}|{source_job_id}").hexdigest()[:16]`
- `content_hash` = sha256 of canonical JSON of the **stable published field
  values** — `{title, company, salary_raw, sorted(locations_raw), posted_date_raw, source_job_id}` —
  whitespace-collapsed (`\s+`→" ", trimmed), keys sorted, compact separators.
  *Not* the full HTML (nonces/sessions would make it unstable) and *not* the
  normalized record (schema changes must not re-fire history). Changing the
  formula later = one-time migration: recompute for all existing records and
  treat the diff as "seen", never as "new".

### 6.2 Null semantics
`null` = not published. `""`, `0`, `"N/A"` are contract violations. Salary regex
miss → `salary_min/max/period = null`, `salary_raw` retained verbatim.

### 6.3 Dedupe
`dedupe_key = norm(company) || "||" || norm(title) || "||" || region_norm`
- `norm()`: casefold, collapse whitespace, strip punctuation except `&`, drop
  company suffixes {ltd, limited, co, company, inc, llc, hk, hong kong}.
- `region_norm`: first mapped district from the alias table, else `"unknown"`.
- Cluster only when `company` is non-null (design trap 6). Merge rule:
  require **all three** parts equal (false merge is worse than a miss).

### 6.4 Districts
18 official HK districts + `anywhere_in_hk` bool. Initial aliases:
`Anywhere in H.K.`, `Any district`, `HK-wide` → anywhere; `Kln. Peninsula` →
no single district (leave `districts[]` empty, keep the raw location). Agent
extends the table from observed data during B2 — that extension is autonomous.

### 6.5 Failure policy (tiered)
- **CI:** fixture contract breach → fail build.
- **Runtime, per record:** breach → drop, count in `contract_failures`
  (+ `llm_fallback` hook, disabled unless explicitly enabled).
- **Runtime, systemic:** coverage drop >30 percentage points vs 7-day baseline
  on any tracked field, or contract-failure rate >5% of a source's records →
  **fail the run, write nothing**; staleness banner becomes the visible signal;
  alert fires.
- **Fetch:** 2 retries with backoff per source within the run; source failure on
  2 consecutive day-level runs → alert (not per-retry).

### 6.6 Write-back ownership (merge before upload)
Pipeline owns all source-derived + computed fields. Function owns
`status`, `notes`, `starred`. Daily: read live `jobs.json`, overlay user-state
onto rebuilt records by `job_id`; records absent from the rebuild keep their
user state until purged after 90 days.

### 6.7 Run report (`reports/<date>.json`, also local `runs/`)
`{run_id, started_at, finished_at, sources: {<name>: {fetch_ok, retries,
http_requests, records_fetched, records_parsed, records_written,
contract_failures, null_rates{field: pct}}}, totals{...}, alerts[],
staleness_days}` — the staleness banner and drift canary read this.

### 6.8 Scoring (deterministic, from `profile.yaml`)
```
score = 3·|must_have hits| + 1·|nice_to_have hits|
      + 2·(salary floor cleared, period-adjusted) + 1·(district ∈ preferred)
deal_breakers = exclude-keyword hits | salary floor breach | seniority out-of-band (regex)
salary→month equivalent: day × 22, hour × 8 × 22   (constants documented)
tiers: A = no deal-breaker ∧ score ≥ 8 · B = 4 ≤ score < 8 · C = score < 4 ∨ any deal-breaker
```
All postings shown, sorted tier→score. Site renders headline fields + link out;
never full ad copy (privacy invariant).

---

## 7. Defaults for previously-open decisions (design §9)

| Decision | Default chosen (agent-implemented; human can override at H-checkpoints) |
|---|---|
| Repo | `~/Documents/Github/monitus-career`, **private** (full naming table: §3) |
| `profile.yaml` | Template at A1; human fills at H2; agent drafts candidate keywords from observed titles |
| Raw archive retention | 90 days, purge step in the daily run |
| Alert channel | macOS notification + `alerts.log`; email deferred until the human asks |
| LLM fallback | **Off** by default; hook present; enabling = human opt-in with key |
| Embeddings | ON iff P5 succeeds; else keyword-only degradation |
| CT/recruit rollout | Feature-flagged; enabled after 2 consecutive green runs (F4) |

---

## 8. Milestones & human checkpoints

| Milestone | Contains | Human touch |
|---|---|---|
| **M0** | P1–P3 concluded | (H0 done at approval; P4 needs one sleep/wake) |
| **M1** = Gate 1 | Phases A–C: two adapters, contracts, Docker+launchd, first real run | **H1:** review 20 sample records + coverage report (~30 min) |
| **M2** = Gate 2 | Phases D–E: ranked site, R2/Pages/Access, write-back | **H2:** fill profile.yaml (~30 min) · **H3:** cloud bootstrap (~20 min) |
| **M3** | Phase F: browser sources live | none |
| **M4** | Phase G: alerts, canary, labeling/precision | occasional site labeling (clicks during normal triage) |
| **M5** = soak | 7 consecutive unattended daily runs | **H4:** review metrics (~30 min) |

## 9. Definition of done

1. 7 consecutive daily runs unattended, staleness ≤1 day every day.
2. ≤40 HTTP requests/run logged; zero scraped bytes in git (tripwire green).
3. One alert path demonstrated on a simulated failure; one write-back survived
   a rebuild (stars preserved).
4. Precision@20 ≥70% on ≥50 labels (via site clicks), or a documented iteration
   plan in `PROGRESS.md`.
5. User-reported triage ≤15 min/day.

## 10. Runbook (failure → agent response)

| Symptom | Response |
|---|---|
| `docker info` fails after polling | Log, alert, exit non-zero; launchd retries next schedule; no partial writes |
| Source fetch fails ×2 (day-level) | Alert fires; that source's records go stale naturally; run continues with others |
| Coverage collapse / systemic breach | Fail run before write; banner shows gap; BLOCKERS entry with the diffed fixture suggestion |
| Playwright timeout on browser source | 2 retries → source skipped + counted; never blocks the plain-HTTP sources |
| `jobs.gov.hk` markup change | Fixture-based regression test pinpoints the selector; fix adapter; add the new capture as fixture |
| Embeddings down (ollama) | Keyword-only run + report flag; never fatal |

## 11. Progress tracker

Mirrored in `PROGRESS.md` at scaffold time (A1). Agent updates per session.
Milestones: M0 ☐ · M1 ☐ · M2 ☐ · M3 ☐ · M4 ☐ · M5 ☐
