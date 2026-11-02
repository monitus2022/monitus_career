"""CTgoodjobs adapter — Phase F (F3), behind config feature flag.

Browser-rendered card list (no plain-HTTP list endpoint observed); the
adapter parses *captured card HTML* and detail pages fetched by plain HTTP
after discovery. Session-token handling: per observed behaviour the site
answers 400 on anonymous detail fetches without the ``ctg-jssid`` cookie —
``fetch()`` passes cookies returned by a prior list load; a non-200 detail
response is retried once, then the record keeps list-level fields with a
report flag (never blocks other sources).

Contract: same as the other adapters — ``parse(raw) -> (jobs, dropped)``.
Wired into run.py OFF until 2 consecutive green runs (§7 rollout rule).
"""

from __future__ import annotations

from typing import Any

from ..normalize import map_districts, parse_salary
from ..schema import ContractViolation, Job, clean_text

BASE = "https://www.ctgoodjobs.hk"


def parse(raw: str, base_url: str = BASE) -> tuple[list[Job], int]:
    """Parse captured card HTML → (jobs, dropped).

    Card shape (see fixtures/synthetic/ctgoodjobs_cards.html):
        <div class="ct-job-card" data-job-id="…">
          <a class="title">…</a>
          <div class="comp">… (may be "匿名公司"/confidential)</div>
          <div class="sal">…</div>
          <div class="loc">…</div>
          <div class="posted">…</div>
        </div>
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(raw, "lxml")
    jobs: list[Job] = []
    dropped = 0
    for card in soup.select("div.ct-job-card"):
        try:
            jobs.append(_parse_card(card, base_url=base_url))
        except ContractViolation:
            dropped += 1
    return jobs, dropped


def _parse_card(card, base_url: str = BASE) -> Job:
    source_job_id = (card.get("data-job-id") or "").strip()
    if not source_job_id:
        raise ContractViolation("ctgoodjobs card missing data-job-id")

    title_el = card.select_one("a.title")
    title = clean_text(title_el.get_text(" ", strip=True)) if title_el else None
    if not title:
        raise ContractViolation("ctgoodjobs card missing title")

    comp_el = card.select_one(".comp")
    company = clean_text(comp_el.get_text(" ", strip=True)) if comp_el else None
    if company and company.casefold() in {"confidential", "匿名公司"}:
        company = None

    sal_el = card.select_one(".sal")
    sal_raw = clean_text(sal_el.get_text(" ", strip=True)) if sal_el else None
    smin, smax, period = parse_salary(sal_raw)

    loc_el = card.select_one(".loc")
    loc_raw = clean_text(loc_el.get_text(" ", strip=True)) if loc_el else None
    locs_raw = [loc_raw] if loc_raw else []
    districts, anywhere, region_norm = map_districts(locs_raw)

    posted_el = card.select_one(".posted")
    posted_raw = clean_text(posted_el.get_text(" ", strip=True)) if posted_el else None

    url = None
    if title_el and title_el.get("href"):
        url = title_el["href"]
        if url.startswith("/"):
            url = f"{base_url}{url}"

    job = Job(
        source="ctgoodjobs",
        source_job_id=source_job_id,
        title=title,
        company=company,
        salary_raw=sal_raw,
        salary_min=smin, salary_max=smax, salary_period=period,
        locations_raw=locs_raw,
        districts=districts,
        anywhere_in_hk=anywhere,
        region_norm=region_norm,
        posted_date_raw=posted_raw,
        url=url,
    )
    return job.compute_hashes()


def fetch(session: Any, *_: Any, **__: Any) -> tuple[list[str], int, int]:
    """Phase F: discovery happens in a browser (Playwright) — see scripts/.

    Daily-run wiring stays a no-op behind the F4 flag until the browser
    discovery capture is validated; tests never call this.
    """
    raise NotImplementedError(
        "ctgoodjobs fetch is Phase F: browser discovery required "
        "(see docs/runbook.md, F3/F4)."
    )
