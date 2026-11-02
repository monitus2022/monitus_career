"""State — seen-set + user-state write-back merge (build-plan §6.6, C2).

- ``seen.json``: job_id → {content_hash, first_seen_at, last_seen_at}.
  Persisted locally every run (Invariants 6/7; Asia/Hong_Kong timestamps).
- ``merge_user_state()``: pipeline owns all source-derived + computed fields;
  the function/UI own ``status``/``notes``/``starred``. Daily: read the live
  ``jobs.json`` and overlay user-state onto rebuilt records by ``job_id``;
  records absent from the rebuild keep their user state until purged
  after 90 days.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from .schema import HK_TZ, Job, now_hk

USER_STATE_FIELDS = ("status", "notes", "starred")
USER_STATE_RETENTION_DAYS = 90


class SeenSet:
    """R2/local seen-set: ``{job_id: {content_hash, first_seen_at, ...}}``."""

    def __init__(self, data: dict | None = None) -> None:
        self.data: dict[str, dict] = data or {}

    @classmethod
    def load(cls, path: Path | str) -> "SeenSet":
        p = Path(path)
        if not p.exists():
            return cls({})
        return cls(json.loads(p.read_text() or "{}"))

    def save(self, path: Path | str) -> None:
        Path(path).write_text(json.dumps(self.data, sort_keys=True, indent=1))

    def look(self, job_id_str: str) -> dict | None:
        return self.data.get(job_id_str)

    def upsert(self, job: Job) -> None:
        self.data[job.job_id()] = {
            "content_hash": job.content_hash,
            "first_seen_at": job.first_seen_at,
            "last_seen_at": job.last_seen_at,
        }

    def touch(self, jobs: Iterable[Job]) -> None:
        carries = {k: v for k, v in self.data.items() if k not in {j.job_id() for j in jobs}}
        for j in jobs:
            old = self.look(j.job_id())
            first = (old or {}).get("first_seen_at") or j.first_seen_at or now_hk()
            if (old or {}).get("content_hash") != j.content_hash:
                # re-published/edited posting: history preserved, not "new"
                j.first_seen_at = first
            j.ensure_seen(first_seen=first)
            self.upsert(j)
        # untouched-but-not-seen entries are kept (retention purge elsewhere)


def load_user_state(from_jobs_json: Path | str | None) -> dict[str, dict]:
    """Read current live ``jobs.json`` and harvest ``{job_id: user_state}``.

    ``last_seen_at`` rides along (retention clock, §6.6) but is never written
    back onto rebuilt records by ``merge_user_state`` (pipeline owns it).
    """
    if not from_jobs_json or not Path(from_jobs_json).exists():
        return {}
    data = json.loads(Path(from_jobs_json).read_text())
    records = data if isinstance(data, list) else data.get("jobs", [])
    out: dict[str, dict] = {}
    for rec in records:
        st = {f: rec.get(f) for f in USER_STATE_FIELDS if rec.get(f) is not None}
        if st:
            jid = rec.get("job_id")
            if jid:
                if rec.get("last_seen_at") is not None:
                    st["last_seen_at"] = rec["last_seen_at"]
                out[jid] = st
    return out


def merge_user_state(jobs: list[Job], user_state: dict[str, dict]) -> tuple[list[Job], int]:
    """Overlay user-state onto rebuilt records; return (jobs, orphan_count).

    Records absent from the rebuild keep their user state (kept by the caller
    as orphans) until the retention purge.
    """
    applied = 0
    for j in jobs:
        st = user_state.get(j.job_id())
        if not st:
            continue
        for f in USER_STATE_FIELDS:
            if f in st:
                setattr(j, f, st[f])
        applied += 1
    orphans = {jid: st for jid, st in user_state.items()
               if jid not in {j.job_id() for j in jobs}}
    return jobs, orphans


def apply_user_state_to_dict(jobs_json_list: list[dict], orphans: dict[str, dict]) -> list[dict]:
    """Attach surviving orphans into the payload (retention ≤90 days, §6.6)."""
    cutoff = (datetime.now(HK_TZ) - timedelta(days=USER_STATE_RETENTION_DAYS)
              ).isoformat(timespec="seconds")
    kept = []
    for jid, st in orphans.items():
        last_seen = st.get("last_seen_at") or ""
        if last_seen >= cutoff:
            kept.append({**st, "job_id": jid, "deleted_record": True})
    return jobs_json_list + kept


def purge_state(seen: SeenSet, days: int = 90) -> int:
    """Drop seen-entries untouched for ≥90 days (pair of the raw purge rule)."""
    cutoff = (datetime.now(HK_TZ) - timedelta(days=days)).isoformat(timespec="seconds")
    stale = [k for k, v in seen.data.items()
             if (v.get("last_seen_at") or "") < cutoff]
    for k in stale:
        del seen.data[k]
    return len(stale)
