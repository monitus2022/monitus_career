# Dockerfile — pinned per P2 (docs/probes/P2-playwright-image.md)
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

# P2 caveat: the base image ships browsers but not the playwright pip package
RUN pip3 install --no-cache-dir --quiet playwright==1.64.1

WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY pipeline/ ./pipeline/
COPY fixtures/synthetic/ ./fixtures/synthetic/
COPY scripts/ ./scripts/
COPY profile.yaml.example ./profile.yaml.example
COPY pipeline/config.yaml ./pipeline/config.yaml

# Daily-run entrypoint; mounts: fixtures (captures), runs/ (state)
# Dry-run example:
#   docker compose run pipeline python -m pipeline.run --dry-run
CMD ["python", "-m", "pipeline.run", "--data-dir=/app/runs"]
