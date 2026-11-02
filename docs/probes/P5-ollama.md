# P5 — Ollama / embeddings

**Verdict: PASS — embeddings recall ON.**

- `ollama` CLI present at `/usr/local/bin/ollama`.
- `ollama list` includes **`nomic-embed-text`** (274 MB) already pulled.
- `POST http://localhost:11434/api/embed` with a test sentence → 200,
  **768-dim** vector.
- `embed.py` therefore defaults to ON (`embedding_recall: on`). Failure to
  reach ollama at run time is never fatal: keyword-only degradation + report
  flag `recall_mode=keyword_only` (§6.7 style).
