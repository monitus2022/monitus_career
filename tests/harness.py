"""Contract test harness (A3) — required-fields check + coverage report.

Runs against captured or synthetic fixture payloads via the adapter's
``parse(raw) -> (jobs, dropped)``. Tests never touch the network (Invariant 2).
"""

from __future__ import annotations

from pipeline.schema import ContractViolation, Job, validate_field_coverage

REQUIRED = ("source", "source_job_id", "title")


def check_contract(jobs: list[Job]) -> list[str]:
    """Global-violation list; empty ⇒ contract holds for these records."""
    errors: list[str] = []
    for j in jobs:
        for f in REQUIRED:
            if not getattr(j, f):
                errors.append(f"{j.source}: missing required field {f}")
        if (j.salary_min is None and j.salary_max is None) and j.salary_period is not None:
            errors.append(f"{j.source}:{j.source_job_id}: salary_period set without salary")
        if (j.salary_min is not None or j.salary_max is not None) and j.salary_period is None:
            errors.append(f"{j.source}:{j.source_job_id}: salary set without period")
        if j.salary_period is not None and j.salary_period not in ("hour", "day", "month", "year"):
            errors.append(f"{j.source}:{j.source_job_id}: salary_period invalid")
        try:
            validate_field_coverage(j)
        except ContractViolation as e:  # pragma: no cover
            errors.append(str(e))
    return errors


def coverage_report(jobs: list[Job]) -> dict[str, dict[str, float]]:
    """Per-source field coverage % (B4 drift canary; missing ⇒ not published)."""
    out: dict[str, dict[str, float]] = {}
    by_source: dict[str, list[Job]] = {}
    for j in jobs:
        by_source.setdefault(j.source, []).append(j)
    for src, recs in by_source.items():
        n = len(recs)
        cov: dict[str, float] = {}
        for f in ("title", "company", "salary", "locations_raw", "districts",
                  "posted_date", "url"):
            present = 0
            for j in recs:
                if f == "salary":
                    present += int(not (j.salary_min is None and j.salary_max is None))
                elif f == "districts":
                    present += int(not (not j.districts and not j.anywhere_in_hk))
                elif f == "locations_raw":
                    present += int(bool(j.locations_raw))
                else:
                    present += int(getattr(j, f) is not None)
            cov[f] = round(100.0 * present / n, 1)
        out[src] = cov
    return out
