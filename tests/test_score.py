"""D1 — deterministic scorer §6.8; D3 ranked output; ties reproducible."""

from __future__ import annotations

from pipeline.score import apply_ranking, score
from pipeline.schema import Job


def mk(title, company=None, smin=None, smax=None, period="month",
       districts=None, region="unknown"):
    has_sal = smin is not None or smax is not None
    return Job(
        source="syn", source_job_id=title,
        title=title, company=company,
        salary_min=smin, salary_max=smax,
        salary_period=period if has_sal else None,
        districts=districts or [], region_norm=region,
    )


PROFILE = {
    "must_have": ["python"], "nice_to_have": ["docker"],
    "exclude": ["sales"], "salary_floor_month": 30000,
    "districts": ["Kowloon City"], "anywhere_in_hk": False,
    "seniority": None, "seniority_out_match": r"regex:(?i)\binterns?\b",
}


def test_score_formula():
    j = mk("Senior Python Developer", company="Zenari L1", smin=32000,
           districts=["Kowloon City"], region="Kowloon City")
    s, reasons, tier = score(j, PROFILE)
    # 3(must) + 1(nice? no 'docker') + 2(floor ok) + 1(district) = 6 → B
    assert s == 6 and tier == "B"
    assert set(reasons) == {"must:python", "salary_ok", "district"}


def test_tier_boundaries():
    a = mk("Python Backend Lead docker", company="Zenari L2", smin=31000,
           districts=["Kowloon City"], region="Kowloon City")
    s, _, tier = score(a, PROFILE)  # 3 + 1(nice docker) + 2 + 1 = 7 → B
    assert s == 7 and tier == "B"

    # maybe must+nice+floor+district only reaches 7 without a second nice hit
    j2 = mk("Python Architect docker docker kubernetes", company="Zenari L2b",
            smin=31000, districts=["Kowloon City"], region="Kowloon City")
    s, _, tier = score(j2, PROFILE)  # distinct nice key hits are 1 per keyword
    assert s == 7 and tier == "B"

    c = mk("Junior Revenue Sales Executive", company="Zenari L3", smin=31000)
    s, reasons, tier = score(c, PROFILE)  # exclude hit → C (deal-breaker)
    assert tier == "C" and any(r.startswith("deal:exclude:sales") for r in reasons)


def test_deal_breaker_demotes_never_hides():
    j = mk("Python Unbeatable Sales & docker", company="Zenari L4", smin=50000,
           districts=["Kowloon City"], region="Kowloon City")
    ranked = apply_ranking([j], PROFILE)
    # score still tallies positive hits (§6.8): 3 must + 1 nice + 2 salary + 1 district
    assert ranked[0].tier == "C" and ranked[0].match_score == 7
    # salary floor breach below → also a deal-breaker
    jd = mk("Python Architect", company="Zenari L5", smin=20000)
    _, reasons, tier = score(jd, PROFILE)
    assert tier == "C" and any(r.startswith("deal:salary<30000") for r in reasons)


def test_salary_floor_period_adjusted():
    # day ×22 → 1500/day = 33 000/month ≥ 30 000 → no breach
    day = mk("Nurse Python duelist", company="Z L6", smin=1500, period="day")
    _, reasons, tier = score(day, PROFILE)
    assert not any(r.startswith("deal:salary<30000") for r in reasons) and tier != "C"
    # hour ×8×22 → 150/hr = 26 400 < 30 000 → breach
    hr = mk("Python per-hour contract", company="Z L7", smin=150, period="hour")
    _, reasons, tier = score(hr, PROFILE)
    assert tier == "C"


def test_seniority_out_of_band():
    p = {**PROFILE, "seniority_out_match": r"regex:(?i)\binterns?\b"}
    j = mk("Data Intern", company="Z L8")
    _, reasons, tier = score(j, p)
    assert tier == "C" and any(r.startswith("deal:seniority_out_of_band") for r in reasons)


def test_seniority_band_required():
    p = {**PROFILE, "salary_floor_month": None,
         "seniority": r"regex:(?i)\b(senior|lead|principal)\b"}
    ok = mk("Platform Lead Python", company="Z L10")
    _, r_ok, t_ok = score(ok, p)
    assert not any(r.startswith("deal:seniority_out_of_band") for r in r_ok)
    bad = mk("Python Padawan", company="Z L11")
    _, r_bad, t_bad = score(bad, p)
    assert t_bad == "C" and any(r.startswith("deal:seniority_out_of_band") for r in r_bad)


