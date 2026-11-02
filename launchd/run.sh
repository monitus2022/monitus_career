#!/bin/zsh
# launchd/run.sh — C4: unattended daily run entrypoint (org.monitus.career.pipeline)
#
# Order per P3/P4 probes + runbook:
#   1. start Docker headlessly if the daemon is down (P3: ~25 s, poll ≤120 s)
#   2. caffeinate-wrapped compose run (prevents sleep mid-run)
#   3. on failure: alert (non-zero exit → launchd retries next schedule)
set -u

cd "$(dirname "$0")/.."   # repo root

mkdir -p runs
LOG="runs/$(date +%Y-%m-%d).log"
exec > >(tee -a "$LOG") 2>&1

echo "=== pipeline start $(date -u +%FT%TZ) ==="

# 1. daemon up? (see above)
if ! docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; then
  echo "docker daemon down — starting Docker Desktop headlessly (P3)"
  open -g -a Docker
  tries=0
  until docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ $tries -ge 12 ]; then           # 12 × 10 s = 120 s budget
      echo "docker info fails after polling — alert + non-zero exit (runbook)"
      /usr/bin/osascript -e 'display notification "Docker daemon did not start; run skipped" with title "HK Job Engine"'
      echo "docker daemon start FAILED $(date -u +%FT%TZ)" >> alerts.log
      exit 1
    fi
    sleep 10
  done
fi

# 2. double-run guard: skip if today's report already exists and is not failed
TODAY=$(date +%F)
REPORT="runs/reports/$TODAY.json"
if [ -s "$REPORT" ] && ! grep -q '"failed": true' "$REPORT"; then
  echo "today's run already succeeded ($REPORT) — skip"
  exit 0
fi

# 3. the run (live fetch+parse→dedupe→merge→report→upload-if-creds)
caffeinate -i docker compose run --rm pipeline python -m pipeline.run \
  --data-dir=/app/runs --upload
rc=$?

echo "=== pipeline end rc=$rc $(date -u +%FT%TZ) ==="
if [ $rc -ne 0 ]; then
  /usr/bin/osascript -e "display notification \"daily run failed (rc=$rc)\" with title \"HK Job Engine\""
  echo "pipeline run FAILED rc=$rc $(date -u +%FT%TZ)" >> alerts.log
fi
exit $rc
