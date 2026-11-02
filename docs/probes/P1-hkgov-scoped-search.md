# P1 — HK Gov scoped search

**Verdict: PASS — scoped URLs work.** No full-sweep fallback needed.

## What changed vs. the build plan's assumptions

The legacy URL `https://jobs.gov.hk/en/joblist/grid/<params>` (and the apex
`jobs.gov.hk` itself via DNS resolution of `www-jobs.4dns.info.gov.hk`) is
**dead** — 404 "Page not found" big5 page. The service now lives at
**`www2.jobs.gov.hk/0/`** (root `https://www.jobs.gov.hk/` JS-redirects to
`/0`), an ASP.NET app, zh-Hant default with `/0/en/` English tree.

## Evidence (requests used ≤20, one-off)

- `GET https://www.jobs.gov.hk/0/` → 200, 196 KB, lands `www2.jobs.gov.hk/0/`
  (title 勞工處互動就業服務).
- Scripts: `/0/Scripts/JobSeeker/simplifed_search.js`, `search_common.js`
  form fields `#simp_JobType`, `#simp_PostTitle`, `#simp_Loc`, `#simp_Inds`,
  `#simp_SalaryFr`, `#simp_SalaryTo`, `#simp_searchKeyword`; form actions
  `POST /0/{tc,en}/jobseeker/jobsearch/simple/` and `.../jobsearch/search/`.
- The documented hidden API exists: `POST {g_root}/api/SimpJobSearch/*`
  (e.g. `ClearSearchForValue`), `POST {g_root}/api/CommonCode/GetCode`.
- `GET /0/en/jobseeker/jobsearch/quickview/fulltime_epem/` → 200, 95 KB,
  **server-rendered job rows** (no JS needed for parsing):

```html
<div class="row item p-1 no-gutters" data-roworder="1"
     data-jobcard="/0/en/jobseeker/jobCard/?order=<base64-id>&from=quickview&for=fulltime_epem">
  <div class="d-flex justify-content-between pb-2">
    <div>Security Guard(Kowloon Tong)**</div>
    <a ... data-ordno="23-26-0018344" ...>
  </div>
  <div class="menu_icon icon_salary pb-2">$15,000  per month</div>
  <div class="menu_icon icon_address pb-2">Kln. Tong</div>
</div>
<div class="order_no d-none"><input type="hidden" value="23-26-0018344" id="ord_no_1"/></div>
```

  Pagination via `?page=N`; per-view sorts via `#sort_order_form`
  (`GET ...?direct=False&page=1`).

## Decision

- Adapters use **scoped server-rendered quickview URL lists** (per-source
  request budget applies). A quickview page parsed by
  `sources/hkgov.py : parse(raw_html)`.
- `source_job_id` = the HK Gov order number (`data-ordno`, e.g.
  `23-26-0018344`) — stable across pages (NOT the per-session base64
  `data-jobcard` blob, which is session/order-dependent).
- Traps confirmed present in the wild: district shorthand `Kln. Tong`
  (§6.4 alias table), `**` suffix = **anonymous/no-company rows** (§6.3).
- `SimpJobSearch` API kept as documented backup if quickviews narrow too far.
