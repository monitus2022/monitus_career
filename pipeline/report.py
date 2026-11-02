"""Run report (§6.7) + field-coverage / drift-canary (B4/G3).

``{run_id, started_at, finished_at,
   sources: {<name>: {fetch_ok, retries, http_requests, records_fetched,
                      records_parsed, records_written, contract_failures,
                      null_rates{field: pct}}},
   totals{...}, alerts[], staleness_days}``
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .schema import HK_TZ, TRACKED_FIELDS, Job, validate_field_coverage

# fields whose published-coverage rate is tracked for the drift canary
CANARY_FIELDS = ("title", "company", "salary_raw", "salary", "locations_raw",
                 "districts", "posted_date_raw", "url")


@dataclass
class SourceStats:
    name: str
    fetch_ok: bool = False
    retries: int = 0
    http_requests: int = 0
    records_fetched: int = 0
    records_parsed: int = 0
    records_written: int = 0
    contract_failures: int = 0
    null_rates: dict = field(default_factory=dict)
    recall_mode: str | None = None

    def compute_null_rates(self, jobs: list[Job]) -> dict:
        """Null-rate % for tracked fields on the *parsed* records (B4)."""
        n = len(jobs) or 1
        rates: dict[str, float] = {}
        for f in CANARY_FIELDS:
            miss = 0
            for j in jobs:
                if f == "salary":
                    miss += int(j.salary_min is None and j.salary_max is None)
                elif f in ("title", "salary_raw", "company", "posted_date_raw", "url"):
                    miss += int(getattr(j, f) is None)
                elif f in ("locations_raw", "districts"):
                    miss += 0 if getattr(j, f) else 1
            rates[f] = round(100.0 * miss / n, 1)
        self.null_rates = rates
        return rates

    def to_dict(self) -> dict:
        return {
            "fetch_ok": self.fetch_ok,
            "retries": self.retries,
            "http_requests": self.http_requests,
            "records_fetched": self.records_fetched,
            "records_parsed": self.records_parsed,
            "records_written": self.records_written,
            "contract_failures": self.contract_failures,
            "null_rates": self.null_rates,
            "recall_mode": self.recall_mode,
        }


@dataclass
class RunReport:
    run_id: str
    started_at: str
    finished_at: str = ""
    sources: dict = field(default_factory=dict)
    totals: dict = field(default_factory=dict)
    alerts: list = field(default_factory=list)
    staleness_days: int | None = None
    failed: bool = False
    fail_reason: str | None = None

    def finish(self) -> None:
        self.finished_at = datetime.now(HK_TZ).isoformat(timespec="seconds")
        self.totals = {
            "records_written": sum(s.records_written for s in self.sources.values()),
            "contract_failures": sum(s.contract_failures for s in self.sources.values()),
            "http_requests": sum(s.http_requests for s in self.sources.values()),
            "retries": sum(s.retries for s in self.sources.values()),
        }

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "sources": {k: v.to_dict() for k, v in self.sources.items()},
            "totals": self.totals,
            "alerts": list(self.alerts),
            "staleness_days": self.staleness_days,
            "failed": self.failed,
            "fail_reason": self.fail_reason,
        }

    def save(self, report_dir: Path | str) -> Path:
        p = Path(report_dir) / f"{self.run_id[:10]}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=1, ensure_ascii=False))
        return p


# ------------------------------------------------------------ drift canary


def load_baselines(report_dir: Path | str, window_days: int = 7) -> dict[str, dict[str, float]]:
    """7-day rolling per-field null-rate baseline from past run reports."""
    p = Path(report_dir)
    if not p.exists():
        return {}
    baselines: dict[str, dict[str, list[float]]] = {}
    for f in sorted(p.glob("*.json")):  # filenames are dates (YYYY-MM-DD)
        try:
            rep = json.loads(f.read_text())
        except (ValueError, OSError):
            continue
        for name, s in (rep.get("sources") or {}).items():
            rates = (s or {}).get("null_rates") or {}
            slot = baselines.setdefault(name, {})
            for fld, pct in rates.items():
                slot.setdefault(fld, []).append(float(pct))
    return {
        name: {fld: sum(v) / len(v) for fld, v in fields.items()}
        for name, fields in baselines.items()
    }


def coverage_drop_breach(
    source: str,
    stats: SourceStats,
    baseline: dict[str, dict[str, float]] | None,
    max_drop_pp: float = 30.0,
) -> list[str]:
    """Systemic breach if any tracked field's null-rate rose >30 pp (§6.5)."""
    breaches: list[str] = []
    base = (baseline or {}).get(source) or {}
    for fld, now_pct in (stats.null_rates or {}).items():
        past_pct = base.get(fld)
        if past_pct is None:
            continue
        if now_pct - past_pct > max_drop_pp:
            breaches.append(f"{source}.{fld} null-rate {past_pct}% → {now_pct}% "
                            f"(> {max_drop_pp} pp)")
    return breaches
