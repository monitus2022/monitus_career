# Runbook — failure modes → responses

The daily-run failure policy (§6.5, design doc §9 as summarized by the build
plan). The orchestrator (`pipeline/run.py`) enforces tiers; this page is the
human-readable map.

## Failure → response table

| Symptom | Response |
|---|---|
| `docker info` fails after polling (`launchd/run.sh`, ≤120 s) | Log, alert, exit non-zero; launchd retries next schedule; **no partial writes** |
| Source fetch fails ×2 within a run | 2 retries with backoff per source; if still failing, that source is *failed for the day* (day-level failure countdown), run continues with other sources |
| A source fails on 2 consecutive day-level runs | Alert fires (`alerts.log` + macOS notification), never per-retry |
| Contract failure, per record | Record **dropped + counted** in `contract_failures` (records with `""`/`0`/`N/A` where null intended etc.); LLM fallback hook exists but is OFF (`LLM_FALLBACK=1` + key required) |
| Contract failure, systemic (coverage drop >30 pp vs 7-day baseline on any tracked field, **or** >5 % of a source's records contract-failing) | **Fail the run, write nothing**; staleness banner becomes the visible signal; alert fires; BLOCKERS entry with the diffed-fixture suggestion |
| Playwright/browser-source timeout (Phase F sources) | 2 retries → source skipped + counted; never blocks the plain-HTTP sources |
| `jobs.gov.hk` markup change | Fixture-based regression test pinpoints the selector; fix adapter; add the new capture as the (untracked) regression fixture |
| Embeddings down (ollama missing/dead at run time) | Keyword-only run + `recall_mode=keyword_only` report flag; never fatal |
| Staleness >1 day | Site banner shows N days; humans check `runs/`/`reports/` for the failed date |
| R2 upload fails | Run stays local; retry next scheduled run; banner reflects data age |

## Scheduler

- `launchd/org.monitus.career.plist` fires daily (06:00 HK).
- `launchd/run.sh`: start Docker headlessly if needed → poll `docker info`
  ≤120 s → `caffeinate -i` wrap → `docker compose run pipeline` → exit code.
- Missed-run-then-wake semantics: see `docs/probes/P4-launchd-wake.md`
  (both `StartCalendarInterval` and a `StartInterval` fallback present until
  P4 is measured).
