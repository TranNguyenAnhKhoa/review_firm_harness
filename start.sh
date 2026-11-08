#!/usr/bin/env bash
# Check the environment, then serve the dashboard in the foreground (Ctrl+C stops it).
#   ./start.sh [--port 8790] [--host 127.0.0.1] [--no-browser] [--check]
# Port/host also come from .env (HARNESS_PORT, HARNESS_HOST). For a background service: ./service.sh install
# From another computer: ssh -L 8790:127.0.0.1:8790 <this-machine>, then open http://127.0.0.1:8790
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
[ -x .venv/bin/python ] || { echo "Thiếu .venv: chạy ./setup.sh" >&2; exit 2; }
if [ -f .env ]; then set -a; . ./.env; set +a; fi
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
ARGS=()
CHECK=0
OPEN=1
while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=1 ;;
    --no-browser) OPEN=0 ;;
    --port|--host) ARGS+=("$1" "$2"); shift ;;
    *) echo "Tham số lạ: $1" >&2; exit 2 ;;
  esac
  shift
done
.venv/bin/python -m harness doctor || echo "(Một số mục còn thiếu: dashboard vẫn chạy, pipeline có thể lỗi ở bước cần chúng)"
[ "$CHECK" = 1 ] && exit 0
[ "$OPEN" = 1 ] && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] || ARGS+=(--no-browser)
exec .venv/bin/python -m harness serve "${ARGS[@]}"
