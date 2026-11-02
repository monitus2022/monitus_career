# P3 — Unattended Docker daemon start

**Verdict: PASS.**

- CLI: `docker` 28.5.1 (engine), context `desktop-linux`.
- Docker Desktop app version: **4.48.0** (read from
  `/Applications/Docker.app/Contents/Info.plist`).
- Test: quit-killed daemon state → ran `open -g -a Docker` (headless,
  no UI) → polled `docker info`; **daemon answered in ~25 s** (≤120 s budget).
- Desktop version < 4.89 → the known boot-prompt caveat does **not** apply.
- conclusion: launchd-triggered `run.sh` can rely on `open -g -a Docker` +
  `docker info` polling; remains in `launchd/run.sh`.