def test_ties_reproducible():
    """Ties: score desc, then title, then job_id — order stable across runs."""
    r1 = apply_ranking([
        mk("Python Engineer A", company="Tie Co 1", smin=31000),
        mk("Python Engineer B", company="Tie Co 2", smin=31000),
        mk("Python Engineer C", company="Tie Co 3", smin=36000),
    ], PROFILE)
    r2 = apply_ranking([
        mk("Python Engineer C", company="Tie Co 3", smin=36000),
        mk("Python Engineer B", company="Tie Co 2", smin=31000),
        mk("Python Engineer A", company="Tie Co 1", smin=31000),
    ], PROFILE)
    assert [j.title for j in r1] == [j.title for j in r2]
    # stable tie order is title-ascending among equal scores
    tied = [j.title for j in r1 if j.match_score == r1[0].match_score]
    assert tied == sorted(tied)


def test_rank_never_filters():
    jobs = [mk("Anti Sales Python", company="Z L9", smin=50000)]
    ranked = apply_ranking(jobs, PROFILE)
    assert len(ranked) == 1  # deal-breakers demote, never hide
    assert ranked[0].tier == "C"


def test_must_desc_hit_weaker_evidence():
    """Synopsis mentions must-have but title doesn't → +2 not +3 (deviation
    logged in PROGRESS.md: desc evidence is weaker than title evidence)."""
    j = mk("Platform Engineer", smin=32000, districts=["Kowloon City"],
           region="Kowloon City")
    j.short_desc = "Comfortable with python; some SQL"
    s, reasons, tier = score(j, PROFILE)
    # 2(desc) + 2(floor) + 1(district) = 5 → B (would be C with no hit)
    assert s == 5 and tier == "B"
    assert "must:desc:python" in reasons and "must:python" not in reasons

    # title hit outranks desc hit for the same keyword (exclusive, not both)
    t = mk("Python Developer", smin=32000, districts=["Kowloon City"],
           region="Kowloon City")
    t.short_desc = "python-heavy stack"
    s2, r2, _ = score(t, PROFILE)
    assert s2 == 3 + 2 + 1  # must via title only
    assert "must:python" in r2 and "must:desc:python" not in r2

    # regex keywords also hit the synopsis
    rx_profile = dict(PROFILE)
    rx_profile["must_have"] = ["regex:(?i)\\bllm\\b"]
    r = mk("Data Engineer", smin=32000, districts=["Kowloon City"],
           region="Kowloon City")
    r.short_desc = "Experience with LLM pipelines a plus"
    s3, r3, _ = score(r, rx_profile)
    assert s3 == 2 + 2 + 1 and any(x.startswith("must:desc:") for x in r3)


def test_short_desc_never_serialized(tmp_path):
    """Privacy invariant: the synopsis is scoring evidence only — it must not
    reach jobs.json (to_dict) nor shift content_hash."""
    from pipeline.schema import content_hash

    a = mk("Data Engineer", smin=32000)
    b = mk("Data Engineer", smin=32000)
    b.short_desc = "python, sql, aws"
    assert "short_desc" not in a.to_dict()
    assert a.content_hash == b.content_hash  # hash ignores desc

    # and the live adapter assigns it from the card
    from pipeline.sources import jobsdb
    raw = (tmp_path / "x.html")
    raw.write_text((  # minimal single-card page
        '<div data-automation="normalJob">'
        '<a href="/job/777" data-automation="jobTitle">Qa Analyst</a>'
        '<span data-automation="jobShortDescription">python+cypress</span>'
        "</div>"), encoding="utf-8")
    jobs, dropped = jobsdb.parse(raw.read_text(encoding="utf-8"))
    assert dropped == 0 and jobs[0].short_desc == "python+cypress"


def test_no_profile_no_ranking():
    j = [mk("Anything", company="X")]
    ranked = apply_ranking(j, {})
    assert ranked[0].tier is None and ranked[0].match_score is None
