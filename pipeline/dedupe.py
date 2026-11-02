"""Dedup — dedupe_key / cluster_id per build-plan §6.3.

- ``dedupe_key = norm(company) || "||" || norm(title) || "||" || region_norm``
- cluster only when company is non-null; anonymous HK Gov rows never cluster.
- merge requires all three parts equal (false merge worse than a miss).
"""

from __future__ import annotations

import hashlib

from .normalize import norm_operand
from .schema import Job


def dedupe_key(company: str | None, title: str, region_norm: str) -> str:
    if company is None:
        # anonymous rows keep an empty-company key so we can still dedupe
        # *within* the same source by the §6.1 job_id (never cross-source).
        return f"||{norm_operand(title)}||{region_norm}"
    return f"{norm_operand(company)}||{norm_operand(title)}||{region_norm}"


def cluster_id(dedupe_key: str) -> str:
    return hashlib.sha256(dedupe_key.encode("utf-8")).hexdigest()[:16]


def _stable_region(job: Job) -> str:
    return job.region_norm or "unknown"


def apply_dedupe(jobs: list[Job]) -> list[Job]:
    """Fill dedupe_key/cluster_id; group records with same full key.

    Returns the input list (mutated) with ``cluster_id`` set on every record
    whose company is non-null; company-less rows keep ``cluster_id=None``.
    """
    for j in jobs:
        key = dedupe_key(j.company, j.title, _stable_region(j))
        j.dedupe_key = key
        j.cluster_id = cluster_id(key) if j.company is not None else None
    return jobs


def merge_into(events: list[Job], existing: list[Job]) -> list[Job]:
    """Idempotence helper: prefer existing ``first_seen_at`` (Invariant 7).

    A record only counts as *new* when its ``job_id`` was never seen OR its
    ``content_hash`` changed (re-published promotion).
    """
    by_job_id = {j.job_id(): j for j in existing}
    out: list[Job] = []
    for e in events:
        old = by_job_id.get(e.job_id())
        if old is None:
            e.ensure_seen()
            out.append(e)
            continue
        if old.content_hash != e.content_hash:
            # changed posting: keep first_seen_at, refresh stale fields
            e.first_seen_at = old.first_seen_at or e.first_seen_at
            e.ensure_seen(first_seen=e.first_seen_at)
        else:
            # unchanged: keep history untouched
            e.first_seen_at = old.first_seen_at
            e.last_seen_at = old.last_seen_at or e.last_seen_at
        out.append(e)
    return out
