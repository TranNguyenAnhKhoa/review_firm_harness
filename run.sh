#!/usr/bin/env bash
# Harness command line (works from any folder; relative paths are relative to where you call it).
#   ./run.sh new <job> <video> [--title T] [--voice baotrang|maichi|kimoanh] [--read agy|claude|codex|manual]
#   ./run.sh run <job> [--from STAGE] [--to STAGE] [--only STAGE] [--force]
#   ./run.sh status [<job>] | approve <job> read|write | reject <job> read|write --note "..."
#   ./run.sh import <job> timeline|review <file> | check <job> | brief <video> | doctor | serve
# Full help: ./run.sh --help
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"
[ -x "$PYTHON" ] || { echo "Thiếu .venv: chạy ./setup.sh" >&2; exit 2; }
if [ -f "$ROOT/.env" ]; then set -a; . "$ROOT/.env"; set +a; fi
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m harness "$@"
