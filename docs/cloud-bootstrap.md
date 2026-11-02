# Cloud bootstrap — H3 checklist (human, ~20 min)

Everything below is human-only (H3). The agent verifies each step
automatically where a CLI check exists. Fill `.env` as you go (from
`.env.example`).

## 1. Cloudflare account & zone
- [ ] Sign in to Cloudflare (account: existing owner account).
- [ ] Add the domain **monitus.org** to Cloudflare if it isn't there already.
- [ ] Point the registrar's nameservers at Cloudflare if migrating.
- *Agent verify:* `wrangler whoami` + `wrangler dns list zones` if the CLI
  supports it — or just tell the agent; it will re-check with `curl`.

## 2. R2 bucket
- [ ] Create (or confirm) R2 bucket **`monitus-career-data`**.
- [ ] Leave **both** public access options OFF (no custom domain, no
      `r2.dev` — the naming table forbids public exposure).
- *Agent verify:* `wrangler r2 bucket list` shows it.

## 3. Pages project + custom domain
- [ ] Create Pages project **`monitus-career`** (direct upload, not git, or
      connect the repo — either way).
- [ ] Wire the custom domain **`career.monitus.org`** → Pages custom domain.
- [ ] DNS: create the `career` CNAME → `<project>.pages.dev`.
- *Agent verify:* `curl -I https://career.monitus.org` after first deploy.

## 4. Access (gating)
- [ ] Create a Zero Trust (Access) application **`monitus-career`** for
      `career.monitus.org/*` (and `*.monitus-career.pages.dev/*` if you want
      previews gated too). Allow-list: your email only.
- [ ] Policy: allow `emails: <owner email>`; everything else denied.

## 5. launchd wake test (P4 — takes 1 minute, no password)
When convenient, run this then **put the Mac to sleep and wake it once**:
```zsh
mkdir -p ~/Library/LaunchAgents
cp launchd/org.monitus.career.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/org.monitus.career.plist
# (sleep/wake now), then check runs/launchd.out
launchctl list | grep monitus
```
Tell the agent whether the wake test fired; it will record P4 and can trim
the `StartInterval` fallback.

## 6. API tokens (paste into `.env`)
- [ ] R2 token → read+write objects on `monitus-career-data`.
- [ ] Pages token (only if the agent should deploy; else the human deploys).
- [ ] Fill `.env` sections (see `.env.example`):
```ini
CF_ACCOUNT_ID=<account id>
CF_API_TOKEN=<r2 token>
R2_BUCKET=monitus-career-data
```
Then the agent can run `wrangler r2 object put ...` from the daily run
upload step (run.py `_upload()`).

## 7. Agent verification steps (run after 1–6)
```zsh
set -a; source .env; set +a
wrangler whoami
wrangler r2 bucket list            # → monitus-career-data present
wrangler r2 object list monitus-career-data --prefix "" | head
.venv/bin/python -m pipeline.run --upload   # writes + uploads today's jobs.json
curl -sI https://career.monitus.org/api/jobs | head
```
Expect: `200`, an Access redirect otherwise. Report any failure to the agent
in plain words; the runbook (`docs/runbook.md`) has the failure→response map.
