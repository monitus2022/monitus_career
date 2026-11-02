"""A4 — the trap fixtures, plus adapter contract (A3 harness on both sources)."""

from __future__ import annotations

from pathlib import Path

from pipeline.sources import hkgov, jobsdb
from tests.harness import check_contract, coverage_report

FIX = Path(__file__).parent.parent / "fixtures" / "synthetic"
HKGOV_RAW = (FIX / "hkgov_quickview.html").read_text(encoding="utf-8")
HKGOV_BROKEN = (FIX / "hkgov_broken.html").read_text(encoding="utf-8")
JOBSDB_RAW = (FIX / "jobsdb_cards.html").read_text(encoding="utf-8")
JOBSDB_BROKEN = (FIX / "jobsdb_broken.html").read_text(encoding="utf-8")


def test_hkgov_traps():
    jobs, dropped = hkgov.parse(HKGOV_RAW)
    assert dropped == 0  # clean synthetic: all rows contract-valid
    assert len(jobs) == 6
    jobs_broken, dropped_broken = hkgov.parse(HKGOV_BROKEN)
    assert dropped_broken == 1 and len(jobs_broken) == 0  # T7: missing order no

    by_id = {j.source_job_id: j for j in jobs}

    # T1 — day-rate salary: raw number kept per-period, month-equivalent ×22
    t1 = by_id["23-26-9000001"]
    assert t1.salary_min == 2400 and t1.salary_period == "day"
    assert t1.month_equiv_min() == 2400 * 22

    # T2 — "Kln. Peninsula": no single district; raw retained
    t2 = by_id["23-26-9000002"]
    assert t2.districts == [] and t2.locations_raw == ["Kln. Peninsula"]
    assert t2.region_norm == "unknown"

    # T3 — "Central - United States": non-HK marker ⇒ no HK district
    t3 = by_id["23-26-9000003"]
    assert "Central and Western" not in (t3.districts or [])
    assert t3.region_norm == "unknown"

    # T4 — anonymous row ("**"): company stays None, title marker stripped, district maps
    t4 = by_id["23-26-9000004"]
    assert t4.company is None
    assert t4.title == "Security Guard(Kowloon Tong)"
    assert t4.districts == ["Kowloon City"]

    # T6 — "Negotiable": salary regex miss ⇒ all-null, raw retained verbatim
    t6 = by_id["23-26-9000005"]
    assert t6.salary_raw == "Negotiable"
    assert t6.salary_min is None and t6.salary_max is None and t6.salary_period is None
    assert t6.anywhere_in_hk is True

    # contract + coverage on the whole capture
    assert check_contract(jobs) == []


def test_jobsdb_traps():
    jobs, dropped = jobsdb.parse(JOBSDB_RAW)
    assert dropped == 0  # clean synthetic (all cards contract-valid)
    ids = {j.source_job_id for j in jobs}
    assert "900000101" in ids and "900000103" in ids and "900000104" in ids

    by_id = {j.source_job_id: j for j in jobs}
    # salary variants parse (per-period raw, month-equiv computed elsewhere)
    assert by_id["900000101"].salary_min == 30000
    assert by_id["900000103"].salary_max == 50000
    assert by_id["900000104"].salary_period == "day"
    assert by_id["900000105"].company is None  # "Confidential" → null semantics


def test_content_hash_stable_across_parses():
    """B1 acceptance: content_hash stable across 2 parses of the same capture."""
    j1, _ = hkgov.parse(HKGOV_RAW)
    j2, _ = hkgov.parse(HKGOV_RAW)
    hash1 = {j.source_job_id: j.content_hash for j in j1}
    hash2 = {j.source_job_id: j.content_hash for j in j2}
    assert hash1 == hash2

    k1, _ = jobsdb.parse(JOBSDB_RAW)
    k2, _ = jobsdb.parse(JOBSDB_RAW)
    assert {j.source_job_id: j.content_hash for j in k1} == \
           {j.source_job_id: j.content_hash for j in k2}


def test_coverage_report_smoke():
    jobs, _ = hkgov.parse(HKGOV_RAW)
    db, _ = jobsdb.parse(JOBSDB_RAW)
    rep = coverage_report(jobs + db)
    assert rep["hkgov"]["salary"] >= 75.0  # 4/5 synthetic salaries parse as values
    assert rep["jobsdb"]["districts"] >= 75.0


def test_harness_on_dummy_adapter():
    """A3 acceptance: harness runs on a dummy adapter."""
    class DummyAdapter:
        source = "dummy"

        @staticmethod
        def parse(raw):
            return ([hkgov.Job(source="dummy", source_job_id="d1", title="T",
                               salary_min=14000, salary_period="month",
                               locations_raw=["Wan Chai"])], 0)

    from pipeline.schema import Job as RealJob
    jobs, dropped = DummyAdapter.parse("")
    assert dropped == 0
    errs = check_contract(jobs)
    assert errs == []
    cov = coverage_report(jobs)
    assert cov["dummy"]["salary"] == 100.0
    assert cov["dummy"]["company"] == 0.0  # missing field counted as not published
    _ = RealJob
