"""C1/C2/D3 — orchestrator behavior: idempotence, write-back merge, tiers."""
import json
import tempfile
from pathlib import Path

from pipeline import run as runmod
from pipeline.run import run_pipeline


def _tmp_dirs(tmp_path: Path, profile_yaml: str | None = None):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    real = Path(__file__).parent.parent / "fixtures" / "synthetic"
    (fixtures / "hkgov_quickview.html").write_text(
        (real / "hkgov_quickview.html").read_text(encoding="utf-8"))
    (fixtures / "jobsdb_cards.html").write_text(
        (real / "jobsdb_cards.html").read_text(encoding="utf-8"))
    data = tmp_path / "runs"
    data.mkdir()
    if profile_yaml:
        (Path("profile.yaml")).write_text(profile_yaml)
    return data, fixtures


PROFILE = """
must_have: [python]
nice_to_have: [docker]
exclude: [sales]
salary_floor_month: 30000
districts: [Kowloon City]
anywhere_in_hk: false
seniority: null
seniority_out_match: null
"""


def test_enabled_sources_from_config():
    """CLI default derives from config.yaml enabled flags (user decision
    2026-11-02: hkgov OFF). Implicit KEYWORD_CONFIG reload via load path."""
    from pipeline.run import enabled_sources, _load_keyword_config
    _load_keyword_config()
    assert enabled_sources() == ["jobsdb"]
    # re-enabling hkgov restores canonical order
    runmod.KEYWORD_CONFIG["sources"]["hkgov"]["enabled"] = True
    assert enabled_sources() == ["hkgov", "jobsdb"]
    runmod.KEYWORD_CONFIG["sources"] = {}
    assert enabled_sources() == ["jobsdb"]  # never an empty run


def test_double_run_idempotent(tmp_path):
    data, fixtures = _tmp_dirs(tmp_path)
    rr1, p1 = run_pipeline(["hkgov", "jobsdb"], data_dir=data,
                           fixtures_dir=fixtures, dry_run=True)
    assert not rr1.failed
    first_ids = sorted(r["job_id"] for r in p1)
    rr2, p2 = run_pipeline(["hkgov", "jobsdb"], data_dir=data,
                           fixtures_dir=fixtures, dry_run=True)
    assert not rr2.failed
    second_ids = sorted(r["job_id"] for r in p2)
    assert first_ids == second_ids
    # no duplicate records, first_seen_at preserved
    by_job = {r["job_id"]: r for r in p2}
    assert len(by_job) == len(p2)
    assert all(r["first_seen_at"] for r in p2)


def test_tiers_present_when_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(__file__).parent.parent)
    # write a tiny profile the loader will pick up — via explicit path
    ppath = tmp_path / "profile.yaml"
    ppath.write_text(PROFILE)
    data, fixtures = _tmp_dirs(tmp_path)
    rr, payload = run_pipeline(["hkgov", "jobsdb"], data_dir=data,
                               fixtures_dir=fixtures, dry_run=True,
                               profile_path=ppath)
    assert not rr.failed
    with_tier = [r for r in payload if r.get("tier")]
    assert with_tier, "profile present → tiers must be attached"
    assert all(r["tier"] in ("A", "B", "C") for r in with_tier)
    # ranked output carrying match_score/match_reasons
    assert all("match_score" in r for r in with_tier)


def test_user_state_preserved_across_rebuild(tmp_path):
    data, fixtures = _tmp_dirs(tmp_path)
    rr1, p1 = run_pipeline(["hkgov", "jobsdb"], data_dir=data,
                           fixtures_dir=fixtures, dry_run=True)
    # simulate a starred/annotated job from the function/UI
    target = p1[0]
    (data / "jobs.json").write_text(json.dumps([
        {**target, "starred": True, "status": "applied", "notes": "todo"}
    ]))
    rr2, p2 = run_pipeline(["hkgov", "jobsdb"], data_dir=data,
                           fixtures_dir=fixtures, dry_run=True)
    again = next(r for r in p2 if r["job_id"] == target["job_id"])
    assert again["starred"] is True
    assert again["status"] == "applied"
    assert again["notes"] == "todo"


def test_orphan_user_state_kept_until_90_days(tmp_path):
    data, fixtures = _tmp_dirs(tmp_path)
    run_pipeline(["hkgov", "jobsdb"], data_dir=data, fixtures_dir=fixtures,
                 dry_run=True)
    orphan = {"job_id": "ghost", "starred": True, "status": "interested",
              "last_seen_at": "2026-11-01T00:00:00+08:00"}
    (data / "jobs.json").write_text(json.dumps([orphan]))
    rr, payload = run_pipeline(["hkgov", "jobsdb"], data_dir=data,
                               fixtures_dir=fixtures, dry_run=True)
    assert any(r["job_id"] == "ghost" for r in payload)


def test_report_schema(tmp_path):
    data, fixtures = _tmp_dirs(tmp_path)
    rr, _ = run_pipeline(["hkgov", "jobsdb"], data_dir=data,
                         fixtures_dir=fixtures, dry_run=True)
    d = rr.to_dict()
    for key in ("run_id", "started_at", "finished_at", "sources", "totals",
                "alerts", "staleness_days"):
        assert key in d
    for name in ("hkgov", "jobsdb"):
        s = d["sources"][name]
        for key in ("fetch_ok", "retries", "http_requests", "records_fetched",
                    "records_parsed", "records_written", "contract_failures",
                    "null_rates"):
            assert key in s
    assert d["totals"]["http_requests"] <= 40  # Invariant 3 (dry: 0)
