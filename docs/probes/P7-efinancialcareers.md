# P7 — eFinancialCareers HK probe (2026-11-02)

**Decision following the probe: DO NOT add it now** (user chose
"jobsdb-only stays minimal"). Recorded so a future session doesn't re-probe.

## Method

2 plain `requests` GETs (read-only, untracked):

```
GET https://www.efinancialcareers.hk/jobs?keywords=python
Headers: UA Chrome-like, Accept-Language: en-HK
```

## Findings

- **SSR works for plain HTTP** (no browser, ~271 KB, HTTP 200).
- Angular pre-rendered cards (`efc-job-card`, `class="job-title"`), and —
  better — a **flat JSON result payload embedded in the HTML**:
  `"jobs":[{job_id, job_title, company_name, job_location, salary,
  destination_url, score, ...}]`.
- 33 results/page, every card structurally identical; salary present on most;
  `"salary → 61` substring hits on page 1.
- No `__NEXT_DATA__`, no anti-bot, no API-auth wrapper needed.

## Why it would be the easiest second source (when/if wanted)

JSON-payload extraction ≪ DOM parsing — the same reason it scored "simplest".
Recommended effort when revived: adapter + capture script + synthetic fixture
+ tests ≈ half a day; +1 request/day. Config: add
`pipeline/config.yaml → sources.efc.enabled` and mirror the jobsdb adapter.

## Why others lose

- **CTgoodjobs**: browser-rendered list; anonymous detail fetches need the
  `ctg-jssid` session cookie (probe in its adapter docstring). Playwright
  every run → violates "no browser wars" operational simplicity.
- **Indeed / Moovup / Glassdoor HK**: anti-bot/captcha surfaces.
- **LinkedIn**: login-walled, GraphQL, ToS-sensitive.

## Request-accounting

2 probe requests total (this session). No captures retained.
