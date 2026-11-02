"""Embeddings recall (D2) — local ollama ``nomic-embed-text`` (P5: ON).

Union into candidates before scoring, per build-plan §7: recall never
*filters* (Invariant 5) — it only widens the candidate field the deterministic
scorer would otherwise under-read (keywords miss paraphrases). Graceful-off
whenever ollama is unreachable (keyword-only degradation + report flag).
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import urllib.request

log = logging.getLogger(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/embed")
MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
TOP_K = 50


def _embed(texts: list[str]) -> list[list[float]] | None:
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps({"model": MODEL, "input": texts}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read()).get("embeddings")
    except Exception as exc:  # noqa: BLE001 — never fatal (runbook)
        log.warning("embeddings unavailable: %s", exc)
        return None


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def recall_query(profile: dict) -> str:
    return ". ".join(profile.get("must_have") or []) or "information technology"


def apply_recall(jobs: list, profile: dict, top_k: int = TOP_K) -> str:
    """Annotate jobs recalled by embeddings; returns report-mode string.

    - ``embedding_recall`` — ollama answered, top_k annotated
    - ``keyword_only`` — ollama unavailable (graceful degradation, runbook §)
      or no profile (nothing to recall *for*)
    - ``off`` — embeddings intentionally disabled
    """
    if os.environ.get("EMBEDDINGS", "") == "off":
        return "off"
    if not profile:
        return "keyword_only"

    t0 = time.monotonic()
    texts = [recall_query(profile)] + [
        f"{j.title}. {j.company or ''}. {'; '.join(j.locations_raw)}"
        for j in jobs
    ]
    vecs = _embed(texts)
    if vecs is None or len(vecs) != len(texts):
        return "keyword_only"

    q = vecs[0]
    sims = [(_cos(q, v), j) for j, v in zip(jobs, vecs[1:])]
    for _, j in sims:
        j.match_reasons = list(getattr(j, "match_reasons", []) or [])
    top = sorted(sims, key=lambda p: -p[0])[:top_k]
    recalled = 0
    for sim, j in top:
        j.recalled = True  # type: ignore[attr-defined]
        j.match_reasons.append("embedding_recalled")  # type: ignore[attr-defined]
        recalled += 1
    log.info("embeddings recall over %d jobs in %.2fs", len(jobs), time.monotonic() - t0)
    return "embedding_recall"
