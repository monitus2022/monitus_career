"""B5 — tiered failure policy §6.5: CI / per-record / systemic paths."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pipeline.report import SourceStats, coverage_drop_breach, load_baselines
from pipeline.run import run_pipeline
from pipeline.sources import hkgov, jobsdb

FIX = Path(__file__).parent.parent / "fixtures" / "synthetic"
HKGOV_BROKEN = (FIX / "hkgov_broken.html").read_text(encoding="utf-8")
JOBSDB_BROKEN = (FIX / "jobsdb_broken.html").read_text(encoding="utf-8")


def test_per_record_drop_and_count():
    """Adapter contract: violations are dropped + counted (§6.5 per-record)."""
    hkgov_jobs, hkgov_dropped = hkgov.parse(HKGOV_BROKEN)
    assert hkgov_dropped == 1 and len(hkgov_jobs) == 0
    for j in hkgov_jobs:
        assert j.title and j.source_job_id  # only contract-valid records return

    db_jobs, db_dropped = jobsdb.parse(JOBSDB_BROKEN)
    # SSR broken fixture: single invalid card (empty title)
    assert db_dropped == 1 and len(db_jobs) >= 1
    for j in db_jobs:
        assert j.title and j.source_job_id


def test_pipe_no_fixture_data_day_failure(tmp_path):
    """Missing fixture files ⇒ day-level source failure, run still 'green'
    for other sources; alert only after 2 consecutive failures."""
    rr, payload = run_pipeline(["hkgov"], data_dir=tmp_path / "runs",
                               fixtures_dir=tmp_path / "fixtures", dry_run=True)
    assert payload == []
    assert not rr.failed  # single source missing ≠ systemic; banner shows gap


def test_clean_dry_run_contract_counts_zero(tmp_path):
    real = Path(__file__).parent.parent / "fixtures" / "synthetic"
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "hkgov_quickview.html").write_text(
        (real / "hkgov_quickview.html").read_text(encoding="utf-8"))
    (fixtures / "jobsdb_cards.html").write_text(
        (real / "jobsdb_cards.html").read_text(encoding="utf-8"))
    rr, payload = run_pipeline(["hkgov", "jobsdb"], data_dir=tmp_path / "runs",
                               fixtures_dir=fixtures, dry_run=True)
    assert not rr.failed
    assert rr.sources["hkgov"].contract_failures == 0
    assert rr.sources["jobsdb"].contract_failures == 0


def test_systemic_contract_failure_fails_run(tmp_path):
    """>5% contract-failure rate ⇒ run fails, nothing written."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    # clean page first, then inject 4 missing-order-number rows (>5% breach)
    raw = (FIX / "hkgov_quickview.html").read_text(encoding="utf-8")
    broken = raw
    for i in range(1, 5):
        broken = broken.replace(f'value="23-26-900000{i}"', f'value=""')
    (fixtures / "hkgov_quickview.html").write_text(broken)

    rr, payload = run_pipeline(["hkgov"], data_dir=tmp_path / "runs",
                               fixtures_dir=fixtures, dry_run=True)
    assert rr.failed
    assert "contract-failure rate" in (rr.fail_reason or "")
    assert payload == []
    assert not (tmp_path / "runs" / "jobs.json").exists()


def test_coverage_drop_systemic_breach(tmp_path):
    """null-rate jump >30pp vs a 7-day baseline ⇒ fail run, write nothing."""
    rep_dir = tmp_path / "runs" / "reports"
    rep_dir.mkdir(parents=True)
    # create a baseline report with hkgov company null-rate 0%
    old = {"run_id": "2026-10-25T06:00:01+08:00", "started_at": "", "finished_at": "",
           "sources": {"hkgov": {"fetch_ok": True, "retries": 0, "http_requests": 1,
                                 "records_fetched": 10, "records_parsed": 10,
                                 "records_written": 10, "contract_failures": 0,
                                 "null_rates": {"company": 0.0}}},
           "totals": {}, "alerts": [], "staleness_days": 0}
    (rep_dir / "2026-10-25.json").write_text(json.dumps(old))

    stats = SourceStats(name="hkgov")
    stats.null_rates = {"company": 45.0}  # +45pp against the baseline
    breaches = coverage_drop_breach("hkgov", stats, load_baselines(rep_dir))
    assert breaches and "company" in breaches[0]

    stats2 = SourceStats(name="hkgov")
    stats2.null_rates = {"company": 5.0}
    assert coverage_drop_breach("hkgov", stats2, load_baselines(rep_dir)) == []


def test_two_consecutive_day_failures_alert(tmp_path):
    """Source failing 2 consecutive day-level runs fires once (G1 tier)."""
    data = tmp_path / "runs"
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    # no fixture files at all ⇒ source-level fetch failure both runs
    rr1, p1 = run_pipeline(["hkgov"], data_dir=data, fixtures_dir=fixtures,
                           dry_run=True)
    assert p1 == []
    rr2, p2 = run_pipeline(["hkgov"], data_dir=data, fixtures_dir=fixtures,
                           dry_run=True)
    assert p2 == []
    failures = json.loads((data / "failures.json").read_text())
    assert failures["hkgov"] == 2
    alerts_log = (data.parent / "alerts.log")
    # alert.log writes to data_dir root
    alerted = (data / "alerts.log").read_text()
    assert "source failed day-level: hkgov" in alerted


def test_real_run_cap_violation_trips(tmp_path, capsys):
    """Sources × cap > total → abort BEFORE any request (Invariant 3)."""
    import subprocess, sys
    code = subprocess.run(
        [sys.executable, "-m", "pipeline.run", "--sources=hkgov,jobsdb,ctgoodjobs,recruit,extra"],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent,
    )
    assert code.returncode == 2
    assert "aborting" in code.stderr
