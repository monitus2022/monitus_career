"""recruit.com.hk adapter — Phase F (F1/F2), behind config feature flag.

Two-step design per build-plan F2:
    1. *discovery* — browser (Playwright) search-POST with the unresolved
       ViewState; fallback: plain HTTP crawl of the ``MoreSearchResultsOnline.aspx``
       endpoints exposed by the site's robots map.
    2. *detail enrichment* — plain HTTP per discovered detail URL (capped).

parse() consumes discovery captures; fetch() runs LIVE only from scripts/.
"""

from __future__ import annotations

from ..normalize import map_districts, parse_salary
from ..schema import ContractViolation, Job, clean_text

BASE = "https://www.recruit.com.hk"


def parse(raw: str, base_url: str = BASE) -> tuple[list[Job], int]:
    """Parse captured search-results HTML → (jobs, dropped).

    Row shape (fixtures/synthetic/recruit_results.html):
        <tr class="jobrow" data-jobno="R-2026-0001">
          <td class="jtitle"><a href="/JobDtl.aspx?JobNo=…">…</a></td>
          <td class="jcomp">…</td>
          <td class="jsal">…</td>
          <td class="jloc">…</td>
        </tr>
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(raw, "lxml")
    jobs: list[Job] = []
    dropped = 0
    for row in soup.select("tr.jobrow"):
        try:
            jobs.append(_parse_row(row, base_url=base_url))
        except ContractViolation:
            dropped += 1
    return jobs, dropped


def _parse_row(row, base_url: str = BASE) -> Job:
    source_job_id = (row.get("data-jobno") or "").strip()
    if not source_job_id:
        raise ContractViolation("recruit row missing data-jobno")

    title_el = row.select_one(".jtitle a")
    title = clean_text(title_el.get_text(" ", strip=True)) if title_el else None
    if not title:
        raise ContractViolation("recruit row missing title")

    comp_el = row.select_one(".jcomp")
    company = clean_text(comp_el.get_text(" ", strip=True)) if comp_el else None

    sal_el = row.select_one(".jsal")
    sal_raw = clean_text(sal_el.get_text(" ", strip=True)) if sal_el else None
    smin, smax, period = parse_salary(sal_raw)

    loc_el = row.select_one(".jloc")
    loc_raw = clean_text(loc_el.get_text(" ", strip=True)) if loc_el else None
    locs_raw = [loc_raw] if loc_raw else []
    districts, anywhere, region_norm = map_districts(locs_raw)

    url = title_el["href"] if (title_el and title_el.get("href")) else None
    if url and url.startswith("/"):
        url = f"{base_url}{url}"

    return Job(
        source="recruit",
        source_job_id=source_job_id,
        title=title,
        company=company,
        salary_raw=sal_raw,
        salary_min=smin, salary_max=smax, salary_period=period,
        locations_raw=locs_raw,
        districts=districts,
        anywhere_in_hk=anywhere,
        region_norm=region_norm,
        url=url,
    ).compute_hashes()


def fetch(session, *_: Any, browser_discovery: Any = None) -> tuple[list[dict], int, int]:
    """Phase F. Discovery (browser) + detail enrichment (plain HTTP).

    ``browser_discovery`` is an injected callable from scripts (Playwright);
    when absent this stays OFF (F4 flag) and the plain-HTTP
    ``MoreSearchResultsOnline.aspx`` fallback per robots map is used by the
    daily-run scripts after a real capture exists.
    """
    raise NotImplementedError(
        "recruit fetch is Phase F: browser discovery capture pending (F1); "
        "see BLOCKERS.md/F1."
    )
