# P2 — Playwright image

**Verdict: PASS (with a pinning caveat).**

- Pulled `mcr.microsoft.com/playwright/python:v1.64.1-noble` (latest stable
  tag at build time; registry listed up to v1.64.1-noble-arm64).
- Headless render test `example.com` inside container: **works**
  (title returned).
- **Caveat:** this image tag ships the browsers (`/ms-playwright/chromium-1248`,
  `firefox-1555`, `webkit-2370`, Windows arm64 multi-arch manifest) but the
  `playwright` **pip package is not importable** in this tag. Any image built
  from it must `RUN pip3 install --no-cache-dir playwright==1.64.1`.
  This is pinned in the project `Dockerfile`.
- Recorded for `C3`: base image = v1.64.1-noble, playwright pip ==1.64.1.
