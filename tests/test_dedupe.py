"""B6 — dedupe §6.3: keys, clustering, anonymous-row exclusion, idempotence."""

from __future__ import annotations

from pipeline.dedupe import apply_dedupe, cluster_id, dedupe_key, merge_into
from pipeline.normalize import norm_operand
from pipeline.schema import Job


def test_norm_operand_spec():
    # casefold, collapse ws, strip punctuation except &, drop company suffixes
    assert norm_operand("Foo & Co Ltd") == "foo &"
    assert norm_operand("Bigsound Studio Limited") == "bigsound studio"
    assert norm_operand("MEGA-TECH, Inc.") == "mega tech"
    assert norm_operand(None) == ""


def test_dedupe_key_formula():
    key = dedupe_key("Zenari Labs Ltd", "Junior Software Developer", "Kowloon City")
    assert key == "zenari labs||junior software developer||Kowloon City"


def test_cluster_id_deterministic():
    k = dedupe_key("A Ltd", "T", "Wan Chai")
    assert cluster_id(k) == cluster_id(dedupe_key("A limited", "T", "Wan Chai"))


def test_cross_source_duplicate_pair_clusters():
    jobs, _ = _dup_pair()
    apply_dedupe(jobs)
    a, b = jobs
    assert a.cluster_id is not None
    assert a.cluster_id == b.cluster_id


def test_anonymous_hkgov_rows_excluded_from_clustering():
    j1 = Job(source="hkgov", source_job_id="1", title="Security Guard(Kowloon Tong)")
    j2 = Job(source="hkgov", source_job_id="2", title="Security Guard(Kowloon Tong)")
    j1.locations_raw = ["Kln. Tong"]; j1.districts = ["Kowloon City"]; j1.region_norm = "Kowloon City"
    j2.locations_raw = ["Kln. Tong"]; j2.districts = ["Kowloon City"]; j2.region_norm = "Kowloon City"
    apply_dedupe([j1, j2])
    assert j1.cluster_id is None and j2.cluster_id is None


def _dup_pair():
    a = Job(source="jobsdb", source_job_id="900000001",
            title="Junior Software Developer", company="Zenari Labs Ltd",
            locations_raw=["Kowloon Tong"], districts=["Kowloon City"],
            region_norm="Kowloon City")
    b = Job(source="recruit", source_job_id="R-2026-0002",
            title="Junior Software Developer", company="Zenari Labs",
            locations_raw=["Kln. Tong"], districts=["Kowloon City"],
            region_norm="Kowloon City")
    a.compute_hashes(); b.compute_hashes()
    return [a, b], 0


def test_merge_into_preserves_first_seen_on_content_change():
    existing = Job(source="jobsdb", source_job_id="42", title="Elderly Care Assistant",
                   company="C", first_seen_at="2026-10-01T06:00:00+08:00")
    existing.compute_hashes(); existing.ensure_seen("2026-10-01T06:00:00+08:00")
    new_h = Job(source="jobsdb", source_job_id="42", title="Elderly Care Assistant Jr",
                company="C")
    new_h.compute_hashes()
    merged = merge_into([new_h], [existing])
    assert merged[0].first_seen_at == "2026-10-01T06:00:00+08:00"
    # unchanged content: nothing changes
    new_same = Job(source="jobsdb", source_job_id="42", title="Elderly Care Assistant",
                   company="C")
    new_same.compute_hashes()
    merged2 = merge_into([new_same], [existing])
    assert merged2[0].first_seen_at == existing.first_seen_at
    assert merged2[0].content_hash == existing.content_hash
