"""LIVE capture: HK Gov quickview page → untracked local fixture + synthetic.

Usage (one-off, request-capped):
    python scripts/capture_hkgov.py [outfile]

 Makes exactly ONE request for the default list path. The captured payload
 lives ONLY in fixtures/ (untracked); a synthetic version with the same
 structure lives in fixtures/synthetic/ (tracked).
"""

import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def main() -> int:
    import requests  # local only — never imported into tests
    from pipeline.sources import hkgov

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else FIXTURES / "hkgov_quickview.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.Session() as s:
        s.headers.update({"User-Agent": "Mozilla/5.0 (monitus-career capture)"})
        raw, made, _ = hkgov.fetch(s, cap=1, pages=1, paths=hkgov.DEFAULT_LIST_PATHS[:1])
    if not raw:
        print("capture empty (source returned nothing)")
        return 1
    out.write_text(raw, encoding="utf-8")
    jobs, dropped = hkgov.parse(raw)
    print(f"{made} request(s) → {out} ({len(raw)} B); parsed {len(jobs)} rows, {dropped} dropped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
