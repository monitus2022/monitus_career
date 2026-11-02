"""HK Gov (Labour Dept IES) adapter — build-plan §3.1 / P1 findings.

``fetch()`` pulls server-rendered quickview pages; ``parse(raw_html) -> [Job]``
is a pure function usable with **fixtures only** (Invariant 2: tests never
touch the network).

Real page structure (P1 evidence, docs/probes/P1-hkgov-scoped-search.md):
    div#job_list_table > div.row.item[data-jobcard][data-roworder]
      ├─ div (title, may end in **)
      ├─ .icon_salary   e.g. "$15,000  per month" / "$18,459 - $19,570"
      ├─ .icon_address  e.g. "Kln. Tong" / "Kln. Peninsula"
      └─ .order_no input[type=hidden]  e.g. "23-26-0018344"
Anonymous rows end with "**" (no company published → company stays None).
"""

from __future__ import annotations

import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from ..normalize import map_districts, parse_posted_date, parse_salary
from ..schema import ContractViolation, Job, clean_text

BASE = "https://www2.jobs.gov.hk/0/en"

# Scoped quickview lists (P1 decision: adapters use scoped URLs; the daily run
# budget is ≤10 requests for this source, config.yaml holds the exact set).
DEFAULT_LIST_PATHS = [
    "/jobseeker/jobsearch/quickview/fulltime_epem/",
    "/jobseeker/jobsearch/quickview/fulltime_na/",
]

ANON_MARK = re.compile(r"\*{1,3}\s*$")


def build_list_url(path: str, page: int = 1) -> str:
    return f"{BASE}{path}?direct=False&page={page}"


def parse(raw: str,
          base_url: str = BASE) -> tuple[list[Job], int]:
    """Pure parse of one quickview page HTML → (canonical Jobs, dropped_rows).

    Adapter contract (run.py): per-row contract breaches are skipped and
    counted; the orchestrator applies the systemic rate threshold (§6.5).
    """
    soup = BeautifulSoup(raw, "lxml")
    jobs: list[Job] = []
    dropped = 0
    for row in soup.select("div#job_list_table div.row.item"):
        try:
            jobs.append(_parse_row(row, base_url=base_url))
        except ContractViolation:
            dropped += 1
    return jobs, dropped


def _parse_row(row, base_url: str = BASE) -> Job:
    title_el = row.select_one("div.d-flex.justify-content-between > div")
    salary_el = row.select_one(".icon_salary")
    addr_el = row.select_one(".icon_address")
    ord_el = row.select_one(".order_no input[type=hidden]")
    card_url = row.get("data-jobcard")

    if title_el is None or ord_el is None:
        raise ContractViolation("hkgov row missing title or order_no")

    title_raw = title_el.get_text(" ", strip=True)
    anonymous = bool(ANON_MARK.search(title_raw))
    title = ANON_MARK.sub("", title_raw).strip()

    source_job_id = (ord_el.get("value") or "").strip()
    if not source_job_id:
        raise ContractViolation("hkgov row missing order number")

    salary_raw = clean_text(salary_el.get_text(" ", strip=True)) if salary_el else None
    addr_raw = clean_text(addr_el.get_text(" ", strip=True)) if addr_el else None

    # The quickview list page does not publish employer names; rows whose
    # title ends with "**" are explicitly "company not published". If a
    # future layout adds a company element, pick it up defensively.
    company_el = row.select_one(".icon_company, [data-company]")
    ann_on_el = (company_el.get("data-published") == "false") if company_el else False
    company = (clean_text(company_el.get_text(" ", strip=True))
               if (company_el and not ann_on_el) else None)
    if anonymous:
        company = None

    locations_raw = [addr_raw] if addr_raw else []
    districts, anywhere, region_norm = map_districts(locations_raw)

    smin, smax, speriod = parse_salary(salary_raw)

    url = card_url if card_url else None
    if url and url.startswith("/"):
        # data-jobcard carries an absolute path (starts with /0/...) — join
        # against the origin, not the BASE subtree
        url = f"https://www2.jobs.gov.hk{url}"

    return Job(
        source="hkgov",
        source_job_id=source_job_id,
        title=title,
        company=company,
        salary_raw=salary_raw,
        salary_min=smin, salary_max=smax, salary_period=speriod,
        locations_raw=locations_raw,
        districts=districts,
        anywhere_in_hk=anywhere,
        region_norm=region_norm,
        posted_date_raw=None,  # not published on the list page (§6.2 null)
        posted_date=None,
        url=url,
    ).compute_hashes()


def fetch(session: Any, cap: int = 10, pages: int = 1,
          paths: list[str] | None = None) -> tuple[str, int, int]:
    """LIVE fetch (scripts/daily-run only — never in tests).

    Returns (combined_raw_html, http_requests_made, retries_used). Honors the
    per-source request cap: stops before exceeding it, never silently breaks
    (§2 Invariant 3).
    """
    import time

    paths = paths or DEFAULT_LIST_PATHS
    parts: list[str] = []
    made = 0
    retries_used = 0
    for path in paths:
        for page in range(1, pages + 1):
            if made >= cap:
                break
            url = build_list_url(path, page)
            resp = None
            for attempt in range(3):  # initial + 2 retries (§6.5)
                resp = session.get(url, timeout=30)
                made += 1
                if resp.status_code == 200:
                    break
                if attempt:
                    retries_used += 1
                time.sleep(2 ** attempt)
            if resp is None or resp.status_code != 200:
                break
            parts.append(resp.text)
    return "\n<!--PAGEBREAK-->\n".join(parts), made, retries_used
