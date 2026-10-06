#!/bin/sh
set -eu

streamlit_port="${EVIDENCEFORGE_STREAMLIT_PORT:-8502}"
export EVIDENCEFORGE_STREAMLIT_PORT="$streamlit_port"

case "${CADDY_AUTH_REQUIRED:-false}" in
    true|TRUE|1|yes|YES)
        : "${CADDY_AUTH_USERNAME:?CADDY_AUTH_USERNAME is required when proxy auth is enabled}"
        : "${CADDY_AUTH_PASSWORD_HASH:?CADDY_AUTH_PASSWORD_HASH is required when proxy auth is enabled}"
        config=/app/Caddyfile.auth
        ;;
    *)
        config=/app/Caddyfile.public
        ;;
esac

caddy validate --config "$config" --adapter caddyfile
evidenceforge-ui --host 127.0.0.1 --port "$streamlit_port" &
streamlit_pid=$!
caddy run --config "$config" --adapter caddyfile &
caddy_pid=$!

cleanup() {
    kill "$streamlit_pid" "$caddy_pid" 2>/dev/null || true
    wait "$streamlit_pid" "$caddy_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM

# Stop the container when either required process exits. Platform restarts then
# recover checkpoints instead of leaving an unhealthy proxy running forever.
while kill -0 "$streamlit_pid" 2>/dev/null && kill -0 "$caddy_pid" 2>/dev/null; do
    sleep 1
done
exit 1
