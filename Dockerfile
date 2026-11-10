# syntax=docker/dockerfile:1.7
# Parser Service image: runtime dependencies only, non-root, migrations run at start-up.

FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runtime
# libmagic is needed by python-magic for content-based type detection (Phase 0, track B).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system parser && useradd --system --gid parser --home /app parser
WORKDIR /app
COPY --from=builder --chown=parser:parser /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PARSER_ARTIFACT_ROOT=/var/lib/parser/artifacts \
    PARSER_HTTP_HOST=0.0.0.0 \
    PARSER_HTTP_PORT=8000
RUN mkdir -p /var/lib/parser/artifacts && chown -R parser:parser /var/lib/parser
USER parser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"
CMD ["parser-api"]
