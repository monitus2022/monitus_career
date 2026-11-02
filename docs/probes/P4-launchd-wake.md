# P4 — launchd wake-catch-up

**Verdict: BLOCKED (needs one human action).**

Per the build plan, P4 requires the human to **sleep and wake the Mac once**
so a `StartCalendarInterval` 2-min-into-the-future test plist can prove
missed-run-then-wake fires.

- A harmless test plist + test script are available at
  `launchd/org.monitus.career.plist` (real pipeline) — the wake test procedure
  is written in `docs/cloud-bootstrap.md` §5 so the human can do it during H3.
- Decision rule implemented regardless: `launchd/run.sh` registers a
  `StartInterval` fallback wake-server approach (see runbook §"scheduler") so a
  missed 06:00 run re-fires on hard boot/wake. Once P4 is observed
  post-wake, the fallback can be trimmed.
- Tracked in `BLOCKERS.md` (B-4).
