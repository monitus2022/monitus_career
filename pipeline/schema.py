"""Canonical job record, ids/hashes, validation — build-plan §6.1–6.3.

Every field published by a source plus computed fields; strict null semantics
are enforced here (§6.2): ``None`` = not published; ``""``, ``0`` and
``"N/A"`` never appear where a value is intended; regex salary-miss ⇒
``salary_min/max/period = None`` with ``salary_raw`` retained verbatim.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

HK_TZ = ZoneInfo("Asia/Hong_Kong")

SALARY_PERIODS = ("hour", "day", "month", "year")

# §6.8 month equivalents (documented constants)
DAY_TO_MONTH = 22
HOUR_TO_MONTH = 8 * 22
YEAR_TO_MONTH = 1 / 12

_WS_RE = re.compile(r"\s+")


class ContractViolation(ValueError):
    """A record violates the contract (schema or null semantics)."""


# ---------------------------------------------------------------- utils


def now_hk() -> str:
    """ISO timestamp in Asia/Hong_Kong (Invariant 6)."""
    return datetime.now(HK_TZ).isoformat(timespec="seconds")


def collapse_ws(s: str) -> str:
    """Collapse ``\\s+`` → single space and trim."""
    return _WS_RE.sub(" ", s).strip()


def clean_text(s: Optional[str]) -> Optional[str]:
    """Collapse whitespace; empty/N/A-ish strings become None (never emitted)."""
    if s is None:
        return None
    s2 = collapse_ws(s)
    if s2 == "" or s2.upper() in {"N/A", "NA", "-", "NIL"}:
        return None
    return s2


# ------------------------------------------------------------- identity


def job_id(source: str, source_job_id: str) -> str:
    """``sha256(f"{source}|{source_job_id}")[:16]`` — build-plan §6.1."""
    return hashlib.sha256(f"{source}|{source_job_id}".encode("utf-8")).hexdigest()[:16]


def content_hash(
    title: str,
    company: Optional[str],
    salary_raw: Optional[str],
    locations_raw: list[str],
    posted_date_raw: Optional[str],
    source_job_id: str,
) -> str:
    """sha256 of canonical JSON of the stable published values (§6.1).

    Keys sorted, compact separators, whitespace-collapsed values,
    ``sorted(locations_raw)``. Not the raw HTML, not the normalized record.
    """
    payload = {
        "title": collapse_ws(title),
        "company": collapse_ws(company) if company is not None else None,
        "salary_raw": collapse_ws(salary_raw) if salary_raw is not None else None,
        "locations_raw": sorted(collapse_ws(x) for x in locations_raw),
        "posted_date_raw": collapse_ws(posted_date_raw)
        if posted_date_raw is not None
        else None,
        "source_job_id": collapse_ws(source_job_id),
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- model


@dataclass
class Job:
    """Canonical record. Source-derived fields + pipeline-computed fields."""

    # -- identity (source-derived) -------------------------------------
    source: str
    source_job_id: str
    title: str
    company: Optional[str] = None
    salary_raw: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_period: Optional[str] = None  # ∈ SALARY_PERIODS iff any salary set
    locations_raw: list[str] = field(default_factory=list)
    districts: list[str] = field(default_factory=list)  # 18-district list
    anywhere_in_hk: bool = False
    region_norm: str = "unknown"
    posted_date_raw: Optional[str] = None
    posted_date: Optional[str] = None  # ISO date, Asia/Hong_Kong
    url: Optional[str] = None

    # -- pipeline-computed ---------------------------------------------
    content_hash: str = ""
    dedupe_key: str = ""
    cluster_id: Optional[str] = None  # None ⇔ not clustered (company-less)
    first_seen_at: str = ""
    last_seen_at: str = ""
    # added by run.py/state.py (never source-derived):
    match_score: Optional[int] = None
    match_reasons: list[str] = field(default_factory=list)
    tier: Optional[str] = None  # A | B | C
    # preserved across rebuilds by write-back ownership (§6.6):
    status: Optional[str] = None  # interested | applied | irrelevant
    notes: Optional[str] = None
    starred: Optional[bool] = None

    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        self.title = collapse_ws(self.title if self.title is not None else "")
        if not self.title or self.title.upper() in {"N/A", "NA", "-", "NIL"}:
            raise ContractViolation("title must be non-empty (null semantics §6.2)")

        if not self.source:
            raise ContractViolation("source must be non-empty")
        self.source_job_id = collapse_ws(self.source_job_id)
        if not self.source_job_id:
            raise ContractViolation("source_job_id must be non-empty")
        self.company = clean_text(self.company)
        self.salary_raw = clean_text(self.salary_raw)
        self.locations_raw = [clean_text(x) or x for x in (self.locations_raw or [])]
        self.locations_raw = [x for x in self.locations_raw if x]
        self.posted_date_raw = clean_text(self.posted_date_raw)
        self.salary_period = clean_text(self.salary_period)
        # null semantics: no zero transported as data
        if self.salary_period is not None and self.salary_period not in SALARY_PERIODS:
            raise ContractViolation(f"salary_period {self.salary_period!r} invalid")
        if self.salary_period and self.salary_min is None and self.salary_max is None:
            raise ContractViolation("salary_period set without salary values")
        if (self.salary_min is not None or self.salary_max is not None) and (
            self.salary_period is None
        ):
            raise ContractViolation("salary values set without salary_period")
        if self.salary_min is None and self.salary_max is not None:
            raise ContractViolation("salary_max set without salary_min")
        if self.tier is not None and self.tier not in ("A", "B", "C"):
            raise ContractViolation(f"tier {self.tier!r} invalid")
        if self.status is not None and self.status not in (
            "interested", "applied", "irrelevant",
        ):
            raise ContractViolation(f"status {self.status!r} invalid")
        # month equivalents are derived, never user-supplied (0-guard below)

    # ------------------------------------------------------------------
    @property
    def id(self) -> str:
        return self.job_id()  # read-only accessor; compute lazily

    def job_id(self) -> str:  # noqa: A003 — canonical §6.1 key
        return job_id(self.source, self.source_job_id)

    def compute_hashes(self) -> "Job":
        """Fill content_hash/dedupe_key/cluster_id/versionless derived fields."""
        self.content_hash = content_hash(
            self.title, self.company, self.salary_raw, self.locations_raw,
            self.posted_date_raw, self.source_job_id,
        )
        from .dedupe import dedupe_key, cluster_id as mk_cluster
        self.dedupe_key = dedupe_key(self.company, self.title, self.region_norm)
        self.cluster_id = (
            mk_cluster(self.dedupe_key)
            if self.company is not None else None
        )
        return self

    def ensure_seen(self, first_seen: str | None = None) -> None:
        """Stamp first/last seen. Idempotence: first_seen never resets (Invariant 7)."""
        stamp = first_seen or now_hk()
        if not self.first_seen_at:
            self.first_seen_at = stamp
        self.last_seen_at = stamp

    def month_equiv_min(self) -> Optional[float]:
        """Period-adjusted minimum salary in monthly HKD (§6.8 constants)."""
        return self._month_equiv(self.salary_min)

    def month_equiv_max(self) -> Optional[float]:
        return self._month_equiv(self.salary_max)

    def _month_equiv(self, v: Optional[float]) -> Optional[float]:
        if v is None or self.salary_period is None:
            return None
        factor = {
            "hour": HOUR_TO_MONTH,
            "day": DAY_TO_MONTH,
            "month": 1.0,
            "year": YEAR_TO_MONTH,
        }[self.salary_period]
        return round(v * factor, 2)

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        d = {
            "job_id": self.job_id(),
            "source": self.source,
            "source_job_id": self.source_job_id,
            "title": self.title,
            "company": self.company,
            "salary_raw": self.salary_raw,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_period": self.salary_period,
            "locations_raw": list(self.locations_raw),
            "districts": list(self.districts),
            "anywhere_in_hk": self.anywhere_in_hk,
            "region_norm": self.region_norm,
            "posted_date_raw": self.posted_date_raw,
            "posted_date": self.posted_date,
            "url": self.url,
            "content_hash": self.content_hash,
            "dedupe_key": self.dedupe_key,
            "cluster_id": self.cluster_id,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
        }
        # computed/optional only when set (records stay lean)
        if self.month_equiv_min() is not None:
            d["salary_month_min"] = self.month_equiv_min()
        if self.month_equiv_max() is not None:
            d["salary_month_max"] = self.month_equiv_max()
        if self.match_score is not None:
            d["match_score"] = self.match_score
        if self.match_reasons:
            d["match_reasons"] = list(self.match_reasons)
        if self.tier is not None:
            d["tier"] = self.tier
        if self.status is not None:
            d["status"] = self.status
        if self.notes is not None:
            d["notes"] = self.notes
        if self.starred is not None:
            d["starred"] = self.starred
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        j = cls(
            source=d["source"],
            source_job_id=d["source_job_id"],
            title=d["title"],
            company=d.get("company"),
            salary_raw=d.get("salary_raw"),
            salary_min=d.get("salary_min"),
            salary_max=d.get("salary_max"),
            salary_period=d.get("salary_period"),
            locations_raw=d.get("locations_raw") or [],
            districts=d.get("districts") or [],
            anywhere_in_hk=bool(d.get("anywhere_in_hk")),
            region_norm=d.get("region_norm") or "unknown",
            posted_date_raw=d.get("posted_date_raw"),
            posted_date=d.get("posted_date"),
            url=d.get("url"),
            content_hash=d.get("content_hash", ""),
            dedupe_key=d.get("dedupe_key", ""),
            cluster_id=d.get("cluster_id"),
            first_seen_at=d.get("first_seen_at", ""),
            last_seen_at=d.get("last_seen_at", ""),
            match_score=d.get("match_score"),
            match_reasons=list(d.get("match_reasons") or []),
            tier=d.get("tier"),
            status=d.get("status"),
            notes=d.get("notes"),
            starred=d.get("starred"),
        )
        return j


# ------------------------------------------------------------- validation


TRACKED_FIELDS = (
    "title", "company", "salary_raw", "salary_min", "salary_max",
    "salary_period", "locations_raw", "districts",
    "posted_date_raw", "url",
)


def validate_field_coverage(job: Job) -> list[str]:
    """Missing-field names for the drift canary (report null-rates)."""
    missing = []
    for f in ("title", "source_job_id"):
        if not getattr(job, f):
            missing.append(f)
    for f in ("company", "salary_raw", "posted_date_raw", "url"):
        if getattr(job, f) is None:
            missing.append(f)
    if not job.locations_raw:
        missing.append("locations_raw")
    if not job.districts and not job.anywhere_in_hk:
        missing.append("districts")
    if job.salary_min is None and job.salary_max is None:
        missing.append("salary")
    return missing


def validate_record(job: Job) -> None:
    """Full contract check — raises ContractViolation, drops at runtime (§6.5)."""
    # re-validate null semantics: reconstructing re-runs __post_init__ checks
    Job.from_dict(job.to_dict())
    if not job.job_id():  # pragma: no cover — constructor guarantees
        raise ContractViolation("missing job_id")
