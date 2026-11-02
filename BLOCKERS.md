# BLOCKERS.md

## B-1 — design doc missing
The design doc `hk-job-engine-plan.md` (source of truth for *why*; §5
"Traps 1–7" referenced by build-plan A4) is not in the repo.
**Options:** (a) commit the design doc if the human still has it locally;
(b) treat build-plan §6 as the spec (currently implemented).
**Impact:** build-plan §6 specs were implemented verbatim; the 2 of the 7
"traps" not named in A4 are un-matched — implemented the obvious pair
(null/neg semester salary + within-source duplicate) as best guess.
Note: the two captures from `B1` fixtures lived up to contract; no material
behavioural difference observed so far.

## B-2 — repo name/path mismatch
Build plan §3/§7 names the repo `monitus-career` and path
`~/Documents/Github/monitus-career`. Actual repo (remote already configured)
is `monitus-career` at `~/Documents/Github/monitus_career`
(↑ underscore, not hyphen).
**Options:** (a) rename (GitHub rename is namespace-wide, cheap but
human-visible); (b) keep as-is since `career.monitus.org` (Pages custom
domain) is unaffected. **Chosen default:** keep as-is; human can override at
any checkpoint.

## B-3 — Cloud bootstrap needs human (H3)
R2 bucket, Pages project + custom domain, Access allow-list, and API tokens
are H3 tasks. The pipeline implementation side (upload/merge code paths) is
complete and unit-tested against mocks; the checkpoint blocks end-to-end
E1/E2/C5/E5. Checklist: `docs/cloud-bootstrap.md`.

## B-4 — launchd wake-catch-up needs human (P4/H0-follow-up)
The 2-min-into-the-future plist requires the human to sleep/wake the Mac once.
Plist ships with both `StartCalendarInterval` and a `StartInterval`
wake-fallback; the decision (which to keep) is recorded once the human
runs the one-line test in `docs/cloud-bootstrap.md` §5.

## B-5 — JobsDB v5 API returns the AU corpus (P6 amendment; resolved)
`/api/jobsearch/v5/search` never scoped to HK (verified: HK-origin IP + headers
+ locale params all still served Sydney listings). **Resolved** by switching
the adapter to the SSR job list (`https://hk.jobsdb.com/jobs?keywords=…`),
which serves the HK corpus to plain `requests` — 30 cards/page,
`data-automation="jobTitle|jobCompany|jobLocation|jobListingDate|jobSalary"`.
Live capture (untracked): `fixtures/jobsdb_cards.html` (1 MB,
30 rows parsed / 0 dropped). No browser needed at all; P2's Docker
Playwright image stays available for future JS-only surfaces.

## B-6 — H1 payload review (RESOLVED 2026-11-02)
Human reviewed `docs/h1-sample-records.md` and approved ("lgtm"). The first
real live run followed: 70 records (hkgov 40 + jobsdb 30), 3 HTTP requests,
0 contract failures. Adapters confirmed on live data.

## B-7 — Access gating not yet observed (H3 follow-up)
`GET https://career.monitus.org` and `GET /api/jobs` return 200 without an
Access challenge — no Cloudflare Access application protects the domain (or
its policy currently bypasses anonymous visitors). The site still carries
noindex/nofollow + robots disallow; risk is limited to strangers seeing the
job list + being able to POST user-state junk. Remedy: create a Zero Trust
Access app for `career.monitus.org/*` (+ the pages.dev host), policy allow
owner email only. Then re-verify: anonymous `curl -I` should yield 302 →
`<team>.cloudflarersaccess.com` style login.

## B-8 — R2 upload creds missing from `.env` (H3 tail)
Bucket, Pages, binding, domain all verified live — the only missing piece is
the API token inside `.env` (`CF_ACCOUNT_ID`, `CF_API_TOKEN`,
`R2_BUCKET=monitus-career-data`). Upload path is now a plain REST PUT from
the pipeline (no wrangler needed). Once `.env` is filled:
`PYTHONPATH=. .venv/bin/python -m pipeline.run --dry-run --upload` fills the
site instantly (replays today's captures, no new HTTP requests).
