"""Orchestrator — build-plan C1/C5, §6.5–6.8 tiered failure policy.

Adapter contract (all ``pipeline/sources/*.py``):
    parse(raw) -> (jobs, contract_dropped_count)   # pure, fixture-driven
    fetch(...) -> (raw_pages, retries, http_requests)  # LIVE only, capped

Usage:
    python -m pipeline.run [--dry-run] [--sources=hkgov,jobsdb]
                           [--data-dir=runs] [--fixtures-dir=fixtures]
                           [--upload] [--profile=profile.yaml]

Dry-run replays captured fixtures from ``fixtures/`` (untracked local
captures) → full pipeline locally (Invariant 2: tests never touch the net).
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
from datetime import datetime
from pathlib import Path

from . import alert, embed
from .dedupe import apply_dedupe
from .report import (
    RunReport, SourceStats, coverage_drop_breach, load_baselines,
)
from .schema import HK_TZ, ContractViolation, Job, now_hk, validate_record
from .state import (
    SeenSet, apply_user_state_to_dict, load_user_state, merge_user_state,
    purge_state,
)
from .score import apply_ranking, load_profile

log = logging.getLogger("run")

# §2 Invariant 3 — request budgets
PER_SOURCE_CAP = 10
TOTAL_CAP = 40

# §6.5 systemic thresholds
CONTRACT_FAILURE_RATE_MAX = 5.0 / 100.0
COVERAGE_DROP_PP_MAX = 30.0

LOCAL_DATA_DIR = Path("runs")

KEYWORD_CONFIG: dict = {}


def _load_keyword_config(path: Path = Path("pipeline/config.yaml")) -> None:
    if path.exists():
        import yaml  # noqa: PLC0415
        KEYWORD_CONFIG.update(yaml.safe_load(path.read_text()) or {})


# --------------------------------------------------------------- fetch


def _fetch_source(source_name: str, session, keyword: str = ""):
    mod = importlib.import_module(f"pipeline.sources.{source_name}")
    if source_name == "hkgov":
        raw, made, retries = mod.fetch(session, cap=PER_SOURCE_CAP)
        return [raw], retries, made
    if source_name == "jobsdb":
        pages, made, retries = mod.fetch(session, keyword=keyword,
                                         cap=PER_SOURCE_CAP)
        return pages, retries, made
    # ctgoodjobs / recruit — Phase F (browser sources), feature-flagged OFF
    return [], 0, 0


def _parse_source(source_name: str, raw_pages: list) -> tuple[list[Job], int]:
    mod = importlib.import_module(f"pipeline.sources.{source_name}")
    jobs: list[Job] = []
    dropped = 0
    for raw in raw_pages:
        j, d = mod.parse(raw)
        jobs.extend(j)
        dropped += d
    return jobs, dropped


# ------------------------------------------------------------------ run


def run_pipeline(
    sources: list[str],
    data_dir: Path = LOCAL_DATA_DIR,
    fixtures_dir: Path = Path("fixtures"),
    dry_run: bool = False,
    do_upload: bool = False,
    profile_path: Path | None = None,
) -> tuple[RunReport, list[dict]]:
    _load_keyword_config()
    _early_profile = load_profile(profile_path or Path("profile.yaml"))
    if _early_profile.get("must_have"):
        # recall hook (§6.8): scope the source keyword search to the profile's
        # must-have keywords (jobsdb treats space-separated terms as AND).
        KEYWORD_CONFIG["jobsdb"] = " ".join(_early_profile["must_have"])
    elif _early_profile.get("nice_to_have"):
        # no must-haves → recall still benefits from the nice keywords
        KEYWORD_CONFIG["jobsdb"] = " ".join(_early_profile["nice_to_have"])
    # else: fall back to the broad keyword from config.yaml
    rep_dir = data_dir / "reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    rr = RunReport(run_id=now_hk().replace("+08:00", "+0800"),
                   started_at=now_hk())

    failures_history = _load_failures(data_dir)
    user_state_local = load_user_state(data_dir / "jobs.json")

    all_jobs: list[Job] = []
    systemic_breaches: list[str] = []
    baseline = load_baselines(rep_dir)
    seen = SeenSet.load(data_dir / "seen.json")
    fail_fast: str | None = None

    for name in sources:
        stats = SourceStats(name=name)
        rr.sources[name] = stats
        try:
            if dry_run:
                raw_pages = _load_dry_fixture(name, fixtures_dir)
                retries = 0
                stats.http_requests = 0
            else:
                import requests
                with requests.Session() as session:
                    session.headers.update({
                        "User-Agent": "Mozilla/5.0 (monitus-career pipeline)",
                    })
                    raw_pages, retries, made = _fetch_source(
                        name, session, KEYWORD_CONFIG.get(name, ""),
                    )
                    stats.http_requests = made
            stats.retries = retries
            stats.records_fetched = len(raw_pages)
            if not raw_pages:
                # no data obtained → day-level source failure (§6.5)
                stats.fetch_ok = False
                _record_no_jobs(stats)
                _streak_inc(failures_history, name)
                if failures_history[name] >= 2:
                    alert.log_alert(
                        rr, f"source failed day-level: {name} "
                            f"({failures_history[name]} consecutive days)",
                        root=data_dir,
                    )
                continue
            jobs, dropped = _parse_source(name, raw_pages)
            stats.contract_failures = dropped
            stats.fetch_ok = True
        except Exception as exc:  # noqa: BLE001 — a source failing is normal
            _record_no_jobs(stats)
            _streak_inc(failures_history, name)
            if failures_history[name] >= 2:
                alert.log_alert(
                    rr, f"source failed day-level: {name} "
                        f"({failures_history[name]} consecutive days)",
                    root=data_dir,
                )
            log.exception("source %s failed: %s", name, exc)
            continue

        # per-record contract tier: adapters already dropped; the systemic
        # check watches the ratio (§6.5)
        if len(jobs) + dropped and dropped / (len(jobs) + dropped) > CONTRACT_FAILURE_RATE_MAX:
            fail_fast = (f"{name}: contract-failure rate {dropped}/"
                         f"{len(jobs) + dropped} > 5%")
            systemic_breaches.append(fail_fast)
            continue

        stats.records_parsed = len(jobs)
        stats.compute_null_rates(jobs)
        systemic_breaches.extend(
            coverage_drop_breach(name, stats, baseline, COVERAGE_DROP_PP_MAX))
        all_jobs.extend(jobs)
        _streak_reset(failures_history, name)

    if systemic_breaches and fail_fast is None:
        fail_fast = "; ".join(systemic_breaches)
    if fail_fast:
        rr.failed = True
        rr.fail_reason = fail_fast
        alert.log_alert(rr, f"SYSTEMIC BREACH — run failed, nothing written: {fail_fast}",
                        root=data_dir)
        rr.finish()
        rr.save(rep_dir)
        _save_failures(data_dir, failures_history)
        return rr, []

    # ---- idempotent merge, dedupe, recall, ranking --------------------------
    seen.touch(all_jobs)
    apply_dedupe(all_jobs)

    profile = load_profile(profile_path or Path("profile.yaml"))
    recall_mode = embed.apply_recall(all_jobs, profile)
    for stats in rr.sources.values():
        stats.recall_mode = recall_mode
    apply_ranking(all_jobs, profile)

    # ---- write-back merge (§6.6) -------------------------------------------
    merged_jobs, orphans = merge_user_state(all_jobs, user_state_local)
    payload = apply_user_state_to_dict(
        [j.to_dict() for j in merged_jobs], orphans)
    for stats in rr.sources.values():
        stats.records_written = len(payload)

    # ---- persist ------------------------------------------------------------
    seen.save(data_dir / "seen.json")
    (data_dir / "jobs.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False))
    _save_failures(data_dir, failures_history)
    purge_state(seen)
    staleness = _compute_staleness(rep_dir)
    rr.staleness_days = staleness
    if staleness is not None and staleness >= 2:
        alert.log_alert(rr, f"data staleness {staleness} days", root=data_dir)

    if do_upload:
        code = _upload(data_dir)
        if code:
            alert.log_alert(rr, f"R2 upload exit {code}", root=data_dir)

    rr.finish()
    rr.save(rep_dir)
    return rr, payload


# ---------------------------------------------------------------- helpers


def _load_dry_fixture(name: str, fixtures_dir: Path) -> list:
    """Replay captured fixtures; NEVER the network (Invariant 2)."""
    if name == "hkgov":
        p = fixtures_dir / "hkgov_quickview.html"
        return [p.read_text(encoding="utf-8", errors="replace")] if p.exists() else []
    if name == "jobsdb":
        p = fixtures_dir / "jobsdb_cards.html"
        if p.exists():
            return [p.read_text(encoding="utf-8", errors="replace")]
        # untracked real capture first, synthetic fallback second
        p2 = fixtures_dir / "synthetic" / "jobsdb_cards.html"
        return [p2.read_text(encoding="utf-8", errors="replace")] if p2.exists() else []
    if name in ("ctgoodjobs", "recruit"):
        p = fixtures_dir / f"{name}_cards.html"
        return [p.read_text(encoding="utf-8", errors="replace")] if p.exists() else []
    return []


def _record_no_jobs(stats: SourceStats) -> None:
    stats.records_parsed = 0
    stats.compute_null_rates([])


def _load_failures(data_dir: Path) -> dict:
    p = data_dir / "failures.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _save_failures(data_dir: Path, failures: dict) -> None:
    (data_dir / "failures.json").write_text(json.dumps(failures, indent=1))


def _streak_inc(failures: dict, source: str) -> int:
    s = failures.get(source, 0) + 1
    failures[source] = s
    return s


def _streak_reset(failures: dict, source: str) -> None:
    if source in failures:
        failures[source] = 0


def _compute_staleness(rep_dir: Path) -> int | None:
    """Days since the last saved report (banner truth; the site reads reports/)."""
    p = Path(rep_dir)
    if not p.exists():
        return None
    dates = sorted(
        (f.name[:10] for f in p.glob("*.json")),
        key=lambda d: datetime.strptime(d, "%Y-%m-%d").toordinal(),
        reverse=True,
    )
    if not dates:
        return None
    last = datetime.strptime(dates[0], "%Y-%m-%d")
    return (datetime.now(HK_TZ) - last.replace(tzinfo=HK_TZ)).days


def _upload(data_dir: Path) -> int:
    """Upload jobs.json via the R2 REST API (H3 creds in environment)."""
    import os

    import requests
    acct = os.environ.get("CF_ACCOUNT_ID")
    tok = os.environ.get("CF_API_TOKEN")
    if not (acct and tok):
        log.warning("upload skipped: CF_ACCOUNT_ID/CF_API_TOKEN not set (H3)")
        return 2
    bucket = os.environ.get("R2_BUCKET", "monitus-career-data")
    url = (f"https://api.cloudflare.com/client/v4/accounts/{acct}"
           f"/r2/buckets/{bucket}/objects/jobs.json")
    body = (data_dir / "jobs.json").read_bytes()
    resp = requests.put(
        url, headers={"Authorization": f"Bearer {tok}",
                      "Content-Type": "application/json"},
        data=body, timeout=60)
    if resp.status_code // 100 == 2:
        log.info("uploaded jobs.json → R2 %s (%d B)", bucket, len(body))
        return 0
    log.error("R2 upload failed: %d %s", resp.status_code, resp.text[:300])
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HK Job Engine daily pipeline")
    ap.add_argument("--dry-run", action="store_true",
                    help="replay fixtures, no requests")
    ap.add_argument("--sources", default="hkgov,jobsdb")
    ap.add_argument("--upload", action="store_true",
                    help="upload to R2 (needs H3 creds)")
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--fixtures-dir", default="fixtures")
    ap.add_argument("--profile", default="profile.yaml")
    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    data_dir = Path(args.data_dir) if args.data_dir else LOCAL_DATA_DIR
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]

    # Invariant 3 — total request budget; trip *before* exceeding
    if not args.dry_run and len(sources) * PER_SOURCE_CAP > TOTAL_CAP:
        log.error("sources (%d) × cap %d > total %d — aborting before breach",
                  len(sources), PER_SOURCE_CAP, TOTAL_CAP)
        return 2

    rr, payload = run_pipeline(
        sources=sources,
        data_dir=data_dir,
        fixtures_dir=Path(args.fixtures_dir),
        dry_run=args.dry_run,
        do_upload=args.upload,
        profile_path=Path(args.profile),
    )
    print(json.dumps(rr.to_dict(), indent=1, ensure_ascii=False))
    return 1 if rr.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
