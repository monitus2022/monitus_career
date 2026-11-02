"""LIVE capture: JobsDB SSR job list → untracked local fixture.

One request (P6 finding: SSR serves the HK corpus; the v5 JSON does not).
"""

import sys
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def main() -> int:
    import requests
    from pipeline.sources import jobsdb

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else FIXTURES / "jobsdb_cards.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.Session() as s:
        pages, made, _ = jobsdb.fetch(s, keyword="", cap=1)
    if not pages:
        print("capture empty")
        return 1
    out.write_text(pages[0], encoding="utf-8")
    jobs, dropped = jobsdb.parse(pages[0])
    print(f"{made} request(s) → {out} ({len(pages[0])} B); "
          f"parsed {len(jobs)} rows, {dropped} dropped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
