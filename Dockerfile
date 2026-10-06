FROM ghcr.io/astral-sh/uv:0.11.13 AS uv
FROM caddy:2.10.2 AS caddy
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
COPY --from=caddy /usr/bin/caddy /usr/bin/caddy
COPY Caddyfile.public Caddyfile.public
COPY Caddyfile.auth Caddyfile.auth
COPY scripts/container_entrypoint.sh /usr/local/bin/container_entrypoint.sh
RUN chmod 0755 /usr/local/bin/container_entrypoint.sh \
    && mkdir -p /config/caddy /data \
    && chown -R 10001:10001 /config/caddy /data
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    EVIDENCEFORGE_DATA_DIR=/data EVIDENCEFORGE_MODEL_PROVIDER=fixture \
    EVIDENCEFORGE_TRACING_ENABLED=false PORT=8501 \
    EVIDENCEFORGE_STREAMLIT_PORT=8502 \
    XDG_CONFIG_HOME=/config
USER 10001:10001
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8501') + '/_stcore/health', timeout=3)"
ENTRYPOINT ["/usr/local/bin/container_entrypoint.sh"]
