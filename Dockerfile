FROM ghcr.io/astral-sh/uv:0.11.13 AS uv
FROM python:3.12.13-slim-bookworm AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
RUN uv sync --locked --no-dev --extra ui --no-editable --python /usr/local/bin/python

FROM python:3.12.13-slim-bookworm AS runtime
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --create-home app \
    && mkdir -p /data && chown app:app /data
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    EVIDENCEFORGE_DATA_DIR=/data EVIDENCEFORGE_MODEL_PROVIDER=fixture \
    EVIDENCEFORGE_TRACING_ENABLED=false PORT=8501
USER 10001:10001
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8501') + '/_stcore/health', timeout=3)"
CMD ["evidenceforge-ui", "--host", "0.0.0.0"]
