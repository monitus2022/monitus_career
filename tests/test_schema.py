"""A2 — schema: ids/hashes, null-semantics rejection cases."""

from __future__ import annotations

import pytest

from pipeline.schema import (
    ContractViolation, Job, collapse_ws, content_hash, job_id,
)


def test_job_id_formula():
    assert job_id("hkgov", "23-26-9000001") == \
        __import__("hashlib").sha256(b"hkgov|23-26-9000001").hexdigest()[:16]


def test_content_hash_stability_and_input_sensitivity():
    h1 = content_hash("Senior Python Developer", "bigsound studio limited",
                      "$2,400  per\nday", ["Kln. Tong"], None, "X")
    # whitespace collapses to the same canonical payload
    h2 = content_hash("Senior Python Developer", "bigsound studio   limited",
                      "$2,400 per day", ["Kln. Tong"], None, "X")
    assert h1 == h2
    # locations ordering is canonical
    h3 = content_hash("T", None, None, ["A", "B"], None, "X")
    h4 = content_hash("T", None, None, ["B", "A"], None, "X")
    assert h3 == h4
    # but different values change it (§6.1: no casefolding in the formula)
    assert h1 != content_hash("Senior python Developer", "bigsound studio limited",
                              "$2,400 per day", ["Kln. Tong"], None, "X")


def test_collapse_ws():
    assert collapse_ws("  a\n\tb   C \n ") == "a b C"


@pytest.mark.parametrize("kwargs", [
    {"title": "", "source_job_id": "x"},
    {"title": "N/A", "source_job_id": "x"},
    {"title": "  ", "source_job_id": "x"},
    {"title": "T", "source_job_id": ""},
    {"title": "T", "source_job_id": "x", "salary_period": "month"},
    {"title": "T", "source_job_id": "x", "salary_min": 100},
    {"title": "T", "source_job_id": "x", "salary_max": 100, "salary_period": "month"},
    {"title": "T", "source_job_id": "x", "salary_min": None,
     "salary_max": 100, "salary_period": "month"},
    {"title": "T", "source_job_id": "x", "salary_period": "fortnight"},
    {"title": "T", "source_job_id": "x", "tier": "S"},
    {"title": "T", "source_job_id": "x", "status": "maybe"},
])
def test_contract_rejections(kwargs):
    with pytest.raises(ContractViolation):
        Job(source="hkgov", **kwargs)


def test_roundtrip_through_dict():
    j = Job(source="hkgov", source_job_id="23-26-9000002", title="Kitchen Technician",
            salary_raw="$21,500 - $23,000 per month", salary_min=21500,
            salary_max=23000, salary_period="month",
            locations_raw=["Kln. Peninsula"], first_seen_at="2026-11-01T06:00:00+08:00")
    j.compute_hashes()
    j2 = Job.from_dict(j.to_dict())
    assert j2.to_dict() == j.to_dict()


def test_month_equivalents():
    assert Job(source="s", source_job_id="x", title="T",
               salary_min=100, salary_period="hour").month_equiv_min() == 100 * 8 * 22
    assert Job(source="s", source_job_id="y", title="T",
               salary_min=800, salary_period="day").month_equiv_min() == 800 * 22
    assert Job(source="s", source_job_id="z", title="T",
               salary_min=24000, salary_period="month").month_equiv_min() == 24000
