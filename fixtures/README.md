# fixtures/

- `synthetic/` — **tracked in git**. Hand-made, synthetic HTML/JSON used by
  contract tests. Must never contain real scraped bytes.
- anything else under this dir — **untracked**, captured from LIVE sources
  (e.g. `hkgov_joblist.html`). CI runs a privacy tripwire to ensure no
  captured payload ends up in a tracked file.

Captures are recreated with `scripts/capture_*.py` (LIVE, request-capped).
