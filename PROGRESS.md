# PROGRESS.md

Agent-maintained task tracker for the HK Job Engine build.
One line per task — `ID | done|blocked|open | notes`. Seeded at scaffold (A1).

Milestones: M0 ☐ · M1 ☐ · M2 ☐ · M3 ☐ · M4 ☐ · M5 ☐

## Session protocol

Every session starts by reading `PROGRESS.md` + `BLOCKERS.md` and resumes the
first non-done task in dependency order; every session ends by updating this
file (checkboxes, notes, deviations from the design doc).

## Task tracker

| ID | Status | Notes |
|---|---|---|
| H0 | done | plan approved by human in session 1 |
| P1 | done | jobs.gov.hk old grid URL is DEAD; site moved to `www2.jobs.gov.hk/0/` (session 2026-11-01). Scoped server-rendered quickview URLs work: `/0/en/jobseeker/jobsearch/quickview/fulltime_epem/?page=N` (also `fulltime_na/…`). Search-form fields: `simp_JobType/PostTitle/Loc/Inds/SalaryFr/SalaryTo/searchKeyword`, POST endpoints `/api/SimpJobSearch/*` under `g_root=/0`. → adapters use scoped URL lists; no full-sweep fallback needed. Original joblist URL 404s at apex and `/en/joblist/grid/...`; canonical host is `www2.jobs.gov.hk` |
| P2 | done | `mcr.microsoft.com/playwright/python:v1.64.1-noble` pulled & headless render works (example.com). CAVEAT: the pip package `playwright` is MISSING from this tag's image; containers must `pip3 install playwright==1.64.1` (browsers preinstalled under `/ms-playwright`). Pinned in `Dockerfile` |
| P3 | done | unattended Docker start works: `open -g -a Docker` → daemon in ~25 s (engine 28.5.1). Docker Desktop 4.48.0 (<4.89, no boot-prompt caveat) |
| P4 | blocked | needs the human to sleep/wake the Mac once before the 2-min plist test fires. Plist written with both `StartCalendarInterval` + `StartInterval` wake-server fallback; test deferred to H0-follow-up |
| P5 | done | ollama + `nomic-embed-text` present; embedding call works (768-dim, local). Embeddings recall ON |
| P6 | done | **amended during SSR discovery**: the v5 JSON API (`/api/jobsearch/v5/search`) returns the **AU default corpus** even with HK-originating IP/headers — unusable for HK. Workable surface: SSR job list `https://hk.jobsdb.com/jobs?keywords=` serves the HK corpus to plain `requests` (no browser): 30 cards/page with `data-automation="jobTitle/jobCompany/jobLocation/jobListingDate/jobSalary"`. Untracked capture `fixtures/jobsdb_cards.html`; synthetic fixture `fixtures/synthetic/jobsdb_cards.html` committed |
| A1 | done | scaffold complete; matched §3 layout; PROGRESS.md/BLOCKERS.md/runbook/.env.example/profile template created |
| A2 | done | `pipeline/schema.py`: `Job` dataclass, validation, `job_id`/`content_hash` per §6.1, month-equiv constants (hour×8×22, day×22), null semantics, `ContractViolation` |
| A3 | done | `tests/harness.py`: contract checks (required fields, salary/period iff, coverage report helpers) |
| A4 | done | `fixtures/synthetic/`: hkgov_quickview (6 rows incl. day-rate/Kln.Peninsula/geo-trap/anonymous/Negotiable traps), hkgov_broken, jobsdb_cards (6 SSR cards incl. duplicate-pair/Confidential/no-salary traps), jobsdb_broken, ctgoodjobs/recruit cards |
| A5 | done | CI `.github/workflows/ci.yml` (pytest + privacy tripwire), requirements.txt, Dockerfile, docker-compose.yml, wrangler.toml |
| B1 | done | live captures via `scripts/capture_hkgov.py` & `capture_jobsdb.py`: hkgov 20 rows/0 dropped (94 KB), jobsdb SSR 30 rows/0 dropped (1.0 MB). Untracked (privacy) — payloads only 1 request/source |
| B2 | done | adapters `hkgov.py` (quickview HTML), `jobsdb.py` (**rewritten: SSR-card adapter** — v5 JSON unusable for HK, see P6), `ctgoodjobs.py`, `recruit.py`. Each: `parse→(jobs,dropped)` pure + `fetch(session,cap)` live. hkgov URL path-join bug fixed (origin-join, not base-join) |
| B3 | done | tiered failure: per-record violation drop+count; >5 % contract-fail rate fails run & writes nothing (`runs/failures.json` + report) |
| B4 | done | district normalization (alias handling incl. `, X District` suffixes), salary normalization incl. Neg/HK$‑free variants, month-equiv |
| B5 | done | `pipeline/dedupe.py` (`dedupe_key` = company‖title‖district, cluster cross-source), `pipeline/state.py` (seen-set, user-state harvest incl. `last_seen_at` retention clock, 90-day purge) |
| B6 | done | `pipeline/run.py` orchestrator: fetch→parse→dedupe→merge→report→(upload) + `--dry-run` (fixtures replay, zero HTTP, zero personal data) |
| H1 | done | **human approved 2026-11-02** ("lgtm"): 20 sample records reviewed via `docs/h1-sample-records.md`. Live run followed: 70 records (hkgov 40 + jobsdb 30), 3 HTTP requests, 0 contract failures, no personal fields |
| C1 | done | `pipeline/score.py` (tier A/B/C rules on profile) — verified via synthetic; real runs omit `profile.yaml` (H2) so tiers stay null |
| C2 | done | `pipeline/embed.py` (ollama `nomic-embed-text` 768-dim, local-only) — P5 verified; runs in live mode only |
| C3 | done | alerts `pipeline/alert.py` (2 consecutive day failures → local alert), macOS notification via run.sh `osascript` |
| C4 | done | `launchd/run.sh` (daemon poll ≤120 s, caffeinate wrap, double-run guard on today's report) + `org.monitus.career.plist` (06:00 HK + 2 h wake-fallback) |
| C5 | done (blocked) | code complete; the upload step no-ops without CF creds (H3). Verified locally as a no-op |
| H2 | blocked | human fills `profile.yaml` from `profile.yaml.example` |
| D1 | done | dedupe state machine verified via `test_run.py` (update-in-place, star preserved across rebuild, orphan retention) |
| D2 | done | staleness banner data: report `finished_at`/`staleness_days` + site banner (≥1 day old → warn) |
| D3 | done | runbook indexed in `docs/runbook.md` (failure→response map) |
| H3 | blocked | human creates Cloudflare resources per `docs/cloud-bootstrap.md`; blocks E1/E2/E5 + C5-upload |
| E1 | open | blocked on H3 |
| E2 | open | blocked on H3 |
| E3 | done | `functions/api/jobs.js` (GET /api/jobs w/ user-state overlay; POST /api/jobs/user-state w/ field-ownership merge, validation, noindex headers) |
| E4 | done | `site/`: index.html, app.js (tier grouping/sorting/filters, star/interested/applied/irrelevant/notes, staleness banner, escaping), style.css, `_headers` (noindex+CSP), robots.txt (disallow) |
| E5 | open | blocked on H3 (Pages deploy + Access) |
| F1 | open | feature-flagged OFF (no LLM by default — invariant) |
| F2 | open | OFF (same invariant) |
| F3 | open | OFF |
| F4 | open | OFF |
| G1 | done | privacy tripwire `scripts/privacy_tripwire.py` wired into CI |
| G2 | done | status labels double as labels (`interested/applied/irrelevant` in UI + state) |
| G3 | done | `.gitignore` blocks `fixtures/*.html`, `runs*/`, `.env`, `profile.yaml`; untracked captures verified clean of real data |
| G4 | done | docs tree: `docs/probes/P1–P6`, `docs/runbook.md`, `docs/cloud-bootstrap.md`, `docs/h1-sample-records.md` |

## Deviations from design doc

The design doc `hk-job-engine-plan.md` is NOT in the repo — the build-plan doc
quotes enough (§6.1–6.8) to implement verbatim. Where the build plan cites a
*numbered section* of the design doc (§3.x, §4, §5 Traps 1–7, §7, §9), this
build implemented the corresponding build-plan paragraphs and logged the
interpretation in BLOCKERS.md. All naming/grammar of §6.x followed exactly.

## Probe results

See `docs/probes/` for P1–P6.
