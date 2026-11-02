"""Deterministic scorer — build-plan §6.8, verbatim.

    score = 3·|must_have hits| + 1·|nice_to_have hits|
          + 2·(salary floor cleared, period-adjusted) + 1·(district ∈ preferred)
    deal_breakers = exclude-keyword hits | salary floor breach
                  | seniority out-of-band (regex)
    salary→month: day × 22, hour × 8 × 22 (constants in schema.py)
    tiers: A = no deal-breaker ∧ score ≥ 8 · B = 4 ≤ score < 8
           C = score < 4 ∨ any deal-breaker

All postings appear (rank, never filter — Invariant 5): deal-breakers demote
to C, they never hide a record. Ties are reproducible (stable order:
score desc, then title, then job_id).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from .schema import Job

log = logging.getLogger(__name__)

TIER_A = 8
TIER_B = 4


def _as_regex(kw: str) -> re.Pattern | None:
    if kw.startswith("regex:"):
        return re.compile(kw[6:], re.IGNORECASE)
    return None


def keyword_hit(job: Job, keyword: str, fields: tuple[str, ...]) -> bool:
    rx = _as_regex(keyword)
    hay = [getattr(job, f) for f in fields]
    hay = [h for h in hay if isinstance(h, str) and h]
    if rx is not None:
        return any(rx.search(h) for h in hay)
    k = keyword.casefold()
    return any(k in h.casefold() for h in hay)


def load_profile(path: Path | str = "profile.yaml") -> dict:
    """Parse profile.yaml (H2 input). Missing file → empty profile (all C/A-less)."""
    p = Path(path)
    if not p.exists():
        log.info("no profile.yaml — scoring disabled (no tiers)")
        return {}
    import yaml
    raw = yaml.safe_load(p.read_text()) or {}
    return {
        "must_have": [str(x) for x in (raw.get("must_have") or [])],
        "nice_to_have": [str(x) for x in (raw.get("nice_to_have") or [])],
        "exclude": [str(x) for x in (raw.get("exclude") or [])],
        "salary_floor_month": raw.get("salary_floor_month") or None,
        "districts": [str(x) for x in (raw.get("districts") or [])],
        "anywhere_in_hk": bool(raw.get("anywhere_in_hk", False)),
        "seniority": raw.get("seniority") or None,
        "seniority_out_match": raw.get("seniority_out_match") or None,
    }


def score(job: Job, profile: dict) -> tuple[int, list[str], str | None]:
    """(score, match_reasons, tier). tier None ⇒ no profile, no ranking."""
    if not profile:
        return 0, [], None
    reasons: list[str] = []
    score = 0
    deal_breakers: list[str] = []

    for kw in profile["must_have"]:
        if keyword_hit(job, kw, ("title",)):
            score += 3
            reasons.append(f"must:{kw}")
    for kw in profile["nice_to_have"]:
        if keyword_hit(job, kw, ("title", "company")):
            score += 1
            reasons.append(f"nice:{kw}")
    # exclude hits on *published* fields, never full ad copy (privacy)
    for kw in profile["exclude"]:
        if keyword_hit(job, kw, ("title", "company")):
            deal_breakers.append(f"exclude:{kw}")
            continue
        locs = " ".join(job.locations_raw)
        rx = _as_regex(kw)
        if (rx and rx.search(locs)) or (bool(locs) and kw.casefold() in locs.casefold()):
            deal_breakers.append(f"exclude:{kw}")

    # salary floor (period-adjusted monthly equivalent; schema constants)
    floor = profile["salary_floor_month"]
    if floor is not None:
        hi = job.month_equiv_max() or job.month_equiv_min()
        if hi is not None and hi < floor:
            deal_breakers.append(f"salary<{floor}")
        else:
            score += 2
            reasons.append("salary_ok")

    # districts ∈ preferred
    pref = set(profile["districts"])
    if pref and (set(job.districts) & pref):
        score += 1
        reasons.append("district")
    elif profile["anywhere_in_hk"] and job.anywhere_in_hk:
        score += 1
        reasons.append("district:anywhere")

    # seniority band (out-of-band = deal-breaker)
    if profile["seniority"]:
        rx = _as_regex(profile["seniority"])
        if rx and not rx.search(job.title):
            deal_breakers.append("seniority_out_of_band")
    if profile["seniority_out_match"]:
        rx = _as_regex(profile["seniority_out_match"])
        if rx and rx.search(job.title):
            deal_breakers.append("seniority_out_of_band")

    tier = "C" if deal_breakers else ("A" if score >= TIER_A else ("B" if score >= TIER_B else "C"))
    # deal-breaker reasons are reported too (site shows them alongside hits)
    reasons = reasons + [f"deal:{d}" for d in deal_breakers]
    return score, reasons, tier


def apply_ranking(jobs: list[Job], profile: dict) -> list[Job]:
    """Fill match_score/match_reasons/tier; return list sorted tier→score."""
    if not profile:
        return jobs
    for j in jobs:
        s, reasons, tier = score(j, profile)
        j.match_score = s
        j.match_reasons = reasons
        j.tier = tier
    jobs.sort(key=lambda j: (
        {"A": 0, "B": 1, "C": 2}.get(j.tier, 3),
        -(j.match_score or 0),
        j.title.casefold(),
        j.job_id(),
    ))
    return jobs
