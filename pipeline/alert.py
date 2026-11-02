"""Alerting (G1) — macOS notification + alerts.log + report flag.

Fires on: 2 consecutive day-level failures of a source, systemic breach,
scheduler failure. Never per-retry.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from .schema import HK_TZ


def _notify_macos(title: str, body: str) -> None:
    try:
        script = (
            f'display notification "{body}\" with title \"{title}\"'
        )
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, timeout=10,
        )
    except Exception:  # pragma: no cover — notification is best-effort
        pass


def log_alert(report: "object", message: str, root: Path | str = ".") -> None:
    """Append to alerts.log, macOS-notify, and flag the run report."""
    root = Path(root)
    log_path = root / "alerts.log"
    stamp = datetime.now(HK_TZ).isoformat(timespec="seconds")
    line = f"{stamp}\t{message}"
    with log_path.open("a") as fh:
        fh.write(line + "\n")
    try:
        report.alerts.append(message)  # type: ignore[attr-defined]
    except AttributeError:
        pass
    _notify_macos("HK Job Engine", message)


def failure_streak(alerts_log: Path | str, source: str) -> int:
    """Read the alerts.log/run history for consecutive day-level failures.

    The authoritative streak is maintained by run.py in ``runs/failures.json``;
    this helper is for tests/manual inspection.
    """
    p = Path(alerts_log)
    if not p.exists():
        return 0
    streak = 0
    for line in reversed(p.read_text().splitlines()):
        if f"source failed day-level: {source}" in line:
            streak += 1
        elif streak:
            break
    return streak
