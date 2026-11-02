# monitus_career — HK Job Engine

A private daily job-feed pipeline + minimal UI, built from
`hk-job-engine-build-plan.md` (agent-executable plan; the referenced design
doc quotes exact specs in §6).

- **Pipeline** (`pipeline/`): ≥2 daily-run HTTP adapters (HK Gov, JobsDB),
  contract-tested; deterministic scoring; local embeddings recall (ollama)
  with graceful degradation; dedupe; R2 write-back merge; macOS alerting.
- **Site** (`site/`): single vanilla-JS page served behind Cloudflare Access at
  `career.monitus.org` (data via Pages Function reading R2).
- **Function** (`functions/api/jobs.js`): read `jobs.json` + user-state
  write-back (stars/status/notes) with field-ownership merge.
- **Scheduler**: launchd + Docker (plist in `launchd/`).

## Quickstart (local, no live requests)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest                            # contract tests (fixtures only, no network)
.venv/bin/python -m pipeline.run --dry-run  # end-to-end on captured fixtures
```

## Live daily run

```bash
.venv/bin/python -m pipeline.run            # capped ≤10 req/source, ≤40 total
.venv/bin/python -m pipeline.run --upload   # + R2 upload (requires .env from H3)
```

## Layout

See `hk-job-engine-build-plan.md` §3; task state lives in `PROGRESS.md`,
human checkpoints in `BLOCKERS.md`, fail-book in `docs/runbook.md`.
