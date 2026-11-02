"""JobsDB adapter — build-plan §3.2, updated per P6 *role* of the source.

DEVIATION from the design doc (logged in PROGRESS.md): the v5 JSON
``/api/jobsearch/v5/search`` returns the AU default corpus even for
HK-originating requests (no siteId/locale combination scoped it to HK;
verified in the P6 follow-up + browser capture). The SSR job-list page
however serves the HK corpus to plain HTTP requests:

    GET https://hk.jobsdb.com/jobs?keywords=<kw>
    → 200, ~1 MB HTML, server-rendered card list:
        div[data-automation="normalJob"] per listing, containing
        data-automation="jobTitle / jobCompany / jobLocation / jobListingDate
        / jobSalary / jobShortDescription / jobClassification".

`parse(raw_html) -> (jobs, dropped)` is pure (fixtures only in tests).
"""

from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from ..normalize import map_districts, parse_salary, parse_posted_date
from ..schema import ContractViolation, Job, clean_text

BASE = "https://hk.jobsdb.com"
DEFAULT_LISTS = ["/jobs?keywords=python&locale=en"]  # config.yaml scopes this
ORIGIN = "https://hk.jobsdb.com"


def _auto(el, name: str):
    return el.find(attrs={"data-automation": name})


def parse(raw: str, base_url: str = BASE) -> tuple[list[Job], int]:
    """Pure parse of the SSR job-list HTML → (canonical Jobs, dropped_rows)."""
    soup = BeautifulSoup(raw, "lxml")
    jobs: list[Job] = []
    dropped = 0
    for card in soup.find_all(attrs={"data-automation": "normalJob"}):
        try:
            jobs.append(_parse_card(card))
        except ContractViolation:
            dropped += 1
    return jobs, dropped


def _parse_card(card) -> Job:
    title_el = _auto(card, "jobTitle")
    title = clean_text(title_el.get_text(" ", strip=True)) if title_el else None
    if not title:
        raise ContractViolation("jobsdb card missing title")

    comp_el = _auto(card, "jobCompany")
    company = clean_text(comp_el.get_text(" ", strip=True)) if comp_el else None
    if company and company.casefold() in {"confidential", "confidential company"}:
        company = None

    loc_el = _auto(card, "jobLocation")
    loc_raw = clean_text(loc_el.get_text(" ", strip=True)) if loc_el else None
    locs_raw = [loc_raw] if loc_raw else []
    districts, anywhere, region_norm = map_districts(_un_district(locs_raw))

    sal_el = _auto(card, "jobSalary")
    sal_raw = clean_text(sal_el.get_text(" ", strip=True)) if sal_el else None
    smin, smax, speriod = parse_salary(sal_raw)

    date_el = _auto(card, "jobListingDate")
    posted_raw = clean_text(date_el.get_text(" ", strip=True)) if date_el else None
    # SSR shows relative dates ("Today", "2d ago"); ISO only when absolute
    posted_date = parse_posted_date(posted_raw) if posted_raw else None
    if posted_date is None:
        posted_date = None  # relative dates stay raw (idempotent-safe)

    a = card.find("a", href=True)
    url = None
    if a and a["href"].startswith("/"):
        url = f"{ORIGIN}{a['href']}"

    return Job(
        source="jobsdb",
        # SSR card does not carry a separate listing id; the url slug is the id
        source_job_id=_extract_job_id(a["href"]) if a and a["href"] else title,
        title=title,
        company=company,
        salary_raw=sal_raw,
        salary_min=smin, salary_max=smax, salary_period=speriod,
        locations_raw=locs_raw,
        districts=districts,
        anywhere_in_hk=anywhere,
        region_norm=region_norm,
        posted_date_raw=posted_raw,
        posted_date=posted_date,
        url=url,
    ).compute_hashes()


def _extract_job_id(href: str) -> str:
    import re
    m = re.search(r"/job/(\d+)", href)
    if m:
        return m.group(1)
    # last resort: hash the path (stable within a day)
    import hashlib
    return "slug-" + hashlib.sha256(href.encode()).hexdigest()[:12]


def _un_district(locs: list[str]) -> list[str]:
    """Locations like 'Central, Central and Western District' → strip the
    official-district suffix (the suffix itself is the alias table's job)."""
    out = []
    for s in locs:
        out.append(s.replace(", Central and Western District", "")
                   .replace(", Southern District", "")
                   .replace(", Sham Shui Po District", "")
                   .replace(", Sha Tin District", ""))
    return out


def fetch(session: Any, keyword: str = "",
          pages: int = 1, cap: int = 10) -> tuple[list[str], int, int]:
    """LIVE fetch (daily-run only). One request per page of results.

    SSR pages serve the HK corpus to this HK IP; no browser needed.
    """
    import time

    parts: list[str] = []
    made = 0
    retries_used = 0
    for page in range(1, pages + 1):  # SSR URL params support ?page=N
        if made >= cap:
            break
        url = f"{BASE}/jobs?keywords={keyword}&page={page}"
        resp = None
        for attempt in range(3):  # initial + 2 retries
            resp = session.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"),
                    "Accept-Language": "en-HK,en;q=0.9",
                },
                timeout=40,
            )
            made += 1
            if resp.status_code == 200 and 'data-automation="jobTitle"' in resp.text:
                break
            if attempt:
                retries_used += 1
            time.sleep(2 ** attempt)
        if resp is None or resp.status_code != 200:
            break
        parts.append(resp.text)
    return parts, made, retries_used
