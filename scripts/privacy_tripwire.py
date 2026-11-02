"""Privacy tripwire (Invariant 1 — no scraped data in git, A5).

Scraped payloads live ONLY in untracked ``fixtures/`` files. This tripwire
checks that no *tracked* file shares a contiguous ≥200-char slice with any
untracked capture; fallback pattern: long base64 blobs (capture page
compression artifacts).

Synthetic fixtures (``fixtures/synthetic/``, tracked) deliberately mirror
structure but contain fabricated values, so they never match a real capture
slice.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SLICE_LEN = 200


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=ROOT,
    ).stdout.split()
    return [ROOT / p for p in out]


def main() -> int:
    import re

    captures: list[tuple[Path, str]] = []
    if (ROOT / "fixtures").exists():
        for p in (ROOT / "fixtures").rglob("*"):
            if not p.is_file() or "synthetic" in p.parts or p.name == "README.md":
                continue
            if p.suffix in {".html", ".json", ".har", ".txt"}:
                try:
                    captures.append(
                        (p, p.read_text(encoding="utf-8", errors="replace")))
                except OSError:
                    pass

    needles: set[str] = set()
    for _, text in captures:
        for i in range(0, max(0, len(text) - SLICE_LEN), 137):
            needles.add(text[i:i + SLICE_LEN])
    rx_long_b64 = re.compile(r"[A-Za-z0-9+/]{600,}")

    bad: list[str] = []
    for path in tracked_files():
        if not path.exists() or path.stat().st_size > 20_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for needle in needles:
            if needle in text:
                bad.append(
                    f"{path.relative_to(ROOT)} contains a 200-char slice of "
                    f"a real capture (elided)")
                break
        else:
            if rx_long_b64.search(text):
                bad.append(f"{path.relative_to(ROOT)} contains a long base64 blob")

    if bad:
        for line in bad:
            print(f"PRIVACY TRIPWIRE: {line}")
        print("Refusing: scraped data appears to be committed (Invariant 1).")
        return 1
    print("privacy tripwire clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
